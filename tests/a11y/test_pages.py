"""Run the harness over every page the application serves, in every locale it serves.

S1 landed 18 routes, and three of QA's assumptions needed re-pointing. All three
re-pointings are taken, and two of them change what the test asserts rather than
only which routes it visits — so the reasoning is recorded here, not just the
result.

**1. `NOT_PAGES` was a list; it is now an invariant.** `/sw.js`, `/robots.txt`
and `/manifest.webmanifest` were being parsed as HTML and failing four rules
each, which is meaningless — a service worker cannot have an `<h1>`. The list
said it covered "the two operational endpoints"; these three come from the same
contract table and did not exist when the harness was written, and the next
contract table will add more. `CLAUDE.md` rules 11 and 15: **the harness now
skips on the response not being `text/html`**, which asks the property instead
of enumerating the cases and will never need lengthening again. Frontend's read,
adopted.

**2. The `[ta]` parameter asked for the violation it checks for.** This is the
one QA got wrong, and frontend's sharper half is right. SC 3.1.1 is about the
*default human language of the page*. With `feature_flags['i18n.ta_enabled']`
false, no reviewed Tamil is served, so the default human language of these pages
genuinely **is** English — and `<html lang="ta">` over English text is the real
3.1.1 failure, the one that hurts: a screen reader switches to a Tamil voice and
reads English as noise. QA's test demanded exactly that. **Passing it would have
made the product worse.**

QA also agrees with the half frontend did not have to argue: serving English for
a Tamil `Accept-Language` beats refusing. `Accept-Language` is a preference, not
a demand (RFC 9110), a large part of the target population has an Android set to
Tamil, and a `406` would lock them out of signing in, reading the privacy notice
and **reaching the grievance officer** — which is an IT Rules r.3(2)(a) route and
a path `THREAT-MODEL.md` §5.7 says may never require an account. A refusal for a
locale we were never going to serve is the worse failure by a wide margin.

**So the parameter is derived from the locales actually served, and the gated
locale skips naming the flag and the slice.** But QA does not simply delete the
assertion: `test_an_unserved_locale_is_served_in_a_language_the_page_is_actually_in`
below **runs today** and asserts the fallback is correct and safe, because that
is the behaviour a Tamil-Android student actually meets, and the behaviour that
would hurt them if it broke. Removing a wrong assertion and leaving nothing in
its place is how `THREAT-MODEL.md` §6.1(c)'s claim would go unchecked
(`CLAUDE.md` rule 9).

**3. Signed-in pages were never reached.** Seven of S1's pages redirect to
`/auth/start` without a session, so the harness was silently checking four pages
out of eleven — `status_code != 200` meant "skip", which is rule 12's shape
again. There is a `users` table now, so the harness signs in.
"""

import pytest
from django.conf import settings
from django.urls import get_resolver

from .harness import check_html

#: Every locale the product has strings for. The parameter is this, not the
#: served set, so that a locale being gated produces a **skip with a reason**
#: rather than disappearing from the report entirely — a disappearing test and a
#: passing test are indistinguishable in a summary line.
ALL_LOCALES = [code for code, _name in settings.LANGUAGES]


def _served_locales():
    """The locales a student may actually be served, read from the flag.

    Derived rather than hard-coded, so the day `i18n.ta_enabled` flips this
    activates for real with no edit — which was frontend's proposal and is the
    whole point of deriving it.
    """
    from web import context

    return context.offered_locales()


def _page_routes():
    """Every zero-argument route in the live URLconf, as request paths."""
    found = []

    def walk(patterns, prefix=""):
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                walk(pattern.url_patterns, prefix + str(pattern.pattern))
                continue
            route = prefix + str(pattern.pattern)
            if any(ch in route for ch in "<(^$*"):
                continue  # parameterised, or the catch-all 404 regex
            found.append("/" + route.lstrip("/"))

    walk(get_resolver().url_patterns)
    return sorted(set(found))


def _is_html(response):
    """The invariant that replaced `NOT_PAGES`.

    `Content-Type` is the response's own statement about what it is. A JSON
    manifest, a JavaScript service worker and a plain-text robots file all say
    so, and none of them can satisfy a rule about `<h1>`.
    """
    return response.headers.get("Content-Type", "").split(";")[0] == "text/html"


def _sweep(client, locale, routes):
    """Fetch each route and check the HTML ones. Returns (violations, counts)."""
    violations = {}
    checked, skipped_non_html, skipped_status = [], [], []
    for path in routes:
        response = client.get(path, headers={"accept-language": locale})
        if response.status_code != 200:
            skipped_status.append((path, response.status_code))
            continue
        if not _is_html(response):
            skipped_non_html.append(path)
            continue
        checked.append(path)
        found = check_html(response.content.decode(), expect_lang=locale)
        if found:
            violations[path] = [str(v) for v in found]
    return violations, checked, skipped_non_html, skipped_status


