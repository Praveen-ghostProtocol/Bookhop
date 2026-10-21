"""Seed data and real data must never mix — ADR-002 §4.1(c), PRD AC-M6.3.

This is the design that makes D-009 workable: developers and QA exercise the
whole product against seed rows while no real student's listing is reachable by
another real student. It rests on three things:

1. `users.is_seed` and `listings.is_seed`, `NOT NULL DEFAULT false`;
2. `transfers CHECK (seller_is_seed = buyer_is_seed)`;
3. every metric view filtering `is_seed = false` **and printing the excluded
   seed count**, so contamination is visible rather than silent.

At the end of S0 **none of the three exists**, because `users` is S1,
`listings` is S2, `transfers` is S4 and the metric views are S7. The only
S0-verifiable half is the query predicate, tested in
`tests/e2e/test_gate_journey.py::test_a_closed_campus_restricts_a_queryset_to_seed_rows`.

The rest skips. It skips rather than passing because a passing test here would
be the exact failure this project has already identified: a green suite that
proves less than it appears to. `seed_demo` creating no users
(ENGINE-DIVERGENCE §8 item 7) is the reason there is nothing to assert.
"""

import pytest

pytestmark = pytest.mark.django_db


def test_is_seed_is_not_nullable_on_every_tenant_scoped_table(engine):
    pytest.skip(
        f"NOT VERIFIABLE IN S0 (engine={engine}): ADR-002 §4.1(c) puts "
        "`is_seed NOT NULL DEFAULT false` on `users` (S1) and `listings` (S2). "
        "Neither table exists after S0's migrations, so there is no column to "
        "assert on."
    )


def test_a_seed_user_and_a_real_user_cannot_form_a_transfer(engine):
    pytest.skip(
        f"NOT VERIFIABLE IN S0 (engine={engine}): `CHECK (seller_is_seed = "
        "buyer_is_seed)` lives on `transfers`, which slice S4 creates. "
        "ENGINE-DIVERGENCE §3.2 verifies that this engine enforces a two-column "
        "CHECK of that shape on INSERT and UPDATE — that is the engine "
        "capability, not the constraint. Until S4, nothing in this repository "
        "prevents a seed/real transfer, and nothing creates transfers either."
    )


def test_a_real_listing_is_invisible_on_a_closed_campus(engine):
    pytest.skip(
        f"NOT VERIFIABLE IN S0 (engine={engine}): the `(:discovery_open OR "
        "is_seed)` predicate is verified against an annotated queryset in "
        "tests/e2e/test_gate_journey.py. Verifying it against real listing rows "
        "needs `listings` (S2) and is S3's QA item in TASKS §2."
    )


def test_the_metric_views_exclude_seed_rows_and_print_the_excluded_count(engine):
    pytest.skip(
        f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S7): PRD "
        "AC-M6.3 requires every metric view to filter `is_seed = false` and the "
        "weekly export to print the excluded seed count. ENGINE-DIVERGENCE §6 "
        "records that none of `DATA-MODEL.md` §9's SQL can execute on SQLite at "
        "all (`percentile_cont`, `date_trunc`, `interval`, `::numeric`), so S7 "
        "cannot be verified on this machine in any form."
    )


def test_seed_demo_creates_the_browsable_dataset_tasks_s0_promises(engine):
    pytest.skip(
        f"NOT VERIFIABLE IN S0 (engine={engine}): TASKS §2 S0's 'done when "
        "`seed_demo` produces a browsable-by-staff dataset' cannot be met before "
        "S1/S2 — there are no users and no listings. ENGINE-DIVERGENCE §8 item 7 "
        "states this and the command prints that it created neither, which is "
        "the honest behaviour; QA confirms the promise is unmet rather than "
        "scoring it green. The command's tenancy rows and closed gate ARE "
        "verified in tests/e2e/test_gate_journey.py."
    )
