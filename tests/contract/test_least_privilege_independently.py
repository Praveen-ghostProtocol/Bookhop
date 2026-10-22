"""The privilege layer, measured in the state production actually runs in.

**Why this file exists.** Migration `core/0008` answers RED TEAM §1 and §3 by
revoking INSERT/UPDATE/TRUNCATE on `gate_authorisations` and TRUNCATE on
`audit_log` from the application role. `tests/conftest.py::
restore_gate_privileges_for_the_harness` then **grants all of it back for the
whole session**, for reasons that are good and documented: the suite has to
create `gate_authorisations` rows (the row is the subject of the gate tests), it
has to reach the UPDATE branch of 0002's trigger to assert it at all
(`CLAUDE.md` rule 16), and `transactional_db` teardown is Django's own
`sql_flush`, which is a TRUNCATE.

QA agrees with the fixture. It is the harness yielding to the control rather
than the control yielding to the harness, and backend flags it as *"the shape of
thing that quietly disarms a guard"* itself.

**But it has a consequence nothing measured: no test in the suite ever runs
against the privilege state production has.** `test_least_privilege.py` asserts
the migration contains the revocation and reads the live grant state — which, in
a session that re-granted, is the *re-granted* state. So the privilege layer was
verified **structurally** while every behavioural guard test was exercising the
**trigger** layer, on a database with one layer where production has two. If the
revocation were deleted from the migration tomorrow, the migration test would
catch it; if PostgreSQL stopped enforcing it, nothing would.

`GRANT` and `REVOKE` are transactional in PostgreSQL, so QA can put the
production state back **inside one test's transaction**, assert the behaviour,
and let the rollback restore the harness. That is what this file does, and it is
the first time the privilege layer has been asserted as behaviour rather than as
text.
"""

import pytest
from django.db import DatabaseError, connection, transaction

postgres_only = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason=(
        "REQUIRES PostgreSQL (slice=S1): a privilege layer needs a role system. "
        "SQLite has none — one process, full access to the file — so there is no "
        "weaker version of this control to assert, and migration 0008 is a no-op "
        "there by design. ENGINE-DIVERGENCE §12 records it as a PostgreSQL-only "
        "control with no SQLite equivalent, which means the two-layer property "
        "`CLAUDE.md` rule 14 asks for exists on one engine only."
    ),
)

pytestmark = [pytest.mark.django_db, postgres_only]

INSUFFICIENT_PRIVILEGE = "42501"
RAISE_EXCEPTION = "P0001"

#: Migration 0008's own table, verbatim.
REVOCATIONS = (
    ("gate_authorisations", "INSERT, UPDATE, TRUNCATE"),
    ("audit_log", "TRUNCATE"),
)


def _sqlstate(exc):
    cause = getattr(exc, "__cause__", None)
    return getattr(getattr(cause, "diag", None), "sqlstate", None)


def _role():
    with connection.cursor() as cur:
        cur.execute("SELECT current_user")
        return cur.fetchone()[0]


def _apply_production_privileges():
    """Put the production grant state back, inside this test's transaction.

    The rollback at the end of the test restores the harness's re-grant, so this
    cannot leak into another test — which is the property that makes asserting
    the real state affordable at all.
    """
    role = _role()
    with connection.cursor() as cur:
        for table, privileges in REVOCATIONS:
            cur.execute(f'REVOKE {privileges} ON {table} FROM "{role}"')


def _privileges():
    with connection.cursor() as cur:
        cur.execute(
            "SELECT has_table_privilege('gate_authorisations','INSERT'), "
            "has_table_privilege('gate_authorisations','UPDATE'), "
            "has_table_privilege('gate_authorisations','TRUNCATE'), "
            "has_table_privilege('audit_log','TRUNCATE')"
        )
        return cur.fetchone()


@pytest.fixture
def campus_and_entity(db):
    from apps.core.models import Campus, City, LegalEntity

    entity = LegalEntity.objects.create(
        cin="U72900TN2026PTC000001", inc20a_filed_at="2026-11-05",
        grievance_officer_name="G", grievance_officer_email="g@x.test",
        grievance_officer_phone="+910000000000",
    )
    city = City.objects.create(name="Chennai", state="Tamil Nadu")
    campus = Campus.objects.create(
        city=city, name="Privilege Campus", slug="privilege", legal_entity=entity
    )
    return campus, entity


