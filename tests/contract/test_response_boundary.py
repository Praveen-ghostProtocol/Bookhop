"""The response-schema control, attacked the way the schema guard was attacked.

`tests/unit/test_forbidden_response.py` is not an ordinary test. ADR-003 §5.3
and §5.3.1 make it **the compensating control for the two residuals P14 cannot
close** — a number inside a jsonb document and a number inside free text — and
THREAT-MODEL §6 states what it must assert:

> *"**No response anywhere carries a forbidden key, a money-shaped key, a
> contact detail or an amount.**" — ADR-003 §5.3's compensating control.*

ADR-003 §5.3.1 goes further and **adopts QA's conformance detectors as the gate
on its own prose**: *"the packet sentence may only name a control that a test
proves exists … §5.3 cannot claim a control the repository does not have."* It
also states that nobody may quote §5.3's stronger G4 sentence until those
detectors are green.

So this file does two jobs, and keeps them apart:

1. **Attack the walker** — does it catch what it claims to catch, at depth, and
   does it stay quiet on the names three frozen contracts mandate?
2. **Be the gate ADR-003 §5.3.1 asked for** — measure which of the four limbs
   THREAT-MODEL §6 names are actually implemented, so the G4 sentence cannot
   outrun the code again. That is `CLAUDE.md` rule 9 applied to this control.

Written from THREAT-MODEL §6, ADR-003 §2.3 and §5.3/§5.3.1 — not from the
implementation, which QA read only to call `forbidden_keys_in` correctly.
"""

import importlib

import pytest

pytestmark = pytest.mark.django_db


def control():
    """The shipped response guard. Skips loudly if it cannot be read."""
    try:
        return importlib.import_module("tests.unit.test_forbidden_response")
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"cannot load the response-schema control: {exc!r}")


def walk(payload):
    return control().forbidden_keys_in(payload)


# --------------------------------------------------------------------------
# 1. the recursion claim — verified in behaviour, then in the code
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload,expected,why",
    [
        ({"settled_price": 1}, "settled_price", "depth 1, the obvious case"),
        ({"job": {"payload": {"paid": 1}}}, "job.payload.paid",
         "the jsonb limb: a nested document, which is the shape the control exists for"),
        ({"a": {"b": {"c": {"d": {"e": {"cash_total": 1}}}}}}, "cash_total",
         "depth 6 — deeper than the control's own guard goes"),
        ({"items": [{"consideration_paise": 1}]}, "items[0].consideration_paise",
         "a list of objects, which every cursor-paginated response is"),
        ({"items": [[{"amt": 1}]]}, "amt", "a list inside a list"),
        ({"a": [{"b": [{"c": {"rupees_exchanged": 1}}]}]}, "rupees_exchanged",
         "lists and dicts alternating"),
        ({"meta": {"nested": {"deeper": {"tender": 1}}}}, "tender",
         "a token only the widened W1b set carries"),
    ],
)
def test_the_walker_recurses_into_every_container_shape(payload, expected, why):
    """**Backend's reasoning, verified: it holds.**

    The stated reason for making the walker recursive is that *"the jsonb limb
    of P14 is a nested document, so a walker that only inspected top-level keys
    would miss the one shape this control exists for."* That is correct, and it
    is the right reason — the residual ADR-003 §2.3 W5 names is specifically a
    value inside `jobs.payload` or `notifications.payload`, which reaches a
    response as a nested object.

    QA derived these cases from the container shapes the API actually produces
    (API-CONTRACT §2.3's `{"items": [...]}` envelope, a jsonb payload, a list of
    lists) rather than re-running the control's own, and went two levels deeper
    than its guard does.
    """
    offenders = walk(payload)
    assert any(expected in offender for offender in offenders), (
        f"{why}: the walker missed {expected!r} — {offenders}"
    )


def test_the_recursion_is_structural_in_the_code_not_only_in_its_results():
    """The behavioural test above could pass on a two-level walker for some of
    its cases. This reads the code's shape: `forbidden_keys_in` must call itself
    for dict values **and** for list elements, or one container type is a hole
    that happens not to be exercised.
    """
    import inspect

    source = inspect.getsource(control().forbidden_keys_in)
    assert source.count("forbidden_keys_in(") >= 2, (
        "the walker recurses in fewer than two places; a dict-only or list-only "
        f"recursion leaves the other container unwalked:\n{source}"
    )
    assert "isinstance(payload, dict)" in source
    assert "list" in source and "tuple" in source


