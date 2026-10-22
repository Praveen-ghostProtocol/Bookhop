"""Request middleware — API-CONTRACT §2.1 and THREAT-MODEL §4 B3.

Two things live here:

  * `RequestIdMiddleware` — X-Request-Id, accepted from the client, else
    generated. Echoed on every response, written to `audit_log.request_id` and
    every log line. **This is the identifier a 6-hour CERT-In investigation
    uses, so it is never optional.**
  * `ContentSecurityPolicyMiddleware` — the ASVS V1/V3 **L2** control
    THREAT-MODEL §4 B3 names and TASKS §2 assigns to S1 backend, with the
    standing instruction that it must exist **before the first HTML page
    ships**. The frontend agent is writing templates concurrently, so it lands
    in S1's first commit rather than beside the first page.
"""

import re
import secrets

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
            # A job has no request, so the only moment an absolute link's
            # scheme and host are knowable is here. `get_host()` is validated
            # against ALLOWED_HOSTS by Django, so a Host-header injection
            # cannot put an attacker's domain into a sign-in email.
            scheme=request.scheme,
            host=request.get_host(),
        )
        try:
            response = self.get_response(request)
        finally:
            reset_request(token)
        response["X-Request-Id"] = request_id
        return response


class LocaleGateMiddleware:
    """The Tamil locale gate, applied where every request passes — not per page.

    **THREAT-MODEL §6.1(c) forbids this leak by name:** *"Tamil is absent from
    the language switcher **and from `Accept-Language` negotiation** while
    `i18n.ta_enabled` is false."* `django.middleware.locale.LocaleMiddleware`
    negotiates against `settings.LANGUAGES`, which lists `ta`, so without
    intervention a plain `Accept-Language: ta` header selects Tamil and ships
    unreviewed strings to a student.

    frontend-developer found the leak and closed it in its own page helper,
    which was the right escalation and the wrong layer: **a helper in `web/`
    covers only the pages that call it**, and API-CONTRACT §2.1 makes
    `Accept-Language` select the locale for the JSON API too — handlers that
    never call a `web/` helper. So the leak was closed on six pages and open on
    every L2 endpoint, now and in every later slice, and it reopened on the
    first page that forgot the helper. One middleware, one place, every request.

    **`ta` stays in `settings.LANGUAGES`** and that is deliberate: removing it
    breaks `makemessages` and breaks staff rendering once the flag *is* on, and
    a static setting cannot read a database flag at import time anyway. **The
    flag is the gate; this is where it is applied.**

    Placed immediately after `LocaleMiddleware`, because it has to correct a
    decision that middleware has already made — running before it would be
    overwritten.

    # ponytail: one flag read per request, uncached. Ceiling: one indexed
    # primary-key lookup on `feature_flags` on every request that negotiated a
    # gated language. Upgrade path: none wanted — `flag()`'s own note applies,
    # a cache-invalidation bug here would ship unreviewed Tamil.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.utils import translation

        from .i18n import allowed_locale

        active = translation.get_language()
        # `apps.core.i18n.allowed_locale` is the **one** definition of the gate
        # (REVIEW-S1 B4 / `CLAUDE.md` rule 10): this middleware and every
        # service that picks a locale are readers of it, never second copies.
        permitted = allowed_locale(active)
        if permitted != (active or "").split("-")[0]:
            translation.activate(permitted)
            request.LANGUAGE_CODE = translation.get_language()
        return self.get_response(request)


#: The policy, as one ordered list of directives. `script-src` gains the
#: per-request nonce; everything else is fixed.
#:
#: TASKS §2 S1 specifies "`default-src 'self'`, no inline script, nonce for the
#: one bootstrap script". The rest of the list is the ASVS V3 L2 set that costs
#: nothing once `default-src` is already `'self'`, and each line says what it
#: stops:
#:
#:   object-src 'none'      — no Flash/applet/embed sink
#:   base-uri 'none'        — an injected <base> cannot re-point every relative URL
#:   form-action 'self'     — an injected form cannot POST a CSRF token offsite
#:   frame-ancestors 'none' — clickjacking; the header half is X_FRAME_OPTIONS
#:   img-src 'self' data:   — `data:` because inline SVG icons are a design-system
#:                            idiom frontend owns; it is not a script sink
#:
#: **No `'unsafe-inline'` and no `'unsafe-eval'`, on any directive.** htmx is
#: vendored (THREAT-MODEL §6.2), so there is no CDN origin to allow, and
#: `script-src 'self'` plus a nonce is the whole script surface.
#:
#: `style-src` is `'self'` with **no** nonce and no `'unsafe-inline'`: a style
#: attribute is blocked, which is the property backend's own hard rule
#: ("backend never emits inline styles", TASKS §1) already assumes. If a
#: frontend component genuinely needs one, the answer is a class in
#: `static/css/tokens.css`, not a widened policy — recorded here because the
#: tempting fix under schedule pressure is `'unsafe-inline'`, which would
#: silently take the chapter back to L1.
CSP_DIRECTIVES = (
    "default-src 'self'",
    "script-src 'self' 'nonce-{nonce}'",
    "style-src 'self'",
    "img-src 'self' data:",
    "connect-src 'self'",
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'self'",
    "frame-ancestors 'none'",
)


class ContentSecurityPolicyMiddleware:
    """`Content-Security-Policy` on every response, with a per-request nonce.

    The nonce is on `request.csp_nonce`, which is what a template renders as
    `<script nonce="{{ request.csp_nonce }}">`. It is generated **before** the
    view runs, because a template that reads it is rendered inside the view.

    `secrets.token_urlsafe(16)` is 128 bits, which is the CSP specification's
    own floor, and a fresh value per request — a reused nonce is the same as no
    nonce, since an injected script can carry it.

    # ponytail: one static policy for every response, HTML or JSON. Ceiling: a
    # page needing a third-party origin would need a per-view override, which
    # does not exist. Upgrade path: a `csp_extra` attribute read off the view,
    # the day there is a second origin. There is deliberately no report-only
    # mode and no report-uri: a report endpoint is a new unauthenticated write
    # surface (ASVS V13) and nobody is watching a report queue at pilot.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce
        response = self.get_response(request)
        # An explicit header already set by a view wins, so a future
        # `/dev/states` or a sandboxed preview can tighten but not be
        # overwritten by accident.
        response.setdefault(
            "Content-Security-Policy",
            "; ".join(d.format(nonce=nonce) for d in CSP_DIRECTIVES),
        )
        return response
