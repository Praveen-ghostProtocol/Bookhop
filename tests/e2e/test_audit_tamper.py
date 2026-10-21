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

    **Now written for both engines.** Until the first PostgreSQL run this
    helper skipped off SQLite, which meant the chain's *detection* capability —
    the whole subject of this file, and the charter question "is a tamper
    actually detectable" — had been verified on the development engine only,
    while ENGINE-DIVERGENCE §10.4 verified *prevention* on PostgreSQL. Those are
    two different claims and only one of them was covered on the engine that
    will hold the data.

    On PostgreSQL the tamperer's move is `ALTER TABLE … DISABLE TRIGGER USER`
    rather than `DROP TRIGGER`: it is name-independent, it is reversed by the
    test's rollback, and — asserted below — it works on `ENABLE ALWAYS`
    triggers, because ALWAYS governs `session_replication_role` and not an
    explicit disable. A tamperer with `ALTER` on the table has it either way.
    """
    if connection.vendor == "postgresql":
        with connection.cursor() as cur:
            cur.execute(
                "SELECT tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                "WHERE c.relname = 'audit_log' AND NOT t.tgisinternal"
            )
            names = [r[0] for r in cur.fetchall()]
            cur.execute("ALTER TABLE audit_log DISABLE TRIGGER USER")
            cur.execute(
                "SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                "WHERE c.relname = 'audit_log' AND NOT t.tgisinternal "
                "AND t.tgenabled <> 'D'"
            )
            still_enabled = cur.fetchone()[0]
        assert still_enabled == 0, (
            "DISABLE TRIGGER USER left a guard enabled, so the tamper below "
            "would be blocked and the detection assertions would pass for the "
            "wrong reason"
        )
        return names

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


#: `CLAUDE.md` rule 12, in the shape the first PostgreSQL run exposed
#: (ENGINE-DIVERGENCE §10.6). A bare `pytest.skip()` whose reason interpolates
#: the live vendor into a sentence about SQLite is honest on SQLite and
#: self-contradicting on PostgreSQL — it names the wrong engine and stops being
#: true. The tests below therefore have **bodies**, and skip through a marker
#: that states which engine they need and why.
postgres_only = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason=(
        "REQUIRES PostgreSQL (slice=S0): this asserts a plpgsql trigger body or "
        "a TRUNCATE guard. SQLite has no TRUNCATE statement at all (measured: a "
        "syntax error) and no plpgsql, so the property cannot exist here "
        "(ENGINE-DIVERGENCE §3.5, §3.6). Run with BOOKHOP_DB_ENGINE=postgres."
    ),
)

#: ADR-002/DATA-MODEL guards raise with `RAISE EXCEPTION`, which is SQLSTATE
#: P0001. `CLAUDE.md` rule 16: a refused operation is not evidence the guard
#: fired for the right reason, because plpgsql resolves identifiers at the first
#: execution of each branch — so a body with a typo in an unexercised branch
#: creates cleanly and then fails *as something else* while still blocking the
#: operation. The SQLSTATE and the message text are what distinguish "the guard
#: refused this" from "the guard is broken and the write happened not to land".
RAISE_EXCEPTION = "P0001"


def _sqlstate(exc):
    """The SQLSTATE psycopg attached to a refusal, or None."""
    cause = getattr(exc, "__cause__", None)
    return getattr(getattr(cause, "diag", None), "sqlstate", None)


def _assert_guard_refused(excinfo, *, contains):
    """Rule 16's standard, applied once so every call site states it."""
    assert _sqlstate(excinfo.value) == RAISE_EXCEPTION, (
        "the operation was refused, but not by a plpgsql RAISE EXCEPTION "
        f"(SQLSTATE {_sqlstate(excinfo.value)!r}). Rule 16: a refusal is not "
        "evidence the guard fired for the right reason"
    )
    assert contains in str(excinfo.value), (
        f"the guard raised P0001 but the message does not contain {contains!r}: "
        f"{excinfo.value}"
    )
    assert "%" not in str(excinfo.value), (
        "a literal % survived into the message, so a format specifier did not "
        "interpolate (ENGINE-DIVERGENCE §10.1)"
    )


@postgres_only
@pytest.mark.parametrize(
    "operation,expected",
    [("update", "UPDATE is not permitted"), ("delete", "DELETE is not permitted")],
)
def test_the_plpgsql_append_only_trigger_body_fires(campus, operation, expected):
    """**QA-S0 §7 item 1, now written and run.** `DATA-MODEL.md` §8's
    append-only guarantee, on the engine that will actually store the audit log.

    Until this run, migration 0002's PostgreSQL half had never been parsed by a
    server: the SQLite half was verified and the production half was unexecuted
    text. This asserts the real thing, to rule 16's standard — the SQLSTATE
    **and** the message, because `TG_OP` and `TG_TABLE_NAME` interpolate inside
    the message and §10.1 found four `%` specifiers that psycopg was eating
    before PostgreSQL ever saw them.

    It also pins what ENGINE-DIVERGENCE §10.2 corrected: the exception class is
    `ProgrammingError` on psycopg 3, not the `InternalError` §3.8 predicted.
    Caught as `DatabaseError` for that reason, which is why nothing broke.
    """
    rows = _chain(campus, 1)
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            if operation == "update":
                AuditLog.objects.filter(pk=rows[0].pk).update(action="qa.tampered")
            else:
                AuditLog.objects.filter(pk=rows[0].pk).delete()
    _assert_guard_refused(exc, contains=expected)
    assert "audit_log is append-only" in str(exc.value)
    assert AuditLog.objects.get(pk=rows[0].pk).action == "qa.step0"


