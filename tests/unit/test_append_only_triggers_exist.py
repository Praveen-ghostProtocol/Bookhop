"""Every append-only table **refuses** an UPDATE and a DELETE, on both engines.

**QA finding A-1, and the first thing to say is that my implementation drifted
from the specification rather than merely being incomplete.** The CTO specified
*"the exact expected trigger set per table per engine, failing by name"*. What
I wrote asserted that the table had **at least one** trigger — so when QA
dropped one of a pair on PostgreSQL and left the sibling standing, the control
reported green while `audit_log` was freely UPDATE-able. That is the same shape
as everything else this slice has turned up: **the check cannot fail in the
case it was written for.** The drift is mine and the specification was right.

So this file now has three layers, cheapest first, and the last is the one that
holds:

  1. **the exact expected set, by name, per engine** — the specification as
     written. A dropped sibling fails here and the message names it;
  2. **both operations are expressed** — on SQLite the UPDATE and DELETE guards
     are separate triggers, so a rebuild can take one and leave the other;
  3. **the property, measured** — an UPDATE and a DELETE are actually refused,
     per table, per engine. Presence is a proxy; refusal is the thing. A
     trigger that exists and whose body was replaced with `RETURN NEW` passes
     (1) and (2) and fails (3).

**Why presence is kept at all rather than replaced.** It fails *by name* and
therefore says *which* guard went, which a behavioural failure does not —
`erase_account` and the retention job both touch these tables, and "an UPDATE
succeeded" is a worse starting point for a 3am diagnosis than "`audit_log` is
missing `audit_log_append_only`". Two layers, `CLAUDE.md` rule 14, and here
they genuinely are independent: one reads the catalog, the other issues SQL.

The hazard that motivated the file is unchanged and is in `ENGINE-DIVERGENCE`
§12.2: on SQLite **any** `AlterField` or constraint change rebuilds the table
and **the DROP takes its triggers**, silently, invisibly to PostgreSQL. That is
how `notice_versions` lost both of its guards for one migration.
"""

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

pytestmark = pytest.mark.django_db

#: table -> what claims it is append-only. Not a flat list (`CLAUDE.md`
#: rule 11): the citation is per entry, so adding a table forces its reader to
#: name the document that promises the property.
APPEND_ONLY = {
    "audit_log": "DATA-MODEL §8 — append-only, tamper-evident hash chain",
    "gate_authorisations": "DATA-MODEL §1 — no UPDATE except revoked_at/revoked_reason",
    "consents": "DATA-MODEL §2 — append-only; the record that the deletion was lawful",
    "age_verification_events": "DATA-MODEL §2 — append-only; the whole age audit trail",
    "notice_versions": "DATA-MODEL §2 — immutable; §8.1 rests on it",
}

#: **The exact expected trigger set, per table, per engine** — the CTO's
#: specification, which the first version of this file did not implement.
#:
#: PostgreSQL expresses UPDATE and DELETE in one `BEFORE UPDATE OR DELETE`
#: trigger and adds a statement-level TRUNCATE guard; SQLite has no TRUNCATE
#: statement at all and needs one trigger per operation. The sets differ
#: because the engines differ, and writing both out is what lets a missing
#: **sibling** fail by name instead of being covered by its partner.
EXPECTED = {
    "postgresql": {
        "audit_log": {"audit_log_append_only", "audit_log_no_truncate"},
        "gate_authorisations": {
            "gate_authorisations_append_only",
            "gate_authorisations_no_truncate",
            "gate_authorisations_evidence_complete",
        },
        "consents": {"consents_append_only", "consents_no_truncate"},
        "age_verification_events": {
            "age_verification_events_append_only",
            "age_verification_events_no_truncate",
        },
        "notice_versions": {"notice_versions_append_only", "notice_versions_no_truncate"},
        "campuses": {"campuses_gate_authorised"},
    },
    "sqlite": {
        "audit_log": {"audit_log_no_update", "audit_log_no_delete"},
        "gate_authorisations": {
            "gate_authorisations_no_update",
            "gate_authorisations_no_delete",
            "gate_authorisations_evidence_complete_insert",
            "gate_authorisations_evidence_complete_update",
        },
        "consents": {"consents_no_update", "consents_no_delete"},
        "age_verification_events": {
            "age_verification_events_no_update",
            "age_verification_events_no_delete",
        },
        "notice_versions": {"notice_versions_no_update", "notice_versions_no_delete"},
        "campuses": {"campuses_gate_authorised", "campuses_gate_closed_on_insert"},
    },
}


