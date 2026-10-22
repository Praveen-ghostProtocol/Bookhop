"""L2 `/api/v1` accounts endpoints — API-CONTRACT §5.1.

Pointed at `tests/urls_api_only` rather than the real root URLconf, because
`bookhop/urls.py` includes `web.urls` and `web/**` is frontend-developer's tree,
written concurrently — so the real root's **importability** depends on another
agent's work in progress. The prefix under test is the real `api/v1/` one, and
`test_the_real_root_urlconf_mounts_the_l2_api` asserts the real mount by reading
the file, so the isolation cannot hide an unwired route.

**Two contract requirements that read as bugs if you do not know why**, and both
are asserted here rather than described:

  * `POST /auth/magic-link` answers **the same bytes** for a known address, an
    unknown address at a recognised domain, and a gmail address (AC-A1.1). A
    different response is an account-enumeration oracle.
  * An anonymous POST **requires** an `Idempotency-Key` and it must be a
    canonical UUIDv4 (§4.1 as amended, QA-S0 F10/F11) — anonymous keys share one
    global namespace, so a short key is another caller's key.
"""

import json
import uuid

import pytest

from apps.accounts.models import Consent, User, UserTombstone
from apps.accounts.sessions import SESSION_USER_KEY
from tests.unit.test_forbidden_response import assert_no_forbidden_content

pytestmark = [
    pytest.mark.django_db,
    # `override_settings` as a pytestmark entry is rejected by pytest ("got
    # override_settings instead of Mark"); the django_db-compatible form is the
    # `urls` marker, which pytest-django applies per test.
    pytest.mark.urls("tests.urls_api_only"),
]

MAGIC_LINK = "/api/v1/auth/magic-link"
AGE = "/api/v1/account/age-declaration"
ACCOUNT = "/api/v1/account"
CONSENTS = "/api/v1/account/consents"
ERASE = "/api/v1/account/erase"


def post(client, path, body=None, key=None):
    return client.post(
        path,
        data=json.dumps(body or {}),
        content_type="application/json",
        headers={"Idempotency-Key": key or str(uuid.uuid4())},
    )


def sign_in(client, user):
    session = client.session
    session[SESSION_USER_KEY] = user.id
    session.save()
    return user


# --- the enumeration-proof 202 --------------------------------------------


def test_every_outcome_of_a_sign_in_request_is_the_same_response(client, signup_campus, student):
    """PRD AC-A1.1: *"QA asserts byte-identical responses for a known address,
    an unknown address at a recognised domain, and a gmail address."*

    Backend asserts it too, because this is the one property whose failure is
    invisible in the happy path — all three cases "work" and the difference
    between them is the leak.
    """
    responses = [
        post(client, MAGIC_LINK, {"email": student.email}),
        post(client, MAGIC_LINK, {"email": "nobody-at-all@example.ac.in"}),
        post(client, MAGIC_LINK, {"email": "someone@gmail.com"}),
    ]
    statuses = {r.status_code for r in responses}
    bodies = {r.content for r in responses}

    assert statuses == {202}, f"the status differed by address: {statuses}"
    assert len(bodies) == 1, (
        "the response body differed by address, which is an account-enumeration "
        f"oracle: {[b.decode() for b in bodies]}"
    )


def test_the_202_names_the_accepted_domains_without_echoing_the_address(client, signup_campus):
    """PRD AC-A1.2: *"This is a product requirement, not polish"* — without it
    the enumeration-proof 202 and the `EmailDomainNotRecognised` raise combine
    into a silent dead end, the most likely first-run failure in the product."""
    body = json.loads(post(client, MAGIC_LINK, {"email": "someone@gmail.com"}).content)
    assert body["accepted_domains"] == ["example.ac.in"]
    assert "someone@gmail.com" not in json.dumps(body)


def test_a_malformed_address_is_a_400_because_it_leaks_nothing(client, signup_campus):
    """The one thing that *may* differ: a malformed address is the caller's own
    input and says nothing about whether any account exists."""
    response = post(client, MAGIC_LINK, {"email": "not-an-address"})
    assert response.status_code == 400
    assert json.loads(response.content)["error"]["code"] == "VALIDATION_FAILED"


def test_a_rate_limited_request_is_a_429_and_not_a_202(client, signup_campus):
    """The other permitted difference: a 429 is about the **caller**, not about
    the address, so it leaks nothing and the client needs it."""
    for _ in range(5):
        assert post(client, MAGIC_LINK, {"email": "priya@example.ac.in"}).status_code == 202
    response = post(client, MAGIC_LINK, {"email": "priya@example.ac.in"})
    assert response.status_code == 429
    assert response["Retry-After"]


# --- idempotency on an anonymous POST -------------------------------------


