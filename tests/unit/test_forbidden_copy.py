"""The English copy deny-list — THREAT-MODEL §6.1(a), TASKS S1.

*"**English** (`en`): no template or `.po` entry contains a banned stem as a
whole word outside the exception manifest."*

**REVIEW-S1 B5: this file did not exist, and nothing in the repository read
`locale/FORBIDDEN_EXCEPTIONS.toml`.** The manifest recorded *"122 strings
scanned, 0 findings"* — a **manual** scan, in a comment. Review re-ran it by
hand and it was clean, which is exactly why it has to be mechanised now: a
control whose evidence is "someone looked" is a control that is true on the day
someone looked.

**What is scanned, and the two shape exemptions the manifest declares.** The
scan reads *translatable text*, never raw bytes:

  * a gettext **context key** (`{% translate … context "trust.campus_mail" %}`,
    `pgettext("trust.…", …)`, `msgctxt "…"`) is an identifier, not copy — no
    student ever sees it — and `COMPLIANCE.md` §2.5a cites `trust.campus_mail`
    **by name**, so `CLAUDE.md` rule 13's first resort (rename ours) does not
    apply and resort 2 does;
  * a **comment** body is not copy either, and every rationale in
    `templates/**`, in the manifest and **in this file** quotes the banned
    words in order to explain the ban. A test that fires on its own rationale
    is a test that gets edited under schedule pressure.

**Both exemptions are marked `PENDING` in the manifest and this file treats
them as pending.** Review's instruction is exact: *a reviewer cannot ratify an
exemption to a control that does not exist.* So
`test_finding_the_shape_exemptions_are_not_yet_ratified` reports their status
and will fail the day the manifest claims ratification without naming a human —
the control exists first, the ratification follows, in that order.

The word list is `apps/core/copy_rules.py`, never retyped here
(`CLAUDE.md` rule 10). The manifest is **frontend-developer's** (TASKS §1) and
is read, never written, by this test — *"neither agent can both write a
sign-off and write the test that checks it."*
"""

import pathlib
import re
import tomllib

import pytest

from apps.core.copy_rules import BANNED_LABELS, BANNED_PHRASES, BANNED_WORDS, all_inflections

REPO = pathlib.Path(__file__).resolve().parents[2]
LOCALE = REPO / "locale"
TEMPLATES = REPO / "templates"
MANIFEST = LOCALE / "FORBIDDEN_EXCEPTIONS.toml"


def manifest():
    if not MANIFEST.exists():
        pytest.skip(
            f"NOT VERIFIABLE YET (slice=S1): {MANIFEST.relative_to(REPO)} does not "
            "exist. It is frontend-developer's (TASKS.md §1) and the scan cannot "
            "know which strings are excepted without it — running the deny-list "
            "with an assumed-empty exception set would report findings this "
            "project has already ruled on."
        )
    return tomllib.loads(MANIFEST.read_text(encoding="utf-8"))


# --- what counts as translatable text ------------------------------------

#: Strip a `{% comment %}` body, a Django `{# … #}` comment, and a `//` or `/* */`
#: comment in a vendored script. Shape exemption 2.
_COMMENT_SHAPES = (
    re.compile(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}", re.S),
    re.compile(r"\{#.*?#\}", re.S),
    re.compile(r"/\*.*?\*/", re.S),
    re.compile(r"^\s*//.*$", re.M),
)

#: Strip a gettext **context key**. Shape exemption 1 — and it is written as
#: three precise shapes rather than "anything containing `trust.`", because a
#: pattern that broad would exempt a msgid that merely mentioned one.
_MSGCTXT_SHAPES = (
    re.compile(r'context\s*=?\s*"[^"]*"'),
    re.compile(r"context\s*=?\s*'[^']*'"),
    re.compile(r'pgettext(?:_lazy)?\(\s*["\'][^"\']*["\']'),
    re.compile(r'^\s*msgctxt\s+".*"$', re.M),
)


def translatable_text(source):
    """`source` with comments and context keys removed.

    Order matters: comments go first, because a comment can contain anything
    including a half-written context key.
    """
    for pattern in _COMMENT_SHAPES:
        source = pattern.sub(" ", source)
    for pattern in _MSGCTXT_SHAPES:
        source = pattern.sub(" ", source)
    return source


