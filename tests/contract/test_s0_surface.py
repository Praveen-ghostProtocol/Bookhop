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


def test_the_root_urlconf_registers_no_student_facing_route_itself():
    """**Re-pointed for S1, and the old assertion was the wrong one.**

    This test used to assert the surface was *exactly* `/healthz` and `/readyz`.
    Its own docstring anticipated S1 breaking it, and S1 did: eighteen routes
    exist. A count of routes was never the thing QA wanted guaranteed — it was a
    stand-in for "nobody can add a route without someone looking at it", and as
    a flat list it is the shape `CLAUDE.md` rule 11 names: it needs an entry per
    slice, and the entry gets added without the looking.

    **What QA actually wants guaranteed about the surface, and can:** the root
    URLconf is an *ownership* boundary. `TASKS.md` §1 says
    `bookhop/urls.py` includes `web.urls` once, in S0, and that
    frontend-developer never edits it; the API-CONTRACT §1 blocks mount per app.
    So the invariant is that **this file declares operational endpoints and
    includes, and no third thing** — a student-facing route registered here
    would be a route outside any owning module's slice discipline, which is the
    route nobody reviews.

    Asserted structurally, so it does not grow with pages.
    """
    from django.urls import get_resolver

    own_routes, includes = [], []
    for pattern in get_resolver().url_patterns:
        if hasattr(pattern, "url_patterns"):
            includes.append(str(pattern.pattern))
        else:
            own_routes.append(str(pattern.pattern))

    assert set(own_routes) == {"healthz", "readyz"}, (
        "bookhop/urls.py declares a route that is neither an operational "
        f"endpoint nor an include: {sorted(set(own_routes) - {'healthz', 'readyz'})}. "
        "TASKS §1 makes this file an ownership boundary; a route here belongs to "
        "nobody's slice and gets nobody's gate test."
    )
    assert includes, "web.urls is not mounted; the student-facing surface is gone"


def test_no_route_serves_campus_scoped_data_while_the_gate_is_closed(client):
    """The property the route count was standing in for, in the form that is
    checkable today.

    What QA wants is *"no route reaches a listing while the gate is closed"*.
    `listings` is an S2 table, so that assertion has no subject yet and saying
    it now would be rule 12's vacuous guard. What exists today is **campus-scoped
    tenancy data**, and the same question can be asked of it: with a campus
    seeded and its gate shut, no route may put that campus's name or slug in a
    response.

    This sweeps **every** route — operational, L2 and L3 — rather than the two
    QA checked before, and it extends to listings by adding one needle when S2
    lands, instead of by adding eighteen routes to a list.
    """
    from apps.core.models import Campus, City

    city = City.objects.create(name="Chennai", state="Tamil Nadu")
    campus = Campus.objects.create(
        city=city, name="Secret Campus Name", slug="secret-campus-slug"
    )
    assert campus.discovery_enabled_at is None, "the fixture must be gate-closed"

    needles = ("Secret Campus Name", "secret-campus-slug")
    leaks = {}
    for route in sorted(_http_routes()):
        if any(ch in route for ch in "<(^$*"):
            continue
        path = "/" + route.lstrip("/")
        response = client.get(path)
        body = response.content.decode(errors="ignore")
        found = [n for n in needles if n in body]
        if found:
            leaks[path] = found
    assert leaks == {}, (
        f"these routes put a gate-closed campus's identity in a response: {leaks}"
    )


