"""The PostgreSQL halves of the five database guards, audited as text.

**Why a text audit is the strongest thing available, and what it does not buy.**
ENGINE-DIVERGENCE §1 records that no PostgreSQL server exists on this machine,
so not one line of the plpgsql in migrations 0002 and 0003 has ever been parsed,
let alone executed. §9 item 3 calls the Postgres halves of the append-only
triggers "the largest unverified thing S0 shipped", and three guards now depend
on that engine:

  * the `audit_log` / `gate_authorisations` TRUNCATE guards (§3.6), which §3.6
    calls "the single most important thing for a Postgres box to confirm";
  * `ENABLE ALWAYS` on all five triggers (§3.6a);
  * the `campuses.discovery_enabled_at` write guard's plpgsql half (§3.6b).

A test cannot execute them here. What it **can** do is assert the properties
that are decidable from the SQL text, and the one that matters most is a
direction: ENGINE-DIVERGENCE §7.1 says the TRUNCATE escape "yields NULL when
unset, so the default is to raise". **A guard whose escape hatch defaults open
is worse than no guard**, and that framing is this project's own, so the
direction is asserted rather than trusted — by reading the migration, not by
reading the report that describes it.

Every assertion here is `VERIFIED` about the *text* and `UNVERIFIED` about the
*behaviour*. That distinction is the whole point of the file and it is restated
in the skips at the bottom.
"""

import re
from pathlib import Path

import pytest

MIGRATIONS = Path(__file__).resolve().parents[2] / "apps" / "core" / "migrations"


def _text(name):
    path = MIGRATIONS / name
    assert path.exists(), f"{name} is missing"
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def m0002():
    return _text("0002_append_only_triggers.py")


@pytest.fixture(scope="module")
def m0003():
    return _text("0003_gate_column_write_guard.py")


# --------------------------------------------------------------------------
# 1. the TRUNCATE escape defaults to deny
# --------------------------------------------------------------------------


def test_the_truncate_escape_reads_the_setting_with_missing_ok(m0003):
    """`current_setting('bookhop.allow_flush', true)` — the two-argument form.

    The one-argument form **raises** when the setting is unset, which would turn
    a TRUNCATE on a fresh session into an unhandled error inside the trigger
    rather than into the intended `RAISE EXCEPTION`, and would make the guard's
    behaviour depend on whether anyone had ever set the GUC in that session. The
    second argument is what makes "unset" a value rather than an error.
    """
    # Only the executable function body: migration 0003's prose comment also
    # contains the literal text `current_setting(..., true)`, and a guard test
    # that cannot tell code from a comment about the code is worthless.
    body = m0003[m0003.index("bookhop_truncate_guard"):]
    body = body[: body.index("LANGUAGE plpgsql")]
    calls = re.findall(r"current_setting\(([^)]*)\)", body)
    assert calls, "the TRUNCATE guard body contains no current_setting call"
    for call in calls:
        args = [a.strip() for a in call.split(",")]
        assert args[0] == "'bookhop.allow_flush'", args
        assert len(args) == 2 and args[1] == "true", (
            "the escape must use the two-argument current_setting(name, true) "
            f"form so an unset GUC yields NULL rather than raising: {call!r}"
        )


def test_the_truncate_escape_is_an_equality_test_so_unset_means_deny(m0003):
    """The direction, which is the property this file exists for.

    `current_setting(..., true) = 'yes'` evaluates to NULL when the GUC is
    unset. `IF NULL THEN` does not take the branch, so control falls through to
    `RAISE EXCEPTION` — deny by default.

    The shapes that would invert it, asserted absent:
      * `IS DISTINCT FROM 'no'` / `<> 'no'` — NULL is distinct from 'no', so an
        unset GUC would **permit** the flush;
      * `IS NULL OR ... = 'yes'` — explicitly permits the unset case;
      * `COALESCE(current_setting(...), 'yes')` — defaults the unset case open.
    """
    body = m0003[m0003.index("bookhop_truncate_guard"):]
    guard = body[: body.index("LANGUAGE plpgsql")]

    assert re.search(r"current_setting\([^)]*\)\s*=\s*'yes'", guard), (
        "the escape must be an equality test against the permitting value, so "
        f"that NULL (unset) is not a match: {guard!r}"
    )
    for inverted in ("IS DISTINCT FROM", "<>", "!=", "IS NULL", "COALESCE"):
        assert inverted not in guard.upper(), (
            f"{inverted!r} appears in the TRUNCATE escape; every one of these "
            "makes an unset GUC permit the flush, which is an escape hatch that "
            "defaults open"
        )
    assert "RAISE EXCEPTION" in guard, (
        "the guard must raise when the escape is not declared"
    )
    # The raise is the fall-through: it comes after the escape branch.
    assert guard.index("current_setting") < guard.index("RAISE EXCEPTION")


