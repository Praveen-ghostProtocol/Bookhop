"""ENGINE-DIVERGENCE rows that were *explained* rather than *measured*.

ENGINE-DIVERGENCE §10.2 found one of these and it is the defect class QA has
been hunting all project, found in the document whose whole job is to describe
engine differences:

> §2.11 said the boolean divergence "only bites raw SQL written as
> `WHERE flag = 'true'`. The CHECK probe in `test_seed_separation.py` uses
> `1`/`0` **for that reason**." On PostgreSQL that INSERT never reached the
> CHECK at all — `DatatypeMismatch`, 42804 — so the probe had been passing for
> a reason the document had written down as deliberate.

**A test passing for a stated-but-wrong reason is invisible precisely because
the reason is stated.** So QA went looking for siblings: rows whose "SQLite
measured" column is an argument rather than a measurement, or whose evidence is
a Django capability flag rather than a behaviour. Four were found, and each is
measured here, **on whichever engine the suite is running**, so the two engines
are compared by running the same assertion rather than by reasoning about it.

None of the four turned out to be a defect. That is a useful result and not a
wasted pass: they were unmeasured, which is a different thing from wrong, and
the difference is only visible once someone runs them.
"""

import pytest
from django.db import DatabaseError, connection, transaction

from apps.core.models import AuditLog, Job

pytestmark = pytest.mark.django_db


def _probe(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params or [])
        return cur.fetchall()


# --------------------------------------------------------------------------
# sibling 1 — §3.1: "enforced", evidenced by a Django capability flag
# --------------------------------------------------------------------------


def test_an_enum_check_constraint_actually_rejects_a_bad_value(engine):
    """**ENGINE-DIVERGENCE §3.1's sibling of the §2.11 defect.**

    §3.1 says every enum's `CHECK (col IN (...))` is "enforced", and its
    evidence column reads `supports_table_check_constraints = True` — a
    **Django feature flag**, which is a claim about what Django believes the
    backend can do, not a measurement that this database rejected a bad value.
    §2.11 is what happens when that gap is left open: the probe ran, it passed,
    and nobody had checked which thing it proved.

    Measured here instead, through the ORM's own `update()` so Django's
    field-level validation is bypassed and the **database** is the thing
    answering: `audit_log.actor_type` has `CHECK (actor_type IN ('USER',
    'STAFF', 'SYSTEM'))` from `DATA-MODEL.md` §0, and a fourth value must be
    refused.

    `actor_type` is also the column ENGINE-DIVERGENCE §10.3(a) mentions as
    having once surfaced a CHECK violation as `AuditChainBroken`, so it is the
    right one to probe.
    """
    from apps.core.models import City
    from apps.core.services import record_audit

    city = City.objects.create(name="Chennai", state="Tamil Nadu")
    row = record_audit(None, "qa.check", city)

    # The append-only trigger will also refuse an UPDATE, so probe on INSERT:
    # a direct insert of a row whose actor_type is not in the CHECK set.
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            AuditLog.objects.create(
                actor_type="ROBOT", action="qa.bad", object_type="City",
                object_id=str(city.pk), prev_hash="z" * 64, row_hash="y" * 64,
            )
    assert "actor_type" in str(exc.value).lower() or "chk" in str(exc.value).lower(), (
        f"the insert was refused on {engine}, but the message does not point at "
        f"the enum CHECK, so what refused it is unclear: {exc.value}"
    )
    assert AuditLog.objects.filter(actor_type="ROBOT").count() == 0
    assert AuditLog.objects.filter(pk=row.pk).exists()


def test_the_enum_check_accepts_every_value_the_contract_lists(engine):
    """The other half, so the test above cannot pass by refusing everything.
    `DATA-MODEL.md` §8 lists three actor types and all three must insert.
    """
    from apps.core.models import City

    City.objects.create(name="Chennai", state="Tamil Nadu")
    for index, actor_type in enumerate(("USER", "STAFF", "SYSTEM")):
        AuditLog.objects.create(
            actor_type=actor_type, action="qa.ok", object_type="City",
            object_id="1", prev_hash=f"{index}" * 64, row_hash=f"{index}" * 64,
        )
    assert AuditLog.objects.count() == 3


