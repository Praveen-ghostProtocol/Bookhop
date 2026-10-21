"""Every route into S0, and whether any of them can get past the gate.

The brief for this slice is "a real listing must be unreachable while
`discovery_enabled_at` is NULL, by every route you can find". So this file
enumerates the routes rather than assuming it knows them:

* the HTTP surface, from the live URLconf;
* the management commands, from Django's own command registry;
* the writers of `discovery_enabled_at`, from the source tree;
* the ORM, which has no gate in front of it at all.

Written from ADR-002 §4, API-CONTRACT §5.8 and TASKS §2 S0.
"""

import re
from pathlib import Path

import pytest
from django.core.management import get_commands
from django.urls import get_resolver
from django.utils import timezone

from apps.core.models import AuditLog, Campus

pytestmark = pytest.mark.django_db

REPO = Path(__file__).resolve().parents[2]

#: API-CONTRACT §5.8 and TASKS §2 S0: the whole HTTP surface of this slice.
#: `web.urls` (frontend-developer, S1) is expected to add routes; when it does,
#: every one of them is a discovery read path until proven otherwise and
#: belongs in a gate test of its own.
EXPECTED_S0_ROUTES = {"healthz", "readyz"}


def _http_routes():
    """Every concrete pattern in the live URLconf, as `route` strings."""
    out = []

    def walk(patterns, prefix=""):
        for p in patterns:
            if hasattr(p, "url_patterns"):
                walk(p.url_patterns, prefix + str(p.pattern))
            else:
                out.append(prefix + str(p.pattern))

    walk(get_resolver().url_patterns)
    return set(out)


# --------------------------------------------------------------------------
# 1. the HTTP surface
# --------------------------------------------------------------------------


def test_the_http_surface_is_exactly_the_two_operational_endpoints():
    """A route that appears without a gate test is the gate's most likely
    bypass, so a new route fails this test on purpose.

    If this fails because `web/urls.py` has landed, that is S1's frontend and
    each new route needs: `assert_discovery_open` on every discovery read path
    (ADR-002 §4.1(a)), and a journey test that a real student on a closed campus
    sees no listing data (PRD AC-M6.1).
    """
    routes = _http_routes()
    unexpected = routes - EXPECTED_S0_ROUTES
    assert unexpected == set(), (
        f"routes outside S0's declared surface: {sorted(unexpected)}. Each needs "
        "a gate check and a gate test before it ships (ADR-002 §4.1(a))."
    )


def test_neither_operational_endpoint_leaks_tenant_data(client):
    """API-CONTRACT §5.8 and `apps/core/views.py`'s own rule: no version, no
    detail, nothing to fingerprint. And nothing about a campus — `/readyz` is
    unauthenticated, so anything in it is public."""
    from apps.core.models import City

    Campus.objects.create(
        city=City.objects.create(name="Chennai", state="Tamil Nadu"),
        name="Secret Campus Name",
        slug="secret-campus",
    )
    for path in ("/healthz", "/readyz"):
        body = client.get(path).content.decode()
        assert "Secret Campus Name" not in body
        assert "secret-campus" not in body
        assert "Django" not in body
        assert "Traceback" not in body


