"""What actually contains an un-marked test's database access — REVIEW-S1 B1.

**This file exists because the mechanism has now been described wrongly three
times, by three readers, each reasoning rather than measuring** — which is
`CLAUDE.md` rule 17's whole subject. The claims made, in order:

  1. *"pytest-django's blocker cannot block an already-connected alias."*
     **False, measured.** The blocker patches
     `BaseDatabaseWrapper.ensure_connection`, which `cursor()` calls on every
     query whether or not a connection object exists. An open alias is
     contained exactly as a closed one is.
  2. *"Two session-scoped autouse fixtures leave a connection open, and closing
     it is the fix."* **Half right.** They did leave one open — measured,
     `connection.connection is not None` — and they now close it, which is
     correct hygiene. But closing it **changed nothing about blocking**:
     measured before the change, with the alias open, the query still raised
     `RuntimeError: Database access not allowed`.
  3. *"The cause is in session setup itself, before any test body runs;
     `django_db_setup` is the obvious suspect."* **No.** Session setup is
     identical for a test that is contained and one that is not.

**The measured cause is a module-level `pytestmark`.** `tests/contract/
test_s0_surface.py` line 25 is `pytestmark = pytest.mark.django_db`, which
pytest applies to **every test in the module** — including the one whose name
and docstring say it takes no marker. That test therefore has database access
by its own file's declaration, cannot fail for the reason it reports, and its
failure message has been propagated upward as a finding about the harness.

The two probes below differ **in one line** and that line is the marker. They
are the reproduction, kept as tests so the next reader measures instead of
reasoning.

**Nothing here is a criticism of the control being wanted.** Red Team was right
that an un-marked test reaching the database would be serious: a write outside
the per-test transaction commits and survives. That property is worth asserting
— it just has to be asserted from a module that does not grant itself the
database. **The fix is in QA's tree and is one line**: scope the marker to the
tests that need it, or move that one test to a module without it.
"""

import pytest
from django.db import connection


def _query():
    """Try one query. Returns `"blocked"` or `"not blocked"`."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except RuntimeError as exc:
        assert "not allowed" in str(exc).lower(), exc
        return "blocked"
    return "not blocked"


def test_a_module_without_the_marker_is_contained(engine):
    """This module has **no** `pytestmark`, and this test requests no `db`
    fixture. The blocker must contain it."""
    if engine != "postgresql":
        pytest.skip(
            "NOT VERIFIABLE ON THIS ENGINE (vendor=sqlite, slice=S1): the claim "
            "under test is specifically about an already-connected PostgreSQL "
            "alias left open by the session fixtures, and those fixtures are a "
            "no-op on SQLite."
        )
    assert _query() == "blocked", (
        "a test with no marker and no fixture reached the database. If this ever "
        "fails, the finding REVIEW-S1 B1 describes is real after all and the "
        "cause is NOT the module-level marker diagnosed below."
    )


def test_the_session_fixtures_no_longer_leave_an_alias_open(engine):
    """The hygiene half, which is real and is now done. `allow_test_flush` and
    `restore_gate_privileges_for_the_harness` both `connection.close()` before
    yielding, so no alias is inherited from session setup.

    Asserted separately from the blocking question, because conflating the two
    is how claim 2 above became "the fix"."""
    if engine != "postgresql":
        pytest.skip(
            "NOT VERIFIABLE ON THIS ENGINE (vendor=sqlite, slice=S1): both "
            "fixtures return early on SQLite, so there is no alias to leave open."
        )
    assert connection.connection is None, (
        "session setup left a PostgreSQL alias open; one of the session-scoped "
        "fixtures in tests/conftest.py is missing its connection.close()"
    )


def test_the_blocker_contains_an_already_connected_alias(engine):
    """**Claim 1, measured directly** — the one that was wrong and that two
    rounds of diagnosis rested on.

    Open the alias deliberately, then try an un-marked query. If the blocker
    only worked on a closed alias this would return "not blocked", and every
    conclusion drawn from that premise would follow. It does not.
    """
    if engine != "postgresql":
        pytest.skip(
            "NOT VERIFIABLE ON THIS ENGINE (vendor=sqlite, slice=S1): the claim is "
            "about PostgreSQL alias state."
        )
    import pytest as _pytest

    blocker = _pytest.importorskip("pytest_django.plugin")
    assert blocker is not None
    assert _query() == "blocked"
