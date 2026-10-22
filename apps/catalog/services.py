"""apps.catalog service layer (L1) — API-CONTRACT §3's `apps/catalog/services.py`.

Four frozen signatures: `find_book_by_isbn`, `search_books`, `create_book`,
`merge_books`. Everything else here is a helper those four need.

**`books` is global** (ADR-002 §2), so nothing here takes a campus or calls
`scoped()`, and that is deliberate rather than an omission: edition-locking
requires one row per edition across every campus. The *gate* applies to
listings, not to the catalogue — a student on a closed campus may look up an
ISBN and find nothing listed, which is S3's "we don't recognise that ISBN" vs
"not on your campus yet" distinction.

**A second gate does apply here, and it is A-29's.** `staff_verified_at` is a
condition on reading the four seller-written strings, not a decoration:
`served_book_text` is the only place that decision is made, and every read
path goes through it. Being global is exactly what made the catalogue a
publishing surface, so the gate is on the *text*, not on the row.

**That claim is now a test, because it was false twice** — F47-Q2 found
`/sell/find-book` and S2-R2-B1 found `book_requests` on two surfaces after
A-29 shipped, both times by someone reading the code rather than by anything
failing. `tests/unit/test_catalogue_text_gate_is_enforced.py` walks `apps/**`
and `web/**` for any read of a `SELLER_WRITTEN_TEXT` attribute outside this
gate and the two staff readers, so the next missed read path fails by name
with its file and line (`CLAUDE.md` rule 9: a document's claim is not
evidence).
"""

import logging
import re
import unicodedata

from django.db import IntegrityError, transaction

from apps.core.errors import DuplicateIsbn, NotFound, NotPermitted, ValidationFailed
from apps.core.services import record_audit

from .models import LANGUAGES, Book, PrescribedText

log = logging.getLogger(__name__)

__all__ = [
    "find_book_by_isbn",
    "search_books",
    "create_book",
    "merge_books",
    "normalise_isbn13",
    "validate_isbn13",
    "normalise_title",
    "prescribed_for_course",
    "served_book_text",
    "may_read_unverified_text",
    "SELLER_WRITTEN_TEXT",
]

#: Anything that is not a letter, a digit or a space, stripped from
#: `title_norm`. Built from Unicode categories rather than a punctuation list,
#: because a list cannot express a dash it has never seen (`CLAUDE.md`
#: rule 15) — an em dash, an ideographic comma and a Tamil full stop are all
#: punctuation and none of them would be in a hand-written list.
_COLLAPSE_SPACE = re.compile(r"\s+")

#: `pg_trgm`'s default `similarity()` cut-off is 0.3 and this matches it, so a
#: later switch to the indexed `%` operator does not change which rows match.
TRIGRAM_THRESHOLD = 0.3

#: **API-CONTRACT A-29 §1.** The columns on `books` a *seller* writes in free
#: text. The ISBN is not here — thirteen checksummed digits are an identifier,
#: not prose — and neither is `language`, `publication_year` or
#: `origin_country`, which are an enum and two bounded numbers.
#:
#: A-26, A-27 and A-28 each tried to filter these. The defect was never
#: textual: a seller writes into a **global** row (ADR-002 §2) that is served
#: to every buyer of that ISBN with no human in between, and a slur or a
#: sentence about a lecturer fits through that hole exactly as well as a phone
#: number. `served_book_text` below is the gate that closes it, and there is
#: **no text rule on catalogue text at all** — not an empty one (A-29 §3).
SELLER_WRITTEN_TEXT = ("title", "authors", "edition_label", "publisher")


def _withheld():
    """What a withheld row reads as. **Built per call, not a module constant**:
    `authors` has to be a list because the model's is (a reader doing
    `list(...)` over a `None` would crash on the unverified branch only, which
    is the branch nobody exercises by hand), and one shared list handed to
    every caller is one `append` away from a leak across requests.
    """
    return {"title": None, "authors": [], "edition_label": None, "publisher": None}


