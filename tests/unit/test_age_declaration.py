"""Adults only, server-side, with **no date of birth persisted anywhere**.

DATA-MODEL §2 (amendment A-5 / PRD CG-5), `COMPLIANCE.md` §1.4 and §7 row 7,
PRD AC-A2.1 to AC-A2.3, JOURNEYS J1 step 4 and J8-staff step 1.

**The load-bearing test in this file is not the age arithmetic.** It is
`test_no_submitted_date_reaches_any_column_in_any_table`, which scans every
column of every table for the submitted date rather than checking the columns
someone thought of. `CLAUDE.md` rule 18 is why: *"a control that guarantees a
state does not thereby detect a bad input"*. ADR-003 §2.3's deny-list proves no
column is **named** for a date of birth; it cannot prove none **holds** one, and
a date in `audit_log.user_agent` or a job payload would pass every schema
assertion in the repository.

`tests/unit/test_no_dob_persisted.py` is the filename THREAT-MODEL §6 uses and
TASKS §3's table assigns to **test-qa**. That is a genuine ownership collision —
`tests/unit/**` is backend's by TASKS §1 — so this file deliberately takes a
different name and leaves theirs free. Raised in the slice note; QA's version is
written against the spec without reading this one, which is the point of having
both.
"""

from datetime import date, timedelta

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from apps.accounts.models import AgeVerificationEvent, Consent, User
from apps.accounts.services import (
    ADULT_AGE,
    age_on,
    age_review_queue,
    review_age,
    submit_age_declaration,
)
from apps.core.errors import NotPermitted, UnderEighteen, ValidationFailed

pytestmark = pytest.mark.django_db


def _dob_for_age(years, offset_days=0):
    return timezone.localdate() - timedelta(days=round(years * 365.25) + offset_days)


# --- the server-side check ------------------------------------------------


def test_an_adult_is_confirmed_and_no_date_is_kept(pending_student):
    outcome = submit_age_declaration(pending_student, _dob_for_age(21), "198.51.100.7")
    pending_student.refresh_from_db()

    assert outcome == "ADULT_CONFIRMED"
    assert pending_student.adult_verified is True
    event = AgeVerificationEvent.objects.get(user_pseudonym=pending_student.person_pseudonym)
    assert event.outcome == "ADULT_CONFIRMED"
    assert event.method == "SELF_DECLARED_DOB_SERVER_CHECKED"
    assert event.note is None


def test_a_seventeen_year_old_cannot_create_an_account(pending_student):
    """PRD AC-A2.1, verbatim: *"A declared DOB under 18 returns 403 and, after
    the request, there is **no `users` row** … for that email, and **no DOB
    anywhere in the database.** Exactly one `age_verification_events` row exists
    with `outcome='REJECTED_UNDER_18'`, and its `note` contains no date."*"""
    pseudonym = pending_student.person_pseudonym
    email = pending_student.email

    with pytest.raises(UnderEighteen) as refusal:
        submit_age_declaration(pending_student, _dob_for_age(17), "198.51.100.7")

    assert refusal.value.http_status == 403
    assert refusal.value.code == "NOT_ADULT_VERIFIED"
    assert not User.objects.filter(email=email).exists(), "the users row survived the rejection"
    assert not User.objects.filter(person_pseudonym=pseudonym).exists()

    events = list(AgeVerificationEvent.objects.filter(user_pseudonym=pseudonym))
    assert len(events) == 1, "exactly one event, not zero and not two"
    assert events[0].outcome == "REJECTED_UNDER_18"
    assert events[0].note is None
    assert events[0].user_id is None, (
        "the event kept a FK to a row that was deleted in the same transaction; "
        "`user_pseudonym` is what survives"
    )


