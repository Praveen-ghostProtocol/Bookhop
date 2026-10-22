"""EXIF stripping, and why `exif_stripped_at NOT NULL` is a guarantee.

`COMPLIANCE.md` §7 row 9 and DATA-MODEL §3: *"the row cannot exist unless EXIF
was stripped, which makes 'purge EXIF at upload' a structural guarantee rather
than a code-path hope."* The structural half is the column; **this file is the
behavioural half**, because a NOT NULL timestamp proves a value was written
and proves nothing about whether anything was stripped (`CLAUDE.md` rule 12 —
a control that guarantees a *state* does not detect a *bad input*).

So every assertion here is about **bytes**: the marker is present in the
fixture, absent in what is stored, and the stored file is still a valid image
of the right size.

**Why it matters more than it looks.** A photo of a textbook is taken at a
desk, and a phone writes GPS into APP1. Publishing it would put a student's
home address in a listing that another student can open.
"""

import pytest

from apps.core.errors import TooManyPhotos, UnsupportedImage
from apps.listings import services
from apps.listings.images import ImageRejected, strip_metadata
from apps.listings.storage import read_object

pytestmark = pytest.mark.django_db


def _upload(data, name="photo.jpg"):
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(name, data, content_type="image/jpeg")


def _jpeg(width=2, height=3):
    """A minimal JPEG of a given size, carrying no metadata.

    Used where a test needs several *different* images; the EXIF-carrying
    fixture is `jpeg_with_exif`.

    Markers are written as integers rather than as escape sequences, because
    a JPEG marker is a number and spelling it that way removes a layer of
    escaping that has already gone wrong once in this file.
    """
    import struct

    SOI, SOF0, SOS, EOI = 0xD8, 0xC0, 0xDA, 0xD9
    marker = lambda code: bytes((0xFF, code))
    sof = (
        marker(SOF0)
        + struct.pack(">H", 11)       # length: 2 + 1 + 2 + 2 + 1 + 3
        + bytes((8,))                 # sample precision
        + struct.pack(">HH", height, width)
        + bytes((1,))                 # one component
        + bytes((1, 0x11, 0))         # component id, sampling, quant table
    )
    sos = marker(SOS) + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0))
    return marker(SOI) + sof + sos + bytes((0, 0)) + marker(EOI)


def test_the_same_photo_twice_on_one_listing_is_refused_not_a_500(seller, book, jpeg_with_exif):
    """The defect the four-photo test surfaced, pinned.

    The storage key is content-addressed, so identical bytes produce an
    identical key and the UNIQUE index raised an `IntegrityError` — a 500 on
    a seller double-tapping "add". It is a refusal with a sentence now,
    because a silently-ignored upload reads as "it did not work" and gets
    tapped again.
    """
    from apps.core.errors import ValidationFailed

    listing = _listing(seller, book)
    services.add_photo(seller, listing, _upload(jpeg_with_exif))
    with pytest.raises(ValidationFailed, match="already"):
        services.add_photo(seller, listing, _upload(jpeg_with_exif))


def _listing(seller, book):
    return services.create_listing(
        seller, book=book, asking_price_paise=30000, condition="GOOD",
        annotation_level="NONE", damage_flags=[], no_damage=True,
        language="en", category="PRESCRIBED_TEXTBOOK",
    )


# --- the stripper, on bytes ------------------------------------------------


def test_the_fixture_really_carries_exif_before_anything_strips_it(jpeg_with_exif):
    """**The guard for the guard.** If the fixture had no EXIF, every
    assertion below would pass for free — the vacuous-fixture shape
    `CLAUDE.md` rule 10 names, and the one this project has hit repeatedly."""
    assert b"\xff\xe1" in jpeg_with_exif, "no APP1 marker in the fixture"
    assert b"Exif\x00\x00" in jpeg_with_exif, "no EXIF header in the fixture"
    assert b"\x25\x88" in jpeg_with_exif or b"\x88\x25" in jpeg_with_exif, (
        "no GPSInfo tag in the fixture, so 'the GPS tag is removed' is untested"
    )


def test_stripping_removes_the_app1_segment_and_keeps_a_valid_jpeg(jpeg_with_exif):
    stripped, image_format, width, height = strip_metadata(jpeg_with_exif)
    assert image_format == "jpeg"
    assert (width, height) == (2, 3), "the fixture is 2 wide and 3 tall"
    assert stripped.startswith(b"\xff\xd8"), "the result is not a JPEG any more"
    assert b"Exif\x00\x00" not in stripped
    assert b"\xff\xe1" not in stripped
    assert len(stripped) < len(jpeg_with_exif)


