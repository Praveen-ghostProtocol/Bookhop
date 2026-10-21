"""P14 — the data behind the guard. ADR-003 §2.3 W1d.

**ADR-003 §2.3 is the specification of record. This module is its single
expression in code**, and the tests import it rather than retyping it:

  * `tests/unit/test_forbidden_schema.py` — the schema assertions (W1, W1a, W1b,
    W2, W3)
  * `tests/unit/test_forbidden_source.py` — the source-level grep (W1c)
  * `tests/contract/test_p14.py` (test-qa) — asserts this module says what the
    ADR says

W1d exists because of a measured incident, not a principle: QA-S0 F2 found the
guard had been **retyped** from the ADR's prose table and had diverged — it
still carried the `age_check_pending` DOB exemption that amendment A-5
explicitly withdrew, so `age_check_pending.date_of_birth` passed a green build.
During the rework that fixed it, the guard's own guard caught a second
divergence in flight: `rupees_exchanged` escaped every layer until `rupee` and
`paise` were restored to the token set. A control that was briefly weaker than
its predecessor *while being made stronger* is the whole argument for this
file. **Do not inline any of it back into a test.**

**Nothing here may be relaxed without a founder escalation** (ADR-003 §2.3's
closing paragraph). Three diffs carry that escalation: a change to the deny-list
or the whitelist; a widened CHECK constraint; and a new column on one of the
four frozen tables. By the same decision procedure, **adding a money token and
narrowing an exemption are tightenings and do not** — they are recorded in the
commit message so the next reader knows the bar was considered rather than
bypassed.
"""

# --- W1 · the whitelist ---------------------------------------------------

#: ADR-003 §2.1/§2.3 W1 — the only money column in the entire database.
MONEY_COLUMN = ("listings", "asking_price_paise")

#: ADR-003 §2.3 W1a — and it must be an integer type. A `real` or `numeric`
#: declaration fails: QA attack 7 declared this exact column `real` and a
#: name-based control passed it.
MONEY_COLUMN_INTEGER_TYPES = frozenset({
    "IntegerField", "BigIntegerField", "PositiveIntegerField",
})

#: ADR-003 §2.3 W1, **RATIFIED by cto 2026-10-21**. A numeric column must be
#: MONEY_COLUMN, or its name must END WITH one of these words, or BE one of
#: them exactly.
#:
#: The discriminating question for any word here, from the ratification: *can
#: this word denote a quantity that could be a consideration?* For all thirteen
#: the answer is no — they denote identities, counts, dimensions, durations and
#: states. A word that could denote money (`total`, `value`, `sum`, `amount`,
#: `balance`, `rate`) is a widening, is refused, and is already a W1b deny
#: token. **Adding a word here is an amendment to ADR-003.**
NON_MONETARY_WORDS = (
    "id", "count", "seconds", "minutes", "attempts", "bytes",
    "width", "height", "year", "position", "version", "no", "status",
)

#: ADR-003 §2.3 W1's escape hatch for a genuinely odd name that no word above
#: describes. `(table, column) -> one-line reason`. **Present and empty on
#: purpose**, and the ADR says to prefer an entry here over a new word in
#: NON_MONETARY_WORDS, because a vocabulary word applies database-wide.
DECLARED_NON_MONETARY: "dict[tuple[str, str], str]" = {}

#: ADR-003 §2.3 W1b, verbatim: 22 tokens. **Any column whose name contains any
#: of these, anywhere in the database, in any type, must be
#: `listings.asking_price_paise` or the build fails.**
#:
#: All 22 are enforced. The earlier guard enforced 15 and QA-S0 F6 measured the
#: cost: `amt`, `paid`, `payment` and `due` were caught by nothing, and because
#: W1 inspects only *numeric* columns, `receipts.amt text`,
#: `receipts.paid text`, `handover_log.payment_received text` and
#: `receipts.due_inr text` each stored a settled price on a green build.
W1B_MONEY_TOKENS = (
    "price", "paise", "rupee", "rs_", "amount", "amt", "cash", "money", "fee",
    "cost", "value", "total", "sum", "consideration", "settle", "settled",
    "tender", "charge", "paid", "payment", "due", "balance",
)