@pytest.fixture
def student(db):
    """A signed-in, fully verified student, so the harness reaches the pages
    behind `_signed_in_only`."""
    from apps.accounts.models import User
    from apps.core.models import Campus, City

    city = City.objects.create(name="Chennai", state="Tamil Nadu")
    campus = Campus.objects.create(city=city, name="A11y Campus", slug="a11y")
    return User.objects.create(
        email="a11y@example.test", display_name="A Student",
        campus=campus, city=city, status="ACTIVE",
        adult_verified=True, campus_verified=True,
    )


@pytest.fixture
def signed_in(client, student):
    from apps.accounts.sessions import SESSION_USER_KEY

    session = client.session
    session[SESSION_USER_KEY] = student.id
    session.save()
    return client


# --------------------------------------------------------------------------
# the sweep, per locale
# --------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("locale", ALL_LOCALES)
def test_every_page_passes_the_structural_a11y_rules(client, locale):
    """Every HTML page the application serves anonymously, in every locale it
    serves, against the nine structural rules."""
    served = _served_locales()
    if locale not in served:
        pytest.skip(
            f"NOT SERVED YET (locale={locale}, flag=i18n.ta_enabled, slice=S1): "
            "`THREAT-MODEL.md` §6.1(c) keeps Tamil out of the language switcher "
            "**and out of `Accept-Language` negotiation** until a named native "
            "speaker signs off `locale/ta/BLOCKING_CLASSES.toml`. Asserting "
            f"`<html lang={locale!r}>` while the strings served are English "
            "would demand the SC 3.1.1 failure this harness exists to catch — a "
            "Tamil-tagged English page is what a screen reader turns into "
            "noise. The fallback that a student in this locale actually meets "
            "IS asserted, by "
            "`test_an_unserved_locale_is_served_in_a_language_the_page_is_actually_in`. "
            f"Served locales today: {served}. This activates with no edit when "
            "the flag flips."
        )

    routes = _page_routes()
    if not routes:
        pytest.skip("NOT VERIFIABLE (slice=S0): the application serves no routes.")

    violations, checked, non_html, by_status = _sweep(client, locale, routes)
    assert checked, (
        "no route returned HTML, so this test asserted nothing. "
        f"non-HTML: {non_html}; non-200: {by_status}"
    )
    assert violations == {}, f"[{locale}] structural a11y violations: {violations}"


@pytest.mark.django_db
@pytest.mark.parametrize("locale", ALL_LOCALES)
def test_every_signed_in_page_passes_the_structural_a11y_rules(signed_in, locale):
    """The seven pages behind a session, which the harness never reached.

    Without a session they redirect to `/auth/start`, and `status_code != 200`
    meant "skip" — so the harness was checking four pages out of eleven and
    reporting green. `CLAUDE.md` rule 12's shape, in QA's own harness.
    """
    served = _served_locales()
    if locale not in served:
        pytest.skip(
            f"NOT SERVED YET (locale={locale}, flag=i18n.ta_enabled, slice=S1): "
            "see the anonymous sweep for the full reason."
        )

    routes = _page_routes()
    violations, checked, _non_html, _by_status = _sweep(signed_in, locale, routes)

    # The property, not a count: every route that redirects anonymously and
    # answers 200 with a session must be in this sweep. A count would have to be
    # edited every slice, which is the shape rule 11 names.
    from django.test import Client

    anonymous = Client()
    gated = {
        path for path in routes
        if anonymous.get(path, headers={"accept-language": locale}).status_code == 302
    }
    reached = gated & set(checked)
    assert reached, (
        f"the session is not being accepted: {len(gated)} routes redirect "
        f"anonymously and none of them answered 200 with a session. "
        f"checked={checked}"
    )
    assert "/account/privacy" in checked, (
        "the privacy and consent-withdrawal page is the one S1 page a DPDP "
        "complaint is most likely to be about, and it is behind a session"
    )
    assert violations == {}, f"[{locale}] signed-in a11y violations: {violations}"


# --------------------------------------------------------------------------
# the assertion that replaces the `[ta]` parameter
# --------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "header,why",
    [
        ("ta", "the gated locale, which a Tamil-set Android sends"),
        ("ta-IN", "the regional form Android actually sends"),
        ("ta;q=0.9, en;q=0.1", "quality-weighted, preferring the gated locale"),
        ("zz", "a locale the product has no strings for at all"),
        ("", "no preference at all"),
    ],
)
def test_an_unserved_locale_is_served_in_a_language_the_page_is_actually_in(
    client, header, why
):
    """**The assertion that replaces QA's wrong `[ta]` parameter**, and it runs
    today rather than waiting for the flag.

    Four properties, and the first is the one that matters most to a student:

    1. **The page is served, not refused.** A `406` for a Tamil-set Android
       would lock that student out of sign-in, the privacy notice and the
       grievance route. `Accept-Language` is a preference, not a demand.
    2. **`lang` names the language the page is actually in.** This is SC 3.1.1
       read correctly: with no reviewed Tamil the default human language is
       English, so `lang="en"` is not a compromise, it is the accurate answer.
    3. **`Content-Language` agrees with `lang`.** Two statements of one fact
       must not disagree, or a client that trusts the header and a screen reader
       that trusts the attribute will do different things.
    4. **The page still passes every structural rule** in the language it was
       actually served in.

    Together these check `THREAT-MODEL.md` §6.1(c)'s claim that Tamil is absent
    from `Accept-Language` negotiation — which is a claim about behaviour and so
    needs a check, not a sentence (`CLAUDE.md` rule 9).
    """
    served = _served_locales()
    for path in ("/", "/auth/start", "/help", "/legal/privacy"):
        response = client.get(path, headers={"accept-language": header})
        assert response.status_code == 200, (
            f"{path} returned {response.status_code} for Accept-Language "
            f"{header!r} ({why}). A refusal locks out every device set to a "
            "locale we do not serve, for a locale we were never going to serve."
        )
        if not _is_html(response):
            continue

        body = response.content.decode()
        content_language = response.headers.get("Content-Language")
        assert content_language in served, (
            f"{path} declared Content-Language {content_language!r}, which is "
            f"not a served locale {served}"
        )
        violations = check_html(body, expect_lang=content_language)
        assert violations == [], (
            f"{path} served as {content_language!r} fails its own rules: "
            f"{[str(v) for v in violations]}"
        )
        assert f'lang="{content_language}"' in body, (
            f"{path}: Content-Language is {content_language!r} but the document "
            "does not carry the matching lang attribute. A header and an "
            "attribute stating one fact must not disagree."
        )


