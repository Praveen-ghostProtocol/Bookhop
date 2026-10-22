"""`apps.catalog` — the edition lock. DATA-MODEL §3, JOURNEYS J2 steps 2–3.

The ISBN is the whole wedge: *"a syllabus-to-shelf matching layer for
**edition-locked** prescribed textbooks on one campus"*. A buyer who needs the
3rd edition and receives the 2nd has had the product fail at the only thing it
claims to do, so the checksum is a refusal and not a warning.
"""

import pytest

from apps.catalog import services
from apps.core.errors import DuplicateIsbn, NotPermitted, ValidationFailed

pytestmark = pytest.mark.django_db


# --- the checksum: rule 12's shape, on the catalogue ----------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("9788177589139", "9788177589139"),
        ("978-81-7758-913-9", "9788177589139"),
        ("978 81 7758 913 9", "9788177589139"),
        ("  9788177589139  ", "9788177589139"),
        # An en dash and a non-breaking hyphen, which a student pasting from a
        # PDF reading list actually produces. A list of "hyphen characters"
        # could never have all of them; the normaliser takes the Unicode dash
        # range.
        ("978‑81‑7758‑913‑9", "9788177589139"),
    ],
)
def test_an_isbn_is_normalised_before_it_is_compared(raw, expected):
    """One definition, so `978-81-…` and `97881…` are the same book.

    Without this the edition lock is defeated by punctuation: two `books`
    rows, two sets of listings, and a buyer who searched one spelling never
    sees the other's copies.
    """
    assert services.validate_isbn13(raw) == expected


@pytest.mark.parametrize(
    "bad,why",
    [
        ("9788177589130", "the check digit is wrong by nine"),
        ("9788177589131", "the check digit is wrong by eight"),
        ("978817758913", "twelve digits"),
        ("97881775891390", "fourteen digits"),
        ("978817758913X", "a letter where the check digit goes"),
        ("", "empty"),
        (None, "absent"),
    ],
)
def test_a_bad_checksum_is_refused_rather_than_stored(bad, why):
    """**`CLAUDE.md` rule 12 on the catalogue.** A length CHECK proves the
    stored *state* — thirteen characters — and proves nothing about whether
    any of them is right. The mod-10 checksum has no portable SQL expression,
    so detection lives above the schema and the test passes a bad **input**
    rather than inspecting a column type."""
    with pytest.raises(ValidationFailed):
        services.validate_isbn13(bad)


def test_a_ten_digit_isbn_is_refused_rather_than_converted():
    """JOURNEYS J2 step 2's *"check the digits"*, and the refusal is deliberate.

    A 10-digit ISBN converts to a 13-digit one mechanically, and converting it
    silently would mean the number we matched is not the number on the book
    the student is holding. **A wrong edition is the one failure this product
    cannot afford**, so the student is told which number to use.
    """
    with pytest.raises(ValidationFailed, match="10-digit"):
        services.validate_isbn13("8177589130")


# --- title normalisation: the invariant, not a punctuation list -----------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Engineering Mathematics", "engineering mathematics"),
        ("ENGINEERING  MATHEMATICS", "engineering mathematics"),
        ("Engineering Mathematics, 44th ed.", "engineering mathematics 44th ed"),
        ("Higher—Engineering", "higher engineering"),
        ("கணிதம்", "கணிதம்"),
        # A zero-width space and a byte-order mark: **format** characters, so
        # they survive a strip and render as nothing. A whitespace list could
        # never catch them; `unicodedata.category` can.
        ("Engineering​Mathematics", "engineeringmathematics"),
        ("﻿Engineering", "engineering"),
    ],
)
def test_title_normalisation_asks_unicode_rather_than_consulting_a_list(raw, expected):
    assert services.normalise_title(raw) == expected


# --- create, duplicate, merge ---------------------------------------------


def test_a_student_may_create_a_book_and_it_is_not_staff_verified(student, book):
    """DATA-MODEL §3: *"a student may create a `books` row; that row is
    flagged for staff verification"* — by the **absence** of
    `staff_verified_at`, not by a second boolean that could disagree with it.
    """
    created = services.create_book(
        student, isbn13="9780131103627", title="The C Programming Language",
        authors=["Kernighan", "Ritchie"], language="en",
    )
    assert created.staff_verified_at is None
    assert created.is_staff_verified is False
    assert created.created_by_id == student.id
    assert created.title_norm == "the c programming language"


