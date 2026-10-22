r"""A-29 §1's gate, asked as a property instead of remembered as a list.

`apps/catalog/services.py` claims *"`served_book_text` is the only place that
decision is made, and every read path goes through it."* **That sentence has
now been false twice**, both times on a route the ruling had not looked at:
F47-Q2 found `/sell/find-book`, and S2-R2-B1 found `book_requests` on two
surfaces after A-29 shipped. Each time the remedy was to find the call sites
by grep and fix them, which is the remedy that produced the second miss.

So this file asks the question the grep was standing in for: **does any module
under `apps/**` or `web/**` read one of the four `SELLER_WRITTEN_TEXT`
attributes off anything at all, outside the gate and the staff readers?** A
new read path fails here by name, with its file, line and receiver, before
anybody has to notice it exists (`CLAUDE.md` rule 11 — ask the property, do
not enumerate the cases).

The instrument is `tests/a11y/test_page_cache_headers.py`'s shape, reused
rather than reinvented: `ast.parse` asked a question that has an answer, not a
regex with coverage.

**Scope, declared rather than assumed.** This walk sees attribute reads and
`getattr` with a literal name, in `apps/**` and `web/**`. Three things it
cannot see, and the layer for each:

1. **`getattr(book, name)` with a computed name**, which is invisible to every
   name-based control here. `test_a_dynamic_attribute_name_is_pinned_to_a_non_book_receiver`
   below pins the two that exist, in both roots, with the reason each
   receiver cannot be a `Book`.

   **The first draft of this paragraph said that
   `tests/unit/test_forbidden_source.py::test_apps_contains_no_dynamic_attribute_construction`
   already covered `apps/**`. It does not** — that walk matches `setattr` and
   `delattr`, and a *read* through a computed name was outside it. So the
   sentence was the unmeasured "another layer covers it" claim that `CLAUDE.md`
   rule 12 was amended about, written into the very file whose job is to stop
   that; it survived until the pin was pointed at `apps/**` and found
   `open_discovery.py:134`. Recorded rather than quietly corrected.
2. **`templates/**`.** A template cannot reach a model: the context carries
   `_book_of`'s dict, which is `served_book_text`'s answer. Code Review
   verified every `{{ book.title }}` in the four page templates reads that
   dict.
3. **`values()` / `values_list()` naming the columns as strings.** Nothing in
   the tree does, and that would be a query the service layer composed — it
   would show up as a `.values(` with those names rather than as an
   attribute. **Covered elsewhere now, and measured**:
   `tests/contract/test_catalogue_text_gate_blind_spots.py::test_no_sealed_column_is_named_as_a_string_to_the_orm`
   is QA's walk over string arguments to `values`/`only`/`F`/`annotate`.
4. **A derived copy of a sealed column, and a lookup written as a keyword
   argument rather than a string.** This is **A-34, and it cost ten digits of
   a phone number.** `title_norm` is `normalise_title(title)` — the seller's
   own words in a different shape — and it is not a sealed *name*, so
   `base.filter(title_norm__contains=needle)` named no sealed attribute, no
   sealed string, and nothing in this file or in QA's walk could see it **even
   in principle**. A value you may not read is still a value you may match
   against.

   Two changes rather than a note. `SEALED` now imports
   `DERIVED_FROM_SELLER_TEXT` as well, so a read of `book.title_norm` fails
   here by name; and `test_no_sealed_column_is_matched_on_outside_the_gate`
   below walks **keyword-argument names** on query methods, which is the shape
   QA's string walk cannot reach and the shape the extraction used.

   **What is still outside all three walks**, declared rather than discovered:
   raw SQL (`cursor.execute`, `RawSQL`, a migration body) naming either column.
   The layer is `tests/unit/test_forbidden_source.py`'s raw-SQL rules plus the
   behavioural measurement, which is the one that does not depend on a name at
   all: `tests/unit/test_catalog.py::test_a_needle_in_withheld_text_selects_nothing_for_a_reader_who_may_not_read_it`
   runs Red Team's own digit walk through `search_books` on both engines and
   asserts no digit comes out.
"""

import ast
import pathlib

import pytest

from apps.catalog.services import DERIVED_FROM_SELLER_TEXT, SELLER_WRITTEN_TEXT

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The attribute names the gate owns. **Imported, not copied** — a fifth
#: seller-written column added to `SELLER_WRITTEN_TEXT` is sealed here the
#: same day, with no edit to this file (`CLAUDE.md` rule 11).
#:
#: **A-34's derived columns are deliberately NOT in here, and the reason is
#: rule 13's order of resort.** `tests/contract/test_catalogue_text_gate_blind_spots.py`
#: imports this set and matches string arguments by their last `__` segment, so
#: adding `title_norm` would turn QA's walk red on `F("title_norm")` inside
#: `search_books` — the gated predicate's own expression, which is the code
#: the control exists to protect. The derived names get their own set and their
#: own match rule below instead, each entry matched on its own terms rather
#: than folded into a flat list (`CLAUDE.md` rule 11).
SEALED = set(SELLER_WRITTEN_TEXT)

#: **A-34.** The sealed columns *plus* every derived copy of one. Used by
#: `test_no_sealed_column_is_matched_on_outside_the_gate`, which asks about
#: **matching**, not about reading a value — `filter(title_norm__contains=…)`
#: reads nothing and discloses everything.
MATCHABLE = SEALED | set(DERIVED_FROM_SELLER_TEXT)

