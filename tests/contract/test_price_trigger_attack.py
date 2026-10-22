"""P14's price-immutability trigger, attacked the way the schema guard was.

**Why a second file when backend has `tests/unit/test_price_immutable.py`.**
This is not a re-assertion of that file. ADR-003 §2.2's control is *"the first
plpgsql body that could ever be executed"* (`POSTGRES-FIRST-RUN.md` §0a), and
`POSTGRES-FIRST-RUN.md` §1 item 1 is explicit about why an executable plpgsql
guard needs its refusal paths exercised one at a time:

> `check_function_bodies` validates plpgsql **syntax** at `CREATE FUNCTION`.
> It does **not** resolve identifiers inside the body — plpgsql resolves those
> at the first execution of **each branch**. So a guard can be created
> cleanly, pass every happy-path test, and fail the first time anyone triggers
> the thing it exists to forbid — **and that failure still blocks the
> operation, so it looks like the guard working.**

So the question this file asks is not *"is the column immutable"*. It is
**"which routes reach the trigger, which routes must not, and is the refusal
the right refusal"** — asked once per route, because each route is a different
SQL statement and the engine resolves each branch separately.

Three groups:

1. **Routes that must be refused**, by message text and not by exit status.
   `QuerySet.update`, `Model.save()` with the attribute changed,
   `save(update_fields=["asking_price_paise"])`, `bulk_update`, raw SQL, and
   an `UPDATE` that touches many rows at once.
2. **Routes that must NOT be refused**, because a guard that stops the
   product is a guard that gets dropped (`CLAUDE.md` rule 13). A status
   transition, a full `save()` that rewrites every column at its current
   value, a no-change write of the same price, and the real publish/withdraw
   journey over HTTP.
3. **The guard's own failure modes** — the structural limb against a gutted
   body (backend claims this; **verified here rather than taken**), a
   disabled trigger, and `session_replication_role = 'replica'`, which is the
   **only** thing `ENABLE ALWAYS` is for and which nothing had measured.

Written from ADR-003 §2.1–2.2, `DATA-MODEL.md` §3 and §6.1, and
`POSTGRES-FIRST-RUN.md` §1 — not from the migration, which QA read only to
learn the trigger's name.
"""

import pytest
from django.db import connection, transaction
from django.db.utils import DatabaseError

pytestmark = pytest.mark.django_db

#: ADR-003 §2.2's trigger, by the name the migration gives it.
TRIGGER = "listings_price_immutable"

#: The token `POSTGRES-FIRST-RUN.md` §1 item 1 requires every refusal to carry,
#: because an exit status cannot tell a guard's refusal apart from the guard
#: itself erroring at first execution of a branch.
REFUSAL_TOKEN = "P14"


def _listing_model():
    from django.apps import apps as django_apps

    return django_apps.get_model("listings", "Listing")


# --------------------------------------------------------------------------
# 1. every route that must be refused
# --------------------------------------------------------------------------


def test_a_queryset_update_is_refused_by_message(s2_listing):
    """The ORM's bulk path: one `UPDATE … SET asking_price_paise = …`."""
    Listing = _listing_model()
    with pytest.raises(DatabaseError, match=REFUSAL_TOKEN), transaction.atomic():
        Listing.all_objects.filter(id=s2_listing.id).update(asking_price_paise=1)


def test_a_model_save_with_a_changed_price_is_refused(s2_listing):
    """**The route a developer actually takes**, and a different statement from
    the one above: `save()` with no `update_fields` emits every column, so the
    changed price arrives in a `SET` list of twenty — which is exactly the
    shape a trigger comparing one column must still catch.
    """
    s2_listing.asking_price_paise = 99900
    with pytest.raises(DatabaseError, match=REFUSAL_TOKEN), transaction.atomic():
        s2_listing.save()


def test_a_targeted_save_of_only_the_price_is_refused(s2_listing):
    """`save(update_fields=["asking_price_paise"])` — a one-column `SET`, and
    the narrowest statement that can carry the attack."""
    s2_listing.asking_price_paise = 1
    with pytest.raises(DatabaseError, match=REFUSAL_TOKEN), transaction.atomic():
        s2_listing.save(update_fields=["asking_price_paise"])


def test_a_bulk_update_is_refused(s2_listing):
    """`bulk_update` builds a `CASE` expression rather than a plain `SET`, so
    it is a third distinct statement shape reaching the same trigger."""
    Listing = _listing_model()
    s2_listing.asking_price_paise = 12345
    with pytest.raises(DatabaseError, match=REFUSAL_TOKEN), transaction.atomic():
        Listing.all_objects.bulk_update([s2_listing], ["asking_price_paise"])


