"""P14 — the impossibility of storing a settled transaction price.

Written from ADR-003 §2.1–2.3 as amended 2026-10-21 (W1–W5), `DATA-MODEL.md` §0
and PRD EX-18.

**QA correcting itself first.** QA-S0 v1.0's aggregate finding measured
`tests/contract/denylist.py` — QA's own transcription of the ADR — and reported
its escapes as the shipped control's escapes. Backend's objection is correct and
is upheld: that is the same defect QA found in the guard, one layer up. Every
attack in this file is now run against the control the build enforces, through
`tests/contract/shipped_control.py`, which imports the guard and calls its
live-schema assertions over real DDL. An attack is "caught" if and only if the
build would go red.

Three questions, kept apart, because conflating them is what produced the v1.0
error:

1. **Does the shipped control stop the attack?** `test_attack_*`,
   measured against the real guard, one verdict per shape.
2. **Does the shipped control say what ADR-003 §2.3 says?** `test_conformance_*`.
   Measured against `denylist.py`, which is the ADR in data form — and the ADR
   itself (W1d) says this comparison should not be necessary.
3. **What can no schema control reach?** `test_a_computed_property_*` and
   ADR-003 §2.3 W5's two declared residuals.
"""

import pytest
from django.db import connection, transaction

from . import denylist as adr
from .shipped_control import control_catches, run_shipped_control, shipped

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

_IDENT_OK = set("abcdefghijklmnopqrstuvwxyz0123456789_")


def _ident(name):
    assert name and set(name) <= _IDENT_OK and not name[0].isdigit(), name
    return name


def _create(table, columns):
    """Add `columns` = [(name, sql_type)] to `table`, creating it if absent.

    Raw DDL inside the test's transaction, rolled back with it. Raw DDL on
    purpose: a model would be visible to Django's model meta, and the attack
    this file cares most about — a column added by `RunSQL` — is the one only
    `connection.introspection` can see (ADR-003 §2.3 W4 route 2).
    """
    _ident(table)
    with connection.cursor() as cur:
        if table not in connection.introspection.table_names(cur):
            cur.execute(f'CREATE TABLE "{table}" (id integer primary key)')
        for name, sql_type in columns:
            cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{_ident(name)}" {sql_type}')


def _live_columns():
    out = []
    with connection.cursor() as cur:
        for table in connection.introspection.table_names(cur):
            for col in connection.introspection.get_table_description(cur, table):
                out.append((table.lower(), col.name.lower()))
    return out


# --------------------------------------------------------------------------
# 1. the clean baseline — the guard passes on the real schema
# --------------------------------------------------------------------------


def test_the_shipped_control_passes_on_the_migrated_schema():
    """The baseline every attack below is measured against. If this failed, a
    "caught" result would mean nothing."""
    failures, errors = run_shipped_control()
    assert failures == [] and errors == [], (
        f"the P14 guard is already red on a clean schema: {failures} {errors}"
    )


def test_the_runner_sees_every_schema_reading_assertion():
    """Guards the runner. If the guard grows an assertion this runner cannot
    call, every "escaped" verdict below becomes unsafe, so that fails here
    instead of being silently under-measured."""
    import inspect

    from .shipped_control import _SKIP_NOT_SCHEMA_READING

    module = shipped()
    uncallable = []
    for name, fn in vars(module).items():
        if not name.startswith("test_") or not callable(fn):
            continue
        if name in _SKIP_NOT_SCHEMA_READING:
            continue
        params = list(inspect.signature(fn).parameters)
        if params and params != ["table"] and params != ["key"]:
            uncallable.append((name, params))
    assert uncallable == [], (
        "the shipped guard has assertions this runner cannot invoke, so the "
        f"attack measurements below are incomplete: {uncallable}"
    )


# --------------------------------------------------------------------------
# 2. the attack, measured against the shipped control
# --------------------------------------------------------------------------

