"""The composite foreign key. ADR-002 §2 amendment, 2026-10-22. **BLOCKING F32.**

**What this closes, measured by QA rather than predicted:** a `listing_photos`
row whose `is_seed` or `campus_id` disagreed with its listing's was served —
`200`, real image bytes — to a non-owner, on a campus whose discovery gate was
closed. The denormalised columns are copies that **nothing re-derived**, and
the gated manager asks the gate question of the row it is given, so a child
that lies about its parent is visible while its parent is not. That is a
compliance failure, not a defect: it is a real student's listing reachable
before Gate C.

> **ADR-002 §2, verbatim:** *"A composite foreign key makes the inconsistency
> IMPOSSIBLE rather than detectable. One extra unique index on the parent and
> one `FOREIGN KEY` clause per child … A child row referencing a parent with
> a different campus, city or seed flag cannot be written, on either engine,
> by any path — service, admin, raw SQL, a migration, or a fixture. No
> trigger, no job, no window."*
>
> And the sentence that replaced the cto's own remedy: *"**Where a database
> can make a class of wrong state unrepresentable, that beats detecting it**
> — and I reached for a job when a constraint was available."*

**The nightly `city_id` consistency check ADR-002 §2 originally specified is
superseded by this, not dropped.** It was never written, and the second
composite FK here — `(campus_id, city_id) REFERENCES campuses (id, city_id)`
— is what replaces it: a scoped row can no longer name a city its campus is
not in, which is the property the job was going to look for a day late.
`tests/unit/test_tenant_identity.py::
test_the_nightly_city_check_is_superseded_rather_than_forgotten` is the record.

---

**Two mechanisms, one property, and the divergence is stated rather than
assumed** (`CLAUDE.md` rule 9's labelling rule).

* **PostgreSQL — VERIFIED HERE.** `ALTER TABLE … ADD CONSTRAINT … FOREIGN KEY
  (…) REFERENCES …`, which is exactly the DDL the ADR writes.
* **SQLite — VERIFIED HERE.** SQLite has no `ADD CONSTRAINT` at all, so a
  foreign key can only be added by **rebuilding the table**. That is done
  here for the two child tables, and the new `CREATE TABLE` is **derived from
  `sqlite_master` rather than retyped** — the existing statement is read back
  and the `FOREIGN KEY` clause is inserted before its closing parenthesis, so
  every column, CHECK and existing reference is carried across by
  construction and cannot drift from the models (rule 11).

**`listings` itself is NOT rebuilt on SQLite, and that is a deliberate
limit with a named cost.** Rebuilding it would drop
`listings_price_immutable` — SQLite triggers belong to the table — which is
precisely the defect accounts/0004 exists because of, and it would do so to
the one trigger P14 depends on. `listings`'s own `(campus_id, city_id)`
constraint is therefore a **trigger** on SQLite and a real FK on PostgreSQL.
The property is identical on both; the catalog shape is not, and
`ENGINE-DIVERGENCE.md` needs the row (flagged in the slice note —
`company/architecture/**` is cto's).

`# ponytail: a table rebuild on one engine, ALTER on the other. Ceiling: the
# rebuild is non-atomic, so a failure halfway leaves SQLite mid-migration.
# Acceptable because SQLite is the development engine (ADR-001 §2.2) and
# `migrate` from empty is the tested path; PostgreSQL, which production runs,
# does this as a single transactional ALTER. Upgrade path: none — SQLite will
# not grow ADD CONSTRAINT.`
"""

from django.db import migrations

#: The parent's identity tuple, ADR-002 §2's DDL verbatim. One definition,
#: read by both engine paths and by the index name below.
TENANT_IDENTITY = ("id", "campus_id", "city_id", "is_seed")

#: `(table, child columns, parent table, parent columns)` for every composite
#: FK this migration installs. Data rather than four copies of one statement,
#: so a fifth child is a row rather than a new code path.
COMPOSITE_FKS = [
    (
        "listing_photos",
        ("listing_id", "campus_id", "city_id", "is_seed"),
        "listings",
        TENANT_IDENTITY,
        "listing_photos_parent_tenant_fk",
    ),
    (
        "book_requests",
        ("campus_id", "city_id"),
        "campuses",
        ("id", "city_id"),
        "book_requests_campus_city_fk",
    ),
]

