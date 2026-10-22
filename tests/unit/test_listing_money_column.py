"""The money column, now that it exists. TASKS §2 S2's last two done-when items.

> - [ ] **`listings.paise_count` fails the P14 guard** and
> - [ ] `asking_price_paise` declared `real` fails it **via introspection even
>   though the model declares `IntegerField`** (R2's union).

Both are regressions against shapes that **passed every layer before this
slice**, which is why they are checkable items rather than notes.

**And this file carries coverage that moved, not only coverage that is new.**
test-qa's `tests/contract/test_p14.py` has a `float_money` attack that creates
`listings` with `asking_price_paise real`. That attack worked while `listings`
did not exist; **the day the real table arrived its `CREATE TABLE` started
failing with `DuplicateColumn`, so the single most important W1a case — the
one permitted money column declared as a float — stopped being measured at
exactly the moment the column became real.** That is QA's file to fix and is
reported to them. It is also not something to leave uncovered in the meantime,
so the same property is asserted here by a route that does not depend on the
table being absent: `ALTER COLUMN … TYPE real` inside a rolled-back
transaction.
"""

import pytest
from django.db import connection, transaction

from apps.core.p14 import (
    FLOAT_TYPES,
    MONEY_COLUMN,
    MONEY_COLUMN_INTEGER_TYPES,
    is_declared_non_monetary,
    money_tokens_in,
)
from tests.unit.test_forbidden_schema import all_type_reports, type_reports

pytestmark = pytest.mark.django_db


# --- R1: the shape that passed every layer before this slice --------------


def test_paise_count_is_rejected_by_the_schema_guard():
    """REVIEW-S0 R1's regression, as a predicate test.

    `listings.paise_count` is the shape the table-wide W1b exemption used to
    let through: `count` is a ratified non-monetary suffix, so **W1 passes
    it**, and while the exemption was the `listings` *table* rather than two
    *columns*, W1b passed it too. One table was allowed to hold money and
    therefore became the softest target in the schema.

    Asserted on the predicate rather than on the live schema, so it cannot
    pass vacuously the way a loop over a table that does not contain the
    column can — and so it stays true in S4 and S7.
    """
    assert is_declared_non_monetary("paise_count"), (
        "if `count` stopped being a ratified suffix this test would pass for "
        "the wrong reason; W1 must still accept the name"
    )
    hits = money_tokens_in("paise_count")
    assert hits == ["paise"], (
        "W1b is the layer that must catch `paise_count`, because W1 cannot: "
        f"got {hits}"
    )
    assert ("listings", "paise_count") not in {MONEY_COLUMN, ("listings", "price_fixed_at")}


def test_the_money_column_is_an_integer_on_every_route():
    """W1a, now that there is a column to ask about.

    The skip that guarded this in S0 — *"`listings` is created in S2"* — is
    spent. Both routes must agree, and both must say integer.
    """
    reports = type_reports(MONEY_COLUMN)
    assert reports, f"{MONEY_COLUMN[0]}.{MONEY_COLUMN[1]} is missing (ADR-003 §2.1)"
    assert len(reports) >= 2, (
        "only one route reported a type, so the union R2 requires is not being "
        f"formed: {reports}"
    )
    assert all(r in MONEY_COLUMN_INTEGER_TYPES for r in reports), reports


# --- R2: the union, and the attack the model declaration would hide -------


def test_a_real_declaration_fails_via_introspection_despite_the_model(engine):
    """**R2's union, demonstrated rather than described.**

    The model says `IntegerField`. The *database* is altered to `real`. If the
    guard let model meta override introspection — the precedence that is
    correct for **names** — the declaration would vouch for the column it is
    suspected of misrepresenting, and this attack would read green. The union
    is what stops that: the float check fails if **either** route reports a
    non-integer.

    Run inside a rolled-back transaction so the schema is restored however the
    assertion ends. SQLite cannot `ALTER COLUMN … TYPE` at all and does not
    enforce column types anyway (ENGINE-DIVERGENCE §2.8), so this **skips
    naming the engine and the slice** rather than passing.
    """
    if engine != "postgresql":
        pytest.skip(
            "NOT VERIFIABLE ON THIS ENGINE (vendor=sqlite, slice=S2): SQLite has "
            "no `ALTER COLUMN ... TYPE` and does not enforce declared column "
            "types, so a `real` declaration cannot be installed to be caught. "
            "The predicate half is asserted below on both engines."
        )
    from django.apps import apps as django_apps

    model = django_apps.get_model("listings", "Listing")
    declared = model._meta.get_field("asking_price_paise").get_internal_type()
    assert declared in MONEY_COLUMN_INTEGER_TYPES, declared

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE listings ALTER COLUMN asking_price_paise TYPE real"
            )
        reports = all_type_reports()[MONEY_COLUMN]
        assert any(r in FLOAT_TYPES for r in reports), (
            "the column is now `real` in the database and the guard's union "
            f"did not see it: {reports}. Model meta is vouching for a type it "
            "does not control, which is the inversion R2 corrected."
        )
        assert declared in reports, (
            "the union should still carry the model's own (wrong) answer too; "
            "if it does not, the union has collapsed to one route"
        )
        transaction.set_rollback(True)