#: (id, table, columns, note, residual_key_or_None)
#:
#: `residual_key` is set only for shapes ADR-003 §2.3 W5 **declares** are not
#: closable by any schema or source control. Everything else the ADR claims to
#: catch, so an escape there is a finding.
ATTACKS = [
    (
        "renamed_column_on_transfers", "transfers",
        [("consideration_paise", "integer")],
        "a differently-named money column on the transaction table", None,
    ),
    (
        "euphemism_on_transfers", "transfers",
        [("cash_handed_over", "integer")],
        "a money column named in plain English rather than in schema words", None,
    ),
    (
        "unit_rename_on_transfers", "transfers",
        [("rupees_exchanged", "integer")],
        "a money column named for its unit", None,
    ),
    (
        "unpredicted_name_on_transfers", "transfers",
        [("value_x", "integer")],
        "compliance's own example: the name nobody predicted", None,
    ),
    (
        "related_table", "transfer_settlements",
        [("amount_paise", "integer")],
        "the amount moved to a table the deny-list's row-2 table list does not name",
        None,
    ),
    (
        "related_table_euphemism", "transfer_settlements",
        [("cash_total", "integer")],
        "the same, renamed to escape a paise/price/rupee allow-list", None,
    ),
    (
        "float_money", "listings",
        [("asking_price_paise", "real")],
        "the one permitted column, declared as a float", None,
    ),
    (
        "decimal_money", "receipts",
        [("asking_price_paise", "numeric(10,2)")],
        "the same shape as a decimal, on another table", None,
    ),
    (
        "offer_amount", "offers",
        [("offer_amount_paise", "integer")],
        "an accepted offer amount IS a settled consideration "
        "(COMPLIANCE §4.3.2 item 4)", None,
    ),
    (
        "price_history", "listing_price_log",
        [("previous_price_paise", "integer")],
        "price history reconstructs the price at the moment of handover "
        "(item 5)", None,
    ),
    (
        "charge_component", "transfers",
        [("delivery_charge_paise", "integer")],
        "a charge component, which Circular 20/2023 folds into the gross "
        "amount (item 7)", None,
    ),
    (
        "dob_on_the_deleted_table", "age_check_pending",
        [("date_of_birth", "date")],
        "the exact table and column amendment A-5/CG-5 deleted", None,
    ),
    # --- the 22-token conformance gap, hunted as DDL ---------------------
    (
        "adr_token_amt_text", "receipts",
        [("amt", "text")],
        "ADR-003 W1b lists `amt`; a *text* column escapes W1a, which only looks "
        "at numeric columns", None,
    ),
    (
        "adr_token_paid_text", "receipts",
        [("paid", "text")],
        "ADR-003 W1b lists `paid`", None,
    ),
    (
        "adr_token_payment_text", "handover_log",
        [("payment_received", "text")],
        "ADR-003 W1b lists `payment`", None,
    ),
    (
        "adr_token_due_text", "receipts",
        [("due_inr", "text")],
        "ADR-003 W1b lists `due`", None,
    ),
    (
        "listings_exempt_table_text", "listings",
        [("cash_received", "text")],
        "W1b exempts the whole `listings` table, and a text column is invisible "
        "to W1a — so the money table itself is the softest target", None,
    ),
    (
        "listings_exempt_table_settlement", "listings",
        [("settlement", "text")],
        "the same, with a word the deny-list's `%settled%` does not match", None,
    ),
    # --- the residuals ADR-003 §2.3 W5 declares --------------------------
    (
        "jsonb_payload", "transfers", [("meta", "text")],
        "an amount inside a jsonb/text document: no column name to deny",
        "a number inside a jsonb document",
    ),
    (
        "free_text_note", "transfers", [("handover_note", "text")],
        "an amount typed into a text field: no control can read intent",
        "a number inside free text",
    ),
]


@pytest.mark.parametrize("attack", ATTACKS, ids=[a[0] for a in ATTACKS])
def test_attack_reaches_the_schema_the_control_reads(attack):
    """Each attack is executed, and the column really exists where the guard
    looks. Asserted separately so an "escaped" verdict can never be an attack
    that silently failed to apply."""
    attack_id, table, columns, _note, _residual = attack
    _create(table, columns)
    live = set(_live_columns())
    for name, _type in columns:
        assert (table, name) in live, f"{attack_id}: attack column was not created"


