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


def redacted(payload):
    """What a finished job's payload is replaced by: its **key names only**.

    **RED TEAM ENGINEERING-MEMO §2, CRITICAL.** `jobs.payload` is jsonb in the
    production database, S1's `accounts.send_magic_link` put the **raw
    single-use sign-in token** in it, and `apps/accounts/jobs.py` licensed that
    by claiming the row was deleted once the job finished — which was false. Nothing deleted
    a `Job` row anywhere in `apps/**` and `purge_expired` did not walk `jobs`,
    so every magic link ever issued stayed in the database in plaintext and a
    nightly `pg_dump` was a file of working sign-in links for named students.
    That is rule 9 broken inside the file implementing the credential path: a
    docstring asserted a property, nothing checked it, and it was wrong by a
    factor of forever.

    **Key names, not a redaction of known-secret keys.** `CLAUDE.md` rule 15:
    a list of secret-looking key names would need an entry for every future
    handler and would be wrong the first time someone wrote `link` instead of
    `token`. Asking "which of these values is a credential?" has no reliable
    answer; asking "does this job still need its input?" does — a finished job
    does not. So the values go and the shape stays, which is all a diagnostic
    needs: *"it had token_id, token and locale"* identifies the payload without
    being it.

    Applied on success **and** on terminal failure. It is deliberately **not**
    applied on a retryable failure, because the retry needs its input — and that
    residual is bounded and stated in `run_pending_jobs`.
    """
    if isinstance(payload, dict):
        return {"_redacted_keys": sorted(str(key) for key in payload)}
    return {"_redacted_keys": []}


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
        payload = job.payload
        try:
            if fn is None:
                raise RuntimeError(f"no handler registered for job kind {job.kind!r}")
            fn(payload)
        except Exception:
            # RED TEAM §2: `last_error` is a text column in the same database as
            # `payload`, so a traceback carrying a payload value would reinstate
            # the credential it was just scrubbed from. Scrubbed by value, not
            # by key name, so a handler that interpolated a token into its own
            # exception message is covered too.
            job.last_error = _scrub(traceback.format_exc(), payload)[-4000:]
            job.locked_at = None
            job.locked_by = None
            if job.attempts >= job.max_attempts:
                job.failed_at = timezone.now()
                # Terminal: nothing will read this payload again, so it goes.
                job.payload = redacted(payload)
                log.error("job.failed", extra={"job_id": job.id, "kind": job.kind})
            else:
                # Retryable: the retry needs its input, so the payload stays.
                # **The stated residual** (RED TEAM §2): a credential-bearing
                # job that keeps failing retains its credential across the
                # retry window -- 1+4+9+16 minutes at the default budget. For
                # the magic link that is bounded by the token's own 10-minute
                # expiry, after which the row holds a dead string, and the
                # handler refuses to deliver a stale token. Bounded, named, and
                # no longer "forever".
                job.run_after = timezone.now() + _backoff(job.attempts)
            job.save(
                update_fields=[
                    "last_error", "locked_at", "locked_by", "failed_at", "run_after", "payload",
                ]
            )
            failed += 1
        else:
            job.completed_at = timezone.now()
            job.locked_at = None
            # The fix for RED TEAM §2's CRITICAL. A finished job does not need
            # its input, and `jobs.payload` is jsonb in the production database
            # that `pg_dump` copies nightly.
            job.payload = redacted(payload)
            job.save(update_fields=["completed_at", "locked_at", "payload"])
            succeeded += 1
    return succeeded, failed


def _scrub(text, payload):
    """Remove every payload *value* from `text`.

    By value rather than by key name, for the reason `redacted` gives: naming
    the secret keys is a list that is wrong the first time a handler calls one
    `link` instead of `token`. Short values are left alone — a 2-character
    locale is not a credential and removing it would make a traceback
    unreadable.
    """
    if not isinstance(payload, dict):
        return text
    for value in payload.values():
        if isinstance(value, str) and len(value) >= 12:
            text = text.replace(value, "[redacted]")
    return text


@handler("core.noop")
def _noop(payload):
    """A registered handler S0 can test the runner with.

    Not a stub standing in for a later slice: it does nothing on purpose, and
    nothing in the product enqueues it.
    """
    return None
