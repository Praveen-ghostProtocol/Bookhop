"""The harness checking itself.

With no UI in S0 there is nothing to audit, so the only honest thing to assert
today is that the harness works: each rule fires on HTML that breaks it and no
rule fires on HTML that does not. Without this, S1 would inherit a harness whose
silence could mean "clean page" or "broken checker", and those are not the same
result.
"""

import pytest

from .harness import NOT_COVERED_BY_THIS_HARNESS, check_html

CLEAN = """<!doctype html>
<html lang="en">
  <head><title>Sign in - BookHop</title></head>
  <body>
    <main>
      <h1>Sign in</h1>
      <form method="post" action="/auth/start">
        <label for="email">Your college email</label>
        <input type="email" id="email" name="email">
        <input type="hidden" name="csrfmiddlewaretoken" value="x">
        <button type="submit">Email me a link</button>
      </form>
      <a href="/legal/privacy">Privacy notice</a>
      <img src="/static/img/logo.svg" alt="BookHop">
    </main>
  </body>
</html>"""


def test_a_clean_page_produces_no_violations():
    assert check_html(CLEAN, expect_lang="en") == []


@pytest.mark.parametrize(
    "rule,html",
    [
        ("WCAG 3.1.1", CLEAN.replace('<html lang="en">', "<html>")),
        ("WCAG 2.4.2", CLEAN.replace("<title>Sign in - BookHop</title>", "<title></title>")),
        ("WCAG 1.3.1", CLEAN.replace("<h1>Sign in</h1>", "<p>Sign in</p>")),
        ("WCAG 1.3.1", CLEAN.replace("<h1>Sign in</h1>", "<h1>A</h1><h1>B</h1>")),
        ("WCAG 2.4.1", CLEAN.replace("<main>", "<div>").replace("</main>", "</div>")),
        ("WCAG 1.1.1", CLEAN.replace(' alt="BookHop"', "")),
        ("WCAG 1.3.1/4.1.2", CLEAN.replace('<label for="email">Your college email</label>', "")),
        ("WCAG 2.4.4", CLEAN.replace(">Privacy notice</a>", "></a>")),
        ("WCAG 4.1.2", CLEAN.replace(">Email me a link</button>", "></button>")),
        ("WCAG 2.4.3", CLEAN.replace('id="email"', 'id="email" tabindex="3"')),
    ],
)
def test_each_rule_fires_on_html_that_breaks_it(rule, html):
    found = [v[0] for v in check_html(html, expect_lang="en")]
    assert rule in found, f"rule {rule} did not fire; harness reported {found}"


def test_a_tamil_page_served_with_the_wrong_lang_is_caught():
    """THREAT-MODEL §6.1's Tamil gate is about copy review; this is the other
    half — a translated page whose `lang` was not switched reads as English to a
    screen reader, which is the failure no sighted reviewer sees."""
    assert check_html(CLEAN, expect_lang="ta") != []
    ta = CLEAN.replace('<html lang="en">', '<html lang="ta">')
    assert check_html(ta, expect_lang="ta") == []


def test_an_aria_label_satisfies_the_control_and_link_rules():
    """The harness must not force a visible <label> where ARIA is correct, or
    frontend will route around it."""
    html = CLEAN.replace(
        '<label for="email">Your college email</label>', ""
    ).replace('id="email"', 'id="email" aria-label="Your college email"')
    assert [v for v in check_html(html, expect_lang="en")
            if v[0].startswith("WCAG 1.3.1/4.1.2")] == []


def test_the_harness_states_what_it_does_not_cover():
    """The charter: "automated checks alone are not a pass". The list is part of
    the harness so that a report cannot be written without it."""
    assert len(NOT_COVERED_BY_THIS_HARNESS) >= 8
    assert any("keyboard-only" in item for item in NOT_COVERED_BY_THIS_HARNESS)
    assert any("3.3.8" in item for item in NOT_COVERED_BY_THIS_HARNESS)


def test_malformed_html_does_not_crash_the_harness():
    """A half-rendered page after a template error must give a result, not a
    traceback, or the first real failure in S1 looks like a harness bug."""
    assert check_html("<html><body><h1>unclosed", expect_lang="en") != []
    assert check_html("", expect_lang="en") != []
