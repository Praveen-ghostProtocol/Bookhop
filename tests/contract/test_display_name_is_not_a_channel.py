r"""F49 regression — `display_name` cannot carry a way to reach the seller.

Red Team measured `update_profile(seller, display_name="Priya R —
wa.me/919840012345 · call me")` accepted without comment, then rendered twice
on `/listing/{id}` and shipped in the L2 payload, under two product claims
that *"there is no such field"*.

**Written at the boundary the contract claims** (`CLAUDE.md` rule 9).
API-CONTRACT §5.2 says *"Listing responses never contain … a phone number"*,
so there is an assertion on a listing response and not only on the setter.
The setter is where it is prevented; the response is where it is promised.

**Both sides are rows** (rule 10's corollary). The rule splits the set of
strings a student might type, and the permitted side is the expensive one to
get wrong: a guard that rejects `Priya R 2`, a Tamil name, or `Jean-Luc
O'Brien` is worse than the defect it closes, because it blocks the primary
journey for real people and gets relaxed under pressure (rule 13). Every one
of those is a row here.

**What this does not cover** is in `apps/core/contact.py`'s docstring and is
asserted below by name, so the suite cannot be read as claiming more than it
measures.
"""

import pytest

from apps.core.contact import CHANNEL_KINDS, contact_channels_in, has_contact_channel
from apps.core.errors import ValidationFailed

pytestmark = pytest.mark.django_db


#: Paths in a listing response whose value is a **machine or contract
#: identifier**, not text a person typed, and which the digit limb therefore
#: matches for the wrong reason: an ISBN-13 is thirteen digits by definition
#: and a pseudonym is a UUID whose hex sometimes contains a run of seven.
#:
#: **This is `CLAUDE.md` rule 13's second resort — exempt the shape — and it
#: is recorded as one.** Neither name is ours to rename: `isbn13` is frozen
#: in API-CONTRACT §5.2 and `pseudonym` in `COMPLIANCE.md` §2.4(i). The first
#: resort does not apply and the third is not needed. **The exemption is by
#: PATH, not by value**, so a contact channel typed into one of these fields
#: would still have to be caught somewhere — and
#: `test_the_exemption_does_not_swallow_a_human_string` is the proof that it
#: is the path and not the digits that is exempted.
MACHINE_IDENTIFIERS = frozenset({"$.book.isbn13", "$.seller.pseudonym"})

#: The permitted side. Each is a name a real student on a Chennai campus
#: might give, and each would be rejected by one of the obvious wrong rules
#: (no digits, ASCII letters only, no punctuation).
NAMES_THAT_MUST_BE_ACCEPTED = [
    ("Priya R", "the ordinary case"),
    ("Priya R 2", "a digit, because two Priya Rs share a batch"),
    ("Batch of 2024", "four digits, which is a year and not a number"),
    ("ப்ரியா ரமேஷ்", "Tamil — a letter rule over ASCII would reject this"),
    ("Jean-Luc O'Brien", "a hyphen and an apostrophe are name punctuation"),
    ("Dr. A. R. Kumar", "initials and full stops"),
    ("Priya @ MIT", "an @ with a space after it addresses nobody"),
    ("Room 12, Block 4", "digits that are a place, not a number to dial"),
    ("K. S. Venkat (KS)", "parentheses around a short form"),
]

#: The forbidden side. Every one is a channel, and the first is verbatim what
#: Red Team measured.
CHANNELS_THAT_MUST_BE_REFUSED = [
    ("Priya R — wa.me/919840012345 · call me", "linked", "the measured string"),
    ("Priya 9840012345", "dialable", "a bare Indian mobile"),
    ("Priya +91 98400 12345", "dialable", "spaced, the way a person writes it"),
    ("Priya 98400-12345", "dialable", "hyphenated"),
    ("priya.r@gmail.com", "addressed", "an email address"),
    ("Priya @priya_books", "addressed", "a handle"),
    ("Priya t.me/priyabooks", "linked", "a link with no digits at all"),
    ("Priya https://wa.me/priya", "linked", "a full URL"),
]


# --- the property itself ---------------------------------------------------


@pytest.mark.parametrize(
    ("name", "why"), [(n, w) for n, w in NAMES_THAT_MUST_BE_ACCEPTED]
)
def test_the_property_leaves_a_real_name_alone(name, why):
    assert contact_channels_in(name) == [], why


@pytest.mark.parametrize(
    ("text", "kind", "why"), CHANNELS_THAT_MUST_BE_REFUSED
)
def test_the_property_names_the_channel_it_found(text, kind, why):
    """The *kind* is asserted, not merely truthiness.

    A limb that fired for the wrong reason would be a green check measuring
    something else — `CLAUDE.md` rule 10's "green on both engines for two
    different wrong reasons".
    """
    assert kind in contact_channels_in(text), why


def test_every_limb_is_reachable_and_the_set_is_the_one_the_module_declares():
    """**A guard for the guard.** Each named limb must be exercised above.

    A limb nobody tests is a limb that can be deleted by a false-positive fix
    and never noticed — which is exactly how a flat list loses coverage
    (rule 11).
    """
    exercised = {kind for _text, kind, _why in CHANNELS_THAT_MUST_BE_REFUSED}
    assert exercised == set(CHANNEL_KINDS), (
        f"these limbs of the rule have no must-fire row: "
        f"{sorted(set(CHANNEL_KINDS) - exercised)}"
    )


