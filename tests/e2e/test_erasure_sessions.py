"""Attack the one step of `erase_account` that depends on a decode succeeding.

**Why this file exists.** `_delete_sessions_for` scans the session table,
**decodes each row** and matches a user id. It is the only step in
`DATA-MODEL.md` §10.1 that rests on a decode rather than on a column comparison,
it swallows the decode exception by design, and a signing-key rotation, a
changed serialiser or a non-database session backend would make it **silently
match nothing while `erase_account` reports success.** The failure mode is a
deleted account still signed in on the student's phone — `JOURNEYS.md` J8 step 4
promises *"Your account is gone." Signed out*.

The existing test proves the scan deletes the session it created. **That is not
the same claim.** It cannot distinguish "the scan found and deleted the session"
from "the scan found nothing, which also leaves no session behind". So every
test here is written as the property a student would notice — *can this cookie
still reach my account?* — and the scan's row count is only ever a secondary
assertion.

**Method note (charter: verify behaviour independently of implementation).**
Nothing here reads `_delete_sessions_for`. Every session is created by walking
the real journey: `POST /auth/start`, run the queue, read the link out of the
email the way the student reads it, `GET /auth/c/{token}`. The one internal name
used is the session key the journey itself puts in the session dict, discovered
by inspecting a signed-in session, and guarded against renaming by
`test_the_session_key_this_file_plants_is_the_one_the_application_reads`.

**The answer, stated here so a reader does not have to infer it from nine tests:
the scan CAN be made to match nothing — three ways, all measured below — and
`erase_account` does report success in all three. No live session results,
because a second and independent layer rejects a `TOMBSTONED` user at request
time.** That layer is what makes the decode scan non-load-bearing, which is
`CLAUDE.md` rule 14 satisfied by accident rather than by design: **no document
names it and no test but this one asserts it.** If it were removed — a refactor
of the session-to-user lookup would do it — all three attacks become live
sessions on a deleted account, and every pre-existing test would stay green.
"""

import re

import pytest
from django.contrib.sessions.models import Session
from django.core import mail

pytestmark = pytest.mark.django_db

#: The key the signed-in session carries. Discovered behaviourally (sign in,
#: read the session), not from the service layer.
SESSION_USER_KEY = "_bookhop_user_id"

#: A page that exists only for a signed-in student. `API-CONTRACT.md` §5.1 maps
#: `GET /account` to the profile.
SIGNED_IN_PAGE = "/account"


def _sign_in(client, email, settings, capture):
    """Walk J1 steps 2 and 3 for real, and return the student's `users` row.

    The token is read out of the email body because that is where the student
    reads it: `DATA-MODEL.md` §2 says `email_login_tokens.token_hash` holds a
    sha256 and *"plaintext never stored"*, so there is no other honest way in.
    """
    from apps.accounts.models import User
    from apps.core.jobs import run_pending_jobs

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    mail.outbox.clear()
    with capture(execute=True):
        assert client.post("/auth/start", {"email": email}).status_code == 302
    run_pending_jobs()
    assert mail.outbox, "no sign-in email was sent, so this test has no session"
    token = re.search(r"/auth/c/(\S+)", mail.outbox[-1].body).group(1)
    assert client.get(f"/auth/c/{token}").status_code == 302
    assert client.get(SIGNED_IN_PAGE).status_code == 200, (
        "the journey did not produce a signed-in session, so nothing below "
        "asserts anything"
    )
    return User.objects.get(email=email)


def _rows_that_decode_to(user_id):
    """`(rows naming this user, rows that decoded to nothing)`.

    The second list is the subject of half this file, so it is returned rather
    than filtered away. Django's `SessionBase.decode` returns `{}` instead of
    raising, which is itself why a scan can fail silently.
    """
    live, undecodable = [], []
    for row in Session.objects.all():
        data = row.get_decoded()
        if not data:
            undecodable.append(row.session_key)
        elif data.get(SESSION_USER_KEY) == user_id:
            live.append(row.session_key)
    return live, undecodable


def _is_signed_in(client):
    return client.get(SIGNED_IN_PAGE).status_code == 200


# ---------------------------------------------------------------------------
# 0. the guard that stops this file passing vacuously
# ---------------------------------------------------------------------------


