"""L2 — `/api/v1` listings handlers. API-CONTRACT §5.2.

Thin: validate, call L1, serialise. Every business rule — the price refusal,
the seller-terms check, the state machine, EXIF stripping — is in
`apps.listings.services`, because `web/**` calls the same functions and a rule
implemented here is a rule L3 does not get.

**What no response in this file contains** (API-CONTRACT §5.2, verbatim): *"a
seller address, a phone number, an email, precise coordinates, a settled
price, or any field in ADR-003 §2.3's deny-list."* Seller identity is
`{display_name, campus_name, pseudonym}` and nothing else
(`COMPLIANCE.md` §2.4(i)), and `services.seller_block` is the one place that
decides it so a serialiser here cannot reach for `listing.seller.email`.
`tests/unit/test_forbidden_response.py` asserts that against these payloads
rather than against the database.
"""

from django.views.decorators.http import require_safe

from apps.accounts.api import _may_write, _signed_in
from apps.core.api import endpoint
from apps.core.errors import ValidationFailed
from apps.core.ratelimit import ONE_DAY, consume_quota, is_exempt

from . import services
from .models import Listing


def _actor(request):
    from apps.accounts.sessions import session_user

    return session_user(request)


def _page_payload(page, serialise):
    return {
        "items": [serialise(row) for row in page["items"]],
        "next_cursor": page["next_cursor"],
    }


def _request_payload(row):
    """One `book_requests` row. No requester identity at all.

    A want is the demand signal; who wants it is nobody's business but staff's
    and the requester's own, and this payload is reachable by neither
    anonymously nor across campuses. The pseudonym is included **only** on the
    owner's own list, which is the only place this is serialised today.
    """
    return {
        "id": row.id,
        "status": row.status,
        "course_code": row.course_code,
        "created_at": row.created_at,
        "book": (
            {"id": row.book_id, "isbn13": row.book.isbn13, "title": row.book.title}
            if row.book_id
            else None
        ),
        "free_text_title": row.free_text_title,
    }


# --- listings ---------------------------------------------------------------


@endpoint(methods=["GET", "POST"], idempotent_write="POST /api/v1/listings", actor=_actor)
def listings(request, body, user):
    """§5.2 `POST /api/v1/listings`, and `GET` for the seller's own list.

    `POST` is **Stack M with the `listing_publication` purpose** — the consent
    JOURNEYS J1 step 5 names as the second required one, which S1 deliberately
    left to the slice that has something to publish.

    The listing is created **`DRAFT`**. That is JOURNEYS J2 step 7 and it is
    what makes EC-13 free: a photo upload that dies at 3 of 4 on 3G leaves a
    resumable draft rather than a lost form.

    Rate limited 10/day per user (§2.4).
    """
    if request.method == "POST":
        actor = _may_write(user, purposes=("listing_publication",))
        if not is_exempt(actor):
            consume_quota("listings.create", actor.id, limit=10, window=ONE_DAY)
        _accept_seller_terms_if_ticked(actor, body, request)
        book = _resolve_book(body.get("book_id"))
        listing = services.create_listing(
            actor,
            book=book,
            asking_price_paise=body.get("asking_price_paise"),
            condition=body.get("condition"),
            annotation_level=body.get("annotation_level"),
            damage_flags=body.get("damage_flags") or [],
            language=body.get("language") or "en",
            category=body.get("category") or "PRESCRIBED_TEXTBOOK",
            intent=body.get("intent") or "SELL",
            no_damage=bool(body.get("no_damage")),
            suspect_reproduction_flag=bool(body.get("suspect_reproduction_flag")),
        )
        return 201, services.listing_payload(listing)

    page = services.my_listings(
        _signed_in(user), cursor=request.GET.get("cursor"), limit=request.GET.get("limit")
    )
    return 200, _page_payload(page, services.listing_payload)


#: The body field that carries JOURNEYS J2 step 6's seller-terms tick.
#:
#: > **CONTRACT GAP, found by running the journey rather than by reading it.**
#: > API-CONTRACT §5.2 has **no row for accepting the seller terms**, and
#: > `accept_seller_terms` is an L1 function with no L2 or L3 route. Every
#: > unit test passed — they call the service directly — while a real client
#: > signed in, found a book, posted a listing and got
#: > `403 SELLER_TERMS_NOT_ACCEPTED` **with nothing it could do about it.**
#: > That is the exact shape TASKS §4's end-to-end checkbox exists to catch.
#: >
#: > Resolved **inside** the contract rather than by inventing a route: J2
#: > steps 6 and 7 are one form submission at L3 (*"accepts seller terms"*
#: > then *"creates the listing → `POST /sell`"*), so the tick rides on the
#: > create. No new endpoint, no changed L1 signature, and the refusal stays
#: > in L1 where `create_listing` can enforce it for every caller.
#: >
#: > Raised to cto as a one-row §5.2 clarification, and to frontend as the
#: > field name their sell form must post.
SELLER_TERMS_FIELD = "accept_seller_terms"


