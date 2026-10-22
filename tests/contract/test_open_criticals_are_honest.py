"""The two strict xfails fail for the reason they claim, and not for another.

**The defect class this file exists for.** A `strict=True` xfail is the project's
way of carrying an open critical without hiding it, and the mechanism is sound —
the day the exposure closes, the suite goes red and somebody has to look. But
`xfail` records only *that* the test failed. **It does not record which
assertion failed, and it treats an exception exactly like a failed assertion.**
So an xfail can report a tracked exposure while the exposure is actually closed
and the test is failing for an unrelated reason: a renamed fixture, a changed
error class, a second assertion about an audit row that nobody is thinking
about. That failure mode is worse than a skip, because a skip says it did not
run while an xfail says it ran and the bad thing happened.

`tests/unit/test_least_privilege.py` carries two of them, both citing RED TEAM
`ENGINEERING-MEMO.md`. Each has **two** assertions, and only the first is the
attack:

| xfail | first assertion — the attack | second assertion |
|---|---|---|
| `test_three_orm_statements_cannot_open_the_discovery_gate` | the gate stayed closed | an audit row was written |
| `test_the_application_role_cannot_truncate_the_audit_log` | rows survive the TRUNCATE | — |

If the gate trigger were fixed and the audit row were still missing, the first
xfail would keep reporting *"the gate opens"* while the gate was shut. **That is
the specific thing checked here.**

**Method.** The attacks are reproduced from the memo's own text, in this file, so
the honesty claim rests on QA's reproduction rather than on reading the test it
is auditing. The assertions are inverted: each test **passes while the exposure
is open** and, when `ENGINEERING-MEMO.md` §1 and §3 are fixed, goes red with a
message saying to de-xfail the other file. Two tests going red on the same fix
is the intended cost — the alternative is a fix that silently leaves a stale
xfail behind.
"""

import pytest
from django.db import connection
from django.utils import timezone

pytestmark = pytest.mark.django_db

DE_XFAIL = (
    "If this is now red, RED TEAM ENGINEERING-MEMO §{section} is CLOSED. "
    "Remove the `xfail(strict=True)` from "
    "`tests/unit/test_least_privilege.py::{test}` in the same commit — a strict "
    "xfail left on a passing test fails the build, and a non-strict one left on "
    "a passing test is a tracked critical that is no longer tracked."
)


def test_the_gate_xfail_fails_on_the_gate_and_not_on_the_audit_row(
    qa_city, qa_entity, engine
):
    """**ENGINEERING-MEMO §1, reproduced, with the two limbs separated.**

    The memo's three statements: an empty `legal_entities` row; a
    `gate_authorisations` row for gate C whose six evidence values are the
    literal string `"x"` — on ADR-002 §4.1(b)'s own placeholder deny-list — and
    which is granted against a **different** legal entity; then a plain queryset
    `update()` of `discovery_enabled_at`.

    Measured on PostgreSQL 16 and on SQLite: **the gate opens.** So the xfail in
    `test_least_privilege.py` fires on its first assertion, which is the attack,
    which is honest.

    The audit limb is asserted separately and reported separately, so that
    fixing one without the other cannot leave either xfail saying the wrong
    thing.
    """
    from apps.core.models import AuditLog, Campus, GateAuthorisation, LegalEntity

    unrelated_entity = LegalEntity.objects.create()
    campus = Campus.objects.create(
        city=qa_city, name="Memo Attack Campus", slug="memo-attack",
        legal_entity=qa_entity,
    )
    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=campus.id,
        legal_entity=unrelated_entity,
        evidence={
            "counsel_engagement_ref": "x", "takedown_sop_ref": "x",
            "oncall_rota_ref": "x", "breach_rehearsal_at": "x",
            "campus_mou_ref": "x", "notice_version_ids": ["x"],
        },
        authorised_by_human="a",
    )
    audit_before = AuditLog.objects.count()

    Campus.objects.filter(id=campus.id).update(discovery_enabled_at=timezone.now())
    campus.refresh_from_db()

    assert campus.discovery_enabled_at is not None, DE_XFAIL.format(
        section="1", test="test_three_orm_statements_cannot_open_the_discovery_gate"
    ) + (
        " Specifically: three ORM statements no longer open the gate, so that "
        "xfail's FIRST assertion now passes and it would be failing — if at all "
        "— on its audit-row limb instead. That is the dishonest-xfail case this "
        "test exists to catch."
    )
    assert AuditLog.objects.count() == audit_before, (
        "the gate opened AND an audit row was written. The xfail would then be "
        "failing only on its first assertion, which is still honest — but the "
        "second limb has changed, so re-read "
        "ENGINEERING-MEMO §10 and this test's docstring."
    )