#: ADR-003 §2.3 W1b second limb, **as amended on REVIEW-S0 R1**: the exemption
#: is scoped to two COLUMNS, not to the `listings` table.
#:
#: The table-wide version was a real hole and QA-S0 F7 demonstrated it:
#: `listings.cash_received text` and `listings.settlement text` were stored on a
#: green build, making the one table permitted to hold money the softest target
#: in the schema. §2.1 says "exactly one money column in the entire database",
#: so the contract was right and the control disagreed with it.
#:
#: `price_fixed_at` is here because ADR-003 §2.1 and DATA-MODEL §3 both mandate
#: it and it contains the token `price` (this is REVIEW-S0 M2, kept fixed).
MONEY_WORDS_EXEMPT = frozenset({
    ("listings", "asking_price_paise"),
    ("listings", "price_fixed_at"),
})

#: Retained, and `None` on purpose: the W1b rule exempts no table at all.
#: QA-S0 F7 asserts this is None, and the name is left here so the change from
#: a table-wide exemption is visible rather than silent.
MONEY_WORDS_EXEMPT_TABLE = None

#: Shapes in which a W1b token cannot denote an amount, so they do not match.
#:
#: **This is an allowance, not a tightening, and it is therefore escalated to
#: cto** (see ENGINE-DIVERGENCE §9 item 9) rather than claimed as obvious. The
#: token `due` collides with every SLA-clock column DATA-MODEL mandates —
#: `listings.purge_due_at`, `reports.acknowledge_due_at` / `act_due_at` /
#: `disposal_due_at`, `data_subject_requests.due_at`, `disputes.sla_due_at`,
#: `legal_notices.act_due_at`, `grievances.disposal_due_at`,
#: `transfers.purge_due_at` and more. Enforcing the bare token would turn the
#: P14 guard red on about fifteen columns three frozen contracts require, from
#: S1 onward, with the tempting fix being an edit to a founder-escalating file
#: under schedule pressure. That is REVIEW-S0 M2 recreated, which is the exact
#: counterfactual cto used to ratify `status` in NON_MONETARY_WORDS.
#:
#: `sum` has the same problem in source (W1c): `consume_magic_link` contains it,
#: and that name is **frozen by API-CONTRACT §3** and cannot be renamed.
#:
#: The discriminating question, answered for each: `due_at` is a **deadline** —
#: a timestamp, not a quantity; `overdue` is a backlog state; `consume` is a
#: verb about using a token once. None can denote a consideration.
#: `amount_due`, `due_paise`, `total_due` and QA's `due_inr` all still fail, and
#: `test_the_token_shape_exemptions_cannot_swallow_a_known_attack` proves that
#: rather than asserting it.
#:
#: **Where a name is ours to choose, it is renamed instead of exempted.**
#: `run_due_jobs` became `run_pending_jobs` rather than earning an entry here:
#: a tightening beats an allowance, and nothing outside this repository's own
#: tests referenced it.
MONEY_TOKEN_SHAPE_EXEMPTIONS = (
    "due_at",     # an SLA deadline (DATA-MODEL §7, §10) — a timestamp, not an amount
    "overdue",    # `/readyz`'s job-backlog signal (API-CONTRACT §5.8)
    "consume",    # consume_magic_link — a frozen signature (API-CONTRACT §3)
)

#: ADR-003 §3 — the only permissible future fee shape, pre-approved before
#: anyone builds one: `fee_asked_paise` computed from the asking price, and
#: `fee_paid` as a **boolean, never an amount**.
#:
#: Note the live interaction: W1b's `fee` and `paise` tokens forbid both names
#: outright, because MONEY_WORDS_EXEMPT names only two columns. That is correct
#: for v1 — a fee needs D-008's trigger, counsel C10 and a new ADR — and the
#: W1b exemption is part of what that ADR would have to amend.
FEE_ALLOWED = frozenset({"fee_asked_paise", "fee_paid"})

NUMERIC_TYPES = frozenset({
    "AutoField", "BigAutoField", "SmallAutoField",
    "IntegerField", "BigIntegerField", "SmallIntegerField",
    "PositiveIntegerField", "PositiveBigIntegerField", "PositiveSmallIntegerField",
    "FloatField", "DecimalField",
})

FLOAT_TYPES = frozenset({"FloatField", "DecimalField"})

#: `handover_points.latitude`/`longitude` are `numeric` in DATA-MODEL §5 and
#: describe a public campus landmark, not a person or an amount. The only
#: non-integer numbers permitted anywhere.
FLOAT_EXEMPT = frozenset({
    ("handover_points", "latitude"), ("handover_points", "longitude"),
})

