"""The races, run for the first time — QA-S0 §7 items 3, 6, 7 and 8.

For three passes these were skips with an engine-and-slice reason, and
ENGINE-DIVERGENCE §10.6 is right that the reason was all they were: a bare
`pytest.skip()` whose f-string interpolated the live vendor into a sentence
about SQLite. Honest on SQLite, self-contradicting on PostgreSQL. **The
correction is taken, and these are the assertions written.**

Every test here needs `transactional_db`, because a race needs real committed
rows that other connections can see — which means every test here is also a
live exercise of the TRUNCATE escape, since the teardown flush is what
ENGINE-DIVERGENCE §7.1 and §10.3(b) are about. If the escape ever stops
reaching a connection, this file fails in teardown and names the reason.

What this file does **not** cover, stated once so nothing here is over-read:
double-booking. The partial unique index is on `transfers`, an S4 table that
does not exist. `test_the_idempotency_insert_is_the_lock` is a **rehearsal** of
the same mechanism — a unique index under real contention — on a table that
exists. A pass here predicts a pass there and is not one.
"""

import threading

import pytest
from django.db import DatabaseError, IntegrityError, connection, connections, transaction

from apps.core.errors import AuditAppendContention, AuditChainBroken
from apps.core.models import AuditLog, City, IdempotencyKey, Job
from apps.core.services import GENESIS_HASH, record_audit, verify_audit_chain

postgres_only = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason=(
        "REQUIRES PostgreSQL (slice=S0): every assertion in this file is about a "
        "race between real connections. SQLite has one database writer, so the "
        "race cannot occur and a green run would prove the mechanism's "
        "uniqueness rather than the concurrency property it was added for "
        "(ENGINE-DIVERGENCE §4.1, §4.5, §5.3). Run with "
        "BOOKHOP_DB_ENGINE=postgres."
    ),
)

pytestmark = [pytest.mark.django_db(transaction=True), postgres_only]


def _in_threads(work, n):
    """Run `work(i)` on `n` threads released together, and collect outcomes.

    A barrier rather than a stagger: without it the threads serialise by
    start-up latency and the contention being asserted never happens, which is
    the way a concurrency test most often passes for the wrong reason.
    """
    barrier = threading.Barrier(n)
    results, errors = [], []
    lock = threading.Lock()

    def runner(index):
        try:
            barrier.wait(timeout=30)
            value = work(index)
            with lock:
                results.append(value)
        except BaseException as exc:  # noqa: BLE001 - the outcome is the datum
            with lock:
                errors.append(exc)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=runner, args=(i,)) for i in range(n)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert not any(t.is_alive() for t in threads), "a worker thread did not finish"
    return results, errors


@pytest.fixture
def campus(db):
    city = City.objects.create(name="Chennai", state="Tamil Nadu")
    from apps.core.models import Campus

    return Campus.objects.create(city=city, name="Race Campus", slug="race")


# --------------------------------------------------------------------------
# item 6 — the audit chain under concurrent appenders
# --------------------------------------------------------------------------


@pytest.mark.parametrize("appenders", [12, 24])
def test_concurrent_appenders_cannot_fork_the_chain(campus, appenders):
    """**QA-S0 §7 item 6, written and run.** `DATA-MODEL.md` §8: `prev_hash` is
    UNIQUE so that two appenders reading the same head cannot both commit — the
    loser retries against the new head instead of forking.

    Three things are asserted, and the **row count is the one that matters
    most**: ENGINE-DIVERGENCE §10.3(a) found a dropped audit row at 12
    appenders, and a lost row with no exception is worse than a raised one
    because nothing signals it. A test that checked only `verify_audit_chain`
    would have passed while rows went missing — the chain of what survived is
    perfectly linear.

    12 and 24 because §10.3(a) measured the attempts-to-win tail growing with
    contention (5 attempts at 8 appenders, 7 at 24), so a single low number
    would not have exercised the budget.
    """
    before = AuditLog.objects.count()

    def append(index):
        row = record_audit(None, f"qa.race{index}", campus)
        return row.pk

    results, errors = _in_threads(append, appenders)

    assert errors == [], f"appenders failed: {[repr(e) for e in errors]}"
    assert len(results) == appenders
    assert AuditLog.objects.count() == before + appenders, (
        "an audit row was dropped. §10.3(a)'s defect: record_audit runs inside "
        "the mutation's transaction, so a dropped row means a failed mutation"
    )
    checked, _head = verify_audit_chain()
    assert checked == before + appenders
    assert len(set(AuditLog.objects.values_list("prev_hash", flat=True))) == checked, (
        "two rows share a prev_hash: the chain forked"
    )


