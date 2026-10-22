"""The denormalised tenant columns, attacked by writing the state nothing prevents.

**Written from ADR-002 §2 as amended 2026-10-22, which specifies both the
control and the test**, and from API-CONTRACT §5.2's rule for the photo route.
The ADR's words, because they are the test brief:

> S2's child tables now carry denormalised `campus_id`, `city_id` and
> `is_seed` **that nothing re-derives**. … **if either is ever written
> inconsistently with its parent listing, the gated manager silently returns
> the wrong rows** — and **every test sets both through the same service that
> sets them correctly, so the fixture cannot produce the failure mode.**
>
> **The test that matters is the one whose fixture CAN produce the failure**:
> a test that **writes an inconsistent child directly, bypassing the service,
> and asserts the database refuses it.** A test that goes through the service
> proves only that the service is correct, which was never the thing in doubt.

So this file does not call `add_photo` or `create_request` anywhere. It writes
rows with `all_objects` and with raw SQL, which is the only way to reach the
state the control exists to make impossible.

**`CLAUDE.md` rule 9 — both limbs, and they answer different questions.**

* **Existence** (`test_the_composite_*`): the named constraint is installed.
  It fails *by name*, so a reader learns which guard went missing.
* **Behaviour** (`test_an_inconsistent_*`): the wrong state is refused —
  or, if it is not refused, it is **harmless**, which is the property the
  contract actually promises. A child row that can be written inconsistently
  AND changes who can see it is a discovery-gate bypass, and API-CONTRACT
  §5.2 is explicit that *"a photo is as gated as the listing it belongs
  to"*.

The behavioural assertions are written so that **landing the constraint turns
them green through the refusal branch** rather than making them unwritable.
That is deliberate: a test that has to be deleted when the fix arrives is a
test that stops guarding the fix.
"""

import pytest
from django.db import connection, transaction
from django.db.utils import DatabaseError, IntegrityError

pytestmark = pytest.mark.django_db


#: ADR-002 §2's amendment names this index on the parent, verbatim:
#: `CREATE UNIQUE INDEX listings_tenant_identity ON listings (id, campus_id,
#: city_id, is_seed);`
TENANT_IDENTITY_INDEX = "listings_tenant_identity"

#: The columns the amendment says each child must carry into its FK.
TENANT_IDENTITY_COLUMNS = ("id", "campus_id", "city_id", "is_seed")

#: Child tables the amendment covers that actually carry the columns.
#: `swap_wants` is named in the ADR but the shipped model deliberately carries
#: no campus key — *"the listing is the thing that belongs to a campus"* — so
#: it has no inconsistency to write and is recorded here rather than silently
#: dropped.
CHILDREN_WITH_TENANT_COLUMNS = ["listing_photos"]
CHILDREN_WITHOUT = {
    "swap_wants": (
        "the shipped model carries no campus_id/city_id/is_seed, so there is "
        "no denormalised copy to disagree with the parent. ADR-002's "
        "amendment names the table; the implementation removed the subject, "
        "which is the stronger answer and is recorded rather than asserted."
    )
}


# --------------------------------------------------------------------------
# helpers — raw writes, because the service is not the thing in doubt
# --------------------------------------------------------------------------


def _indexes_on(table):
    with connection.cursor() as cur:
        return set(connection.introspection.get_constraints(cur, table))


def _constraint_details(table):
    with connection.cursor() as cur:
        return connection.introspection.get_constraints(cur, table)


def _composite_fks(table):
    """Multi-column foreign keys on `table`, as `[(columns, parent)]`.

    **Two catalogs, because Django's introspection has a shape difference
    that is not a property difference.** On PostgreSQL `get_constraints`
    reports one entry carrying all four columns. On SQLite it reports **one
    entry per column**, so counting columns per entry finds none — the
    composite FK is there and `PRAGMA foreign_key_list` is where it shows:
    the rows of one constraint share an `id`, and a composite is an `id`
    with more than one row.

    Read from the engine's own catalog either way, never from the migration.
    """
    if connection.vendor != "sqlite":
        return [
            (tuple(meta.get("columns") or ()), meta.get("foreign_key"))
            for meta in _constraint_details(table).values()
            if meta.get("foreign_key") and len(meta.get("columns") or []) > 1
        ]

    grouped = {}
    with connection.cursor() as cur:
        # PRAGMA columns: id, seq, table, from, to, on_update, on_delete, match
        cur.execute(f'PRAGMA foreign_key_list("{table}")')
        for row in cur.fetchall():
            grouped.setdefault(row[0], {"parent": row[2], "columns": []})
            grouped[row[0]]["columns"].append(row[3])
    return [
        (tuple(entry["columns"]), (entry["parent"], None))
        for entry in grouped.values()
        if len(entry["columns"]) > 1
    ]


