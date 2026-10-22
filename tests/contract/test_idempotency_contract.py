"""Idempotency and optimistic concurrency, from API-CONTRACT §4.

§4.1 is a four-way decision table, and the interesting thing about it is that
three of the four branches are failure branches. Written from the contract:

| situation                            | contract says             |
|--------------------------------------|---------------------------|
| no key on a POST/PATCH/DELETE        | `400 IDEMPOTENCY_KEY_REQUIRED` |
| same key, same body, response stored | the stored response verbatim, `Idempotency-Replayed: true` |
| same key, same body, no response yet | `409 IDEMPOTENCY_IN_PROGRESS`, `Retry-After: 2` |
| same key, different body             | `409 IDEMPOTENCY_KEY_REUSED` |

§4.2 (`expected_version`) has nothing versioned to act on until S4, and the
race it protects against cannot happen on this engine; both are skipped with
reasons rather than faked.
"""

import uuid
from datetime import timedelta

import pytest

from .engine_limits import unavailable
from django.conf import settings
from django.utils import timezone

from apps.core.errors import (
    IdempotencyInProgress,
    ValidationFailed,
    IdempotencyKeyRequired,
    IdempotencyKeyReused,
)
from apps.core.models import IdempotencyKey
from apps.core.services import Replay, idempotent, store_idempotent_response

pytestmark = pytest.mark.django_db

ENDPOINT = "POST /api/v1/transfers/1/accept"
BODY = {"expected_version": 3}


# --------------------------------------------------------------------------
# the four branches
# --------------------------------------------------------------------------


@pytest.mark.parametrize("missing", [None, ""])
def test_a_missing_key_is_the_contract_400(missing):
    with pytest.raises(IdempotencyKeyRequired) as exc:
        idempotent(user_id=7, key=missing, endpoint=ENDPOINT, body=BODY)
    assert exc.value.code == "IDEMPOTENCY_KEY_REQUIRED"
    assert exc.value.http_status == 400


def test_a_first_attempt_claims_the_key_and_records_the_endpoint():
    row = idempotent(user_id=7, key="k-1", endpoint=ENDPOINT, body=BODY)
    assert row.pk is not None
    assert row.endpoint == ENDPOINT
    assert row.response_status is None, "a claim must not look like a stored response"


def test_a_replay_before_the_response_exists_is_in_progress_with_retry_after():
    """API-CONTRACT §4.1: "The insert of the key row is the lock, so two
    simultaneous retries cannot both execute." The second caller must be told to
    come back, not allowed through and not told the request failed."""
    idempotent(user_id=7, key="k-2", endpoint=ENDPOINT, body=BODY)
    with pytest.raises(IdempotencyInProgress) as exc:
        idempotent(user_id=7, key="k-2", endpoint=ENDPOINT, body=BODY)
    assert exc.value.code == "IDEMPOTENCY_IN_PROGRESS"
    assert exc.value.http_status == 409
    assert exc.value.retry_after == 2


def test_a_replay_after_the_response_returns_it_verbatim():
    """"the stored response is returned verbatim" — so the body comes back as the
    same object, not re-serialised, and the handler does not run again."""
    row = idempotent(user_id=7, key="k-3", endpoint=ENDPOINT, body=BODY)
    stored = {"id": 1, "state": "ACCEPTED", "version": 4}
    store_idempotent_response(row, 200, stored)

    with pytest.raises(Replay) as exc:
        idempotent(user_id=7, key="k-3", endpoint=ENDPOINT, body=BODY)
    assert exc.value.status == 200
    assert exc.value.body == stored
    assert IdempotencyKey.objects.filter(user_id=7, key="k-3").count() == 1


def test_the_same_key_with_a_different_body_is_a_409_reuse():
    """The branch that stops a client reusing one key for two different actions —
    the failure mode that would make "accept" idempotently return the response to
    "decline"."""
    idempotent(user_id=7, key="k-4", endpoint=ENDPOINT, body=BODY)
    with pytest.raises(IdempotencyKeyReused) as exc:
        idempotent(user_id=7, key="k-4", endpoint=ENDPOINT,
                   body={"expected_version": 99})
    assert exc.value.code == "IDEMPOTENCY_KEY_REUSED"
    assert exc.value.http_status == 409


def test_the_body_hash_is_order_insensitive_but_value_sensitive():
    """A JSON body is a dict; two serialisations of the same dict must be the
    same request, or every client that reorders keys gets a spurious 409."""
    idempotent(user_id=7, key="k-5", endpoint=ENDPOINT, body={"a": 1, "b": 2})
    with pytest.raises(IdempotencyInProgress):
        idempotent(user_id=7, key="k-5", endpoint=ENDPOINT, body={"b": 2, "a": 1})
    with pytest.raises(IdempotencyKeyReused):
        idempotent(user_id=7, key="k-5", endpoint=ENDPOINT, body={"b": 2, "a": 3})