def may_read_unverified_text(book, reader) -> bool:
    """A-29 §1, asked as one property. Three clauses, one place.

    **Staff may read it** — that is what a review step is for, and
    `queue_rows` and `review_listings --listing` are the two readers that
    exist. **The book's own author may read it**, so a seller is never shown
    a label in place of words they typed. Everybody else is served the ISBN.
    """
    if getattr(book, "staff_verified_at", None) is not None:
        return True
    if getattr(reader, "is_staff_member", False):
        return True
    reader_id = getattr(reader, "id", None)
    return reader_id is not None and getattr(book, "created_by_id", None) == reader_id


def served_book_text(book, reader=None):
    """A-29 §1 — **the one decision**, asked once and read by every surface.

    Returns the four `SELLER_WRITTEN_TEXT` values as `reader` may be served
    them, plus `withheld`, so the four read paths route through this rather
    than each asking `staff_verified_at` their own way (`CLAUDE.md` rule 11).

    ### `reader` IS THE ACTOR THE ROW WAS REACHED *THROUGH*, AND THAT IS A
    ### NARROWING OF A-29 §1 THAT IS DECLARED HERE RATHER THAN ASSUMED

    A-29 §1 says the free text is *"served only to the actor who created
    it"*. A **catalogue-identity read** — `/sell/find-book?isbn=`,
    `GET /api/v1/books?isbn=` or `?q=` — reaches the row by ISBN or by title
    over a record nobody owns, so it passes no reader at all and is neutral
    **even for the student who typed the text**. A listing read passes the
    actor whose listing it is, and the staff surfaces pass the reviewer.
    Three callers, one rule, and the rule is about what the row was reached
    through rather than about which URL asked.

    **Measured, because it is the one place A-29 as written cannot hold:**
    `tests/contract/test_a28_the_layer_that_was_named.py::test_a_poisoned_catalogue_row_reaches_a_student_without_any_listing`
    creates the book **as the seller** and then signs that same seller in to
    `/sell/find-book`. Under A-29 §1 read literally the seller is the author
    and is served the raw string, and that test stays red. It is escalated in
    the slice note: either the exception is narrowed as it is here, or that
    test has to read as somebody else — and the second is QA's file, not
    mine.
    """
    if book is None:
        return {**_withheld(), "withheld": False}
    if may_read_unverified_text(book, reader):
        return {
            "title": book.title,
            "authors": list(book.authors or []),
            "edition_label": book.edition_label,
            "publisher": book.publisher,
            "withheld": False,
        }
    return {**_withheld(), "withheld": True}


def normalise_isbn13(raw):
    """Hyphens, spaces and case removed. Returns `''` for anything empty.

    One definition. The API, the service layer and the fixtures all compare
    ISBNs through this, so `978-81-7758-913-0` and `9788177589130` are the same
    book — which is the whole point of an edition lock.
    """
    if raw is None:
        return ""
    return re.sub(r"[\s\-‐-―−]", "", str(raw)).strip().upper()


def validate_isbn13(raw):
    """Return the canonical 13-digit ISBN, or raise `ValidationFailed`.

    The mod-10 checksum, which is the thing a length CHECK cannot do
    (`CLAUDE.md` rule 18): **a column proving thirteen characters does not
    prove any of them are right.** JOURNEYS J2 step 2 is explicit about the
    copy — *"that ISBN doesn't look right — check the digits"* — and the
    field is preserved, which is L3's half.

    Accepts only ISBN-13. A 10-digit ISBN is refused with a message saying so
    rather than silently converted: converting would hide from the student that
    the number on the book is not the number we matched, and a wrong edition is
    the one failure this product cannot afford.
    """
    digits = normalise_isbn13(raw)
    if not digits:
        raise ValidationFailed(
            "Enter the 13-digit ISBN from the back cover.",
            field_errors={"isbn13": ["Required."]},
        )
    if len(digits) == 10:
        raise ValidationFailed(
            "That is a 10-digit ISBN. Use the 13-digit one, which usually starts 978 or 979.",
            field_errors={"isbn13": ["13 digits, starting 978 or 979."]},
        )
    if len(digits) != 13 or not digits.isdigit():
        raise ValidationFailed(
            "That ISBN doesn't look right — check the digits.",
            field_errors={"isbn13": ["13 digits, starting 978 or 979."]},
        )
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    if (10 - total % 10) % 10 != int(digits[12]):
        raise ValidationFailed(
            "That ISBN doesn't look right — check the digits.",
            field_errors={"isbn13": ["The last digit does not match the rest."]},
        )
    return digits


