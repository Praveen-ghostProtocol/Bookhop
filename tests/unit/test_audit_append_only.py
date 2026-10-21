"""The audit trail is append-only and tamper-evident — DATA-MODEL §8.

These assertions are about the database, not the service layer: an UPDATE or
DELETE issued by the ORM, by a management command, or by a staff member in a
Django shell must fail. The enforcement is the trigger in migration
core/0002, written for both engines, so this test means the same thing on
SQLite locally and on Postgres in production.

Note for whoever adds tests here: use `django_db` (transaction rollback), never
`transactional_db`. A TransactionTestCase flushes with DELETE, which the
append-only trigger correctly refuses.
"""

import pytest
from django.db import DatabaseError, transaction

from apps.core.errors import AuditChainBroken
from apps.core.models import AuditLog, City
from apps.core.services import GENESIS_HASH, record_audit, verify_audit_chain

pytestmark = pytest.mark.django_db


def test_record_audit_writes_a_row_and_chains_it(city):
    first = record_audit(None, "test.one", city, after={"a": 1})
    second = record_audit(None, "test.two", city, before={"a": 1}, after={"a": 2})
    assert first.prev_hash == GENESIS_HASH
    assert second.prev_hash == first.row_hash
    assert len(first.row_hash) == 64


def test_record_audit_stores_hashes_of_the_payload_not_the_payload(city):
    row = record_audit(None, "test.one", city, after={"email": "student@example.test"})
    assert "student@example.test" not in (row.after_hash or "")
    assert len(row.after_hash) == 64


def test_verify_audit_chain_passes_on_a_clean_chain(city):
    for i in range(5):
        record_audit(None, f"test.{i}", city, after={"i": i})
    checked, head = verify_audit_chain()
    assert checked == 5
    assert head == AuditLog.objects.order_by("-id").first().row_hash


def test_audit_row_cannot_be_updated(city, engine):
    row = record_audit(None, "test.one", city)
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            AuditLog.objects.filter(id=row.id).update(action="test.tampered")
    row.refresh_from_db()
    assert row.action == "test.one", f"audit_log was mutable on {engine}"


def test_audit_row_cannot_be_deleted(city, engine):
    row = record_audit(None, "test.one", city)
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            AuditLog.objects.filter(id=row.id).delete()
    assert AuditLog.objects.filter(id=row.id).exists(), f"audit_log was deletable on {engine}"


def test_the_whole_audit_table_cannot_be_emptied_by_a_bulk_delete(city, engine):
    """N9: renamed. The old name said "truncated", implying TRUNCATE coverage
    this assertion does not have and that SQLite cannot have — it has no
    TRUNCATE statement (measured: a syntax error). The Postgres TRUNCATE guard
    is migration 0003's, and QA's `test_truncate_cannot_empty_the_audit_log`
    skips with the engine named."""
    record_audit(None, "test.one", city)
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            AuditLog.objects.all().delete()
    assert AuditLog.objects.count() == 1


def test_a_non_prev_hash_integrity_error_is_not_reported_as_a_broken_chain(city):
    """S11. The retry loop caught `IntegrityError` generically, which is right
    for the `prev_hash` race it exists for and wrong for every other integrity
    failure on the same insert: a CHECK violation on `actor_type` was retried
    four times and surfaced as "could not append to the audit chain", throwing
    away the real cause in the one code path where a misleading diagnostic is
    most expensive."""
    row = AuditLog(
        actor_type="NOT_A_VALID_ACTOR_TYPE",  # violates audit_actor_type_chk
        action="test.bad", object_type="City", object_id="1",
        prev_hash="x" * 64, row_hash="y",
    )
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            row.save()
    assert "chain" not in str(exc.value).lower()


def test_a_tampered_chain_is_detected():
    """The trigger is the primary control; the hash chain is the evidence.

    Drop the guard, tamper, and verify. Nothing is restored: pytest-django
    rolls the whole test back, including the DDL (`can_rollback_ddl` is True on
    both engines), which is what returns the trigger. N9 — the previous
    docstring said "restore" and the code never did.
    """
    from django.db import connection

    city = City.objects.create(name="X", state="Y")
    record_audit(None, "test.one", city, after={"a": 1})
    second = record_audit(None, "test.two", city, after={"a": 2})

    with connection.cursor() as cursor:
        # Drop the guard, tamper, verify, restore. Scoped to this test's
        # transaction, which pytest-django rolls back.
        if connection.vendor == "sqlite":
            cursor.execute("DROP TRIGGER audit_log_no_update")
        else:
            cursor.execute("ALTER TABLE audit_log DISABLE TRIGGER audit_log_append_only")
        cursor.execute("UPDATE audit_log SET action = 'test.tampered' WHERE id = %s", [second.id])

    with pytest.raises(AuditChainBroken, match=str(second.id)):
        verify_audit_chain()


def test_audit_write_is_rolled_back_with_its_transaction(city):
    """One transaction per mutation, with the audit row inside it.

    A rolled-back mutation must not leave an audit row claiming it happened.
    """
    before = AuditLog.objects.count()
    with pytest.raises(RuntimeError):
        with transaction.atomic():
            record_audit(None, "test.doomed", city)
            raise RuntimeError("boom")
    assert AuditLog.objects.count() == before


