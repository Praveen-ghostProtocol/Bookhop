"""P14 — ADR-003 §2.3 as amended 2026-10-21 (`COMPLIANCE.md` §4.3.2).

**Every list this file enforces lives in `apps/core/p14.py`** and is imported,
not retyped (ADR-003 §2.3 W1d). That module's docstring has the incident that
made W1d a requirement; the short version is that a hand-copied control
silently diverged from its specification twice, once in the commit that was
fixing the first divergence. **Do not inline a list back into this file.**

The layers, in the order they catch things:

  W1   every numeric column must be `listings.asking_price_paise` or carry a
       ratified non-monetary name. `value_x`, `amt`, `consideration` and `paid`
       fail on sight, without anyone having predicted the name.
  W1a  the one permitted money column must be an **integer** type, and no float
       or decimal column exists anywhere. Names carry no types, and QA-S0 F1
       attack 7 declared `asking_price_paise` as `real`.
  W1b  **no column anywhere, in any type, may contain a money token**, except
       the two columns ADR-003 names. The "any type" is what catches
       `receipts.amt text`; the column-scoped exemption is what catches
       `listings.cash_received text` (QA-S0 F6/F7).
  W2   the four transaction tables have their full column lists frozen.
  W3   the deny-list, kept for its error message: a whitelist failure says
       "`value_x` is not an allowed numeric column", a deny-list failure can
       say "`offered_price` is a settled consideration — read ADR-003 §2.3".

W1c, the source-level grep, is `tests/unit/test_forbidden_source.py`.

**How the schema is read (W4).** Two engine-neutral routes — never
`information_schema` (SQLite has none), never `PRAGMA table_info` (a test that
branches on the engine has two code paths and one is never exercised):

  1. Django model meta, which fails at the point a developer adds the field;
  2. `connection.introspection`, which catches a column added by `RunSQL`.

**They compose differently for names than for types, and conflating them
inverted W1a's purpose** (ADR-003 §2.3's amendment on REVIEW-S0 R2):

  * **names** — model meta overrides introspection: a declared field is the
    stronger fact about what the codebase intends;
  * **types** — **union, not override**: the float check fails if *either*
    route reports a non-integer. Never trust the declaration about the thing
    the declaration is suspected of misrepresenting. In S0 `listings` has no
    model, so an `ALTER COLUMN … TYPE real` is visible either way; from S2 it
    does, and an override would mask exactly the attack W1a was written for.

**Residual exposure, recorded rather than papered over** (ADR-003 §2.3 W5):
a jsonb document or a free-text column can always hold a number, and a Python
`@property` changes zero columns. W1c is the control for the third;
`tests/unit/test_forbidden_response.py`, which ADR-003 §2.3 and THREAT-MODEL §6
both name, **still has no owning slice** (REVIEW-S0 N2) and is the compensating
control for the first.
"""

import pytest
from django.apps import apps as django_apps
from django.db import connection

from apps.core.p14 import (  # ADR-003 §2.3 W1d — one definition, imported
    ALLOWED_TABLE_NAMES,
    CONDITIONAL_COLUMNS,
    DECLARED_NON_MONETARY,
    FAIL,
    FEE_ALLOWED,
    FLOAT_EXEMPT,
    FLOAT_TYPES,
    FORBIDDEN_COLUMNS,
    FORBIDDEN_PAIRS,
    FROZEN_ENUMS,
    FROZEN_TABLES,
    MONEY_COLUMN,
    MONEY_COLUMN_INTEGER_TYPES,
    MONEY_TOKEN_SHAPE_EXEMPTIONS,
    MONEY_WORDS_EXEMPT,
    MONEY_WORDS_EXEMPT_TABLE,
    NON_MONETARY_WORDS,
    NUMERIC_TYPES,
    TRANSACTION_TABLE_PREFIXES,
    W1B_MONEY_TOKENS,
    is_declared_non_monetary,
    matches,
    money_tokens_in,
)

pytestmark = pytest.mark.django_db

#: Names test-qa's conformance harness reads off this module
#: (`tests/contract/test_p14.py`). Aliased rather than redefined.
MONEY_WORDS = W1B_MONEY_TOKENS


# --- reading the schema (W4) ----------------------------------------------