def _accept_seller_terms_if_ticked(actor, body, request):
    """Record r.6(4)(a)'s prior written contract when the student ticked it.

    Only when the body says so: a handler that accepted the terms silently on
    every create would make the acceptance row evidence of nothing, which is
    the opposite of what `COMPLIANCE.md` §2.4 needs it for.
    """
    if not body.get(SELLER_TERMS_FIELD):
        return
    from apps.accounts.services import accept_seller_terms, current_seller_terms

    accept_seller_terms(
        actor, current_seller_terms(actor), request.META.get("REMOTE_ADDR")
    )


def _resolve_book(book_id):
    from apps.catalog.services import get_book

    if not book_id:
        raise ValidationFailed(
            "Pick the book this copy is.", field_errors={"book_id": ["Required."]}
        )
    return get_book(book_id)


@endpoint(methods=["GET"], actor=_actor)
def my_listings(request, body, user):
    """§5.2 `GET /api/v1/listings/mine`. The seller's own, newest first."""
    page = services.my_listings(
        _signed_in(user), cursor=request.GET.get("cursor"), limit=request.GET.get("limit")
    )
    return 200, _page_payload(page, services.listing_payload)


@endpoint(methods=["GET"], actor=_actor)
def listing_detail(request, body, user, listing_id=None):
    """§5.2 `GET /api/v1/listings/{id}`.

    **The seller's own view.** The *discovery* read — another student's
    listing, behind `assert_discovery_open` — is `get_listing` in
    `apps/discovery/services.py` and is S3's. Serving it here would be the
    substitution ADR-002 §2.3 warns about: the gated manager would make a
    closed campus return nothing and the student would get a 404 where the
    contract requires `403 GATE_CLOSED`.
    """
    actor = _signed_in(user)
    return 200, services.listing_payload(services.get_own_listing(actor, listing_id))


@endpoint(
    methods=["POST"], idempotent_write="POST /api/v1/listings/photos", actor=_actor
)
def listing_photos(request, body, user, listing_id=None):
    """§5.2 `POST /api/v1/listings/{id}/photos` — multipart, ≤4, ≤8 MB each.

    **EXIF is stripped before the row exists.** Rate limited 40/day per user.

    The body is multipart rather than JSON, so `body` is empty and the file
    comes off `request.FILES`. The idempotency key still applies: a retried
    upload of the same photo must not create a fifth row.
    """
    actor = _may_write(user, purposes=("listing_publication",))
    if not is_exempt(actor):
        consume_quota("listings.photo", actor.id, limit=40, window=ONE_DAY)
    listing = services.get_own_listing(actor, listing_id)
    upload = request.FILES.get("photo")
    if upload is None:
        raise ValidationFailed(
            "Choose a photo to add.", field_errors={"photo": ["Required."]}
        )
    photo = services.add_photo(actor, listing, upload)
    return 201, {
        "id": photo.id,
        "sha256": photo.sha256,
        "width": photo.width,
        "height": photo.height,
        "bytes": photo.bytes,
        "listing_id": listing.id,
    }


@endpoint(
    methods=["POST"], idempotent_write="POST /api/v1/listings/publish", actor=_actor
)
def publish(request, body, user, listing_id=None):
    """§5.2 `POST /api/v1/listings/{id}/publish`. Needs `expected_version`."""
    actor = _may_write(user, purposes=("listing_publication",))
    listing = services.get_own_listing(actor, listing_id)
    updated = services.publish_listing(actor, listing, body.get("expected_version"))
    return 200, services.listing_payload(updated)


@endpoint(
    methods=["POST"], idempotent_write="POST /api/v1/listings/withdraw", actor=_actor
)
def withdraw(request, body, user, listing_id=None):
    """§5.2 `POST /api/v1/listings/{id}/withdraw`. Terminal."""
    actor = _may_write(user)
    listing = services.get_own_listing(actor, listing_id)
    updated = services.withdraw_listing(actor, listing, body.get("expected_version"))
    return 200, services.listing_payload(updated)


# --- book requests ----------------------------------------------------------


