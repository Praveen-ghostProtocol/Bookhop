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

**QA-S0 F13 — the regexes saw three declaration shapes and missed three.**
Measured: a property *assigned* rather than decorated
(`settled_price = property(_get)`), a bare class or module constant
(`SETTLED_PRICE_PAISE = 30000`) and an annotation with no assignment
(`settled_price: int`) were all invisible. QA's recommendation was two more
regexes and an explicit *"do not use a blanket `^\\s*(\\w+)\\s*=`"*, which is
right about the blanket — it would match every local variable in the codebase
and then be deleted the first time it cost someone an afternoon.

**So the mechanism changed instead of the list growing** (`CLAUDE.md` rule 15:
ask the property, do not enumerate the cases). `ast.parse` is asked *"does this
module bind this name?"*, which is a question with an answer rather than a
pattern with coverage. It sees all six shapes and every shape nobody has
thought of yet, it cannot silently miss one through a regex that stopped
matching, and it is shorter than six regexes.

**What narrowed, stated plainly, because `CLAUDE.md` rule 11 exists for exactly
the case where a control was made "better" and lost coverage nobody counted.**
The AST walk is a strict superset of the six regexes on every declaration shape
they saw, with two exceptions, both deliberate and both publishing nothing:

1. **A bare assignment inside a function body is not collected.** The regexes
   did not collect one either *except* `x = models.Field()`, which they matched
   at any indent — so `def f(): paid_amount = models.IntegerField()` was seen
   before and is not now. A model field is a class attribute by definition, so
   that shape is not a model field; it is a local. The first version of this
   rewrite *did* collect locals and parameters, and it immediately reddened on
   `value`, `values` and `due` — three ordinary Python names in
   `apps/core/{services,models,jobs}.py`. The cheap fix would have been adding
   `value` and `due` to `PERMITTED`, and `PERMITTED` is checked against **column
   names** too, so that fix would have exempted the name on a model. The
   collision is not resolved; it is not created.
2. **Identifier-looking text inside a string or a docstring is not collected.**
   The `["'](\\w+)["']\\s*:` regex matched `"total":` wherever it appeared,
   including in prose. The AST sees a dict literal's keys instead. This removes
   false positives only — there is no `eval` anywhere in `apps/**`.

**Everything else is wider**, not narrower: annotations with no assignment, a
property assigned rather than decorated, bare constants, attribute assignments
(`self.amount = …`), keyword arguments, non-identifier dict keys
(`"paid-amount"`), and annotations too complex for `\\w+`
(`x: dict[str, int] = {}`). `CLAUDE.md` rule 14's question — which other layer
catches an excluded thing — is answered by `test_forbidden_schema.py`: anything
reaching a column is caught there by model meta **and** by
`connection.introspection`, independently of this file.