def test_healthz_says_nothing_but_ok(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.content.decode().strip() == "ok"


def test_readyz_reports_not_ready_when_a_job_is_overdue(client):
    """API-CONTRACT §5.8: `/readyz` is a readiness gate, so it must be able to
    say no. ENGINE-DIVERGENCE §8 item 5 records that the third check is "no job
    overdue by more than 5 minutes" rather than the contract's "last job run <
    5 min ago"; this asserts the behaviour that was actually built, which is the
    one an S8 load balancer will act on."""
    from datetime import timedelta

    from apps.core.models import Job

    assert client.get("/readyz").status_code == 200
    Job.objects.create(kind="qa.overdue", payload={},
                       run_after=timezone.now() - timedelta(minutes=30))
    r = client.get("/readyz")
    assert r.status_code == 503
    assert r.json()["ready"] is False


# --------------------------------------------------------------------------
# 2. the management-command surface
# --------------------------------------------------------------------------


def test_only_the_two_gate_commands_exist_in_the_project():
    """ADR-002 §4.1(b): discovery is opened by `open_discovery` and closed by
    `close_discovery`. A third project command touching the gate would be a
    second front door."""
    project = {name for name, app in get_commands().items() if app.startswith("apps.")}
    assert project == {
        "open_discovery", "close_discovery", "seed_demo", "run_jobs",
        "verify_audit_chain",
    }, f"unexpected project management commands: {sorted(project)}"


def test_only_the_gate_commands_write_discovery_enabled_at():
    """The static half of the gate guard: ADR-002 §4.1(b) says discovery "cannot
    be opened by `UPDATE campuses SET discovery_enabled_at = now()`", which is
    only true while exactly one code path writes the column.

    Reads are fine — `scoping.py` must read it, and `seed_demo` prints it. This
    looks for writes: an attribute assignment, a queryset `update()`, or a
    `setattr`.

    # ponytail: a source grep, not a database constraint. Ceiling: it sees three
    # spellings of a write and would miss a fourth (raw SQL, an admin form, a
    # `**kwargs` save). Upgrade path is the trigger recommended in
    # `test_the_gate_column_cannot_be_opened_outside_the_authorised_command`,
    # which would make this test redundant — the better outcome.
    """
    write = re.compile(
        r"\.discovery_enabled_at\s*=(?!=)"
        r"|update\([^)]*discovery_enabled_at\s*="
        r"|setattr\([^)]*discovery_enabled_at",
        re.S,
    )
    allowed = {
        "apps/core/management/commands/open_discovery.py",
        "apps/core/management/commands/close_discovery.py",
        "apps/core/models.py",  # the field declaration itself
    }
    offenders = []
    for path in sorted(list((REPO / "apps").rglob("*.py")) + list((REPO / "bookhop").rglob("*.py"))):
        rel = path.relative_to(REPO).as_posix()
        if rel in allowed or "/migrations/" in rel:
            continue
        if write.search(path.read_text(encoding="utf-8")):
            offenders.append(rel)
    assert offenders == [], (
        f"these files write the discovery gate column: {offenders}. ADR-002 "
        "§4.1(b) permits one writer, the `open_discovery` command."
    )


# --------------------------------------------------------------------------
# 3. the ORM
# --------------------------------------------------------------------------


def test_regression_the_gate_column_cannot_be_opened_outside_an_authorisation():
    """**REGRESSION for QA-S0 F3** — was the finding that blocked integration,
    now the fixed behaviour.

    F3 measured that ADR-002 §4.1(b)'s *"Discovery cannot be opened by `UPDATE
    campuses SET discovery_enabled_at = now()`"* was false: a plain queryset
    update opened the gate on a campus with no `gate_authorisations` row, no
    legal entity, no CoI and no MoU, and wrote no `audit_log` row.

    Migration 0003 makes the sentence true. The write now **raises** rather than
    silently not persisting, which is the right failure: application code that
    tried it finds out. The exception class differs by engine, so this catches
    `django.db.DatabaseError` (ENGINE-DIVERGENCE §3.8).

    The residual — the trigger requires an authorisation to *exist*, not to be
    *complete* — is F8 in
    `tests/e2e/test_gate_journey.py::test_finding_the_write_guard_checks_that_an_authorisation_exists_not_that_it_is_complete`.
    """
    from django.db import DatabaseError, transaction

    from apps.core.models import City

    city = City.objects.create(name="Chennai", state="Tamil Nadu")
    campus = Campus.objects.create(city=city, name="Unauthorised", slug="unauthorised")
    audit_before = AuditLog.objects.count()

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            Campus.objects.filter(pk=campus.pk).update(
                discovery_enabled_at=timezone.now()
            )

    campus.refresh_from_db()
    assert campus.discovery_enabled_at is None
    assert AuditLog.objects.count() == audit_before


def test_a_django_admin_is_not_registered_in_s0():
    """TASKS §2 S2 puts the moderation queue "in admin", so an admin site is a
    future route into every table including `campuses`. Recorded here so that
    the slice which adds it is the slice that gates it: `django.contrib.admin` is
    absent from INSTALLED_APPS at the end of S0, which is why the route
    enumeration above is complete."""
    from django.conf import settings

    assert "django.contrib.admin" not in settings.INSTALLED_APPS