@pytest.mark.parametrize(
    "years,offset_days,allowed,why",
    [
        (18, 0, True, "exactly eighteen by the day"),
        (18, -1, False, "one day short of eighteen"),
        (17, 0, False, "seventeen"),
        (99, 0, True, "no upper bound, and there should not be one"),
    ],
)
def test_the_boundary_is_on_the_day_not_in_the_year(pending_student, years, offset_days, allowed, why):
    """The off-by-one that matters: a student whose birthday is tomorrow is 17
    today. `age_on` compares `(month, day)`, so this is a test of the
    comparison and not of the arithmetic."""
    dob = _dob_for_age(years, offset_days)
    if allowed:
        assert submit_age_declaration(pending_student, dob, None) == "ADULT_CONFIRMED", why
    else:
        with pytest.raises(UnderEighteen):
            submit_age_declaration(pending_student, dob, None)


def test_age_on_is_whole_years_on_the_calendar():
    assert age_on(date(2008, 2, 29), date(2026, 2, 28)) == 17
    assert age_on(date(2008, 3, 1), date(2026, 3, 1)) == 18
    assert ADULT_AGE == 18


@pytest.mark.parametrize("bad", [None, "", "not-a-date", 2004, {"year": 2004}])
def test_a_non_date_is_refused_rather_than_coerced(pending_student, bad):
    """`CLAUDE.md` rule 18 in its own words: *"the test that matters is never
    'the column is of integer type' — it is 'passing a non-integer is
    refused.'"* The same shape applies to a date: a string that `date()` would
    happily mis-parse must be refused, not guessed at."""
    with pytest.raises(ValidationFailed):
        submit_age_declaration(pending_student, bad, None)


def test_a_future_date_is_refused(pending_student):
    with pytest.raises(ValidationFailed):
        submit_age_declaration(pending_student, timezone.localdate() + timedelta(days=1), None)


def test_declaring_twice_is_refused_rather_than_appending_a_second_event(pending_student):
    """Also the guard that keeps the under-18 delete safe: a user who has
    consented has append-only `consents` rows, and a cascade that tried to NULL
    their FK would be **refused by the database**. Reachable only from
    PENDING_VERIFICATION is therefore a correctness guard, not a convenience."""
    submit_age_declaration(pending_student, _dob_for_age(20), None)
    with pytest.raises(ValidationFailed):
        submit_age_declaration(pending_student, _dob_for_age(20), None)
    assert AgeVerificationEvent.objects.filter(
        user_pseudonym=pending_student.person_pseudonym
    ).count() == 1


def test_an_active_student_with_consents_cannot_reach_the_delete_path(student):
    """The same guard, from the other side, and the reason it exists.

    `student` has an appended `consents` row. If `submit_age_declaration` ran
    its rejection path here, the `users` delete would try to NULL
    `consents.user_id` — and `consents` is append-only by trigger, so the
    database would refuse the UPDATE and the whole request would 500. The guard
    turns that into a clean 400.
    """
    assert Consent.objects.filter(user_pseudonym=student.person_pseudonym).exists()
    with pytest.raises(ValidationFailed):
        submit_age_declaration(student, _dob_for_age(17), None)
    student.refresh_from_db()
    assert student.status == "ACTIVE"


# --- the invariant: no DOB in any column of any table ---------------------


def _all_text_in_database():
    """Every value in every column of every table, as text.

    Reads `connection.introspection` rather than `information_schema` or
    `PRAGMA`, per ADR-003 §2.3 W4 — the same route the schema guard uses, so
    this works identically on both engines and cannot be written in a way that
    only one of them understands.
    """
    values = []
    with connection.cursor() as cursor:
        tables = connection.introspection.table_names(cursor)
        for table in tables:
            try:
                columns = [c.name for c in connection.introspection.get_table_description(cursor, table)]
            except Exception:  # pragma: no cover - a view or a system table
                continue
            if not columns:
                continue
            quoted = ", ".join(connection.ops.quote_name(c) for c in columns)
            cursor.execute(f"SELECT {quoted} FROM {connection.ops.quote_name(table)}")
            for row in cursor.fetchall():
                for column, value in zip(columns, row):
                    if value is not None:
                        values.append((table, column, str(value)))
    return values


