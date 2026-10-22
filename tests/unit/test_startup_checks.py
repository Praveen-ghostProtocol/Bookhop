"""The app refuses to serve against a half-migrated database.

**Written because it happened, in a browser, on the first POST a student
makes.** `no such table: rate_limit_counters`: the dev database was two
migrations behind, `runserver` defaults to SQLite, and every verified run had
been on PostgreSQL — so **1,017 green tests sat beside an application that was
broken on its first form submission.**

Django's `runserver` already prints *"You have N unapplied migration(s)"* and
**starts anyway**, three lines above the URL a developer clicks. An `Error`
does not start.
"""

import pytest

from apps.core.checks import MIGRATION_COMMANDS, unapplied_migrations

pytestmark = pytest.mark.django_db


def test_a_fully_migrated_database_passes():
    """The test database is migrated by pytest-django, so the check must be
    silent here — otherwise it would be an error on every command forever,
    which is how a check gets deleted."""
    assert unapplied_migrations(None) == []


def test_an_unapplied_migration_is_an_error_naming_the_command(monkeypatch):
    """The failure case, with the plan faked rather than the database
    un-migrated: rolling a real migration back inside a test would leave the
    schema wrong for every later test in the session."""
    from django.db.migrations.executor import MigrationExecutor

    class _Pending:
        app_label = "core"
        name = "0009_something"

    monkeypatch.setattr(
        MigrationExecutor, "migration_plan", lambda self, targets: [(_Pending(), False)]
    )
    monkeypatch.setattr("sys.argv", ["manage.py", "runserver"])

    errors = unapplied_migrations(None)
    assert len(errors) == 1
    assert errors[0].id == "bookhop.E001"
    assert "core.0009_something" in errors[0].msg
    assert "manage.py migrate" in errors[0].hint
    assert "sqlite" in errors[0].hint, (
        "the hint must name the engine split; a developer and CI looking at two "
        "different databases is how this defect happened"
    )


def test_the_check_does_not_block_the_command_that_fixes_it(monkeypatch):
    """**The deadlock this would otherwise create.** A check that errors on an
    unmigrated database and also runs for `migrate` makes that database
    unrecoverable."""
    from django.db.migrations.executor import MigrationExecutor

    class _Pending:
        app_label = "core"
        name = "0009_something"

    monkeypatch.setattr(
        MigrationExecutor, "migration_plan", lambda self, targets: [(_Pending(), False)]
    )
    for command in ("migrate", "makemigrations", "showmigrations"):
        monkeypatch.setattr("sys.argv", ["manage.py", command])
        assert unapplied_migrations(None) == [], f"the check blocks `{command}`"
    assert "migrate" in MIGRATION_COMMANDS


def test_an_unreachable_database_is_not_reported_as_a_migration_fault(monkeypatch):
    """Reporting a connection failure here would send a developer to the wrong
    fix. Nothing can be concluded about migrations against a database we cannot
    read, so the check is silent and the real error surfaces on its own."""
    from django.db.migrations.executor import MigrationExecutor

    def _boom(self, connection):
        raise OSError("connection refused")

    monkeypatch.setattr(MigrationExecutor, "__init__", _boom)
    monkeypatch.setattr("sys.argv", ["manage.py", "runserver"])
    assert unapplied_migrations(None) == []


def test_the_check_is_registered_and_not_database_tagged():
    """It must run for `runserver`, which **skips** database-tagged checks — so
    tagging it `Tags.database` would have made it absent from the exact
    situation it was written for."""
    from django.core.checks import Tags, registry

    registered = {check.__name__ for check in registry.registry.get_checks()}
    assert "unapplied_migrations" in registered
    assert Tags.database not in getattr(unapplied_migrations, "tags", []), (
        "the check is database-tagged, so `runserver` will skip it — which is "
        "the one command it exists for"
    )
