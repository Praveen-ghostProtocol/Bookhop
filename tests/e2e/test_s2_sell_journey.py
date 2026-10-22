"""JOURNEYS J2 and J4 over real HTTP, and the seams the journey is the only
thing that reaches.

**The standing argument for this file is backend's own, and it is the right
one**: running the journey over real HTTP found four defects *"no unit test
could see, all at seams"* — a multipart 500, a 500 after the write committed,
a wrong replay status, and **a seller-terms route that did not exist, so a
real client met a refusal it could do nothing about.** Every one of those was
invisible to a suite that calls L1 directly.

Backend wrote a regression for each. QA's question is different and is the one
the charter asks: **does the regression pin the seam, or the symptom?** A
regression on `/listings/{id}/photos` catches that endpoint; the seam was
`apps.core.api.endpoint` consuming the request stream, and S5's support
attachments and S6's report evidence are the next multipart endpoints. So the
sweeps here are **derived from the URLconf**, not from a list of paths — a new
route joins them by being mounted.

Nothing in this file calls a service function. That is not style: it is the
only way to reach seam 4's defect class, which is *"an L1 function the journey
needs with no route reaching it"*. A test that can import the function cannot
discover that no client can call it.

Written from `JOURNEYS.md` J2/J4, API-CONTRACT §4.1, §5.2 and §2.2, and
`DATA-MODEL.md` §3 and §6.1.
"""

import io
import json
import threading
import struct
import uuid

import pytest
from django.db import connection, connections

from django.urls import get_resolver

_VENDOR = connection.vendor

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def jpeg(width=4, height=3, *, exif=True, trailing=b""):
    """A structurally valid JPEG container. **The dimensions are what the
    container CLAIMS**, which is the distinction `test_a_file_that_is_a_valid`
    below is about — nothing decodes a pixel.
    """
    parts = [bytes((0xFF, 0xD8))]
    if exif:
        payload = b"Exif\x00\x00II*\x00" + struct.pack("<I", 8)
        payload += struct.pack("<H", 1) + struct.pack("<HHII", 0x8825, 4, 1, 26)
        payload += b"\x00\x00\x00\x00"
        parts.append(bytes((0xFF, 0xE1)) + struct.pack(">H", len(payload) + 2) + payload)
    parts.append(
        bytes((0xFF, 0xC0)) + struct.pack(">H", 11) + bytes((8,))
        + struct.pack(">HH", height, width) + bytes((1,)) + bytes((1, 0x11, 0))
    )
    parts.append(bytes((0xFF, 0xDA)) + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0)))
    parts.append(trailing + bytes((0, 0)) + bytes((0xFF, 0xD9)))
    return b"".join(parts)


def upload(data, name="photo.jpg"):
    buf = io.BytesIO(data)
    buf.name = name
    return buf


def key():
    return str(uuid.uuid4())


def code(response):
    try:
        return response.json().get("error", {}).get("code")
    except Exception:  # noqa: BLE001
        return None


def l2_routes():
    """Every mounted `api/v1/` route, as a Django path pattern string."""
    found = set()

    def walk(patterns, prefix=""):
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                walk(pattern.url_patterns, prefix + str(pattern.pattern))
            else:
                found.add(prefix + str(pattern.pattern))

    walk(get_resolver().url_patterns)
    return {r for r in found if r.startswith("api/v1/")}


@pytest.fixture
def api(client_as, seller):  # noqa: D401
    """A signed-in seller's client with the three verbs the journey uses."""
    client = client_as(seller)

    class Api:
        def post(self, path, body=None, **extra):
            return client.post(
                path, data=json.dumps(body or {}),
                content_type="application/json",
                headers={"Idempotency-Key": key()}, **extra,
            )

        def multipart(self, path, data, idem=None):
            return client.post(
                path, data=data, headers={"Idempotency-Key": idem or key()}
            )

        def get(self, path):
            return client.get(path)

        def delete(self, path):
            return client.delete(path, headers={"Idempotency-Key": key()})

    return Api()


# --------------------------------------------------------------------------
# 1. the journey — seam 4's pin, generalised
# --------------------------------------------------------------------------


def test_a_seller_can_reach_a_published_listing_with_no_service_call(api, book):
    """**JOURNEYS J2, end to end, with nothing but HTTP.**

    This is the generalised form of seam 4's regression. The defect was not
    *"the seller-terms check is wrong"* — it was that `accept_seller_terms`
    was an L1 function **no route reached**, so every unit test passed while
    a real client got `403 SELLER_TERMS_NOT_ACCEPTED` with nothing it could
    do. Backend's regression asserts the tick records the acceptance, which
    pins the fix. This pins the **class**: a journey a client can complete
    without importing anything.

    J2's steps 4-9 in order: find the book, accept the terms and create, add
    a photo, read it back, publish.
    """
    found = api.get(f"/api/v1/books?isbn={book.isbn13}")
    assert found.status_code == 200, found.content[:300]
    assert found.json()["items"][0]["id"] == book.id

    created = api.post("/api/v1/listings", {
        "accept_seller_terms": True, "book_id": book.id,
        "asking_price_paise": 32000, "condition": "GOOD",
        "annotation_level": "LIGHT_PENCIL", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    })
    assert created.status_code == 201, created.content[:400]
    listing = created.json()
    assert listing["status"] == "DRAFT", (
        "JOURNEYS J2 step 7: the listing is created DRAFT, which is what makes "
        "EC-13 free — an upload that dies at 3 of 4 on 3G leaves a resumable "
        "draft rather than a lost form"
    )

    photo = api.multipart(
        f"/api/v1/listings/{listing['id']}/photos", {"photo": upload(jpeg())}
    )
    assert photo.status_code == 201, photo.content[:400]

    mine = api.get("/api/v1/listings/mine")
    assert mine.status_code == 200
    assert [row["id"] for row in mine.json()["items"]] == [listing["id"]]

    published = api.post(
        f"/api/v1/listings/{listing['id']}/publish",
        {"expected_version": listing["version"]},
    )
    assert published.status_code == 200, published.content[:400]
    assert published.json()["status"] in ("PENDING_REVIEW", "LIVE"), published.json()