def test_a_duplicate_isbn_is_refused_with_the_existing_book_id(student, book):
    """API-CONTRACT §3 names `DuplicateIsbn`. The id is carried so the client
    can send the student back to J2 step 2's *"is this the one?"* rather than
    to an error page."""
    with pytest.raises(DuplicateIsbn) as caught:
        services.create_book(student, isbn13=book.isbn13, title="Something else")
    assert caught.value.context["book_id"] == book.id
    assert caught.value.http_status == 409


def test_a_merged_book_still_resolves_so_its_listings_still_load(staff, student, book):
    """J2-staff step 6 and EC-7: *"no row is deleted — listings point at it,
    and a listing on a merged book still loads."*"""
    duplicate = services.create_book(
        student, isbn13="9780131103627", title="Engineering Mathematics (dup)"
    )
    services.merge_books(staff, duplicate, book)
    duplicate.refresh_from_db()
    assert duplicate.merged_into_id == book.id
    assert services.find_book_by_isbn("9780131103627").id == book.id


def test_a_merge_cycle_is_refused_rather_than_looping(staff, student, book):
    """A→B then B→A is one careless staff action away, and an unbounded
    follow is an infinite loop inside a request."""
    duplicate = services.create_book(student, isbn13="9780131103627", title="dup")
    services.merge_books(staff, duplicate, book)
    with pytest.raises(ValidationFailed, match="cycle"):
        services.merge_books(staff, book, duplicate)


def test_only_staff_may_merge_or_verify(student, book):
    other = services.create_book(student, isbn13="9780131103627", title="dup")
    with pytest.raises(NotPermitted):
        services.merge_books(student, other, book)
    with pytest.raises(NotPermitted):
        services.verify_book(student, book)


def test_staff_verification_stamps_the_timestamp(staff, book):
    """J2-staff step 7. Without this the column is one nothing can ever set,
    and `publish_listing`'s unverified-book branch has no exit."""
    assert book.staff_verified_at is None
    services.verify_book(staff, book)
    book.refresh_from_db()
    assert book.staff_verified_at is not None


# --- search: the engine difference, labelled -------------------------------


def test_search_finds_an_exact_title_on_both_engines(book):
    assert book in services.search_books("engineering mathematics")
    assert book in services.search_books("Engineering")


def test_search_excludes_a_merged_row(staff, student, book):
    duplicate = services.create_book(
        student, isbn13="9780131103627", title="Engineering Mathematics copy"
    )
    services.merge_books(staff, duplicate, book)
    assert duplicate not in services.search_books("engineering mathematics")


def test_a_misspelling_is_found_on_postgres_and_not_on_sqlite(engine, book):
    """**The engine difference, measured rather than predicted.**

    `CLAUDE.md` rule 9: a cross-engine claim is labelled. **VERIFIED HERE on
    PostgreSQL** — `pg_trgm`'s `similarity()` matches a one-character typo
    above the 0.3 cut-off. **VERIFIED HERE on SQLite** — there is no `pg_trgm`
    and the substring match finds nothing, so the contract any caller above
    may rely on is the weaker one.

    This is a skip on neither engine: both branches assert, because *"a
    misspelling finds nothing on SQLite"* is a property worth pinning. A
    developer who writes S3's ranking against a local green run would
    otherwise assume fuzziness that production has and the tests never showed.
    """
    hits = services.search_books("enginering mathematics")
    if engine == "postgresql":
        assert book in hits, (
            "pg_trgm similarity did not match a one-character typo; either the "
            "extension or the GIN index from catalog/0002 is missing"
        )
    else:
        assert hits == [], (
            "SQLite has no pg_trgm, so a misspelling must find nothing — if it "
            "found something, search_books is not doing what this test records"
        )


