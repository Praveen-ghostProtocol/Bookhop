"""What the server actually installed, and rule 16's standard applied to all five guards.

Two jobs:

1. **Read the catalog, not the migration.** `POSTGRES-FIRST-RUN.md` v1.1's own
   correction is that `sqlmigrate` emits nothing for these operations (they are
   `RunPython`) and that `pg_trigger`/`pg_proc` are better evidence anyway —
   they report what the server kept, not what a migration intended. QA agrees
   and asserts it here so it is re-read on every run rather than once by hand.

2. **Encode rule 16's standard for every guard.** `CLAUDE.md` rule 16: *a
   refused operation is not evidence a guard fired for the right reason*,
   because plpgsql resolves identifiers at the first execution of **each
   branch** — so a body with a typo in an unexercised branch is created
   cleanly, passes every happy path, and then fails as something else while
   still blocking the operation. Backend set the right standard (SQLSTATE **and**
   message text) and applied it across 95 direct assertions during the run.
   **QA's finding is that the SQLSTATE half did not come back into the
   repository** — see `test_finding_the_sqlstate_half_of_rule_16_is_not_in_the_suite`
   — so these tests put it there for the two guards no other test reaches.
"""

import pytest
from django.db import DatabaseError, connection, transaction

postgres_only = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason=(
        "REQUIRES PostgreSQL (slice=S0): this reads `pg_trigger`/`pg_proc` and "
        "asserts SQLSTATEs that only exist on PostgreSQL. SQLite has no "
        "catalog of this shape and no SQLSTATE. The SQLite halves of the same "
        "guards are asserted in tests/e2e/test_gate_journey.py. Run with "
        "BOOKHOP_DB_ENGINE=postgres."
    ),
)

pytestmark = [pytest.mark.django_db, postgres_only]

RAISE_EXCEPTION = "P0001"
INSUFFICIENT_PRIVILEGE = "42501"

#: ADR-002/ADR-003's five guards, by the names the migrations create.
EXPECTED_TRIGGERS = {
    "audit_log_append_only",
    "audit_log_no_truncate",
    "gate_authorisations_append_only",
    "gate_authorisations_no_truncate",
    "gate_authorisations_evidence_complete",
    "campuses_gate_authorised",
}

EXPECTED_FUNCTIONS = {
    "audit_log_is_append_only",
    "gate_authorisations_is_append_only",
    "campuses_gate_is_authorised",
    "bookhop_truncate_guard",
    "gate_authorisations_evidence_complete",
}


def _sqlstate(exc):
    cause = getattr(exc, "__cause__", None)
    return getattr(getattr(cause, "diag", None), "sqlstate", None)


def _rows(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params or [])
        return cur.fetchall()


# --------------------------------------------------------------------------
# 1. the catalog
# --------------------------------------------------------------------------


def test_every_guard_trigger_is_installed_and_enable_always():
    """ENGINE-DIVERGENCE §3.6a. `tgenabled` is the only thing that answers this:
    a trigger can exist and still be bypassed by `session_replication_role`
    unless it is `'A'`, and a logical-replication apply worker and some restore
    paths use exactly that role.

    QA previously asserted this as **migration text**. This is the catalog.
    """
    rows = _rows(
        "SELECT tgname, tgenabled FROM pg_trigger t "
        "JOIN pg_class c ON c.oid = t.tgrelid "
        "WHERE NOT t.tgisinternal AND c.relname IN "
        "('audit_log', 'gate_authorisations', 'campuses')"
    )
    installed = {name: enabled for name, enabled in rows}
    assert set(installed) == EXPECTED_TRIGGERS, (
        f"installed triggers differ from the five guards: {sorted(installed)}"
    )
    not_always = {n: e for n, e in installed.items() if e != "A"}
    assert not_always == {}, (
        f"these guards are not ENABLE ALWAYS, so session_replication_role or a "
        f"restore bypasses them: {not_always}"
    )