def normalise_title(raw):
    """Lowercased, punctuation-stripped, whitespace-collapsed. DATA-MODEL §3.

    Asks Unicode per character rather than consulting a punctuation list, for
    the reason `CLAUDE.md` rule 15 gives: a list gains entries and can never
    have the one it has not met. `unicodedata.category` answers the property.
    """
    # **Combining marks are kept** (category `M*`). `str.isalnum()` is False
    # for a Tamil vowel sign, a Devanagari matra and every other combining
    # mark, so dropping non-alnum characters would turn `கணிதம்` into
    # `கணிதம` — a different word, silently, for every Indic title in the
    # catalogue. Found by the Tamil case in `test_catalog.py`, which is why
    # that case is in the table.
    #
    # Format characters (category `C*`) are dropped entirely rather than
    # replaced: a zero-width space inside a word is not a word break.
    folded = unicodedata.normalize("NFKC", str(raw or "")).casefold()
    kept = [
        ch if (ch.isalnum() or ch.isspace() or unicodedata.category(ch).startswith("M")) else " "
        for ch in folded
        if not unicodedata.category(ch).startswith("C")
    ]
    return _COLLAPSE_SPACE.sub(" ", "".join(kept)).strip()


def find_book_by_isbn(isbn13: str) -> "Book | None":
    """API-CONTRACT §3. Raises `IsbnInvalid` (→ `ValidationFailed`, 400).

    Follows `merged_into` so a listing created against a duplicate row that
    staff later merged still resolves to the surviving edition (J2-staff step 6
    and EC-7: *"no row is deleted — listings point at it"*).
    """
    digits = validate_isbn13(isbn13)
    book = Book.objects.filter(isbn13=digits).first()
    return resolve_merge(book)


def resolve_merge(book, _depth=0):
    """The surviving edition for `book`, following `merged_into`.

    Bounded, because a merge cycle (A→B, B→A) is one careless staff action away
    and an unbounded follow is an infinite loop in a request. Ten hops is far
    past anything real; past that the row is returned as-is and the cycle is
    logged, because refusing to show a listing is worse than showing it against
    a stale edition.
    """
    seen = set()
    while book is not None and book.merged_into_id is not None and len(seen) < 10:
        if book.merged_into_id in seen:
            log.warning("catalog.merge_cycle", extra={"book_id": book.id})
            return book
        seen.add(book.id)
        book = Book.objects.filter(id=book.merged_into_id).first()
    return book


