"""J1 and J9, driven as a student drives them — and the unhappy column first.

`JOURNEYS.md` J1 is written as a table whose last column is *"If it goes wrong"*,
and the charter says plainly where this product's risk lives: *"Test the unhappy
paths first … that is where this product's risk lives, not in the happy path."*
So the happy path appears here once, as the control that makes the refusals
meaningful, and everything else is a refusal, a limit or a dead end.

Every test drives the L3 surface with the test client, because J1's own
constraint is *"JS disabled: identical page, form POSTs normally"* — so a form
POST is the right instrument and not a simplification.

Written from `JOURNEYS.md` J1 and J9, `PRD.md` §4.1 (AC-A1.x, AC-A2.x) and §4.6,
`API-CONTRACT.md` §5.1 and §2.4, and `COPY-DECK.md` §4, §5, §10.3.
"""

import html
import re

import pytest
from django.core import mail

pytestmark = pytest.mark.django_db


def _text(response):
    return re.sub(
        r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", response.content.decode()))
    )


def _link_from_last_email():
    return re.search(r"/auth/c/(\S+)", mail.outbox[-1].body).group(1)


# ---------------------------------------------------------------------------
# J1 step 2 — the enumeration oracle, which is the one that cannot be fixed later
# ---------------------------------------------------------------------------


def test_an_unrecognised_domain_is_indistinguishable_from_a_recognised_one(
    client, signup_campus, settings, django_capture_on_commit_callbacks
):
    """`API-CONTRACT.md` §5.1: *"**Always returns 202 whatever happens** — a
    different response for an unknown address is an account-enumeration
    oracle."* `PRD.md` AC-A1.1 and J1 step 2 say *identical*.

    Asserted as **indistinguishability**, not as a status code: the status, the
    redirect target and the rendered page are compared between a known-good
    campus address and an address on a domain no campus accepts, with only the
    address itself differing. A test that checked `== 302` on each separately
    would pass while the two pages said different things, which is the whole
    oracle.
    """
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    def submit(email):
        with django_capture_on_commit_callbacks(execute=True):
            posted = client.post("/auth/start", {"email": email})
        page = _text(client.get(posted["Location"]))
        return posted.status_code, posted["Location"], page.replace(email, "<ADDRESS>")

    good = submit("known@example.ac.in")
    unknown = submit("nobody@gmail.com")

    assert good[0] == unknown[0], f"different status: {good[0]} vs {unknown[0]}"
    assert good[1] == unknown[1], f"different redirect: {good[1]} vs {unknown[1]}"
    assert good[2] == unknown[2], (
        "the link-sent page differs between a recognised and an unrecognised "
        "address, which is an account-enumeration oracle:\n"
        f"  recognised:   {good[2][:300]!r}\n"
        f"  unrecognised: {unknown[2][:300]!r}"
    )


