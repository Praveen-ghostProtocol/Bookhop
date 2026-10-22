"""RED TEAM PROBE · S2 per-slice pass. **Not a regression test.**

Subject: *"a photo of a used textbook is a photo of wherever that student
lives."*

`apps/listings/images.py` claims, and `listing_photos.exif_stripped_at NOT
NULL` encodes as a structural guarantee, that **"every metadata segment that
can carry EXIF, GPS, XMP or a comment is gone from the bytes that are
written."** The module is labelled `VERIFIED HERE … ASSUMED THERE: nothing`.

The probe is not "does it strip the APP1 it was given" — unit tests cover
that. It is **what a real mid-range Android actually produces**, and whether
the byte arithmetic walks all of it.

The case: every current Samsung and Pixel phone, with Motion Photo / Top Shot
on by default, writes a complete secondary media stream **after the primary
image's EOI marker**. Multi-Picture Format (MPF, CIPA DC-007) does the same
with a second full JPEG — which carries its **own, unstripped, APP1 EXIF**.
"""

import struct

import pytest

from apps.listings.images import strip_metadata


def _exif_app1(gps_ref=b"N"):
    """An APP1 segment with a GPS IFD pointer — the tag that is a home address."""
    body = b"Exif\x00\x00II*\x00" + struct.pack("<I", 8)
    body += struct.pack("<H", 1) + struct.pack("<HHII", 0x8825, 4, 1, 26)
    body += b"\x00\x00\x00\x00" + b"GPSLAT" + gps_ref
    return b"\xff\xe1" + struct.pack(">H", len(body) + 2) + body


def _jpeg(width=12, height=9, *, exif=True, appended=b""):
    """A structurally valid JPEG. `appended` lands **after the EOI marker**,
    which is where a phone puts the second stream."""
    parts = [b"\xff\xd8"]
    if exif:
        parts.append(_exif_app1())
    parts.append(
        b"\xff\xc0" + struct.pack(">H", 11) + bytes((8,))
        + struct.pack(">HH", height, width) + bytes((1, 1, 0x11, 0))
    )
    parts.append(b"\xff\xda" + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0)))
    parts.append(b"\x10\x20\x30")          # entropy-coded data
    parts.append(b"\xff\xd9")              # EOI — the image ends HERE
    parts.append(appended)                 # …and this is still in the file
    return b"".join(parts)


def test_the_primary_images_own_exif_really_is_removed():
    """**The control works on what it was aimed at.** Asserted first, so a
    failure below cannot be read as "the stripper is broken"."""
    stripped, fmt, w, h = strip_metadata(_jpeg())
    assert fmt == "jpeg" and (w, h) == (12, 9)
    assert b"Exif" not in stripped
    assert b"GPSLAT" not in stripped


def test_everything_after_the_eoi_marker_is_copied_into_storage():
    """**FINDING, if red.** A trailing payload survives the strip verbatim.

    `_strip_jpeg` handles SOS with `out += data[i:]; break` — from the scan
    header to the **end of the file**, not to the EOI two bytes later. So the
    segment walk stops and everything past the image is appended unexamined.
    """
    secret = b"MOTIONPHOTO-SECOND-STREAM-" + b"\x00ftypmp42" + _exif_app1(b"S")
    stripped, _, _, _ = strip_metadata(_jpeg(appended=secret))

    assert secret not in stripped, (
        "FINDING. %d bytes placed after the JPEG EOI marker were copied "
        "verbatim into the stored object, including a second APP1/EXIF block "
        "with a GPS tag. The stripper never walks past SOS."
        % len(secret)
    )


def test_a_second_whole_jpeg_concatenated_after_eoi_keeps_its_gps():
    """The MPF / Motion Photo shape exactly: image, EOI, then another image.

    This is the one that matters for the product claim, because the appended
    bytes are not noise — they are a *second photograph of the same room*,
    with its own untouched EXIF.
    """
    second = _jpeg(width=4000, height=3000, exif=True, appended=b"")
    stripped, _, w, h = strip_metadata(_jpeg(appended=second))

    assert (w, h) == (12, 9), "the dimensions read belong to the first frame"
    assert b"Exif" not in stripped, (
        "FINDING. A concatenated second JPEG survives the strip with its EXIF "
        "APP1 intact. `exif_stripped_at NOT NULL` is therefore not the "
        "structural guarantee the model docstring says it is."
    )


def test_png_drops_the_same_payload_and_the_asymmetry_is_undocumented():
    """**Both sides are rows.** PNG stops at IEND; JPEG does not stop at EOI.

    Recorded because the asymmetry is the evidence that the JPEG behaviour is
    an oversight rather than a decision — nothing in the module names it.
    """
    png = (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 5, 4)
        + b"\x08\x02\x00\x00\x00" + b"\x00\x00\x00\x00"
        + struct.pack(">I", 0) + b"IEND" + b"\x00\x00\x00\x00"
    )
    appended = b"PNG-TRAILING-SECRET"
    stripped, fmt, _, _ = strip_metadata(png + appended)
    assert fmt == "png"
    assert appended not in stripped, "PNG also keeps trailing bytes"


def test_the_stored_object_is_the_stripped_bytes_so_the_leak_reaches_disk(
    seller, book, settings, tmp_path
):
    """Closes the loop: not a library curiosity, a file on the pilot's VM.

    `add_photo` hashes and writes exactly what `strip_metadata` returned, and
    `photo_response` serves that file. So whatever survives here is what an
    authorised buyer downloads.
    """
    import io

    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.listings import services
    from apps.listings.storage import read_object

    listing = services.create_listing(
        seller, book=book, asking_price_paise=19900, condition="GOOD",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    secret = b"HOME-ADDRESS-IN-THE-SECOND-STREAM"
    buf = io.BytesIO(_jpeg(appended=secret))
    buf.name = "IMG_20261022.jpg"
    photo = services.add_photo(seller, listing, buf)

    on_disk = read_object(photo.storage_key)
    assert secret not in on_disk, (
        "FINDING. The payload appended after EOI is on disk under MEDIA_ROOT, "
        f"inside {photo.storage_key!r}, and `exif_stripped_at` is set to "
        f"{photo.exif_stripped_at!r} — the row asserts the strip happened."
    )
