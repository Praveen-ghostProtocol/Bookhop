"""apps.core service layer (L1) — API-CONTRACT §3.

Everything here is called by L2 handlers, L3 views, management commands and job
handlers. Nothing here renders, and nothing above here touches the ORM.
"""

import hashlib
import json
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .errors import (
    AuditChainBroken,
    IdempotencyInProgress,
    IdempotencyKeyRequired,
    IdempotencyKeyReused,
    ValidationFailed,
)
from .models import AuditLog, FeatureFlag, IdempotencyKey, Job
from .request_context import current_request
from .scoping import (  # re-exported: API-CONTRACT §3 lists these on apps.core.services
    SYSTEM,
    assert_discovery_open,
    restrict_when_gate_closed,
    scoped,
    visible_campus_ids,
)

__all__ = [
    "SYSTEM",
    "assert_discovery_open",
    "visible_campus_ids",
    "scoped",
    "restrict_when_gate_closed",
    "flag",
    "record_audit",
    "verify_audit_chain",
    "enqueue",
    "idempotent",
]

#: The first row's predecessor. A constant rather than NULL so that `prev_hash`
#: can be UNIQUE NOT NULL and the genesis row is as constrained as every other.
GENESIS_HASH = "0" * 64


# --- Feature flags --------------------------------------------------------


def flag(key, campus=None):
    """DATA-MODEL §1 `feature_flags`. Absent key means off.

    Deliberately not a cache: at pilot volume one indexed primary-key lookup is
    cheaper than a cache-invalidation bug.
    """
    qs = FeatureFlag.objects.filter(key=key)
    if campus is not None:
        row = qs.filter(scope_type="CAMPUS", scope_id=campus.id).first() or qs.filter(
            scope_type="GLOBAL"
        ).first()
    else:
        row = qs.filter(scope_type="GLOBAL").first()
    return bool(row and row.enabled)


# --- Audit trail ----------------------------------------------------------


