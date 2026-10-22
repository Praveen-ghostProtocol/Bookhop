r"""F47 regression — nothing past the end of the image reaches storage.

Red Team measured 78 bytes placed after a JPEG's EOI marker, including an
APP1 block with a GPS tag, arriving on disk **with `exif_stripped_at` set**.
This is the regression, in backend's tree, written at the boundary the
documents claim rather than at the one the probe used:

  * `apps/listings/images.py` claims *"every metadata segment that can carry
    EXIF, GPS, XMP or a comment is gone from the bytes that are written"* —
    so the assertion is about **the bytes that are written**, which means the
    file under `MEDIA_ROOT`, not only `strip_metadata`'s return value. Both
    are asserted; the second is the claim.
  * **Both sides are rows** (`CLAUDE.md` rule 10's corollary). A rule that
    drops trailing data must still keep a legitimate file intact, so every
    container has a must-keep case beside its must-drop case. A stripper that
    returned `b""` would pass a drop-only suite.
  * **All three accepted containers**, because *"the other formats do not
    have this problem"* was a claim until it was measured. PNG was already
    correct; WebP was not.
"""

import io
import struct

import pytest

pytestmark = pytest.mark.django_db


# --- containers ------------------------------------------------------------
#
# Built here rather than imported from `apps/**`: a test that asks the subject
# to build its own input measures the subject twice.


def _app1_with_gps(marker=b"N"):
    body = b"Exif\x00\x00II*\x00" + struct.pack("<I", 8)
    body += struct.pack("<H", 1) + struct.pack("<HHII", 0x8825, 4, 1, 26)
    body += b"\x00\x00\x00\x00" + b"GPSLATITUDE" + marker
    return b"\xff\xe1" + struct.pack(">H", len(body) + 2) + body


def _jpeg(width=12, height=9, *, exif=True, scans=1, appended=b""):
    parts = [b"\xff\xd8"]
    if exif:
        parts.append(_app1_with_gps())
    parts.append(
        b"\xff\xc0" + struct.pack(">H", 11) + bytes((8,))
        + struct.pack(">HH", height, width) + bytes((1, 1, 0x11, 0))
    )
    for scan in range(scans):
        parts.append(b"\xff\xda" + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0)))
        # Entropy-coded data containing a stuffed 0xFF and a restart marker,
        # so the scan walk is exercised on the two byte sequences that are
        # NOT markers. A walk that stopped at either would truncate a real
        # photograph, which is the failure mode opposite to F47's.
        parts.append(b"\x10\xff\x00\x20\xff\xd0\x30")
        if scan + 1 < scans:
            # A metadata segment BETWEEN two scans: unreachable by the old
            # code, which copied everything from the first SOS onward.
            parts.append(_app1_with_gps(b"S"))
    parts.append(b"\xff\xd9")
    return b"".join(parts) + appended


