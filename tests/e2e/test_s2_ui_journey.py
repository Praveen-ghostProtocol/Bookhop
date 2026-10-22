"""TASKS §2 S2's last done-when: **one real journey end to end through the
actual UI**, driven by a client that was served the pages.

    sign in → find a book by ISBN → set condition, annotations, damage,
    price → upload a photo → publish → see it listed

`test_s2_sell_journey.py` drives L2, which is the JSON API. That is not this
checkbox and must not be reported as it: §4's requirement says *"driven by a
client that was served the pages"*, and the whole reason the requirement
exists is that the four S2 seam defects were invisible to every layer above
the wire.

**So this client reads its field names off the HTML it was served** rather
than from anything a developer knows. That is the property that matters: a
form whose `name=` attributes do not match what the handler reads is a page a
student cannot submit, and no test that posts a hand-written dict can see it.
Measured and recorded here: L3 posts `asking_price_rupees` and
`seller_terms`; L2 takes `asking_price_paise` and `accept_seller_terms`. Two
different vocabularies for one service call, which is correct — a human types
rupees — and is also a money conversion at a trust boundary, so it gets its
own test below.

JavaScript is off, because ADR-001 §2.3 requires every flow to work without
it and the Django test client has none. That is not a limitation of this
file; it is the configuration the contract asks for.
"""

import io
import re
import struct

import pytest

pytestmark = pytest.mark.django_db


def jpeg(width=4, height=3):
    """A JPEG with a GPS-bearing EXIF APP1, so the strip has something to do."""
    payload = b"Exif\x00\x00II*\x00" + struct.pack("<I", 8)
    payload += struct.pack("<H", 1) + struct.pack("<HHII", 0x8825, 4, 1, 26)
    payload += b"\x00\x00\x00\x00"
    return b"".join([
        bytes((0xFF, 0xD8)),
        bytes((0xFF, 0xE1)) + struct.pack(">H", len(payload) + 2) + payload,
        bytes((0xFF, 0xC0)) + struct.pack(">H", 11) + bytes((8,))
        + struct.pack(">HH", height, width) + bytes((1,)) + bytes((1, 0x11, 0)),
        bytes((0xFF, 0xDA)) + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0)),
        bytes((0, 0)) + bytes((0xFF, 0xD9)),
    ])


def form_fields(html, action):
    """The `name=` attributes of the form posting to `action`, read off the page.

    Crude on purpose. A parser would be a dependency, and the thing being
    asserted is that the names the page carries are the names the handler
    reads — which a regex over the served bytes answers exactly as well.
    """
    match = re.search(
        r'<form[^>]*action="' + re.escape(action) + r'"[^>]*>(.*?)</form>',
        html, re.S,
    )
    assert match, f"no form posting to {action!r} on this page"
    return set(re.findall(r'<(?:input|select|textarea)[^>]*name="([^"]+)"',
                          match.group(1)))


def csrf(client):
    cookie = client.cookies.get("csrftoken")
    return cookie.value if cookie else ""


@pytest.fixture
def ui(client_as, seller):
    return client_as(seller)


