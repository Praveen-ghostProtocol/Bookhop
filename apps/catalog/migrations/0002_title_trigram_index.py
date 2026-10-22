"""`pg_trgm` on `books.title_norm`. DATA-MODEL §3: *"GIN (title_norm gin_trgm_ops)"*.

**The two engines get different index kinds and the difference is recorded
rather than assumed** (`CLAUDE.md` rule 9's labelling rule):

  * **PostgreSQL — VERIFIED HERE.** `CREATE EXTENSION pg_trgm` and a GIN index
    with `gin_trgm_ops`. `apps.catalog.services.search_books` uses
    `similarity()`, so a misspelling still matches;
    `tests/unit/test_catalog.py` asserts a one-character typo is found, and
    skips that assertion on SQLite naming the engine and the slice rather
    than passing.
  * **SQLite — VERIFIED HERE.** No `pg_trgm` exists, so `0001` already created
    a plain B-tree and `search_books` does a substring match. **A misspelling
    finds nothing**, and the contract every caller may rely on is therefore
    the weaker one.

**`CREATE EXTENSION` needs privileges the application role may not have in
production**, which is the one thing about this migration that can fail
somewhere this machine is not. `IF NOT EXISTS` plus a caught failure would be
the tempting shape and is refused: an extension that silently did not install
leaves `similarity()` undefined and `search_books` raising at runtime on the
first search, which is a worse failure than a migration that stops. **So it
raises**, and `INFRA.md`'s provisioning step is where the extension is created
by a superuser — flagged to platform-sre in the slice note, because S8 is when
that role exists.
"""

from django.db import migrations


def _create_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm", None)
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS books_title_trgm_idx "
        "ON books USING gin (title_norm gin_trgm_ops)",
        None,
    )


def _drop_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP INDEX IF EXISTS books_title_trgm_idx", None)
    # The extension is deliberately **not** dropped on reverse: another
    # database object may depend on it, and `DROP EXTENSION` cascading is a
    # far larger action than reversing one migration should take.


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]

    operations = [migrations.RunPython(_create_index, _drop_index)]