def test_a_raw_sql_update_is_refused(s2_listing):
    """The path ADR-002 §4.2 concedes the application layer cannot see, and
    the one a staff member with a `psql` prompt has."""
    with pytest.raises(DatabaseError, match=REFUSAL_TOKEN), transaction.atomic():
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE listings SET asking_price_paise = 1 WHERE id = %s",
                [s2_listing.id],
            )


def test_an_unqualified_update_across_the_whole_table_is_refused(s2_listing):
    """`UPDATE listings SET asking_price_paise = …` with **no WHERE** — the
    migration-script shape, where a single statement rewrites every price in
    the pilot. A row trigger fires per row, so one refusal aborts the lot;
    asserted because *"it worked on one row"* is not *"it works on the
    statement a migration writes"*.
    """
    with pytest.raises(DatabaseError, match=REFUSAL_TOKEN), transaction.atomic():
        with connection.cursor() as cur:
            cur.execute("UPDATE listings SET asking_price_paise = 500")


def test_the_refusal_is_the_guards_and_not_an_unresolved_identifier(s2_listing, engine):
    """**`POSTGRES-FIRST-RUN.md` §1 item 1, as an assertion rather than a note.**

    The worst failure of a plpgsql guard — a name that does not resolve at
    first execution — *also* aborts the statement, so the exit status is
    identical to the guard working. The message is the only thing that tells
    them apart, so the message is read: it must be the contract's refusal, and
    it must not be an `undefined_column`/`undefined_function` class error.
    """
    Listing = _listing_model()
    with pytest.raises(DatabaseError) as caught, transaction.atomic():
        Listing.all_objects.filter(id=s2_listing.id).update(asking_price_paise=7)

    text = str(caught.value)
    assert REFUSAL_TOKEN in text, text
    assert "fixed at intake" in text, (
        f"the refusal does not carry ADR-003 §2.2's reason: {text!r}"
    )
    for symptom in ("does not exist", "undefined", "syntax error"):
        assert symptom not in text.lower(), (
            f"this looks like the body failing to resolve rather than the "
            f"guard refusing, which aborts the statement either way: {text!r}"
        )
    if engine == "postgresql":
        cause = getattr(caught.value, "__cause__", None)
        sqlstate = getattr(getattr(cause, "diag", None), "sqlstate", None)
        assert sqlstate == "P0001", (
            f"a `RAISE EXCEPTION` with no condition is SQLSTATE P0001; got "
            f"{sqlstate!r}, which means something other than the guard raised"
        )
        assert str(s2_listing.id) in text, (
            "the PostgreSQL body interpolates `OLD.id` so an operator reading "
            f"a log knows which listing: {text!r}"
        )


def test_the_two_engine_bodies_refuse_the_same_thing_and_differ_only_where_recorded(engine):
    """**A cross-engine claim, labelled.** The migration says the two bodies
    *"say the same thing rather than happening to agree"*.

    **VERIFIED HERE** on whichever engine is running: the refusal carries
    `P14` and the contract's reason. **Recorded divergence:** the PostgreSQL
    body interpolates `OLD.id` and the SQLite body cannot, because SQLite's
    `RAISE(ABORT, …)` takes a literal. That is a real difference in operator
    value and it is asserted as a difference rather than smoothed over — a
    test that accepted either would stop noticing if PostgreSQL lost the id
    too.
    """
    if engine == "postgresql":
        with connection.cursor() as cur:
            cur.execute("SELECT prosrc FROM pg_proc WHERE proname = %s",
                        ["listings_price_is_immutable"])
            row = cur.fetchone()
        assert row, "ADR-003 §2.2's function is not installed"
        body = row[0]
        assert REFUSAL_TOKEN in body and "OLD.id" in body
    else:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT sql FROM sqlite_master WHERE type='trigger' AND name = %s",
                [TRIGGER],
            )
            row = cur.fetchone()
        assert row, "ADR-003 §2.2's trigger is not installed on SQLite"
        body = row[0]
        assert REFUSAL_TOKEN in body
        assert "OLD.id" not in body, (
            "SQLite's `RAISE(ABORT, …)` takes a literal, so the listing id "
            "cannot be interpolated. If this changed, the divergence note in "
            "the migration is out of date."
        )