def test_the_escape_exists_only_for_truncate_and_not_for_update_or_delete(m0002, m0003):
    """ENGINE-DIVERGENCE §7.1: "UPDATE and DELETE get no escape; only the
    whole-table flush, which is what the harness needs and what an attacker does
    not."

    Asserted by locating every plpgsql function body in both migrations and
    checking that `bookhop.allow_flush` appears in exactly one of them. If the
    escape ever leaks into `audit_log_is_append_only`, the append-only guarantee
    becomes one `SET` away from nothing.
    """
    bodies = {}
    for text in (m0002, m0003):
        for match in re.finditer(
            r"FUNCTION\s+(\w+)\(\)\s+RETURNS\s+trigger\s+AS\s+\$fn\$(.*?)\$fn\$",
            text, re.S,
        ):
            bodies[match.group(1)] = match.group(2)
    assert bodies, "no plpgsql function bodies found in migrations 0002/0003"

    with_escape = sorted(n for n, b in bodies.items() if "allow_flush" in b)
    assert with_escape == ["bookhop_truncate_guard"], (
        f"the flush escape appears in {with_escape}; it must exist only in the "
        "TRUNCATE guard. An escape in the UPDATE/DELETE guard would make "
        "audit_log mutable with one SET."
    )


def test_the_truncate_guard_is_attached_only_to_truncate(m0003):
    """The escape is only safe because the function it lives in can be reached
    by nothing but a TRUNCATE. Asserted: every trigger that executes
    `bookhop_truncate_guard` is `BEFORE TRUNCATE`."""
    checked = 0
    for match in re.finditer(
        r"CREATE TRIGGER\s+(\w+)\s+(.*?)EXECUTE FUNCTION\s+(\w+)\(\)", m0003, re.S
    ):
        name, clause, function = match.groups()
        if function == "bookhop_truncate_guard":
            assert "BEFORE TRUNCATE" in clause.upper(), (
                f"trigger {name} runs the flush-escaping guard on {clause!r}"
            )
            checked += 1
    assert checked == 2, f"expected two TRUNCATE guards, found {checked}"


def test_regression_the_harness_now_declares_the_flush_escape():
    """**REGRESSION for QA-S0 F9(1)** — was a characterisation test asserting
    the fixture's absence, now the fixture.

    F9 measured that `bookhop.allow_flush` appeared in exactly one file, the
    migration, while ENGINE-DIVERGENCE §7.1 called a session fixture setting it
    mandatory. The first PostgreSQL run of S4's transactional
    `test_double_booking.py` would have failed in teardown, where the tempting
    fix is deleting the guard §3.6 calls the most important unverified thing S0
    shipped.

    `tests/conftest.py::allow_test_flush` now exists. QA verified what it does
    rather than that it exists:

    * it is **session-scoped and autouse**, so a teardown failure is not
      something a test has to opt out of;
    * it depends on `django_db_setup`/`django_db_blocker`, so the setting lands
      on the connection the harness actually flushes with;
    * it is a **deliberate no-op off PostgreSQL** — SQLite has no TRUNCATE and
      flushes with DELETE, which the append-only trigger correctly refuses, so
      `transactional_db` stays unusable locally and that remains the right
      answer;
    * it sets the escape and nothing else: no `DISABLE TRIGGER`, no `DROP`.

    Still `UNVERIFIED` as behaviour: no PostgreSQL server exists, so the fixture
    has never taken its `postgresql` branch. F9(2) — that no mechanism could
    make production refuse the `SET` — is unchanged and is now recorded in
    ENGINE-DIVERGENCE §7.1 as resting on THREAT-MODEL §4 B5/B6, which is the
    honest framing and was the point of the finding.
    """
    repo = Path(__file__).resolve().parents[2]
    conftest = (repo / "tests" / "conftest.py").read_text(encoding="utf-8")

    assert "bookhop.allow_flush" in conftest, (
        "ENGINE-DIVERGENCE §7.1 requires a session fixture that declares the "
        "flush escape; tests/conftest.py does not"
    )
    fixture = conftest[conftest.index("def allow_test_flush"):]
    fixture = fixture[: fixture.index("\n@pytest.fixture")]
    decorator = conftest[: conftest.index("def allow_test_flush")]

    assert 'scope="session"' in decorator and "autouse=True" in decorator, (
        "the flush fixture must be session-scoped and autouse, or a Postgres "
        "teardown failure becomes something each test has to remember"
    )
    assert "django_db_blocker" in fixture, (
        "the setting must land on the connection the harness flushes with"
    )
    assert 'vendor != "postgresql"' in fixture, (
        "the fixture must be a no-op off PostgreSQL; SQLite has no TRUNCATE and "
        "flushing with DELETE is correctly refused by the append-only trigger"
    )
    for weakening in ("DISABLE TRIGGER", "DROP TRIGGER", "ALTER TABLE"):
        assert weakening not in fixture, (
            f"the flush fixture does more than declare the escape: {weakening}"
        )


