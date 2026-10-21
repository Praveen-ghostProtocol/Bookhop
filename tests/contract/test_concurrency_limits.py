"""The races this machine cannot run — stated as skips, never as passes.

ENGINE-DIVERGENCE §5.3 instructs test-qa that "any test whose subject is a race
must skip on SQLite rather than pass", and §9 item 4(a) repeats it. This file is
where S0's QA pass records the races it is not running and why, so that the
count of skipped tests is the honest measure of what a green run does not cover.

`tests/api/test_double_booking.py` is backend-developer's file and is S4's work.
The skip here is QA's own record that **the single most important correctness
property in BookHop is verified nowhere at the end of S0**, which
ENGINE-DIVERGENCE §5.3 states and this suite must not quietly contradict.
"""

import pytest

from .engine_limits import unavailable

pytestmark = pytest.mark.django_db


def test_n_concurrent_accepts_yield_exactly_one_success():
    pytest.skip(unavailable(
        slice_="S4", needs_tables=("transfers",),
        subject="the double-booking guard -- a partial unique index on "
                "`transfers (listing_id)` over the four active states, where a "
                "concurrent second accept must return 409 "
                "LISTING_ALREADY_RESERVED (DATA-MODEL 5, API-CONTRACT 4.3)",
        note="PostgreSQL has stopped being the limit: the table, the index and "
             "`accept_offer` do not exist. The same mechanism -- a unique index "
             "under real contention from 12 connections -- is now exercised on "
             "a table that does exist, in tests/e2e/test_postgres_concurrency.py"
             "::test_the_idempotency_insert_is_the_lock. A pass there predicts "
             "a pass here and is not one.",
    ))


def test_the_partial_unique_index_exists_on_transfers(engine):
    pytest.skip(
        f"NOT VERIFIABLE IN S0 (engine={engine}): "
        "`one_active_transfer_per_listing` is created with `transfers` in S4. "
        "ENGINE-DIVERGENCE §5.1 verifies that this engine honours a partial "
        "unique index with an `IN (...)` predicate — that is the engine "
        "capability the guard will rest on, not the guard."
    )


# `test_two_job_workers_cannot_claim_the_same_job` lived here as a bare `pytest.skip()` until PostgreSQL 16
# arrived. ENGINE-DIVERGENCE 10.6 is right that a skip reason naming
# SQLite while running on PostgreSQL is self-contradicting, so the
# placeholder is gone and the assertion is written:
#   tests/e2e/test_postgres_concurrency.py::test_two_job_workers_cannot_claim_the_same_job


def test_a_reservation_expiring_during_an_accept_resolves_one_way():
    pytest.skip(unavailable(
        slice_="S4/S5", needs_tables=("transfers",),
        subject="the unhappy path the charter puts first -- the "
                "`reservation.expire` job firing while a student taps Accept, a "
                "read-modify-write race between a job and a request",
        note="PostgreSQL can host this race now; nothing creates a transfer to "
             "race over. Recorded so S4 does not discover the gap mid-slice.",
    ))