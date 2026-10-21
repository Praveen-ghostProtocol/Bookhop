"""Per-request context: request_id, ip, user_agent.

These three belong on every audit row and every log line, and threading them
through every service signature would be noise in fifty places. A contextvar is
the stdlib answer and is correct under both WSGI threads and async.
"""

from contextvars import ContextVar

_ctx = ContextVar("bookhop_request", default={})


def current_request():
    return _ctx.get()


def set_request(request_id=None, ip=None, user_agent=None):
    return _ctx.set({"request_id": request_id, "ip": ip, "user_agent": user_agent})


def reset_request(token):
    _ctx.reset(token)
