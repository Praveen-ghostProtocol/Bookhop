"""Fixtures for red-team probes only.

**Deliberately independent of `tests/e2e/conftest.py`.** A probe that shares a
fixture with the gate it is auditing measures the fixture, not the product.

## This tree is opt-in, and the opt-out is implemented HERE because it is not
## implemented anywhere else.

The red-team charter says `tests/redteam/**` is *"excluded from the default
suite run"*. **It is not.** `pytest.ini` carries `testpaths = tests` and no
`norecursedirs`, so the moment this directory existed every probe in it
joined the number both gates quote. A probe is a deliberately red
measurement; a red probe inside QA's headline count is how a probe tree
silently becomes a second QA suite — the exact outcome the charter names.

`pytest.ini` is outside this agent's write scope during the freeze, so the
exclusion lives here and the gap is reported as a finding (REDTEAM-S2 F54,
cto). Run the probes with:

    BOOKHOP_REDTEAM=1 pytest tests/redteam -q

**The skip names the switch and the slice** rather than passing, per
`CLAUDE.md` rule 10: a probe that silently passed when nobody asked for it
would be indistinguishable from a probe that found nothing.
"""

import os

import pytest

_ENABLED = os.environ.get("BOOKHOP_REDTEAM", "") not in ("", "0", "false", "no")


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    """Skip every probe in this tree unless `BOOKHOP_REDTEAM` is set."""
    if _ENABLED:
        return
    mark = pytest.mark.skip(
        reason=(
            "RED TEAM PROBE, NOT RUN BY DEFAULT (slice=S2): set "
            "BOOKHOP_REDTEAM=1 to run. These probes are measurements, not "
            "regressions; a finding routes to the owning agent and the "
            "regression is written in that agent's tree."
        )
    )
    here = str(config.rootpath / "tests" / "redteam")
    for item in items:
        if str(item.fspath).startswith(here):
            item.add_marker(mark)


@pytest.fixture
def rt_client_as(db):
    """A fresh signed-in Django test client per actor.

    A reused client makes every actor after the first anonymous, because the
    session key is reminted on save while the cookie still points at the old
    one — so a 401 would read as an authorisation finding.
    """
    from django.test import Client

    from apps.accounts.sessions import SESSION_USER_KEY

    def _sign_in(user):
        client = Client()
        session = client.session
        session[SESSION_USER_KEY] = user.id
        session.save()
        return client

    return _sign_in


@pytest.fixture
def rt_second_student(db, signup_campus, privacy_notice):
    """A **second real** student on the same campus, owning nothing.

    `is_seed=False`: every interesting disclosure question is about the actor
    the gate was written for, and the shared `student` fixture is seed.
    """
    from apps.accounts.models import User
    from apps.accounts.services import grant_consent

    user = User.objects.create(
        email="arun@example.ac.in", display_name="Arun K",
        campus=signup_campus, city_id=signup_campus.city_id,
        status="PENDING_VERIFICATION", adult_verified=True, campus_verified=True,
        is_seed=False,
    )
    grant_consent(user, "account", privacy_notice, "SIGNUP_FORM", None, "pytest")
    user.status = "ACTIVE"
    user.save(update_fields=["status"])
    user.refresh_from_db()
    return user
