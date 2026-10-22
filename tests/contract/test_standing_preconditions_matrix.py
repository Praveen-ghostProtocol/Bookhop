"""API-CONTRACT §2.5 on every write, derived from the contract and not from the lists.

**Why this file exists.** `apps/accounts/api._may_write` runs a reduced
precondition set on four endpoints, each with a stated reason, and backend's
own words on handing it over are the right ones: *"it chose those lists by
reasoning about the contract and wrote its tests from the same reasoning. A
list one entry too short grants a write to an actor who should not have it, and
every test it wrote would still pass."*

That is the shape of defect this project has now found six times, and QA has
been the author of three of them. A second enumeration by QA, derived the same
way, would be a fourth — so this file does not enumerate the lists at all.

**What it derives from instead**, which is two contract facts and nothing else:

1. **§2.5's ordered preconditions** and the error each produces: authenticated
   → `401 NOT_AUTHENTICATED`; `status='ACTIVE'` → `403 SUSPENDED`;
   `adult_verified` → `403 NOT_ADULT_VERIFIED`; `campus_verified` →
   `403 NOT_CAMPUS_VERIFIED`; required consent → `403 CONSENT_REQUIRED`.
2. **§5.1's own statement of the journey order** — `POST /auth/consume` returns
   `{needs: ["age", "consent", "campus"]}` *"so the client knows the next
   step"*. That ordering is the contract telling us which preconditions a
   student can legitimately not yet satisfy, and when.

From those two, a drop is legitimate **only** if requiring the check would make
the step that fixes it unreachable. So every dropped check is tested in both
directions:

* **too short** — the actor state the check exists to refuse is constructed, and
  the endpoint must still refuse it or have a deadlock that excuses it;
* **too long** — the journey is walked end to end from a fresh account, which
  is the only thing that catches a retained check the student cannot yet
  satisfy. A list one entry too *long* locks a real student out of becoming
  ACTIVE, and no enumeration of lists on either side would show it.
"""

import uuid

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db

#: §2.5's preconditions, in its order, with the code each produces. Transcribed
#: from the contract table, not from `services.require_actor`.
PRECONDITIONS = {
    "status": ("SUSPENDED", 403),
    "adult": ("NOT_ADULT_VERIFIED", 403),
    "campus": ("NOT_CAMPUS_VERIFIED", 403),
    "consent": ("CONSENT_REQUIRED", 403),
}

#: §5.1: the order in which a student can legitimately still owe a step.
JOURNEY_ORDER = ("age", "consent", "campus")

#: Every write in §5.1's left-hand column, with the body and key it needs. A
#: write is any method §4.1 requires an `Idempotency-Key` on, plus the two
#: statutory-right endpoints.
WRITES = {
    "age": ("POST", "/api/v1/account/age-declaration", {"date_of_birth": "2000-01-01"}),
    "consent_grant": ("PUT", "/api/v1/account/consents/account", {"granted": True}),
    "consent_withdraw": ("PUT", "/api/v1/account/consents/account", {"granted": False}),
    "locale": ("PATCH", "/api/v1/account", {"locale": "en"}),
    "profile": ("PATCH", "/api/v1/account", {"display_name": "New Name"}),
    "export": ("GET", "/api/v1/account/export", None),
    "nominee": ("POST", "/api/v1/account/nominee",
                {"nominee": {"name": "A Nominee", "email": "n@example.test"}}),
    "erase": ("POST", "/api/v1/account/erase", {"confirm": True}),
}


def _call(client, name, user=None):
    method, path, body = WRITES[name]
    headers = {}
    kwargs = {}
    if method != "GET":
        headers["Idempotency-Key"] = str(uuid.uuid4())
        kwargs = {"data": body, "content_type": "application/json"}
    return getattr(client, method.lower())(path, headers=headers, **kwargs)


def _code(response):
    try:
        return response.json().get("error", {}).get("code")
    except Exception:  # noqa: BLE001 - a non-JSON body is itself the answer
        return None


