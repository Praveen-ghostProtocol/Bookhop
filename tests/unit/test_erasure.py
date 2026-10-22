"""Tombstone-plus-purge — DATA-MODEL §10.1, `COMPLIANCE.md` §7, PRD US-X1.

*"'Delete my account' never means `DELETE FROM users`."* The two properties that
have to hold together, and which this file asserts separately so a failure says
which one broke:

  * the identity is gone — email, display name, password NULLed, sessions and
    tokens destroyed, campus-verification evidence deleted;
  * the **pseudonym survives**, because repeat-transfer-@90d groups by it (§9.2)
    and the counterparty's dispute needs the record to keep referring to
    someone. *"That last assertion is the test that proves erasure and
    measurement coexist"* (PRD AC-X1.3).

`tests/e2e/test_deletion.py` is test-qa's and carries DATA-MODEL §10.3's seven
assertions, **written from the spec without reading this implementation.** This
file is the implementation-side half: the registry of steps, the salt's
externality, and idempotency. Four of §10.3's seven assertions cannot be made
until S2–S5 create the tables they are about, and
`test_every_erasure_step_is_executed_or_names_its_slice` is what stops that
being forgotten.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import (
    AgeVerificationEvent,
    CampusVerification,
    Consent,
    DataSubjectRequest,
    EmailLoginToken,
    User,
    UserTombstone,
)
from apps.accounts.services import (
    ERASURE_STEPS,
    RETENTION_FLOOR,
    email_hash,
    erase_account,
    request_magic_link,
    submit_age_declaration,
)
from apps.core.models import AuditLog

pytestmark = pytest.mark.django_db


# --- the identity is gone --------------------------------------------------


def test_erasure_nulls_the_identity_and_keeps_the_row(student, salt):
    address = student.email
    erase_account(student)
    student.refresh_from_db()

    assert User.objects.filter(id=student.id).exists(), (
        "`DELETE FROM users` is never the answer (DATA-MODEL §10.1)"
    )
    assert student.email is None
    assert student.display_name is None
    assert student.password is None
    assert student.status == "TOMBSTONED"
    assert student.tombstoned_at is not None
    assert not User.objects.filter(email=address).exists()


def test_erasure_destroys_the_tokens_and_the_campus_verification_evidence(student, salt):
    """§10.1 steps 3 and 4. `campus_verified` **stays** as a boolean: the fact
    of eligibility outlives the evidence, which is §7 row 6's whole design."""
    EmailLoginToken.objects.create(
        user=student, token_hash="x" * 64, expires_at=timezone.now() + timedelta(minutes=10)
    )
    CampusVerification.objects.create(
        user=student, method="INSTITUTIONAL_EMAIL", email_domain="example.ac.in"
    )

    erase_account(student)
    student.refresh_from_db()

    assert not EmailLoginToken.objects.filter(user=student).exists()
    assert not CampusVerification.objects.filter(user=student).exists()
    assert student.campus_verified is True, (
        "the boolean was cleared with the evidence; §7 row 6 keeps the boolean"
    )


def test_erasure_invalidates_the_session_server_side(client, student, salt, settings):
    """ASVS V7 L2 wants server-side invalidation, so "the cookie expires
    eventually" is not an answer. DATA-MODEL §10.1 step 3 lists sessions."""
    from django.contrib.sessions.models import Session

    from apps.accounts.sessions import SESSION_USER_KEY

    session = client.session
    session[SESSION_USER_KEY] = student.id
    session.save()
    assert Session.objects.filter(session_key=session.session_key).exists()

    erase_account(student)
    assert not Session.objects.filter(session_key=session.session_key).exists()


# --- the pseudonym survives ------------------------------------------------


