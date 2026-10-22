"""Does pytest-django's blocker actually contain an undeclared write?

**This module declares no `pytestmark`, and that is the whole point of it
existing separately.**

QA-S1 §3 reported that the blocker was not containing the alias, and the
measurement was wrong for an embarrassing reason: the test lived in
`test_s0_surface.py`, which declares `pytestmark = pytest.mark.django_db` at
module level. A module-level marker applies to every test in the module, so the
test asserting "a test with no marker cannot reach the database" **had the
marker, by its own file's declaration**. Its premise was false and it could not
have passed.

Backend's measurement is the one that settled it: the same test body, verbatim,
in a module with no `pytestmark`, run in the same pytest invocation against the
same database — `1 failed, 1 passed`. Identical code, one line of difference.
`tests/unit/test_db_blocker_mechanism.py` pins that, and three wrong claims
about the mechanism are corrected there:

* *"the blocker cannot block an already-connected alias"* — **false**. It
  patches `ensure_connection`, which every query calls regardless.
* *"the session fixtures leave a connection open and closing it is the fix"* —
  half right. They did, they now close it, that is correct hygiene — and
  **closing changed nothing about blocking.**
* *"the cause is in session setup"* — **false**, and that narrowing was QA's.
  Session setup is identical for a contained and an uncontained test.

**Two of the three wrong claims were QA's, and one of them reached the founder
as fact.** The lesson is not "QA was careless" — it is that three agents
reasoned their way to three different wrong answers about one mechanism, and
only running it settled it. This module is QA's side of making the next reader
measure instead of reason.

**The verdict delta from the whole isolation episode is zero**, measured two
independent ways, and the variance that started it is fully accounted for: it
was the stale test database (QA-S1 F20), and nothing else.
"""

import pytest
from django.db import connection


def test_a_test_without_the_django_db_marker_cannot_reach_the_database():
    """The guard that the blocker is wired, asserted from a module that can
    honestly ask the question.

    It is kept — rather than deleted as a wrong alarm — because the property is
    worth a standing check: if a future conftest change silenced the blocker,
    every "unit" test in the repository could commit rows that survive into
    every later test, and the failures would land on whichever test next reads
    global state rather than on the one that leaked. QA watched that happen for
    a different reason (F20) and it cost five runs to understand.
    """
    with pytest.raises(RuntimeError) as exc:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    assert "django_db" in str(exc.value), (
        "a query from an unmarked test raised, but not from the blocker: "
        f"{exc.value!r}"
    )


def test_this_module_declares_no_module_level_database_marker():
    """The guard on the guard, because the defect above was invisible by
    construction: a `pytestmark` added to this file later would make the test
    above pass for the wrong reason and nothing would say so.

    `CLAUDE.md` rule 12's shape — a guard that passes vacuously is worse than no
    guard — applied to the one file where the absence of a marker *is* the
    fixture.
    """
    import pathlib

    source = pathlib.Path(__file__).read_text(encoding="utf-8")
    # `pytestmark` only. A `@pytest.mark.django_db` decorator applies to the one
    # test it sits on and is in fact required below for the positive control;
    # the thing that would silently break this module is the module-level
    # assignment, which is the exact line that broke it in test_s0_surface.py.
    offenders = [
        line for line in source.splitlines() if line.startswith("pytestmark")
    ]
    assert offenders == [], (
        "this module has acquired a database marker, so the test above no "
        f"longer asks what it says it asks: {offenders}"
    )


@pytest.mark.django_db
def test_the_same_query_succeeds_when_the_marker_is_present():
    """The positive control proper: identical body, marker present, succeeds."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)