@pytest.mark.parametrize("years", [17, 21])
def test_no_submitted_date_reaches_any_column_in_any_table(pending_student, years):
    """**The assertion this slice lives or dies by.**

    A distinctive date is submitted and then **every column of every table** is
    scanned for it, in every spelling a developer might have written it in. Both
    paths are tested, because the rejection path writes an event and deletes a
    row while the acceptance path writes an event and sets a boolean — and
    either could have carried the date into an audit payload, a log column, a
    job payload or a jsonb document.

    This is the control for the residual ADR-003 §2.3 W5 declares: *"a number
    inside a jsonb document"* and *"a number inside free text"*. The deny-list
    proves no column is **named** for a DOB; only this proves none **holds**
    one.
    """
    # A date far from any default, with a distinctive day and month so a
    # substring match cannot collide with a timestamp written by the test.
    dob = date(timezone.localdate().year - years, 3, 29)
    try:
        submit_age_declaration(pending_student, dob, "198.51.100.7")
    except UnderEighteen:
        pass

    spellings = {
        dob.isoformat(),                       # 2009-03-29
        dob.strftime("%d/%m/%Y"),              # 29/03/2009
        dob.strftime("%d-%m-%Y"),
        dob.strftime("%m/%d/%Y"),
        dob.strftime("%d %b %Y"),              # 29 Mar 2009
        dob.strftime("%Y%m%d"),                # 20090329
        str(dob.toordinal()),                  # a proleptic ordinal
    }
    stored = _all_text_in_database()
    assert stored, "no rows were read at all — this test would pass vacuously"

    offenders = [
        f"{table}.{column} = {value!r}"
        for table, column, value in stored
        for spelling in spellings
        if spelling in value
    ]
    assert offenders == [], (
        "DATA-MODEL §2 amendment A-5: **no date of birth is persisted anywhere, "
        "in any state.** The declared date reached storage:\n" + "\n".join(sorted(set(offenders)))
    )


def test_the_dob_scan_would_actually_find_a_date(pending_student):
    """`CLAUDE.md` rule 12. The scan above asserts an absence, and an absence is
    exactly what a broken scanner reports. So plant a date in a real column, in
    a real table, and prove the scanner sees it."""
    dob = date(2009, 3, 29)
    User.objects.filter(id=pending_student.id).update(display_name=dob.isoformat())
    stored = _all_text_in_database()
    assert any(dob.isoformat() in value for _t, _c, value in stored), (
        "the scanner cannot see a date that is demonstrably in the database"
    )


def test_no_column_anywhere_is_named_for_a_date_of_birth():
    """The second, independent layer (`CLAUDE.md` rule 14). The scan above is
    about a *value*; this is about a *name*, and it comes from
    `apps/core/p14.py` rather than being retyped."""
    from apps.core.p14 import CONDITIONAL_COLUMNS

    for pattern in ("date_of_birth", "dob", "birth"):
        assert pattern in CONDITIONAL_COLUMNS
        assert CONDITIONAL_COLUMNS[pattern] is None, (
            f"{pattern!r} has an exception again; CG-5 withdrew the only one there was"
        )


# --- the logged human review ----------------------------------------------


def test_a_student_cannot_review_an_age_decision(student, pending_student):
    with pytest.raises(NotPermitted):
        review_age(student, pending_student, "ADULT_CONFIRMED", "looks fine")
    with pytest.raises(NotPermitted):
        age_review_queue(student)


def test_staff_review_records_the_reviewer_the_outcome_and_the_timestamp(staff, pending_student):
    """DATA-MODEL §2: *"The audit trail §1.4 wants is the reviewer, the outcome
    and the timestamp — all three survive."* And the review reviews **the
    account, not a date.**"""
    submit_age_declaration(pending_student, _dob_for_age(20), None)
    review_age(staff, pending_student, "ADULT_CONFIRMED", "college email domain matches the campus")

    event = AgeVerificationEvent.objects.filter(method="STAFF_REVIEW").get()
    assert event.reviewer_id == staff.id
    assert event.outcome == "ADULT_CONFIRMED"
    assert event.occurred_at is not None
    assert "domain" in event.note


