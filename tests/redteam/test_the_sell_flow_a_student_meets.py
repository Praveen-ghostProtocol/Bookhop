"""RED TEAM PROBE · S2 per-slice pass. **Not a regression test.**

Subject: *"whether the listing flow is something a student would actually
complete on a mid-range Android"*, and the standing target *competition from
free channels already working*.

The benchmark is not an abstraction. `COMPETITORS.md` / `company/README.md`
§1 name the two things this flow is measured against: the campus-gate
photocopy, and posting a photo to the batch WhatsApp group. Posting to
WhatsApp is **one** action with **zero** required fields.

`sell_find.html` itself claims the cost: *"It takes about two minutes: the
ISBN from the back of the book, what's wrong with it, and your price."*
This probe counts what the form actually demands.
"""

import re

import pytest

pytestmark = pytest.mark.django_db


def _form_page(rt_client_as, seller, book):
    client = rt_client_as(seller)
    response = client.get(f"/sell/find-book?isbn={book.isbn13}")
    assert response.status_code == 200, response.status_code
    return client, response.content.decode("utf-8", "replace")


def test_the_intake_form_demands_more_than_the_screen_promises(
    rt_client_as, seller, book
):
    """**Counted, not estimated.** Every control the student must operate.

    The page says *"the ISBN, what's wrong with it, and your price"* — three
    things. The threshold below is deliberately generous: more than eight
    required decisions on one screen for a Rs 275 item is a claim worth
    testing against a real student, not a defect to fix in code.
    """
    _, html = _form_page(rt_client_as, seller, book)

    radios = re.findall(r'type="radio"[^>]*name="([^"]+)"', html)
    checkboxes = re.findall(r'type="checkbox"[^>]*name="([^"]+)"', html)
    text_inputs = re.findall(
        r'<input(?![^>]*type="(?:radio|checkbox|hidden)")[^>]*name="([^"]+)"', html
    )

    decisions = {
        "radio groups": sorted(set(radios)),
        "checkbox groups": sorted(set(checkboxes)),
        "typed fields": sorted(set(text_inputs)),
        "individual radio options": len(radios),
        "individual checkboxes": len(checkboxes),
    }
    controls = (
        len(set(radios)) + len(set(checkboxes)) + len(set(text_inputs))
    )
    taps = len(radios) + len(checkboxes) + len(set(text_inputs))

    assert controls <= 4, (
        f"FINDING (for product, not for code). The intake screen presents "
        f"{controls} required decision groups across {taps} individual "
        f"controls, against copy promising three things and a WhatsApp "
        f"alternative that requires none: {decisions}"
    )


def test_the_whole_sell_journey_is_four_round_trips_before_anyone_can_see_it(
    rt_client_as, seller, book, settings, tmp_path
):
    """Counted over real HTTP. Each round trip is a 3G page load.

    Recorded as a number rather than graded: the comparison is the WhatsApp
    post, and that is one.
    """
    settings.MEDIA_ROOT = str(tmp_path / "media")
    client = rt_client_as(seller)
    trips = []

    trips.append(("GET /sell", client.get("/sell").status_code))
    trips.append(
        ("GET /sell/find-book", client.get(f"/sell/find-book?isbn={book.isbn13}").status_code)
    )
    created = client.post("/sell", data={
        "isbn": book.isbn13,
        "asking_price_rupees": "275", "condition": "GOOD",
        "annotation_level": "NONE", "damage_flags": ["NONE_OF_THESE"],
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
        "seller_terms": "on",
    })
    trips.append(("POST /sell", created.status_code))

    from apps.listings.models import Listing
    listing = Listing.all_objects.order_by("-id").first()
    assert listing is not None, f"the form did not create a listing: {created.status_code}"

    trips.append(
        ("GET /sell/{id}/photos", client.get(f"/sell/{listing.id}/photos").status_code)
    )
    published = client.post(f"/sell/{listing.id}/publish", data={
        "expected_version": str(listing.version)
    })
    trips.append(("POST /sell/{id}/publish", published.status_code))

    listing.refresh_from_db()
    assert len(trips) <= 2, (
        f"FINDING (for product). {len(trips)} round trips from 'I have a book' "
        f"to a row that is not even visible yet — it lands at "
        f"{listing.status!r}, awaiting a human. Trips: {trips}"
    )


def test_what_the_seller_is_told_at_the_end_of_all_that(
    rt_client_as, seller, book, settings, tmp_path
):
    """**Expected to pass, and it is the slice's best work.** The disclosure
    is honest and carries no promise of a date.

    Kept as a row so the findings above are not read as "the flow is bad".
    The flow is long; what it *says* is accurate, which is rarer.
    """
    settings.MEDIA_ROOT = str(tmp_path / "media")
    client = rt_client_as(seller)
    client.get(f"/sell/find-book?isbn={book.isbn13}")
    client.post("/sell", data={
        "isbn": book.isbn13,
        "asking_price_rupees": "275", "condition": "GOOD",
        "annotation_level": "NONE", "damage_flags": ["NONE_OF_THESE"],
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
        "seller_terms": "on",
    })
    from apps.listings.models import Listing
    listing = Listing.all_objects.order_by("-id").first()
    client.post(f"/sell/{listing.id}/publish",
                data={"expected_version": str(listing.version)})

    html = client.get("/sell").content.decode("utf-8", "replace")
    lowered = html.lower()
    assert "nobody can see this yet" in lowered, html[:400]
    for promise in ("soon", "shortly", "will open", "launching", "next week"):
        assert promise not in lowered, f"the disclosure now promises {promise!r}"