#: QuerySet methods whose **keyword arguments are column lookups**. Narrower
#: than QA's `COLUMN_NAMERS` on purpose: a projection carries a value out, and
#: these carry a *needle in*, which is the half nothing measured. Writes
#: (`create`, `update`) are not here — `title_norm=normalise_title(title)` in
#: `create_book` is the derivation itself, and writing a column is not
#: disclosing it.
LOOKUP_CALLS = ("filter", "exclude", "get", "get_or_create", "Q")

#: `(path, qual) -> the lookups that allowance covers`. One entry, and it is
#: the gate: `search_books` must match `title_norm`, which is the whole point
#: of A-34 putting `readable_text_rows` in front of it.
ALLOWED_LOOKUPS = {
    ("apps/catalog/services.py", "search_books"): frozenset({"title_norm"}),
}

#: `(path, qualname) -> the reason that read is not the gate's business`.
#:
#: Keyed on the **enclosing function**, not on the file, because a file-level
#: allowance exempts the next function somebody adds to that file for free —
#: which is the aggregate-mark failure `CLAUDE.md` rule 10's corollary names.
#: Every entry is a claim and every entry is measured: an entry that matches
#: no live access fails in `test_every_allowance_matches_a_live_access`, and
#: the two staff allowances name a refusal that
#: `test_the_staff_readers_refuse_a_non_staff_actor` exercises rather than
#: describes.
ALLOWED = {
    ("apps/catalog/services.py", "served_book_text"): (
        "the gate itself — this is the one place the decision is made"
    ),
    ("apps/catalog/services.py", "create_book"): (
        "writes the title into the `audit_log` after-dict. That is the record "
        "of what was written, not a read served to anybody; withholding it "
        "would make the audit row describe a different write"
    ),
    ("apps/catalog/models.py", "Book.__str__"): (
        "no call site. Nothing in the tree stringifies a `Book`: no "
        "`str(book)`, no `f\"{book}\"`, no `{{ book }}`, and the one log line "
        "touching one logs `book.id`. The reason used to name the Django "
        "admin, which is not in `INSTALLED_APPS` — a permitted read whose "
        "stated consumer does not exist (F55). The allowance is legitimate "
        "exactly while it stays unreached, which "
        "`tests/contract/test_catalogue_text_gate_blind_spots.py::"
        "test_nothing_stringifies_a_book_while_str_returns_seller_written_text`"
        " is what measures"
    ),
    ("apps/listings/staff.py", "queue_rows"): (
        "a staff reader. `review_queue` refuses a non-staff actor before any "
        "row is read, which is the clause `may_read_unverified_text` grants "
        "staff anyway — so routing it through the gate would change nothing "
        "and hide that the reviewer is the layer"
    ),
    ("apps/listings/management/commands/review_listings.py", "Command._show"): (
        "a staff reader, and the one whose whole purpose is printing the "
        "unverified text so a named human can look at it (A-29's layer). "
        "`listing_for_review` refuses a non-staff actor before the row exists"
    ),
}

#: The two functions whose allowance rests on a refusal rather than on being
#: harmless. Named here so the measurement below cannot drift from the reason.
STAFF_READERS = ("queue_rows", "Command._show")

#: `(path, qual) -> the sealed attributes that allowance covers`. An absent key
#: means the whole function, which is every allowance that is a *surface*
#: judgement — a staff reader is a staff reader whatever it prints.
#:
#: `create_book`'s is not a surface judgement. Its reason is one `audit_log`
#: after-dict line about `title`, and a function-scoped allowance would cover a
#: future read of `authors`, `publisher` or `edition_label` in the same
#: function for free — the aggregate-mark failure of `CLAUDE.md` rule 10's
#: corollary, one scope up from the file-level one the `ALLOWED` comment
#: already names. QA raised it with no instance in the tree; this is the clause
#: rather than a note saying a clause would help.
ALLOWED_ATTRS = {
    ("apps/catalog/services.py", "create_book"): frozenset({"title"}),
}


def _sealed_reads(source):
    """`[(lineno, qualname, attr, receiver_source), …]` for one module.

    Two shapes, because both appeared in the defect: `book.title` and
    `getattr(book, "title", None)` — the second is what `_request_row` used,
    and a walk that saw only the first would have reported `web/views.py` as
    clean while it served the string.

    A method call of the same name is **not** a read: `kind.title()` is
    `str.title`, and flagging it would redden
    `apps/core/management/commands/seed_demo.py` on a string method. That is
    the one narrowing here, and it is a narrowing by *syntax* — the node is
    the `func` of a `Call` — not by name, so it cannot be widened by someone
    choosing a different attribute.
    """
    tree = ast.parse(source)
    called = {
        node.func
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    found = []

    def visit(node, qual):
        for child in ast.iter_child_nodes(node):
            if isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                visit(child, qual + [child.name])
                continue
            where = ".".join(qual) or "<module>"
            if (
                isinstance(child, ast.Attribute)
                and child.attr in SEALED
                and child not in called
            ):
                found.append(
                    (child.lineno, where, child.attr,
                     ast.get_source_segment(source, child.value) or "?")
                )
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id == "getattr"
                and len(child.args) >= 2
                and isinstance(child.args[1], ast.Constant)
                and child.args[1].value in SEALED
            ):
                found.append(
                    (child.lineno, where, child.args[1].value,
                     f"getattr({ast.get_source_segment(source, child.args[0])}, …)")
                )
            visit(child, qual)

    visit(tree, [])
    return found


