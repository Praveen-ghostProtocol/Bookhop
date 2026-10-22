"""The gate and the audit log as a **privilege**, not only as a trigger.

RED TEAM ENGINEERING-MEMO §1 (CRITICAL) and §3 (MATERIAL). Both findings have
one root cause — the application role holds the privileges the control is
supposed to withhold — and `CLAUDE.md` rule 14 is the rule they break: *"an
exemption in one layer is affordable only when another layer independently
rejects the same thing."* The gate had one layer twice.

This file is in three parts, and the split is the point:

  1. **The control exists** (`CLAUDE.md` rule 9) — migration `core/0008`
     revokes the right privileges on the right tables. Engine-neutral: it reads
     the migration.
  2. **The live grant state**, measured on PostgreSQL. Reported rather than
     asserted green, because the test harness deliberately re-grants (see
     `conftest.restore_gate_privileges_for_the_harness`) and a test asserting
     the revoke here would be asserting the harness, not production.
  3. **The attack the memo measured**, as `xfail(strict=True)`. It is **not
     skipped**: a skip claims the property cannot be tested, and it can — it is
     simply still broken. `strict=True` means the day the exposure closes, this
     file goes red and has to be de-xfailed, which is how a tracked critical
     stops being tracked.
"""

import pathlib

import pytest
from django.db import connection
from django.utils import timezone

from apps.core.models import AuditLog, Campus, GateAuthorisation

pytestmark = pytest.mark.django_db

MIGRATION = (
    pathlib.Path(__file__).resolve().parents[2]
    / "apps" / "core" / "migrations" / "0008_least_privilege.py"
)


def _migration():
    """The migration module, imported by its filename.

    A numeric-leading module name is not a valid identifier, so it cannot be a
    plain `import` — `import_module` is the one way to read the constants
    instead of retyping them (`CLAUDE.md` rule 10).
    """
    import importlib

    return importlib.import_module("apps.core.migrations." + MIGRATION.stem)


# --- 1. the control exists (both engines) ---------------------------------


def test_the_privilege_migration_revokes_the_memos_two_sets():
    """The memo's own prescription, as a conformance check on the repository:

        REVOKE INSERT, UPDATE, TRUNCATE ON gate_authorisations FROM bookhop;
        REVOKE TRUNCATE ON audit_log FROM bookhop;
    """
    assert MIGRATION.exists(), "RED TEAM §1's ranked-first fix is not in the repository"
    revocations = dict(_migration().REVOCATIONS)
    assert set(revocations) == {"gate_authorisations", "audit_log"}
    assert set(revocations["gate_authorisations"].replace(",", " ").split()) == {
        "INSERT", "UPDATE", "TRUNCATE"
    }
    assert revocations["audit_log"].strip() == "TRUNCATE"


def test_the_migration_keeps_insert_on_audit_log():
    """`record_audit` runs as the application role on **every** mutation, so
    revoking INSERT on `audit_log` would stop the application working — and an
    audit trail nothing can append to is worse than an un-revoked privilege."""
    assert "INSERT" not in dict(_migration().REVOCATIONS)["audit_log"]


def test_the_migration_states_its_ceiling_rather_than_claiming_the_fix_is_complete():
    """**The finding this file adds to the memo, measured below.** The memo's
    one-migration fix is necessary and is not sufficient: the application role
    *owns* both tables, and an owner can grant itself back what it was revoked.
    The migration has to say so, or the next reader reads a revoke as a wall.
    """
    text = MIGRATION.read_text(encoding="utf-8")
    assert "OWNS both tables" in text
    assert "straight back to itself in one statement" in text
    assert "ownership" in text.lower()


# --- 2. the live grant state, measured ------------------------------------


