"""M0 — `campuses.discovery_enabled_at` gets a database write guard.

ADR-002 §4.1(b): *"Discovery cannot be opened by `UPDATE campuses SET
discovery_enabled_at = now()`. It is opened by `manage.py open_discovery`,
which refuses unless…"* Before this migration that sentence was false: the
column was an ordinary nullable timestamp, a plain `Campus.objects.update()`
opened the gate on a campus with no authorisation row and no legal entity, and
no `audit_log` row was written. Found by test-qa (QA-S0 F3) and confirmed by
code-review (REVIEW-S0 M0).

The rule, enforced for every writer including the application's own ORM:

  * **INSERT** must leave `discovery_enabled_at` NULL. A new campus is closed;
    that is ADR-002 §4.1(a)'s "closed unless someone deliberately opened it",
    and it removes any question about what `NEW.id` means in a BEFORE INSERT
    trigger.
  * **Closing** — setting it to NULL — is always permitted. `close_discovery`
    must never be the thing that fails, and a campus that cannot be closed is a
    worse failure than one that was opened carelessly.
  * **Opening** requires a live Gate C authorisation for *that* campus:
    `gate = 'C'`, `scope_type = 'CAMPUS'`, `scope_id = NEW.id`,
    `revoked_at IS NULL`. The command's evidence checklist is unchanged and
    still runs; this is the floor beneath it.
  * **Opening an inactive campus is refused** (QA-S0 B1). No document says
    deactivating a campus closes discovery, which is a specification silence
    routed to cto — but "an `active = false` campus may not be *opened*" is
    free here and closes the half of B1 that a trigger can reach. The read
    path is closed in `assert_discovery_open`.

Written for both engines, as 0002 already does twice. The SQLite half is what
the test suite exercises; the Postgres half is unexecuted text on this machine
(ENGINE-DIVERGENCE §1).

This migration also **corrects M5** for Postgres: the TRUNCATE guards added in
0002 collide with Django's own `sql_flush`, which emits TRUNCATE on Postgres,
so every `transactional_db` teardown would error on the first Postgres box —
landing on S4's double-booking test, the one thing ENGINE-DIVERGENCE §5 calls
the most important correctness property in the system. The guards are
redefined to accept one declared escape, a session setting the harness sets
and nothing else does. 0002 is left untouched so an already-migrated database
moves forward rather than needing a rebuild.
"""

from django.db import migrations

CAMPUS_GUARD_MESSAGE = (
    "ADR-002 4.1(b): campuses.discovery_enabled_at may only be set while a live "
    "gate_authorisations row (gate=C, scope_type=CAMPUS, not revoked) exists for "
    "this campus, and the campus is active. Use: manage.py open_discovery "
    "--campus <slug>. Setting it to NULL (closing) is always allowed."
)

PG_FORWARD = f"""
CREATE OR REPLACE FUNCTION campuses_gate_is_authorised() RETURNS trigger AS $fn$
BEGIN
  IF TG_OP = 'INSERT' THEN
    IF NEW.discovery_enabled_at IS NOT NULL THEN
      RAISE EXCEPTION
        'ADR-002 4.1(a): a new campus is created closed. Insert with '
        'discovery_enabled_at NULL and open it with manage.py open_discovery.';
    END IF;
    RETURN NEW;
  END IF;

  IF NEW.discovery_enabled_at IS NOT DISTINCT FROM OLD.discovery_enabled_at THEN
    RETURN NEW;                                  -- not a gate change
  END IF;

  IF NEW.discovery_enabled_at IS NULL THEN
    RETURN NEW;                                  -- closing is always permitted
  END IF;

  IF NOT NEW.active THEN
    RAISE EXCEPTION '{CAMPUS_GUARD_MESSAGE}';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM gate_authorisations
     WHERE gate = 'C' AND scope_type = 'CAMPUS'
       AND scope_id = NEW.id AND revoked_at IS NULL
  ) THEN
    RAISE EXCEPTION '{CAMPUS_GUARD_MESSAGE}';
  END IF;

  RETURN NEW;
END $fn$ LANGUAGE plpgsql;

CREATE TRIGGER campuses_gate_authorised
  BEFORE INSERT OR UPDATE ON campuses
  FOR EACH ROW EXECUTE FUNCTION campuses_gate_is_authorised();

-- N7: the default enable state is bypassed by `SET session_replication_role =
-- 'replica'`, which is also what a logical-replication apply worker and some
-- restore paths use. ENABLE ALWAYS costs one line per trigger.
ALTER TABLE campuses ENABLE ALWAYS TRIGGER campuses_gate_authorised;
ALTER TABLE audit_log ENABLE ALWAYS TRIGGER audit_log_append_only;
ALTER TABLE gate_authorisations ENABLE ALWAYS TRIGGER gate_authorisations_append_only;

-- M5: give the TRUNCATE guards the one escape a test harness can declare.
-- `current_setting(..., true)` returns NULL when unset, so the default is to
-- raise. UPDATE and DELETE get no escape; only the whole-table flush does,
-- because that is the operation Django's own test teardown needs and a
-- plausible attacker does not need (THREAT-MODEL §4 B5 already accepts direct
-- SQL as out of scope).
CREATE OR REPLACE FUNCTION bookhop_truncate_guard() RETURNS trigger AS $fn$
BEGIN
  IF current_setting('bookhop.allow_flush', true) = 'yes' THEN
    RETURN NULL;
  END IF;
  RAISE EXCEPTION
    '% is append-only: TRUNCATE is not permitted. A test harness that needs to '
    'flush must SET bookhop.allow_flush = ''yes'' for its session '
    '(ENGINE-DIVERGENCE.md section 7.1).', TG_TABLE_NAME;
END $fn$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_log_no_truncate ON audit_log;
CREATE TRIGGER audit_log_no_truncate
  BEFORE TRUNCATE ON audit_log
  FOR EACH STATEMENT EXECUTE FUNCTION bookhop_truncate_guard();
ALTER TABLE audit_log ENABLE ALWAYS TRIGGER audit_log_no_truncate;

DROP TRIGGER IF EXISTS gate_authorisations_no_truncate ON gate_authorisations;
CREATE TRIGGER gate_authorisations_no_truncate
  BEFORE TRUNCATE ON gate_authorisations
  FOR EACH STATEMENT EXECUTE FUNCTION bookhop_truncate_guard();
ALTER TABLE gate_authorisations ENABLE ALWAYS TRIGGER gate_authorisations_no_truncate;
"""