def scanned_files():
    """Every file whose text can reach a student, in English."""
    files = []
    for root, globs in ((TEMPLATES, ("**/*.html", "**/*.txt")), (LOCALE / "en", ("**/*.po",))):
        if not root.exists():
            continue
        for pattern in globs:
            for path in sorted(root.glob(pattern)):
                files.append((path.relative_to(REPO).as_posix(), path.read_text(encoding="utf-8")))
    return files


#: The three places a student-facing English string is actually written.
#:
#: **Not "every double-quoted string"**, which was the first draft and was
#: wrong in a way worth recording: it matched `class="price"` in
#: `templates/listing.html` and reported a **CSS class** as banned copy. A
#: class name is not shown to anybody, and a guard that flags one teaches the
#: next reader that the guard is noise — which is how a guard gets switched
#: off (`CLAUDE.md` rule 13).
_TRANSLATE_TAG = re.compile(r'{%\s*(?:translate|trans)\s+"((?:[^"\\]|\\.)*)"', re.S)
_BLOCKTRANSLATE = re.compile(
    r'{%\s*blocktranslate[^%]*%}(.*?){%\s*endblocktranslate\s*%}', re.S
)
_PO_STRING = re.compile(r'^(?:msgid|msgstr)(?:\[\d+\])?\s+"((?:[^"\\]|\\.)*)"', re.M)


def translatable_strings(source):
    """The individual student-facing strings in `source`.

    **Needed because the label rule is about a string's shape.** Asking *"is
    this four words with no full stop"* of a whole template is meaningless;
    it has to be asked of each string a student is actually shown.

    A `blocktranslate` body keeps its `{{ placeholders }}`, which is correct:
    *"Asking ₹{{ amount }}"* is the label, and the placeholder is part of its
    shape.
    """
    found = []
    for pattern in (_TRANSLATE_TAG, _BLOCKTRANSLATE, _PO_STRING):
        found.extend(match.group(1) for match in pattern.finditer(source))
    return found


def findings(text):
    """Warranting words and forbidden phrases, over the whole text.

    **The label rule is not here** — it is `label_findings`, applied per
    string, because a label rule applied to a file is a label rule applied to
    prose. See `apps.core.copy_rules.is_label_shaped`.
    """
    hits = []
    lowered = text.lower()
    for word in sorted(all_inflections()):
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            hits.append(word)
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            hits.append(phrase)
    return hits


def label_findings(source):
    """Banned labels, asked **per string** and only of label-shaped ones.

    cto's scope correction, 2026-10-22: the bare-label rule's rationale is
    about how a field is labelled, so scanning prose with it was over-breadth
    of the same kind criterion 7f had. `Price` and `Max price` are still
    findings; *"This is the price you're asking"* is not, and
    `BANNED_PHRASES` covers the sentence it appears in.
    """
    from apps.core.copy_rules import banned_label_in

    hits = []
    for candidate in translatable_strings(source):
        hits.extend(banned_label_in(candidate))
    return hits


# --- the control ----------------------------------------------------------


def test_no_shipped_english_string_contains_a_banned_word():
    """The rule itself, mechanised. A failure names the file and the word."""
    excepted = set(manifest().get("strings", {}))
    files = scanned_files()
    if not files:
        pytest.skip(
            "NOT VERIFIABLE YET (slice=S1): no templates/** or locale/en/**/*.po "
            "files exist. They are frontend-developer's (TASKS.md §1), and a "
            "deny-list over zero files is the vacuous guard CLAUDE.md rule 12 names."
        )

    offenders = []
    for name, source in files:
        cleaned = translatable_text(source)
        for word in findings(cleaned) + label_findings(cleaned):
            if word not in excepted:
                offenders.append(f"{name}: {word!r}")
    assert offenders == [], (
        "THREAT-MODEL §6.1(a): BookHop may describe a mechanism, name a fact or "
        "give an instruction — it may never warrant. These shipped English "
        "strings contain a banned word and are not in "
        "locale/FORBIDDEN_EXCEPTIONS.toml:\n" + "\n".join(sorted(set(offenders)))
        + "\n\nAdding an entry to that manifest is a Code Review escalation "
        "(TASKS §1), not a review comment."
    )


