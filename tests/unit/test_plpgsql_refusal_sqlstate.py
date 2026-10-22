"""QA-S0 **F17** — rule 16's SQLSTATE half, in backend's trees.

`CLAUDE.md` rule 16: *"A refused operation is not evidence a guard fired for the
right reason … Exercise every refusal path and **assert the message text, not
the exit status.**"* The repository had the message half —
`test_audit_append_only.py` and `test_gate*.py` assert text — and QA-S0 §5
measured the gap: **the string `P0001` appeared in `tests/unit/**` and
`tests/api/**` exactly once, in a comment.** No test in backend's trees asserted
a SQLSTATE.

**What the SQLSTATE adds that the text does not.** The hazard rule 16 names — an
unresolved identifier in an unexercised plpgsql branch — changes the *text* as
well as the code, so the message assertions already catch it. The narrow case
they do not catch is **a guard that keeps its text and changes its mechanism**:
re-expressed as a CHECK constraint (`23514`), or a `RAISE … USING ERRCODE`, or a
`RAISE … USING MESSAGE` wrapped by something else. `RAISE EXCEPTION 'text'` with
no `USING` clause is `P0001` (`raise_exception`) and nothing else is, so one
assertion per body pins the mechanism.

**Every body, by name**, because a test covering five of six would be reported
as covering the set. S0 had five; S1 adds the sixth:

  1. `audit_log_is_append_only`                 (core/0002)
  2. `gate_authorisations_is_append_only`       (core/0002)
  3. `campuses_gate_is_authorised`              (core/0003)
  4. `bookhop_truncate_guard`                   (core/0003)
  5. `gate_authorisations_evidence_complete`    (core/0005)
  6. `bookhop_append_only_guard`                (accounts/0002) — **new in S1**,
     and deliberately **one** body serving `consents`,
     `age_verification_events` and `notice_versions` via `TG_TABLE_NAME` rather
     than three near-identical ones

**Both halves are asserted together, in one call site each.** Asserting the
SQLSTATE alone would be the mirror of the gap it closes: `P0001` from the wrong
body, or from a body whose message has become a `%`-escaping accident, is still
`P0001`. ENGINE-DIVERGENCE §10.1 records that exact escaping hazard as a live
defect on the first Postgres run.

**On SQLite this file skips with the engine and the slice named** (`CLAUDE.md`
rule 12). SQLite's `RAISE(ABORT, …)` carries no SQLSTATE at all — it surfaces as
`sqlite3.IntegrityError` with a message and nothing else — so there is no weaker
assertion to make here, and a silently-passing guard would be worse than none.
The message half of each of these five refusals **is** asserted on both engines,
in `test_audit_append_only.py`, `test_gate.py` and `test_gate_evidence_*`.
"""

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from apps.core.models import AuditLog, Campus, GateAuthorisation
from apps.core.services import record_audit

pytestmark = pytest.mark.django_db

#: `RAISE EXCEPTION 'text'` with no `USING` clause. Anything else — a CHECK
#: (23514), a NOT NULL (23502), a type mismatch (42804), an undefined column
#: (42703) — is a different mechanism and fails this file.
RAISE_EXCEPTION = "P0001"


def requires_postgres(engine):
    if engine != "postgresql":
        pytest.skip(
            f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S1): a SQLSTATE "
            "is a PostgreSQL concept. SQLite's RAISE(ABORT, ...) surfaces as "
            "sqlite3.IntegrityError with a message and no error code, so rule 16's "
            "SQLSTATE half cannot be asserted here at any strength. The message "
            "half of all five refusals IS asserted on both engines — "
            "test_audit_append_only.py, test_gate.py, test_gate_evidence_typing.py."
        )


def refusal(operation):
    """Run `operation`, expect it to be refused, return (sqlstate, message).

    The savepoint is load-bearing twice over: a raised exception poisons the
    surrounding transaction, and `pytest.raises` outside one would leave the
    test's own connection unusable for the assertions that follow.

    psycopg3 puts the SQLSTATE on the driver exception, which Django wraps, so
    the cause is where it is read from. Asserted as present rather than
    defaulted: `getattr(..., None)` returning None would make every comparison
    below fail open on a driver change, which is the shape of defect this file
    exists to catch.
    """
    with pytest.raises(DatabaseError) as caught:
        with transaction.atomic():
            operation()
    cause = caught.value.__cause__
    sqlstate = getattr(cause, "sqlstate", None)
    assert sqlstate is not None, (
        f"no SQLSTATE on {type(cause).__name__}; this file cannot assert rule 16's "
        f"SQLSTATE half against this driver: {cause!r}"
    )
    return sqlstate, str(caught.value)


# --- 1. audit_log_is_append_only (migration 0002) -------------------------


def test_audit_log_update_is_refused_with_p0001(engine, city):
    requires_postgres(engine)
    row = record_audit(None, "test.one", city)
    sqlstate, message = refusal(
        lambda: AuditLog.objects.filter(id=row.id).update(action="tampered")
    )
    assert sqlstate == RAISE_EXCEPTION, f"audit_log UPDATE refused with {sqlstate}, not a RAISE"
    assert "append-only" in message and "UPDATE" in message, message