@pytest.fixture
def open_gate(db, qa_evidence):
    """Open a campus **the only way it can lawfully be opened.**

    Not `Campus.objects.update(discovery_enabled_at=...)`: ADR-002 §4.1(a)'s
    trigger refuses that, as it should, and a test that worked around it
    would be measuring a state the product cannot reach.
    """
    from django.core.management import call_command

    from apps.core.models import GateAuthorisation

    def _open(campus):
        GateAuthorisation.objects.create(
            gate="C", scope_type="CAMPUS", scope_id=campus.id,
            legal_entity_id=campus.legal_entity_id,
            evidence=qa_evidence, authorised_by_human="A Named Human",
        )
        call_command("open_discovery", campus=campus.slug)
        campus.refresh_from_db()
        assert campus.discovery_enabled_at is not None
        return campus

    return _open


@pytest.fixture
def second_campus(db, signup_campus, legal_entity):
    """A second campus in the same city. Created closed, which is the only
    state ADR-002 §4.1(a) permits a new campus row to be in."""
    from apps.core.models import Campus

    return Campus.objects.create(
        city_id=signup_campus.city_id, name="Second Campus", slug="second-campus",
        legal_entity=legal_entity, email_domains=["second.ac.in"],
    )


@pytest.fixture
def other_student(db, signup_campus, privacy_notice):
    """A second real student on the seller's campus who owns nothing.

    Non-seed on purpose: ADR-002 §4.1(c)'s whole subject is *"a real student
    on a closed campus"*, and the existing fixtures are all `is_seed=True`.
    """
    from apps.accounts.models import User
    from apps.accounts.services import grant_consent

    user = User.objects.create(
        email="bystander@example.ac.in", display_name="A Bystander",
        campus=signup_campus, city_id=signup_campus.city_id,
        status="ACTIVE", adult_verified=True, campus_verified=True,
        is_seed=False,
    )
    grant_consent(user, "account", privacy_notice, "SIGNUP_FORM", None, "qa")
    user.refresh_from_db()
    return user


@pytest.fixture
def real_listing_with_photo(db, s2_listing):
    """A **non-seed** LIVE listing on a closed campus, with one photo row.

    `s2_listing`'s seller is a seed student, so the listing is seed and the
    gate lets it through legitimately. The flag is flipped with `all_objects`
    rather than rebuilt, because the subject of every assertion below is a
    child row that disagrees with its parent — and the parent has to be the
    kind of row the gate is supposed to hide.
    """
    import hashlib

    from django.utils import timezone

    from apps.listings.models import Listing, ListingPhoto

    Listing.all_objects.filter(id=s2_listing.id).update(is_seed=False)
    s2_listing.refresh_from_db()
    assert s2_listing.status == "LIVE" and not s2_listing.is_seed
    assert s2_listing.campus.discovery_enabled_at is None, (
        "this fixture is about a CLOSED campus; if the gate is open the whole "
        "file is measuring nothing"
    )

    # **EXIF-free bytes, and the reason is a defect QA caused and caught.**
    # `media_root()` is process-global and nothing isolates it between tests,
    # so a file written here outlives this test. The first draft of this
    # fixture wrote the EXIF-carrying `jpeg_bytes` straight to disk with
    # `write_object`, and `tests/unit/test_listing_photos.py::
    # test_the_original_is_never_written_anywhere` — which rglobs the whole
    # media tree asserting no file carries `Exif\\x00\\x00` — went red in
    # another agent's suite. That test is right and QA's fixture was wrong:
    # the row says `exif_stripped_at` is set, so the bytes behind it must be
    # stripped. Recorded rather than quietly fixed, because the shared
    # `MEDIA_ROOT` is a finding of its own (QA-S2 F38).
    from tests.contract.conftest import build_jpeg

    payload = build_jpeg(exif=False)
    digest = hashlib.sha256(payload).hexdigest()
    key = f"qa/denorm/{digest}.jpeg"
    # The bytes are written to disk as well as the row, so that a refusal
    # below is unambiguously the authorisation refusing and never the file
    # being absent. Those are two different answers and conflating them is
    # how a leak reads as a 404.
    from apps.listings.storage import object_path, write_object

    write_object(key, payload)

    photo = ListingPhoto.all_objects.create(
        listing=s2_listing,
        campus_id=s2_listing.campus_id,
        city_id=s2_listing.city_id,
        is_seed=False,
        storage_key=key,
        sha256=digest,
        width=4, height=3, bytes=len(payload),
        exif_stripped_at=timezone.now(),
    )
    yield s2_listing, photo
    # The row goes with the transaction; the file does not. Cleaned up so
    # this fixture leaves the shared media tree as it found it.
    object_path(key).unlink(missing_ok=True)


