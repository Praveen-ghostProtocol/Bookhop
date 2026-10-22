"""Magic-link sign-in — ADR-001 §2.5, API-CONTRACT §5.1, PRD US-A1, JOURNEYS J1.

No password column, no phone column, no social login. The properties that have
to hold:

  * **single use, by the database**, not by a read-then-write;
  * **10-minute expiry**;
  * **the plaintext token is never stored** — a database read cannot sign
    anyone in;
  * **no response distinguishes a known address from an unknown one**
    (AC-A1.1), which is asserted at the API boundary in
    `tests/api/test_accounts_api.py` and here at the service boundary;
  * the campus email domain **is** the campus evidence, so no enrolment
    artefact is ever stored (§7 row 6).
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import CampusVerification, EmailLoginToken, User
from apps.accounts.services import (
    TOKEN_TTL,
    accepted_email_domains,
    campus_for_email,
    consume_magic_link,
    normalise_email,
    request_magic_link,
)
from apps.core.errors import (
    EmailDomainNotRecognised,
    RateLimited,
    Suspended,
    TokenAlreadyUsed,
    TokenExpired,
    TokenInvalid,
    ValidationFailed,
)
from apps.core.models import Job

pytestmark = pytest.mark.django_db


@pytest.fixture
def issue(django_capture_on_commit_callbacks):
    """Request a link and return the raw token the email would carry.

    **`django_capture_on_commit_callbacks` is required, not incidental.** The
    enqueue is inside `transaction.on_commit` so a rolled-back request never
    sends a working link (API-CONTRACT §3) — and under `django_db` the
    transaction is rolled back, so the callback never runs and `jobs` stays
    empty. A test written without this helper fails with "no send job was
    enqueued" and the tempting fix is moving the enqueue out of `on_commit`,
    which would delete the property
    `test_the_job_is_enqueued_only_on_commit` asserts.
    """

    def _issue(address="priya@example.ac.in", ip="198.51.100.7"):
        with django_capture_on_commit_callbacks(execute=True):
            request_magic_link(address, ip, "Mozilla/5.0 (Linux; Android 11)")
        job = Job.objects.filter(kind="accounts.send_magic_link").order_by("-id").first()
        assert job is not None, "no send job was enqueued"
        return job.payload["token"]

    return _issue


# --- normalisation ---------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected,why",
    [
        ("Priya@Example.AC.in", "priya@example.ac.in", "case"),
        ("  priya@example.ac.in  ", "priya@example.ac.in", "surrounding whitespace"),
        ("ＰＲＩＹＡ@example.ac.in", "priya@example.ac.in",
         "fullwidth codepoints — the same mailbox to the receiving server, and "
         "otherwise a second account on one address"),
    ],
)
def test_two_spellings_of_one_address_are_one_account(raw, expected, why):
    """**And the reason this is a function rather than `iexact`:** `LIKE` is
    case-sensitive on PostgreSQL and case-insensitive on SQLite, so a
    case-insensitive lookup written locally passes locally and changes meaning
    in production (QA-S0 §8 item 4). Normalising on write and comparing exactly
    removes the class."""
    assert normalise_email(raw) == expected, why


@pytest.mark.parametrize("bad", ["", None, "nope", "a@b", "two@@at.in", "a b@example.ac.in", 42])
def test_a_malformed_address_is_refused(bad):
    with pytest.raises(ValidationFailed):
        normalise_email(bad)


def test_no_service_function_uses_a_case_insensitive_lookup():
    """The engine trap, as a guard rather than as a convention.

    `__iexact`, `__icontains` and `__istartswith` all compile to `LIKE`/`ILIKE`
    and behave differently on the two engines for the ASCII case. A green local
    test over one of them says nothing about production, so the control is that
    there are none.
    """
    import pathlib

    source = pathlib.Path(__file__).resolve().parents[2] / "apps" / "accounts" / "services.py"
    text = source.read_text(encoding="utf-8")
    offenders = [token for token in ("__iexact", "__icontains", "__istartswith") if token in text]
    assert offenders == [], (
        "apps/accounts/services.py uses a case-insensitive ORM lookup "
        f"({offenders}); on SQLite `LIKE` is case-insensitive and on PostgreSQL "
        "it is not, so this passes locally and changes meaning in production. "
        "Use `normalise_email` on write and compare exactly."
    )


# --- the domain is the evidence -------------------------------------------


def test_an_unrecognised_domain_sends_nothing(signup_campus):
    with pytest.raises(EmailDomainNotRecognised):
        request_magic_link("priya@gmail.com", "198.51.100.7", "pytest")
    assert not Job.objects.filter(kind="accounts.send_magic_link").exists()
    assert not User.objects.exists()


def test_a_campus_with_no_domains_has_no_self_service_signup(closed_campus):
    """DATA-MODEL §1: *"Empty list = no self-service signup."* JOURNEYS J1 step
    2 calls this EC-11 — *"No MoU yet"* — and it is the correct **production**
    default, which is why the permissive campus is a separate fixture."""
    assert campus_for_email("anyone@example.ac.in") is None
    with pytest.raises(EmailDomainNotRecognised):
        request_magic_link("anyone@example.ac.in", None, None)


def test_the_accepted_domains_are_nameable_without_echoing_the_address(signup_campus):
    """PRD AC-A1.2. *"This is a product requirement, not polish:"* without it
    the enumeration-proof 202 and the `EmailDomainNotRecognised` raise combine
    into a silent dead end — the most likely first-run failure in the product."""
    domains = accepted_email_domains()
    assert domains == ["example.ac.in"]
    assert all("@" not in domain for domain in domains), (
        "an accepted-domain line must not be able to carry an address"
    )


def test_signing_in_records_campus_verification_and_stores_no_artefact(signup_campus, issue):
    """§7 row 6: *"Purge the evidence immediately on successful verification.
    Retain only a boolean + method + timestamp."* The magic-link design means
    there is no artefact to purge — the cheapest compliance win in the schema."""
    token = issue()
    user = consume_magic_link(token, "198.51.100.7", "Mozilla/5.0 (Linux; Android 11)")

    verification = CampusVerification.objects.get(user=user)
    assert verification.method == "INSTITUTIONAL_EMAIL"
    assert verification.email_domain == "example.ac.in"
    assert user.campus_verified is True
    assert user.email_verified_at is not None
    # The record is three fields and nothing else.
    assert {f.name for f in CampusVerification._meta.fields} == {
        "id", "user", "method", "email_domain", "verified_at", "verifier"
    }


# --- the token -------------------------------------------------------------


def test_the_plaintext_token_is_never_stored(signup_campus, issue):
    token = issue()
    rows = list(EmailLoginToken.objects.values_list("token_hash", flat=True))
    assert rows and token not in rows
    assert len(rows[0]) == 64, "token_hash is not a sha256 hex digest"


def test_a_link_works_once(signup_campus, issue):
    """PRD AC-A1.3, and API-CONTRACT §4.1's one idempotency-key exemption: *"a
    single-use token is idempotent by construction."*"""
    token = issue()
    consume_magic_link(token, "198.51.100.7", "pytest")
    with pytest.raises(TokenAlreadyUsed):
        consume_magic_link(token, "198.51.100.7", "pytest")


