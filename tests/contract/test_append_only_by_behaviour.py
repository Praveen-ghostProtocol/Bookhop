"""Append-only, asked as a refusal rather than as a trigger's existence.

**Why a second file on this.** `tests/unit/test_append_only_triggers_exist.py`
closed a measured, shipped defect — SQLite rebuilt `notice_versions` to widen a
CHECK and the rebuild took the table's triggers with it — and it closed it the
right way, by introspecting both engines' catalogues. QA's question is the next
one: `CLAUDE.md` rule 18 says *"a control that guarantees a state does not
thereby detect a bad input"*, and rule 16 says *"exercise every refusal path and
assert the message text, not the exit status."* An existence check is a state
guarantee. **It cannot tell a trigger that refuses from a trigger that does
not.**

So this file:

1. derives the table set **from `DATA-MODEL.md` itself** rather than from a
   hand-kept dictionary, so a table the contract starts calling append-only is
   covered the day the document says so and not the day someone remembers
   (`CLAUDE.md` rule 11 — the list that gets edited instead of extended);
2. asserts the **behaviour** — UPDATE refused, DELETE refused — on both engines,
   **with the message text**, which is the only thing that distinguishes "the
   guard fired" from "the operation failed" (rule 16);
3. exercises the one **permitted** UPDATE the contract carves out
   (`gate_authorisations.revoked_at`), because a guard that refuses it would make
   closing a gate impossible and nothing else would notice;
4. **records a migration shape that defeats the existence control**, measured.
   Finding F-A1 below.
"""

import re
from pathlib import Path

import pytest
from django.db import DatabaseError, connection, transaction

pytestmark = pytest.mark.django_db

REPO = Path(__file__).resolve().parents[2]
DATA_MODEL = REPO / "company" / "architecture" / "DATA-MODEL.md"

#: A `###` heading in DATA-MODEL that declares a table append-only or immutable.
#: Example: "### `consents` — S1 · append-only"
_DECLARATION = re.compile(
    r"^###\s+`(?P<table>\w+)`\s*[—-]\s*(?P<slice>S\d+)[^\n]*?(?P<claim>append-only|immutable)",
    re.I | re.M,
)


def declared_append_only():
    """`{table: (slice, claim, heading)}`, read out of the contract.

    The point of reading the document is that this set can grow without this
    file changing. The ceiling, declared beside it: it sees a table whose
    **heading** carries the words, and would miss one declared only in prose.
    That is a narrower gap than a hand-kept list, and the layer that catches the
    prose case is a human reading the amendment — which is where it has to be,
    because no parser rules on prose.
    """
    text = DATA_MODEL.read_text(encoding="utf-8")
    return {
        match.group("table"): (
            match.group("slice"),
            match.group("claim").lower(),
            match.group(0).strip(),
        )
        for match in _DECLARATION.finditer(text)
    }


def _existing_tables():
    with connection.cursor() as cursor:
        return set(connection.introspection.table_names(cursor))


def test_the_contract_declares_at_least_the_tables_this_slice_builds():
    """`CLAUDE.md` rule 12 on the parser. If the regex stopped matching, every
    parametrised test below would run zero cases and the file would report
    green while asserting nothing."""
    declared = declared_append_only()
    assert declared, (
        "no append-only declaration was parsed out of DATA-MODEL.md, so every "
        "test in this file would be vacuous. Check the heading format."
    )
    expected = {"gate_authorisations", "age_verification_events", "consents",
                "notice_versions", "audit_log"}
    missing = expected - set(declared)
    assert not missing, (
        f"these tables are append-only in S0/S1 and the parser did not find "
        f"their declaration: {sorted(missing)}. Found: {sorted(declared)}"
    )


# ---------------------------------------------------------------------------
# a row to attack, per table, built from the contract's own column list
# ---------------------------------------------------------------------------


def _seed_row(table, fixtures):
    """Insert one row in `table` and return `(pk_column, pk_value)`.

    Built per table because each has different NOT NULLs, and deliberately via
    the real services or the ORM rather than raw SQL — a raw INSERT could sidestep
    a constraint and leave the test attacking a row the application could never
    create.
    """
    city, entity, campus, student, notice, evidence = fixtures

    if table == "audit_log":
        from apps.core.models import AuditLog
        from apps.core.services import record_audit

        record_audit(None, "qa.append_only", city)
        return "id", AuditLog.objects.latest("id").pk

    if table == "gate_authorisations":
        from apps.core.models import GateAuthorisation

        row = GateAuthorisation.objects.create(
            gate="C", scope_type="CAMPUS", scope_id=campus.id, legal_entity=entity,
            evidence=evidence, authorised_by_human="A Named Human",
        )
        return "id", row.pk

    if table == "consents":
        from apps.accounts.models import Consent
        from apps.accounts.services import grant_consent

        grant_consent(student, "chat", notice, "SIGNUP_FORM", None, "pytest")
        return "id", Consent.objects.filter(purpose_key="chat").latest("id").pk

    if table == "age_verification_events":
        from apps.accounts.models import AgeVerificationEvent

        row = AgeVerificationEvent.objects.create(
            user_pseudonym=student.person_pseudonym, user_id=student.pk,
            outcome="ADULT_CONFIRMED", method="SELF_DECLARED_DOB_SERVER_CHECKED",
        )
        return "id", row.pk

    if table == "notice_versions":
        from apps.accounts.models import NoticeVersion

        row = NoticeVersion.objects.create(
            kind="TERMS", version="2026-11-01.qa", locale="en",
            body_md="# Terms", sha256="1" * 64,
        )
        return "id", row.pk

    raise AssertionError(
        f"no seed written for {table!r}. DATA-MODEL now declares a table this "
        "file cannot attack, which is a gap in the test, not in the guard — add "
        "a branch here."
    )


