"""Every shape-B constant equals the bound in a real CHECK. THREAT-MODEL §6.

**This file is half of one control, and the other half is in
`test_forbidden_source.py`.** ADR-003 §2.3's ratified exemption (cto,
2026-10-22) lets W1c's source guard skip an UPPER_SNAKE money-shaped constant,
on the invariant that *a money-shaped name is permitted only if it cannot
carry a per-transaction value* — there is one of a bound, not one per row.

**Shape A has a second layer and shape B does not.** A lookup can only
reference the permitted column, and W1's whitelist guarantees that column is
the only money column — to write `settled_price__gte` you first need a
`settled_price` column, and the whitelist kills it. **A constant is not a
column, so the whitelist does not reach it at all.** Under `CLAUDE.md` rule 12
an exemption with no other catcher is a widening, not a clarification, so cto
refused to grant shape B unpinned. **This file is the missing layer.**

**It is also rule 11.** The bound exists twice — once as
`MAX_ASKING_PRICE_PAISE` and once inside
`listings_asking_price_range_chk` — and nothing made them the same number.
Pinning them makes one of them the copy rather than a second definition free
to drift, which is the ordinary way a guard and the thing it guards come
apart.

**The name that proves this is load-bearing rather than ceremonial, measured
by cto before ratifying: `MAX_OFFER_PAISE` passes the shape test.** It is
UPPER_SNAKE, it is money-shaped, and the shape rules alone would have admitted
exactly the S4 case the ratification exists to forbid. It fails *here*,
because shape B needs a CHECK to pin to and there is no offer-amount column to
have one. cto's sentence for why that is the right outcome is worth keeping
next to the assertion: ***a bound on a quantity we refuse to store is a
quantity we are about to start storing.***

So the test below is deliberately not "the two known constants are correct".
It **discovers** every shape-B name in `apps/**` and requires each one to
resolve to a CHECK bound — so a constant added in S4, S5 or S7 is caught by
the control rather than by a reviewer remembering this file exists.
"""

import ast
import pathlib

import pytest
from django.apps import apps as django_apps
from django.db.models import CheckConstraint, Q

from apps.core.p14 import money_tokens_in, source_shape_exempt

REPO = pathlib.Path(__file__).resolve().parents[2]
APPS = REPO / "apps"

#: `apps/core/p14.py` is the specification of record and names the shapes in
#: prose; it declares no bound. Excluded by name so the exclusion cannot widen,
#: exactly as `test_forbidden_source.py` excludes it.
EXCLUDED_FILES = {"apps/core/p14.py"}


def shape_b_constants():
    """`[(file, name, value)]` — every module-level money-shaped UPPER_SNAKE
    constant bound to a literal int anywhere in `apps/**`.

    **Module level and a literal int, both required**, because that is the
    shape ADR-003 ratified. A constant computed at import time
    (`MAX_PRICE_PAISE = _read_config()`) is not a literal, so it does not
    qualify for the exemption at all and W1c refuses it there — which is the
    correct place for that refusal, not here.
    """
    found = []
    for path in sorted(APPS.rglob("*.py")):
        rel = path.relative_to(REPO).as_posix()
        if rel in EXCLUDED_FILES or "/migrations/" in rel:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                if source_shape_exempt(target.id) != "B":
                    continue
                if not money_tokens_in(target.id.lower()):
                    continue
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int):
                    found.append((rel, target.id, node.value.value))
                else:
                    found.append((rel, target.id, None))
    return found


def check_constraint_bounds():
    """`{(table, column, lookup): value}` from every model's CHECK constraints.

    Read from Django model meta rather than from `information_schema` or
    `PRAGMA`, which is ADR-003 §2.3 W4's rule and the reason this runs
    identically on both engines rather than skipping on one.
    """
    bounds = {}
    for model in django_apps.get_models():
        table = model._meta.db_table.lower()
        for constraint in model._meta.constraints:
            if not isinstance(constraint, CheckConstraint):
                continue
            condition = getattr(constraint, "condition", None)
            if condition is None:  # pragma: no cover - Django <5.1 spelling
                condition = getattr(constraint, "check", None)
            for lookup, value in _q_leaves(condition):
                if isinstance(value, bool) or not isinstance(value, int):
                    continue
                parts = lookup.split("__")
                column = parts[0]
                suffix = parts[1] if len(parts) > 1 else "exact"
                bounds[(table, column, suffix)] = value
    assert bounds, (
        "no integer CHECK bounds found in any model — this test would pass "
        "vacuously for every constant"
    )
    return bounds


def _q_leaves(node):
    """Every `(lookup, value)` pair inside a `Q`, however deeply combined."""
    if node is None:
        return
    if isinstance(node, Q):
        for child in node.children:
            yield from _q_leaves(child)
        return
    if isinstance(node, tuple) and len(node) == 2:
        yield node


