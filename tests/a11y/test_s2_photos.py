"""The photo strip: it renders, every URL it renders resolves, and the
data-saver criterion is no longer vacuous.

**Why this file exists.** `REDTEAM-S2.md` F48: two photos stored,
EXIF-stripped, authorised and served with `200 image/jpeg`, and **no page a
student is served emitted an `<img>` or named either URL**. The probe that
measured it lives in `tests/redteam/` and is a measurement, not a regression —
it is excluded from the default run and is not edited. This is the
regression, and it asserts at the boundary the contract claims rather than at
the boundary the template chose:

* `API-CONTRACT.md` **A-25** freezes the HTML twin as
  `GET /listing/{id}/photo/{sha256}`. Every `src` and every `href` the strip
  emits is asserted against that spelling and then **fetched**, because a
  rendered `<img>` that 404s passes a template test and fails a student.
* `SYSTEM.md` §4.16 criterion 9 — *"no `<img>` emitted when `Save-Data: on`"*
  — **used to pass because there were no images anywhere** (`A-20` says so in
  as many words). That is `CLAUDE.md` rule 10's second disguise: a
  requirement that cannot be violated. It can be violated now, and both sides
  of the split are rows here: the header suppresses every image **and** the
  priced link appears in their place. Checking only the suppressed side
  passes on a page with no photos.

**The reach assertion, first and separately** (rule 10's fourth disguise).
`tests/a11y/test_s2_pages.py` sweeps `/listing/{id}` using `s2_listing`, which
has **no photos** — so every assertion in this file's subject area was green
on that sweep while the strip did not exist. The fixture here uploads real
photos through the real service, and `test_the_fixture_really_produced_photos`
fails by name if it ever stops doing so.

**What this file does not claim.** It is HTML-level. It does not verify
contrast, focus visibility, target size or the keyboard walkthrough — those
are `harness.NOT_COVERED_BY_THIS_HARNESS` and are unchanged by this slice.
It verifies Tamil nothing: the locale is still gated.
"""

import re
import struct

import pytest

from tests.a11y.harness import check_html

pytestmark = pytest.mark.django_db

#: A-25's frozen spelling. One definition, read by every assertion below
#: rather than re-spelled in each (rule 11).
PHOTO_URL = "/listing/{listing_id}/photo/{sha256}"


def _jpeg(width, height):
    """A structurally valid, metadata-free JPEG of a given intrinsic size.

    Different sizes on purpose: the whole point of the `width`/`height`
    attributes is that they are **this photo's** pixels, and a fixture where
    every image is the same size cannot tell a correct attribute from a
    hard-coded one.
    """
    sof = (
        b"\xff\xc0" + struct.pack(">H", 11) + bytes((8,))
        + struct.pack(">HH", height, width) + bytes((1, 1, 0x11, 0))
    )
    sos = b"\xff\xda" + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0))
    return b"\xff\xd8" + sof + sos + bytes((0, 0)) + b"\xff\xd9"


def _upload(data, name):
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(name, data, content_type="image/jpeg")


#: Four photos, which is the stored maximum and the case the alt text has to
#: survive: a seller photographing one battered textbook from four angles
#: produces four images nobody here has looked at.
PHOTO_SIZES = ((11, 7), (13, 9), (17, 5), (19, 11))


