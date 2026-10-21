"""Run the harness over every page the application serves, in EN and TA.

At the end of S0 there are no pages: `bookhop/urls.py` exposes `/healthz` and
`/readyz`, and `web/urls.py` (frontend-developer, S1) does not exist yet. So
this file **skips**, naming the slice, rather than passing over an empty list —
a parametrised test with no parameters is a green test that asserted nothing,
which is the failure mode this project has already identified.

When S1 lands, nothing here needs editing: `_page_routes()` discovers the routes
and the test runs. That is the whole point of standing the harness up in S0.
"""

import pytest
from django.urls import get_resolver

from .harness import check_html

#: Not pages: the two operational endpoints (API-CONTRACT §5.8) serve JSON and
#: plain text and are checked in tests/contract/test_s0_surface.py instead.
NOT_PAGES = {"healthz", "readyz"}

LOCALES = ["en", "ta"]


def _page_routes():
    """Every zero-argument route in the live URLconf, as request paths."""
    found = []

    def walk(patterns, prefix=""):
        for p in patterns:
            if hasattr(p, "url_patterns"):
                walk(p.url_patterns, prefix + str(p.pattern))
            else:
                route = prefix + str(p.pattern)
                if route in NOT_PAGES or "<" in route or "(" in route:
                    continue
                found.append("/" + route.lstrip("/"))

    walk(get_resolver().url_patterns)
    return sorted(found)


@pytest.mark.django_db
@pytest.mark.parametrize("locale", LOCALES)
def test_every_page_passes_the_structural_a11y_rules(client, locale):
    routes = _page_routes()
    if not routes:
        pytest.skip(
            "NOT VERIFIABLE IN S0 (slice=S0): the application serves no HTML "
            "pages. `web/urls.py` and `templates/**` are frontend-developer's "
            "tree and land in S1 (TASKS §1, §3). The harness itself is verified "
            "by tests/a11y/test_harness_selfcheck.py; this test runs the moment "
            "the first page exists, with no edit."
        )

    failures = {}
    for path in routes:
        response = client.get(path, headers={"accept-language": locale})
        if response.status_code != 200:
            continue  # routes needing auth or state belong to their slice's journey test
        violations = check_html(response.content.decode(), expect_lang=locale)
        if violations:
            failures[path] = [str(v) for v in violations]
    assert failures == {}, f"[{locale}] structural a11y violations: {failures}"


def test_keyboard_only_walkthrough_of_every_flow():
    pytest.skip(
        "MANUAL, NOT AUTOMATED (slice=S0): the charter requires "
        "'automated WCAG 2.2 AA plus a keyboard-only walkthrough of every flow, "
        "in both English and Tamil', and states that automated checks alone are "
        "not a pass. There is no flow to walk through at the end of S0 and no "
        "browser on this machine. Recorded in QA-S0.md as not verified, with the "
        "list of criteria no HTML-level harness can decide."
    )


def test_p75_lcp_on_a_throttled_mid_range_android_profile():
    pytest.skip(
        "NOT VERIFIABLE IN S0 (slice=S3): TASKS §2 S3 assigns p75 LCP and p95 "
        "search latency to QA. Both need a page, a browser and a throttling "
        "profile; this machine has no browser automation and S0 serves no page."
    )
