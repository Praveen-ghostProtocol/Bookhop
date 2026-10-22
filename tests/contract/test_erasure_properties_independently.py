"""`DATA-MODEL.md` §10.1's erasure table, re-derived from the specification.

**Why this exists even though `tests/e2e/test_deletion.py` is sound.** §10.3
assigns that file to test-qa *"and written independently"*, and the implementer
wrote it. QA read it and found the content sound — but **reading a test tells
you it is internally coherent, not that it is right**, and the risk
independence addresses is not sloppiness. It is a *shared blind spot*: a test
written from the implementation inherits the implementation's misconceptions,
and both are then wrong together in a way no amount of reading detects.

So rather than rewrite a sound twenty-thousand-character file to change its
author — which buys no coverage and which S4 will have to redo anyway when the
four deferred assertions gain their subjects — QA re-derived the properties
**that can be checked today** straight from §10.1's table, and asserts them
here. If this agrees, the deferral is safe and QA can say so with a measurement
instead of with a reading. If it disagrees, independence has just earned itself
and the rewrite stops being a hygiene question.

The two properties chosen are the ones where implementer and test are most
likely to share an assumption:

* **step 7's "untouched" list** — the direction a deletion feature gets wrong,
  because every instinct in "delete my account" pulls towards deleting more,
  and what must survive is precisely the record that the deletion was lawful;
* **the salt's location** — §10.1's re-identification claim rests on a secret
  *"not stored in the database"*, which is a property of deployment rather than
  of code, and the kind of thing a test written beside the code assumes.
"""

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db


@pytest.fixture
def erased_student(db):
    """A student with one row in each of §10.1 step 7's untouched tables,
    erased through the real service."""
    import hashlib

    from apps.accounts.models import NoticeVersion, User
    from apps.accounts.services import erase_account, grant_consent
    from apps.core.models import Campus, City
    from apps.core.services import record_audit

    body = "PRIVACY for the erasure derivation"
    notice = NoticeVersion.objects.create(
        kind="PRIVACY", version=1, locale="en", body_md=body,
        sha256=hashlib.sha256(body.encode()).hexdigest(),
        published_at=timezone.now(),
    )
    city = City.objects.create(name="Chennai", state="Tamil Nadu")
    campus = Campus.objects.create(
        city=city, name="Erasure Campus", slug="erasure",
        email_domains=["example.test"],
    )
    user = User.objects.create(
        email="erasure-derivation@example.test", display_name="To Be Erased",
        campus=campus, city=city, status="ACTIVE",
        adult_verified=True, campus_verified=True,
        email_verified_at=timezone.now(),
    )
    pseudonym = user.person_pseudonym
    email = user.email

    grant_consent(user, "account", notice, "SIGNUP_FORM", None, "qa")
    record_audit(user, "qa.before_erasure", user)

    erase_account(user, reason="USER_REQUEST")
    user.refresh_from_db()
    return user, pseudonym, email


def test_the_record_that_the_deletion_was_lawful_survives_the_deletion(erased_student):
    """**§10.1 step 7, and it is the direction a deletion feature gets wrong.**

    *"Untouched: `repeat_infringer_records`, `audit_log`,
    `personal_data_access_log`, `age_verification_events`, `consents`, security
    logs."* Every instinct in "delete my account" pulls towards deleting more,
    and `COMPLIANCE.md` §7 is explicit that it *"never means `DELETE FROM
    users`"* — purge some rows, pseudonymise some, **and leave these alone**.

    What these rows are is the evidence that the erasure itself was lawful and
    that consent was given before it: the `consents` ledger, the audit chain,
    and the age decision. An over-eager erasure destroys the proof that the
    processing it is erasing was permitted — which is the worst possible thing
    to be unable to show, because the only party who asks for it is a regulator
    after a complaint.

    Derived from §10.1's table rather than from the erasure code, on tables
    that exist today.
    """
    user, pseudonym, _email = erased_student

    from apps.accounts.models import Consent
    from apps.core.models import AuditLog

    consents = Consent.objects.filter(user_pseudonym=pseudonym)
    assert consents.exists(), (
        "the consent ledger was destroyed by erasure. §10.1 step 7 lists "
        "`consents` as untouched, and it is the record that the processing "
        "being erased was permitted in the first place"
    )

    audit = AuditLog.objects.filter(actor_pseudonym=pseudonym)
    assert audit.exists(), (
        "audit rows for the erased user are gone. §10.1 step 7 lists "
        "`audit_log` as untouched, and §8 makes it append-only precisely so "
        "that a deletion cannot remove the record of itself"
    )

    assert AuditLog.objects.filter(action__icontains="eras").exists() or \
        AuditLog.objects.filter(action__icontains="delete").exists(), (
        "§10.1 step 8 requires an `audit_log` row for the erasure itself; no "
        f"row names it: {sorted(set(AuditLog.objects.values_list('action', flat=True)))}"
    )


def test_the_identity_is_gone_and_the_pseudonym_is_not(erased_student):
    """**§10.1 step 2**, the half that makes the retained record pseudonymous
    rather than anonymous — which is what lets §9.2's metric still work.

    Asserted from the table's own column list rather than from the service, so
    a future step that NULLs one more column than §7 permits shows up here.
    """
    user, pseudonym, _email = erased_student

    assert user.status == "TOMBSTONED"
    assert user.tombstoned_at is not None
    assert not user.email, f"email survived erasure: {user.email!r}"
    assert not user.display_name, f"display_name survived: {user.display_name!r}"
    assert user.person_pseudonym == pseudonym, (
        "the pseudonym changed during erasure, so every retained row that "
        "references it is now orphaned and §9.2's repeat-transfer metric "
        "cannot find the deleted user's history — which §10.3 calls the "
        "central claim of this data model"
    )


