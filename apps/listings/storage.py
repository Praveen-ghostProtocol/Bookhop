"""Where a stripped listing photo's bytes live.

**Files on disk under `MEDIA_ROOT`, not rows in the database**, and not an
object store: `INFRA.md` §1 is one VM, `COST-MODEL.md` §5 gates every rupee of
infrastructure spend on the founder, and a photo in a `bytea` column is a
photo in every `pg_dump` and every nightly backup transfer.

Three properties this module exists to keep, each of them one line and each of
them a thing that is expensive to retrofit:

  * **The key is derived from the content hash**, so the same bytes uploaded
    twice occupy one file and a key leaks nothing about the uploader.
  * **The key is validated before it reaches the filesystem.** A storage key
    is assembled from a listing id and a hex digest here, so traversal is not
    reachable today — but `delete_object` is called by the retention job with
    a key read back **out of the database**, and a control that depends on
    nobody ever writing a bad row is the shape `CLAUDE.md` rule 12 is about.
    The floor is that the resolved path must stay inside `MEDIA_ROOT`.
  * **Deletion is idempotent**, because the retention job is at-least-once
    (API-CONTRACT §4.4) and a second run must not fail on a file the first
    run removed.

# ponytail: local files, no object store, no CDN, no derivatives. Ceiling: one
# VM's disk, and a restore has to carry the media directory as well as the
# database dump — which is `INFRA.md` §3's backup scope and is flagged in the
# slice note, because a tested restore that restores the rows and not the
# photos passes its own test. Upgrade path: S3-compatible storage behind the
# same three functions, which is why callers never see a path.
"""

import logging
import os
import pathlib

from django.conf import settings

log = logging.getLogger(__name__)

__all__ = ["media_root", "write_object", "read_object", "delete_object", "object_path"]


def media_root():
    """The directory photos live in. Created on demand.

    Defaults to `BASE_DIR/media` rather than to a temporary directory: a
    default that disappears on reboot would pass every test and lose every
    photo, which is the shape of plausible-looking default `PUBLIC_ORIGIN`
    was given no fallback to avoid.
    """
    root = getattr(settings, "MEDIA_ROOT", None) or (settings.BASE_DIR / "media")
    path = pathlib.Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def object_path(key):
    """`key` resolved under `MEDIA_ROOT`, or `ValueError`.

    The containment check is `Path.resolve()` on both sides and a prefix
    comparison, which answers the property rather than scanning for `..` — a
    list of dangerous sequences cannot express a symlink or a UNC path, and
    this is Windows as well as Linux (`CLAUDE.md` rule 11).
    """
    root = media_root().resolve()
    candidate = (root / str(key)).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"storage key escapes the media root: {key!r}")
    return candidate


def write_object(key, data):
    """Write `data` at `key`. Returns the number of bytes written.

    Written to a temporary name and then renamed, so a reader never sees a
    half-written file and a crash mid-write leaves no partial object that a
    `sha256` check would later report as corruption.
    """
    path = object_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with open(temporary, "wb") as handle:
        handle.write(data)
    os.replace(temporary, path)
    return len(data)


def read_object(key):
    path = object_path(key)
    if not path.exists():
        return None
    return path.read_bytes()


def delete_object(key):
    """Remove the object. **Idempotent**: already gone is success.

    The retention job is at-least-once, so a second run must find nothing to
    do rather than fail. A `ValueError` from `object_path` is deliberately not
    swallowed: a key that escapes the media root is a defect to surface, not a
    file to skip.
    """
    path = object_path(key)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