@pytest.mark.django_db
def test_no_page_claims_a_locale_it_does_not_serve(client):
    """The inverse, stated as the invariant rather than per header: **no response
    may declare a locale that is not in the served set.**

    This is what would catch the regression the `[ta]` parameter was asking for
    — a page tagged `ta` while the flag is false — from whatever direction it
    arrived, including from a template hard-coding `lang`.
    """
    served = set(_served_locales())
    offenders = {}
    for path in _page_routes():
        for header in ("ta", "ta-IN", "en", "zz", ""):
            response = client.get(path, headers={"accept-language": header})
            if response.status_code != 200 or not _is_html(response):
                continue
            declared = response.headers.get("Content-Language")
            if declared not in served:
                offenders[(path, header)] = declared
    assert offenders == {}, (
        f"responses declared a locale outside the served set {sorted(served)}: "
        f"{offenders}"
    )


# --------------------------------------------------------------------------
# the harness's own guards
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_the_content_type_invariant_skips_only_non_html_routes(client):
    """The rule-12 guard on the invariant that replaced `NOT_PAGES`.

    A content-type skip is silent by construction, so a page route that started
    returning JSON would vanish from the sweep and the sweep would still be
    green. This asserts the split is what it should be.

    Note what the set contains: the invariant **subsumed the old `NOT_PAGES`
    list entirely**, including the two operational endpoints it was originally
    written for. `/healthz` is `text/plain` and `/readyz` is JSON, so both are
    skipped for the same reason as the service worker — by what they are, not by
    being named. That is the difference rules 11 and 15 are about, and it is why
    the list is gone rather than shortened.
    """
    _violations, checked, non_html, _by_status = _sweep(client, "en", _page_routes())
    assert set(non_html) == {
        "/healthz", "/readyz",                              # API-CONTRACT §5.8
        "/sw.js", "/robots.txt", "/manifest.webmanifest",   # the PWA shell
    }, (
        f"the non-HTML set changed: {non_html}. If a page route is now serving "
        "a non-HTML content type it has silently left the a11y sweep; if a new "
        "asset route has landed, it belongs here deliberately."
    )
    assert len(checked) >= 4, f"only {checked} HTML routes answered 200 anonymously"


@pytest.mark.django_db
def test_the_sweep_reports_what_it_did_not_check(client):
    """What a green sweep does **not** cover, as a measurement rather than a
    caveat: the routes that answer something other than 200 anonymously are not
    checked by the anonymous sweep, and the signed-in sweep is what covers them.

    Printed as an assertion so the two numbers have to add up: every page route
    is either checked anonymously, checked signed-in, or non-HTML.
    """
    routes = _page_routes()
    _v, anon_checked, non_html, by_status = _sweep(client, "en", routes)
    unchecked = {path for path, _code in by_status}
    assert set(routes) == set(anon_checked) | set(non_html) | unchecked
    assert unchecked, (
        "no route redirects anonymously, which would mean S1 has no "
        "session-gated page — then `test_every_signed_in_page_*` is the "
        "vacuous one and needs re-reading"
    )


def test_keyboard_only_walkthrough_of_every_flow():
    pytest.skip(
        "MANUAL, NOT AUTOMATED (slice=S1): the charter requires 'automated WCAG "
        "2.2 AA plus a keyboard-only walkthrough of every flow, in both English "
        "and Tamil', and states that automated checks alone are not a pass. S1 "
        "is the first slice with flows to walk. No browser automation exists on "
        "this machine; recorded in QA-S0.md as not verified, with the list of "
        "criteria no HTML-level harness can decide."
    )


def test_p75_lcp_on_a_throttled_mid_range_android_profile():
    pytest.skip(
        "NOT VERIFIABLE (slice=S3): TASKS §2 S3 assigns p75 LCP and p95 search "
        "latency to QA. Both need a browser and a throttling profile; this "
        "machine has no browser automation."
    )