def test_the_student_facing_tree_cannot_reach_a_listing_because_it_cannot_reach_the_orm():
    """Why frontend's eighteen routes are **structurally** not discovery read
    paths — which is the claim that lets the gate journey wait for S2/S3.

    `TASKS.md` §1: `web/**` *"calls L1 services, never the ORM, never L2 over
    HTTP"*. That is the whole argument: a view that cannot query a model cannot
    return a listing except through a service function, and every discovery
    service function begins with `assert_discovery_open` (ADR-002 §4.1(a)).

    Measured rather than trusted: no file in `web/**` uses a queryset, imports a
    model, or imports `requests`/`urllib` to call L2 over HTTP. This is cheap
    now and it is the check that keeps being true as pages are added — the
    alternative is re-asserting the gate on every new route, which is the list
    again.
    """
    import pathlib
    import re

    web = pathlib.Path(__file__).resolve().parents[2] / "web"
    assert web.is_dir(), "web/** does not exist"

    orm = re.compile(r"\.objects\.|from apps\.\w+\.models|from django\.db import")
    http = re.compile(r"^\s*import (requests|urllib)|^\s*from (requests|urllib)", re.M)
    offenders = {}
    for path in sorted(web.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        hits = [m.group(0) for m in orm.finditer(text)] + [
            m.group(0).strip() for m in http.finditer(text)
        ]
        if hits:
            offenders[path.relative_to(web.parent).as_posix()] = sorted(set(hits))
    assert offenders == {}, (
        "web/** reaches the database or L2 directly, so the gate is no longer "
        f"guaranteed by the service layer it was placed in: {offenders}"
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

    # This test owns its precondition rather than assuming a clean database.
    # It previously asserted `/readyz` was 200 *first*, which made it depend on
    # global state -- and it duly failed in suite order while passing alone,
    # which is the signature of leaked committed rows. That leak is a finding in
    # its own right (`test_the_test_database_is_not_polluted_by_committed_rows`)
    # and not something this test should be silently absorbing.
    overdue = Job.objects.filter(
        run_after__lt=timezone.now() - timedelta(minutes=5),
        completed_at__isnull=True, failed_at__isnull=True,
    )
    overdue.delete()
    assert client.get("/readyz").status_code == 200

    Job.objects.create(kind="qa.overdue", payload={},
                       run_after=timezone.now() - timedelta(minutes=30))
    r = client.get("/readyz")
    assert r.status_code == 503
    assert r.json()["ready"] is False

    # The body is `{"ready": false}` and nothing else. API-CONTRACT §5.8
    # reserves counters for the token-protected `/metricsz`, and the view now
    # logs the detail instead of serving it (ASVS V13). Asserted, because an
    # unauthenticated probe that grows a field is how a counter becomes public.
    assert set(r.json()) == {"ready"}, (
        f"/readyz exposes more than readiness: {sorted(r.json())}"
    )


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
        # S2 · API-CONTRACT §5.7's moderation queue. It is in this set and not
        # a third gate command: `test_only_the_gate_commands_write_discovery_
        # enabled_at` below is the assertion that matters and it is derived
        # from the source rather than from this list, so a command that did
        # touch the gate would fail there whatever it is called here.
        "review_listings",
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


def test_the_test_database_carries_no_committed_rows_between_tests(client):
    """**FINDING F19 — the isolation canary, and it is Red Team's finding
    measured from QA's side.**

    Red Team established that an autouse cache-clearing fixture gives roughly 99
    tests undeclared database access, and that pytest-django's blocker cannot
    block an already-connected PostgreSQL alias. A test with undeclared access
    writes **outside** the per-test transaction, so its rows commit and stay for
    the rest of the session.

    QA met this before reading the memo:
    `test_readyz_reports_not_ready_when_a_job_is_overdue` passed alone and
    failed in suite order, because something had committed an overdue `jobs`
    row and `/readyz` was therefore 503 before the test created anything. **A
    test that passes alone and fails in suite order is the signature of leaked
    committed state**, and the right response is to measure the leak rather than
    to make the test tolerant of it — which is why this canary exists and why
    the readyz test now clears its own precondition instead of absorbing the
    problem.

    The tables listed are ones no properly isolated test should leave behind.
    They are checked at the *start* of a test, so a non-empty table means a
    previous test committed. When the isolation fix lands this goes green, and
    the number of tests whose verdict changes is the measure of what this
    session's green actually meant.
    """
    from apps.core.models import AuditLog, Campus, City, GateAuthorisation, Job

    leaked = {
        model.__name__: model.objects.count()
        for model in (Job, AuditLog, GateAuthorisation, Campus, City)
        if model.objects.count()
    }
    assert leaked == {}, (
        "rows committed by an earlier test are visible at the start of this "
        f"one, so the per-test transaction is not containing writes: {leaked}. "
        "Red Team's undeclared-database-access finding, measured."
    )