def test_the_pseudonym_survives_and_the_tombstone_keeps_the_coarse_campus(student, salt):
    """PRD AC-X1.3 and DATA-MODEL §9.2. **The pseudonym is never rewritten**:
    destroying it would destroy the transaction record's only remaining
    reference, breaking both the counterparty's dispute and the metric."""
    pseudonym = student.person_pseudonym
    campus_id, city_id = student.campus_id, student.city_id

    erase_account(student)
    student.refresh_from_db()

    assert student.person_pseudonym == pseudonym
    tombstone = UserTombstone.objects.get(person_pseudonym=pseudonym)
    assert tombstone.campus_id == campus_id
    assert tombstone.city_id == city_id
    assert tombstone.reason == "USER_REQUEST"


def test_the_consent_and_age_records_survive_untouched(student, salt):
    """§10.1 step 7: *"**Untouched:** `repeat_infringer_records`, `audit_log`,
    `personal_data_access_log`, `age_verification_events`, `consents`"* —
    `consents` because it is *the record that the deletion itself was lawful*,
    which is exactly the record you need after a deletion."""
    submit_age_declaration(
        User.objects.create(
            email="other@example.ac.in", campus=student.campus, city_id=student.city_id,
            campus_verified=True, is_seed=True,
        ),
        timezone.localdate().replace(year=timezone.localdate().year - 25),
        None,
    )
    consents_before = Consent.objects.filter(user_pseudonym=student.person_pseudonym).count()
    ages_before = AgeVerificationEvent.objects.count()
    audit_before = AuditLog.objects.count()

    erase_account(student)

    assert Consent.objects.filter(user_pseudonym=student.person_pseudonym).count() == consents_before
    assert AgeVerificationEvent.objects.count() == ages_before
    assert AuditLog.objects.count() > audit_before, "no audit row for the erasure"
    assert AuditLog.objects.filter(action="accounts.erased").exists()


def test_the_consent_rows_still_resolve_by_pseudonym_after_the_fk_is_gone(student, salt):
    """The half that proves pseudonymisation is **one-way and still usable**:
    the retained rows carry the pseudonym, and the pseudonym→identity mapping
    is what was destroyed."""
    erase_account(student)
    rows = Consent.objects.filter(user_pseudonym=student.person_pseudonym)
    assert rows.exists()
    assert all(row.user_pseudonym == student.person_pseudonym for row in rows)


def test_a_data_subject_request_records_the_erasure_within_seven_days(student, salt):
    """DATA-MODEL §2: `due_at = received_at + 7 days` — **not 90.**
    `COMPLIANCE.md` §1.8: 90 is DPDP's ceiling and the tightest clock governs."""
    from apps.accounts.services import DSR_DEADLINE

    erase_account(student)
    row = DataSubjectRequest.objects.get(user_pseudonym=student.person_pseudonym, kind="ERASURE")
    assert row.completed_at is not None
    assert (row.due_at - row.received_at) == DSR_DEADLINE
    assert DSR_DEADLINE.days == 7


# --- the salt --------------------------------------------------------------


def test_the_email_hash_is_salted_and_the_salt_is_not_in_the_database(student, salt):
    """`COMPLIANCE.md` §7 rows 3 and 24. A bare sha256 of an institutional
    address is enumerable from a roll list, so the hash is only one-way in
    practice if the salt is a server-side secret **outside** the database."""
    address = student.email
    import hashlib

    unsalted = hashlib.sha256(address.encode()).hexdigest()

    erase_account(student)
    tombstone = UserTombstone.objects.get(person_pseudonym=student.person_pseudonym)

    assert tombstone.email_hash and tombstone.email_hash != unsalted, (
        "the hash is unsalted and therefore enumerable"
    )
    assert tombstone.email_hash == email_hash(address)[0]
    assert tombstone.salt_version == "test-v1"

    # The salt itself must appear nowhere in any column of any table.
    from tests.unit.test_age_declaration import _all_text_in_database

    assert not any(salt in value for _t, _c, value in _all_text_in_database()), (
        "the tombstone salt is stored in the database, which defeats its purpose"
    )


