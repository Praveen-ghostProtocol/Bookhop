"""EXIF stripping and dimension reading, in the standard library.

**No new runtime dependency, and that is a security decision before it is a
laziness one.** `requirements.txt` lists `pillow==11.0.0  # S2, listing photo
resize + EXIF strip` as pre-approved, so taking it would have been within
ADR-001 §2.8. It is not taken, for three reasons in descending order of weight:

1. **A decoder is the attack surface.** Pillow *decodes* attacker-supplied
   image data in-process; the CVE history of every image library is the
   history of malformed files reaching a decoder. Everything this slice needs
   — remove the metadata, read the dimensions, confirm the container is what
   it claims — is **container parsing**, which never touches a pixel.
   `THREAT-MODEL.md` §4 B3 is about what an authenticated student can send us,
   and an upload is the largest thing they can send.
2. **Nothing needs decoding.** DATA-MODEL §3 wants `width`, `height`, `bytes`,
   `sha256` and `exif_stripped_at`. Resizing and derivative generation are
   `INFRA.md`'s and are not in this slice; the comment in `requirements.txt`
   says *"resize + EXIF strip"* and only the second half is S2's.
3. Rung 3 of the ladder: the standard library does it.

**What this is NOT**, stated because the opposite is easy to assume: it is not
a validity check on the image *content*. A file can pass here, be a structurally
valid JPEG, and render as garbage. What it guarantees is narrower and is the
thing the schema promises — **every metadata segment that can carry EXIF, GPS,
XMP or a comment is gone from the bytes that are written**, which is what makes
`listing_photos.exif_stripped_at NOT NULL` a structural guarantee rather than a
code path somebody has to remember.

# ponytail: container-level segment rewriting, no decode. Ceiling: no resize,
# no re-encode, no thumbnail, and a hostile file that is structurally valid is
# stored as-is. Upgrade path: Pillow behind a size and dimension cap, in the
# slice that needs derivatives (S7/S8) — and it is pre-approved in
# requirements.txt for exactly that.

**VERIFIED HERE** on both engines and both Python paths by
`tests/unit/test_listing_photos.py`: the fixtures carry a real EXIF APP1
segment with a GPS tag, the test asserts the marker is present before and
absent after, and asserts the stripped bytes still begin with the format's
magic. **ASSUMED THERE:** nothing — there is no platform-dependent behaviour
in this module; it is byte arithmetic.
"""

import struct

__all__ = ["strip_metadata", "ImageRejected", "CONTENT_TYPES"]