@pytest.mark.parametrize(
    "payload,why",
    [
        ({"ready": True, "checks": {"db": True, "jobs_overdue": 0}}, "/readyz's real body"),
        ({"items": [{"id": 1, "condition": "GOOD"}], "next_cursor": None},
         "API-CONTRACT §2.3's pagination envelope"),
        ({"purge_due_at": None, "act_due_at": None, "disposal_due_at": None},
         "the SLA clocks MONEY_TOKEN_SHAPE_EXEMPTIONS exists for"),
        ({"asking_price_paise": 30000, "price_fixed_at": "2026-11-01T00:00:00Z"},
         "the two permitted names"),
        ({"error": {"code": "GATE_CLOSED", "request_id": "01JB"}},
         "API-CONTRACT §2.2's error shape"),
        ({"needs": ["age", "consent", "campus"]}, "the auth/consume body"),
    ],
)
def test_the_walker_stays_quiet_on_responses_the_contracts_mandate(payload, why):
    """`CLAUDE.md` rule 13: a guard that fires on the contracts it protects gets
    edited, not obeyed. Every shape here is one API-CONTRACT or DATA-MODEL
    requires, including the SLA-clock names and the two permitted money names.
    """
    assert walk(payload) == [], why


def test_the_walker_is_not_vacuous():
    """`CLAUDE.md` rule 12. S0 has two responses and both are small, so the live
    assertions in the shipped control could pass while the walker matched
    nothing at all. One positive and one negative, side by side, rules that out.
    """
    assert walk({"amount": 1}) != []
    assert walk({"ready": True}) == []


def test_the_permitted_key_set_is_the_two_adr_names_and_comes_from_p14():
    """The permitted set must be derived from `apps/core/p14.py`, not retyped —
    `CLAUDE.md` rule 10, which exists because of this project's three-copies
    incident."""
    p14 = importlib.import_module("apps.core.p14")
    assert control().PERMITTED_KEYS == {
        column for _table, column in p14.MONEY_WORDS_EXEMPT
    }
    assert control().PERMITTED_KEYS == {"asking_price_paise", "price_fixed_at"}


# --------------------------------------------------------------------------
# 2. the gate ADR-003 §5.3.1 asked QA to be
# --------------------------------------------------------------------------


def test_finding_the_control_covers_two_of_the_four_limbs_the_spec_names():
    """**FINDING F15, non-blocking, and it belongs to S1 where the control is
    assigned.**

    THREAT-MODEL §6 states the control's job as four limbs: *"No response
    anywhere carries **a forbidden key**, **a money-shaped key**, **a contact
    detail** or **an amount**."* ADR-003 §2.3 W5 says the same, naming it as the
    control that is "extended to amounts, not only contact details".

    Measured. Two limbs are implemented and are good:

    * a forbidden response key name — `price`, `amount`, `total`, `value`;
    * a money-shaped key at any depth, using `apps/core/p14.py`'s token set.

    Two are not implemented, and they are the two that matter for the residuals
    this control compensates for:

    * **an amount as a *value***. `{"handover_note": "Paid Rs 300"}` and
      `{"meta": {"note": "he paid 300 rupees"}}` both pass. ADR-003 §2.3 W5's
      free-text residual **is a value**, so the compensating control does not
      currently reach the thing it compensates for.
    * **a contact detail**. No phone, email or address pattern is checked. That
      limb is also DATA-MODEL §5's "no response anywhere contains a contact
      detail" and is S5's acceptance criterion, so it has a second home — but
      THREAT-MODEL §6 names this file as its owner.

    A third gap, smaller: a **double-encoded** payload —
    `{"payload": "{\\"paid\\": 30000}"}` — is a JSON document inside a string, so
    the walker sees one harmless key. `jobs.payload` is a real jsonb column and
    a serialiser that str()s it would produce exactly this.

    **Why this is not blocking S0.** ADR-003 §5.3.1's own status table assigns
    `test_forbidden_response.py` to **backend, S1**; it has landed early with
    half its scope, which is better than not landing. S0 has two responses and
    neither carries a free-text field or a nested payload. **What it does block
    is a sentence:** §5.3.1 says nobody may quote the stronger G4 wording until
    the control is complete, and on this measurement it is not. This test is
    that gate, and it is the reason the gate is a test rather than a promise
    (`CLAUDE.md` rule 9).

    It will fail the day the value limb lands, which is the right moment to
    re-read §5.3.1's table and the G4 sentence.
    """
    # Limb 1 and 2 — implemented.
    assert walk({"total": 1}) != [], "the forbidden-key limb is missing"
    assert walk({"job": {"payload": {"paid": 1}}}) != [], (
        "the money-shaped-key limb is missing"
    )

    # Limb 3 — an amount as a value. Not implemented.
    assert walk({"handover_note": "Paid Rs 300"}) == []
    assert walk({"meta": {"note": "he paid 300 rupees"}}) == []
    assert walk({"message": "I gave him Rs 300 for it"}) == []

    # Limb 4 — a contact detail. Not implemented.
    assert walk({"message": "call me on +91 90000 00001"}) == []
    assert walk({"body": "mail me at student@example.test"}) == []

    # And the double-encoded payload.
    assert walk({"payload": '{"paid": 30000}'}) == []


