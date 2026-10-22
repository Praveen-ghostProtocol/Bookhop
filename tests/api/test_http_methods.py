"""Every route that answers GET answers HEAD — probed, not read.

**Found by frontend's resolver probe, in backend's tree.** Three JSON routes —
`/api/v1/account`, `/api/v1/account/consents`, `/api/v1/account/export` —
returned 401 on GET (correct, unauthenticated) and **405 on HEAD**. Anything
that answers GET must answer HEAD.

**The instrument matters more than the bug here.** A HEAD is a request only a
real client sends; no amount of the tests we already write would have caught
it, because none of them sends one. That is the same shape as the other two
defects found by running the application this week — a Django comment that
swallowed a page, and a 500 on the first POST against a stale database.
*"Running the thing beat testing it"*, twice in two hours.

So this test is the **probe**, not an enumeration: it walks every route in the
resolver and tries both methods. A list of paths would have to be remembered;
the resolver cannot be forgotten, and every route S2 adds is covered the day
it is added.

The fix is one derivation in `apps.core.api.endpoint` — `GET` implies `HEAD`,
computed from the declared methods — so the pair cannot be split by someone
editing one of the two names. That is the property Django's own `require_safe`
has, which is what frontend used for the same omission.
"""

import pytest
from django.urls import get_resolver

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.urls_api_only")]

#: A 405 is the failure under test; anything else means the route answered.
METHOD_NOT_ALLOWED = 405


def api_paths():
    """Every concrete `/api/v1/` path in the resolver, with its parameters
    filled in. Parameterised routes are included because a 405 does not depend
    on whether the id resolves."""
    resolver = get_resolver("tests.urls_api_only")
    paths = []
    for pattern in resolver.url_patterns:
        prefix = str(pattern.pattern)
        sub = getattr(pattern, "url_patterns", None)
        if sub is None:
            paths.append("/" + prefix)
            continue
        for leaf in sub:
            route = prefix + str(leaf.pattern)
            route = route.replace("<str:purpose_key>", "chat").replace("<str:kind>", "privacy")
            paths.append("/" + route)
    return sorted(set(paths))


def test_the_probe_sees_the_routes_it_claims_to():
    """`CLAUDE.md` rule 12. A probe over an empty resolver passes everything."""
    paths = api_paths()
    assert len(paths) >= 10, paths
    assert "/api/v1/account" in paths
    assert "/api/v1/notices/privacy" in paths


@pytest.mark.parametrize("path", api_paths())
def test_a_route_that_answers_get_also_answers_head(client, path):
    """The rule. A route that refuses GET may refuse HEAD — the two POST-only
    routes do, correctly — but a route that answers GET must not 405 on HEAD.
    """
    get_status = client.get(path).status_code
    head_status = client.head(path).status_code

    if get_status == METHOD_NOT_ALLOWED:
        assert head_status == METHOD_NOT_ALLOWED, (
            f"{path} refuses GET but answers HEAD, which is the inverse omission"
        )
        return
    assert head_status != METHOD_NOT_ALLOWED, (
        f"{path} answers GET with {get_status} and refuses HEAD with 405. "
        "Anything that answers GET must answer HEAD."
    )


@pytest.mark.parametrize("path", api_paths())
def test_head_and_get_agree_on_the_status(client, path):
    """Not just "not 405": a HEAD whose status differed from its GET would be a
    second, invisible code path — and `/api/v1/account` returning 401 on GET
    and 200 on HEAD would be an authorization bypass nobody would look for."""
    assert client.head(path).status_code == client.get(path).status_code, path


def test_a_post_only_route_still_refuses_both(client):
    """The derivation adds HEAD only where GET is declared, so a POST-only
    route is unchanged. Asserted because the obvious wrong fix is allowing HEAD
    everywhere."""
    for path in ("/api/v1/auth/magic-link", "/api/v1/account/erase"):
        assert client.get(path).status_code == METHOD_NOT_ALLOWED, path
        assert client.head(path).status_code == METHOD_NOT_ALLOWED, path
