"""No date of birth is persisted in any state — verified independently.

`DATA-MODEL.md` amendment A-5 is the strongest claim in the schema and it is
stated with no exception: *"a declared date of birth exists only inside the HTTP
request that declares it. It is never written to any table, any log, any cache
or any backup."* `THREAT-MODEL.md` §6 lists one test for it, scanning every
column of every table for the submitted date.

**This file is the independent second reading, and it differs in four ways that
each close a route the column sweep cannot see.**

1. **It drives the real HTTP surface**, both the L3 form and the L2 endpoint, in
   both outcomes. A service-level test establishes that `submit_age_declaration`
   keeps no date; it does not establish that the *view* in front of it keeps
   none — a form error path that re-renders the submitted value, a flash message,
   a session key holding the bound form, an idempotency record of the request
   body.
2. **It sweeps the places a column sweep is not looking**: the session store,
   `jobs.payload`, `idempotency_keys.request_hash`/`response_body`, the
   `bookhop.security` log stream and the rendered response bodies. The brief
   named four of these by name and `idempotency_keys.response_body` is the fifth,
   because a replayed age declaration would hand the stored body back.
3. **It covers the two paths A-5's own text singles out and the sweep does not
   reach**: the staff age-review path (`review_age`, §2's *"logged human
   review"*, whose `note` is free text) and the **rejection** path, where the
   `users` row is deleted in the same transaction and the question is what the
   deletion leaves behind.
4. **It checks the export file**, which is a document the student receives and
   which `API-CONTRACT.md` §5.1 generates live from the database — so a date
   reaching it would be a disclosure, not just a retention.

Both engines. Planted-date control included, independently of backend's, because
a scanner that cannot find a date it was shown is not a scanner.
"""

import datetime as dt
import json
import re

import pytest
from django.core import mail
from django.db import connection

pytestmark = pytest.mark.django_db

#: The declared date, chosen so every component is distinctive in a database of
#: ids and counts: 17 and 1998 appear nowhere else, and 0417/1704 are not a port
#: or a status code.
DOB = dt.date(1998, 4, 17)

#: A second date that makes the student a minor, for the rejection path. Kept in
#: the same year-month shape so a scanner tuned to one is tuned to both.
MINOR_DOB = dt.date(2014, 4, 17)


def spellings(date):
    """Every rendering of one date that a naive store might produce.

    Not a list someone will extend (`CLAUDE.md` rule 15 where it can be obeyed):
    it is generated from the date's own components, so a different date needs no
    edit. The ceiling is declared rather than hidden — **it cannot see a date
    that was transformed rather than formatted** (an epoch, an age in days, a
    hash), and the only general answer to that is that no column exists to hold
    one, which `test_forbidden_schema.py` asserts from the other side. This
    sweep's job is the formatted cases, which are the ones a template, a log line
    or a JSON payload actually emit.
    """
    y, m, d = date.year, f"{date.month:02d}", f"{date.day:02d}"
    day_no_pad, month_no_pad = str(date.day), str(date.month)
    out = {
        f"{y}-{m}-{d}", f"{d}-{m}-{y}", f"{m}-{d}-{y}",
        f"{y}/{m}/{d}", f"{d}/{m}/{y}", f"{m}/{d}/{y}",
        f"{d}.{m}.{y}", f"{y}{m}{d}", f"{d}{m}{y}",
        f"{day_no_pad}/{month_no_pad}/{y}", f"{y}-{month_no_pad}-{day_no_pad}",
        date.strftime("%d %b %Y"), date.strftime("%d %B %Y"),
        date.isoformat(),
    }
    return sorted(out)


def _sweep_database(needles):
    """Every column of every table, cast to text, searched for every needle.

    Reads the catalogue rather than a model list, so it covers Django's own
    tables (`django_session`, `django_migrations`) and anything a migration
    created outside the ORM — which is where a sweep written from
    `apps.get_models()` would have a blind spot.
    """
    hits = {}
    text = "text" if connection.vendor == "postgresql" else "TEXT"
    with connection.cursor() as cursor:
        for table in connection.introspection.table_names(cursor):
            try:
                columns = connection.introspection.get_table_description(cursor, table)
            except Exception:  # noqa: BLE001 - a view or a system object
                continue
            for column in columns:
                for needle in needles:
                    cursor.execute(
                        f'SELECT count(*) FROM "{table}" '
                        f'WHERE CAST("{column.name}" AS {text}) LIKE %s',
                        [f"%{needle}%"],
                    )
                    if cursor.fetchone()[0]:
                        hits.setdefault(f"{table}.{column.name}", []).append(needle)
    return hits


