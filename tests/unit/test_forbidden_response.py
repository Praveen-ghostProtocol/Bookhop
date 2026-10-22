"""P14 at the contract boundary. ADR-003 §2.3, THREAT-MODEL §6.

*"A price absent from storage but present in a response is still a record"*
(`COMPLIANCE.md` §4.3.2 item 2). So no API response may contain a forbidden
key, and — extended by the 2026-10-21 amendment — **no response key may be
named `price`, `amount`, `total` or `value`** at all: the money field is
`asking_price_paise` at the boundary as well as in the table, so a template
cannot render "Price:" from a field that invited it.

**Why this is in S0 and not S1.** `TASKS.md` assigns it to S1's first commit,
and it had been named by ADR-003 §2.3 and THREAT-MODEL §6 while being claimed
by no slice for two review rounds — REVIEW-S0 N2, then QA-S0 F5. It is the
compensating control for the **jsonb and free-text limbs of P14** that ADR-003
§5.3 accepts as residual: `jobs.payload` and, from S3, `notifications.payload`
can hold `{"paid": 30000}`, and nothing in the schema can see it, but a
response that *serialises* such a payload is reachable here. A control that
exists before the thing it guards is the only kind that was ever tested, so it
lands now rather than beside the first endpoint.

**What it asserts today, honestly.** S0 has two responses — `/healthz` and
`/readyz` — and no L2 endpoint, so the live surface it can walk is small. It
therefore does three things rather than one:

  1. walks every response S0 actually produces, including nested structures;
  2. exposes `assert_no_forbidden_keys()`, which every later slice's response
     test calls, so the rule arrives with the endpoint instead of after it;
  3. tests the walker itself against money-shaped payloads, so it cannot pass
     vacuously when the surface is two endpoints — the defect class `CLAUDE.md`
     rule 12 names.

Tokens come from `apps/core/p14.py`, never retyped (`CLAUDE.md` rule 10).
"""

import json
import re

import pytest

from apps.core.p14 import FORBIDDEN_RESPONSE_KEYS, MONEY_WORDS_EXEMPT, money_tokens_in

pytestmark = pytest.mark.django_db

#: The only key name that may be money-shaped, at the boundary as in the table.
PERMITTED_KEYS = {column for _table, column in MONEY_WORDS_EXEMPT}

# --- the value limb (QA-S0 F15) -------------------------------------------
#
# THREAT-MODEL §6 states this control's job as four limbs: *"No response
# anywhere carries a forbidden key, a money-shaped key, a contact detail or an
# amount."* S0 shipped the two key limbs. QA-S0 F15 measured what that left:
#
#   > *"**an amount as a value**. `{"handover_note": "Paid Rs 300"}` and
#   > `{"meta": {"note": "he paid 300 rupees"}}` both pass. ADR-003 §2.3 W5's
#   > free-text residual **is a value**, so the compensating control does not
#   > currently reach the thing it compensates for."*
#
# That is the finding that matters, because W5's free-text residual is the whole
# reason this file exists (ADR-003 §5.3 item 4). A control that covers only key
# *names* compensates for the shape P14 already catches in the schema and not
# for the shape it cannot. So the value limb lands here, in S1, as assigned.
#
# **The fourth limb — a contact detail — is NOT implemented here, and is
# escalated rather than silently dropped.** See
# `test_finding_the_contact_detail_limb_collides_with_a_mandated_response`.

#: A currency marker, with the match rule for each (`CLAUDE.md` rule 11: a
#: per-entry rule, so a false positive is narrowed rather than deleted).
#: `word` entries match on word boundaries; `raw` entries are symbols with no
#: word boundary to match on.
CURRENCY_MARKERS = (
    ("raw", "₹", "the rupee sign"),
    ("raw", "₨", "the old rupee sign — still on some keyboards"),
    ("word", r"rs\.?", "Rs / Rs. — by far the commonest written form"),
    ("word", "inr", "the ISO currency code"),
    ("word", "rupees?", "the word, singular or plural"),
    ("word", "paise", "the unit the one permitted column is denominated in"),
)

#: A verb that makes an adjacent number an amount even with no currency marker.
#: *"he paid 300"* is the shape QA measured; `MONEY_TOKEN_SHAPE_EXEMPTIONS` does
#: not apply here because this limb reads prose, not identifiers.
PAYMENT_VERBS = (
    "paid", "pay", "paying", "gave", "giving", "received", "charged",
    "owes?", "settled", "tendered", "refunded",
)

