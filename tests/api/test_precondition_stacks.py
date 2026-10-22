"""API-CONTRACT §2.5 as **two stacks** — the cto ruling after S1's escalation.

**Stack M** keeps all eight preconditions, for marketplace writes.
**Stack S** is authenticated + not-tombstoned + idempotency and **nothing
else** — not `ACTIVE`, not adult, not campus-verified, not consent, not the
gate. Export, erasure, consent withdrawal, correction and locale sit in S.

The reasoning, kept here because it is what stops the list being "hardened"
back: *a right that a precondition can switch off is not a right*. And **the
defect was wider than suspension** — a student who never completed campus
verification and wanted their data deleted would have been refused erasure by
a verification check. That is the case that makes this a stack rather than an
exception, and it is the first thing this file tests.
"""

import json
import uuid

import pytest

from apps.accounts.sessions import SESSION_USER_KEY

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.urls_api_only")]


def sign_in(client, user):
    session = client.session
    session[SESSION_USER_KEY] = user.id
    session.save()
    return user


def post(client, path, body=None):
    return client.post(
        path, data=json.dumps(body or {}), content_type="application/json",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )


def put(client, path, body):
    return client.put(
        path, data=json.dumps(body), content_type="application/json",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )


def patch(client, path, body):
    return client.patch(
        path, data=json.dumps(body), content_type="application/json",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )


# --- Stack S survives every precondition ---------------------------------


@pytest.mark.parametrize(
    "state,why",
    [
        ({"status": "SUSPENDED"}, "suspension must not remove a statutory right"),
        ({"campus_verified": False},
         "the case that makes this a stack: a student who never finished campus "
         "verification and wants their data"),
        ({"adult_verified": False}, "an unconfirmed age must not block an export"),
        ({"status": "PENDING_VERIFICATION", "campus_verified": False,
          "adult_verified": False}, "mid-signup, nothing satisfied"),
    ],
)
def test_the_export_right_survives_every_precondition(client, student, state, why, salt):
    for field, value in state.items():
        setattr(student, field, value)
    student.save()
    sign_in(client, student)
    assert client.get("/api/v1/account/export").status_code == 200, why


@pytest.mark.parametrize(
    "state,why",
    [
        ({"status": "SUSPENDED"}, "s12 erasure, suspended"),
        ({"campus_verified": False}, "s12 erasure, never campus-verified"),
        ({"adult_verified": False}, "s12 erasure, age not confirmed"),
    ],
)
def test_the_erasure_right_survives_every_precondition(client, student, state, why, salt):
    for field, value in state.items():
        setattr(student, field, value)
    student.save()
    sign_in(client, student)
    assert post(client, "/api/v1/account/erase").status_code == 200, why


@pytest.mark.parametrize("state", [{"status": "SUSPENDED"}, {"campus_verified": False}])
def test_consent_withdrawal_survives_every_precondition(client, student, state, privacy_notice):
    """DPDP r.3(c)(i). Withdrawal is the direction the ruling names."""
    for field, value in state.items():
        setattr(student, field, value)
    student.save()
    sign_in(client, student)
    response = put(client, "/api/v1/account/consents/account", {"granted": False})
    assert response.status_code == 200, response.content
    assert json.loads(response.content)["granted"] is False


@pytest.mark.parametrize("state", [{"status": "SUSPENDED"}, {"campus_verified": False}])
def test_changing_locale_survives_every_precondition(client, student, state):
    """Which language the product speaks to you in is not a marketplace action
    and cannot be a lever."""
    for field, value in state.items():
        setattr(student, field, value)
    student.save()
    sign_in(client, student)
    assert patch(client, "/api/v1/account", {"locale": "en"}).status_code == 200


# --- Stack M still refuses ------------------------------------------------


def test_a_suspended_student_cannot_change_their_public_handle(client, student):
    """**The judgement call, as a test.** Correction is a statutory right; it
    is not a right to a public-facing handle while suspended, because changing
    the name counterparties recognise is an evasion vector after a safety
    report. The right is served by a staff-reviewed correction endpoint."""
    student.status = "SUSPENDED"
    student.save()
    sign_in(client, student)
    response = patch(client, "/api/v1/account", {"display_name": "Someone Else"})
    assert response.status_code == 403
    assert json.loads(response.content)["error"]["code"] == "SUSPENDED"
    student.refresh_from_db()
    assert student.display_name == "Priya R"


def test_the_stricter_stack_wins_when_both_fields_are_sent(client, student):
    """The both-at-once case, which is where a field-by-field branch goes
    wrong: a suspended student must not slip a `display_name` through by
    attaching a `locale` to it."""
    student.status = "SUSPENDED"
    student.save()
    sign_in(client, student)
    response = patch(client, "/api/v1/account", {"display_name": "Evader", "locale": "en"})
    assert response.status_code == 403
    student.refresh_from_db()
    assert student.display_name == "Priya R"


