"""Per-request context: request_id, ip, user_agent.

These three belong on every audit row and every log line, and threading them
through every service signature would be noise in fifty places. A contextvar is
the stdlib answer and is correct under both WSGI threads and async.
"""

from contextvars import ContextVar

_ctx = ContextVar("bookhop_request", default={})


def current_request():
    return _ctx.get()


def set_request(request_id=None, ip=None, user_agent=None, scheme=None, host=None):
    """`scheme` and `host` are here for one reason, stated so nobody widens it:

    **a job has no request, so it has no scheme or host to build a link from.**
    `accounts.send_magic_link` renders an email containing an absolute sign-in
    URL, and the two pieces an absolute URL needs can only be known at the
    moment a *request* enqueues the job. They are captured here and copied into
    the job payload at enqueue time; `public_origin()` is the one place that
    falls back when there is no request at all.
    """
    return _ctx.set(
        {
            "request_id": request_id,
            "ip": ip,
            "user_agent": user_agent,
            "scheme": scheme,
            "host": host,
        }
    )


def reset_request(token):
    _ctx.reset(token)


def public_origin():
    """`(scheme, host)` for a link that has to work outside the browser.

    From the live request when there is one; otherwise from
    `BOOKHOP_PUBLIC_ORIGIN`, which is what a management command or a job-chained
    enqueue has.

    **Raises when neither is available.** A default of `localhost` would send a
    student an email containing a link to their own machine — a plausible-looking
    value that fails silently for the recipient and succeeds in every test, which
    is the defect class this project keeps finding. An unsendable email that
    raises is better than a sent one that cannot be clicked.
    """
    from django.conf import settings

    context = current_request()
    scheme, host = context.get("scheme"), context.get("host")
    if scheme and host:
        return scheme, host

    configured = getattr(settings, "PUBLIC_ORIGIN", "") or ""
    if "://" in configured:
        scheme, _, host = configured.partition("://")
        if scheme and host:
            return scheme, host.rstrip("/")

    raise RuntimeError(
        "no public origin is available, so an absolute link cannot be built. "
        "Either this ran inside a request (RequestIdMiddleware supplies the "
        "scheme and host) or BOOKHOP_PUBLIC_ORIGIN must be set, e.g. "
        "https://bookhop.example. There is deliberately no default: a localhost "
        "default would email a student a link to their own machine."
    )
