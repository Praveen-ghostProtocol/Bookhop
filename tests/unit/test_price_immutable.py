"""ADR-003 §2.2 — the `listings_price_immutable` trigger exists and raises.

**This test is written now and skipped until S2**, per TASKS.md §2 S0: the
trigger lands with the `listings` table in S2 and a guard added after the thing
it guards is a guard that was never tested.

The skip is not a free pass. Two things make the deferral honest:
  * `tests/unit/test_forbidden_schema.py::
    test_the_only_money_column_is_the_listing_asking_price` already fails if a
    second money column appears anywhere, so S2 cannot add one quietly;
  * `test_trigger_mechanism_raises_on_this_engine` below verifies, on whichever
    engine the suite is running, that a BEFORE UPDATE trigger of exactly this
    shape does abort the statement. That is the engine capability the S2
    trigger depends on, and it is checked today.

The S2 trigger body is Postgres plpgsql and has no SQLite equivalent; see
company/architecture/ENGINE-DIVERGENCE.md §3.9 for what that means for
verifying P14 locally.
"""

import pytest
from django.db import DatabaseError, connection, transaction

pytestmark = pytest.mark.django_db

LISTINGS_EXISTS = False
try:  # pragma: no cover - flips to True in S2
    from django.apps import apps as _apps

    _apps.get_model("listings", "Listing")
    LISTINGS_EXISTS = True
except Exception:
    pass


@pytest.mark.skipif(not LISTINGS_EXISTS, reason="`listings` is created in S2 (TASKS.md §2)")
def test_asking_price_cannot_be_changed(s2_listing):
    """S2 unskips this. Create a listing, UPDATE the price, expect a raise.

    N10: the earlier version read `Listing.objects.first()` and asserted it was
    not None with no fixture creating one, so on the day S2 unskipped it the
    test would have errored rather than run. The `s2_listing` fixture below is
    the seam S2 fills in.
    """
    from django.apps import apps as _apps

    Listing = _apps.get_model("listings", "Listing")
    with pytest.raises(DatabaseError, match="P14"):
        with transaction.atomic():
            Listing.objects.filter(id=s2_listing.id).update(asking_price_paise=1)


@pytest.fixture
def s2_listing(db):
    """The one fixture S2 must supply for the two tests above to mean anything.

    It fails loudly rather than skipping, because by the time `listings` exists
    a missing fixture is a gap in S2's work, not a property of S0.
    """
    from django.apps import apps as _apps

    Listing = _apps.get_model("listings", "Listing")
    raise NotImplementedError(
        "S2 must create a LIVE seed listing here (ADR-003 §2.2's trigger needs a "
        f"row to refuse an UPDATE on). Model: {Listing}"
    )


@pytest.mark.skipif(not LISTINGS_EXISTS, reason="`listings` is created in S2 (TASKS.md §2)")
def test_the_trigger_object_exists_by_name():
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute("SELECT 1 FROM pg_trigger WHERE tgname = 'listings_price_immutable'")
        else:
            cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name='listings_price_immutable'"
            )
        assert cursor.fetchone(), "ADR-003 §2.2: the listings_price_immutable trigger is missing"


def test_trigger_mechanism_raises_on_this_engine(engine):
    """Does *this* engine abort an UPDATE from a BEFORE UPDATE trigger?

    Verified today so S2 is not the first time anyone finds out. This proves
    the mechanism on `engine`; it does not prove anything about the real
    `listings` trigger, which does not exist yet.
    """
    with connection.cursor() as cursor:
        cursor.execute("CREATE TABLE _price_probe (id integer primary key, p integer not null)")
        if engine == "sqlite":
            cursor.execute(
                "CREATE TRIGGER _price_probe_immutable BEFORE UPDATE ON _price_probe "
                "WHEN NEW.p IS NOT OLD.p "
                "BEGIN SELECT RAISE(ABORT, 'P14: asking_price_paise is fixed at intake'); END"
            )
        else:
            cursor.execute(
                "CREATE FUNCTION _price_probe_fn() RETURNS trigger AS $fn$ BEGIN "
                "IF NEW.p IS DISTINCT FROM OLD.p THEN "
                "RAISE EXCEPTION 'P14: asking_price_paise is fixed at intake'; END IF; "
                "RETURN NEW; END $fn$ LANGUAGE plpgsql"
            )
            cursor.execute(
                "CREATE TRIGGER _price_probe_immutable BEFORE UPDATE ON _price_probe "
                "FOR EACH ROW EXECUTE FUNCTION _price_probe_fn()"
            )
        cursor.execute("INSERT INTO _price_probe (id, p) VALUES (1, 30000)")

    with pytest.raises(DatabaseError, match="P14"):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE _price_probe SET p = 1 WHERE id = 1")