def test_two_users_may_use_the_same_key():
    """Uniqueness is on `(user_id, key)`, so one student's client-generated UUID
    cannot collide with another's and lock them out."""
    idempotent(user_id=7, key="shared", endpoint=ENDPOINT, body=BODY)
    row = idempotent(user_id=8, key="shared", endpoint=ENDPOINT, body=BODY)
    assert row.user_id == 8


def test_regression_the_same_key_on_a_different_endpoint_is_a_409():
    """**REGRESSION for REVIEW-S0 M3**, which QA's v1.0 suite characterised as
    deliberate contract behaviour and which was in fact a correctness bug.

    QA-S0 v1.0 asserted the old behaviour under the name
    `test_the_same_key_on_a_different_endpoint_is_still_the_same_key`, reasoning
    that API-CONTRACT §4.1 keys uniqueness on `(user_id, key)` and so the key,
    not the endpoint, is the unit of "the same request". **That reading was
    wrong and code-review's is right:** `endpoint` was stored and never
    compared, so a key claimed on `POST /offers` replayed its
    `201 {"state": "OFFERED"}` verbatim to `POST /transfers/9/accept`, and the
    client believed a transition had run that never did. From S4 every
    transition endpoint shares one key namespace per user, so the collision is
    reachable in normal use, not only under client error.

    QA records the miss rather than quietly inheriting the fix: a
    characterisation test is only as good as the contract reading behind it, and
    this one asserted a bug into the baseline.
    """
    row = idempotent(user_id=7, key="k-6", endpoint="POST /a", body=BODY)
    store_idempotent_response(row, 201, {"from": "a"})
    with pytest.raises(IdempotencyKeyReused) as exc:
        idempotent(user_id=7, key="k-6", endpoint="POST /b", body=BODY)
    assert exc.value.code == "IDEMPOTENCY_KEY_REUSED"
    assert exc.value.http_status == 409
    # The original endpoint still replays correctly.
    with pytest.raises(Replay) as replay:
        idempotent(user_id=7, key="k-6", endpoint="POST /a", body=BODY)
    assert replay.value.body == {"from": "a"}


def test_the_key_expires_after_the_contract_s_24_hours():
    """API-CONTRACT §4.1: "24-hour retention". Asserted against the contract's
    number, not against the setting, so lowering the setting fails here."""
    row = idempotent(user_id=7, key="k-7", endpoint=ENDPOINT, body=BODY)
    assert row.expires_at - timezone.now() > timedelta(hours=23)
    assert row.expires_at - timezone.now() <= timedelta(hours=24)
    assert settings.IDEMPOTENCY_RETENTION_HOURS == 24


# --------------------------------------------------------------------------
# the branch the contract does not cover
# --------------------------------------------------------------------------


def test_regression_an_anonymous_replay_now_returns_the_stored_response():
    """**REGRESSION for QA-S0 B3** — was a characterisation test of a contract
    gap, now the fixed behaviour.

    B3 measured that an anonymous replay claimed a *second* row instead of
    replaying the first, because `UNIQUE (user_id, key)` does not fire when
    `user_id` is NULL (ENGINE-DIVERGENCE §3.4, identical on both engines). The
    contract has four anonymous POSTs and two of them, `/grievances` and the
    public copyright-notice form, are the safety paths THREAT-MODEL §5.7 forbids
    requiring an account — so a double submission meant two tickets with two
    24-hour acknowledgement clocks running on one complaint.

    Migration 0004 adds a partial unique index on `key` alone WHERE
    `user_id IS NULL`. All four branches are asserted for an anonymous caller,
    because the fix is only worth having if the whole decision table works, not
    just the insert.
    """
    key = str(uuid.uuid4())
    first = idempotent(user_id=None, key=key, endpoint=ENDPOINT, body=BODY)
    assert IdempotencyKey.objects.filter(key=key).count() == 1

    # in flight
    with pytest.raises(IdempotencyInProgress) as exc:
        idempotent(user_id=None, key=key, endpoint=ENDPOINT, body=BODY)
    assert exc.value.retry_after == 2

    # stored, then replayed — the status, and per F10 never the body
    store_idempotent_response(first, 202, {"accepted": True})
    with pytest.raises(Replay) as replay:
        idempotent(user_id=None, key=key, endpoint=ENDPOINT, body=BODY)
    assert replay.value.status == 202, (
        "an anonymous retry must still be told the outcome and must still not "
        "re-execute; dropping the status would break the retry the mechanism "
        "exists to serve"
    )
    assert replay.value.body is None, (
        "QA-S0 F10: an anonymous replay must never carry a stored body"
    )

    # a different body on the same key is still a 409
    with pytest.raises(IdempotencyKeyReused):
        idempotent(user_id=None, key=key, endpoint=ENDPOINT, body={"x": 1})

    assert IdempotencyKey.objects.filter(key=key).count() == 1