@pytest.mark.parametrize("attack", ATTACKS, ids=[a[0] for a in ATTACKS])
def test_attack_measured_against_the_shipped_control(attack):
    """One attack, one verdict, recorded per shape.

    A shape ADR-003 claims to cover must be caught. A shape ADR-003 §2.3 W5
    declares residual must **not** be reported as caught, because the ADR's
    position is that it is accepted exposure — if one of those starts being
    caught, W5 should be rewritten rather than left claiming the opposite.
    """
    attack_id, table, columns, note, residual = attack
    _create(table, columns)
    caught, failures, errors = control_catches()

    if residual is None:
        assert caught, (
            f"{attack_id}: {table}.{columns[0][0]} — {note}. The shipped P14 "
            "control does not fail the build on it, and ADR-003 §2.3 claims to "
            "cover it. See QA-S0.md."
        )
        assert not errors or failures, (
            f"{attack_id}: the guard went red by crashing rather than by "
            f"asserting: {errors}"
        )
    else:
        assert not caught, (
            f"{attack_id} is listed in ADR-003 §2.3 W5 as an accepted residual "
            f"({residual}) but the control now catches it: {failures}. Update W5."
        )


def test_a_computed_property_is_invisible_to_a_schema_level_control():
    """ADR-003 §2.3 W5's third residual, re-measured against the real guard.

    A Python `@property` that divides, sums or formats an amount exposes a
    settled price with no column anywhere. The ADR accepts this and W1c
    prescribes a source-level grep as the compensating control. QA's finding is
    that **W1c does not exist** — see `test_conformance_w1c_source_grep_exists`.
    """
    from apps.core.models import Campus

    before = set(_live_columns())
    Campus.settled_price_paise = property(lambda self: 30000)
    try:
        assert set(_live_columns()) == before
        assert Campus().settled_price_paise == 30000
        caught, _f, _e = control_catches()
        assert not caught, (
            "the schema control now sees a Python property; ADR-003 §2.3 W5 "
            "says it cannot, so one of the two should change"
        )
    finally:
        del Campus.settled_price_paise


# --------------------------------------------------------------------------
# 3. conformance — does the enforced control say what ADR-003 §2.3 says?
# --------------------------------------------------------------------------


def test_conformance_w1d_single_source_of_truth_module_exists():
    """**REGRESSION for QA-S0 F4** — the structural fix, and the one that makes
    the rest of this section nearly redundant.

    ADR-003 §2.3 W1d: *"The token sets, the suffix allow-list, the deny patterns
    and the frozen column lists live as **data in `apps/core/p14.py`**, which the
    tests import."* QA-S0 v2.0 found the module absent and the lists retyped into
    the guard, and found F6 and F7 — the divergence W1d was written to prevent —
    already present in that retyping.

    The module now exists and the guard imports from it rather than declaring
    its own copies. Asserted structurally: every list the guard uses must be the
    object `apps.core.p14` exports, not an equal copy, because an equal copy is
    exactly what drifts.
    """
    import importlib

    assert importlib.util.find_spec("apps.core.p14") is not None, (
        "ADR-003 §2.3 W1d requires the P14 lists to live as data in "
        "apps/core/p14.py, imported by the tests"
    )
    p14 = importlib.import_module("apps.core.p14")
    guard = shipped()
    shared = [
        "MONEY_COLUMN", "NON_MONETARY_WORDS", "W1B_MONEY_TOKENS",
        "MONEY_WORDS_EXEMPT", "FROZEN_TABLES", "FROZEN_ENUMS",
        "FORBIDDEN_COLUMNS", "FLOAT_TYPES", "NUMERIC_TYPES",
    ]
    not_shared = [
        name for name in shared
        if hasattr(guard, name) and getattr(guard, name) is not getattr(p14, name, object())
    ]
    assert not_shared == [], (
        "the guard holds its own copy of these rather than the object "
        f"apps/core/p14.py exports: {not_shared}. An equal copy is what drifted "
        "last time."
    )