def test_an_empty_query_returns_nothing_rather_than_everything(book):
    """A blank search that returned the whole catalogue would be the scraping
    surface `THREAT-MODEL.md` §5.6 is about, reached by pressing enter."""
    assert services.search_books("") == []
    assert services.search_books("   ") == []
    assert services.search_books(None) == []


# --- prescribed texts: R-01's measurement ----------------------------------


def test_a_reading_list_is_scoped_to_its_campus(book, signup_campus, closed_campus, staff):
    """Tenant-scoped, so a course code on one campus does not resolve on
    another. R-01's test seeds one department's list; this is the property
    that makes a second campus's list a different answer."""
    from apps.catalog.models import PrescribedText

    PrescribedText.objects.create(
        campus=signup_campus, city_id=signup_campus.city_id,
        course_code="MA8151", course_title="Engineering Mathematics I",
        term_label="2026-ODD", book=book, source="DEPT_CONFIRMED",
        added_by=staff,
    )
    assert len(services.prescribed_for_course(signup_campus, "MA8151")) == 1
    assert services.prescribed_for_course(closed_campus, "MA8151") == []
    # Case and whitespace are normalised, because a student types what is on
    # the timetable and a reading list is typed by staff.
    assert len(services.prescribed_for_course(signup_campus, " ma8151 ")) == 1


# --- A-26: catalogue text is not a contact channel -------------------------
#
# Backend found this writing F49's boundary sweep and escalated rather than
# chose: `create_book` validated `title` for non-empty, `authors` for being a
# list, and `publisher` and `edition_label` not at all, so
# `"Engineering Mathematics wa.me/919840012345"` became a channel on **every**
# listing of that ISBN — `books` is global, so this is wider than F49, which
# reached only the seller's own listings. API-CONTRACT A-26 is the ruling:
# `dialable` and `addressed` apply; `linked` does not.
#
# **Both sides are rows** (`CLAUDE.md` rule 10's corollary). The permitted
# side is the expensive one to get wrong: `linked` is exempt precisely
# because real titles contain slashes, and a table that only listed refusals
# would pass with the exemption silently removed.


def _create(student, **over):
    """`create_book` with one field replaced. No ISBN — `isbn13` is NULL
    UNIQUE, so the accepted rows do not need thirteen made-up digits each."""
    fields = {"title": "Engineering Mathematics", "authors": ["B S Grewal"]}
    fields.update(over)
    return services.create_book(student, **fields)


@pytest.mark.parametrize(
    "field,value,why",
    [
        ("title", "Physics/Chemistry Combined", "the title A-26 exempts `linked` for"),
        ("title", "Maths I/II", "roman numerals around a slash"),
        ("title", "Advanced Microeconomics & Public Policy", "an ampersand"),
        ("title", "NCERT Class 12 Physics Part I", "digits that are a class, not a number"),
        ("title", "Engineering Mathematics — Volume 2", "an em dash and a volume number"),
        ("publisher", "S. Chand & Co.", "initials, an ampersand and a full stop"),
        ("publisher", "Tata McGraw-Hill", "a hyphen inside a name"),
        ("edition_label", "3rd ed., 2019 reprint", "a year is four digits"),
        ("edition_label", "Vol. I/II", "a slash in an edition label"),
        ("authors", ["H. K. Dass", "Dr. R. S. Aggarwal"], "initials and titles"),
        # The declared gap, asserted as a gap so the suite cannot be read as
        # covering it. `apps/core/contact.py` lists it; A-26 names the review
        # queue as the layer that catches it, and the test below pins the
        # flag that queue depends on.
        ("title", "Discrete Maths t.me/priya", "`linked` is exempt — the review queue catches this"),
    ],
)
def test_real_catalogue_text_is_accepted(student, field, value, why):
    book = _create(student, **{field: value})
    assert getattr(book, field) == value, why


CHANNELS_THAT_MUST_BE_REFUSED = [
    ("98400 12345", "dialable", "a mobile number with a space in it"),
    ("priya.r@gmail.com", "addressed", "an email address"),
    ("wa.me/919840012345", "dialable", "a WhatsApp link — caught by its digits, not by `linked`"),
]