def test_a_student_can_record_a_want_with_no_service_call(api):
    """JOURNEYS J4 steps 2 and 6, the same way.

    PRD AC-B2.5 is asserted on the payload rather than on the template:
    *"nothing here returns an estimate of when the book will arrive, and there
    is no column for one"*. A want that promised a date would be the one
    sentence in this product most likely to be read as a commitment.
    """
    made = api.post("/api/v1/requests", {
        "free_text_title": "Higher Engineering Mathematics", "course_code": "MA8151",
    })
    assert made.status_code == 201, made.content[:300]
    row = made.json()
    assert row["status"] == "OPEN"

    flat = json.dumps(row).lower()
    for promise in ("eta", "expected", "estimate", "likely", "soon", "within"):
        assert promise not in flat, (
            f"the want response carries {promise!r} (PRD AC-B2.5: the want "
            "form never promises a time, a probability, or that the book "
            "will come)"
        )

    closed = api.delete(f"/api/v1/requests/{row['id']}")
    assert closed.status_code == 200, closed.content[:300]
    assert closed.json()["status"] == "WITHDRAWN"


# --------------------------------------------------------------------------
# 2. seam 1 — multipart, derived from the URLconf
# --------------------------------------------------------------------------

#: Routes the multipart sweep sends a file at. Derived below; this records
#: which ones are expected to *accept* one so a 400 can be told from a 500.
MULTIPART_ACCEPTING = {"api/v1/listings/<int:listing_id>/photos"}


def test_no_post_route_answers_500_to_a_multipart_body(client_as, seller, book):
    """**Seam 1, pinned at the seam.**

    The defect was in `apps.core.api.endpoint`: *"the decorator consumed the
    request stream"*, so Django's multipart parser found nothing and every
    multipart request was a 500. It is a property of the **decorator**, not
    of the photo route — and the photo route is the only multipart endpoint
    today, which is exactly why a regression written against it stops
    measuring the moment S5 adds support attachments or S6 adds report
    evidence.

    So every mounted POST route is sent a multipart body. A `4xx` is fine:
    the handler read the request and refused it, which is the property. A
    `5xx` is the defect, whatever the route.
    """
    client = client_as(seller)
    substitutions = {"<int:listing_id>": "1", "<int:book_id>": str(book.id),
                     "<int:request_id>": "1", "<str:purpose_key>": "account",
                     "<str:kind>": "PRIVACY", "<str:sha256>": "0" * 64}

    checked, crashed = [], []
    for route in sorted(l2_routes()):
        path = "/" + route
        for pattern, value in substitutions.items():
            path = path.replace(pattern, value)
        if "<" in path:
            continue
        response = client.post(
            path, data={"photo": upload(jpeg()), "field": "value"},
            headers={"Idempotency-Key": key()},
        )
        checked.append(route)
        if response.status_code >= 500:
            crashed.append((route, response.status_code))

    assert len(checked) >= 10, (
        f"the sweep reached only {len(checked)} routes; an instrument asserts "
        f"its own reach: {checked}"
    )
    assert crashed == [], (
        "these routes answer 5xx to a multipart body, which is seam 1's "
        f"defect class recurring on a route its regression does not name: "
        f"{crashed}"
    )


def test_the_json_branch_of_the_same_seam_still_works(api, book):
    """The other half of the split. A fix that branches on content type has
    two halves and a test on one of them is a branch with an untested half —
    `CLAUDE.md` rule 10's *"where a rule splits a set, both sides are rows"*.
    """
    response = api.post("/api/v1/listings", {
        "accept_seller_terms": True, "book_id": book.id,
        "asking_price_paise": 25000, "condition": "FAIR",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    })
    assert response.status_code == 201, response.content[:300]


# --------------------------------------------------------------------------
# 3. seam 2 — the idempotency store, pinned at the store
# --------------------------------------------------------------------------


