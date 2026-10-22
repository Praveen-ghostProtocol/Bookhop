r"""The EXIF stripper, attacked with the shapes a camera actually produces.

**Why this file exists on top of `test_nothing_past_the_end_of_the_image.py`.**
That file asserts the property F47 named — nothing past the declared end of
the image reaches storage — on fixtures built to carry it. Code Review
verified the new `_jpeg_entropy_end` walk's termination and bounds **by
reading**. This file verifies them **by running**, against the four shapes a
phone camera in Chennai emits and the three shapes a truncated upload emits,
plus a bounded mutation fuzz that asserts the parser cannot be made to hang
or to raise anything other than `ImageRejected`.

**The stake, stated once:** a used-textbook photograph is taken on a desk in
a student's room. An APP1 that survives carries a GPS IFD. `exif_stripped_at`
is `NOT NULL` on the row, so a byte that survives is a byte the schema
promises is gone.

No database, no fixtures, no network: this is byte arithmetic over
`apps.listings.images`, which is what makes it cheap enough to fuzz.

Every assertion names the shape it failed on, because "the stripper is
broken" is not a bug report.
"""

import random
import struct
import time

import pytest

from apps.listings.images import ImageRejected, strip_metadata

# --- what must never survive -------------------------------------------------

#: A distinctive run planted inside every metadata payload below. If this
#: appears in the stripped output the segment survived, whatever the marker
#: arithmetic says.
CANARY = b"GPS-13.0827N-80.2707E-CANARY"

#: Container-level markers of metadata that must not be in the output.
FORBIDDEN = (
    (b"Exif\x00\x00", "an EXIF APP1"),
    (b"http://ns.adobe.com/xap/1.0/", "an XMP APP1"),
    (b"MPF\x00", "an MPF (CIPA DC-007) APP2 index"),
    (b"ftyp", "an ISO-BMFF box — a Motion Photo video trailer"),
    (CANARY, "the planted GPS canary"),
)


# --- JPEG construction -------------------------------------------------------


def _seg(marker, payload):
    """One length-prefixed JPEG segment."""
    return bytes((0xFF, marker)) + struct.pack(">H", len(payload) + 2) + payload


def _exif_app1_with_gps():
    """An APP1 shaped like a real EXIF block, with a GPS IFD pointer.

    Not a decoder test — nothing parses this — but the *shape* is real so
    that a stripper keying off `Exif\\x00\\x00`, off the TIFF magic, or off
    the GPS tag id all have something to key off, and so the canary sits
    where a real latitude sits.
    """
    tiff = b"II*\x00" + struct.pack("<I", 8)
    ifd0 = struct.pack("<H", 1) + struct.pack("<HHII", 0x8825, 4, 1, 26) + struct.pack("<I", 0)
    gps = struct.pack("<H", 1) + struct.pack("<HHII", 0x0002, 2, len(CANARY), 44)
    gps += struct.pack("<I", 0) + CANARY
    return _seg(0xE1, b"Exif\x00\x00" + tiff + ifd0 + gps)


def _xmp_app1():
    return _seg(
        0xE1,
        b"http://ns.adobe.com/xap/1.0/\x00"
        b'<x:xmpmeta><GCamera:MotionPhoto>1</GCamera:MotionPhoto>' + CANARY + b"</x:xmpmeta>",
    )


def _exif_app1_with_embedded_thumbnail():
    """An EXIF APP1 whose payload contains a whole JPEG thumbnail.

    **This is the trap the `find(b"\\xff\\xd9")` shortcut falls into**, and
    it is not exotic — every phone that writes EXIF writes a thumbnail, and
    that thumbnail has its own SOI and its own EOI *inside* the APP1 payload
    of the primary image. A stripper that located the end of the image by
    searching for the first `FF D9` would truncate the file here, before the
    real image data has even started.
    """
    thumb = b"\xff\xd8" + _seg(0xDB, b"\x00" + b"\x10" * 64)
    thumb += _seg(0xC0, b"\x08\x00\x10\x00\x10\x01\x01\x11\x00") + b"\xff\xd9"
    return _seg(0xE1, b"Exif\x00\x00II*\x00" + CANARY + thumb)


def _dqt():
    return _seg(0xDB, b"\x00" + b"\x10" * 64)


def _dht():
    return _seg(0xC4, b"\x00" + b"\x00" * 16 + b"\x00")


def _sof(marker=0xC0, width=1600, height=1200):
    return _seg(marker, struct.pack(">BHHB", 8, height, width, 1) + b"\x01\x11\x00")


def _sos(entropy):
    return _seg(0xDA, b"\x01\x01\x00\x00\x3f\x00") + entropy