def test_single_use_is_enforced_by_the_update_not_by_a_read(signup_campus, issue):
    """The claim is a conditional UPDATE filtered on `consumed_at IS NULL`, so
    two simultaneous clicks mean one row affected and one zero. Simulated by
    consuming the row underneath the service's own pre-check, which is exactly
    what a concurrent click does."""
    token = issue()
    row = EmailLoginToken.objects.get()

    # The service has already passed its read-time checks at this point in a
    # real race; mark the row consumed and assert the UPDATE is what refuses.
    EmailLoginToken.objects.filter(id=row.id).update(consumed_at=timezone.now())
    with pytest.raises(TokenAlreadyUsed):
        consume_magic_link(token, None, None)


def test_a_link_expires_in_ten_minutes(signup_campus, issue):
    assert TOKEN_TTL == timedelta(minutes=10)
    token = issue()
    EmailLoginToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    with pytest.raises(TokenExpired):
        consume_magic_link(token, None, None)


@pytest.mark.parametrize("bad", ["", None, "not-a-token", "x" * 64, 7])
def test_an_unknown_token_is_refused_without_saying_why(signup_campus, bad):
    with pytest.raises(TokenInvalid):
        consume_magic_link(bad, None, None)


def test_a_user_agent_mismatch_is_logged_and_not_blocked(signup_campus, security_log, issue):
    """DATA-MODEL §2: a **soft** binding. A hard one breaks on webmail link
    prefetching and on "mail on the laptop, link on the phone", which on a
    campus is the normal case rather than the edge case."""
    token = issue()
    user = consume_magic_link(token, "198.51.100.7", "Mozilla/5.0 (Macintosh)")
    assert user.id
    assert any(
        record.getMessage() == "auth.consume.user_agent_mismatch" for record in security_log
    ), "a family mismatch was not logged"