def test_every_plpgsql_function_is_installed_and_there_are_exactly_five():
    """`POSTGRES-FIRST-RUN.md` §0(a): **five** bodies, not six. The sixth was
    the price-immutability trigger, which does not exist because `listings` is
    an S2 table — a number repeated in three documents before the run corrected
    it.

    Asserted as an exact set, so S2 adding `listings_price_is_immutable` turns
    this red and the count is updated deliberately rather than discovered.
    """
    rows = _rows(
        "SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'public' AND p.prorettype = 'trigger'::regtype"
    )
    installed = {name for (name,) in rows}
    assert installed == EXPECTED_FUNCTIONS, (
        f"plpgsql trigger functions differ from the five: {sorted(installed)}"
    )


def test_the_truncate_guards_are_statement_level_and_the_rest_are_row_level():
    """The distinction the whole TRUNCATE hole rests on: row triggers **do not
    fire on TRUNCATE**, which is why migration 0003 adds separate statement-level
    triggers. Read from `tgtype`'s bitmask rather than from the migration, so a
    guard attached at the wrong level is visible.

    `tgtype` bit 0 is FOR EACH ROW; bit 5 (32) is TRUNCATE.
    """
    rows = _rows(
        "SELECT tgname, tgtype FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
        "WHERE NOT t.tgisinternal AND c.relname IN ('audit_log', 'gate_authorisations')"
    )
    for name, tgtype in rows:
        for_each_row = bool(tgtype & 1)
        on_truncate = bool(tgtype & 32)
        if name.endswith("_no_truncate"):
            assert on_truncate and not for_each_row, (
                f"{name} must be a statement-level TRUNCATE trigger "
                f"(tgtype={tgtype}); a row trigger never fires on TRUNCATE"
            )
        else:
            assert for_each_row and not on_truncate, (
                f"{name} must be a row trigger (tgtype={tgtype})"
            )


def test_finding_the_application_role_cannot_reach_the_replica_bypass():
    """ENGINE-DIVERGENCE §10.4 item 3's finding, verified independently — and it
    is a **security property worth having in the suite**, not only a note.

    `session_replication_role = 'replica'` is the documented way to make
    non-ALWAYS triggers stop firing. Measured here: the application role is
    refused with SQLSTATE 42501, so **the bypass is unreachable from the
    application at all** — which is why backend's negative control for item 3
    had to run as `postgres`.

    Two consequences QA draws, and they point opposite ways:
    * the `ENABLE ALWAYS` hardening is defence against a **restore or a
      replication apply worker**, not against the app. `INFRA.md` §3.3's restore
      rehearsal is where it earns its place, and the S8 escalation stands.
    * it also means QA **cannot** reproduce item 3's negative control under the
      application role, so that one assertion rests on backend's run as
      `postgres`. Stated rather than implied: see
      `test_the_replica_role_negative_control_is_not_reproducible_here`.
    """
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute("SET session_replication_role = 'replica'")
    assert _sqlstate(exc.value) == INSUFFICIENT_PRIVILEGE, (
        "the application role can set session_replication_role; the "
        f"non-ALWAYS bypass is reachable from the app: {_sqlstate(exc.value)}"
    )


def test_the_replica_role_negative_control_is_not_reproducible_here():
    """**NOT VERIFIED BY QA, and recorded rather than skipped silently.**

    Backend's negative control for `ENABLE ALWAYS` — downgrade one trigger to
    plain-enabled, set `session_replication_role='replica'`, and show the UPDATE
    **does** get through — is the control that proves those assertions measure
    ALWAYS and not something else. It needs a superuser, and the test role is
    refused (42501, asserted above).

    So QA confirms the *premise* of that control (the role is refused) and the
    *state* it measures (`tgenabled='A'` for all six, asserted above), but not
    the control itself. A green QA run is not evidence for item 3's negative
    control; backend's run as `postgres` is the only evidence, and it should be
    re-run by platform-sre as part of the S8 restore rehearsal, where the role
    doing the work genuinely is privileged.
    """
    rows = _rows("SELECT current_setting('is_superuser')")
    assert rows[0][0] == "off", (
        "the test role is a superuser, so the privilege finding above is not "
        "what it appears and item 3's control could in fact be reproduced here"
    )


