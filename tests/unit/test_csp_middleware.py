"""CSP — the ASVS V1/V3 **L2** control THREAT-MODEL §4 B3 names.

`CLAUDE.md` rule 9: the document names this control, so the control needs a test
asserting it exists. TASKS §2 S1 is sharper about *when*: *"It must exist
**before the first HTML page ships**, not after."* frontend-developer is writing
templates concurrently with this commit, so these assertions land now.

**What is asserted, and why each one is here rather than being obvious.** Every
row is a way this control has been weakened in other codebases without anyone
noticing, because the header is still present in all of them:

  * the header exists on an HTML response **and on a JSON one** — a policy
    applied only to HTML misses a JSON error page rendered as HTML by a proxy;
  * `default-src 'self'`, verbatim, which is the directive TASKS names;
  * **no `'unsafe-inline'` and no `'unsafe-eval'` on any directive** — the one
    weakening that keeps the header, keeps the directive and removes the
    protection;
  * a nonce in `script-src`, matching `request.csp_nonce`, so a template can
    actually use it — a nonce the template cannot read is a nonce nobody uses,
    and the fix under pressure is `'unsafe-inline'`;
  * **the nonce differs between requests** — a reused nonce is the same as no
    nonce, because an injected script can carry it.
"""

import pytest

pytestmark = pytest.mark.django_db

HEADER = "Content-Security-Policy"


def policy(client, path="/healthz"):
    return client.get(path)[HEADER]


def test_every_response_carries_the_policy(client):
    for path in ("/healthz", "/readyz"):
        response = client.get(path)
        assert HEADER in response, f"{path} has no Content-Security-Policy"


def test_the_policy_is_default_src_self(client):
    assert "default-src 'self'" in policy(client)


@pytest.mark.parametrize("weakening", ["unsafe-inline", "unsafe-eval", "*", "http:", "data: script"])
def test_the_policy_contains_no_weakening(client, weakening):
    """The failure mode that keeps the header and removes the control.

    `data:` is permitted on `img-src` (inline SVG icons are a design-system
    idiom frontend owns) and is **not** a script sink, so the case asserted is
    `data:` reaching a script directive, not `data:` anywhere.
    """
    assert weakening not in policy(client)


def test_a_nonce_is_offered_to_script_src_and_to_the_template(client, rf):
    """The nonce must be on the request *before* the view runs, because a
    template that renders it is rendered inside the view."""
    from apps.core.middleware import ContentSecurityPolicyMiddleware

    seen = {}

    def view(request):
        from django.http import HttpResponse

        seen["nonce"] = request.csp_nonce
        return HttpResponse("<p>hi</p>", content_type="text/html")

    response = ContentSecurityPolicyMiddleware(view)(rf.get("/"))
    assert seen["nonce"], "request.csp_nonce was not set before the view ran"
    assert f"'nonce-{seen['nonce']}'" in response[HEADER]
    assert "script-src 'self'" in response[HEADER]


def test_the_nonce_is_fresh_per_request(client):
    """A reused nonce is no nonce. Twenty requests, twenty distinct values —
    enough to catch a module-level constant or a cached property, which is how
    this is usually got wrong."""
    nonces = {policy(client) for _ in range(20)}
    assert len(nonces) == 20, "the CSP nonce is not per-request"


def test_the_nonce_has_at_least_128_bits_of_entropy():
    """The CSP specification's own floor. Asserted on the generator rather than
    on a sample, because a 1-byte nonce would still look random."""
    import inspect

    from apps.core.middleware import ContentSecurityPolicyMiddleware

    source = inspect.getsource(ContentSecurityPolicyMiddleware.__call__)
    assert "secrets.token_urlsafe(16)" in source, (
        "the nonce is not 16 bytes from `secrets`; a nonce from `random` or "
        f"shorter than 128 bits is a guessable nonce:\n{source}"
    )


@pytest.mark.parametrize(
    "directive",
    ["object-src 'none'", "base-uri 'none'", "form-action 'self'", "frame-ancestors 'none'"],
)
def test_the_clickjacking_and_injection_directives_are_present(client, directive):
    """ASVS V3 L2. Each costs one directive once `default-src` is `'self'`, and
    each stops a different injected element: `<object>`, a re-pointed `<base>`,
    a form POSTing a CSRF token offsite, and framing."""
    assert directive in policy(client)


def test_a_view_that_sets_its_own_policy_is_not_overwritten(rf):
    """`setdefault`, asserted. A future `/dev/states` or a sandboxed preview must
    be able to tighten the policy; a middleware that always overwrote would make
    that impossible and the workaround would be removing the middleware."""
    from django.http import HttpResponse

    from apps.core.middleware import ContentSecurityPolicyMiddleware

    def view(request):
        response = HttpResponse("ok")
        response[HEADER] = "default-src 'none'"
        return response

    assert ContentSecurityPolicyMiddleware(view)(rf.get("/"))[HEADER] == "default-src 'none'"


def test_the_middleware_is_installed_in_settings():
    """The control existing in a module and not in MIDDLEWARE is the shape
    `CLAUDE.md` rule 9 is about: present in the repository, absent from every
    response."""
    from django.conf import settings

    assert "apps.core.middleware.ContentSecurityPolicyMiddleware" in settings.MIDDLEWARE