def model_schema():
    """{(table, column): internal_type} from Django model meta."""
    schema = {}
    for model in django_apps.get_models():
        table = model._meta.db_table.lower()
        for field in model._meta.concrete_fields:
            schema[(table, (field.db_column or field.column).lower())] = field.get_internal_type()
    assert schema, "model meta returned no fields — every assertion here would pass vacuously"
    return schema


def live_schema():
    """{table: [columns]} from connection.introspection, on either engine.

    The emptiness assertion lives here, not in one caller, so none of the
    assertions below can pass trivially if introspection returns nothing
    (REVIEW-S0 S8).
    """
    with connection.cursor() as cursor:
        tables = [t for t in connection.introspection.table_names(cursor) if not t.startswith("sqlite_")]
        schema = {
            table.lower(): [
                c.name.lower() for c in connection.introspection.get_table_description(cursor, table)
            ]
            for table in tables
        }
    assert schema, "introspection returned no tables — every assertion here would pass vacuously"
    assert any(schema.values()), "introspection returned no columns"
    return schema


def introspected_types():
    """{(table, column): django_field_type | None} from introspection.

    `get_field_type()` is Django's own mapping and exists for both backends, so
    this stays engine-neutral. A type Django cannot map yields None and the
    type assertions **fail closed** on it: `numeric` and `double precision` are
    exactly the shapes they hunt.
    """
    types = {}
    with connection.cursor() as cursor:
        for table in connection.introspection.table_names(cursor):
            if table.startswith("sqlite_"):
                continue
            for column in connection.introspection.get_table_description(cursor, table):
                try:
                    field_type = connection.introspection.get_field_type(column.type_code, column)
                except Exception:
                    field_type = None
                types[(table.lower(), column.name.lower())] = field_type
    assert types, "introspection returned no columns — every assertion here would pass vacuously"
    return types


def all_columns():
    """Every (table, column) either route can see. Names only."""
    pairs = set(model_schema())
    for table, columns in live_schema().items():
        pairs.update((table, column) for column in columns)
    return pairs


def typed_columns_for_names():
    """Model meta overrides introspection — the right precedence for *names*."""
    merged = dict(introspected_types())
    merged.update(model_schema())
    return merged


def all_type_reports():
    """{(table, column): [every type either route reports]} — the **union**.

    The precedence that is right for names is backwards for types: W1a exists
    to see what the database actually holds, so a model's `IntegerField` must
    not be allowed to vouch for a column the database stores as `real`.

    Both routes are read once per call rather than once per column: reading
    them per column made the guard quadratic, and test-qa's attack suite runs
    the whole guard once per attack.
    """
    introspected, declared = introspected_types(), model_schema()
    reports = {}
    for source in (introspected, declared):
        for table_column, field_type in source.items():
            reports.setdefault(table_column, []).append(field_type)
    return reports


def type_reports(table_column):
    return all_type_reports().get(table_column, [])


# --- W1 · the whitelist ---------------------------------------------------


def test_every_numeric_column_is_the_money_column_or_declared_non_monetary():
    """One assertion in place of a list that has to keep growing.

    Runs over both routes, so a numeric column added by `RunSQL` is covered.
    """
    for (table, column), internal_type in sorted(
        typed_columns_for_names().items(), key=lambda kv: kv[0]
    ):
        if internal_type not in NUMERIC_TYPES:
            continue
        if (table, column) == MONEY_COLUMN or (table, column) in DECLARED_NON_MONETARY:
            continue
        assert is_declared_non_monetary(column), FAIL.format(
            table=table, column=column,
            why=f"a numeric column ({internal_type}) that is neither "
                f"{MONEY_COLUMN[0]}.{MONEY_COLUMN[1]} nor named with a ratified "
                f"non-monetary word {NON_MONETARY_WORDS}",
        )


def test_there_is_at_most_one_money_column_and_it_is_the_permitted_one():
    found = {
        (table, column)
        for (table, column), internal_type in typed_columns_for_names().items()
        if internal_type in NUMERIC_TYPES
        and not is_declared_non_monetary(column)
        and (table, column) not in DECLARED_NON_MONETARY
    }
    assert found <= {MONEY_COLUMN}, FAIL.format(
        table="(several)", column=sorted(f"{t}.{c}" for t, c in found),
        why="ADR-003 §2.1 permits exactly one money column in the entire database",
    )