def test_conformance_w1c_source_grep_exists():
    """**REGRESSION for QA-S0 F5.** ADR-003 §2.3 W1c requires a CI grep of
    `apps/**` for money-shaped model fields, properties, serialiser keys and
    response keys. QA-S0 v2.0 measured that no test in `tests/unit` or
    `tests/api` read a source file at all, which left the `@property` residual
    ADR-003 §2.3 W5 accepts with no compensating control.

    `tests/unit/test_forbidden_source.py` now exists, reads `apps/**` and
    asserts it is not looking at an empty list. Both halves are asserted,
    because a grep that silently matches nothing is this project's recurring
    defect and the second half is what rules it out.
    """
    import importlib
    import pathlib

    repo = pathlib.Path(__file__).resolve().parents[2]
    path = repo / "tests" / "unit" / "test_forbidden_source.py"
    assert path.exists(), "ADR-003 §2.3 W1c's source grep does not exist"

    text = path.read_text(encoding="utf-8")
    assert "rglob" in text and "apps" in text, "the grep does not read apps/**"
    assert "pass vacuously" in text, (
        "the grep must assert it found something; one that silently matches "
        "nothing is a green test that asserted nothing"
    )

    module = importlib.import_module("tests.unit.test_forbidden_source")
    found = module.declared_identifiers()
    assert len(found) > 100, (
        f"the grep sees only {len(found)} declarations in apps/**, which is too "
        "few to be reading the tree"
    )


def test_conformance_the_w1b_token_set_matches_the_adr():
    """**REGRESSION for QA-S0 F6.** The guard enforced 15 of ADR-003 §2.3 W1b's
    22 tokens, and `amt`, `paid`, `payment` and `due` were caught by nothing.

    All 22 are now enforced, and against **every column in any type** rather
    than only numeric ones — which is what let a text column through.
    """
    import importlib

    p14 = importlib.import_module("apps.core.p14")
    enforced = tuple(p14.W1B_MONEY_TOKENS)
    missing = [token for token in adr.W1B_MONEY_TOKENS if token not in enforced]
    assert missing == [], (
        f"ADR-003 §2.3 W1b tokens not enforced: {missing}"
    )
    assert len(enforced) == 22, (
        f"W1b states 22 tokens; apps/core/p14.py holds {len(enforced)}"
    )


def test_conformance_the_w1b_exemption_is_two_columns_not_a_table():
    """**REGRESSION for QA-S0 F7.** The guard exempted the whole `listings`
    table from the money-token rule, making the one table permitted to hold
    money the softest target in the schema: `listings.cash_received text` and
    `listings.settlement text` were stored on a green build.

    The exemption is now scoped to two named columns, and the table-wide name is
    kept and set to `None` so the change is visible rather than silent — which
    is what QA asked for and is better than deleting it.
    """
    import importlib

    p14 = importlib.import_module("apps.core.p14")
    assert p14.MONEY_WORDS_EXEMPT_TABLE is None
    assert set(p14.MONEY_WORDS_EXEMPT) == {
        ("listings", "asking_price_paise"),
        ("listings", "price_fixed_at"),
    }, sorted(p14.MONEY_WORDS_EXEMPT)


