"""RED TEAM PROBE · S2 per-slice pass. **Not a regression test.**

Subject: the standing targets *disintermediation* and *physical safety of
handovers between strangers*.

S2 is the first slice that puts one student's identity in front of another.
`help.html` states the product's own rule plainly:

> *"NO PHONE NUMBER AND NO WHATSAPP NUMBER appears here or anywhere in the
> product, the emails or the notices (AC-H6.4, PRD EX-7). An unlogged channel
> makes support minutes unmeasurable."*

and `listing.html` states the constraint on the seller block:

> *"No address, no phone, no email, no precise location — **there is no such
> field** and no screen may imply one."*

Those are claims about the *schema*. This probe asks the different question:
is there a field whose **contents** can be any of those things.
"""

import io
import re
import struct

import pytest

pytestmark = pytest.mark.django_db

#: The field is 60 characters. This is 44, and it is what a seller who wants
#: to skip the app writes once and never thinks about again.
CHANNEL = "Priya R — wa.me/919840012345 · call me"


def _jpeg():
    return b"".join([
        b"\xff\xd8",
        b"\xff\xc0" + struct.pack(">H", 11) + bytes((8,))
        + struct.pack(">HH", 9, 12) + bytes((1, 1, 0x11, 0)),
        b"\xff\xda" + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0)),
        b"\x10\x20\x30\xff\xd9",
    ])


def test_the_profile_endpoint_accepts_a_contact_channel_as_a_display_name(seller):
    """**Measured, not argued.** `update_profile` takes it without comment.

    `CORRECTABLE_FIELDS` includes `display_name`; the only rules are
    non-empty after whitespace collapse and at most 60 characters. There is
    no character class, no digit rule and no URL rule at any layer.
    """
    from apps.accounts.services import update_profile

    update_profile(seller, display_name=CHANNEL)
    seller.refresh_from_db()
    assert seller.display_name == CHANNEL, (
        "the field now constrains its contents; retire this probe"
    )


def test_a_phone_number_reaches_the_listing_page_twice(
    rt_client_as, seller, book, settings, tmp_path
):
    """**FINDING, if red.** It renders in the seller block *and* in the
    attribution `<cite>` under the seller's own words about the condition.

    Two independent sites, so a fix that sanitises one leaves the other.
    """
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.accounts.services import update_profile
    from apps.listings import services

    update_profile(seller, display_name=CHANNEL)
    seller.refresh_from_db()
    listing = services.create_listing(
        seller, book=book, asking_price_paise=27500, condition="GOOD",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    services.publish_listing(seller, listing, listing.version)

    html = rt_client_as(seller).get(f"/listing/{listing.id}").content.decode()
    occurrences = html.count("wa.me/919840012345")

    assert occurrences == 0, (
        "FINDING. A WhatsApp link and a phone number are rendered %d time(s) "
        "on /listing/{id} — in the 'About this seller' block and in the "
        "<cite> attribution on the seller's condition quotation. The page's "
        "own comment says 'no phone … there is no such field'. There is: it "
        "is called display_name and nothing inspects what is in it."
        % occurrences
    )


def test_the_api_payload_carries_it_too_so_it_is_not_a_template_problem(
    rt_client_as, seller, book
):
    """The same string in `seller_block`'s `display_name`, which
    `test_forbidden_response.py` sweeps for *keys*, never for *values*."""
    from apps.accounts.services import update_profile
    from apps.listings import services

    update_profile(seller, display_name=CHANNEL)
    seller.refresh_from_db()
    listing = services.create_listing(
        seller, book=book, asking_price_paise=27500, condition="GOOD",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    body = rt_client_as(seller).get(f"/api/v1/listings/{listing.id}").json()
    found = body.get("seller", {}).get("display_name")
    assert "wa.me" not in str(found), (
        f"FINDING. The L2 listing response carries {found!r} in `seller."
        "display_name`. API-CONTRACT §5.2's rule — 'Listing responses never "
        "contain … a phone number' — is enforced on key names only."
    )


def test_the_sell_flow_offers_no_other_place_to_put_one_which_is_why_this_matters(
    seller, book
):
    """**Both sides are rows.** Confirms there is no free-text description
    field, so `display_name` is the *only* uncontrolled string a seller can
    attach to a listing — which is what makes it the channel rather than one
    of several.

    Expected to pass. Its job is to show the finding above is not a generic
    "user input is unvalidated" note.
    """
    import inspect

    from apps.listings import services
    from apps.listings.models import Listing

    text_columns = {
        f.name for f in Listing._meta.get_fields()
        if getattr(f, "get_internal_type", lambda: "")() == "TextField"
    }
    seller_typed_free_text = text_columns - {
        "intent", "condition", "annotation_level", "category",
        "language", "visibility_scope", "status",
    }
    assert seller_typed_free_text == set(), (
        f"a free-text column exists on listings: {seller_typed_free_text}"
    )
    assert "description" not in inspect.signature(services.create_listing).parameters
