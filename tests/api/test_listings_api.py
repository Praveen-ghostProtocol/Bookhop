"""L2 for the catalogue and listings — API-CONTRACT §5.2, over the stack.

**Four of these are regressions for defects that every unit test missed**,
because each lives at a *seam* rather than inside a function. TASKS §4 added
the end-to-end checkbox for exactly this, and the S2 run earned it again:

1. **A multipart upload was a 500.** `@endpoint` read `request.body` to parse
   JSON, which consumes the stream, so `request.FILES` then raised *"You
   cannot access body after reading from request's data stream"*. Every photo
   unit test calls `add_photo` directly with a file object, so the decorator
   was never in the path. The **only** multipart endpoint in the product was
   broken for every client.
2. **Any response carrying a timestamp was a 500 — after the write had
   committed.** `store_idempotent_response` put the handler's dict into a
   `JSONField` whose encoder has no `default=str`, so `POST /requests` and
   `POST /account/correction` raised on `created_at` / `due_at`. The row was
   created and the student was told the service had failed. No S1 response
   carried a datetime, which is why it shipped.
3. **A replayed transition answered 422 where the contract says 409.** The
   state check ran before the version check, so a stale form was told *"that
   cannot be done at this stage"* when the truth was *"someone changed this"*.
4. **There was no way to accept the seller terms.** §5.2 has no row for it
   and `accept_seller_terms` had no route, so a client could sign in, find a
   book, post a listing and receive `403 SELLER_TERMS_NOT_ACCEPTED` with
   nothing it could do. Carried on the create, per JOURNEYS J2 steps 6+7.

The client here is Django's test client, which is enough to keep each of them
fixed. It is **not** enough to have found them — only a real request over the
wire was — and that is the standing argument for the checkbox.
"""

import io
import json
import uuid

import pytest

pytestmark = pytest.mark.django_db


def _jpeg(width=4, height=3, tag=0):
    """A JPEG with a real EXIF APP1 segment carrying a GPS tag."""
    import struct

    exif = b"Exif\x00\x00" + b"II*\x00" + struct.pack("<I", 8)
    exif += struct.pack("<H", 1) + struct.pack("<HHII", 0x8825, 4, 1, 26)
    exif += bytes((tag, tag, tag, tag))
    app1 = bytes((0xFF, 0xE1)) + struct.pack(">H", len(exif) + 2) + exif
    sof = (bytes((0xFF, 0xC0)) + struct.pack(">H", 11) + bytes((8,))
           + struct.pack(">HH", height, width) + bytes((1,)) + bytes((1, 0x11, 0)))
    sos = bytes((0xFF, 0xDA)) + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0))
    return bytes((0xFF, 0xD8)) + app1 + sof + sos + bytes((0, 0)) + bytes((0xFF, 0xD9))


@pytest.fixture
def client_as(db):
    from django.test import Client

    from apps.accounts.sessions import SESSION_USER_KEY

    def _sign_in(user):
        client = Client()
        session = client.session
        session[SESSION_USER_KEY] = user.id
        session.save()
        return client

    return _sign_in


def _post(client, path, body, **extra):
    return client.post(
        path, data=json.dumps(body), content_type="application/json",
        headers={"Idempotency-Key": str(uuid.uuid4())}, **extra,
    )


def _code(response):
    try:
        return response.json().get("error", {}).get("code")
    except Exception:  # noqa: BLE001
        return None


# --- 1. the multipart seam ------------------------------------------------


