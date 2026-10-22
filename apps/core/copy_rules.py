"""The English copy deny-list — THREAT-MODEL §6.1(a), as one definition.

*"A developer **authors** a warranting string"* is the threat, and a deny-list
is the control. The words come from `JOURNEYS.md` Appendix A via THREAT-MODEL
§6.1(a) and `COPY-DECK.md` §1.1, **with their inflections enumerated rather
than stemmed** — a stem match catches `protection` in "data protection", which
`COMPLIANCE.md` §8.2 *requires* the privacy notice to use.

This module is the list; `tests/unit/test_forbidden_copy.py` is the scan. They
are separate because `CLAUDE.md` rule 10 has cost this project three divergent
hand-made copies of one rule, and because the exemption manifest
(`locale/FORBIDDEN_EXCEPTIONS.toml`, **frontend-developer's**) has to be read by
the test rather than restated here.

**Why the inflections are written out.** Every one is a word a reasonable
developer would write without noticing, and the reason each is banned is the
same: BookHop may *describe a mechanism, name a fact, or give an instruction*;
it may never make a prediction or a judgement about a person, a book or an
outcome (`COPY-DECK.md` §1.2). "Verified seller" is a judgement we cannot
support and `COMPLIANCE.md` §2.5 and R-16 call it our worst asymmetry.

**What this cannot catch, stated here so the suite is not read as covering
it:** "You'll be fine" and "Trusted seller" — the second contains a banned word,
the first does not, and *neither* is caught by a word list in the general case.
THREAT-MODEL §6.1 is explicit that the sentence rule *"is not greppable in any
language"* and is a Code Review checklist item. **The grep catches words; the
reviewer catches sentences; neither substitutes for the other.**
"""

#: stem -> the inflections shipped copy might use. A per-entry rule rather than
#: a flat list (`CLAUDE.md` rule 11), so a false positive narrows one entry
#: instead of deleting a word.
BANNED_WORDS = {
    "safe": ("safe", "safely", "safer", "safest", "safety"),
    "verified": ("verify", "verifies", "verified", "verifying", "verification"),
    "guaranteed": ("guarantee", "guarantees", "guaranteed", "guaranteeing", "guarantor"),
    "protected": ("protect", "protects", "protected", "protecting", "protection"),
    "assured": ("assure", "assures", "assured", "assuring", "assurance"),
    "trusted": ("trust", "trusts", "trusted", "trusting", "trustworthy"),
    "certified": ("certify", "certifies", "certified", "certifying", "certification"),
    "authentic": ("authentic", "authentically", "authenticity", "authenticated"),
}

#: `COPY-DECK.md` §1.1 Ban 2 and `COMPLIANCE.md` §4.3.1 — price language that
#: implies BookHop sets or settles a price. Phrases, so they are matched as
#: whole phrases rather than word by word, **everywhere**: prose and labels
#: alike, because a sentence is where this claim actually gets made.
#:
#: **Extended on the cto ratification, 2026-10-22, and the reason is the
#: general one.** The original four came from one compliance section and were
#: *never a complete expression of the rule they enforce* — `set price` and
#: `the price is fixed` say the same forbidden thing in the active voice and
#: were caught by nothing. **Narrowing one layer is the right moment to
#: strengthen the other**, so the label rule's scope correction below and
#: these three additions land together.
BANNED_PHRASES = (
    "pay the listed price",
    "fixed price",
    "non-negotiable",
    "final price",
    "price final",
    "set price",
    "the price is fixed",
)

#: The bare **label**. `asking_price_paise` is the only money name anywhere
#: (ADR-003 §2.3), and a field labelled `Price` in the UI is the label a
#: developer copies from a column that invited it — it reads as *the* price,
#: which is the settled figure P14 exists to keep out of the product.
#:
#: > **SCOPE CORRECTED — cto, 2026-10-22, and it is a correction rather than
#: > an exemption.** The rule's rationale is about how a field is *labelled*;
#: > the implementation matched the word anywhere, so it scanned **prose with
#: > a label rule**. That is over-breadth of the same kind criterion 7f had —
#: > **a control broader than the rationale it was written from, invisible
#: > because it still reads protective** — and S2's sell flow is the first
#: > screen that had to violate it to work: JOURNEYS J2 step 5's own copy is
#: > *"This is the price you're asking."*
#: >
#: > So the label rule now matches **label-shaped text only** (see
#: > `is_label_shaped`), and `asking` is the one qualifier permitted beside
#: > it. **`Price` and `Max price` remain findings.** Prose is unaffected by
#: > this rule and still fully covered by `BANNED_PHRASES`, which gained
#: > three entries in the same change.
BANNED_LABELS = ("price",)

#: The qualifier that makes a price label honest: *whose* price it is. ADR-003
#: §2.1's whole position is that an asking price is not a consideration, and
#: the contract's own column name is `asking_price_paise`.
LABEL_QUALIFIERS = ("asking",)

#: A label is short and is not a sentence. Four words is the ceiling because
#: every real label in `COPY-DECK.md` is at most four ("Asking price", "Max
#: asking price"), and a fifth word means prose.
MAX_LABEL_WORDS = 4


def is_label_shaped(text):
    """Is `text` a label rather than a sentence? cto's scope correction.

    Two conditions, both necessary and both cheap to check: **at most four
    words**, and **no sentence-ending punctuation**. A string that is one of
    those but not the other is prose — *"You can't change it later."* is four
    words of a sentence, and a four-word fragment ending in a full stop is a
    sentence someone shortened.

    This is deliberately a property of the string and not a list of permitted
    strings: a list would need an entry per label and would be edited the
    first time one changed (`CLAUDE.md` rule 11).
    """
    stripped = str(text).strip()
    if not stripped:
        return False
    # `.`, `!` and `?` end a **sentence**. A colon does not — `Price:` is the
    # single most label-shaped string there is, and treating it as prose
    # would exempt the exact form the rule was written about. Measured by
    # `test_the_label_rule_applies_to_labels_and_not_to_prose`, which carries
    # `Price:` as a must-fire row.
    if stripped[-1] in ".!?":
        return False
    return len(stripped.split()) <= MAX_LABEL_WORDS


def banned_label_in(text):
    """The banned labels in `text`, applying the label rule's real scope.

    Returns `[]` for prose — that is what `BANNED_PHRASES` is for — and for a
    label qualified by `asking`. `Price` and `Max price` are returned.
    """
    import re

    if not is_label_shaped(text):
        return []
    lowered = str(text).lower()
    if any(qualifier in lowered for qualifier in LABEL_QUALIFIERS):
        return []
    return [
        label for label in BANNED_LABELS
        if re.search(rf"\b{re.escape(label)}\b", lowered)
    ]


def all_inflections():
    """Every banned token, flattened. One definition, many readers."""
    return {word for forms in BANNED_WORDS.values() for word in forms}
