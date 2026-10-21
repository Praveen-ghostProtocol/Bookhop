"""The double-booking guard, as far as S0 can verify it.

DATA-MODEL §5 / API-CONTRACT §4.3: a second `accept_offer` on the same listing
cannot succeed, because of

    CREATE UNIQUE INDEX one_active_transfer_per_listing
      ON transfers (listing_id)
      WHERE state IN ('ACCEPTED','SCHEDULED','AWAITING_CONFIRMATION','DISPUTED');

**This file does not test the real constraint.** `transfers` is an S4 table and
does not exist. What it tests is the engine behaviour the guard rests on, on
whichever engine the suite is running, which is the one thing about the guard
that is worth knowing before S4:

  1. a partial unique index with an `IN (...)` predicate is actually enforced;
  2. it is enforced on UPDATE as well as INSERT — `accept_offer` moves an
     existing OFFERED row into ACCEPTED, so the UPDATE path is the real one;
  3. rows outside the predicate are unconstrained, so many OFFERED transfers
     per listing stay legal;
  4. Django's `UniqueConstraint(condition=...)` compiles to a partial index on
     this backend rather than silently dropping the condition.

`tests/api/test_double_booking.py` (N concurrent accepts, exactly one 2xx) is
S4's and is not written here. Read company/architecture/ENGINE-DIVERGENCE.md
§5 before treating a green run of this file as evidence about production.
"""

import pytest
from django.db import DatabaseError, connection, models, transaction

pytestmark = pytest.mark.django_db

ACTIVE_STATES = ("ACCEPTED", "SCHEDULED", "AWAITING_CONFIRMATION", "DISPUTED")


@pytest.fixture
def probe(db):
    """A table shaped like `transfers` for this one property, plus the index."""
    states = ", ".join(f"'{s}'" for s in ACTIVE_STATES)
    with connection.cursor() as cursor:
        cursor.execute(
            "CREATE TABLE _transfer_probe ("
            " id integer primary key, listing_id integer not null, state text not null)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX _one_active_transfer_per_listing "
            f"ON _transfer_probe (listing_id) WHERE state IN ({states})"
        )
    return "_transfer_probe"


def _insert(id_, listing_id, state):
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO _transfer_probe (id, listing_id, state) VALUES (%s, %s, %s)",
            [id_, listing_id, state],
        )


def test_engine_supports_partial_indexes(engine):
    assert connection.features.supports_partial_indexes, (
        f"{engine} does not support partial indexes; the double-booking guard "
        "in DATA-MODEL §5 cannot be expressed on it"
    )


def test_second_active_transfer_on_the_same_listing_is_rejected_on_insert(probe, engine):
    _insert(1, 100, "ACCEPTED")
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _insert(2, 100, "ACCEPTED")
    print(f"partial unique index enforced on INSERT: engine={engine}")


def test_moving_a_second_transfer_into_an_active_state_is_rejected_on_update(probe, engine):
    """The path `accept_offer` actually takes: OFFERED -> ACCEPTED by UPDATE."""
    _insert(1, 100, "ACCEPTED")
    _insert(2, 100, "OFFERED")
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE _transfer_probe SET state = 'ACCEPTED' WHERE id = 2")
    print(f"partial unique index enforced on UPDATE: engine={engine}")


@pytest.mark.parametrize("state", ACTIVE_STATES)
def test_every_active_state_in_the_predicate_collides(probe, state):
    _insert(1, 100, "ACCEPTED")
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _insert(2, 100, state)


def test_many_offered_transfers_per_listing_remain_legal(probe):
    _insert(1, 100, "OFFERED")
    _insert(2, 100, "OFFERED")
    _insert(3, 100, "DECLINED")
    _insert(4, 100, "CANCELLED")
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM _transfer_probe WHERE listing_id = 100")
        assert cursor.fetchone()[0] == 4


def test_a_terminal_transfer_does_not_block_a_new_one(probe):
    _insert(1, 100, "ACCEPTED")
    with connection.cursor() as cursor:
        cursor.execute("UPDATE _transfer_probe SET state = 'CANCELLED' WHERE id = 1")
    _insert(2, 100, "ACCEPTED")  # the listing relists; this must succeed


def test_django_uniqueconstraint_condition_compiles_to_a_partial_index(engine):
    """The S4 model will declare the index as a Django constraint, not raw SQL.

    Assert the ORM emits the `WHERE` clause on this backend instead of quietly
    producing a full unique index, which would reject legitimate repeat offers.

    The schema editor is instantiated rather than entered as a context manager:
    SQLite's editor refuses to start inside a transaction, and pytest-django
    runs every test in one. Nothing is executed -- `create_sql` only renders.
    """
    from apps.core.models import Campus

    constraint = models.UniqueConstraint(
        fields=["slug"],
        condition=models.Q(active=True),
        name="_probe_partial_unique",
    )
    editor = connection.schema_editor(collect_sql=True)
    sql = str(constraint.create_sql(Campus, editor)).upper()
    assert "WHERE" in sql, f"{engine}: UniqueConstraint(condition=...) lost its condition: {sql}"
    assert "UNIQUE" in sql


def test_a_django_condition_index_really_reaches_this_database(engine):
    """Not a rendering check: read the partial index migration 0001 created.

    `jobs_due_idx` is declared as `models.Index(condition=...)` and is the only
    conditional index S0 ships. If the condition were dropped between the model
    and the database, this is where it would show.
    """
    with connection.cursor() as cursor:
        if engine == "postgresql":
            cursor.execute("SELECT indexdef FROM pg_indexes WHERE indexname = 'jobs_due_idx'")
        else:
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='jobs_due_idx'")
        row = cursor.fetchone()
    assert row, "jobs_due_idx is missing"
    assert "WHERE" in row[0].upper(), f"{engine} dropped the index condition: {row[0]}"