def test_stripping_removes_a_png_text_chunk(png_with_text):
    stripped, image_format, width, height = strip_metadata(png_with_text)
    assert image_format == "png"
    assert (width, height) == (2, 3)
    assert stripped.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"tEXt" not in stripped
    assert b"taken at home" not in stripped
    assert b"IHDR" in stripped and b"IDAT" in stripped and b"IEND" in stripped


def test_the_png_keep_list_holds_only_chunks_the_keep_list_can_decide():
    """**`PLTE` was in `_PNG_KEEP_ANCILLARY` and was dead** (QA, A-29 pass).

    A chunk type whose first letter is uppercase is *critical* and
    `_strip_png` keeps it several lines before this set is consulted, so an
    entry like that is unreachable — and worse than unreachable, because it
    tells a reader that the ancillary rule is what preserves palettes. The
    entry is gone; this is the guard that stops the next one arriving.

    `_PNG_METADATA_CHUNKS` went in the same pass: it claimed to be kept
    *"for the error message and for the test's own assertions"* and the name
    appeared exactly once in the repository — its own definition. Nothing
    interpolated it and no test read it. The property above
    (`test_stripping_removes_a_png_text_chunk`, and the ancillary rule it
    exercises) is what actually dropped those chunks, so there was no claim
    to make true.
    """
    from apps.listings import images

    assert images._PNG_KEEP_ANCILLARY, "the keep list is empty, so this guards nothing"
    critical = sorted(k for k in images._PNG_KEEP_ANCILLARY if k[:1].isupper())
    assert not critical, (
        f"{critical} are CRITICAL PNG chunks sitting in the ancillary keep "
        "list. `_strip_png` keeps every critical chunk before it reads this "
        "set, so the entry changes nothing and misdescribes the control."
    )
    assert not hasattr(images, "_PNG_METADATA_CHUNKS"), (
        "`_PNG_METADATA_CHUNKS` is back. If it is to exist it must be read "
        "by something — a message, an assertion — or it is a list claiming "
        "coverage that the ancillary property already provides."
    )


def test_every_appn_is_removed_not_just_the_ones_on_a_list(jpeg_with_exif):
    """**Rule 11: ask the property.** A list of "the metadata markers" gains
    an entry every time someone meets a new one, and the one it does not have
    is the one carrying the GPS tag. The rule is *is it an APPn or a COM*,
    which is a property of the JPEG specification and not of our knowledge.
    """
    import struct

    # APP13 is Photoshop/IPTC and carries a caption and a byline. It is not
    # APP1 and a hand-written list would plausibly have missed it.
    app13 = b"\xff\xed" + struct.pack(">H", 2 + 11) + b"Photoshop3\x00"
    doctored = jpeg_with_exif[:2] + app13 + jpeg_with_exif[2:]
    stripped, _f, _w, _h = strip_metadata(doctored)
    assert b"Photoshop3" not in stripped
    assert b"\xff\xed" not in stripped


@pytest.mark.parametrize(
    "data,why",
    [
        (b"", "empty"),
        (b"not an image at all", "plain text"),
        (b"<!doctype html><html></html>", "an HTML document named .jpg"),
        (b"\xff\xd8\xff", "a JPEG header and nothing else"),
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 8, "a PNG signature with a broken chunk"),
        (b"%PDF-1.4\n", "a PDF"),
        (b"GIF89a", "a GIF, which is not one of the three permitted formats"),
    ],
)
def test_a_file_that_is_not_one_of_the_three_formats_is_rejected(data, why):
    """**Decided by the magic bytes, never by the filename or the client's
    `Content-Type`** — both are attacker-controlled on an upload, and a `.jpg`
    that is an HTML document is the oldest trick there is."""
    with pytest.raises(ImageRejected):
        strip_metadata(data)


def test_a_truncated_segment_length_is_rejected_rather_than_read_past(jpeg_with_exif):
    """A length word that runs past the end of the buffer is the classic
    container-parser bug. The parser refuses rather than slicing."""
    import struct

    broken = bytearray(jpeg_with_exif)
    # Overstate the APP1 length so it claims to extend beyond the file.
    broken[4:6] = struct.pack(">H", 60000)
    with pytest.raises(ImageRejected):
        strip_metadata(bytes(broken))


# --- the service: the row cannot exist without the strip ------------------


def test_a_photo_row_carries_exif_stripped_at_and_the_stored_bytes_are_clean(
    seller, book, jpeg_with_exif
):
    """**The structural guarantee and the behavioural one, together.**

    The column is NOT NULL, so the row cannot exist unstamped. That is the
    floor. What this adds is the thing the floor cannot prove: the file on
    disk has no EXIF in it.
    """
    listing = _listing(seller, book)
    photo = services.add_photo(seller, listing, _upload(jpeg_with_exif))

    assert photo.exif_stripped_at is not None
    assert photo.width == 2 and photo.height == 3
    assert photo.bytes < len(jpeg_with_exif)

    stored = read_object(photo.storage_key)
    assert stored is not None, "the row exists and the object does not"
    assert b"Exif\x00\x00" not in stored, (
        "the stored bytes still carry EXIF — the row says they were stripped "
        "and the file says otherwise, which is the exact gap the NOT NULL "
        "column cannot see"
    )
    assert photo.sha256 == __import__("hashlib").sha256(stored).hexdigest(), (
        "the recorded digest is of something other than what was stored"
    )


