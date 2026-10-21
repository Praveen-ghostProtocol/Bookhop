"""ADR-002 §4.1(c) — a seed account and a real account can never transact.

The guarantee is `transfers CHECK (seller_is_seed = buyer_is_seed)`.
`transfers` is an S4 table (DATA-MODEL §5), so **the real assertion cannot run
in S0 and is skipped with the slice named.** What runs today is the engine
capability it rests on: that a two-column CHECK constraint of this exact shape
is enforced on whichever engine the suite is running.

Reported, not hidden: until S4, nothing in this repository prevents a seed and
a real account from forming a transfer, because nothing forms transfers.
"""

import pytest
from django.db import DatabaseError, connection, transaction

pytestmark = pytest.mark.django_db

TRANSFERS_EXISTS = False
try:  # pragma: no cover - flips to True in S4
    from django.apps import apps as _apps

    _apps.get_model("transfers", "Transfer")
    TRANSFERS_EXISTS = True
except Exception:
    pass


@pytest.mark.skipif(not TRANSFERS_EXISTS, reason="`transfers` is created in S4 (TASKS.md §2)")
def test_a_seed_account_cannot_transact_with_a_real_account():
    """S4 unskips this: insert a transfer with seller_is_seed != buyer_is_seed
    and assert the CHECK constraint rejects it."""
    from django.apps import apps as _apps

    Transfer = _apps.get_model("transfers", "Transfer")
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            Transfer.objects.create(seller_is_seed=True, buyer_is_seed=False)


def test_check_constraint_mechanism_is_enforced_on_this_engine(engine):
    """Verified today: this engine enforces `CHECK (a = b)` on INSERT and UPDATE.

    SQLite silently ignores some DDL it does not understand, so this is checked
    rather than assumed. It proves the mechanism on `engine`; it proves nothing
    about the real `transfers` constraint, which does not exist yet.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "CREATE TABLE _seed_probe ("
            " id integer primary key,"
            " seller_is_seed boolean not null,"
            " buyer_is_seed boolean not null,"
            " CHECK (seller_is_seed = buyer_is_seed))"
        )
        cursor.execute("INSERT INTO _seed_probe VALUES (1, 1, 1)")
        cursor.execute("INSERT INTO _seed_probe VALUES (2, 0, 0)")

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO _seed_probe VALUES (3, 1, 0)")

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE _seed_probe SET buyer_is_seed = 0 WHERE id = 1")
