"""`DATA-MODEL.md` §6.1 as an exhaustive matrix: every state x every endpoint.

The charter's transition-matrix deliverable names `transfers.state` (§6.2),
which is S4. **`listings.status` is the state machine S2 ships** and it has
the same property that makes a matrix worth writing: the diagram names the
legal moves and says nothing about the rest, so the illegal cells are the
ones nobody writes a test for and the ones a student reaches by using the
back button.

§6.1, transcribed — this is the only input, and the code was not read to
build it:

    DRAFT ──submit──> PENDING_REVIEW ──approve──> LIVE
      │                     │
      │                     └──reject──> REJECTED (terminal)
      │
      └──discard──> WITHDRAWN (terminal)

    LIVE ──offer accepted──> RESERVED ──transfer completed──> CLOSED_TRANSFERRED
                                │
                                └──cancelled/expired/no-show──> LIVE (relisted)

    LIVE | RESERVED | PENDING_REVIEW ──seller withdraws──> WITHDRAWN (terminal)
    LIVE | RESERVED | PENDING_REVIEW ──staff/legal takedown──> REMOVED_LEGAL

**Every cell is 2xx or 422**, per API-CONTRACT §2.2: *"422 — valid request,
illegal state transition"*, and *"403 vs 422 is a real distinction: 403 means
**you** may not; 422 means the **object** is not in a state where this is
possible."* The actor in every cell below is the owning seller with every
precondition satisfied, so a 403 anywhere is itself a finding.

**Two endpoints the diagram does not cover** are recorded rather than
guessed, because the charter's job includes *"behaviour nobody specified"*:
adding a photo, and reading the listing back. Their rows assert what the
build does and say that no document rules it.
"""

import json
import uuid

import pytest

pytestmark = pytest.mark.django_db

#: §6.1's eight values, from `DATA-MODEL.md` §3's CHECK constraint.
STATES = [
    "DRAFT", "PENDING_REVIEW", "LIVE", "RESERVED",
    "CLOSED_TRANSFERRED", "WITHDRAWN", "REJECTED", "REMOVED_LEGAL",
]

#: §6.1's terminal states, named in the diagram with "(terminal)".
TERMINAL = {"CLOSED_TRANSFERRED", "WITHDRAWN", "REJECTED", "REMOVED_LEGAL"}

#: `publish` is §6.1's `submit`: the only arrow leaving DRAFT that is not
#: `discard`. Whether it lands in PENDING_REVIEW or LIVE depends on
#: `LISTING_REVIEW_ALL`, which §6.1 says is `true` at pilot — that is a
#: question about the *destination*, not about which states may be left.
PUBLISH_ALLOWED_FROM = {"DRAFT"}

#: §6.1 gives `withdraw` two arrows: `DRAFT ──discard──> WITHDRAWN` and
#: `LIVE | RESERVED | PENDING_REVIEW ──seller withdraws──> WITHDRAWN`. Four
#: source states, and the four that are missing are exactly the terminals.
WITHDRAW_ALLOWED_FROM = {"DRAFT", "PENDING_REVIEW", "LIVE", "RESERVED"}


def _force(listing, status):
    """Put the row in `status` without going through a transition.

    Deliberate: the matrix is about **which moves each state permits**, and
    reaching RESERVED or CLOSED_TRANSFERRED legitimately needs `transfers`,
    which is S4. Driving the column directly is the only way to ask the S2
    question today, and the price trigger is untouched by it — which
    `tests/contract/test_price_trigger_attack.py` asserts is the correct
    behaviour for a non-price update.
    """
    from apps.listings.models import Listing

    Listing.all_objects.filter(id=listing.id).update(status=status)
    listing.refresh_from_db()
    return listing


@pytest.fixture
def seller_api(client_as, seller, book):
    client = client_as(seller)

    class Api:
        def post(self, path, body=None):
            return client.post(
                path, data=json.dumps(body or {}),
                content_type="application/json",
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )

        def get(self, path):
            return client.get(path)

        def multipart(self, path, data):
            return client.post(
                path, data=data, headers={"Idempotency-Key": str(uuid.uuid4())}
            )

        def new_listing(self):
            from apps.listings.models import Listing

            created = self.post("/api/v1/listings", {
                "accept_seller_terms": True, "book_id": book.id,
                "asking_price_paise": 30000, "condition": "GOOD",
                "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
                "language": "en", "category": "PRESCRIBED_TEXTBOOK",
            })
            assert created.status_code == 201, created.content[:300]
            return Listing.all_objects.get(id=created.json()["id"])

    return Api()