def test_a_suspended_student_cannot_grant_a_new_consent(client, student, privacy_notice):
    """Granting is **Stack M**: not a right being exercised but processing
    being enabled. r.3(c)(i)'s "as easy as granting" is mechanism parity —
    same route, same shape — not a shared authorization, and reading it the
    other way would make the easier direction the one that unlocks things."""
    student.status = "SUSPENDED"
    student.save()
    sign_in(client, student)
    assert put(client, "/api/v1/account/consents/chat", {"granted": True}).status_code == 403


def test_signup_is_not_deadlocked_by_the_grant_stack(client, pending_student, privacy_notice):
    """The grant stack drops the consent limb this endpoint establishes. A
    student mid-signup has granted nothing yet, so requiring it would make
    JOURNEYS J1 step 5 unreachable."""
    pending_student.adult_verified = True
    pending_student.save()
    sign_in(client, pending_student)
    assert put(client, "/api/v1/account/consents/account", {"granted": True}).status_code == 200


# --- the warning: the tombstoned check is tombstoned-only -----------------


def test_the_tombstoned_check_refuses_only_tombstoned(student):
    """**The warning attached to the ruling, as a test.**

    `require_actor` refuses a TOMBSTONED principal unconditionally, outside
    `checks`, because Stack S is "authenticated + **not tombstoned**". If that
    check were ever hardened to also refuse SUSPENDED it would **silently
    re-create the bypass in the one place no endpoint-level review would
    look**: every Stack S endpoint would start refusing a suspended student
    their export, their erasure, their consent withdrawal and their appeal,
    and not one endpoint's own code would have changed.
    """
    from apps.accounts.services import STACK_S, require_actor
    from apps.core.errors import Suspended

    student.status = "SUSPENDED"
    student.save()
    assert require_actor(student, checks=STACK_S) is student, (
        "the unconditional check now refuses SUSPENDED; every Stack S right is "
        "switched off and no endpoint changed"
    )

    student.status = "TOMBSTONED"
    student.save()
    with pytest.raises(Suspended):
        require_actor(student, checks=STACK_S)


def test_session_user_excludes_tombstoned_and_not_suspended(client, student):
    """The same warning at the other layer. `session_user` is the second,
    independent guarantee that a deleted account cannot act — and it must not
    grow a SUSPENDED exclusion, or a suspended student is signed out of the
    appeal channel they are owed."""
    from django.test import RequestFactory

    from apps.accounts.sessions import session_user

    student.status = "SUSPENDED"
    student.save()
    session = client.session
    session[SESSION_USER_KEY] = student.id
    session.save()

    request = RequestFactory().get("/")
    request.session = client.session
    assert session_user(request) is not None, (
        "a suspended student is signed out, which removes their export, "
        "erasure, withdrawal and appeal in one line"
    )


def test_the_two_stacks_are_declared_and_differ():
    """The stacks as data, so a reader sees both at once. Stack S is empty by
    construction: every name added to it is a precondition a right would be
    subject to."""
    from apps.accounts.services import ACTOR_CHECKS, STACK_M, STACK_S

    assert STACK_S == ()
    assert STACK_M == ACTOR_CHECKS
    assert set(STACK_M) == {"status", "adult", "campus", "consent"}


# --- derived from the contract, not from the code ------------------------


def contract_stack_rows():
    """§2.5's Stack table, parsed out of `API-CONTRACT.md`.

    **This is the fix for the failure mode that bit twice in one slice.** My
    other tests enumerate the stacks *the code declares*, so they agree with
    the code by construction and stayed green through two wrong placements of
    `POST /account/nominee`. QA found it in one pass because it derived
    membership from **the table**, which is the normative list — I had read
    the ruling's prose summary, which names five examples.

    A test written from the implementation cannot discover that the
    implementation read the wrong document. So this one reads the document.
    """
    import pathlib as _p
    import re

    contract = (
        _p.Path(__file__).resolve().parents[2]
        / "company" / "architecture" / "API-CONTRACT.md"
    ).read_text(encoding="utf-8")
    rows = {}
    for stack in ("S", "M"):
        match = re.search(rf"^\|\s*\*\*{stack}\*\*\s*\|(.+?)\|\s*$", contract, re.M)
        assert match, f"§2.5's Stack {stack} row is not in API-CONTRACT.md"
        rows[stack] = match.group(1)
    return rows


def test_the_contract_table_is_readable_and_names_both_stacks():
    """`CLAUDE.md` rule 12: a parser that matches nothing would make every
    assertion below vacuous."""
    rows = contract_stack_rows()
    assert "/account/export" in rows["S"]
    assert "display_name" in rows["M"]
    assert len(rows["S"]) > 200 and len(rows["M"]) > 100


