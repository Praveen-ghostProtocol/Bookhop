"""Invariants over `templates/**` that a parser can decide, run as a guard.

WHY THIS FILE EXISTS, AND WHY IT IS HERE RATHER THAN UNDER `tests/`.

S2 shipped a `<label>` containing a link. Chrome then computed the checkbox's
accessible name as **"on"** — its `value` attribute — so a screen-reader user
met an *unlabelled required control* on the one tick `r.6(4)(a)` needs
informed, and a tap on the link toggled the box instead of opening the terms.

`tests/a11y/harness.py` passed it, and passed it **correctly**: a
`<label for>` with text does exist, which is all its rule asks. The defect was
one level down, in what the browser computes *from* that label. The fix was
one line of markup and **nothing asserted it**, so the correction was
unguarded — which is the same shape as the defect, one level up again.

`TASKS.md` §1 gives `tests/unit/**` and `tests/api/**` to backend-developer and
`tests/e2e/**`, `tests/a11y/**` and `tests/contract/**` to test-qa.
**frontend-developer owns no test directory.** Writing into one of those trees
while an ownership question about a shared file is already with cto would be
the wrong way to close this. So the rules live in the tree that owns the
templates, as an importable module with a `__main__`, and the wiring is one
line for whoever owns a suite:

    from web.selfcheck import run
    def test_template_invariants():
        assert run() == []

**STATED PLAINLY: until that line exists somewhere that CI runs, this is a
check that has not started**, which `CLAUDE.md` rule 10 names as one of the
six disguises of a passing check that cannot fail. It is run by hand with
`python -m web.selfcheck` and its result is reported with the slice; that is a
measurement, not coverage, and the difference is the point.

WHAT IT CAN AND CANNOT DECIDE. These are *preconditions* of the accessible
name, not the name itself — the name is computed by a browser and only a
browser can report it. A label that contains no interactive content and has
text **will** name its control; that is what the accname algorithm does with
it. So this catches the defect that happened, and the browser remains the
instrument for the thing it computes.
"""

from __future__ import annotations

import pathlib
import re
import sys

TEMPLATES = pathlib.Path(__file__).resolve().parent.parent / "templates"

#: Elements that must never appear inside a `<label>`. HTML forbids
#: interactive content there, and the accessible-name computation is where the
#: breach shows up: Chrome fell back to the input's `value`.
INTERACTIVE = ("a", "button", "input", "select", "textarea", "details", "summary")

_COMMENTS = (
    re.compile(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}", re.S),
    re.compile(r"\{#.*?#\}", re.S),
)
_LABEL = re.compile(r"<label\b(?P<attrs>[^>]*)>(?P<body>.*?)</label>", re.S)
_TAG = re.compile(r"<(?P<tag>[a-zA-Z][\w-]*)\b")
_DJANGO = re.compile(r"\{[%{].*?[%}]\}", re.S)
_HTML_TAG = re.compile(r"<[^>]*>")


def _strip_comments(source: str) -> str:
    for pattern in _COMMENTS:
        source = pattern.sub(" ", source)
    return source


def _label_text(body: str) -> str:
    """The text a label contributes to a name: markup and template tags out.

    A `{% translate %}` tag is *replaced by a placeholder rather than removed*,
    because a label whose entire content is one translate tag has text at
    render time — treating it as empty would make this guard fire on the
    correct markup, which `CLAUDE.md` rule 13 says is how a guard gets edited
    instead of obeyed.
    """
    body = _DJANGO.sub("x", body)
    return _HTML_TAG.sub(" ", body).strip()


def check_source(name: str, source: str) -> list[str]:
    """The rules, over one document. Split out so the detector has a detector."""
    findings: list[str] = []
    source = _strip_comments(source)
    for match in _LABEL.finditer(source):
        body, attrs = match.group("body"), match.group("attrs")

        nested = {
            tag.group("tag").lower()
            for tag in _TAG.finditer(body)
            if tag.group("tag").lower() in INTERACTIVE
        }
        # A label wrapping its own control is the one legal exception, and it
        # is not the shape that broke: the name still comes from the text
        # beside it. Only a *second* kind of control, or a link, is a finding.
        wrapped_own_control = nested <= {"input", "select", "textarea"}
        if nested and not wrapped_own_control:
            findings.append(
                f"{name}: a <label> contains interactive content "
                f"{sorted(nested)}. The accessible name of its control is "
                "computed from this label, and a browser may fall back to the "
                'control\'s `value` instead — which is how a required checkbox '
                'came to be named "on". Move it outside.'
            )

        if 'for="' in attrs and not _label_text(body):
            findings.append(
                f"{name}: a <label for> has no text, so the control it names "
                "has no accessible name from it."
            )
    return findings


#: `CLAUDE.md` rule 10: *"write a guard for a guard."* Each case is markup a
#: reasonable developer would write, and the first is the exact shape that
#: shipped in S2.
_DETECTOR_CASES = (
    (True, '<label for="id_t">I agree <a href="/legal/x">read it</a></label>'),
    (True, '<label for="id_t"><button type="button">x</button> tick</label>'),
    (True, '<label for="id_t"><span></span></label>'),
    (False, '<label for="id_t">I have read the seller terms '
            '<span class="field__req">(required)</span></label>'),
    (False, '<label for="id_t">{% translate "Edition" context "sell.edition.label" %}</label>'),
    (False, '<label>Name <input type="text" name="n"></label>'),
    (False, '{% comment %}<label for="id_t"><a href="/x">why this is wrong</a>'
            '</label>{% endcomment %}'),
)


def selfcheck_detector() -> list[str]:
    """Every case in `_DETECTOR_CASES` behaves. Returns the failures."""
    bad = []
    for should_fire, markup in _DETECTOR_CASES:
        fired = bool(check_source("<case>", markup))
        if fired != should_fire:
            bad.append(
                f"detector {'missed' if should_fire else 'fired on'}: {markup}"
            )
    return bad


def run() -> list[str]:
    """Every finding over `templates/**`, as `file: detail`. Empty means clean.

    **CEILING, DECLARED HERE RATHER THAN DISCOVERED** (`CLAUDE.md` rule 11):
    this reads template *source*, so it sees only labels written by hand. The
    labels Django renders for a `RadioSelect` or a `CheckboxSelectMultiple`
    are not in any file and are **not covered**. They are safe by construction
    — Django emits the option text and nothing else — but "safe by
    construction" is an argument, not a measurement, and the measurement would
    need rendered output. The layer that still catches it is the browser:
    `read_page` reports the computed name of every control, which is how the
    original defect was found at all.
    """
    findings = selfcheck_detector()
    for path in sorted(TEMPLATES.rglob("*.html")):
        findings += check_source(
            path.relative_to(TEMPLATES.parent).as_posix(),
            path.read_text(encoding="utf-8"),
        )
    return findings


def main() -> int:
    findings = run()
    for finding in findings:
        print(finding)
    paths = list(TEMPLATES.rglob("*.html"))
    labels = sum(
        len(_LABEL.findall(_strip_comments(p.read_text(encoding="utf-8")))) for p in paths
    )
    # The corpus is printed because an empty finding list over an empty corpus
    # is the vacuous pass rule 10 names, and a count is the cheapest way to
    # tell the two apart from outside.
    print(
        f"{len(findings)} findings · {labels} hand-written <label> elements in "
        f"{len(paths)} templates · {len(_DETECTOR_CASES)} detector cases"
    )
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