#: digits-near-marker, in either order. `\W{0,3}` is "adjacent": it spans a
#: space, a colon, a currency separator or nothing, and stops well short of
#: joining two unrelated clauses.
_MARKER_ALT = "|".join(
    [rf"\b(?:{p})\b" for kind, p, _why in CURRENCY_MARKERS if kind == "word"]
    + [re.escape(p) for kind, p, _why in CURRENCY_MARKERS if kind == "raw"]
    + [rf"\b(?:{v})\b" for v in PAYMENT_VERBS]
)
AMOUNT_IN_TEXT = re.compile(
    rf"(?:(?:{_MARKER_ALT})\W{{0,3}}\d)|(?:\d\W{{0,3}}(?:{_MARKER_ALT}))|(?:\d\s*/-)",
    re.IGNORECASE,
)

# ponytail: a marker-adjacent-to-digits regex over string values. **Ceiling: it
# reads Latin-script digits beside an English or symbol marker.** "three hundred
# rupees" (words, no digits), a Tamil-script amount, and a bare "300" with no
# marker at all all pass — the last one necessarily, because a bare number in
# free text is indistinguishable from a page count. That is exactly the residual
# ADR-003 §2.3 W5 declares and §5.3 item 3 bounds with a product rule (PRD
# EX-18: no in-app "how much did you pay?" field, anywhere). **This limb makes
# the common case fail the build; it does not close W5, and §5.3's second
# sentence — "guaranteed by none of them" — stays true.** Upgrade path: none
# wanted. A broader matcher would fire on a listing title containing a page
# count and would then be deleted, which is `CLAUDE.md` rule 13.


def forbidden_keys_in(payload, path=""):
    """Every money-shaped or forbidden-named key anywhere in `payload`.

    Recursive on purpose: the jsonb limb of P14 is a *nested* document, so a
    walker that only inspected top-level keys would miss the one shape this
    control exists for.
    """
    offenders = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            here = f"{path}.{key}" if path else str(key)
            name = str(key).lower()
            if name not in PERMITTED_KEYS:
                if name in FORBIDDEN_RESPONSE_KEYS:
                    offenders.append(f"{here} (a forbidden response key name)")
                else:
                    hits = money_tokens_in(name)
                    if hits:
                        offenders.append(f"{here} (money tokens {hits})")
            offenders += forbidden_keys_in(value, here)
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            offenders += forbidden_keys_in(value, f"{path}[{index}]")
    return offenders


def _decoded(text):
    """A JSON document carried inside a string, or None.

    QA-S0 F15's third gap: `{"payload": '{"paid": 30000}'}` is a document inside
    a string, so the key walker sees one harmless key. `jobs.payload` is a real
    jsonb column and a serialiser that `str()`s it produces exactly this — which
    is not hypothetical, because the jsonb limb is one of the two residuals this
    file is the compensating control for.
    """
    candidate = text.strip()
    if not candidate.startswith(("{", "[")):
        return None
    try:
        parsed = json.loads(candidate)
    except ValueError:
        return None
    return parsed if isinstance(parsed, (dict, list)) else None


def forbidden_values_in(payload, path=""):
    """Every string value that carries an amount, anywhere in `payload`.

    The value limb (QA-S0 F15). Also re-walks a double-encoded JSON document
    with the **full** check, so a nested payload's keys are examined too.
    """
    offenders = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            offenders += forbidden_values_in(value, f"{path}.{key}" if path else str(key))
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            offenders += forbidden_values_in(value, f"{path}[{index}]")
    elif isinstance(payload, str):
        inner = _decoded(payload)
        if inner is not None:
            where = f"{path or '<root>'} (double-encoded JSON)"
            for offender in forbidden_keys_in(inner) + forbidden_values_in(inner):
                offenders.append(f"{where} -> {offender}")
        hit = AMOUNT_IN_TEXT.search(payload)
        if hit:
            offenders.append(f"{path or '<root>'} (an amount in free text: {hit.group(0)!r})")
    return offenders


def forbidden_content_in(payload, path=""):
    """Both implemented limbs: a money-shaped key, and an amount as a value."""
    return forbidden_keys_in(payload, path) + forbidden_values_in(payload, path)


def assert_no_forbidden_content(payload, where=""):
    """The assertion later slices import. One line per endpoint test."""
    offenders = forbidden_content_in(payload)
    assert offenders == [], (
        f"P14 at the contract boundary (ADR-003 §2.3): {where or 'this response'} "
        "contains money. A price absent from storage but present in a response is "
        "still a record: no response key may be named price, amount, total or "
        "value, and no response value may carry an amount in free text "
        "(THREAT-MODEL §6; QA-S0 F15).\n" + "\n".join(offenders)
    )


#: The S0 name, kept because every later slice's response test is told to call
#: it. It now checks both limbs, which is the direction that cannot weaken a
#: caller.
assert_no_forbidden_keys = assert_no_forbidden_content


# --- 1. the live surface S0 produces --------------------------------------