# --------------------------------------------------------------------------
# 2. every route that must NOT be refused
# --------------------------------------------------------------------------
#
# `CLAUDE.md` rule 13: a guard that fires on the contracts it protects will be
# edited, not obeyed. Each of these is a legitimate write that touches the row
# the trigger guards, and each one is a way this control could have been
# built wrong in the direction nobody tests.


def test_a_status_transition_is_unaffected(s2_listing):
    """DATA-MODEL §6.1's `LIVE → WITHDRAWN`, straight through the ORM."""
    Listing = _listing_model()
    Listing.all_objects.filter(id=s2_listing.id).update(status="WITHDRAWN")
    s2_listing.refresh_from_db()
    assert s2_listing.status == "WITHDRAWN"


def test_a_full_save_that_rewrites_every_column_is_unaffected(s2_listing):
    """**The case the trigger is most likely to have got wrong.**

    `Model.save()` with no `update_fields` emits `asking_price_paise` in the
    `SET` list on *every* save, at its current value. A trigger written as
    *"was this column in the statement"* rather than *"did this column
    change"* would refuse every ordinary save in the product — and the fix
    under schedule pressure would be to drop the trigger.
    """
    s2_listing.condition = "FAIR"
    s2_listing.save()
    s2_listing.refresh_from_db()
    assert s2_listing.condition == "FAIR"


def test_writing_the_same_price_back_is_not_a_change(s2_listing):
    """`IS DISTINCT FROM` / `IS NOT` semantics, asserted as behaviour."""
    Listing = _listing_model()
    Listing.all_objects.filter(id=s2_listing.id).update(
        asking_price_paise=s2_listing.asking_price_paise
    )
    s2_listing.refresh_from_db()
    assert s2_listing.asking_price_paise == 30000


def test_the_publish_and_withdraw_journey_over_http_is_unaffected(
    client_as, seller, book
):
    """**The end-to-end half, because the unit routes above all bypass L2.**

    JOURNEYS J2: create → publish → withdraw, over real HTTP, each step
    rewriting `status`, `published_at`, `closed_at`, `purge_due_at` and
    `version` on a row whose price column is guarded. If the trigger fired
    anywhere in here the product would not work, and every unit test would
    still pass.
    """
    import json
    import uuid

    client = client_as(seller)

    def post(path, body):
        return client.post(
            path, data=json.dumps(body), content_type="application/json",
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )

    created = post("/api/v1/listings", {
        "accept_seller_terms": True, "book_id": book.id,
        "asking_price_paise": 45000, "condition": "AS_NEW",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    })
    assert created.status_code == 201, created.content[:300]
    listing = created.json()

    published = post(f"/api/v1/listings/{listing['id']}/publish",
                     {"expected_version": listing["version"]})
    assert published.status_code == 200, published.content[:300]

    withdrawn = post(f"/api/v1/listings/{listing['id']}/withdraw",
                     {"expected_version": published.json()["version"]})
    assert withdrawn.status_code == 200, withdrawn.content[:300]
    assert withdrawn.json()["status"] == "WITHDRAWN"
    assert withdrawn.json()["asking_price_paise"] == 45000, (
        "the price changed across the journey, which the trigger should have "
        "made impossible — so either it did not fire or the value was "
        "rewritten by a path that bypasses it"
    )


def test_the_contract_sanctioned_way_to_change_a_price_still_works(
    client_as, seller, book
):
    """ADR-003 §2.2 names the remedy: *"a seller who wants a different price
    withdraws the listing and creates a new one."* An immutability guard with
    no sanctioned alternative is a guard that gets argued away, so the
    alternative is asserted to exist.
    """
    import json
    import uuid

    client = client_as(seller)

    def post(path, body):
        return client.post(
            path, data=json.dumps(body), content_type="application/json",
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )

    first = post("/api/v1/listings", {
        "accept_seller_terms": True, "book_id": book.id,
        "asking_price_paise": 45000, "condition": "GOOD",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    }).json()
    assert post(f"/api/v1/listings/{first['id']}/withdraw",
                {"expected_version": first["version"]}).status_code == 200

    second = post("/api/v1/listings", {
        "accept_seller_terms": True, "book_id": book.id,
        "asking_price_paise": 39000, "condition": "GOOD",
        "annotation_level": "NONE", "damage_flags": [], "no_damage": True,
        "language": "en", "category": "PRESCRIBED_TEXTBOOK",
    })
    assert second.status_code == 201, second.content[:300]
    assert second.json()["asking_price_paise"] == 39000