def test_audit_log_delete_is_refused_with_p0001(engine, city):
    """The second branch of the same body. **Rule 16's own reason for being:**
    plpgsql resolves identifiers at the first execution of *each branch*, so
    UPDATE passing says nothing about DELETE — and `TG_OP` is interpolated with
    a literal `%`, which ENGINE-DIVERGENCE §10.1 measured breaking on the first
    Postgres run."""
    requires_postgres(engine)
    row = record_audit(None, "test.one", city)
    sqlstate, message = refusal(lambda: AuditLog.objects.filter(id=row.id).delete())
    assert sqlstate == RAISE_EXCEPTION
    assert "append-only" in message and "DELETE" in message, message


# --- 2. gate_authorisations_is_append_only (migration 0002) ---------------


def test_gate_authorisation_delete_is_refused_with_p0001(engine, legal_entity, complete_evidence):
    requires_postgres(engine)
    row = GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=1, legal_entity=legal_entity,
        evidence=complete_evidence, authorised_by_human="A Human",
    )
    sqlstate, message = refusal(lambda: GateAuthorisation.objects.filter(id=row.id).delete())
    assert sqlstate == RAISE_EXCEPTION
    assert "append-only" in message and "DELETE" in message, message


def test_rewriting_a_gate_authorisation_is_refused_with_p0001(
    engine, legal_entity, complete_evidence
):
    """The body's *second* branch — the eight-column comparison. A different
    message and a different code path from the DELETE above."""
    requires_postgres(engine)
    row = GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=1, legal_entity=legal_entity,
        evidence=complete_evidence, authorised_by_human="A Human",
    )
    sqlstate, message = refusal(
        lambda: GateAuthorisation.objects.filter(id=row.id).update(authorised_by_human="Someone Else")
    )
    assert sqlstate == RAISE_EXCEPTION
    assert "no UPDATE except revoked_at" in message, message


# --- 3. campuses_gate_is_authorised (migration 0003) ----------------------


def test_opening_the_gate_without_an_authorisation_is_refused_with_p0001(engine, closed_campus):
    requires_postgres(engine)
    from django.utils import timezone

    sqlstate, message = refusal(
        lambda: Campus.objects.filter(id=closed_campus.id).update(
            discovery_enabled_at=timezone.now()
        )
    )
    assert sqlstate == RAISE_EXCEPTION
    assert "gate_authorisations" in message and "open_discovery" in message, message


def test_inserting_an_open_campus_is_refused_with_p0001(engine, city, legal_entity):
    """The INSERT branch, which is a separate plpgsql branch with its own
    message and its own first execution."""
    requires_postgres(engine)
    from django.utils import timezone

    sqlstate, message = refusal(
        lambda: Campus.objects.create(
            city=city, name="Born Open", slug="born-open", legal_entity=legal_entity,
            discovery_enabled_at=timezone.now(),
        )
    )
    assert sqlstate == RAISE_EXCEPTION
    assert "a new campus is created closed" in message, message


# --- 4. bookhop_truncate_guard (migration 0003) ---------------------------


def test_truncate_is_refused_with_p0001_when_the_escape_is_not_declared(engine, city):
    """The one body whose happy path is a test-harness escape, so its refusal
    path is the one least likely to be exercised by accident.

    `tests/conftest.py` declares `bookhop.allow_flush = 'yes'` on **every**
    connection, which is correct and is why this test has to un-declare it for
    the duration. It is restored in a `finally`: leaving it off would break
    every later `transactional_db` teardown in the session, which is the exact
    failure QA-S0 F9 and ENGINE-DIVERGENCE §7.1 exist to prevent.
    """
    requires_postgres(engine)
    record_audit(None, "test.one", city)

    def truncate():
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE audit_log")

    with connection.cursor() as cursor:
        cursor.execute("SET bookhop.allow_flush = 'no'")
    try:
        sqlstate, message = refusal(truncate)
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SET bookhop.allow_flush = 'yes'")

    assert sqlstate == RAISE_EXCEPTION, f"TRUNCATE refused with {sqlstate}, not a RAISE"
    assert "TRUNCATE is not permitted" in message, message
    # TG_TABLE_NAME reaches the message through a literal `%`, which is the
    # escaping hazard ENGINE-DIVERGENCE §10.1 found live. If the `%` were eaten
    # the sentence would still contain the text above, so the table name is
    # asserted separately.
    assert "audit_log" in message, f"TG_TABLE_NAME did not interpolate: {message}"


# --- 5. gate_authorisations_evidence_complete (migration 0005) ------------


def test_an_incomplete_gate_c_authorisation_is_refused_with_p0001(engine, legal_entity):
    requires_postgres(engine)
    sqlstate, message = refusal(
        lambda: GateAuthorisation.objects.create(
            gate="C", scope_type="CAMPUS", scope_id=1, legal_entity=legal_entity,
            evidence={}, authorised_by_human="A Human",
        )
    )
    assert sqlstate == RAISE_EXCEPTION
    assert "every evidence item" in message, message
    # The FOREACH loop interpolates the missing key through a literal `%`.
    assert "counsel_engagement_ref" in message, f"the key did not interpolate: {message}"


