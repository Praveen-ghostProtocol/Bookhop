r"""The photo filename stops being derivable. API-CONTRACT A-25, Red Team F51.

`add_photo` built `listings/{id}/{sha256[:32]}.{fmt}` while `listing_payload`
publishes both the id and the full `sha256`. **Anyone who could read one
listing response could write down the exact path on disk and hand it to
anyone at all** — and `ADR-001.md` §2.6 and `INFRA.md` §1 both route
`MEDIA_ROOT` through a public nginx location, so the Django authorisation
decision is not the only thing between that path and the internet. A-25:
*"The stored filename gains a component that appears in **no** response — a
per-photo random token, stored on the row. The URL keeps the `sha256`; the
disk does not."*

**Three operations, and the middle one is why this file is long.**

1. `listing_photos.storage_token` — 32 hex characters from the OS CSPRNG.
2. **The backfill renames every existing object on disk** and rewrites its
   `storage_key`. A column added without this would leave every photo
   already uploaded at its derivable path, which is the whole finding.
3. `listing_photos_one_copy_per_listing` — `UNIQUE (listing_id, sha256)`.
   Duplicate detection used to be a *side effect* of `storage_key` being
   UNIQUE and content-addressed. A random token removes that side effect, so
   the guarantee is restored as the property it always was before the thing
   providing it goes away (`CLAUDE.md` rule 12: the new remedy goes in beside
   the old, and the old comes out in the commit that turns the new one green
   — here, in the same migration).

---

**`SeparateDatabaseAndState`, and it is not ceremony — it is F46's lesson
applied one migration later.**

Django's SQLite backend implements `AddField` and `AddConstraint` by
**rebuilding the table from its own model state**. `listings/0003` added
`listing_photos_parent_tenant_fk` — the composite foreign key that makes a
photo lying about its parent's campus or seed flag *unrepresentable* — with
raw SQL that Django's model state has never heard of. **A plain `AddField`
here would therefore have rebuilt `listing_photos` without that FK, on
SQLite only, silently**, re-opening F32: a `listing_photos` row whose
`is_seed` disagreed with its listing's, served to a non-owner on a closed
campus.

So the database half is raw `ALTER TABLE … ADD COLUMN` and `CREATE UNIQUE
INDEX`, which **neither engine implements by rebuilding**, and the state half
is the ordinary Django operations so `makemigrations --check` stays clean.
`tests/contract/test_the_storage_key_is_not_derivable.py` asserts the
composite FK is still there afterwards — on both engines, because an
assertion about SQLite's behaviour that only runs on PostgreSQL is a
prediction.

**Reverse — VERIFIED HERE on both engines**, which `listings/0003` is not
(F46, still open). `DROP COLUMN` has been in SQLite since 3.35 (2021) and
this runtime has 3.45; the index drop and the rename-back are symmetric with
the forward direction, so `migrate listings 0003` restores the previous
spelling of every file as well as the schema. Asserted by
`test_the_migration_reverses_on_this_engine`.

# ponytail: the backfill loops rows in Python and renames files one at a
# time. Ceiling: it is O(photos) with a filesystem call each, so it is a
# minutes-long migration at a scale this product does not have (pilot is two
# or three campuses). Upgrade path: none worth writing — the backfill runs
# once and the set it walks is bounded by a four-photo cap per listing.
"""

import hashlib
import secrets

from django.db import migrations, models

TABLE = "listing_photos"
INDEX = "listing_photos_one_copy_per_listing"


def _key(listing_id, token, suffix):
    return f"listings/{listing_id}/{token}.{suffix}"


def _rename(old_key, new_key):
    """Move one object. `False` if the source is not there.

    **It reports the absence; it does not decide what the absence means.**
    That decision moved to `forward`, because the two states it conflated —
    a row whose bytes are genuinely gone, and a row whose bytes an earlier
    rolled-back run already moved — need opposite answers, and tolerating
    both in here is what lost the photographs.
    """
    from apps.listings.storage import object_path

    source = object_path(old_key)
    if not source.exists():
        return False
    target = object_path(new_key)
    target.parent.mkdir(parents=True, exist_ok=True)
    source.replace(target)
    return True


