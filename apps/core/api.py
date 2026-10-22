"""The L2 plumbing every `/api/v1` handler shares — API-CONTRACT §2.2 and §4.1.

**TASKS §2 S1 assigns the §2.2 error-shape renderer to this slice**, with the
reason stated: *"It sits between backend L2 and frontend L3 and would otherwise
fall between two agents."* So it is one function, here, imported by both — never
a shape each handler builds for itself (`CLAUDE.md` rule 10).

Three pieces:

  * `error_payload(exc)` — the one error shape, as a dict. **L3 renders the
    same codes as pages**, so frontend needs the payload without the JSON
    response wrapped around it (API-CONTRACT §2.2).
  * `error_response(exc)` — that payload as a JSON response with the right
    status.
  * `endpoint(...)` — the decorator that gives an L2 handler its method check,
    JSON body parsing, `Idempotency-Key` handling, error rendering and audit
    request-id, so twelve handlers do not each reimplement eight lines of it.

**The 500 rule is the one with teeth.** API-CONTRACT §2.2: *"`INTERNAL` — never
echoes an exception message; the `request_id` is the only thing the user gets,
and it is enough to find the log."* An exception message is the single most
common way a stack trace, a SQL fragment or a file path reaches a user, so the
renderer does not take the message from the exception at all for a 5xx — it
takes it from `GENERIC_MESSAGES` and logs the real one.
"""

import functools
import json
import logging

from django.http import HttpResponse
from django.utils.translation import gettext as _

from .errors import (
    IdempotencyKeyRequired,
    ServiceError,
    ValidationFailed,
)
from .request_context import current_request
from .services import Replay, idempotent, store_idempotent_response

log = logging.getLogger(__name__)

#: The user-facing message for a code, used when the raise carried none. Every
#: one is a complete sentence a student can read, because `message` is
#: specified as "already localised" and L3 renders it directly.
#:
#: **5xx entries are not defaults — they are the only thing a 5xx may say.**
GENERIC_MESSAGES = {
    "VALIDATION_FAILED": _("Some of that could not be accepted. Check the fields marked below."),
    "NOT_AUTHENTICATED": _("Please sign in first."),
    "GATE_CLOSED": _("Listings are not open on this campus yet."),
    "NOT_ADULT_VERIFIED": _("BookHop is for students aged 18 and over."),
    "NOT_CAMPUS_VERIFIED": _("Confirm your college email address first."),
    "CONSENT_REQUIRED": _("This needs your permission first. You can change it any time."),
    "SUSPENDED": _("This account cannot do that at the moment."),
    # `FORBIDDEN` is a code API-CONTRACT §2.2's 403 row does not list. Its table
    # says "**Example** codes", so adding one is within the contract rather than
    # an amendment — but it is worth naming: the listed 403 codes are all about
    # the *student's* state (not adult, not campus-verified, suspended, gate
    # closed) and none covers "this is a staff-only operation". `NotPermitted`
    # is raised only by `review_age`, `age_review_queue` and
    # `log_personal_data_access`, which §5.7 puts behind the Django admin rather
    # than on L2 — so no student can reach it today. Flagged to cto as the one
    # code S1 adds.
    "FORBIDDEN": _("That is a staff-only action."),
    "NOT_FOUND": _("Not found."),
    "GONE": _("That is no longer available."),
    "VERSION_CONFLICT": _("Someone changed this while you were looking at it. Reload and try again."),
    "IDEMPOTENCY_KEY_REQUIRED": _("That request could not be sent. Please try again."),
    "IDEMPOTENCY_KEY_REUSED": _("That looks like a different request with a key already used."),
    "IDEMPOTENCY_IN_PROGRESS": _("Still working on the last one. Try again in a moment."),
    "TRANSITION_NOT_ALLOWED": _("That cannot be done at this stage."),
    # S2. Both are raised with their own sentence at every site; these are the
    # fallbacks, and they exist so a future raise with no message cannot render
    # a bare code to a student.
    "DUPLICATE_ISBN": _("We already have that book — check it is the same edition."),
    "SELLER_TERMS_NOT_ACCEPTED": _("Please read and accept the seller terms first."),
    "TOO_MANY_PHOTOS": _("That listing already has four photos."),
    "LISTING_ALREADY_RESERVED": _("Someone is already arranging to take this book."),
    "GUARD_FAILED": _("That cannot be done at this stage."),
    "RATE_LIMITED": _("Too many requests. Please try again later."),
    "METHOD_NOT_ALLOWED": _("That request could not be sent. Please try again."),
    # The whole of what a 500 is permitted to say.
    "INTERNAL": _("Something went wrong on our side. Quote this reference if you contact us."),
}


