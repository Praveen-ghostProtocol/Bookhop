"""RED TEAM PROBE · S2 per-slice pass. **Not a regression test.**

Subject: *"the gate opening wider than intended now that there is finally
content behind it."*

S2 built a Django authorisation decision in front of every photo byte, and
`API-CONTRACT.md` §5.2 (A-20, cto, 2026-10-22) says why:

> *"A Django view, **not** a public static path … a guessable media URL would
> be a side channel around ADR-002 §4 exactly as `match_scan` would have
> been … The files stay off any publicly-routable path (ADR-001 §2.6)."*

Two other frozen documents describe the production deployment, and both of
them put `MEDIA_ROOT` on a public nginx location:

* `ADR-001-stack.md` §2.6 — the clause A-20 cites as its own authority —
  *"written to a local directory **served by nginx** with `Cache-Control:
  private`."*
* `INFRA.md` §1's topology diagram — *"nginx … ├── /static/, **/media/**
  (direct, private cache)"*.

Nothing in either names an `internal` location, and nothing in either sets
`BOOKHOP_MEDIA_INTERNAL_PREFIX`, which `bookhop/settings/base.py` tells the
operator to *"set in production (`INFRA.md` §1)"* — a pointer into the
document that specifies the opposite arrangement.

This probe measures the two halves that make it exploitable rather than
merely untidy: the documents disagree, and the storage key is **derivable**
from a payload any authorised reader already holds.
"""

import io
import pathlib
import re
import struct

import pytest

pytestmark = pytest.mark.django_db

REPO = pathlib.Path(__file__).resolve().parents[2]


def _jpeg(w=12, h=9):
    return b"".join([
        b"\xff\xd8",
        b"\xff\xc0" + struct.pack(">H", 11) + bytes((8,))
        + struct.pack(">HH", h, w) + bytes((1, 1, 0x11, 0)),
        b"\xff\xda" + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0)),
        b"\x10\x20\x30\xff\xd9",
    ])


def test_the_storage_key_is_fully_derivable_from_the_public_listing_payload(
    rt_client_as, seller, book, settings, tmp_path
):
    """**The capability token.** `photos[].sha256` plus the listing id is the
    whole key.

    `add_photo` builds `listings/{listing.id}/{digest[:32]}.{format}` and
    `listing_payload` publishes the full `sha256` and the id. So anyone who
    can read one listing response can write down the exact path of the file
    on disk — and hand it to anyone at all.
    """
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.listings import services

    listing = services.create_listing(
        seller, book=book, asking_price_paise=27500, condition="GOOD",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    buf = io.BytesIO(_jpeg())
    buf.name = "p.jpg"
    photo = services.add_photo(seller, listing, buf)

    payload = rt_client_as(seller).get(f"/api/v1/listings/{listing.id}").json()
    published_sha = payload["photos"][0]["sha256"]

    derived = f"listings/{payload['id']}/{published_sha[:32]}.jpeg"
    assert derived == photo.storage_key, (
        "the key is no longer derivable from the payload; retire this probe"
    )
    assert (pathlib.Path(settings.MEDIA_ROOT) / derived).exists()


def test_the_two_deployment_documents_put_media_root_on_a_public_nginx_location():
    """**FINDING, if red.** A-20's control is defeated by the topology that
    ships, and A-20 cites as its authority the clause that defeats it.

    Read as documents on purpose: no code change can close this, because the
    arrangement is specified outside the code.
    """
    adr = (REPO / "company/architecture/ADR-001-stack.md").read_text(encoding="utf-8")
    infra = (REPO / "company/architecture/INFRA.md").read_text(encoding="utf-8")
    settings_src = (REPO / "bookhop/settings/base.py").read_text(encoding="utf-8")

    evidence = {
        "ADR-001 §2.6 serves media from nginx":
            "served by nginx" in adr,
        "ADR-001 §2.6 says the location is `internal`":
            bool(re.search(r"internal\s*;|`internal`", adr)),
        "INFRA.md §1 routes /media/ direct":
            bool(re.search(r"/media/\s*\(direct", infra)),
        "INFRA.md names an internal location or X-Accel-Redirect":
            ("X-Accel" in infra) or ("internal;" in infra),
        "INFRA.md sets BOOKHOP_MEDIA_INTERNAL_PREFIX":
            "BOOKHOP_MEDIA_INTERNAL_PREFIX" in infra,
        "settings points the operator at INFRA.md §1 for the value":
            "INFRA.md` §1" in settings_src or "INFRA.md §1" in settings_src,
    }

    assert evidence["INFRA.md names an internal location or X-Accel-Redirect"], (
        "FINDING. `MEDIA_ROOT` holds every listing photo. API-CONTRACT §5.2 "
        "(A-20) requires it to stay 'off any publicly-routable path' and to "
        "be served only via `X-Accel-Redirect` from an nginx `internal` "
        "location. Neither deployment document describes that arrangement; "
        "both describe nginx serving /media/ directly, and settings sends the "
        f"operator to the one that does. Evidence: {evidence}"
    )


def test_a_direct_media_fetch_would_carry_none_of_the_response_controls(
    rt_client_as, seller, book, settings, tmp_path
):
    """What is lost is not only the authorisation. Recorded as its own row.

    Every header on a photo response is set by `photo_response` in Django.
    An nginx location serving the file directly runs none of that code, so
    `X-Robots-Tag: noindex`, `nosniff` and the content-type-from-the-key rule
    all go with the gate.
    """
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.listings import services

    listing = services.create_listing(
        seller, book=book, asking_price_paise=27500, condition="GOOD",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    buf = io.BytesIO(_jpeg())
    buf.name = "p.jpg"
    photo = services.add_photo(seller, listing, buf)
    services.publish_listing(seller, listing, listing.version)

    authorised = rt_client_as(seller).get(
        f"/api/v1/listings/{listing.id}/photos/{photo.sha256}"
    )
    set_by_django = {
        h: authorised[h] for h in
        ("Cache-Control", "X-Robots-Tag", "X-Content-Type-Options", "Content-Type")
    }
    assert set_by_django["X-Robots-Tag"] == "noindex"

    # The same bytes, at a path nginx would answer from disk with none of it.
    on_disk = pathlib.Path(settings.MEDIA_ROOT) / photo.storage_key
    assert on_disk.read_bytes() == authorised.content, (
        "the served bytes are the file on disk, so a direct location returns "
        f"the identical object without any of {sorted(set_by_django)}"
    )


def test_the_gate_still_holds_on_every_route_that_does_go_through_django(
    rt_client_as, rt_second_student, seller, book, settings, tmp_path
):
    """**The other side is a row.** Where Django decides, the gate is correct.

    Expected to pass. It is here so the finding above cannot be read as "the
    gate is broken" — it is not; it is bypassed by the deployment, which is a
    different and cheaper thing to fix.
    """
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.listings import services

    listing = services.create_listing(
        seller, book=book, asking_price_paise=27500, condition="GOOD",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    buf = io.BytesIO(_jpeg())
    buf.name = "p.jpg"
    photo = services.add_photo(seller, listing, buf)
    services.publish_listing(seller, listing, listing.version)

    other = rt_client_as(rt_second_student)
    assert other.get(f"/listing/{listing.id}").status_code == 404
    assert other.get(f"/api/v1/listings/{listing.id}").status_code == 404
    assert other.get(
        f"/api/v1/listings/{listing.id}/photos/{photo.sha256}"
    ).status_code == 404
