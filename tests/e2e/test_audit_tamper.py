"""Is a tamper of `audit_log` actually detectable?

Written from `DATA-MODEL.md` §8 (the hash chain and its stated ceiling),
`COMPLIANCE.md` §8.5's list of what the chain must cover, and
ENGINE-DIVERGENCE §3.5–3.8 and §7.1.

`DATA-MODEL.md` §8 claims two separate things, and they need separating:

1. **append-only** — UPDATE and DELETE are refused by a database trigger. That
   is a prevention claim.
2. **tamper-evident** — `row_hash = sha256(prev_hash || canonical_json(row))`,
   verified by `verify_audit_chain`. That is a detection claim, and it only
   matters for a tamperer who got past (1).

So the interesting tests are the ones where the trigger is gone — because a
tamperer with write access to the database has `DROP TRIGGER`. These tests drop
whatever triggers the live schema has on `audit_log`, which is both the attack
and a check that dropping them is all it takes.

Per ENGINE-DIVERGENCE §9 item 4(b), every assertion that a trigger fired catches
`django.db.DatabaseError`, the common parent, because the class differs by
engine: SQLite's `RAISE(ABORT)` surfaces as `IntegrityError` and Postgres's
`RAISE EXCEPTION` as `InternalError`.
"""

import pytest
from django.db import DatabaseError, connection, transaction

from apps.core.errors import AuditChainBroken
from apps.core.models import AuditLog, Campus
from apps.core.services import GENESIS_HASH, record_audit, verify_audit_chain

pytestmark = pytest.mark.django_db


def _chain(campus, n=3):
    """Append n real audit rows through the service, as production does."""
    return [record_audit(None, f"qa.step{i}", campus) for i in range(n)]


def _drop_audit_triggers():
    """The tamperer's first move. Returns the names dropped.

    Discovered from the live schema rather than read out of the migration, so
    this works whatever the triggers are called — and so a missing trigger shows
    up as an empty list rather than as a passing test.
    """
    if connection.vendor != "sqlite":
        pytest.skip(
            "NOT VERIFIABLE ON THIS ENGINE (vendor="
            f"{connection.vendor}, slice=S0): dropping the append-only triggers "
            "to simulate a tamper is written for SQLite's `sqlite_master`. The "
            "PostgreSQL equivalent needs a server (ENGINE-DIVERGENCE §9 item 3)."
        )
    with connection.cursor() as cur:
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='audit_log'"
        )
        names = [r[0] for r in cur.fetchall()]
        for name in names:
            cur.execute(f'DROP TRIGGER "{name}"')
    return names


@pytest.fixture
def campus(db):
    from apps.core.models import City

    city = City.objects.create(name="Chennai", state="Tamil Nadu")
    return Campus.objects.create(city=city, name="Audit Campus", slug="audit")


# --------------------------------------------------------------------------
# 1. prevention: the trigger refuses UPDATE and DELETE
# --------------------------------------------------------------------------


def test_an_audit_row_cannot_be_updated(campus, engine):
    """`DATA-MODEL.md` §8 / ENGINE-DIVERGENCE §3.5: append-only is a property of
    the database, not of the service layer."""
    rows = _chain(campus, 1)
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            AuditLog.objects.filter(pk=rows[0].pk).update(action="qa.rewritten")
    assert AuditLog.objects.get(pk=rows[0].pk).action == "qa.step0"


def test_an_audit_row_cannot_be_deleted(campus, engine):
    rows = _chain(campus, 1)
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            AuditLog.objects.filter(pk=rows[0].pk).delete()
    assert AuditLog.objects.filter(pk=rows[0].pk).exists()


def test_the_whole_audit_table_cannot_be_emptied(campus, engine):
    _chain(campus, 3)
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            AuditLog.objects.all().delete()
    assert AuditLog.objects.count() == 3


def test_the_append_only_triggers_exist_at_all(campus):
    """If there are no triggers, every test above passed for a different reason
    than the one claimed. This is the test that says which."""
    names = _drop_audit_triggers()
    assert names, (
        "no trigger on `audit_log` in the live schema: `DATA-MODEL.md` §8's "
        "append-only claim would rest on nothing"
    )


# --------------------------------------------------------------------------
# 2. detection: what the hash chain catches once the trigger is gone
# --------------------------------------------------------------------------


def test_a_rewritten_row_is_detected_and_named(campus):
    """The tamper the chain exists for: a middle row's content is changed."""
    rows = _chain(campus, 3)
    _drop_audit_triggers()
    with connection.cursor() as cur:
        cur.execute("UPDATE audit_log SET action = 'qa.rewritten' WHERE id = %s",
                    [rows[1].pk])
    with pytest.raises(AuditChainBroken) as exc:
        verify_audit_chain()
    assert str(rows[1].pk) in str(exc.value), (
        "the chain broke but did not name the row that broke it, which is the "
        "difference between an alert and an investigation"
    )


def test_a_deleted_middle_row_is_detected(campus):
    """Deleting from the middle leaves a `prev_hash` pointing at nothing."""
    rows = _chain(campus, 3)
    _drop_audit_triggers()
    with connection.cursor() as cur:
        cur.execute("DELETE FROM audit_log WHERE id = %s", [rows[1].pk])
    with pytest.raises(AuditChainBroken):
        verify_audit_chain()


def test_a_forged_appended_row_is_detected(campus):
    """An INSERT is legal — the table is append-only, not read-only — so a
    tamperer can add a row. A row whose `prev_hash` does not match the head, or
    whose `row_hash` does not match its contents, must be caught."""
    _chain(campus, 2)
    AuditLog.objects.create(
        actor_type="SYSTEM", action="qa.forged", object_type="Campus",
        object_id=str(campus.pk), prev_hash="f" * 64, row_hash="e" * 64,
    )
    with pytest.raises(AuditChainBroken):
        verify_audit_chain()