def test_contention_is_not_reported_as_tamper(campus, monkeypatch):
    """**The first half of §10.3(a)'s diagnostic fix, verified.**

    Exhausting the retry budget used to raise `AuditChainBroken` — a class whose
    name asserts tampering — during an incident that establishes only write
    contention and in which the chain is provably intact. A load spike would
    have sent an operator hunting a tamper.

    Budget exhaustion is forced deterministically rather than by hoping a race
    loses 12 times: with the budget at zero the loop cannot run, which is
    exactly the state a real exhaustion ends in.

    Asserted: the class raised is `AuditAppendContention`, it is **not** an
    `AuditChainBroken` and not a subclass of one, and the chain still verifies —
    because the whole claim of the new class is that nothing is broken.
    """
    monkeypatch.setattr("apps.core.services.APPEND_MAX_ATTEMPTS", 0)

    with pytest.raises(AuditAppendContention) as exc:
        record_audit(None, "qa.contention", campus)

    assert not isinstance(exc.value, AuditChainBroken), (
        "contention still arrives as the tamper class; an alert on a broken "
        "chain would fire on a load spike"
    )
    assert not issubclass(AuditAppendContention, AuditChainBroken)
    assert not issubclass(AuditChainBroken, AuditAppendContention)
    verify_audit_chain()  # the chain is intact, which is the class's claim


def test_a_genuine_tamper_is_still_reported_as_tamper(campus):
    """**The second half, and the one that makes the fix a fix.**

    A change that made contention look like contention but also made a real
    tamper look like contention would be strictly worse than the bug it
    replaced — the obvious way to get this wrong. So the same two classes are
    asserted from the other direction: a rewritten row must still raise
    `AuditChainBroken`, and must **not** raise `AuditAppendContention`.

    The tamper is performed the way a tamperer would, with the guards disabled,
    on PostgreSQL.
    """
    rows = [record_audit(None, f"qa.step{i}", campus) for i in range(3)]

    with connection.cursor() as cur:
        cur.execute("ALTER TABLE audit_log DISABLE TRIGGER USER")
        cur.execute(
            "UPDATE audit_log SET action = 'qa.rewritten' WHERE id = %s", [rows[1].pk]
        )

    try:
        with pytest.raises(AuditChainBroken) as exc:
            verify_audit_chain()
        assert not isinstance(exc.value, AuditAppendContention), (
            "a real tamper is being reported as contention, which is worse than "
            "the defect this fix replaced"
        )
        assert str(rows[1].pk) in str(exc.value)
    finally:
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE audit_log SET action = 'qa.step1' WHERE id = %s", [rows[1].pk]
            )
            # Restore each guard to ENABLE ALWAYS by name. This test is
            # transactional, so the DDL is not rolled back for us, and
            # `ENABLE TRIGGER USER` would restore them as plain-enabled ('O')
            # -- silently undoing ENGINE-DIVERGENCE 3.6a for every later test.
            cur.execute(
                "SELECT tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                "WHERE c.relname = 'audit_log' AND NOT t.tgisinternal"
            )
            for (name,) in cur.fetchall():
                cur.execute(f'ALTER TABLE audit_log ENABLE ALWAYS TRIGGER "{name}"')
            cur.execute(
                "SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                "WHERE c.relname = 'audit_log' AND NOT t.tgisinternal AND t.tgenabled <> 'A'"
            )
            assert cur.fetchone()[0] == 0, "a guard was left off ENABLE ALWAYS"


def test_the_two_audit_failure_classes_are_distinguishable_by_an_alert(campus):
    """What the fix has to buy, stated as the property an on-call rota needs:
    a monitor can subscribe to the tamper class without being woken by
    contention, and neither class is reachable from the other by `except`.
    """
    assert AuditChainBroken.__mro__[1:] == AuditAppendContention.__mro__[1:], (
        "the two classes have different parents; one of them may be catchable "
        "by a handler written for the other"
    )
    common = set(AuditChainBroken.__mro__) & set(AuditAppendContention.__mro__)
    assert AuditChainBroken not in common and AuditAppendContention not in common


# --------------------------------------------------------------------------
# item 7 — "the insert of the key row is the lock"
# --------------------------------------------------------------------------