#: The three formats API-CONTRACT §5.2 permits, mapped to the media type the
#: response reports. The *magic bytes* decide, never the filename and never the
#: client's `Content-Type`: both are attacker-controlled on an upload.
CONTENT_TYPES = {
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


class ImageRejected(Exception):
    """Raised with a developer-facing reason; the caller renders the contract's."""


# --- JPEG ------------------------------------------------------------------

#: Markers with no payload, which therefore have no length word to skip.
_JPEG_STANDALONE = {0x01, *range(0xD0, 0xD8)}

#: Everything stripped from a JPEG: every APPn (APP0 is JFIF, APP1 is EXIF and
#: XMP, APP2 is ICC, APP13 is IPTC/Photoshop) and COM.
#:
#: **Asked as a range, not as a list** (`CLAUDE.md` rule 11). A list of "the
#: metadata markers" would gain an entry every time someone met a new one, and
#: the one it did not have is the one that carries the GPS tag. Every APPn is
#: application metadata by the JPEG specification's own definition; none of
#: them is image data, so the property is "is it an APPn or a COM", not "is it
#: in my list".
#:
#: APP0/JFIF carries density and nothing identifying, and is dropped with the
#: rest because keeping it would mean a list again.
def _is_jpeg_metadata(marker):
    return 0xE0 <= marker <= 0xEF or marker == 0xFE


def _strip_jpeg(data):
    if not data.startswith(b"\xff\xd8"):
        raise ImageRejected("not a JPEG: no SOI marker")
    out = bytearray(b"\xff\xd8")
    width = height = None
    i = 2
    end = len(data)
    while i < end - 1:
        if data[i] != 0xFF:
            raise ImageRejected(f"JPEG segment structure broken at byte {i}")
        # Fill bytes: 0xFF may be repeated before a marker.
        while i < end and data[i] == 0xFF:
            i += 1
        if i >= end:
            raise ImageRejected("JPEG ended inside a marker")
        marker = data[i]
        i += 1
        if marker in _JPEG_STANDALONE:
            out += bytes((0xFF, marker))
            continue
        if marker == 0xD9:  # EOI
            out += b"\xff\xd9"
            break
        if i + 2 > end:
            raise ImageRejected("JPEG ended inside a segment header")
        (length,) = struct.unpack(">H", data[i:i + 2])
        if length < 2 or i + length > end:
            raise ImageRejected("JPEG segment length runs past the end of the file")
        payload = data[i + 2:i + length]
        # SOF0..SOF15 except the four that are not frame headers. The frame
        # header is where the real dimensions are; EXIF's own width/height tags
        # are metadata and are being deleted.
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            if len(payload) < 5:
                raise ImageRejected("JPEG frame header is too short to carry dimensions")
            height, width = struct.unpack(">HH", payload[1:5])
        if not _is_jpeg_metadata(marker):
            out += bytes((0xFF, marker)) + data[i:i + length]
        i += length
        if marker == 0xDA:  # SOS — entropy-coded data to the end of the file
            out += data[i:]
            break
    if width is None or height is None:
        raise ImageRejected("no JPEG frame header, so the file carries no dimensions")
    return bytes(out), width, height


# --- PNG -------------------------------------------------------------------

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

#: PNG chunks that carry metadata rather than image data. Unlike JPEG there is
#: no structural property that separates them — a chunk type is four letters —
#: **so this is a list, and its ceiling is declared here** (`CLAUDE.md`
#: rule 11): a future metadata chunk type is not caught. The layer that
#: generalises is the ancillary-chunk rule below, which is a property: a
#: lowercase first letter means ancillary, and **every** ancillary chunk except
#: the three that affect rendering is dropped. The named list is kept only for
#: the error message and for the test's own assertions.
_PNG_METADATA_CHUNKS = {b"eXIf", b"tEXt", b"iTXt", b"zTXt", b"tIME", b"iCCP"}

#: Ancillary chunks that are kept because dropping them changes how the image
#: renders. Everything else ancillary goes.
_PNG_KEEP_ANCILLARY = {b"tRNS", b"gAMA", b"sRGB", b"PLTE", b"bKGD", b"sBIT"}


def _strip_png(data):
    if not data.startswith(_PNG_MAGIC):
        raise ImageRejected("not a PNG: bad signature")
    out = bytearray(_PNG_MAGIC)
    width = height = None
    i = len(_PNG_MAGIC)
    end = len(data)
    saw_iend = False
    while i + 8 <= end:
        (length,) = struct.unpack(">I", data[i:i + 4])
        kind = data[i + 4:i + 8]
        nxt = i + 12 + length
        if length > end or nxt > end:
            raise ImageRejected("PNG chunk length runs past the end of the file")
        if kind == b"IHDR":
            if length < 8:
                raise ImageRejected("PNG IHDR is too short to carry dimensions")
            width, height = struct.unpack(">II", data[i + 8:i + 16])
        # Critical chunks have an uppercase first letter and are always kept.
        critical = kind[:1].isupper()
        if critical or kind in _PNG_KEEP_ANCILLARY:
            out += data[i:nxt]
        i = nxt
        if kind == b"IEND":
            saw_iend = True
            break
    if width is None or height is None:
        raise ImageRejected("no PNG IHDR, so the file carries no dimensions")
    if not saw_iend:
        raise ImageRejected("PNG ended without an IEND chunk")
    return bytes(out), width, height


# --- WebP ------------------------------------------------------------------


def _strip_webp(data):
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ImageRejected("not a WebP: bad RIFF header")
    kept = bytearray()
    width = height = None
    i = 12
    end = len(data)
    while i + 8 <= end:
        kind = data[i:i + 4]
        (length,) = struct.unpack("<I", data[i + 4:i + 8])
        payload = data[i + 8:i + 8 + length]
        if len(payload) != length:
            raise ImageRejected("WebP chunk length runs past the end of the file")
        if kind == b"VP8X" and length >= 10:
            width = int.from_bytes(payload[4:7], "little") + 1
            height = int.from_bytes(payload[7:10], "little") + 1
        elif kind == b"VP8 " and length >= 10:
            width = int.from_bytes(payload[6:8], "little") & 0x3FFF
            height = int.from_bytes(payload[8:10], "little") & 0x3FFF
        elif kind == b"VP8L" and length >= 5:
            bits = int.from_bytes(payload[1:5], "little")
            width = (bits & 0x3FFF) + 1
            height = ((bits >> 14) & 0x3FFF) + 1
        # EXIF, XMP and ICCP are the three metadata chunks the WebP container
        # defines; ANIM/ANMF/ALPH and the VP8* bitstreams are image data.
        if kind not in (b"EXIF", b"XMP ", b"ICCP"):
            kept += data[i:i + 8 + length + (length & 1)]
        i += 8 + length + (length & 1)
    if width is None or height is None:
        raise ImageRejected("no WebP bitstream header, so the file carries no dimensions")
    body = b"WEBP" + bytes(kept)
    return b"RIFF" + struct.pack("<I", len(body)) + body, width, height


_FORMATS = (
    (b"\xff\xd8\xff", "jpeg", _strip_jpeg),
    (_PNG_MAGIC, "png", _strip_png),
    (b"RIFF", "webp", _strip_webp),
)


def strip_metadata(data):
    """`(stripped_bytes, format, width, height)`, or raise `ImageRejected`.

    The format is decided by the magic bytes. **Neither the filename nor the
    client's `Content-Type` is consulted** — both are attacker-controlled on an
    upload, and a `.jpg` that is an HTML document is the oldest trick there is.
    """
    if not data:
        raise ImageRejected("empty upload")
    for magic, name, strip in _FORMATS:
        if data.startswith(magic):
            stripped, width, height = strip(data)
            if width <= 0 or height <= 0 or width > 20000 or height > 20000:
                raise ImageRejected(f"implausible dimensions {width}x{height}")
            return stripped, name, width, height
    raise ImageRejected("not a JPEG, PNG or WebP")