def installed_triggers():
    """`{table: {trigger names}}`, from the engine's own catalog.

    The only engine-specific code here, and it is two queries rather than two
    behaviours: both answer *"which triggers are attached to which table?"*,
    which both engines can answer exactly. Never `information_schema` on one
    and `PRAGMA` on the other (ADR-003 §2.3 W4).
    """
    found = {}
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute(
                "SELECT c.relname, t.tgname FROM pg_trigger t "
                "JOIN pg_class c ON c.oid = t.tgrelid WHERE NOT t.tgisinternal"
            )
        elif connection.vendor == "sqlite":
            cursor.execute("SELECT tbl_name, name FROM sqlite_master WHERE type = 'trigger'")
        else:  # pragma: no cover - ADR-001 §2.2 permits two engines
            pytest.fail(f"no trigger introspection written for {connection.vendor!r}")
        for table, trigger in cursor.fetchall():
            found.setdefault(table, set()).add(trigger)
    return found


# --- layer 1: the exact expected set, by name ----------------------------


@pytest.mark.parametrize("table", sorted(EXPECTED["postgresql"]))
def test_the_exact_expected_trigger_set_is_installed(table, engine):
    """**The specification as written, and the fix for QA A-1.**

    A set comparison, not a truthiness check. The case that matters is a
    **dropped sibling**: with `{table}_no_truncate` alive and
    `{table}_append_only` gone, the old control said "this table has a trigger"
    and the table was freely UPDATE-able.
    """
    expected = EXPECTED[connection.vendor][table]
    actual = installed_triggers().get(table, set())
    missing = sorted(expected - actual)
    assert not missing, (
        f"{table} is missing {missing} on {engine}, but {APPEND_ONLY.get(table, 'it is guarded')}.\n"
        "The likeliest cause is a migration that altered this table: on SQLite a "
        "CHECK or field change rebuilds the table and the DROP takes its triggers "
        "with it, silently (ENGINE-DIVERGENCE §12.2). Re-create them in the same "
        "migration — accounts/0004_restore_append_only_guards is the worked example."
    )


@pytest.mark.parametrize("table", sorted(EXPECTED["postgresql"]))
def test_no_unexpected_trigger_is_installed(table, engine):
    """The other direction. A trigger nobody expected is a control nobody
    reviewed, and on these five tables that is a write path nobody reviewed."""
    expected = EXPECTED[connection.vendor][table]
    extra = sorted(installed_triggers().get(table, set()) - expected)
    assert not extra, (
        f"{table} carries {extra} on {engine}, which no migration in this "
        "repository is expected to have created. Add it to EXPECTED with its "
        "reason, or find out who did."
    )


# --- layer 3: the property, measured -------------------------------------


def _subject(table, student, privacy_notice, legal_entity, complete_evidence, city):
    """One row to attack, and a column to attack it on.

    The column is deliberately one **no CHECK constraint governs**, so a
    refusal is the append-only trigger's and not a constraint's — otherwise
    the test could pass while the guard was gone.
    """
    from apps.accounts.models import AgeVerificationEvent, Consent, NoticeVersion
    from apps.core.models import AuditLog, GateAuthorisation
    from apps.core.services import record_audit

    if table == "audit_log":
        record_audit(None, "test.one", city)
        return AuditLog, AuditLog.objects.first(), "action", "tampered"
    if table == "gate_authorisations":
        row = GateAuthorisation.objects.create(
            gate="C", scope_type="CAMPUS", scope_id=city.id, legal_entity=legal_entity,
            evidence=complete_evidence, authorised_by_human="A Human",
        )
        return GateAuthorisation, row, "authorised_by_human", "Someone Else"
    if table == "consents":
        return Consent, Consent.objects.filter(
            user_pseudonym=student.person_pseudonym
        ).first(), "created_at", timezone.now()
    if table == "age_verification_events":
        row = AgeVerificationEvent.objects.create(
            user_pseudonym=student.person_pseudonym, outcome="ADULT_CONFIRMED",
            method="SELF_DECLARED_DOB_SERVER_CHECKED",
        )
        return AgeVerificationEvent, row, "occurred_at", timezone.now()
    # notice_versions: a fresh, unreferenced row. `privacy_notice` is the
    # target of a `consents` FK declared PROTECT, so deleting it would raise
    # Django's ProtectedError before a statement reached the server and the
    # test would measure the ORM rather than the trigger.
    row = NoticeVersion.objects.create(
        kind="TERMS", version="9999-01-01.1", locale="en",
        body_md="unreferenced", sha256="9" * 64,
    )
    return NoticeVersion, row, "published_at", timezone.now()


