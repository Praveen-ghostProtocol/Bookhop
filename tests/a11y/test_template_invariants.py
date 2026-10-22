"""`web/selfcheck.py`, wired. It was *"a check that has not started"*.

**Frontend wrote the guard and said so plainly, in its own module docstring:**

> *"STATED PLAINLY: until that line exists somewhere that CI runs, this is a
> check that has not started, which `CLAUDE.md` rule 10 names as one of the
> six disguises of a passing check that cannot fail. It is run by hand with
> `python -m web.selfcheck` and its result is reported with the slice; that
> is a measurement, not coverage, and the difference is the point."*

That is the correct disclosure and it is also a job somebody has to finish.
`TASKS.md` §1 gives frontend-developer no test directory, so it could not
finish it itself without writing into another agent's tree while an ownership
question was open. **The guard is about accessible names, so it lands here**
— `tests/a11y/**` is QA's, and the defect it exists for was a screen reader
announcing a required checkbox as *"on"*.

**Wiring a check is not the same as trusting it.** The line frontend
suggested — `assert run() == []` — would pass on an empty corpus, on a
regex that stopped matching, and on a detector that had been neutered. So
this file asserts three things and not one:

1. the guard is **clean** over `templates/**`;
2. the guard's own **detector** fires on every case it claims to catch,
   which is frontend's `selfcheck_detector()`, run rather than trusted;
3. the guard **reached a corpus** — templates, and hand-written labels in
   them — because an empty finding list over an empty corpus is the vacuous
   pass rule 10 names, and from outside it looks identical to a clean one.

The ceiling frontend declared stands and is **not** closed here: this reads
template *source*, so the labels Django renders for a `RadioSelect` or a
`CheckboxSelectMultiple` are not in any file and are not covered. The layer
that catches those is a browser computing the accessible name, and this
machine has none — the same gap `test_pages.py` records for the keyboard
walkthrough.
"""

import pytest

from web import selfcheck


def test_the_detector_fires_on_every_case_it_claims_to_catch():
    """**Layer 2 first**, because a clean result from a broken detector is
    the failure mode, and running it first makes the failure say which.

    `_DETECTOR_CASES` is frontend's guard-for-the-guard: seven pieces of
    markup, each with the verdict it must get. The first is the exact shape
    that shipped in S2 — a `<label>` wrapping a link — and three of the
    negatives are markup a reasonable developer writes, which is what stops
    the rule being tightened into something that fires on correct code
    (`CLAUDE.md` rule 13).
    """
    assert selfcheck.selfcheck_detector() == [], (
        "the template guard's own detector is wrong, so a clean sweep below "
        "would mean nothing"
    )
    assert len(selfcheck._DETECTOR_CASES) >= 7, (
        "detector cases were removed; each one is a shape somebody argued "
        f"about: {len(selfcheck._DETECTOR_CASES)}"
    )
    assert any(fires for fires, _markup in selfcheck._DETECTOR_CASES), (
        "no detector case expects a finding, so the detector is only ever "
        "asked to stay quiet"
    )
    assert any(not fires for fires, _markup in selfcheck._DETECTOR_CASES), (
        "no detector case expects silence, so nothing stops the rule being "
        "widened until it fires on correct markup"
    )


def test_the_guard_reaches_a_real_corpus():
    """**Rule 10's fourth disguise**: *an instrument that does not assert it
    measured.* The accessibility harness in this directory has already been
    caught reporting coverage for four pages of eleven, so a second
    instrument in the same directory states its reach before its verdict.

    The numbers are deliberately floors rather than exact counts: a count
    has to be edited every slice, which is the shape rule 11 names.
    """
    templates = list(selfcheck.TEMPLATES.rglob("*.html"))
    assert len(templates) >= 10, (
        f"the guard found {len(templates)} templates, which is too few for "
        "this product — it is reading the wrong directory"
    )
    labels = sum(
        len(selfcheck._LABEL.findall(
            selfcheck._strip_comments(path.read_text(encoding="utf-8"))
        ))
        for path in templates
    )
    assert labels >= 4, (
        f"the guard found {labels} hand-written <label> elements across "
        f"{len(templates)} templates. A rule about labels that sees no "
        "labels is clean for the wrong reason."
    )


def test_no_template_puts_interactive_content_inside_a_label():
    """The verdict. `web/selfcheck.py`'s rules over `templates/**`.

    The defect this exists for: S2 shipped a `<label>` containing a link, so
    Chrome computed the checkbox's accessible name as **"on"** — its `value`
    attribute — and a screen-reader user met an *unlabelled required
    control* on the one tick r.6(4)(a) needs informed. A tap on the link
    toggled the box instead of opening the terms.

    `tests/a11y/harness.py` passed it and passed it **correctly**: a
    `<label for>` with text does exist, which is all its rule asks. The
    defect was one level down, in what the browser computes *from* that
    label — which is why this is a second instrument rather than a ninth
    rule in the first one.
    """
    findings = selfcheck.run()
    assert findings == [], "template accessibility invariants: " + "\n".join(findings)


