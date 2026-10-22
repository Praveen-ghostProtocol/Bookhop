r"""Does this text address a person off the platform? One definition.

Two readers, and the second is why this is a module rather than four lines in
`update_profile`:

  * **`accounts.update_profile`** refuses a `display_name` that carries one.
    Red Team F49: the field's only rules were non-empty and ≤60 characters, so
    `"Priya R — wa.me/919840012345 · call me"` was accepted and rendered twice
    on `/listing/{id}` and once in the L2 payload, under a product claim that
    *"there is no such field"*. There was: the claim was about **key names**
    and nothing constrained **contents**.
  * **`messages.contact_pattern_flag`** (S4, API-CONTRACT §5.5) must set a
    flag on *"a phone/email/UPI pattern"*. That is the same question with a
    different verb — flag there, refuse here — and `CLAUDE.md` rule 11 has
    already cost this project three hand-made copies of one rule that
    disagreed. **Import this; do not retype it.**

**The property, not the patterns.** The question asked is *"does this text
contain a token that addresses a system"* — something a stranger can dial,
mail or open. It is deliberately **not** *"does this look like a name"*: a
character-class rule over names is the trap, because it rejects `Priya R 2`
and has to be taught every script Tamil Nadu writes in. A name may contain
digits, dashes, dots and any letter in Unicode.

**Three limbs, each with its own match rule** (rule 11's second half, so a
false positive narrows one limb instead of deleting the set):

  1. `dialable` — seven or more digits once the characters a phone number is
     written with are removed. Seven is the shortest dialable number
     anywhere; an Indian mobile is ten and E.164 caps at fifteen. `Priya R 2`
     has one digit, `Batch of 2024` has four, `98400 12345` has ten.
  2. `addressed` — an `@` with something attached to it: an email local part
     or a handle. `Priya @ MIT` has a space after the `@` and is not one.
  3. `linked` — a path separator. `wa.me/91…`, `t.me/priya`,
     `https://…` — no personal name contains `/` or `\`.

**WHAT THIS CANNOT CATCH, stated here so the suite is not read as covering
it** (`CLAUDE.md` rule 10's instrument rule):

  * a bare domain with no slash and no digits — `Priya (t.me priya)`;
  * a handle written in words — `Priya, insta priya_r`;
  * an instruction with no address at all — `Priya, ask me in class`;
  * a number spelled out, or written in a script whose digits are not Unicode
    decimal digits.

**The layer that still catches those** is the human review queue — every
listing stops at `PENDING_REVIEW` at pilot (`LISTING_REVIEW_ALL=true`) and
the moderator now sees the listing's claims — plus the S4 message flag built
on this same function. Naming that layer is rule 12's requirement: a limb
this narrow is only defensible because something else is looking.

# ponytail: three regexes over a string, no NLP, no homoglyph folding.
# Ceiling: the four shapes listed above, and a seller determined to leak a
# channel will find a fifth. Upgrade path: none in code — the upgrade is the
# moderation queue reading the name, which is a human and is already there.
"""

import re

__all__ = ["CHANNEL_KINDS", "contact_channels_in", "has_contact_channel"]

#: Characters a phone number is written with, removed before the digits are
#: counted. Not a list of *bad* characters — a list of the punctuation that
#: does **not** interrupt a number, which is why `/` is here (`wa.me/9198…`).
_NUMBER_SEPARATORS = r"\s.\-()/+ ‐-―"

_DIGIT_RUN = re.compile(rf"\d(?:[{_NUMBER_SEPARATORS}]*\d)*")

#: The shortest number anyone can dial. Below this the digits are an address,
#: a batch year or a middle initial.
MIN_DIALABLE_DIGITS = 7


def _dialable(text):
    """A run of digits long enough to be dialled."""
    return any(
        len(re.sub(r"\D", "", run.group())) >= MIN_DIALABLE_DIGITS
        for run in _DIGIT_RUN.finditer(text)
    )


def _addressed(text):
    """An `@` with a local part or a handle attached to it."""
    return re.search(r"@[^\s@]", text) is not None


def _linked(text):
    """A path separator — the thing every URL has and no name has."""
    return re.search(r"[/\\]", text) is not None


#: `kind -> predicate`. The kinds are the vocabulary the callers log and the
#: tests name, so a new limb is a row here and nothing else changes.
CHANNEL_KINDS = {
    "dialable": _dialable,
    "addressed": _addressed,
    "linked": _linked,
}


def contact_channels_in(text, kinds=None):
    """The kinds of off-platform channel in `text`, sorted. `[]` if none.

    `kinds` restricts which limbs are applied; `None` applies all of them.
    **The subset is a caller's ruling, not a caller's reimplementation**
    (rule 11): `apps/catalog` applies `("addressed", "dialable")` under
    API-CONTRACT A-26 because a real book title contains a slash
    (`Physics/Chemistry Combined`), and a limb that fires on legitimate
    content gets edited rather than obeyed (rule 13). It passes the names; it
    does not keep its own copy of the predicates.

    A name that is not a limb **raises** rather than matching nothing: a
    typo'd kind would be a guard that silently stopped guarding and was still
    reported as coverage (rule 10).
    """
    subject = str(text or "")
    selected = CHANNEL_KINDS if kinds is None else {k: CHANNEL_KINDS[k] for k in kinds}
    return sorted(kind for kind, matches in selected.items() if matches(subject))


def has_contact_channel(text, kinds=None):
    return bool(contact_channels_in(text, kinds))