def test_the_whole_sell_journey_through_the_served_pages(ui, book):
    """**TASKS §2 S2's checkbox, run.** Six steps, each one starting from the
    HTML the previous step produced."""
    from apps.listings.models import Listing

    # J2 step 2 — the seller's own page is reachable and offers the flow.
    sell = ui.get("/sell")
    assert sell.status_code == 200
    assert "/sell/find-book" in sell.content.decode(), (
        "the sell page does not link to the book finder, so the journey has "
        "no first step a student can click"
    )

    # J2 step 4 — find the book by ISBN, using the finder's own form.
    finder = ui.get("/sell/find-book")
    assert "isbn" in form_fields(finder.content.decode(), "/sell/find-book")
    found = ui.get("/sell/find-book", {"isbn": book.isbn13})
    assert found.status_code == 200
    html = found.content.decode()
    assert book.title in html, "the matched book is not shown to the seller"

    # J2 steps 5-7 — the create form, posted with the names the PAGE carries.
    fields = form_fields(html, "/sell")
    assert {"isbn", "condition", "annotation_level", "asking_price_rupees",
            "seller_terms"} <= fields, (
        f"the create form is missing fields J2 names: {sorted(fields)}"
    )
    posted = ui.post("/sell", {
        "isbn": book.isbn13,
        "condition": "GOOD",
        "annotation_level": "LIGHT_PENCIL",
        "damage_flags": ["COVER_DAMAGE"],
        "language": "en",
        "category": "PRESCRIBED_TEXTBOOK",
        "asking_price_rupees": "320",
        "seller_terms": "on",
        "csrfmiddlewaretoken": csrf(ui),
    })
    assert posted.status_code in (200, 302), posted.content[:400]

    listing = Listing.all_objects.order_by("-id").first()
    assert listing is not None, "the form submission created no listing"
    assert listing.asking_price_paise == 32000, (
        f"Rs 320 was stored as {listing.asking_price_paise} paise"
    )
    assert listing.status == "DRAFT", listing.status

    # J2 step 8 — the photo, through the multipart form the page serves.
    photos_page = ui.get(f"/sell/{listing.id}/photos")
    assert photos_page.status_code == 200
    assert "photo" in form_fields(photos_page.content.decode(),
                                  f"/sell/{listing.id}/photos")
    buf = io.BytesIO(jpeg())
    buf.name = "book.jpg"
    uploaded = ui.post(f"/sell/{listing.id}/photos",
                       {"photo": buf, "csrfmiddlewaretoken": csrf(ui)})
    assert uploaded.status_code in (200, 302), uploaded.content[:400]
    assert listing.photos.count() == 1, "the upload form produced no photo row"

    # J2 step 9 — publish, and see it listed.
    listing.refresh_from_db()
    published = ui.post(f"/sell/{listing.id}/publish", {
        "expected_version": listing.version, "csrfmiddlewaretoken": csrf(ui),
    })
    assert published.status_code in (200, 302), published.content[:400]
    listing.refresh_from_db()
    assert listing.status in ("PENDING_REVIEW", "LIVE"), listing.status

    back_on_sell = ui.get("/sell").content.decode()
    assert book.title in back_on_sell, (
        "the published listing is not on the seller's own page, so the last "
        "step of J2 — *see it listed* — does not happen"
    )


def test_the_rupees_field_refuses_a_value_it_cannot_represent(ui, book):
    """**`CLAUDE.md` rule 12 at the UI boundary, which is where it bites.**

    The rule's own words: *"a database proving no float is stored does not
    prove none was passed — it rounds silently, and a rounded money value is
    a wrong value that looks right."* L2 takes integer paise and
    `tests/unit/test_listing_money_column.py` asserts `300.75` is refused
    there.

    **L3 takes rupees from a human**, so the conversion lives in the view and
    this is the only place a student can type `320.755`. The price is
    immutable by trigger, so a seller who gets a price they did not type can
    never correct it — they withdraw and relist. Five shapes a real form
    receives: more decimals than paise can hold, a negative, scientific
    notation, a thousands separator, and nothing at all.
    """
    from apps.listings.models import Listing

    html = ui.get("/sell/find-book", {"isbn": book.isbn13}).content.decode()
    assert "asking_price_rupees" in form_fields(html, "/sell")

    # **The guard that stops this test passing vacuously, and it is not
    # hypothetical: the first draft omitted `damage_flags` and every post
    # 400'd on "Tick what is damaged, or tick No damage to report" — so
    # every assertion below held for a reason that had nothing to do with
    # the price. `CLAUDE.md` rule 10's first disguise, caught by the sibling
    # test failing rather than by this one.
    outcomes = {}
    for typed in ("320.755", "-5", "1e3", "320,00", "", "275"):
        before = Listing.all_objects.count()
        response = ui.post("/sell", {
            "isbn": book.isbn13, "condition": "GOOD",
            "annotation_level": "NONE", "language": "en",
            "category": "PRESCRIBED_TEXTBOOK", "seller_terms": "on",
            "damage_flags": ["NONE_OF_THESE"],
            "asking_price_rupees": typed,
            "csrfmiddlewaretoken": csrf(ui),
        })
        created = Listing.all_objects.count() > before
        stored = (
            Listing.all_objects.order_by("-id").first().asking_price_paise
            if created else None
        )
        outcomes[typed] = (response.status_code, stored)

    # A decimal point is named and refused, which is right and is the
    # control rule 12 asks for. A **comma** is stripped before that check
    # ever runs, so the same intent expressed with the other separator takes
    # the opposite path.
    assert outcomes["320.755"][1] is None, (
        f"a price with paise was stored: {outcomes['320.755']}"
    )
    assert outcomes["320,00"][1] is None, (
        "FINDING. `web/forms.py::clean_asking_price_rupees` names this exact "
        "input in its own docstring — *'the three mistakes a student "
        "actually makes — ₹280, `2,80`, 280.50 — each deserves a different "
        "sentence'* — and then strips commas on the line before the decimal "
        "check, so `2,80` never reaches a sentence. Measured: "
        f"`320,00` was accepted and stored as {outcomes['320,00'][1]} paise, "
        "which is Rs 32,000 for a book the student priced at Rs 320 — a "
        "hundredfold error. "
        "Why it is not cosmetic: `asking_price_paise` is immutable by "
        "trigger (ADR-003 §2.2), so the seller cannot correct it. They must "
        "withdraw and relist, and in the meantime the listing carries a "
        "price they did not set. `320.00` is refused with a clear sentence "
        "and `320,00` is not, which is the asymmetry — the same intent, two "
        "separators, opposite outcomes. "
        "Note the comma strip is also what makes `1,200` work, which is the "
        "Indian grouping a student really does type. So the fix is not "
        "'stop stripping commas': it is to refuse a comma that is not in a "
        "valid grouping position, which is the distinction the docstring "
        f"already draws. All outcomes: {outcomes}"
    )
    assert outcomes["-5"][1] is None, f"a negative price was stored: {outcomes['-5']}"
    assert outcomes[""][1] is None, f"an empty price was stored: {outcomes['']}"
    assert outcomes["275"][1] == 27500, (
        "A VALID price was not accepted, so every refusal above is a refusal "
        "of the form rather than of the price and this test asserts nothing: "
        f"{outcomes}"
    )