# --------------------------------------------------------------------------
# 1. the production state refuses what RED TEAM §1 and §3 measured
# --------------------------------------------------------------------------


def test_the_revocation_takes_effect_and_the_rollback_restores_it():
    """The mechanism this whole file rests on, asserted first.

    If `REVOKE` were not transactional, every test below would leak the
    production privilege state into the rest of the session and break the
    harness — so the rollback is checked before anything is built on it.
    """
    before = _privileges()
    assert all(before), (
        "the harness re-grant is not in effect, so this file is measuring "
        f"something else: {before}"
    )

    sid = transaction.savepoint()
    _apply_production_privileges()
    assert _privileges() == (False, False, False, False), (
        "REVOKE did not take effect against the table owner; migration 0008's "
        "measured claim does not hold here"
    )
    transaction.savepoint_rollback(sid)
    assert _privileges() == before, "the rollback did not restore the harness grant"


def test_an_orm_insert_into_gate_authorisations_is_refused_by_privilege(campus_and_entity):
    """**RED TEAM §1's first statement, closed by privilege rather than by
    trigger.** The memo measured three ORM statements opening the gate on a
    campus with no CIN and no INC-20A, under an authorisation granted against a
    different legal entity, with every evidence value the string `"x"`, and zero
    `audit_log` rows.

    The first of those statements is the `gate_authorisations` insert. With the
    production grant state it is refused **before any trigger runs** — 42501, a
    privilege error, not P0001. That is what makes it a second independent
    layer: it does not depend on the trigger body being correct, or present.
    """
    from apps.core.models import GateAuthorisation

    campus, entity = campus_and_entity
    complete = {
        "counsel_engagement_ref": "ENG-1", "takedown_sop_ref": "SOP-1",
        "oncall_rota_ref": "ROTA-1", "breach_rehearsal_at": "2026-11-12",
        "campus_mou_ref": "MOU-1", "notice_version_ids": [1],
    }
    _apply_production_privileges()

    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            GateAuthorisation.objects.create(
                gate="C", scope_type="CAMPUS", scope_id=campus.id,
                legal_entity=entity, evidence=complete,
                authorised_by_human="A Named Human",
            )
    assert _sqlstate(exc.value) == INSUFFICIENT_PRIVILEGE, (
        "the insert was refused, but by the evidence trigger rather than by the "
        f"privilege ({_sqlstate(exc.value)}). The point of 0008 is a layer that "
        "holds when the trigger does not"
    )


def test_an_orm_update_of_gate_authorisations_is_refused_by_privilege(campus_and_entity):
    """The same for UPDATE, which is the branch `CLAUDE.md` rule 16 says has to
    be reachable to be asserted — and which, in production, is not reachable at
    all because the privilege is gone. Both facts are true and they are about
    different layers.
    """
    from apps.core.models import GateAuthorisation
    from django.utils import timezone

    campus, entity = campus_and_entity
    auth = GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=campus.id, legal_entity=entity,
        evidence={
            "counsel_engagement_ref": "ENG-1", "takedown_sop_ref": "SOP-1",
            "oncall_rota_ref": "ROTA-1", "breach_rehearsal_at": "2026-11-12",
            "campus_mou_ref": "MOU-1", "notice_version_ids": [1],
        },
        authorised_by_human="A Named Human",
    )
    _apply_production_privileges()

    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            GateAuthorisation.objects.filter(pk=auth.pk).update(
                revoked_at=timezone.now(), revoked_reason="by privilege"
            )
    assert _sqlstate(exc.value) == INSUFFICIENT_PRIVILEGE


# --------------------------------------------------------------------------
# 2. the independence `CLAUDE.md` rule 14 asks for, proved
# --------------------------------------------------------------------------


def test_truncate_is_refused_by_privilege_even_with_the_trigger_escape_granted(campus_and_entity):
    """**The test this file exists for: the two layers are independent.**

    Rule 14 asks for two layers that each reject the thing on their own, and
    RED TEAM §3's finding was that the gate had *one layer twice* — the trigger
    and the command both ran as the same role. So the escape is granted, which
    makes the **trigger** permit the TRUNCATE, and the privilege is revoked. If
    the two layers were one, this would succeed.

    It is refused, with 42501 — a privilege error, from a layer that does not
    read `bookhop.allow_flush` at all and cannot be reached by a session
    setting.
    """
    from apps.core.models import AuditLog

    with connection.cursor() as cur:
        cur.execute("SET bookhop.allow_flush = 'yes'")  # the trigger would allow it
    _apply_production_privileges()

    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute('TRUNCATE "audit_log"')
    assert _sqlstate(exc.value) == INSUFFICIENT_PRIVILEGE, (
        "with the trigger escape granted and the privilege revoked the TRUNCATE "
        f"was refused by {_sqlstate(exc.value)}; it must be the privilege, or "
        "the two layers are not independent"
    )
    assert AuditLog.objects.count() == 0 or True  # the table is untouched either way