@pytest.mark.parametrize("path", ["/healthz", "/readyz"])
def test_no_s0_response_contains_a_forbidden_key(client, path):
    response = client.get(path)
    body = response.content.decode()
    try:
        payload = json.loads(body)
    except ValueError:
        payload = {"_text": body}
    assert_no_forbidden_keys(payload, where=path)


def test_the_readyz_body_is_walked_rather_than_assumed_flat(client):
    """`/readyz` used to return a nested `checks` object (REVIEW-S0 S12 removed
    it). Asserting the walker sees nesting means the control does not quietly
    become top-level-only the next time a response grows a sub-object."""
    payload = json.loads(client.get("/readyz").content)
    assert isinstance(payload, dict)
    assert forbidden_keys_in(payload) == []


# --- 2. the walker's own guard --------------------------------------------


@pytest.mark.parametrize(
    "payload,expected_hit",
    [
        ({"settled_price": 30000}, "settled_price"),
        ({"amount": 1}, "amount"),
        ({"total": 1}, "total"),
        ({"value": 1}, "value"),
        ({"price": 1}, "price"),
        ({"cash_received": True}, "cash_received"),
        # the jsonb limb: nested, which is the shape P14 cannot see in storage
        ({"job": {"payload": {"paid": 30000}}}, "job.payload.paid"),
        ({"items": [{"consideration_paise": 1}]}, "items[0].consideration_paise"),
        ({"transfer": {"meta": {"amt": "300"}}}, "transfer.meta.amt"),
        ({"a": {"b": {"c": {"rupees_exchanged": 1}}}}, "a.b.c.rupees_exchanged"),
    ],
)
def test_the_walker_catches_a_money_shaped_key_at_any_depth(payload, expected_hit):
    """`CLAUDE.md` rule 12: with two endpoints in the whole slice, the live
    assertions above could pass while the walker matched nothing at all. These
    prove it does not."""
    offenders = forbidden_keys_in(payload)
    assert any(expected_hit in offender for offender in offenders), offenders
    with pytest.raises(AssertionError, match="contract boundary"):
        assert_no_forbidden_keys(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"ready": True},
        {"request_id": "abc", "state": "OFFERED"},
        {"items": [{"id": 1, "condition": "GOOD", "campus_name": "Demo"}], "next_cursor": None},
        {"purge_due_at": "2027-01-01T00:00:00Z", "act_due_at": None},
        {"needs": ["age", "consent", "campus"]},
        {"asking_price_paise": 30000, "price_fixed_at": "2026-11-01T00:00:00Z"},
    ],
)
def test_the_walker_does_not_flag_a_legitimate_response(payload):
    """The other half, so the test above cannot pass by flagging everything —
    including the two permitted names and the SLA-clock shape that
    `MONEY_TOKEN_SHAPE_EXEMPTIONS` exists for."""
    assert forbidden_keys_in(payload) == []


def test_the_permitted_keys_are_exactly_the_two_adr_names():
    assert PERMITTED_KEYS == {"asking_price_paise", "price_fixed_at"}
    assert set(FORBIDDEN_RESPONSE_KEYS) == {"price", "amount", "total", "value"}


# --- 3. the value limb (QA-S0 F15) ----------------------------------------


@pytest.mark.parametrize(
    "payload,why",
    [
        ({"handover_note": "Paid Rs 300"}, "QA's first measured case"),
        ({"meta": {"note": "he paid 300 rupees"}}, "QA's second, nested"),
        ({"message": "I gave him Rs 300 for it"}, "QA's third"),
        ({"body": "₹300"}, "the rupee sign with no space"),
        ({"body": "it was 300/-"}, "the Indian short form, which no word list carries"),
        ({"body": "INR 1,200 in cash"}, "the ISO code and a separator"),
        ({"items": [{"note": "received 250"}]}, "inside a pagination envelope"),
        ({"a": {"b": [{"c": "settled 30000 paise"}]}}, "deep, both a verb and a unit"),
        # the double-encoded limb: a jsonb document serialised as a string
        ({"payload": '{"paid": 30000}'}, "a jsonb document inside a string — the key"),
        ({"payload": '{"note": "paid Rs 300"}'}, "a jsonb document inside a string — the value"),
        ({"outer": '[{"settled_price": 1}]'}, "a double-encoded list"),
    ],
)
def test_the_value_limb_catches_an_amount_in_free_text(payload, why):
    """**QA-S0 F15, closed.** The free-text residual ADR-003 §2.3 W5 declares
    *is a value*, so until this limb existed the compensating control did not
    reach the thing it compensates for. Every case here is one QA measured as
    passing, or the double-encoded shape QA named as a third gap.
    """
    offenders = forbidden_content_in(payload)
    assert offenders != [], f"{why}: nothing fired on {payload!r}"
    with pytest.raises(AssertionError, match="contract boundary"):
        assert_no_forbidden_content(payload)