#: Contract endpoint string -> the handler implementing it, for the Stack S
#: entries **S1 ships**. Every other entry in the row belongs to a later
#: slice and is listed in `STACK_S_LATER_SLICES` — so the two together must
#: account for *everything the table contains*, and a sixth entry added to
#: §2.5 lands in neither and fails.
STACK_S_HANDLERS = {
    "POST /auth/logout": "logout",
    "GET /account": "account",
    # Listed in the row as **"for `locale` only"** — the field split, which
    # `account()` implements by taking Stack S unconditionally and adding the
    # marketplace gate only when a Stack M field is present.
    "PATCH /account": "account",
    "GET /account/export": "export",
    "POST /account/erase": "erase",
    "PUT /account/consents/{purpose_key}": "set_consent",
    "POST /account/nominee": "nominee",
    "GET /legal/{kind}": "notice",
}

#: Stack S endpoints whose tables do not exist yet, with the slice. Not an
#: excuse list: `test_the_stack_s_row_is_fully_accounted_for` requires every
#: token in the row to be in one map or the other.
STACK_S_LATER_SLICES = {
    "POST /account/correction": "S6 — staff-reviewed correction queue",
    "POST /grievances": "S6",
    "POST /reports": "S6 — safety categories only",
    "GET /help": "S5",
    "GET /help/{id}": "S5",
    "POST /help/{id}/reply": "S5",
}


def stack_s_endpoint_tokens():
    """Every endpoint token in §2.5's Stack S row, extracted from the table.

    **Extracted, not typed.** The previous version parametrised over a
    four-element literal I had chosen, so it validated four names rather than
    enumerating the row — and *a fifth Stack S endpoint added to §2.5 would
    have gone unnoticed*, which is precisely the failure this file exists to
    prevent. Same defect as the nominee placement, one level up.
    """
    import re

    row = contract_stack_rows()["S"]
    tokens = set()
    for code in re.findall(r"`([^`]+)`", row):
        code = code.strip()
        if re.match(r"^(GET|POST|PUT|PATCH|DELETE) ", code) or code.startswith("/"):
            tokens.add(code)
    return tokens


def test_the_stack_s_row_is_fully_accounted_for():
    """**The enumeration, with a count floor.** Every endpoint token in the
    row is either implemented and gated, or recorded against the slice that
    will implement it. A new entry lands in neither map and fails here."""
    tokens = stack_s_endpoint_tokens()
    assert len(tokens) >= 10, (
        f"only {len(tokens)} endpoint tokens extracted from §2.5's Stack S row "
        f"({sorted(tokens)}); the parser has stopped reading the table"
    )
    known = set(STACK_S_HANDLERS) | set(STACK_S_LATER_SLICES)
    unaccounted = sorted(tokens - known)
    assert unaccounted == [], (
        "§2.5's Stack S row contains endpoints this test does not account for. "
        "Either S1 implements one and it needs a STACK_S_HANDLERS entry with a "
        "gate, or a later slice does and it needs a STACK_S_LATER_SLICES entry "
        f"naming that slice: {unaccounted}"
    )


def test_no_mapped_endpoint_has_left_the_stack_s_row():
    """The other direction: a handler still gated as Stack S after the table
    moved it to M would be a permission nobody granted."""
    tokens = stack_s_endpoint_tokens()
    for endpoint_text in sorted(STACK_S_HANDLERS):
        assert endpoint_text in tokens, (
            f"{endpoint_text} is gated as Stack S but is no longer in §2.5's "
            "Stack S row"
        )


@pytest.mark.parametrize("endpoint_text", sorted(STACK_S_HANDLERS))
def test_every_stack_s_endpoint_in_the_contract_uses_the_stack_s_gate(endpoint_text):
    """The assertion that would have caught the nominee placement, in
    backend's own tree, on the first wrong move rather than the second."""
    import inspect

    from apps.accounts import api

    handler = STACK_S_HANDLERS[endpoint_text]
    body = inspect.getsource(getattr(api, handler))

    if handler == "notice":
        # Public and unauthenticated — there is no actor to gate (r.4(2)).
        assert "require_safe" in body
        return

    if handler == "set_consent":
        # The row says *"**withdrawal above all**"*, and this endpoint carries
        # both directions. Asserted as the **property** rather than by looking
        # for a token: the withdrawal direction's check list must be exactly
        # Stack S. A token match would pass on a handler that mentioned
        # `_stack_s` in a comment and gated neither direction.
        from apps.accounts.api import CONSENT_DIRECTION_STACKS
        from apps.accounts.services import STACK_S

        assert CONSENT_DIRECTION_STACKS[False] == STACK_S, (
            "withdrawing consent is not on Stack S; DPDP r.3(c)(i) and §2.5 "
            "both put it there, and it is the direction the ruling names"
        )
        assert "CONSENT_DIRECTION_STACKS[" in body
        return

    assert "_stack_s(" in body, (
        f"§2.5's table puts {endpoint_text} in Stack S and {handler}() does not "
        "call the Stack S gate. The table is normative; the prose summary names "
        "examples."
    )


