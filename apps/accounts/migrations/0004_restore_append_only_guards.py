"""Re-create the S1 append-only triggers, which `0003` silently destroyed on SQLite.

**Measured, and it is the defect class this project keeps finding — this time in
the direction nobody was watching.** After `0003` widened
`notice_versions.kind`'s CHECK to add `RANKING` and `GRIEVANCE_PROCEDURE`
(DATA-MODEL A-25), `sqlite_master` listed ten of the twelve expected triggers:

    age_verification_events_no_delete / _no_update   present
    audit_log_no_delete / _no_update                 present
    campuses_gate_authorised / _closed_on_insert     present
    consents_no_delete / _no_update                  present
    gate_authorisations_* (4)                        present
    notice_versions_no_update                        **GONE**
    notice_versions_no_delete                        **GONE**

**Why.** SQLite cannot alter a CHECK constraint, so Django's SQLite backend
rebuilds the table: create a new one, copy the rows, `DROP TABLE` the old,
rename. **Triggers belong to the table, so the drop takes them** — and nothing
puts them back. `tests/unit/test_consent.py::test_the_notice_version_is_immutable`
went red on SQLite and stayed green on PostgreSQL, where
`ALTER TABLE … DROP/ADD CONSTRAINT` leaves triggers alone.

So for one migration, on one engine, `notice_versions` was an ordinary mutable
table while the contract said *"Trigger blocks all UPDATE and DELETE"* and
`COMPLIANCE.md` §8.1 rested *"we can show what a user agreed to on a given
date"* on it.

**The general hazard, which is bigger than this migration.** On SQLite **any**
future `AlterField`, constraint change or column rename on a trigger-protected
table silently removes its guard — and that covers every append-only guarantee
in the system: `audit_log`, `gate_authorisations`, `campuses`, `consents`,
`age_verification_events`, `notice_versions`. A migration can be reviewed by two
agents, applied cleanly, and leave a tamper-evidence guarantee switched off,
with the only symptom being a test that nobody wrote.

**So the fix is two things, and the second is the one that matters.** This
migration restores the triggers; `tests/unit/test_append_only_triggers_exist.py`
asserts on **both engines** that every table claiming append-only actually has
its guard installed, so the next table rebuild fails the build instead of
quietly removing the guarantee. Recorded in `ENGINE-DIVERGENCE.md` §12 and
raised in the slice note, because the next person to widen an enum needs to
know, not to rediscover.

`DROP TRIGGER IF EXISTS` first, so this is idempotent and safe to re-run on a
database where the triggers survived.
"""

from importlib import import_module

from django.db import migrations

#: Imported from the migration that defines them, never retyped
#: (`CLAUDE.md` rule 10) — a second hand-made list of the append-only tables is
#: how one of them gets left out of a restore. A numeric-leading module name is
#: not a valid identifier, so it has to come through `import_module`.
APPEND_ONLY_TABLES = import_module(
    "apps.accounts.migrations.0002_append_only_guards"
).APPEND_ONLY_TABLES

SQLITE_FORWARD = [
    statement
    for table in APPEND_ONLY_TABLES
    for op in ("UPDATE", "DELETE")
    for statement in (
        f"DROP TRIGGER IF EXISTS {table}_no_{op.lower()};",
        f"""
        CREATE TRIGGER {table}_no_{op.lower()} BEFORE {op} ON {table}
        BEGIN
          SELECT RAISE(ABORT,
            '{table} is append-only (DATA-MODEL.md section 2): {op} is not permitted. A correction is a new row, never a rewrite.');
        END;
        """,
    )
]

SQLITE_REVERSE = [
    f"DROP TRIGGER IF EXISTS {table}_no_{op.lower()};"
    for table in APPEND_ONLY_TABLES
    for op in ("UPDATE", "DELETE")
]


def apply(apps, schema_editor):
    """PostgreSQL needs nothing: `ALTER TABLE … ADD CONSTRAINT` does not touch
    triggers there, which is exactly why this defect was invisible on the engine
    production runs on."""
    if schema_editor.connection.vendor != "sqlite":
        return
    for statement in SQLITE_FORWARD:
        schema_editor.execute(statement, None)


def reverse(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        return
    for statement in SQLITE_REVERSE:
        schema_editor.execute(statement, None)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_remove_noticeversion_notice_kind_chk_and_more")]

    operations = [migrations.RunPython(apply, reverse)]