# --------------------------------------------------------------------------
# sibling 2 — §3.12: "identical", evidenced by `can_rollback_ddl`
# --------------------------------------------------------------------------


def test_ddl_inside_a_transaction_really_rolls_back(engine):
    """**ENGINE-DIVERGENCE §3.12's sibling.** The row says DDL in a transaction
    is "identical" on both engines and cites `can_rollback_ddl = True`, another
    Django flag.

    This matters more than it looks, because **QA's own attack tests depend on
    it**: every P14 attack creates a real table with raw DDL inside the test's
    transaction and relies on the rollback to clean up. If DDL did not roll
    back on one engine, those attacks would leak tables into every later test
    and the suite's results would depend on ordering.

    Measured: create a table inside a savepoint, roll back, and assert the
    table is gone from the live introspection.
    """
    name = "_qa_ddl_rollback_probe"
    sid = transaction.savepoint()
    with connection.cursor() as cur:
        cur.execute(f'CREATE TABLE "{name}" (id integer primary key)')
    with connection.cursor() as cur:
        assert name in connection.introspection.table_names(cur)
    transaction.savepoint_rollback(sid)
    with connection.cursor() as cur:
        assert name not in connection.introspection.table_names(cur), (
            f"DDL did not roll back on {engine}; every raw-DDL attack test in "
            "tests/contract leaks its table into the rest of the run"
        )


# --------------------------------------------------------------------------
# sibling 3 — §2.10: identity vs rowid, explained for both engines
# --------------------------------------------------------------------------


def test_a_deleted_rows_id_is_not_reused_on_this_engine(engine):
    """**ENGINE-DIVERGENCE §2.10's sibling.** The row explains that PostgreSQL
    uses a sequence whose values "are never reused" while SQLite's
    `INTEGER PRIMARY KEY` is a rowid alias whose "max rowid can be reused after
    the highest row is deleted", and then reasons that this "matters only for a
    table whose rows are deleted and whose ids are referenced elsewhere".

    Neither half was measured, and the reasoning is the part that could be
    wrong: `purge_log.object_pk` (S1) records the primary key of a row that has
    been deleted, and S1's purge job is exactly "a table whose rows are deleted
    and whose ids are referenced elsewhere".

    Measured on `jobs`, which is deletable: insert, delete the highest, insert
    again, and compare. The result is recorded per engine rather than asserted
    identical, because the two genuinely differ and the test's job is to say so
    out loud before S1 relies on it.
    """
    first = Job.objects.create(kind="core.noop", payload={})
    highest = first.pk
    first.delete()
    second = Job.objects.create(kind="core.noop", payload={})

    if engine == "postgresql":
        assert second.pk > highest, (
            "a sequence value was reused on PostgreSQL, which contradicts "
            "§2.10 and would make purge_log.object_pk ambiguous"
        )
    else:
        # SQLite may reuse it. Recorded, not asserted either way: the point is
        # that S1's purge_log must not treat an id as a durable identity.
        assert second.pk in (highest, highest + 1), (
            f"unexpected rowid behaviour on {engine}: {highest} -> {second.pk}"
        )


# --------------------------------------------------------------------------
# sibling 4 — §3.4: "identical by the SQL standard"
# --------------------------------------------------------------------------