# --- W1b · money tokens, every column, every type -------------------------


def test_no_column_anywhere_contains_a_money_token():
    """ADR-003 §2.3 W1b: *"any column whose name contains any of these,
    anywhere in the database, must be `listings.asking_price_paise` or the
    build fails."*

    Two things this fixes, both measured by QA-S0:

    * **F6 — it reads every column, not only numeric ones.** W1 inspects types,
      so `receipts.amt text`, `receipts.paid text`,
      `handover_log.payment_received text` and `receipts.due_inr text` each
      stored a settled price on a green build.
    * **F7 — the exemption is two columns, not the `listings` table.**
      `listings.cash_received text` and `listings.settlement text` escaped,
      which made the one table allowed to hold money the softest target in the
      schema.
    """
    for table, column in sorted(all_columns()):
        if (table, column) in MONEY_WORDS_EXEMPT:
            continue
        hits = money_tokens_in(column)
        assert not hits, FAIL.format(
            table=table, column=column,
            why=f"its name contains the money token(s) {hits}; ADR-003 §2.3 W1b "
                f"permits money-shaped names only at {sorted(MONEY_WORDS_EXEMPT)}",
        )


def test_no_money_shaped_table_name_exists():
    """`settlements`, `transfer_settlements` and `handovers_cash` fail here."""
    for table in sorted(live_schema()):
        hits = money_tokens_in(table)
        assert not hits, FAIL.format(
            table=table, column="(table name)",
            why=f"the table name contains the money token(s) {hits}",
        )


# --- W1a · the type, not only the name ------------------------------------


def test_no_float_or_decimal_column_exists_anywhere():
    """ADR-003 §2.1: "Integer paise. No floats for money, ever."

    Asserted over the whole schema rather than one column, because the local
    engine does not enforce column types at all — it stores `300.75` in an
    `integer NOT NULL` and returns it as a float (ENGINE-DIVERGENCE §2.8) — and
    because a name-based control reads no types. This is the one part of P14
    that can be *checked* rather than named.

    **Union of both routes**, so a model's `IntegerField` cannot vouch for a
    column the database holds as `real`, and **fails closed** on a type Django
    cannot classify.
    """
    every = all_type_reports()
    for table_column in sorted(every):
        if table_column in FLOAT_EXEMPT:
            continue
        reports = every[table_column]
        table, column = table_column
        assert reports and all(r is not None for r in reports), FAIL.format(
            table=table, column=column,
            why=f"its declared type could not be classified (reports: {reports}), so "
                "it cannot be shown not to be a float money column — declare it "
                "through a Django model",
        )
        bad = [r for r in reports if r in FLOAT_TYPES]
        if bad:
            pytest.fail(FAIL.format(
                table=table, column=column,
                why=f"reported as {bad} by at least one route; no float or decimal "
                    "column is permitted outside handover_points' public-landmark "
                    "coordinates",
            ))


@pytest.mark.skipif(
    not django_apps.all_models.get("listings", {}).get("listing"),
    reason="`listings` is created in S2 (TASKS.md §2); the schema-wide float rule "
           "above already forbids declaring asking_price_paise as real or numeric",
)
def test_the_money_column_is_an_integer_type():
    reports = type_reports(MONEY_COLUMN)
    assert reports, "listings.asking_price_paise is missing (ADR-003 §2.1)"
    assert all(r in MONEY_COLUMN_INTEGER_TYPES for r in reports), (
        f"ADR-003 §2.3 W1a: asking_price_paise must be an integer type on every "
        f"route, got {reports}"
    )


def test_fee_columns_if_they_ever_exist_have_only_the_two_permitted_shapes():
    """ADR-003 §3 fixes the shape of a future fee before anyone builds one:
    `fee_asked_paise` computed from the asking price, and `fee_paid` as a
    **boolean, never an amount**. W1b forbids both names outright today, so a
    fee also needs that exemption amended — which is the point."""
    for (table, column), internal_type in sorted(model_schema().items()):
        if "fee" not in column:
            continue
        assert column in FEE_ALLOWED, FAIL.format(
            table=table, column=column,
            why="the only permitted fee columns are fee_asked_paise and fee_paid "
                "(ADR-003 §3), and W1b forbids even those until amended",
        )
        if column == "fee_paid":
            assert internal_type == "BooleanField", (
                "ADR-003 §3: fee_paid is a boolean, never an amount"
            )