@pytest.fixture
def listed_with_photos(seller, book, settings, tmp_path):
    """A LIVE listing carrying four photos, created only through the service."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from django.utils import timezone

    from apps.listings import services
    from apps.listings.models import Listing

    listing = services.create_listing(
        seller, book=book, asking_price_paise=27500, condition="GOOD",
        annotation_level="LIGHT_PENCIL", damage_flags=["TORN_PAGES"],
        language="en", category="PRESCRIBED_TEXTBOOK",
    )
    photos = [
        services.add_photo(seller, listing, _upload(_jpeg(w, h), f"p{i}.jpg"))
        for i, (w, h) in enumerate(PHOTO_SIZES)
    ]
    listing = services.publish_listing(seller, listing, listing.version)
    if listing.status != "LIVE":
        # `LISTING_REVIEW_ALL` is true at pilot, so publish lands in
        # PENDING_REVIEW. The buyer-facing page is the subject, so the row is
        # moved on directly rather than through a staff fixture.
        Listing.all_objects.filter(id=listing.id).update(
            status="LIVE", published_at=timezone.now()
        )
        listing.refresh_from_db()
    return listing, photos


@pytest.fixture
def seller_client(client_as, seller):
    return client_as(seller)


def _imgs(html):
    """Every `<img>` in the page, as attribute dicts."""
    return [
        dict(re.findall(r'(\w[\w-]*)="([^"]*)"', tag))
        for tag in re.findall(r"<img\b([^>]*)>", html, re.I)
    ]


#: The pages that must carry the strip. `(path template, why)` so a failure
#: names the page in product terms.
STRIP_PAGES = (
    ("/listing/{id}", "the listing page a buyer reads — F48's named subject"),
    ("/sell/{id}/photos", "the seller's own upload step, JOURNEYS J2 step 8"),
)


# --------------------------------------------------------------------------
# the reach assertion, before anything that would be green without it
# --------------------------------------------------------------------------


def test_the_fixture_really_produced_photos(listed_with_photos):
    """**The guard on every other test in this file.**

    If `add_photo` ever stops producing rows — a changed signature, a
    refused fixture image, a storage backend that silently drops — every
    assertion below would sweep an empty list and report green. That is
    exactly how criterion 9 passed for a whole slice. So the condition the
    other tests depend on is asserted by itself, where it fails by name.
    """
    listing, photos = listed_with_photos
    assert len(photos) == len(PHOTO_SIZES), (
        f"the fixture produced {len(photos)} photos, not {len(PHOTO_SIZES)}; "
        "every image assertion in this file is now vacuous"
    )
    assert all(p.sha256 and p.storage_key for p in photos), (
        "a photo row exists with no digest or no stored object, so the URL "
        "the page renders cannot be served"
    )
    assert {(p.width, p.height) for p in photos} == set(PHOTO_SIZES), (
        "the stored intrinsic sizes are not the uploaded ones, so the "
        "width/height assertions below would be comparing a value to itself"
    )


# --------------------------------------------------------------------------
# F48 · the photo reaches a human
# --------------------------------------------------------------------------


@pytest.mark.parametrize("template,why", STRIP_PAGES)
def test_the_page_emits_one_img_per_stored_photo(
    seller_client, listed_with_photos, template, why
):
    """**F48's pass threshold, as Red Team wrote it:** one `<img>` per stored
    photo, on every page that carries the strip."""
    listing, photos = listed_with_photos
    path = template.format(id=listing.id)
    response = seller_client.get(path)
    assert response.status_code == 200, (path, why, response.status_code)

    imgs = _imgs(response.content.decode())
    assert len(imgs) == len(photos), (
        f"{path} ({why}) emitted {len(imgs)} <img> for {len(photos)} stored "
        "photos"
    )
    assert [i["src"] for i in imgs] == [
        PHOTO_URL.format(listing_id=listing.id, sha256=p.sha256) for p in photos
    ], (
        "the strip does not render API-CONTRACT A-25's frozen URL, in stored "
        f"order: {[i['src'] for i in imgs]}"
    )


@pytest.mark.parametrize("template,why", STRIP_PAGES)
def test_every_url_the_page_renders_actually_serves_an_image(
    seller_client, listed_with_photos, template, why
):
    """**The boundary assertion.** A rendered `<img>` that 404s passes a
    template test and fails a student, so every `src` and every thumbnail
    `href` the page emitted is fetched and must come back as image bytes.
    """
    listing, _photos = listed_with_photos
    path = template.format(id=listing.id)
    html = seller_client.get(path).content.decode()

    urls = {i["src"] for i in _imgs(html)}
    urls |= set(re.findall(rf'href="(/listing/{listing.id}/photo/[^"]+)"', html))
    assert urls, f"{path} ({why}) rendered no photo URL at all"

    served = {}
    for url in sorted(urls):
        r = seller_client.get(url)
        served[url] = (r.status_code, r.headers.get("Content-Type"))
    broken = {
        u: v for u, v in served.items()
        if v[0] != 200 or not (v[1] or "").startswith("image/")
    }
    assert broken == {}, (
        f"{path} ({why}) renders URLs that do not serve an image: {broken}"
    )


def test_the_html_twin_is_the_route_the_frozen_amendment_names(listed_with_photos):
    """A-25 by name, independently of what any template happens to emit.

    The URL is frozen, so it is asserted against the URLconf rather than
    inferred from the page — otherwise a template and a route could drift
    together and both tests above would stay green.
    """
    from django.urls import Resolver404, resolve

    listing, photos = listed_with_photos
    path = PHOTO_URL.format(listing_id=listing.id, sha256=photos[0].sha256)
    try:
        match = resolve(path)
    except Resolver404:  # pragma: no cover - the catch-all makes this unreachable
        pytest.fail(f"A-25's HTML twin does not resolve: {path}")
    assert match.url_name == "listing-photo", (
        f"{path} resolves to {match.url_name!r}, so A-25's twin is being "
        "answered by something else — most likely web/urls.py's catch-all 404"
    )


def test_the_photo_route_asks_before_it_serves(seller_client, listed_with_photos):
    """The two refusal paths that belong to **this** layer, exercised rather
    than assumed (rule 10's sixth disguise).

    Who may see which photo is `get_photo_for_download`'s decision and is
    tested in backend's tree; re-deriving its gate semantics here would be a
    second copy of one rule (rule 11). What is asserted here is that L3 does
    not *lose* it — an `<img>` URL is the easiest place in a web app to
    serve bytes without asking anyone — and that a miss is a `404` rather
    than a traceback.
    """
    from django.test import Client

    listing, photos = listed_with_photos
    path = PHOTO_URL.format(listing_id=listing.id, sha256=photos[0].sha256)

    anonymous = Client().get(path)
    assert anonymous.status_code in (301, 302), (
        f"a signed-out request was answered {anonymous.status_code}, not a "
        "redirect to sign-in; the route is serving bytes to anybody"
    )
    assert b"\xff\xd8" not in anonymous.content, "image bytes in the refusal"

    # A well-formed-but-unknown digest, signed in as the owner: the one case
    # where everything else about the request is allowed.
    unknown = seller_client.get(
        PHOTO_URL.format(listing_id=listing.id, sha256="0" * 64)
    )
    assert unknown.status_code == 404, (
        f"an unknown digest was answered {unknown.status_code}; a miss must "
        "read the same as a photo on somebody else's campus (§2.2)"
    )


# --------------------------------------------------------------------------
# the alt text
# --------------------------------------------------------------------------


#: Words that would make the alt text a claim about the image's contents.
#: Not a copy deny-list — `tests/unit/test_forbidden_copy.py` owns that — but
#: the specific failure this string is engineered against: BookHop describing
#: a photo nobody here has looked at, or restating the condition enum as if
#: the picture confirmed it.
CONTENT_CLAIMS = (
    "cover", "page", "spine", "torn", "damaged", "clean", "good", "new",
    "excellent", "condition", "shows", "showing", "picture of", "image of",
)


@pytest.mark.parametrize("template,why", STRIP_PAGES)
def test_the_alt_text_is_positional_and_makes_no_claim_about_the_image(
    seller_client, listed_with_photos, template, why
):
    """**The alt-text decision, asserted as the property it rests on.**

    Four near-identical photos of one battered textbook must produce four alt
    texts that are *all true*. The only sentence with that property says
    where the image came from and which of how many it is — position plus
    provenance, no content. `alt=""` is the other failure: it tells a screen
    reader there is nothing here while four images decide the purchase for
    everyone else.

    So: every alt is non-empty, every alt is distinct (an index, not a
    label), and no alt contains a word that would describe the picture.
    """
    listing, photos = listed_with_photos
    path = template.format(id=listing.id)
    imgs = _imgs(seller_client.get(path).content.decode())

    alts = [i.get("alt") for i in imgs]
    assert all(a for a in alts), (
        f"{path} ({why}) has an image with a missing or empty alt: {alts}. "
        "A photo of a used textbook carries the condition claim the buyer is "
        "judging; it is not decorative."
    )
    assert len(set(alts)) == len(alts), (
        f"{path} ({why}) gives two images the same alt text, so a screen "
        f"reader cannot tell the four apart: {alts}"
    )
    for alt in alts:
        hits = [w for w in CONTENT_CLAIMS if w in alt.lower()]
        assert not hits, (
            f"the alt text {alt!r} describes the contents of a photo nobody "
            f"at BookHop has looked at: {hits}. It must say where the image "
            "came from and which of how many it is, and nothing else."
        )
    # Positional, and the position is the real one: the n-th image says n.
    for i, alt in enumerate(alts, start=1):
        assert str(i) in alt and str(len(photos)) in alt, (
            f"alt {i} of {len(photos)} is {alt!r} and does not carry its own "
            "position, which is the only information it is allowed to carry"
        )


@pytest.mark.parametrize("template,why", STRIP_PAGES)
def test_every_thumbnail_link_says_where_it_goes(
    seller_client, listed_with_photos, template, why
):
    """SC 2.4.4. An `<img>` inside an `<a>` leaves the link's accessible name
    to the alt, and the alt describes the *image*, not the destination. The
    visually-hidden suffix is what makes the link name say the destination —
    so it is asserted, not assumed.
    """
    listing, _photos = listed_with_photos
    html = seller_client.get(template.format(id=listing.id)).content.decode()
    links = re.findall(
        rf'<a href="/listing/{listing.id}/photo/[^"]+">(.*?)</a>', html, re.S
    )
    assert links, f"{template} ({why}) renders no thumbnail link"
    for body in links:
        assert "<img" in body, "a photo link with no image in it"
        assert re.search(r'<span class="vh">[^<]*\S[^<]*</span>', body), (
            "the thumbnail link has no visually-hidden destination text, so "
            f"its accessible name describes the image and not the link: {body!r}"
        )


# --------------------------------------------------------------------------
# criterion 9 · the data-saver gate, no longer vacuous
# --------------------------------------------------------------------------


@pytest.mark.parametrize("template,why", STRIP_PAGES)
def test_save_data_suppresses_every_image_and_names_the_real_cost(
    seller_client, listed_with_photos, template, why
):
    """`SYSTEM.md` §4.16 `disabled` / criterion 9, **both sides as rows.**

    The permitted side alone — "zero images under the header" — is the
    assertion that passed for a whole slice because there were no images at
    all. So the suppression and the replacement are separate asserts, and the
    byte figure is compared against the summed stored sizes rather than
    against whatever the page printed.
    """
    listing, photos = listed_with_photos
    path = template.format(id=listing.id)
    html = seller_client.get(path, headers={"save-data": "on"}).content.decode()

    assert _imgs(html) == [], (
        f"{path} ({why}) emitted images under `Save-Data: on`: "
        f"{[i.get('src') for i in _imgs(html)]}"
    )
    kb = -(-sum(p.bytes for p in photos) // 1024)
    assert f"about {kb} KB" in html, (
        "the data-saver link does not name the real cost summed from the "
        f"stored byte counts ({kb} KB). Page: {html[:400]!r}"
    )
    assert "?photos=1" in html, (
        "there is no way out of the data-saver state, so the student's only "
        "option is to never see the photos"
    )


@pytest.mark.parametrize("template,why", STRIP_PAGES)
def test_the_students_own_opt_in_overrides_their_data_saver_setting(
    seller_client, listed_with_photos, template, why
):
    """The other half of the gate. `?photos=1` is the link the suppressed
    page offers; if it did not work the criterion would be satisfied by a
    page that can never show a photo, which is the vacuous state again with
    an extra click in it.
    """
    listing, photos = listed_with_photos
    path = template.format(id=listing.id)
    html = seller_client.get(
        path + "?photos=1", headers={"save-data": "on"}
    ).content.decode()
    assert len(_imgs(html)) == len(photos), (
        f"{path} ({why}) did not honour the student's explicit opt-in"
    )


def test_a_listing_with_no_photos_cannot_satisfy_the_data_saver_criterion(
    seller_client, s2_listing
):
    """**The guard on the guard.** `s2_listing` has no photos, and it is what
    the sweep in `test_s2_pages.py` uses. If criterion 9 were asserted only as
    "zero images under the header", this page would satisfy it — which is
    precisely how it was reported as passing before the route existed. Pinned
    so a future simplification of the test above cannot quietly restore that.
    """
    html = seller_client.get(
        f"/listing/{s2_listing.id}", headers={"save-data": "on"}
    ).content.decode()
    assert _imgs(html) == []
    assert "about" not in html.lower() or "KB" not in html, (
        "a listing with no photos is offering a data-saver link, so the link "
        "is not driven by stored photos"
    )


# --------------------------------------------------------------------------
# the copy that asserted the absence
# --------------------------------------------------------------------------


def test_no_page_tells_a_student_the_photos_cannot_be_shown(
    seller_client, listed_with_photos
):
    """F48's second half. *"BookHop has no way to show them yet"* was the
    honest sentence while the route did not exist; the route exists, so the
    sentence is the gap. Asserted on the served page, under both header
    states, because a string removed from one branch is still shipped.
    """
    listing, _photos = listed_with_photos
    for template, why in STRIP_PAGES:
        path = template.format(id=listing.id)
        for headers in ({}, {"save-data": "on"}):
            html = seller_client.get(path, headers=headers).content.decode().lower()
            assert "no way to show" not in html, (path, why, headers)


def test_the_absence_copy_is_gone_from_both_catalogues():
    """And out of the `.po` files, where it would otherwise sit as dead copy
    waiting to be re-used — this catalogue has already held shipped sentences
    as empty msgids (`tests/contract/test_copy_catalogue_is_the_shipped_copy.py`),
    so "not rendered anywhere" is not the same as "gone".
    """
    import pathlib

    repo = pathlib.Path(__file__).resolve().parents[2]
    for locale in ("en", "ta"):
        body = (repo / "locale" / locale / "LC_MESSAGES" / "django.po").read_text(
            encoding="utf-8"
        )
        assert "no way to show" not in body, (
            f"locale/{locale} still carries the sentence that says the "
            "photos cannot be shown"
        )
        assert "listing.photos.pending" not in body, (
            f"locale/{locale} still carries the `listing.photos.pending` "
            "context, whose only text was that claim"
        )


def test_the_alt_text_string_is_inside_the_tamil_blocking_gate():
    """`CLAUDE.md` rule 13, first resort, asserted so it cannot be undone by a
    rename. The alt text is a no-warranty string — B2's subject — and a Tamil
    rendering that reads as *"the seller's checked photo"* would warrant in a
    script `test_forbidden_copy.py` cannot read. It is keyed `trust.photo.alt`
    so the `trust.` prefix in `locale/ta/BLOCKING_CLASSES.toml` catches it
    with no edit to that file.
    """
    import pathlib
    import tomllib

    repo = pathlib.Path(__file__).resolve().parents[2]
    classes = tomllib.loads(
        (repo / "locale/ta/BLOCKING_CLASSES.toml").read_text(encoding="utf-8")
    )["classes"]
    prefixes = [k for c in classes.values() for k in c["keys"]]
    assert any("trust.photo.alt".startswith(p) for p in prefixes), (
        "the photo alt text is outside every Tamil blocking class, so an "
        "unreviewed Tamil rendering of it could be served"
    )
    for name in ("listing.html", "sell_photos.html"):
        body = (repo / "templates" / name).read_text(encoding="utf-8")
        assert 'context "listing.photo.alt"' not in body, (
            f"templates/{name} reverted the alt text to a key no blocking "
            "class matches"
        )


# --------------------------------------------------------------------------
# the structural rules, on a page that now has images on it
# --------------------------------------------------------------------------


@pytest.mark.parametrize("template,why", STRIP_PAGES)
def test_the_strip_does_not_break_the_structural_rules(
    seller_client, listed_with_photos, template, why
):
    """The existing sweep runs these rules over a listing with **no photos**,
    so none of them has ever seen an `<img>` on this product. Same rules,
    same harness, a page that has four.
    """
    listing, _photos = listed_with_photos
    path = template.format(id=listing.id)
    response = seller_client.get(path, headers={"accept-language": "en"})
    assert response.status_code == 200, (path, why, response.status_code)
    found = check_html(response.content.decode(), expect_lang="en")
    assert found == [], f"{path} ({why}): {[str(v) for v in found]}"


@pytest.mark.parametrize("template,why", STRIP_PAGES)
def test_every_image_reserves_its_own_box_and_defers_its_own_bytes(
    seller_client, listed_with_photos, template, why
):
    """The 3G half, and it is per-image rather than per-page.

    `width`/`height` are the **stored intrinsic pixels**, which is what lets
    the browser compute the aspect ratio and reserve the right space before a
    byte arrives — a page-level "some image has dimensions" assertion would
    pass with three of four photos reflowing. `loading="lazy"` and
    `decoding="async"` are the other two attributes, and there is no third
    thing: no script, no polyfill, no intersection observer.

    **No `srcset`, and that is asserted too.** `add_photo` stores one
    rendition per row, so a `srcset` could only name widths nobody writes.
    If a resize job ever lands, this assertion is the one to invert.
    """
    listing, photos = listed_with_photos
    by_sha = {p.sha256: p for p in photos}
    path = template.format(id=listing.id)
    imgs = _imgs(seller_client.get(path).content.decode())
    assert imgs, f"{path} ({why}) rendered no image"

    for img in imgs:
        photo = by_sha[img["src"].rsplit("/", 1)[-1]]
        assert img.get("width") == str(photo.width), (img, photo.width)
        assert img.get("height") == str(photo.height), (img, photo.height)
        assert img.get("loading") == "lazy", img
        assert img.get("decoding") == "async", img
        assert "srcset" not in img, (
            "a srcset names widths nothing generates; `add_photo` stores one "
            f"rendition per photo: {img}"
        )


def test_the_page_ships_no_javascript_with_the_strip(
    seller_client, listed_with_photos
):
    """No lightbox, no carousel, no lazy-load polyfill. The full-size view is
    a page navigation to the same URL, which is why there is nothing to
    ship.

    The page already carries exactly one script — the PWA service-worker
    registration from the S1 shell — so the assertion is **that number did
    not change**, not "zero". Asserting zero would have been a test that
    fails on arrival and gets deleted rather than obeyed; asserting the
    existing one by name is what catches a second one appearing.
    """
    listing, _photos = listed_with_photos
    html = seller_client.get(f"/listing/{listing.id}").content.decode()
    scripts = re.findall(r"<script\b[^>]*>", html, re.I)
    assert scripts == ['<script src="/static/js/sw-register.js" defer>'], (
        "the listing page's script tags changed. The photo strip is "
        f"specified as native markup and CSS: {scripts}"
    )
    for handler in ("onclick", "onload", "onerror"):
        assert handler not in html.lower(), f"inline {handler} on the strip"