PG_REVERSE = """
DROP TRIGGER IF EXISTS campuses_gate_authorised ON campuses;
DROP FUNCTION IF EXISTS campuses_gate_is_authorised();
DROP TRIGGER IF EXISTS audit_log_no_truncate ON audit_log;
DROP TRIGGER IF EXISTS gate_authorisations_no_truncate ON gate_authorisations;
DROP FUNCTION IF EXISTS bookhop_truncate_guard();
CREATE TRIGGER audit_log_no_truncate
  BEFORE TRUNCATE ON audit_log
  FOR EACH STATEMENT EXECUTE FUNCTION audit_log_is_append_only();
CREATE TRIGGER gate_authorisations_no_truncate
  BEFORE TRUNCATE ON gate_authorisations
  FOR EACH STATEMENT EXECUTE FUNCTION gate_authorisations_is_append_only();
"""

_LIVE_AUTH = (
    "SELECT 1 FROM gate_authorisations "
    "WHERE gate = 'C' AND scope_type = 'CAMPUS' "
    "AND scope_id = NEW.id AND revoked_at IS NULL"
)

SQLITE_FORWARD = [
    f"""
    CREATE TRIGGER campuses_gate_closed_on_insert BEFORE INSERT ON campuses
    WHEN NEW.discovery_enabled_at IS NOT NULL
    BEGIN
      SELECT RAISE(ABORT, 'ADR-002 4.1(a): a new campus is created closed. Insert with discovery_enabled_at NULL and open it with manage.py open_discovery.');
    END;
    """,
    f"""
    CREATE TRIGGER campuses_gate_authorised BEFORE UPDATE ON campuses
    WHEN NEW.discovery_enabled_at IS NOT OLD.discovery_enabled_at
     AND NEW.discovery_enabled_at IS NOT NULL
     AND (NEW.active = 0 OR NOT EXISTS ({_LIVE_AUTH}))
    BEGIN
      SELECT RAISE(ABORT, '{CAMPUS_GUARD_MESSAGE}');
    END;
    """,
]

SQLITE_REVERSE = [
    "DROP TRIGGER IF EXISTS campuses_gate_closed_on_insert;",
    "DROP TRIGGER IF EXISTS campuses_gate_authorised;",
]


def _run(statements_pg, statements_sqlite):
    def apply(apps, schema_editor):
        vendor = schema_editor.connection.vendor
        if vendor == "postgresql":
            schema_editor.execute(statements_pg)
        elif vendor == "sqlite":
            for statement in statements_sqlite:
                schema_editor.execute(statement)
        else:
            raise RuntimeError(
                f"the gate write guard is not written for {vendor!r}; ADR-001 §2.2 "
                "permits postgresql (production) and sqlite (local dev) only"
            )

    return apply


class Migration(migrations.Migration):
    dependencies = [("core", "0002_append_only_triggers")]

    operations = [
        migrations.RunPython(_run(PG_FORWARD, SQLITE_FORWARD), _run(PG_REVERSE, SQLITE_REVERSE)),
    ]
