r"""A-28 attacked: the limb that was kept, and the layer that was named.

A-28 exempts `dialable` and `linked` from `title`, `authors`, `publisher`
and `edition_label`, keeps `addressed`, and discharges `CLAUDE.md` rule 12 by
naming one other layer:

> The human review queue: at pilot `LISTING_REVIEW_ALL=true` stops every
> listing, and after F50 the reviewer is shown the title, the publisher and
> the edition.

Rule 12 is explicit that naming the layer is the condition of the exemption —
*"if none does, it is a widening, not a clarification"* — and `CLAUDE.md`
rule 9 is explicit that a document's claim is not evidence. So this file does
two things no previous test in the tree does:

1. **Asks the kept limb rule 13's question**, which A-27 records as the
   failure mode of A-26 — *"asking the question once and treating it as asked
   is its own failure mode"*. A-28 asks it of `dialable` and `linked` and
   asserts of `addressed` that it *"never fired on anything real"*. That is a
   claim about the world and it is measured here.
2. **Measures the named layer at the boundary the document claims**
   (rule 9): does a contact channel in each exempted field actually reach a
   moderator who can see it?

These tests are written from `API-CONTRACT.md` A-26/A-27/A-28 and
`CLAUDE.md` rules 9, 12 and 13. They are not written from
`apps/catalog/services.py`.
"""

import pytest
from django.core.management import call_command

from apps.catalog.services import create_book
from apps.core.errors import ValidationFailed

pytestmark = pytest.mark.django_db

#: A channel of the shape A-28 exempted: eleven digits and a path separator,
#: no `@`. Both `dialable` and `linked` would catch it; neither applies to
#: catalogue text any more, so the review queue is the whole defence.
CHANNEL = "wa.me/919840012345"


def _sign_in(user):
    from django.test import Client

    from apps.accounts.sessions import SESSION_USER_KEY

    client = Client()
    session = client.session
    session[SESSION_USER_KEY] = user.id
    session.save()
    return client


