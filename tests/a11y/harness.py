"""The accessibility harness — test-qa, TASKS §3 ("test-qa S0: a11y harness").

Why this is hand-written rather than axe-core: this machine has Python 3.11.9,
no Node, and no Playwright, and `requirements-dev.txt` is backend-developer's
file (TASKS §1), so QA cannot add a dependency to get a browser. What it can do
is make the harness real, dependency-free and ready, so that S1's first page
lands into a working check instead of waiting for one.

**What this harness is:** nine objective structural rules from WCAG 2.2 A/AA,
each of which can be decided from the served HTML alone, run over every L3 route
in both locales.

**What this harness is NOT, and must never be reported as:** a WCAG 2.2 AA pass.
The charter is explicit — "accessibility is verified, never claimed; automated
checks alone are not a pass". Contrast ratios (1.4.3), focus visibility (2.4.7),
focus-not-obscured (2.4.11, new in 2.2), target size (2.5.8, new in 2.2),
dragging alternatives (2.5.7), reflow at 320 CSS px (1.4.10), accessible
authentication (3.3.8, new in 2.2 and directly relevant to the magic-link flow)
and the keyboard-only walkthrough all need a browser or a human. Each is listed
in QA-S0.md as not verified.
"""

from html.parser import HTMLParser

VOID = {"img", "input", "br", "hr", "meta", "link", "area", "base", "col",
        "embed", "source", "track", "wbr"}

#: Input types that need no label of their own.
UNLABELLED_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image"}


class Violation(tuple):
    """(rule, detail). A tuple so pytest prints it readably."""

    def __new__(cls, rule, detail):
        return super().__new__(cls, (rule, detail))

    def __str__(self):
        return f"{self[0]}: {self[1]}"


class _Page(HTMLParser):
    """Collect only what the nine rules need. Not a DOM."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.html_attrs = {}
        self.title = ""
        self._in_title = False
        self.h1_count = 0
        self.landmarks = 0
        self.images = []        # [attrs]
        self.controls = []      # [(tag, attrs)]
        self.labels = []        # [attrs]
        self.tabindexes = []    # [str]
        self._open = []         # stack of (tag, attrs, text_parts)
        self.interactive = []   # [(tag, attrs, text)] for a and button

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html_attrs = a
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "img":
            self.images.append(a)
        elif tag in ("input", "select", "textarea"):
            self.controls.append((tag, a))
        elif tag == "label":
            self.labels.append(a)
        elif tag == "main":
            self.landmarks += 1
        if a.get("role") == "main":
            self.landmarks += 1
        if "tabindex" in a:
            self.tabindexes.append(a["tabindex"])
        if tag in ("a", "button") and tag not in VOID:
            self._open.append((tag, a, []))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in ("a", "button"):
            for i in range(len(self._open) - 1, -1, -1):
                if self._open[i][0] == tag:
                    t, a, parts = self._open.pop(i)
                    self.interactive.append((t, a, "".join(parts).strip()))
                    break

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        for _tag, _a, parts in self._open:
            parts.append(data)


def _named(attrs):
    """Does this element carry its own accessible name?"""
    return bool((attrs.get("aria-label") or "").strip()) or bool(
        (attrs.get("aria-labelledby") or "").strip()
    )


def check_html(html, *, expect_lang=None):
    """Return a list of Violation for one page's served HTML.

    `expect_lang` asserts the document language is the locale the page was
    requested in, which is the check that catches a Tamil page served with
    `lang="en"` — a 3.1.1 failure a screen reader turns into gibberish, and one
    that is invisible to a sighted reviewer.
    """
    p = _Page()
    p.feed(html)
    v = []

    # 3.1.1 Language of Page (A)
    lang = (p.html_attrs.get("lang") or "").strip()
    if not lang:
        v.append(Violation("WCAG 3.1.1", "<html> has no lang attribute"))
    elif expect_lang and lang.split("-")[0].lower() != expect_lang.lower():
        v.append(Violation("WCAG 3.1.1",
                           f"<html lang={lang!r}> but the page was served as {expect_lang!r}"))

    # 2.4.2 Page Titled (A)
    if not p.title.strip():
        v.append(Violation("WCAG 2.4.2", "<title> is missing or empty"))

    # 1.3.1 Info and Relationships (A) — one top-level heading
    if p.h1_count == 0:
        v.append(Violation("WCAG 1.3.1", "no <h1> on the page"))
    elif p.h1_count > 1:
        v.append(Violation("WCAG 1.3.1", f"{p.h1_count} <h1> elements; expected one"))

    # 2.4.1 Bypass Blocks (A) — a main landmark is the cheapest way to satisfy it
    if p.landmarks == 0:
        v.append(Violation("WCAG 2.4.1", 'no <main> element or role="main"'))

    # 1.1.1 Non-text Content (A)
    for img in p.images:
        if "alt" not in img:
            v.append(Violation("WCAG 1.1.1",
                               f"<img src={img.get('src')!r}> has no alt attribute"))

    # 1.3.1 / 4.1.2 — every control has a programmatic label
    label_targets = {(lab.get("for") or "").strip() for lab in p.labels}
    for tag, attrs in p.controls:
        if tag == "input" and (attrs.get("type") or "text").lower() in UNLABELLED_INPUT_TYPES:
            continue
        cid = (attrs.get("id") or "").strip()
        if cid and cid in label_targets:
            continue
        if _named(attrs):
            continue
        v.append(Violation(
            "WCAG 1.3.1/4.1.2",
            f"<{tag} name={attrs.get('name')!r} id={cid!r}> has no <label for>, "
            "aria-label or aria-labelledby",
        ))

    # 2.4.4 Link Purpose (A) / 4.1.2 Name, Role, Value (A)
    for tag, attrs, text in p.interactive:
        if text or _named(attrs):
            continue
        if attrs.get("hidden") is not None or attrs.get("aria-hidden") == "true":
            continue
        rule = "WCAG 2.4.4" if tag == "a" else "WCAG 4.1.2"
        v.append(Violation(rule, f"<{tag}> has no accessible text"))

    # 2.4.3 Focus Order (A) — a positive tabindex reorders focus by hand
    for value in p.tabindexes:
        try:
            if int(value) > 0:
                v.append(Violation("WCAG 2.4.3", f"tabindex={value!r} is positive"))
        except ValueError:
            v.append(Violation("WCAG 2.4.3", f"tabindex={value!r} is not an integer"))

    return v


#: Checks this harness deliberately does not make, carried into QA-S0.md so the
#: gap is never implied away. Needs a browser, a human, or both.
NOT_COVERED_BY_THIS_HARNESS = (
    "1.4.3 contrast (needs computed style)",
    "1.4.10 reflow at 320 CSS px (needs a viewport)",
    "1.4.11 non-text contrast (needs computed style)",
    "2.4.7 focus visible (needs a browser)",
    "2.4.11 focus not obscured (WCAG 2.2, needs a browser)",
    "2.5.7 dragging movements (WCAG 2.2, needs interaction)",
    "2.5.8 target size 24x24 (WCAG 2.2, needs layout)",
    "3.3.8 accessible authentication (WCAG 2.2, the magic-link flow, needs a human)",
    "keyboard-only walkthrough of every flow, in EN and TA (needs a human)",
)
