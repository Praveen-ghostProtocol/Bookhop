"""S2's pages, including the ones the sweep in `test_pages.py` cannot reach.

**Why a second a11y file.** `_page_routes()` walks the URLconf and **skips
every parameterised route** — `if any(ch in route for ch in "<(^$*"): continue`
— which was right when every page was zero-argument. S2 ships the two pages
the product is actually about behind an id:

    /listing/<int:listing_id>        the listing a buyer reads
    /sell/<int:listing_id>/photos    the upload step, JOURNEYS J2 step 8

Neither is in the sweep, and neither would have been reported as missing: the
sweep's reach assertion is *"some gated route answered 200"*, which the account
pages satisfy. That is `CLAUDE.md` rule 10's fourth disguise in QA's own
harness for the **second** time — *"the accessibility harness reached four
pages of eleven and reported coverage for a whole slice"* — and the correction
the first time was to assert the reach, so the correction this time is to
assert it **by name**.

`SYSTEM.md` and WCAG 2.2 AA are the standard. The structural rules are
`tests/a11y/harness.py`'s, reused rather than restated.

**Scope, stated so nothing here is over-read.** These are the structural
rules an HTML-level harness can decide. **The keyboard-only walkthrough is
still not run** — no browser automation exists on this machine — and
`test_pages.py` records that as a skip naming the slice. That skip covers S2's
pages too and this file does not weaken it. Automated checks alone are not a
pass; the charter says so and QA-S2 repeats it.
"""

import pytest

from tests.a11y.harness import check_html
from tests.a11y.test_pages import _is_html, _served_locales

pytestmark = pytest.mark.django_db


def _s2_pages(listing_id):
    """S2's routes, with the parameterised ones resolved to a real row.

    Returned as `(path, why)` so a failure names the page in product terms —
    *"the listing a buyer reads"* is a more useful failure than `/listing/3`.
    """
    return [
        ("/sell", "the seller's own listings, JOURNEYS J2 step 2"),
        ("/sell/find-book", "the book finder, J2 step 4 — htmx, degrades to submit"),
        (f"/listing/{listing_id}", "the listing page a buyer reads"),
        (f"/sell/{listing_id}/photos", "the photo upload step, J2 step 8"),
        ("/wanted", "the want form, JOURNEYS J4 step 2"),
    ]


@pytest.fixture
def seller_client(client_as, seller, s2_listing):
    return client_as(seller), s2_listing


def test_every_s2_page_passes_the_structural_a11y_rules(seller_client):
    """The sweep, extended to the pages S2 added — **and it asserts which.**

    Every page is fetched, every one must be HTML and 200, and every one is
    checked. A page that redirects or 404s is a **failure** here rather than a
    skip, because a skipped page in an a11y sweep is the exact thing that
    produced a green report for four pages of eleven.
    """
    client, listing = seller_client
    violations, unreached = {}, []

    for path, why in _s2_pages(listing.id):
        response = client.get(path, headers={"accept-language": "en"})
        if response.status_code != 200 or not _is_html(response):
            unreached.append((path, why, response.status_code,
                              response.headers.get("Content-Type")))
            continue
        found = check_html(response.content.decode(), expect_lang="en")
        if found:
            violations[f"{path} ({why})"] = [str(v) for v in found]

    assert unreached == [], (
        "these S2 pages were not reached, so they were not checked — and an "
        "unchecked page in an a11y sweep is reported as coverage unless this "
        f"assertion exists: {unreached}"
    )
    assert violations == {}, f"S2 structural a11y violations: {violations}"


def test_the_parameterised_pages_really_are_outside_the_other_sweep():
    """**The guard on this file.** If `_page_routes()` ever starts including
    parameterised routes, this file becomes a duplicate and should be deleted;
    if it keeps excluding them, this file is the only thing checking the two
    pages the product is about. Either way the reader needs to know which,
    so it is asserted rather than assumed.
    """
    from tests.a11y.test_pages import _page_routes

    routes = set(_page_routes())
    assert not any(r.startswith("/listing/") for r in routes), (
        "`_page_routes()` now yields the listing page, so the two sweeps "
        "overlap and this file's reason for existing has changed"
    )
    assert "/sell" in routes and "/wanted" in routes, (
        "the zero-argument S2 pages should still be in the main sweep; if "
        "they are not, the main sweep has lost reach rather than this file "
        "gaining it"
    )


