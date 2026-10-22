"""S1's job handlers — ADR-001 §2.4, API-CONTRACT §4.4.

Both are **idempotent under at-least-once delivery**, because the runner is
at-least-once and a handler that is not idempotent is a handler that will
eventually do its thing twice:

  * `accounts.send_magic_link` — a second delivery emails the same single-use
    token, so the *link* remains single-use whatever the job does. The handler
    additionally refuses to send a token that has already been consumed or has
    expired, so a retry hours later does not put a dead link in a student's
    inbox.
  * `retention.purge` — every rule is a timestamp comparison, so a second run
    in the same night finds nothing left to do and writes no `purge_log` rows.

**`retention.purge` is a standing recurring job**, which closes the ceiling
`apps/core/views.readyz` records: with an empty queue a dead runner reads as
ready, and from S1 there is always something scheduled.
"""

import logging
from datetime import timedelta

from django.utils import timezone

from apps.core.jobs import handler
from apps.core.mail import deliver_email
from apps.core.services import enqueue

from .models import EmailLoginToken
from .services import TOKEN_TTL, purge_expired

log = logging.getLogger(__name__)

#: One purge run per night. The schedule is a systemd timer in S8; until then
#: the job reschedules itself, so `manage.py run_jobs` from cron is enough and
#: there is no second place the cadence is written.
PURGE_INTERVAL_HOURS = 24


@handler("accounts.send_magic_link")
def send_magic_link(payload):
    """Email the single-use link. Context dict only; the body is frontend's.

    **The raw token is in the job payload for exactly as long as the job is
    unfinished, and `apps/core/jobs.run_pending_jobs` redacts the payload the
    moment it finishes.** That sentence is now true; the one it replaces was
    not, and RED TEAM ENGINEERING-MEMO §2 rated it CRITICAL: the old docstring
    claimed the row was deleted once the job finished. **Nothing in `apps/**` deleted a
    `Job` row and `purge_expired` did not walk `jobs`**, so every magic link
    ever issued stayed in the database in plaintext and a nightly `pg_dump` was
    a file of working sign-in links for named students.

    Four changes closed it, and the fourth is this paragraph:
      1. `run_pending_jobs` replaces the payload with its key names on success
         and on terminal failure;
      2. `last_error` is scrubbed of every payload value before it is written;
      3. `purge_expired` walks `jobs`;
      4. the docstring says what the code does.

    **Why the token is still in the payload at all.** The sender cannot derive
    it: `email_login_tokens.token_hash` is a one-way sha256, which is the
    property that makes a database read unable to sign anyone in. So the
    plaintext has to travel from the request that minted it to the sender
    somehow, and the two options are this payload or sending inline inside the
    request. ADR-001 §2.4 puts *"email and push sending"* in the queue, and a
    synchronous SMTP call in the sign-in POST trades a bounded at-rest window
    for a student who cannot sign in whenever the mail host is slow. The queue
    stays; the window is now bounded by the job's own run rather than by
    nothing.

    # ponytail: the token rides in the job payload. Ceiling: a plaintext
    # credential at rest between enqueue and the job's first run — seconds in
    # normal operation, and up to the token's own 10-minute expiry if the job
    # keeps failing retryably, after which the string is dead and the handler
    # refuses to deliver it. Upgrade path: send inline on commit, which needs
    # ADR-001 §2.4 amended and buys a sign-in that fails when SES is slow.

    **`scheme` and `host` are in the payload rather than a built URL**, and that
    is an ownership line, not a preference: the route is `/auth/c/{token}` in
    `web/urls.py`, which is frontend-developer's, and backend building the path
    would hard-code another agent's URL in a Python file they cannot edit. A job
    has no request, so the two pieces are captured at enqueue time from
    `request_context.public_origin()` — without them the template renders
    `://` and the student gets a dead link, which is what shipped before this
    fix.

    **`display_name` and `campus_name` are deliberately NOT in the payload.**
    Frontend does not use them, and its reasoning is right and worth keeping
    written down: a sign-in email can arrive at an address whose owner never
    requested it, so greeting them by name would move the enumeration leak the
    202 response exists to prevent into the mailbox. A payload that carries a
    name is also one more thing a retained job row discloses.
    """
    token_id = payload["token_id"]
    raw = payload["token"]
    row = EmailLoginToken.objects.filter(id=token_id).select_related("user").first()
    if row is None:
        log.info("mail.magic_link.token_gone", extra={"token_id": token_id})
        return
    if row.consumed_at is not None or row.expires_at <= timezone.now():
        # A retry that arrives after the link is dead must not deliver it.
        log.info("mail.magic_link.stale", extra={"token_id": token_id})
        return
    if not row.user.email:  # pragma: no cover - erased between enqueue and send
        return

    deliver_email(
        to=row.user.email,
        name="magic_link",
        locale=payload.get("locale") or row.user.locale,
        context={
            # The context dict is the contract between backend and the template
            # (API-CONTRACT §3's `notify()` payloads).
            "token": raw,
            "scheme": payload.get("scheme"),
            "host": payload.get("host"),
            "expires_at": row.expires_at,
            "expires_in_minutes": int(TOKEN_TTL.total_seconds() // 60),
        },
    )


@handler("retention.purge")
def retention_purge(payload):
    """DATA-MODEL §10.2's nightly expiry, then reschedule itself.

    Rescheduling inside the handler rather than from a crontab keeps the cadence
    in one place and means the job cannot silently stop existing — the one
    failure mode that turns a retention policy back into a promise.
    """
    counts = purge_expired(job_run_id=payload.get("run_id") or timezone.now().isoformat())
    log.info("retention.purge", extra=counts)
    if payload.get("reschedule", True):
        enqueue(
            "retention.purge",
            {"reschedule": True},
            run_after=timezone.now() + timedelta(hours=PURGE_INTERVAL_HOURS),
        )
    return counts
