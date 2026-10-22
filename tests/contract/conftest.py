"""Fixtures QA's contract tests share. Nothing here is imported by another
agent's tree, and nothing here reaches into one for a fixture.

`jpeg_bytes` builds its own container rather than importing backend's `_jpeg`:
the attacks in `tests/contract/test_image_content.py` need to vary the
container deliberately (truncate it, lie about the dimensions, put PNG magic
on a `.jpg`), and a helper owned by the tree under test is the wrong place for
the knobs an attack needs. Rule 11 does not apply across the test/subject
boundary — a test fixture that the subject's own tests also define is not two
copies of one *rule*, it is two witnesses.
"""

import struct

import pytest

from tests.e2e.conftest import (  # noqa: F401
    qa_authorisation,
    qa_campus,
    qa_city,
    qa_entity,
    qa_evidence,
)


def build_jpeg(width=4, height=3, *, exif=True, tag=0):
    """A structurally valid JPEG, optionally carrying an EXIF APP1 with GPS.

    The dimensions live in the SOF0 segment, which is what `apps.listings.images`
    reads — so `width`/`height` here are what the *container claims*, which is
    exactly the distinction `test_image_content.py` is about.
    """
    parts = [bytes((0xFF, 0xD8))]
    if exif:
        payload = b"Exif\x00\x00" + b"II*\x00" + struct.pack("<I", 8)
        payload += struct.pack("<H", 1) + struct.pack("<HHII", 0x8825, 4, 1, 26)
        payload += bytes((tag, tag, tag, tag))
        parts.append(bytes((0xFF, 0xE1)) + struct.pack(">H", len(payload) + 2) + payload)
    parts.append(
        bytes((0xFF, 0xC0)) + struct.pack(">H", 11) + bytes((8,))
        + struct.pack(">HH", height, width) + bytes((1,)) + bytes((1, 0x11, 0))
    )
    parts.append(bytes((0xFF, 0xDA)) + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0)))
    parts.append(bytes((0, 0)) + bytes((0xFF, 0xD9)))
    return b"".join(parts)


@pytest.fixture
def jpeg_bytes():
    return build_jpeg()


@pytest.fixture
def client_as(db):
    """A **fresh** client per signed-in user.

    One client reused across users measures nonsense: `client.session` mints a
    new key on each save while the cookie still points at the first, so every
    actor after the first is anonymous. QA paid for that once already
    (`test_standing_preconditions_matrix.py`).
    """
    from django.test import Client

    from apps.accounts.sessions import SESSION_USER_KEY

    def _sign_in(user):
        client = Client()
        session = client.session
        session[SESSION_USER_KEY] = user.id
        session.save()
        return client

    return _sign_in
