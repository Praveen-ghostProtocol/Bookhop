"""Append-only enforcement for `audit_log` and `gate_authorisations`.

DATA-MODEL §8 says `audit_log` is append-only and §1 says
`gate_authorisations` permits no UPDATE except `revoked_at`/`revoked_reason`.
A service-layer rule would not satisfy either: the audit trail has to resist
the application as well as the user, and `GateAuthorisation.objects.update()`
or a careless admin action is exactly the bypass the ADR is guarding against.
So it is a trigger.

Postgres and SQLite both have triggers but share no syntax, so the DDL is
written twice. That is deliberate: it means the property is enforced on the
engine the tests run on **and** on the engine production runs on, and the test
that asserts it is therefore meaningful in both places. The two bodies are
behaviourally compared in company/architecture/ENGINE-DIVERGENCE.md §3.5-§3.7.
"""

from django.db import migrations

PG_FORWARD = """
CREATE OR REPLACE FUNCTION audit_log_is_append_only() RETURNS trigger AS $fn$
BEGIN
  RAISE EXCEPTION
    'audit_log is append-only (DATA-MODEL.md section 8): % is not permitted', TG_OP;
END $fn$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_append_only
  BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION audit_log_is_append_only();

-- Row-level triggers do not fire on TRUNCATE, so without this a Postgres
-- superuser or a test harness could empty the audit trail past the guard
-- above. SQLite has no TRUNCATE statement (measured: it is a syntax error),
-- so there is nothing to block there -- which also means this statement
-- trigger is the one part of the append-only guarantee that CANNOT be
-- exercised on the development machine. ENGINE-DIVERGENCE.md §3.6.
CREATE TRIGGER audit_log_no_truncate
  BEFORE TRUNCATE ON audit_log
  FOR EACH STATEMENT EXECUTE FUNCTION audit_log_is_append_only();

CREATE OR REPLACE FUNCTION gate_authorisations_is_append_only() RETURNS trigger AS $fn$
BEGIN
  IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
    RAISE EXCEPTION
      'gate_authorisations is append-only (DATA-MODEL.md section 1): % is not permitted', TG_OP;
  END IF;
  IF NEW.id                  IS DISTINCT FROM OLD.id
  OR NEW.gate                IS DISTINCT FROM OLD.gate
  OR NEW.scope_type          IS DISTINCT FROM OLD.scope_type
  OR NEW.scope_id            IS DISTINCT FROM OLD.scope_id
  OR NEW.legal_entity_id     IS DISTINCT FROM OLD.legal_entity_id
  OR NEW.evidence            IS DISTINCT FROM OLD.evidence
  OR NEW.authorised_by_human IS DISTINCT FROM OLD.authorised_by_human
  OR NEW.authorised_at       IS DISTINCT FROM OLD.authorised_at THEN
    RAISE EXCEPTION
      'gate_authorisations permits no UPDATE except revoked_at/revoked_reason '
      '(DATA-MODEL.md section 1, ADR-002 section 4.1(b))';
  END IF;
  RETURN NEW;
END $fn$ LANGUAGE plpgsql;

CREATE TRIGGER gate_authorisations_append_only
  BEFORE UPDATE OR DELETE ON gate_authorisations
  FOR EACH ROW EXECUTE FUNCTION gate_authorisations_is_append_only();

CREATE TRIGGER gate_authorisations_no_truncate
  BEFORE TRUNCATE ON gate_authorisations
  FOR EACH STATEMENT EXECUTE FUNCTION gate_authorisations_is_append_only();
"""

PG_REVERSE = """
DROP TRIGGER IF EXISTS audit_log_append_only ON audit_log;
DROP TRIGGER IF EXISTS audit_log_no_truncate ON audit_log;
DROP FUNCTION IF EXISTS audit_log_is_append_only();
DROP TRIGGER IF EXISTS gate_authorisations_append_only ON gate_authorisations;
DROP TRIGGER IF EXISTS gate_authorisations_no_truncate ON gate_authorisations;
DROP FUNCTION IF EXISTS gate_authorisations_is_append_only();
"""

SQLITE_FORWARD = [
    """
    CREATE TRIGGER audit_log_no_update BEFORE UPDATE ON audit_log
    BEGIN
      SELECT RAISE(ABORT,
        'audit_log is append-only (DATA-MODEL.md section 8): UPDATE is not permitted');
    END;
    """,
    """
    CREATE TRIGGER audit_log_no_delete BEFORE DELETE ON audit_log
    BEGIN
      SELECT RAISE(ABORT,
        'audit_log is append-only (DATA-MODEL.md section 8): DELETE is not permitted');
    END;
    """,
    """
    CREATE TRIGGER gate_authorisations_no_delete BEFORE DELETE ON gate_authorisations
    BEGIN
      SELECT RAISE(ABORT,
        'gate_authorisations is append-only (DATA-MODEL.md section 1): DELETE is not permitted');
    END;
    """,
    """
    CREATE TRIGGER gate_authorisations_no_update BEFORE UPDATE ON gate_authorisations
    WHEN NEW.id                  IS NOT OLD.id
      OR NEW.gate                IS NOT OLD.gate
      OR NEW.scope_type          IS NOT OLD.scope_type
      OR NEW.scope_id            IS NOT OLD.scope_id
      OR NEW.legal_entity_id     IS NOT OLD.legal_entity_id
      OR NEW.evidence            IS NOT OLD.evidence
      OR NEW.authorised_by_human IS NOT OLD.authorised_by_human
      OR NEW.authorised_at       IS NOT OLD.authorised_at
    BEGIN
      SELECT RAISE(ABORT,
        'gate_authorisations permits no UPDATE except revoked_at/revoked_reason (DATA-MODEL.md section 1, ADR-002 section 4.1(b))');
    END;
    """,
]

SQLITE_REVERSE = [
    "DROP TRIGGER IF EXISTS audit_log_no_update;",
    "DROP TRIGGER IF EXISTS audit_log_no_delete;",
    "DROP TRIGGER IF EXISTS gate_authorisations_no_delete;",
    "DROP TRIGGER IF EXISTS gate_authorisations_no_update;",
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
                f"append-only triggers are not written for {vendor!r}; "
                "ADR-001 §2.2 permits postgresql (production) and sqlite (local dev) only"
            )

    return apply


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.RunPython(
            _run(PG_FORWARD, SQLITE_FORWARD),
            _run(PG_REVERSE, SQLITE_REVERSE),
        ),
    ]