@pytest.mark.parametrize(
    "column,caught",
    [
        # The three exempted shapes, in the names the contracts mandate.
        ("purge_due_at", False),
        ("act_due_at", False),
        ("sla_due_at", False),
        ("disposal_due_at", False),
        ("jobs_overdue", False),
        ("consume_magic_link", False),
        # The same shapes, carrying an amount. None may be swallowed.
        ("amount_due_at", True),
        ("due_at_paise", True),
        ("cash_due_at", True),
        ("settlement_due_at", True),
        ("overdue_amount", True),
        ("cash_overdue", True),
        ("overdue_balance", True),
        ("consume_price", True),
        ("consumed_total", True),
        ("consume_amount_paise", True),
        # And the bare tokens the exemptions are carved out of.
        ("due_inr", True),
        ("amount_due", True),
        ("due_paise", True),
        ("sum_paise", True),
        ("cash_sum", True),
    ],
)
def test_the_token_shape_exemptions_cannot_hide_an_amount(column, caught):
    """**Attack on the new allowance** (ENGINE-DIVERGENCE §9 item 9).

    `MONEY_TOKEN_SHAPE_EXEMPTIONS` is an *allowance*, not a tightening: three
    shapes — `due_at`, `overdue`, `consume` — stop a W1b token matching. Two of
    them exist because `due` collides with about fifteen SLA-clock columns the
    schema mandates and `sum` is inside `consume_magic_link`, a frozen
    signature. The reasoning is sound and the ADR's discriminating question is
    the right one, but an exemption is a hole until someone tries to climb
    through it.

    So QA re-derived the cases rather than re-running backend's six: for each
    exempted shape, the contract-mandated name must pass **and** the same shape
    carrying any money token must still fail. The matcher strips exempted shapes
    and re-searches, so the interesting cases are the ones where stripping could
    destroy evidence — `consumed_total`, `cash_due_at`, `overdue_balance`.
    """
    import importlib

    p14 = importlib.import_module("apps.core.p14")
    hits = p14.money_tokens_in(column)
    if caught:
        assert hits, (
            f"{column!r} carries a W1b money token that the shape exemptions "
            "swallow — the allowance is wider than ENGINE-DIVERGENCE §9 item 9 "
            "claims"
        )
    else:
        assert not hits, (
            f"{column!r} is a name three frozen contracts mandate and the guard "
            f"flags it on {hits}; REVIEW-S0 M2 is how that ends"
        )


def test_finding_the_rs_token_will_false_positive_on_an_ordinary_plural():
    """**FINDING F12, non-blocking, lands in S2/S4.**

    W1b's 22nd token is `rs_`, now enforced. It matches any column whose name
    contains a plural followed by an underscore: `offers_count`,
    `members_count`, `reports_count`, `users_seen`, `errors_total`. Backend
    rejected `rs_` for exactly this reason in the previous round — *"a guard
    test whose first real encounter with the codebase is a false positive
    teaches a developer that the guard is wrong"* — and then enforced all 22
    tokens to close F6, which is the right trade but reinstates the collision.

    No such column exists today, so the guard is green and this is not an S0
    blocker. It becomes live at the first `*rs_*` column, and `offers_count` on
    a listing or `reports_count` on a user are both plausible in S2/S4. The
    answer is the mechanism that already exists — a
    `MONEY_TOKEN_SHAPE_EXEMPTIONS` entry — plus an ADR-003 §2.3 W1b note, and
    deciding it now is cheaper than deciding it in a slice under pressure with a
    red founder-escalating file.
    """
    import importlib

    p14 = importlib.import_module("apps.core.p14")
    for plural in ("offers_count", "members_count", "users_seen",
                   "authors_count", "followers_count"):
        assert "rs_" in plural, plural
        # The finding: `rs_` is the only token each of these carries, so each
        # would fail CI on a name that is plainly a count.
        assert p14.money_tokens_in(plural) == ["rs_"], (
            plural, p14.money_tokens_in(plural)
        )

    # Today's schema is clean, which is why this is a prediction and not a bug.
    caught, _failures, _errors = control_catches()
    assert not caught


def test_conformance_the_dob_exception_is_withdrawn():
    """**REGRESSION for QA-S0 F2(a)** — was a failing finding, now the fixed
    behaviour.

    QA-S0 v1.0 found the guard still mapping `date_of_birth`, `dob` and `birth`
    to a permitted table `age_check_pending`, which amendment A-5 deleted and
    ADR-003 §2.3 row 6 (CG-5) forbids with no exception. QA demonstrated it by
    creating the table and watching the guard pass. This asserts the fix from
    the other side: the ADR's position, read out of the enforced data.
    """
    module = shipped()
    conditional = getattr(module, "CONDITIONAL_COLUMNS", {})
    for pattern in adr.DOB_EXACT + adr.DOB_PATTERNS:
        assert conditional.get(pattern, None) is None, (
            f"ADR-003 §2.3 row 6 as amended grants no exception for {pattern!r}; "
            f"the guard permits it on {conditional.get(pattern)!r}"
        )


