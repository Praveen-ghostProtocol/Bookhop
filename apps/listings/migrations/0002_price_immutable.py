"""P14's price-immutability trigger. ADR-003 §2.2.

**This is the sixth plpgsql body, and the first time this control can be
executed at all.** `POSTGRES-FIRST-RUN.md` §0 corrected "six bodies" to five
precisely because this one did not exist — `listings` is an S2 table — so
five security controls were verified by that run and this one was deferred
with its exact test shape written down in §3. That shape is now
`tests/unit/test_price_immutable.py`.

ADR-003 §2.2's reasoning, kept here because it is what stops someone adding a
price-history table later: *"a price-history table would let anyone
reconstruct 'the price at the moment of handover', which is functionally a
settled price. A seller who wants a different price withdraws the listing and
creates a new one."* The trigger is the ladder rung — **a DB constraint beats
app code** — and the service layer never issues an UPDATE naming the column,
so a legitimate transition never meets it.

**Both engines, because a guard on one engine is not a guard.** The bodies
differ (plpgsql vs `RAISE(ABORT)`) and the behaviour asserted is the same:
an UPDATE that changes `asking_price_paise` is refused with a message
containing `P14`, and an UPDATE that does not is unaffected.
`tests/unit/test_price_immutable.py` asserts **both limbs on both engines** —
the existence of the trigger *by name* (the diagnostic, so a failure says
which guard went missing) and the refusal *by behaviour* (the guarantee, which
fails however the property is lost: dropped trigger, replaced body, disabled
trigger, rebuilt table).

**`CLAUDE.md` rule 10's last bullet is why the test asserts the message and
not the exit status.** PostgreSQL resolves identifiers at the first execution
of *each branch*, so a body that is created cleanly can fail the first time
someone does the forbidden thing — and that failure still blocks the
operation, so it looks like the guard working. The test matches on `P14`.

**`ENABLE ALWAYS`**, like every other guard here (ENGINE-DIVERGENCE §3.6a):
`session_replication_role = 'replica'` is what a logical-replication apply
worker and some restore paths use, and a guard a restore bypasses is a guard
that is off exactly when a bad row is being written.

**No TRUNCATE trigger and no DELETE trigger on this table, deliberately.**
`listings` is not append-only — a row is withdrawn, not deleted, and the
retention purge is DATA-MODEL §10.2's job. What is immutable is one *column*,
so the guard is `BEFORE UPDATE` and nothing else. The append-only tables get
their TRUNCATE guards from `core/0002`; adding one here would imply a
guarantee this table does not make.
"""

from django.db import migrations

PG_FORWARD = """
CREATE OR REPLACE FUNCTION listings_price_is_immutable() RETURNS trigger AS $fn$
BEGIN
  IF NEW.asking_price_paise IS DISTINCT FROM OLD.asking_price_paise THEN
    RAISE EXCEPTION
      'P14: asking_price_paise is fixed at intake and cannot be changed '
      '(listing %). Withdraw the listing and create a new one.', OLD.id;
  END IF;
  RETURN NEW;
END $fn$ LANGUAGE plpgsql;

CREATE TRIGGER listings_price_immutable
  BEFORE UPDATE ON listings
  FOR EACH ROW EXECUTE FUNCTION listings_price_is_immutable();

ALTER TABLE listings ENABLE ALWAYS TRIGGER listings_price_immutable;
"""

PG_REVERSE = """
DROP TRIGGER IF EXISTS listings_price_immutable ON listings;
DROP FUNCTION IF EXISTS listings_price_is_immutable();
"""

SQLITE_FORWARD = [
    # `IS NOT` is SQLite's null-safe inequality -- the same semantics as
    # PostgreSQL's `IS DISTINCT FROM`. The column is NOT NULL, so the null
    # case cannot arise today; writing the null-safe form anyway means the
    # two bodies say the same thing rather than happening to agree.
    """
    CREATE TRIGGER listings_price_immutable BEFORE UPDATE ON listings
    WHEN NEW.asking_price_paise IS NOT OLD.asking_price_paise
    BEGIN
      SELECT RAISE(ABORT,
        'P14: asking_price_paise is fixed at intake and cannot be changed. Withdraw the listing and create a new one.');
    END;
    """,
]

SQLITE_REVERSE = ["DROP TRIGGER IF EXISTS listings_price_immutable;"]


def _run(statements_pg, statements_sqlite):
    def apply(apps, schema_editor):
        vendor = schema_editor.connection.vendor
        if vendor == "postgresql":
            # params=None, not the default (): psycopg's placeholder parser
            # reads the literal `%` in `RAISE ... , OLD.id` as an incomplete
            # placeholder otherwise, which kills `migrate` from empty. The
            # same escape hatch core/0002 documents at length.
            schema_editor.execute(statements_pg, None)
        elif vendor == "sqlite":
            for statement in statements_sqlite:
                schema_editor.execute(statement, None)
        else:
            raise RuntimeError(
                f"the price-immutability trigger is not written for {vendor!r}; "
                "ADR-001 §2.2 permits postgresql (production) and sqlite (local dev) only"
            )

    return apply


class Migration(migrations.Migration):
    dependencies = [("listings", "0001_initial")]

    operations = [
        migrations.RunPython(
            _run(PG_FORWARD, SQLITE_FORWARD),
            _run(PG_REVERSE, SQLITE_REVERSE),
        ),
    ]
