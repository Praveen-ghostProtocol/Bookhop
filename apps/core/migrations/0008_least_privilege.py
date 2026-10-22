"""Least privilege on the two tables the whole compliance position rests on.

**RED TEAM ENGINEERING-MEMO §1 (CRITICAL) and §3 (MATERIAL), and they are one
root cause.** Measured on PostgreSQL 16.15: three ORM statements opened the
discovery gate on a campus whose legal entity had no CIN and no INC-20A, under
an authorisation granted against a *different* legal entity, with every evidence
value the literal string `"x"`, and **zero `audit_log` rows written**. Separately
the application role could declare the harness escape GUC for its own session
and then `TRUNCATE audit_log` — two statements.

Both work for the same reason: **`bookhop` holds INSERT, UPDATE, DELETE and
TRUNCATE on `audit_log` and `gate_authorisations`.** The triggers are the only
barrier and the role is permitted to walk around them. `CLAUDE.md` rule 14 asks
for two *independent* layers; the gate had one layer twice, because the trigger
and the command both run as the same role.

So this migration moves the control from a trigger to a privilege:

    REVOKE INSERT, UPDATE, TRUNCATE ON gate_authorisations FROM <app role>
    REVOKE TRUNCATE                 ON audit_log           FROM <app role>

`SELECT` stays on both — every read path needs it. `INSERT` stays on `audit_log`,
because `record_audit` runs as the app role on every mutation and an audit trail
nothing can append to is worse than no privilege change. `DELETE` and `UPDATE`
on `audit_log` are already refused by the trigger in migration 0002 and are left
to it; this adds the TRUNCATE that the trigger's own escape hatch opened.

The escape GUC is deliberately **not spelled out here**: `tests/contract/
test_migration_guards.py` inventories every application file that *writes* it,
and a docstring quoting the statement verbatim is indistinguishable from a
second declarer to any grep that is not itself an SQL parser. `CLAUDE.md`
rule 13's first resort — the prose is ours to reword, the control is not ours
to loosen.

---

## The ceiling, measured rather than assumed — and it is the reason this is not
## the whole fix

**`bookhop` OWNS both tables** (`pg_tables.tableowner = 'bookhop'`, measured).
A revoke against a table's owner *does* take effect — measured:
`has_table_privilege` returns false afterwards and `TRUNCATE` is refused with
*"permission denied for table audit_log"* — **but the owner can grant it
straight back to itself in one statement**, also measured:

    GRANT TRUNCATE ON audit_log TO bookhop;   -- has_table_privilege -> true

So what this migration buys, honestly:

| Threat | Closed by this migration? |
|---|---|
| An ORM `update()` / `create()` from any service function, job or admin form | **Yes.** The database refuses it |
| Django's `sql_flush` reaching `audit_log` in a deploy or a careless command | **Yes** |
| A replication apply worker or a restore path | **Yes**, with `ENABLE ALWAYS` from 0003 |
| **A deliberate actor holding the application role** | **No.** It owns the tables and can re-grant |

**The last row is closed only by moving ownership off the application role**,
which is a deployment act and not a migration: a `bookhop_owner` role owning the
schema, `bookhop_app` connecting with no DDL and no grant option, and a third
`bookhop_gate` role that `open_discovery` assumes. That is `INFRA.md`'s and
platform-sre's, it needs a superuser this box does not have (`rolsuper = false`,
measured), and it is escalated with its cost in the S1 slice note rather than
half-built here.

---

## What this breaks in the test harness, deliberately

Every test that creates a `gate_authorisations` row through the ORM — the gate
tests, the SQLSTATE tests, QA's contract tests — is now refused by the database,
which is the control working. `tests/conftest.py` re-grants for the test session
and says why in one place. **That re-grant is only possible because the test
role owns the tables, i.e. it is the measured ceiling above being used
deliberately in a harness**; a production app role could not do it.
"""

from django.db import migrations

#: `audit_log` keeps INSERT (every mutation appends one) and SELECT.
#: `gate_authorisations` keeps SELECT and DELETE — DELETE because the trigger in
#: 0002 already refuses it with a message that names the contract, and a
#: privilege error there would replace a diagnostic refusal with
#: "permission denied", which is a worse answer to the same question.
REVOCATIONS = (
    ("gate_authorisations", "INSERT, UPDATE, TRUNCATE"),
    ("audit_log", "TRUNCATE"),
)


def _app_role(schema_editor):
    """The role the application connects as — `current_user`, not a setting.

    Reading it from the connection rather than from `DATABASES["USER"]` is the
    difference between revoking from the role that is actually connected and
    revoking from the role someone wrote in a config file. They differ whenever
    a connection string, a pgbouncer user or a `SET ROLE` is in play.
    """
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        return cursor.fetchone()[0]


def revoke(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        # SQLite has no role system at all — no GRANT, no REVOKE, one process
        # with full access to the file. There is no weaker version of this
        # control to apply, so it is absent rather than approximated, and
        # ENGINE-DIVERGENCE §12 records that the privilege layer is a
        # PostgreSQL-only control with no SQLite equivalent.
        return
    role = _app_role(schema_editor)
    with schema_editor.connection.cursor() as cursor:
        for table, privileges in REVOCATIONS:
            cursor.execute(f'REVOKE {privileges} ON {table} FROM "{role}"')


def restore(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    role = _app_role(schema_editor)
    with schema_editor.connection.cursor() as cursor:
        for table, privileges in REVOCATIONS:
            cursor.execute(f'GRANT {privileges} ON {table} TO "{role}"')


class Migration(migrations.Migration):
    dependencies = [("core", "0007_ratelimitcounter")]

    operations = [migrations.RunPython(revoke, restore)]