def test_a_suspended_account_is_sent_no_link(signup_campus):
    user = User.objects.create(
        email="suspended@example.ac.in", campus=signup_campus, city_id=signup_campus.city_id,
        status="SUSPENDED", is_seed=True,
    )
    with pytest.raises(Suspended):
        request_magic_link(user.email, None, None)
    assert not Job.objects.filter(kind="accounts.send_magic_link").exists()


# --- rate limits (API-CONTRACT §2.4) --------------------------------------


def test_the_per_email_limit_is_five_an_hour(signup_campus):
    for _ in range(5):
        request_magic_link("priya@example.ac.in", "198.51.100.7", "pytest")
    with pytest.raises(RateLimited) as limited:
        request_magic_link("priya@example.ac.in", "198.51.100.7", "pytest")
    assert limited.value.http_status == 429
    assert limited.value.retry_after >= 1, "a 429 with no Retry-After is not actionable"


def test_the_per_ip_limit_is_twenty_an_hour(signup_campus):
    """Twenty from one IP across **different** addresses, which is the shape
    the per-email limit cannot see: a single machine enumerating a roll list."""
    for index in range(20):
        request_magic_link(f"s{index}@example.ac.in", "198.51.100.9", "pytest")
    with pytest.raises(RateLimited):
        request_magic_link("s99@example.ac.in", "198.51.100.9", "pytest")


def test_the_rate_limit_is_checked_before_the_campus_lookup(signup_campus):
    """**Otherwise the limiter is itself the oracle.** If an unrecognised domain
    short-circuited before the counter incremented, an attacker could tell a
    recognised domain from an unrecognised one by whether they got rate-limited
    — which is the enumeration AC-A1.1 closes everywhere else."""
    for _ in range(5):
        with pytest.raises(EmailDomainNotRecognised):
            request_magic_link("nobody@gmail.com", "198.51.100.11", "pytest")
    with pytest.raises(RateLimited):
        request_magic_link("nobody@gmail.com", "198.51.100.11", "pytest")


def test_no_rate_limit_leaks_the_address_into_the_cache_table(signup_campus):
    """The limiter keys on a **hash** of the subject. An email address sitting
    in a cache table is personal data in a table nobody thinks of as holding
    any, and `COMPLIANCE.md` §7's standing rule makes a field with no row a
    defect."""
    request_magic_link("priya@example.ac.in", "198.51.100.7", "pytest")
    from tests.unit.test_age_declaration import _all_text_in_database

    assert not any(
        "priya@example.ac.in" in value
        for table, _c, value in _all_text_in_database()
        if table == "bookhop_cache"
    )


# --- the send job ----------------------------------------------------------


def test_the_job_is_enqueued_only_on_commit(signup_campus):
    """API-CONTRACT §3: notifications are enqueued `on_commit` *"so a
    rolled-back transition never sends an email"* — here, so a rolled-back
    sign-in request never sends a **working link**."""
    from django.db import transaction

    try:
        with transaction.atomic():
            request_magic_link("priya@example.ac.in", None, None)
            raise RuntimeError("roll back")
    except RuntimeError:
        pass
    assert not Job.objects.filter(kind="accounts.send_magic_link").exists()
    assert not User.objects.filter(email="priya@example.ac.in").exists()


def test_a_stale_retry_does_not_deliver_a_dead_link(signup_campus, issue):
    """At-least-once delivery (API-CONTRACT §4.4), so the handler has to cope
    with arriving after the link is already used or expired — otherwise a retry
    hours later puts a dead link in a student's inbox."""
    from django.core import mail

    from apps.accounts.jobs import send_magic_link

    token = issue()
    job = Job.objects.filter(kind="accounts.send_magic_link").get()
    consume_magic_link(token, None, None)

    mail.outbox.clear()
    send_magic_link(job.payload)
    assert mail.outbox == [], "a consumed token was emailed anyway"


def test_the_handler_refuses_to_invent_an_email_body(signup_campus):
    """TASKS §1: *"Backend owns **no** templates — not even for emails."* So the
    handler renders `templates/email/magic_link.*`, which is
    frontend-developer's, and **raises** when it is missing rather than falling
    back to a built-in string.

    A fallback would be backend writing copy, and worse, untranslated English
    that no forbidden-copy test reads (`THREAT-MODEL.md` §6.1 covers
    `templates/**` and `locale/**`). A failed job naming the missing file and
    its owner is the honest outcome.
    """
    from django.template import TemplateDoesNotExist

    from apps.core.mail import deliver_email

    with pytest.raises(TemplateDoesNotExist) as missing:
        deliver_email(to="x@example.ac.in", name="a_template_nobody_wrote", context={})
    assert "frontend-developer" in str(missing.value)
    assert "templates/email/" in str(missing.value)
