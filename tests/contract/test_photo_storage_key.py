r"""F51/F52 regression — the on-disk path is not printed on the door.

`add_photo` built `listings/{id}/{sha256[:32]}.{fmt}` while `listing_payload`
publishes both the id and the full `sha256`, so any authorised reader could
compute the exact path of the file and hand it to anyone. API-CONTRACT A-25
corrects it: *"The stored filename gains a component that appears in **no**
response — a per-photo random token, stored on the row. The URL keeps the
`sha256`; the disk does not."*

**Written at the boundary A-25 claims**, which is two boundaries and they are
asserted separately: the **response** must not contain the component, and the
**key** must not be computable from what the response does contain. A test of
only the first would pass against a key derived from the id and the sha256
with a fixed salt.

**The migration half is here too**, because the caller's instruction and
F46's open finding make it part of this change: `listings/0003` cannot be
reversed on SQLite, and a second migration that could not would compound it.
`test_the_migration_reverses_on_this_engine` runs the reverse on whichever
engine the suite is on (skipping, with the cause named, if F46's own test has
already left the table unmigratable), and `test_the_composite_foreign_key_survived_0004`
asserts the thing a naive `AddField` would have silently destroyed.
"""

import io
import struct

import pytest
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction

pytestmark = pytest.mark.django_db


def _jpeg(width=12, height=9):
    return b"".join([
        b"\xff\xd8",
        b"\xff\xc0" + struct.pack(">H", 11) + bytes((8,))
        + struct.pack(">HH", height, width) + bytes((1, 1, 0x11, 0)),
        b"\xff\xda" + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0)),
        b"\x10\x20\x30\xff\xd9",
    ])


@pytest.fixture
def second_student(db, signup_campus, privacy_notice):
    """**A real student, not a seed one**, owning nothing on this campus.

    `is_seed=False` on purpose: ADR-002 §4.1(c) serves a seed row on a closed
    campus, so a seed second actor would be refused for a reason that has
    nothing to do with ownership and the assertion would measure the gate
    instead of the authorisation.
    """
    from apps.accounts.models import User
    from apps.accounts.services import grant_consent

    user = User.objects.create(
        email="arjun@example.ac.in", display_name="Arjun K",
        campus=signup_campus, city_id=signup_campus.city_id,
        status="PENDING_VERIFICATION", adult_verified=True, campus_verified=True,
        is_seed=False,
    )
    grant_consent(user, "account", privacy_notice, "SIGNUP_FORM", None, "pytest")
    user.refresh_from_db()
    return user


