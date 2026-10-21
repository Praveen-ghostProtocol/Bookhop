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

pytestmark = pytest.mark.django_db


def test_n_concurrent_accepts_yield_exactly_one_success(engine):
    pytest.skip(
        f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S4): the "
        "double-booking guard is a partial unique index on `transfers "
        "(listing_id)` over the four active states, and the claim is that a "
        "concurrent second accept violates it and returns "
        "`409 LISTING_ALREADY_RESERVED` (DATA-MODEL §5, API-CONTRACT §4.3). "
        "SQLite has one database writer, so the N-1 losers would be serialised "
        "by the database write lock and typically fail with 'database is locked' "
        "rather than with the integrity error the service converts to a 409 — a "
        "green run would show 'exactly one success' without once exercising the "
        "guard (ENGINE-DIVERGENCE §5.2 item 3). `transfers` does not exist "
        "either: there is no table, no index and no `accept_offer` at the end of "
        "S0."
    )


def test_the_partial_unique_index_exists_on_transfers(engine):
    pytest.skip(
        f"NOT VERIFIABLE IN S0 (engine={engine}): "
        "`one_active_transfer_per_listing` is created with `transfers` in S4. "
        "ENGINE-DIVERGENCE §5.1 verifies that this engine honours a partial "
        "unique index with an `IN (...)` predicate — that is the engine "
        "capability the guard will rest on, not the guard."
    )


def test_two_job_workers_cannot_claim_the_same_job(engine):
    pytest.skip(
        f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S0): job "
        "claiming is a compare-and-swap `UPDATE ... WHERE id = ? AND locked_at "
        "IS NULL` because `SELECT ... FOR UPDATE SKIP LOCKED` is a silent no-op "
        "on SQLite (ENGINE-DIVERGENCE §4.3). The single-threaded claim-skipping "
        "property is covered by the backend's unit test; multi-worker claiming "
        "is UNVERIFIED on both engines and needs two processes against one "
        "PostgreSQL server."
    )


def test_a_reservation_expiring_during_an_accept_resolves_one_way(engine):
    pytest.skip(
        f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S4/S5): the "
        "unhappy path the charter puts first — the `reservation.expire` job "
        "firing while a student taps Accept — is a read-modify-write race "
        "between a job and a request. PostgreSQL's READ COMMITTED permits it; "
        "SQLite's single writer prevents it (ENGINE-DIVERGENCE §4.1, §4.2). "
        "Recorded now so S4 does not discover the gap mid-slice."
    )