def test_a_multipart_photo_upload_is_not_a_500(client_as, seller, book):
    """**The defect the journey found.** The only multipart endpoint in the
    product answered 500 for every client, and no unit test could see it
    because they all bypass the decorator."""
    from apps.listings.services import create_listing

    listing = create_listing(
        seller, book=book, asking_price_paise=30000, condition="GOOD",
        annotation_level="NONE", damage_flags=[], no_damage=True,
        language="en", category="PRESCRIBED_TEXTBOOK",
    )
    client = client_as(seller)
    response = client.post(
        f"/api/v1/listings/{listing.id}/photos",
        data={"photo": io.BytesIO(_jpeg())},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 201, response.content[:300]
    body = response.json()
    assert body["width"] == 4 and body["height"] == 3
    assert body["listing_id"] == listing.id


def test_a_json_post_still_parses_after_the_multipart_fix(client_as, seller, book):
    """The other side of the split (rule 10's corollary). The fix branches on
    the content type, so the JSON path has to be asserted too — a branch that
    only ever gets tested on one side is a branch with an untested half."""
    client = client_as(seller)
    response = _post(client, "/api/v1/listings", {
        "accept_seller_terms": True, "book_id": book.id,
        "asking_price_paise": 25000, "condition": "FAIR",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    })
    assert response.status_code == 201, response.content[:300]
    assert response.json()["asking_price_paise"] == 25000


# --- 2. the idempotency-store seam ---------------------------------------


@pytest.mark.parametrize(
    "path,body,want",
    [
        ("/api/v1/requests", {"free_text_title": "A book we do not stock"}, 201),
        ("/api/v1/account/correction", {"stated_problem": "My name is wrong."}, 201),
    ],
)
def test_a_response_carrying_a_timestamp_is_not_a_500(client_as, seller, path, body, want):
    """**The write committed and the student was told it failed.**

    `idempotency_keys.response_body` is a `JSONField` whose encoder has no
    `default=str`, so storing a payload with a `datetime` raised *after* the
    mutation. Both of these endpoints return one.
    """
    client = client_as(seller)
    response = _post(client, path, body)
    assert response.status_code == want, response.content[:300]


def test_a_replay_returns_the_same_response_as_the_original(client_as, seller, engine):
    """API-CONTRACT §4.1: a replay *"returns the stored response"*.

    Asserted on the **parsed document**, and the reason it is not asserted on
    the bytes is a measured engine property worth recording rather than
    working around.

    **VERIFIED HERE, PostgreSQL 16:** `idempotency_keys.response_body` is a
    `JSONField`, which is **`jsonb`** — and jsonb *does not preserve key
    order*. So the replay comes back semantically identical and byte-different
    (measured: `{"id", "book", …}` returns as `{"id", "status", …}`).
    **VERIFIED HERE, SQLite:** the same column is text, so order survives and
    the bytes do match. §4.1's word *"verbatim"* is therefore satisfiable in
    the sense that matters — same status, same document — and not in the
    literal one on the engine we ship on.

    The single canonicalisation (`apps.core.api.jsonable`) is still the thing
    that makes this true at all: without it the store raised on a timestamp
    and there was no replay to compare.
    """
    client = client_as(seller)
    key = str(uuid.uuid4())
    first = client.post(
        "/api/v1/requests", data=json.dumps({"free_text_title": "Replay me"}),
        content_type="application/json", headers={"Idempotency-Key": key},
    )
    second = client.post(
        "/api/v1/requests", data=json.dumps({"free_text_title": "Replay me"}),
        content_type="application/json", headers={"Idempotency-Key": key},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.headers.get("Idempotency-Replayed") == "true"
    assert second.json() == first.json(), (
        "the replay is not the same document as the original, so one of the "
        "two is being serialised by a different rule"
    )
    if engine == "sqlite":
        assert second.content == first.content, (
            "on SQLite the column is text and key order survives, so the "
            "bytes must match too"
        )


# --- 3. the 409-before-422 ordering --------------------------------------


def test_a_replayed_publish_is_a_version_conflict_not_a_transition_error(
    client_as, seller, book
):
    """API-CONTRACT §2.2's split, and which answer is useful.

    409 means *someone changed this* and leads to "reload and try again".
    422 means *the object cannot do this* and leads nowhere — which is what a
    student replaying a stale form used to get, while the truth was that
    their listing had already been published.
    """
    from apps.listings.services import create_listing

    listing = create_listing(
        seller, book=book, asking_price_paise=30000, condition="GOOD",
        annotation_level="NONE", damage_flags=[], no_damage=True,
        language="en", category="PRESCRIBED_TEXTBOOK",
    )
    client = client_as(seller)
    first = _post(client, f"/api/v1/listings/{listing.id}/publish",
                  {"expected_version": listing.version})
    assert first.status_code == 200, first.content[:300]

    stale = _post(client, f"/api/v1/listings/{listing.id}/publish",
                  {"expected_version": listing.version})
    assert stale.status_code == 409, stale.content[:300]
    assert _code(stale) == "VERSION_CONFLICT"


def test_a_current_version_on_an_illegal_transition_is_still_422(client_as, seller, book):
    """The other side: when the version is right and the move is genuinely
    impossible, 422 is the correct answer and must not have been swallowed by
    the reordering."""
    from apps.listings.services import create_listing, withdraw_listing

    listing = create_listing(
        seller, book=book, asking_price_paise=30000, condition="GOOD",
        annotation_level="NONE", damage_flags=[], no_damage=True,
        language="en", category="PRESCRIBED_TEXTBOOK",
    )
    listing = withdraw_listing(seller, listing, listing.version)
    client = client_as(seller)
    response = _post(client, f"/api/v1/listings/{listing.id}/publish",
                     {"expected_version": listing.version})
    assert response.status_code == 422, response.content[:300]
    assert _code(response) == "TRANSITION_NOT_ALLOWED"


# --- 4. the seller-terms route that did not exist ------------------------


def test_a_listing_is_refused_until_the_terms_are_accepted(client_as, student, book,
                                                           privacy_notice, seller_terms_notice):
    from apps.accounts.services import grant_consent

    student.status = "ACTIVE"
    student.save(update_fields=["status"])
    grant_consent(student, "listing_publication", privacy_notice, "SIGNUP_FORM", None, "pytest")
    client = client_as(student)
    response = _post(client, "/api/v1/listings", {
        "book_id": book.id, "asking_price_paise": 30000, "condition": "GOOD",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    })
    assert response.status_code == 403
    assert _code(response) == "SELLER_TERMS_NOT_ACCEPTED"


def test_the_tick_on_the_create_records_the_acceptance(client_as, student, book,
                                                       privacy_notice, seller_terms_notice):
    """JOURNEYS J2 steps 6+7, which are one form submission at L3.

    And the acceptance is **evidence**, so it is recorded only when the
    student ticked: a handler that accepted silently on every create would
    make the row evidence of nothing.
    """
    from apps.accounts.models import SellerTermsAcceptance
    from apps.accounts.services import grant_consent

    student.status = "ACTIVE"
    student.save(update_fields=["status"])
    grant_consent(student, "listing_publication", privacy_notice, "SIGNUP_FORM", None, "pytest")
    client = client_as(student)
    response = _post(client, "/api/v1/listings", {
        "accept_seller_terms": True,
        "book_id": book.id, "asking_price_paise": 30000, "condition": "GOOD",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    })
    assert response.status_code == 201, response.content[:300]
    row = SellerTermsAcceptance.objects.get(user_pseudonym=student.person_pseudonym)
    assert row.notice_version_id == seller_terms_notice.id


# --- the response shape ---------------------------------------------------


def test_a_listing_response_carries_no_contact_detail(client_as, seller, book):
    """API-CONTRACT §5.2, verbatim: *"listing responses never contain a seller
    address, a phone number, an email, precise coordinates, a settled price,
    or any field in ADR-003 §2.3's deny-list."*

    Asserted on the **values** as well as the keys, because the seller's own
    address is a value that would appear under an innocuous key.
    """
    from apps.listings.services import create_listing

    listing = create_listing(
        seller, book=book, asking_price_paise=30000, condition="GOOD",
        annotation_level="NONE", damage_flags=[], no_damage=True,
        language="en", category="PRESCRIBED_TEXTBOOK",
    )
    client = client_as(seller)
    body = client.get(f"/api/v1/listings/{listing.id}").json()

    assert set(body["seller"]) == {
        "display_name", "campus_name", "pseudonym", "signed_in_with_college_email"
    }, (
        "COMPLIANCE.md §2.4(i): the seller block is display_name, campus_name "
        "and pseudonym, plus the campus-mail disclosure a buyer is owed"
    )
    rendered = json.dumps(body)
    assert seller.email not in rendered, "the seller's email address is in the response"
    for key in ("phone", "latitude", "longitude", "address", "settled"):
        assert key not in rendered, f"{key!r} appears in a listing response"


def test_the_money_key_is_the_contract_name_at_the_boundary(client_as, seller, book):
    """ADR-003 §2.3's response-key rule: no key named `price`, `amount`,
    `total` or `value`. The money key is `asking_price_paise` at the boundary
    as well as in the table, so a template cannot render "Price:" from a field
    that invited it."""
    from apps.listings.services import create_listing

    listing = create_listing(
        seller, book=book, asking_price_paise=30000, condition="GOOD",
        annotation_level="NONE", damage_flags=[], no_damage=True,
        language="en", category="PRESCRIBED_TEXTBOOK",
    )
    client = client_as(seller)
    body = client.get(f"/api/v1/listings/{listing.id}").json()
    assert "asking_price_paise" in body
    for forbidden in ("price", "amount", "total", "value"):
        assert forbidden not in body


def test_the_books_endpoint_refuses_an_anonymous_caller(db):
    """An unauthenticated catalogue search is the scraping surface
    `THREAT-MODEL.md` §5.6 is about, reached by pressing enter."""
    from django.test import Client

    response = Client().get("/api/v1/books?q=engineering")
    assert response.status_code == 401


def test_every_listing_route_refuses_an_anonymous_caller(db):
    from django.test import Client

    client = Client()
    for path in ("/api/v1/listings", "/api/v1/listings/mine", "/api/v1/listings/1",
                 "/api/v1/requests"):
        assert client.get(path).status_code == 401, path


def test_listings_mine_resolves_rather_than_falling_through_to_the_detail_route(
    client_as, seller
):
    """`listings/mine` is declared before `listings/<int:listing_id>`.

    Django resolves in order and `mine` is not an int, so a wrong order sends
    it to `web/urls.py`'s catch-all 404 — a contract route silently missing,
    which is the shape QA's own resolver guard was written for.
    """
    from django.urls import resolve

    assert resolve("/api/v1/listings/mine").func.__module__.startswith("apps.")
    assert client_as(seller).get("/api/v1/listings/mine").status_code == 200


# --- the photo route: Django authorises, the web server serves -----------


@pytest.fixture
def listing_with_photo(seller, book):
    from apps.listings.services import add_photo, create_listing

    listing = create_listing(
        seller, book=book, asking_price_paise=30000, condition="GOOD",
        annotation_level="NONE", damage_flags=[], no_damage=True,
        language="en", category="PRESCRIBED_TEXTBOOK",
    )
    photo = add_photo(seller, listing, io.BytesIO(_jpeg()))
    return listing, photo


def test_the_seller_can_fetch_their_own_draft_photo(client_as, seller, listing_with_photo):
    listing, photo = listing_with_photo
    response = client_as(seller).get(
        f"/api/v1/listings/{listing.id}/photos/{photo.sha256}"
    )
    assert response.status_code == 200, response.content[:200]
    assert response["Content-Type"] == "image/jpeg"
    assert response.content.startswith(b"\xff\xd8"), "the bytes are not a JPEG"
    assert b"Exif\x00\x00" not in response.content, (
        "EXIF must be absent by construction: the stored bytes are the "
        "stripped ones and this route serves what was stored"
    )


def test_the_photo_route_sets_private_caching_and_noindex(client_as, seller, listing_with_photo):
    """A photo of a student's book is not shared-cacheable and is never
    indexed. `public` here would let a shared cache serve one student's photo
    from another student's authorised request."""
    listing, photo = listing_with_photo
    response = client_as(seller).get(f"/api/v1/listings/{listing.id}/photos/{photo.sha256}")
    assert "private" in response["Cache-Control"]
    assert "public" not in response["Cache-Control"]
    assert response["X-Robots-Tag"] == "noindex"
    assert response["X-Content-Type-Options"] == "nosniff"


def test_another_students_photo_is_404_and_never_403(
    client_as, seller, listing_with_photo, pending_student, privacy_notice
):
    """**The catalogue leak, and why the code is 404.**

    A 403 would confirm that this listing exists — on another campus, or in
    a state this student may not see. API-CONTRACT §2.2: *"the same body
    either way."* That is a real difference from `GATE_CLOSED` on a search,
    where the student is asking about their own campus and is owed the
    explanation.
    """
    from apps.accounts.services import grant_consent

    listing, photo = listing_with_photo
    pending_student.status = "ACTIVE"
    pending_student.adult_verified = True
    pending_student.save(update_fields=["status", "adult_verified"])
    grant_consent(pending_student, "account", privacy_notice, "SIGNUP_FORM", None, "pytest")

    response = client_as(pending_student).get(
        f"/api/v1/listings/{listing.id}/photos/{photo.sha256}"
    )
    assert response.status_code == 404, response.content[:200]
    assert _code(response) == "NOT_FOUND", (
        "a GATE_CLOSED or FORBIDDEN here confirms the listing exists"
    )


def test_an_anonymous_caller_cannot_fetch_a_photo(db, listing_with_photo):
    """**The side channel the whole route exists to close.** A media URL
    served straight off `MEDIA_ROOT` by nginx would be reachable without a
    session, which is a path around the discovery gate."""
    from django.test import Client

    listing, photo = listing_with_photo
    assert Client().get(
        f"/api/v1/listings/{listing.id}/photos/{photo.sha256}"
    ).status_code == 401


def test_a_purged_photo_is_404_rather_than_a_crash(client_as, seller, listing_with_photo):
    """DATA-MODEL §10.2: the row survives its bytes. *Gone* must read the
    same as *never here* — nobody outside the audit trail is owed the
    distinction."""
    from apps.listings.models import ListingPhoto

    listing, photo = listing_with_photo
    ListingPhoto.all_objects.filter(id=photo.id).update(storage_key=None)
    response = client_as(seller).get(f"/api/v1/listings/{listing.id}/photos/{photo.sha256}")
    assert response.status_code == 404


def test_the_route_answers_head_as_well_as_get(client_as, seller, listing_with_photo):
    """`require_safe` is `require_http_methods(["GET", "HEAD"])`, so the pair
    cannot be split by editing one name. Three S1 routes answered GET and
    refused HEAD with 405, and only a real client sends one."""
    listing, photo = listing_with_photo
    response = client_as(seller).head(f"/api/v1/listings/{listing.id}/photos/{photo.sha256}")
    assert response.status_code == 200


def test_an_unsafe_method_on_the_photo_route_is_405(client_as, seller, listing_with_photo):
    listing, photo = listing_with_photo
    response = client_as(seller).post(f"/api/v1/listings/{listing.id}/photos/{photo.sha256}")
    assert response.status_code == 405


def test_production_hands_the_file_to_the_web_server_and_reads_nothing(
    client_as, seller, listing_with_photo, settings
):
    """**Django authorises, nginx serves**, and the authorisation is the same
    object on both paths — only the I/O moves.

    Asserted rather than described, because *"we will set X-Accel-Redirect in
    production"* is a claim about a configuration nobody has run. With the
    prefix set the body is empty and the header names the internal location;
    the status is still whatever the authorisation decided.
    """
    settings.MEDIA_INTERNAL_PREFIX = "/_media"
    listing, photo = listing_with_photo
    response = client_as(seller).get(f"/api/v1/listings/{listing.id}/photos/{photo.sha256}")
    assert response.status_code == 200
    assert response.content == b"", "Django is still reading the file"
    assert response["X-Accel-Redirect"] == f"/_media/{photo.storage_key}"
    assert response["Content-Type"] == "image/jpeg"


def test_the_authorisation_is_identical_whichever_path_serves_the_bytes(
    client_as, seller, listing_with_photo, pending_student, privacy_notice, settings
):
    """The property that makes the split safe: turning nginx on must not turn
    an authorisation off. The refused case is refused with the prefix set."""
    from apps.accounts.services import grant_consent

    settings.MEDIA_INTERNAL_PREFIX = "/_media"
    listing, photo = listing_with_photo
    pending_student.status = "ACTIVE"
    pending_student.adult_verified = True
    pending_student.save(update_fields=["status", "adult_verified"])
    grant_consent(pending_student, "account", privacy_notice, "SIGNUP_FORM", None, "pytest")
    response = client_as(pending_student).get(
        f"/api/v1/listings/{listing.id}/photos/{photo.sha256}"
    )
    assert response.status_code == 404
    assert "X-Accel-Redirect" not in response, (
        "a refused request still named an internal location, so nginx would "
        "serve a file Django just refused"
    )
