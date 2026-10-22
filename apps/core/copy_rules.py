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
#: whole phrases rather than word by word.
BANNED_PHRASES = (
    "pay the listed price",
    "fixed price",
    "non-negotiable",
    "final price",
)

#: The bare label. `asking_price_paise` is the only money name anywhere
#: (ADR-003 §2.3), and a column called `price` in the UI is the label a
#: developer copies from a field that invited it.
BANNED_LABELS = ("price",)


def all_inflections():
    """Every banned token, flattened. One definition, many readers."""
    return {word for forms in BANNED_WORDS.values() for word in forms}
