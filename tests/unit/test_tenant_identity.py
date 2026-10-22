"""The composite foreign key, by name and by behaviour. ADR-002 §2, F32.

**The blocking finding this closes was a compliance failure, not a defect.**
QA measured it: a `listing_photos` row whose `is_seed` disagreed with its
listing's was served — 200, real image bytes — to a non-owner on a campus
whose discovery gate was closed. The denormalised columns were copies that
nothing re-derived, and the gated manager asks the gate question of the row
it is handed.

**Both limbs, and the structural one is engine-aware because the catalogs
differ** (`CLAUDE.md` rule 9's labelling rule):

* **PostgreSQL — VERIFIED HERE.** A real multi-column `FOREIGN KEY`
  constraint, visible in `pg_constraint` with four key columns.
* **SQLite — VERIFIED HERE.** A real composite FK in the table definition,
  visible as **one** `PRAGMA foreign_key_list` id spanning four `seq` rows.
  Django's own `connection.introspection` **flattens it into four
  single-column entries**, so a structural check written as *"a constraint
  whose `columns` list is longer than one"* cannot see it on this engine —
  **the constraint is there and enforcing; the introspection API is what
  cannot express it.** That is reported to test-qa, whose
  `test_denormalised_scope_columns.py` uses exactly that shape and is red on
  SQLite for this reason while its behavioural tests pass.
* **`listings (campus_id, city_id)` is a trigger pair on SQLite**, not an FK,
  because adding an FK there means rebuilding the table and a SQLite rebuild
  **drops the table's triggers** — which on `listings` is
  `listings_price_immutable`, the one trigger P14 depends on. Same property,
  different mechanism, stated rather than assumed.
"""

import pytest
from django.db import connection, transaction
from django.db.utils import DatabaseError, IntegrityError

pytestmark = pytest.mark.django_db

TENANT_IDENTITY = ("id", "campus_id", "city_id", "is_seed")


def _force(table, row_id, **columns):
    """Write straight to the row, past the ORM and past the service.

    The service is not the thing in doubt. ADR-002 §2 puts the control in the
    **database**, so the attack has to be a database write.
    """
    assignments = ", ".join(f'"{column}" = %s' for column in columns)
    with connection.cursor() as cursor:
        cursor.execute(
            f'UPDATE "{table}" SET {assignments} WHERE id = %s',
            [*columns.values(), row_id],
        )


# --- structural: the diagnostic, per engine -------------------------------


def test_the_tenant_identity_index_exists_on_the_parent():
    """ADR-002 §2's DDL, first half. Portable, so no engine branch."""
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, "listings")
    assert "listings_tenant_identity" in constraints, sorted(constraints)
    assert tuple(constraints["listings_tenant_identity"]["columns"]) == TENANT_IDENTITY


def test_the_campus_city_identity_index_exists():
    """The target of the second composite FK — `campuses (id, city_id)`."""
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, "campuses")
    assert "campuses_city_identity" in constraints, sorted(constraints)


def test_the_composite_foreign_key_is_installed(engine):
    """One constraint covering four columns, read from the engine's own catalog.

    Not from `connection.introspection`, which flattens it on SQLite — the
    thing being asserted is what the **server** holds, and the two servers
    describe it differently.
    """
    with connection.cursor() as cursor:
        if engine == "postgresql":
            cursor.execute(
                "SELECT conname, array_length(conkey, 1) FROM pg_constraint "
                "WHERE conrelid = 'listing_photos'::regclass AND contype = 'f' "
                "AND array_length(conkey, 1) > 1"
            )
            rows = cursor.fetchall()
            assert rows, (
                "no multi-column FK on listing_photos; ADR-002 §2's amendment "
                "is not installed"
            )
            assert rows[0][1] == 4, rows
        else:
            cursor.execute("PRAGMA foreign_key_list(listing_photos)")
            rows = cursor.fetchall()
            by_id = {}
            for row in rows:
                by_id.setdefault(row[0], []).append(row[3])
            composite = [columns for columns in by_id.values() if len(columns) > 1]
            assert composite, (
                "no composite FK in the listing_photos table definition: "
                f"{by_id}"
            )
            assert sorted(composite[0]) == sorted(
                ["listing_id", "campus_id", "city_id", "is_seed"]
            ), composite


