"""The flush escape lets a `transactional_db` test tear down. ENGINE-DIVERGENCE §7.1.

**Why this file exists: nothing was measuring it.** §7.1 was corrected twice,
`tests/conftest.py::allow_test_flush` was written to satisfy it (QA-S0 F9), and
`QA-S0.md` §7 item 3 calls this "the single highest-value skip to run early,
because it is the one whose failure would be misdiagnosed". But on the first
PostgreSQL run the suite had **no test using `transactional_db` at all** —
measured: the name appeared in three files and all three were prose. So a green
run said nothing about teardown, and the collision would still have been
discovered in S4, by S4's `test_double_booking.py`, which ENGINE-DIVERGENCE
§5.3 requires to be transactional *and* to run on PostgreSQL.

At that moment the tempting fix is deleting the TRUNCATE guard, which §3.6
calls the most important unverified thing S0 shipped, and which `CLAUDE.md`'s
last hard rule names as the failure mode to resist. The cheap way to resist it
is to have already proved the escape works — before anyone is under schedule
pressure and before the guard is between them and a green run.

**This file deliberately does not name the session setting.**
`tests/contract/test_migration_guards.py` keeps an inventory of every file that
does, so that an escape hatch cannot acquire a second declarer. A diagnostic
pre-check here would have been a third hand-copy of the name
(`CLAUDE.md` rule 10) and would have turned that inventory red on a file it has
no reason to allow (rule 13: rename ours, do not widen theirs). It is not
needed: when the escape is missing, teardown fails with the message migration
0003 raises, which names the setting and the document section — from the one
place the name is defined rather than from a copy that can drift.

The test writes an `audit_log` row on purpose, because an empty table is
flushed without either guard firing: the row trigger needs a row and the
statement trigger needs the TRUNCATE to be attempted. A version of this test
that wrote nothing would pass against a database with no escape at all.
Verified by running it with the fixture revoked: teardown then fails with
`audit_log is append-only: TRUNCATE is not permitted`, on
`TRUNCATE "audit_log", "django_session", …` — Django 5.2's multi-table
`sql_flush`, exactly the shape §7.1 predicted.
"""

import pytest
from django.db import connection

from apps.core.models import AuditLog


@pytest.mark.django_db(transaction=True)
def test_the_flush_escape_permits_a_transactional_teardown():
    """A transactional test that wrote an `audit_log` row must tear down.

    **The assertion is the teardown**, which happens after this function
    returns: pytest-django flushes, Django's `postgresql.sql_flush` emits
    `TRUNCATE "audit_log", …`, the BEFORE TRUNCATE statement trigger fires, and
    the session setting `tests/conftest.py::allow_test_flush` declares is what
    decides whether the run ends green or with `audit_log is append-only`. So
    this failing looks like a teardown error rather than an assertion failure,
    and that is the shape to expect.
    """
    if connection.vendor != "postgresql":
        pytest.skip(
            f"NOT VERIFIABLE ON THIS ENGINE (vendor={connection.vendor}, slice=S0): "
            "the escape is a PostgreSQL session setting read by a BEFORE TRUNCATE "
            "statement trigger. SQLite has no TRUNCATE statement and no "
            "current_setting, and Django flushes it with DELETE, which the "
            "append-only row trigger correctly refuses — so `transactional_db` "
            "with audit_log rows is unusable on SQLite by design, and that is "
            "the right answer rather than a gap (ENGINE-DIVERGENCE §7.1). Use "
            "`django_db` unless a race is the subject."
        )

    AuditLog.objects.create(
        actor_type="SYSTEM",
        action="teardown.probe",
        object_type="audit_log",
        prev_hash="TEARDOWN-PROBE",
        row_hash="TEARDOWN-PROBE-ROW",
    )
    assert AuditLog.objects.count() >= 1, (
        "the row must really be committed, or the flush has nothing to refuse "
        "and this test passes vacuously (CLAUDE.md rule 12)"
    )