def _sweep_sessions(needles):
    from django.contrib.sessions.models import Session

    hits = {}
    for row in Session.objects.all():
        blob = row.session_data + json.dumps(row.get_decoded(), default=str)
        found = [n for n in needles if n in blob]
        if found:
            hits[row.session_key] = found
    return hits


def _sweep_log_records(records, needles):
    hits = {}
    for record in records:
        blob = record.getMessage() + json.dumps(
            {k: v for k, v in vars(record).items() if isinstance(v, (str, int, float))},
            default=str,
        )
        found = [n for n in needles if n in blob]
        if found:
            hits[record.name] = found
    return hits


def _sign_in(client, email, settings, capture):
    from apps.accounts.models import User
    from apps.core.jobs import run_pending_jobs

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    mail.outbox.clear()
    with capture(execute=True):
        client.post("/auth/start", {"email": email})
    run_pending_jobs()
    token = re.search(r"/auth/c/(\S+)", mail.outbox[-1].body).group(1)
    client.get(f"/auth/c/{token}")
    return User.objects.get(email=email)


# ---------------------------------------------------------------------------
# 0. the scanner is not blind — asserted before it is believed
# ---------------------------------------------------------------------------


def test_the_sweep_finds_a_planted_date_in_every_place_it_claims_to_look(
    db, signup_campus, security_log
):
    """`CLAUDE.md` rule 12, and the reason this file can be trusted at all.

    A sweep that returns `{}` is indistinguishable from a sweep that is looking
    in the wrong place, at the wrong column, with the wrong cast. So plant the
    date in **each** of the five places this file searches and assert each sweep
    finds it. A sweep that cannot find a date it was handed is not evidence about
    a date it was not.
    """
    import logging
    from datetime import timedelta

    from django.contrib.sessions.backends.db import SessionStore
    from django.utils import timezone

    from apps.core.models import FeatureFlag, IdempotencyKey, Job

    needles = spellings(DOB)
    iso = DOB.isoformat()

    FeatureFlag.objects.create(key=f"qa.planted.{iso}", enabled=False, updated_by="qa")
    Job.objects.create(kind="qa.planted", payload={"date_of_birth": iso})
    IdempotencyKey.objects.create(
        key="qa-planted", endpoint="/qa", request_hash=iso,
        response_status=200, response_body={"dob": iso},
        expires_at=timezone.now() + timedelta(days=1),
    )
    session = SessionStore()
    session["planted"] = iso
    session.save()
    logging.getLogger("bookhop.security").warning("planted %s", iso)

    db_hits = _sweep_database(needles)
    assert any(name.startswith("feature_flags.") for name in db_hits), (
        f"the column sweep missed a plain text column: {sorted(db_hits)}"
    )
    assert any(name.startswith("jobs.") for name in db_hits), (
        f"the column sweep cannot see inside a jsonb payload: {sorted(db_hits)}"
    )
    assert any(name.startswith("idempotency_keys.") for name in db_hits), (
        f"the column sweep missed the idempotency record: {sorted(db_hits)}"
    )
    assert _sweep_sessions(needles), "the session sweep is blind"
    assert _sweep_log_records(security_log, needles), "the log sweep is blind"


