r"""A-29 §1's gate — the read paths its own instrument cannot see.

`tests/unit/test_catalogue_text_gate_is_enforced.py` is backend's answer to
the two misses (F47-Q2, S2-R2-B1) and it is now **the** control: an AST walk
over `apps/**` and `web/**` that fails by name on any read of a
`SELLER_WRITTEN_TEXT` attribute outside five declared allowances. QA audited
it by mutation rather than by reading it, and it holds — an injected
`req.book.title` reddens with file, line and receiver, and the dynamic-`getattr`
pin reddens on a changed receiver spelling.

**This file is the three holes that audit found, and they are holes of two
kinds.** Its docstring declares three; two of those are measured elsewhere
(the pin, and Code Review's read of the four page templates) and **one is
not**. Two more are not declared at all. Rule 12 as amended today: before
granting an exemption, *name the other layer that still catches it — if none
does, it is a widening*. For these three there was no other layer, so they
are rows here:

1. **The ORM naming the column as a string.** Declared in that docstring as
   *"Not covered here, and no instance exists."* The second half is true
   today and nothing asserts it. QA injected
   `Book.objects.values_list("title", flat=True)` into `web/views.wanted` and
   the instrument stayed **green on all 25 tests** — that is the measurement,
   and it is why this is a row rather than a note.
2. **Roots outside `apps/**` and `web/**`.** `bookhop/**` holds the URLconf
   and the WSGI entry point and is walked by nothing. Undeclared.
3. **`Book.__str__`, whose allowance names a surface that is not
   installed.** `ALLOWED[("apps/catalog/models.py", "Book.__str__")]` reads
   *"`__str__` reaches the Django admin and the logs, both of which are staff
   surfaces"*. `django.contrib.admin` is **not in `INSTALLED_APPS`**, and the
   one log line that touches a book logs `book.id`. So the permitted read has
   no consumer named correctly and no call site at all — and every call site
   it could acquire (`str(book)`, `f"{book}"`, `{{ book }}`) is invisible to
   a walk that keys on attribute names. Inverted per rule 10's fifth
   disguise: the day something stringifies a `Book`, this reddens.

**Ceiling, declared.** Rows 1 and 3 match *source text*, because the subject
is source text: a column named through a variable (`.values(col)`) or a
`Book` stringified through an alias this file cannot resolve gets through.
The layer above is the same one A-29 §1 rests on — a named human reading the
diff — and that is the honest statement of it, not a second instrument.
"""

import ast
import pathlib
import re

