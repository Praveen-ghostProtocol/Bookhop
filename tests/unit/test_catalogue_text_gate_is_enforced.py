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
   attribute. Not covered here, and no instance exists.
"""

import ast
import pathlib

import pytest

from apps.catalog.services import SELLER_WRITTEN_TEXT

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The attribute names the gate owns. **Imported, not copied** — a fifth
#: seller-written column added to `SELLER_WRITTEN_TEXT` is sealed here the
#: same day, with no edit to this file (`CLAUDE.md` rule 11).
SEALED = set(SELLER_WRITTEN_TEXT)

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
        "`__str__` reaches the Django admin and the logs, both of which are "
        "staff surfaces. No student-facing template renders a model instance"
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
    unknown = {k: v for k, v in _tree_reads().items() if k not in ALLOWED}
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
        ('x = getattr(book, name)', "a computed name — covered by test_forbidden_source"),
        ('x = text["title"]', "`_book_of` reading the gate's own answer"),
    ],
)
def test_the_walk_does_not_fire_on_these(snippet, why):
    """Both sides are rows (rule 10's corollary). A walk that flagged every
    `.title()` in the tree would be edited rather than obeyed (rule 13), and
    `x = getattr(book, name)` is listed here as the **declared hole**, not as
    a safe shape: it is `test_forbidden_source`'s to catch, and that is the
    other layer rule 12 asks me to name."""
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