def test_the_suspended_body_names_what_is_still_open():
    """§2.5: *"A suspension that tells someone only 'no' is the failure this
    amendment exists to prevent."* The four doors are the Stack S ones a
    suspension does not close."""
    from apps.accounts.services import SUSPENDED_MESSAGE, SUSPENDED_STILL_AVAILABLE

    assert len(SUSPENDED_STILL_AVAILABLE) == 4
    for door in ("data", "delete", "withdraw", "help"):
        assert door in SUSPENDED_MESSAGE.lower(), f"the body does not mention {door}"
    assert SUSPENDED_MESSAGE.rstrip().endswith(".")


def test_a_suspended_student_is_told_what_is_still_open(client, student):
    """End to end, because a message that exists in a constant and never
    reaches a response is the shape `require_actor` itself had."""
    student.status = "SUSPENDED"
    student.save()
    sign_in(client, student)
    body = json.loads(patch(client, "/api/v1/account", {"display_name": "X"}).content)
    assert body["error"]["code"] == "SUSPENDED"
    assert "still" in body["error"]["message"].lower()
    assert "delete your account" in body["error"]["message"]


#: handler -> the exact token its body must contain to count as placed.
#:
#: **Corrected: `age_declaration` said `_stack_s` and the code calls
#: `_may_write`.** The map was wrong, not the code — §2.5's Stack S row does
#: not list `POST /account/age-declaration` and the M row is "everything
#: else", so age declaration is Stack M minus the two preconditions that would
#: deadlock it. The mismatch survived because the assertion below used to read
#: `expected in body or expected in source`, and `source` is the whole module,
#: so **every expected token was present by definition** and the per-handler
#: check could never fail. Three characters, and they made the guard against
#: the authorization bypass silent about a live mismatch.
HANDLER_GATES = {
    "magic_link": None,          # anonymous (§5.1: always 202)
    "consume": None,             # anonymous
    "logout": "_stack_s(",
    "age_declaration": "_may_write(",
    "consents": "_signed_in(",   # a read
    "set_consent": "CONSENT_DIRECTION_STACKS[",
    "account": "_stack_s(",      # plus _may_write for the display_name field
    "export": "_stack_s(",
    "nominee": "_stack_s(",
    "erase": "_stack_s(",
    # **S2, and it is the endpoint §2.5 named twice and nobody built.**
    # Stack S: s12(1)-(2) correction is a statutory right, so a suspended
    # student, one who never finished campus verification and one who
    # withdrew every optional consent can all reach it. It is also what makes
    # `display_name` sitting in Stack M defensible — QA-S1 F24 measured that
    # the justification was unbuilt, which is why the route being placed here
    # matters as much as the route existing.
    "correction": "_stack_s(",
    "notice": None,              # public, unauthenticated (r.4(2))
}


def test_every_s1_endpoint_declares_a_stack():
    """`CLAUDE.md` rule 9 on the placement itself: an endpoint that calls
    neither gate is one nobody placed, and the failure mode is silence.

    Each handler's **own body** is read — no module-wide fallback. That `or`
    is what made this guard vacuous.
    """
    import inspect

    from apps.accounts import api

    for name, expected in sorted(HANDLER_GATES.items()):
        assert hasattr(api, name), f"API-CONTRACT §5.1 names {name} and it is absent"
        if expected is None:
            continue
        body = inspect.getsource(getattr(api, name))
        assert expected in body, (
            f"{name}() does not call {expected!r}; an endpoint nobody placed is "
            "the shape REVIEW-S1 B3 had"
        )


def test_the_handler_map_covers_every_route_in_the_urlconf():
    """The map's own guard. A handler absent from `HANDLER_GATES` is one this
    file does not check, which is how the next endpoint ships unplaced."""
    from apps.accounts import urls

    routed = {pattern.callback.__name__ for pattern in urls.urlpatterns}
    missing = sorted(routed - set(HANDLER_GATES))
    assert missing == [], (
        f"these routed handlers have no entry in HANDLER_GATES: {missing}"
    )


def test_the_placement_guard_can_actually_fail():
    """`CLAUDE.md` rule 12, and the reason this test exists at all: the
    assertion above was green for two wrong placements because of one `or`.
    So prove the predicate rejects a body that calls the wrong gate."""
    import inspect

    from apps.accounts import api

    body = inspect.getsource(api.export)
    assert "_stack_s(" in body
    assert "_may_write(" not in body, (
        "export calls the marketplace gate; §2.5's table puts it in Stack S"
    )
