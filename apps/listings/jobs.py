"""S2's job handler — the expiry for the retention this slice creates.

`COMPLIANCE.md` §8.3, and `CLAUDE.md`'s engineering standard restated in the
backend charter: **the expiry job ships in the same slice as the retention it
expires.** S2 creates two retention clocks — `listings.purge_due_at` and
`listing_photos.purge_due_at`, both `closed_at + 1 year` (r.8(3)) — so the
thing that honours them ships here, not in S8 with the cron timer.

**Idempotent under at-least-once delivery** (API-CONTRACT §4.4): every rule is
a timestamp comparison and a `purged_at IS NULL` test, so a second run in the
same night finds nothing left and writes no `purge_log` rows. `delete_object`
is idempotent for the same reason — the file the first run removed is not an
error for the second.

**What is purged and what is not.** The photo *objects* go and the photo
*rows* stay, with `purged_at`-shaped evidence in `purge_log`. That is the
tombstone-plus-purge shape the rest of the system uses: the row is what proves
a listing had four photos when a dispute is read a year later, and the bytes
are the personal data (a photo of a book carries a room, a desk and sometimes
a face). `COMPLIANCE.md` §7 row 9 asks for the originals and derivatives to be
deleted; it does not ask for the count to be forgotten.
"""

import logging
from datetime import timedelta

from django.utils import timezone

from apps.core.jobs import handler
from apps.core.services import enqueue

from .models import ListingPhoto
from .storage import delete_object

log = logging.getLogger(__name__)

#: One run per night, self-rescheduling, exactly as `retention.purge` does —
#: so `readyz`'s "last job run < 5 min ago" ceiling keeps having something to
#: measure and the cadence is written in one place rather than two.
PURGE_INTERVAL_HOURS = 24

#: How many objects one run removes. A bound rather than a full table walk,
#: because a purge that takes longer than the night is the failure mode
#: DATA-MODEL §10.2's own ponytail note names, and a bounded run that
#: reschedules drains at the same rate without holding a transaction open.
PURGE_BATCH = 500


@handler("listings.purge_media")
def purge_media(payload):
    """Delete the stored bytes of every photo past its `purge_due_at`.

    Returns `{"photos": n}`. Writes one `purge_log` row per object removed,
    which is how we prove to G3/G4 that the job ran rather than claiming it.

    `storage_key` goes NULL rather than empty, because the column is UNIQUE
    and a second purged row would collide on `""` -- NULLs are distinct on
    both engines and "there is no object" is exactly what NULL means.

    **The object is deleted before the row is marked**, and that order is
    deliberate: if the process dies between the two, the next run finds the
    row still unmarked, calls `delete_object` on a file that is already gone,
    gets `False`, and marks it. The reverse order would mark a row whose bytes
    are still on disk — a purge that reports success and leaves the personal
    data behind, which is the one failure mode a retention job must not have.
    """
    from apps.core.models import PurgeLog

    now = timezone.now()
    due = list(
        ListingPhoto.all_objects.filter(
            purge_due_at__isnull=False, purge_due_at__lte=now, storage_key__isnull=False
        )
        .order_by("purge_due_at", "id")[:PURGE_BATCH]
    )
    removed = 0
    for photo in due:
        delete_object(photo.storage_key)
        ListingPhoto.all_objects.filter(id=photo.id).update(storage_key=None)
        PurgeLog.objects.create(
            table_name="listing_photos",
            object_pk=str(photo.id),
            purge_due_at=photo.purge_due_at,
            purged_at=now,
            job_run_id=str(payload.get("job_run_id") or ""),
            mode="PURGE",
        )
        removed += 1

    if removed:
        log.info("listings.media_purged", extra={"photos": removed})
    # Reschedule unconditionally, and sooner when the batch was full, so a
    # backlog drains instead of waiting a day per 500 objects.
    enqueue(
        "listings.purge_media",
        {},
        run_after=now + timedelta(minutes=5)
        if removed == PURGE_BATCH
        else now + timedelta(hours=PURGE_INTERVAL_HOURS),
    )
    return {"photos": removed}