# --------------------------------------------------------------------------
# 1. existence — the control ADR-002 §2 names, asserted by name
# --------------------------------------------------------------------------


def test_the_composite_tenant_identity_index_exists_on_the_parent():
    """ADR-002 §2's amendment, first half, quoted as DDL in the ADR itself.

    Diagnostic limb. It fails by name so a reader knows **which** guard is
    missing rather than only that something is wrong.
    """
    names = _indexes_on("listings")
    assert TENANT_IDENTITY_INDEX in names, (
        f"ADR-002 §2 (amendment, 2026-10-22) specifies "
        f"`CREATE UNIQUE INDEX {TENANT_IDENTITY_INDEX} ON listings "
        f"({', '.join(TENANT_IDENTITY_COLUMNS)})` as the parent half of the "
        "composite foreign key that makes a tenant-inconsistent child "
        "unwritable. It is not installed. Installed on `listings`: "
        f"{sorted(names)}"
    )


@pytest.mark.parametrize("table", CHILDREN_WITH_TENANT_COLUMNS)
def test_the_composite_foreign_key_exists_on_each_child(table):
    """ADR-002 §2's amendment, second half:

    > ``FOREIGN KEY (listing_id, campus_id, city_id, is_seed) REFERENCES
    >   listings (id, campus_id, city_id, is_seed)``

    Read from the catalog rather than from the migration, because what matters
    is what the server installed.

    **The engine branch is an introspection limit, not a second property.**
    Django's SQLite introspection flattens a multi-column foreign key into
    **one `get_constraints` entry per column**, so a `len(columns) > 1` test
    sees four single-column FKs and concludes the composite one is missing —
    while `PRAGMA foreign_key_list` shows one constraint spanning four
    columns and the write is refused. QA's first version reported that
    flattening as a missing control on SQLite, which was wrong in the
    direction that cries wolf; the sibling structural tests in this file
    already branch by engine and this one needed the same. The **property**
    is asserted on both engines by the behavioural tests below, which is the
    limb that cannot be fooled by an introspection shape.
    """
    composite = _composite_fks(table)
    assert composite, (
        f"`{table}` has no multi-column foreign key, so ADR-002 §2's "
        "amendment is not implemented: *'A child row referencing a parent "
        "with a different campus, city or seed flag cannot be written, on "
        "either engine, by any path.'* Today it can be written by any path. "
        "Single-column FKs present: "
        + str(sorted(
            n for n, m in _constraint_details(table).items() if m.get("foreign_key")
        ))
    )