def error_payload(exc, request_id=None):
    """API-CONTRACT §2.2, one shape, everywhere.

    `field_errors` is present **only on 400**, per the contract's own sentence;
    on every other status the key is absent rather than null, so a client
    branching on its presence is branching on what the contract promises.
    """
    code = getattr(exc, "code", "INTERNAL")
    status = getattr(exc, "http_status", 500)
    if status >= 500:
        # Never the exception's own text. See the module docstring.
        message = str(GENERIC_MESSAGES["INTERNAL"])
        log.error("api.internal_error", exc_info=exc, extra={"code": code})
    else:
        message = str(exc) if str(exc) and str(exc) != code else str(GENERIC_MESSAGES.get(code, code))
    body = {
        "code": code,
        "message": message,
        "request_id": request_id or current_request().get("request_id"),
        "retry_after": getattr(exc, "retry_after", None),
    }
    if status == 400:
        body["field_errors"] = dict(getattr(exc, "context", {}).get("field_errors", {}) or {})
    return {"error": body}


def error_response(exc, request_id=None):
    """The payload as a JSON response, with the contract's status and headers."""
    status = getattr(exc, "http_status", 500)
    payload = error_payload(exc, request_id=request_id)
    response = json_response(payload, status=status)
    retry_after = payload["error"]["retry_after"]
    if retry_after is not None:
        response["Retry-After"] = str(retry_after)
    return response


def jsonable(payload):
    """`payload` with every value in the form the response will carry.

    **One canonicalisation, used by the response and by the stored replay**,
    and that is a correctness requirement rather than tidiness. API-CONTRACT
    §4.1 promises a replay *"returns the stored response"* — so the bytes a
    retry gets must be the bytes the first caller got, and a second
    serialisation rule would make them differ in exactly the fields that are
    hardest to notice.

    **Found by running the journey.** `store_idempotent_response` wrote the
    handler's dict straight into `idempotency_keys.response_body`, a
    `JSONField` whose encoder does **not** take `default=str` — so any payload
    containing a `datetime` raised *"Object of type datetime is not JSON
    serializable"* **after the mutation had committed**. The student saw a
    500 for a listing, a want or a correction request that had actually been
    created. S1 never hit it because no S1 response carried a timestamp;
    `POST /requests` and `POST /account/correction` both do.
    """
    return json.loads(json.dumps(payload, default=str))


def json_response(payload, status=200):
    return HttpResponse(
        json.dumps(payload, default=str), status=status, content_type="application/json"
    )


#: Content types whose body Django parses itself, from the raw stream.
#:
#: **Reading `request.body` first makes `request.FILES` raise**
#: (*"You cannot access body after reading from request's data stream"*), and
#: that is a 500 on the only multipart endpoint in the product —
#: `POST /api/v1/listings/{id}/photos`.
#:
#: **Found by running the journey, not by a test.** Every photo unit test
#: calls `add_photo` directly with a file object, so the decorator was never
#: in the path; the first client to send a real multipart upload got a 500
#: with an exception message the contract forbids echoing. This is the same
#: shape as the S1 defect TASKS §4's checkbox was added for, one layer up.
_STREAM_PARSED = ("multipart/form-data", "application/x-www-form-urlencoded")


def _parse_body(request):
    content_type = (request.content_type or "").lower()
    if content_type.startswith(_STREAM_PARSED):
        # Django will parse this into `request.POST` / `request.FILES` when
        # the handler asks. Touching `request.body` here would consume the
        # stream and make that raise.
        return {key: value for key, value in request.POST.items()}
    if not request.body:
        return {}
    try:
        parsed = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ValidationFailed(_("That request could not be read."), field_errors={}) from None
    if not isinstance(parsed, dict):
        raise ValidationFailed(_("That request could not be read."), field_errors={}) from None
    return parsed