@pytest.fixture
def campus(db):
    from apps.core.models import Campus, City

    city = City.objects.create(name="Chennai", state="Tamil Nadu")
    return Campus.objects.create(
        city=city, name="Matrix Campus", slug="matrix",
        email_domains=["example.test"],
    )


@pytest.fixture
def make_user(campus):
    from apps.accounts.models import User

    def build(**overrides):
        fields = dict(
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            display_name="A Student",
            campus=campus, city=campus.city, status="ACTIVE",
            adult_verified=True, campus_verified=True,
            email_verified_at=timezone.now(),
        )
        fields.update(overrides)
        return User.objects.create(**fields)

    return build


@pytest.fixture
def sign_in():
    """A **fresh** client per signed-in user.

    Reusing one client across users is how QA's first draft of this file
    measured nonsense: `client.session` mints a new key on each save while the
    cookie still points at the first, so every actor after the first was
    anonymous and every endpoint answered 401. A fixture that returns a new
    client makes the actor the only variable.
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


@pytest.fixture(autouse=True)
def published_notices(db):
    """DATA-MODEL §2: a consent row names the notice version agreed to, so a
    published PRIVACY notice is a precondition of the fixture rather than of
    the contract. Created here so the matrix measures §2.5 and not this."""
    import hashlib

    from apps.accounts.models import NoticeVersion

    for kind in ("PRIVACY", "TERMS", "SELLER_TERMS"):
        body = f"{kind} notice for the precondition matrix."
        NoticeVersion.objects.get_or_create(
            kind=kind, version=1, locale="en",
            defaults={
                "body_md": body,
                "sha256": hashlib.sha256(body.encode()).hexdigest(),
                "published_at": timezone.now(),
            },
        )


def _grant_required_consents(user):
    from apps.accounts.models import NoticeVersion
    from apps.accounts.services import REQUIRED_CONSENT_PURPOSES, grant_consent

    notice = NoticeVersion.objects.filter(kind="PRIVACY").order_by("-id").first()
    for purpose in REQUIRED_CONSENT_PURPOSES:
        grant_consent(user, purpose, notice, "SIGNUP_FORM", None, "qa")
    return user


# --------------------------------------------------------------------------
# 1. precondition 1 — the one no endpoint may drop
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(WRITES))
def test_every_write_refuses_an_unauthenticated_caller(client, name):
    """§2.5 precondition 1. The only precondition with **no** legitimate reason
    to be narrowed anywhere, on any endpoint, ever — including the statutory
    rights, because s11 and s12 are rights of an identified data principal.
    """
    response = _call(client, name)
    assert response.status_code == 401, (
        f"{name} answered {response.status_code} without a session"
    )
    assert _code(response) == "NOT_AUTHENTICATED"


# --------------------------------------------------------------------------
# 2. the two stacks, derived from the contract's own membership table
# --------------------------------------------------------------------------

#: API-CONTRACT §2.5 **as amended**, transcribed from its membership table. The
#: amendment is the cto ruling that *"a right that a precondition can switch
#: off is not a right"*, and the table is the contract's statement of which
#: endpoint is which. QA transcribes the table rather than reading the code's
#: stacks, because whether those two agree is the whole question.
STACK = {
    # The table lists the *endpoint*; two of them are split finer than that,
    # and the split is in the contract's own prose rather than in the table —
    # which is why QA reads both. Getting this wrong is how the first draft of
    # this file reported four phantom findings.
    "consent_withdraw": "S",  # "withdrawal above all" (DPDP r.3(c)(i):
                              # as easy as granting)
    "export": "S",            # table: s11
    "erase": "S",             # table: s12(3)
    "nominee": "S",           # table: s14
    "locale": "S",            # "PATCH /account for `locale` only"
    "profile": "M",           # "PATCH /account for display_name"
    # Granting a marketplace consent is not a right being exercised — it is the
    # student taking on a marketplace capability — so it is Stack M **minus the
    # consent limb this endpoint establishes**. The contract's table does not
    # say this; the code does, and QA agrees with it. Excluded from both strict
    # tests and covered by the journey walk.
    "consent_grant": "M-minus-consent",
    # `POST /account/age-declaration` appears in neither list, so it falls under
    # the table's "everything else" — Stack M, minus the `adult` limb it exists
    # to establish, and minus consent, which §5.1 orders after it. Also excluded
    # and also covered by the walk.
    "age": "M-minus-adult",
}

#: §2.5 Stack S precondition 2, verbatim: **`status <> 'TOMBSTONED'` → else
#: `401` (not 403 — the account is gone; see DATA-MODEL §10.1 layer 2)**.
TOMBSTONED_EXPECTED = (401, "NOT_AUTHENTICATED")


@pytest.mark.parametrize("name", sorted(n for n in WRITES if STACK[n] == "M"))
@pytest.mark.parametrize("precondition", ["status", "adult", "campus", "consent"])
def test_a_stack_m_write_refuses_every_precondition_in_the_contracts_order(
    make_user, sign_in, name, precondition
):
    """Stack M, as §2.5 lists it. Each precondition violated on its own, so a
    failing cell names the single check that was missing rather than whichever
    one happened to run first."""
    overrides = {}
    if precondition == "status":
        overrides["status"] = "SUSPENDED"
    if precondition == "adult":
        overrides["adult_verified"] = False
    if precondition == "campus":
        overrides["campus_verified"] = False
    user = make_user(**overrides)
    if precondition != "consent":
        _grant_required_consents(user)

    response = _call(sign_in(user), name)
    code, status = PRECONDITIONS[precondition]
    assert (response.status_code, _code(response)) == (status, code), (
        f"{name} is Stack M, so §2.5 requires {status} {code} for a failing "
        f"`{precondition}`; got {response.status_code} {_code(response)}. A "
        "Stack M list one entry short grants a marketplace write to an actor "
        "the contract refuses."
    )


@pytest.mark.parametrize("name", sorted(n for n in WRITES if STACK[n] == "S"))
@pytest.mark.parametrize("precondition", ["status", "adult", "campus", "consent"])
def test_a_stack_s_right_is_not_switched_off_by_any_marketplace_precondition(
    make_user, sign_in, name, precondition
):
    """**Stack S — and this is the direction no enumeration of the code's lists
    can catch.**

    §2.5 as amended: *"And nothing else. Not `ACTIVE`, not `adult_verified`,
    not `campus_verified`, not consent, not the discovery gate."* So a Stack S
    endpoint must still serve an actor failing any of those four.

    A Stack S list one entry too **long** denies a suspended student their s11
    export or their s12(3) erasure — the defect the amendment exists to
    prevent, and one a test enumerating the code's own lists would agree with
    rather than catch.
    """
    overrides = {}
    if precondition == "status":
        overrides["status"] = "SUSPENDED"
    if precondition == "adult":
        overrides["adult_verified"] = False
    if precondition == "campus":
        overrides["campus_verified"] = False
    user = make_user(**overrides)
    if precondition != "consent":
        _grant_required_consents(user)

    response = _call(sign_in(user), name)
    assert response.status_code not in (401, 403), (
        f"{name} is Stack S in §2.5's table and it refused an actor failing "
        f"`{precondition}` with {response.status_code} {_code(response)}. "
        "§2.5: 'A right that a precondition can switch off is not a right.'\n"
        "\nFINDING F23 if this is `nominee`: §2.5's table lists "
        "`POST /account/nominee (s14)` in Stack S, and `apps/accounts/api.py` "
        "runs `_may_write(user)` on it — the full Stack M. So a suspended, "
        "unverified or unconsented student cannot exercise their s14 "
        "nomination. The contract table and the code disagree, and this is the "
        "shape backend asked QA to look for: the list is one entry short at the "
        "stack level rather than within a stack, and a test enumerating the "
        "code's stacks agrees with the code."
    )


@pytest.mark.parametrize("name", sorted(WRITES))
def test_a_tombstoned_actor_is_refused_as_gone_rather_than_as_forbidden(
    make_user, sign_in, name
):
    """§2.5 Stack S precondition 2 is explicit about the code and about why:
    **401, not 403** — *"the account is gone"*.

    Not cosmetic. `403` says the caller is authenticated and not permitted,
    which confirms the account still exists; `401` says there is nothing behind
    this session, which is the true statement after erasure and what
    `DATA-MODEL.md` §10.1 layer 2 is about.
    """
    user = make_user(status="TOMBSTONED")
    response = _call(sign_in(user), name)
    assert (response.status_code, _code(response)) == TOMBSTONED_EXPECTED, (
        f"{name} answered {response.status_code} {_code(response)} to a "
        f"tombstoned actor; §2.5 Stack S specifies {TOMBSTONED_EXPECTED}, and "
        "says in the same line that 403 is the wrong answer."
    )


def test_the_patch_split_follows_the_field_and_not_the_endpoint(make_user, sign_in):
    """§2.5's table splits one endpoint across both stacks: `PATCH /account` is
    **S for `locale` only** and **M for `display_name`**.

    That is the placement most likely to be implemented as "whichever stack the
    endpoint is in", so it is asserted from both sides on a suspended actor.
    §2.5's reasoning is worth keeping beside the test: correction is a
    statutory right, but *"not a right to a public-facing handle while
    suspended — changing the name counterparties recognise is an evasion vector
    after a safety report."*
    """
    user = _grant_required_consents(make_user(status="SUSPENDED"))

    locale = _call(sign_in(user), "locale")
    assert locale.status_code == 200, (
        "a suspended student cannot change their locale, which §2.5 puts in "
        f"Stack S: {locale.status_code} {_code(locale)}"
    )

    renamed = _call(sign_in(user), "profile")
    assert (renamed.status_code, _code(renamed)) == (403, "SUSPENDED"), (
        "a suspended student changed their display_name, which §2.5 puts in "
        f"Stack M: {renamed.status_code} {_code(renamed)}"
    )


def test_both_fields_at_once_takes_the_stricter_stack(make_user, sign_in):
    """The both-at-once case, which is where a field-to-stack map goes wrong: a
    body carrying `locale` **and** `display_name` must take Stack M, or a
    suspended student renames themselves by sending a locale alongside it."""
    user = _grant_required_consents(make_user(status="SUSPENDED"))
    client = sign_in(user)
    response = client.patch(
        "/api/v1/account",
        data={"locale": "en", "display_name": "Evasion"},
        content_type="application/json",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert (response.status_code, _code(response)) == (403, "SUSPENDED"), (
        "a body with both fields was served under Stack S, so a suspended "
        "student can rename themselves by including a locale: "
        f"{response.status_code} {_code(response)}"
    )
    user.refresh_from_db()
    assert user.display_name != "Evasion"


# --------------------------------------------------------------------------
# 4. the direction no enumeration of lists can catch
# --------------------------------------------------------------------------


def test_a_fresh_student_can_walk_the_whole_journey_without_being_refused(
    campus, sign_in
):
    """**The deadlock test.** §5.1's `needs` order is age then consent then
    campus. If any endpoint retains a precondition the student cannot yet
    satisfy they can never become ACTIVE — and every enumeration of the check
    lists on both sides would still pass, because the lists would agree with
    each other and with the tests derived from them.
    """
    from apps.accounts.models import User
    from apps.accounts.services import outstanding_steps

    user = User.objects.create(
        email="fresh@example.test", display_name="Fresh",
        campus=campus, city=campus.city, status="PENDING_VERIFICATION",
        adult_verified=False, campus_verified=True,
        email_verified_at=timezone.now(),
    )

    steps = outstanding_steps(user)
    assert steps, "fixture error: a fresh student should owe at least one step"
    assert [s for s in JOURNEY_ORDER if s in steps] == steps, (
        f"outstanding_steps is not in §5.1's order: {steps}"
    )

    for step in steps:
        if step == "campus":
            continue  # evidenced at sign-in; see the finding below
        response = _call(sign_in(user), "age" if step == "age" else "consent_grant")
        assert response.status_code < 400, (
            f"a fresh student was refused at step {step!r} with "
            f"{response.status_code} {_code(response)}. That endpoint's "
            "precondition list is one entry too long and the student can never "
            f"become ACTIVE. Outstanding at that point: {steps}"
        )
        user.refresh_from_db()


def test_finding_the_campus_step_in_the_contract_cannot_occur(campus):
    """**FINDING F22, low severity.** §5.1 specifies
    `needs: ["age", "consent", "campus"]`, so the contract describes a
    signed-in student who still owes campus verification. Measured:
    `consume_magic_link` sets `campus_verified = True` for **every** user it
    signs in — *"the domain match is the evidence"* (ADR-001 §2.5) — so after a
    successful consume that entry can never appear.

    Worth one word in the contract rather than a reader inferring a screen that
    does not exist. Recorded here because the walk above skips that step for
    the same reason, and a skipped step in a journey test should never be
    silent.
    """
    import inspect

    from apps.accounts import services
    from apps.accounts.models import User

    user = User.objects.create(
        email="nocampus@example.test", display_name="No Campus",
        campus=campus, city=campus.city, status="ACTIVE",
        adult_verified=True, campus_verified=False,
    )
    assert "campus" in services.outstanding_steps(user)  # representable
    assert "campus_verified = True" in inspect.getsource(services.consume_magic_link), (
        "consume no longer verifies campus unconditionally, so the `campus` "
        "step is reachable and the journey walk must stop skipping it"
    )


# --------------------------------------------------------------------------
# 5. the guard on this file
# --------------------------------------------------------------------------


def test_every_write_in_the_contract_is_in_this_matrix():
    """`CLAUDE.md` rule 12 applied to the matrix itself: a write that is not in
    `WRITES` is a write this file silently does not check, and the whole value
    of the file is that it is exhaustive.

    Derived from the URLconf rather than from a list, so S2's listing writes and
    S4's offer writes appear here as a failure the day they are mounted — which
    is what `_may_write`'s docstring says those slices inherit.
    """
    from django.urls import get_resolver

    mounted = set()

    def walk(patterns, prefix=""):
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                walk(pattern.url_patterns, prefix + str(pattern.pattern))
            else:
                mounted.add(prefix + str(pattern.pattern))

    walk(get_resolver().url_patterns)
    api_routes = {r for r in mounted if r.startswith("api/v1/")}

    #: Reads and anonymous endpoints, which §2.5 does not govern as writes.
    not_writes = {
        "api/v1/auth/magic-link",      # anonymous by §5.1
        "api/v1/auth/consume",         # anonymous by §5.1
        "api/v1/auth/logout",          # a session teardown, not a data write
        "api/v1/account",              # also GET; the PATCH is in WRITES
        "api/v1/account/consents",     # GET, the read half of §5.1
        "api/v1/notices/<str:kind>",   # public notice text
    }
    covered = {
        "api/v1/account/age-declaration",
        "api/v1/account/consents/<str:purpose_key>",
        "api/v1/account/export",
        "api/v1/account/nominee",
        "api/v1/account/erase",
        "api/v1/account",
    }
    missing = api_routes - not_writes - covered
    assert missing == set(), (
        f"L2 routes not covered by this precondition matrix: {sorted(missing)}. "
        "Each needs a row in WRITES and a derivation of which §2.5 checks it "
        "may narrow, or it is a write nobody has checked §2.5 against."
    )