def test_the_scan_reads_a_real_corpus_and_is_not_vacuous():
    """`CLAUDE.md` rule 12. The assertion above is an absence, and an absence
    is what a scan over zero files reports. The manifest records 122 strings
    scanned by hand at S1; this asserts the mechanised scan reaches a corpus of
    the same order rather than silently reading nothing."""
    files = scanned_files()
    if not files:
        pytest.skip("NOT VERIFIABLE YET (slice=S1): frontend's trees are empty")
    total = sum(len(translatable_text(src)) for _n, src in files)
    assert len(files) >= 5, f"only {len(files)} files scanned: {[n for n, _ in files]}"
    assert total > 5000, f"only {total} characters of translatable text scanned"


@pytest.mark.parametrize(
    "text,word,why",
    [
        ("<p>This seller is verified.</p>", "verified", "the warranting adjective"),
        ("{% translate 'Your handover is safe' %}", "safe", "the word TR-8 added first"),
        ("<p>A trusted seller</p>", "trusted", "a judgement about a person"),
        ("<p>Guaranteed authentic</p>", "guaranteed", "two in one phrase"),
        ("<p>Pay the listed price</p>", "pay the listed price", "Ban 2's phrase"),
        ("<p>The price is fixed</p>", "the price is fixed",
         "cto 2026-10-22: the same claim in the active voice, caught by nothing before"),
        ("<p>We set price for you</p>", "set price", "the second of the three added phrases"),
        ("<p>That is the price final</p>", "price final", "the third"),
        ("<p>We offer full protection</p>", "protection",
         "an inflection, enumerated rather than stemmed — 'protect' would not match it"),
        ("<p>Your data is protected</p>", "protected", "the participle"),
        ("<p>Safety first</p>", "safety", "the noun form of the first banned word"),
    ],
)
def test_the_detector_catches_each_banned_shape(text, word, why):
    """The detector needs a detector. Each case is a string a reasonable
    developer would write, and each must be seen."""
    assert word in findings(translatable_text(text)), (
        f"{why}: {text!r} produced {findings(translatable_text(text))}"
    )


@pytest.mark.parametrize(
    "label,hit,why",
    [
        ("Price", True, "the bare label ADR-003 §2.3 forbids"),
        ("Max price", True, "cto 2026-10-22: still a finding after the scope correction"),
        ("Price:", True, "a colon does not make it prose"),
        ("Asking price", False, "the contract's own name for the figure"),
        ("Max asking price", False, "the filter label, qualified"),
        ("Asking ₹{{ amount }}", False, "the short form, qualified"),
        ("This is the price you are asking", False,
         "prose: five words. BANNED_PHRASES covers the sentence, the label rule does not"),
        ("You cannot change the price later.", False,
         "prose ending in a full stop - JOURNEYS J2 step 5's own copy"),
        ("To ask a different price, take this down.", False, "prose"),
    ],
)
def test_the_label_rule_applies_to_labels_and_not_to_prose(label, hit, why):
    """**cto's scope correction, 2026-10-22, as the test that defines it.**

    The bare-label rule's rationale is about how a field is *labelled*;
    scanning prose with it was over-breadth of the same kind criterion 7f
    had - a control broader than the rationale it was written from, and
    invisible because it still read protective.

    Both sides are rows, because checking only the permitted side passes
    (rule 10's corollary). `Price` and `Max price` must still fire.
    """
    from apps.core.copy_rules import banned_label_in

    assert bool(banned_label_in(label)) is hit, why


def test_a_css_class_is_not_copy():
    """The extractor's own guard, and it caught a real false positive.

    The first draft matched every double-quoted string, so `class="price"` in
    `templates/listing.html` was reported as banned copy. A class name is
    shown to nobody, and a guard that flags one teaches the next reader that
    the guard is noise - which is how a guard gets switched off.
    """
    source = '<p class="price"><span class="price__sym">x</span>{{ row.asking_price_paise }}</p>'
    assert label_findings(translatable_text(source)) == []
    assert translatable_strings(source) == []


