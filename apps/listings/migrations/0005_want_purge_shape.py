r"""`requests_book_or_title_chk` gains the purged shape. COMPLIANCE P16(i).

**This migration is an escalation, not a resolved decision.** DATA-MODEL §3
states the CHECK verbatim as `(book_id IS NOT NULL OR free_text_title IS NOT
NULL)` and backend may not edit that file. P16(i) requires a purge limb that
**NULLs `free_text_title` and `course_code` at `purge_due_at` and keeps the
row** — the row without its free text is still R-01's demand signal — and a
free-text want has `book_id IS NULL`, so the two-term CHECK refuses exactly
the write the pilot blocker demands. Measured before this was written:

    UPDATE "book_requests" SET "free_text_title" = NULL, "course_code" = NULL
    -> IntegrityError: CHECK constraint failed: requests_book_or_title_chk

The third term is the narrowest one that admits the purged shape: nothing sets
`purge_due_at` without `closed_at`, so an OPEN want cannot reach it, and
`create_request` never writes `closed_at`, so the creation path is unchanged.
**cto ratifies this as a DATA-MODEL §3 amendment or reverts the migration.**

---

**`SeparateDatabaseAndState`, for §13.1's reason and nothing else.**
`listings/0003` installed `book_requests_campus_city_fk` with raw SQL, so it
lives **only in the database** on PostgreSQL and only in a derived
`CREATE TABLE` on SQLite. Django implements `RemoveConstraint`/`AddConstraint`
on SQLite by rebuilding the table **from model state**, which has never heard
of that FK — a plain pair of operations would therefore drop the tenant
identity FK on SQLite only, silently, which is §13.1's defect one table over.

So the database half is written per engine:

  * **PostgreSQL — VERIFIED HERE.** `DROP CONSTRAINT` / `ADD CONSTRAINT`, which
    does not rebuild anything.
  * **SQLite — VERIFIED HERE.** SQLite cannot alter a CHECK at all, so the
    table *is* rebuilt — but from **its own existing DDL**, not from model
    state, so the composite FK and every index and trigger survive. The same
    read-back shape as `0003._sqlite_rebuild_with_fk`, which is where it came
    from.

**Reversible on both engines**, and the reverse is tested. It restores the
two-term CHECK, so it fails — loudly, with the constraint's own name — if a
purged row already exists. That is the correct failure: reversing this
migration re-imposes an invariant the purge has already broken, and a reverse
that silently dropped those rows would delete R-01's measurement.
"""

from django.db import migrations, models

CHECK_NAME = "requests_book_or_title_chk"
TABLE = "book_requests"

#: The two bodies, as data. One definition each, read by both engines and by
#: both directions, so a forward and a reverse cannot disagree.
TWO_TERM = '"book_id" IS NOT NULL OR "free_text_title" IS NOT NULL'
THREE_TERM = TWO_TERM + ' OR "closed_at" IS NOT NULL'


def _pg(schema_editor, body):
    schema_editor.execute(
        f'ALTER TABLE "{TABLE}" DROP CONSTRAINT "{CHECK_NAME}"', None
    )
    schema_editor.execute(
        f'ALTER TABLE "{TABLE}" ADD CONSTRAINT "{CHECK_NAME}" CHECK ({body})', None
    )


def _sqlite(schema_editor, body):
    """Rebuild `book_requests` with one CHECK body swapped, keeping the rest.

    The new `CREATE TABLE` is **derived from the old one** — nothing is
    retyped — and the indexes and triggers are read back from `sqlite_master`
    rather than listed here, because a hand-written list is a list that is one
    short the first time somebody adds an index.
    """
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = %s", [TABLE]
        )
        row = cursor.fetchone()
        if not row:  # pragma: no cover - the table is created by 0001
            raise RuntimeError(f"{TABLE} does not exist, so it cannot be rebuilt")
        original = row[0]
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE tbl_name = %s "
            "AND type IN ('index', 'trigger') AND sql IS NOT NULL",
            [TABLE],
        )
        extras = [sql for (sql,) in cursor.fetchall()]

    named = original.find(CHECK_NAME)
    if named == -1:
        raise RuntimeError(
            f"{CHECK_NAME} is not in {TABLE}'s CREATE TABLE, so this migration "
            "would rebuild the table and change nothing. A migration that "
            "silently does nothing is worse than one that fails."
        )
    opened = original.index("(", original.index("CHECK", named))
    depth = 0
    closed = opened
    while True:
        if original[closed] == "(":
            depth += 1
        elif original[closed] == ")":
            depth -= 1
            if depth == 0:
                break
        closed += 1
    rebuilt = original[:opened] + f"({body})" + original[closed + 1 :]

    temporary = f"{TABLE}__rebuild"
    rebuilt = rebuilt.replace(f'"{TABLE}"', f'"{temporary}"', 1)

    execute = schema_editor.execute
    execute(rebuilt, None)
    execute(f'INSERT INTO "{temporary}" SELECT * FROM "{TABLE}"', None)
    execute(f'DROP TABLE "{TABLE}"', None)
    execute(f'ALTER TABLE "{temporary}" RENAME TO "{TABLE}"', None)
    for sql in extras:
        execute(sql, None)


def _run(body):
    def apply(apps, schema_editor):
        vendor = schema_editor.connection.vendor
        if vendor == "postgresql":
            _pg(schema_editor, body)
        elif vendor == "sqlite":
            _sqlite(schema_editor, body)
        else:
            raise RuntimeError(
                f"{CHECK_NAME} is not written for {vendor!r}; ADR-001 §2.2 "
                "permits postgresql (production) and sqlite (local dev) only"
            )

    return apply


class Migration(migrations.Migration):
    # Not atomic, for `0003`'s reason: the SQLite path drops and renames a
    # table, and a DDL sequence that cannot be rolled back is better run where
    # a half-applied state is visible than inside a transaction that hides it.
    atomic = False

    dependencies = [("listings", "0004_photo_storage_token")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(_run(THREE_TERM), _run(TWO_TERM)),
            ],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="bookrequest", name=CHECK_NAME,
                ),
                migrations.AddConstraint(
                    model_name="bookrequest",
                    constraint=models.CheckConstraint(
                        condition=(
                            models.Q(book__isnull=False)
                            | models.Q(free_text_title__isnull=False)
                            | models.Q(closed_at__isnull=False)
                        ),
                        name=CHECK_NAME,
                    ),
                ),
            ],
        ),
    ]
