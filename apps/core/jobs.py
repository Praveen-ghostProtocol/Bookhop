"""The job runner — ADR-001 §2.4.

A `jobs` table and one management command, run by cron. No Celery, no Redis, no
broker.

# ponytail: single-process polling job runner, one-minute granularity,
# at-least-once delivery. Ceiling: sub-second scheduling, or more throughput
# than one worker handles. Upgrade path: run N workers (claiming is a
# compare-and-swap UPDATE, so that is already safe), then a real broker only if
# that fails.

Claiming deviates from the ADR's stated mechanism and says so out loud.
ADR-001 §2.4 specifies `SELECT ... FOR UPDATE SKIP LOCKED`. On SQLite Django
reports `has_select_for_update = False` and **silently omits the locking
clause** rather than raising -- measured, not assumed -- so on the development
machine that mechanism would appear to work while locking nothing. Claiming is
therefore a conditional UPDATE (`WHERE id = ? AND locked_at IS NULL`, then check
the row count), which gives the same property -- at most one worker claims a
row -- in SQL that means the same thing on both engines and can be read in the
query log. See ENGINE-DIVERGENCE.md §4.3.
"""

import logging
import socket
import traceback
import uuid
from datetime import timedelta

from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone

from .models import Job

log = logging.getLogger(__name__)

#: kind -> handler(payload: dict) -> None. Handlers must be idempotent.
REGISTRY = {}


def handler(kind):
    def register(fn):
        if kind in REGISTRY:
            raise RuntimeError(f"duplicate job handler for {kind!r}")
        REGISTRY[kind] = fn
        return fn

    return register


def _backoff(attempts):
    """1m, 4m, 9m, 16m ... — quadratic, bounded by max_attempts."""
    return timedelta(minutes=attempts**2)


def _claimable(now):
    """A job is claimable if nobody holds its lock, or the holder is gone.

    M4. The conditional UPDATE gives the same "at most one worker claims a row"
    property as `SKIP LOCKED`, but not the same release: `SKIP LOCKED` drops its
    lock when the connection dies, and a `locked_at` column does not. Without
    expiry a worker killed by SIGKILL, OOM, power loss or a deploy mid-handler
    takes its job with it permanently and silently — which delivers the job
    **zero** times and breaks the at-least-once guarantee in ADR-001 §2.4 and
    API-CONTRACT §4.4 in exactly the case the guarantee exists for.

    # ponytail: a wall-clock lock timeout. Ceiling: a handler that legitimately
    # runs longer than JOB_LOCK_TIMEOUT is run twice concurrently, which is safe
    # only because every handler is required to be idempotent. Upgrade path: a
    # heartbeat column the handler touches, which is only worth it when a
    # handler is genuinely long-running. No S0–S7 handler is.
    """
    cutoff = now - settings.JOB_LOCK_TIMEOUT
    return Q(locked_at__isnull=True) | Q(locked_at__lt=cutoff)


def _claim(worker_id, now):
    """Claim one due job, or return None.

    The UPDATE is the lock. A second worker's UPDATE matches zero rows and it
    moves on, which is what SKIP LOCKED would have given us.
    """
    claimable = _claimable(now)
    due = (
        Job.objects.filter(
            claimable, run_after__lte=now, completed_at__isnull=True, failed_at__isnull=True
        )
        .order_by("run_after", "id")
        .values_list("id", flat=True)[:20]
    )
    for job_id in list(due):
        # The same predicate in the CAS, so a worker that claimed the row
        # between the SELECT and here still wins and this one moves on.
        claimed = Job.objects.filter(claimable, id=job_id).update(
            locked_at=now, locked_by=worker_id, attempts=F("attempts") + 1
        )
        if claimed:
            job = Job.objects.get(id=job_id)
            if job.locked_by != worker_id:  # someone else won; do not run it
                continue
            return job
    return None


def new_worker_id():
    """S3: the old `f"{hostname}:{id(object())}"` produced **one** distinct
    value in 200 tries -- the object is collected immediately and its address
    reused. `locked_by` answers "which worker holds this lock", and M4's expiry
    makes that question live."""
    return f"{socket.gethostname()}:{uuid.uuid4().hex[:12]}"


def run_pending_jobs(limit=50, worker_id=None):
    """Run up to `limit` due jobs. Returns (succeeded, failed)."""
    worker_id = worker_id or new_worker_id()
    succeeded = failed = 0
    for _ in range(limit):
        now = timezone.now()
        job = _claim(worker_id, now)
        if job is None:
            break
        fn = REGISTRY.get(job.kind)
        try:
            if fn is None:
                raise RuntimeError(f"no handler registered for job kind {job.kind!r}")
            fn(job.payload)
        except Exception:
            job.last_error = traceback.format_exc()[-4000:]
            job.locked_at = None
            job.locked_by = None
            if job.attempts >= job.max_attempts:
                job.failed_at = timezone.now()
                log.error("job.failed", extra={"job_id": job.id, "kind": job.kind})
            else:
                job.run_after = timezone.now() + _backoff(job.attempts)
            job.save(update_fields=["last_error", "locked_at", "locked_by", "failed_at", "run_after"])
            failed += 1
        else:
            job.completed_at = timezone.now()
            job.locked_at = None
            job.save(update_fields=["completed_at", "locked_at"])
            succeeded += 1
    return succeeded, failed


@handler("core.noop")
def _noop(payload):
    """A registered handler S0 can test the runner with.

    Not a stub standing in for a later slice: it does nothing on purpose, and
    nothing in the product enqueues it.
    """
    return None