from tests.unit.test_catalogue_text_gate_is_enforced import (
    ALLOWED,
    SEALED,
    _sealed_reads,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: Every root that ships. The instrument walks the first two.
CODE_ROOTS = ("apps", "web", "bookhop")

#: QuerySet methods and expressions that name a column as a string literal.
#: `F` and `Value` are included because `annotate(t=F("book__title"))` is the
#: shape that would reach a serialiser without one attribute access anywhere.
#:
#: **`order_by` is deliberately not here, and it was, for one run.** It
#: matched three live and legitimate sites — `apps/catalog/services.py:293`,
#: `:302` and `:456` order a search and `prescribed_for_course` by `title`
#: and `book__title`. Ordering *by* a column does not put it in the result
#: set, so the match was wrong rather than inconvenient, and rule 13 says a
#: guard that fires on the code it protects gets edited rather than obeyed.
#: Narrowed to the calls that actually carry a value out: a projection
#: (`values`/`values_list`/`only`/`defer`) or an expression
#: (`F`/`Value`/`annotate`/`aggregate`).
COLUMN_NAMERS = (
    "values", "values_list", "only", "defer", "F", "Value",
    "annotate", "aggregate",
)


def _python_files():
    for root in CODE_ROOTS:
        base = ROOT / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            yield path.relative_to(ROOT).as_posix(), path.read_text(encoding="utf-8")


def test_no_sealed_column_is_named_as_a_string_to_the_orm():
    """Hole 1, measured. **The instrument is green while this leaks.**

    A `.values("title")` or an `F("book__title")` carries the same string to
    the same reader with no attribute access for a name-based walk to see.

    The match is on a string argument equal to a sealed name or ending
    `__<sealed name>`, so `title_norm` and `isbn13` do not fire (both are in
    `test_catalog.py`'s declared exempt set) and `book__title` does.
    """
    named = []
    for rel, text in _python_files():
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = (
                func.attr if isinstance(func, ast.Attribute)
                else func.id if isinstance(func, ast.Name)
                else None
            )
            if name not in COLUMN_NAMERS:
                continue
            for arg in [*node.args, *(kw.value for kw in node.keywords)]:
                if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
                    continue
                leaf = arg.value.lstrip("-").split("__")[-1]
                if leaf in SEALED:
                    named.append(f"  {rel}:{node.lineno} {name}({arg.value!r})")

    assert named == [], (
        "A-29 §1: these name a `SELLER_WRITTEN_TEXT` column as a string to "
        "the ORM, which carries the seller's text to the caller without one "
        "attribute access — so "
        "`tests/unit/test_catalogue_text_gate_is_enforced.py` stays green on "
        "it. Measured: an injected "
        "`Book.objects.values_list('title', flat=True)` in `web/views.wanted` "
        "reddened nothing.\n"
        + "\n".join(named)
        + "\n\nRoute the read through `apps.catalog.services.served_book_text` "
        "and pass the reader, or — if the column is not `books.title` at all "
        "— rename the local so the string is not the sealed spelling."
    )


def test_no_sealed_attribute_is_read_in_a_root_the_instrument_does_not_walk():
    """Hole 2. The walk itself, re-pointed at the root nobody walks.

    Reusing `_sealed_reads` rather than restating it (rule 11): if backend
    widens or narrows what a read *is*, this moves with it, and if the
    function is deleted this errors on import instead of passing quietly.

    **The instrument asserts its own reach**: `bookhop/**` must contain at
    least one parsed module, or a clean run here means the directory was
    renamed and nothing is being checked.
    """
    unwalked = [r for r in CODE_ROOTS if r not in ("apps", "web")]
    parsed = {
        rel: _sealed_reads(text)
        for rel, text in _python_files()
        if rel.split("/")[0] in unwalked
    }
    assert parsed, (
        f"no module was parsed in {unwalked}, so this test covers nothing — "
        "the root was renamed and `CODE_ROOTS` has not followed it"
    )
    reads = {rel: found for rel, found in parsed.items() if found}
    assert reads == {}, (
        "these modules live outside `apps/**` and `web/**`, which is the "
        "whole scope of A-29 §1's instrument, and they read a sealed "
        f"catalogue attribute: {reads}. Either move the code into an app or "
        "add the root to that walk."
    )


#: Source spellings that would make `Book.__str__` a live read path.
#: `(regex, what it is)`. Matched against source text — see the ceiling in
#: this module's docstring.
STRINGIFIERS = (
    (re.compile(r"\bstr\(\s*[\w.]*\bbook\b\s*\)"), "`str(book)`"),
    (re.compile(r"\{\s*[\w.]*\bbook\b\s*[:!}]"), "an f-string of a bare book"),
    (re.compile(r"\bformat\(\s*[\w.]*\bbook\b\s*\)"), "`format(book)`"),
    (re.compile(r"\{\{\s*[\w.]*\bbook\s*(\||\}\})"), "a template rendering a bare book"),
)


def test_nothing_stringifies_a_book_while_str_returns_seller_written_text():
    """Hole 3, inverted (rule 10's fifth disguise).

    `Book.__str__` reads `title` and is in `ALLOWED` on the ground that it
    reaches *"the Django admin and the logs"*. Half of that reason does not
    exist — there is no admin in `INSTALLED_APPS` — and the allowance has no
    call site, so from outside, *"nobody stringifies a Book"* and *"the
    allowance is covering a leak"* are indistinguishable. This makes them
    distinguishable: the allowance stays legitimate exactly while this test
    has nothing to report.

    It fails the day a `str(book)`, an `f"{book}"` or a `{{ book }}` lands.
    That is not automatically a defect — a staff template may legitimately
    want it — but it is the point at which somebody has to decide, which is
    what the allowance currently assumes already happened.
    """
    assert ("apps/catalog/models.py", "Book.__str__") in ALLOWED, (
        "`Book.__str__` is no longer an allowed sealed read, so this tripwire "
        "guards nothing — delete it, or re-point it at whatever replaced it"
    )

    sites = []
    for rel, text in _python_files():
        for pattern, what in STRINGIFIERS[:3]:
            for match in pattern.finditer(text):
                line = text[: match.start()].count("\n") + 1
                sites.append(f"  {rel}:{line} {what} — {match.group(0)!r}")
    for path in sorted((ROOT / "templates").rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        for match in STRINGIFIERS[3][0].finditer(text):
            line = text[: match.start()].count("\n") + 1
            sites.append(
                f"  templates/{path.name}:{line} {STRINGIFIERS[3][1]} — "
                f"{match.group(0)!r}"
            )

    assert sites == [], (
        "`Book.__str__` returns the seller-written title, and these "
        "stringify a `Book`, so each is a read of sealed catalogue text that "
        "A-29 §1's attribute walk cannot see:\n"
        + "\n".join(sites)
        + "\n\nIf the surface is staff-only, say so in that allowance's "
        "reason **and name the refusal that precedes it**, the way the two "
        "staff readers do. If it is student-facing, it is the sixth missed "
        "read path."
    )


def test_the_admin_named_in_the_str_allowance_is_still_absent():
    """The other half of hole 3, asserted rather than left as prose.

    The allowance's reason names the Django admin. It is not installed. If it
    ever is, `Book.__str__` acquires a real reader and a real call site in the
    same commit, and the reason becomes a claim about a live surface instead
    of a description of one that does not exist.
    """
    from django.conf import settings

    assert "django.contrib.admin" not in settings.INSTALLED_APPS, (
        "the Django admin is now installed, so `ALLOWED`'s reason for "
        "`Book.__str__` has become live rather than hypothetical. Check that "
        "`books` is either unregistered or staff-gated, and that the sealed "
        "columns are not in a `list_display`."
    )


def test_the_reused_walk_is_the_one_the_instrument_uses():
    """A guard for this file. Rule 11's point: one definition, many readers.

    If `_sealed_reads` is ever narrowed so that it sees nothing, both tests
    above would pass vacuously while the instrument they borrow it from
    failed loudly — the two would disagree and only one would say so.
    """
    assert _sealed_reads("x = book.title"), (
        "the borrowed walk no longer sees a plain sealed attribute read, so "
        "the two tests above are passing vacuously"
    )
    assert SEALED, "`SELLER_WRITTEN_TEXT` is empty; the gate seals nothing"
