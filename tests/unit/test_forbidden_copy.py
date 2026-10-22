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


def findings(text):
    """Every banned token, phrase or label in `text`, whole-word."""
    hits = []
    lowered = text.lower()
    for word in sorted(all_inflections() | set(BANNED_LABELS)):
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            hits.append(word)
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            hits.append(phrase)
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
        for word in findings(translatable_text(source)):
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
        ("<p>Price</p>", "price", "the bare label ADR-003 §2.3 forbids"),
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