def test_the_tombstone_salt_is_not_recoverable_from_the_database(erased_student):
    """**§10.1's re-identification claim, which rests on a deployment property
    rather than on code.**

    *"The `user_tombstones.email_hash` is salted with a server-side secret
    **not stored in the database**, so a database-only compromise cannot
    re-identify by rainbow-table."*

    That is §10.3 (c) — *cannot be re-linked by any query available to a staff
    account* — and it is exactly the kind of claim a test written beside the
    code assumes rather than checks, because from inside the process the secret
    is simply available. Checked here the way an attacker with a database dump
    would: the hash must not equal the unsalted digest of the address, and the
    secret must not appear in any column of the tombstone row.
    """
    import hashlib

    from apps.accounts.models import UserTombstone

    user, pseudonym, email = erased_student
    tombstone = UserTombstone.objects.filter(person_pseudonym=pseudonym).first()
    assert tombstone is not None, "§10.1 step 1 requires a user_tombstones row"

    stored = (tombstone.email_hash or "").lower()
    assert stored, "the tombstone carries no email_hash"

    naive = hashlib.sha256(email.encode()).hexdigest()
    assert stored != naive, (
        "the tombstone hash is the plain SHA-256 of the address, so anyone "
        "with the dump and a list of campus addresses re-identifies every "
        "erased student by rainbow table. §10.1 requires a server-side salt"
    )
    assert stored != hashlib.sha256(email.lower().encode()).hexdigest()

    from django.conf import settings

    secret = getattr(settings, "BOOKHOP_TOMBSTONE_SALT", None) or getattr(
        settings, "SECRET_KEY", ""
    )
    if secret:
        row = " ".join(str(value) for value in (
            tombstone.email_hash, getattr(tombstone, "salt_version", ""),
            str(tombstone.person_pseudonym),
        ))
        assert secret not in row, (
            "the salt itself is in the tombstone row, so the database "
            "contains both halves and the salt buys nothing against a dump"
        )


def test_a_brand_new_session_for_a_tombstoned_principal_is_dead_on_arrival(
    erased_student
):
    """**§10.1a layer 2 — the guarantee, re-derived.**

    §10.1a is explicit that layer 1 (deleting session rows at erasure) is
    best-effort and that **no document may cite it as the reason erasure
    holds**: it matches nothing under a cookie-backed store, a rotated signing
    key or a changed serialiser. The guarantee is layer 2 — *"every
    authenticated request resolves the actor and refuses if `users.status =
    'TOMBSTONED'`, before any other precondition, regardless of whether the
    session is valid."*

    The only honest way to test that is the way §10.1a describes: plant a
    **brand-new, wholly valid** session after erasure, so layer 1 cannot be
    what refuses it, and check the request is still dead. Re-derived here
    independently because it is the single sentence the specification says must
    survive a refactor.
    """
    from django.test import Client

    from apps.accounts.sessions import SESSION_USER_KEY

    user, _pseudonym, _email = erased_student
    client = Client()
    session = client.session
    session[SESSION_USER_KEY] = user.id
    session.save()

    response = client.get("/api/v1/account")
    assert response.status_code == 401, (
        "a freshly planted, wholly valid session for a tombstoned principal "
        f"was served ({response.status_code}). Layer 1 cannot be what refuses "
        "this — the session was created after erasure — so layer 2 is not "
        "doing the work §10.1a says is the guarantee."
    )


def test_layer_two_refuses_tombstoned_only_and_not_suspended(db):
    """**§10.1a's WARNING, asserted so the "hardening" it forbids turns red.**

    *"Layer 2 refuses `TOMBSTONED` ONLY, and must not be 'hardened' to refuse
    `SUSPENDED`… Extending layer 2 to suspension would silently re-create P-1,
    and would do it in the one place no endpoint-level review would look."*

    A suspended student must still reach export, erasure, consent withdrawal
    and their own ticket (§2.5 Stack S). The asymmetry looks like an oversight
    to anyone reading layer 2 alone, which is exactly why it needs a test
    rather than a comment.
    """
    from django.test import Client

    from apps.accounts.models import User
    from apps.accounts.sessions import SESSION_USER_KEY
    from apps.core.models import Campus, City

    city = City.objects.create(name="Chennai", state="Tamil Nadu")
    campus = Campus.objects.create(
        city=city, name="Layer Two Campus", slug="layer-two",
        email_domains=["example.test"],
    )
    suspended = User.objects.create(
        email="suspended-layer2@example.test", display_name="Suspended",
        campus=campus, city=city, status="SUSPENDED",
        adult_verified=True, campus_verified=True,
    )
    client = Client()
    session = client.session
    session[SESSION_USER_KEY] = suspended.id
    session.save()

    response = client.get("/api/v1/account/export")
    assert response.status_code == 200, (
        "a suspended student was refused their s11 export "
        f"({response.status_code}). If layer 2 has been widened to refuse "
        "SUSPENDED, §10.1a's warning has come true and P-1 is back in the one "
        "place no endpoint-level review would look."
    )
