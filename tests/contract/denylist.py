"""ADR-003 §2.3 **as written**, expressed as data, for conformance comparison.

**What this file is for, after QA-S0 v1.0 got its role wrong.** In v1.0 this
module was used as a stand-in for the shipped control: QA ran attacks against
*this* transcription and reported the escapes as the build's escapes. Backend is
right that that is the same defect QA found in the guard — a control judged
against a hand-copied rule. Attacks are now run against the real guard, through
`tests/contract/shipped_control.py`.

The module survives for one narrower job, which ADR-003 §2.3 W1d explicitly
assigns to `tests/contract/test_p14.py`: **assert that the control the build
enforces says what the ADR says.** For that, QA needs the ADR's lists in data
form — and keeping them here, in QA's own tree, is the point: if the guard's
copy and this copy agree, the specification and the enforcement agree. If they
drift, one test fails and says which.

**Decision, 2026-10-21, now that `apps/core/p14.py` exists: this file stays
independent and does NOT import it.** The question was put to QA directly and
the reasoning is worth recording, because the opposite choice is defensible.

Importing would make these tests tautologies — `assert p14.TOKENS ==
p14.TOKENS` — and would delete the only check that the *specification* and the
*enforcement* still agree. `apps/core/p14.py` removes the drift between the
guard and the module; it cannot remove the drift between the module and the ADR,
because the ADR is prose in a document no test can read. Something has to hold
the ADR's text in a form a test can compare, and that something must not be the
thing it is comparing against.

**The condition on that, which is the real lesson of QA-S0 F1:** an independent
re-derivation is only a check if someone compares the two deliberately. QA-S0
v1.0 held this file beside the guard and compared them *by accident*, through a
human reading two reports — and QA's own escapes went unexplained for a round
because of it. So the comparison is now explicit, named and automatic:
`test_p14.py::test_conformance_*` asserts `apps/core/p14.py` against the lists
below, one list at a time, and a divergence fails with the list named. This file
is a reference, never a judge: every attack verdict comes from running the
shipped control (`shipped_control.py`), never from the data here.

**Three copies became two by design, and the two are compared on every run.**

Every list below is transcribed from ADR-003 §2.3 as amended 2026-10-21, and
each carries the W-number or table row it comes from so a reviewer can diff it
against the ADR by eye.
"""

# --- W1 · the whitelist ---------------------------------------------------

#: ADR-003 §2.1/§2.3 W1 — the only money column in the database.
MONEY_COLUMN = ("listings", "asking_price_paise")

#: ADR-003 §2.3 W1's `NON_MONETARY_SUFFIXES`, verbatim and in order.
NON_MONETARY_SUFFIXES = (
    "_id", "_count", "_seconds", "_minutes", "_attempts", "_bytes",
    "_width", "_height", "_year", "_position", "_version", "_no",
)

#: ADR-003 §2.3 W1b's token set, verbatim: 22 tokens.
#: "Any column whose name contains any of these, anywhere in the database, must
#: be `listings.asking_price_paise` or the build fails."
W1B_MONEY_TOKENS = (
    "price", "paise", "rupee", "rs_", "amount", "amt", "cash", "money", "fee",
    "cost", "value", "total", "sum", "consideration", "settle", "settled",
    "tender", "charge", "paid", "payment", "due", "balance",
)

#: ADR-003 §2.3 W1's second limb — forbidden outside `listings` in any type.
W1_SECOND_LIMB = ("price", "amount", "value", "cost", "rate", "sum", "total")

#: ADR-003 §2.3 W1a — the permitted money column must be an integer type.
W1A_INTEGER_TYPES = ("IntegerField", "BigIntegerField")

#: ADR-003 §2.3 W2 — the four tables whose full column list is frozen.
W2_FROZEN_TABLES = ("transfers", "transfer_events", "messages", "transfer_followups")

