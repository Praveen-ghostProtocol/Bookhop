"""`listings/0003`'s SQLite path: the splice, and the reverse nobody ran.

**Why this file exists.** The composite foreign key that closed F32–F37 is
installed two different ways. On PostgreSQL it is `ALTER TABLE … ADD
CONSTRAINT`, which is the DDL ADR-002 §2 writes. SQLite has no `ADD
CONSTRAINT` at all, so the migration **rebuilds the table**: it reads the
existing `CREATE TABLE` out of `sqlite_master`, splices a `FOREIGN KEY`
clause in before the closing parenthesis, copies the rows across and renames.

Deriving the new statement from the old one is the right call — rule 11, and
it is why no column or CHECK can drift from the models. **But the thing that
makes the splice land in the right place is a string index:**

    closing = original.rfind(")")
    rebuilt = original[:closing] + clause

`rfind` is the *last* `)` in the statement. That is the table's closing
parenthesis **only if nothing after it contains one** — which is true of
every `CREATE TABLE` Django emits, and is true by nothing anybody asserts.
`book_requests` is the case that makes this worth measuring: its definition
ends in two CHECK constraints, the last of which closes with three
parentheses in a row.

So: the splice point is pinned as an invariant, the trailing-CHECK case is
measured on the real table rather than a synthetic one, and the migration is
**round-tripped** — forward, reverse, forward — which is the half that was
not run.

Written from the migration's stated contract (*"every column, CHECK and
existing reference is carried across by construction"*) and from ADR-002 §2,
not from the splice's implementation beyond the two lines quoted above.
"""

import re
import uuid

import pytest
from django.core.management import call_command
from django.db import connection

pytestmark = pytest.mark.django_db

def _table_sql(table):
    with connection.cursor() as cur:
        cur.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = %s", [table]
        )
        row = cur.fetchone()
    return row[0] if row else None


def _strip_literals(sql):
    """Single-quoted literals out, so a `(` inside a CHECK's value list does
    not count as structure. `'OPEN'` has none today; a future enum value
    could, and that is the sort of thing a paren-counting guard must not be
    fooled by."""
    return re.sub(r"'(?:[^']|'')*'", "''", sql)


# --------------------------------------------------------------------------
# 1. the splice point, pinned as an invariant
# --------------------------------------------------------------------------


@pytest.mark.parametrize("table", ["listing_photos", "book_requests"])
def test_the_last_paren_really_is_the_tables_closing_paren(table):
    """**The guard on the string index.**

    `rfind(")")` is safe if and only if the table's closing parenthesis is
    the last one in the statement. That is a property of the DDL shape, not
    of the splice, and nothing in the migration asserts it — so a future
    `CREATE TABLE` carrying anything parenthesised after its body (a
    `WITHOUT ROWID` variant, a generated-column clause, a dialect option)
    would splice the `FOREIGN KEY` into the wrong place and the failure would
    be a syntax error at migrate time at best.

    Measured directly: take the live statement, cut it at `rfind(")")`, and
    assert the prefix has **exactly one** unclosed `(` — the table's opener.
    """
    if connection.vendor != "sqlite":
        pytest.skip(
            "NOT APPLICABLE ON THIS ENGINE (vendor=postgresql, slice=S2): the "
            "splice exists because SQLite has no `ALTER TABLE ... ADD "
            "CONSTRAINT`. PostgreSQL never rebuilds a table, so there is no "
            "string index to guard."
        )
    sql = _table_sql(table)
    assert sql, f"{table} does not exist"

    cleaned = _strip_literals(sql)
    closing = cleaned.rfind(")")
    assert closing != -1, sql
    prefix = cleaned[:closing]
    depth = prefix.count("(") - prefix.count(")")
    assert depth == 1, (
        f"`rfind(')')` on {table}'s CREATE TABLE does not land on the table's "
        f"own closing parenthesis: the text before it has {depth} unclosed "
        "parentheses, not 1. `listings/0003`'s SQLite path splices the "
        "FOREIGN KEY clause at exactly this index, so the clause would land "
        f"inside a nested expression.\n\n{sql}"
    )
    assert cleaned[closing + 1:].strip() in ("", ";"), (
        f"there is text after {table}'s closing parenthesis, which `rfind` "
        f"cannot see past: {cleaned[closing + 1:]!r}"
    )


def test_the_trailing_check_case_is_the_one_that_really_shipped():
    """**The dangerous shape, measured on the table that has it.**

    `book_requests` ends in two CHECK constraints, and the last one closes
    with `IS NOT NULL)))` — three parentheses in a row, of which only the
    third is the table's. If the splice had used the *first* `)` after the
    last column, or any index derived by counting, it would have landed
    inside the CHECK. It did not.

    Asserted on the real definition rather than a synthetic one, because the
    question is whether **this** migration handled **this** table, and a
    hand-written example proves only that the example was chosen well.
    """
    if connection.vendor != "sqlite":
        pytest.skip(
            "NOT APPLICABLE ON THIS ENGINE (vendor=postgresql, slice=S2): "
            "no table is rebuilt here."
        )
    sql = _table_sql("book_requests")
    assert "CHECK" in sql, (
        "book_requests no longer carries a CHECK, so this file is no longer "
        "measuring the trailing-CHECK case and another table must be chosen"
    )
    assert "FOREIGN KEY (\"campus_id\", \"city_id\")" in sql, (
        f"the composite FK is not in book_requests' definition:\n{sql}"
    )
    # The CHECKs survived the rebuild intact, which is the migration's own
    # claim: *"every column, CHECK and existing reference is carried across
    # by construction"*.
    for name in ("requests_status_chk", "requests_book_or_title_chk"):
        assert name in sql, f"the rebuild dropped {name}:\n{sql}"