def test_regression_anonymous_and_authenticated_keys_do_not_collide():
    """The partial index covers only `user_id IS NULL`, so the two namespaces
    are separate. Asserted in both orders, because a single global index on
    `key` would have made one student's client UUID lock out an anonymous
    grievance — turning a fix for a safety path into a denial of one.
    """
    shared = str(uuid.uuid4())
    anon = idempotent(user_id=None, key=shared, endpoint=ENDPOINT, body=BODY)
    user = idempotent(user_id=7, key=shared, endpoint=ENDPOINT, body=BODY)
    assert anon.pk != user.pk
    assert user.user_id == 7 and anon.user_id is None

    other = idempotent(user_id=8, key=shared, endpoint=ENDPOINT, body=BODY)
    assert other.user_id == 8
    assert IdempotencyKey.objects.filter(key=shared).count() == 3


def test_regression_an_anonymous_key_must_be_a_uuid():
    """**REGRESSION for QA-S0 F10, first half.**

    F10 measured that `idempotent()` accepted any truthy string as an anonymous
    key, which made API-CONTRACT §4.1's "a collision requires guessing a
    UUIDv4" argument an assumption rather than a fact: `Idempotency-Key: 1` was
    legal, and anonymous keys share one global namespace.

    The guard now rejects a non-UUID anonymous key with `VALIDATION_FAILED`
    (400). Parametrised over the shapes a careless or hostile client actually
    sends, and paired with the positive case so the narrowing cannot have closed
    the door on a conforming client.
    """
    for bad in ("1", "abc", "00000000-0000-0000-0000-00000000000", "null",
                "4", "-", "retry-1"):
        with pytest.raises(ValidationFailed) as exc:
            idempotent(user_id=None, key=bad, endpoint=ENDPOINT, body=BODY)
        assert exc.value.http_status == 400
        assert exc.value.code == "VALIDATION_FAILED"
    assert IdempotencyKey.objects.count() == 0

    good = idempotent(user_id=None, key=str(uuid.uuid4()), endpoint=ENDPOINT, body=BODY)
    assert good.pk is not None


def test_regression_no_anonymous_caller_can_receive_another_callers_response():
    """**REGRESSION for QA-S0 F10, second half — the disclosure itself.**

    F10 demonstrated a stranger receiving `{"grievance_ref": "GRV-000123"}`.
    This walks every path on which an anonymous second caller gets an answer
    about a key a first caller claimed, and asserts that none of them carries a
    body:

    * **Replay** — the fixed path: status only, body `None`.
    * **IdempotencyInProgress** — no body, and none to leak yet.
    * **IdempotencyKeyReused** — a different body hash or endpoint, so the two
      callers are not making the same request; no body either way.

    The surviving channel is the **status code**, which a colliding caller does
    learn. That is exactly what API-CONTRACT §4.1 now promises ("the consequence
    of a collision is a 409"), it requires guessing a UUID to reach, and it
    carries no content. QA records it as the accepted residual rather than
    leaving the word "never" unqualified.
    """
    key = str(uuid.uuid4())
    victim = idempotent(user_id=None, key=key, endpoint="POST /api/v1/grievances",
                        body={"body": "a complaint"})

    # in flight: no body exists yet, and none is offered
    with pytest.raises(IdempotencyInProgress) as in_flight:
        idempotent(user_id=None, key=key, endpoint="POST /api/v1/grievances",
                   body={"body": "a complaint"})
    assert not hasattr(in_flight.value, "body")

    store_idempotent_response(victim, 201, {"grievance_ref": "GRV-000123"})

    # same endpoint, same body — the exact path that leaked in F10
    with pytest.raises(Replay) as replay:
        idempotent(user_id=None, key=key, endpoint="POST /api/v1/grievances",
                   body={"body": "a complaint"})
    assert replay.value.status == 201
    assert replay.value.body is None
    assert "GRV-000123" not in str(replay.value.body)

    # a different body, and a different endpoint: both 409, neither carries data
    with pytest.raises(IdempotencyKeyReused) as reused:
        idempotent(user_id=None, key=key, endpoint="POST /api/v1/grievances",
                   body={"body": "a different complaint"})
    assert not hasattr(reused.value, "body")
    with pytest.raises(IdempotencyKeyReused):
        idempotent(user_id=None, key=key, endpoint="POST /api/v1/reports",
                   body={"body": "a complaint"})

    # and the stored body is still on the row, for the first caller's own retry
    victim.refresh_from_db()
    assert victim.response_body == {"grievance_ref": "GRV-000123"}


