"""Consent as a ledger — DATA-MODEL §2, `COMPLIANCE.md` §7 row 18, PRD US-A3.

Four properties, and the first is the one everything else rests on:

  * **append-only, by the database.** A withdrawal inserts a row; nothing is
    ever updated in place. `Consent.objects.update(withdrawn_at=now())` is the
    obvious thing to write and the trigger refuses it.
  * **granular.** Six purpose keys, exactly the reduced P6 set, each
    independently grantable and withdrawable (AC-A3.2).
  * **versioned.** Every row names the `notice_versions` row the student agreed
    to (AC-A3.3), so *"we can show what a user agreed to on a given date"*
    (§8.1) is answerable.
  * **withdrawal is a toggle, not an email** (DPDP r.3(c)(i)) — asserted as the
    same function shape rather than as a promise.

The "no pre-ticked boxes" half of AC-A3.1 is a **rendered-HTML** property and is
frontend's and QA's; the service half is that a grant requires an explicit
`granted=True` and that nothing defaults it, which
`test_a_consent_row_is_a_grant_or_a_withdrawal_never_neither` covers from the
schema side.
"""

from datetime import timedelta

import pytest
from django.db import DatabaseError, transaction
from django.utils import timezone

from apps.accounts.models import CONSENT_PURPOSES, REQUIRED_CONSENT_PURPOSES, Consent, NoticeVersion
from apps.accounts.services import (
    consent_state,
    current_notice,
    grant_consent,
    missing_consents,
    withdraw_consent,
)
from apps.core.errors import ValidationFailed
from apps.core.models import AuditLog

pytestmark = pytest.mark.django_db


def test_the_six_purposes_are_exactly_the_reduced_p6_set():
    """DATA-MODEL §2: *"**exactly** the reduced P6 set … `payments` and
    `fee_billing` dropped."* A seventh key is a seventh lawful basis and needs
    privacy-compliance sign-off, so the set is asserted rather than described.

    `service_improvement` is named in `COMPLIANCE.md` §7 row 21 as the key that
    *would* be needed if `search_events` ever carried an actor key. It is
    deliberately absent, and this is where that stays visible.
    """
    assert set(CONSENT_PURPOSES) == {
        "account", "listing_publication", "location_proximity",
        "chat", "safety_moderation", "notifications",
    }
    assert "payments" not in CONSENT_PURPOSES
    assert "fee_billing" not in CONSENT_PURPOSES
    assert "service_improvement" not in CONSENT_PURPOSES


def test_granting_appends_a_row_naming_the_notice_version(pending_student, privacy_notice):
    grant_consent(pending_student, "chat", privacy_notice, "SIGNUP_FORM", "198.51.100.7", "pytest")
    row = Consent.objects.get(purpose_key="chat")
    assert row.granted_at is not None
    assert row.withdrawn_at is None
    assert row.notice_version_id == privacy_notice.id
    assert row.user_pseudonym == pending_student.person_pseudonym
    assert row.mechanism == "SIGNUP_FORM"
    assert AuditLog.objects.filter(action="accounts.consent_granted").exists()


def test_withdrawing_appends_and_never_updates(student, privacy_notice):
    """AC-A3.2, verbatim: *"turning it off appends a `consents` row with
    `withdrawn_at` set and **never updates a row in place.** QA asserts row
    count increases and no prior row changed."*"""
    grant_consent(student, "notifications", privacy_notice, "SIGNUP_FORM", None, "pytest")
    before = list(
        Consent.objects.order_by("id").values("id", "purpose_key", "granted_at", "withdrawn_at")
    )

    withdraw_consent(student, "notifications", "SETTINGS_TOGGLE", None, "pytest")

    after = list(
        Consent.objects.order_by("id").values("id", "purpose_key", "granted_at", "withdrawn_at")
    )
    assert len(after) == len(before) + 1, "a withdrawal did not append a row"
    assert after[: len(before)] == before, "a prior consent row was modified"
    assert after[-1]["withdrawn_at"] is not None
    assert after[-1]["granted_at"] is None


