"""`audit_log.prev_hash UNIQUE` under genuine concurrent appenders — ENGINE-DIVERGENCE §4.5.

**The defect this file exists for was shipped in S0 with a green suite, and only
a PostgreSQL server could find it.** `record_audit` retries the `prev_hash`
race, and the budget was 4 attempts with no backoff. Measured on the first
PostgreSQL run, 12 appenders on 12 real connections: one lost four straight
races, **its audit row was dropped**, and the exception it raised was
`AuditChainBroken` — so a load spike would have failed a user's mutation with a
tamper-shaped error while the chain was perfectly intact. The attempts-to-win
tail grows with contention: a winner needed 5 attempts at 8 appenders and 7 at
24, so 4 was already below the observed need.

SQLite has **one database writer**, so this race cannot occur there at all
(§4.1). That is the whole reason a budget too small by a factor of two survived
S0: every concurrency assertion in the repository passed for a reason that does
not exist in production, exactly as §4 warned.

Two tests, because two different things were wrong:
  * the **budget** — a lost race dropped a row. Needs real concurrency, so it
    runs on PostgreSQL and skips on SQLite with the engine named.
  * the **diagnostic** — exhausting the budget claimed the chain was broken.
    That is engine-independent and runs everywhere.
"""

import threading

import pytest
from django.db import connection, connections

from apps.core import services
from apps.core.errors import AuditAppendContention, AuditChainBroken  # noqa: F401
from apps.core.models import AuditLog, City

APPENDERS = 16


@pytest.mark.django_db(transaction=True)
def test_concurrent_appenders_all_land_and_the_chain_stays_linear():
    """N simultaneous appenders: every row lands, and the chain verifies.

    `transaction=True` is required — the appenders are separate connections and
    must see each other's committed rows, which a single rolled-back
    transaction cannot provide. That makes teardown a real flush, which is why
    `tests/unit/test_transactional_teardown.py` exists.
    """
    if connection.vendor != "postgresql":
        pytest.skip(
            f"NOT VERIFIABLE ON THIS ENGINE (vendor={connection.vendor}, slice=S0): "
            "SQLite has one database writer, so concurrent appenders are "
            "serialised by the database-level write lock rather than by "
            "`prev_hash UNIQUE`, and a loser typically fails with 'database is "
            "locked' instead of the integrity error this retry loop exists for. "
            "A green run here would measure the write lock, not the guard "
            "(ENGINE-DIVERGENCE §4.1, §4.5, and §5.3's instruction to test-qa)."
        )

    city = City.objects.create(name="RaceCity", state="TN")
    barrier = threading.Barrier(APPENDERS)
    outcomes, lock = [], threading.Lock()

    def appender(i):
        try:
            barrier.wait(timeout=30)
            services.record_audit(services.SYSTEM, "race.probe", city)
            verdict = "ok"
        except Exception as exc:  # noqa: BLE001 - the verdict IS the assertion
            verdict = f"{type(exc).__name__}: {exc}"
        finally:
            # Each thread owns its connection; pytest-django does not close it.
            connections.close_all()
        with lock:
            outcomes.append(verdict)

    threads = [threading.Thread(target=appender, args=(i,)) for i in range(APPENDERS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    losers = [o for o in outcomes if o != "ok"]
    assert not losers, (
        f"{len(losers)} of {APPENDERS} concurrent appenders failed and their "
        f"audit rows were dropped. Raise services.APPEND_MAX_ATTEMPTS -- never "
        f"lower this test's APPENDERS, and never drop the row: {losers}"
    )
    assert len(outcomes) == APPENDERS, "a thread never reported; it is still running or died"

    rows, _head = services.verify_audit_chain()
    assert rows == APPENDERS, (
        f"the chain verifies but holds {rows} rows, not {APPENDERS}: a row was "
        f"lost without any appender reporting a failure, which is worse than a "
        f"raised exception because nothing signals it"
    )


@pytest.mark.django_db
def test_losing_the_race_is_not_reported_as_a_broken_chain(city, monkeypatch):
    """Contention and tampering are different incidents and must not share a class.

    `CLAUDE.md` rule 9: the claim and the check are one artefact. `record_audit`
    exhausting its retry budget establishes *write contention*; it establishes
    nothing about the chain's integrity, and the chain is in fact intact. An
    alert on `AuditChainBroken` firing during a load spike spends an operator's
    incident on a tamper that did not happen.

    Forced by setting the budget to zero rather than by racing, so this runs on
    both engines — the race itself cannot be produced on SQLite.
    """
    monkeypatch.setattr(services, "APPEND_MAX_ATTEMPTS", 0)

    with pytest.raises(AuditAppendContention) as caught:
        services.record_audit(None, "test.contended", city)

    assert not isinstance(caught.value, AuditChainBroken), (
        "AuditAppendContention must not be an AuditChainBroken, or an alert on "
        "the broken-chain class still fires on ordinary contention"
    )
    assert "NOT broken" in str(caught.value), (
        "the message must say the chain is intact, because the class name is "
        "what an operator reads first and the old one claimed the opposite"
    )
    assert AuditLog.objects.count() == 0, "nothing should have been appended"

    # The positive counterpart, so a budget of 0 is not the only thing measured:
    # with the shipped budget the same call appends and the chain verifies. The
    # real `AuditChainBroken` path has its own coverage in
    # test_audit_append_only.py, which has to disable the trigger to tamper.
    monkeypatch.undo()
    assert services.APPEND_MAX_ATTEMPTS >= 12, (
        "the budget measured at 12 and 24 competing appenders; lowering it is a "
        "dropped audit row, not a tuning decision (see this module's docstring)"
    )
    services.record_audit(None, "test.ok", city)
    rows, _head = services.verify_audit_chain()
    assert rows == 1