def test_the_city_rule_is_installed_by_some_mechanism(engine):
    """`listings.city_id` cannot disagree with its campus.

    FK on PostgreSQL, trigger pair on SQLite — because rebuilding `listings`
    on SQLite would drop `listings_price_immutable`. The **property** is
    asserted behaviourally below on both engines; this names the mechanism so
    a failure says which one went missing.
    """
    with connection.cursor() as cursor:
        if engine == "postgresql":
            cursor.execute(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'listings'::regclass AND contype = 'f' "
                "AND array_length(conkey, 1) = 2"
            )
            assert cursor.fetchall(), "listings has no (campus_id, city_id) FK"
        else:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' "
                "AND name LIKE 'listings_campus_city_%'"
            )
            names = {name for (name,) in cursor.fetchall()}
            assert names == {"listings_campus_city_insert", "listings_campus_city_update"}, (
                f"both directions must be guarded; found {sorted(names)}"
            )


def test_the_price_trigger_survived_the_sqlite_rebuild(engine):
    """**The hazard accounts/0004 exists because of, checked here.**

    A SQLite table rebuild drops the table's triggers. This migration rebuilds
    two child tables and deliberately does **not** rebuild `listings` for
    exactly that reason. If a later migration ever does, P14's trigger goes
    with it — and this is the test that notices.
    """
    with connection.cursor() as cursor:
        if engine == "postgresql":
            cursor.execute(
                "SELECT 1 FROM pg_trigger WHERE tgname = 'listings_price_immutable'"
            )
        else:
            cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'trigger' "
                "AND name = 'listings_price_immutable'"
            )
        assert cursor.fetchone(), "the price-immutability trigger is gone"


# --- behavioural: the guarantee, on both engines --------------------------


@pytest.mark.parametrize("column", ["is_seed", "campus_id", "city_id"])
def test_a_child_cannot_claim_a_tenant_identity_its_parent_does_not_have(
    s2_listing, seller, book, column
):
    """**The attack ADR-002 §2 asks for, written directly at the database.**

    Each of the three denormalised columns, one at a time. The write is raw
    SQL so the result is a statement about the database — *"by any path:
    service, admin, raw SQL, a migration, or a fixture"*.
    """
    from apps.core.models import Campus, City
    from apps.listings.services import add_photo

    photo = add_photo(seller, s2_listing, _tiny_jpeg())
    values = {
        "is_seed": not s2_listing.is_seed,
        "campus_id": Campus.objects.exclude(id=s2_listing.campus_id).first(),
        "city_id": City.objects.exclude(id=s2_listing.city_id).first(),
    }
    value = values[column]
    if column != "is_seed" and value is None:
        other = _another_campus(s2_listing)
        value = other.id if column == "campus_id" else other.city_id
    elif column != "is_seed":
        value = value.id

    with pytest.raises((IntegrityError, DatabaseError)):
        with transaction.atomic():
            _force("listing_photos", photo.id, **{column: value})


def test_the_consistent_child_is_still_writable(s2_listing, seller):
    """The other side of the split (rule 10's corollary).

    A constraint that refused every write would pass the three attacks above
    and break photo upload entirely. The ordinary case has to keep working,
    and `add_photo` succeeding is that assertion.
    """
    from apps.listings.services import add_photo

    photo = add_photo(seller, s2_listing, _tiny_jpeg())
    assert photo.campus_id == s2_listing.campus_id
    assert photo.is_seed == s2_listing.is_seed
    # And a legitimate update of a non-tenant column still goes through.
    _force("listing_photos", photo.id, width=99)
    photo.refresh_from_db()
    assert photo.width == 99


def test_a_book_request_city_cannot_disagree_with_its_campus(seller, signup_campus):
    """The second composite FK, which replaces the nightly check.

    A request whose `city_id` is not its campus's city is counted in the
    wrong city by every `METRICS.md` query that groups by city — §9.3's match
    rate among them — and no read path notices.
    """
    from apps.core.models import City
    from apps.listings.models import BookRequest

    other_city = City.objects.create(name="Coimbatore", state="Tamil Nadu")
    row = BookRequest.all_objects.create(
        requester=seller, requester_pseudonym=seller.person_pseudonym,
        free_text_title="A want with a wrong city",
        campus_id=signup_campus.id, city_id=signup_campus.city_id,
        status="OPEN", is_seed=True,
    )
    with pytest.raises((IntegrityError, DatabaseError)):
        with transaction.atomic():
            _force("book_requests", row.id, city_id=other_city.id)