#: Entropy-coded bytes that exercise the three things `_jpeg_entropy_end`
#: must not mistake for the end of a scan: byte stuffing, restart markers,
#: and a stuffed `FF 00` immediately followed by `D9` — which spells
#: `FF 00 D9` and is *not* an EOI, though a sloppy scanner reads one.
ENTROPY = (
    b"\x9a\x4b\xff\x00\x3c\xff\x00\xd9\x71"
    + b"\xff\xd0" + b"\x11\x22\xff\x00\x33"
    + b"\xff\xd1" + b"\x44\x55\x66"
    + b"\xff\xd7" + b"\x77\x88\xff\x00"
)


def _baseline(trailer=b"", with_metadata=True):
    out = b"\xff\xd8"
    if with_metadata:
        out += _exif_app1_with_gps() + _xmp_app1() + _seg(0xFE, b"comment " + CANARY)
    out += _dqt() + _sof() + _dht() + _sos(ENTROPY) + b"\xff\xd9"
    return out + trailer


def _motion_photo():
    """Google Motion Photo / Samsung Top Shot: a whole MP4 after EOI.

    The trailer carries an unstripped `ftyp` box and — in the real article —
    a video of the room. `_strip_jpeg` used to copy from SOS to
    `len(data)`, so all of it reached storage under a row stamped
    `exif_stripped_at`.
    """
    mp4 = struct.pack(">I", 24) + b"ftypmp42" + b"\x00" * 8 + CANARY
    mp4 += struct.pack(">I", 16) + b"moov" + b"\x00" * 8
    return _baseline(trailer=mp4)


def _mpf_multi_picture():
    """CIPA DC-007: an APP2 MPF index, then a second JPEG after the EOI.

    The second image carries **its own** EXIF APP1 with a GPS IFD, which is
    the exact sentence in the module docstring. The primary image's APP1 is
    stripped by marker; the second one is only stripped if the copy stops at
    the primary's EOI.
    """
    second = b"\xff\xd8" + _exif_app1_with_gps() + _dqt() + _sof(width=320, height=240)
    second += _dht() + _sos(b"\x01\x02\x03") + b"\xff\xd9"
    mpf = _seg(0xE2, b"MPF\x00II*\x00" + b"\x00" * 16)
    body = b"\xff\xd8" + mpf + _exif_app1_with_gps() + _dqt() + _sof() + _dht()
    body += _sos(ENTROPY) + b"\xff\xd9"
    return body + second


def _progressive_with_metadata_between_scans():
    """SOF2 and three scans, with an APP1 and a COM sitting between them.

    This is the shape the module docstring says the one-line `find` would
    have got wrong: *"the walk hands control back to the segment loop, which
    strips the metadata segments between them too."* A real progressive JPEG
    from a phone does not usually carry EXIF mid-stream, but an attacker's
    does, and the claim under test is the walk's, not the camera's.
    """
    out = b"\xff\xd8" + _exif_app1_with_gps() + _dqt() + _sof(marker=0xC2)
    out += _dht() + _sos(ENTROPY)
    out += _xmp_app1() + _dht() + _sos(ENTROPY)
    out += _seg(0xFE, b"between scans " + CANARY) + _dht() + _sos(ENTROPY)
    return out + b"\xff\xd9"


def _fill_bytes_before_every_marker():
    """`FF FF FF D8`-style padding, which the specification permits."""
    body = _baseline()
    return body.replace(b"\xff\xdb", b"\xff\xff\xff\xdb", 1).replace(
        b"\xff\xd9", b"\xff\xff\xd9", 1
    )


ACCEPTED = {
    "baseline-with-exif-xmp-and-comment": _baseline,
    "motion-photo-mp4-trailer": _motion_photo,
    "mpf-second-image-with-its-own-gps": _mpf_multi_picture,
    "progressive-metadata-between-scans": _progressive_with_metadata_between_scans,
    "exif-app1-containing-a-jpeg-thumbnail": lambda: (
        b"\xff\xd8" + _exif_app1_with_embedded_thumbnail() + _dqt() + _sof()
        + _dht() + _sos(ENTROPY) + b"\xff\xd9"
    ),
    "fill-bytes-before-markers": _fill_bytes_before_every_marker,
    "no-metadata-at-all": lambda: _baseline(with_metadata=False),
}


# --- the accepted shapes -----------------------------------------------------