def test_no_email_is_sent_to_an_unrecognised_domain(
    client, signup_campus, settings, django_capture_on_commit_callbacks
):
    """The other half of the same property, and the half a page comparison
    cannot see. Identical pages are only safe if the *side effect* also differs
    — an attacker who can observe mail delivery has the same oracle by another
    route, and a student on a typo'd domain must not be mailed a working link to
    a campus they have no affiliation with."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        client.post("/auth/start", {"email": "nobody@gmail.com"})
    from apps.core.jobs import run_pending_jobs

    run_pending_jobs()
    assert mail.outbox == [], (
        f"a sign-in link was emailed to an address on no campus's domain: "
        f"{[m.to for m in mail.outbox]}"
    )


def test_the_link_sent_page_names_the_accepted_domains_generically(
    client, signup_campus, settings, django_capture_on_commit_callbacks
):
    """`PRD.md` AC-A1.2 and `API-CONTRACT.md` amendment A-17: the page tells the
    student which domains the campus accepts, because *"the domain line at step 2
    is the only thing that stops this being a silent void"*.

    A-17's narrowing is the point: this is campus configuration, identical for
    every visitor, about nobody — **not** another person's email domain, which
    criterion 7f still forbids.
    """
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    with django_capture_on_commit_callbacks(execute=True):
        client.post("/auth/start", {"email": "someone@example.ac.in"})
    page = _text(client.get("/auth/sent"))
    assert "example.ac.in" in page, (
        "the link-sent page does not name the accepted domain, so a student who "
        f"used a personal address learns nothing. Page: {page[:300]!r}"
    )


def test_a_campus_with_no_mou_offers_no_self_service_signup(client, closed_campus):
    """`DATA-MODEL.md` §1: *"Empty list = no self-service signup"*, and J1 step 2
    EC-11: *"No MoU yet … the same page says the campus is not open for sign-ups
    yet."*

    `closed_campus` has `email_domains = []`, which is the production default. An
    address on any domain must not produce a usable sign-in, and — the part that
    matters — must not produce a different *shape* of answer either.
    """
    from apps.accounts.models import EmailLoginToken, User

    response = client.post("/auth/start", {"email": "someone@nomou.ac.in"})
    assert response.status_code in (200, 302), response.status_code
    assert not User.objects.filter(email="someone@nomou.ac.in").exists(), (
        "an account was created on a campus with no accepted domains"
    )
    assert not EmailLoginToken.objects.exists(), (
        "a sign-in token was issued for a campus that has no MoU"
    )


@pytest.mark.parametrize("attempt", range(1, 7))
def test_the_magic_link_rate_limit_bites_at_the_published_number_with_a_retry_after(
    attempt, client, signup_campus, settings
):
    """J1 step 2 and `API-CONTRACT.md` §2.4: 5 per hour per email, *"with
    `Retry-After` honoured"*.

    Parametrised one request at a time so the report shows **where** the limit
    bit rather than only that it bit — a limit that fired at the first attempt
    would be a denial of service on the only way into the product, and a
    single loop asserting "a 429 happened somewhere" cannot tell the two apart.
    """
    for _ in range(attempt - 1):
        client.post("/auth/start", {"email": "limit@example.ac.in"})
    response = client.post("/auth/start", {"email": "limit@example.ac.in"})

    if attempt <= 5:
        assert response.status_code != 429, (
            f"attempt {attempt} of a published 5-per-hour limit was refused. "
            "A limit below its published number locks students out of the only "
            "entrance."
        )
        return

    assert response.status_code == 429, (
        f"attempt {attempt} was allowed past a 5-per-hour limit "
        f"({response.status_code})"
    )
    retry_after = response.get("Retry-After")
    assert retry_after and retry_after.isdigit() and int(retry_after) > 0, (
        f"the 429 carries no usable Retry-After ({retry_after!r}), so a client "
        "cannot honour it and J1 step 2's promise is not keepable"
    )


# ---------------------------------------------------------------------------
# J1 step 3 — the dead ends
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    ["reused", "expired", "nonsense", "another_students_token_shape"],
)
def test_a_link_that_cannot_be_used_says_so_in_plain_words_and_offers_a_way_on(
    case, client, signup_campus, settings, django_capture_on_commit_callbacks
):
    """J1 step 3: *"a plain page — 'this link has been used, ask for a new one' —
    with a working button. **Never a stack trace, never a bare code.**"*

    All four dead ends, because they are four different code paths that must
    converge on one page: single-use consumption, the 10-minute expiry, a
    malformed token and a well-formed token that was never issued. A student who
    forwards a link to themselves twice meets the first; a student on a slow
    mailbox meets the second.
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.accounts.models import EmailLoginToken
    from apps.core.jobs import run_pending_jobs

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        client.post("/auth/start", {"email": f"dead{case[:4]}@example.ac.in"})
    run_pending_jobs()
    token = _link_from_last_email()

    if case == "reused":
        assert client.get(f"/auth/c/{token}").status_code == 302
    elif case == "expired":
        EmailLoginToken.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
    elif case == "nonsense":
        token = "nonsense-token"
    else:
        token = "A" * len(token)

    response = client.get(f"/auth/c/{token}")
    page = _text(response)

    assert response.status_code in (400, 404), (
        f"{case}: an unusable link returned {response.status_code}"
    )
    assert "Traceback" not in response.content.decode(errors="ignore"), (
        f"{case}: a stack trace reached the student"
    )
    assert re.search(r"link", page, re.I), (
        f"{case}: the page does not mention the link, so a student cannot tell "
        f"what went wrong. Page: {page[:300]!r}"
    )
    assert re.search(r"/auth/start|send a new|another", response.content.decode(), re.I), (
        f"{case}: the dead end offers no way on, which J1 step 3 requires. "
        f"Page: {page[:300]!r}"
    )