@pytest.mark.parametrize("channel,kind,why", CHANNELS_THAT_MUST_BE_REFUSED)
@pytest.mark.parametrize("field", ["title", "authors", "publisher", "edition_label"])
def test_a_contact_channel_in_catalogue_text_is_refused(student, field, channel, kind, why):
    """All four fields, because all four render on every listing of the ISBN.

    `authors` is a **list**, and it is the second element that carries the
    channel — a per-element check, not a check of the list's first entry.
    """
    from apps.catalog.models import Book

    before = Book.objects.count()
    value = ["B S Grewal", f"B S Grewal {channel}"] if field == "authors" else f"Grewal {channel}"
    with pytest.raises(ValidationFailed) as caught:
        _create(student, **{field: value})
    # The *kind* is asserted, not merely the refusal: `wa.me/91…` must be
    # refused by `dialable`, because `linked` is exempt here and a test that
    # only asserted "refused" would still pass if the exemption were dropped
    # and then re-dropped for the wrong reason.
    assert kind in caught.value.context["detail"], why
    assert field in caught.value.context["field_errors"]
    assert Book.objects.count() == before, "refused before the row exists"


def test_the_authors_list_check_still_stands(student):
    """A-26: *"each element is checked, and the list-ness check stays — one
    does not replace the other."* A string is iterable, so a per-element
    check that replaced the type check would validate `"Grewal"` one
    character at a time and store a row with 6 authors."""
    with pytest.raises(ValidationFailed) as caught:
        _create(student, authors="B S Grewal")
    assert "authors" in caught.value.context["field_errors"]


def test_the_catalogue_applies_the_limbs_a26_ruled_and_no_others():
    """The exemption is a *named* limb, not an accident of a short tuple.

    This fails by name in three directions: a limb added to
    `apps/core/contact.py` without an A-26 ruling, `linked` quietly added
    here, and `linked` deleted from the shared definition — which would leave
    the exemption above describing something that no longer exists.
    """
    from apps.core.contact import CHANNEL_KINDS

    assert set(services.CATALOGUE_CHANNEL_KINDS) == set(CHANNEL_KINDS) - {"linked"}


def test_a_misspelled_limb_name_raises_rather_than_guarding_nothing():
    """Rule 10: the subset is passed by name, so a typo must be loud. A
    `kinds` that silently matched nothing would be a guard reported as
    coverage while refusing nothing at all."""
    from apps.core.contact import contact_channels_in

    with pytest.raises(KeyError):
        contact_channels_in("98400 12345", ("dialble",))


def test_the_linked_exemption_rests_on_a_flag_that_is_still_true():
    """**The guard for the conditional exemption** — it fails, it does not skip.

    A-26 exempts `linked` from catalogue text because real titles contain
    slashes. Rule 12 required naming the layer that still catches
    `t.me/priya` in a title, and that layer is the human review queue: at
    pilot `LISTING_REVIEW_ALL=true`, every listing stops at `PENDING_REVIEW`
    and the moderator is shown the title, edition and publisher (F50).

    So the exemption is **conditional on a flag**, and rule 10's fifth
    disguise says what a conditional check must not be: forward-dated, or
    skipped, both of which are indistinguishable from passing trivially.
    Inverted — this asserts the condition the exemption rests on, and goes
    red in the same diff as the one-line change that removes it.

    Asserted against `bookhop.settings.base`, the **default**, not
    `django.conf.settings`, which any test may override for a scenario.
    """
    from bookhop.settings import base

    assert base.LISTING_REVIEW_ALL is True, (
        "LISTING_REVIEW_ALL has been flipped off, and that removes the only "
        "layer standing behind API-CONTRACT A-26's `linked` exemption: "
        "`t.me/priya` in a book title is accepted by `create_book` and "
        "renders on every listing of that ISBN, with no moderator between "
        "the seller and the buyer. Before this ships, either extend `linked` "
        "to the catalogue fields in apps/catalog/services.CATALOGUE_CHANNEL_KINDS "
        "(and accept that it refuses `Physics/Chemistry Combined`, which is "
        "why A-26 did not), or put a second layer in front of the queue and "
        "amend A-26 to name it. This is a contract amendment, not a test fix."
    )