@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_a_real_world_shape_is_accepted_and_carries_no_metadata_out(name):
    """Accepted, dimensions read, and not one forbidden run survives.

    Both halves in one test on purpose: a stripper that refused every one of
    these would pass a "no metadata survives" assertion vacuously, and a
    stripper that accepted them and copied everything would pass an
    "accepted" assertion. Neither is the property.
    """
    data = ACCEPTED[name]()
    stripped, fmt, width, height = strip_metadata(data)

    assert fmt == "jpeg", f"{name}: detected as {fmt!r}"
    assert (width, height) != (0, 0), f"{name}: no dimensions"
    assert stripped.startswith(b"\xff\xd8\xff"), f"{name}: output is not a JPEG"
    assert stripped.endswith(b"\xff\xd9"), (
        f"{name}: output does not end at an EOI, so where it ends is unknown"
    )
    for needle, what in FORBIDDEN:
        assert needle not in stripped, (
            f"{name}: {what} survived the strip. `exif_stripped_at` is "
            f"NOT NULL on listing_photos, so this row would claim a "
            f"guarantee the bytes do not hold."
        )


@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_the_output_stops_at_the_first_eoi_and_nothing_follows(name):
    """The F47 property stated as arithmetic, not as a substring search.

    The output must contain exactly one EOI and it must be the last two
    bytes. A trailer that re-entered the output anywhere — including spliced
    into the middle, which a substring check for the trailer would still
    catch but a length check would not — fails here.
    """
    data = ACCEPTED[name]()
    stripped, _fmt, _w, _h = strip_metadata(data)
    eoi = b"\xff\xd9"
    assert stripped.count(eoi) == 1, (
        f"{name}: {stripped.count(eoi)} EOI markers in the output; "
        "the copy did not stop at the first one"
    )
    trailing = len(stripped) - 2 - stripped.rindex(eoi)
    assert trailing == 0, (
        f"{name}: {trailing} bytes follow the EOI in the stored object"
    )


@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_stripping_is_idempotent(name):
    """Strip twice, get the same bytes.

    Not decoration: `purge_media`, a restore and a re-upload all re-run this
    path over bytes it has already produced, and a second pass that changed
    the object would change its `sha256` — which is the storage key's content
    half and the UNIQUE `(listing_id, sha256)` the 0004 migration adds.
    """
    once, _f, w1, h1 = strip_metadata(ACCEPTED[name]())
    twice, _f2, w2, h2 = strip_metadata(once)
    assert twice == once, f"{name}: a second strip changed the bytes"
    assert (w1, h1) == (w2, h2), f"{name}: dimensions moved on the second pass"


# --- the refused shapes ------------------------------------------------------

