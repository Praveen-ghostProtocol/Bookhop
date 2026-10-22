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


def test_staff_verification_stamps_the_timestamp(staff, unverified_book):
    """J2-staff step 7. Without this the column is one nothing can ever set,
    and after A-29 the row's text reaches nobody and its listings reach no
    buyer — so this is the only exit from both."""
    assert unverified_book.staff_verified_at is None
    services.verify_book(staff, unverified_book)
    unverified_book.refresh_from_db()
    assert unverified_book.staff_verified_at is not None


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
# reached only the seller's own listings. API-CONTRACT A-28 is the settled
# ruling: `addressed` applies; `dialable` and `linked` do not.
#
# **Both sides are rows** (`CLAUDE.md` rule 10's corollary), and after A-28
# the permitted side is by far the larger one: every digit run in catalogue
# text is accepted, a phone number and a `wa.me` link included. A table that
# only listed refusals would pass with the exemptions silently removed — and
# would also read as covering what A-28 handed to the review queue.


def _create(student, **over):
    """`create_book` with one field replaced. No ISBN — `isbn13` is NULL
    UNIQUE, so the accepted rows do not need thirteen made-up digits each."""
    fields = {"title": "Engineering Mathematics", "authors": ["B S Grewal"]}
    fields.update(over)
    return services.create_book(student, **fields)


#: Real catalogue text, stored as typed. **There is no text rule on these
#: four fields at all after A-29 §3** — not a narrowed one and not an empty
#: tuple — so this list is no longer the accepted side of a split. It is kept,
#: and the rows that broke A-26, A-27 and A-28 are kept with it, because each
#: one is a string a student holding a real book will type, and the next
#: person tempted to add a filter here should have to make them go red first.
#:
#: The three rulings and what refused them, for exactly that reason:
#:   * A-26 refused `A History of India 1707-1947` as a phone number;
#:   * A-27 refused `Journal 2019 2020 2021` — twelve digits, three groups,
#:     structurally identical to `+91 98400 12345`;
#:   * A-28 refused `@War: The Rise of the Military-Internet Complex`, a
#:     published title, on the one limb it had kept.
REAL_CATALOGUE_TEXT = [
    ("title", "Physics/Chemistry Combined", "a slash between two subjects"),
    ("title", "Maths I/II", "roman numerals around a slash"),
    ("title", "Advanced Microeconomics & Public Policy", "an ampersand"),
    ("title", "NCERT Class 12 Physics Part I", "digits that are a class, not a number"),
    ("title", "Engineering Mathematics — Volume 2", "an em dash and a volume number"),
    ("publisher", "S. Chand & Co.", "initials, an ampersand and a full stop"),
    ("publisher", "Tata McGraw-Hill", "a hyphen inside a name"),
    ("edition_label", "3rd ed., 2019 reprint", "a year is four digits"),
    ("edition_label", "Vol. I/II", "a slash in an edition label"),
    ("authors", ["H. K. Dass", "Dr. R. S. Aggarwal"], "initials and titles"),
    ("title", "A History of India 1707-1947", "A-26: eight digits across one hyphen"),
    ("publisher", "Cambridge 2020-2021", "a two-year range in a publisher line"),
    ("edition_label", "2019-2020 reprint", "a reprint spanning two academic years"),
    ("edition_label", "Vol. 1-2, 1998-2002", "two runs, four digits and eight"),
    ("title", "Maths I/II 2021-2022", "a slash and a year range in one title"),
    ("authors", ["Nilakanta Sastri 1892-1975"], "an author's dates, as a catalogue prints them"),
    ("title", "Tamil Nadu Gazetteer Vol. 1 (1901-1911)", "nine digits in one joined run"),
    ("title", "Journal 2019 2020 2021", "A-27: twelve digits in three groups"),
    ("title", "Collected Works 1 2 3 4 5 6 7 8 9 10", "eleven digits in ten groups"),
    ("title", "Engineering Mathematics 9788177589139", "an ISBN-13 in the title: misfiled, not refused"),
    ("title", "@War: The Rise of the Military-Internet Complex", "A-28: a published title the kept limb refused"),
    ("title", "Love@First Site", "an `@` inside a title, between two words"),
    ("title", "Chat@Work", "and with no space at all"),
    # The channels themselves. **Accepted into the row and withheld on the
    # way out** — which is A-29's whole move, and `test_served_book_text_*`
    # below is the half that makes accepting them safe. A row that refused
    # them would be a text rule again.
    ("title", "Discrete Maths t.me/priya", "a link in a title"),
    ("title", "Grewal 98400 12345", "a bare mobile"),
    ("title", "Grewal wa.me/919840012345", "a WhatsApp link"),
    ("title", "Grewal priya.r@gmail.com", "an email address"),
    ("authors", ["B S Grewal", "notes @priya_r"], "a handle in authors[1]"),
]


@pytest.mark.parametrize("field,value,why", REAL_CATALOGUE_TEXT)
def test_real_catalogue_text_is_accepted(student, field, value, why):
    book = _create(student, **{field: value})
    assert getattr(book, field) == value, why


def test_the_authors_list_check_still_stands(student):
    """A-26: *"each element is checked, and the list-ness check stays — one
    does not replace the other."* A string is iterable, so a per-element
    check that replaced the type check would validate `"Grewal"` one
    character at a time and store a row with 6 authors."""
    with pytest.raises(ValidationFailed) as caught:
        _create(student, authors="B S Grewal")
    assert "authors" in caught.value.context["field_errors"]


def test_a_misspelled_limb_name_raises_rather_than_guarding_nothing():
    """Rule 10: the subset is passed by name, so a typo must be loud. A
    `kinds` that silently matched nothing would be a guard reported as
    coverage while refusing nothing at all."""
    from apps.core.contact import contact_channels_in

    with pytest.raises(KeyError):
        contact_channels_in("98400 12345", ("dialble",))