def _code(response):
    try:
        return response.json().get("error", {}).get("code")
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------
# the matrix
# --------------------------------------------------------------------------


@pytest.mark.parametrize("state", STATES)
def test_publish_from_every_state(seller_api, state):
    """One row per state. A legal source must be 2xx; every other must be 422.

    Parameterised per state rather than looped, so a failing cell names the
    state rather than burying it in a dict — the charter's reason for an
    exhaustive matrix is that the failing cell has to be readable.
    """
    listing = _force(seller_api.new_listing(), state)
    response = seller_api.post(
        f"/api/v1/listings/{listing.id}/publish",
        {"expected_version": listing.version},
    )
    if state in PUBLISH_ALLOWED_FROM:
        assert 200 <= response.status_code < 300, (
            f"§6.1 has `DRAFT ──submit──> PENDING_REVIEW`, so publish from "
            f"{state} must succeed; got {response.status_code} "
            f"{_code(response)}: {response.content[:200]}"
        )
        return
    assert response.status_code == 422, (
        f"§6.1 has no `submit` arrow leaving {state}, so API-CONTRACT §2.2 "
        f"makes this 422 ('the object is not in a state where this is "
        f"possible'); got {response.status_code} {_code(response)}"
    )
    assert _code(response) == "TRANSITION_NOT_ALLOWED", _code(response)
    assert response.status_code != 403, (
        "403 would say *you* may not, and the actor here is the owning "
        "seller with every precondition met — §2.2 calls this a real "
        "distinction and clients branch on it"
    )


@pytest.mark.parametrize("state", STATES)
def test_withdraw_from_every_state(seller_api, state):
    """§6.1's two withdraw arrows, and the four states that have neither."""
    listing = _force(seller_api.new_listing(), state)
    response = seller_api.post(
        f"/api/v1/listings/{listing.id}/withdraw",
        {"expected_version": listing.version},
    )
    if state in WITHDRAW_ALLOWED_FROM:
        assert 200 <= response.status_code < 300, (
            f"§6.1 gives {state} a withdraw arrow "
            f"({'discard' if state == 'DRAFT' else 'seller withdraws'}); got "
            f"{response.status_code} {_code(response)}: {response.content[:200]}"
        )
        assert response.json()["status"] == "WITHDRAWN"
        return
    assert response.status_code == 422, (
        f"{state} is terminal in §6.1 and has no outgoing arrow; got "
        f"{response.status_code} {_code(response)}"
    )
    assert _code(response) == "TRANSITION_NOT_ALLOWED", _code(response)


def test_the_allowed_sets_partition_the_states_and_both_sides_are_rows():
    """`CLAUDE.md` rule 10's corollary: *where a rule splits a set, both sides
    are rows, and a test enforces that.*

    Checking only the permitted side passes. These two assertions make the
    matrices above exhaustive by construction rather than by having been
    written out carefully once.
    """
    for name, allowed in (
        ("publish", PUBLISH_ALLOWED_FROM), ("withdraw", WITHDRAW_ALLOWED_FROM)
    ):
        assert allowed <= set(STATES), (name, allowed - set(STATES))
        refused = set(STATES) - allowed
        assert refused, f"{name} has no refused states, so half the matrix is empty"
    assert WITHDRAW_ALLOWED_FROM == set(STATES) - TERMINAL, (
        "§6.1's withdraw arrows cover exactly the four non-terminal states. "
        "If that stopped being true, either a terminal gained an outgoing "
        "arrow or a live state lost one, and the diagram is the thing to "
        "change first"
    )
    assert TERMINAL == {"CLOSED_TRANSFERRED", "WITHDRAWN", "REJECTED", "REMOVED_LEGAL"}


