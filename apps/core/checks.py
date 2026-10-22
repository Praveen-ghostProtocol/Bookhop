"""Startup checks — the app refuses to serve against a half-migrated database.

**Written because it happened.** The first browser walk of S1 hit
`no such table: rate_limit_counters` as a **500 on the first POST a student
makes**: the development database had not been migrated past `core/0007`,
`runserver` defaults to SQLite, and every verified run had been on PostgreSQL.
**1,017 tests were green while the application a person touches was broken on
its first form submission.**

The shape is worth naming, because it is the same one twice: QA found a stale
**test** database producing a spread of 0–14 failures on an unchanged tree, and
this is a stale **dev** database. In both cases the schema and the code
disagreed and nothing said so; the difference is only which database it was.

`runserver` already calls Django's own `check_migrations()`, which prints
*"You have N unapplied migration(s)"* and **starts the server anyway**. That
warning is three lines above the URL a developer clicks, so it is read exactly
once. An `Error` is not: `manage.py check`, `runserver` and every management
command that runs system checks refuse until it is resolved, and the message
carries the command to run.

**Why it is an `Error` and not a `Warning`:** a server that serves pages and
500s on the first write is strictly worse than one that does not start. The
failure is deferred to a student, surfaces as a stack trace, and points at the
wrong thing — the missing table, not the unapplied migration.
"""

import sys

from django.core.checks import Error, register

#: Commands that legitimately run against an unmigrated database. `migrate` is
#: the obvious one and the deadlock this list exists to prevent — a check that
#: blocked `migrate` would make an unmigrated database unrecoverable.
#:
#: Read from `sys.argv` rather than hooked per command, because a check has no
#: other way to know its caller. Approximate by design, and the approximation
#: is safe in one direction: a false *skip* loses the check for that one
#: command, while a false *fire* would wedge the project.
MIGRATION_COMMANDS = frozenset({
    "migrate", "makemigrations", "showmigrations", "sqlmigrate", "squashmigrations",
    "createcachetable", "flush", "test", "collectstatic", "shell", "dbshell",
})


def _running_a_migration_command():
    return any(arg in MIGRATION_COMMANDS for arg in sys.argv[1:])


@register()
def unapplied_migrations(app_configs, **kwargs):
    """`bookhop.E001` — the schema and the code disagree.

    Deliberately **not** tagged `Tags.database`: database-tagged checks are
    skipped by commands that do not declare them, and `runserver` is one of
    them — which would have made this check absent from the exact situation it
    was written for.
    """
    if _running_a_migration_command():
        return []

    from django.db import DEFAULT_DB_ALIAS, connections
    from django.db.migrations.executor import MigrationExecutor

    connection = connections[DEFAULT_DB_ALIAS]
    try:
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    except Exception:
        # An unreachable database is a different problem with its own,
        # clearer, error — and reporting it here as a migration fault would
        # send a developer to the wrong fix. Silence is correct: nothing can
        # be concluded about migrations against a database we cannot read.
        return []

    if not plan:
        return []

    pending = ", ".join(f"{migration.app_label}.{migration.name}" for migration, _ in plan)
    return [
        Error(
            f"{len(plan)} unapplied migration(s) on the {connection.vendor!r} database "
            f"{connection.settings_dict.get('NAME')!r}: {pending}",
            hint=(
                "Run `python manage.py migrate`.\n"
                "The server is refused rather than started because the first write to "
                "a missing table is a 500 on a student's first form submission, not a "
                "startup failure a developer sees — which is exactly how this was "
                "found. Note that `bookhop.settings.dev` defaults to "
                "BOOKHOP_DB_ENGINE=sqlite while the suite is verified on PostgreSQL, "
                "so a developer and CI can be looking at two different databases: "
                "check which one this is before migrating."
            ),
            id="bookhop.E001",
        )
    ]