# --------------------------------------------------------------------------
# 3. the guard's own failure modes
# --------------------------------------------------------------------------


def test_the_structural_limb_passes_against_a_gutted_body(engine, s2_listing):
    """**Backend claims a guard-for-the-guard shows this; verified here.**

    The slice note says *"a guard for the guard replaces the body with a no-op
    inside a rolled-back transaction and shows the structural limb still
    passing while the behavioural one fails."* That is a claim about this
    repository, so QA measures it rather than relaying it — and measures the
    **catalog** limb QA's own `test_postgres_catalog.py` uses, not the
    assertion backend wrote, so the two files are independent witnesses to the
    same property.
    """
    if engine != "postgresql":
        pytest.skip(
            "NOT VERIFIABLE ON THIS ENGINE (vendor=sqlite, slice=S2): "
            "replacing a body in place needs `CREATE OR REPLACE FUNCTION`. "
            "SQLite's trigger is its body, so gutting it means dropping and "
            "recreating it under the same name — a different attack, asserted "
            "by `test_a_dropped_trigger_is_caught_by_name` below."
        )
    Listing = _listing_model()
    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute(
                "CREATE OR REPLACE FUNCTION listings_price_is_immutable() "
                "RETURNS trigger AS $fn$ BEGIN RETURN NEW; END $fn$ LANGUAGE plpgsql"
            )
            cur.execute(
                "SELECT tgname, tgenabled FROM pg_trigger WHERE tgname = %s", [TRIGGER]
            )
            structural = cur.fetchone()

        assert structural == (TRIGGER, "A"), (
            "the structural limb should be **unmoved** by a gutted body — if "
            "it noticed, this demonstration proves nothing and the two-limb "
            "argument needs a different example"
        )

        Listing.all_objects.filter(id=s2_listing.id).update(asking_price_paise=1)
        s2_listing.refresh_from_db()
        assert s2_listing.asking_price_paise == 1, (
            "the no-op body did not take effect, so the behavioural limb was "
            "not actually defeated and this test demonstrates nothing"
        )
        transaction.set_rollback(True)


def test_a_dropped_trigger_is_caught_by_the_structural_limb(engine, s2_listing):
    """The other half: the limb that *does* notice, so neither is redundant.

    An existence check cannot see a gutted body; a behavioural check cannot
    say **which** guard went missing. Both failures are produced here so the
    division of labour is measured rather than argued.
    """
    Listing = _listing_model()
    with transaction.atomic():
        with connection.cursor() as cur:
            if engine == "postgresql":
                cur.execute(f"DROP TRIGGER {TRIGGER} ON listings")
                cur.execute("SELECT 1 FROM pg_trigger WHERE tgname = %s", [TRIGGER])
            else:
                cur.execute(f"DROP TRIGGER {TRIGGER}")
                cur.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name = %s",
                    [TRIGGER],
                )
            assert cur.fetchone() is None, "the drop did not take effect"

        Listing.all_objects.filter(id=s2_listing.id).update(asking_price_paise=2)
        s2_listing.refresh_from_db()
        assert s2_listing.asking_price_paise == 2, (
            "the price changed with no trigger present, which is the point; "
            "if it did not, something other than this trigger is enforcing "
            "immutability and the control is not where the ADR says it is"
        )
        transaction.set_rollback(True)


def test_a_disabled_trigger_is_caught_by_tgenabled_and_not_by_name(engine, s2_listing):
    """`ALTER TABLE … DISABLE TRIGGER` leaves the object in `pg_trigger` under
    its own name. A structural limb that asked only *"is it there"* would pass
    while the column was freely updatable — **the exact shape `CLAUDE.md`
    rule 9 was earned on**, one table over.
    """
    if engine != "postgresql":
        pytest.skip(
            "NOT VERIFIABLE ON THIS ENGINE (vendor=sqlite, slice=S2): SQLite "
            "has no `DISABLE TRIGGER`; a trigger is present or dropped, and "
            "the dropped case is asserted above."
        )
    Listing = _listing_model()
    with transaction.atomic():
        # `ALTER TABLE` refuses while the fixture's own inserts have deferred
        # FK trigger events outstanding. Firing them is not part of the
        # attack; it is the harness getting out of the way.
        connection.check_constraints()
        with connection.cursor() as cur:
            cur.execute(f"ALTER TABLE listings DISABLE TRIGGER {TRIGGER}")
            cur.execute(
                "SELECT tgname, tgenabled FROM pg_trigger WHERE tgname = %s", [TRIGGER]
            )
            name, enabled = cur.fetchone()

        assert name == TRIGGER, "a name check still passes against a disabled trigger"
        assert enabled == "D", f"expected tgenabled 'D' after DISABLE, got {enabled!r}"

        Listing.all_objects.filter(id=s2_listing.id).update(asking_price_paise=3)
        s2_listing.refresh_from_db()
        assert s2_listing.asking_price_paise == 3, (
            "a disabled trigger still refused, which would mean `tgenabled` "
            "is not what decides — and the whole `ENABLE ALWAYS` argument "
            "rests on it"
        )
        transaction.set_rollback(True)