def test_the_float_predicate_rejects_the_declaration_on_both_engines():
    """The predicate half of the same attack, with no DDL.

    Asserted on both engines so the property is not only true where it can be
    installed — the skip above is about *installing* a `real` column, not
    about whether the guard would catch one.
    """
    assert "FloatField" in FLOAT_TYPES
    assert "DecimalField" in FLOAT_TYPES
    assert not FLOAT_TYPES & MONEY_COLUMN_INTEGER_TYPES, (
        "a type counted as both a float and a permitted money type would make "
        "W1a unfalsifiable"
    )


# --- rule 12: the schema is the floor, detection lives above it -----------


def test_a_non_integer_price_is_refused_rather_than_rounded(seller, book):
    """**The test that matters** (`CLAUDE.md` rule 12).

    *"A database proving no float is stored does not prove none was sent —
    PostgreSQL rounds `300.75` to `301` silently, and a rounded money value is
    a wrong value that looks right."* So the assertion is never *"the column
    is of integer type"*; it is *"passing a non-integer is refused"*.

    `300.75` is the contract's own example. A seller who typed Rs 300.75 and
    got a listing asking Rs 301 would have a price they did not set, on a
    column that can never be corrected because it is immutable by trigger.
    """
    from apps.core.errors import ValidationFailed
    from apps.listings.services import create_listing

    with pytest.raises(ValidationFailed):
        create_listing(
            seller, book=book, asking_price_paise=300.75, condition="GOOD",
            annotation_level="NONE", damage_flags=[], no_damage=True,
            language="en", category="PRESCRIBED_TEXTBOOK",
        )


def test_a_boolean_price_is_refused_because_python_calls_it_an_integer(seller, book):
    """`isinstance(True, int)` is True, so `True` would store as 1 paisa.

    Not a hypothetical shape: a form field that posts a checkbox into the
    wrong name produces exactly this, and 1 paisa is a plausible-looking
    number that no CHECK would refuse.
    """
    from apps.core.errors import ValidationFailed
    from apps.listings.services import create_listing

    with pytest.raises(ValidationFailed):
        create_listing(
            seller, book=book, asking_price_paise=True, condition="GOOD",
            annotation_level="NONE", damage_flags=[], no_damage=True,
            language="en", category="PRESCRIBED_TEXTBOOK",
        )


def test_the_engine_would_have_rounded_it_which_is_why_the_refusal_is_above(engine):
    """**The measurement behind rule 12, run rather than quoted.**

    The claim is that PostgreSQL rounds a float into an integer column
    silently. That is a cross-engine claim about platform behaviour, so it is
    **VERIFIED HERE** rather than asserted: the probe writes `300.75` into an
    `integer` column and reads back what the server kept.

    On SQLite the same write stores `300.75` unchanged (ENGINE-DIVERGENCE
    §2.8) — a *different* wrong answer from the same input, which is why the
    refusal lives in the service layer and not in either engine.
    """
    with connection.cursor() as cursor:
        cursor.execute("CREATE TABLE _round_probe (id integer primary key, p integer not null)")
        cursor.execute("INSERT INTO _round_probe (id, p) VALUES (1, 300.75)")
        cursor.execute("SELECT p FROM _round_probe WHERE id = 1")
        stored = cursor.fetchone()[0]

    if engine == "postgresql":
        assert stored == 301, (
            f"PostgreSQL stored {stored!r}; rule 12's premise is that it rounds "
            "300.75 to 301. If this changed, the premise is wrong and the "
            "explanation in the service layer should be corrected, not the test."
        )
    else:
        assert stored == 300.75, (
            f"SQLite stored {stored!r}; ENGINE-DIVERGENCE §2.8 measured that it "
            "keeps the float in an integer column. Either way the value is not "
            "the one that was sent, which is the point."
        )
