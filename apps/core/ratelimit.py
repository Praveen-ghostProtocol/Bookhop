"""Rate limiting — API-CONTRACT §2.4, ADR-001 §2.4.

*"Enforced by a DB-backed fixed-window counter … keyed as stated. Exceeding
returns `429` with `Retry-After`. Staff endpoints are exempt; every staff action
is in `audit_log` instead."*

**The limits themselves are not here.** They are in `API-CONTRACT.md` §2.4's
table and are passed by the caller, because a second copy of a published limit
is the hand-copied rule `CLAUDE.md` rule 10 is about — and the limits differ per
endpoint group in ways only the caller knows (per email, per IP, per user, per
transfer).

Why a table rather than Django's database cache backend — which is what ADR-001
§2.4 names — is on `apps.core.models.RateLimitCounter`, with the deviation
raised to cto. Short version: the cache table has a column named `value`, the
P14 guard is right to object to it, and `CLAUDE.md` rule 13 says rename ours
before exempting theirs.

**What this is NOT a control against:** a distributed attacker with many IPs and
many addresses. THREAT-MODEL §5.5 is where that lives, and the magic-link design
is what bounds the consequence — there is no password to stuff.
"""

import hashlib
import math
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .errors import RateLimited
from .models import RateLimitCounter

ONE_HOUR = timedelta(hours=1)
ONE_DAY = timedelta(days=1)


def _subject_key(subject):
    """One-way, and truncated to 32 hex characters — 128 bits, which is far
    past collision relevance for a counter that lives one window."""
    return hashlib.sha256(str(subject).encode("utf-8")).hexdigest()[:32]


def window_start(window, now=None):
    """The start of the fixed window `now` falls in.

    Integer division on the epoch, so it is stable across processes and across
    both engines without any shared state beyond the clock.
    """
    now = now or timezone.now()
    seconds = int(window.total_seconds())
    ordinal = int(now.timestamp() // seconds)
    return datetime.fromtimestamp(ordinal * seconds, tz=dt_timezone.utc)


def consume_quota(bucket, subject, *, limit, window, now=None):
    """Count one request against `(bucket, subject)`. Raises RateLimited.

    Returns the count after this request, so a caller can log how close it came
    — the cheap instrument that tells us whether a published limit is the right
    number *before* an abuse incident does.

    The increment is `UPDATE … SET hit_count = hit_count + 1`, which is atomic
    on both engines. The read-back afterwards is a separate statement, so under
    concurrency it can see a **later** value than this caller's own — which
    over-counts and never under-counts, and over-counting is the safe direction
    for a limit.
    """
    if subject in (None, ""):
        # A limiter keyed on nothing limits everyone together, which is a
        # denial of service on the whole campus rather than a rate limit.
        raise ValueError(f"rate-limit bucket {bucket!r} needs a subject to key on")

    now = now or timezone.now()
    started = window_start(window, now)
    seconds = int(window.total_seconds())
    key = dict(bucket=bucket, subject_hash=_subject_key(subject), window_started_at=started)

    try:
        with transaction.atomic():
            RateLimitCounter.objects.create(
                **key, hit_count=0, expires_at=started + window + timedelta(seconds=1)
            )
    except IntegrityError:
        pass  # another request opened this window first; the UNIQUE is the lock

    RateLimitCounter.objects.filter(**key).update(hit_count=F("hit_count") + 1)
    count = RateLimitCounter.objects.filter(**key).values_list("hit_count", flat=True).first() or 0

    if count > limit:
        retry_after = max(1, math.ceil((started.timestamp() + seconds) - now.timestamp()))
        raise RateLimited(
            "Too many requests. Please try again later.",
            retry_after=retry_after,
            bucket=bucket,
            limit=limit,
        )
    return count


def quota_used(bucket, subject, *, window, now=None):
    """The current count, for a test or a log line. Never increments."""
    return (
        RateLimitCounter.objects.filter(
            bucket=bucket,
            subject_hash=_subject_key(subject),
            window_started_at=window_start(window, now),
        )
        .values_list("hit_count", flat=True)
        .first()
        or 0
    )


def is_exempt(user):
    """API-CONTRACT §2.4: *"Staff endpoints are exempt; every staff action is in
    `audit_log` instead."* Exported so a caller states the exemption rather than
    open-coding `if user.role != "STUDENT"`, which is the shape that gets copied
    wrong."""
    return bool(user is not None and getattr(user, "is_staff_member", False))