REFUSED = {
    "soi-only": b"\xff\xd8",
    "soi-and-a-dangling-ff": b"\xff\xd8\xff",
    "truncated-inside-a-segment-header": _baseline()[:4],
    "truncated-inside-a-segment-payload": _baseline()[: len(_baseline()) // 3],
    "truncated-inside-the-entropy-stream": _baseline()[:-1],
    "eoi-removed-entirely": _baseline()[:-2],
    "all-markers-no-frame-header": b"\xff\xd8" + b"\xff\xd0" * 4000 + b"\xff\xd9",
    "segment-length-past-the-end": b"\xff\xd8" + b"\xff\xe1\xff\xff" + b"x" * 8,
    "segment-length-below-the-minimum": b"\xff\xd8" + b"\xff\xe1\x00\x01" + b"x" * 8,
    "frame-header-too-short-for-dimensions": (
        b"\xff\xd8" + _seg(0xC0, b"\x08\x00") + _sos(b"\x01") + b"\xff\xd9"
    ),
    "non-marker-byte-where-a-marker-must-be": b"\xff\xd8" + b"\x41" * 32 + b"\xff\xd9",
}


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_broken_or_truncated_file_is_refused_by_name(name):
    """Refused with `ImageRejected`, never with a bare exception.

    The exception type is the contract: `add_photo` catches `ImageRejected`
    and renders the student's sentence. Anything else is a 500 on an upload,
    which is a denial of service any student can trigger with a dropped
    connection mid-upload.
    """
    with pytest.raises(ImageRejected) as caught:
        strip_metadata(REFUSED[name])
    assert str(caught.value), f"{name}: refused with an empty reason"


def test_a_truncated_upload_never_yields_a_half_image():
    """Every prefix of a valid JPEG is either refused or ends at an EOI.

    The shape a dropped 3G connection produces, asked of **every** cut point
    rather than of three chosen ones. A prefix that came back accepted with
    bytes that do not end at an EOI would be an object whose end nobody can
    locate — the state the `saw_eoi` refusal was added to prevent.
    """
    whole = _baseline()
    accepted_prefixes = 0
    for cut in range(1, len(whole) + 1):
        try:
            stripped, _f, _w, _h = strip_metadata(whole[:cut])
        except ImageRejected:
            continue
        accepted_prefixes += 1
        assert stripped.endswith(b"\xff\xd9"), (
            f"a {cut}-byte prefix was accepted and does not end at an EOI"
        )
    assert accepted_prefixes == 1, (
        "exactly the whole file should be accepted; "
        f"{accepted_prefixes} of {len(whole)} prefixes were"
    )


# --- termination and bounds, measured ---------------------------------------


@pytest.mark.parametrize("seed", range(8))
def test_mutation_fuzz_terminates_and_refuses_cleanly(seed):
    """Bounded random mutation of the three containers.

    **Code Review verified termination and bounds by reading.** This runs
    it. Every case must return or raise `ImageRejected` — not `IndexError`,
    not `struct.error`, not `MemoryError`, and not never.

    # ponytail: 400 mutations a seed, wall-clock budget, no hypothesis.
    # Ceiling: it samples, it does not prove; a shape needing three
    # coordinated mutations is not reachable from here. Upgrade path is a
    # structured generator, and the named shapes above are that upgrade for
    # the cases we know matter.
    """
    rng = random.Random(seed)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 8, 8)
        + b"\x08\x02\x00\x00\x00" + b"\x00" * 4
        + struct.pack(">I", len(CANARY)) + b"tEXt" + CANARY + b"\x00" * 4
        + struct.pack(">I", 0) + b"IEND" + b"\x00" * 4
    )
    vp8x = b"VP8X" + struct.pack("<I", 10) + b"\x00" * 4 + (7).to_bytes(3, "little") * 2
    webp_body = b"WEBP" + vp8x + b"EXIF" + struct.pack("<I", len(CANARY)) + CANARY
    webp = b"RIFF" + struct.pack("<I", len(webp_body)) + webp_body
    corpus = [_baseline(), _motion_photo(), _mpf_multi_picture(), png, webp]

    started = time.monotonic()
    for _ in range(400):
        base = bytearray(rng.choice(corpus))
        for _ in range(rng.randint(1, 6)):
            op = rng.random()
            if op < 0.5 and base:
                base[rng.randrange(len(base))] = rng.randrange(256)
            elif op < 0.8 and len(base) > 4:
                del base[rng.randrange(len(base)) :]
            else:
                base.extend(rng.randbytes(rng.randint(1, 64)))
        try:
            strip_metadata(bytes(base))
        except ImageRejected:
            pass
        except Exception as exc:  # noqa: BLE001 — the point of the test
            pytest.fail(
                f"seed {seed}: a mutated upload raised "
                f"{type(exc).__name__}({exc}) instead of ImageRejected. "
                f"An upload handler that 500s on malformed bytes is a "
                f"denial of service any student can trigger. "
                f"bytes={bytes(base[:64])!r}"
            )
    elapsed = time.monotonic() - started
    assert elapsed < 20, (
        f"seed {seed}: 400 mutations took {elapsed:.1f}s. The parser is "
        "super-linear on some shape in this corpus, which is the other half "
        "of 'termination' — a loop that finishes in an hour has not."
    )


# --- at the boundary the row claims -----------------------------------------


@pytest.mark.django_db
def test_a_motion_photo_uploaded_through_the_service_stores_no_trailer(
    seller, book, settings, tmp_path
):
    """The same attack at the boundary `listing_photos` claims, not at the
    function's.

    Everything above tests `strip_metadata`. The schema's promise is about a
    **row**: `exif_stripped_at NOT NULL`, with the bytes the row points at.
    Between the two sits `add_photo`, which could hash the original and store
    the stripped copy, or store the original and hash the stripped copy, and
    the unit tests above would not notice either. So one journey test, on the
    one shape that actually ships out of a phone camera.
    """
    import io

    from apps.listings import services
    from apps.listings.storage import read_object

    settings.MEDIA_ROOT = str(tmp_path / "media")
    listing = services.create_listing(
        seller, book=book, asking_price_paise=27500, condition="GOOD",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    buf = io.BytesIO(_motion_photo())
    buf.name = "IMG_20261022_motion.jpg"
    photo = services.add_photo(seller, listing, buf)

    stored = read_object(photo.storage_key)
    assert stored, "nothing was written to the object store"
    assert photo.exif_stripped_at is not None, (
        "the row claims nothing about the strip, so the column is decorative"
    )
    for needle, what in FORBIDDEN:
        assert needle not in stored, (
            f"{what} is in the stored object of a row stamped "
            f"exif_stripped_at={photo.exif_stripped_at!r}"
        )
    assert photo.bytes == len(stored), (
        "listing_photos.bytes does not match the object on disk, so the row "
        "was sized from the upload rather than from what was stored"
    )
    import hashlib

    assert photo.sha256 == hashlib.sha256(stored).hexdigest(), (
        "the row's sha256 is of the *original* upload, not of the stripped "
        "object — so the content-addressed URL A-25 freezes resolves by a "
        "digest of bytes nobody can fetch, and a re-upload of the same "
        "photograph would not be detected as a duplicate"
    )
