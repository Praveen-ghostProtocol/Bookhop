"""`API-CONTRACT.md` §2.5 — the standing preconditions, asked of every S1 write.

§2.5 is the shortest normative list in the contract and the most reused: eight
preconditions, *"checked in L1, in this order"*, on **every student-facing
write**. Every later slice's writes inherit it. S1 is the slice where it is
cheapest to find out whether it is actually there, because S1's writes are a
profile field and a consent toggle rather than a listing or an offer.

Preconditions 1, 3, 4, 5, 6 and 7 are either exercised elsewhere or have no
subject in S1 (there is nothing campus-scoped to fetch and no gate to be closed
against a profile edit). **Precondition 2 — `status='ACTIVE'` → else `403
SUSPENDED` — has a subject in S1 and is the one tested here, because suspension
is the mechanism behind two things that matter: the
`REVOKED_MINOR_DISCOVERED` procedure in `DATA-MODEL.md` §2 (*"suspend, erase,
log"*) and staff enforcement.

**This file contains a failing test. It is a finding, reported not fixed.**
"""

import json
import uuid

import pytest

pytestmark = pytest.mark.django_db


def _idempotent(client, method, path, body):
    return getattr(client, method)(
        path,
        data=json.dumps(body),
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )


@pytest.fixture
def signed_in_active(client, student, settings):
    """A signed-in, ACTIVE, fully-verified student.

    The session is planted rather than walked, because this file is about §2.5
    and not about J1 — the journey is driven for real in
    `tests/e2e/test_erasure_sessions.py`, whose first test is the guard that this
    session key is the one the application reads.
    """
    from django.contrib.sessions.backends.db import SessionStore

    from apps.accounts.models import User

    User.objects.filter(pk=student.pk).update(
        status="ACTIVE", adult_verified=True, campus_verified=True,
        display_name="Original Name",
    )
    session = SessionStore()
    session["_bookhop_user_id"] = student.pk
    session.save()
    client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
    student.refresh_from_db()
    return student


def test_an_active_student_can_write_so_the_suspended_case_is_a_real_comparison(
    client, signed_in_active
):
    """`CLAUDE.md` rule 12 on the test below. A `403` for a suspended student
    proves nothing unless an active student gets a `200` through the same call —
    otherwise the refusal could be a missing header, a bad body or an unmounted
    route."""
    response = _idempotent(
        client, "patch", "/api/v1/account", {"display_name": "Active Name"}
    )
    assert response.status_code == 200, response.content
    signed_in_active.refresh_from_db()
    assert signed_in_active.display_name == "Active Name"


#: The S1 student-facing writes §2.5 governs, with the L2 route and method from
#: `API-CONTRACT.md` §5.1. Per entry rather than one loop over a path list, so a
#: failure names the write rather than an index.
S1_WRITES = {
    "profile edit": ("patch", "/api/v1/account", {"display_name": "Suspended Name"}),
    "consent toggle": (
        "put", "/api/v1/account/consents/notifications", {"granted": True},
    ),
}


@pytest.mark.parametrize("write", sorted(S1_WRITES))
def test_a_suspended_student_is_refused_every_student_facing_write(
    write, client, signed_in_active
):
    """**FINDING — MATERIAL, FAILING. `API-CONTRACT.md` §2.5 precondition 2 is
    not enforced on any S1 write.**

    Measured on PostgreSQL 16 and SQLite: with `users.status = 'SUSPENDED'`,

    * `PATCH /api/v1/account` returns **200** and the display name changes;
    * `PUT /api/v1/account/consents/notifications` returns **200** and appends a
      consent row.

    §2.5 requires `403 SUSPENDED`, second in the order, before adult and campus
    verification are even consulted.

    **Why this is material rather than cosmetic in a slice whose writes are
    small.** Suspension is not a cosmetic state. `DATA-MODEL.md` §2 makes
    *suspend, erase, log* the documented response to `REVOKED_MINOR_DISCOVERED` —
    a minor discovered after verification — and `user_tombstones.reason` carries
    `STAFF_ENFORCEMENT` as a deletion reason, which implies a suspension that
    held. An account that keeps writing after it is suspended makes both of those
    procedures advisory. And the precondition is **one check in one place** that
    every S2 listing write and every S4 offer write will inherit: the cheapest
    moment to find it absent is now, and the most expensive is after four slices
    have been written on top of it.

    **Not negotiable down to a known issue**, per the charter: the age-revocation
    path is compliance-derived (`COMPLIANCE.md` §1.4's suspend-erase-log
    instruction), and a compliance-derived test failing is a cto escalation.

    **What this test does NOT assert, deliberately.** It does not assert a 403
    for `POST /api/v1/account/erase`. §2.5 read literally would refuse a
    suspended student their DPDP s12 erasure right and their s11 access right,
    which cannot be the intent — and measured behaviour today is that erasure
    succeeds for a suspended student. **That is a contradiction in the
    specification, not a defect in the build, and it is escalated to cto
    separately rather than smuggled into this assertion.** Nor does it assert
    anything about *reads*: a suspended student reaching `GET /account` is
    unspecified and defensible, and is recorded in
    `tests/e2e/test_erasure_sessions.py::test_the_second_layer_is_narrow_and_only_tombstoned_is_refused`.
    """
    from apps.accounts.models import User

    method, path, body = S1_WRITES[write]
    User.objects.filter(pk=signed_in_active.pk).update(status="SUSPENDED")

    response = _idempotent(client, method, path, body)

    assert response.status_code == 403, (
        f"{write}: a SUSPENDED student's write returned {response.status_code}, "
        f"not 403. API-CONTRACT §2.5 precondition 2 is not enforced. "
        f"Body: {response.content[:300]!r}"
    )
    assert response.json()["error"]["code"] == "SUSPENDED", (
        f"{write}: refused, but not with the code §2.5 names, so a client cannot "
        f"tell suspension from any other 403. Body: {response.content[:300]!r}"
    )