def test_regression_a_dob_column_is_now_refused():
    """**REGRESSION for QA-S0 F2(a)**, the demonstration half.

    v1.0's `test_demonstration_a_dob_column_passes_the_shipped_control` created
    `age_check_pending(date_of_birth date)` and asserted the guard let it
    through, which it did. The same DDL now fails the build. Kept under a name
    that traces to the finding so the regression is not mistaken for a new test.
    """
    _create("age_check_pending", [("date_of_birth", "date")])
    caught, failures, _errors = control_catches()
    assert caught, (
        "QA-S0 F2(a) regression: a `date_of_birth` column on the deleted "
        "`age_check_pending` table no longer fails the P14 guard"
    )
    assert any("dob" in msg.lower() or "birth" in msg.lower() for _n, msg in failures), (
        f"the guard fired, but not on the DOB rule: {failures}"
    )


def test_conformance_the_deny_list_rows_are_all_present():
    """The amendment added four deny-list rows (items 4–7). Each is asserted
    present in the enforced data, because an amendment that lands in prose and
    not in code is F4 happening again."""
    module = shipped()
    enforced = {p for p, _exact in getattr(module, "FORBIDDEN_COLUMNS", [])}
    expected = set(
        adr.SETTLED_PATTERNS + adr.GOVT_ID_EXACT + adr.GOVT_ID_PATTERNS
        + adr.INSTRUMENT_PATTERNS + adr.BALANCE_PATTERNS + adr.OFFER_PATTERNS
        + adr.HISTORY_PATTERNS + adr.DERIVATION_PATTERNS + adr.CHARGE_PATTERNS
    )
    # An enforced pattern covers an ADR pattern when either contains the other:
    # `ledger` is *wider* than the ADR's `%ledger_entry%` and deliberately so —
    # it closes the `ledger_entries` pluralisation near-miss QA-S0 F2 recorded.
    # A wider guard is not a conformance failure; a narrower one is.
    missing = sorted(
        pattern for pattern in expected
        if not any(pattern in e or e in pattern for e in enforced)
    )
    assert missing == [], (
        f"ADR-003 §2.3 deny-list patterns not enforced: {missing}"
    )


def test_the_ledger_entries_pluralisation_near_miss_is_closed():
    """**REGRESSION for QA-S0 F2's near-miss (a).** `%ledger_entry%` does not
    match `ledger_entries`, which is what Django pluralises `LedgerEntry` into.
    The guard now denies `ledger` instead, which is wider than ADR-003 §2.3 row
    5 as written — so the fix is real and the ADR's wording is now the thing
    that lags. Recorded as a wording amendment in QA-S0.md, not as a defect.
    """
    _create("ledger_entries", [("note", "text")])
    caught, failures, _errors = control_catches()
    assert caught, "a table named `ledger_entries` no longer fails the guard"
    assert any("ledger" in msg.lower() for _n, msg in failures), failures


def test_conformance_the_frozen_tables_are_the_four_the_adr_names():
    module = shipped()
    assert set(getattr(module, "FROZEN_TABLES", {})) == set(adr.W2_FROZEN_TABLES)


def test_conformance_the_frozen_enum_values_match_the_adr():
    """`DATA-MODEL.md` §5 promises "no question about money, ever", and ADR-003
    §2.3 W2's instruction is to promise it in the test. Asserted by value."""
    module = shipped()
    enforced = getattr(module, "FROZEN_ENUMS", {})
    for key, values in adr.W2_FROZEN_ENUMS.items():
        assert key in enforced, f"ADR-003 §2.3 W2 freezes {key}; the guard does not"
        assert set(enforced[key]) == set(values), (
            f"{key}: guard enforces {sorted(enforced[key])}, ADR-003 §2.3 W2 "
            f"says {sorted(values)}"
        )



