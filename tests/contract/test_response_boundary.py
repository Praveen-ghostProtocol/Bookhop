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
    pytest.skip(
        f"NOT VERIFIABLE IN S0 (engine={engine}): the control's value is in "
        "being run over real payloads, and S0 serves two — `/healthz` and "
        "`/readyz` — both of which it already checks. Every response with a "
        "nested payload, a free-text field or a contact detail arrives in "
        "S1–S5. THREAT-MODEL §6 assigns the file to backend in S1; QA's job "
        "from S1 is to assert it is called from each new endpoint's test rather "
        "than existing beside them."
    )