def test_enable_always_survives_replica_session_replication_role(engine, s2_listing):
    """**The claim `ENABLE ALWAYS` exists for, measured instead of assumed.**

    ENGINE-DIVERGENCE §3.6a and the migration both say the mode matters
    because *"`session_replication_role = 'replica'` is what a logical
    replication apply worker and some restore paths use, and a guard a restore
    bypasses is a guard that is off exactly when a bad row is being written."*
    Nothing had executed that sentence. `ORIGIN`-mode triggers are skipped in
    replica mode; `ALWAYS` ones are not — so this is the difference between
    an immutable price and a price a restore can rewrite.

    **VERIFIED HERE** when the role can be set; it needs superuser, and on a
    box where the application role is not one this **skips naming the engine,
    the slice and the privilege**, because a pass would be the role refusing
    rather than the trigger firing.
    """
    if engine != "postgresql":
        pytest.skip(
            "NOT APPLICABLE ON THIS ENGINE (vendor=sqlite, slice=S2): SQLite "
            "has no `session_replication_role` and no logical replication, so "
            "there is no mode in which a trigger is skipped."
        )
    Listing = _listing_model()
    with transaction.atomic():
        try:
            with connection.cursor() as cur:
                cur.execute("SET LOCAL session_replication_role = 'replica'")
                cur.execute("SHOW session_replication_role")
                mode = cur.fetchone()[0]
        except DatabaseError as exc:
            transaction.set_rollback(True)
            pytest.skip(
                "NOT VERIFIABLE WITH THIS ROLE (vendor=postgresql, slice=S2): "
                "`SET session_replication_role` needs superuser and the "
                f"application role is not one on this box ({exc!r}). The "
                "`ENABLE ALWAYS` claim in ENGINE-DIVERGENCE §3.6a is therefore "
                "**ASSUMED THERE**, not verified here, and `INFRA.md` §3.3's "
                "restore test is where it has to be measured."
            )
        assert mode == "replica", mode
        with pytest.raises(DatabaseError, match=REFUSAL_TOKEN):
            Listing.all_objects.filter(id=s2_listing.id).update(asking_price_paise=4)
        transaction.set_rollback(True)


def test_the_trigger_is_not_claimed_to_guard_inserts_or_deletes(engine):
    """What the control does **not** promise, asserted so nobody quotes it as
    more than it is.

    The migration says it plainly: *"No TRUNCATE trigger and no DELETE trigger
    on this table, deliberately … what is immutable is one **column**, so the
    guard is `BEFORE UPDATE` and nothing else."* A reader who assumed this
    protected the row would be wrong, and ADR-003 §2.2's sanctioned remedy
    (withdraw and relist) depends on the row being deletable by retention.
    """
    if engine != "postgresql":
        with connection.cursor() as cur:
            cur.execute(
                "SELECT sql FROM sqlite_master WHERE type='trigger' AND name = %s",
                [TRIGGER],
            )
            sql = cur.fetchone()[0].upper()
        assert "BEFORE UPDATE" in sql
        assert "BEFORE DELETE" not in sql and "AFTER DELETE" not in sql
        return

    with connection.cursor() as cur:
        # tgtype bit 2 (4) is INSERT, bit 3 (8) is DELETE, bit 4 (16) is UPDATE.
        cur.execute("SELECT tgtype FROM pg_trigger WHERE tgname = %s", [TRIGGER])
        tgtype = cur.fetchone()[0]
    assert tgtype & 16, "the trigger does not fire on UPDATE"
    assert not tgtype & 4, "the trigger fires on INSERT, which it does not claim to"
    assert not tgtype & 8, "the trigger fires on DELETE, which it does not claim to"
    assert not tgtype & 32, "the trigger fires on TRUNCATE, which it does not claim to"