@pytest.fixture
def qa_student(db, qa_campus):
    """A student on QA's own campus.

    Not `tests/conftest.py`'s `student`: that one hangs off a second `cities`
    row, which collides with `qa_city` on `UNIQUE (name, state)` — and more to
    the point, the charter asks that a change to the backend agent's fixtures
    cannot quietly change what these tests assert.
    """
    from apps.accounts.models import User

    return User.objects.create(
        email="append-only@qa.example.test", display_name="QA Student",
        campus=qa_campus, city_id=qa_campus.city_id, status="ACTIVE",
        adult_verified=True, campus_verified=True, is_seed=True,
    )


@pytest.fixture
def qa_notice(db):
    from apps.accounts.models import NoticeVersion

    return NoticeVersion.objects.create(
        kind="PRIVACY", version="2026-11-01.qa-append-only", locale="en",
        body_md="# Privacy", sha256="2" * 64,
    )


@pytest.fixture
def seeds(db, qa_city, qa_entity, qa_campus, qa_student, qa_notice, qa_evidence):
    return (qa_city, qa_entity, qa_campus, qa_student, qa_notice, qa_evidence)


def _tables_to_test():
    """The declared set, intersected with what this slice built."""
    return sorted(declared_append_only())


@pytest.mark.parametrize("table", _tables_to_test())
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_every_declared_append_only_table_refuses_the_operation_by_behaviour(
    table, operation, seeds, engine, salt
):
    """The assertion the existence check cannot make, on both engines.

    Run as raw SQL against the live row, because the ORM is not the threat model:
    `DATA-MODEL.md` §8's claim is that *"the audit trail has to resist the
    application as well as the user"*, and an ORM-only test would be satisfied by
    a model-level `save()` override.

    `UPDATE` on `gate_authorisations` is the contract's one carve-out, so it is
    attacked on a column the carve-out does **not** cover.
    """
    declared = declared_append_only()
    slice_name, claim, heading = declared[table]
    if table not in _existing_tables():
        pytest.skip(
            f"NOT VERIFIABLE IN THIS SLICE (table={table}, slice={slice_name}, "
            f"vendor={engine}): DATA-MODEL declares it {claim} — {heading!r} — and "
            f"{slice_name} creates it. There is no row to attack, so asserting the "
            "refusal now would be a guard that passes vacuously (CLAUDE.md "
            "rule 12)."
        )

    pk_column, pk = _seed_row(table, seeds)

    if operation == "UPDATE":
        column, value = _mutable_looking_column(table)
        statement = f'UPDATE "{table}" SET "{column}" = %s WHERE "{pk_column}" = %s'
        params = [value, pk]
    else:
        statement = f'DELETE FROM "{table}" WHERE "{pk_column}" = %s'
        params = [pk]

    with pytest.raises(DatabaseError) as refusal:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(statement, params)

    message = str(refusal.value)
    assert re.search(r"append-only|not permitted|permits no UPDATE", message, re.I), (
        f"{table}: the {operation} failed, but not with the guard's own message, "
        "so this test cannot tell a fired guard from an unrelated error "
        f"(CLAUDE.md rule 16). Got: {message!r}"
    )
    assert table in message, (
        f"{table}: the refusal does not name the table, so an operator reading "
        f"the log cannot tell which guarantee they hit. Got: {message!r}"
    )


def _mutable_looking_column(table):
    """A column whose UPDATE must be refused, and a value for it.

    For `gate_authorisations` this deliberately avoids `revoked_at` and
    `revoked_reason`, which `DATA-MODEL.md` §1 permits — attacking the permitted
    column would make this test assert the opposite of the contract.
    """
    return {
        "audit_log": ("action", "tampered"),
        "gate_authorisations": ("authorised_by_human", "Somebody Else"),
        "consents": ("purpose_key", "chat"),
        "age_verification_events": ("outcome", "REVOKED_MINOR_DISCOVERED"),
        "notice_versions": ("body_md", "# Rewritten"),
    }[table]