def test_erasure_refuses_when_no_salt_is_configured(student, settings):
    """**No default and no fallback.** A shared default salt makes every
    deployment's hashes identical and the control worthless, and a silent empty
    salt is the shape of defect that passes every test — so the refusal is the
    behaviour, asserted."""
    settings.TOMBSTONE_EMAIL_SALT = ""
    with pytest.raises(RuntimeError, match="BOOKHOP_TOMBSTONE_EMAIL_SALT"):
        erase_account(student)
    student.refresh_from_db()
    assert student.status == "ACTIVE", "the account was half-erased before the refusal"
    assert not UserTombstone.objects.exists()


def test_a_restore_to_a_new_box_loses_hash_matching_and_that_is_expected(student, salt, settings):
    """**Named as a property rather than discovered as a bug.**

    The salt lives in the environment, not in the dump, so a database restored
    to a box with a different salt cannot match an `email_hash` it did not have
    the salt for. That is what the external salt is *for* — and `INFRA.md`
    §3.3's restore rehearsal should assert it rather than be surprised by it.
    """
    address = student.email
    erase_account(student)
    stored = UserTombstone.objects.get(person_pseudonym=student.person_pseudonym).email_hash

    settings.TOMBSTONE_EMAIL_SALT = "a-different-boxs-salt"
    assert email_hash(address)[0] != stored, (
        "two different salts produced the same hash, so the salt is not in the hash"
    )


# --- idempotency and the step registry ------------------------------------


def test_erasing_twice_is_not_two_tombstones(student, salt):
    """API-CONTRACT §4.4: at-least-once everywhere, so a second call must be a
    no-op rather than a second tombstone with a later `purge_due_at` — which
    would silently **extend** the retention of the hash by a year."""
    erase_account(student)
    first = UserTombstone.objects.get(person_pseudonym=student.person_pseudonym)
    student.refresh_from_db()

    erase_account(student)
    assert UserTombstone.objects.count() == 1
    assert UserTombstone.objects.get().purge_due_at == first.purge_due_at


def test_the_purge_due_date_is_one_year_out(student, salt):
    erase_account(student)
    tombstone = UserTombstone.objects.get()
    assert (tombstone.purge_due_at - tombstone.tombstoned_at) == RETENTION_FLOOR
    assert RETENTION_FLOOR.days == 365


def test_every_erasure_step_is_executed_or_names_its_slice():
    """**TASKS R-1's lesson, applied here:** *"a deferral recorded only in a
    review is how an ownerless control becomes an unwritten one."*

    DATA-MODEL §10.1 has eight steps and S1 can execute five of them, because
    steps 5 and 6 name tables S2–S6 create. `ERASURE_STEPS` is that registry as
    data, so a reader can see which steps are pending and a later slice has a
    list to work from rather than a docstring to re-read.
    """
    assert ERASURE_STEPS, "the registry is empty — this test would pass vacuously"
    steps_covered = {step for step, _what, _slice, _done in ERASURE_STEPS}
    assert steps_covered == {1, 2, 3, 4, 5, 6, 7, 8}, (
        f"DATA-MODEL §10.1 has eight steps; the registry names {sorted(steps_covered)}"
    )
    for step, what, slice_name, executed in ERASURE_STEPS:
        assert slice_name.startswith("S"), f"step {step} ({what}) names no slice"
        if not executed:
            assert slice_name != "S1", (
                f"step {step} ({what}) is marked not-executed but assigned to S1, "
                "which means this slice is claiming a step it does not run"
            )


def test_the_steps_this_slice_claims_are_the_ones_it_can_run():
    """The other direction: an entry marked executed in S1 must name only
    tables that exist, or the registry is a wish list."""
    from django.apps import apps as django_apps

    existing = {model._meta.db_table for model in django_apps.get_models()}
    for step, what, slice_name, executed in ERASURE_STEPS:
        if not executed:
            continue
        assert slice_name == "S1", f"step {step} is executed but attributed to {slice_name}"
        for table in ("user_tombstones", "users", "email_login_tokens", "campus_verifications",
                      "data_subject_requests"):
            if table in what.replace(" ", "_") or table in what:
                assert table in existing, f"step {step} names {table}, which does not exist"