# --------------------------------------------------------------------------
# 3a. W1c's source grep — the detector, attacked rather than trusted
# --------------------------------------------------------------------------


def _grep():
    import importlib

    return importlib.import_module("tests.unit.test_forbidden_source")


def _sees(snippet):
    """Every identifier the shipped grep's regexes extract from `snippet`."""
    module = _grep()
    return {
        match.group(1)
        for pattern in module.DECLARATIONS
        for match in pattern.finditer(snippet)
    }


@pytest.mark.parametrize(
    "shape,snippet,identifier",
    [
        ("@property",
         "    @property\n    def settled_price_paise(self):\n        return 1\n",
         "settled_price_paise"),
        ("@cached_property",
         "    @cached_property\n    def cash_total(self):\n        return 1\n",
         "cash_total"),
        ("a plain method",
         "    def amount_received(self):\n        pass\n",
         "amount_received"),
        ("a model field",
         "    paid_amount = models.IntegerField()\n",
         "paid_amount"),
        ("a serialiser / response key",
         '    return {"total": 1}\n',
         "total"),
        ("an annotated class attribute",
         "    settlement_total: int = 0\n",
         "settlement_total"),
    ],
)
def test_the_source_grep_sees_every_declaration_shape_adr_w1c_names(
    shape, snippet, identifier
):
    """ADR-003 §2.3 W1c names five declaration kinds — model field, `@property`,
    `@cached_property`, serialiser key and API response key. QA re-derived them
    from the ADR rather than re-running the guard's own six cases, and asserts
    each is visible to at least one regex **and** recognised as money-shaped.

    Backend's reasoning for having this guard at all is right and worth keeping
    in writing: a grep that silently matches nothing is this project's recurring
    defect, so the detector needs a detector. QA's contribution is to derive the
    cases from the contract instead of from the implementation.
    """
    assert identifier in _sees(snippet), (
        f"no DECLARATIONS regex sees a {shape}: {snippet!r}"
    )
    import importlib

    p14 = importlib.import_module("apps.core.p14")
    assert p14.money_tokens_in(identifier), f"{identifier!r} is not money-shaped"


@pytest.mark.parametrize(
    "shape,snippet,identifier",
    [
        ("a property assigned rather than decorated",
         "    settled_price_paise = property(lambda self: 30000)\n",
         "settled_price_paise"),
        ("a bare class constant",
         "    cash_received = 30000\n",
         "cash_received"),
        ("an annotation with no assignment",
         "    amount_paid: int\n",
         "amount_paid"),
    ],
)
def test_finding_the_source_grep_misses_three_declaration_shapes(
    shape, snippet, identifier
):
    """**FINDING F13, non-blocking, one line each to close.**

    The grep sees `def`, `x = models.Field(...)`, `"key":` and `x: type = ...`.
    Three money-shaped declaration shapes are outside all four:

    1. **`settled_price_paise = property(lambda self: 30000)`** — a property
       *assigned* rather than decorated. This is the exact shape QA used to
       demonstrate the `@property` residual in QA-S0 v1.0 and v2.0, and it is
       the one W1c exists for. The decorated form is caught; this one is not.
    2. **`cash_received = 30000`** — a bare class constant.
    3. **`amount_paid: int`** — an annotation with no assignment, which is how a
       dataclass or a `NamedTuple` field is written.

    Severity: lower than it sounds, and QA says so rather than inflating it. The
    schema control catches any of these that reaches a column, and (1) and (3)
    both require a developer to pick an unusual spelling. But W1c is the **only**
    control for a computed money value — ADR-003 §2.3 W5 says so — so a gap in
    it is a gap in the whole of that control.

    The fix is two regexes:
    `^\\s*(\\w+)\\s*=\\s*(?:property|cached_property)\\(` and
    `^\\s*(\\w+)\\s*:\\s*\\w+\\s*$`. A blanket `^\\s*(\\w+)\\s*=` would also
    catch (2) but would match local variables inside functions, and a guard
    whose first encounter with the codebase is a false positive teaches a
    developer that the guard is wrong — this project's own reasoning, and the
    reason QA is not recommending it.

    Belongs in S1, with the first real `@property` on a model. Not an S0
    blocker: nothing in `apps/**` uses any of the three shapes today, which
    `test_the_source_grep_is_green_on_the_current_tree` confirms.
    """
    assert identifier not in _sees(snippet), (
        f"the grep now sees {shape}; F13 is closed and this test should become a "
        "regression"
    )
    import importlib

    p14 = importlib.import_module("apps.core.p14")
    assert p14.money_tokens_in(identifier), (
        f"{identifier!r} is money-shaped, so the miss matters"
    )


