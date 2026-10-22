"""Is the test database the one these migrations describe?

**QA-S1 F20, instrumented.** A reused test database silently goes stale the
moment a migration lands, and the failures it produces land **nowhere near the
cause**: QA measured 0, 1, 4, 13 and 14 failures across five consecutive runs
of an unchanged tree, concentrated on audit-chain tests, because
`transactional_db` teardown flushed a table the stale database did not have
(`relation "rate_limit_counters" does not exist`), left rows behind, and the
next test that read the chain broke. Nothing in that sequence mentions
migrations.

The fix is one flag — `--create-db` — and the problem is that nobody knows to
reach for it, because the symptom names an audit test. So this file makes the
cause say its own name: **one named failure here instead of a scatter of
failures elsewhere.**

It is in QA's tree because it is a property of the harness both trees depend
on, and because QA is the agent that lost five runs to it.
"""

import pytest
from django.db import connection

pytestmark = pytest.mark.django_db

ADVICE = (
    "The test database is older than the migrations in this working tree. "
    "Re-create it:\n\n"
    "    .venv/Scripts/python.exe -m pytest --create-db\n\n"
    "Why this matters more than it looks (QA-S1 F20): a stale test database "
    "does not fail where it is stale. `transactional_db` teardown flushes "
    "every table, hits one the database does not have, and leaves rows "
    "committed — so the failures surface on whichever test next reads global "
    "state, which in this schema is the audit chain, because it is one linked "
    "list across the whole table. QA measured 0, 1, 4, 13 and 14 failures "
    "across five runs of an unchanged tree before locating this."
)


def test_no_migration_is_unapplied_in_the_test_database():
    """The direct question, asked the way `/readyz` asks it.

    A reused test database is not re-migrated, so `django_migrations` lags the
    tree and the plan is non-empty. That is the whole of the detection, and it
    is cheap enough to run every time.
    """
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    pending = [f"{migration.app_label}.{migration.name}" for migration, _backwards in plan]
    assert pending == [], f"{len(pending)} unapplied migration(s): {pending}\n\n{ADVICE}"


def test_every_model_has_its_table():
    """The second shape of staleness, which the migration plan does not catch:
    a database whose `django_migrations` says it is current while a table is
    missing — a half-applied migration, or a table dropped by hand during a
    debugging session.

    Checked through `connection.introspection`, so it reports what the server
    actually has rather than what the migration state claims.
    """
    from django.apps import apps as django_apps

    with connection.cursor() as cursor:
        existing = {name.lower() for name in connection.introspection.table_names(cursor)}

    missing = sorted(
        model._meta.db_table
        for model in django_apps.get_models()
        if model._meta.managed and model._meta.db_table.lower() not in existing
    )
    assert missing == [], f"tables missing from the test database: {missing}\n\n{ADVICE}"


def test_the_tables_transactional_teardown_will_flush_all_exist():
    """The specific failure F20 actually produced, asserted directly.

    Django's `sql_flush` enumerates **every** table in the database, so a
    `transactional_db` test tears down by flushing tables no test touched —
    which is why a missing `rate_limit_counters` broke audit-chain tests in a
    different file. Asserting that the flush statement can be built is the
    closest thing to a dry run of the teardown that broke.
    """
    with connection.cursor() as cursor:
        tables = connection.introspection.django_table_names(
            only_existing=False, include_views=False
        )
        existing = {name.lower() for name in connection.introspection.table_names(cursor)}

    missing = sorted(name for name in tables if name.lower() not in existing)
    assert missing == [], (
        "`transactional_db` teardown will flush these tables and they do not "
        f"exist, so the flush will error and leave rows committed: {missing}"
        f"\n\n{ADVICE}"
    )


def test_this_detector_runs_before_the_tests_it_protects():
    """A detector that runs last is a post-mortem.

    pytest collects files in directory order, so `tests/contract/` runs before
    `tests/e2e/` and `tests/unit/` runs before both — which means this cannot
    be guaranteed to run first and is not relied on to. What it does guarantee
    is that when the scatter happens, **one of the failures names the cause**,
    and this one is findable by searching the output for the advice text.

    Asserted so the advice is not silently reworded into something unsearchable.
    """
    assert "--create-db" in ADVICE
    assert "QA-S1 F20" in ADVICE