@pytest.mark.parametrize("user_id", [7, None], ids=["authenticated", "anonymous"])
def test_the_idempotency_insert_is_the_lock(user_id):
    """**QA-S0 §7 item 7, written and run.** API-CONTRACT §4.1: *"The insert of
    the key row is the lock, so two simultaneous retries cannot both execute."*

    That is a concurrency claim and SQLite satisfied it for the wrong reason —
    the database-level write lock, not the index. Both namespaces are raced,
    because they are enforced by **two different indexes**: `(user_id, key)` for
    an authenticated caller and the partial `key WHERE user_id IS NULL` that
    migration 0004 added for QA-S0 B3.

    Asserted: exactly one winner, exactly one row, and every loser arrives as a
    service error the API layer can turn into a response — not as a raw
    database error, which would become a 500 on a path whose whole purpose is
    making a retry safe.
    """
    import uuid

    from apps.core.errors import IdempotencyInProgress, IdempotencyKeyReused
    from apps.core.services import idempotent

    key = str(uuid.uuid4())
    endpoint = "POST /api/v1/grievances"
    body = {"body": "a complaint"}

    def claim(_index):
        try:
            return ("won", idempotent(user_id, key, endpoint, body).pk)
        except (IdempotencyInProgress, IdempotencyKeyReused) as exc:
            return ("lost", type(exc).__name__)

    results, errors = _in_threads(claim, 12)

    assert errors == [], (
        "a loser escaped as something other than a service error, so the API "
        f"layer would render a 500 instead of a 409: {[repr(e) for e in errors]}"
    )
    won = [r for r in results if r[0] == "won"]
    assert len(won) == 1, f"expected exactly one winner, got {len(won)}"
    assert IdempotencyKey.objects.filter(key=key).count() == 1
    assert all(r[1] == "IdempotencyInProgress" for r in results if r[0] == "lost")


def test_the_losers_outer_transaction_survives_the_unique_violation():
    """The Django trap ENGINE-DIVERGENCE §10.4 item 8 names, asserted as a
    **negative control** so it cannot pass vacuously.

    On PostgreSQL a failed statement poisons the whole transaction unless it is
    wrapped in a savepoint. `services.idempotent()` has its own `atomic()`
    around the insert for that reason, and S4's `accept_offer` must keep it.

    Both directions are measured: with the savepoint the loser's outer
    transaction is still usable (so a `409` is renderable), and **without** one
    the same violation leaves the transaction broken. A control that did not
    actually fail would be the most convincing possible way to be wrong.
    """
    import uuid

    from apps.core.errors import IdempotencyInProgress
    from apps.core.services import idempotent

    key = str(uuid.uuid4())
    idempotent(7, key, "POST /a", {"x": 1})

    # With the savepoint: the service raises, and the connection is still usable.
    with transaction.atomic():
        with pytest.raises(IdempotencyInProgress):
            idempotent(7, key, "POST /a", {"x": 1})
        assert IdempotencyKey.objects.filter(key=key).count() == 1  # a query works

    # Without one: the same violation, raised by a bare insert, poisons it.
    from django.db.transaction import TransactionManagementError

    with transaction.atomic():
        with pytest.raises(IntegrityError):
            IdempotencyKey.objects.create(
                user_id=7, key=key, endpoint="POST /a", request_hash="x",
                expires_at=_one_hour(),
            )
        with pytest.raises(TransactionManagementError):
            IdempotencyKey.objects.filter(key=key).count()


def _one_hour():
    from datetime import timedelta

    from django.utils import timezone

    return timezone.now() + timedelta(hours=1)


# --------------------------------------------------------------------------
# item 8 — job claiming under two real workers
# --------------------------------------------------------------------------


def test_two_job_workers_cannot_claim_the_same_job():
    """**QA-S0 §7 item 8, written and run** — and ENGINE-DIVERGENCE §4.3 records
    this property as `UNVERIFIED` **on both engines**, so it is the only item on
    the checklist that had never been exercised anywhere.

    ADR-001 §2.4 specified `SELECT … FOR UPDATE SKIP LOCKED`; §4.3 records the
    deviation to a compare-and-swap `UPDATE … WHERE id = ? AND locked_at IS
    NULL`, on the grounds that the ADR's mechanism is a silent no-op on SQLite
    and that the compare-and-swap has the same single-claim property. **That
    equivalence is the claim this test checks**, with 12 workers on 12 real
    connections against one job.

    At-least-once delivery means a double claim is a double run, and from S1 the
    first job is `retention.purge` — a DPDP r.8(3) obligation.
    """
    job = Job.objects.create(kind="core.noop", payload={})

    def claim(index):
        claimed = Job.objects.filter(pk=job.pk, locked_at__isnull=True).update(
            locked_at=_one_hour(), locked_by=f"worker-{index}"
        )
        return claimed

    results, errors = _in_threads(claim, 12)

    assert errors == [], f"a worker raised: {[repr(e) for e in errors]}"
    assert sum(results) == 1, (
        f"{sum(results)} workers claimed one job; at-least-once became "
        "at-least-twice, and every handler would run twice"
    )
    job.refresh_from_db()
    assert job.locked_by is not None and job.locked_at is not None


# --------------------------------------------------------------------------
# item 3 — the flush escape survives a connection close mid-run
# --------------------------------------------------------------------------