def test_the_f10_narrowing_did_not_break_authenticated_replay():
    """The mechanism the fix exists to protect.

    API-CONTRACT §4.1's core promise is that a flaky connection is safe: "the
    user taps Accept twice, one transfer is accepted, and both taps see the same
    answer." That promise is about an **authenticated** caller, and dropping the
    body for everyone would have traded a narrow disclosure for a broken retry
    on every transition endpoint from S4.

    Asserted directly: an authenticated replay still returns the stored body.
    """
    stored = {"id": 42, "state": "ACCEPTED", "version": 4}
    row = idempotent(user_id=7, key="k-auth", endpoint=ENDPOINT, body=BODY)
    store_idempotent_response(row, 200, stored)

    with pytest.raises(Replay) as replay:
        idempotent(user_id=7, key="k-auth", endpoint=ENDPOINT, body=BODY)
    assert replay.value.status == 200
    assert replay.value.body == stored


def test_an_authenticated_key_is_not_required_to_be_a_uuid():
    """The narrowing is scoped to the anonymous namespace, where the global
    index makes key choice everyone's business. An authenticated key lives in
    `(user_id, key)` and collides with nobody, so requiring a UUID there would
    be a breaking change to L2 clients for no property gained. Asserted so the
    scope is a tested fact rather than an implementation detail."""
    row = idempotent(user_id=7, key="tap-1", endpoint=ENDPOINT, body=BODY)
    assert row.key == "tap-1"


def test_regression_an_anonymous_key_must_be_a_uuid_version_4():
    """**REGRESSION for QA-S0 F11** — was a characterisation test, now the fix.

    F11 measured that `uuid.UUID(key)` accepts any version and variant, so
    API-CONTRACT §4.1's words — "client-generated **UUIDv4**" — were enforced
    only as "UUID-shaped". `00000000-0000-0000-0000-000000000001` was a legal
    anonymous key, and anonymous keys share one global namespace, so the
    contract's own argument ("a collision requires guessing one") rested on an
    unenforced format.

    The version is now checked. Both halves asserted, because a version check
    that also refused real UUIDv4s would have replaced a weak guard with an
    outage on `/grievances` — a path THREAT-MODEL §5.7 says may never be closed.
    """
    import uuid as uuid_module

    from apps.core.errors import ValidationFailed

    for low_entropy, why in [
        ("00000000-0000-0000-0000-000000000001", "a v1-shaped all-zero key"),
        ("00000000-0000-1000-8000-000000000000", "a valid UUID of version 1"),
        ("00000000-0000-3000-8000-000000000000", "version 3"),
        ("00000000-0000-5000-8000-000000000000", "version 5"),
    ]:
        parsed = uuid_module.UUID(low_entropy)
        assert parsed.version != 4, f"fixture error: {why} is a v4"
        with pytest.raises(ValidationFailed) as exc:
            idempotent(user_id=None, key=low_entropy, endpoint=ENDPOINT, body=BODY)
        assert exc.value.http_status == 400, why

    # And a real v4 still works, in every spelling a client may send it in.
    real = uuid_module.uuid4()
    assert real.version == 4
    row = idempotent(user_id=None, key=str(real), endpoint=ENDPOINT, body=BODY)
    assert row.pk is not None

    # An authenticated key is still unconstrained: it lives in (user_id, key)
    # and collides with nobody, so requiring a UUID there would break L2
    # clients for no property gained.
    assert idempotent(user_id=7, key="tap-2", endpoint=ENDPOINT, body=BODY).key == "tap-2"
def test_expected_version_rejects_a_stale_write(engine):
    pytest.skip(
        f"NOT VERIFIABLE IN S0 (engine={engine}): API-CONTRACT §4.2's "
        "`UPDATE ... WHERE version = :expected` needs a versioned row, and the "
        "first one is `transfers` in S4 (`listings` in S2). Nothing in S0 has a "
        "`version` column to conflict on."
    )


def test_expected_version_under_a_real_read_modify_write_race():
    pytest.skip(unavailable(
        slice_="S4", needs_tables=("transfers",),
        subject="API-CONTRACT 4.2's optimistic lock in its failure mode -- "
                "`UPDATE ... WHERE version = :expected` returning zero rows "
                "because another request won",
        note="PostgreSQL's READ COMMITTED permits this race, so the engine has "
             "stopped being the limit; there is no versioned row to race on.",
    ))