def test_measured_the_application_role_owns_the_tables_it_is_revoked_on(engine):
    """**VERIFIED HERE on PostgreSQL 16.15** (`CLAUDE.md` rule 17).

    This is the measurement that makes `core/0008` a partial fix rather than a
    complete one, and it is a *measurement* because reasoning about whether
    PostgreSQL binds a table's owner to its own ACL is exactly the kind of
    platform claim this project has been wrong about three times.

    What was measured, in order: `REVOKE TRUNCATE ON audit_log FROM bookhop`
    **does** bind the owner — `has_table_privilege` returns false and the
    TRUNCATE is refused with *"permission denied for table audit_log"* — and
    then `GRANT TRUNCATE ON audit_log TO bookhop` restores it in one statement.
    So the revoke stops accidents and does not stop an actor holding that role.
    """
    if engine != "postgresql":
        pytest.skip(
            f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S1): SQLite has "
            "no role system — no GRANT, no REVOKE, one process with full access to "
            "the file. There is no weaker form of a privilege control to assert "
            "here, so the layer is absent on this engine rather than approximated. "
            "ENGINE-DIVERGENCE §12."
        )
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        role = cursor.fetchone()[0]
        cursor.execute(
            "SELECT tableowner FROM pg_tables WHERE tablename IN "
            "('audit_log', 'gate_authorisations')"
        )
        owners = {row[0] for row in cursor.fetchall()}

    assert owners, "neither table was found — this test would pass vacuously"
    assert owners == {role}, (
        "ownership has moved off the application role, which is the deployment "
        "step RED TEAM §1 needs. Re-read this file: the xfails below should now "
        "be passing, and `conftest.restore_gate_privileges_for_the_harness` "
        f"can no longer re-grant. owners={owners} role={role}"
    )


# --- 3. the attack, tracked rather than hidden ----------------------------

LIVE_CRITICAL = (
    "RED TEAM ENGINEERING-MEMO §1, CRITICAL, STILL OPEN. This is NOT a "
    "limitation of the test — the attack genuinely succeeds. It closes when "
    "ownership of `gate_authorisations` and `campuses` moves off the "
    "application role (a superuser deployment step; this box has rolsuper=false) "
    "and the harness can no longer re-grant. strict=True, so this file goes red "
    "the day it is fixed and must be de-xfailed then."
)


@pytest.mark.xfail(strict=True, reason=LIVE_CRITICAL)
def test_three_orm_statements_cannot_open_the_discovery_gate(city, legal_entity):
    """The memo's measured attack, reproduced exactly.

    An empty legal entity, an authorisation whose evidence values are all the
    literal string `"x"` — on ADR-002 §4.1(b)'s own placeholder deny-list — and
    granted against a **different** legal entity, then a plain queryset
    `update()`. **Fail = the gate opens, or the audit row count is zero.**
    """
    from apps.core.models import LegalEntity

    other_entity = LegalEntity.objects.create()
    campus = Campus.objects.create(
        city=city, name="Attack Campus", slug="attack", legal_entity=legal_entity
    )
    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=campus.id,
        legal_entity=other_entity,
        evidence={
            "counsel_engagement_ref": "x", "takedown_sop_ref": "x", "oncall_rota_ref": "x",
            "breach_rehearsal_at": "x", "campus_mou_ref": "x", "notice_version_ids": ["x"],
        },
        authorised_by_human="a",
    )
    audit_before = AuditLog.objects.count()

    Campus.objects.filter(id=campus.id).update(discovery_enabled_at=timezone.now())

    campus.refresh_from_db()
    assert campus.discovery_enabled_at is None, (
        "three ORM statements opened the discovery gate: ADR-002 §4.1(b)'s "
        "floor is below the control it describes"
    )
    assert AuditLog.objects.count() > audit_before, (
        "the gate changed state with no audit row — the most legally "
        "significant action in the system left no trace"
    )


@pytest.mark.xfail(strict=True, reason=LIVE_CRITICAL)
def test_the_application_role_cannot_truncate_the_audit_log(city):
    """RED TEAM §3. Two statements from the application's own role:
    `SET bookhop.allow_flush='yes'` then `TRUNCATE audit_log`.

    Migration 0002's justification is *"the audit trail has to resist the
    application as well as the user"*, and the escape hatch added for Django's
    `sql_flush` is reachable from the application. The project **proved** the
    other bypass shut — 42501 on `SET session_replication_role` — which makes
    the asymmetry the finding.
    """
    from apps.core.services import record_audit

    if connection.vendor != "postgresql":
        pytest.skip(
            "NOT VERIFIABLE ON THIS ENGINE (vendor=sqlite, slice=S1): SQLite has no "
            "TRUNCATE statement (measured: a syntax error) and no role system, so "
            "neither half of this attack exists here. ENGINE-DIVERGENCE §12."
        )
    record_audit(None, "test.one", city)
    with connection.cursor() as cursor:
        cursor.execute("SET bookhop.allow_flush = 'yes'")
        cursor.execute("TRUNCATE audit_log")
    assert AuditLog.objects.exists(), "the application role emptied the audit log"