def test_every_column_survived_the_rebuild():
    """The migration's claim, checked against the models rather than against
    the statement it produced. A rebuild that dropped a column would still
    look well-formed."""
    if connection.vendor != "sqlite":
        pytest.skip(
            "NOT APPLICABLE ON THIS ENGINE (vendor=postgresql, slice=S2)."
        )
    from django.apps import apps as django_apps

    for label, table in (("ListingPhoto", "listing_photos"),
                         ("BookRequest", "book_requests")):
        model = django_apps.get_model("listings", label)
        expected = {f.column for f in model._meta.concrete_fields}
        with connection.cursor() as cur:
            live = {
                col.name
                for col in connection.introspection.get_table_description(cur, table)
            }
        assert expected <= live, (
            f"{table} lost columns in the rebuild: {sorted(expected - live)}"
        )


# --------------------------------------------------------------------------
# 2. the round trip — forward, reverse, forward
# --------------------------------------------------------------------------


def _controls_present():
    """What `listings/0003` installs, as a dict, read from the live catalog."""
    with connection.cursor() as cur:
        if connection.vendor == "sqlite":
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND name = 'listings_tenant_identity'"
            )
            index = bool(cur.fetchone())
            cur.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='trigger' "
                "AND name LIKE '%campus_city%'"
            )
            guards = cur.fetchone()[0]
        else:
            cur.execute(
                "SELECT count(*) FROM pg_class WHERE relname = 'listings_tenant_identity'"
            )
            index = bool(cur.fetchone()[0])
            cur.execute(
                "SELECT count(*) FROM pg_constraint WHERE conname LIKE '%campus_city_fk'"
            )
            guards = cur.fetchone()[0]
    return {"tenant_identity_index": index, "campus_city_guards": guards}


@pytest.mark.django_db(transaction=True)
def test_the_migration_round_trips_forward_reverse_forward():
    """**The half that was verified only forwards.**

    A migration is two functions and `INFRA.md` §4's rollback runs the second
    one. Backend ran the first. This runs `migrate listings 0002` and then
    `migrate listings 0003` again, and asserts the controls are back.

    **It restores the database in a `finally` whatever happens**, because
    this test needs `transaction=True` and a half-migrated schema would
    follow it into every test after.
    """
    # A committed listing, so the damage probe has a subject — built with
    # plain model creates rather than `create_listing`, and the reason is a
    # harness constraint worth stating: this test needs `transaction=True`,
    # and `tests/conftest.py` records that on SQLite the flush escape is a
    # deliberate no-op, so a transactional test that writes `consents` or
    # `audit_log` dies in teardown on the append-only trigger — correctly.
    # The service writes both. Nothing here does.
    listing = _committed_listing()

    before = _controls_present()
    assert before["tenant_identity_index"], (
        "the forward state is already wrong, so a round trip would prove "
        f"nothing: {before}"
    )

    reverse_error = None
    try:
        try:
            call_command("migrate", "listings", "0002", verbosity=0)
        except Exception as exc:  # noqa: BLE001 - the outcome is the datum
            reverse_error = exc
        after_reverse = _controls_present()
        damage = None
        if reverse_error is not None:
            damage = _measure_damage_after_a_failed_reverse(listing.id)
        else:
            call_command("migrate", "listings", "0003", verbosity=0)
            assert _controls_present() == before, (
                "the second forward did not restore the controls the first "
                f"one installed: {before} -> {_controls_present()}"
            )
    finally:
        recovery = _restore(before)
        _cleanup(listing)

    assert _controls_present() == before, (
        "the restore in `finally` did not put the schema back, so this test "
        "has damaged the database for everything after it"
    )

    assert reverse_error is None, (
        "FINDING. `listings/0003` **cannot be reversed on SQLite**, and the "
        "failure is worse than an error.\n\n"
        f"  {type(reverse_error).__name__}: {str(reverse_error)[:160]}\n\n"
        "Cause, from the migration's own reverse: it drops "
        "`listings_tenant_identity` and the eight `*_campus_city_*` triggers, "
        "and **deliberately leaves the composite FK on the rebuilt child "
        "tables** — *'dropping it would need a second rebuild, and a reverse "
        "that recreates a table is a reverse that can lose data; the "
        "constraint is harmless to leave.'* It is not harmless: the child FK "
        "now references a parent tuple with no unique index behind it, which "
        "is SQLite's `foreign key mismatch`.\n\n"
        f"State after the failed reverse: controls {after_reverse}, "
        f"and measured behaviour {damage}.\n\n"
        "**The migration is `atomic = False`, so the reverse stops halfway** "
        "— and `django_migrations` still records 0003 as applied, because "
        "the RunPython raised before Django could delete the row. So "
        "`migrate --check` is clean, the schema says the controls are "
        "installed, and they are gone. That is a guard that is off and "
        "reports as on, which is the defect class F32-F37 were about, "
        "reintroduced by their own fix's rollback path.\n\n"
        f"Recovery, measured: {recovery}.\n\n"
        "**PostgreSQL round-trips cleanly** (VERIFIED HERE) because its "
        "reverse drops the constraints before the indexes. The two paths are "
        "not equivalent and only one of them was run."
    )