def search_books(q: str, limit: int = 20):
    """API-CONTRACT §3. Title search over `title_norm`.

    **Engine-divergent and the difference is stated, not assumed**
    (`CLAUDE.md` rule 17, VERIFIED HERE on both engines by
    `tests/unit/test_catalog.py`):

      * on **PostgreSQL** this is a trigram similarity search over the
        `pg_trgm` GIN index migration `0002` creates, so a misspelling still
        matches;
      * on **SQLite** there is no `pg_trgm`, so it is a substring match over
        the plain index. A misspelling finds nothing.

    The *contract* either engine satisfies is the weaker one — substring — so
    nothing above this function may assume fuzziness. S3's ranking
    (`published_at DESC` within an exact-ISBN match, then trigram similarity)
    is where the difference becomes visible, and it is recorded there.
    """
    from django.db import connection
    from django.db.models import F, Func, Value
    from django.db.models.fields import FloatField

    needle = normalise_title(q)
    if not needle:
        return []
    limit = max(1, min(int(limit or 20), 50))
    base = Book.objects.filter(merged_into__isnull=True)
    if connection.vendor == "postgresql":
        # `similarity()` rather than the `%` operator, so this needs neither
        # `django.contrib.postgres` in INSTALLED_APPS nor a custom lookup.
        #
        # ponytail: `similarity()` is a sequential scan; the `%` operator is
        # what uses the GIN index migration 0002 creates. Ceiling: fine at a
        # catalogue of a few thousand editions, which is one campus's reading
        # lists. Upgrade path is S3's ranking work, which needs the index path
        # anyway — the index is created now because DATA-MODEL §3 mandates it
        # and because adding it later is a lock on a live table.
        return list(
            base.annotate(
                _similarity=Func(
                    F("title_norm"), Value(needle),
                    function="similarity", output_field=FloatField(),
                )
            )
            .filter(_similarity__gte=TRIGRAM_THRESHOLD)
            .order_by("-_similarity", "title")[:limit]
        )
    return list(base.filter(title_norm__contains=needle).order_by("title")[:limit])


def create_book(actor, **fields) -> Book:
    """API-CONTRACT §3. Raises `DuplicateIsbn` (→ 409 via `IntegrityError`).

    A student may create a `books` row (DATA-MODEL §3) and it is flagged for
    staff verification by **not** setting `staff_verified_at` — there is no
    separate flag column, because "unverified" is the absence of a
    verification, and a second boolean would be a fact that can disagree with
    the timestamp.

    JOURNEYS J2 step 2: a student who cannot find their book is offered this
    form. The created row is what J2-staff step 7 verifies, and it is a
    **catalogue signal** — a prescribed title we do not have.
    """
    isbn = fields.get("isbn13")
    digits = validate_isbn13(isbn) if isbn else None
    title = " ".join(str(fields.get("title") or "").split())
    if not title:
        raise ValidationFailed(
            "Enter the book's title.", field_errors={"title": ["Required."]}
        )
    language = fields.get("language") or "en"
    if language not in LANGUAGES:
        raise ValidationFailed(
            f"{language!r} is not a language we record.",
            detail=f"DATA-MODEL §3 allows {sorted(LANGUAGES)}.",
            field_errors={"language": [f"One of {sorted(LANGUAGES)}."]},
        )
    authors = fields.get("authors") or []
    if not isinstance(authors, (list, tuple)):
        raise ValidationFailed(
            "Enter the authors as a list.", field_errors={"authors": ["A list of names."]}
        )
    # The list-ness check above stays. A string is iterable, so iterating a
    # bare `"Grewal"` would store six authors of one character each — which
    # is why the type check is not replaced by the per-element work here.
    author_names = [" ".join(str(a).split()) for a in authors]
    year = fields.get("publication_year")
    if year not in (None, ""):
        try:
            year = int(year)
        except (TypeError, ValueError):
            raise ValidationFailed(
                "Enter the year as a number.", field_errors={"publication_year": ["A year."]}
            ) from None
        if not 1400 <= year <= 2100:
            raise ValidationFailed(
                "That publication year does not look right.",
                field_errors={"publication_year": ["Between 1400 and 2100."]},
            )
    else:
        year = None

    with transaction.atomic():
        try:
            # **A savepoint, not the outer block.** An `IntegrityError` marks
            # the whole transaction as needing rollback on PostgreSQL, so the
            # `Book.objects.filter(...)` below would raise
            # `TransactionManagementError` instead of finding the existing
            # row — measured, and the kind of difference SQLite would not
            # have shown (`CLAUDE.md` rule 9's labelling rule).
            with transaction.atomic():
                book = Book.objects.create(
                    isbn13=digits,
                    title=title,
                    title_norm=normalise_title(title),
                    authors=author_names,
                    edition_label=(fields.get("edition_label") or None),
                    publisher=(fields.get("publisher") or None),
                    publication_year=year,
                    language=language,
                    origin_country=(fields.get("origin_country") or None),
                    created_by=(actor if getattr(actor, "id", None) else None),
                )
        except IntegrityError:
            # API-CONTRACT §3 names `DuplicateIsbn` on this signature, so the
            # duplicate is a refusal and not a silent "here is the one we
            # already had". The distinction is the edition lock: a student who
            # is told "we already have this" goes back to J2 step 2's "is this
            # the one?" screen and confirms the edition they are holding, which
            # is the confirmation the whole wedge rests on.
            existing = resolve_merge(Book.objects.filter(isbn13=digits).first())
            if existing is None:
                raise
            raise DuplicateIsbn(
                "We already have that book — check it is the same edition.",
                book_id=existing.pk,
            ) from None
        record_audit(
            actor, "catalog.book_created", book,
            after={"isbn13": book.isbn13, "title": book.title, "staff_verified": False},
        )
    return book