def test_the_original_is_never_written_anywhere(seller, book, jpeg_with_exif):
    """Stronger than stripping on read: there is no copy to leak later.

    A derivative pipeline that kept originals would satisfy *"EXIF stripped
    before the row exists"* in the letter and keep the GPS tag on disk for a
    year.
    """
    from apps.listings.storage import media_root

    listing = _listing(seller, book)
    services.add_photo(seller, listing, _upload(jpeg_with_exif))
    for path in media_root().rglob("*"):
        if path.is_file():
            assert b"Exif\x00\x00" not in path.read_bytes(), f"{path} carries EXIF"


def test_a_fifth_photo_is_refused_with_the_count(seller, book, jpeg_with_exif):
    """DATA-MODEL §3's cap, and JOURNEYS J2 step 8's *"refused with the count
    shown"*. Each upload is a distinct image so the content-hash key does not
    make four uploads one file."""
    listing = _listing(seller, book)
    for index in range(4):
        # **Four genuinely different images.** The first draft varied a COM
        # comment segment — which this module strips — so all four hashed
        # identically, collided on the content-addressed key, and surfaced a
        # real defect: the same photo twice on one listing was an
        # `IntegrityError` and a 500. That is a refusal with a sentence now
        # (the test above), and these vary the width so four uploads are four
        # photos rather than one.
        services.add_photo(seller, listing, _upload(_jpeg(width=2 + index)))
    with pytest.raises(TooManyPhotos) as caught:
        services.add_photo(seller, listing, _upload(_jpeg(width=99)))
    assert caught.value.context["photo_count"] == 4
    assert caught.value.http_status == 422


def test_an_oversized_photo_is_refused_before_it_is_parsed(seller, book):
    """8 MB, API-CONTRACT §5.2. Checked on the byte count **before** the
    parser runs, so a 40 MB file is not walked segment by segment first."""
    listing = _listing(seller, book)
    with pytest.raises(UnsupportedImage):
        services.add_photo(seller, listing, _upload(b"\xff\xd8\xff" + b"\x00" * (9 * 1024 * 1024)))


def test_an_unsupported_format_names_the_formats(seller, book):
    """JOURNEYS J2 step 8: *"refused, format list given."*"""
    listing = _listing(seller, book)
    with pytest.raises(UnsupportedImage) as caught:
        services.add_photo(seller, listing, _upload(b"GIF89a" + b"\x00" * 50))
    assert "JPEG" in str(caught.value)


def test_a_rejected_upload_leaves_no_row_and_no_file(seller, book):
    """The two must fail together. A file with no row is a leak the retention
    job will never find, because the job walks rows."""
    from apps.listings.models import ListingPhoto
    from apps.listings.storage import media_root

    listing = _listing(seller, book)
    before = {p for p in media_root().rglob("*") if p.is_file()}
    with pytest.raises(UnsupportedImage):
        services.add_photo(seller, listing, _upload(b"nonsense"))
    assert not ListingPhoto.all_objects.filter(listing=listing).exists()
    assert {p for p in media_root().rglob("*") if p.is_file()} == before


def test_photos_inherit_the_listings_campus_and_seed_flag(seller, book, jpeg_with_exif):
    """ADR-002 §2 names `listing_photos` as tenant-scoped, and the gated
    manager needs `is_seed`. Both are denormalised from the listing at insert
    rather than joined, which is the same decision `city_id` carries."""
    listing = _listing(seller, book)
    photo = services.add_photo(seller, listing, _upload(jpeg_with_exif))
    assert photo.campus_id == listing.campus_id
    assert photo.city_id == listing.city_id
    assert photo.is_seed == listing.is_seed


def test_a_photo_cannot_be_added_to_someone_elses_listing(
    seller, book, pending_student, privacy_notice, jpeg_with_exif
):
    from apps.accounts.services import grant_consent
    from apps.core.errors import NotFound

    listing = _listing(seller, book)
    pending_student.status = "ACTIVE"
    pending_student.adult_verified = True
    pending_student.save(update_fields=["status", "adult_verified"])
    grant_consent(pending_student, "account", privacy_notice, "SIGNUP_FORM", None, "pytest")
    grant_consent(pending_student, "listing_publication", privacy_notice, "SIGNUP_FORM", None, "x")
    with pytest.raises(NotFound):
        services.add_photo(pending_student, listing, _upload(jpeg_with_exif))