def _tree_reads():
    """Every sealed read in `apps/**` and `web/**`, keyed as `ALLOWED` is."""
    out = {}
    for root in ("apps", "web"):
        for path in sorted((ROOT / root).rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            for lineno, qual, attr, receiver in _sealed_reads(
                path.read_text(encoding="utf-8")
            ):
                out.setdefault((rel, qual), []).append((lineno, attr, receiver))
    return out


def test_no_sealed_catalogue_attribute_is_read_outside_the_gate():
    """A-29 §1 as a property. **The test that would have caught S2-R2-B1.**

    `_request_row` read `getattr(book, "title", None)` and `_request_payload`
    read `row.book.title`; both would be named here with their line, which is
    the difference between a control and a grep somebody has to remember to
    run.
    """
    assert set(ALLOWED_ATTRS) <= set(ALLOWED), (
        "`ALLOWED_ATTRS` narrows a key that is not in `ALLOWED`, so the "
        "narrowing is never consulted and reads as coverage it does not give"
    )
    unknown = {}
    for key, reads in _tree_reads().items():
        covered = ALLOWED_ATTRS.get(key, SEALED) if key in ALLOWED else frozenset()
        extra = [r for r in reads if r[1] not in covered]
        if extra:
            unknown[key] = extra
    assert not unknown, (
        "A-29 §1: these read a `SELLER_WRITTEN_TEXT` attribute outside "
        "`served_book_text` and the staff readers, so unverified text a "
        "student typed into a global `books` row can reach a reader who is "
        "not its author.\n\n"
        + "\n".join(
            f"  {path}:{lineno} in {qual}() — {receiver}.{attr}"
            for (path, qual), reads in sorted(unknown.items())
            for lineno, attr, receiver in reads
        )
        + "\n\nRoute it through `apps.catalog.services.served_book_text` "
        "(or `_book_of` / `book_block`, which call it) and thread the reader "
        "down to it. If it is genuinely a staff surface, add it to `ALLOWED` "
        "**with the refusal that precedes it named**, and add that refusal to "
        "`STAFF_READERS` so it is measured and not merely asserted."
    )


@pytest.mark.parametrize(
    ("path", "qual"), sorted(ALLOWED), ids=lambda v: v.replace("/", ".")
)
def test_every_allowance_matches_a_live_access(path, qual):
    """A guard for the guard. An allowance that matches nothing is a hole
    waiting for the next function of that name.

    This caught a real thing on its first run: `create_book` reads
    `book.title` once, at line 385, and it is the only read in the file
    outside the gate — had it been removed, the entry would have sat there
    silently permitting a future `create_book` to do anything.
    """
    reads = _tree_reads().get((path, qual))
    assert reads, (
        f"`ALLOWED[({path!r}, {qual!r})]` permits a read that no longer "
        f"exists — the reason given is {ALLOWED[(path, qual)]!r}. A stale "
        f"entry is not harmless: it silently exempts the next function "
        f"somebody gives that name in that file. Delete the entry."
    )
    # And the same question of a narrowed allowance's attribute list: a pinned
    # attribute nobody reads any more is the same stale exemption one scope
    # smaller, and the pin is what would hide it from the assert above.
    pinned = ALLOWED_ATTRS.get((path, qual))
    if pinned is not None:
        dead = pinned - {attr for _lineno, attr, _recv in reads}
        assert not dead, (
            f"`ALLOWED_ATTRS[({path!r}, {qual!r})]` pins {sorted(dead)}, which "
            f"{qual}() no longer reads. Narrow the pin to what it does read, "
            f"or delete the entry and let the allowance cover the function."
        )


@pytest.mark.parametrize(
    ("snippet", "why"),
    [
        ("x = book.title", "the plain attribute read"),
        ('x = getattr(book, "title", None)', "the `getattr` form — what `_request_row` used"),
        ("x = row.book.authors", "a chained receiver — what `_request_payload` used"),
        ("x = self.publisher", "`self`, for a method on the model itself"),
        ("x = anything_at_all.edition_label", "an unrecognised receiver name"),
        ("def f():\n    return b.title", "inside a function, which is where reads live"),
        ("class C:\n    def m(self):\n        return self.title", "inside a method"),
    ],
)
def test_the_walk_sees_each_read_shape(snippet, why):
    """Rule 10's fourth disguise: an instrument that does not assert its reach.

    The walk keys on the **attribute name**, not on the receiver, precisely so
    there is no receiver heuristic to fool. These assert that, including the
    shapes the two defects actually took.
    """
    assert _sealed_reads(snippet), f"the walk does not see {why}: {snippet!r}"


@pytest.mark.parametrize(
    ("snippet", "why"),
    [
        ('x = kind.replace("_", " ").title()', "`str.title()` is a method, not a read"),
        ('x = {"title": t}', "a dict key is not an attribute"),
        ('x = form.cleaned_data["title"]', "a subscript is not an attribute"),
        ('x = getattr(book, name)', "a computed name — the declared hole, pinned below"),
        ('x = text["title"]', "`_book_of` reading the gate's own answer"),
    ],
)
def test_the_walk_does_not_fire_on_these(snippet, why):
    """Both sides are rows (rule 10's corollary). A walk that flagged every
    `.title()` in the tree would be edited rather than obeyed (rule 13), and
    `x = getattr(book, name)` is listed here as the **declared hole**, not as
    a safe shape. The layer that catches it is
    `test_a_dynamic_attribute_name_is_pinned_to_a_non_book_receiver` below —
    not `test_forbidden_source`, which this module's docstring withdraws by
    measurement, and which the reason on that row said until F56."""
    assert not _sealed_reads(snippet), f"the walk fires on {why}: {snippet!r}"


#: `(path, qualname, receiver source) -> why that receiver cannot be a `Book``.
#:
#: A `getattr` with a computed name is invisible to **every** name-based
#: control in this repository, this walk included, so the only control left is
#: a human having looked at the receiver — and a pin is what makes them look.
#: Keyed on the receiver's source text as well as the function, so swapping
#: `_listings()` for `book` on that same line reddens rather than inheriting
#: the allowance.
DYNAMIC_GETATTR = {
    ("web/views.py", "_transition", "_listings()"): (
        "the receiver is the `apps.listings.services` **module**, not a model "
        "instance, and the name is one of two literals passed by "
        "`publish_listing_view` / `withdraw_listing_view`. A module has no "
        "`title`"
    ),
    ("apps/core/management/commands/open_discovery.py", "checklist", "entity"): (
        "the receiver is a `legal_entities` row and the names come from "
        "`LEGAL_ENTITY_FIELDS`, a literal tuple of that table's own columns. "
        "`LegalEntity` has no field in `SELLER_WRITTEN_TEXT`"
    ),
}


def test_a_dynamic_attribute_name_is_pinned_to_a_non_book_receiver():
    """The declared hole above, closed as far as it can be, in both roots.

    `getattr(book, column)` would pass every other walk in this file and in
    `tests/unit/test_forbidden_source.py` — see this module's docstring for
    what I wrongly believed covered `apps/**`. Measured rather than declared,
    because rule 12 now requires the named layer to be measured in the same
    pass.

    **Not a blanket refusal**, because both sites that exist are legitimate
    and a guard that fires on legitimate code gets edited rather than obeyed
    (rule 13). The blanket version found both on its first run, which is how I
    know the narrowing is a narrowing and not a convenience.
    """
    found = {}
    for path in sorted(
        [*(ROOT / "web").rglob("*.py"), *(ROOT / "apps").rglob("*.py")]
    ):
        source = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()

        def visit(node, qual):
            for child in ast.iter_child_nodes(node):
                if isinstance(
                    child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    visit(child, qual + [child.name])
                    continue
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id == "getattr"
                    and len(child.args) >= 2
                    and not (
                        isinstance(child.args[1], ast.Constant)
                        and isinstance(child.args[1].value, str)
                    )
                ):
                    key = (
                        rel,
                        ".".join(qual) or "<module>",
                        ast.get_source_segment(source, child.args[0]) or "?",
                    )
                    found.setdefault(key, []).append(child.lineno)
                visit(child, qual)

        visit(ast.parse(source), [])

    unknown = {k: v for k, v in found.items() if k not in DYNAMIC_GETATTR}
    assert not unknown, (
        "`getattr` with a computed attribute name is invisible to "
        "every name-based control in this repository, the A-29 walk above "
        "included — so `getattr(book, column)` would serve unverified seller "
        "text with nothing to stop it.\n\n"
        + "\n".join(
            f"  {path}:{lineno} in {qual}() — receiver {receiver}"
            for (path, qual, receiver), lines in sorted(unknown.items())
            for lineno in lines
        )
        + "\n\nUse a literal name, or pin it in `DYNAMIC_GETATTR` with "
        "the reason that receiver cannot be a `Book`."
    )
    stale = set(DYNAMIC_GETATTR) - set(found)
    assert not stale, (
        f"pinned dynamic `getattr` sites that no longer exist: {sorted(stale)}. "
        "A stale pin exempts the next one that lands in that function with "
        "that receiver spelling."
    )


def test_the_staff_readers_refuse_a_non_staff_actor(student, book):
    """The refusal two allowances rest on, exercised rather than described.

    `queue_rows` and `Command._show` read the four strings raw. Their reason
    for being in `ALLOWED` is not "staff may see anything" — it is that a
    non-staff actor never reaches the read. Rule 12: name the other layer,
    **and measure it in the same pass**, because across three amendments the
    unmeasured "another layer covers it" sentence was every time the false
    one.
    """
    from apps.core.errors import ServiceError
    from apps.listings import staff as staff_surface

    assert set(STAFF_READERS) <= {q for _p, q in ALLOWED}, (
        "STAFF_READERS names a function that is not in ALLOWED, so this test "
        "measures a refusal nothing depends on"
    )

    with pytest.raises(ServiceError):
        staff_surface.queue_rows(student)
    with pytest.raises(ServiceError):
        # The entry point of `Command._show`: the command cannot reach a row
        # without it, so this is the refusal that precedes that read.
        staff_surface.listing_for_review(student, 1)


# --- S2-R2-B1, behaviourally: the journey, on both routes -------------------
#
# The walk above is the **existence** half — it fails by name, so you know
# which read path went missing. These are the **behaviour** half, and
# `CLAUDE.md` rule 9 says ship both and never only the first. The walk would
# stay green if `_book_of` were threaded a reader it then ignored.


@pytest.fixture
def requester(db, signup_campus, privacy_notice):
    """**Student B** — ACTIVE, on the same campus, and not the book's author.

    `unverified_book` is created by `student`, so the fixture that produces
    S2-R2-B1's condition is a *second* actor: the whole defect is that the
    person reading their own want list is routinely not the person who typed
    the catalogue entry. `is_seed=True` because the pilot campus's gate is
    lawfully closed and a non-seed actor would be refused for a reason that
    has nothing to do with authorship (ADR-002 §4.1(c)) — which would measure
    the gate and report it as coverage of the gate under test.
    """
    from apps.accounts.models import User
    from apps.accounts.services import grant_consent

    user = User.objects.create(
        email="arjun@example.ac.in", display_name="Arjun K",
        campus=signup_campus, city_id=signup_campus.city_id,
        status="ACTIVE", adult_verified=True, campus_verified=True, is_seed=True,
    )
    grant_consent(user, "account", privacy_notice, "SIGNUP_FORM", None, "pytest")
    user.refresh_from_db()
    return user


def _want(requester, book):
    from apps.listings.services import create_request

    return create_request(requester, book=book, free_text_title=None, course_code=None)


@pytest.mark.django_db
@pytest.mark.parametrize("verified", [False, True], ids=["unverified", "verified"])
def test_the_wanted_page_withholds_a_row_its_reader_did_not_type(
    requester, unverified_book, book, verified
):
    """`/wanted` — F47-Q2's journey on the second route.

    Both sides are rows (rule 10's corollary): on a verified catalogue row the
    same page shows the title, so a view that withheld everything would not
    pass. The condition is asserted before any markup is looked at, because a
    fixture that stopped producing a withheld row would otherwise make this
    pass vacuously (rule 10's third disguise).
    """
    from apps.accounts.sessions import SESSION_USER_KEY
    from apps.catalog.services import served_book_text
    from django.test import Client

    subject = book if verified else unverified_book
    assert served_book_text(subject, requester)["withheld"] is not verified, (
        "the fixture no longer produces the condition this test is about"
    )
    _want(requester, subject)

    client = Client()
    session = client.session
    session[SESSION_USER_KEY] = requester.id
    session.save()
    body = client.get("/wanted").content.decode()

    if verified:
        assert subject.title in body
    else:
        assert subject.title not in body, (
            "a student who typed an ISBN into /wanted is served the raw "
            "catalogue text of a row somebody else wrote — S2-R2-B1, which "
            "is F47-Q2 on a second route"
        )
        assert f"ISBN {subject.isbn13}" in body, "the identity half of A-29 §1"


@pytest.mark.django_db
@pytest.mark.parametrize("verified", [False, True], ids=["unverified", "verified"])
def test_the_requests_api_withholds_a_row_its_reader_did_not_type(
    requester, unverified_book, book, verified
):
    """`GET /api/v1/requests` — the same journey, the JSON twin.

    `text_withheld` is asserted as well as the absence of the string: a
    client that cannot tell a withheld title from a real one will render
    `ISBN 978…` as a book called that.
    """
    import json

    from apps.accounts.sessions import SESSION_USER_KEY
    from django.test import Client

    subject = book if verified else unverified_book
    _want(requester, subject)

    client = Client()
    session = client.session
    session[SESSION_USER_KEY] = requester.id
    session.save()
    response = client.get("/api/v1/requests")
    assert response.status_code == 200, response.content
    row = json.loads(response.content)["items"][0]

    assert row["book"]["isbn13"] == subject.isbn13, "the identity is always served"
    assert row["book"]["text_withheld"] is not verified
    if verified:
        assert row["book"]["title"] == subject.title
    else:
        assert subject.title not in response.content.decode(), (
            "`_request_payload` is serving raw seller-written catalogue text "
            "to a requester who is not its author (S2-R2-B1)"
        )


def test_listing_detail_is_still_an_own_rows_read():
    """S2-R2-R2 — a guard for a forward-dated decision, not for today's code.

    `listing_detail` passes the **signed-in viewer** as `reader`, and A-30
    words a listing read as passing *"the actor whose listing it is"*. In S2
    they are the same actor, because the view reads `get_own_listing`. Its own
    docstring promises S3 *"swaps one line"* to `discovery.get_listing`, and
    on the day that happens `reader` becomes the buyer — so the choice has to
    be made deliberately rather than inherited.

    It is not a leak either way while A-29 §2 holds (a listing on an
    unverified book cannot reach a buyer), which is why this is a tripwire and
    not an assertion about data. The viewer is the tighter of the two forms:
    the seller-form is correct only *because* of A-29 §2, and the viewer-form
    is correct without it. That is written down in `_book_of`'s docstring; this
    is what makes somebody read it.
    """
    source = (ROOT / "web" / "views.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    view = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "listing_detail"
        ),
        None,
    )
    assert view is not None, (
        "`listing_detail` no longer exists in web/views.py, so this tripwire "
        "guards nothing. Re-point it at whatever view serves `/listing/{id}`."
    )
    calls = {
        node.func.attr
        for node in ast.walk(view)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "get_own_listing" in calls and "get_listing" not in calls, (
        "`listing_detail` has stopped being an own-rows read, which is S3's "
        "promised one-line swap. `_listing_row(listing, user)` passes the "
        "*viewer* as A-29's `reader`, and A-30 words it as the listing's "
        "owner — the two have just stopped coinciding. Read `_book_of`'s "
        "docstring, decide which actor this page passes, and change this test "
        "to assert that decision. Do not simply delete it: A-29 §2 is the "
        "only reason the difference is not a leak today."
    )


# --- A-32: a student's own words, and only on the surface they are theirs ---

#: A typed title that cannot be confused with `unverified_book`'s own
#: ("Higher Engineering Mathematics"). A test that typed the same words could
#: not tell *their title was shown* from *the other student's title leaked*,
#: which is rule 10's vacuous pass wearing the right assertion.
MY_WORDS = "Grewal maths, 43e, the big green one"


@pytest.mark.django_db
@pytest.mark.parametrize("typed", [True, False], ids=["typed-a-title", "typed-nothing"])
def test_the_wanted_page_serves_a_student_their_own_words_and_withholds_the_rows(
    requester, unverified_book, typed
):
    """A-32, F51 and F52 — through the POST that threw the words away.

    **Both sides are rows** (rule 10's corollary). *Typed:* what they wrote is
    stored and rendered, and the catalogue row's title still is not. *Typed
    nothing:* the row stays withheld as the `ISBN 978…` identity, which is
    A-29 §1 unchanged. A view that served the catalogue title to anyone who
    had typed anything would pass the first half and fail the second; a view
    that still discarded the typed title would pass the second and fail the
    first.

    Driven through `POST /wanted` and not `create_request`, because the defect
    was the view's: `free_text_title=None if book is not None else …` threw
    the words away before the service saw them, so a service-level test was
    green while the page was bare.
    """
    from apps.accounts.sessions import SESSION_USER_KEY
    from apps.catalog.services import served_book_text
    from apps.listings.models import BookRequest
    from django.test import Client

    assert served_book_text(unverified_book, requester)["withheld"] is True, (
        "the fixture no longer produces the condition this test is about"
    )

    client = Client()
    session = client.session
    session[SESSION_USER_KEY] = requester.id
    session.save()
    posted = client.post(
        "/wanted",
        {
            "isbn": unverified_book.isbn13,
            "title": MY_WORDS if typed else "",
            "course_code": "MA8151",
        },
    )
    assert posted.status_code == 302, posted.content

    row = BookRequest.all_objects.get(requester_pseudonym=requester.person_pseudonym)
    assert row.book_id == unverified_book.id, (
        "the ISBN no longer matches the unverified row, so this test is about "
        "a free-text want and not about F51"
    )
    assert row.free_text_title == (MY_WORDS if typed else None), (
        "F51: what the student typed is stored whether or not the ISBN "
        "matched somebody else's catalogue row"
    )

    body = client.get("/wanted").content.decode()
    assert unverified_book.title not in body, (
        "A-29 §1: the title on that row is another student's words, and no "
        "amount of the reader's own typing unlocks it"
    )
    if typed:
        assert MY_WORDS in body, "F52: their own words, served back to them"
        assert f"ISBN {unverified_book.isbn13}" not in body, (
            "the ISBN-only form is what a bare row reads as; this row is not "
            "bare, so the substitution did not happen"
        )
    else:
        assert f"ISBN {unverified_book.isbn13}" in body, (
            "a student who typed nothing has no words of their own, and the "
            "row must stay withheld rather than borrow the catalogue's"
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("second_post", "rows", "why"),
    [
        ({"title": "the big green maths book"}, 1, "two spellings of one want are one want"),
        ({"course_code": "MA8251"}, 2, "a different course is a different want"),
    ],
    ids=["another-spelling", "another-course"],
)
def test_a_want_carrying_a_book_fk_is_idempotent_on_the_book_and_the_course(
    requester, unverified_book, second_post, rows, why
):
    """A-32's one consequence, decided in the amendment rather than here.

    Storing the typed label would otherwise split one want into two rows,
    because the shape filter keyed on it. **Both sides are rows:** a second
    spelling of the same want for the same course collapses, and the same book
    for a different course does not — so the key is `book_id` and
    `course_code` rather than the broader *one open want per book*, which
    would pass the first case and swallow a real second want.
    """
    from apps.accounts.sessions import SESSION_USER_KEY
    from apps.listings.models import BookRequest
    from django.test import Client

    client = Client()
    session = client.session
    session[SESSION_USER_KEY] = requester.id
    session.save()
    first = {"isbn": unverified_book.isbn13, "title": MY_WORDS, "course_code": "MA8151"}
    assert client.post("/wanted", first).status_code == 302
    assert client.post("/wanted", {**first, **second_post}).status_code == 302

    open_rows = BookRequest.all_objects.filter(
        requester_pseudonym=requester.person_pseudonym, status="OPEN"
    )
    assert open_rows.count() == rows, (
        f"{why} — stored: "
        f"{list(open_rows.values_list('free_text_title', 'course_code'))}"
    )


@pytest.mark.django_db
def test_the_bare_line_can_be_replaced_by_going_back_and_typing_a_title(
    requester, unverified_book
):
    """**F56, folded into A-34.** A-32's idempotency clause re-created F51.

    Walk the journey A-32's remedy exists for. A student resolves an ISBN,
    types no title (the form does not require one), and is shown the bare
    `ISBN 978…` line. They do the one thing that screen invites: they go back
    and type the title. Before the fix the same `(book, course_code)` key
    returned the existing row, their words were dropped under a flash saying
    it was already on their list, and — with no `update_request` — **that row
    stayed bare for as long as it existed.**

    `create_request` now fills `free_text_title` on an existing row when it is
    NULL. No new endpoint, no second row.
    """
    from apps.accounts.sessions import SESSION_USER_KEY
    from apps.listings.models import BookRequest
    from django.test import Client

    client = Client()
    session = client.session
    session[SESSION_USER_KEY] = requester.id
    session.save()
    bare = {"isbn": unverified_book.isbn13, "title": "", "course_code": ""}
    assert client.post("/wanted", bare).status_code == 302
    assert f"ISBN {unverified_book.isbn13}" in client.get("/wanted").content.decode(), (
        "the bare line is gone, so this test's premise is retired"
    )

    assert client.post("/wanted", {**bare, "title": MY_WORDS}).status_code == 302
    rows = list(BookRequest.all_objects.filter(book=unverified_book))
    assert len(rows) == 1, "A-32's idempotency no longer collapses the retry"
    assert rows[0].free_text_title == MY_WORDS, (
        "F56: the student typed a title to replace the bare line and the row "
        f"still carries free_text_title={rows[0].free_text_title!r}"
    )
    body = client.get("/wanted").content.decode()
    assert MY_WORDS in body
    assert f"ISBN {unverified_book.isbn13}" not in body
    assert unverified_book.title not in body, (
        "A-29 §1 is unchanged by F56: the backfill writes the reader's own "
        "words, never the catalogue row's"
    )


@pytest.mark.django_db
def test_the_backfill_cannot_overwrite_a_title_or_reach_another_students_row(
    requester, student, unverified_book
):
    """**Both sides of F56's fix are rows** (rule 10's corollary). The fill is
    NULL-only and own-row-only, and a fix that wrote on every retry would pass
    the test above and fail both of these.

    The second clause is `create_request`'s existing shape filter, which keys
    on `requester_pseudonym` — so this asserts a property the fix *inherits*
    rather than one it adds, which is the half that silently breaks if
    somebody ever widens that filter.
    """
    from apps.listings.models import BookRequest
    from apps.listings.services import create_request

    first = create_request(requester, book=unverified_book, free_text_title=MY_WORDS)
    again = create_request(
        requester, book=unverified_book, free_text_title="something else entirely"
    )
    assert again.id == first.id
    again.refresh_from_db()
    assert again.free_text_title == MY_WORDS, (
        "the backfill overwrote a title the student already had; it fills "
        "NULL and nothing else"
    )

    # `student` is a second student on the same campus with no row yet. Their
    # post must create their own row, not touch `requester`'s.
    theirs = create_request(student, book=unverified_book, free_text_title="my own")
    assert theirs.id != first.id
    first.refresh_from_db()
    assert first.free_text_title == MY_WORDS
    assert BookRequest.all_objects.filter(book=unverified_book).count() == 2


@pytest.mark.django_db
def test_the_substitution_is_the_requests_and_cannot_reach_a_listing(
    requester, unverified_book
):
    """A-32's boundary: a seller who typed nothing has no words to show.

    `listings` has no free-text column, so a listing surface has nothing to
    fall back **to** — which is a property of the schema today, not a control.
    The control is in two clauses: the helper every listing template reads
    (`_book_of`, through `sell.html`, `sell_photos.html`, `listing.html` and
    `sell_find.html`) still answers with the withheld form, and the request's
    column has exactly one reader in `web/views.py`. The second is what fails
    the day somebody wires the fallback into `_book_of` or `_listing_row` and
    makes the leak possible — at which point a seller would be shown either
    another student's typed title or the catalogue row A-29 §1 withholds.
    """
    from web.views import _book_of

    served = _book_of(unverified_book, requester)
    assert served["withheld"] is True
    assert served["title"] == f"ISBN {unverified_book.isbn13}", (
        "the shared listing/request helper has started serving something "
        "other than the identity for a row its reader did not write"
    )

    source = (ROOT / "web" / "views.py").read_text(encoding="utf-8")
    readers = {
        node.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(
            (isinstance(child, ast.Attribute) and child.attr == "free_text_title")
            or (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id == "getattr"
                and len(child.args) >= 2
                and isinstance(child.args[1], ast.Constant)
                and child.args[1].value == "free_text_title"
            )
            for child in ast.walk(node)
        )
    }
    assert readers == {"_request_row"}, (
        "A-32 substitutes a student's own words on the **request** surface "
        f"only, and these functions read `free_text_title`: {sorted(readers)}"
    )


# --- A-34: the half that matches rather than reads -------------------------


def _sealed_lookups(source):
    """`[(lineno, qualname, lookup, call)]` — every keyword-argument lookup on
    a `MATCHABLE` column in one module.

    The shape A-34 is about: `base.filter(title_norm__contains=needle)` names
    no attribute and no string, so the attribute walk above and QA's string
    walk are both green while ten digits of a phone number come out one
    signed-in `200` at a time.

    Matched on **any** `__` segment, so a traversal into the column
    (`book__title_norm__contains`) is seen as well as the column itself. The
    first draft read only the first segment and QA's walk reads only the last,
    which left `book__title_norm` outside both — a gap found by writing the
    both-sides parametrisation below, which is what that convention is for.
    Measured cost of the wider rule: **zero** extra sites in the tree.
    """
    tree = ast.parse(source)
    found = []

    def visit(node, qual):
        for child in ast.iter_child_nodes(node):
            if isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                visit(child, qual + [child.name])
                continue
            where = ".".join(qual) or "<module>"
            if isinstance(child, ast.Call):
                func = child.func
                name = (
                    func.attr if isinstance(func, ast.Attribute)
                    else func.id if isinstance(func, ast.Name)
                    else None
                )
                if name in LOOKUP_CALLS:
                    for kw in child.keywords:
                        if set((kw.arg or "").split("__")) & MATCHABLE:
                            found.append((child.lineno, where, kw.arg, name))
            visit(child, qual)

    visit(tree, [])
    return found


def test_no_sealed_column_is_matched_on_outside_the_gate():
    """**A-34 as a property.** The test that would have caught the oracle.

    `search_books` did `base.filter(title_norm__contains=needle)` with no row
    gate in front of it, and every control in this repository was green:
    `title_norm` is not a sealed attribute name, nothing read it as an
    attribute, and no string argument named it in a projection. This walk
    names it with its line.

    The one allowance is `search_books` itself, and it is legitimate **only
    because `readable_text_rows` runs first** — which is a property of the
    function body, not of this list, so it is measured separately in
    `tests/unit/test_catalog.py::test_a_needle_in_withheld_text_selects_nothing_for_a_reader_who_may_not_read_it`.
    """
    unknown = {}
    live = set()
    for root in ("apps", "web"):
        for path in sorted((ROOT / root).rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            for lineno, qual, lookup, call in _sealed_lookups(
                path.read_text(encoding="utf-8")
            ):
                permitted = ALLOWED_LOOKUPS.get((rel, qual), frozenset())
                if set(lookup.split("__")) & permitted:
                    live.add((rel, qual))
                else:
                    unknown.setdefault((rel, qual), []).append((lineno, lookup, call))
    # **A guard for the guard**, the same one `test_every_allowance_matches_a_live_access`
    # is for the attribute walk: an allowance that matches nothing is not
    # harmless, it silently exempts the next function somebody gives that name
    # in that file. `ALLOWED_LOOKUPS` is its own namespace and not a subset of
    # `ALLOWED` — `search_books` reads no sealed *attribute*, which is exactly
    # why this walk had to exist.
    assert set(ALLOWED_LOOKUPS) == live, (
        f"`ALLOWED_LOOKUPS` permits {sorted(set(ALLOWED_LOOKUPS) - live)}, "
        "which match no live lookup. Delete the stale entries."
    )
    assert not unknown, (
        "A-34: these match a needle against seller-written catalogue text, or "
        "against a derived copy of it, without narrowing the rows to the ones "
        "the actor may read. A value you may not print is still a value you "
        "may match against — this is the predicate the phone number came out "
        "of.\n\n"
        + "\n".join(
            f"  {path}:{lineno} in {qual}() — {call}({lookup}=…)"
            for (path, qual), hits in sorted(unknown.items())
            for lineno, lookup, call in hits
        )
        + "\n\nPut `apps.catalog.services.readable_text_rows(qs, actor)` in "
        "front of the match and thread the actor down to it."
    )


@pytest.mark.parametrize(
    ("snippet", "why"),
    [
        ('qs.filter(title_norm__contains=n)', "the derived copy — the A-34 defect itself"),
        ('qs.filter(title_norm=n)', "the derived copy, exact"),
        ('qs.filter(title__icontains=n)', "the sealed column directly"),
        ('qs.exclude(publisher=n)', "`exclude` is a match too"),
        ('Q(edition_label__startswith=n)', "a bare `Q`, which composes into one"),
        ('qs.get(authors__contains=n)', "`get` narrows by the same predicate"),
        ('qs.filter(book__title_norm=n)', "a traversal into the derived copy — outside both earlier rules"),
        ('def f():\n    return qs.filter(title_norm__contains=n)', "inside a function"),
    ],
)
def test_the_lookup_walk_sees_each_match_shape(snippet, why):
    """Rule 10's fourth disguise, for the new half: the instrument asserts its
    own reach before any clean run of it means anything."""
    assert _sealed_lookups(snippet), f"the walk does not see {why}: {snippet!r}"


@pytest.mark.parametrize(
    ("snippet", "why"),
    [
        ('qs.filter(isbn13=d)', "an ISBN is published deliberately (A-29 §1)"),
        ('qs.filter(merged_into__isnull=True)', "not a seller-written column"),
        ('Book.objects.create(title_norm=normalise_title(t))', "the derivation: a write, not a match"),
        ('x = {"title_norm": t}', "a dict key is not a lookup"),
        ('qs.order_by("title")', "ordering by a column does not put it in the result set"),
    ],
)
def test_the_lookup_walk_does_not_fire_on_these(snippet, why):
    """**Both sides are rows** (rule 10's corollary): the permitted side is
    asserted, because a walk that fired on `isbn13=` or on the derivation
    itself would be edited rather than obeyed (rule 13).

    `order_by("title")` is here for the reason QA's file records against its
    own narrowing: ordering by a column does not carry it out and does not
    match a needle against it, so firing there would be wrong rather than
    inconvenient.
    """
    assert not _sealed_lookups(snippet), f"the walk fires on {why}: {snippet!r}"
