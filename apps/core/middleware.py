"""X-Request-Id — API-CONTRACT §2.1.

Accepted from the client, else generated. Echoed on every response, written to
`audit_log.request_id` and every log line. **This is the identifier a 6-hour
CERT-In investigation uses, so it is never optional.**
"""

import re

from .request_context import reset_request, set_request
from .services import new_request_id

#: A client-supplied id goes into logs and the audit trail, so it is validated
#: rather than trusted: no newlines (log injection), no unbounded length.
#:
#: `fullmatch`, not `match`: with `match`, `$` also matches *before* a trailing
#: newline, so "abc\n" was accepted. The practical consequence was narrow — a
#: conformant server rejects LF in a header value and `json.dumps` escapes the
#: log line regardless — but `response["X-Request-Id"] = "abc\n"` raises
#: Django's BadHeaderError, i.e. a 500, and the value also reached
#: `audit_log.request_id`. REVIEW-S0 S1.
_SAFE_ID = re.compile(r"[A-Za-z0-9._:-]{1,64}")


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = request.headers.get("X-Request-Id", "")
        request_id = supplied if _SAFE_ID.fullmatch(supplied) else new_request_id()
        request.request_id = request_id
        token = set_request(
            request_id=request_id,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=(request.headers.get("User-Agent") or "")[:400],
        )
        try:
            response = self.get_response(request)
        finally:
            reset_request(token)
        response["X-Request-Id"] = request_id
        return response
