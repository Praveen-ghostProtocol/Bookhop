r"""F50 regression — the one human control can see what it is deciding.

At pilot `LISTING_REVIEW_ALL=true`, so every listing stops at
`PENDING_REVIEW` and a moderator decides. Red Team measured what that
moderator was handed: an ISBN, a title, a photo *count*, and nothing else.
`condition` and `damage_flags` were built by `queue_rows` and never printed;
`asking_price_paise` was in no key of it; and no staff surface at any layer
resolved a photo, though the reviewer's documented job is *"about the book
**and the images**"*.

**Both sides are rows** (`CLAUDE.md` rule 10's corollary). The rule here
splits *who may see a photo*, so the regression asserts the permitted side
(a staff moderator can) **and the refused side** (a student who is not the
owner still cannot, and `get_photo_for_download` still refuses staff). A
suite that only checked the permitted side would pass if the fix had been a
widening — which is exactly the fix that was not wanted.
"""

import io
import struct

import pytest
from django.core.management import call_command

from apps.core.errors import NotFound, NotPermitted

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
def pending(seller, book, settings, tmp_path):
    """**The shape the reviewer has to catch**: a ₹900 prescribed textbook
    offered at ₹60, claimed `AS_NEW`, no damage, with photos. Every field is
    lawful; the combination is the signal, and the combination is only
    visible if every part of it reaches the screen.
    """
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.listings import services

    listing = services.create_listing(
        seller, book=book, asking_price_paise=6000, condition="AS_NEW",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    for index in range(2):
        buf = io.BytesIO(_jpeg(12 + index, 9))
        buf.name = f"p{index}.jpg"
        services.add_photo(seller, listing, buf)
    services.publish_listing(seller, listing, listing.version)
    listing.refresh_from_db()
    assert listing.status == "PENDING_REVIEW"
    return listing


# --- the queue line --------------------------------------------------------


def test_the_queue_row_carries_the_claims_and_the_asking_figure(staff, pending):
    """The service layer, where the data has to exist before it can print."""
    from apps.listings.staff import queue_rows

    row = next(r for r in queue_rows(staff) if r["id"] == pending.id)
    assert row["condition"] == "AS_NEW"
    assert row["damage_flags"] == []
    assert row["asking_price_paise"] == 6000


def test_the_printed_queue_line_carries_all_three(staff, pending, capsys):
    """**The boundary the finding was at.** `queue_rows` already returned two
    of the three and the reviewer still could not see them, so asserting the
    dict is not asserting the control — the only reader is this command.
    """
    call_command("review_listings", "--staff", staff.email)
    out = capsys.readouterr().out

    assert "AS_NEW" in out, "the seller's condition claim"
    assert "damage=none" in out, "the seller's damage claim, stated rather than absent"
    assert "Rs 60.00" in out, "the asking figure, which was in no layer at all"


def test_an_empty_queue_still_says_so(staff, capsys):
    """The other side of the printing rule: no listing, no fabricated line."""
    call_command("review_listings", "--staff", staff.email)
    assert "Nothing is waiting for review." in capsys.readouterr().out


def test_opening_one_listing_shows_the_claims_without_deciding_it(
    staff, pending, capsys
):
    """`--listing N` alone used to be an error. It is now the read step."""
    call_command("review_listings", "--staff", staff.email, "--listing", str(pending.id))
    out = capsys.readouterr().out
    pending.refresh_from_db()

    assert "AS_NEW" in out and "Rs 60.00" in out
    assert "none claimed" in out
    assert pending.status == "PENDING_REVIEW", "reading must not decide"


# --- the photos ------------------------------------------------------------


def test_a_staff_moderator_resolves_the_photo_bytes(staff, pending):
    from apps.listings.staff import photos_for_review

    resolved = photos_for_review(staff, pending.id)
    assert len(resolved) == 2
    for photo, data in resolved:
        assert data is not None
        assert data.startswith(b"\xff\xd8"), "real image bytes, not a path"
        assert len(data) == photo.bytes


def test_the_staff_read_writes_a_personal_data_access_row(staff, pending):
    """DPDP r.6(1)(c). A photo of a book on a desk is where a student lives —
    that is why EXIF is stripped — so a staff view of one owes a row.

    `queue_rows` deliberately writes none: a list is not an opening. The row
    is asserted here with its subject and its purpose, because a row that
    names no fields provides no visibility.
    """
    from apps.accounts.models import PersonalDataAccessLog
    from apps.listings.staff import photos_for_review

    before = PersonalDataAccessLog.objects.count()
    photos_for_review(staff, pending.id)
    rows = PersonalDataAccessLog.objects.order_by("-id")
    assert rows.count() == before + 1
    row = rows.first()
    assert row.staff_id == staff.id
    assert str(row.subject_pseudonym) == str(pending.seller_pseudonym)
    assert "listing_photos.storage_key" in row.fields_accessed
    assert str(pending.id) in row.purpose


def test_listing_the_queue_writes_no_access_row(staff, pending):
    """The other side. If a list wrote a row per listing, the log would be
    noise and the opening would be invisible inside it."""
    from apps.accounts.models import PersonalDataAccessLog
    from apps.listings.staff import queue_rows

    before = PersonalDataAccessLog.objects.count()
    queue_rows(staff)
    assert PersonalDataAccessLog.objects.count() == before


def test_a_student_cannot_use_the_staff_path(seller, pending):
    """**The refused side.** The new function is a staff authorisation, so
    the seller — who may read their own photos through the student path —
    must be refused by *this* one."""
    from apps.listings.staff import photos_for_review

    with pytest.raises(NotPermitted):
        photos_for_review(seller, pending.id)


def test_the_student_photo_path_was_not_widened_to_let_staff_in(staff, pending):
    """**The fix that was not made, asserted so it cannot be made later.**

    `get_photo_for_download` authorises on ownership or an open discovery
    gate. Adding `or is_staff_member` to it would have closed the finding and
    turned one decision into two — a student read and a staff read with
    different justifications and different logs, sharing a branch. A
    `404` here is the correct answer and is what keeps the two separable.
    """
    from apps.listings.services import get_photo_for_download

    photo = pending.photos.all().first()
    with pytest.raises(NotFound):
        get_photo_for_download(staff, pending.id, photo.sha256)


def test_the_command_writes_the_photos_where_a_human_can_open_them(
    staff, pending, tmp_path, capsys
):
    """End to end: the moderator's actual keystrokes produce actual files."""
    target = tmp_path / "review"
    call_command(
        "review_listings", "--staff", staff.email,
        "--listing", str(pending.id), "--photos", str(target),
    )
    out = capsys.readouterr().out
    written = sorted(target.glob("listing-*"))

    assert len(written) == 2, out
    for path in written:
        assert path.read_bytes().startswith(b"\xff\xd8")
        assert str(path) in out


def test_a_purged_photo_says_so_rather_than_crashing_the_queue(
    staff, pending, tmp_path, capsys
):
    """DATA-MODEL §10.2: the row survives its bytes. A moderator opening a
    listing whose photos were purged must get a sentence, not a traceback."""
    from apps.listings.models import ListingPhoto
    from apps.listings.storage import delete_object

    for photo in ListingPhoto.all_objects.filter(listing=pending):
        delete_object(photo.storage_key)
        photo.storage_key = None
        photo.save(update_fields=["storage_key"])

    call_command(
        "review_listings", "--staff", staff.email,
        "--listing", str(pending.id), "--photos", str(tmp_path / "purged"),
    )
    assert "purged" in capsys.readouterr().out