class MethodNotAllowed(ServiceError):
    code = "METHOD_NOT_ALLOWED"
    http_status = 405


def endpoint(*, methods, idempotent_write=None, actor=None):
    """Wrap an L2 handler: method, body, idempotency, errors.

    `idempotent_write` is the endpoint key stored in `idempotency_keys.endpoint`
    and compared on replay (API-CONTRACT §4.1, M3). Pass it on every POST, PATCH
    and DELETE; pass `None` on a GET, which carries no key and needs none.

    `actor` is a callable `request -> user | None`. It is injected rather than
    imported so `apps.core` does not import `apps.accounts` (the dependency runs
    the other way), and so a test can drive a handler without a session.

    The handler signature is `handler(request, body, user) -> (status, payload)`.
    """

    # **Anything that answers GET must answer HEAD.** Derived here, once, from
    # the `methods` the endpoint declares, so the pair cannot be split by
    # someone later editing one of the two names — which is the property
    # Django's own `require_safe` has and why frontend used it for the same
    # omission in its tree. Measured by frontend's resolver probe: three JSON
    # routes answered GET and refused HEAD with 405.
    #
    # Worth recording what found it rather than only what it was: a HEAD is a
    # request only a real client sends, so no amount of the tests we already
    # write would have caught it. Both defects found by running the app this
    # week were that shape.
    allowed = frozenset(methods) | ({"HEAD"} if "GET" in methods else frozenset())

    def decorate(handler):
        def view(request, *args, **kwargs):
            request_id = current_request().get("request_id")
            try:
                if request.method not in allowed:
                    raise MethodNotAllowed()
                body = _parse_body(request) if request.method in ("POST", "PATCH", "PUT") else {}
                user = actor(request) if actor else None
                row = None
                if idempotent_write and request.method in ("POST", "PATCH", "PUT", "DELETE"):
                    key = request.headers.get("Idempotency-Key", "")
                    if not key:
                        raise IdempotencyKeyRequired()
                    row = idempotent(
                        getattr(user, "id", None), key, idempotent_write, body
                    )
                status, payload = handler(request, body, user, *args, **kwargs)
                # Canonicalised **before** storing and returning, so the
                # replay and the original are the same bytes — and so a
                # timestamp in the payload cannot make the store raise after
                # the mutation has already committed. See `jsonable`.
                payload = jsonable(payload)
                if row is not None:
                    store_idempotent_response(row, status, payload)
                return json_response(payload, status=status)
            except Replay as replay:
                response = json_response(replay.body, status=replay.status)
                response["Idempotency-Replayed"] = "true"
                return response
            except ServiceError as exc:
                return error_response(exc, request_id=request_id)
            except Exception as exc:  # noqa: BLE001 - deliberate catch-all
                # **REVIEW-S1 R11.** Without this an unexpected exception
                # escapes to Django's own handler, and the student gets a page
                # that is not §2.2's shape, carries no `request_id`, and — with
                # DEBUG on anywhere — carries a traceback. §2.2 is explicit that
                # a 500 *"never echoes an exception message; the `request_id` is
                # the only thing the user gets, and it is enough to find the
                # log."* That promise needs something to keep it.
                #
                # `error_payload` logs the real exception with `exc_info` and
                # renders only the generic sentence, so nothing is lost from the
                # operator's side and nothing leaks to the student's.
                return error_response(ServiceError(str(exc)), request_id=request_id)

        # `functools.wraps` rather than copying two attributes by hand: it
        # also sets `__wrapped__`, which is what makes `inspect.getsource`
        # return the **handler** instead of this wrapper. Without it, any test
        # that reads a handler's body — including the one asserting each
        # endpoint calls the precondition gate §2.5's table requires — reads
        # the decorator for every endpoint and compares it against itself.
        functools.wraps(handler)(view)
        view.csrf_exempt = False
        return view

    return decorate