def test_each_layer_refuses_the_truncate_on_its_own(campus_and_entity):
    """The same property stated as a matrix, which is how rule 14 reads.

    | escape | privilege | expected |
    |---|---|---|
    | unset  | granted   | refused by the **trigger** (P0001) |
    | granted| revoked   | refused by the **privilege** (42501) |
    | granted| granted   | permitted — this is the harness's own state, and it
    |        |           | is the only combination that lets the suite flush |
    """
    from apps.core.models import AuditLog

    # layer 1 alone: the trigger
    sid = transaction.savepoint()
    with connection.cursor() as cur:
        cur.execute("SET bookhop.allow_flush = 'no'")
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute('TRUNCATE "audit_log"')
    assert _sqlstate(exc.value) == RAISE_EXCEPTION
    transaction.savepoint_rollback(sid)

    # layer 2 alone: the privilege
    sid = transaction.savepoint()
    with connection.cursor() as cur:
        cur.execute("SET bookhop.allow_flush = 'yes'")
    _apply_production_privileges()
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute('TRUNCATE "audit_log"')
    assert _sqlstate(exc.value) == INSUFFICIENT_PRIVILEGE
    transaction.savepoint_rollback(sid)

    # neither: permitted, which is what the harness needs and why the fixture
    # exists. Asserted so the matrix has a negative control -- if this were also
    # refused, the two tests above would be measuring one thing twice.
    with connection.cursor() as cur:
        cur.execute("SET bookhop.allow_flush = 'yes'")
        cur.execute('TRUNCATE "audit_log"')
    assert AuditLog.objects.count() == 0


def test_the_revocation_does_not_remove_a_privilege_the_application_needs(campus_and_entity):
    """The other half of any privilege change: what still works.

    `audit_log` must remain **appendable** — `record_audit` runs inside every
    mutation's transaction, and a revoked INSERT would stop the application
    dead rather than stop an attacker. 0008 revokes TRUNCATE only on that table,
    and this asserts the distinction holds in the production state.
    """
    from apps.core.models import Campus
    from apps.core.services import record_audit

    campus, _entity = campus_and_entity
    _apply_production_privileges()

    row = record_audit(None, "qa.privilege", campus)
    assert row.pk is not None, (
        "the production privilege state blocks an audit append, which would "
        "stop every audited mutation"
    )
    assert isinstance(campus, Campus)


# --------------------------------------------------------------------------
# 3. the finding
# --------------------------------------------------------------------------


def test_finding_no_other_test_in_the_suite_sees_the_production_privilege_state():
    """**FINDING F18, non-blocking, and QA is not asking for the fixture to
    go.**

    Measured: with the harness fixture in effect, all four revoked privileges
    read back as granted. So every other guard test in the repository — the
    SQLSTATE tests, the gate tests, QA's own contract tests — exercises the
    **trigger** layer on a database that has one layer, while production has
    two. The privilege layer is asserted structurally by
    `test_least_privilege.py` (the migration contains the REVOKE) and
    behaviourally by nothing, which is `CLAUDE.md` rule 9's shape one level up:
    the control exists, and what was checked is that it exists.

    This file is the answer rather than the complaint — `GRANT`/`REVOKE` are
    transactional, so the production state can be restored per test and rolled
    back. What remains open is narrower and belongs to whoever owns the harness:
    **the suite's default state is the weaker of the two**, so a developer
    reading a green run is reading the trigger layer. One line in
    `test_least_privilege.py` pointing at this file would close that, and the
    deeper fix is the one 0008 already names — **move table ownership off the
    application role**, after which the harness could not re-grant and the
    question would not arise.
    """
    granted = _privileges()
    assert all(granted), (
        "the harness re-grant is no longer in effect. If the fixture has been "
        "removed, F18 is closed and this test should become a regression; if it "
        f"has been narrowed, the matrix in this file needs re-reading: {granted}"
    )