@pytest.mark.parametrize(
    "note",
    [
        "declared 2004-08-21",
        "dob 21/08/2004",
        "born 21.8.2004",
        "said 21 Aug 2004",
        "DOB: 2004-8-1",
    ],
)
def test_a_review_note_containing_a_date_is_refused(staff, pending_student, note):
    """DATA-MODEL §2 calls this a code review item. It is a refusal as well,
    because the reviewer's free-text box is the last route by which a DOB could
    reach storage, and a review is the one place someone would be tempted to
    write one down."""
    with pytest.raises(ValidationFailed, match="date of birth"):
        review_age(staff, pending_student, "ADULT_CONFIRMED", note)
    assert not AgeVerificationEvent.objects.filter(method="STAFF_REVIEW").exists()


def test_the_note_refusal_still_accepts_an_ordinary_reason(staff, pending_student):
    """The other half, so the test above cannot pass by refusing everything —
    including a note with a number in it, which is the obvious false positive."""
    review_age(staff, pending_student, "ADULT_CONFIRMED", "3 sessions, campus domain, no flags")
    assert AgeVerificationEvent.objects.filter(method="STAFF_REVIEW").exists()


def test_an_empty_review_note_is_refused(staff, pending_student):
    with pytest.raises(ValidationFailed):
        review_age(staff, pending_student, "ADULT_CONFIRMED", "   ")


def test_rejected_under_18_is_not_a_reviewable_outcome(staff, pending_student):
    """It is written by the server at declaration time. A reviewer able to
    record it would be recording a decision they did not make."""
    with pytest.raises(ValidationFailed):
        review_age(staff, pending_student, "REJECTED_UNDER_18", "they look young")


def test_discovering_a_minor_suspends_the_account_and_names_the_pocso_next_step(
    staff, pending_student, security_log
):
    """JOURNEYS J8-staff and PRD EC-12. The POCSO limb needs a
    `safety_incidents` row and that table is **S6**, so this slice suspends,
    records and **logs the duty as a named next step** rather than half-running
    the procedure. The slice note carries the gap.

    Uses the `security_log` fixture rather than `caplog`: `bookhop.security` is
    configured with `propagate: False` (settings LOGGING), so pytest's root
    handler never sees it. That is worth knowing beyond this test — **every
    assertion about the CERT-In security stream has to attach to that logger,
    and one written with `caplog` passes vacuously.**
    """
    submit_age_declaration(pending_student, _dob_for_age(20), None)
    review_age(staff, pending_student, "REVOKED_MINOR_DISCOVERED", "campus office confirmed")

    pending_student.refresh_from_db()
    assert pending_student.status == "SUSPENDED"
    assert pending_student.adult_verified is False
    assert AgeVerificationEvent.objects.filter(outcome="REVOKED_MINOR_DISCOVERED").exists()

    events = [record for record in security_log if record.getMessage() == "accounts.minor_discovered"]
    assert events, "no security-stream event was written for a discovered minor"
    assert "POCSO" in str(getattr(events[0], "next_step", "")), (
        "the POCSO reporting duty was not surfaced; a legal duty rendered as "
        "nothing is a legal duty that gets missed"
    )


def test_the_age_review_queue_shows_unreviewed_self_declarations(staff, pending_student):
    submit_age_declaration(pending_student, _dob_for_age(20), None)
    assert len(age_review_queue(staff)) == 1
    review_age(staff, pending_student, "ADULT_CONFIRMED", "domain matches")
    assert age_review_queue(staff) == [], "a reviewed account stayed in the queue"


def test_an_age_event_cannot_be_rewritten_or_deleted(pending_student, engine):
    """`age_verification_events` is append-only (DATA-MODEL §2). It is the whole
    audit trail for "this account was checked", with **no DOB behind it**, so if
    the row can be rewritten there is nothing else to fall back on."""
    submit_age_declaration(pending_student, _dob_for_age(20), None)
    event = AgeVerificationEvent.objects.get()

    with pytest.raises(DatabaseError, match="append-only"):
        with transaction.atomic():
            AgeVerificationEvent.objects.filter(id=event.id).update(outcome="REJECTED_UNDER_18")
    with pytest.raises(DatabaseError, match="append-only"):
        with transaction.atomic():
            AgeVerificationEvent.objects.filter(id=event.id).delete()

    event.refresh_from_db()
    assert event.outcome == "ADULT_CONFIRMED", f"age_verification_events was mutable on {engine}"
