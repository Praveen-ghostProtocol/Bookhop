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

import pytest

from apps.core.p14 import FORBIDDEN_RESPONSE_KEYS, MONEY_WORDS_EXEMPT, money_tokens_in

pytestmark = pytest.mark.django_db

#: The only key name that may be money-shaped, at the boundary as in the table.
PERMITTED_KEYS = {column for _table, column in MONEY_WORDS_EXEMPT}


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


def assert_no_forbidden_keys(payload, where=""):
    """The assertion later slices import. One line per endpoint test."""
    offenders = forbidden_keys_in(payload)
    assert offenders == [], (
        f"P14 at the contract boundary (ADR-003 §2.3): {where or 'this response'} "
        "contains key(s) that name money. A price absent from storage but present "
        "in a response is still a record, and no response key may be named price, "
        "amount, total or value.\n" + "\n".join(offenders)
    )


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