@pytest.fixture
def photo_on_a_live_listing(seller, book, settings, tmp_path):
    """A listing with one photo. **Read by its own seller**, which
    `get_photo_for_download` permits regardless of the discovery gate — the
    gate is a discovery control and a seller reading their own draft is not
    discovery (ADR-002 §4)."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.listings import services

    listing = services.create_listing(
        seller, book=book, asking_price_paise=27500, condition="GOOD",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    buf = io.BytesIO(_jpeg())
    buf.name = "p.jpg"
    photo = services.add_photo(seller, listing, buf)
    return listing, photo


# --- the key ---------------------------------------------------------------


def test_the_key_is_not_computable_from_the_published_fields(
    client_as, seller, photo_on_a_live_listing
):
    """**The finding, inverted.** Every field the response publishes, tried.

    Not just the one spelling the defect used: the id and the `sha256` are
    the whole of what a reader has, so any arrangement of them must miss.
    """
    listing, photo = photo_on_a_live_listing
    body = client_as(seller).get(f"/api/v1/listings/{listing.id}").json()
    published = body["photos"][0]["sha256"]
    assert published == photo.sha256, "the URL still content-addresses"

    for candidate in (
        f"listings/{listing.id}/{published[:32]}.jpeg",
        f"listings/{listing.id}/{published}.jpeg",
        f"listings/{listing.id}/{published[:16]}.jpeg",
        f"listings/{listing.id}/{listing.id}.jpeg",
    ):
        assert candidate != photo.storage_key, (
            f"the on-disk path is still derivable as {candidate!r}"
        )


def test_the_token_is_on_the_row_in_the_key_and_in_no_response(
    client_as, seller, photo_on_a_live_listing
):
    """A-25's three clauses, each as its own assertion.

    The response is searched as **raw text**, not key by key: the clause says
    the component appears in no response, and a key-by-key check is the exact
    shape of control that let F49 through one field over.
    """
    listing, photo = photo_on_a_live_listing
    assert photo.storage_token, "the row carries the component"
    assert len(photo.storage_token) == 32
    assert photo.storage_token in photo.storage_key, "the disk uses it"

    client = client_as(seller)
    for path in (
        f"/api/v1/listings/{listing.id}",
        "/api/v1/listings/mine",
    ):
        text = client.get(path).content.decode()
        assert photo.storage_token not in text, f"{path} leaks the component"
        assert photo.storage_key not in text, f"{path} leaks the whole key"


def test_two_photos_of_different_books_get_unrelated_keys(
    seller, book, settings, tmp_path
):
    """**The random half.** A per-photo token must differ per photo, or it is
    a salt and the path is derivable again for anyone who learns it once.
    """
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.listings import services

    listing = services.create_listing(
        seller, book=book, asking_price_paise=27500, condition="GOOD",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    tokens = set()
    for index in range(3):
        buf = io.BytesIO(_jpeg(12 + index, 9))
        buf.name = f"p{index}.jpg"
        tokens.add(services.add_photo(seller, listing, buf).storage_token)
    assert len(tokens) == 3


# --- the route -------------------------------------------------------------


def test_the_route_serves_the_bytes_with_the_frozen_cache_header(
    client_as, seller, photo_on_a_live_listing
):
    """F52: the route shipped `max-age=3600` against a frozen `86400`."""
    listing, photo = photo_on_a_live_listing
    response = client_as(seller).get(
        f"/api/v1/listings/{listing.id}/photos/{photo.sha256}"
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "image/jpeg"
    assert response["Cache-Control"] == "private, max-age=86400"
    assert response["X-Robots-Tag"] == "noindex"
    assert response["X-Content-Type-Options"] == "nosniff"


def test_the_route_still_refuses_someone_it_should(
    client_as, second_student, photo_on_a_live_listing
):
    """**The other side.** An underivable filename is the second layer; the
    Django authorisation decision is the first, and A-25 is explicit that
    this change does not replace it. If the route started serving everyone,
    every assertion above would still pass."""
    listing, photo = photo_on_a_live_listing
    response = client_as(second_student).get(
        f"/api/v1/listings/{listing.id}/photos/{photo.sha256}"
    )
    assert response.status_code in (403, 404)


# --- the remedy that moved -------------------------------------------------


def test_the_same_photo_twice_is_still_refused_by_the_service(
    seller, book, settings, tmp_path
):
    """The diagnosis. It used to rest on `storage_key` being UNIQUE and
    content-addressed, which a random token removes."""
    from apps.core.errors import ValidationFailed
    from apps.listings import services

    settings.MEDIA_ROOT = str(tmp_path / "media")
    listing = services.create_listing(
        seller, book=book, asking_price_paise=27500, condition="GOOD",
        annotation_level="NONE", damage_flags=[], language="en",
        category="PRESCRIBED_TEXTBOOK", no_damage=True,
    )
    first = io.BytesIO(_jpeg())
    first.name = "p.jpg"
    services.add_photo(seller, listing, first)
    again = io.BytesIO(_jpeg())
    again.name = "p-again.jpg"
    with pytest.raises(ValidationFailed, match="already on this listing"):
        services.add_photo(seller, listing, again)


def test_the_database_refuses_it_too_whatever_the_service_does(
    seller, photo_on_a_live_listing
):
    """**The guarantee, where the service check is the diagnosis.**

    `CLAUDE.md` rule 12: never remove a remedy before its replacement is
    green. The old remedy was a UNIQUE on `storage_key`; the new one is
    `listing_photos_one_copy_per_listing`, and it is asserted by *behaviour*
    — a direct insert that bypasses `add_photo` entirely — because a test
    that the constraint is declared is a test of the model file.
    """
    listing, photo = photo_on_a_live_listing
    from apps.listings.models import ListingPhoto

    with pytest.raises(IntegrityError), transaction.atomic():
        ListingPhoto.all_objects.create(
            listing=listing,
            campus_id=listing.campus_id,
            city_id=listing.city_id,
            is_seed=listing.is_seed,
            storage_key="listings/x/handwritten.jpeg",
            storage_token="handwritten",
            sha256=photo.sha256,
            width=1, height=1, bytes=1,
            exif_stripped_at=photo.exif_stripped_at,
        )


def test_the_same_photo_on_a_different_listing_is_allowed(
    seller, book, settings, tmp_path
):
    """The permitted side of the same rule. The constraint is *per listing*;
    two sellers — or one seller with two copies of a textbook — photographing
    the same page must both be able to."""
    from apps.listings import services

    settings.MEDIA_ROOT = str(tmp_path / "media")
    made = []
    for _ in range(2):
        listing = services.create_listing(
            seller, book=book, asking_price_paise=27500, condition="GOOD",
            annotation_level="NONE", damage_flags=[], language="en",
            category="PRESCRIBED_TEXTBOOK", no_damage=True,
        )
        buf = io.BytesIO(_jpeg())
        buf.name = "p.jpg"
        made.append(services.add_photo(seller, listing, buf))
    assert made[0].sha256 == made[1].sha256
    assert made[0].storage_key != made[1].storage_key


# --- the migration ---------------------------------------------------------


def _listing_photos_controls():
    """What must still be true of `listing_photos` after 0004, per engine.

    **No skip and no `information_schema`** (ADR-003 §2.3 W4): the composite
    FK is read out of each engine's own catalog, because a guard test that
    runs on one engine is a prediction about the other.
    """
    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' "
                "AND name='listing_photos'"
            )
            sql = (cursor.fetchone() or [""])[0] or ""
            cursor.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='index' "
                "AND name='listing_photos_one_copy_per_listing'"
            )
            # **One condition, not three OR'd together.** The spliced clause
            # is unnamed on SQLite — `0003` inserts it into the `CREATE
            # TABLE` text — so matching on the constraint *name* would be a
            # condition that can never be true, and OR-ing it beside a loose
            # one is how a check passes for a reason nobody checked
            # (`CLAUDE.md` rule 10). This is the exact tuple `0003` writes.
            return {
                "composite_fk": (
                    'FOREIGN KEY ("listing_id", "campus_id", "city_id", "is_seed") '
                    'REFERENCES "listings" ("id", "campus_id", "city_id", "is_seed")'
                ) in sql,
                "one_copy_index": bool(cursor.fetchone()[0]),
            }
        cursor.execute(
            "SELECT count(*) FROM pg_constraint "
            "WHERE conname = 'listing_photos_parent_tenant_fk'"
        )
        composite = bool(cursor.fetchone()[0])
        cursor.execute(
            "SELECT count(*) FROM pg_class "
            "WHERE relname = 'listing_photos_one_copy_per_listing'"
        )
        return {"composite_fk": composite, "one_copy_index": bool(cursor.fetchone()[0])}


def test_the_composite_foreign_key_survived_0004(engine):
    """**The thing a plain `AddField` would have destroyed, on SQLite only.**

    Django's SQLite backend implements `AddField` and `AddConstraint` by
    rebuilding the table from *model state*, and `listings/0003` installed
    `listing_photos_parent_tenant_fk` with raw SQL that model state has never
    heard of. So the rebuild would have dropped it — silently, on the
    development engine only, re-opening F32 (a photo row whose `is_seed`
    disagreed with its listing's, served on a closed campus).

    `engine` is requested so this runs and is attributed on both engines
    rather than being a PostgreSQL claim about SQLite.
    """
    controls = _listing_photos_controls()
    assert controls["composite_fk"], (
        "listing_photos lost its parent-tenant composite foreign key — "
        f"on {connection.vendor}, after listings/0004"
    )
    assert controls["one_copy_index"], "the duplicate-photo guarantee is missing"


def test_a_photo_row_still_cannot_disagree_with_its_listing(
    engine, photo_on_a_live_listing
):
    """**The behaviour limb.** The catalog read above diagnoses — it fails by
    name, so a missing guard is identifiable. This one guarantees, and it
    fails however the property is lost: a dropped constraint, a rebuilt
    table, a migration that reinstated the column list and not the clause.

    F32 in one line: a `listing_photos` row whose `is_seed` disagreed with
    its listing's was **served, 200, with real bytes**, to a non-owner on a
    campus whose gate was closed.
    """
    listing, photo = photo_on_a_live_listing
    from apps.listings.models import ListingPhoto

    with pytest.raises(IntegrityError), transaction.atomic():
        ListingPhoto.all_objects.create(
            listing=listing,
            campus_id=listing.campus_id,
            city_id=listing.city_id,
            is_seed=not listing.is_seed,
            storage_key="listings/x/liar.jpeg",
            storage_token="liar",
            sha256="0" * 64,
            width=1, height=1, bytes=1,
            exif_stripped_at=photo.exif_stripped_at,
        )


def _schema_is_migratable():
    """`None` if `listing_photos` can still take a schema change, else why not.

    **This exists because of F46's blast radius, which is wider than F46
    says.** `tests/contract/test_tenant_fk_migration.py::
    test_the_migration_round_trips_forward_reverse_forward` reverses
    `listings/0003` on SQLite, which fails halfway, and its recovery
    (`migrate listings 0002 --fake` then a real forward) leaves
    `listing_photos` carrying a composite FK that **`PRAGMA
    foreign_key_check` rejects** — so every later `ALTER TABLE` on that table
    dies in Django's SQLite schema editor with `foreign key mismatch`. F46
    reports that the reverse fails; it does not report that the table is
    left unmigratable afterwards. *(Measured here, 2026-10-22, backend.)*

    This file is named to sort before `test_tenant_fk_migration.py` so the
    round trip below runs on an undamaged schema. The guard is here anyway,
    because an ordering dependency that is not asserted is an ordering
    dependency that breaks silently — and `CLAUDE.md` rule 10 wants a skip
    that names the cause, never a pass.
    """
    if connection.vendor != "sqlite":
        return None
    try:
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_key_check")
            cursor.fetchall()
    except Exception as exc:  # noqa: BLE001 - any failure is the condition
        return f"{type(exc).__name__}: {exc}"
    return None


@pytest.mark.django_db(transaction=True)
def test_the_migration_reverses_on_this_engine():
    """F46 says `listings/0003` cannot be reversed on SQLite. **0004 can.**

    `INFRA.md` §4's rollback runs the reverse, so a migration whose reverse
    has never been executed is half a migration. The schema is restored in a
    `finally` whatever happens: a half-migrated database would follow this
    test into every test after it, which is how a round-trip test becomes
    the defect it was written to find.
    """
    damage = _schema_is_migratable()
    if damage is not None:
        pytest.skip(
            f"NOT VERIFIABLE IN THIS RUN (engine={connection.vendor}, slice=S2): "
            "`listing_photos` cannot take a schema change because a prior test "
            "left it with a foreign key SQLite rejects — REDTEAM-S2 F46, still "
            f"open. Run this file alone to verify the round trip. ({damage})"
        )

    before = _listing_photos_controls()
    assert before["composite_fk"] and before["one_copy_index"], (
        f"the forward state is already wrong, so a round trip proves nothing: {before}"
    )

    error = None
    try:
        try:
            call_command("migrate", "listings", "0003", verbosity=0)
        except Exception as exc:  # noqa: BLE001 - the outcome is the datum
            error = exc
        else:
            reversed_state = _listing_photos_controls()
            assert not reversed_state["one_copy_index"], (
                "the reverse left its index behind, which is the shape of "
                "F46: a migration that reports as rolled back and is not"
            )
            assert reversed_state["composite_fk"], (
                "the reverse took `listings/0003`'s composite FK with it"
            )
    finally:
        call_command("migrate", "listings", "0004", verbosity=0)

    assert _listing_photos_controls() == before, (
        "the second forward did not restore what the first one installed"
    )
    assert error is None, (
        "`listings/0004` cannot be reversed on "
        f"{connection.vendor}: {type(error).__name__}: {str(error)[:200]}"
    )


def test_the_backfill_renames_an_existing_object_and_reverses_it(
    photo_on_a_live_listing,
):
    """**The branch that an empty test database never runs.**

    `migrate` on a fresh database applies 0004 with no rows, so the loop that
    renames every already-uploaded photo executes zero times and the suite
    would report the migration as covered. That is `CLAUDE.md` rule 10's
    "check that has not started": from outside, *"ran against nothing"* and
    *"ran correctly"* are indistinguishable.

    So both functions are called directly against a row that exists and a
    file that is on disk. `django.apps` stands in for the historical registry
    — sound here because 0004 changes no field this code reads.
    """
    import importlib

    from django.apps import apps as live_apps

    from apps.listings.models import ListingPhoto
    from apps.listings.storage import object_path, read_object

    migration = importlib.import_module(
        "apps.listings.migrations.0004_photo_storage_token"
    )
    listing, photo = photo_on_a_live_listing
    original = read_object(photo.storage_key)
    assert original, "the fixture must have written a file for this to mean anything"

    # Put the row and the file back into the pre-A-25 shape the backfill is
    # written for: a derivable key and no token.
    derivable = f"listings/{listing.id}/{photo.sha256[:32]}.jpeg"
    object_path(photo.storage_key).replace(object_path(derivable))
    ListingPhoto.all_objects.filter(id=photo.id).update(
        storage_key=derivable, storage_token=None
    )

    migration.forward(live_apps, None)

    photo.refresh_from_db()
    assert photo.storage_token, "the backfill left a row without the component"
    assert photo.storage_key != derivable
    assert photo.storage_token in photo.storage_key
    assert read_object(photo.storage_key) == original, "the bytes moved with the row"
    assert not object_path(derivable).exists(), "the derivable path still resolves"

    migration.reverse(live_apps, None)

    photo.refresh_from_db()
    assert photo.storage_key == derivable, "the reverse is a real reverse"
    assert read_object(derivable) == original


def _backfill_module():
    import importlib

    return importlib.import_module("apps.listings.migrations.0004_photo_storage_token")


def test_the_backfill_refuses_a_row_whose_file_is_genuinely_gone(
    photo_on_a_live_listing,
):
    """**This test used to assert the branch that lost the photographs.**

    It asserted that a row whose file is missing is re-keyed anyway — a
    fresh token, a `storage_key` pointing at a path that has never existed.
    On the state that actually produces a missing file in practice (an
    earlier run of this migration that moved the objects and then rolled
    back), that silently orphaned every photograph under a token recorded
    nowhere: unreachable by the app, invisible to `purge_media`, and out of
    reach of `COMPLIANCE.md` §7 row 9's deletion obligation. Review R-R5.

    A restore that carried the database and not the media directory
    (`INFRA.md` §3's backup scope) is still a real state, and the migration
    still tells the operator what to do about it — but it says so, rather
    than writing a row that claims bytes that do not exist. The message is
    asserted, not the exception type: a refusal whose text does not reach
    the person running it is a refusal that gets worked around (rule 10's
    sixth disguise).
    """
    from django.apps import apps as live_apps

    from apps.listings.models import ListingPhoto
    from apps.listings.storage import delete_object

    _listing, photo = photo_on_a_live_listing
    before_key = photo.storage_key
    delete_object(photo.storage_key)
    # Pre-migration state: the column exists but this row has not been
    # through the backfill.
    ListingPhoto.all_objects.filter(id=photo.id).update(storage_token=None)

    with pytest.raises(RuntimeError) as caught:
        _backfill_module().forward(live_apps, None)

    message = str(caught.value)
    assert "will not mint a token" in message
    assert "NULL storage_key" in message, "the recovery must be in the message"
    photo.refresh_from_db()
    assert photo.storage_token is None and photo.storage_key == before_key, (
        "the refusal must leave the row exactly as it found it"
    )


def test_the_backfill_adopts_the_bytes_an_earlier_rolled_back_run_moved(
    photo_on_a_live_listing,
):
    """**The rollback that R-R5 is about, reconstructed and measured.**

    The renames are filesystem operations inside a transaction. When a later
    operation in the migration fails, the database reverts to the old
    `storage_key` values and the files stay at their new random paths — and
    nothing in the database records those paths. This is the second run.

    Content addressing is what makes it recoverable: the row carries the
    `sha256`, so the orphan is identifiable as *this* row's bytes. The
    photograph survives the rollback, which is the whole point of the
    finding.
    """
    from django.apps import apps as live_apps

    from apps.listings.models import ListingPhoto
    from apps.listings.storage import object_path, read_object

    _listing, photo = photo_on_a_live_listing
    original = read_object(photo.storage_key)
    old_key = photo.storage_key

    # Exactly what a rolled-back apply leaves behind: the bytes at a random
    # token, the row still at its pre-migration key and with no token.
    abandoned = f"listings/{photo.listing_id}/{'ab' * 16}.jpeg"
    target = object_path(abandoned)
    target.parent.mkdir(parents=True, exist_ok=True)
    object_path(old_key).replace(target)
    ListingPhoto.all_objects.filter(id=photo.id).update(storage_token=None)

    _backfill_module().forward(live_apps, None)

    photo.refresh_from_db()
    assert photo.storage_key == abandoned, (
        "the backfill minted a fresh token instead of adopting the bytes "
        "the previous run moved — the photograph is now orphaned"
    )
    assert photo.storage_token == "ab" * 16
    assert read_object(photo.storage_key) == original


def test_the_backfill_is_a_no_op_on_a_row_it_has_already_done(
    photo_on_a_live_listing,
):
    """Idempotence, asserted on the thing that must not move twice.

    A second pass that re-keyed an already-keyed row would rename a file for
    no reason and, on any run that did not complete, do it again.
    """
    from django.apps import apps as live_apps

    _listing, photo = photo_on_a_live_listing
    photo.refresh_from_db()
    key, token = photo.storage_key, photo.storage_token
    assert token, "the fixture must already be backfilled, or this proves nothing"

    _backfill_module().forward(live_apps, None)

    photo.refresh_from_db()
    assert (photo.storage_key, photo.storage_token) == (key, token)