def test_the_listing_page_shows_no_contact_detail_in_the_rendered_html(ui, book, seller):
    """API-CONTRACT §5.2's rule, asserted on the **page** rather than on the
    payload.

    §5.2 says a contract test asserts this *"against the response schema, not
    just the database"*. `tests/contract/test_response_boundary.py` does that
    for the JSON. A template can reach `listing.seller.email` without the
    serialiser being involved at all, which is the layer the deny-list cannot
    see — so the rendered bytes are checked too.
    """
    from apps.listings.models import Listing

    ui.get("/sell/find-book", {"isbn": book.isbn13})  # mints the CSRF cookie
    created = ui.post("/sell", {
        "isbn": book.isbn13, "condition": "GOOD", "annotation_level": "NONE",
        "damage_flags": ["NONE_OF_THESE"], "language": "en",
        "category": "PRESCRIBED_TEXTBOOK", "asking_price_rupees": "300",
        "seller_terms": "on", "csrfmiddlewaretoken": csrf(ui),
    })
    assert created.status_code in (200, 302), created.content[:300]
    listing = Listing.all_objects.order_by("-id").first()
    assert listing is not None, "the create form produced no listing"
    html = ui.get(f"/listing/{listing.id}").content.decode()

    assert seller.email not in html, "the seller's email address is on the page"
    for forbidden in ("@example.ac.in", "whatsapp", "settled price"):
        assert forbidden.lower() not in html.lower(), (
            f"the listing page contains {forbidden!r}. §5.2: *'listing "
            "responses never contain a seller address, a phone number, an "
            "email, precise coordinates, a settled price'*."
        )


# --------------------------------------------------------------------------
# A-22's two consequences at the interface, both sides of each
# --------------------------------------------------------------------------


