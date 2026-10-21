import pytest
from django.db import connection


@pytest.fixture(scope="session", autouse=True)
def allow_test_flush(django_db_setup, django_db_blocker):
    """Let the test harness flush tables the append-only triggers protect.

    **QA-S0 F9: ENGINE-DIVERGENCE §7.1 called this fixture mandatory and it did
    not exist.** `bookhop.allow_flush` appeared in exactly one file — migration
    0003 — so the first PostgreSQL run of S4's `test_double_booking.py`, which
    §5.3 requires to be transactional, would have failed in teardown: Django's
    `postgresql.sql_flush` emits `TRUNCATE`, the statement trigger fires, and
    the tempting fix at that moment is deleting the guard §3.6 calls the most
    important unverified thing S0 shipped. Writing the fixture now is cheaper
    than discovering that on a Postgres box under schedule pressure.

    On SQLite this is a deliberate no-op: there is no `TRUNCATE` statement
    (measured — it is a syntax error) and Django flushes with `DELETE`, which
    the append-only trigger correctly refuses. So `transactional_db` remains
    unusable with `audit_log` rows locally and that is the right answer; use
    `django_db` unless a race is the subject.

    `autouse` and session-scoped because a teardown failure is not something a
    test should have to opt into avoiding, and because on Postgres the setting
    must be live on the connection the harness flushes with.
    """
    if connection.vendor != "postgresql":
        yield
        return
    with django_db_blocker.unblock():
        with connection.cursor() as cursor:
            # A custom GUC, so this needs no privilege and grants none: see
            # ENGINE-DIVERGENCE §7.1 on why production cannot refuse it either.
            cursor.execute("SET bookhop.allow_flush = 'yes'")
    yield


@pytest.fixture
def engine():
    """The vendor the assertion in front of you actually ran on.

    Tests print this so a green run cannot be mistaken for a green run on
    Postgres. See company/architecture/ENGINE-DIVERGENCE.md.
    """
    return connection.vendor


@pytest.fixture
def legal_entity(db):
    from apps.core.models import LegalEntity

    return LegalEntity.objects.create(
        cin="U12345TN2026PTC000001",
        inc20a_filed_at="2026-11-01",
        grievance_officer_name="A Human",
        grievance_officer_email="grievance@example.test",
        grievance_officer_phone="+910000000000",
    )


@pytest.fixture
def city(db):
    from apps.core.models import City

    return City.objects.create(name="Chennai", state="Tamil Nadu")


@pytest.fixture
def closed_campus(db, city, legal_entity):
    """A campus with discovery_enabled_at NULL — the default and the only
    lawful state before Gate C."""
    from apps.core.models import Campus

    return Campus.objects.create(
        city=city, name="Closed Campus", slug="closed", legal_entity=legal_entity
    )


@pytest.fixture
def complete_evidence():
    return {
        "counsel_engagement_ref": "ENG-2026-01",
        "takedown_sop_ref": "SOP-TD-1",
        "oncall_rota_ref": "ROTA-1",
        "breach_rehearsal_at": "2026-11-10",
        "campus_mou_ref": "MOU-DEMO-1",
        "notice_version_ids": [1, 2, 3],
    }