# --- storage: containment and idempotent deletion -------------------------


@pytest.mark.parametrize(
    "key", ["../escape.jpg", "a/../../escape.jpg", "/etc/passwd", "listings/../../x"]
)
def test_a_storage_key_cannot_escape_the_media_root(key):
    """The keys this app generates are safe by construction — but
    `delete_object` is called by the retention job with a key read back **out
    of the database**, and a control that depends on nobody ever writing a bad
    row is the shape rule 10 is about. Asked as containment of the resolved
    path, not as a scan for `..`, because a list of dangerous sequences cannot
    express a symlink."""
    from apps.listings.storage import object_path

    with pytest.raises(ValueError):
        object_path(key)


def test_deleting_an_object_twice_is_not_an_error():
    """The retention job is at-least-once (API-CONTRACT §4.4), so the second
    run must find nothing to do rather than fail."""
    from apps.listings.storage import delete_object, write_object

    write_object("listings/test/idempotent.jpeg", b"x")
    assert delete_object("listings/test/idempotent.jpeg") is True
    assert delete_object("listings/test/idempotent.jpeg") is False


# --- the retention job, which ships in the slice that creates the clock ---


def test_the_purge_job_deletes_the_bytes_and_keeps_the_row(seller, book, jpeg_with_exif):
    """DATA-MODEL §10.2 and `COMPLIANCE.md` §8.3.

    **Tombstone-plus-purge, applied to a photo**: the bytes are the personal
    data and go; the row is what proves a listing had four photos when a
    dispute is read a year later, and stays with a `purge_log` entry.
    """
    from django.utils import timezone

    from apps.core.models import PurgeLog
    from apps.listings.jobs import purge_media
    from apps.listings.models import ListingPhoto

    listing = _listing(seller, book)
    photo = services.add_photo(seller, listing, _upload(jpeg_with_exif))
    key = photo.storage_key

    # Not yet due.
    ListingPhoto.all_objects.filter(id=photo.id).update(
        purge_due_at=timezone.now() + timezone.timedelta(days=1)
        if hasattr(timezone, "timedelta")
        else None
    )
    photo.refresh_from_db()
    if photo.purge_due_at:
        assert purge_media({})["photos"] == 0
        assert read_object(key) is not None

    ListingPhoto.all_objects.filter(id=photo.id).update(
        purge_due_at=timezone.now() - __import__("datetime").timedelta(days=1)
    )
    assert purge_media({})["photos"] == 1
    assert read_object(key) is None
    photo.refresh_from_db()
    assert photo.storage_key is None, "the key must go NULL, not empty — the column is UNIQUE"
    assert photo.id, "the row itself survives its bytes"
    assert PurgeLog.objects.filter(table_name="listing_photos", object_pk=str(photo.id)).exists()


def test_the_purge_job_is_idempotent(seller, book, jpeg_with_exif):
    """A second run in the same night finds nothing left and writes no rows."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.core.models import PurgeLog
    from apps.listings.jobs import purge_media
    from apps.listings.models import ListingPhoto

    listing = _listing(seller, book)
    photo = services.add_photo(seller, listing, _upload(jpeg_with_exif))
    ListingPhoto.all_objects.filter(id=photo.id).update(
        purge_due_at=timezone.now() - timedelta(days=1)
    )
    assert purge_media({})["photos"] == 1
    assert purge_media({})["photos"] == 0
    assert PurgeLog.objects.filter(table_name="listing_photos").count() == 1


def test_erasure_starts_the_photo_clock_on_an_open_listing(seller, book, jpeg_with_exif):
    """DATA-MODEL §10.1 step 5, and the half that is easy to miss.

    A listing that is still open has no `closed_at`, so `purge_due_at` would
    be NULL and its photos would **never** expire. Erasure withdraws the
    listing, which both closes something the seller can no longer manage and
    starts the retention clock on its photos.
    """
    from apps.accounts.services import erase_account
    from apps.listings.models import Listing, ListingPhoto

    listing = _listing(seller, book)
    photo = services.add_photo(seller, listing, _upload(jpeg_with_exif))
    assert photo.purge_due_at is None

    erase_account(seller)

    listing.refresh_from_db()
    photo.refresh_from_db()
    assert listing.status == "WITHDRAWN"
    assert listing.seller_id is None, "step 6: the FK is NULL"
    assert listing.seller_pseudonym is not None, "step 6: the pseudonym survives"
    assert photo.purge_due_at is not None, (
        "step 5: an open listing's photos would otherwise never expire"
    )
    assert Listing.all_objects.filter(id=listing.id).exists(), (
        "deletion is tombstone-plus-purge; the listing row is not DELETEd"
    )
    assert ListingPhoto.all_objects.filter(id=photo.id).exists()