def test_the_label_rule_still_sees_a_label_in_a_real_template_line():
    """The other direction, so the narrowed extractor did not narrow to zero."""
    source = '<p>{% translate "Price" context "listing.price.row" %}</p>'
    assert label_findings(translatable_text(source)) == ["price"]


@pytest.mark.parametrize(
    "text,why",
    [
        ('{% translate "Signed in with a college email address" context "trust.campus_mail" %}',
         "shape exemption 1: the context key is an identifier, cited by name in COMPLIANCE §2.5a"),
        ('{% comment %}We never say "verified" or "safe" here — see TR-8.{% endcomment %}',
         "shape exemption 2: a rationale quoting the ban is not copy"),
        ("{# the banned word 'trusted' is explained here #}",
         "shape exemption 2, Django's own comment syntax"),
        ('<p>{% translate "BookHop hasn\'t checked this book" %}</p>',
         "the deck's actual engineering: say what we did NOT do"),
        ('<p>{% translate "Look at the book before you hand over any money" %}</p>',
         "an instruction, which is permitted voice"),
        ('<p>{% translate "Asking price" %}</p>',
         "NOT exempt and NOT a false positive — this SHOULD fire; see the test below"),
    ][:-1],
)
def test_the_detector_stays_quiet_on_permitted_copy(text, why):
    """`CLAUDE.md` rule 13: a guard that fires on the copy three frozen
    contracts mandate gets edited, not obeyed. Every case here is a string the
    product actually ships or a rationale it actually contains."""
    assert findings(translatable_text(text)) == [], why


def test_a_context_key_exemption_does_not_exempt_the_msgid_beside_it():
    """The exemption is **the shape, never a string** — the manifest says so in
    capitals. A pattern broad enough to exempt `trust.campus_mail` must not
    exempt a msgid that happens to sit on the same line."""
    line = '{% translate "This seller is verified" context "trust.campus_mail" %}'
    assert "verified" in findings(translatable_text(line))


def test_the_manifest_is_actually_read():
    """REVIEW-S1 B5's other half: **nothing in the repository read this file.**
    An exception manifest nobody reads is a list of permissions that grant
    nothing and forbid nothing."""
    data = manifest()
    assert "strings" in data, "the manifest has no [strings] table"
    assert "shapes" in data, "the manifest declares no shape exemptions"
    assert data["meta"]["locale"] == "en"


def test_finding_the_shape_exemptions_are_not_yet_ratified():
    """**Review's instruction, as a test:** the two shape exemptions are marked
    `PENDING` and *"a reviewer cannot ratify an exemption to a control that does
    not exist."* The control exists as of this file, so ratification is now
    possible — and until a human is named, the status must keep saying so.

    This asserts the direction that can mislead: a `ratified_by` that claims
    sign-off **without naming a person**. A still-`PENDING` entry is the honest
    state and passes.
    """
    for name, shape in manifest().get("shapes", {}).items():
        status = str(shape.get("ratified_by", ""))
        assert status, f"shape exemption {name!r} records no ratification status at all"
        if "PENDING" not in status.upper():
            assert not status.strip().lower().startswith(("agent", "backend", "frontend", "qa")), (
                f"shape exemption {name!r} is ratified by {status!r}, which is an "
                "agent. TASKS §1: the reviewer named inside these manifests is a "
                "human, not an agent"
            )


def test_the_word_list_matches_the_threat_model():
    """`CLAUDE.md` rule 9 on the list itself: THREAT-MODEL §6.1(a) names eight
    words, and a list enforcing seven would be the money-token incident again."""
    assert set(BANNED_WORDS) == {
        "safe", "verified", "guaranteed", "protected",
        "assured", "trusted", "certified", "authentic",
    }
    for stem, forms in BANNED_WORDS.items():
        assert stem in forms, f"{stem!r} does not appear in its own inflection list"
        assert len(forms) >= 3, f"{stem!r} has {len(forms)} inflections, which looks unfinished"