def test_a_consent_row_cannot_be_updated_or_deleted(student, engine):
    """The trigger, not the convention. `consents` is *the record that the
    deletion itself was lawful* (§7 row 18), so it has to resist the
    application as well as the user — and
    `Consent.objects.filter(...).update(withdrawn_at=now())` is the obvious
    thing a developer writes."""
    row = Consent.objects.filter(user_pseudonym=student.person_pseudonym).first()
    assert row is not None

    with pytest.raises(DatabaseError, match="append-only"):
        with transaction.atomic():
            Consent.objects.filter(id=row.id).update(withdrawn_at=timezone.now())
    with pytest.raises(DatabaseError, match="append-only"):
        with transaction.atomic():
            Consent.objects.filter(id=row.id).delete()

    row.refresh_from_db()
    assert row.withdrawn_at is None, f"consents was mutable on {engine}"


def test_the_refusal_message_names_the_table_and_the_operation(student, engine):
    """`CLAUDE.md` rule 16: *"assert the message text, not the exit status."*
    One shared plpgsql body serves three tables, so `TG_TABLE_NAME` and `TG_OP`
    are what make a refusal diagnosable — and a `%` that failed to interpolate
    would leave a message that still said "append-only"."""
    row = Consent.objects.filter(user_pseudonym=student.person_pseudonym).first()
    with pytest.raises(DatabaseError) as refusal:
        with transaction.atomic():
            Consent.objects.filter(id=row.id).delete()
    message = str(refusal.value)
    assert "consents" in message, f"TG_TABLE_NAME did not interpolate on {engine}: {message}"
    assert "DELETE" in message, f"TG_OP did not interpolate on {engine}: {message}"
    assert "a new row, never a rewrite" in message


def test_current_state_is_the_latest_row_per_purpose(student, privacy_notice):
    """DATA-MODEL §2. A second implementation of "which row wins" is how a
    withdrawal silently stops counting, so there is one — `consent_state`."""
    grant_consent(student, "chat", privacy_notice, "SIGNUP_FORM", None, "pytest")
    assert consent_state(student)["chat"] is True

    withdraw_consent(student, "chat", "SETTINGS_TOGGLE", None, "pytest")
    assert consent_state(student)["chat"] is False

    grant_consent(student, "chat", privacy_notice, "SETTINGS_TOGGLE", None, "pytest")
    assert consent_state(student)["chat"] is True
    assert Consent.objects.filter(purpose_key="chat").count() == 3, (
        "the ledger lost a row; the history is the evidence"
    )


def test_every_purpose_appears_in_the_state_even_when_never_granted(pending_student):
    state = consent_state(pending_student)
    assert set(state) == set(CONSENT_PURPOSES)
    assert all(value is False for value in state.values())


def test_withdrawing_a_purpose_never_granted_is_a_no_op(student):
    """Idempotent: a ledger whose rows can be appended by a client loop is a
    ledger nobody can read."""
    before = Consent.objects.count()
    withdraw_consent(student, "location_proximity", "SETTINGS_TOGGLE", None, "pytest")
    withdraw_consent(student, "location_proximity", "SETTINGS_TOGGLE", None, "pytest")
    assert Consent.objects.count() == before


def test_an_unknown_purpose_is_refused(student, privacy_notice):
    with pytest.raises(ValidationFailed, match="six consent purposes"):
        grant_consent(student, "payments", privacy_notice, "SIGNUP_FORM", None, "pytest")
    with pytest.raises(ValidationFailed):
        withdraw_consent(student, "service_improvement", "SETTINGS_TOGGLE", None, "pytest")


def test_a_grant_with_no_notice_version_is_refused(pending_student):
    """AC-A3.3: the screen names *"the exact `notice_versions` version the
    student is agreeing to"*. A consent row with no version cannot answer
    §8.1's question, so it is refused rather than written with a NULL."""
    with pytest.raises(ValidationFailed, match="notice version"):
        grant_consent(pending_student, "account", None, "SIGNUP_FORM", None, "pytest")