def test_a_magic_link_for_an_erased_address_does_not_resurrect_the_account(student, salt, settings):
    """JOURNEYS J8 step 7: *"They come back later → a new account, a new
    pseudonym."* The old row's email is NULL, so the lookup misses and a fresh
    row is created — and the old pseudonym is **not** reused, which is what
    makes the §9.2 undercount an undercount rather than a re-link."""
    address = student.email
    old_pseudonym = student.person_pseudonym
    erase_account(student)

    request_magic_link(address, "198.51.100.9", "pytest")
    fresh = User.objects.get(email=address)
    assert fresh.id != student.id
    assert fresh.person_pseudonym != old_pseudonym


# --- REVIEW-S1: the session scan, and the layer that actually holds --------


def test_the_session_scan_reports_what_it_scanned_and_deleted(client, student, salt):
    """**REVIEW-S1.** The scan used to swallow every exception around the
    decode, on the assumption that an unreadable session would raise. Django's
    `decode` catches everything itself and **returns `{}`**, so the `except` was
    dead code for the modes it was written for and the real failure mode —
    matching nothing — was silent.

    The counts are what make silence detectable, so they are asserted.
    """
    from apps.accounts.sessions import SESSION_USER_KEY
    from apps.accounts.services import _delete_sessions_for

    session = client.session
    session[SESSION_USER_KEY] = student.id
    session.save()

    scanned, deleted = _delete_sessions_for(student)
    assert scanned >= 1
    assert deleted == 1


def test_a_scan_that_matches_nothing_is_logged_rather_than_silent(
    client, student, salt, security_log
):
    """A rotated `SECRET_KEY` makes every decode return `{}`, which is
    indistinguishable from "this student had no sessions" unless it is said out
    loud. Simulated by a session belonging to somebody else: rows present, none
    matching."""
    from apps.accounts.sessions import SESSION_USER_KEY
    from apps.accounts.services import _delete_sessions_for

    session = client.session
    session[SESSION_USER_KEY] = student.id + 999
    session.save()

    scanned, deleted = _delete_sessions_for(student)
    assert (scanned, deleted) == (1, 0)
    assert any(
        record.getMessage() == "accounts.session_scan_matched_nothing"
        for record in security_log
    ), "a scan that matched nothing produced no signal at all"


def test_the_device_is_signed_out_even_if_the_session_scan_matches_nothing(
    client, student, salt
):
    """**The independent second layer, asserted rather than claimed**
    (`CLAUDE.md` rule 14).

    REVIEW-S1's reassuring half: even if `_delete_sessions_for` matched
    nothing — a rotated `SECRET_KEY`, a changed serialiser — the student's
    device is still signed out, because `sessions.session_user` excludes a
    `TOMBSTONED` account and **flushes** the session it found. That layer does
    not share the scan's decode dependency, which is what makes it independent.

    Nothing tested it. This does, by erasing **without** the scan and then
    using the session: the row survives the erasure and the request is still
    unauthenticated.
    """
    from unittest.mock import patch

    from apps.accounts.sessions import SESSION_USER_KEY

    session = client.session
    session[SESSION_USER_KEY] = student.id
    session.save()
    key = session.session_key

    with patch("apps.accounts.services._delete_sessions_for", return_value=(0, 0)):
        erase_account(student)

    from django.contrib.sessions.models import Session

    assert Session.objects.filter(session_key=key).exists(), (
        "the scan was supposed to be disabled for this test, so the row should "
        "survive — otherwise the second layer is not what is being measured"
    )

    from django.test import RequestFactory

    from apps.accounts.sessions import session_user

    request = RequestFactory().get("/")
    request.session = client.session
    assert session_user(request) is None, (
        "a tombstoned account still resolved to a signed-in user; the second "
        "layer does not hold and erasure leaves the device signed in"
    )