# ponytail: an AST walk over binding nodes, not a type checker. Ceiling: it
# sees *bindings*, not arbitrary expressions, so a name assembled at runtime
# (`setattr(obj, "settled_" + "price", x)`) still gets through — unchanged from
# the regex version, and `apps/**` contains no dynamic attribute construction at
# all, which this file asserts rather than assumes. Upgrade path: none wanted;
# the residual is W5's and is bounded by the frozen column lists.
"""

import ast
import pathlib

import pytest

from apps.core.p14 import (
    FORBIDDEN_RESPONSE_KEYS,
    MONEY_COLUMN,
    MONEY_WORDS_EXEMPT,
    SOURCE_GUARD_SHAPE_EXEMPTIONS,
    money_tokens_in,
    source_shape_exempt,
)

APPS = pathlib.Path(__file__).resolve().parents[2] / "apps"

#: The one permitted money name, at the boundary as well as in the table, plus
#: the second column ADR-003 §2.3 W1b names.
PERMITTED = {column for _table, column in MONEY_WORDS_EXEMPT} | {MONEY_COLUMN[1]}

#: `apps/core/p14.py` *is* the token list, so every token appears in it by
#: definition. It is the specification of record in code and is excluded by
#: name rather than by a pattern, so the exclusion cannot widen.
EXCLUDED_FILES = {"apps/core/p14.py"}


def source_files():
    files = []
    for path in sorted(APPS.rglob("*.py")):
        rel = path.relative_to(APPS.parent).as_posix()
        if rel in EXCLUDED_FILES or "/migrations/" in rel:
            continue
        files.append((rel, path.read_text(encoding="utf-8")))
    assert files, "no source files found under apps/** — this test would pass vacuously"
    return files


def bound_names(source):
    """Every **externally visible** name this module or fragment declares.

    The nine shapes W1c and QA-S0 F13 name, and the node that catches each:

      | shape                                    | node               |
      | `def f()` / `@property def f()`           | FunctionDef        |
      | `class F`                                 | ClassDef           |
      | `f = models.IntegerField()`               | module/class Assign|
      | `f = property(_get)`   (F13, missed)      | module/class Assign|
      | `F = 30000`            (F13, missed)      | module/class Assign|
      | `f: int` with no value (F13, missed)      | AnnAssign          |
      | `{"f": ...}` serialiser / payload key     | Dict const key     |
      | `self.f = ...` / `obj.f = ...`            | Attribute target   |
      | `fn(f=...)` keyword                       | keyword.arg        |

    **A bare assignment inside a function body is not collected, and neither is
    a parameter.** That boundary is `CLAUDE.md` rule 13 applied before the
    collision rather than after it: `for key, value in payload.items()` and
    `def _canonical(value)` are ordinary Python, `value` is a W1b token and a
    forbidden response key, and a control that reddened on them would be
    switched off within a day — or, worse, fixed by adding `value` to
    `PERMITTED`, which would then exempt the name **on a model column too**.
    W1c's subject is what `apps/**` *publishes* — a field, a property, a
    serialiser key, a response key — and a local variable publishes nothing. The
    schema guard is the second layer underneath (`CLAUDE.md` rule 14): any of
    these that reaches a column is caught by `test_forbidden_schema.py`
    independently.

    `self.x = ...` and `obj.x = ...` *are* collected wherever they appear,
    because a money-shaped attribute set on a model instance is the `@property`
    residual by another route, and an attribute is published.

    **An annotated name is collected wherever it appears, including inside a
    function body.** An annotation is a declaration by Python's own word, the
    regex this replaced matched one at any indent, and keeping it at any indent
    is what makes this function a strict superset of that regex on every shape
    it saw. The two shapes it is *not* a superset on are named in the module
    docstring under "what narrowed".

    **Imports are excluded**: `from .p14 import money_tokens_in` binds a name
    this control's own predicate owns, and treating a re-export as a declaration
    would turn the guard red on its own helpers.

    Accepts a whole module or a bare fragment, because
    `tests/contract/test_p14.py` feeds it indented class-body snippets derived
    from ADR-003 rather than whole files. A fragment is dedented first; one that
    is still not a module on its own (`return {...}`) is wrapped, and in that
    case only the scope-independent collectors apply — which is enough, because
    the only such shape is a dict literal.
    """
    names = set()
    _collect(_parse_fragment(source), names, published=True)
    return names


def _parse_fragment(source):
    """`ast.parse` for a whole module, a dedented fragment, or a statement."""
    import textwrap

    for candidate in (source, textwrap.dedent(source)):
        try:
            return ast.parse(candidate)
        except SyntaxError:
            continue
    wrapped = "def _fragment():\n" + textwrap.indent(textwrap.dedent(source), "    ")
    return ast.parse(wrapped)


def _collect(node, names, published):
    """Walk `node`'s children, tracking whether a bare binding here is published.

    `published` is True in a module body and a class body, False inside a
    function body. It is the only state the walk needs, which is why this is a
    recursion and not a scope table.
    """
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(child.name)
            _collect(child, names, published=False)
            continue
        if isinstance(child, ast.ClassDef):
            names.add(child.name)
            _collect(child, names, published=True)
            continue
        if isinstance(child, (ast.Assign, ast.AugAssign)):
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            for target in targets:
                names.update(_target_names(target, published))
        elif isinstance(child, ast.AnnAssign):
            # `published=True` regardless of scope: an annotation is a
            # declaration, and the regex this replaced matched one at any
            # indent. See `bound_names`.
            names.update(_target_names(child.target, True))
        elif isinstance(child, ast.Dict):
            for key in child.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    names.add(key.value)
        elif isinstance(child, ast.keyword) and child.arg:
            names.add(child.arg)
        _collect(child, names, published)


def _target_names(target, published):
    if isinstance(target, ast.Name):
        return {target.id} if published else set()
    if isinstance(target, ast.Attribute):
        return {target.attr}
    if isinstance(target, (ast.Tuple, ast.List)):
        found = set()
        for element in target.elts:
            found |= _target_names(element, published)
        return found
    return set()


class _AstDeclarationScanner:
    """The detector, behind the iterator interface `DECLARATIONS` has always had.

    **This is a compatibility surface, not a second mechanism.** There is one
    detector — `bound_names` — and this wraps it so
    `tests/contract/test_p14.py`'s `_sees()` helper, which does
    `for pattern in module.DECLARATIONS: pattern.finditer(snippet)`, keeps
    working across the change from six regexes to one AST walk.

    It exists because of what breaking the interface actually cost: **seven of
    QA's assertions went red, and six of them were the ADR's own contract** —
    *"W1c must see a `@property`, a `@cached_property`, a method, a model field,
    a serialiser key and an annotated attribute"*. Those six are what the
    architecture requires; turning them red to rename an internal was the wrong
    direction, and `CLAUDE.md` rule 13's order of resort says so: **rename ours,
    do not break theirs.** The three that remain red are QA's **finding** tests
    for F13, and they are red because the finding is fixed — the same shape as
    F11's and F17's finding tests this slice.

    Flagged to cto and test-qa as a one-line improvement in QA's tree, not fixed
    there: `_sees()` reaching into a private regex list *is* the coupling that
    broke, and the behavioural call is `module.bound_names(snippet)`. Until QA
    makes that change this adapter is what keeps the contract assertions honest,
    and it is deliberately the thinnest thing that can.
    """

    def finditer(self, snippet):
        for name in sorted(bound_names(snippet)):
            yield _Found(name)


class _Found:
    """A `re.Match`-shaped result: `.group(1)` is the identifier."""

    def __init__(self, name):
        self._name = name

    def group(self, index):
        if index != 1:
            raise IndexError("no such group")
        return self._name


#: Kept as the detector's public name. One entry, because there is one
#: mechanism; the tuple shape is the interface QA's contract test reads.
DECLARATIONS = (_AstDeclarationScanner(),)


def declared_identifiers():
    """[(file, identifier)] for every name `apps/**` binds."""
    found = []
    for rel, text in source_files():
        for name in sorted(bound_names(text)):
            found.append((rel, name))
    assert found, "no identifiers found in apps/** — this test would pass vacuously"
    return found


def test_no_declared_identifier_in_apps_is_money_shaped():
    """The rule itself. One failure names the file and the identifier.

    **Two ratified shapes are skipped here and nowhere else** (ADR-003 §2.3's
    `SOURCE_GUARD_SHAPE_EXEMPTIONS`, cto 2026-10-22): an ORM lookup that ends
    at the permitted column, and an UPPER_SNAKE bound. The invariant is that
    **a money-shaped name is permitted only if it cannot carry a
    per-transaction value**, which is exactly what P14 protects.

    **This predicate alone is a widening, and it is not granted alone.** Shape
    A's second layer is W1's whitelist — you need a `settled_price` column
    before you can write `settled_price__gte`, and the whitelist kills the
    column. Shape B has no such layer, because a constant is not a column, so
    `tests/unit/test_exempted_bound_is_pinned.py` is the layer: every shape-B
    name must equal the bound in a real CHECK. Measured by cto before
    ratifying — `MAX_OFFER_PAISE` passes the shape test and is caught only by
    the pin.
    """
    offenders = []
    for rel, name in declared_identifiers():
        lowered = name.lower()
        if lowered in PERMITTED:
            continue
        hits = money_tokens_in(lowered)
        if hits and source_shape_exempt(name):
            continue
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
    "snippet,identifier,why",
    [
        ("@property\ndef settled_price_paise(self):\n    return 1\n",
         "settled_price_paise", "a decorated property — W1c's named shape"),
        ("def cash_received(self):\n    pass\n", "cash_received", "a plain method"),
        ("amount_due = models.IntegerField()\n", "amount_due", "a model field"),
        ('x = {"total": 1}\n', "total", "a serialiser / response key"),
        ('payload = {"paid_amount_paise": 30000}\n', "paid_amount_paise", "a jsonb payload key"),
        ("settlement_total: int = 0\n", "settlement_total", "an annotated assignment"),
        # --- the three QA-S0 F13 shapes the regex version could not see ---
        ("settled_price = property(_get_it)\n", "settled_price",
         "F13: a property ASSIGNED rather than decorated"),
        ("SETTLED_PRICE_PAISE = 30000\n", "SETTLED_PRICE_PAISE",
         "F13: a bare class or module constant"),
        ("class X:\n    cash_total: int\n", "cash_total",
         "F13: an annotation with NO assignment"),
        # and three more the mechanism gets for free, named so the gain is
        # visible rather than incidental
        ("def f(self):\n    self.amount_settled = 1\n", "amount_settled",
         "an attribute set on an instance — the @property residual by another route"),
        ("record(total_paid=1)\n", "total_paid", "a keyword argument"),
    ],
)
def test_the_detector_actually_sees_each_declaration_shape(snippet, identifier, why):
    """QA's demonstration, as a test of the detector.

    A grep that silently matches nothing is the defect class this project has
    named repeatedly (`CLAUDE.md` rule 12), so each shape is proved **visible**
    and proved **money-shaped** — the two halves that together make a hit.
    """
    assert identifier in bound_names(snippet), f"the AST walk misses {why}: {snippet!r}"
    assert money_tokens_in(identifier), f"{identifier!r} is not recognised as money-shaped"


@pytest.mark.parametrize(
    "snippet,name,why",
    [
        ("def f(payload):\n    for key, value in payload.items():\n        print(key, value)\n",
         "value", "a loop variable — `value` is a W1b token and ordinary Python"),
        ("def _canonical(value):\n    return value\n",
         "value", "a parameter — this exact signature is in apps/core/services.py"),
        ("def f():\n    due = Job.objects.all()\n    return due\n",
         "due", "a local holding a queryset — this exact line is in apps/core/jobs.py"),
    ],
)
def test_a_function_local_is_not_a_declaration(snippet, name, why):
    """**The scope boundary, asserted rather than assumed** — `CLAUDE.md` rule 13.

    Each of these three is real code in `apps/**` today and each contains a W1b
    money token. A control that reddened on them would be resolved either by
    switching it off or by adding `value` and `due` to `PERMITTED` — and
    `PERMITTED` is checked against **column names** as well, so that fix would
    exempt the name on a model. The collision is not resolved; it is not
    created.

    `CLAUDE.md` rule 14 asks which other layer still catches the excluded thing:
    `test_forbidden_schema.py` does, for anything that reaches a column, by
    model meta and by `connection.introspection` independently — see the test
    below, which proves it rather than claiming it.
    """
    assert money_tokens_in(name), f"{name!r} is not money-shaped, so this case proves nothing"
    assert name not in bound_names(snippet), why


def test_the_excluded_shape_is_caught_by_the_schema_layer_instead():
    """`CLAUDE.md` rule 14: an exemption is affordable only when another layer
    independently rejects the same thing. The excluded shape is a *local
    binding*; the thing that would matter is one reaching a column, so this
    asserts the schema guard's predicate rejects it by name.

    Not a claim about `test_forbidden_schema.py`'s own passing state — it
    asserts the shared predicate both layers call, which is the one definition
    (`CLAUDE.md` rule 10).
    """
    for name in ("value", "due_inr", "total"):
        assert money_tokens_in(name) or name in FORBIDDEN_RESPONSE_KEYS, (
            f"{name!r} would be invisible to the schema layer too, so excluding "
            "it from the source layer is a widening and not a scope decision"
        )


def test_the_detector_ignores_an_import_rather_than_flagging_its_own_helpers():
    """`CLAUDE.md` rule 13, as a test. `money_tokens_in` is money-shaped by name
    and is this control's own predicate; a detector that counted an import as a
    declaration would be red on every file that uses it, and the cheap fix under
    pressure is widening PERMITTED — which would then exempt the name
    everywhere, including on a model."""
    assert "money_tokens_in" not in bound_names(
        "from apps.core.p14 import money_tokens_in\nimport apps.core.p14 as price_rules\n"
    )


def test_apps_contains_no_dynamic_attribute_construction():
    """The stated ceiling, asserted instead of assumed.

    The `# ponytail` note says a name assembled at runtime gets through and that
    `apps/**` has none. That second half is a claim about the repository, so it
    is a test: if a `setattr` with a non-literal name ever lands, the ceiling
    stops being theoretical and this fails on the commit that makes it real.
    """
    offenders = []
    for rel, text in source_files():
        for node in ast.walk(ast.parse(text)):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in ("setattr", "delattr")
                and len(node.args) >= 2
                and not (isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str))
            ):
                offenders.append(f"{rel}:{node.lineno} {node.func.id}() with a non-literal name")
    assert offenders == [], (
        "ADR-003 §2.3 W1c's stated ceiling is now reachable: a name is built at "
        "runtime, so the source control cannot see it. Either use a literal name "
        "or escalate the residual to cto.\n" + "\n".join(offenders)
    )


def test_the_permitted_set_is_exactly_the_two_adr_names():
    assert PERMITTED == {"asking_price_paise", "price_fixed_at"}


# --- the ratified shape exemption, and what it must still refuse -----------


@pytest.mark.parametrize(
    "name,shape,why",
    [
        ("asking_price_paise__gte", "A", "the S2 collision: a CHECK's lower bound"),
        ("asking_price_paise__lte", "A", "the S2 collision: a CHECK's upper bound"),
        ("asking_price_paise__isnull", "A", "a registered lookup"),
        ("listing__asking_price_paise__lte", "A",
         "S4's traversal — the relation prefix is needed and is confirmed here"),
        ("transfer__listing__asking_price_paise", "A", "two relations, ending at the column"),
        ("MAX_ASKING_PRICE_PAISE", "B", "the bound, whose honest name carries both tokens"),
    ],
)
def test_the_ratified_shapes_are_recognised(name, shape, why):
    """Both halves of a hit, so neither can pass vacuously: the name **is**
    money-shaped, and it **is** matched by the ratified shape."""
    assert money_tokens_in(name.lower()), f"{name!r} is not money-shaped, so this proves nothing"
    assert source_shape_exempt(name) == shape, why


@pytest.mark.parametrize(
    "name,why",
    [
        ("settled_price_paise", "QA's @property — the case W1c exists for, invisible to the schema"),
        ("settled_price", "a property assigned rather than decorated"),
        ("offered_price", "an offer amount; an accepted offer amount IS a settled consideration"),
        ("offer_amount", "the same, under the other name"),
        ("asking_price_paise__total", "`total` is NOT a lookup suffix — the discriminating case"),
        ("cash_received", "a plain method"),
        ("amount_due", "a model field"),
        ("paid_amount_paise", "a jsonb payload key"),
        ("asking_price_paise_settled", "a suffix that is not a lookup and not `__`-separated"),
        ("sale_price_paise__gte", "a lookup on a column that is not the permitted one"),
    ],
)
def test_the_exemption_cannot_swallow_a_forbidden_shape(name, why):
    """**The half that makes the allowance affordable**, and it is where the
    measurement went before cto ratified rather than after.

    Every one of these is money-shaped and **none** matches a ratified shape,
    so the guard still refuses it. `asking_price_paise__total` is the one to
    read twice: it starts with the permitted column and is still refused,
    because the exemption is "ends at the column, optionally plus a **lookup**"
    and not "mentions the column".
    """
    assert money_tokens_in(name.lower()), f"{name!r} is not money-shaped, so this proves nothing"
    assert source_shape_exempt(name) is None, why


def test_a_free_floating_money_constant_matches_the_shape_and_is_caught_by_the_pin():
    """**Rule 12, as the one test that shows where this exemption is weakest.**

    `MAX_OFFER_PAISE` and `TYPICAL_SALE_PRICE_PAISE` both satisfy shape B —
    UPPER_SNAKE, money-shaped — and **shape B has no second layer in this
    file**, because a constant is not a column and W1's whitelist cannot reach
    it. That is precisely why cto refused to grant shape B unpinned.

    So this test asserts the gap honestly rather than pretending it is closed
    here: the shape matches, and the control that catches it is
    `tests/unit/test_exempted_bound_is_pinned.py`. If that file is ever
    deleted, this comment is the only thing left saying the exemption was
    conditional — so the pin test asserts its own registration too.
    """
    for name in ("MAX_OFFER_PAISE", "TYPICAL_SALE_PRICE_PAISE"):
        assert source_shape_exempt(name) == "B"
    import pathlib as _pathlib

    pin = _pathlib.Path(__file__).with_name("test_exempted_bound_is_pinned.py")
    assert pin.exists(), (
        "shape B is exempted here and its only other layer is the pin test, "
        f"which is missing: {pin}. ADR-003 §2.3 grants shape B *conditionally*."
    )
    assert len(SOURCE_GUARD_SHAPE_EXEMPTIONS) == 2