def test_prev_hash_is_unique_so_the_chain_cannot_fork(city):
    row = record_audit(None, "test.one", city)
    duplicate = AuditLog(
        actor_type="SYSTEM", action="test.fork", object_type="City", object_id="1",
        prev_hash=row.prev_hash, row_hash="deadbeef",
    )
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            duplicate.save()


# --------------------------------------------------------------------------
# The refusal MESSAGE, not just the refusal. POSTGRES-FIRST-RUN.md §1-§2.
#
# `check_function_bodies` validates plpgsql syntax at CREATE FUNCTION; plpgsql
# resolves identifiers and operators at the first execution of each branch. So
# a guard can be created cleanly, pass every happy-path test, and fail the
# first time anyone does the forbidden thing -- and the worst shape of that
# failure (`relation does not exist`, `record "new" is not assigned yet`) still
# BLOCKS the operation, so it reads as the guard working while proving nothing
# about the rule. The tests above assert that a DatabaseError was raised. These
# assert it was raised *for the stated reason*.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_the_append_only_message_names_the_operation_it_refused(city, engine, operation):
    """The message a developer actually reads must name the operation.

    **This is the regression guard for a two-layer escaping bug.** Migration
    0002's Postgres body is `RAISE EXCEPTION '... % is not permitted', TG_OP`,
    and psycopg parses that `%` as a parameter placeholder before Postgres ever
    sees it: the first `migrate` from empty on a real server died with
    `incomplete placeholder: '%'`. The fix passes `params=None` so the SQL
    reaches the server unparsed.

    The other available fix -- doubling the `%` -- also makes `migrate` pass,
    and **getting it wrong is silent**: a mis-doubled format string produces a
    literal `%` or `%%` in the message while the guard still refuses the
    operation, so the refusal looks identical and only the text is broken.
    `CLAUDE.md` rule 9 is the reason this is a test and not a comment: the
    claim and the check are one artefact. Asserting the interpolated value is
    present is what makes the next person's debugging session possible.

    Engine-neutral by construction: SQLite's trigger bodies hardcode the
    operation in four separate literals, Postgres interpolates `TG_OP` once.
    Both must produce it, so one assertion covers both -- and a mismatch
    between the engines is itself what this would catch.
    """
    row = record_audit(None, "test.one", city)
    with pytest.raises(DatabaseError) as caught:
        with transaction.atomic():
            if operation == "UPDATE":
                AuditLog.objects.filter(id=row.id).update(action="test.tampered")
            else:
                AuditLog.objects.filter(id=row.id).delete()

    message = str(caught.value)
    assert "append-only" in message, f"refused on {engine}, but not by the guard: {message!r}"
    assert operation in message, (
        f"the guard refused the {operation} on {engine} but its message does not "
        f"name it, so the interpolation is broken even though the refusal works: "
        f"{message!r}"
    )
    assert "%" not in message, (
        f"an un-interpolated or double-escaped format specifier reached the "
        f"message on {engine}: {message!r}"
    )


# **The TRUNCATE REFUSAL is deliberately not asserted here, and that is a
# finding rather than a gap.** Unsetting the escape is the only way to test the
# refusal, and naming it is the only way to unset it -- but
# `tests/contract/test_migration_guards.py` keeps a flat inventory of every file
# that names it, allowing exactly two plus QA's own tree by path. So this
# assertion can only live in QA's tree, where
# `tests/e2e/test_audit_tamper.py::test_truncate_cannot_empty_the_audit_log`
# already reserves the name and currently skips. `CLAUDE.md` rule 13's order of
# resort put it there: renaming ours was free, widening QA's allowlist was not,
# and turning a red guard into an edit of a protected inventory under schedule
# pressure is the failure mode the rule exists for.
#
# Verified by direct execution on PostgreSQL 16.15 instead, with the message
# text asserted (POSTGRES-FIRST-RUN §1-§2, §7): `TRUNCATE audit_log` with the
# escape unset raises SQLSTATE P0001 `audit_log is append-only: TRUNCATE is not
# permitted`, `TRUNCATE gate_authorisations` names its own table, and both still
# refuse under `session_replication_role = 'replica'`. The inverse -- that the
# escape is an escape and not dead code -- is the test below, which needs no
# name because the harness has already declared it.


def test_the_declared_flush_escape_really_is_an_escape(city):
    """The inverse of the test above, so the guard is not dead code.

    ENGINE-DIVERGENCE §7.1 rests a real thing on this: with the escape
    declared, Django's own `sql_flush` must be able to empty the table, or
    every `transactional_db` teardown on Postgres fails and the tempting fix is
    deleting the guard. Asserting only the refusal would leave "the escape
    works" as reasoning; this makes it a measurement.
    """
    from django.db import connection

    if connection.vendor != "postgresql":
        pytest.skip(
            f"NOT VERIFIABLE ON THIS ENGINE (vendor={connection.vendor}, slice=S0): "
            "there is no TRUNCATE statement and no `current_setting` on SQLite, "
            "so neither the guard nor its escape exists here "
            "(ENGINE-DIVERGENCE §3.6, §7.1)."
        )

    record_audit(None, "test.one", city)
    # Declared for every connection by tests/conftest.py::allow_test_flush.
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE audit_log")
    assert AuditLog.objects.count() == 0, (
        "the escape did not take effect, so the TRUNCATE guard has no way out "
        "and transactional teardown on Postgres is impossible"
    )