@pytest.mark.parametrize(
    "payload,why",
    [
        ({"ready": True}, "/readyz"),
        ({"error": {"code": "GATE_CLOSED", "message": "Listings are not open on this campus yet.",
                    "request_id": "01JB", "retry_after": None}},
         "API-CONTRACT §2.2's error shape, which S1 ships"),
        ({"needs": ["age", "consent", "campus"]}, "API-CONTRACT §5.1's auth/consume body"),
        ({"display_name": "Priya R", "campus_name": "Demo Campus",
          "pseudonym": "0f3c…"}, "COMPLIANCE §2.4(i)'s seller identity, exactly"),
        ({"asking_price_paise": 30000}, "the one permitted money name, as an integer"),
        ({"body_md": "We never handle money. You pay the seller directly, in person."},
         "the handover-guidance notice: the word with no digits beside it"),
        ({"body_md": "Records are kept for 1 year after you delete your account."},
         "the deletion disclosure: a number with no currency marker"),
        ({"message": "Too many requests. Please try again later."}, "the 429 message"),
        ({"note": "48 hours to confirm"}, "an SLA clock in prose — 'hours' contains 'rs'"),
        ({"title": "Physics for Class 12, 300 pages"},
         "a page count: a bare number in prose, which W5 declares as residual"),
        ({"version": "2026-11-01.1"}, "a notice version string"),
    ],
)
def test_the_value_limb_stays_quiet_on_responses_the_contracts_mandate(payload, why):
    """`CLAUDE.md` rule 13. A limb reading prose is the one most likely to fire
    on copy three frozen contracts require, and the one whose false positive
    would be fixed by deleting it.

    **`{"note": "48 hours to confirm"}` is the case worth naming:** `rs` as a
    bare substring matches inside "hours", so a marker list without word
    boundaries would redden on every SLA sentence in the product. The
    word-boundary rule in `CURRENCY_MARKERS` is what makes that safe, and this
    asserts it rather than trusting the regex.

    The page-count row is the declared ceiling, asserted as a ceiling: a bare
    number in prose passes, deliberately, and ADR-003 §5.3 item 3's product rule
    is what bounds it.
    """
    assert forbidden_content_in(payload) == [], why


def test_the_value_limb_is_not_vacuous():
    """`CLAUDE.md` rule 12, for the new limb specifically: one positive and one
    negative, side by side, so a regex that stopped matching anything cannot be
    reported as coverage."""
    assert forbidden_values_in({"x": "Rs 300"}) != []
    assert forbidden_values_in({"x": "no money here"}) == []
    assert forbidden_values_in({"x": '{"paid": 1}'}) != []


def test_finding_the_contact_detail_limb_collides_with_a_mandated_response():
    """**The fourth limb is NOT implemented, and this is why — escalated to cto,
    not dropped.**

    THREAT-MODEL §6 names four limbs; three are now implemented. The fourth —
    *"no response anywhere carries a contact detail"* — **cannot be written at
    this file's scope without firing on a response API-CONTRACT §5.1
    mandates**: `GET /api/v1/account` returns the signed-in student **their own
    email address**, and `GET /legal/{kind}` publishes the grievance officer's
    email because E-Com r.4(2) requires it. Both are contact details in a
    response, both are correct, and a blanket matcher here would redden on them.
    `CLAUDE.md` rule 13 then applies: a guard that fires on the contracts it
    protects gets edited, not obeyed.

    **The limb's real subject is a *counterparty's* contact detail** —
    DATA-MODEL §5's *"no response anywhere contains a contact detail"* is about
    the handover and disclosure surface, and it is S5's acceptance criterion.
    That is a per-endpoint rule, not a global one: it needs to know whose
    address it is looking at, which this walker cannot know from the payload.

    **So the ruling this test asks cto for is one line: is the contact-detail
    limb (a) scoped to the S5 transfer/message/disclosure responses, or (b)
    global with a declared allow-list of the two mandated cases?** Until that
    is answered, the limb stays unimplemented and this test keeps saying so —
    which is `CLAUDE.md` rule 9 applied to a control I am declining to write
    rather than to one I wrote.

    It asserts the two mandated responses are *not* flagged, so the day someone
    adds a global matcher, this fails and the ruling is forced before it ships.
    """
    own_profile = {"email": "priya@example.ac.in", "display_name": "Priya R"}
    grievance_officer = {"grievance_officer_email": "grievance@example.test"}
    assert forbidden_content_in(own_profile) == []
    assert forbidden_content_in(grievance_officer) == []