def test_the_session_key_this_file_plants_is_the_one_the_application_reads(
    client, signup_campus, privacy_notice, settings, django_capture_on_commit_callbacks
):
    """`CLAUDE.md` rule 12. Several attacks below plant or inspect
    `_bookhop_user_id`. If the application renamed that key, each would plant a
    session nobody can use and every assertion would pass for the wrong reason —
    a whole file of vacuous guards reported as coverage.

    So: a session planted with this key and nothing else must sign a real
    student in. That is what makes the rest of the file mean anything.
    """
    from django.contrib.sessions.backends.db import SessionStore

    user = _sign_in(
        client, "keyguard@example.ac.in", settings, django_capture_on_commit_callbacks
    )
    fresh = SessionStore()
    fresh[SESSION_USER_KEY] = user.id
    fresh.save()
    client.cookies[settings.SESSION_COOKIE_NAME] = fresh.session_key

    assert _is_signed_in(client), (
        f"a session carrying only {SESSION_USER_KEY!r} does not sign this "
        "student in, so this file's planted sessions prove nothing. Find the "
        "key the application actually reads and update SESSION_USER_KEY."
    )


# ---------------------------------------------------------------------------
# 1. the property, through the surface a student meets
# ---------------------------------------------------------------------------


def test_erasure_signs_the_student_out_on_the_device_they_deleted_from(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """`JOURNEYS.md` J8 step 4: *"Your account is gone." Signed out.* Driven
    through `POST /account/delete`, not the service function, because the student
    presses the button."""
    user = _sign_in(client, "j8@example.ac.in", settings, django_capture_on_commit_callbacks)
    client.post("/account/age", {"date_of_birth": "2001-04-17"})

    assert client.post("/account/delete", {"confirm": "yes"}).status_code in (200, 302)

    assert not _is_signed_in(client), (
        "the account was deleted and this browser is still signed in"
    )
    live, _ = _rows_that_decode_to(user.id)
    assert live == [], f"session rows for the erased user survive: {live}"


def test_erasure_reaches_every_device_not_only_the_one_that_asked(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """`DATA-MODEL.md` §10.1 step 3 says *sessions*, plural. A student who signed
    in on a laptop and a phone and then deletes from the laptop must not stay
    signed in on the phone — the exact failure the brief names."""
    from django.contrib.sessions.backends.db import SessionStore
    from django.test import Client

    from apps.accounts.services import erase_account

    user = _sign_in(client, "two@example.ac.in", settings, django_capture_on_commit_callbacks)
    phone = SessionStore()
    phone[SESSION_USER_KEY] = user.id
    phone.save()

    live_before, _ = _rows_that_decode_to(user.id)
    assert len(live_before) == 2, f"expected two live sessions, found {live_before}"

    erase_account(user)

    live_after, _ = _rows_that_decode_to(user.id)
    assert live_after == [], f"a second device keeps its session row: {live_after}"

    other = Client()
    other.cookies[settings.SESSION_COOKIE_NAME] = phone.session_key
    assert not _is_signed_in(other), "the phone is still signed in to a deleted account"


# ---------------------------------------------------------------------------
# 2. the attacks on the decode
# ---------------------------------------------------------------------------


def test_an_undecodable_row_beside_a_valid_one_does_not_hide_the_valid_one(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """The swallow has to be **per row**, not per scan.

    If the exception handling sat around the loop rather than inside it, one
    unreadable session — a row left by an older key, a half-written row, a row
    from a rolled-back deployment — would abort the scan and every session after
    it would survive, while `erase_account` still committed and reported success.

    The second assertion is the other half, and it matters as much: the scan must
    not delete a row it cannot attribute. That row is somebody else's session.
    """
    from datetime import timedelta

    from django.contrib.sessions.backends.db import SessionStore
    from django.utils import timezone

    from apps.accounts.services import erase_account

    user = _sign_in(client, "mixed@example.ac.in", settings, django_capture_on_commit_callbacks)
    Session.objects.create(
        session_key="qagarbage" + "0" * 23,
        session_data="this is not a signed blob",
        expire_date=timezone.now() + timedelta(days=1),
    )
    second = SessionStore()
    second[SESSION_USER_KEY] = user.id
    second.save()

    live_before, undecodable_before = _rows_that_decode_to(user.id)
    assert len(live_before) == 2 and len(undecodable_before) == 1, (
        f"precondition not met: live={live_before} undecodable={undecodable_before}"
    )

    erase_account(user)

    live_after, undecodable_after = _rows_that_decode_to(user.id)
    assert live_after == [], (
        "an unreadable row beside a valid one stopped the scan: these sessions "
        f"for the erased user survive: {live_after}"
    )
    assert len(undecodable_after) == 1, (
        "the scan deleted a session row it could not attribute to anyone. That "
        "is another student's session, deleted by a guess."
    )


def test_a_rotated_signing_key_with_a_fallback_does_not_hide_the_session(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """The supported rotation: the new key signs, the old key still verifies
    (`SECRET_KEY_FALLBACKS`). The student is still signed in, so the session is
    live and erasure must reach it.

    **VERIFIED HERE** (`CLAUDE.md` rule 17): mid-rotation `GET /account` is 200,
    asserted below, so this is a real live session and not a dead row.
    """
    from apps.accounts.services import erase_account

    old_key = settings.SECRET_KEY
    user = _sign_in(client, "rot1@example.ac.in", settings, django_capture_on_commit_callbacks)

    settings.SECRET_KEY = "qa-rotated-key-with-fallback-aaaaaaaaaaaa"
    settings.SECRET_KEY_FALLBACKS = [old_key]

    assert _is_signed_in(client), (
        "the fallback key did not keep the session readable, so this test is "
        "not exercising a live session and would pass vacuously"
    )

    erase_account(user)

    assert not _is_signed_in(client), "a key rotation hid a live session from erasure"
    live, _ = _rows_that_decode_to(user.id)
    assert live == [], f"session rows survive a rotation with a fallback: {live}"


def test_a_rotated_signing_key_without_a_fallback_leaves_a_row_erasure_did_not_reach(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """**FINDING (minor, reported not fixed): the scan matches nothing and the
    row survives.**

    Rotate the signing key with no fallback — a key compromise, the documented
    emergency — and every stored session becomes undecodable. The student is
    signed out, which is correct and is the point of rotating. But the scan then
    matches nothing, `erase_account` reports success, and **the session row stays
    in the table carrying the erased student's user id in its data.**

    Two reasons it is reported rather than shrugged at:

    1. `DATA-MODEL.md` §10.1 step 3 says *delete* `sessions`. A surviving row is
       retained personal data after an erasure the student was told completed.
    2. The row is unreadable only while the old key is unavailable. Restore that
       key — from a backup, a rolled-back deploy, a `SECRET_KEY_FALLBACKS` entry
       added later — and the row decodes to the erased user again. **The only
       thing then between it and a live session is the second layer asserted at
       the bottom of this file.**

    The assertion records the measured truth, so it goes red if the behaviour
    changes in either direction.
    """
    from apps.accounts.services import erase_account

    user = _sign_in(client, "rot2@example.ac.in", settings, django_capture_on_commit_callbacks)
    rows_before = Session.objects.count()
    assert rows_before, "no session row to begin with"

    settings.SECRET_KEY = "qa-rotated-key-no-fallback-bbbbbbbbbbbbb"
    settings.SECRET_KEY_FALLBACKS = []

    assert not _is_signed_in(client), (
        "a key rotation with no fallback left the session readable; the "
        "precondition of this test does not hold"
    )

    erase_account(user)  # reports success

    assert not _is_signed_in(client), (
        "a session survived BOTH the key rotation and the erasure, which is the "
        "live-session failure this file was written to look for"
    )
    live, undecodable = _rows_that_decode_to(user.id)
    assert live == [], f"unexpectedly still attributable: {live}"
    assert len(undecodable) == rows_before, (
        "MEASURED BEHAVIOUR CHANGED. This test records that the erasure scan "
        f"leaves {rows_before} undecodable session row(s) behind after a key "
        f"rotation; it now leaves {len(undecodable)}. If the scan was changed to "
        "delete by a means that needs no decode, this assertion is the one to "
        "delete — and the finding in the docstring is closed."
    )


def test_a_changed_session_serialiser_makes_the_scan_match_nothing(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """**FINDING (minor; same shape as the rotation, different cause).**

    `SESSION_SERIALIZER` is a setting. Change it and the signature on every
    stored row still verifies while the payload no longer parses, so Django's
    `decode` returns `{}` and the scan attributes nothing. `erase_account`
    reports success and the row survives with the erased user's id inside it,
    recoverable the moment the serialiser is changed back.

    This is the `ASSUMED THERE` half of `CLAUDE.md` rule 17 made concrete: the
    erasure guarantee is coupled to two settings — `SESSION_ENGINE` and
    `SESSION_SERIALIZER` — and **nothing in the repository asserts that
    coupling.**
    """
    from apps.accounts.services import erase_account

    user = _sign_in(client, "ser@example.ac.in", settings, django_capture_on_commit_callbacks)
    rows_before = Session.objects.count()
    assert rows_before, "no session row to begin with"

    settings.SESSION_SERIALIZER = "tests.e2e._weird_serializer.PrefixedJSONSerializer"

    assert not _is_signed_in(client), (
        "the stored rows still decoded under the new serialiser, so this test "
        "is not exercising the divergence it claims to"
    )

    erase_account(user)

    live, undecodable = _rows_that_decode_to(user.id)
    assert live == [], f"unexpectedly still attributable: {live}"
    assert len(undecodable) == rows_before, (
        "MEASURED BEHAVIOUR CHANGED: the serialiser divergence no longer leaves "
        f"rows behind ({len(undecodable)} of {rows_before}). See the rotation "
        "test's note."
    )
    assert not _is_signed_in(client)


def test_a_non_database_session_backend_makes_the_scan_delete_nothing_at_all(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """**The attack the brief named, and the worst of the three, because there is
    no row to find at all.**

    With `SESSION_ENGINE = signed_cookies` the session lives entirely in the
    student's cookie. The session table is empty, so a scan over it deletes
    nothing and cannot fail; `erase_account` reports success; the cookie on the
    phone is byte-for-byte unchanged and still carries the user id.

    **Measured: the student is still signed out** — and the whole reason is the
    second layer, not this step. That is the finding: this step's contribution to
    `JOURNEYS.md` J8's *"Signed out"* is **zero** under a supported Django
    setting, and nothing says so.
    """
    from apps.accounts.services import erase_account

    settings.SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
    user = _sign_in(client, "cookie@example.ac.in", settings, django_capture_on_commit_callbacks)

    assert Session.objects.count() == 0, (
        "the cookie backend still wrote session rows, so this test is not "
        "exercising a non-database backend"
    )

    erase_account(user)  # nothing to scan, nothing deleted, success reported

    assert not _is_signed_in(client), (
        "FINDING, CRITICAL: with a non-database session backend the erasure "
        "scan deletes nothing and the deleted account is still signed in. The "
        "session step of DATA-MODEL §10.1 is the only thing that was supposed "
        "to prevent this."
    )


# ---------------------------------------------------------------------------
# 3. the layer that is actually doing the work, named so it cannot be removed
#    quietly
# ---------------------------------------------------------------------------


def test_a_tombstoned_user_is_rejected_by_something_other_than_the_session_scan(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """**The load-bearing assertion in this file, and before it nothing in the
    repository made it.**

    `CLAUDE.md` rule 14 asks which *other* layer catches a thing when one layer
    is exempted. All three attacks above exempt the session scan, and this is the
    answer: a request carrying a session that names a `TOMBSTONED` user is
    refused at request time, independently of whether any session row was
    deleted.

    Asserted by planting a **brand-new** session for the erased user *after*
    erasure — so the scan demonstrably cannot have deleted it, because it did not
    exist when the scan ran. If this goes red, every attack above becomes a live
    session on a deleted account and `JOURNEYS.md` J8's promise is false.
    """
    from django.contrib.sessions.backends.db import SessionStore

    from apps.accounts.services import erase_account

    user = _sign_in(client, "layer2@example.ac.in", settings, django_capture_on_commit_callbacks)
    user_id = user.id
    erase_account(user)

    planted = SessionStore()
    planted[SESSION_USER_KEY] = user_id
    planted.save()
    client.cookies[settings.SESSION_COOKIE_NAME] = planted.session_key

    assert not _is_signed_in(client), (
        "a session created AFTER erasure signs the deleted student in. The "
        "session scan is therefore the only thing standing between a deleted "
        "account and a live login, and every configuration divergence in this "
        "file becomes a live session on a deleted account."
    )


def test_the_second_layer_is_narrow_and_only_tombstoned_is_refused(
    client, signup_campus, privacy_notice, salt, settings,
    django_capture_on_commit_callbacks,
):
    """What the second layer does **not** cover, measured, so nobody reads the
    test above as "status is checked".

    `DATA-MODEL.md` §2 gives `users.status` four values. Measured: a session
    naming a `SUSPENDED` user is accepted and serves the account page; only
    `TOMBSTONED` is refused. That is defensible for a *read* — a suspended
    student still has DPDP access and erasure rights — and it is recorded here
    because the write-side consequence is a separate, failing finding in
    `tests/contract/test_standing_preconditions.py`.
    """
    from django.contrib.sessions.backends.db import SessionStore

    from apps.accounts.models import User
    from apps.accounts.services import erase_account

    user = _sign_in(client, "narrow@example.ac.in", settings, django_capture_on_commit_callbacks)
    user_id = user.id
    erase_account(user)

    def planted_session_reaches_the_account():
        session = SessionStore()
        session[SESSION_USER_KEY] = user_id
        session.save()
        client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        return _is_signed_in(client)

    assert not planted_session_reaches_the_account(), "TOMBSTONED was accepted"

    User.objects.filter(pk=user_id).update(status="SUSPENDED")
    assert planted_session_reaches_the_account(), (
        "a SUSPENDED user is now refused at request time too. That is a "
        "strengthening, not a break — delete this assertion and keep the "
        "TOMBSTONED one."
    )