#: ADR-003 §2.3 W2 — the two enum value sets asserted by value.
W2_FROZEN_ENUMS = {
    ("transfer_followups", "question_key"): ("STILL_HAVE_BOOK", "DID_YOU_GET_BOOK"),
    ("transfer_followups", "answer"): ("YES", "NO", "NO_REPLY"),
}

#: ADR-003 §2.3 W5 — the residuals the ADR declares not closable by any schema
#: or source control. An attack that escapes and is NOT one of these is a
#: finding; an attack that escapes and IS one of these is the accepted position.
W5_DECLARED_RESIDUALS = (
    "a number inside a jsonb document",
    "a number inside free text",
    "a Python @property, invisible to every schema assertion",
)


# --- W3 · the deny-list, row by row from the ADR's table ------------------

#: Row 1 — a settled consideration under any name. P14, s194-O / s393.
SETTLED_PATTERNS = (
    "settled", "sale_price", "final_price", "sold_price", "agreed_price",
    "paid_amount", "amount_paid", "transaction_amount", "gross_amount",
)

#: Row 2 — any money column on these tables. `handover_*` is a prefix glob.
TRANSACTION_TABLES = ("transfers", "transfer_events", "disputes")
TRANSACTION_TABLE_PREFIXES = ("handover_",)

#: Row 3 — government identifiers. `pan` and `aadhaar` are bare, i.e. exact.
GOVT_ID_EXACT = ("pan", "aadhaar")
GOVT_ID_PATTERNS = ("pan_number", "aadhar", "uidai", "govt_id", "id_proof")

#: Row 4 — financial instrument data.
INSTRUMENT_PATTERNS = ("upi", "vpa", "bank_account", "ifsc", "card_number")

#: Row 5 — a denominated balance under any name. P12, D-003, RBI PPI.
BALANCE_PATTERNS = ("wallet", "credit_balance", "balance", "points", "escrow",
                    "payout", "ledger_entry")

#: Item 4 (amendment) — an offer, bid or negotiation amount. An accepted offer
#: amount IS a settled consideration.
OFFER_PATTERNS = ("offered_price", "bid", "negotiat", "accepted_price", "deal")
OFFER_PAIRS = (("offer", "amount"), ("counter", "price"))

#: Item 5 (amendment) — price history in any shape.
HISTORY_PATTERNS = ("price_history", "price_change", "previous_price",
                    "old_price", "price_at")

#: Item 6 (amendment) — price-derivation fields.
DERIVATION_PATTERNS = ("discount", "rebate", "cashback", "coupon", "voucher",
                       "refund")
DERIVATION_PAIRS = (("adjust", "amount"),)

#: Item 7 (amendment) — charge components. `fee` has two permitted spellings.
CHARGE_PATTERNS = ("shipping", "packaging", "commission", "fee")
CHARGE_PAIRS = (("delivery", "charge"), ("convenience", "fee"))
FEE_ALLOWED = ("fee_asked_paise", "fee_paid")

#: Row — DOB. **No exception** (amendment 2026-10-21, CG-5).
DOB_EXACT = ("date_of_birth", "dob")
DOB_PATTERNS = ("birth",)

#: Row — precise location, except on `handover_points`.
LOCATION_PATTERNS = ("latitude", "longitude", "precise_location", "gps")
LOCATION_EXEMPT_TABLES = ("handover_points",)

#: Row — addresses, except `legal_entities.registered_address`.
ADDRESS_PATTERNS = ("street", "address_line", "pincode", "postal")
ADDRESS_EXEMPT = (("legal_entities", "registered_address"),)

#: ADR-003 §2.3's response-key rule, extended by the amendment.
FORBIDDEN_RESPONSE_KEYS = ("price", "amount", "total", "value")


def w1b_money_shaped(column):
    """ADR-003 §2.3 W1b, as written: contains any of the 22 tokens."""
    name = column.lower()
    return any(token in name for token in W1B_MONEY_TOKENS)


def w1_declared_non_monetary(column):
    """ADR-003 §2.3 W1, as written: the name **ends** in a declared suffix."""
    return column.lower().endswith(NON_MONETARY_SUFFIXES)
