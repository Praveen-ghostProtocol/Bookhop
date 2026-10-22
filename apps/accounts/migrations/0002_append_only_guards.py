"""Append-only enforcement for the three S1 tables that claim it.

DATA-MODEL §2 marks `age_verification_events` and `consents` **append-only**,
and `notice_versions` **immutable** with *"Trigger blocks all UPDATE and
DELETE"* written into the contract. Migration core/0002 makes the same argument
for `audit_log` and it applies unchanged here: a service-layer rule would not
satisfy any of the three, because

  * `consents` is *the record that the deletion itself was lawful*
    (`COMPLIANCE.md` §7 row 18), so it has to resist the application as well as
    the user — `Consent.objects.filter(...).update(withdrawn_at=now())` is the
    bypass, and it is the *obvious* thing to write;
  * `age_verification_events` is the whole audit trail for "this account was
    checked to be an adult" with **no DOB behind it**, so if the row can be
    rewritten there is nothing else to fall back on;
  * `notice_versions` carries *"we can show what a user agreed to on a given
    date"* (§8.1), which is false the moment a published notice can be edited.
    A correction is a new version.

**One plpgsql body, not three.** `TG_TABLE_NAME` and `TG_OP` put the table and
the operation in the message, so the three tables share
`bookhop_append_only_guard()` and the count of security-relevant plpgsql bodies
goes from five to six rather than to eight. TRUNCATE reuses migration 0003's
`bookhop_truncate_guard()` and therefore inherits the one declared test-harness
escape, which is what keeps `transactional_db` teardown working
(ENGINE-DIVERGENCE §7.1).

Both engines, as 0002/0003/0005 already do. `tests/unit/test_append_only_s1.py`
asserts the message on both and
`tests/unit/test_plpgsql_refusal_sqlstate.py` asserts the SQLSTATE on
PostgreSQL, skipping on SQLite with the engine named.
"""

from django.db import migrations

#: The tables this migration protects. One list, read by both engine paths and
#: by the reverse, so a table cannot be added to one and forgotten in another.
APPEND_ONLY_TABLES = ("age_verification_events", "consents", "notice_versions")

PG_FORWARD = """
CREATE OR REPLACE FUNCTION bookhop_append_only_guard() RETURNS trigger AS $fn$
BEGIN
  RAISE EXCEPTION
    '% is append-only (DATA-MODEL.md section 2): % is not permitted. '
    'A correction is a new row, never a rewrite.', TG_TABLE_NAME, TG_OP;
END $fn$ LANGUAGE plpgsql;
""" + "".join(
    f"""
CREATE TRIGGER {table}_append_only
  BEFORE UPDATE OR DELETE ON {table}
  FOR EACH ROW EXECUTE FUNCTION bookhop_append_only_guard();
ALTER TABLE {table} ENABLE ALWAYS TRIGGER {table}_append_only;

CREATE TRIGGER {table}_no_truncate
  BEFORE TRUNCATE ON {table}
  FOR EACH STATEMENT EXECUTE FUNCTION bookhop_truncate_guard();
ALTER TABLE {table} ENABLE ALWAYS TRIGGER {table}_no_truncate;
"""
    for table in APPEND_ONLY_TABLES
)

PG_REVERSE = "".join(
    f"""
DROP TRIGGER IF EXISTS {table}_append_only ON {table};
DROP TRIGGER IF EXISTS {table}_no_truncate ON {table};
"""
    for table in APPEND_ONLY_TABLES
) + "DROP FUNCTION IF EXISTS bookhop_append_only_guard();"

#: SQLite has no TRUNCATE statement at all (measured: a syntax error), so there
#: is nothing to block there — the UPDATE and DELETE guards are the whole of
#: what this engine can express, and ENGINE-DIVERGENCE §11 says so rather than
#: leaving the gap to be inferred from the absence of a statement.
SQLITE_FORWARD = [
    f"""
    CREATE TRIGGER {table}_no_{op.lower()} BEFORE {op} ON {table}
    BEGIN
      SELECT RAISE(ABORT,
        '{table} is append-only (DATA-MODEL.md section 2): {op} is not permitted. A correction is a new row, never a rewrite.');
    END;
    """
    for table in APPEND_ONLY_TABLES
    for op in ("UPDATE", "DELETE")
]

SQLITE_REVERSE = [
    f"DROP TRIGGER IF EXISTS {table}_no_{op.lower()};"
    for table in APPEND_ONLY_TABLES
    for op in ("UPDATE", "DELETE")
]


def _run(statements_pg, statements_sqlite):
    def apply(apps, schema_editor):
        vendor = schema_editor.connection.vendor
        if vendor == "postgresql":
            # params=None: see the note in core/0002. `% is append-only ... %`
            # needs two literal `%` to reach plpgsql, and psycopg's placeholder
            # parser would otherwise read the first as an incomplete
            # placeholder and kill `migrate` from empty (ENGINE-DIVERGENCE §1).
            schema_editor.execute(statements_pg, None)
        elif vendor == "sqlite":
            for statement in statements_sqlite:
                schema_editor.execute(statement, None)
        else:
            raise RuntimeError(
                f"the S1 append-only guards are not written for {vendor!r}; "
                "ADR-001 §2.2 permits postgresql (production) and sqlite (local dev) only"
            )

    return apply


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        # bookhop_truncate_guard() is defined there and is reused rather than
        # redefined, so this migration must not run before it exists.
        ("core", "0003_gate_column_write_guard"),
    ]

    operations = [
        migrations.RunPython(_run(PG_FORWARD, SQLITE_FORWARD), _run(PG_REVERSE, SQLITE_REVERSE)),
    ]