def test_the_city_key_cannot_disagree_with_its_campus():
    """ADR-002 §2's amendment, third half — *"the same move upgrades the
    `city_id` rule above: a composite FK to `campuses (id, city_id)` replaces
    the nightly check."*

    This one covers **every** tenant-scoped table, not just the children, and
    it is the one that decides whether a Chennai row can claim to be a Madurai
    row. Asserted on `listings` as the representative; the sweep over the rest
    is `test_every_tenant_scoped_table_is_covered_or_recorded` below.

    **Two mechanisms, one property, labelled** (`CLAUDE.md` rule 9). On
    PostgreSQL it is the composite FK the ADR writes. **On SQLite it is a
    trigger pair, and the reason is load-bearing rather than a shortcut:**
    SQLite has no `ADD CONSTRAINT`, so an FK can only arrive by rebuilding
    the table — and rebuilding `listings` would drop
    `listings_price_immutable`, because a SQLite trigger belongs to its
    table. That is ADR-003 §2.2's control, and trading P14's guard for
    ADR-002's would be a widening dressed as a fix. The behavioural limb
    below asserts the same refusal on both.
    """
    if connection.vendor == "sqlite":
        with connection.cursor() as cur:
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' "
                "AND tbl_name = 'listings' AND name LIKE '%campus_city%'"
            )
            triggers = sorted(name for (name,) in cur.fetchall())
        assert triggers == [
            "listings_campus_city_insert", "listings_campus_city_update"
        ], (
            "SQLite's stand-in for the `(campus_id, city_id)` FK is a trigger "
            "pair, and **both directions are required**: a guard that checks "
            "only INSERT is a guard an UPDATE walks past, which is the exact "
            f"shape of the defect this control closes. Installed: {triggers}"
        )
        return

    composite = [
        columns for columns, parent in _composite_fks("listings")
        if parent and parent[0] == "campuses"
    ]
    assert composite, (
        "ADR-002 §2 (amendment) replaces its own nightly consistency check "
        "with `FOREIGN KEY (campus_id, city_id) REFERENCES campuses (id, "
        "city_id)`, on the stated reasoning that *'where a database can make "
        "a class of wrong state unrepresentable, that beats detecting it'*. "
        "Neither the constraint nor the nightly check it replaced exists, so "
        "`listings.city_id` is unchecked by anything."
    )


def test_every_tenant_scoped_table_is_covered_or_recorded():
    """The guard on this file. A child table that grows the denormalised
    columns later must appear above or here — a table in neither is one this
    file silently stopped covering, which is the defect class the file is
    about, one level up.
    """
    from apps.core.scoping import TENANT_SCOPED_MODELS

    from django.apps import apps as django_apps

    live_children = set()
    for app_label, model_name, _slice in TENANT_SCOPED_MODELS:
        try:
            model = django_apps.get_model(app_label, model_name)
        except LookupError:
            continue
        fields = {f.name for f in model._meta.get_fields()}
        if "listing" in fields and "is_seed" in fields:
            live_children.add(model._meta.db_table)

    unaccounted = live_children - set(CHILDREN_WITH_TENANT_COLUMNS) - set(CHILDREN_WITHOUT)
    assert unaccounted == set(), (
        f"these child tables carry a denormalised tenant identity and are not "
        f"attacked by this file: {sorted(unaccounted)}"
    )


# --------------------------------------------------------------------------
# 2. behaviour — the inconsistency written directly
# --------------------------------------------------------------------------


def _force(table, photo_id, **columns):
    """Write columns straight to the row, past the ORM and past the service.

    Returns `True` if the database accepted the write. `all_objects.update()`
    would do for the ORM path; raw SQL is used so the result is a statement
    about the **database**, which is where ADR-002 puts the control.
    """
    assignments = ", ".join(f'"{c}" = %s' for c in columns)
    with connection.cursor() as cur:
        cur.execute(
            f'UPDATE "{table}" SET {assignments} WHERE id = %s',
            [*columns.values(), photo_id],
        )
    return True


