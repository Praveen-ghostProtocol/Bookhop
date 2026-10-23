"""P16(iv): the ninth `erase.retained.*` item, asserted on the served page.

**frontend-developer's tree** (`TASKS.md` §1), for the same reason
`test_withheld_catalogue_text.py` is: a regression for a template and a
catalogue row belongs to whoever owns those files.

### WHY THIS IS NOT THE TEST PRIVACY-COMPLIANCE ALREADY WROTE

`tests/contract/test_the_inventory_covers_the_schema.py::test_the_deletion_card_enumerates_the_want`
greps `templates/delete_confirm.html` for the context key. That is the right
instrument for *"the enumeration names a want"*, and it is blind to the one
way the enumeration can still be false to a reader: **a line that is defined
and never shown.** A `{% translate %}` inside a `{% comment %}`, an `<li>`
below a `{% endblock %}`, a card the route stopped rendering — all of them
keep the key in the file. That is `CLAUDE.md` rule 10's third disguise, so
this fetches `GET /account/delete` and reads the response body.

Three things are asserted before the new sentence, so a pass means what it
looks like:

1. **the response is the card** — the heading and the lead-in are on it;
2. **the sentence is non-empty in the catalogue.** `""` is a substring of
   every page, so an empty `msgid` would make the assertion below pass over
   nothing — which is exactly how three empty ids survived the deny-list
   (`test_copy_catalogue_is_the_shipped_copy.py`);
3. **the other eight items are on the page**, so a card that lost its list
   fails here by name rather than passing on a sentence that happens to be
   somewhere else.

And the sentence must be **inside the retained list**, not merely on the
page: a disclosure that sits under a different heading is not an entry in the
enumeration the card asserts.

The text is read from `locale/en` rather than retyped, so this file cannot
drift from the shipped copy (`CLAUDE.md` rule 11). `django.po` is never
compiled here, so `pgettext` falls through to the `msgid` and the `msgid` is
what a student is served.
"""

import pathlib

import pytest
from django.test import Client

from apps.accounts.sessions import SESSION_USER_KEY

pytestmark = pytest.mark.django_db

CATALOGUE = pathlib.Path(__file__).resolve().parents[2] / "locale/en/LC_MESSAGES/django.po"

ITEMS = (
    "transfers", "wants", "chat", "reports",
    "email_hash", "account", "age", "audit", "consents",
)


def shipped(context):
    """The `msgid` for one `msgctxt`, read as text — no loader, no fallback."""
    for block in CATALOGUE.read_text(encoding="utf-8").split("\n\n"):
        if f'msgctxt "{context}"\n' not in block:
            continue
        for line in block.splitlines():
            if line.startswith("msgid "):
                return line[len("msgid "):].strip().strip('"')
    raise AssertionError(f"{context} is not in {CATALOGUE}")


def test_the_card_shows_the_want_inside_the_retained_list(student):
    client = Client()
    session = client.session
    session[SESSION_USER_KEY] = student.id
    session.save()

    response = client.get("/account/delete")
    assert response.status_code == 200
    body = response.content.decode()

    # (1) this is the card.
    heading = shipped("erase.retained.h")
    lead_in = shipped("erase.confirm.retained")
    assert heading in body and lead_in in body, (
        "the response is not the deletion card, so everything below would be "
        "measuring the wrong page"
    )

    # (2) the sentence exists before it is looked for.
    want = shipped("erase.retained.wants")
    assert len(want) > 60, (
        f"erase.retained.wants is {len(want)} characters in the catalogue; an "
        "empty or truncated msgid makes the assertion below vacuous"
    )

    # (3) the whole enumeration reaches the page, and the want is in it.
    enumeration = body.split(heading, 1)[1].split("</ul>", 1)[0]
    missing = [k for k in ITEMS if shipped(f"erase.retained.{k}") not in enumeration]
    assert missing == [], (
        "these erase.retained.* items are not rendered inside the list under "
        f"{heading!r}, so the card's enumeration is incomplete on the page a "
        f"student is served: {missing}"
    )