def test_a_row_whose_hash_was_recomputed_but_whose_link_was_not_is_detected(campus):
    """Half-competent tampering: the attacker fixes `row_hash` for the row they
    changed but not the `prev_hash` of the row after it."""
    rows = _chain(campus, 3)
    _drop_audit_triggers()
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE audit_log SET action = 'qa.rewritten', row_hash = %s WHERE id = %s",
            ["a" * 64, rows[1].pk],
        )
    with pytest.raises(AuditChainBroken):
        verify_audit_chain()


def test_an_empty_chain_verifies_and_reports_the_genesis_head():
    """The boundary: no rows is a valid chain, and the head is the genesis
    constant rather than NULL, so the first row is as constrained as the rest."""
    assert AuditLog.objects.count() == 0
    checked, head = verify_audit_chain()
    assert (checked, head) == (0, GENESIS_HASH)


# --------------------------------------------------------------------------
# 3. the ceilings `DATA-MODEL.md` §8 admits — asserted, so they stay admitted
# --------------------------------------------------------------------------


def test_the_chain_is_tamper_evident_not_tamper_proof(campus):
    """**Documented ceiling, asserted so it cannot drift into a stronger claim.**

    `DATA-MODEL.md` §8's own note: "assumes one appender and does not prove the
    chain head was not rewritten. Upgrade path: write the daily chain head to a
    second place."

    Two tampers this chain cannot detect, measured:

    (a) **tail truncation** — deleting the newest rows leaves a chain that is
        internally consistent, so `verify_audit_chain` returns OK. Anything the
        last rows recorded is gone without a trace in the database.
    (b) **full rewrite** — an attacker holding the application's own hashing
        code can change a row and recompute every hash after it. The chain then
        verifies.

    Both are closed by the same one-line S8 item: print the head hash somewhere
    outside the database each day. Until then, `verify_audit_chain` passing is
    evidence against *partial* tampering only. When the daily head lands, this
    test must be replaced by one asserting detection.
    """
    rows = _chain(campus, 4)
    _drop_audit_triggers()

    # (a) tail truncation
    with connection.cursor() as cur:
        cur.execute("DELETE FROM audit_log WHERE id = %s", [rows[3].pk])
    checked, _head = verify_audit_chain()
    assert checked == 3, "tail truncation was expected to go undetected"

    # (b) full rewrite, using the application's own hashing code
    from apps.core.services import _canonical, _row_fields, _sha256

    with connection.cursor() as cur:
        cur.execute("UPDATE audit_log SET action = 'qa.rewritten' WHERE id = %s",
                    [rows[1].pk])
    prev = GENESIS_HASH
    for row in list(AuditLog.objects.order_by("id")):
        new_hash = _sha256(prev + _canonical(_row_fields(row)))
        with connection.cursor() as cur:
            cur.execute("UPDATE audit_log SET prev_hash = %s, row_hash = %s WHERE id = %s",
                        [prev, new_hash, row.pk])
        prev = new_hash
    checked, head = verify_audit_chain()
    assert (checked, head) == (3, prev), (
        "a wholesale rewrite was expected to verify clean — if this now fails, "
        "the head is being checked against something outside the database and "
        "DATA-MODEL.md §8's ponytail note should be closed"
    )
    assert AuditLog.objects.filter(action="qa.rewritten").exists()


def test_an_audit_row_rolls_back_with_the_change_it_records(campus):
    """`apps/core/services.py`'s own rule, from API-CONTRACT §3: "a rolled-back
    mutation must roll back its audit row". `record_audit` retries inside a
    savepoint, so this is worth asserting rather than assuming: a savepoint that
    committed independently would leave an audit row for a change that never
    happened."""
    before = AuditLog.objects.count()
    with pytest.raises(RuntimeError):
        with transaction.atomic():
            record_audit(None, "qa.rolled_back", campus)
            raise RuntimeError("the mutation failed after the audit row")
    assert AuditLog.objects.count() == before
    assert not AuditLog.objects.filter(action="qa.rolled_back").exists()


# --------------------------------------------------------------------------
# 4. what cannot be verified on this engine
# --------------------------------------------------------------------------


def test_truncate_cannot_empty_the_audit_log(engine):
    pytest.skip(
        f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S0): "
        "`DATA-MODEL.md` §8 append-only has a TRUNCATE-shaped hole on PostgreSQL "
        "that does not exist here, because SQLite has no TRUNCATE statement at "
        "all (ENGINE-DIVERGENCE §3.6, measured as a syntax error). The "
        "BEFORE TRUNCATE statement trigger in migration 0002 is unexecuted text "
        "and ENGINE-DIVERGENCE §3.6 calls it 'the single most important thing "
        "for a Postgres box to confirm'. QA agrees and has verified nothing "
        "about it."
    )


def test_the_plpgsql_append_only_trigger_body_is_valid(engine):
    pytest.skip(
        f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S0): migration "
        "0002's PostgreSQL half has never been parsed by a server "
        "(ENGINE-DIVERGENCE §1, §3.5). The SQLite half is what the tests above "
        "exercise. A green run here says nothing about production's trigger."
    )


def test_concurrent_appenders_cannot_fork_the_chain(engine):
    pytest.skip(
        f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S0): "
        "`audit_log.prev_hash UNIQUE` exists so that the loser of a race retries "
        "against the new head. SQLite has one database writer, so the race "
        "cannot occur and a green test would prove the uniqueness of the index, "
        "not the concurrency property it was added for "
        "(ENGINE-DIVERGENCE §4.1, §4.5)."
    )
