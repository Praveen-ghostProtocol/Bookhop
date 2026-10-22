"""ADR-003 §2.2 — `listings_price_immutable` exists **and** the property holds.

**S0 wrote this file skipped and S2 unskips it.** It is the sixth plpgsql body
and the first time this control can be executed at all: `POSTGRES-FIRST-RUN.md`
§0 corrected *"six bodies"* to five because `listings` is an S2 table, and §3
recorded the exact shape to test when the table arrived —

> `UPDATE listings SET asking_price_paise = …` raises; a no-op update of other
> columns succeeds; the trigger exists and is `ENABLE ALWAYS`

— which is what this file now asserts, on **both** engines.

**Both limbs, and the second is the guarantee** (`CLAUDE.md` rule 9,
THREAT-MODEL §6.3). An existence check **diagnoses**: it fails by name, so the
message says which guard went missing. A behavioural check **guarantees**: it
fails whenever the property is gone, by any cause — dropped trigger, replaced
body, disabled trigger, rebuilt table. **A trigger whose body is replaced with
a no-op passes an existence check**, which is exactly the defect that was
found once already on `audit_log`, where a surviving sibling trigger satisfied
the structural limb while the table was freely updatable.

**The behavioural limb asserts the message text, not the exit status**
(rule 10's last bullet). PostgreSQL validates plpgsql syntax at creation but
resolves identifiers and operators at the first execution of *each branch*, so
a body can be created cleanly, pass every happy path, and fail the first time
someone does the forbidden thing — **and the worst form of that failure still
blocks the UPDATE, so it looks like the guard working.** Matching on `P14`
distinguishes the guard firing from the guard crashing.

**And the negative control is not optional either.** A trigger that refused
*every* UPDATE would pass a naive version of this file while breaking every
state transition in DATA-MODEL §6.1 — so the no-op case is asserted as
deliberately as the refusal.
"""

import pytest
from django.db import DatabaseError, connection, transaction

pytestmark = pytest.mark.django_db

#: The trigger's name on both engines, and the plpgsql function's name on
#: PostgreSQL. One definition, so the structural limb's message names the
#: thing a developer would grep for.
TRIGGER_NAME = "listings_price_immutable"
FUNCTION_NAME = "listings_price_is_immutable"


# --- limb (b): the behavioural guarantee ----------------------------------


def test_asking_price_cannot_be_changed(s2_listing):
    """**The guarantee.** An UPDATE that changes the price is refused.

    Issued as a raw queryset `.update()` rather than through the service
    layer, deliberately: the service never writes this column, so routing
    through it would test the service's restraint rather than the database's
    refusal. ADR-003 §2.2's whole argument is that *a DB constraint beats app
    code*, and the thing being asserted is the database.
    """
    from django.apps import apps as django_apps

    Listing = django_apps.get_model("listings", "Listing")
    with pytest.raises(DatabaseError, match="P14"):
        with transaction.atomic():
            Listing.all_objects.filter(id=s2_listing.id).update(asking_price_paise=1)

    s2_listing.refresh_from_db()
    assert s2_listing.asking_price_paise == 30000, (
        "the UPDATE raised but the value changed, which would mean the "
        "exception came from somewhere after the write"
    )


def test_the_refusal_names_p14_rather_than_merely_failing(s2_listing):
    """**Rule 10's last bullet, as its own assertion.**

    A guard that crashes on an unresolvable identifier *also* blocks the
    UPDATE, so "the statement failed" proves nothing about why. The message is
    the only thing that distinguishes the control working from the control
    being broken in the way that looks like working.
    """
    from django.apps import apps as django_apps

    Listing = django_apps.get_model("listings", "Listing")
    with pytest.raises(DatabaseError) as caught:
        with transaction.atomic():
            Listing.all_objects.filter(id=s2_listing.id).update(asking_price_paise=99)
    message = str(caught.value)
    assert "P14" in message, message
    assert "asking_price_paise" in message, message
    assert "fixed at intake" in message, message


def test_an_update_that_does_not_touch_the_price_succeeds(s2_listing):
    """**The negative control, and it is not decoration.**

    A trigger that refused every UPDATE would pass the two tests above and
    break every transition in DATA-MODEL §6.1 — `publish`, `withdraw`,
    `RESERVED`, the optimistic-concurrency version bump. Asserting that the
    guard is *narrow* is asserting that the product still works.
    """
    from django.apps import apps as django_apps

    Listing = django_apps.get_model("listings", "Listing")
    changed = Listing.all_objects.filter(id=s2_listing.id).update(
        status="WITHDRAWN", version=s2_listing.version + 1
    )
    assert changed == 1
    s2_listing.refresh_from_db()
    assert s2_listing.status == "WITHDRAWN"
    assert s2_listing.asking_price_paise == 30000


def test_writing_the_same_price_back_is_not_a_change(s2_listing):
    """`IS DISTINCT FROM` / `IS NOT`, asserted rather than assumed.

    An ORM `save()` writes every column, including the unchanged price, so if
    the trigger compared with `<>` or `!=` **every** `listing.save()` would
    raise — and the two engines spell null-safe inequality differently, which
    is exactly the kind of difference that is true on one and not the other
    (`CLAUDE.md` rule 9's labelling rule). **VERIFIED HERE on both.**
    """
    s2_listing.condition = "FAIR"
    s2_listing.save()
    s2_listing.refresh_from_db()
    assert s2_listing.condition == "FAIR"
    assert s2_listing.asking_price_paise == 30000