# --- W2 · frozen column lists ---------------------------------------------


@pytest.mark.parametrize("table", sorted(FROZEN_TABLES))
def test_frozen_column_list(table):
    slice_name, expected = FROZEN_TABLES[table]
    actual = {column for (t, column) in model_schema() if t == table}
    if not actual:
        pytest.skip(f"`{table}` is created in {slice_name} (TASKS.md §2)")
    assert actual == expected, (
        f"FROZEN COLUMN LIST (DATA-MODEL.md A-11, ADR-003 §2.3 W2): {table} "
        f"added {sorted(actual - expected)} and removed {sorted(expected - actual)}. "
        "Any new column on transfers, transfer_events, messages or "
        "transfer_followups fails the build until apps/core/p14.py's expected "
        "list is edited, and that edit is a founder escalation."
    )


@pytest.mark.parametrize("key", sorted(FROZEN_ENUMS))
def test_frozen_enum_value_set(key):
    """DATA-MODEL §5's "no question about money, ever" lived only in prose
    until A-11 put it in a test."""
    table, column = key
    model = next((m for m in django_apps.get_models() if m._meta.db_table == table), None)
    if model is None:
        pytest.skip(f"`{table}` is created in S5 (TASKS.md §2)")
    field = model._meta.get_field(column)
    actual = {value for value, _label in (field.choices or [])}
    assert actual == FROZEN_ENUMS[key], (
        f"FROZEN ENUM (DATA-MODEL.md A-11): {table}.{column} is "
        f"{sorted(actual)}, expected {sorted(FROZEN_ENUMS[key])}"
    )


# --- W3 · the deny-list ---------------------------------------------------


def test_no_forbidden_column_exists():
    for table, column in sorted(all_columns()):
        for pattern, exact in FORBIDDEN_COLUMNS:
            if pattern == "fee" and column in FEE_ALLOWED:
                continue
            assert not matches(column, pattern, exact), FAIL.format(
                table=table, column=column, why=f"matches the forbidden pattern {pattern!r}",
            )
        for first, second in FORBIDDEN_PAIRS:
            assert not (first in column and second in column), FAIL.format(
                table=table, column=column, why=f"matches the forbidden pattern %{first}%{second}%",
            )


def test_conditionally_forbidden_columns_only_where_permitted():
    for table, column in sorted(all_columns()):
        for pattern, permitted in CONDITIONAL_COLUMNS.items():
            if pattern not in column:
                continue
            if permitted is not None and (table, column) == permitted:
                continue
            pytest.fail(FAIL.format(
                table=table, column=column,
                why=f"matches {pattern!r}, permitted only at "
                    f"{'nowhere' if permitted is None else permitted[0] + '.' + permitted[1]}",
            ))


def test_no_money_column_on_a_transaction_table():
    """ADR-003 §2.3 row 2: the price belongs to the listing, never to the
    transaction. Redundant against W1b and kept for the error message."""
    for table, column in sorted(all_columns()):
        if not table.startswith(TRANSACTION_TABLE_PREFIXES) or table in ALLOWED_TABLE_NAMES:
            continue
        hits = money_tokens_in(column)
        assert not hits, FAIL.format(
            table=table, column=column,
            why=f"a money column (tokens {hits}) on a transaction table — the "
                "transfer is the thing s194-O cares about",
        )


def test_no_forbidden_table_name():
    for table in sorted(live_schema()):
        if table in ALLOWED_TABLE_NAMES:
            continue
        for pattern, exact in FORBIDDEN_COLUMNS:
            if pattern == "fee":
                continue  # a table cannot be named fee_asked_paise/fee_paid
            assert not matches(table, pattern, exact), FAIL.format(
                table=table, column="(table name)",
                why=f"table name matches the forbidden pattern {pattern!r}",
            )


# --- the guard's own guards ------------------------------------------------


def test_the_withdrawn_dob_exception_is_gone():
    """Pinned so it cannot come back by a careless revert. CG-5 withdrew the
    `age_check_pending` exception and A-5 deleted the table; for a while the
    shipped control still mapped all three DOB patterns to it, so the one shape
    the amendment was written to forbid was the one shape still permitted."""
    for pattern in ("date_of_birth", "dob", "birth"):
        assert CONDITIONAL_COLUMNS[pattern] is None, (
            f"ADR-003 §2.3 as amended: {pattern!r} has NO permitted table. "
            "No DOB is persisted anywhere, in any state (DATA-MODEL A-5)."
        )