def test_the_idempotency_store_round_trips_every_type_a_payload_can_hold(seller):
    """**Seam 2, pinned at the seam rather than at the two endpoints.**

    The defect: *"`idempotency_keys.response_body` is a `JSONField` whose
    encoder has no `default=str`, so storing a payload with a `datetime`
    raised **after** the mutation"* — the write committed and the student was
    told it failed. Backend's regression parametrises two paths that happen to
    return a timestamp today.

    The seam is the **encoder**. Every type a response payload can hold is put
    through the store directly, so a payload that starts carrying a `Decimal`
    or a `UUID` in S4 fails here rather than in production. `UUID` is not
    hypothetical: every pseudonym in this schema is one, and `seller_block`
    returns a pseudonym.
    """
    import datetime as dt
    import decimal

    from apps.core.models import IdempotencyKey

    payload = {
        "when": dt.datetime(2026, 11, 1, 9, 30, tzinfo=dt.timezone.utc),
        "on": dt.date(2026, 11, 1),
        "who": uuid.uuid4(),
        "how_much": decimal.Decimal("1.00"),
        "nested": [{"at": dt.datetime.now(dt.timezone.utc)}],
    }
    from apps.core.api import jsonable

    row = IdempotencyKey.objects.create(
        key=str(uuid.uuid4()), endpoint="qa/store-probe",
        user_id=seller.id, request_hash="0" * 64,
        response_status=201, response_body=jsonable(payload),
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1),
    )
    row.refresh_from_db()
    assert set(row.response_body) == set(payload), row.response_body
    assert isinstance(row.response_body["nested"][0]["at"], str)


def test_no_post_route_answers_500_on_a_replay(client_as, seller, book):
    """The behavioural half of the same seam, swept rather than listed.

    The symptom was *"a 500 after the write had committed"*, and the thing
    that makes it dangerous is that it happens on the **store**, after the
    mutation. So every POST route is called twice with the same key and the
    second call must not be a 5xx — whatever the first answered.
    """
    client = client_as(seller)
    substitutions = {"<int:listing_id>": "1", "<int:book_id>": str(book.id),
                     "<int:request_id>": "1", "<str:purpose_key>": "account",
                     "<str:kind>": "PRIVACY", "<str:sha256>": "0" * 64}
    bodies = {
        "api/v1/listings": {
            "accept_seller_terms": True, "book_id": book.id,
            "asking_price_paise": 30000, "condition": "GOOD",
            "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
            "language": "en", "category": "PRESCRIBED_TEXTBOOK",
        },
        "api/v1/requests": {"free_text_title": "A replayed want"},
        "api/v1/account/correction": {"stated_problem": "A replayed correction."},
    }

    checked, crashed = [], []
    for route in sorted(l2_routes()):
        if route in ("api/v1/account/erase",):  # terminal: tombstones the actor
            continue
        path = "/" + route
        for pattern, value in substitutions.items():
            path = path.replace(pattern, value)
        if "<" in path:
            continue
        idem = key()
        body = json.dumps(bodies.get(route, {}))
        first = client.post(path, data=body, content_type="application/json",
                            headers={"Idempotency-Key": idem})
        second = client.post(path, data=body, content_type="application/json",
                             headers={"Idempotency-Key": idem})
        checked.append(route)
        for label, response in (("first", first), ("replay", second)):
            if response.status_code >= 500:
                crashed.append((route, label, response.status_code,
                                response.content[:120]))

    assert len(checked) >= 10, f"the sweep reached only {checked}"
    assert crashed == [], (
        "seam 2's defect class — a 5xx raised by the idempotency store after "
        f"the mutation — recurring: {crashed}"
    )


def test_a_replay_with_a_different_body_is_a_409(client_as, seller):
    """API-CONTRACT §4.1's third rule, which none of the four seam regressions
    covers and which the charter names explicitly: *same key with a different
    body is a 409*.

    Different from a replay: a replay is the **same** request arriving twice
    and must return the stored response. The same key with a different body is
    a client bug or a key collision, and answering it with the first call's
    response would silently drop the second write.
    """
    client = client_as(seller)
    idem = key()

    def send(title):
        return client.post(
            "/api/v1/requests", data=json.dumps({"free_text_title": title}),
            content_type="application/json", headers={"Idempotency-Key": idem},
        )

    first = send("First body")
    assert first.status_code == 201, first.content[:200]
    second = send("A different body entirely")
    assert second.status_code == 409, (
        f"API-CONTRACT §4.1: the same `Idempotency-Key` with a different body "
        f"is a 409; got {second.status_code} {code(second)}"
    )


# --------------------------------------------------------------------------
# 4. seam 3 — 409 before 422, on every transition endpoint
# --------------------------------------------------------------------------

#: §6.1's transitions that have an L2 endpoint in S2. Derived from the
#: URLconf in `test_every_transition_endpoint_orders_409_before_422` so a
#: fifth one in S4 joins without an edit here.
TRANSITION_SUFFIXES = ("publish", "withdraw")


