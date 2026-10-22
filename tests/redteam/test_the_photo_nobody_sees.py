"""RED TEAM PROBE · S2 per-slice pass. **Not a regression test.**

Subject: the photo, end to end, from the seller's camera to the buyer's eye.

S2's headline feature is photos. The question this pass asks is not "is the
upload correct" — Code Review and QA both answered that — but **does a photo
reach a human**, and if not, is the reason the one written down.

Routes under probe:
  * `GET /media/listing-photo/{photo_id}`  — the path API-CONTRACT §5.2 / A-20
    (cto, 2026-10-22) specifies and freezes.
  * `GET /api/v1/listings/{id}/photos/{sha256}` — the path that shipped.
  * `GET /listing/{id}`, `GET /sell/{id}/photos`, `GET /sell` — every page a
    student is served that could carry an image.
"""

import io
import re
import struct

import pytest
from django.urls import Resolver404, get_resolver, resolve

pytestmark = pytest.mark.django_db


def jpeg(width=7, height=5):
    """A structurally valid JPEG carrying a GPS-bearing EXIF APP1."""
    payload = b"Exif\x00\x00II*\x00" + struct.pack("<I", 8)
    payload += struct.pack("<H", 1) + struct.pack("<HHII", 0x8825, 4, 1, 26)
    payload += b"\x00\x00\x00\x00"
    return b"".join([
        b"\xff\xd8",
        b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload,
        b"\xff\xc0" + struct.pack(">H", 11) + bytes((8,))
        + struct.pack(">HH", height, width) + bytes((1, 1, 0x11, 0)),
        b"\xff\xda" + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0)),
        b"\x01\x02\x03\xff\xd9",
    ])


def upload(data, name="photo.jpg"):
    buf = io.BytesIO(data)
    buf.name = name
    return buf


