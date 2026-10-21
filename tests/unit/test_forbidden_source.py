"""W1c — the source-level half of P14. ADR-003 §2.3 W1c.

It landed in S0 rather than S1 (where `TASKS.md` assigns it) because it was
cheap once `apps/core/p14.py` existed, and because W1c is the only control
ADR-003 §2.3 W5 offers for the `@property` residual — a named control with
no code is a specification, and two of W5's three controls already were.

**Filename note.** `TASKS.md` S1 calls this `test_no_money_shaped_source.py`.
It is not renamed, because test-qa's `tests/contract/test_p14.py` already
imports `tests.unit.test_forbidden_source` by name in three places and those
tests are green; renaming to match a filename would turn three of QA's
passing tests red for nothing. Flagged to cto as a one-line TASKS
correction (ENGINE-DIVERGENCE §9 item 13) rather than fixed in the
direction that breaks working code.

*"CI additionally greps `apps/**` and asserts that no model field, `@property`,
`@cached_property`, serialiser key or API response key is money-shaped unless
it is `asking_price_paise`."*

**Why a source grep exists beside a schema one.** QA demonstrated it rather than
argued it: a Python `@property settled_price_paise` added to a live model changes
**zero** columns, so every assertion in `test_forbidden_schema.py` passes while
a settled price is computable and renderable. ADR-003 §2.3 W5 accepts that
residual *and names W1c as its compensating control* — so until this file
existed, the residual had no control at all (QA-S0 F5).

The tokens come from `apps/core/p14.py`, like every other P14 list (W1d). The
pattern — grepping source in CI for a rule a type system cannot express — is the
one S1's copy-enforcement tests use for the forbidden trust words.

# ponytail: regex over source text, not an AST walk. Ceiling: it sees
# definitions, not arbitrary expressions, so `setattr(obj, "settled_" + "price",
# x)` or a name assembled at runtime gets through. Upgrade path: `ast.parse` and
# walk FunctionDef/AnnAssign/Assign/Dict nodes — maybe 30 more lines, worth it
# the first time someone builds a serialiser layer. Today `apps/**` has no
# dynamic attribute construction at all, and a rule nobody can read is worse
# than a rule with a stated ceiling.
"""

import pathlib
import re

import pytest

from apps.core.p14 import (
    FORBIDDEN_RESPONSE_KEYS,
    MONEY_COLUMN,
    MONEY_WORDS_EXEMPT,
    money_tokens_in,
)

APPS = pathlib.Path(__file__).resolve().parents[2] / "apps"

#: The one permitted money name, at the boundary as well as in the table, plus
#: the second column ADR-003 §2.3 W1b names.
PERMITTED = {column for _table, column in MONEY_WORDS_EXEMPT} | {MONEY_COLUMN[1]}

#: `apps/core/p14.py` *is* the token list, so every token appears in it by
#: definition. It is the specification of record in code and is excluded by
#: name rather than by a pattern, so the exclusion cannot widen.
EXCLUDED_FILES = {"apps/core/p14.py"}

#: What counts as a declaration. Each group captures one identifier.
DECLARATIONS = (
    # def foo(...)  — covers @property and @cached_property, which are defs
    re.compile(r"^\s*def\s+(\w+)\s*\(", re.M),
    # foo = models.IntegerField(...)  — a model field
    re.compile(r"^\s*(\w+)\s*=\s*models\.\w+\(", re.M),
    # "foo": ...  — a serialiser key, a response body key, an audit payload key
    re.compile(r"""["'](\w+)["']\s*:""", re.M),
    # class Foo: / @property\n def foo
    re.compile(r"^\s*(\w+)\s*:\s*\w+\s*=", re.M),
)


def source_files():
    files = []
    for path in sorted(APPS.rglob("*.py")):
        rel = path.relative_to(APPS.parent).as_posix()
        if rel in EXCLUDED_FILES or "/migrations/" in rel:
            continue
        files.append((rel, path.read_text(encoding="utf-8")))
    assert files, "no source files found under apps/** — this test would pass vacuously"
    return files


def declared_identifiers():
    """[(file, identifier)] for every declaration the regexes can see."""
    found = []
    for rel, text in source_files():
        for pattern in DECLARATIONS:
            for match in pattern.finditer(text):
                found.append((rel, match.group(1)))
    assert found, "no identifiers found in apps/** — this test would pass vacuously"
    return found


def test_no_declared_identifier_in_apps_is_money_shaped():
    """The rule itself. One failure names the file and the identifier."""
    offenders = []
    for rel, name in declared_identifiers():
        lowered = name.lower()
        if lowered in PERMITTED:
            continue
        hits = money_tokens_in(lowered)
        if hits:
            offenders.append(f"{rel}: {name} (tokens {hits})")
    assert offenders == [], (
        "ADR-003 §2.3 W1c: these declarations in apps/** are money-shaped, and "
        "only `asking_price_paise` may be. A `@property settled_price` is "
        "invisible to every schema assertion, which is why this check exists.\n"
        + "\n".join(sorted(set(offenders)))
    )


def test_no_forbidden_response_key_is_declared_in_apps():
    """ADR-003 §2.3: *"no response key may be named `price`, `amount`, `total`
    or `value`"* — the money field is `asking_price_paise` at the boundary as
    well as in the table, so a template cannot render "Price:" from a field
    that invited it."""
    offenders = [
        f"{rel}: {name}"
        for rel, name in declared_identifiers()
        if name.lower() in FORBIDDEN_RESPONSE_KEYS and name.lower() not in PERMITTED
    ]
    assert offenders == [], (
        "ADR-003 §2.3: forbidden response key name(s) declared in apps/**:\n"
        + "\n".join(sorted(set(offenders)))
    )


# --- the check's own guard -------------------------------------------------


@pytest.mark.parametrize(
    "snippet,identifier",
    [
        ("    @property\n    def settled_price_paise(self):\n        return 1\n", "settled_price_paise"),
        ("    def cash_received(self):\n        pass\n", "cash_received"),
        ("    amount_due = models.IntegerField()\n", "amount_due"),
        ('    return {"total": 1}\n', "total"),
        ('    payload = {"paid_amount_paise": 30000}\n', "paid_amount_paise"),
        ("    settlement_total: int = 0\n", "settlement_total"),
    ],
)
def test_the_grep_actually_sees_each_declaration_shape(snippet, identifier):
    """QA's demonstration, as a test of the detector.

    A grep that silently matches nothing is the defect class this project has
    named repeatedly, so each declaration shape W1c names is proved visible to
    at least one regex, and proved money-shaped.
    """
    seen = {m.group(1) for pattern in DECLARATIONS for m in pattern.finditer(snippet)}
    assert identifier in seen, f"no DECLARATIONS regex sees {identifier!r} in {snippet!r}"
    assert money_tokens_in(identifier), f"{identifier!r} is not recognised as money-shaped"


def test_the_permitted_set_is_exactly_the_two_adr_names():
    assert PERMITTED == {"asking_price_paise", "price_fixed_at"}