def test_a_traversal_in_the_token_position_is_an_ordinary_not_found(client):
    """The case that is *not* a dead-end-link page, separated so neither
    assertion has to be loosened to accommodate the other.

    `../../etc/passwd` in the token position does not match
    `auth/c/<str:token>` at all — a `str` converter excludes `/` — so it falls
    to the catch-all and must be a plain 404. Asserted on its own because
    folding it into the dead-link test above would have meant weakening that
    test's *"the page mentions the link"* assertion, and a guard loosened to
    accommodate an unrelated case is how guards stop guarding.
    """
    response = client.get("/auth/c/../../etc/passwd")
    assert response.status_code == 404, response.status_code
    body = response.content.decode(errors="ignore")
    assert "Traceback" not in body and "root:" not in body, (
        "a traversal attempt returned something other than a plain not-found page"
    )


# ---------------------------------------------------------------------------
# J1 step 5 — declining
# ---------------------------------------------------------------------------


def test_nothing_on_the_consent_screen_is_pre_ticked(
    client, signup_campus, privacy_notice, settings, django_capture_on_commit_callbacks
):
    """E-Com r.4(9), **in force now** (`DATA-MODEL.md` §2, `COMPLIANCE.md` §1.3):
    *"No pre-ticked boxes."* The cheapest compliance failure in the product to
    introduce by accident — one `checked` attribute in a template — and the
    cheapest to assert."""
    from apps.core.jobs import run_pending_jobs

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    with django_capture_on_commit_callbacks(execute=True):
        client.post("/auth/start", {"email": "preticked@example.ac.in"})
    run_pending_jobs()
    client.get(f"/auth/c/{_link_from_last_email()}")
    client.post("/account/age", {"date_of_birth": "2001-04-17"})

    markup = client.get("/account/privacy").content.decode()
    checkboxes = re.findall(r"<input[^>]*type=[\"']checkbox[\"'][^>]*>", markup)
    assert checkboxes, "no checkboxes found, so this test asserted nothing"
    pre_ticked = [tag for tag in checkboxes if re.search(r"\bchecked\b", tag)]
    assert not pre_ticked, (
        f"the consent screen pre-ticks {len(pre_ticked)} of {len(checkboxes)} "
        f"purposes, which E-Com r.4(9) forbids and which is in force today: "
        f"{pre_ticked}"
    )


def test_declining_a_required_purpose_names_what_it_blocks_and_keeps_the_student_in(
    client, signup_campus, privacy_notice, settings, django_capture_on_commit_callbacks
):
    """J1 step 5: *"the screen says which action that blocks and **leaves the
    student signed in**."*

    The second half is the one a reasonable developer breaks: refusing a required
    consent looks like a reason to end the session, and a student who is signed
    out for declining has effectively been forced. `COMPLIANCE.md` §1.3's whole
    point is that consent is not consent if refusing it costs the account.
    """
    from apps.accounts.models import Consent
    from apps.core.jobs import run_pending_jobs

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    with django_capture_on_commit_callbacks(execute=True):
        client.post("/auth/start", {"email": "declines@example.ac.in"})
    run_pending_jobs()
    client.get(f"/auth/c/{_link_from_last_email()}")
    client.post("/account/age", {"date_of_birth": "2001-04-17"})

    # Grants `notifications` only, which is optional, and declines `account` and
    # `listing_publication`, which J1 step 5 calls required.
    after = client.post("/account/privacy", {"notifications": "on"}, follow=True)
    page = _text(after)

    assert not Consent.objects.filter(
        purpose_key="account", granted_at__isnull=False
    ).exists(), "a purpose the student did not tick was recorded as granted"

    assert client.get("/account").status_code == 200, (
        "declining a required purpose signed the student out. Consent obtained "
        "on pain of losing the account is not freely given (COMPLIANCE §1.3)."
    )
    assert re.search(r"can'?t do|cannot do|blocks|not able", page, re.I), (
        "the screen does not say what declining blocks, so the student has no "
        f"way to connect the refusal to the consequence. Page: {page[:400]!r}"
    )


# ---------------------------------------------------------------------------
# J9 — the help surface, and the number that must not exist
# ---------------------------------------------------------------------------