def test_the_flush_escape_survives_connections_being_closed_mid_test():
    """**QA-S0 §7 item 3, written and run — and it is the regression test for
    ENGINE-DIVERGENCE §10.3(b).**

    The escape is a session GUC: it lives on a *connection*. The old
    session-scoped fixture `SET` it once, binding it to whichever connection
    existed at setup, so **any close reopened a connection without it** —
    measured by backend: one test that used threads and called
    `connections.close_all()`, and the *next* transactional test died in
    teardown on `TRUNCATE "cities", "jobs", …`.

    That is QA-S0 F9's prediction cashing in, and it would have landed on S4's
    `test_double_booking.py`, which needs `transactional_db` **and** several
    real connections — both halves at once.

    This test performs the exact sequence that broke it: close every connection
    mid-test, then force a brand-new connection and assert the escape is live on
    it. Every test in this file also closes connections in its worker threads,
    so the whole file is a continuous exercise of the fix; this one asserts it
    directly rather than relying on a teardown that might be silent.
    """
    def read_escape():
        with connection.cursor() as cur:
            cur.execute("SELECT current_setting('bookhop.allow_flush', true)")
            return cur.fetchone()[0]

    assert read_escape() == "yes", "the escape is not live on the initial connection"

    connections.close_all()
    assert connection.connection is None, "the connection did not actually close"

    # A fresh connection, opened by this query, must carry the declaration.
    assert read_escape() == "yes", (
        "a connection opened after close_all() has no flush escape — "
        "ENGINE-DIVERGENCE §10.3(b) has regressed, and the next transactional "
        "teardown will fail on TRUNCATE"
    )

    # And the thing the escape exists for actually works on that connection.
    record_audit(None, "qa.flush", City.objects.create(name="X", state="Y"))
    with connection.cursor() as cur:
        cur.execute('TRUNCATE "audit_log"')
    assert AuditLog.objects.count() == 0


def test_the_escape_is_live_on_a_connection_opened_inside_a_thread():
    """The other half of §10.3(b): `connection_created` must fire for a
    connection a worker thread opens, not only for the main one. Every race
    test above depends on this, and a failure here would surface as a teardown
    error in an unrelated test — which is how the original defect presented.
    """
    seen = []

    def read(_index):
        with connections["default"].cursor() as cur:
            cur.execute("SELECT current_setting('bookhop.allow_flush', true)")
            seen.append(cur.fetchone()[0])
        return True

    _results, errors = _in_threads(read, 4)
    assert errors == [], [repr(e) for e in errors]
    assert seen == ["yes"] * 4, f"a thread's own connection lacked the escape: {seen}"


# --------------------------------------------------------------------------
# what the retry budget does not cover
# --------------------------------------------------------------------------


def test_finding_the_retry_budget_is_sized_for_an_empty_table_not_a_loaded_one(campus):
    """**FINDING F16, non-blocking, S1/S4.** The budget of 12 was sized from 40
    appenders on a near-empty `audit_log`, and that is not the shape production
    has.

    Two things make a loaded table harder than the measurement, and neither is
    in it:

    1. **Every retry re-reads the head** with
       `ORDER BY -id LIMIT 1`, so each attempt is an index scan whose cost is
       independent of table size — but the *window* between reading the head and
       committing grows with the row's own insert cost, and that grows with
       index maintenance on a table that is append-only and never pruned
       (`audit_log` cannot be deleted from). More time in the window is more
       chance of losing the race.
    2. **The real appenders are not symmetric.** The measurement raced 40
       identical `record_audit` calls. Production races one long mutation
       holding its transaction open (a moderation action with
       `work_seconds`) against many short ones, and the long one is the one that
       cannot afford to lose — it has the most work to discard.

    What QA can assert here is narrow and is asserted: the **class** on
    exhaustion is the contention class, so whatever the right budget turns out
    to be, exceeding it is diagnosable rather than misleading. What QA cannot
    assert is that 12 is enough, because the subject is a load profile that does
    not exist yet.

    The cheap instrument is one line and belongs with S1's first real write
    volume: count the attempts each append needed and expose the distribution,
    so the budget is set from production contention instead of from a bench.
    **`DATA-MODEL.md` §8's own upgrade path — print the daily chain head — does
    not help here;** this is a different failure, and nothing currently reports
    how close to the budget a normal day runs.
    """
    import apps.core.services as services

    assert services.APPEND_MAX_ATTEMPTS == 12
    assert services.APPEND_BACKOFF_SECONDS > 0, (
        "without backoff every loser re-reads the same head and spends the "
        "budget on self-inflicted collisions"
    )
    # The only assertion available: exhaustion is diagnosable.
    import pytest as _pytest

    with _pytest.MonkeyPatch.context() as mp:
        mp.setattr("apps.core.services.APPEND_MAX_ATTEMPTS", 0)
        with pytest.raises(AuditAppendContention):
            record_audit(None, "qa.budget", campus)
