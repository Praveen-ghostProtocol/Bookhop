"""`Vary` and `Cache-Control` on the HTML pages — Code Review **R-R4**.

The listing page and the photo-upload page both change their body on the
`Save-Data` request header and both sent **no `Vary` and no `Cache-Control`**.
A shared or carrier proxy — a real intermediary on Indian mobile networks,
not a hypothetical — could then cache the image-bearing variant and serve it
to a request that asked for data-saver, or the stripped variant to a student
who wanted the photos. `SYSTEM.md` §4.16 criterion 9 would be defeated **at
the cache**, with every page-level test still green, because every
page-level test looks at a body.

**The property, not the two routes.** The invariant is *any response whose
body depends on a request header declares that header in `Vary`*, and it is
held by `web.views._varying_header`: reading a header through it records the
header, and `_page` turns what was recorded into `Vary`. Two assertions keep
that true rather than one:

* the **behavioural** one, by differential fetch on a page that really does
  change — it proves the recorder reaches the wire, and it would fail if
  `_page` stopped patching;
* the **structural** one, an AST walk asserting that no view reads a request
  header except through the recorder — so a third route added later cannot
  get this wrong silently, whatever header it reads. This is what makes the
  pair property-shaped instead of an enumeration of `Save-Data`.

Neither alone is enough: the first knows only about headers it probes, and
the second knows only about source shape.
"""

import ast
import pathlib

import pytest

from tests.a11y.test_s2_photos import (  # noqa: F401 — fixtures
    STRIP_PAGES,
    listed_with_photos,
    seller_client,
)

pytestmark = pytest.mark.django_db

#: The one place a request header may be read without recording it, and why.
#: `_ip_ua` reads `User-Agent` for the audit record; nothing in any body
#: depends on it, so declaring it in `Vary` would split every cache entry by
#: browser for no gain. Any further entry here is a claim that a header
#: changes nothing a student sees, and must be defended in the same breath.
HEADER_READERS_THAT_NEED_NO_VARY = {"_ip_ua"}

#: The recorder itself.
THE_RECORDER = "_varying_header"


def _probe(client, path):
    """The page with and without the data-saver header."""
    plain = client.get(path)
    saved = client.get(path, headers={"save-data": "on"})
    return plain, saved


@pytest.mark.parametrize("template,why", STRIP_PAGES)
def test_the_probe_really_changes_the_page(seller_client, listed_with_photos, template, why):
    """**The guard on the test below** (`CLAUDE.md` rule 10).

    A `Vary` assertion on a page that does not actually vary is satisfied by
    any page at all, including one with no photos — which is the state
    criterion 9 was already found in once. So the premise is asserted on its
    own, where it fails by name.
    """
    listing, _photos = listed_with_photos
    path = template.format(id=listing.id)
    plain, saved = _probe(seller_client, path)
    assert plain.status_code == saved.status_code == 200, (
        f"{path} ({why}) was not reached: {plain.status_code}/{saved.status_code}"
    )
    assert plain.content != saved.content, (
        f"{path} ({why}) renders the same body with and without "
        "`Save-Data: on`, so the Vary assertion below proves nothing"
    )


@pytest.mark.parametrize("template,why", STRIP_PAGES)
def test_a_body_that_depends_on_a_header_declares_it_in_vary(
    seller_client, listed_with_photos, template, why
):
    """The header that changed the body is named in `Vary`, on both variants.

    On both, deliberately: a proxy caches whichever response it saw first, so
    a `Vary` that appears only on the stripped variant still lets the
    image-bearing one be stored unqualified and replayed to a data-saver
    request.
    """
    listing, _photos = listed_with_photos
    path = template.format(id=listing.id)
    for response in _probe(seller_client, path):
        varies = {
            v.strip().lower()
            for v in response.headers.get("Vary", "").split(",")
            if v.strip()
        }
        assert "save-data" in varies, (
            f"{path} ({why}) varies its body on `Save-Data` but declares "
            f"Vary: {response.headers.get('Vary')!r} — a shared cache may "
            "serve the wrong variant and criterion 9 is defeated at the cache"
        )


def test_no_view_reads_a_request_header_outside_the_one_recorder():
    """**The property.** Every header read goes through `_varying_header`.

    Asking the shape of the source rather than listing the headers we happen
    to know about (rule 11): a route added in S3 that branches on
    `Accept-Encoding`, `Accept-Language` or anything else is caught here
    without this file being edited. The fix when it fires is one call, not an
    exemption.

    # ponytail: AST over `web/views.py` only. Ceiling — a header read in
    # `web/context.py`, `web/forms.py` or a template tag is not seen. No such
    # read exists today; the upgrade path is the same walk over the package,
    # which is a one-line change to `_sources()` below when a second module
    # starts reading the request.
    """
    source = pathlib.Path(__file__).resolve().parents[2] / "web" / "views.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    offenders = []

    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if func.name == THE_RECORDER or func.name in HEADER_READERS_THAT_NEED_NO_VARY:
            continue
        for node in ast.walk(func):
            reads_headers = (
                isinstance(node, ast.Attribute)
                and node.attr == "headers"
                and isinstance(node.value, ast.Name)
                and node.value.id == "request"
            )
            reads_meta = (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value.startswith("HTTP_")
            )
            if reads_headers or reads_meta:
                offenders.append(f"{func.name}() line {node.lineno}")

    assert offenders == [], (
        "these views read a request header directly instead of through "
        f"`{THE_RECORDER}`, so nothing adds it to `Vary` and a shared cache "
        f"may serve the wrong variant: {offenders}"
    )


@pytest.mark.parametrize("template,why", STRIP_PAGES)
def test_a_page_is_never_stored_by_a_shared_cache(
    seller_client, listed_with_photos, template, why
):
    """`Cache-Control` on the page, which is a different decision from the
    one A-25 made on the photo bytes.

    The bytes are content-addressed, so a private cache with a lifetime is
    correct for them. A page has one URL whose content changes underneath it
    — a listing is withdrawn, a seller edits their words, a consent is
    revoked — and it is rendered for one signed-in student. So: never
    `public`, and no lifetime that could outlive a withdrawal.
    """
    listing, _photos = listed_with_photos
    path = template.format(id=listing.id)
    for response in _probe(seller_client, path):
        cc = response.headers.get("Cache-Control", "")
        assert cc, f"{path} ({why}) sends no Cache-Control at all"
        assert "public" not in cc, (
            f"{path} ({why}) permits a shared cache to store a signed-in "
            f"student's page: {cc!r}"
        )
        assert "no-cache" in cc or "no-store" in cc, (
            f"{path} ({why}) may be replayed without revalidation, so a "
            f"withdrawn listing keeps rendering: {cc!r}"
        )
