"""L2 — `/api/v1` catalogue handlers. API-CONTRACT §5.2's first two rows.

Thin: validate, call L1, serialise. **Nothing here touches the ORM** and
nothing here contains a business rule — the ISBN checksum, the merge
resolution and the duplicate refusal all live in `apps.catalog.services`,
because `web/**` calls the same functions and a rule implemented at L2 is a
rule L3 does not get.

**`books` is global, so these two routes are not gated** (ADR-002 §2): looking
up an ISBN is not discovery, and a student on a closed campus who looks up a
book finds the edition and no listings. That distinction is what makes S3's
three truths expressible — *we don't recognise that ISBN* is a different
answer from *not on your campus yet*, and they come from different layers.
"""

from apps.accounts.api import _may_write, _signed_in
from apps.core.api import endpoint
from apps.core.errors import ValidationFailed

from . import services
from .models import Book


def _actor(request):
    from apps.accounts.sessions import session_user

    return session_user(request)


def book_payload(book):
    """One book. **No price of any kind** — a catalogue price would be a price
    history by another name (ADR-003 §2.2)."""
    return {
        "id": book.id,
        "isbn13": book.isbn13,
        "title": book.title,
        "authors": list(book.authors or []),
        "edition_label": book.edition_label,
        "publisher": book.publisher,
        "publication_year": book.publication_year,
        "language": book.language,
        "staff_verified": book.staff_verified_at is not None,
    }


@endpoint(methods=["GET", "POST"], idempotent_write="POST /api/v1/books", actor=_actor)
def books(request, body, user):
    """§5.2 `GET /api/v1/books?isbn=` · `?q=`, and `POST /api/v1/books`.

    **One handler, because §5.2 gives both verbs the same path** and Django
    routes by path, not by method. The two halves have different stacks and
    the split is by `request.method`, which is the one discriminator that
    cannot be confused with a body value — the shape that went wrong on
    `PATCH /account`.

    `GET` is **signed in and nothing more**: it reads global data, so §2.5's
    marketplace stack would refuse a student mid-signup the lookup that tells
    them what the product is. Not public, because an unauthenticated
    catalogue search is the scraping surface `THREAT-MODEL.md` §5.6 is about.

    `POST` is **Stack M** — JOURNEYS J2 step 2's *"add this book"* form.
    Creating a catalogue row is a marketplace write and the row it creates is
    one staff will have to verify (J2-staff step 7). A duplicate ISBN is
    `409 DUPLICATE_ISBN` carrying the existing `book_id`, so the client sends
    the student back to *"is this the one?"* rather than to an error page.
    """
    if request.method == "POST":
        _may_write(user)
        book = services.create_book(
            user,
            isbn13=body.get("isbn13"),
            title=body.get("title"),
            authors=body.get("authors") or [],
            edition_label=body.get("edition_label"),
            publisher=body.get("publisher"),
            publication_year=body.get("publication_year"),
            language=body.get("language") or "en",
        )
        return 201, book_payload(book)

    _signed_in(user)
    isbn = request.GET.get("isbn")
    query = request.GET.get("q")
    if isbn:
        found = services.find_book_by_isbn(isbn)
        return 200, {"items": [book_payload(found)] if found else [], "next_cursor": None}
    if query:
        rows = services.search_books(query, limit=request.GET.get("limit") or 20)
        return 200, {"items": [book_payload(b) for b in rows], "next_cursor": None}
    raise ValidationFailed(
        "Enter an ISBN or a title.",
        field_errors={"isbn": ["An ISBN, or use q= for a title."]},
    )


@endpoint(methods=["GET"], actor=_actor)
def book_detail(request, body, user, book_id=None):
    """§5.2. One book by id, following merges so EC-7 holds."""
    _signed_in(user)
    return 200, book_payload(services.get_book(book_id))


__all__ = ["books", "book_detail", "book_payload", "Book"]