@pytest.mark.parametrize("empty", [(), [], set(), frozenset(), ""])
def test_selecting_no_limb_raises_rather_than_guarding_nothing(empty):
    """**The second way to select nothing**, and it had no exception.

    The docstring already promised that a *misspelled* limb raises rather
    than matching nothing. An empty selector is the same guard by a different
    typo: measured on the shipped code,
    `has_contact_channel("wa.me/91 98400 12345 priya@x.com", ())` returned
    `False` — a string carrying all three channels, read as carrying none,
    by a caller that looks exactly like a caller that is guarding.

    `None` is the only way to mean "all of them" (rule 10).
    """
    loud = "wa.me/91 98400 12345 priya@x.com"
    assert contact_channels_in(loud) == sorted(CHANNEL_KINDS), (
        "the fixture must carry every channel, or this proves nothing"
    )
    with pytest.raises(ValueError):
        contact_channels_in(loud, empty)
    with pytest.raises(ValueError):
        has_contact_channel(loud, empty)


@pytest.mark.parametrize(
    "uncaught",
    [
        "Priya (t.me priya)",
        "Priya, insta priya_r",
        "Priya, ask me in class",
    ],
)
def test_the_declared_ceiling_is_the_real_ceiling(uncaught):
    """**The limits, asserted rather than described.**

    `apps/core/contact.py` lists what it cannot catch. This pins that list to
    the measurement: if a future tightening starts catching one of these, the
    docstring is now wrong and this test says so. It is the opposite of a
    coverage claim — it is the record of where the human layer takes over.
    """
    assert contact_channels_in(uncaught) == [], (
        "this now IS caught — update apps/core/contact.py's declared ceiling, "
        "because a docstring that understates a control is still a document "
        "disagreeing with a measurement"
    )


# --- the setter ------------------------------------------------------------


@pytest.mark.parametrize("name, why", NAMES_THAT_MUST_BE_ACCEPTED)
def test_update_profile_accepts_a_real_name(seller, name, why):
    from apps.accounts.services import update_profile

    update_profile(seller, display_name=name)
    seller.refresh_from_db()
    assert seller.display_name == name, why


@pytest.mark.parametrize("text, kind, why", CHANNELS_THAT_MUST_BE_REFUSED)
def test_update_profile_refuses_a_channel_and_changes_nothing(
    seller, text, kind, why
):
    from apps.accounts.services import update_profile

    before = seller.display_name
    before_version = seller.version
    with pytest.raises(ValidationFailed) as raised:
        update_profile(seller, display_name=text)
    assert "display_name" in raised.value.context.get("field_errors", {}), (
        "the refusal must say which field, or the student cannot act on it"
    )
    assert kind in raised.value.context.get("detail", ""), (
        "the refusal must name the limb that fired, or a false positive "
        "cannot be diagnosed without a debugger"
    )
    seller.refresh_from_db()
    assert seller.display_name == before, "a refused write must not land"
    assert seller.version == before_version, "a refused write must not bump the version"


# --- the boundary the contract makes the claim at --------------------------


def test_a_listing_response_carries_no_contact_channel_in_any_value(
    client_as, seller, book
):
    """API-CONTRACT §5.2, asked of **values** and not of key names.

    `tests/unit/test_forbidden_response.py` sweeps the keys. That is the
    control that was satisfied while the defect shipped, so this sweeps every
    string in the payload — including `seller.display_name`, which is the one
    a key-name rule can never see.
    """
    from apps.accounts.services import update_profile
    from apps.listings import services

    update_profile(seller, display_name="Priya R 2")
    seller.refresh_from_db()
    listing = services.create_listing(
        seller, book=book, asking_price_paise=27500, condition="GOOD",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    body = client_as(seller).get(f"/api/v1/listings/{listing.id}").json()

    def _strings(node, path="$"):
        if isinstance(node, dict):
            for key, value in node.items():
                yield from _strings(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                yield from _strings(value, f"{path}[{index}]")
        elif isinstance(node, str):
            yield path, node

    offenders = {
        path: contact_channels_in(value)
        for path, value in _strings(body)
        if path not in MACHINE_IDENTIFIERS and contact_channels_in(value)
    }
    assert offenders == {}, (
        f"a listing response carries a contact channel: {offenders}"
    )


def test_the_exemption_does_not_swallow_a_human_string():
    """**The guard for the guard.** The exemption is two paths, not a rule
    about digits — so the detector must still fire on the exempted *values*
    when they appear anywhere a person typed them.

    Without this, `MACHINE_IDENTIFIERS` could grow into a general "ignore
    long numbers" allowance and nothing would notice. That is the shape rule
    13 warns about: the exemption gets widened instead of the control.
    """
    assert contact_channels_in("9788177589139") == ["dialable"], (
        "an ISBN's digits are exempt by PATH; the same digits in a name are "
        "still a channel"
    )
    assert "$.seller.display_name" not in MACHINE_IDENTIFIERS