def test_the_source_grep_is_green_on_the_current_tree():
    """F13's severity rests on this: the three missed shapes are not in use."""
    module = _grep()
    module.test_no_declared_identifier_in_apps_is_money_shaped()
    module.test_no_forbidden_response_key_is_declared_in_apps()


def test_the_source_greps_exclusion_cannot_widen():
    """`apps/core/p14.py` is excluded from its own grep, necessarily — it *is*
    the token list, so every token appears in it. The exclusion must stay a
    named file and never become a pattern, or the next excluded path is the one
    with the property in it."""
    module = _grep()
    assert module.EXCLUDED_FILES == {"apps/core/p14.py"}, module.EXCLUDED_FILES
    for entry in module.EXCLUDED_FILES:
        assert "*" not in entry and "?" not in entry, (
            f"the grep's exclusion list contains a pattern, not a file: {entry!r}"
        )


# --------------------------------------------------------------------------
# 4. the response boundary
# --------------------------------------------------------------------------


def test_the_operational_responses_contain_no_forbidden_key(client):
    """ADR-003 §2.3: the prohibition holds at the contract boundary too, and the
    amendment adds that no response key may be named `price`, `amount`, `total`
    or `value`. S0 exposes two responses; both are checked."""
    for path in ("/healthz", "/readyz"):
        body = client.get(path).content.decode().lower()
        for token in adr.FORBIDDEN_RESPONSE_KEYS + ("paise", "settled", "wallet",
                                                    "upi", "dob", "aadhaar"):
            assert token not in body, f"{path} response contains {token!r}"


def test_the_response_schema_guard_has_no_owning_slice(engine):
    pytest.skip(
        f"NOT VERIFIABLE IN S0 (engine={engine}): ADR-003 §2.3 and "
        "THREAT-MODEL §6 both name `tests/unit/test_forbidden_response.py`, and "
        "ENGINE-DIVERGENCE §9 item 7 records that it still has no owning slice. "
        "It is also the compensating control ADR-003 §2.3 W5 relies on for the "
        "jsonb and free-text residuals. QA cannot write it — it is "
        "backend-developer's tree — and there is no response payload in S0 to "
        "run it against. Escalated in QA-S0.md, not tested here."
    )


# --------------------------------------------------------------------------
# 5. what P14 needs and S0 cannot provide
# --------------------------------------------------------------------------


def test_price_immutability_trigger(engine):
    pytest.skip(
        f"NOT VERIFIABLE IN S0 (engine={engine}): ADR-003 §2.2's "
        "`listings_price_immutable` trigger guards a table `listings` that slice "
        "S2 creates; the plpgsql body is unexecuted text until a PostgreSQL "
        "server exists (ENGINE-DIVERGENCE §3.9, §9 item 3)."
    )


def test_the_money_column_is_rejected_as_a_float_by_the_engine(engine):
    pytest.skip(
        f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S2): ADR-003 "
        "§2.1's 'integer paise, no floats for money, ever' is enforced by the "
        "PostgreSQL type system. ENGINE-DIVERGENCE §2.8 measured that this "
        "engine stores 300.75 in an `integer NOT NULL` column. The *guard* "
        "against a float declaration is now verified above "
        "(`float_money`, `decimal_money`); the *engine's* rejection of a float "
        "value in an integer column is not, and cannot be here."
    )
