"""ADR-002 §2 — a test that cannot be argued with.

Walks every model ADR-002 lists as tenant-scoped, and for each one that exists
asserts `campus_id` and `city_id` are both NOT NULL and that there is an index
leading with `campus_id`. A new tenant table without the keys fails CI.

Models for slices that have not been built yet are reported as pending, not
silently passed: `test_pending_models_are_only_future_slices` fails if this
list ever goes stale in the other direction (a model exists under a different
name and nothing is checking it).

# ponytail: structural test rather than row-level security. Ceiling: it proves
# the columns exist and are indexed, not that every query filters. Upgrade
# path: Postgres RLS (ADR-002 §6 step 2).
"""

import pytest
from django.apps import apps as django_apps

from apps.core.scoping import TENANT_SCOPED_MODELS


def _existing():
    for app_label, model_name, slice_name in TENANT_SCOPED_MODELS:
        try:
            yield django_apps.get_model(app_label, model_name), slice_name
        except LookupError:
            continue


def keys_verdict(has_campus, campus_null, has_city, city_null):
    """The predicate ADR-002 §2 asks for, separated from the models so it can be
    tested on inputs rather than only on whatever happens to exist.

    Returns a list of problems; empty means the model is correctly keyed.
    """
    problems = []
    if not has_campus:
        problems.append("no campus_id")
    elif campus_null:
        problems.append("campus_id is nullable")
    if not has_city:
        problems.append("no city_id")
    elif city_null:
        problems.append("city_id is nullable")
    return problems


@pytest.mark.parametrize(
    "args,expected_problem_count",
    [
        ((True, False, True, False), 0),   # correctly keyed
        ((True, True, True, False), 1),    # nullable campus_id
        ((True, False, True, True), 1),    # nullable city_id
        ((False, False, True, False), 1),  # campus_id missing entirely
        ((False, False, False, False), 2), # neither key
        ((True, True, False, False), 2),
    ],
)
def test_the_key_check_itself_rejects_a_badly_keyed_model(args, expected_problem_count):
    """The checker's own test.

    The previous version of the file iterated the tenant models — of which S0
    has **none**, because `cities` and `campuses` are the tenant registry rather
    than tenant data — and closed with `assert checked >= 0`, which is true for
    every input. Both REVIEW-S0 N8 and QA-S0 §7 named it. Testing the predicate
    on inputs means this file says something today instead of in S1.
    """
    assert len(keys_verdict(*args)) == expected_problem_count


def test_every_tenant_scoped_model_that_exists_has_both_keys_not_null():
    """The live half. It iterates zero models today and that is correct — the
    predicate above is what carries the assertion until S1, and
    `test_pending_tenant_model_is_reported` prints exactly which models are not
    yet built so "green" never reads as "all tenant tables checked"."""
    for model, _slice in _existing():
        fields = {f.name: f for f in model._meta.get_fields() if hasattr(f, "null")}
        problems = keys_verdict(
            "campus" in fields, bool(getattr(fields.get("campus"), "null", False)),
            "city" in fields, bool(getattr(fields.get("city"), "null", False)),
        )
        assert problems == [], (
            f"ADR-002 §2: {model._meta.db_table} — {problems}. Both keys must be "
            "NOT NULL; retrofitting a tenant key is a migration across the whole "
            "database plus a rewrite of every metric."
        )


def test_every_tenant_scoped_model_has_an_index_leading_with_campus_id():
    for model, _ in _existing():
        leading = set()
        for index in model._meta.indexes:
            leading.add(index.fields[0].lstrip("-"))
        for constraint in model._meta.constraints:
            fields = getattr(constraint, "fields", None)
            if fields:
                leading.add(fields[0].lstrip("-"))
        # A FK declared with db_index=True (Django's default) already produces
        # an index on campus_id alone, which leads with campus_id.
        if any(f.name == "campus" and f.db_index for f in model._meta.fields):
            leading.add("campus")
        assert "campus" in leading or "campus_id" in leading, (
            f"ADR-002 §2: {model._meta.db_table} needs an index leading with campus_id"
        )


def test_registry_lists_no_model_that_exists_under_another_name():
    """Guards the list itself.

    Every concrete model in a tenant app that has a `campus` field must appear
    in TENANT_SCOPED_MODELS. Otherwise a future slice could add a scoped table
    that this file never checks.
    """
    registered = {(a, m) for a, m, _ in TENANT_SCOPED_MODELS}
    tenant_apps = {"accounts", "catalog", "listings", "discovery", "transfers",
                   "safety", "support", "notify"}
    for model in django_apps.get_models():
        label = model._meta.app_label
        if label not in tenant_apps:
            continue
        if not any(f.name == "campus" for f in model._meta.fields):
            continue
        assert (label, model.__name__) in registered, (
            f"{label}.{model.__name__} has a campus key but is not in "
            "apps.core.scoping.TENANT_SCOPED_MODELS, so no test checks it"
        )


@pytest.mark.parametrize("app_label,model_name,slice_name", TENANT_SCOPED_MODELS)
def test_pending_tenant_model_is_reported(app_label, model_name, slice_name):
    """Not an assertion about the model — a visible record of what is not yet
    built, so "tests green" never means "every tenant table is checked"."""
    try:
        django_apps.get_model(app_label, model_name)
    except LookupError:
        pytest.skip(f"{app_label}.{model_name} is created in {slice_name}; not built yet")