# --------------------------------------------------------------------------
# 2. rule 16 for the two guards no other test reaches
# --------------------------------------------------------------------------


def _assert_p0001(excinfo, *, contains):
    assert _sqlstate(excinfo.value) == RAISE_EXCEPTION, (
        f"refused with SQLSTATE {_sqlstate(excinfo.value)!r}, not P0001. Rule 16: "
        "a refusal is not evidence the guard fired for the right reason — an "
        "unresolved identifier in an unexercised plpgsql branch also refuses"
    )
    assert contains in str(excinfo.value), (
        f"P0001 raised but the message lacks {contains!r}: {excinfo.value}"
    )
    assert "%" not in str(excinfo.value), (
        "a literal % survived into the message (ENGINE-DIVERGENCE §10.1)"
    )


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
        city=city, name="Catalog Campus", slug="catalog", legal_entity=entity
    )
    return campus, entity


def test_the_gate_write_guard_raises_p0001_with_its_own_message(campus_and_entity):
    """`campuses_gate_is_authorised` — one of the two guards with **no SQLite
    equivalent to compare against**, so its PostgreSQL body is the only version
    of the rule. Rule 16's standard applied: SQLSTATE and text, not just a
    refusal.
    """
    from apps.core.models import Campus
    from django.utils import timezone

    campus, _entity = campus_and_entity
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            Campus.objects.filter(pk=campus.pk).update(
                discovery_enabled_at=timezone.now()
            )
    _assert_p0001(exc, contains="4.1(b)")
    campus.refresh_from_db()
    assert campus.discovery_enabled_at is None


def test_the_gate_insert_guard_raises_p0001_with_its_own_message(campus_and_entity):
    """The INSERT branch of the same function — and a **different branch is a
    different first execution**, which is exactly what rule 16 is about. A typo
    in the INSERT arm would have survived every UPDATE test.
    """
    from apps.core.models import Campus
    from django.utils import timezone

    _campus, entity = campus_and_entity
    from apps.core.models import City

    city = City.objects.get(name="Chennai")
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            Campus.objects.create(
                city=city, name="Born Open", slug="born-open-pg",
                legal_entity=entity, discovery_enabled_at=timezone.now(),
            )
    _assert_p0001(exc, contains="4.1(a)")


@pytest.mark.parametrize(
    "key",
    ["counsel_engagement_ref", "takedown_sop_ref", "oncall_rota_ref",
     "breach_rehearsal_at", "campus_mou_ref", "notice_version_ids"],
)
def test_the_evidence_guard_raises_p0001_naming_the_missing_key(campus_and_entity, key):
    """`gate_authorisations_evidence_complete` — the fifth body, and the one
    whose message interpolates the loop variable `k`. §10.1 found four `%`
    specifiers that psycopg was eating; this asserts the interpolated value
    arrives, per key, so the message tells an operator *which* item to fetch.
    """
    from apps.core.models import GateAuthorisation

    campus, entity = campus_and_entity
    evidence = {
        "counsel_engagement_ref": "ENG-1", "takedown_sop_ref": "SOP-1",
        "oncall_rota_ref": "ROTA-1", "breach_rehearsal_at": "2026-11-12",
        "campus_mou_ref": "MOU-1", "notice_version_ids": [1, 2, 3],
    }
    evidence.pop(key)
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            GateAuthorisation.objects.create(
                gate="C", scope_type="CAMPUS", scope_id=campus.id,
                legal_entity=entity, evidence=evidence,
                authorised_by_human="A Named Human",
            )
    _assert_p0001(exc, contains=key)