# --------------------------------------------------------------------------
# the Tamil half — the charter's standing instruction, applied to S2's surface
# --------------------------------------------------------------------------


def test_no_s2_page_serves_tamil_while_the_locale_is_closed(seller_client):
    """**The charter's rule, on the pages S2 added.**

    > *Verify in English now, and in Tamil only once `i18n.ta_enabled` is on —
    > a11y on an unreviewed locale measures nothing. … The mitigation is that
    > the Tamil locale is closed, **so the test to write is that it is
    > closed**.*

    S2 added 615 lines to `locale/ta/LC_MESSAGES/django.po` and
    `locale/ta/REVIEWED.toml` is still deliberately empty — *"an entry here
    records that a named native Tamil speaker read a specific string"*, and no
    agent may write one. So the new Tamil copy is written and must not be
    reachable.

    `tests/unit/test_locale_gate.py` asserts the middleware and the flag.
    This asserts the **product surface S2 added**, which is the thing a
    student would actually meet: each S2 page requested with
    `Accept-Language: ta` comes back declaring `lang="en"`. A Tamil-tagged
    English page is the SC 3.1.1 failure the harness exists to catch, and a
    Tamil-served unreviewed page is accepted risk A9 going live.

    **This is not a verification of Tamil accessibility and must never be
    reported as one.** Tamil is unverified, in this slice and every slice
    until a named person signs the manifest.
    """
    client, listing = seller_client
    assert "ta" not in _served_locales(), (
        "`i18n.ta_enabled` is on. The charter's instruction changes at that "
        "point: the Tamil a11y sweep becomes required and this test becomes "
        "the wrong assertion. Do not delete it — invert it."
    )

    for path, why in _s2_pages(listing.id):
        for header in ("ta", "ta-IN", "ta;q=0.9, en;q=0.1"):
            response = client.get(path, headers={"accept-language": header})
            assert response.status_code == 200, (path, why, response.status_code)
            html = response.content.decode()
            assert 'lang="en"' in html, (
                f"{path} ({why}) answered `Accept-Language: {header}` with "
                "something other than an English-tagged page. Either Tamil is "
                "being served while unreviewed (THREAT-MODEL §6.1, accepted "
                "risk A9), or the page is tagged with a language it is not in "
                "(WCAG SC 3.1.1)."
            )


def test_the_banned_vocabulary_check_is_recorded_as_english_only():
    """**The gap the charter forbids reporting around, asserted as a gap.**

    > *the banned-vocabulary test covers **English only** until
    > `locale/ta/REVIEWED.toml` exists, so **a Tamil string that warrants
    > would pass a green test suite**.*

    The file now exists and is **empty by design**, which closes the gap's
    trigger condition and not the gap: zero strings are reviewed, so the
    English grep is still the only vocabulary check that runs and S2's 615
    new Tamil lines are unread by anyone. This test records that state so a
    future reader cannot take the file's existence for the sign-off it is
    explicitly not.
    """
    import pathlib

    reviewed = pathlib.Path("locale/ta/REVIEWED.toml")
    assert reviewed.exists(), "the manifest the gate reads is gone"
    body = reviewed.read_text(encoding="utf-8")
    entries = [
        line for line in body.splitlines()
        if line.strip().startswith("[") and not line.strip().startswith("[#")
    ]
    assert entries == [], (
        "`locale/ta/REVIEWED.toml` has entries. If a named native Tamil "
        "speaker signed these off, this test is now the wrong assertion and "
        f"the Tamil a11y sweep becomes required: {entries}. If an agent wrote "
        "them, that is CLAUDE.md rule 1 — fabricated evidence — and "
        "THREAT-MODEL §6.1's residual risk A10 realised."
    )