def test_a_listing_city_cannot_disagree_with_its_campus(s2_listing):
    """The same rule on the parent — FK on PostgreSQL, trigger on SQLite."""
    from apps.core.models import City

    other_city = City.objects.create(name="Madurai", state="Tamil Nadu")
    with pytest.raises((IntegrityError, DatabaseError)):
        with transaction.atomic():
            _force("listings", s2_listing.id, city_id=other_city.id)


def test_a_user_city_cannot_disagree_with_its_campus(student):
    """`users` carries the same pair and had the same hole."""
    from apps.core.models import City

    other_city = City.objects.create(name="Trichy", state="Tamil Nadu")
    with pytest.raises((IntegrityError, DatabaseError)):
        with transaction.atomic():
            _force("users", student.id, city_id=other_city.id)


def test_the_gated_manager_can_no_longer_disagree_with_its_parent(s2_listing, seller):
    """ADR-002 §2's own statement of the risk, now unreachable.

    *"If either is ever written inconsistently with its parent listing, the
    gated manager silently returns the wrong rows."* The write that would
    produce that state is refused, so the manager has nothing to disagree
    with — which is the difference between preventing and detecting.
    """
    from apps.listings.models import Listing, ListingPhoto
    from apps.listings.services import add_photo

    photo = add_photo(seller, s2_listing, _tiny_jpeg())
    try:
        with transaction.atomic():
            _force("listing_photos", photo.id, is_seed=not s2_listing.is_seed)
    except (IntegrityError, DatabaseError):
        pass
    else:  # pragma: no cover - the constraint is installed
        pytest.fail("the inconsistent write was accepted")

    parent_visible = Listing.objects.filter(id=s2_listing.id).exists()
    child_visible = ListingPhoto.objects.filter(id=photo.id).exists()
    assert child_visible == parent_visible


# --- the superseded nightly check -----------------------------------------


def test_the_nightly_city_check_is_superseded_rather_than_forgotten():
    """ADR-002 §2 originally specified a **nightly consistency check** on
    `city_id`, and the amendment replaced it with the composite FK on the
    stated reasoning that *"where a database can make a class of wrong state
    unrepresentable, that beats detecting it"*.

    **It was never written, and "never written" and "deliberately replaced"
    look identical from outside** — which is the shape rule 10 is about. So
    this asserts the replacement exists, by behaviour, for every table the
    job would have walked. If the constraint is ever dropped, the job does
    not silently become the fallback: there is no job.
    """
    from apps.core.jobs import REGISTRY

    assert not any("consistency" in kind or "city_check" in kind for kind in REGISTRY), (
        "a nightly city-consistency job exists; ADR-002 §2's amendment "
        "replaced it with a constraint, so either the job is redundant or "
        "the amendment was reverted"
    )
    # The behavioural replacements are the four tests above, one per table.


# --- helpers ---------------------------------------------------------------


def _tiny_jpeg():
    import io
    import struct

    sof = (
        bytes((0xFF, 0xC0)) + struct.pack(">H", 11) + bytes((8,))
        + struct.pack(">HH", 3, 2) + bytes((1,)) + bytes((1, 0x11, 0))
    )
    sos = bytes((0xFF, 0xDA)) + struct.pack(">H", 8) + bytes((1, 1, 0, 0, 0x3F, 0))
    return io.BytesIO(
        bytes((0xFF, 0xD8)) + sof + sos + bytes((0, 0)) + bytes((0xFF, 0xD9))
    )


def _another_campus(listing):
    from apps.core.models import Campus, City

    city = City.objects.create(name="Elsewhere", state="Tamil Nadu")
    return Campus.objects.create(
        city=city, name="Other Campus", slug="other-campus",
        legal_entity_id=listing.campus.legal_entity_id,
    )
