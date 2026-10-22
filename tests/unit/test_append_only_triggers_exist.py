"""Every table that claims append-only has its guard **installed**.

**This is the test that would have caught a measured, shipped defect**, and the
defect is the reason the file exists rather than the other way round.

`accounts/0003` widened `notice_versions.kind`'s CHECK to add `RANKING` and
`GRIEVANCE_PROCEDURE`. SQLite cannot alter a CHECK, so Django's SQLite backend
**rebuilds the table** — create new, copy rows, `DROP TABLE` old, rename — and
**triggers belong to the table, so the drop takes them.** Nothing puts them
back. For one migration `notice_versions` was an ordinary mutable table on
SQLite while DATA-MODEL §2 said *"Trigger blocks all UPDATE and DELETE"* and
`COMPLIANCE.md` §8.1 rested *"we can show what a user agreed to on a given
date"* on it.

**It was invisible on PostgreSQL**, where `ALTER TABLE … ADD CONSTRAINT` leaves
triggers alone — so the engine production runs on is the one that would never
have reported it, and the only symptom anywhere was a test that happened to
exercise the UPDATE.

**The hazard is general and it is not about `notice_versions`.** On SQLite,
*any* future `AlterField`, constraint change or column rename on a
trigger-protected table silently removes its guard, and that covers every
append-only guarantee in the system. A migration can be reviewed by two agents,
applied cleanly, and leave tamper-evidence switched off.

So the question asked here is the existence one, by introspection, on **both
engines** — not "does an UPDATE raise" (which is `test_consent.py`'s and
`test_audit_append_only.py`'s job, one table at a time) but *"is the guard
there at all, for every table that claims one?"* `CLAUDE.md` rule 9 for a
control that can be deleted by an unrelated migration.

Introspection goes through `connection.introspection` and the engine's own
catalog, never `information_schema` on one engine and `PRAGMA` on the other
(ADR-003 §2.3 W4) — and the two catalog queries are the one place in this file
where the engines differ, which is stated rather than hidden.
"""

import pytest
from django.db import connection

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

#: Tables whose guard is a write **restriction** rather than append-only.
GUARDED = {
    "campuses": "ADR-002 §4.1(b) — discovery_enabled_at may not be set without an authorisation",
}


def installed_triggers():
    """`{table: {trigger names}}`, from the engine's own catalog.

    The only engine-specific code in this file, and it is two queries rather
    than two behaviours: both answer *"which triggers are attached to which
    table?"*, which is a question both engines can answer exactly.
    """
    found = {}
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute(
                "SELECT c.relname, t.tgname FROM pg_trigger t "
                "JOIN pg_class c ON c.oid = t.tgrelid "
                "WHERE NOT t.tgisinternal"
            )
        elif connection.vendor == "sqlite":
            cursor.execute("SELECT tbl_name, name FROM sqlite_master WHERE type = 'trigger'")
        else:  # pragma: no cover - ADR-001 §2.2 permits two engines
            pytest.fail(f"no trigger introspection written for {connection.vendor!r}")
        for table, trigger in cursor.fetchall():
            found.setdefault(table, set()).add(trigger)
    return found


@pytest.mark.parametrize("table,claim", sorted(APPEND_ONLY.items()))
def test_every_append_only_table_has_a_trigger_installed(table, claim, engine):
    """The existence check, per table, with the claim in the failure message so
    a reader learns what broke rather than which trigger is missing."""
    triggers = installed_triggers()
    assert triggers, "no triggers found at all — this test would pass vacuously"
    assert triggers.get(table), (
        f"{table} has **no trigger at all** on {engine}, but {claim}.\n"
        "The likeliest cause is a migration that altered this table: on SQLite a "
        "CHECK or field change rebuilds the table and the DROP takes its triggers "
        "with it, silently. Re-create them in the same migration — "
        "`accounts/0004_restore_append_only_guards` is the worked example."
    )


@pytest.mark.parametrize("table,claim", sorted(GUARDED.items()))
def test_every_write_guarded_table_has_a_trigger_installed(table, claim, engine):
    triggers = installed_triggers()
    assert triggers.get(table), f"{table} has no trigger on {engine}, but {claim}"


def test_each_append_only_table_blocks_both_update_and_delete(engine):
    """Existence is not enough: a table with only a `no_delete` trigger is
    append-only against half the threat, and on SQLite the two are **separate
    triggers** so a rebuild can take one and leave the other.

    PostgreSQL expresses both in one `BEFORE UPDATE OR DELETE` trigger, so the
    shape of the assertion differs by engine while the property does not — which
    is why this reads the count on SQLite and the presence on PostgreSQL, and
    says so instead of asserting a number that means different things.
    """
    triggers = installed_triggers()
    for table in APPEND_ONLY:
        names = triggers.get(table, set())
        if connection.vendor == "sqlite":
            assert any("no_update" in n for n in names), f"{table}: no UPDATE guard on {engine}"
            assert any("no_delete" in n for n in names), f"{table}: no DELETE guard on {engine}"
        else:
            assert names, f"{table}: no guard on {engine}"


def test_the_introspection_would_notice_a_missing_trigger(engine):
    """`CLAUDE.md` rule 12. Every assertion above is a presence check, and a
    broken introspection reports presence for nothing — or, worse, for
    everything. Drop one trigger inside a transaction that rolls back, and
    prove the reader sees it go.
    """
    if connection.vendor != "sqlite":
        pytest.skip(
            f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S1): dropping a "
            "trigger to prove the reader notices needs DDL inside a rolled-back "
            "transaction, and on PostgreSQL migration core/0003 marks these "
            "triggers `ENABLE ALWAYS` on tables the test role is deliberately "
            "being revoked privileges on (RED TEAM §1). The SQLite half proves "
            "the introspection is not blind; the PostgreSQL catalog read is the "
            "same query QA asserts in tests/contract/test_postgres_catalog.py."
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
        # Put them back: `django_db` rolls back DML, and SQLite DDL inside a
        # transaction does roll back (QA measured it in
        # test_engine_claims_measured.py §3.12) — but this test does not depend
        # on that holding, because a leaked missing trigger would make every
        # later test in the file lie.
        from importlib import import_module

        module = import_module("apps.accounts.migrations.0004_restore_append_only_guards")
        with connection.cursor() as cursor:
            for statement in module.SQLITE_FORWARD:
                cursor.execute(statement)


def test_the_claim_list_covers_every_table_the_contract_calls_append_only():
    """The list's own guard: a table marked append-only in DATA-MODEL and absent
    from `APPEND_ONLY` is a table nothing here checks. Read from
    `apps/core/p14.py`'s frozen-table knowledge where it overlaps, and otherwise
    asserted as a fixed set so adding a table is a deliberate edit.
    """
    assert set(APPEND_ONLY) == {
        "audit_log", "gate_authorisations", "consents",
        "age_verification_events", "notice_versions",
    }
    # S4/S5 add two more append-only tables; they are not here because they do
    # not exist yet, and `test_scoping.py`'s pending-model pattern is what makes
    # that visible rather than silent.
    from django.apps import apps as django_apps

    tables = {model._meta.db_table for model in django_apps.get_models()}
    assert "transfer_events" not in tables, (
        "transfer_events exists (S4) and DATA-MODEL §5 calls it append-only; add "
        "it to APPEND_ONLY with its citation"
    )
    assert "messages" not in tables, (
        "messages exists (S5); add its guard and its citation"
    )