def test_publishing_onto_a_closed_campus_says_nobody_can_see_it(ui, book):
    """**A-22's required disclosure, asserted as a control that exists AND
    behaves** (`CLAUDE.md` rule 9).

    The ruling that made the pre-gate write legal created a new way to
    mislead somebody: a student does the whole sell flow, publishes, and
    nothing happens, because the campus is closed. A-22 routed *"a required
    disclosure string"* to design rather than leaving that as acceptable.

    So the test is not *"a flash message appears"* — it is that the sentence
    the seller is shown at the moment of publishing **says the listing is
    not visible**. A confirmation that merely said "Published" would satisfy
    a weaker test and be the defect.
    """
    from apps.listings.models import Listing

    ui.get("/sell/find-book", {"isbn": book.isbn13})
    ui.post("/sell", {
        "isbn": book.isbn13, "condition": "GOOD", "annotation_level": "NONE",
        "damage_flags": ["NONE_OF_THESE"], "language": "en",
        "category": "PRESCRIBED_TEXTBOOK", "asking_price_rupees": "300",
        "seller_terms": "on", "csrfmiddlewaretoken": csrf(ui),
    })
    listing = Listing.all_objects.order_by("-id").first()
    assert listing.campus.discovery_enabled_at is None, (
        "this test is about publishing onto a CLOSED campus"
    )

    published = ui.post(f"/sell/{listing.id}/publish", {
        "expected_version": listing.version, "csrfmiddlewaretoken": csrf(ui),
    }, follow=True)
    assert published.status_code == 200, published.content[:300]
    html = published.content.decode().lower()

    assert "nobody can see this yet" in html, (
        "A-22 requires a disclosure at publish on a closed campus, and the "
        "seller was not given one. The whole basis for permitting the "
        "pre-gate write is that nothing browsable is produced; a seller who "
        "is not told that has been allowed to do work they think has "
        f"landed.\n\n{published.content[:600]}"
    )
    assert "one campus at a time" in html, (
        "the disclosure no longer carries the mechanism clause. Without it "
        "the sentence reads as a fault rather than as how the product works."
    )
    for promise in ("soon", "shortly", "will open", "launching", "next week"):
        assert promise not in html, (
            f"the disclosure contains {promise!r}, which is an undertaking "
            "that the campus will open. COPY-DECK v1.5: the string names no "
            "date, because we do not have one."
        )


def test_a_listing_on_a_closed_campus_is_never_shown_as_stale(
    client_as, seller, book, s2_listing
):
    """**The defect frontend found that QA's tests could not have**, and the
    time-shifted fixture that pins it.

    The stale notice — *"Listed 40 days ago — this may be gone"* — was
    counting from `published_at`. Because A-22 lets a seller publish onto a
    closed campus, a listing can sit at `LIVE` with `published_at` set and
    nobody able to see it. **On the morning a campus finally opened, its
    entire backlog would have greeted the first buyer with a staleness
    warning** — wrong in both halves, since it had not been *listed* in the
    sense a student reads it, and nothing *may be gone* from a listing
    nobody could take.

    The clock is now elapsed **visible** time: the later of publication and
    the campus opening. Both sides are asserted, because a clock that simply
    never fires would also pass the first half.
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.listings.models import Listing

    old = timezone.now() - timedelta(days=40)
    Listing.all_objects.filter(id=s2_listing.id).update(
        status="LIVE", published_at=old
    )
    s2_listing.refresh_from_db()
    assert s2_listing.campus.discovery_enabled_at is None

    client = client_as(seller)
    html = client.get(f"/listing/{s2_listing.id}").content.decode()
    assert "this may be gone" not in html.lower(), (
        "a listing published 40 days ago onto a campus whose gate has never "
        "opened is shown as stale. It has been visible for no time at all, "
        "which is exactly what the clock should read."
    )
    assert "40 days ago" not in html.lower(), (
        "the page quotes 40 days of visibility for a listing nobody could "
        "see"
    )


def test_a_listing_visible_for_long_enough_IS_shown_as_stale(
    client_as, seller, book, s2_listing, open_the_gate
):
    """**The other side**, so the fix is not a clock that never fires.

    `CLAUDE.md` rule 10: a check that cannot fail is worse than no check. A
    staleness notice suppressed everywhere would pass the test above and
    silently remove a control `COMPETITORS.md` §3.5 calls the category's
    oldest failure mode.
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.listings.models import Listing

    campus = open_the_gate(s2_listing.campus)
    old = timezone.now() - timedelta(days=40)
    Listing.all_objects.filter(id=s2_listing.id).update(
        status="LIVE", published_at=old
    )
    # The campus opened long ago too, so visible time really is 40 days.
    from apps.core.models import Campus

    Campus.objects.filter(id=campus.id).update(discovery_enabled_at=old)
    s2_listing.refresh_from_db()

    html = client_as(seller).get(f"/listing/{s2_listing.id}").content.decode()
    assert "this may be gone" in html.lower(), (
        "a listing visible for 40 days on an open campus is NOT shown as "
        "stale, so the staleness control does not fire at all and the test "
        "above was passing for the wrong reason"
    )
