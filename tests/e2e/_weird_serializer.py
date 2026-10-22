"""A session serialiser that is not the one the session rows were written with.

Used by `test_erasure_sessions.py` to model `CLAUDE.md` rule 17's *ASSUMED
THERE* case: the erasure path's session scan depends on a decode succeeding, and
a deployment that changes `SESSION_SERIALIZER` changes what "decodes" means.
Nothing here is production code; it exists so the attack is a real
configuration change rather than a hand-corrupted row.
"""

import json


class PrefixedJSONSerializer:
    """JSON with a one-byte prefix, so rows written by the stock serialiser
    raise on `loads` while their signature still verifies."""

    def dumps(self, obj):
        return b"\x01" + json.dumps(obj, separators=(",", ":")).encode("latin-1")

    def loads(self, data):
        if not data.startswith(b"\x01"):
            raise ValueError("not written by this serialiser")
        return json.loads(data[1:].decode("latin-1"))