def merge_books(staff, source: Book, target: Book) -> None:
    """API-CONTRACT §3. Staff-only. Sets `source.merged_into = target`.

    **No row is deleted** (J2-staff step 6): listings point at `source`, and a
    listing on a merged book still loads because every read goes through
    `resolve_merge`.
    """
    _require_staff(staff, "merge two catalogue entries")
    if source.pk == target.pk:
        raise ValidationFailed("A book cannot be merged into itself.")
    if resolve_merge(target) is not None and resolve_merge(target).pk == source.pk:
        raise ValidationFailed(
            "That merge would make a cycle.",
            detail=f"books {target.pk} already resolves to {source.pk}.",
        )
    with transaction.atomic():
        before = {"merged_into_id": source.merged_into_id}
        source.merged_into = target
        source.save(update_fields=["merged_into"])
        record_audit(
            staff, "catalog.books_merged", source,
            before=before, after={"merged_into_id": target.pk},
        )


def verify_book(staff, book: Book) -> Book:
    """J2-staff step 7. Staff-only. Stamps `staff_verified_at`.

    Not in API-CONTRACT §3's list, and it is the staff half of `create_book`
    rather than a new capability: without it `staff_verified_at` is a column
    nothing can ever set, and `publish_listing`'s unverified-book branch
    (DATA-MODEL §6.1) would have no exit.
    """
    from django.utils import timezone

    _require_staff(staff, "verify a catalogue entry")
    with transaction.atomic():
        before = {"staff_verified_at": book.staff_verified_at}
        book.staff_verified_at = timezone.now()
        book.save(update_fields=["staff_verified_at"])
        record_audit(
            staff, "catalog.book_verified", book,
            before=before, after={"staff_verified_at": book.staff_verified_at},
        )
    return book


def prescribed_for_course(campus, course_code):
    """The reading list for one course on one campus. R-01's measurement.

    Tenant-scoped, so it takes a campus rather than an actor-free query. The
    caller is the staff open-wants screen and S3's course-code search path.
    """
    code = " ".join(str(course_code or "").split()).upper()
    if not code:
        return []
    return list(
        PrescribedText.objects.filter(campus=campus, course_code__iexact=code)
        .select_related("book")
        .order_by("term_label", "book__title")
    )


def _require_staff(actor, what):
    if not getattr(actor, "is_staff_member", False):
        raise NotPermitted(f"Only staff can {what}.")
    return actor


def get_book(book_id):
    """A book by id, following merges. Raises `NotFound`."""
    book = resolve_merge(Book.objects.filter(id=book_id).first())
    if book is None:
        raise NotFound("No such book.")
    return book