def _adopt(ListingPhoto, row):
    """The bytes of `row`, found by content, under a token nothing records.

    **This is the recovery path for a rolled-back apply**, and it exists
    because the two halves of this migration do not roll back together. The
    renames are filesystem operations inside a transaction: if anything later
    in the migration fails — most plausibly the UNIQUE index, on a database
    that already holds two rows with one `(listing_id, sha256)` — the
    database reverts to the old `storage_key` values while the files sit at
    their new random paths. Nothing in the database now records where they
    are.

    Without this, the re-run minted a **fresh** token, every affected row
    pointed at a path that had never existed, and the real bytes were
    orphaned under a token recorded nowhere: unreachable by the app and
    invisible to `purge_media`, so `COMPLIANCE.md` §7 row 9's deletion
    obligation could not be met for them either. The tolerant branch of
    `_rename` was the branch that lost the photographs.

    Content addressing is what makes the recovery possible: `sha256` is on
    the row, so an orphan can be identified as *this* row's bytes rather than
    guessed at. A file another row already claims is skipped, so two rows
    sharing a hash on one listing cannot be collapsed onto one object.
    """
    from apps.listings.storage import media_root

    directory = media_root() / "listings" / str(row.listing_id)
    if not directory.is_dir():
        return None
    claimed = {
        str(key).rsplit("/", 1)[-1]
        for key in ListingPhoto.objects.filter(listing_id=row.listing_id)
        .exclude(storage_key=None)
        .values_list("storage_key", flat=True)
    }
    want = str(row.sha256).lower()
    for candidate in sorted(directory.iterdir()):
        if candidate.name in claimed or not candidate.is_file():
            continue
        if hashlib.sha256(candidate.read_bytes()).hexdigest().lower() == want:
            return candidate.stem
    return None


def forward(apps, schema_editor):
    """Re-runnable, and it refuses rather than inventing a path.

    Three states, three outcomes, because a migration that cannot tell them
    apart will guess wrong on the one that matters:

      * **already backfilled** — `storage_token` is set: skipped, so a second
        run converges instead of re-keying;
      * **bytes present at the old path** — renamed and re-keyed, the
        ordinary case;
      * **bytes absent** — adopted by content hash if they are findable (a
        rolled-back apply), and otherwise **refused**. The row is never
        pointed at a path that has never existed.
    """
    ListingPhoto = apps.get_model("listings", "ListingPhoto")
    for row in ListingPhoto.objects.exclude(storage_key=None).iterator():
        if row.storage_token:
            continue
        suffix = str(row.storage_key).rsplit(".", 1)[-1].lower()
        token = secrets.token_hex(16)
        new_key = _key(row.listing_id, token, suffix)
        if not _rename(row.storage_key, new_key):
            token = _adopt(ListingPhoto, row)
            if token is None:
                raise RuntimeError(
                    f"listing_photos row {row.pk} says its bytes are at "
                    f"{row.storage_key!r} and they are not there, and no "
                    f"file under listings/{row.listing_id}/ hashes to its "
                    f"sha256. This migration will not mint a token for a "
                    f"file it cannot find: that would point the row at a "
                    f"path that has never existed and orphan the real bytes "
                    f"under a name nothing records, out of reach of "
                    f"purge_media and of erasure. Two ways to get here. (1) "
                    f"A restore that carried the database and not the media "
                    f"directory (INFRA.md §3): the bytes are genuinely gone "
                    f"and the correct state for that row is a NULL "
                    f"storage_key, which is how purge_media records bytes "
                    f"that no longer exist — null it and re-run. (2) An "
                    f"earlier run of this migration moved the file and then "
                    f"rolled back, and the media directory has since been "
                    f"replaced or cleaned: find the object, put it back "
                    f"under listings/{row.listing_id}/, and re-run."
                )
            new_key = _key(row.listing_id, token, suffix)
        row.storage_key = new_key
        row.storage_token = token
        row.save(update_fields=["storage_key", "storage_token"])


def reverse(apps, schema_editor):
    """Back to the derivable spelling, so the reverse is a real reverse.

    It restores the **defect**, which is the point of a rollback: `INFRA.md`
    §4 rolls back to a known state, not to a better one. The forward
    direction is what fixes F51.
    """
    ListingPhoto = apps.get_model("listings", "ListingPhoto")
    for row in ListingPhoto.objects.exclude(storage_key=None).iterator():
        suffix = str(row.storage_key).rsplit(".", 1)[-1].lower()
        old_key = _key(row.listing_id, str(row.sha256)[:32], suffix)
        if old_key == row.storage_key:
            continue
        _rename(row.storage_key, old_key)
        row.storage_key = old_key
        row.save(update_fields=["storage_key"])


class Migration(migrations.Migration):

    dependencies = [("listings", "0003_tenant_identity_composite_fk")]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="listingphoto",
                    name="storage_token",
                    field=models.TextField(blank=True, null=True),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=f'ALTER TABLE "{TABLE}" ADD COLUMN "storage_token" text NULL',
                    reverse_sql=f'ALTER TABLE "{TABLE}" DROP COLUMN "storage_token"',
                ),
            ],
        ),
        migrations.RunPython(forward, reverse),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddConstraint(
                    model_name="listingphoto",
                    constraint=models.UniqueConstraint(
                        fields=("listing", "sha256"), name=INDEX
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        f'CREATE UNIQUE INDEX "{INDEX}" '
                        f'ON "{TABLE}" ("listing_id", "sha256")'
                    ),
                    reverse_sql=f'DROP INDEX "{INDEX}"',
                ),
            ],
        ),
    ]