# --- W2 · frozen column lists (ADR-003 §2.3 W2, DATA-MODEL A-11) ----------

#: table -> (slice that creates it, expected column set). **Any** new column on
#: any of these four fails the build until the expected list is edited, and that
#: edit carries the founder escalation. Compliance's reason, adopted: *"enum
#: widening and column addition are how this constraint will actually be broken,
#: not by someone naming a column settled_price."*
FROZEN_TABLES = {
    "transfers": ("S4", {
        "id", "listing_id", "book_id", "campus_id", "city_id",
        "seller_id", "buyer_id", "seller_pseudonym", "buyer_pseudonym",
        "seller_is_seed", "buyer_is_seed", "state", "state_changed_at",
        "offered_at", "accepted_at", "reservation_expires_at",
        "handover_point_id", "handover_window_start", "handover_window_end",
        "seller_confirmed_at", "buyer_confirmed_at", "completed_at",
        "cancelled_by", "cancel_reason_code", "no_show_party", "leakage_class",
        "delisted_within_72h", "version", "created_at", "purge_due_at",
    }),
    "transfer_events": ("S4", {
        "id", "transfer_id", "from_state", "to_state", "actor_type",
        "actor_pseudonym", "reason_code", "request_id", "occurred_at",
    }),
    "messages": ("S5", {
        "id", "thread_id", "sender_pseudonym", "sender_id", "body",
        "body_purged_at", "contact_pattern_flag", "created_at", "removed_at",
        "removal_reason", "preserved_until", "purge_due_at",
    }),
    "transfer_followups": ("S5", {
        "id", "transfer_id", "party", "question_key", "answer",
        "asked_at", "answered_at", "attempt_no",
    }),
}

#: Asserted by value set, not by the presence of a CHECK. DATA-MODEL §5
#: promises "no question about money, ever", and `transfer_followups` is the
#: natural home for "did you pay?".
FROZEN_ENUMS = {
    ("transfer_followups", "question_key"): {"STILL_HAVE_BOOK", "DID_YOU_GET_BOOK"},
    ("transfer_followups", "answer"): {"YES", "NO", "NO_REPLY"},
}

# --- W3 · the deny-list, kept for its error message -----------------------
#
# Redundant against W1/W1b for almost every case, and kept anyway for one
# narrow reason: a whitelist failure says "`value_x` is not an allowed numeric
# column", while a deny-list failure can say "`offered_price` is a settled
# consideration — read ADR-003 §2.3". The second message stops a developer
# renaming the column and moving on.

#: (pattern, exact?) — matched against every column name, both routes.
FORBIDDEN_COLUMNS = (
    # Row 1 — a settled consideration under any name. P14, s194-O / s393.
    ("settled", False), ("sale_price", False), ("final_price", False),
    ("sold_price", False), ("agreed_price", False), ("paid_amount", False),
    ("amount_paid", False), ("transaction_amount", False), ("gross_amount", False),
    # Row 3 — government identifiers. `pan` and `aadhaar` are bare, i.e. exact.
    ("pan", True), ("pan_number", False), ("pan_card", False),
    ("aadhaar", False), ("aadhar", False), ("uidai", False),
    ("govt_id", False), ("id_proof", False),
    # Row 4 — financial instrument data. `vpa` is a substring, as the ADR writes
    # it: it was exact, so `vpa_handle` and `seller_vpa` passed (QA-S0 F2(b)).
    ("upi", False), ("vpa", False), ("bank_account", False),
    ("ifsc", False), ("card_number", False),
    # Row 5 — a denominated balance under any name. P12, D-003, RBI PPI.
    # `ledger` rather than `ledger_entry`: Django pluralises `LedgerEntry` to
    # `ledger_entries`, which `ledger_entry` does not match (QA-S0 F2).
    ("wallet", False), ("credit_balance", False), ("balance", False),
    ("points", False), ("escrow", False), ("payout", False), ("ledger", False),
    # Item 4 — an offer, bid or negotiation amount. An accepted offer amount IS
    # a settled consideration.
    ("offered_price", False), ("counter_price", False), ("accepted_price", False),
    ("bid", False), ("negotiat", False), ("deal", False),
    # Item 5 — price history in any shape.
    ("price_history", False), ("price_change", False), ("previous_price", False),
    ("old_price", False), ("price_at", False),
    # Item 6 — price-derivation fields.
    ("discount", False), ("rebate", False), ("cashback", False),
    ("coupon", False), ("voucher", False), ("refund", False),
    # Item 7 — charge components.
    ("shipping", False), ("packaging", False), ("commission", False),
    ("fee", False),
)