# ---------------------------------------------------------------------------
# 1. the happy path, through both surfaces
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("surface", ["L3", "L2"])
def test_an_accepted_declaration_persists_no_date_anywhere(
    surface, client, signup_campus, privacy_notice, settings,
    django_capture_on_commit_callbacks, security_log,
):
    """`JOURNEYS.md` J1 step 4 and `API-CONTRACT.md` §5.1. Both surfaces, because
    `Accept-Language` and `Idempotency-Key` make L2 a different code path and
    A-5's claim has no surface exemption."""
    import uuid

    from apps.accounts.models import User

    user = _sign_in(
        client, f"dob{surface.lower()}@example.ac.in", settings, django_capture_on_commit_callbacks
    )
    needles = spellings(DOB)

    if surface == "L3":
        response = client.post("/account/age", {"date_of_birth": DOB.isoformat()})
        assert response.status_code in (200, 302), response.status_code
    else:
        response = client.post(
            "/api/v1/account/age-declaration",
            data=json.dumps({"date_of_birth": DOB.isoformat()}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        assert response.status_code == 200, response.content

    user.refresh_from_db()
    assert user.adult_verified, "the declaration was not accepted, so nothing was asserted"

    from apps.core.jobs import run_pending_jobs

    run_pending_jobs()

    assert _sweep_database(needles) == {}, (
        f"a date of birth is in the database after an accepted declaration on "
        f"{surface}: {_sweep_database(needles)}"
    )
    assert _sweep_sessions(needles) == {}, "a date of birth is in the session store"
    assert _sweep_log_records(security_log, needles) == {}, (
        "a date of birth reached the security log stream"
    )
    body = response.content.decode(errors="ignore")
    assert not [n for n in needles if n in body], (
        "the response echoes the submitted date of birth back to the client"
    )


def test_a_replayed_declaration_does_not_hand_back_a_stored_date(
    client, signup_campus, privacy_notice, settings, django_capture_on_commit_callbacks
):
    """`API-CONTRACT.md` §4.1: a replayed request *"returns the stored response"*.
    So the stored response is a persistence site for whatever the first response
    contained, and A-5's *"never written to any table"* has to hold for
    `idempotency_keys.response_body` too — a route the column sweep covers only
    if someone thought to replay."""
    import uuid

    _sign_in(client, "replay@example.ac.in", settings, django_capture_on_commit_callbacks)
    key = str(uuid.uuid4())
    body = json.dumps({"date_of_birth": DOB.isoformat()})

    first = client.post(
        "/api/v1/account/age-declaration", data=body,
        content_type="application/json", HTTP_IDEMPOTENCY_KEY=key,
    )
    second = client.post(
        "/api/v1/account/age-declaration", data=body,
        content_type="application/json", HTTP_IDEMPOTENCY_KEY=key,
    )
    assert first.status_code == 200, first.content

    needles = spellings(DOB)
    for label, response in (("first", first), ("replay", second)):
        found = [n for n in needles if n in response.content.decode(errors="ignore")]
        assert not found, f"the {label} response carries the declared date: {found}"
    assert _sweep_database(needles) == {}, (
        f"the idempotency record stored the date: {_sweep_database(needles)}"
    )


# ---------------------------------------------------------------------------
# 2. the rejection path — A-5 step 3
# ---------------------------------------------------------------------------


def test_a_rejected_under_18_declaration_leaves_no_date_and_no_account(
    client, signup_campus, privacy_notice, settings,
    django_capture_on_commit_callbacks, security_log,
):
    """`DATA-MODEL.md` §2 step 3 and `JOURNEYS.md` J1 step 4: *403
    NOT_ADULT_VERIFIED*, a `REJECTED_UNDER_18` event, **the `users` row deleted
    in the same transaction**, and no DOB anywhere.

    The rejection path is the one that matters most and is the least exercised: a
    minor's date is the most sensitive datum the product ever holds, and it is
    held on the path where the code is also deleting a row and writing an audit
    event — three writes in one transaction, any of which could carry the date.
    """
    from apps.accounts.models import AgeVerificationEvent, User

    user = _sign_in(client, "minor@example.ac.in", settings, django_capture_on_commit_callbacks)
    user_id = user.pk
    needles = spellings(MINOR_DOB)

    response = client.post("/account/age", {"date_of_birth": MINOR_DOB.isoformat()})
    assert response.status_code == 403, (
        f"a minor's declaration returned {response.status_code}, not 403 "
        "NOT_ADULT_VERIFIED, so this test is not on the rejection path"
    )
    assert not User.objects.filter(pk=user_id).exists(), (
        "the account of a self-declared minor survives: §2 step 3 requires it "
        "to be deleted in the same transaction"
    )
    event = AgeVerificationEvent.objects.get(outcome="REJECTED_UNDER_18")
    assert event.user_id is None and event.user_pseudonym, (
        "the rejection event must survive by pseudonym with no FK to a row that "
        "no longer exists"
    )

    from apps.core.jobs import run_pending_jobs

    run_pending_jobs()

    assert _sweep_database(needles) == {}, (
        f"a MINOR's date of birth is in the database: {_sweep_database(needles)}"
    )
    assert _sweep_sessions(needles) == {}, "a minor's date of birth is in the session store"
    assert _sweep_log_records(security_log, needles) == {}, (
        "a minor's date of birth reached the security log stream"
    )
    assert not [n for n in needles if n in response.content.decode(errors="ignore")], (
        "the refusal page echoes the minor's date of birth back to them"
    )


def test_the_refusal_suggests_no_workaround(
    client, signup_campus, privacy_notice, settings, django_capture_on_commit_callbacks
):
    """`JOURNEYS.md` J1 step 4 and `PRD.md` AC-A2.3: the copy *"states the rule
    and stops — no workaround suggested, no invitation to return with another
    date"*. A refusal that hints at a retry is an instruction to lie about an
    age, which is the whole risk §1.4 of `COMPLIANCE.md` is about."""
    _sign_in(client, "nohint@example.ac.in", settings, django_capture_on_commit_callbacks)
    import html

    page = re.sub(
        r"\s+", " ",
        html.unescape(
            re.sub(r"<[^>]+>", " ",
                   client.post("/account/age", {"date_of_birth": MINOR_DOB.isoformat()})
                   .content.decode())
        ),
    )
    forbidden = [
        phrase for phrase in (
            "try again", "another date", "different date", "come back",
            "correct your date", "re-enter", "when you turn",
        )
        if phrase in page.lower()
    ]
    assert not forbidden, (
        f"the under-18 refusal suggests a way around it: {forbidden}. "
        f"AC-A2.3 forbids this. Page: {page[:300]!r}"
    )


# ---------------------------------------------------------------------------
# 3. the staff review path — the free-text column A-5's own text flags
# ---------------------------------------------------------------------------


def test_the_staff_review_note_refuses_a_date_rather_than_relying_on_a_reviewer(
    student, staff, salt, security_log
):
    """**`CLAUDE.md` rule 18, asked of the one column that can hold a DOB.**

    `DATA-MODEL.md` §2 says `age_verification_events.note` *"must not contain a
    date of birth"* and routes the enforcement to *"code review item"*. A
    document asserting a property with a human as the only control is exactly
    what rule 9 and rule 18 are about: the column sweep proves no column *holds*
    a date; it does not prove none can be *passed*.

    Measured: the service **refuses** it, with a message naming the rule. So the
    control is detection, not a convention — asserted here because the
    specification does not require it and a later refactor could drop it without
    failing anything else.
    """
    from apps.accounts.models import AgeVerificationEvent
    from apps.accounts.services import review_age
    from apps.core.services import ValidationFailed

    needles = spellings(DOB)
    before = AgeVerificationEvent.objects.count()

    with pytest.raises(ValidationFailed) as refusal:
        review_age(staff, student, "ADULT_CONFIRMED", f"declared DOB {DOB.isoformat()}, checked")

    assert re.search(r"date of birth", str(refusal.value), re.I), (
        "the refusal does not say what was wrong, so a reviewer will reword the "
        f"note until it is accepted. Message: {str(refusal.value)!r}"
    )
    assert AgeVerificationEvent.objects.count() == before, (
        "the refusal was raised after the row was written"
    )
    assert _sweep_database(needles) == {}, (
        f"the refused note persisted anyway: {_sweep_database(needles)}"
    )
    assert _sweep_log_records(security_log, needles) == {}, (
        "the refused note's date was written to the security log on the way out"
    )


def test_a_lawful_staff_review_is_still_possible_and_records_the_three_facts(
    student, staff, salt
):
    """The other branch of the same guard (`CLAUDE.md` rule 16: exercise every
    path, not only the refusal).

    §2: the review *"reviews the account, not the date"*, and *"the reviewer, the
    outcome and the timestamp — all three survive"*. A guard that refused every
    note would make the §1.4 human review unperformable, which would be a worse
    failure than the one above.
    """
    from apps.accounts.models import AgeVerificationEvent
    from apps.accounts.services import review_age

    review_age(staff, student, "ADULT_CONFIRMED", "campus domain matched; account behaviour normal")

    event = AgeVerificationEvent.objects.filter(method="STAFF_REVIEW").latest("occurred_at")
    assert event.reviewer_id == staff.pk, "the reviewer is not recorded"
    assert event.outcome == "ADULT_CONFIRMED"
    assert event.occurred_at is not None
    assert event.user_pseudonym == student.person_pseudonym


# ---------------------------------------------------------------------------
# 4. the export — a document the student receives
# ---------------------------------------------------------------------------


def test_the_export_file_contains_no_date_of_birth_and_says_so(
    client, signup_campus, privacy_notice, settings, django_capture_on_commit_callbacks
):
    """`API-CONTRACT.md` §5.1 generates the s11 export live from the database, so
    it is the one artefact where a retained date would also be a disclosure.

    The second assertion is the more interesting one: the export **asserts** that
    no date is held. Under `CLAUDE.md` rule 9 a claim in a student-facing
    document needs a check, and this is that check — the sentence and the sweep
    in one test, so the sentence cannot outlive the property.
    """
    _sign_in(client, "export@example.ac.in", settings, django_capture_on_commit_callbacks)
    client.post("/account/age", {"date_of_birth": DOB.isoformat()})

    response = client.get("/api/v1/account/export")
    assert response.status_code == 200, response.content
    payload = response.content.decode()

    found = [n for n in spellings(DOB) if n in payload]
    assert not found, f"the export hands the student back their declared date: {found}"

    document = json.loads(payload)
    assert document["age_check"]["date_of_birth_held"] is False, (
        "the export claims a date of birth is held, which contradicts A-5"
    )
    assert _sweep_database(spellings(DOB)) == {}, (
        "generating the export persisted the date somewhere"
    )