def test_an_inconsistent_seed_flag_on_a_photo_is_refused_or_harmless(
    client_as, other_student, real_listing_with_photo
):
    """**The attack ADR-002 §2 asks for, on `is_seed`.**

    The listing is a real student's, on a campus whose gate is closed. The
    photo row is made to claim `is_seed = true`. Nothing re-derives it.

    API-CONTRACT §5.2 on the media route: *"Gate and scope first … a photo is
    as gated as the listing it belongs to, and a guessable media URL would be
    a side channel around ADR-002 §4."* So the only two acceptable outcomes
    are:

    * the database refuses the write (ADR-002's composite FK), or
    * the write lands and the photo is **still** 404 to a non-owner, because
      the gate decision followed the listing.

    A third outcome — the write lands and the bytes are served — is a
    discovery-gate bypass on a closed campus, reachable by any path that can
    set a child column: a staff tool, a fixture, a future slice's bulk
    update, or a migration.
    """
    listing, photo = real_listing_with_photo
    try:
        with transaction.atomic():
            _force("listing_photos", photo.id, is_seed=True)
    except (IntegrityError, DatabaseError) as exc:
        return  # the constraint landed; this is the passing branch  # noqa: RET502

    response = client_as(other_student).get(
        f"/api/v1/listings/{listing.id}/photos/{photo.sha256}"
    )
    assert response.status_code == 404, (
        "FINDING. A photo row whose `is_seed` disagrees with its listing is "
        f"served ({response.status_code}) to a student who does not own the "
        "listing, on a campus whose `discovery_enabled_at IS NULL`. The gate "
        "decision in `get_photo_for_download` reads the **photo's** copy of "
        "the flag, so the child row decides whether the parent is visible. "
        "ADR-002 §2 (amendment): *'if either is ever written inconsistently "
        "with its parent listing, the gated manager silently returns the "
        "wrong rows'* — measured, and it is the media route as well as the "
        "manager. The remedy ADR-002 specifies is the composite foreign key, "
        "which makes the row unwritable; asserted above and absent."
    )


def test_an_inconsistent_campus_on_a_photo_is_refused_or_harmless(
    client_as, real_listing_with_photo, second_campus, open_gate, db, privacy_notice
):
    """**The same attack on `campus_id` — the cross-tenant half.**

    `get_photo_for_download` scopes with `scoped(ListingPhoto.all_objects…)`,
    which filters on the **photo's** `campus_id`. A photo row pointed at a
    campus the reader belongs to puts a listing from another campus inside
    that reader's scope, which is ADR-002 §2's tenancy boundary rather than
    its gate.

    **Both gates are opened, lawfully, so the gate is out of the question.**
    That isolates the variable: whatever happens below is `scoped()`'s answer
    and not `assert_discovery_open`'s. ADR-002 §2 and §4 are two controls and
    a leak that only one of them happens to stop is still a leak in the
    other.
    """
    from apps.accounts.models import User
    from apps.accounts.services import grant_consent

    listing, photo = real_listing_with_photo
    open_gate(listing.campus)
    open_gate(second_campus)
    listing.refresh_from_db()
    outsider = User.objects.create(
        email="outsider@second.ac.in", display_name="An Outsider",
        campus=second_campus, city_id=second_campus.city_id,
        status="ACTIVE", adult_verified=True, campus_verified=True,
        is_seed=False,
    )
    grant_consent(outsider, "account", privacy_notice, "SIGNUP_FORM", None, "qa")

    before = client_as(outsider).get(
        f"/api/v1/listings/{listing.id}/photos/{photo.sha256}"
    )
    assert before.status_code == 404, (
        "the baseline is wrong: the outsider can already see this photo "
        "before any inconsistency is written, so the attack below would "
        "prove nothing"
    )

    try:
        with transaction.atomic():
            _force("listing_photos", photo.id, campus_id=second_campus.id)
    except (IntegrityError, DatabaseError):
        return  # the constraint landed

    after = client_as(outsider).get(
        f"/api/v1/listings/{listing.id}/photos/{photo.sha256}"
    )
    assert after.status_code == 404, (
        "FINDING. Repointing a photo row's denormalised `campus_id` moved a "
        f"listing across the tenancy boundary: a student on campus "
        f"{second_campus.slug!r} is served ({after.status_code}) a photo of a "
        "listing that belongs to another campus. The scope predicate reads "
        "the child's copy of the key, and ADR-002 §2's composite FK — the "
        "control that would make this unwritable — is not installed."
    )