#: Two-token patterns (`%offer%amount%`, `%counter%price%`, `%adjust%amount%`,
#: `%delivery%charge%`, `%convenience%fee%`): both tokens must appear.
FORBIDDEN_PAIRS = (
    ("offer", "amount"), ("counter", "price"), ("adjust", "amount"),
    ("delivery", "charge"), ("convenience", "fee"),
)

#: pattern -> the one (table, column) where it is permitted, else None.
#:
#: `date_of_birth`/`dob`/`birth` have **no exception**: CG-5 withdrew the
#: `age_check_pending` one and DATA-MODEL A-5 deleted the table. No DOB is
#: persisted anywhere, in any state. The address patterns are scoped to one
#: column, not to a table — `legal_entities.pincode` used to pass (QA-S0 F2(c)).
CONDITIONAL_COLUMNS = {
    "date_of_birth": None,
    "dob": None,
    "birth": None,
    "latitude": ("handover_points", "latitude"),
    "longitude": ("handover_points", "longitude"),
    "precise_location": None,
    "gps": None,
    "street": None,
    "address": ("legal_entities", "registered_address"),
    "address_line": ("legal_entities", "registered_address"),
    "pincode": None,
    "postal": None,
}

#: Tables matched against the column deny-list too; these are the exceptions.
ALLOWED_TABLE_NAMES = frozenset({"handover_points"})

#: ADR-003 §2.3 row 2 — the price belongs to the listing, never to the
#: transaction.
TRANSACTION_TABLE_PREFIXES = ("transfers", "transfer_events", "disputes", "handover")

#: ADR-003 §2.3's response-key rule, as extended by the amendment. Used by
#: `tests/unit/test_forbidden_source.py` (W1c) and by the response-schema test
#: ADR-003 §2.3 names, which still has no owning slice (REVIEW-S0 N2).
FORBIDDEN_RESPONSE_KEYS = ("price", "amount", "total", "value")

#: ADR-003 §2.3 W5 — what no schema or source control can reach. Recorded as
#: accepted residual exposure, not as covered.
W5_DECLARED_RESIDUALS = (
    "a number inside a jsonb document (jobs.payload, notifications.payload)",
    "a number inside free text (a message body, a note)",
)


# --- predicates, shared by every caller so there is one definition ---------


def token_exempt_shape(column):
    """True when a W1b token in this name appears only in an exempted shape."""
    return any(shape in column for shape in MONEY_TOKEN_SHAPE_EXEMPTIONS)


def money_tokens_in(column):
    """The W1b tokens this column name contains, ignoring exempted shapes.

    A token is ignored only when **every** occurrence of it sits inside an
    exempted shape — so `amount_due_at` is still caught on `amount`, and
    `due_inr` is still caught on `due`.
    """
    name = column.lower()
    stripped = name
    for shape in MONEY_TOKEN_SHAPE_EXEMPTIONS:
        stripped = stripped.replace(shape, "")
    hits = []
    for token in W1B_MONEY_TOKENS:
        if token not in name:
            continue
        # A token is ignored only if it disappears once the exempted shapes are
        # removed -- so `amount_due_at` still hits on `amount`, and `due_inr`
        # still hits on `due` because `due_inr` contains no exempted shape.
        if token not in stripped:
            continue
        hits.append(token)
    return hits


def is_declared_non_monetary(column):
    """ADR-003 §2.3 W1, suffix-or-exact, as ratified."""
    name = column.lower()
    return any(name == word or name.endswith("_" + word) for word in NON_MONETARY_WORDS)


def matches(name, pattern, exact):
    return name == pattern if exact else pattern in name


FAIL = (
    "P14 violation: {table}.{column} — {why}. ADR-003 §2.3 as amended "
    "2026-10-21 (COMPLIANCE.md §4.3.2). P14 is binding on the schema: never "
    "store a settled transaction price, an offer or negotiation amount, a "
    "price history, a price-derivation or charge field, a government "
    "identifier, a financial instrument, a denominated balance, a DOB in any "
    "state, a precise user location or an address. If this is genuinely "
    "required it needs a new ADR plus a privacy-compliance sign-off in the "
    "SAME commit. Do not edit apps/core/p14.py to make this pass."
)
