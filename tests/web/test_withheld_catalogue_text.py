"""A-29 §1's label half: the sentence a student is shown where a title would be.

**frontend-developer's tree.** `tests/unit/**` and `tests/api/**` are
backend's, `tests/e2e/**`, `tests/a11y/**` and `tests/contract/**` are QA's,
and `tests/redteam/**` is Red Team's (`TASKS.md` §1). A regression for a
template and a catalogue row belongs to whoever owns those files, so it lives
in a directory of its own rather than in somebody else's (`CLAUDE.md` rule 6).

### WHAT THIS ASSERTS, AND WHY IT IS TWO INSTRUMENTS AND NOT ONE

`CLAUDE.md` rule 10's third disguise is a guard whose fixture cannot produce
the condition: a template invariant that passes because nothing withheld ever
reaches it. So the first test **fetches a real route** and asserts, before it
looks at any markup, that the service actually withheld the row — if a later
change makes `unverified_book` verified, or routes `/sell/find-book` through a
reader, this fails on that assertion by name instead of quietly passing on a
page with a title in it.

`GET /sell/find-book?isbn=` is the surface chosen because it is the one that
is **always** withheld. A-30 ruled that a catalogue-identity read passes no
reader, so an unverified row is withheld there even from the student who typed
it — which makes the condition reachable with one request and no second
account, and makes this the common journey rather than an edge case.

Both sides of the split are rows (`CLAUDE.md` rule 10's corollary): the
verified `book` fixture on the same route must show its title and **must not**
show the sentence. A test that only checked the withheld side would pass on a
template that printed the disclosure unconditionally.

The second test renders `listing.html` directly, because the property it
asserts — *what the `<h1>` contains* — is a property of the template and not
of a route. `/listing/{id}` is `get_own_listing` only in S2, so reaching it
with a withheld row needs a listing whose owner is not the book's author,
which needs a second ACTIVE seller with consents and seller terms. **Stated
rather than skipped:** the route-level walk of that page waits for the slice
that gives a buyer a URL, and until then the heading rule is measured on the
template, which is where it is written.
"""

import pytest
from django.template.loader import render_to_string
from django.test import Client

from apps.catalog.services import served_book_text
from apps.accounts.sessions import SESSION_USER_KEY

pytestmark = pytest.mark.django_db

#: The shipped sentence, read from the catalogue rather than retyped, so this
#: file cannot drift from `locale/en` (`CLAUDE.md` rule 11). `django.po` is
#: never compiled in this project, so gettext falls through to the msgid and
#: the msgid is what a student is served.
SENTENCE = (
    "A student typed this entry and no BookHop staff member has read it, "
    "so BookHop isn't repeating their words here. The ISBN identifies the "
    "edition."
)


def _signed_in(user):
    client = Client()
    session = client.session
    session[SESSION_USER_KEY] = user.id
    session.save()
    return client


def test_the_catalogue_sentence_is_reached_on_a_really_withheld_row(seller, unverified_book):
    """The withheld side, through a real request, with the condition asserted.

    `seller` is the same row as `student`, so this student is the book's
    author — and A-30 says an identity read is neutral even for them. That is
    asserted here as the precondition rather than assumed, because it is the
    whole reason one request is enough.
    """
    # THE CONDITION, FIRST. If this stops being true the test fails here,
    # naming the gate, rather than further down naming the markup.
    text = served_book_text(unverified_book, None)
    assert text["withheld"] is True, (
        "the fixture no longer produces a withheld row, so everything below "
        "this line would pass vacuously"
    )

    body = _signed_in(seller).get(
        "/sell/find-book", {"isbn": unverified_book.isbn13}
    ).content.decode()

    assert SENTENCE in body, (
        "`withheld` is published to the template and the sentence is in both "
        "catalogues, but the student is still shown a bare identifier"
    )
    # The seller's own words are not on the page. `title_norm` is not
    # rendered anywhere, so the raw title is the thing to look for.
    assert unverified_book.title not in body
    assert unverified_book.publisher is None or unverified_book.publisher not in body
    assert f"ISBN {unverified_book.isbn13}" in body, "the identity half of A-29 §1"

    # READING ORDER: identity, then why there is nothing else. Asserted as
    # byte positions because that is what both a screen reader and a sighted
    # reader follow on this page.
    assert body.index(f"ISBN {unverified_book.isbn13}") < body.index(SENTENCE)


def test_a_verified_row_shows_its_title_and_not_the_sentence(seller, book):
    """The other side of the split, on the same route.

    Without this, a template that printed the disclosure on every book would
    pass the test above.
    """
    assert served_book_text(book, None)["withheld"] is False

    body = _signed_in(seller).get(
        "/sell/find-book", {"isbn": book.isbn13}
    ).content.decode()

    assert book.title in body
    assert SENTENCE not in body


@pytest.mark.parametrize("withheld", [True, False])
def test_the_listing_heading_holds_the_identity_and_never_the_disclosure(withheld):
    """`listing.html`'s `<h1>` is a navigation target, so it stays short.

    A screen-reader user arrives at this heading out of a heading list with no
    surrounding context. It carries `ISBN 9789387432147` — a true identity for
    the edition, usable as a heading and as the browser tab's title — and the
    disclosure follows it as prose. The parametrisation keeps both sides rows:
    on a verified row the heading holds the title and the page holds no
    disclosure at all.
    """
    isbn = "9789387432147"
    title = f"ISBN {isbn}" if withheld else "Higher Engineering Mathematics"
    html = render_to_string(
        "listing.html",
        {
            "row": {
                "status": "LIVE",
                "price": "280",
                "book": {
                    "title": title,
                    "authors": "",
                    "isbn": isbn,
                    "withheld": withheld,
                },
            }
        },
    )

    heading = html.split("<h1 class=\"biblio\">", 1)[1].split("</h1>", 1)[0]
    assert heading.strip() == title
    assert SENTENCE not in heading, (
        "the disclosure must not be inside the heading: it would make the "
        "heading list and the browser tab unreadable"
    )
    if withheld:
        assert SENTENCE in html
        assert html.index("</h1>") < html.index(SENTENCE), "identity first"
    else:
        assert SENTENCE not in html