def test_the_gated_manager_disagrees_with_its_parent_when_the_child_lies(
    real_listing_with_photo, second_campus, open_gate
):
    """The manager limb, stated as the ADR states it, with no HTTP involved.

    `GatedManager.get_queryset` asks the gate question of **the row's own**
    campus and seed flag. On a child row those are copies. So the invariant
    the ADR relies on is: *a child is visible through the gate if and only if
    its parent is* — and nothing enforces it.
    """
    from apps.listings.models import Listing, ListingPhoto

    listing, photo = real_listing_with_photo
    open_gate(second_campus)
    assert not Listing.objects.filter(id=listing.id).exists(), (
        "the parent should already be hidden: non-seed row, closed campus"
    )
    assert not ListingPhoto.objects.filter(id=photo.id).exists(), (
        "the consistent child should be hidden with it"
    )

    try:
        with transaction.atomic():
            _force("listing_photos", photo.id, campus_id=second_campus.id)
    except (IntegrityError, DatabaseError):
        return  # the constraint landed

    parent_visible = Listing.objects.filter(id=listing.id).exists()
    child_visible = ListingPhoto.objects.filter(id=photo.id).exists()
    assert child_visible == parent_visible, (
        "FINDING, in ADR-002's own words: *'the gated manager silently "
        f"returns the wrong rows'*. Parent visible: {parent_visible}. Child "
        f"visible: {child_visible}. The child is reachable through the "
        "default manager while the listing it belongs to is not, so any "
        "later code that starts from `ListingPhoto.objects` — a derivative "
        "job, a metric, S3's discovery read — begins outside the gate."
    )


def test_an_inconsistent_city_on_a_book_request_is_refused(db, seller, signup_campus):
    """`book_requests` has no listing parent, so its denormalisable key is the
    pair ADR-002 §2 covers with the *other* composite FK: `(campus_id,
    city_id) REFERENCES campuses (id, city_id)`.

    A request whose `city_id` disagrees with its campus's is counted in the
    wrong city by every `METRICS.md` query that groups by city, and §9.3's
    match rate is one of them. There is no read path that notices.
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
    # If this test fails, the write succeeded: `book_requests.city_id` can
    # name a city its campus is not in, and ADR-002 §2's replacement for the
    # nightly check is absent as well as the check.


def test_the_inconsistent_write_is_refused_and_the_writer_still_works(
    real_listing_with_photo
):
    """**The regression this test became, and it succeeded itself out of its
    old job.**

    It used to be rule 10's third disguise closed from the other side: every
    assertion above has a branch that passes when the database refuses the
    write, so if `_force` ever stopped writing anything the whole file would
    go green while measuring nothing. The old version proved `_force` worked
    by performing the attack and reading the row back changed.

    **The composite FK makes that impossible, which is the fix landing.** A
    test asserting the inconsistent write *succeeds* cannot pass against a
    database that refuses it, and deleting it would take the no-op guard with
    it. So it keeps the shape that proved the attack was real and inverts the
    verdict, in two limbs that have to be kept apart:

    1. **The attack is attempted and refused**, by the constraint, naming it.
    2. **`_force` still writes** — demonstrated on a column the FK does not
       cover. Without this limb, a `_force` that silently stopped issuing
       SQL would make limb 1 and every refusal branch above pass for the
       wrong reason, which is the exact failure the old version existed to
       prevent. The guard survives the fix instead of being replaced by it.
    """
    from apps.listings.models import ListingPhoto

    _listing, photo = real_listing_with_photo

    # Limb 2 first, so a failure says "the writer is broken" rather than
    # "the constraint held" when both are true.
    _force("listing_photos", photo.id, width=4321)
    assert ListingPhoto.all_objects.get(id=photo.id).width == 4321, (
        "`_force` did not change a column no constraint guards, so it is not "
        "writing at all — and every refusal above is being taken for the "
        "wrong reason. This file would assert nothing."
    )

    # Limb 1: the same statement shape, on a column the composite FK covers.
    with pytest.raises((IntegrityError, DatabaseError)) as caught:
        with transaction.atomic():
            _force("listing_photos", photo.id, is_seed=True)

    text = str(caught.value).lower()
    assert "foreign key" in text or "constraint" in text, (
        "the write was refused by something other than the tenant-identity "
        f"constraint, so this does not show the fix working: {caught.value!r}"
    )
    assert ListingPhoto.all_objects.get(id=photo.id).is_seed is False, (
        "the row changed despite the refusal"
    )