def _png(appended=b""):
    import zlib

    def chunk(kind, payload):
        return (
            struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    return b"".join([
        b"\x89PNG\r\n\x1a\n",
        chunk(b"IHDR", struct.pack(">IIBBBBB", 5, 4, 8, 0, 0, 0, 0)),
        chunk(b"tEXt", b"Comment\x00taken at home"),
        chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00\x00" * 4)),
        chunk(b"IEND", b""),
    ]) + appended


def _webp(appended=b""):
    def chunk(kind, payload):
        return kind + struct.pack("<I", len(payload)) + payload + (b"\x00" * (len(payload) & 1))

    vp8l = chunk(b"VP8L", b"\x2f" + struct.pack("<I", (3 << 14) | 4) + b"\x00" * 3)
    exif = chunk(b"EXIF", b"II*\x00GPSLATITUDE")
    body = b"WEBP" + vp8l + exif
    return b"RIFF" + struct.pack("<I", len(body)) + body + appended


# --- the must-drop side ----------------------------------------------------

#: The Motion Photo / MPF shape: a payload that is not noise but a second
#: media stream with its own untouched EXIF.
SECOND_STREAM = b"MOTIONPHOTO" + b"\x00ftypmp42" + _app1_with_gps(b"S")


@pytest.mark.parametrize(
    ("container", "build"),
    [("jpeg", _jpeg), ("png", _png), ("webp", _webp)],
)
def test_bytes_appended_after_the_container_ends_do_not_survive(container, build):
    """**The property, asked of all three containers.**

    Parametrised rather than written three times so a fourth accepted format
    is one row (`CLAUDE.md` rule 11) — and so no container can be quietly
    dropped from the sweep.
    """
    from apps.listings.images import strip_metadata

    stripped, fmt, _, _ = strip_metadata(build(appended=SECOND_STREAM))
    assert fmt == container
    assert SECOND_STREAM not in stripped
    assert b"MOTIONPHOTO" not in stripped
    assert b"GPSLATITUDE" not in stripped


def test_a_second_whole_jpeg_after_the_first_keeps_nothing():
    """MPF exactly: image, EOI, another complete image with its own EXIF."""
    from apps.listings.images import strip_metadata

    stripped, _, width, height = strip_metadata(
        _jpeg(appended=_jpeg(width=4000, height=3000))
    )
    assert (width, height) == (12, 9), "the dimensions belong to the primary frame"
    assert b"Exif" not in stripped
    assert stripped.endswith(b"\xff\xd9")
    assert stripped.count(b"\xff\xd9") == 1


def test_a_metadata_segment_between_two_scans_is_stripped_too():
    """The progressive case the old `out += data[i:]` could not reach.

    This is the second half of the same defect and it is **not** what the
    probe measured: the probe appended after EOI, where a phone writes. A
    progressive JPEG carries segments between its scans, and copying from the
    first SOS to the end of the file copied those as well.
    """
    from apps.listings.images import strip_metadata

    stripped, _, _, _ = strip_metadata(_jpeg(scans=3))
    assert b"Exif" not in stripped
    assert b"GPSLATITUDE" not in stripped
    assert stripped.count(b"\xff\xda") == 3, "all three scans survived"


def test_a_jpeg_with_no_eoi_is_refused_rather_than_stored_to_an_unknown_end():
    """**The branch that makes the truncation decidable.**

    If the file never says where it ends, there is no "truncate at EOI" to
    perform. Refusing is the conservative half and it is asserted here so the
    `saw_eoi` branch is exercised — an unexercised refusal path is
    `CLAUDE.md` rule 10's last bullet.
    """
    from apps.listings.images import ImageRejected, strip_metadata

    truncated = _jpeg()[:-2]
    with pytest.raises(ImageRejected, match="EOI"):
        strip_metadata(truncated)


# --- the must-keep side ----------------------------------------------------


@pytest.mark.parametrize(
    ("container", "build", "magic", "size"),
    [
        ("jpeg", _jpeg, b"\xff\xd8", (12, 9)),
        ("png", _png, b"\x89PNG\r\n\x1a\n", (5, 4)),
        ("webp", _webp, b"RIFF", (5, 4)),
    ],
)
def test_an_ordinary_file_still_round_trips(container, build, magic, size):
    """**The other side of the rule.** A stripper that dropped everything
    would pass every assertion above; these are the rows that fail it.

    The dimensions are asserted exactly, so a container whose body was
    truncated into unreadability cannot pass by returning something.
    """
    from apps.listings.images import strip_metadata

    stripped, fmt, width, height = strip_metadata(build())
    assert fmt == container
    assert stripped.startswith(magic)
    assert (width, height) == size
    assert b"GPSLATITUDE" not in stripped


def test_the_jpeg_entropy_walk_does_not_stop_at_a_stuffed_ff_or_a_restart():
    """A scan's payload contains `FF 00` and `FF D0`; neither ends it.

    Without this the fix is a truncation bug: every real photograph's
    entropy stream is full of stuffed `0xFF` bytes.
    """
    from apps.listings.images import strip_metadata

    stripped, _, _, _ = strip_metadata(_jpeg())
    assert b"\x10\xff\x00\x20\xff\xd0\x30" in stripped


def test_a_fill_byte_before_the_end_marker_does_not_end_the_scan_early():
    """`_jpeg_entropy_end`'s third branch, which had no fixture.

    An encoder may pad with `0xFF` bytes before a marker, so `FF FF D9` is a
    legal end-of-image. The walk must step over the fill and return the
    `FF` that begins the real marker — one byte earlier and the EOI is
    mis-parsed, one byte later and it is missed entirely.

    Review's note, and rule 10: a reachable branch asserted by nothing is
    not covered by the branches around it.
    """
    from apps.listings.images import strip_metadata

    padded = _jpeg()[:-2] + b"\xff\xff\xd9"
    stripped, _fmt, width, height = strip_metadata(padded)
    assert (width, height) == (12, 9)
    assert stripped.endswith(b"\xff\xff\xd9"), "the fill byte and the EOI both survive"
    assert b"GPSLATITUDE" not in stripped


def test_a_frame_header_with_no_scan_at_all_is_still_a_whole_image():
    """The other branch with no fixture: the entropy walk is never entered.

    A JPEG may carry a frame header and no scan — the segment loop runs to
    the EOI without ever calling `_jpeg_entropy_end`. It has dimensions and
    an EOI, so it is a complete file and must be accepted, stripped, rather
    than refused by either of `_strip_jpeg`'s two `ImageRejected` paths.
    """
    from apps.listings.images import strip_metadata

    stripped, _fmt, width, height = strip_metadata(_jpeg(scans=0))
    assert (width, height) == (12, 9)
    assert b"GPSLATITUDE" not in stripped
    assert stripped.endswith(b"\xff\xd9")


# --- the claim, at the boundary the documents make it ----------------------


def test_the_object_written_under_media_root_carries_none_of_it(
    seller, book, settings, tmp_path
):
    """**`exif_stripped_at` must not be set on a row whose file has a GPS tag.**

    `apps/listings/models.py` calls that column *"the whole control"* and
    `COMPLIANCE.md` §7 row 9 is the reason. The assertion is therefore on the
    bytes under `MEDIA_ROOT` and on the column together — a schema guarantee
    about a *state* cannot detect a *bad input* (rule 12), so the input is
    what is checked here.
    """
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.listings import services
    from apps.listings.storage import read_object

    listing = services.create_listing(
        seller, book=book, asking_price_paise=19900, condition="GOOD",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    buf = io.BytesIO(_jpeg(appended=b"HOME-ADDRESS" + _app1_with_gps(b"S")))
    buf.name = "IMG_20261022.jpg"
    photo = services.add_photo(seller, listing, buf)

    on_disk = read_object(photo.storage_key)
    assert photo.exif_stripped_at is not None
    assert b"HOME-ADDRESS" not in on_disk
    assert b"GPSLATITUDE" not in on_disk
    assert b"Exif" not in on_disk
    assert on_disk.endswith(b"\xff\xd9")
    assert photo.bytes == len(on_disk), (
        "the recorded size must be the size of what was written, or the "
        "truncation happened somewhere the row does not know about"
    )
