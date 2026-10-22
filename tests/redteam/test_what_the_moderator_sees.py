"""RED TEAM PROBE · S2 per-slice pass. **Not a regression test.**

Subject: the standing targets *counterfeit, pirated, or misdescribed books*.

At pilot `LISTING_REVIEW_ALL=true`, so **every** listing stops at
`PENDING_REVIEW` and a human decides. That human is the only control standing
between a photocopied textbook and a buyer. `apps/listings/staff.py` states
what the decision is about:

> *"the reviewer's judgement in J2-staff step 3 is about the book **and the
> images**"*

and the same docstring then says *"No photo bytes"*. This probe measures what
the reviewer is actually handed, by running the only surface that exists —
`manage.py review_listings` — and reading its output.
"""

import io
import struct

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def _jpeg(width=12, height=9):
    return b"".join([
        b"\xff\xd8",
        b"\xff\xc0" + struct.pack(">H", 11) + bytes((8,))
        + struct.pack(">HH", height, width) + bytes((1, 1, 0x11, 0)),
        b"\xff\xda" + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0)),
        b"\x10\x20\x30\xff\xd9",
    ])


@pytest.fixture
def listing_awaiting_review(seller, book, settings, tmp_path):
    """**The pirated-copy shape**, stated in the data a seller really types.

    A Rs 900 prescribed textbook offered at Rs 60 — the campus-gate photocopy
    price `company/README.md` §1 names — claimed AS_NEW with no damage and no
    annotations, with four photos. Every field is a lawful value; the
    *combination* is the signal.
    """
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.listings import services

    listing = services.create_listing(
        seller, book=book, asking_price_paise=6000, condition="AS_NEW",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    for n in range(4):
        buf = io.BytesIO(_jpeg(12 + n, 9))
        buf.name = f"p{n}.jpg"
        services.add_photo(seller, listing, buf)
    services.publish_listing(seller, listing, listing.version)
    listing.refresh_from_db()
    assert listing.status == "PENDING_REVIEW", listing.status
    return listing


def test_the_queue_line_omits_the_two_claims_the_queue_exists_to_judge(
    staff, listing_awaiting_review, capsys
):
    """**FINDING, if red.** `condition` and `damage_flags` are assembled by
    `staff.queue_rows` and then not printed by the command that is the only
    reader of it.

    A reviewer approving this listing cannot see that the seller claimed
    AS_NEW with no damage, so they cannot compare the claim to anything.
    """
    call_command("review_listings", "--staff", staff.email)
    out = capsys.readouterr().out

    assert "AS_NEW" in out or "as new" in out.lower(), (
        "FINDING. The seller's condition claim does not reach the reviewer. "
        f"`queue_rows` returns it; `review_listings` prints: {out.strip()!r}"
    )


def test_the_asking_price_never_reaches_the_reviewer_at_all(
    staff, listing_awaiting_review, capsys
):
    """**FINDING, if red.** The price is not in `queue_rows` and not on screen.

    Price against edition is the cheapest counterfeit signal there is, and it
    is the one field the moderation surface cannot see at any layer.
    """
    from apps.listings.staff import queue_rows, listing_for_review

    row = queue_rows(staff)[0]
    call_command("review_listings", "--staff", staff.email)
    out = capsys.readouterr().out

    assert "asking_price_paise" in row or "60" in out, (
        "FINDING. `queue_rows` keys are %s — no price — and the printed line "
        "is %r. The listing asks Rs 60 for a prescribed textbook and nothing "
        "the reviewer is shown says so." % (sorted(row), out.strip())
    )


def test_the_reviewer_cannot_reach_a_photo_through_any_staff_function(
    staff, listing_awaiting_review
):
    """**FINDING, if red.** There is no staff path to a photo, at any layer.

    **RE-POINTED, S2 re-report, and the reason is a defect in this probe.**
    The first version asked `get_photo_for_download(staff, …)` and nothing
    else, and asserted from that one refusal that *"no shipped surface"*
    resolves bytes. The fix added `photos_for_review` — a separate staff
    authorisation with its own `personal_data_access_log` row, which is the
    right shape and not a widening — and left `get_photo_for_download`
    refusing staff, correctly. **So the original probe stayed red against a
    closed finding**: it enumerated a surface instead of asking the property,
    which is `CLAUDE.md` rule 11 against this agent's own instrument.

    It now asks the property: does **any** staff-reachable function in
    `apps.listings.staff` resolve bytes for a queued listing? A future fix
    that moves the surface again does not make this probe lie.
    """
    from apps.listings import staff as staff_module
    from apps.listings.staff import listing_for_review, queue_rows
    from apps.listings.services import get_photo_for_download
    from apps.core.errors import ServiceError

    row = queue_rows(staff)[0]
    assert row["photo_count"] == 4

    detail = listing_for_review(staff, listing_awaiting_review.id)
    photo = detail.photos.all().first()

    reachable = None
    try:
        reachable = get_photo_for_download(staff, detail.id, photo.sha256)
    except ServiceError:
        reachable = None
    if reachable is None:
        # Every public callable on the staff surface that takes a listing, in
        # case the bytes moved rather than arrived.
        for name in dir(staff_module):
            if name.startswith("_") or not callable(getattr(staff_module, name)):
                continue
            try:
                result = getattr(staff_module, name)(staff, detail.id)
            except (ServiceError, TypeError, AttributeError, ValueError):
                continue
            found = [
                b for _row, b in (result or [])
                if isinstance(b, (bytes, bytearray)) and b
            ] if isinstance(result, list) else []
            if found:
                reachable = (name, len(found[0]))
                break

    assert reachable is not None, (
        "FINDING. A staff moderator deciding this listing cannot obtain the "
        "photo bytes through any shipped surface. `get_photo_for_download` "
        "refuses them (not the owner, gate closed, row not seed), the "
        "management command prints `photos=4`, and `queue_rows` is documented "
        "as carrying no photo bytes by design. With LISTING_REVIEW_ALL=true "
        "this is the only control over counterfeit and misdescribed listings."
    )


def test_the_moderation_decision_is_recordable_without_ever_seeing_the_listing(
    staff, listing_awaiting_review, capsys
):
    """**Measured, not argued.** REVIEW_PASS succeeds from the queue line alone.

    This one is expected to pass; it is the evidence that the two findings
    above are reachable rather than theoretical. Nothing in `moderate_listing`
    requires the reviewer to have read anything.
    """
    call_command(
        "review_listings", "--staff", staff.email,
        "--listing", str(listing_awaiting_review.id),
        "--action", "REVIEW_PASS", "--legal-basis", "seller terms",
        "--reason", "looks fine", "--seconds", "3",
    )
    listing_awaiting_review.refresh_from_db()
    assert listing_awaiting_review.status == "LIVE"
    assert "is now LIVE" in capsys.readouterr().out