def _canonical(value):
    """Stable JSON. Sorted keys, no whitespace, dates as ISO-8601 strings.

    `default=str` is what makes a datetime, Decimal or UUID hashable without a
    per-type registry. It also means a change in Python's str() for a type would
    change the hash of rows written after it; the chain is verified
    incrementally by `verify_audit_chain`, which rehashes with today's code, so
    that would surface as a break rather than pass silently.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_payload(payload):
    return None if payload is None else _sha256(_canonical(payload))


def _row_fields(row):
    """The hashed part of an audit row: everything except the two hash columns."""
    return {
        "actor_type": row.actor_type,
        "actor_id": row.actor_id,
        "actor_pseudonym": row.actor_pseudonym,
        "action": row.action,
        "object_type": row.object_type,
        "object_id": row.object_id,
        "before_hash": row.before_hash,
        "after_hash": row.after_hash,
        "request_id": row.request_id,
        "ip": row.ip,
        "user_agent": row.user_agent,
        "occurred_at": row.occurred_at,
    }


def record_audit(actor, action, obj, before=None, after=None):
    """Append one tamper-evident row. API-CONTRACT §3.

    **Call this inside the same transaction as the change it records.** A
    rolled-back mutation must roll back its audit row, and a committed mutation
    must not be able to commit without one.

    Concurrency: `audit_log.prev_hash` is UNIQUE, so if another appender
    committed between reading the head and inserting, this insert fails and is
    retried against the new head. The retry runs in a savepoint so the caller's
    transaction survives it.
    """
    req = current_request()
    if actor is SYSTEM or actor is None:
        actor_type, actor_id, actor_pseudonym = "SYSTEM", None, None
    else:
        actor_type = "STAFF" if getattr(actor, "role", "STUDENT") != "STUDENT" else "USER"
        actor_id = getattr(actor, "id", None)
        actor_pseudonym = getattr(actor, "person_pseudonym", None)

    base = dict(
        actor_type=actor_type,
        actor_id=actor_id,
        actor_pseudonym=actor_pseudonym,
        action=action,
        object_type=obj.__class__.__name__ if not isinstance(obj, str) else obj,
        object_id=str(getattr(obj, "pk", "")) or None,
        before_hash=_hash_payload(before),
        after_hash=_hash_payload(after),
        request_id=req.get("request_id"),
        ip=req.get("ip"),
        user_agent=req.get("user_agent"),
        occurred_at=timezone.now(),
    )

    last_error = None
    for _ in range(4):
        head = AuditLog.objects.order_by("-id").values_list("row_hash", flat=True).first()
        row = AuditLog(prev_hash=head or GENESIS_HASH, **base)
        row.row_hash = _sha256(row.prev_hash + _canonical(_row_fields(row)))
        try:
            with transaction.atomic():
                row.save()
            return row
        except IntegrityError as exc:
            # S11: only a `prev_hash` collision is the race this loop exists
            # for. Retrying anything else four times and then reporting "the
            # chain is broken" discards the real cause in the one code path
            # where a misleading diagnostic is most expensive -- a CHECK
            # violation on actor_type used to surface as AuditChainBroken.
            if "prev_hash" not in str(exc):
                raise
            last_error = exc
    raise AuditChainBroken(
        f"could not append to the audit chain after 4 attempts: {last_error}"
    ) from last_error


def verify_audit_chain(start_id=0, batch=5000):
    """Recompute every row's hash and assert it follows its predecessor.

    Returns (rows_checked, head_hash). Raises AuditChainBroken naming the first
    bad row id.

    # ponytail: single-writer hash chain, verified by a management command.
    # Ceiling: assumes one appender and does not prove the chain head was not
    # rewritten wholesale. Upgrade path: write the daily chain head to a second
    # place -- printing it in the daily digest email is enough and costs nothing.
    """
    expected_prev = GENESIS_HASH
    checked = 0
    last_id = start_id
    if start_id:
        prev_row = AuditLog.objects.filter(id__lte=start_id).order_by("-id").first()
        if prev_row:
            expected_prev = prev_row.row_hash

    while True:
        rows = list(AuditLog.objects.filter(id__gt=last_id).order_by("id")[:batch])
        if not rows:
            break
        for row in rows:
            if row.prev_hash != expected_prev:
                raise AuditChainBroken(f"audit_log row {row.id}: prev_hash does not match the chain")
            recomputed = _sha256(row.prev_hash + _canonical(_row_fields(row)))
            if recomputed != row.row_hash:
                raise AuditChainBroken(f"audit_log row {row.id}: row_hash does not match its contents")
            expected_prev = row.row_hash
            last_id = row.id
            checked += 1
    return checked, expected_prev


# --- Jobs -----------------------------------------------------------------


def enqueue(kind, payload, run_after=None):
    """Queue a job. API-CONTRACT §3.

    Enqueue notifications with `transaction.on_commit(...)` so a rolled-back
    mutation never sends an email (API-CONTRACT §3). Handlers must be idempotent:
    delivery is at-least-once (ADR-001 §2.4).
    """
    from .jobs import REGISTRY

    if kind not in REGISTRY:
        raise ValueError(f"no handler registered for job kind {kind!r}")
    return Job.objects.create(
        kind=kind,
        payload=payload,
        run_after=run_after or timezone.now(),
        max_attempts=settings.JOB_MAX_ATTEMPTS,
    ).id


# --- Idempotency (API-CONTRACT §4.1) --------------------------------------


class Replay(Exception):
    """Raised with the stored response when a request is a replay."""

    def __init__(self, status, body):
        super().__init__("idempotent replay")
        self.status = status
        self.body = body


def idempotent(user_id, key, endpoint, body):
    """Claim an idempotency key, or tell the caller what to do instead.

    Returns the IdempotencyKey row on a first attempt. The *insert* is the lock
    (API-CONTRACT §4.1), so two simultaneous retries cannot both execute.

    Raises:
      IdempotencyKeyRequired  — no key supplied
      Replay                  — same key, same endpoint, same body, response stored
      IdempotencyInProgress   — same key, same endpoint, same body, no response yet
      IdempotencyKeyReused    — same key, different endpoint **or** different body -> 409

    **`endpoint` is part of the match (M3).** It was stored and never compared,
    so a key claimed on `POST /api/v1/offers` replayed its `201 {"state":
    "OFFERED"}` verbatim to `POST /api/v1/transfers/9/accept` — the client
    believing a transition had happened that never ran. From S4 every transition
    endpoint shares one key namespace per user, so this is a correctness bug in
    the mechanism rather than a hardening nicety. The `endpoint` column exists in
    DATA-MODEL §5 for precisely this comparison.

    **Anonymous callers (QA-S0 B3, then F10).** `UNIQUE (user_id, key)` does not
    fire when `user_id` is NULL — NULLs are distinct on both engines — so an
    anonymous replay used to claim a *second* row instead of replaying the
    first, and the contract has anonymous POSTs (`/auth/magic-link`,
    `/auth/consume`, `/grievances`, the public copyright-notice form). Of the
    two semantics on offer, the chosen one is **dedupe on something that is
    actually present**: migration 0004 adds a partial unique index on `key`
    alone WHERE `user_id IS NULL`, so anonymous keys share one global namespace.
    A sentinel `user_id = 0` would break the FK S1 adds to `users`, and keying
    on IP would break the retry it exists to serve the moment a phone changes
    network.

    **A global namespace is only safe if the key is unguessable, and nothing
    checked that.** QA-S0 F10 measured both halves of API-CONTRACT §4.1's
    argument and neither held: `Idempotency-Key: 1` was a legal anonymous key,
    and a second caller sending the same endpoint and the same body got the
    *first* caller's stored response — measured as
    `{"grievance_ref": "GRV-000123"}` reaching a stranger. On `/grievances`,
    which is the door a distressed non-user reaches us through, that is a
    disclosure, not a 409. Two changes, because one was not enough:

    1. **An anonymous key must parse as a UUID**, else `400 VALIDATION_FAILED`.
       That makes the contract's own "a collision requires guessing a UUIDv4"
       argument true instead of assumed.
    2. **An anonymous replay never returns a stored body.** It returns
       `Replay(status, None)`, so a retry still gets the right status code and
       is still not re-executed, and there is no path on which one anonymous
       caller receives another's response. The body is what the first caller
       already has; the second caller has no claim on it. This is the
       privacy-preserving default rather than the convenient one, and it costs a
       retrying client nothing it needs — an L3 form carries a server-generated
       key and an authenticated caller is unaffected.
    """
    if not key:
        raise IdempotencyKeyRequired()
    if user_id is None:
        try:
            uuid.UUID(str(key))
        except (ValueError, AttributeError, TypeError):
            raise ValidationFailed(
                "An Idempotency-Key on an unauthenticated request must be a UUID "
                "(API-CONTRACT §4.1). Anonymous keys share one namespace, so a "
                "short key is another caller's key."
            ) from None
    request_hash = _sha256(_canonical(body))
    try:
        with transaction.atomic():
            return IdempotencyKey.objects.create(
                user_id=user_id,
                key=str(key),
                endpoint=endpoint,
                request_hash=request_hash,
                expires_at=timezone.now() + timedelta(hours=settings.IDEMPOTENCY_RETENTION_HOURS),
            )
    except IntegrityError:
        existing = IdempotencyKey.objects.get(user_id=user_id, key=str(key))
        if existing.request_hash != request_hash or existing.endpoint != endpoint:
            raise IdempotencyKeyReused() from None
        if existing.response_status is None:
            raise IdempotencyInProgress() from None
        # Anonymous: the status, never the body. See the docstring.
        body = None if user_id is None else existing.response_body
        raise Replay(existing.response_status, body) from None


def store_idempotent_response(row, status, body):
    """Record the response so a later replay returns it verbatim."""
    row.response_status = status
    row.response_body = body
    row.save(update_fields=["response_status", "response_body"])


def new_request_id():
    return uuid.uuid4().hex