def test_the_help_page_says_what_bookhop_cannot_do_before_anything_else(client):
    """`PRD.md` AC-H6.5 and J9 step 2: *"We can help you reach the other student,
    put a book back up, or look at a listing. We can't refund you — we never hold
    the money."* — said **before** the student types.

    J9's own note on why: *"Saying this up front is cheaper than saying it in a
    reply, and it is the one unmanaged expectation that turns into the belief
    that BookHop vouches for the trade."* That belief is the vouching liability
    `COMPLIANCE.md` §2.5 and R-16 call our worst asymmetry, so this copy is a
    control and not a nicety.
    """
    page = _text(client.get("/help"))
    assert re.search(r"can'?t refund|cannot refund", page, re.I), (
        f"the help page does not say BookHop cannot refund. Page: {page[:400]!r}"
    )
    assert re.search(r"never hold the money|do(es)? not hold", page, re.I), (
        f"the help page does not say BookHop never holds the money. "
        f"Page: {page[:400]!r}"
    )


def test_no_page_anywhere_publishes_a_phone_number_or_a_whatsapp(
    client, signup_campus, privacy_notice, settings, django_capture_on_commit_callbacks
):
    """`PRD.md` AC-H6.4 and J9 step 6: *"No phone number and no WhatsApp number,
    **anywhere** in the product, the emails, the notices or any listing of the
    service."*

    This is not a support-design preference. `DATA-MODEL.md` §11.3 and
    `METRICS.md` both record that off-platform support makes the support-minutes
    number unmeasurable, and that number is D-009's reversal trigger — so a
    published WhatsApp number would disable the measurement that decides whether
    the business works. J9 step 6 states the mechanism: in-app is the only
    channel *because* nothing else is published.

    Swept over every concrete route and over the sign-in email, rather than over
    a list of pages someone remembered.

    **The declared exemption, with its reason beside it** (`API-CONTRACT.md`
    A-17's lesson about criteria that outgrow their rationale): the grievance
    officer's phone is a column on `legal_entities` and IT Rules r.3(2)(a)
    *requires* it to be published once Gate B4 appoints one. AC-H6.4 bans a
    *support* number — a second way to ask for help that nobody times — not a
    statutory contact. So `/legal/grievance-officer` is exempt, and the sweep
    asserts the exemption is the only one.
    """
    from django.urls import get_resolver

    from apps.core.jobs import run_pending_jobs

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        client.post("/auth/start", {"email": "sweep@example.ac.in"})
    run_pending_jobs()

    exempt = {"/legal/grievance-officer"}
    # A contact number as a human would write one: an Indian mobile with a
    # country code, or the 5-5 grouping that Indian numbers are printed in.
    # Deliberately NOT a bare run of ten digits, which matches a timestamp and
    # a UUID fragment and would make this a test about false positives.
    phone = re.compile(r"\+91[\s-]?\d{5}[\s-]?\d{5}|\b\d{5}[\s-]\d{5}\b|\btel:")
    whatsapp = re.compile(r"whats\s*app", re.I)

    routes = []

    def walk(patterns, prefix=""):
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                walk(pattern.url_patterns, prefix + str(pattern.pattern))
            else:
                routes.append(prefix + str(pattern.pattern))

    walk(get_resolver().url_patterns)

    surfaces = {
        "/" + route.lstrip("/"): client.get("/" + route.lstrip("/")).content.decode(
            errors="ignore"
        )
        for route in routes
        if not any(ch in route for ch in "<(^$*")
    }
    surfaces.update(
        {f"/legal/{kind}": client.get(f"/legal/{kind}").content.decode(errors="ignore")
         for kind in ("privacy", "terms", "community-rules", "handover-guidance",
                      "ranking", "grievance-officer")}
    )
    surfaces.update({f"email:{m.subject}": m.body for m in mail.outbox})

    assert len(surfaces) > 10, (
        f"only {len(surfaces)} surfaces were swept, which cannot be the whole "
        "product; the route walk is broken and this test is vacuous"
    )

    offenders = {}
    for where, body in surfaces.items():
        if where in exempt:
            continue
        hits = phone.findall(body) + whatsapp.findall(body)
        if hits:
            offenders[where] = sorted(set(hits))
    assert offenders == {}, (
        "these surfaces publish a phone number or a WhatsApp, which AC-H6.4 "
        f"forbids and which disables the support-minutes measurement: {offenders}"
    )