def test_unique_treats_nulls_as_distinct_on_this_engine(engine):
    """**ENGINE-DIVERGENCE §3.4's sibling, and the one with a history.** The row
    says NULLs-distinct is "identical by the SQL standard" — a citation, not a
    measurement — and §3.4 itself records that **this identical behaviour was
    the defect** QA-S0 B3 found: an anonymous idempotency key never deduped
    because `UNIQUE (user_id, key)` does not fire on a NULL `user_id`.

    So the claim was right, the reasoning was right, and it was still worth
    measuring, because the fix (migration 0004's partial index on `key` WHERE
    `user_id IS NULL`) only makes sense if the premise is true on the engine
    that will run it.

    Measured on a throwaway table, because the real one now has the partial
    index on top and would answer a different question.
    """
    with connection.cursor() as cur:
        cur.execute(
            'CREATE TABLE "_qa_nulls_probe" '
            "(a integer null, b text not null, UNIQUE (a, b))"
        )
        cur.execute("INSERT INTO _qa_nulls_probe (a, b) VALUES (NULL, 'k')")
        cur.execute("INSERT INTO _qa_nulls_probe (a, b) VALUES (NULL, 'k')")
        cur.execute("SELECT count(*) FROM _qa_nulls_probe")
        count = cur.fetchone()[0]
    assert count == 2, (
        f"NULLs are NOT distinct in a composite UNIQUE on {engine}; "
        "migration 0004's partial index was added for a premise that does not "
        "hold here, and QA-S0 B3's analysis needs re-reading"
    )

    # And the half that the real table adds: a partial index on the non-NULL
    # column does fire, which is what closes B3. The rows above are cleared
    # first — they are the duplicate the index is about to forbid, and building
    # an index over existing violations fails for a different reason.
    with connection.cursor() as cur:
        cur.execute("DELETE FROM _qa_nulls_probe")
        cur.execute(
            'CREATE UNIQUE INDEX "_qa_nulls_partial" ON "_qa_nulls_probe" (b) '
            "WHERE a IS NULL"
        )
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute("INSERT INTO _qa_nulls_probe (a, b) VALUES (NULL, 'k2')")
                cur.execute("INSERT INTO _qa_nulls_probe (a, b) VALUES (NULL, 'k2')")


# --------------------------------------------------------------------------
# the regression for §10.2's own finding
# --------------------------------------------------------------------------


def test_regression_a_boolean_probe_uses_booleans(engine):
    """**REGRESSION for ENGINE-DIVERGENCE §10.2's boolean finding**, asserted
    from QA's side so it cannot quietly revert.

    The defect: a two-column boolean CHECK probe inserted `1`/`0`, which SQLite
    accepted (it was not typing the column) and PostgreSQL rejected **before the
    CHECK was evaluated** (`DatatypeMismatch`). The probe had been passing for a
    reason the document recorded as deliberate.

    This asserts the property the probe is supposed to have: a boolean column
    accepts `true`/`false` on both engines, **and** a CHECK comparing two
    boolean columns is actually reached and actually fires.
    """
    with connection.cursor() as cur:
        cur.execute(
            'CREATE TABLE "_qa_bool_probe" ('
            " id integer primary key,"
            " seller_is_seed boolean not null,"
            " buyer_is_seed boolean not null,"
            " CHECK (seller_is_seed = buyer_is_seed))"
        )
        cur.execute("INSERT INTO _qa_bool_probe VALUES (1, true, true)")
        cur.execute("INSERT INTO _qa_bool_probe VALUES (2, false, false)")

    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute("INSERT INTO _qa_bool_probe VALUES (3, true, false)")

    if engine == "postgresql":
        cause = getattr(exc.value, "__cause__", None)
        sqlstate = getattr(getattr(cause, "diag", None), "sqlstate", None)
        assert sqlstate == "23514", (
            "the mismatched row was refused, but not by the CHECK constraint "
            f"(SQLSTATE {sqlstate!r}). 42804 would mean the probe is testing "
            "type coercion again, which is exactly §10.2's finding"
        )

    with connection.cursor() as cur:
        cur.execute("SELECT count(*) FROM _qa_bool_probe")
        assert cur.fetchone()[0] == 2
