"""The error codes in API-CONTRACT §2.2, as exceptions the service layer raises.

L2 and L3 map `.code` onto the single error shape. Only the codes S0 can
actually raise are here; later slices add theirs beside them.
"""


class ServiceError(Exception):
    code = "INTERNAL"
    http_status = 500

    def __init__(self, message="", **context):
        super().__init__(message or self.code)
        self.context = context


class ValidationFailed(ServiceError):
    code = "VALIDATION_FAILED"
    http_status = 400


class GateClosed(ServiceError):
    """ADR-002 §4.1(a). The campus discovery gate is closed."""

    code = "GATE_CLOSED"
    http_status = 403


class NotFound(ServiceError):
    """API-CONTRACT §2.2: not found *or* not visible to this actor, same body."""

    code = "NOT_FOUND"
    http_status = 404


class VersionConflict(ServiceError):
    code = "VERSION_CONFLICT"
    http_status = 409


class IdempotencyKeyRequired(ServiceError):
    code = "IDEMPOTENCY_KEY_REQUIRED"
    http_status = 400


class IdempotencyKeyReused(ServiceError):
    code = "IDEMPOTENCY_KEY_REUSED"
    http_status = 409


class IdempotencyInProgress(ServiceError):
    code = "IDEMPOTENCY_IN_PROGRESS"
    http_status = 409
    retry_after = 2


# --- S1: accounts, age, consent, campus verification, deletion -------------
#
# API-CONTRACT §2.2's status table is the authority for each `http_status`, and
# §2.5's ordering is the authority for which one a caller sees first. The 403 vs
# 422 split is a real distinction the contract asks clients to branch on: **403
# means *you* may not; 422 means the *object* is not in a state where this is
# possible.**


class NotAuthenticated(ServiceError):
    code = "NOT_AUTHENTICATED"
    http_status = 401


class Suspended(ServiceError):
    code = "SUSPENDED"
    http_status = 403


class NotAdultVerified(ServiceError):
    code = "NOT_ADULT_VERIFIED"
    http_status = 403


class NotCampusVerified(ServiceError):
    code = "NOT_CAMPUS_VERIFIED"
    http_status = 403


class ConsentRequired(ServiceError):
    """403. The body names the missing `purpose_key` (API-CONTRACT §2.5 step 5)."""

    code = "CONSENT_REQUIRED"
    http_status = 403


class NotPermitted(ServiceError):
    """403. A student reached a staff-only service function."""

    code = "FORBIDDEN"
    http_status = 403


class Gone(ServiceError):
    code = "GONE"
    http_status = 410


class RateLimited(ServiceError):
    code = "RATE_LIMITED"
    http_status = 429
    retry_after = 60

    def __init__(self, message="", retry_after=None, **context):
        super().__init__(message, **context)
        if retry_after is not None:
            self.retry_after = retry_after


class EmailDomainNotRecognised(ServiceError):
    """The submitted address is not at a domain any active campus accepts.

    **L2 and L3 must still answer 202** (API-CONTRACT §5.1): *"Always returns
    202 whatever happens — a different response for an unknown address is an
    account-enumeration oracle."* So this exception exists to stop the service
    layer sending an email, not to be rendered. PRD AC-A1.2 is what stops the
    202 being a silent dead end: the page names the accepted domains
    generically, without echoing the submitted address.
    """

    code = "VALIDATION_FAILED"
    http_status = 400


class TokenInvalid(ServiceError):
    code = "VALIDATION_FAILED"
    http_status = 400


class TokenExpired(ServiceError):
    code = "VALIDATION_FAILED"
    http_status = 400


class TokenAlreadyUsed(ServiceError):
    """A magic link used twice. PRD AC-A1.3: *"a plain 'this link has been used
    — ask for a new one' page with a working button, never a stack trace or a
    raw error code."*"""

    code = "VALIDATION_FAILED"
    http_status = 400


class UnderEighteen(ServiceError):
    """403 NOT_ADULT_VERIFIED, and the account is deleted in the same
    transaction (DATA-MODEL §2, PRD AC-A2.1)."""

    code = "NOT_ADULT_VERIFIED"
    http_status = 403


class AuditChainBroken(ServiceError):
    """verify_audit_chain found a row whose hash does not follow its predecessor."""

    code = "INTERNAL"
    http_status = 500


class AuditAppendContention(ServiceError):
    """`record_audit` lost its retry budget racing other appenders.

    **Deliberately NOT an `AuditChainBroken` and deliberately not a subclass of
    one.** The chain is intact in this case — every committed row still follows
    its predecessor, and `verify_audit_chain` passes. What failed is one
    appender's attempt to win the `prev_hash UNIQUE` race.

    Until the first PostgreSQL run these were the same exception, and that was
    wrong in the expensive direction: a load spike would have raised
    `AuditChainBroken` and sent an operator hunting a tamper, during the one
    incident class where a misleading diagnostic costs the most. The race
    cannot occur on SQLite at all (one writer), so nothing had ever raised it
    for this reason — measured at 12 concurrent appenders, where exactly one
    lost four straight races and its audit row was dropped.
    """

    code = "INTERNAL"
    http_status = 500