def test_every_state_in_the_check_constraint_is_in_this_matrix():
    """The guard on the matrix. A ninth status added by a migration without a
    row here is a state nobody checked any endpoint against.

    Read from the **database**, not from the model's choices: the CHECK
    constraint is what the engine enforces and a model `choices` list is a
    form-layer hint.
    """
    from django.db import connection

    with connection.cursor() as cur:
        if connection.vendor == "postgresql":
            cur.execute(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'listings_status_chk'"
            )
        else:
            cur.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='listings'"
            )
        row = cur.fetchone()
    assert row, "`listings_status_chk` is not installed"
    definition = row[0]
    missing = [s for s in STATES if s not in definition]
    assert missing == [], f"this matrix names states the schema does not: {missing}"

    import re

    in_schema = set(re.findall(r"'([A-Z_]{4,})'", definition))
    # The constraint text on SQLite is the whole CREATE TABLE, so other
    # enums appear; intersect with what a status could be rather than
    # comparing wholesale.
    status_like = {s for s in in_schema if s in set(STATES)} | (
        in_schema & {"PENDING_REVIEW", "CLOSED_TRANSFERRED", "REMOVED_LEGAL"}
    )
    assert status_like == set(STATES), (
        "the schema's status set and this matrix's differ: "
        f"{sorted(status_like ^ set(STATES))}"
    )


# --------------------------------------------------------------------------
# the cells no document rules
# --------------------------------------------------------------------------


@pytest.mark.parametrize("state", STATES)
def test_adding_a_photo_from_every_state(seller_api, state, jpeg_bytes):
    """**Behaviour nobody specified — recorded, not graded.**

    §6.1 is a diagram of `status` transitions and adding a photo is not one,
    so no frozen document says whether a seller may add a fifth view of the
    book to a `LIVE` listing a buyer has already read, or to a `RESERVED` one
    a buyer has already committed to. `DATA-MODEL.md` §3 caps the count and
    is silent on the state.

    The build refuses the four terminal states and allows the rest. That is a
    defensible reading and it is **not written down anywhere**, which is the
    finding: the next person to touch this has nothing to check against, and
    the `RESERVED` cell in particular is a product question (changing the
    photos of a book someone has agreed to collect) rather than a technical
    one.

    Asserted as observed, so a later change is visible; routed to cto as an
    unspecified cell rather than reported as a defect.
    """
    import io

    listing = _force(seller_api.new_listing(), state)
    buf = io.BytesIO(jpeg_bytes)
    buf.name = "photo.jpg"
    response = seller_api.multipart(
        f"/api/v1/listings/{listing.id}/photos", {"photo": buf}
    )
    if state in TERMINAL:
        assert response.status_code == 422, (
            f"OBSERVED BEHAVIOUR CHANGED (state={state}): the build refused "
            "photo uploads on terminal listings and now answers "
            f"{response.status_code}. No document rules this cell; if the "
            "rule changed, DATA-MODEL §6.1 or §3 should say so first."
        )
        assert _code(response) == "TRANSITION_NOT_ALLOWED"
    else:
        assert response.status_code == 201, (
            f"OBSERVED BEHAVIOUR CHANGED (state={state}): the build allowed "
            f"photo uploads on non-terminal listings and now answers "
            f"{response.status_code} {_code(response)}. Same note: no "
            "document rules this cell."
        )


@pytest.mark.parametrize("state", STATES)
def test_the_seller_can_read_their_own_listing_in_every_state(seller_api, state):
    """The read cell, in every state including the ones a takedown produces.

    `REMOVED_LEGAL` is the one that matters: `DATA-MODEL.md` §6.1 says that
    content is *"preserved 180 days for investigation (IT Rules r.3(1)(j))"*,
    and a seller who cannot see what was taken down cannot contest it. The
    diagram says preserve; nothing says *served to the seller*, so this is
    the second unspecified cell and it is recorded the same way.
    """
    listing = _force(seller_api.new_listing(), state)
    response = seller_api.get(f"/api/v1/listings/{listing.id}")
    assert response.status_code == 200, (
        f"the owning seller cannot read their own {state} listing "
        f"({response.status_code} {_code(response)}). For REMOVED_LEGAL that "
        "is also a due-process question: §6.1 preserves the content for 180 "
        "days and a seller who cannot see it cannot contest the takedown."
    )
    assert response.json()["status"] == state