def test_the_w1b_exemption_is_scoped_to_columns_not_a_table():
    """QA-S0 F7, pinned. A table-wide exemption is a hole shaped like a
    convenience, and it made the money table the softest target."""
    assert MONEY_WORDS_EXEMPT_TABLE is None
    assert MONEY_WORDS_EXEMPT == frozenset({
        ("listings", "asking_price_paise"), ("listings", "price_fixed_at")
    })


def test_all_twenty_two_adr_money_tokens_are_enforced():
    """QA-S0 F6, pinned. The guard enforced 15 of 22, and `amt`, `paid`,
    `payment` and `due` were caught by nothing at all."""
    assert len(W1B_MONEY_TOKENS) == 22
    for token in ("amt", "paid", "payment", "due", "rs_", "fee", "settled", "balance"):
        assert token in W1B_MONEY_TOKENS


@pytest.mark.parametrize(
    "table,column",
    [
        # QA-S0 F1 and F6/F7's attack lists, plus the review's findings.
        ("transfers", "cash_handed_over"),
        ("transfers", "consideration_paise"),
        ("transfers", "rupees_exchanged"),
        ("transfers", "value_x"),
        ("transfer_settlements", "amount_paise"),
        ("transfer_settlements", "cash_total"),
        ("settlements", "amount_minor"),
        ("settlement_records", "consideration"),
        ("handovers_cash", "cash_received"),
        ("receipts", "total_inr"),
        ("receipts", "amt"),
        ("receipts", "paid"),
        ("receipts", "due_inr"),
        ("handover_log", "payment_received"),
        ("listings", "cash_received"),
        ("listings", "settlement"),
        ("listings", "paise_count"),
        ("listings", "rupees_count"),
        ("listings", "amount_count"),
        ("listings", "handover_value_count"),
        ("users", "vpa_handle"),
        ("users", "pan_card"),
        ("legal_entities", "pincode"),
        ("users", "address"),
        ("ledger_entries", "amount"),
        ("age_check_pending", "date_of_birth"),
        ("offers", "offer_amount_paise"),
        ("listings", "previous_price_paise"),
        ("listings", "price_history_paise"),
        ("transfers", "delivery_charge_paise"),
        ("transfers", "amount_due"),
        ("transfers", "due_paise"),
    ],
)
def test_the_control_would_catch_each_known_attack(table, column):
    """The guard's own guard: every shape a careless developer actually
    produces must be caught by *some* layer.

    A unit test of the predicates, not of the live schema, so it cannot pass
    vacuously the way a loop over an empty schema can — the defect class this
    project has now named five times. If a future edit narrows a pattern, this
    fails even though no such column exists. It earned its place: it caught
    `rupees_exchanged` escaping every layer during the rework that was
    strengthening the control.
    """
    numeric_ish = column.endswith(
        ("_paise", "_minor", "_inr", "_total", "_amount", "amount", "_count")
    )
    caught = (
        # W1b — now every column, every type, two exempt columns
        ((table, column) not in MONEY_WORDS_EXEMPT and bool(money_tokens_in(column)))
        or bool(money_tokens_in(table))
        # W1
        or (numeric_ish and (table, column) != MONEY_COLUMN and not is_declared_non_monetary(column))
        # W3
        or any(
            matches(column, p, e)
            for p, e in FORBIDDEN_COLUMNS
            if not (p == "fee" and column in FEE_ALLOWED)
        )
        or any(first in column and second in column for first, second in FORBIDDEN_PAIRS)
        or any(p in column and CONDITIONAL_COLUMNS[p] != (table, column) for p in CONDITIONAL_COLUMNS)
        or any(matches(table, p, e) for p, e in FORBIDDEN_COLUMNS if p != "fee")
    )
    assert caught, f"no layer of the P14 control catches {table}.{column}"