def test_an_anonymous_post_without_a_key_is_refused(client, signup_campus):
    response = client.post(
        MAGIC_LINK, data=json.dumps({"email": "priya@example.ac.in"}),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert json.loads(response.content)["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"


@pytest.mark.parametrize(
    "key,why",
    [
        ("1", "a short key in a global namespace is another caller's key"),
        ("abc", "not a UUID at all"),
        ("00000000-0000-0000-0000-000000000001", "QA-S0 F11: not version 4"),
        ("00000000-0000-1000-8000-000000000001", "QA-S0 F11: version 1, not 4"),
    ],
)
def test_an_anonymous_key_that_is_not_a_uuid4_is_refused(client, signup_campus, key, why):
    """§4.1's safety argument for the global anonymous namespace is *"a
    collision requires guessing a UUIDv4"*. QA-S0 F10 and F11 measured that
    argument false on both halves; it is true now, and this is where it stays
    true."""
    response = post(client, MAGIC_LINK, {"email": "priya@example.ac.in"}, key=key)
    assert response.status_code == 400, why
    assert json.loads(response.content)["error"]["code"] == "VALIDATION_FAILED"


@pytest.mark.parametrize(
    "spelling,why",
    [
        (lambda k: k.upper(), "upper case"),
        (lambda k: k.replace("-", ""), "the bare 32-hex form"),
        (lambda k: "{" + k + "}", "braces"),
        (lambda k: "urn:uuid:" + k, "the URN prefix"),
        (lambda k: " " + k + " ", "surrounding whitespace"),
    ],
)
def test_every_spelling_of_one_anonymous_uuid_claims_the_same_row(
    client, signup_campus, spelling, why
):
    """**QA-S0 F11's second half, and the one the first fix of this finding got
    wrong.**

    `uuid.UUID` accepts five spellings of the same UUID, and the anonymous
    unique index is on the **string**. Merely *rejecting* what did not already
    look canonical still let upper case through, because the comparison
    lower-cased its own input — so one UUID still took two rows in the one
    namespace whose entire safety argument is uniqueness.

    Refusing a spelling the client chose does not make the namespace unique.
    **Normalising every spelling onto one row does**, which is what
    `canonical_uuid4` now returns and what `idempotent` now stores.
    """
    from apps.core.models import IdempotencyKey

    key = str(uuid.uuid4())
    first = post(client, MAGIC_LINK, {"email": "priya@example.ac.in"}, key=key)
    second = post(client, MAGIC_LINK, {"email": "priya@example.ac.in"}, key=spelling(key))

    assert first.status_code == 202
    assert second.status_code == 202
    assert second["Idempotency-Replayed"] == "true", (
        f"{why} was treated as a different key, so one UUID holds two rows"
    )
    assert IdempotencyKey.objects.filter(user_id=None).count() == 1
    assert IdempotencyKey.objects.get(user_id=None).key == key, (
        "the stored key is not the canonical form"
    )


def test_a_replayed_anonymous_request_is_not_executed_twice(client, signup_campus):
    """§4.1: the stored status is returned and the handler does not run again."""
    key = str(uuid.uuid4())
    first = post(client, MAGIC_LINK, {"email": "priya@example.ac.in"}, key=key)
    second = post(client, MAGIC_LINK, {"email": "priya@example.ac.in"}, key=key)

    assert first.status_code == second.status_code == 202
    assert second["Idempotency-Replayed"] == "true"


def test_an_anonymous_replay_never_returns_the_stored_body(client, signup_campus):
    """QA-S0 F10's **measured disclosure**, as a regression. Anonymous keys share
    one namespace, so a body returned on replay is a body a stranger can claim —
    measured as a `grievance_ref` reaching a non-user. The status is enough for
    a retry; the body is not the second caller's to have."""
    key = str(uuid.uuid4())
    post(client, MAGIC_LINK, {"email": "priya@example.ac.in"}, key=key)
    second = post(client, MAGIC_LINK, {"email": "priya@example.ac.in"}, key=key)
    assert json.loads(second.content) is None


def test_the_same_key_with_a_different_body_is_a_409(client, signup_campus):
    key = str(uuid.uuid4())
    post(client, MAGIC_LINK, {"email": "priya@example.ac.in"}, key=key)
    response = post(client, MAGIC_LINK, {"email": "other@example.ac.in"}, key=key)
    assert response.status_code == 409
    assert json.loads(response.content)["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


# --- age ------------------------------------------------------------------


def test_an_under_18_declaration_is_a_403_and_leaves_no_account(client, pending_student):
    """PRD AC-A2.2: *"The client-side block never substitutes for the server
    one: QA posts the under-18 DOB directly to the endpoint with the form
    bypassed and gets the same result."* This is that post."""
    from django.utils import timezone

    sign_in(client, pending_student)
    minor = timezone.localdate().replace(year=timezone.localdate().year - 17)

    response = post(client, AGE, {"date_of_birth": minor.isoformat()})

    assert response.status_code == 403
    assert json.loads(response.content)["error"]["code"] == "NOT_ADULT_VERIFIED"
    assert not User.objects.filter(id=pending_student.id).exists()


def test_the_declared_date_is_not_echoed_back(client, pending_student):
    from django.utils import timezone

    sign_in(client, pending_student)
    adult = timezone.localdate().replace(year=timezone.localdate().year - 25)
    response = post(client, AGE, {"date_of_birth": adult.isoformat()})
    assert response.status_code == 200
    assert adult.isoformat() not in response.content.decode()
    assert json.loads(response.content)["outcome"] == "ADULT_CONFIRMED"


def test_the_idempotency_row_keeps_a_hash_of_the_body_and_never_the_body(client, pending_student):
    """**The quiet route a DOB could reach storage.** Every POST's body is
    recorded against its idempotency key — and `idempotency_keys.request_hash`
    is a hash, with no column for the body. Asserted here because the age
    endpoint is the one POST whose body must never be stored."""
    from django.utils import timezone

    from apps.core.models import IdempotencyKey

    sign_in(client, pending_student)
    adult = timezone.localdate().replace(year=timezone.localdate().year - 25)
    post(client, AGE, {"date_of_birth": adult.isoformat()})

    rows = list(IdempotencyKey.objects.all())
    assert rows
    for row in rows:
        assert adult.isoformat() not in json.dumps(
            {"hash": row.request_hash, "body": row.response_body, "endpoint": row.endpoint}
        )


# --- consent --------------------------------------------------------------


def test_the_consent_endpoint_names_the_notice_version(client, student, privacy_notice):
    """PRD AC-A3.3: the screen names the exact version. A client cannot name
    what it was not told."""
    sign_in(client, student)
    body = json.loads(client.get(CONSENTS).content)
    assert body["notice_version"] == privacy_notice.version
    assert {p["purpose_key"] for p in body["purposes"]} == {
        "account", "listing_publication", "location_proximity",
        "chat", "safety_moderation", "notifications",
    }
    assert body["required"] == ["account"]


def test_a_consent_toggle_appends_and_is_reflected(client, student, privacy_notice):
    sign_in(client, student)
    before = Consent.objects.count()

    granted = client.put(
        f"{CONSENTS}/chat", data=json.dumps({"granted": True}),
        content_type="application/json", headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert granted.status_code == 200
    assert json.loads(granted.content) == {"purpose_key": "chat", "granted": True}

    withdrawn = client.put(
        f"{CONSENTS}/chat", data=json.dumps({"granted": False}),
        content_type="application/json", headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert json.loads(withdrawn.content)["granted"] is False
    assert Consent.objects.count() == before + 2, "a withdrawal updated instead of appending"


def test_an_unknown_purpose_is_a_404_not_a_400(client, student):
    """§2.2: 404 is *"not found **or** not visible to this actor"*, and a
    purpose key that does not exist is not found."""
    sign_in(client, student)
    response = client.put(
        f"{CONSENTS}/payments", data=json.dumps({"granted": True}),
        content_type="application/json", headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 404


# --- profile, export, erase -----------------------------------------------


def test_the_account_body_carries_the_callers_own_email_and_nothing_elses(client, student):
    sign_in(client, student)
    body = json.loads(client.get(ACCOUNT).content)
    assert body["email"] == student.email
    assert body["pseudonym"] == str(student.person_pseudonym)
    assert body["campus_name"] == student.campus.name
    assert "password" not in body


def test_an_anonymous_caller_gets_401_not_a_redirect(client):
    """§2.2: no session is `401 NOT_AUTHENTICATED`. A redirect to a login page
    from an L2 endpoint is a 200 to a machine client."""
    for path in (ACCOUNT, CONSENTS, "/api/v1/account/export"):
        response = client.get(path)
        assert response.status_code == 401, path
        assert json.loads(response.content)["error"]["code"] == "NOT_AUTHENTICATED"


def test_the_export_is_generated_live_with_no_staff_step(client, student):
    """PRD AC-X2.1. It also states what is retained after deletion, so the §7
    row 11 disclosure exists in two places rather than only in the delete
    flow."""
    sign_in(client, student)
    body = json.loads(client.get("/api/v1/account/export").content)
    assert body["account"]["email"] == student.email
    assert body["age_check"]["date_of_birth_held"] is False
    assert body["consent_state_now"]["account"] is True
    assert any("chat" in line.lower() for line in body["retained_if_you_delete"])


def test_erase_states_plainly_what_is_retained_and_why(client, student, salt):
    """API-CONTRACT §5.1: *"Response states plainly which records are retained
    for one year and why (r.8(3)) — the user learns it here, not from a support
    ticket."* And AC-X1.2 names the chat sentence specifically."""
    sign_in(client, student)
    response = post(client, ERASE)
    body = json.loads(response.content)

    assert response.status_code == 200
    assert body["erased"] is True
    retained = " ".join(body["retained"]).lower()
    assert "one year" in retained
    assert "chat" in retained, (
        "the §7 row 11 chat disclosure is missing; the student must learn it here"
    )
    assert UserTombstone.objects.filter(person_pseudonym=student.person_pseudonym).exists()


def test_erase_signs_the_caller_out(client, student, salt):
    sign_in(client, student)
    post(client, ERASE)
    assert client.get(ACCOUNT).status_code == 401


def test_erase_is_rate_limited_at_three_a_day(client, student, salt, privacy_notice):
    """API-CONTRACT §2.4. The limit is on the endpoint rather than on the
    outcome, because `erase_account` is idempotent and a loop against it would
    otherwise be free."""
    from apps.core.ratelimit import ONE_DAY, consume_quota

    for _ in range(3):
        consume_quota("account.erase", student.id, limit=3, window=ONE_DAY)
    sign_in(client, student)
    assert post(client, ERASE).status_code == 429


def test_the_nominee_endpoint_takes_a_name_and_an_email_and_nothing_else(client, student):
    """PRD AC-X2.2's s14 nomination. The shape is closed: a third party's phone
    or address would be personal data with no `COMPLIANCE.md` §7 row."""
    sign_in(client, student)
    ok = post(client, "/api/v1/account/nominee",
              {"nominee": {"name": "A Parent", "email": "parent@example.ac.in"}})
    assert ok.status_code == 201

    refused = post(client, "/api/v1/account/nominee",
                   {"nominee": {"name": "A Parent", "email": "p@example.ac.in",
                                "phone": "+919000000000"}})
    assert refused.status_code == 400
    assert "phone" in json.loads(refused.content)["error"]["message"]


# --- notices (public) -----------------------------------------------------


def test_a_notice_is_readable_without_a_session(client, privacy_notice):
    """§5.1: *"public, unauthenticated"*. A rights holder, a parent or a college
    is not a user (r.4(2))."""
    response = client.get("/api/v1/notices/privacy")
    assert response.status_code == 200
    assert json.loads(response.content)["version"] == privacy_notice.version


def test_the_handover_notice_slug_is_guidance_not_safety(client):
    """Amendment A-7: *"the identifier is where a label comes from"*, so the
    slug and the enum were renamed together. A `handover-safety` route would be
    the label a developer copies into a template."""
    from apps.accounts.api import NOTICE_SLUGS

    assert "handover-guidance" in NOTICE_SLUGS
    assert "handover-safety" not in NOTICE_SLUGS
    assert NOTICE_SLUGS["handover-guidance"] == "HANDOVER_GUIDANCE"
    assert client.get("/api/v1/notices/handover-safety").status_code == 404


def test_an_unpublished_notice_is_a_404_rather_than_an_empty_page(client):
    assert client.get("/api/v1/notices/terms").status_code == 404


# --- the boundary ---------------------------------------------------------


def test_no_accounts_response_carries_money(client, student, privacy_notice, salt):
    """ADR-003 §2.3 at the contract boundary, over **every** response this slice
    serves — the compensating control for the jsonb and free-text residuals
    (§5.3 item 4), now including the value limb (QA-S0 F15)."""
    sign_in(client, student)
    for path in (ACCOUNT, CONSENTS, "/api/v1/account/export", "/api/v1/notices/privacy"):
        payload = json.loads(client.get(path).content)
        assert_no_forbidden_content(payload, where=path)

    payload = json.loads(post(client, MAGIC_LINK, {"email": student.email}).content)
    assert_no_forbidden_content(payload, where=MAGIC_LINK)


def test_every_response_carries_a_request_id_and_the_csp(client, student):
    """CERT-In's 6-hour clock needs the id on every response (§2.1), and the CSP
    has to be on a JSON response too — a policy applied only to HTML misses an
    error page a proxy renders."""
    sign_in(client, student)
    response = client.get(ACCOUNT)
    assert response["X-Request-Id"]
    assert "default-src 'self'" in response["Content-Security-Policy"]


def test_the_real_root_urlconf_mounts_the_l2_api():
    """This module overrides `ROOT_URLCONF` to isolate itself from frontend's
    tree, so without this the whole file could pass against a route that was
    never wired. Asserted by reading `bookhop/urls.py` rather than by importing
    it, because importing it imports `web.urls`."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[2] / "bookhop" / "urls.py"
    text = root.read_text(encoding="utf-8")
    assert 'path("api/v1/", include("apps.accounts.urls"))' in text, (
        "the L2 accounts routes are not mounted in the real root URLconf"
    )
