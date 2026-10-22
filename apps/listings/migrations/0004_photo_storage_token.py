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

import secrets

from django.db import migrations, models

TABLE = "listing_photos"
INDEX = "listing_photos_one_copy_per_listing"


def _key(listing_id, token, suffix):
    return f"listings/{listing_id}/{token}.{suffix}"


def _rename(old_key, new_key):
    """Move one object, tolerating a row whose file is already gone.

    A missing file is not an error here: `purge_media` nulls `storage_key`
    when it removes the bytes, but a half-finished purge or a restore that
    carried the database and not the media directory both leave a row whose
    object is absent — and `INFRA.md` §3's backup scope makes the second one
    a real state. A migration that died on it would be a migration an
    operator could not run.
    """
    from apps.listings.storage import object_path

    source = object_path(old_key)
    if not source.exists():
        return False
    target = object_path(new_key)
    target.parent.mkdir(parents=True, exist_ok=True)
    source.replace(target)
    return True


def forward(apps, schema_editor):
    ListingPhoto = apps.get_model("listings", "ListingPhoto")
    for row in ListingPhoto.objects.exclude(storage_key=None).iterator():
        suffix = str(row.storage_key).rsplit(".", 1)[-1].lower()
        token = secrets.token_hex(16)
        new_key = _key(row.listing_id, token, suffix)
        _rename(row.storage_key, new_key)
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