#: The same rule on tables that are **not** rebuilt on SQLite, because they
#: carry triggers a rebuild would drop. PostgreSQL gets the FK; SQLite gets
#: the trigger pair below.
CAMPUS_CITY_ONLY_PG = [
    ("listings", "listings_campus_city_fk"),
    ("prescribed_texts", "prescribed_texts_campus_city_fk"),
    ("users", "users_campus_city_fk"),
    ("user_tombstones", "user_tombstones_campus_city_fk"),
]


def _quote(columns):
    return ", ".join(f'"{column}"' for column in columns)


# --- PostgreSQL ------------------------------------------------------------


def _pg_forward(schema_editor):
    execute = schema_editor.execute
    # The parent half. `id` is already unique, so any superset is trivially
    # unique -- this index exists to be the FK's target, not to constrain.
    execute(
        f'CREATE UNIQUE INDEX IF NOT EXISTS listings_tenant_identity '
        f'ON listings ({_quote(TENANT_IDENTITY)})',
        None,
    )
    execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS campuses_city_identity '
        'ON campuses ("id", "city_id")',
        None,
    )
    for table, child_columns, parent, parent_columns, name in COMPOSITE_FKS:
        # ON DELETE CASCADE on the photo FK so it matches the single-column
        # `listing_id` FK the model already declares. Without it a listing
        # delete would fail on the composite constraint instead -- and while
        # deletion is tombstone-plus-purge and listings are not deleted, a
        # constraint that changes delete semantics as a side effect is a
        # change nobody asked for.
        cascade = " ON DELETE CASCADE" if parent == "listings" else ""
        execute(
            f'ALTER TABLE {table} ADD CONSTRAINT {name} '
            f'FOREIGN KEY ({_quote(child_columns)}) '
            f'REFERENCES {parent} ({_quote(parent_columns)}){cascade}',
            None,
        )
    for table, name in CAMPUS_CITY_ONLY_PG:
        execute(
            f'ALTER TABLE {table} ADD CONSTRAINT {name} '
            f'FOREIGN KEY ("campus_id", "city_id") '
            f'REFERENCES campuses ("id", "city_id")',
            None,
        )


def _pg_reverse(schema_editor):
    execute = schema_editor.execute
    for table, _c, _p, _pc, name in COMPOSITE_FKS:
        execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}", None)
    for table, name in CAMPUS_CITY_ONLY_PG:
        execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}", None)
    execute("DROP INDEX IF EXISTS listings_tenant_identity", None)
    execute("DROP INDEX IF EXISTS campuses_city_identity", None)


# --- SQLite ----------------------------------------------------------------


def _sqlite_table_sql(connection, table):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = %s", [table]
        )
        row = cursor.fetchone()
    if not row:
        raise RuntimeError(f"{table} does not exist, so it cannot be rebuilt")
    return row[0]