def test_the_token_shape_exemptions_cannot_swallow_a_known_attack():
    """`MONEY_TOKEN_SHAPE_EXEMPTIONS` is an allowance, so it is checked rather
    than argued.

    `due_at`, `overdue` and `consume` are deadline, backlog and verb shapes, and
    the exemption exists because the bare tokens `due` and `sum` collide with
    every SLA clock the contracts mandate and with `consume_magic_link`, which
    API-CONTRACT §3 freezes. These assertions prove the exemption cannot be used
    to smuggle an amount through: a money name that happens to contain the shape
    is still caught.

    Takes no parameters on purpose — test-qa's conformance runner binds only
    no-argument assertions and a `table` one, and an assertion it cannot invoke
    makes every "escaped" verdict in its attack suite under-measured.
    """
    for shape in MONEY_TOKEN_SHAPE_EXEMPTIONS:
        for attack in (f"amount_{shape}", f"{shape}_paise", f"cash_{shape}", f"{shape}_total"):
            assert money_tokens_in(attack), f"the {shape!r} exemption swallowed {attack!r}"
    for attack in ("due_inr", "amount_due", "due_paise", "total_due", "sum_paise", "cash_sum"):
        assert money_tokens_in(attack), f"a shape exemption swallowed {attack!r}"


def test_the_contract_mandated_columns_are_not_false_positives():
    """The other half: columns the frozen contracts *require* must pass.

    REVIEW-S0 M2 was `listings.price_fixed_at` — mandated by ADR-003 §2.1 and
    DATA-MODEL §3 — failing the money assertion, so S2 would have met a red P14
    guard with the tempting fix being an edit to a founder-escalating file.
    Pinned here so no tightening re-breaks it. The `*_due_at` entries are the
    same risk one slice out, which is why the shape exemption exists.
    """
    mandated = [
        ("listings", "price_fixed_at", "DateTimeField"),
        ("listings", "asking_price_paise", "IntegerField"),
        ("jobs", "attempts", "SmallIntegerField"),
        ("jobs", "max_attempts", "SmallIntegerField"),
        ("idempotency_keys", "response_status", "SmallIntegerField"),
        ("listing_photos", "width", "IntegerField"),
        ("listing_photos", "height", "IntegerField"),
        ("listing_photos", "bytes", "IntegerField"),
        ("support_work_log", "seconds", "IntegerField"),
        ("search_result_opens", "position", "SmallIntegerField"),
        ("transfer_followups", "attempt_no", "SmallIntegerField"),
        ("transfers", "version", "IntegerField"),
        ("moderation_actions", "work_seconds", "IntegerField"),
        ("books", "publication_year", "SmallIntegerField"),
        ("transfers", "completed_at", "DateTimeField"),
        ("transfers", "seller_confirmed_at", "DateTimeField"),
        ("transfers", "buyer_confirmed_at", "DateTimeField"),
        # the SLA clocks, from S1 onward (DATA-MODEL §7, §10)
        ("listings", "purge_due_at", "DateTimeField"),
        ("transfers", "purge_due_at", "DateTimeField"),
        ("reports", "acknowledge_due_at", "DateTimeField"),
        ("reports", "act_due_at", "DateTimeField"),
        ("reports", "disposal_due_at", "DateTimeField"),
        ("data_subject_requests", "due_at", "DateTimeField"),
        ("disputes", "sla_due_at", "DateTimeField"),
        ("legal_notices", "act_due_at", "DateTimeField"),
        ("grievances", "disposal_due_at", "DateTimeField"),
    ]
    for table, column, internal_type in mandated:
        if internal_type in NUMERIC_TYPES:
            assert (table, column) == MONEY_COLUMN or is_declared_non_monetary(column), (
                f"{table}.{column} is mandated by a frozen contract and fails W1"
            )
        if (table, column) not in MONEY_WORDS_EXEMPT:
            assert not money_tokens_in(column), (
                f"{table}.{column} is mandated by a frozen contract and fails W1b "
                f"on {money_tokens_in(column)}"
            )
        for pattern, exact in FORBIDDEN_COLUMNS:
            if pattern == "fee" and column in FEE_ALLOWED:
                continue
            assert not matches(column, pattern, exact), (
                f"{table}.{column} is mandated and fails the deny-list on {pattern!r}"
            )
        for pattern, permitted in CONDITIONAL_COLUMNS.items():
            assert pattern not in column or permitted == (table, column), (
                f"{table}.{column} is mandated and fails the conditional pattern {pattern!r}"
            )