def test_the_flush_escape_is_declared_by_the_harness_and_nothing_else():
    """An inventory, because an escape hatch with two declarers is two hatches.

    The string `bookhop.allow_flush` must appear in exactly two places: the
    migration that defines the escape, and the harness fixture that declares it
    for a PostgreSQL test session. Any third occurrence — a settings module, an
    app, a management command — is a second way to turn the TRUNCATE guard off,
    and would need reading before it is accepted.

    **F9(2) is unchanged and remains the honest framing:** no mechanism could
    make production *refuse* the `SET`. A custom GUC is settable by any role in
    any session and `current_setting` reads whatever that session set, so
    Django settings have no say in it. Backend's v1.1 claim that a test asserted
    otherwise is withdrawn in ENGINE-DIVERGENCE v1.2, and §7.1 now rests the
    control on THREAT-MODEL §4 B5/B6's accepted scope — direct SQL is out of
    scope. The guard stops Django's own `sql_flush` and an accidental TRUNCATE;
    it does not stop a determined session, and the document now says so.
    """
    repo = Path(__file__).resolve().parents[2]
    hits = sorted(
        path.relative_to(repo).as_posix()
        for path in repo.rglob("*.py")
        if ".venv" not in path.parts
        # QA's own tree names the setting in order to assert on it; the question
        # is whether anything *sets* it.
        and "tests/contract" not in path.relative_to(repo).as_posix()
        and "allow_flush" in path.read_text(encoding="utf-8", errors="ignore")
    )
    assert hits == [
        "apps/core/migrations/0003_gate_column_write_guard.py",
        "tests/conftest.py",
    ], (
        "the flush escape must be named by exactly two files: the migration "
        "that defines it and the harness fixture that declares it. Anything "
        f"else is a second way to turn the TRUNCATE guard off: {hits}"
    )


# --------------------------------------------------------------------------
# 2. ENABLE ALWAYS names the triggers that actually exist
# --------------------------------------------------------------------------


def test_every_enable_always_names_a_trigger_the_migrations_create(m0002, m0003):
    """A name typo here is a migration that fails on the first PostgreSQL box,
    after S0 has been signed off — the most expensive possible place to find it,
    and a text comparison finds it for free."""
    created = set(re.findall(r"CREATE TRIGGER\s+(\w+)", m0002 + m0003))
    enabled = set(re.findall(r"ENABLE ALWAYS TRIGGER\s+(\w+)", m0003))
    assert enabled, "migration 0003 enables no trigger ALWAYS (ENGINE-DIVERGENCE §3.6a)"
    assert enabled <= created, (
        f"ENABLE ALWAYS names triggers no migration creates: {sorted(enabled - created)}"
    )


def test_all_five_postgres_guards_are_enable_always(m0003):
    """ENGINE-DIVERGENCE §3.6a: all five, because `session_replication_role =
    'replica'` is also what a logical-replication apply worker and some restore
    paths use — so a guard that is not ALWAYS is a guard a restore silently
    bypasses."""
    enabled = set(re.findall(r"ENABLE ALWAYS TRIGGER\s+(\w+)", m0003))
    assert enabled == {
        "campuses_gate_authorised",
        "audit_log_append_only",
        "gate_authorisations_append_only",
        "audit_log_no_truncate",
        "gate_authorisations_no_truncate",
    }, sorted(enabled)