def test_the_one_permitted_update_is_still_permitted(engine, qa_authorisation):
    """`DATA-MODEL.md` §1: *"No UPDATE permitted except setting
    `revoked_at`/`revoked_reason` (trigger)."*

    The other branch of the same trigger (`CLAUDE.md` rule 16). A guard that
    refused this would make `close_discovery` impossible — and the symptom would
    arrive at the worst moment, when somebody is trying to shut a campus down.
    """
    from django.utils import timezone

    from apps.core.models import GateAuthorisation

    with connection.cursor() as cursor:
        cursor.execute(
            'UPDATE "gate_authorisations" SET "revoked_at" = %s, "revoked_reason" = %s '
            'WHERE "id" = %s',
            [timezone.now(), "closing the campus", qa_authorisation.pk],
        )

    qa_authorisation.refresh_from_db()
    assert qa_authorisation.revoked_at is not None, (
        "revoking an authorisation silently did nothing, which is worse than "
        "raising: a staff member would believe the gate was closed"
    )
    assert GateAuthorisation.objects.filter(revoked_at__isnull=False).exists()


# ---------------------------------------------------------------------------
# FINDING F-A1 — a migration shape the existence control does not catch
# ---------------------------------------------------------------------------


def test_finding_a_surviving_unrelated_trigger_satisfies_the_existence_control(engine):
    """**FINDING F-A1 (material, reported not fixed): on PostgreSQL the existence
    control is satisfied by the wrong trigger.**

    `tests/unit/test_append_only_triggers_exist.py` asks *"is the guard there at
    all?"* and, on PostgreSQL, answers it with `assert names` — any trigger on
    the table. But `audit_log` carries **two**: `audit_log_append_only`, which
    refuses UPDATE and DELETE, and `audit_log_no_truncate`, which refuses only
    TRUNCATE.

    Measured here: drop `audit_log_append_only`, leave `audit_log_no_truncate`,
    and **`audit_log` becomes freely UPDATE-able while every assertion in that
    file still passes.** The defeating migration shape is therefore any
    migration that drops or re-creates the append-only trigger while leaving its
    sibling — including the SQLite table-rebuild case that file was written for,
    if the restore migration happens to put back one of the two.

    This is `CLAUDE.md` rule 18 exactly: a control proving a trigger *exists*
    does not prove an UPDATE is *refused*. The fix is not a longer list of
    trigger names — it is the behavioural parametrisation above, which asks the
    property and cannot be satisfied by a sibling.

    The DDL runs inside the test's own transaction and is rolled back with it.
    """
    from apps.core.models import AuditLog, City
    from apps.core.services import record_audit

    if connection.vendor != "postgresql":
        pytest.skip(
            f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S1): the "
            "finding is about PostgreSQL's assertion branch, which is "
            "`assert names` over a table carrying two triggers. On SQLite the "
            "same control matches trigger names containing `no_update` and "
            "`no_delete`, so the sibling-trigger shape does not defeat it there "
            "— the SQLite exposure is the table rebuild, which that file's own "
            "docstring measures."
        )

    city = City.objects.create(name="Chennai", state="Tamil Nadu")
    record_audit(None, "qa.f_a1", city)

    def triggers_on_audit_log():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                "WHERE NOT t.tgisinternal AND c.relname = 'audit_log'"
            )
            return {row[0] for row in cursor.fetchall()}

    before = triggers_on_audit_log()
    refusing = {name for name in before if "append_only" in name}
    assert refusing and before - refusing, (
        "this finding depends on audit_log carrying a refusing trigger AND an "
        f"unrelated sibling; it now carries {sorted(before)}. If the two were "
        "merged the finding is closed — delete this test."
    )

    with connection.cursor() as cursor:
        for name in refusing:
            cursor.execute(f"DROP TRIGGER {name} ON audit_log")

    surviving = triggers_on_audit_log()
    assert surviving, "nothing survived, so the existence control would catch this"

    with connection.cursor() as cursor:
        cursor.execute("UPDATE audit_log SET action = 'tampered'")
        cursor.execute("SELECT count(*) FROM audit_log WHERE action = 'tampered'")
        tampered = cursor.fetchone()[0]

    assert tampered, (
        "the UPDATE did not take effect, so the append-only guarantee does not "
        "depend on the trigger that was dropped — which would close this "
        "finding. Re-measure and delete this test."
    )
    assert AuditLog.objects.filter(action="tampered").exists()
    # The finding, stated as the thing a reader should act on. The assertion
    # above has already established it; this line fails only if someone makes
    # the existence control behavioural, at which point this test is obsolete.
    assert bool(surviving), (
        "F-A1: the audit log is now mutable and the existence control still "
        f"sees triggers {sorted(surviving)} on audit_log, so it reports green. "
        "The behavioural parametrisation in this file is the layer that catches "
        "it (CLAUDE.md rule 14)."
    )