@pytest.mark.parametrize("table", sorted(APPEND_ONLY))
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_each_append_only_table_actually_refuses_the_operation(
    table, operation, engine, student, privacy_notice, legal_entity, complete_evidence, city
):
    """**The property, not the presence** — QA A-1's actual fix.

    A trigger that exists and whose body was replaced with `RETURN NEW` passes
    every name check in this file and fails here. Ten cases: five tables ×
    two operations, on whichever engine the suite runs.
    """
    model, row, column, value = _subject(
        table, student, privacy_notice, legal_entity, complete_evidence, city
    )
    assert row is not None, f"no {table} row to attack — this case would pass vacuously"

    with pytest.raises(DatabaseError) as refusal:
        with transaction.atomic():
            if operation == "DELETE":
                model.objects.filter(pk=row.pk).delete()
            else:
                model.objects.filter(pk=row.pk).update(**{column: value})

    assert "append-only" in str(refusal.value) or "no UPDATE except" in str(refusal.value), (
        f"{table} refused the {operation}, but not for the append-only reason: "
        f"{refusal.value}"
    )
    assert model.objects.filter(pk=row.pk).exists(), (
        f"{table} was {operation}-able on {engine}, and {APPEND_ONLY[table]}"
    )


def test_the_introspection_would_notice_a_missing_trigger(engine):
    """`CLAUDE.md` rule 12 on layer 1. Every assertion there is a presence
    check, and a broken introspection reports presence for everything. Drop
    one trigger and prove the reader sees it go."""
    if connection.vendor != "sqlite":
        pytest.skip(
            f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S1): dropping a "
            "trigger to prove the reader notices needs DDL inside a rolled-back "
            "transaction, and on PostgreSQL these triggers are `ENABLE ALWAYS` on "
            "tables the test role is being revoked privileges on (RED TEAM §1). "
            "The SQLite half proves the introspection is not blind, and layer 3 "
            "above measures the property itself on both engines."
        )
    before = installed_triggers()["notice_versions"]
    assert before, "nothing to drop — this test would pass vacuously"
    with connection.cursor() as cursor:
        for name in before:
            cursor.execute(f"DROP TRIGGER {name}")
    try:
        assert not installed_triggers().get("notice_versions"), (
            "the introspection still reports triggers that were just dropped"
        )
    finally:
        from importlib import import_module

        module = import_module("apps.accounts.migrations.0004_restore_append_only_guards")
        with connection.cursor() as cursor:
            for statement in module.SQLITE_FORWARD:
                cursor.execute(statement)


def test_the_claim_list_covers_every_table_the_contract_calls_append_only():
    """The list's own guard: a table marked append-only in DATA-MODEL and
    absent from `APPEND_ONLY` is a table nothing here checks."""
    assert set(APPEND_ONLY) == {
        "audit_log", "gate_authorisations", "consents",
        "age_verification_events", "notice_versions",
    }
    assert set(EXPECTED["postgresql"]) == set(EXPECTED["sqlite"]), (
        "the two engines' expected sets cover different tables, so one engine "
        "has a table nothing checks"
    )
    from django.apps import apps as django_apps

    tables = {model._meta.db_table for model in django_apps.get_models()}
    assert "transfer_events" not in tables, (
        "transfer_events exists (S4) and DATA-MODEL §5 calls it append-only; add "
        "it to APPEND_ONLY and to both EXPECTED sets with its citation"
    )
    assert "messages" not in tables, "messages exists (S5); add its guard and its citation"