def _committed_listing():
    """The minimum row the damage probe needs: a listing on a campus."""
    from django.utils import timezone

    from apps.catalog.models import Book
    from apps.core.models import Campus, City
    from apps.listings.models import Listing

    city = City.objects.create(name="Roundtrip City", state="Tamil Nadu")
    campus = Campus.objects.create(
        city=city, name="Roundtrip Campus", slug="roundtrip",
        email_domains=["roundtrip.test"],
    )
    book = Book.objects.create(
        isbn13="9788177589139", title="Roundtrip", title_norm="roundtrip",
        authors=[], language="en",
    )
    return Listing.all_objects.create(
        seller=None, seller_pseudonym=uuid.uuid4(), book=book,
        campus=campus, city=city, asking_price_paise=1000,
        price_fixed_at=timezone.now(), condition="GOOD",
        annotation_level="NONE", damage_flags=[], language="en",
        status="DRAFT", is_seed=False,
    )


def _cleanup(listing):
    """Remove what `_committed_listing` committed, so the flush has nothing
    append-only to delete."""
    from apps.catalog.models import Book
    from apps.core.models import Campus, City
    from apps.listings.models import Listing, ListingPhoto

    ListingPhoto.all_objects.filter(listing_id=listing.id).delete()
    Listing.all_objects.filter(id=listing.id).delete()
    Book.objects.filter(id=listing.book_id).delete()
    Campus.objects.filter(id=listing.campus_id).delete()
    City.objects.filter(id=listing.city_id).delete()


def _restore(target):
    """Put the schema back, and report which route it took.

    **The plain route does not work after a failed reverse, and that is part
    of the finding rather than a wrinkle in the harness.** `migrate listings`
    is a no-op, because `django_migrations` still records 0003 as applied —
    the RunPython raised before Django could delete the row. So the schema is
    missing the index and the eight triggers while the migration ledger says
    they are installed, and the only way forward is to lie to the ledger with
    `--fake` and re-run the migration for real.

    Measured here because it is what a developer or a deploy script would
    actually have to do.
    """
    call_command("migrate", "listings", verbosity=0)
    if _controls_present() == target:
        return "plain `migrate listings` was enough"
    call_command("migrate", "listings", "0002", fake=True, verbosity=0)
    call_command("migrate", "listings", "0003", verbosity=0)
    return (
        "plain `migrate listings` was a NO-OP because 0003 is still recorded "
        "as applied; recovery needed `migrate listings 0002 --fake` followed "
        "by a real forward"
    )


def _measure_damage_after_a_failed_reverse(listing_id):
    """What is actually enforced once the reverse has stopped halfway.

    Measured rather than inferred, because *"the index is gone"* and *"the
    control is off"* are different claims and only the second one matters.
    """
    out = {}
    try:
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE listings SET city_id = city_id + 99 WHERE id = %s",
                [listing_id],
            )
            cur.execute(
                "UPDATE listings SET city_id = city_id - 99 WHERE id = %s",
                [listing_id],
            )
        out["city_rule"] = "NOT ENFORCED - a listing can name a city its campus is not in"
    except Exception:  # noqa: BLE001
        out["city_rule"] = "still enforced"
    try:
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO listing_photos (is_seed, sha256, width, height, "
                "bytes, exif_stripped_at, uploaded_at, campus_id, city_id, "
                "listing_id) SELECT 1, 'qa-damage-probe', 1, 1, 1, "
                "created_at, created_at, campus_id, city_id, id "
                "FROM listings WHERE id = %s",
                [listing_id],
            )
        out["tenant_identity_fk"] = (
            "NOT ENFORCED - a photo whose is_seed disagrees with its listing "
            "was accepted, which is F34 reopened"
        )
        # Removed immediately: it is a row the restored constraint will
        # correctly refuse, and leaving it would make the recovery below fail
        # for a reason that is this probe's doing rather than the migration's.
        with connection.cursor() as cur:
            cur.execute(
                "DELETE FROM listing_photos WHERE sha256 = 'qa-damage-probe'"
            )
    except Exception as exc:  # noqa: BLE001
        out["tenant_identity_fk"] = f"still enforced: {str(exc)[:60]}"
    return out