def _pending_listing(seller, book):
    """A listing of `book` sitting where the moderator will find it."""
    from apps.listings.services import create_listing, publish_listing

    listing = create_listing(
        seller, book=book, asking_price_paise=30000, condition="GOOD",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    return publish_listing(seller, listing, listing.version)


# --- 1 · the limb that was kept ---------------------------------------------


def test_the_kept_limb_does_not_fire_on_a_real_published_title(student):
    """A-28: *"`addressed` … is the limb that never fired on anything real."*

    `@War` is a published book — Shane Harris, 2014, on the militarisation of
    the internet — and its title begins with an `@` immediately followed by a
    non-space, which is `_addressed`'s entire rule. **I cannot check an ISBN
    from this machine**, so the measurement this test makes is the narrower
    and sufficient one: a title of this *shape* is refused, and titles of this
    shape exist in print.

    This is the same failure A-27 recorded against A-26 and A-28 recorded
    against A-27, on the third limb: `create_book` (J2 step 2) is the **only**
    path for a book not already in the catalogue, so a student holding this
    book cannot list it, under a message telling them to enter what is printed
    on the book.

    Rule 13's first resort does not apply — the colliding name is an author's,
    not ours — so if this is to be fixed it is resort 2 again, and the
    narrowing is available and cheap: `_addressed` could require a `.` after
    the `@` run, or a non-leading `@`, neither of which `wa.me` or
    `priya@x.com` evades. **Not my call and not my file**; the measurement is.
    """
    title = "@War: The Rise of the Military-Internet Complex"
    try:
        book = create_book(
            student, isbn13="9780544251793", title=title,
            authors=["Shane Harris"], language="en",
        )
    except ValidationFailed as exc:
        pytest.fail(
            "A-28 states that `addressed` 'never fired on anything real'. It "
            f"fires on {title!r} — a title whose shape exists in print — and "
            f"the student is told: {str(exc)!r}. `create_book` is the only "
            "path for a book not in the catalogue, so there is no "
            "workaround. Rule 13's prediction: a red test on a real title "
            "and an edit to apps/core/contact.py under schedule pressure."
        )
    assert book.title == title, "the title was stored differently from the input"


def test_the_exempted_shapes_really_are_accepted_now(student):
    """The other side of the split (rule 10's corollary).

    A-26 and A-27 were each found by a title they refused. The three rows
    that broke them are rows here, so the accepted side of A-28 is covered by
    assertion rather than by reading.
    """
    for n, title in enumerate(
        (
            "A History of India 1707-1947",
            "Journal 2019 2020 2021",
            "Physics/Chemistry Combined",
            "Physics ISBN 978-93-5260-123-4",
            "Collected Works 1 2 3 4 5 6 7 8 9 10",
        )
    ):
        book = create_book(student, title=title, authors=["A N Other"], language="en")
        assert book.title == title, f"row {n}: stored title differs from the input"


# --- 2 · the layer that was named -------------------------------------------


def test_the_moderator_is_shown_the_authors_field_that_was_exempted(
    seller, staff, capsys
):
    """`authors` is exempted and the reviewer is never shown it.

    A-28 exempts four fields and names what the reviewer sees: *"the title,
    the publisher and the edition"*. `authors` is the fourth, and
    `create_book` checks it per element for exactly the reason A-26 gave —
    *"a channel in `authors[1]` renders exactly as widely as one in
    `title`"*. It renders on `/listing/{id}`, `/sell`, `/sell/find-book` and
    `/sell/{id}/photos`.

    So for one of the four exempted fields the named layer does not exist,
    and under rule 12 that makes the exemption a widening on that field.
    This test asserts the layer, not the absence: it puts the channel in
    `authors` and asks whether a moderator doing the J2-staff step 3 review
    can see it.
    """
    book = create_book(
        seller,
        isbn13="9788177589139",
        title="Engineering Mathematics",
        authors=["B S Grewal", f"notes {CHANNEL}"],
        publisher="Khanna",
        edition_label="44th edition",
        language="en",
    )
    listing = _pending_listing(seller, book)
    assert listing.status == "PENDING_REVIEW", (
        "the premise failed: LISTING_REVIEW_ALL is not stopping this listing, "
        f"so the named layer is not even reachable (status={listing.status})"
    )

    call_command("review_listings", "--staff", staff.email)
    call_command("review_listings", "--staff", staff.email, "--listing", str(listing.id))
    shown = capsys.readouterr().out

    assert CHANNEL in shown, (
        "the moderation queue never prints `authors`, so the contact channel "
        "A-28 exempted from `dialable` and `linked` on that field reaches no "
        "human at all. A-28 names the review queue as the layer that makes "
        "the exemption a clarification rather than a widening (rule 12), and "
        "for `authors` that layer does not exist. The whole reviewer-facing "
        f"output was:\n{shown}"
    )


def test_a_poisoned_catalogue_row_reaches_a_student_without_any_listing(
    seller, staff, capsys
):
    """The review queue reviews **listings**. `books` is global and live.

    `create_book` writes a row that `/sell/find-book` renders to any
    signed-in student the moment it exists — the view's own docstring says
    so: *"What this page may show is the catalogue."* No listing is required,
    so `LISTING_REVIEW_ALL` is not in the path, and the moderation queue is
    empty while the row is being served.

    This is the harder half of the rule-12 question. Even where the reviewer
    *is* shown the field, the layer only runs when somebody lists the book —
    and rejecting that listing does not unwrite the catalogue row, which
    `ADR-002` §2 makes global to every campus and every future listing of
    that ISBN.
    """
    book = create_book(
        seller,
        isbn13="9788177589139",
        title=f"Engineering Mathematics {CHANNEL}",
        authors=["B S Grewal"],
        language="en",
    )

    call_command("review_listings", "--staff", staff.email)
    queue = capsys.readouterr().out
    assert "Nothing is waiting for review." in queue, (
        f"premise failed: the queue is not empty, so this is not the "
        f"no-listing path. Queue said:\n{queue}"
    )

    page = _sign_in(seller).get("/sell/find-book", {"isbn": book.isbn13})
    assert page.status_code == 200, f"/sell/find-book returned {page.status_code}"
    body = page.content.decode()

    assert CHANNEL not in body, (
        "a contact channel typed into a catalogue title is being rendered to "
        "a signed-in student while the moderation queue — the layer A-28 "
        "names as the reason the exemption is not a widening — has nothing "
        "in it. The catalogue is not behind that layer: `books` rows are "
        "global (ADR-002 §2) and `/sell/find-book` serves them on creation. "
        "Rejecting a listing later does not unwrite the row."
    )