def test_every_transition_endpoint_orders_409_before_422(api, book):
    """**Seam 3, swept over the transition endpoints rather than one of them.**

    The defect: a replayed stale form answered `422 TRANSITION_NOT_ALLOWED`
    — *"the object cannot do this"*, which leads nowhere — when the truth was
    `409 VERSION_CONFLICT`, *"someone changed this"*, which leads to "reload
    and try again". Backend's regression pins `publish`. The ordering lives in
    the service layer's precondition order and applies to `withdraw`
    identically, so both are driven and a new one is found from the URLconf.
    """
    endpoints = sorted(
        r for r in l2_routes() if r.rsplit("/", 1)[-1] in TRANSITION_SUFFIXES
    )
    assert endpoints == [
        "api/v1/listings/<int:listing_id>/publish",
        "api/v1/listings/<int:listing_id>/withdraw",
    ], f"the transition surface changed; this sweep must follow it: {endpoints}"

    for suffix in TRANSITION_SUFFIXES:
        created = api.post("/api/v1/listings", {
            "accept_seller_terms": True, "book_id": book.id,
            "asking_price_paise": 30000, "condition": "GOOD",
            "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
            "language": "en", "category": "PRESCRIBED_TEXTBOOK",
        }).json()
        path = f"/api/v1/listings/{created['id']}/{suffix}"
        first = api.post(path, {"expected_version": created["version"]})
        assert first.status_code == 200, (suffix, first.content[:300])

        stale = api.post(path, {"expected_version": created["version"]})
        assert (stale.status_code, code(stale)) == (409, "VERSION_CONFLICT"), (
            f"{suffix}: a stale `expected_version` must be 409 VERSION_CONFLICT "
            f"('someone changed this'), not 422 ('the object cannot do this'). "
            f"Got {stale.status_code} {code(stale)}"
        )


def test_a_current_version_on_an_impossible_move_is_still_422(api, book):
    """The other side of the reorder, so 409 did not swallow 422."""
    created = api.post("/api/v1/listings", {
        "accept_seller_terms": True, "book_id": book.id,
        "asking_price_paise": 30000, "condition": "GOOD",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    }).json()
    withdrawn = api.post(f"/api/v1/listings/{created['id']}/withdraw",
                         {"expected_version": created["version"]}).json()
    response = api.post(f"/api/v1/listings/{created['id']}/publish",
                        {"expected_version": withdrawn["version"]})
    assert (response.status_code, code(response)) == (422, "TRANSITION_NOT_ALLOWED"), (
        f"got {response.status_code} {code(response)}"
    )


# --------------------------------------------------------------------------
# 5. the photo cap, and the race backend declared
# --------------------------------------------------------------------------