def test_the_evidence_guards_empty_array_branch_is_distinguishable(campus_and_entity):
    """The `jsonb_array_length` branch, which is a **separate branch** and so a
    separate first execution. It must name the key too, or the array case is
    indistinguishable from a missing key and an operator is told the wrong
    thing.
    """
    from apps.core.models import GateAuthorisation

    campus, entity = campus_and_entity
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            GateAuthorisation.objects.create(
                gate="C", scope_type="CAMPUS", scope_id=campus.id,
                legal_entity=entity,
                evidence={
                    "counsel_engagement_ref": "ENG-1", "takedown_sop_ref": "SOP-1",
                    "oncall_rota_ref": "ROTA-1", "breach_rehearsal_at": "2026-11-12",
                    "campus_mou_ref": "MOU-1", "notice_version_ids": [],
                },
                authorised_by_human="A Named Human",
            )
    _assert_p0001(exc, contains="notice_version_ids")


def test_the_gate_authorisation_append_only_guard_raises_p0001(campus_and_entity):
    """The second 0002 body, on its own table, with its own table name in the
    message — `TG_TABLE_NAME` interpolation, asserted."""
    from apps.core.models import GateAuthorisation

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
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            GateAuthorisation.objects.filter(pk=auth.pk).update(gate="B")
    _assert_p0001(exc, contains="gate_authorisations")

    # The permitted counterpart, so the guard is not simply "no UPDATE ever".
    from django.utils import timezone

    GateAuthorisation.objects.filter(pk=auth.pk).update(
        revoked_at=timezone.now(), revoked_reason="permitted"
    )
    auth.refresh_from_db()
    assert auth.revoked_at is not None


def test_finding_the_sqlstate_half_of_rule_16_is_not_in_the_suite():
    """**FINDING F17, non-blocking — and it is `CLAUDE.md` rule 9's own shape.**

    ENGINE-DIVERGENCE §10 reports *"95 direct assertions, 0 failures, each
    asserting the SQLSTATE **and** the exception message text"*. The standard is
    the right one and QA adopts it. But those 95 ran **directly against the
    server**, and measured here: the string `P0001` appears in
    `tests/unit/**` and `tests/api/**` exactly once, in a **comment**. No test
    in backend's trees asserts a SQLSTATE.

    So the message half of rule 16 is in the repository
    (`test_the_append_only_message_names_the_operation_it_refused`, which is a
    good test and engine-neutral) and the SQLSTATE half is not. A guard that
    began refusing with a different mechanism — a CHECK constraint (23514), or
    `RAISE … USING ERRCODE` — while keeping its text would pass `pytest`
    tomorrow.

    **Severity: low, and QA says so rather than inflating it.** The hazard rule
    16 actually names — an unresolved identifier in an unexercised plpgsql
    branch — produces *different text* as well as a different SQLSTATE, so the
    message assertions catch it. The SQLSTATE adds the narrower case where the
    text is right and the mechanism changed.

    QA has encoded the SQLSTATE half for all five bodies in this file and in
    `tests/e2e/test_audit_tamper.py`, which is where it belongs — QA's trees run
    on both engines in CI. **This test is the record that the claim in §10 was
    about a run, not about the suite**, so the next reader does not take "each
    asserting the SQLSTATE" as something `pytest` enforces.
    """
    import pathlib

    repo = pathlib.Path(__file__).resolve().parents[2]
    hits = []
    for tree in ("tests/unit", "tests/api"):
        for path in sorted((repo / tree).glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for number, line in enumerate(text.splitlines(), 1):
                if "P0001" in line and not line.strip().startswith(("#", '"', "'")):
                    hits.append(f"{tree}/{path.name}:{number}")
    assert hits == [], (
        "backend's trees now assert a SQLSTATE; F17 is closed and this test "
        f"should become a regression: {hits}"
    )