# --- the control -----------------------------------------------------------


def test_the_scan_finds_the_shape_b_constants_it_claims_to():
    """`CLAUDE.md` rule 10. A walk that found nothing would pass everything,
    and this is the file whose whole job is to be the second layer."""
    found = shape_b_constants()
    assert found, (
        "no shape-B constants found in apps/**. Either the exemption is unused "
        "— in which case it should be withdrawn rather than left standing — or "
        "the AST walk has stopped seeing module-level assignments."
    )
    assert any(name == "MAX_ASKING_PRICE_PAISE" for _f, name, _v in found), (
        "the one constant the exemption was ratified for is not being found, "
        "so this control is measuring nothing"
    )


@pytest.mark.parametrize("entry", shape_b_constants(), ids=lambda e: f"{e[1]}")
def test_every_exempted_bound_equals_a_real_check_constraint(entry):
    """ADR-003 §2.3 shape B's condition, per constant.

    A constant is exempt from W1c **only while** it is the same number as a
    bound the database actually enforces. `TYPICAL_SALE_PRICE_PAISE = 30000`
    matches no CHECK and fails here; so does `MAX_OFFER_PAISE`, because there
    is no offer-amount column for a CHECK to be on.
    """
    rel, name, value = entry
    assert value is not None, (
        f"{rel}: {name} is money-shaped and UPPER_SNAKE, so W1c exempts it as a "
        "shape-B bound — but it is not bound to a literal int, so it cannot be "
        "pinned to a CHECK. ADR-003 §2.3 grants shape B only for a literal "
        "bound; give it a literal value or rename it."
    )
    bounds = check_constraint_bounds()
    matches = sorted(
        f"{table}.{column}__{suffix}"
        for (table, column, suffix), bound in bounds.items()
        if bound == value and money_tokens_in(column)
    )
    assert matches, (
        f"{rel}: {name} = {value} is exempted from the P14 source guard as a "
        "shape-B bound (ADR-003 §2.3, ratified 2026-10-22), and the exemption "
        "is conditional on it equalling the bound in a real CHECK constraint "
        "on a money column. No such CHECK exists.\n\n"
        "A constant is not a column, so W1's whitelist cannot reach it — this "
        "pin is the only other layer, which is why the exemption is refused "
        "without it. If this is a bound on a quantity we do not store, that is "
        "the finding: a bound on a quantity we refuse to store is a quantity "
        "we are about to start storing.\n"
        f"Integer bounds currently enforced on money columns: "
        + str(sorted(
            (f"{t}.{c}__{s}", b) for (t, c, s), b in bounds.items() if money_tokens_in(c)
        ))
    )


def test_the_pinned_bound_is_the_one_the_contract_names():
    """ADR-003 §2.1 and DATA-MODEL §3 both write the ceiling as `10000000`.

    Pinned against the **contract's literal number** as well as against the
    CHECK, so the constant and the constraint cannot drift *together* — which
    is the one failure the pin above cannot see.
    """
    from apps.listings.models import MAX_ASKING_PRICE_PAISE

    assert MAX_ASKING_PRICE_PAISE == 10_000_000


# --- the pin's own guard ---------------------------------------------------


def test_the_pin_rejects_a_bound_with_no_constraint_behind_it():
    """The negative control, as a unit test of the predicate rather than by
    planting a constant in `apps/**`.

    `MAX_OFFER_PAISE` is cto's measured case: it **passes** the shape test, so
    the shape rules alone would have admitted it. The pin is what refuses it,
    and the refusal is a property of there being no offer-amount column — not
    of anybody having listed the name.
    """
    bounds = check_constraint_bounds()
    money_bounds = {b for (_t, c, _s), b in bounds.items() if money_tokens_in(c)}

    assert source_shape_exempt("MAX_OFFER_PAISE") == "B", (
        "if the shape test ever stops matching this name the pin is no longer "
        "the thing refusing it, and this test is no longer measuring the gap"
    )
    # 45000 is an offer amount nobody enforces, which is the whole point.
    assert 45_000 not in money_bounds, (
        "a CHECK now enforces an offer-shaped bound; P14 says no offer amount "
        "is stored, so this is a finding and not a test to adjust"
    )


def test_the_check_bound_reader_sees_a_combined_q():
    """The reader's own test: the real constraint is two leaves under one `Q`,
    and a walk that only saw a single-leaf `Q` would find no bound and would
    then fail *every* constant for the wrong reason."""
    combined = Q(("asking_price_paise__gte", 0)) & Q(("asking_price_paise__lte", 10))
    assert sorted(_q_leaves(combined)) == [
        ("asking_price_paise__gte", 0), ("asking_price_paise__lte", 10)
    ]