@postgres_only
def test_the_append_only_guard_is_a_programming_error_not_an_integrity_error(campus):
    """The class, asserted rather than assumed — ENGINE-DIVERGENCE §10.2.

    §3.8 predicted `InternalError`; psycopg 3 gives `ProgrammingError`. The
    instruction that survived both is "catch `DatabaseError`". This test is the
    one that would have caught the wrong prediction, so it exists now: a service
    that catches `IntegrityError` to turn a trigger refusal into a 4xx would
    swallow nothing here, and S2's price handler and S4's `accept_offer` are the
    two callers that will be tempted.
    """
    from django.db import IntegrityError, ProgrammingError

    rows = _chain(campus, 1)
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            AuditLog.objects.filter(pk=rows[0].pk).update(action="qa.tampered")
    assert isinstance(exc.value, ProgrammingError)
    assert not isinstance(exc.value, IntegrityError), (
        "a trigger refusal arriving as IntegrityError would make the "
        "unique-index and trigger paths indistinguishable to a caller"
    )


@postgres_only
@pytest.mark.parametrize("table", ["audit_log", "gate_authorisations"])
def test_truncate_cannot_empty_the_audit_log(campus, table):
    """**QA-S0 §7 item 2 — the assertion reserved for QA, now written.**

    ENGINE-DIVERGENCE §3.6 calls this "the single most important thing for a
    Postgres box to confirm", because row triggers **do not fire on TRUNCATE**:
    the append-only guarantee has a hole on PostgreSQL that does not exist on
    SQLite, and migration 0003's statement-level trigger is the only thing
    closing it.

    The test harness declares `bookhop.allow_flush` on every connection, so the
    escape has to be withdrawn inside the test to see the guard at all — which
    is why this one was left for QA's tree. `SET` is transaction-scoped, so the
    withdrawal is undone by the rollback that ends the test.

    Asserted to rule 16's standard, on both guarded tables, and each message
    must name **its own** table — `TG_TABLE_NAME` is interpolated, and a
    statement trigger has no `NEW` record to resolve it from, which is the
    ordering hazard §10.4 item 2 covers.
    """
    _chain(campus, 2)
    before = AuditLog.objects.count()

    with connection.cursor() as cur:
        cur.execute("SET bookhop.allow_flush = 'no'")

    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(f'TRUNCATE "{table}"')
    _assert_guard_refused(exc, contains="TRUNCATE is not permitted")
    assert f"{table} is append-only" in str(exc.value), (
        f"the guard fired but did not name {table!r}: {exc.value}"
    )
    assert AuditLog.objects.count() == before


@postgres_only
def test_the_truncate_escape_is_an_escape_and_not_dead_code(campus):
    """The inverse of the test above, and the reason the guard is not simply
    "TRUNCATE never works".

    A guard that refused every TRUNCATE unconditionally would pass the test
    above while breaking every `transactional_db` teardown — which is exactly
    the collision ENGINE-DIVERGENCE §7.1 was written about. So the escape must
    be proved to *work*: with `bookhop.allow_flush = 'yes'` the same statement
    succeeds.

    Four states are measured, because the whole point of §7's item 7 is the
    direction of the default: unset → refused, `'no'` → refused, `'YES'` in the
    wrong case → refused, `'yes'` → permitted.
    """
    _chain(campus, 1)

    for value, permitted in (("no", False), ("YES", False), ("yes", True)):
        sid = transaction.savepoint()
        with connection.cursor() as cur:
            cur.execute("SET bookhop.allow_flush = %s", [value])
        if permitted:
            with connection.cursor() as cur:
                cur.execute('TRUNCATE "audit_log"')
            assert AuditLog.objects.count() == 0
        else:
            with pytest.raises(DatabaseError) as exc:
                with transaction.atomic():
                    with connection.cursor() as cur:
                        cur.execute('TRUNCATE "audit_log"')
            _assert_guard_refused(exc, contains="TRUNCATE is not permitted")
        transaction.savepoint_rollback(sid)

    # And unset: RESET returns the connection to having no declaration at all,
    # which is the state a production connection is in.
    with connection.cursor() as cur:
        cur.execute("RESET bookhop.allow_flush")
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute('TRUNCATE "audit_log"')
    _assert_guard_refused(exc, contains="TRUNCATE is not permitted")


@postgres_only
def test_the_truncate_guard_does_not_block_update_or_delete_for_the_wrong_reason(campus):
    """A negative control on the *escape*, not on the guard.

    ENGINE-DIVERGENCE §7.1 says "UPDATE and DELETE get no escape; only the
    whole-table flush". QA asserted that as migration text; this asserts it as
    behaviour. With the escape fully granted, an UPDATE and a DELETE must
    **still** be refused — otherwise one `SET` turns the append-only guarantee
    off entirely, and the text audit would have been measuring the wrong thing.
    """
    rows = _chain(campus, 1)
    with connection.cursor() as cur:
        cur.execute("SET bookhop.allow_flush = 'yes'")

    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            AuditLog.objects.filter(pk=rows[0].pk).update(action="qa.tampered")
    _assert_guard_refused(exc, contains="UPDATE is not permitted")

    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            AuditLog.objects.filter(pk=rows[0].pk).delete()
    _assert_guard_refused(exc, contains="DELETE is not permitted")


# `test_concurrent_appenders_cannot_fork_the_chain` lived here as a bare `pytest.skip()` until PostgreSQL 16
# arrived. ENGINE-DIVERGENCE 10.6 is right that a skip reason naming
# SQLite while running on PostgreSQL is self-contradicting, so the
# placeholder is gone and the assertion is written:
#   tests/e2e/test_postgres_concurrency.py::test_concurrent_appenders_cannot_fork_the_chain