def test_the_reverse_migration_restores_a_guard_rather_than_leaving_none(m0003):
    """A reverse that drops the TRUNCATE guards and recreates nothing would make
    `migrate core 0002` a way to remove the append-only guarantee."""
    reverse = m0003[m0003.index("PG_REVERSE"):m0003.index("_LIVE_AUTH")]
    assert reverse.count("CREATE TRIGGER") >= 2, (
        "the reverse migration drops the TRUNCATE guards without restoring the "
        f"0002 versions: {reverse!r}"
    )


# --------------------------------------------------------------------------
# 3. the gate write guard's two halves say the same thing
# --------------------------------------------------------------------------


def test_both_engine_halves_of_the_gate_guard_check_the_same_conjuncts(m0003):
    """The guard is written twice — plpgsql for PostgreSQL, two `WHEN`-guarded
    triggers for SQLite — and only the SQLite half is executed by any test. A
    divergence between them would mean the property QA verified locally is not
    the property production enforces, which is the failure mode this whole
    document set exists to prevent.

    Decidable from the text: both halves must carry `gate = 'C'`,
    `scope_type = 'CAMPUS'`, `scope_id = NEW.id`, `revoked_at IS NULL` and
    `active`.
    """
    pg = m0003[m0003.index("PG_FORWARD"):m0003.index("PG_REVERSE")]
    # The SQLite half builds its subquery from the shared `_LIVE_AUTH` constant,
    # so the SQLite side is credited with that text too.
    sqlite = m0003[m0003.index("_LIVE_AUTH"):m0003.index("SQLITE_REVERSE")]

    for conjunct in ("gate = 'C'", "scope_type = 'CAMPUS'", "scope_id = NEW.id",
                     "revoked_at IS NULL"):
        assert conjunct in pg, f"the PostgreSQL half omits {conjunct!r}"
        assert conjunct in sqlite, f"the SQLite half omits {conjunct!r}"
    assert "active" in pg and "active" in sqlite


def test_the_insert_half_exists_on_both_engines(m0003):
    """A new campus is created closed. The PostgreSQL half handles INSERT inside
    one function; SQLite needs a separate trigger. Both must be present, or the
    INSERT route is open on one engine and QA's local verification of it means
    nothing for production."""
    assert "TG_OP = 'INSERT'" in m0003
    assert "BEFORE INSERT ON campuses" in m0003


def test_closing_is_permitted_unconditionally_on_both_halves(m0003):
    """A campus that cannot be closed is a worse failure than one opened
    carelessly, so the NULL case must short-circuit before any authorisation
    check on both engines."""
    pg = m0003[m0003.index("PG_FORWARD"):m0003.index("PG_REVERSE")]
    assert "NEW.discovery_enabled_at IS NULL" in pg
    assert pg.index("NEW.discovery_enabled_at IS NULL") < pg.index("gate = 'C'")
    sqlite = m0003[m0003.index("SQLITE_FORWARD"):m0003.index("SQLITE_REVERSE")]
    assert "IS NOT NULL" in sqlite, (
        "the SQLite UPDATE trigger must only fire when the new value is NOT "
        "NULL, so closing is never blocked"
    )


def test_the_migration_refuses_an_engine_it_was_not_written_for(m0003):
    """ADR-001 §2.2 permits postgresql and sqlite only. A migration that silently
    no-opped on a third engine would create a database with no guards at all."""
    assert "RuntimeError" in m0003
    assert "not written for" in m0003


# --------------------------------------------------------------------------
# 4. what a text audit cannot establish
# --------------------------------------------------------------------------


def test_the_postgres_guards_actually_fire(engine):
    pytest.skip(
        f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S0): everything "
        "in this file is an assertion about migration *text*. Whether the "
        "plpgsql parses, whether the TRUNCATE triggers fire, whether "
        "`ENABLE ALWAYS` is accepted, and whether the escape behaves as the "
        "equality test implies all require a PostgreSQL 16 server, which this "
        "machine does not have (ENGINE-DIVERGENCE §1, §9 item 3). Three guards "
        "now depend on that engine and none of them has ever run."
    )


def test_the_flush_escape_permits_a_transactional_teardown(engine):
    pytest.skip(
        f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S4): the escape "
        "exists so Django's `sql_flush` TRUNCATE can run in a test session "
        "(ENGINE-DIVERGENCE §7.1). SQLite has no TRUNCATE and no "
        "`current_setting`, so neither the escape nor the collision it resolves "
        "can be reproduced here. The first real exercise is S4's "
        "`test_double_booking.py` on a Postgres box, and per F9 the session "
        "fixture it needs does not exist yet."
    )