def test_the_fifth_photo_is_refused(api, book):
    """`DATA-MODEL.md` §3: *"Max 4 photos per listing"*. The sequential case."""
    listing = api.post("/api/v1/listings", {
        "accept_seller_terms": True, "book_id": book.id,
        "asking_price_paise": 30000, "condition": "GOOD",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    }).json()
    path = f"/api/v1/listings/{listing['id']}/photos"
    for n in range(4):
        # Distinct **stripped** bytes, so the content-hash key differs. Varying
        # the EXIF tag would not: stripping removes it and the four uploads
        # would dedupe to one object, which would make this test pass with one
        # photo stored. Dimensions live in SOF0 and survive the strip.
        response = api.multipart(path, {"photo": upload(jpeg(width=4 + n))})
        assert response.status_code == 201, (n, response.content[:300])
    fifth = api.multipart(path, {"photo": upload(jpeg(width=40))})
    assert fifth.status_code == 422, fifth.content[:300]
    assert code(fifth) == "TOO_MANY_PHOTOS", code(fifth)


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(
    _VENDOR != "postgresql",
    reason=(
        "NOT VERIFIABLE ON THIS ENGINE (vendor=sqlite, slice=S2): the cap is "
        "lost to a race between concurrent transactions and SQLite has one "
        "database writer, so a green run here would prove serialisation "
        "rather than the property (ENGINE-DIVERGENCE §4.1). Run with "
        "BOOKHOP_DB_ENGINE=postgres."
    ),
)
def test_the_four_photo_cap_survives_simultaneous_uploads(client_as, seller, book):
    """**The ceiling backend declared — measured, and much wider than declared.**

    `add_photo`'s own note: *"the four-photo cap is a conditional insert
    inside this transaction, not DATA-MODEL §3's counting trigger. Ceiling:
    two simultaneous uploads on the same listing could both see three and
    both insert, giving five. … the cost of exceeding it is a fifth
    thumbnail."*

    A declared ceiling is a prediction until it is run (`CLAUDE.md` rule 9:
    *"an unverified claim about platform behaviour is a prediction and is
    written as one"*). It is run here: a listing with three photos, six
    uploads released together on a barrier so they contend rather than
    serialise by start-up latency.

    **First measured, PostgreSQL 16.15: all six returned `201` and the
    listing ended with NINE photos.** Not two-into-five — every concurrent
    writer passed, because `count() >= 4` was read inside each transaction
    under READ COMMITTED with no lock on the listing row and no unique
    constraint to collide on. The ceiling as written understated it by a
    factor the second half of the note ("a fifth thumbnail") was reasoning
    from, and S7's derivative generation would have sized its work off
    `MAX_PHOTOS_PER_LISTING` believing it was enforced.

    **Re-measured after the fix (`57c6689`): the cap holds at four.** The
    `SELECT … FOR UPDATE` on the listing row serialises the count, so the
    racers queue and the losers get `422 TOO_MANY_PHOTOS`. Run three times
    to be sure the pass is the lock and not the scheduler.

    **This test stays as the regression and is deliberately not softened to
    "the fix is present".** The lock is one line and a later refactor that
    moves the count outside the locked block would restore the defect with
    every unit test still green — which is how it got here. The subject is
    the number of rows, measured, not the mechanism.
    """
    from apps.listings.models import ListingPhoto

    client = client_as(seller)
    listing = json.loads(client.post(
        "/api/v1/listings",
        data=json.dumps({
            "accept_seller_terms": True, "book_id": book.id,
            "asking_price_paise": 30000, "condition": "GOOD",
            "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
            "language": "en", "category": "PRESCRIBED_TEXTBOOK",
        }),
        content_type="application/json",
        headers={"Idempotency-Key": key()},
    ).content)
    path = f"/api/v1/listings/{listing['id']}/photos"

    for n in range(3):
        seeded = client.post(path, data={"photo": upload(jpeg(width=4 + n))},
                             headers={"Idempotency-Key": key()})
        assert seeded.status_code == 201, seeded.content[:200]

    racers = 6
    barrier = threading.Barrier(racers)
    outcomes = []
    lock = threading.Lock()

    def attempt(index):
        try:
            # Distinct dimensions, so distinct **stripped** bytes and distinct
            # content-hash keys. Identical bytes would collide on the UNIQUE
            # `storage_key` and the unique index would do the capping -- which
            # would make this test pass for a reason that has nothing to do
            # with the cap.
            racer = client_as(seller)
            photo = upload(jpeg(width=100 + index))
            barrier.wait(timeout=30)
            response = racer.post(path, data={"photo": photo},
                                  headers={"Idempotency-Key": key()})
            with lock:
                outcomes.append(response.status_code)
        except BaseException as exc:  # noqa: BLE001 - the outcome is the datum
            with lock:
                outcomes.append(repr(exc)[:120])
        finally:
            connections.close_all()

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(racers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert not any(t.is_alive() for t in threads), "a worker thread did not finish"
    assert len(outcomes) == racers, outcomes

    stored = ListingPhoto.all_objects.filter(listing_id=listing["id"]).count()
    accepted = [o for o in outcomes if o == 201]
    assert stored <= 4, (
        f"FINDING. DATA-MODEL §3 says *'Max 4 photos per listing'*. After "
        f"three sequential uploads and {racers} simultaneous ones, the "
        f"listing holds **{stored}** photos and {len(accepted)} of the "
        f"{racers} racers were accepted (outcomes: {outcomes}). "
        "`add_photo` reads `count() >= MAX_PHOTOS_PER_LISTING` inside its "
        "own transaction, under READ COMMITTED, with no `SELECT ... FOR "
        "UPDATE` on the listing row and no unique constraint for a loser to "
        "collide on — so every concurrent writer reads the pre-race count "
        "and every one inserts. The declared ceiling ('two could both see "
        "three, giving five') understates it: there is no bound at all "
        "short of the rate limit. "
        "Reachable by the seller alone, as the note says — but the rate "
        "limit is 40/day and a retrying 3G client on EC-13's own resume path "
        "is a plausible source of simultaneity, not a malicious one."
    )


# --------------------------------------------------------------------------
# 6. what the upload path does not check — image content
# --------------------------------------------------------------------------


def test_a_file_that_is_a_valid_container_and_garbage_content_is_stored(api, book):
    """**Backend named this as unverified; it is now measured.**

    `apps/listings/images.py` is explicit, and correct, that it does container
    parsing and never decodes: *"a file can pass here, be a structurally valid
    JPEG, and render as garbage."* The security argument for not taking Pillow
    is good — *"a decoder is the attack surface"* — and QA is not asking for
    it.

    What QA is asking for is that the **consequence** be written down rather
    than inferred, because it is a product consequence and not only a
    technical one: a seller can upload four files that store cleanly, report
    sensible dimensions, pass every check, and show a buyer nothing. There is
    no later gate — no review of the image, no decode in the moderation queue
    — so the first person to discover it is a student at a handover.

    The file below is a valid JPEG container whose entropy-coded data is one
    zero byte. It is accepted.
    """
    listing = api.post("/api/v1/listings", {
        "accept_seller_terms": True, "book_id": book.id,
        "asking_price_paise": 30000, "condition": "GOOD",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    }).json()

    response = api.multipart(
        f"/api/v1/listings/{listing['id']}/photos",
        {"photo": upload(jpeg(width=4000, height=3000))},
    )
    assert response.status_code == 201, response.content[:300]
    body = response.json()
    assert (body["width"], body["height"]) == (4000, 3000), (
        "FINDING (recorded, not a failure): the stored dimensions are the "
        "ones the SOF0 segment **claims**, read without decoding. A 4000x3000 "
        "row whose payload is a handful of bytes is stored as a 4000x3000 "
        "photo. S7's derivative sizing and any 'is this photo big enough' "
        "check must not trust these numbers; nothing today says so."
    )
    assert body["bytes"] < 200, (
        "the fixture is meant to be a few bytes of payload claiming large "
        f"dimensions; it is {body['bytes']} bytes and the point is lost"
    )


def test_a_truncated_jpeg_is_refused_rather_than_stored(api, book):
    """The other side: the container check is not vacuous.

    If *everything* were accepted the test above would be measuring nothing.
    A JPEG with no SOI is refused, which is what makes "valid container,
    garbage content" a real distinction rather than "no checking at all".
    """
    listing = api.post("/api/v1/listings", {
        "accept_seller_terms": True, "book_id": book.id,
        "asking_price_paise": 30000, "condition": "GOOD",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    }).json()
    response = api.multipart(
        f"/api/v1/listings/{listing['id']}/photos",
        {"photo": upload(b"not an image at all, just text", name="photo.jpg")},
    )
    # §2.2's table: *400 — malformed or failed validation*, and
    # *`field_errors` is present only on 400*. A file that is not an image is
    # a malformed input, not an illegal state transition, so 400 is the
    # contract's answer and 422 would be the wrong one. Recorded because QA's
    # first draft asserted 422 and the contract corrected it.
    assert response.status_code == 400, response.content[:300]
    assert code(response) == "VALIDATION_FAILED", code(response)
    assert "photo" in response.json()["error"]["field_errors"], (
        "§2.2: a 400 carries `field_errors`, and the field is the one the "
        "student has to fix"
    )


# --------------------------------------------------------------------------
# 7. the restore gap, made concrete
# --------------------------------------------------------------------------


def test_a_photo_row_whose_bytes_are_gone_is_404_and_not_500(api, book, settings):
    """**The backup finding, as the behaviour a student would actually meet.**

    `apps/listings/storage.py` declares it: *"a restore has to carry the media
    directory as well as the database dump — which is `INFRA.md` §3's backup
    scope and is flagged in the slice note, because a tested restore that
    restores the rows and not the photos passes its own test."*

    That is the right flag and it is about S8. **This is the S2 half of it**,
    and it is a defect now: `photo_bytes` wraps `get_photo_for_download` in
    `except ServiceError` and calls `photo_response` **outside** that block.
    `photo_response` raises `NotFound` when `read_object` returns `None`. So
    a row whose file is absent is a **500**, not the 404 the contract gives
    for every other absent photo.

    Backend's `test_a_purged_photo_is_404_rather_than_a_crash` does not reach
    this: a *purged* photo has `storage_key = NULL` and is caught inside the
    try. The uncaught case is `storage_key` present, file absent — which is
    precisely the state a database-only restore produces for **every photo in
    the pilot at once.**
    """
    import os

    from apps.listings.storage import object_path

    listing = api.post("/api/v1/listings", {
        "accept_seller_terms": True, "book_id": book.id,
        "asking_price_paise": 30000, "condition": "GOOD",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    }).json()
    photo = api.multipart(
        f"/api/v1/listings/{listing['id']}/photos", {"photo": upload(jpeg())}
    ).json()

    served = api.get(f"/api/v1/listings/{listing['id']}/photos/{photo['sha256']}")
    assert served.status_code == 200, "baseline: the photo is served before the file goes"

    from apps.listings.models import ListingPhoto

    row = ListingPhoto.all_objects.get(sha256=photo["sha256"])
    os.remove(object_path(row.storage_key))

    after = api.get(f"/api/v1/listings/{listing['id']}/photos/{photo['sha256']}")
    assert after.status_code == 404, (
        "FINDING. A photo row whose file is missing answers "
        f"{after.status_code}, not 404. Every other absent-photo case on this "
        "route is 404 by contract (API-CONTRACT §5.2: *'404, not 403'*; "
        "DATA-MODEL §10.2: *'the row survives its bytes'*). The uncaught "
        "`NotFound` from `photo_response` escapes the handler's `except "
        "ServiceError`, which only wraps the authorisation call.\n\n"
        "Why it is more than a status code: this is the exact state a "
        "**database-only restore** leaves the product in — every row present, "
        "every file gone — so `INFRA.md` §3.3's restore test would restore "
        "cleanly, verify every row, and leave a product that 500s on every "
        "photo URL. A restore test that passes while failing."
    )


def test_the_backup_scope_and_the_restore_test_cover_the_same_things():
    """**QA correcting itself, and the finding is narrower and sharper for it.**

    QA's first draft asserted that `INFRA.md` did not name the media
    directory, citing `apps/listings/storage.py`'s own note that *"a restore
    has to carry the media directory as well as the database dump — which is
    INFRA.md §3's backup scope and is flagged in the slice note."* **That was
    wrong, and the measurement says so.** §3.1 reads:

        pg_dump --format=custom bookhop   →  db-<UTC-ts>.dump
        tar -cz /var/lib/bookhop/media    →  media-<UTC-ts>.tar.gz

    The photos are backed up. `storage.py`'s note is out of date in the
    direction that overstates the gap, and the right move is to delete the
    explanation rather than keep the finding (`CLAUDE.md` rule 9's
    corollary).

    **What is actually missing is one step further on, and HALF of it has
    now been closed.** §3.3 gained a step 5a on 2026-10-22 that sets
    `session_replication_role = 'replica'` and re-runs every append-only
    refusal — which is the right home for the `ENABLE ALWAYS` property QA
    could not verify (F39), for the reason the amendment gives itself:
    *"this test is the one context where we hold superuser legitimately."*
    That half is addressed and this test asserts it stayed.

    **The media half is not.** Every other step acts on the database dump:
    fetch and decrypt, `pg_restore`, `migrate --check`, `verify_audit_chain`,
    the replica-role pass, a read-only assertion set, print RESTORE OK. The
    tarball `§3.1` produces nightly is **opened by nothing.** So the backup
    is whole and the *test* of it is partial — and the sentence §3.3 ends on
    is the standard it misses: *"a restore that has not been tested this
    month is reported as untested, not as working."*

    Paired with the photo test above, the consequence is concrete: restore
    from the dump alone, as §3.3 does, and the product comes up with every
    row intact and every photo gone. That used to be a 500 on every photo
    URL; `57c6689` made it a 404, which is the right status and the same
    lost data.

    S8 and platform-sre own the fix. **S2 is when it has to be written
    down**, because S2 is the slice that created the files and by S8 the
    restore script will be written against a step list that never had them.
    """
    import pathlib
    import re

    infra = pathlib.Path("company/architecture/INFRA.md")
    if not infra.exists():
        pytest.skip(f"NOT VERIFIABLE (slice=S8): {infra} is not in the tree")
    text = infra.read_text(encoding="utf-8")

    backed_up = "media" in text.lower() and "tar -cz" in text
    assert backed_up, (
        "`INFRA.md` §3.1 no longer names the media directory in the nightly "
        "backup. If that changed, the photos are not backed up at all and "
        "this is a bigger finding than the one below."
    )

    restore = text[text.index("### 3.3"):text.index("### 3.4")]

    # The half that landed, asserted so it cannot quietly go away again.
    assert "session_replication_role" in restore, (
        "§3.3's step 5a — the `replica`-role pass that is the only place the "
        "`ENABLE ALWAYS` property on all seven triggers can be verified "
        "(QA-S2 F39) — is gone from the restore test. It was added on "
        "2026-10-22 precisely because this is the one context where we hold "
        "superuser legitimately; nowhere else can check it."
    )

    # NARROWED BY cto 2026-10-22, because this check had stopped being able
    # to fail — and an unrelated edit of mine is what did it.
    #
    # It read `re.search(r"\bmedia\b|tarball|tar -|photo", restore)`. I then
    # added step 6b to §3.3: a curl asserting the `/media/` nginx location is
    # `internal` (A-25 / review finding R-R3). That step is about **access
    # control, not restore**, and it opens no archive — but it contains the
    # words "media" and "photo", so **this test went green and F44 reported
    # as closed while the backup's media half remained as untested as ever.**
    # A live finding was erased by editing the document it reads, for an
    # unrelated reason, and nothing announced it.
    #
    # The word "media" was never the control. **Extracting the archive and
    # resolving a stored file is the control**, so that is what is asked —
    # both halves, because either alone is satisfiable by prose that happens
    # to mention a tarball or a column name.
    extracts = bool(
        re.search(r"\btar\b[^\n]*\s-[a-zA-Z]*x|\bunzip\b|\bzcat\b", restore, re.I)
    )
    resolves = bool(
        re.search(r"storage_key|storage_token|listing_photos\b", restore, re.I)
    )
    covers_media = extracts and resolves
    assert covers_media, (
        "FINDING, the surviving half of F44. `INFRA.md` §3.1 backs up the "
        "media directory as `media-<UTC-ts>.tar.gz` and **§3.3's restore "
        "test never opens it.** Every step acts on the database dump — "
        "including the new 5a, which is a correct addition and is about "
        "triggers, not files. A restore verified by that script restores "
        "every row, passes `verify_audit_chain`, re-proves every append-only "
        "refusal under replica role, prints RESTORE OK — and has not "
        "established that a single photo came back.\n\n"
        "§3.3's own closing sentence is the standard it misses: *'a restore "
        "that has not been tested this month is reported as untested, not as "
        "working.'* The media half has never been tested and is reported as "
        "working.\n\n"
        "The fix is a step 5b — extract the tarball and assert that a sample "
        "of `listing_photos.storage_key` resolves to a file. One line of "
        "script and one assertion, in the same place 5a went. Routed to cto "
        "and platform-sre as an `INFRA.md` §3.3 amendment; not code, and not "
        "S2's to write."
    )


# --------------------------------------------------------------------------
# 8. the unhappy paths — the charter's "where this product's risk lives"
# --------------------------------------------------------------------------


def test_consent_withdrawn_mid_flow_stops_the_next_step_and_keeps_the_draft(
    client_as, seller, book, privacy_notice
):
    """**Consent withdrawn between creating a draft and publishing it.**

    DPDP r.3(c)(i) makes withdrawal as easy as granting, and §2.5 puts
    withdrawal in Stack S so nothing can refuse it. The question this asks is
    the half nobody writes: what happens to work already in progress?

    The contract's answer is derivable. `listing_publication` is a §2.5
    precondition-5 purpose on the publish endpoint, so publish must become
    `403 CONSENT_REQUIRED` naming the purpose. And the draft must **survive**
    — erasure is `POST /account/erase`, not a side effect of withdrawing one
    consent, and a withdrawal that silently destroyed a student's unpublished
    work would be a reason not to withdraw.
    """
    from apps.accounts.services import withdraw_consent

    client = client_as(seller)
    created = client.post(
        "/api/v1/listings",
        data=json.dumps({
            "accept_seller_terms": True, "book_id": book.id,
            "asking_price_paise": 30000, "condition": "GOOD",
            "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
            "language": "en", "category": "PRESCRIBED_TEXTBOOK",
        }),
        content_type="application/json", headers={"Idempotency-Key": key()},
    )
    assert created.status_code == 201, created.content[:300]
    listing = created.json()

    withdraw_consent(seller, "listing_publication", "SETTINGS_TOGGLE", None, "qa")

    blocked = client.post(
        f"/api/v1/listings/{listing['id']}/publish",
        data=json.dumps({"expected_version": listing["version"]}),
        content_type="application/json", headers={"Idempotency-Key": key()},
    )
    assert (blocked.status_code, code(blocked)) == (403, "CONSENT_REQUIRED"), (
        f"§2.5 precondition 5 on a Stack M write; got {blocked.status_code} "
        f"{code(blocked)}: {blocked.content[:200]}"
    )
    assert "listing_publication" in blocked.content.decode(), (
        "§2.5: the body names the missing `purpose_key`, which is the "
        "difference between a student who can fix this and one who cannot"
    )

    from apps.listings.models import Listing

    assert Listing.all_objects.filter(id=listing["id"], status="DRAFT").exists(), (
        "withdrawing one consent destroyed an unpublished draft. Erasure is "
        "`POST /account/erase`; a withdrawal that also deletes work is a "
        "reason not to withdraw, which is what DPDP r.3(c)(i) forbids making it"
    )


def test_suspension_mid_flow_refuses_the_write_and_names_the_open_doors(
    client_as, seller, book
):
    """**Suspended between creating a draft and publishing it.**

    §2.5's closing requirement, which is copy and is also a contract: *"The
    `403 SUSPENDED` body must name what the student can still do — export,
    erase, withdraw consent, reply to their ticket. A suspension that tells
    someone only 'no' is the failure this amendment exists to prevent."*
    """
    client = client_as(seller)
    created = client.post(
        "/api/v1/listings",
        data=json.dumps({
            "accept_seller_terms": True, "book_id": book.id,
            "asking_price_paise": 30000, "condition": "GOOD",
            "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
            "language": "en", "category": "PRESCRIBED_TEXTBOOK",
        }),
        content_type="application/json", headers={"Idempotency-Key": key()},
    ).json()

    seller.status = "SUSPENDED"
    seller.save(update_fields=["status"])

    blocked = client.post(
        f"/api/v1/listings/{created['id']}/publish",
        data=json.dumps({"expected_version": created["version"]}),
        content_type="application/json", headers={"Idempotency-Key": key()},
    )
    assert (blocked.status_code, code(blocked)) == (403, "SUSPENDED"), (
        f"got {blocked.status_code} {code(blocked)}"
    )

    message = blocked.json()["error"]["message"].lower()
    doors = [word for word in ("export", "delete", "erase", "consent", "contact",
                               "help", "ticket") if word in message]
    assert doors, (
        "FINDING. §2.5: *'The 403 SUSPENDED body must name what the student "
        "can still do — export, erase, withdraw consent, reply to their "
        "ticket. A suspension that tells someone only \"no\" is the failure "
        "this amendment exists to prevent, and a response that lists the "
        "open doors costs one sentence.'* The body names none of them: "
        f"{blocked.json()['error']['message']!r}"
    )

    # Stack S is still open to them, which is the other half of the same rule.
    still_open = client.get("/api/v1/account/export")
    assert still_open.status_code == 200, (
        "a suspended student lost their s11 export, which §2.5's amendment "
        f"exists to prevent: {still_open.status_code} {code(still_open)}"
    )


def test_a_tombstoned_seller_cannot_touch_their_listings_and_gets_401_not_403(
    client_as, seller, book
):
    """**The account deleted mid-flow**, S2's reachable form of the charter's
    *"account deleted mid-transfer"*.

    §2.5 Stack S precondition 2 is explicit about the code and the reason:
    **401, not 403** — *"the account is gone"*. A 403 says the caller is
    authenticated and not permitted, which confirms the account still exists.
    """
    client = client_as(seller)
    created = client.post(
        "/api/v1/listings",
        data=json.dumps({
            "accept_seller_terms": True, "book_id": book.id,
            "asking_price_paise": 30000, "condition": "GOOD",
            "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
            "language": "en", "category": "PRESCRIBED_TEXTBOOK",
        }),
        content_type="application/json", headers={"Idempotency-Key": key()},
    ).json()

    seller.status = "TOMBSTONED"
    seller.save(update_fields=["status"])

    for path, body in (
        (f"/api/v1/listings/{created['id']}/publish", {"expected_version": 1}),
        (f"/api/v1/listings/{created['id']}/withdraw", {"expected_version": 1}),
        ("/api/v1/requests", {"free_text_title": "After the end"}),
    ):
        response = client.post(
            path, data=json.dumps(body), content_type="application/json",
            headers={"Idempotency-Key": key()},
        )
        assert (response.status_code, code(response)) == (401, "NOT_AUTHENTICATED"), (
            f"{path}: §2.5 Stack S precondition 2 specifies 401 and says in "
            f"the same line that 403 is the wrong answer; got "
            f"{response.status_code} {code(response)}"
        )