# --- A-29 §1: the gate on seller-written text ------------------------------
#
# Four rulings tried to filter this text. The defect was never textual, so
# none of these tests is about a shape: they are about **who is served the
# strings**, and both sides of the split are rows (rule 10's corollary).


def test_an_unverified_row_is_withheld_from_another_student(unverified_book, pending_student):
    """A-29 §1: *"every other reader is served the ISBN and a neutral label;
    never the unverified strings."*

    The row was written by `student`; `pending_student` is somebody else —
    any other student, which is every reader the product has. Asserted
    per field rather than on the dict as a whole, so a field added to
    `SELLER_WRITTEN_TEXT` and forgotten in `served_book_text` fails by name.
    """
    text = services.served_book_text(unverified_book, pending_student)
    assert text["withheld"] is True
    for field in services.SELLER_WRITTEN_TEXT:
        assert not text[field], f"{field} reached a reader who is not its author"


def test_an_unverified_row_is_served_to_its_own_author(unverified_book, student):
    """The other side. A seller shown a label in place of words they typed a
    minute ago reads it as the write having failed."""
    text = services.served_book_text(unverified_book, student)
    assert text["withheld"] is False
    assert text["title"] == unverified_book.title
    assert text["authors"] == list(unverified_book.authors)


def test_an_unverified_row_is_served_to_staff(unverified_book, staff):
    """**The clause the whole review step depends on.** A reviewer served the
    neutral label is a reviewer who cannot review, which is the hole QA
    measured on `authors`: a field shown to no reviewer at all."""
    assert services.served_book_text(unverified_book, staff)["withheld"] is False


def test_a_verified_row_is_served_to_a_stranger(book, pending_student):
    """And the gate opens. A test that only asserted withholding would pass
    with the strings withheld from everybody for ever."""
    text = services.served_book_text(book, pending_student)
    assert text["withheld"] is False
    assert text["title"] == book.title


def test_a_catalogue_identity_read_passes_no_reader_and_is_neutral(unverified_book):
    """**The declared narrowing of A-29 §1, asserted as a narrowing.**

    `/sell/find-book?isbn=` and `GET /api/v1/books?isbn=` reach the row by
    ISBN over a record nobody owns, so they pass no reader and are neutral
    *even for the author*. A-29 §1 read literally would serve the author
    their own strings here; QA's
    `test_a_poisoned_catalogue_row_reaches_a_student_without_any_listing`
    signs the author in to that exact page and requires the opposite. This
    test pins which way it was resolved so the escalation cannot be read as
    an accident.
    """
    assert services.served_book_text(unverified_book)["withheld"] is True


def test_every_seller_written_column_on_books_is_behind_the_gate():
    """**A guard for the gate** (rule 10's corollary, and rule 11's).

    The gate is a named list of four columns, so the failure mode is a fifth
    seller-written column shipping without it. This asks the model rather
    than re-reading `SELLER_WRITTEN_TEXT`: every text-ish field on `Book` is
    either gated or in a declared exempt set with a reason, and a new column
    belongs to one of the two by hand.
    """
    from apps.catalog.models import Book

    #: Why each ungated text-ish column is not seller-written free text.
    exempt = {
        "isbn13": "thirteen checksummed digits: an identifier, not prose",
        "title_norm": "derived from `title` by `normalise_title`, never typed",
        "language": "an enum, refused outside DATA-MODEL §3's set",
        "origin_country": "a two-letter code",
    }
    textish = {
        f.name
        for f in Book._meta.get_fields()
        if getattr(f, "get_internal_type", None)
        and f.get_internal_type() in ("CharField", "TextField", "JSONField")
    }
    # **The instrument asserts its own reach** (rule 10's fourth disguise). An
    # introspection that returned nothing would pass this test while covering
    # no column at all.
    assert textish >= set(services.SELLER_WRITTEN_TEXT) | set(exempt), (
        f"the model introspection reached only {sorted(textish)}, which does "
        "not include every column this test reasons about — so a clean run "
        "means nothing"
    )
    ungated = textish - set(services.SELLER_WRITTEN_TEXT) - set(exempt)
    assert not ungated, (
        f"{sorted(ungated)} are text columns on `books` that A-29 §1's gate "
        "does not cover and that nothing here declares a reason for. `books` "
        "is global, so anything a seller writes into one of them renders on "
        "every listing of that ISBN. Add it to `SELLER_WRITTEN_TEXT`, or to "
        "`exempt` above with the reason it is not free text."
    )


def test_the_catalogue_limb_mechanism_is_gone_rather_than_emptied(unverified_book):
    """A-29 §3: *"deleted, not emptied — an empty tuple invites the next
    person to put a limb back."*

    Fails by name in both directions: the mechanism coming back, and the gate
    that replaced it being absent. Rule 12's *"name the other layer"* is
    discharged by the second assertion and not by a sentence.
    """
    for gone in ("CATALOGUE_CHANNEL_KINDS", "_CATALOGUE_REFUSAL", "_refuse_contact_channel"):
        assert not hasattr(services, gone), (
            f"apps.catalog.services.{gone} is back. A-29 deleted the text "
            "rule on catalogue text because the defect was never textual — "
            "a slur or a sentence about a lecturer fits through the same "
            "hole and no contact rule catches either. The layer is "
            "`served_book_text`."
        )
    assert services.served_book_text(unverified_book)["withheld"] is True, (
        "the limb mechanism is gone and the gate that replaced it is not "
        "withholding anything, which is a widening and not a clarification"
    )
