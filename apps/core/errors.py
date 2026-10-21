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


class AuditChainBroken(ServiceError):
    """verify_audit_chain found a row whose hash does not follow its predecessor."""

    code = "INTERNAL"
    http_status = 500