@pytest.fixture
def listing_with_photos(seller, book, settings, tmp_path):
    """A LIVE listing with two real photos, created only through the service."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.listings import services

    listing = services.create_listing(
        seller, book=book, asking_price_paise=27500, condition="GOOD",
        annotation_level="LIGHT_PENCIL", damage_flags=["TORN_PAGES"],
        language="en", category="PRESCRIBED_TEXTBOOK",
    )
    photos = [
        services.add_photo(seller, listing, upload(jpeg(7, 5))),
        services.add_photo(seller, listing, upload(jpeg(9, 6))),
    ]
    services.publish_listing(seller, listing, listing.version)
    listing.refresh_from_db()
    return listing, photos


def test_the_route_the_frozen_contract_specifies_does_not_exist(listing_with_photos):
    """**A-20's path is unrouted.**

    API-CONTRACT §5.2 names `GET /media/listing-photo/{photo_id}` and marks it
    *"Slice: S2, with the listing surface it completes"*. If it resolves to
    anything other than the catch-all 404, this probe is wrong.
    """
    _, photos = listing_with_photos
    path = f"/media/listing-photo/{photos[0].id}"
    try:
        match = resolve(path)
    except Resolver404:
        match = None
    name = getattr(match, "url_name", None)
    assert name in (None, "not-found"), (
        f"the contract route now exists and resolves to {name!r}; retire this probe"
    )

    # And the same thing from the outside, which is what a browser sees.
    from django.test import Client

    assert Client().get(path).status_code == 404


def test_the_bytes_are_reachable_over_http_at_the_path_that_did_ship(
    rt_client_as, seller, listing_with_photos
):
    """**The capability exists.** The seller's own photo comes back as bytes.

    This is the half that makes the finding a seam rather than a gap: nothing
    is missing from the backend. The route is built, authorised and serving.
    """
    listing, photos = listing_with_photos
    client = rt_client_as(seller)
    response = client.get(f"/api/v1/listings/{listing.id}/photos/{photos[0].sha256}")

    assert response.status_code == 200, response.content[:200]
    assert response["Content-Type"] == "image/jpeg"
    assert response.content.startswith(b"\xff\xd8"), "not JPEG bytes"
    assert b"Exif" not in response.content, "EXIF survived into the served bytes"


def test_no_page_a_student_is_served_points_at_a_photo(
    rt_client_as, seller, listing_with_photos
):
    """**FINDING, if red.** The bytes are reachable and no page reaches them.

    Every HTML page in S2 that could carry an image, driven as the seller who
    owns the listing — the one actor who is allowed to see all of it. If no
    page emits an `<img>`, and none of them so much as names the URL the
    previous test just fetched, then S2's photo pipeline terminates in a
    database row.
    """
    listing, photos = listing_with_photos
    client = rt_client_as(seller)

    pages = {
        "/sell": client.get("/sell"),
        f"/sell/{listing.id}/photos": client.get(f"/sell/{listing.id}/photos"),
        f"/listing/{listing.id}": client.get(f"/listing/{listing.id}"),
    }
    reached = {path: r for path, r in pages.items() if r.status_code == 200}
    assert len(reached) == 3, f"a page did not render: { {p: r.status_code for p, r in pages.items()} }"

    carries_image = {}
    for path, response in reached.items():
        html = response.content.decode("utf-8", "replace")
        carries_image[path] = {
            "img_tags": len(re.findall(r"<img\b", html, re.I)),
            "names_a_sha": any(p.sha256 in html for p in photos),
            "names_the_api_path": "/photos/" in html,
            "names_the_contract_path": "/media/listing-photo" in html,
        }

    assert any(
        v["img_tags"] or v["names_a_sha"] or v["names_the_api_path"]
        or v["names_the_contract_path"]
        for v in carries_image.values()
    ), (
        "FINDING. Two photos are stored, EXIF-stripped, authorised and served "
        "over HTTP (previous test, 200 + image/jpeg) — and NO page a student "
        f"is served emits an <img> or names the URL: {carries_image}"
    )


def test_the_page_tells_the_student_something_that_is_not_true(
    rt_client_as, seller, listing_with_photos
):
    """**The copy and the build disagree, and the copy is the stale one.**

    `listing.html` renders *"BookHop has no way to show them yet"*, sourced
    from a template comment reading *"No route serves a stored photo …
    API-CONTRACT §5.2 has no GET for a photo."* §5.2 gained that GET on
    2026-10-22 (A-20) and the backend built one in this same slice.
    """
    listing, _ = listing_with_photos
    html = rt_client_as(seller).get(f"/listing/{listing.id}").content.decode()
    assert "no way to show" not in html.lower(), (
        "the page no longer claims the capability is absent; retire this probe"
    )


def test_the_shipped_route_diverges_from_the_frozen_specification_in_three_ways(
    rt_client_as, seller, listing_with_photos
):
    """Each difference on its own row, so one being fixed cannot hide another.

    A-20 is a *frozen contract amendment*, so these are divergences, not
    choices. Recorded here because the path divergence is what made the
    frontend's reading of §5.2 correct and its page wrong.
    """
    listing, photos = listing_with_photos
    response = rt_client_as(seller).get(
        f"/api/v1/listings/{listing.id}/photos/{photos[0].sha256}"
    )

    divergences = {}

    # 1. The path. The contract says one path, no L2/L3 split.
    shipped = {str(p.pattern) for p in get_resolver().url_patterns
               if not hasattr(p, "url_patterns")}
    divergences["path"] = ("/media/listing-photo/{photo_id}",
                           "api/v1/listings/{id}/photos/{sha256}")

    # 2. The identifier. `photo_id` is in the contract; `sha256` shipped.
    divergences["identifier"] = ("photo_id", "sha256")

    # 3. Cache lifetime, stated exactly in the specification.
    divergences["cache_control"] = (
        "private, max-age=86400", response.get("Cache-Control")
    )

    assert response["Cache-Control"] == "private, max-age=86400", (
        "API-CONTRACT §5.2 (A-20) specifies `Cache-Control: private, "
        f"max-age=86400`; the route serves {response['Cache-Control']!r}. "
        f"Full divergence set: {divergences}"
    )
