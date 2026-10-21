import pytest
from django.db import connection
from django.db.backends.signals import connection_created


def _declare_flush_escape(sender, connection, **kwargs):  # noqa: ARG001
    """Declare the escape on every connection, as soon as it is opened.

    **The mechanism is `connection_created`, not a one-off `SET`, and the first
    PostgreSQL run is why.** The setting is a session GUC: it lives on a
    *database connection*, not on a pytest session. A session-scoped fixture
    that SET it once bound it to whichever connection happened to exist at
    session setup, and any close reopened a connection without it — measured:
    one test that used threads and called `connections.close_all()` was enough,
    and the *next* transactional test then died in teardown on
    `TRUNCATE "cities", "jobs", …` with `audit_log is append-only`.

    That is the failure QA-S0 F9 and ENGINE-DIVERGENCE §7.1 exist to prevent,
    and it would have landed on S4's `test_double_booking.py`, which needs
    `transactional_db` **and** several real connections to race at all. The
    tempting fix at that moment is deleting the TRUNCATE guard. A per-connection
    setting belongs on a per-connection hook.
    """
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SET bookhop.allow_flush = 'yes'")


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
    must be live on **every** connection the harness might flush with — see
    `_declare_flush_escape` for why "every" is the word that was wrong before.
    """
    if connection.vendor != "postgresql":
        yield
        return
    connection_created.connect(_declare_flush_escape)
    with django_db_blocker.unblock():
        # The signal cannot fire retroactively, so the connection that already
        # exists at session setup is declared here. A custom GUC needs no
        # privilege and grants none: see ENGINE-DIVERGENCE §7.1 on why
        # production cannot refuse it either.
        _declare_flush_escape(None, connection)
    yield
    connection_created.disconnect(_declare_flush_escape)


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