def test_an_unnamed_authoriser_is_refused_with_p0001(engine, legal_entity, complete_evidence):
    """The body's first branch, which is a different `RAISE` with a different
    message — and the one that carries the whole "a named human signed this"
    rule."""
    requires_postgres(engine)
    sqlstate, message = refusal(
        lambda: GateAuthorisation.objects.create(
            gate="C", scope_type="CAMPUS", scope_id=1, legal_entity=legal_entity,
            evidence=complete_evidence, authorised_by_human="​",  # zero-width space
        )
    )
    assert sqlstate == RAISE_EXCEPTION
    assert "named human" in message, message


# --- 6. bookhop_append_only_guard (accounts/0002) -------------------------


@pytest.mark.parametrize("table", ["consents", "age_verification_events", "notice_versions"])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_the_s1_append_only_tables_refuse_with_p0001(engine, table, operation, student, privacy_notice):
    """Six refusal paths through one body — three tables × two operations.

    **`CLAUDE.md` rule 16 is the reason this is parametrised rather than
    sampled:** plpgsql resolves identifiers at the first execution of *each
    branch*, and `TG_TABLE_NAME`/`TG_OP` reach the message through a literal
    `%` that ENGINE-DIVERGENCE §10.1 measured breaking on the first Postgres
    run. A single `consents` DELETE passing says nothing about a
    `notice_versions` UPDATE.
    """
    requires_postgres(engine)
    from apps.accounts.models import AgeVerificationEvent, Consent, NoticeVersion

    # (model, a column the trigger is not keyed on, so the refusal is the
    # trigger's and not a constraint's)
    subjects = {
        "consents": (Consent, "created_at"),
        "age_verification_events": (AgeVerificationEvent, "occurred_at"),
        "notice_versions": (NoticeVersion, "published_at"),
    }
    model, column = subjects[table]
    if model is AgeVerificationEvent:
        model.objects.create(
            user_pseudonym=student.person_pseudonym, outcome="ADULT_CONFIRMED",
            method="SELF_DECLARED_DOB_SERVER_CHECKED",
        )
    if model is NoticeVersion:
        # A fresh, unreferenced version: `privacy_notice` is the target of a
        # `consents` FK declared PROTECT, so deleting it raises Django's
        # `ProtectedError` **before** a statement reaches the server — the test
        # would then measure the ORM rather than the trigger.
        model.objects.create(
            kind="TERMS", version="9999-01-01.1", locale="en",
            body_md="unreferenced", sha256="9" * 64,
        )
        row = model.objects.get(version="9999-01-01.1")
    else:
        row = model.objects.first()
    assert row is not None, f"no {table} row to attack — this test would pass vacuously"

    if operation == "DELETE":
        sqlstate, message = refusal(lambda: model.objects.filter(pk=row.pk).delete())
    else:
        sqlstate, message = refusal(
            lambda: model.objects.filter(pk=row.pk).update(**{column: timezone.now()})
        )

    assert sqlstate == RAISE_EXCEPTION, f"{table} {operation} refused with {sqlstate}, not a RAISE"
    assert "append-only" in message, message
    assert table in message, f"TG_TABLE_NAME did not interpolate for {table}: {message}"
    assert operation in message, f"TG_OP did not interpolate for {operation}: {message}"


# --- the file's own guard -------------------------------------------------


def test_every_plpgsql_body_in_the_migrations_has_a_sqlstate_assertion_here(engine):
    """`CLAUDE.md` rule 9 turned on this file: the set of bodies is read out of
    the migrations rather than retyped, so a sixth body cannot arrive without
    this test naming it.

    Runs on **both** engines — it reads migration source, not a server — so a
    new unasserted body fails the build on SQLite too, where every assertion
    above skips. That is the half of F17 that must not depend on the engine: the
    engine decides whether a SQLSTATE can be *measured*, not whether a body is
    allowed to arrive unmeasured.
    """
    import pathlib
    import re

    apps_dir = pathlib.Path(__file__).resolve().parents[2] / "apps"
    bodies = set()
    for path in sorted(apps_dir.glob("*/migrations/0*.py")):
        text = path.read_text(encoding="utf-8")
        bodies |= set(re.findall(r"CREATE OR REPLACE FUNCTION (\w+)\(\)", text))
    assert bodies, "no plpgsql bodies found in apps/*/migrations — this test would pass vacuously"

    asserted = pathlib.Path(__file__).read_text(encoding="utf-8")
    missing = sorted(body for body in bodies if body not in asserted)
    assert missing == [], (
        "QA-S0 F17 / CLAUDE.md rule 16: these plpgsql bodies have no SQLSTATE "
        "assertion in this file, so a guard that kept its text and changed its "
        "mechanism would pass the build:\n" + "\n".join(missing)
    )
    assert len(bodies) == 6, (
        f"the migrations now define {len(bodies)} plpgsql bodies, not the six S1 "
        "ships. Add the refusal assertions, then update that count in the same "
        "commit — the count is here so a new body cannot arrive unmeasured."
    )