def test_the_service_layer_has_no_path_that_writes_the_price_twice(s2_listing, seller):
    """The layer above the trigger, so the student never meets it.

    ADR-003 §2.2's remedy is *"withdraw the listing and create a new one"*.
    There is no `update_price`, no `set_price` and no service signature that
    takes a price other than `create_listing` — asserted over the module's
    public names rather than by reading it, so a function added later is
    caught.
    """
    import inspect

    from apps.listings import services

    takers = [
        name
        for name, fn in vars(services).items()
        if callable(fn) and not name.startswith("_") and getattr(fn, "__module__", "") == services.__name__
        and "asking_price_paise" in inspect.signature(fn).parameters
    ]
    assert takers == ["create_listing"], (
        "only `create_listing` may take a price; ADR-003 §2.2's remedy for a "
        f"wrong price is withdraw-and-relist. Found: {takers}"
    )


# --- limb (a): the structural diagnostic ----------------------------------


def test_the_trigger_object_exists_by_name(engine):
    """**The diagnostic.** It fails by *name*, so the cause is in the message.

    Redundant against the behavioural limb on the day everything works, and
    not redundant on the day something goes missing: *"UPDATE is refused"*
    tells you the property is broken, *"these exact triggers exist"* tells you
    which one went.
    """
    with connection.cursor() as cursor:
        if engine == "postgresql":
            cursor.execute("SELECT 1 FROM pg_trigger WHERE tgname = %s", [TRIGGER_NAME])
        else:
            cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=?", [TRIGGER_NAME]
            )
        assert cursor.fetchone(), f"ADR-003 §2.2: the {TRIGGER_NAME} trigger is missing"


def test_the_trigger_is_enable_always(engine):
    """ENGINE-DIVERGENCE §3.6a. PostgreSQL only, **skipped with its reason**.

    `session_replication_role = 'replica'` is what a logical-replication apply
    worker and some restore paths use, so a guard that is not `ENABLE ALWAYS`
    is a guard a restore silently bypasses — which is precisely when a bad row
    is being written. SQLite has no equivalent concept at all, so this skips
    naming the engine rather than passing (`CLAUDE.md` rule 10).
    """
    if engine != "postgresql":
        pytest.skip(
            "ENABLE ALWAYS is a PostgreSQL concept: SQLite has no "
            "session_replication_role and no per-trigger enablement, so this "
            "property cannot be tested on sqlite (slice S2)."
        )
    with connection.cursor() as cursor:
        cursor.execute("SELECT tgenabled FROM pg_trigger WHERE tgname = %s", [TRIGGER_NAME])
        row = cursor.fetchone()
    assert row, f"{TRIGGER_NAME} is not installed"
    assert row[0] == "A", (
        f"{TRIGGER_NAME} is tgenabled={row[0]!r}, not 'A'. A restore or a "
        "replication apply worker bypasses it."
    )


def test_the_plpgsql_function_exists_and_is_a_trigger_function(engine):
    """The sixth body, installed. `POSTGRES-FIRST-RUN.md` §3's deferred row."""
    if engine != "postgresql":
        pytest.skip(
            "plpgsql does not exist on sqlite; the SQLite half of this guard "
            "is a RAISE(ABORT) trigger, asserted by the behavioural limb above "
            "(slice S2)."
        )
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'public' AND p.proname = %s "
            "AND p.prorettype = 'trigger'::regtype",
            [FUNCTION_NAME],
        )
        assert cursor.fetchone(), f"{FUNCTION_NAME}() is missing"


def test_a_no_op_body_would_pass_the_existence_check_and_fail_the_behaviour(engine, s2_listing):
    """**The guard-for-the-guard, and the reason both limbs ship.**

    The claim *"an existence check cannot catch a replaced body"* is a claim
    about this codebase, so it is measured rather than asserted: the body is
    replaced with a no-op inside a transaction that is rolled back, and the
    two limbs are run against it. The structural limb still passes. The
    behavioural limb fails. That is the whole argument for rule 9's "ship
    both", demonstrated on the control it was written about.
    """
    if engine != "postgresql":
        pytest.skip(
            "replacing a trigger body in place needs CREATE OR REPLACE FUNCTION, "
            "which sqlite does not have — on sqlite the equivalent is dropping "
            "and recreating the trigger, which the structural limb would catch "
            "by name (slice S2)."
        )
    from django.apps import apps as django_apps

    Listing = django_apps.get_model("listings", "Listing")
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE OR REPLACE FUNCTION listings_price_is_immutable() "
                "RETURNS trigger AS $fn$ BEGIN RETURN NEW; END $fn$ LANGUAGE plpgsql"
            )
            # Limb (a) still passes against the gutted guard.
            cursor.execute("SELECT 1 FROM pg_trigger WHERE tgname = %s", [TRIGGER_NAME])
            assert cursor.fetchone(), "the trigger object is still there, by name"
        # Limb (b) does not.
        Listing.all_objects.filter(id=s2_listing.id).update(asking_price_paise=1)
        s2_listing.refresh_from_db()
        assert s2_listing.asking_price_paise == 1, (
            "the no-op body did not take effect, so this test is not "
            "demonstrating what it claims"
        )
        transaction.set_rollback(True)


# --- the engine capability this all rests on ------------------------------


def test_trigger_mechanism_raises_on_this_engine(engine):
    """Does *this* engine abort an UPDATE from a BEFORE UPDATE trigger?

    Written in S0 against a probe table so S2 would not be the first time
    anyone found out. Kept, because it still separates *"our trigger is
    wrong"* from *"this engine does not do that"* when the behavioural limb
    goes red.
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