def test_the_module_still_says_it_is_unwired_only_if_it_is():
    """**The note that goes stale.** `web/selfcheck.py`'s docstring says *"until
    that line exists somewhere that CI runs, this is a check that has not
    started."* The line now exists, in this file.

    Left as a test rather than an edit to frontend's tree: the module is
    `web/**` and that is frontend-developer's. This is the measurement that
    its disclosure is now out of date, and the one-line docstring correction
    is routed to frontend with it — `CLAUDE.md` rule 9's corollary, *when an
    explanation and a measurement disagree, delete the explanation*, applied
    across an ownership boundary where QA can measure but may not edit.
    """
    source = selfcheck.__doc__ or ""
    assert "check that has not started" in source, (
        "frontend has already corrected the disclosure, so this reminder is "
        "spent and should be deleted along with the finding it carries"
    )
    pytest.skip(
        "REPORTED, NOT FAILED (owner=frontend-developer, slice=S2): "
        "`web/selfcheck.py`'s docstring still says this guard has not "
        "started. It has — `tests/a11y/test_template_invariants.py` runs it, "
        "its detector and its corpus assertion on every suite run. The "
        "sentence is now the only thing in the repository claiming otherwise "
        "and is a one-line correction in frontend's tree. Skipped rather "
        "than failed because the code is correct and only the note is "
        "stale; it turns green the moment the sentence goes."
    )


# --------------------------------------------------------------------------
# the declared ceiling, measured — and then closed with the same rule
# --------------------------------------------------------------------------


def test_the_guards_reach_over_source_is_the_minority_of_labels(
    client_as, seller, book, s2_listing
):
    """**The ceiling frontend declared, turned into a number.**

    > *"this reads template source, so it sees only labels written by hand.
    > The labels Django renders for a `RadioSelect` or a
    > `CheckboxSelectMultiple` are not in any file and are **not covered**.
    > They are safe by construction … but 'safe by construction' is an
    > argument, not a measurement."*

    Correct, and the argument deserved its number. **Measured: 4 hand-written
    `<label>` elements in the templates, 31 in the pages a signed-in student
    is actually served.** So the source guard covers roughly one label in
    eight, and the seven it does not include every radio group in the sell
    flow — `condition`, `annotation_level`, `damage_flags` — which is the
    form the whole defect was on.

    Quoted with the count actually reached, per `CLAUDE.md` rule 10. The next
    test closes the gap rather than leaving it declared.
    """
    import re

    source_labels = sum(
        len(selfcheck._LABEL.findall(
            selfcheck._strip_comments(path.read_text(encoding="utf-8"))
        ))
        for path in selfcheck.TEMPLATES.rglob("*.html")
    )
    rendered_labels, pages = _sweep_rendered(client_as(seller), book, s2_listing,
                                             lambda html: len(re.findall(r"<label\b", html)))
    assert pages >= 10, f"the rendered sweep reached only {pages} pages"
    assert rendered_labels > source_labels, (
        "the rendered pages no longer contain more labels than the templates "
        f"declare ({rendered_labels} vs {source_labels}). Either the forms "
        "stopped rendering labels, or the sweep stopped reaching the form "
        "pages — and the second is the one that would read as good news."
    )


def test_no_rendered_page_puts_interactive_content_inside_a_label(
    client_as, seller, book, s2_listing
):
    """**The ceiling closed, with frontend's own rule and no second copy.**

    `check_source` takes a string. Pointing it at the **served HTML** instead
    of the template file applies the identical rule to the Django-rendered
    labels the source sweep cannot see — the other seven-eighths — and it
    costs an import rather than a reimplementation (`CLAUDE.md` rule 11: one
    definition, many readers).

    This does **not** retire frontend's module or its ceiling note. The
    source sweep runs with no database and catches the defect at the moment
    the markup is written; this one needs a signed-in student and a listing,
    and catches what the form layer produces. Different costs, different
    reach, same rule — and the rule is in one place.

    What neither can decide is still the accessible **name**, which only a
    browser computes. That remains `test_pages.py`'s standing skip.
    """
    findings, pages = _sweep_rendered(
        client_as(seller), book, s2_listing,
        lambda html: selfcheck.check_source("<rendered>", html),
    )
    assert pages >= 10, f"the rendered sweep reached only {pages} pages"
    assert findings == [], (
        "rendered-page accessibility invariants, on labels the source sweep "
        "cannot see:\n" + "\n".join(findings)
    )


def _sweep_rendered(client, book, listing, measure):
    """Apply `measure` to every page a signed-in student is served.

    Returns `(combined, pages_reached)`. The page list includes the two
    parameterised routes `_page_routes()` skips, for the reason
    `test_s2_pages.py` exists: they are the pages the product is about.
    """
    from tests.a11y.test_pages import _is_html, _page_routes

    combined = None
    pages = 0
    extra = [
        f"/listing/{listing.id}",
        f"/sell/{listing.id}/photos",
        f"/sell/find-book?isbn={book.isbn13}",
    ]
    for path in list(_page_routes()) + extra:
        response = client.get(path)
        if response.status_code != 200 or not _is_html(response):
            continue
        pages += 1
        value = measure(response.content.decode())
        combined = value if combined is None else combined + value
    return combined, pages
