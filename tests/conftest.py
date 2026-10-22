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

    **It closes the connection, and that line is the whole of QA's measured
    isolation fix.** Connecting the signal is enough; *using* a connection here
    and leaving it open was not. pytest-django's blocker patches
    `ensure_connection`, so it can stop an alias being **opened** — it cannot
    close one it did not open. A session-scoped fixture that leaves a
    PostgreSQL connection behind therefore hands every subsequent
    non-`django_db` test a live alias, and a test with undeclared access writes
    **outside** the per-test transaction, so its rows commit and survive into
    every later test. Measured cost on an unchanged tree: 0, 1, 4, 13 and 14
    failures across five consecutive runs, landing on the audit-chain tests
    rather than on whichever test leaked, because the chain is one linked list
    across the whole table.

    The retroactive `_declare_flush_escape(None, connection)` call this used to
    make is now **gone, and redundantly so rather than as a trade**: with the
    connection closed, the next real test opens a fresh one and
    `connection_created` fires for it. There is no connection left for a
    retroactive declaration to be about.
    """
    if connection.vendor != "postgresql":
        yield
        return
    connection_created.connect(_declare_flush_escape)
    with django_db_blocker.unblock():
        connection.close()
    yield
    connection_created.disconnect(_declare_flush_escape)


@pytest.fixture(scope="session", autouse=True)
def restore_gate_privileges_for_the_harness(django_db_setup, django_db_blocker):
    """Re-grant what migration `core/0008` revokes, for the test session only.

    **This is the harness yielding to the control, which is the right
    direction** — and it is worth being exact about what it costs, because a
    re-grant in a conftest is the shape of thing that quietly disarms a guard.

    `core/0008` revokes INSERT/UPDATE/TRUNCATE on `gate_authorisations` and
    TRUNCATE on `audit_log` from the application role (RED TEAM §1 and §3). The
    suite then cannot do three things it legitimately needs to:

      * **create `gate_authorisations` rows** — the gate tests, the SQLSTATE
        tests and QA's contract tests all do, because the authorisation row is
        the subject;
      * **exercise the UPDATE branch** of 0002's append-only trigger, which has
        to be reachable to be asserted (`CLAUDE.md` rule 16);
      * **TRUNCATE** during `transactional_db` teardown, which is Django's own
        `sql_flush` on PostgreSQL.

    **The re-grant is only possible because the test role owns these tables**,
    and that is exactly the ceiling `core/0008` documents and measures: an owner
    can grant itself back what it was revoked, in one statement. A production
    application role would not own them, so it could not do this — which is
    simultaneously why the harness can proceed and why the privilege layer is
    not finished until ownership moves. `test_least_privilege.py` asserts the
    revocation exists in the migration and measures the live grant state, so
    this fixture cannot be mistaken for the control being absent.

    **And it closes the connection afterwards** — the same one line as
    `allow_test_flush`, for the same measured reason: pytest-django's blocker
    patches `ensure_connection`, so it cannot close an alias this fixture
    opened, and a session-scoped fixture that leaves one open gives every later
    non-`django_db` test undeclared, **committing** database access. A fixture
    whose job is to restore the harness must not break the harness's isolation
    to do it.
    """
    from django.db import connection

    if connection.vendor != "postgresql":
        yield
        return
    with django_db_blocker.unblock():
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_user")
            role = cursor.fetchone()[0]
            cursor.execute(f'GRANT INSERT, UPDATE, TRUNCATE ON gate_authorisations TO "{role}"')
            cursor.execute(f'GRANT TRUNCATE ON audit_log TO "{role}"')
        connection.close()
    yield


@pytest.fixture(autouse=True)
def _public_origin(settings):
    """An origin for the absolute links emailed sign-in needs.

    `apps.core.request_context.public_origin` **raises** without one, by design
    (RED TEAM §2's sibling: a `localhost` default would email a student a link
    to their own machine). A service-layer test calls `request_magic_link`
    outside any request, so it has no scheme or host and needs the configured
    fallback.

    Autouse, because this is test *infrastructure* rather than the property
    under test — the refusal is asserted explicitly in
    `test_job_payload_credentials.py::test_an_absolute_origin_is_refused_rather_than_defaulted`,
    which clears it again.
    """
    settings.PUBLIC_ORIGIN = "https://bookhop.test"
    return settings.PUBLIC_ORIGIN


# There is deliberately **no autouse fixture clearing `rate_limit_counters`.**
#
# An earlier version of this file had one, and it was wrong twice over. It was
# written when the limiter used Django's **database cache** table, which is
# created by a migration rather than by a model and is therefore **not** rolled
# back by `django_db` — so isolation really did need a fixture. The limiter is
# now `apps.core.models.RateLimitCounter`, an ordinary model: `django_db` rolls
# it back and `transactional_db`'s flush truncates it. The fixture became
# unnecessary the moment the backend changed and nobody noticed, which is the
# ordinary way scaffolding outlives its reason.
#
# It was also actively harmful. As an autouse function-scoped fixture it ran
# **before** an explicitly-requested `db` fixture, so a test written
# `def test_x(db)` rather than with the `django_db` marker **errored at setup**
# with "Database access not allowed" — measured. A fixture that has to guess
# whether the database is available yet is a fixture that will guess wrong.

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
def security_log():
    """Capture the `bookhop.security` stream. **`caplog` cannot.**

    That logger is configured with `propagate: False` (settings `LOGGING`), so
    its records never reach the root handler pytest attaches — which means an
    assertion about the CERT-In/DPDP security stream written with `caplog`
    passes **vacuously**, every time, and is reported as coverage
    (`CLAUDE.md` rule 12). This fixture attaches to the logger itself.
    """
    import logging

    records = []

    class _Collect(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("bookhop.security")
    handler = _Collect(level=logging.DEBUG)
    logger.addHandler(handler)
    try:
        yield records
    finally:
        logger.removeHandler(handler)


@pytest.fixture(autouse=True)
def salt(settings):
    """A development tombstone salt, supplied to **every** test.

    **Autouse, after QA's precondition matrix tripped on it.** `erase_account`
    raises without a salt and there is deliberately no default
    (`COMPLIANCE.md` §7 rows 3 and 24), so any test in any tree that erases an
    account has to know to request a fixture it has no reason to know about —
    and the failure it gets is a `RuntimeError` about a server-side secret,
    which reads like a product defect rather than a missing fixture.

    This weakens nothing. The no-default property is about **settings**, and it
    is still asserted directly by
    `test_erasure.py::test_erasure_refuses_when_no_salt_is_configured`, which
    clears the setting and requires the refusal. Autouse makes the harness
    usable; that test keeps the control honest.

    `erase_account` **raises** when the salt is unset (`COMPLIANCE.md` §7 rows
    3 and 24 — there is no default, because a shared default makes every
    deployment's hashes identical). So a test that erases has to supply one,
    and `tests/unit/test_erasure.py` asserts the refusal as a property rather
    than working around it.
    """
    settings.TOMBSTONE_EMAIL_SALT = "test-salt-not-a-real-secret"
    settings.TOMBSTONE_EMAIL_SALT_VERSION = "test-v1"
    return settings.TOMBSTONE_EMAIL_SALT


@pytest.fixture
def signup_campus(db, city, legal_entity):
    """A closed campus that accepts an email domain, so sign-in is reachable.

    `closed_campus` has `email_domains = []`, which is the correct production
    default — *"empty list = no self-service signup"* (DATA-MODEL §1) — and
    makes `request_magic_link` refuse every address. A campus that accepts a
    domain is a separate fixture so no test can accidentally rely on the
    default being permissive.
    """
    from apps.core.models import Campus

    return Campus.objects.create(
        city=city, name="Signup Campus", slug="signup", legal_entity=legal_entity,
        email_domains=["example.ac.in"],
    )


@pytest.fixture
def privacy_notice(db):
    from apps.accounts.models import NoticeVersion

    return NoticeVersion.objects.create(
        kind="PRIVACY", version="2026-11-01.1", locale="en",
        body_md="# Privacy\n\nTest notice.", sha256="0" * 64,
    )


@pytest.fixture
def privacy_notice_ta(db, privacy_notice):
    """A **published Tamil notice** — the condition the locale-gate tests need
    and previously could not produce.

    **REVIEW-S1 B4's second half.** The gate test passed while the bypass was
    live, because no fixture published a `ta` row: `current_notice` fell back
    to English for a reason that had nothing to do with the gate, so the
    assertion was true by accident. *"A guard test whose fixture cannot produce
    the condition"* is the defect class this project has now hit eight times,
    and it is what `CLAUDE.md` rule 12 is about.

    The body is deliberately distinctive so a test can assert on the **content
    served** rather than only on a `locale` field — a response labelled `en`
    carrying Tamil prose would satisfy the weaker assertion.
    """
    from apps.accounts.models import NoticeVersion

    return NoticeVersion.objects.create(
        kind="PRIVACY", version="2026-11-01.1", locale="ta",
        body_md="# TAMIL-UNREVIEWED-BODY\n\nஇது மதிப்பாய்வு செய்யப்படாதது.",
        sha256="1" * 64,
    )


@pytest.fixture
def student(db, signup_campus, privacy_notice):
    """An ACTIVE seed student with every required consent granted.

    `is_seed=True` because ADR-002 §4.1(c) makes a seed actor the only one that
    can exercise a slice on a campus whose gate is lawfully closed.
    """
    from apps.accounts.models import User
    from apps.accounts.services import grant_consent

    user = User.objects.create(
        email="priya@example.ac.in", display_name="Priya R",
        campus=signup_campus, city_id=signup_campus.city_id,
        status="PENDING_VERIFICATION", adult_verified=True, campus_verified=True,
        is_seed=True,
    )
    grant_consent(user, "account", privacy_notice, "SIGNUP_FORM", None, "pytest")
    user.refresh_from_db()
    return user


@pytest.fixture
def pending_student(db, signup_campus):
    """Fresh from `consume_magic_link`: campus verified, nothing else."""
    from apps.accounts.models import User

    return User.objects.create(
        email="new@example.ac.in", campus=signup_campus, city_id=signup_campus.city_id,
        status="PENDING_VERIFICATION", campus_verified=True, is_seed=True,
    )


@pytest.fixture
def staff(db, signup_campus):
    from apps.accounts.models import User

    return User.objects.create(
        email="staff@example.ac.in", display_name="Demo Staff",
        campus=signup_campus, city_id=signup_campus.city_id,
        role="STAFF_ADMIN", status="ACTIVE", adult_verified=True, campus_verified=True,
        is_seed=True,
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