def test_a_consent_row_is_a_grant_or_a_withdrawal_never_neither(student, privacy_notice):
    """The CHECK, as a refusal. Without it a row with both timestamps NULL is a
    consent record that says nothing, and "the latest row wins" would read it
    as a grant — `CLAUDE.md` rule 18: the test that matters is that the bad
    input is **refused**, not that the column exists."""
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            Consent.objects.create(
                user=student, user_pseudonym=student.person_pseudonym,
                purpose_key="chat", notice_version=privacy_notice,
                granted_at=None, withdrawn_at=None, mechanism="SIGNUP_FORM",
            )
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            Consent.objects.create(
                user=student, user_pseudonym=student.person_pseudonym,
                purpose_key="chat", notice_version=privacy_notice,
                granted_at=timezone.now(), withdrawn_at=timezone.now(),
                mechanism="SIGNUP_FORM",
            )


def test_granting_the_required_purposes_activates_the_account(pending_student, privacy_notice):
    """JOURNEYS J1 step 7: `status='ACTIVE'` once age, campus and consent are
    done. `pending_student` is already campus-verified."""
    pending_student.adult_verified = True
    pending_student.save(update_fields=["adult_verified"])
    assert missing_consents(pending_student) == list(REQUIRED_CONSENT_PURPOSES)

    for purpose in REQUIRED_CONSENT_PURPOSES:
        grant_consent(pending_student, purpose, privacy_notice, "SIGNUP_FORM", None, "pytest")

    pending_student.refresh_from_db()
    assert pending_student.status == "ACTIVE"
    assert missing_consents(pending_student) == []


def test_withdrawing_a_required_purpose_leaves_the_student_signed_in(student):
    """JOURNEYS J1 step 5: *"Declines a required purpose … the screen says which
    action that blocks and leaves the student signed in."* So the withdrawal
    succeeds and `require_actor` is what refuses the next write — not a
    sign-out, which would make withdrawal feel like a punishment."""
    withdraw_consent(student, "account", "SETTINGS_TOGGLE", None, "pytest")
    student.refresh_from_db()
    assert student.status == "ACTIVE"
    assert missing_consents(student) == ["account"]


def test_the_notice_version_is_immutable(privacy_notice, engine):
    """DATA-MODEL §2: *"Trigger blocks all UPDATE and DELETE."* A correction is
    a new version, because §8.1 requires showing what was agreed on a date."""
    with pytest.raises(DatabaseError, match="append-only"):
        with transaction.atomic():
            NoticeVersion.objects.filter(id=privacy_notice.id).update(body_md="rewritten")
    with pytest.raises(DatabaseError, match="append-only"):
        with transaction.atomic():
            NoticeVersion.objects.filter(id=privacy_notice.id).delete()
    privacy_notice.refresh_from_db()
    assert privacy_notice.body_md != "rewritten", f"notice_versions was mutable on {engine}"


def test_a_gated_locale_falls_back_to_english_rather_than_to_nothing(privacy_notice):
    """`i18n.ta_enabled` is seeded **false** and stays false until a native
    speaker signs off (THREAT-MODEL §6.1), so a Tamil notice may legitimately
    not exist. A fallback is right; **a missing legal page is not.**"""
    assert current_notice("PRIVACY", "ta").locale == "en"
    assert current_notice("PRIVACY", "en").id == privacy_notice.id
    assert current_notice("TERMS", "en") is None, (
        "an unpublished notice must read as absent rather than as another kind"
    )


def test_the_latest_published_version_wins(privacy_notice):
    newer = NoticeVersion.objects.create(
        kind="PRIVACY", version="2026-12-01.1", locale="en",
        body_md="# Privacy\n\nNewer.", sha256="1" * 64,
        published_at=privacy_notice.published_at + timedelta(days=1),
    )
    assert current_notice("PRIVACY", "en").id == newer.id