@endpoint(methods=["GET", "POST"], idempotent_write="POST /api/v1/requests", actor=_actor)
def requests_(request, body, user):
    """§5.2 `POST /api/v1/requests` and the student's own `GET`.

    JOURNEYS J4 step 2. **Nothing here returns an estimate of when the book
    will arrive, and there is no column for one** (PRD AC-B2.5): the want form
    never promises a time, a probability, or that the book will come.
    """
    if request.method == "POST":
        actor = _may_write(user)
        book = None
        if body.get("book_id"):
            book = _resolve_book(body.get("book_id"))
        row = services.create_request(
            actor,
            book=book,
            free_text_title=body.get("free_text_title"),
            course_code=body.get("course_code"),
        )
        return 201, _request_payload(row)

    page = services.my_requests(
        _signed_in(user), cursor=request.GET.get("cursor"), limit=request.GET.get("limit")
    )
    return 200, _page_payload(page, _request_payload)


@endpoint(
    methods=["DELETE", "POST"], idempotent_write="DELETE /api/v1/requests", actor=_actor
)
def request_detail(request, body, user, request_id=None):
    """§5.2 `DELETE /api/v1/requests/{id}` — JOURNEYS J4 step 6.

    `POST` is accepted for the same reason the L3 form needs it: an HTML form
    cannot issue `DELETE` without JavaScript, and ADR-001 §2.3 requires every
    flow to work with JavaScript off. Same handler, same service call, same
    idempotency namespace, so the two cannot diverge.
    """
    actor = _may_write(user)
    # `close_request` takes an id as readily as a row — **views never touch
    # the ORM** (API-CONTRACT §1), and the first draft of this handler did,
    # with a `BookRequest.all_objects` lookup. That is both the hard rule and
    # the reason `all_objects` has an allow-list: a bare lookup here would
    # have skipped the ownership predicate the service applies.
    return 200, _request_payload(services.close_request(actor, request_id))


@require_safe
def photo_bytes(request, listing_id=None, sha256=None):
    """`GET /api/v1/listings/{id}/photos/{sha256}` — the image itself.

    **Specified by cto, 2026-10-22, and the shape is the point: Django
    authorises, the web server serves.**

    * **Gate and scope are checked here, in Django, first.** A guessable
      media URL would be a side channel around the discovery gate — exactly
      the shape the notification scan would have been (TASKS S3's
      `match_scan` guard) — and `MEDIA_ROOT` served directly by nginx is a
      guessable media URL. The key is a sha256, which is unguessable, but
      *"unguessable"* is not an authorisation decision and ADR-002 §4 wants
      one.
    * **404, never 403, when out of scope**, so the route cannot confirm that
      a listing exists on another campus (API-CONTRACT §2.2: *"the same body
      either way; a 403 would confirm existence and leak the catalogue"*).
    * **Private caching and `noindex`.** A photo of a student's book is not
      shared-cacheable and is never indexed (§5.8's `X-Robots-Tag` rule).
    * **EXIF is absent by construction**, because `exif_stripped_at` is NOT
      NULL and the bytes on disk are the stripped ones — this route serves
      what was stored and has nothing to strip.

    In production the response carries `X-Accel-Redirect` and an empty body,
    so nginx streams the file and Django never reads it. In development there
    is no nginx, so the bytes are read and returned — **the authorisation is
    identical on both paths**, which is the property that matters, and the
    difference is which process does the I/O.

    # ponytail: `X-Accel-Redirect` assumes nginx. Ceiling: another front end
    # needs its own header (`X-Sendfile` for Apache). Upgrade path: one
    # setting, and `INFRA.md` §1 already names nginx — flagged to
    # platform-sre rather than abstracted over a web server we have not
    # deployed.

    Not wrapped in `endpoint`: it returns bytes rather than JSON, it takes no
    body and it carries no idempotency key. `require_safe` **is**
    `require_http_methods(["GET", "HEAD"])`, so the pair cannot be split by
    someone editing one of the two names — the same guarantee `endpoint`
    derives, and the same reason `notice` uses it.
    """
    from apps.core.api import error_response
    from apps.core.errors import ServiceError

    try:
        actor = _signed_in(_actor(request))
        photo = services.get_photo_for_download(actor, listing_id, sha256)
    except ServiceError as exc:
        return error_response(exc)
    return services.photo_response(photo)


__all__ = [
    "listings", "my_listings", "listing_detail", "listing_photos",
    "publish", "withdraw", "requests_", "request_detail", "photo_bytes",
    "SELLER_TERMS_FIELD", "Listing",
]