def _sqlite_objects_for(connection, table):
    """Every index and trigger SQLite recorded for `table`, with its DDL.

    Read back rather than retyped. A rebuild drops them, and a hand-written
    list of eight index names is a list that will be one short the first time
    somebody adds an index — which is how accounts/0004's defect happened,
    one table over.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE tbl_name = %s "
            "AND type IN ('index', 'trigger') AND sql IS NOT NULL",
            [table],
        )
        return [sql for (sql,) in cursor.fetchall()]


def _sqlite_rebuild_with_fk(schema_editor, table, child_columns, parent, parent_columns):
    """Recreate `table` with one extra FOREIGN KEY clause, keeping everything.

    SQLite's documented procedure, with the new `CREATE TABLE` **derived from
    the old one** so no column, CHECK or existing reference is retyped.
    """
    connection = schema_editor.connection
    original = _sqlite_table_sql(connection, table)
    extras = _sqlite_objects_for(connection, table)

    cascade = " ON DELETE CASCADE" if parent == "listings" else ""
    clause = (
        f', FOREIGN KEY ({_quote(child_columns)}) '
        f'REFERENCES "{parent}" ({_quote(parent_columns)}){cascade})'
    )
    closing = original.rfind(")")
    if closing == -1:  # pragma: no cover - a CREATE TABLE always has one
        raise RuntimeError(f"cannot parse the CREATE TABLE for {table}")
    rebuilt = original[:closing] + clause

    temporary = f"{table}__rebuild"
    rebuilt = rebuilt.replace(f'"{table}"', f'"{temporary}"', 1)

    execute = schema_editor.execute
    execute(rebuilt, None)
    execute(
        f'INSERT INTO "{temporary}" SELECT * FROM "{table}"', None
    )
    execute(f'DROP TABLE "{table}"', None)
    execute(f'ALTER TABLE "{temporary}" RENAME TO "{table}"', None)
    for sql in extras:
        execute(sql, None)


#: SQLite's stand-in for the `listings (campus_id, city_id)` FK, because
#: rebuilding `listings` would drop `listings_price_immutable`.
#:
#: **Both directions are guarded** — INSERT and UPDATE — because a constraint
#: that only checks inserts is a constraint an UPDATE walks past, which is
#: exactly the shape of the defect this migration exists to close.
SQLITE_CITY_TRIGGERS = (
    """
    CREATE TRIGGER {table}_campus_city_insert BEFORE INSERT ON "{table}"
    WHEN NEW.city_id IS NOT (SELECT city_id FROM campuses WHERE id = NEW.campus_id)
    BEGIN
      SELECT RAISE(ABORT,
        'ADR-002 section 2: city_id must be the city of campus_id. A row whose city disagrees with its campus is counted in the wrong city by every metric that groups by city.');
    END
    """,
    """
    CREATE TRIGGER {table}_campus_city_update BEFORE UPDATE ON "{table}"
    WHEN NEW.city_id IS NOT (SELECT city_id FROM campuses WHERE id = NEW.campus_id)
    BEGIN
      SELECT RAISE(ABORT,
        'ADR-002 section 2: city_id must be the city of campus_id. A row whose city disagrees with its campus is counted in the wrong city by every metric that groups by city.');
    END
    """,
)


def _sqlite_forward(schema_editor):
    execute = schema_editor.execute
    execute(
        f'CREATE UNIQUE INDEX IF NOT EXISTS "listings_tenant_identity" '
        f'ON "listings" ({_quote(TENANT_IDENTITY)})',
        None,
    )
    execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS "campuses_city_identity" '
        'ON "campuses" ("id", "city_id")',
        None,
    )
    for table, child_columns, parent, parent_columns, _name in COMPOSITE_FKS:
        _sqlite_rebuild_with_fk(
            schema_editor, table, child_columns, parent, parent_columns
        )
    for table, _name in CAMPUS_CITY_ONLY_PG:
        for template in SQLITE_CITY_TRIGGERS:
            execute(template.format(table=table), None)


def _sqlite_reverse(schema_editor):
    execute = schema_editor.execute
    for table, _name in CAMPUS_CITY_ONLY_PG:
        execute(f"DROP TRIGGER IF EXISTS {table}_campus_city_insert", None)
        execute(f"DROP TRIGGER IF EXISTS {table}_campus_city_update", None)
    execute('DROP INDEX IF EXISTS "listings_tenant_identity"', None)
    execute('DROP INDEX IF EXISTS "campuses_city_identity"', None)
    # The rebuilt child tables keep their composite FK on reverse. Dropping it
    # would need a second rebuild, and a reverse that recreates a table is a
    # reverse that can lose data -- the constraint is harmless to leave.


def _run(forward):
    def apply(apps, schema_editor):
        vendor = schema_editor.connection.vendor
        if vendor == "postgresql":
            (_pg_forward if forward else _pg_reverse)(schema_editor)
        elif vendor == "sqlite":
            (_sqlite_forward if forward else _sqlite_reverse)(schema_editor)
        else:
            raise RuntimeError(
                f"the tenant-identity composite FK is not written for {vendor!r}; "
                "ADR-001 §2.2 permits postgresql (production) and sqlite (local dev) only"
            )

    return apply


class Migration(migrations.Migration):
    # **Not atomic**, because the SQLite path needs `PRAGMA foreign_keys` off
    # while a table is dropped and renamed, and a pragma inside a transaction
    # is a no-op. PostgreSQL's path is a sequence of `ALTER TABLE`s, each
    # transactional on its own.
    atomic = False

    dependencies = [
        ("listings", "0002_price_immutable"),
        ("catalog", "0002_title_trigram_index"),
        ("accounts", "0005_sellertermsacceptance_alter_user_options_and_more"),
        ("core", "0008_least_privilege"),
    ]

    operations = [migrations.RunPython(_run(True), _run(False))]