def test_the_control_is_not_claimed_complete_anywhere_qa_can_read():
    """The other half of the gate: ADR-003 §5.3.1's status table must not say
    this control is implemented while F15 stands, because §5.3.1 exists
    precisely to stop the document outrunning the repository.

    QA asserts the direction that can mislead — the table saying "implemented"
    when two limbs are missing. A table that still says NOT IMPLEMENTED while
    the file exists understates us, and §5.3.1's own ruling is that
    understating is the acceptable error.
    """
    import pathlib

    adr = (pathlib.Path(__file__).resolve().parents[2]
           / "company" / "architecture" / "ADR-003-no-funds-custody.md")
    rows = [
        line for line in adr.read_text(encoding="utf-8").splitlines()
        if "test_forbidden_response" in line and line.strip().startswith("|")
    ]
    assert rows, "ADR-003 §5.3.1's status table no longer tracks this control"
    for row in rows:
        assert "implemented and verified" not in row.lower(), (
            "ADR-003 §5.3.1 claims the response-schema control is implemented "
            f"and verified; QA measures two of four limbs missing (F15): {row}"
        )


# --------------------------------------------------------------------------
# 3. what cannot be verified in S0
# --------------------------------------------------------------------------


def test_the_control_runs_against_every_real_response(engine):
    """**QA-S2 F31, third instance.** An unconditional skip whose reason expired.

    The S0 text said *"S0 serves two responses and it already checks both"*.
    S2 serves thirteen L2 routes. An unconditional skip cannot notice that;
    it is replaced by the sweep below, which derives its subject from the
    URLconf and **asserts its own reach** so it cannot report coverage for a
    route it never called (`CLAUDE.md` rule 10: the accessibility harness that
    reached four pages of eleven).
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
    api = {r for r in mounted if r.startswith("api/v1/")}
    assert len(api) > 2, (
        "the S0 reason for skipping was that only two responses existed. If "
        f"that is true again something has been unmounted: {sorted(api)}"
    )
    assert api <= (EXERCISED_ROUTES | UNEXERCISED_ROUTES.keys()), (
        "these L2 routes are not in this file's sweep and are not recorded as "
        "unexercised with a reason, so the response-boundary control is not "
        "measuring them: "
        f"{sorted(api - EXERCISED_ROUTES - set(UNEXERCISED_ROUTES))}"
    )


# --------------------------------------------------------------------------
# 4. S2 — the sweep that replaces the skip
# --------------------------------------------------------------------------

#: Every L2 route `test_every_s2_response_payload_is_walked_by_the_guard`
#: actually drives. Derived against the URLconf above, so a new route must
#: either be swept or be recorded below with a reason.
EXERCISED_ROUTES = {
    "api/v1/books",
    "api/v1/books/<int:book_id>",
    "api/v1/listings",
    "api/v1/listings/mine",
    "api/v1/listings/<int:listing_id>",
    "api/v1/listings/<int:listing_id>/photos",
    "api/v1/listings/<int:listing_id>/publish",
    "api/v1/listings/<int:listing_id>/withdraw",
    "api/v1/requests",
    "api/v1/requests/<int:request_id>",
    "api/v1/account",
    "api/v1/account/correction",
    "api/v1/account/export",
}

#: Routes deliberately not swept here, each with the reason and the test that
#: does cover it. A route with no entry in either set fails the test above.
UNEXERCISED_ROUTES = {
    "api/v1/auth/magic-link": "anonymous; its body is `{}` and S1 covers it",
    "api/v1/auth/consume": "needs a live token; S1's journey covers it",
    "api/v1/auth/logout": "empty body",
    "api/v1/account/age-declaration": "S1; DOB handling is tests/e2e/test_no_dob_independently.py",
    "api/v1/account/consents": "S1",
    "api/v1/account/consents/<str:purpose_key>": "S1",
    "api/v1/account/nominee": "S1; holds a third party's data and is walked there",
    "api/v1/account/erase": "terminal — it tombstones the actor mid-sweep",
    "api/v1/notices/<str:kind>": "returns notice markdown, not a payload with keys",
    "api/v1/listings/<int:listing_id>/photos/<str:sha256>": (
        "serves image bytes, not JSON; the headers are asserted in "
        "tests/api/test_listings_api.py and the authorisation in "
        "tests/contract/test_denormalised_scope_columns.py"
    ),
}


def _walk(payload, where):
    control().assert_no_forbidden_content(payload, where=where)


def test_every_s2_response_payload_is_walked_by_the_guard(
    client_as, seller, book, jpeg_bytes
):
    """**The control, run over the payloads it exists for.**

    ADR-003 §5.3 makes this file's subject *"the compensating control for the
    two residuals P14 cannot close"*, and API-CONTRACT §5.2 says a contract
    test asserts the listing rule *"against the response schema, not just the
    database"*. Until S2 both sentences were true of `/healthz` and `/readyz`.

    Every payload below is the real HTTP response, parsed, and handed to the
    shipped walker — **imported, not re-implemented** (`CLAUDE.md` rule 11),
    so a narrowing of the walker shows up here as an escape rather than as
    agreement.

    The reach is asserted by `test_the_control_runs_against_every_real_response`
    above, which derives the route list from the URLconf.
    """
    import json
    import uuid

    client = client_as(seller)
    seen = []

    def record(label, response):
        seen.append(label)
        try:
            payload = json.loads(response.content)
        except ValueError:
            payload = {"_text": response.content.decode("utf-8", "replace")}
        _walk(payload, where=f"{label} -> {response.status_code}")
        return payload

    def post(path, body):
        return client.post(
            path, data=json.dumps(body), content_type="application/json",
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )

    record("GET /books?q=", client.get("/api/v1/books?q=Engineering"))
    record("GET /books?isbn=", client.get(f"/api/v1/books?isbn={book.isbn13}"))
    record("GET /books/{id}", client.get(f"/api/v1/books/{book.id}"))

    created = record("POST /listings", post("/api/v1/listings", {
        "accept_seller_terms": True, "book_id": book.id,
        "asking_price_paise": 30075, "condition": "GOOD",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    }))
    # A refusal body is a response. `300.75` is ADR-003's own example and the
    # field_errors shape is where a rejected amount gets echoed back.
    record("POST /listings (refused)", post("/api/v1/listings", {
        "accept_seller_terms": True, "book_id": book.id,
        "asking_price_paise": 300.75, "condition": "GOOD",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    }))
    listing_id = created["id"]

    record("POST /listings/{id}/photos", client.post(
        f"/api/v1/listings/{listing_id}/photos",
        data={"photo": _upload(jpeg_bytes)},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    ))
    record("GET /listings/mine", client.get("/api/v1/listings/mine"))
    record("GET /listings", client.get("/api/v1/listings"))
    record("GET /listings/{id}", client.get(f"/api/v1/listings/{listing_id}"))

    published = record("POST /listings/{id}/publish", post(
        f"/api/v1/listings/{listing_id}/publish", {"expected_version": created["version"]}
    ))
    record("POST /listings/{id}/withdraw", post(
        f"/api/v1/listings/{listing_id}/withdraw",
        {"expected_version": published.get("version", created["version"])},
    ))

    made = record("POST /requests", post("/api/v1/requests", {
        "free_text_title": "A book nobody has listed", "course_code": "MA8151",
    }))
    record("GET /requests", client.get("/api/v1/requests"))
    record("DELETE /requests/{id}", client.delete(
        f"/api/v1/requests/{made['id']}",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    ))

    record("GET /account", client.get("/api/v1/account"))
    record("GET /account/export", client.get("/api/v1/account/export"))
    record("POST /account/correction", post(
        "/api/v1/account/correction", {"stated_problem": "My display name is wrong."}
    ))

    assert len(seen) == 17, (
        "the sweep reached a different number of payloads than it claims; an "
        f"instrument asserts its own reach: {seen}"
    )


def _upload(data):
    import io

    buf = io.BytesIO(data)
    buf.name = "photo.jpg"
    return buf