def test_the_truncate_xfail_fails_on_a_successful_truncate_not_a_permission_error(
    qa_city, engine
):
    """**ENGINEERING-MEMO §3, reproduced, and the honesty question here is
    sharper than §1's.**

    Two statements from the application's own role: `SET bookhop.allow_flush =
    'yes'`, then `TRUNCATE audit_log`. If that TRUNCATE were refused with
    SQLSTATE 42501, the test in `test_least_privilege.py` would raise rather than
    assert — and pytest marks a raising xfail test as xfailed exactly as it marks
    a failing one. The xfail would then be reporting *"the application role
    emptied the audit log"* **while the privilege layer was holding**, which is
    the inverse of the truth and is unreadable from the summary line.

    So this test asserts the distinction the xfail cannot: the TRUNCATE
    **succeeds**, and the table is empty afterwards.

    `CLAUDE.md` rule 16 is the same point from the other side: a refused
    operation is not evidence a guard fired for the right reason, and a
    successful one is not evidence it fired at all until you look at what
    happened.
    """
    from apps.core.models import AuditLog
    from apps.core.services import record_audit

    if connection.vendor != "postgresql":
        pytest.skip(
            f"NOT VERIFIABLE ON THIS ENGINE (vendor={engine}, slice=S1): SQLite "
            "has no TRUNCATE statement and no role system, so neither half of "
            "the attack exists here and the xfail it audits correctly skips on "
            "this engine too (measured: 1 xfail on SQLite, 2 on PostgreSQL). "
            "ENGINE-DIVERGENCE §12."
        )

    record_audit(None, "qa.truncate_honesty", qa_city)
    assert AuditLog.objects.exists(), "nothing to truncate; this test would be vacuous"

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET bookhop.allow_flush = 'yes'")
            cursor.execute("TRUNCATE audit_log")
    except Exception as refusal:  # noqa: BLE001 - the class is the subject
        pytest.fail(
            "the TRUNCATE was REFUSED, so RED TEAM §3 may be closed — and "
            "`test_least_privilege.py::test_the_application_role_cannot_truncate"
            "_the_audit_log` is an xfail that is now firing on an EXCEPTION "
            "rather than on its assertion, while still reporting that the "
            "application role emptied the audit log. "
            + DE_XFAIL.format(
                section="3",
                test="test_the_application_role_cannot_truncate_the_audit_log",
            )
            + f" Refusal was: {type(refusal).__name__}: {refusal}"
        )

    assert not AuditLog.objects.exists(), (
        "the TRUNCATE neither raised nor emptied the table, which is the third "
        "and worst case: the xfail is firing for a reason nobody has identified."
    )


def test_both_xfails_are_strict_and_name_the_memo_section_they_track(engine):
    """The property that makes the mechanism work at all, asserted rather than
    assumed.

    `strict=True` is what turns a fixed exposure into a red build. A
    non-strict xfail on a fixed test reports `XPASS` and passes, so the critical
    stops being tracked with no diff and no signal — and `pytest.ini` sets
    `--strict-markers`, which polices marker *names*, not this.

    Read out of the file's own source rather than by importing it, because
    importing would execute the module and collecting it twice is how a
    `transactional_db` test ends up fighting its own fixtures.
    """
    import re
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[2] / "tests" / "unit" / "test_least_privilege.py"
    ).read_text(encoding="utf-8")

    marks = re.findall(r"@pytest\.mark\.xfail\(([^)]*)\)", source)
    assert len(marks) == 2, (
        f"expected the two tracked criticals, found {len(marks)} xfail marks in "
        "test_least_privilege.py. A third tracked exposure needs a third "
        "honesty test here, or this file is reporting on a set it no longer "
        "covers."
    )
    for mark in marks:
        assert "strict=True" in mark, (
            f"an xfail in test_least_privilege.py is not strict: {mark!r}. A "
            "non-strict xfail stops tracking the critical the moment it is "
            "fixed, which is the one moment the tracking is for."
        )
    assert re.search(r"ENGINEERING-MEMO\s*§1", source), (
        "the xfail reason no longer cites the memo section it tracks, so a "
        "reader cannot find out what is open"
    )
