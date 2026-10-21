"""Idempotency-Key handling — API-CONTRACT §4.1.

The service-layer mechanism, tested directly. The HTTP wrapper arrives with the
first L2 endpoint (S1), and `tests/api/test_idempotency.py` grows an
over-the-wire case then; the semantics asserted here are the ones that endpoint
will inherit.
"""

import pytest

from apps.core.errors import IdempotencyInProgress, IdempotencyKeyRequired, IdempotencyKeyReused
from apps.core.services import Replay, idempotent, store_idempotent_response

pytestmark = pytest.mark.django_db

BODY = {"listing_id": 7, "message": "hello"}


def test_missing_key_is_rejected():
    with pytest.raises(IdempotencyKeyRequired):
        idempotent(1, None, "POST /api/v1/offers", BODY)


def test_first_call_claims_the_key():
    row = idempotent(1, "k-1", "POST /api/v1/offers", BODY)
    assert row.response_status is None


def test_replay_before_a_response_is_stored_is_in_progress():
    idempotent(1, "k-1", "POST /api/v1/offers", BODY)
    with pytest.raises(IdempotencyInProgress) as exc:
        idempotent(1, "k-1", "POST /api/v1/offers", BODY)
    assert exc.value.retry_after == 2


def test_replay_after_a_response_returns_the_stored_response_verbatim():
    row = idempotent(1, "k-1", "POST /api/v1/offers", BODY)
    store_idempotent_response(row, 201, {"id": 42, "state": "OFFERED"})
    with pytest.raises(Replay) as exc:
        idempotent(1, "k-1", "POST /api/v1/offers", BODY)
    assert exc.value.status == 201
    assert exc.value.body == {"id": 42, "state": "OFFERED"}


def test_same_key_different_body_is_a_conflict():
    idempotent(1, "k-1", "POST /api/v1/offers", BODY)
    with pytest.raises(IdempotencyKeyReused):
        idempotent(1, "k-1", "POST /api/v1/offers", {"listing_id": 8})


def test_the_request_hash_ignores_key_order_but_not_values():
    row = idempotent(1, "k-1", "POST /api/v1/offers", {"a": 1, "b": 2})
    store_idempotent_response(row, 200, {})
    with pytest.raises(Replay):
        idempotent(1, "k-1", "POST /api/v1/offers", {"b": 2, "a": 1})
    with pytest.raises(IdempotencyKeyReused):
        idempotent(1, "k-1", "POST /api/v1/offers", {"a": 1, "b": 3})


def test_keys_are_scoped_per_user():
    idempotent(1, "k-1", "POST /api/v1/offers", BODY)
    other = idempotent(2, "k-1", "POST /api/v1/offers", BODY)  # must not collide
    assert other.user_id == 2


# --- M3: the key is scoped to its endpoint --------------------------------


def test_the_same_key_on_a_different_endpoint_is_a_conflict():
    """M3. `endpoint` was stored and never compared, so a key claimed on
    `POST /api/v1/offers` replayed its `201 {"state": "OFFERED"}` verbatim to
    `POST /api/v1/transfers/9/accept` — no transition performed, no error, and
    the client believing it had happened. From S4 every transition endpoint
    shares one key namespace per user (`UNIQUE (user_id, key)`) and L3 forms
    generate a key per render, so a refresh, a back-button or a retry against
    the wrong URL hit it."""
    row = idempotent(1, "k-1", "POST /api/v1/offers", BODY)
    store_idempotent_response(row, 201, {"id": 42, "state": "OFFERED"})

    with pytest.raises(IdempotencyKeyReused):
        idempotent(1, "k-1", "POST /api/v1/transfers/9/accept", BODY)


def test_an_in_flight_key_does_not_leak_to_another_endpoint():
    idempotent(1, "k-1", "POST /api/v1/offers", BODY)
    with pytest.raises(IdempotencyKeyReused):
        idempotent(1, "k-1", "POST /api/v1/transfers/9/accept", BODY)


def test_the_same_key_on_the_same_endpoint_still_replays():
    row = idempotent(1, "k-1", "POST /api/v1/offers", BODY)
    store_idempotent_response(row, 201, {"id": 42})
    with pytest.raises(Replay):
        idempotent(1, "k-1", "POST /api/v1/offers", BODY)


# --- QA-S0 B3: anonymous callers ------------------------------------------


ANON_KEY = "11111111-2222-4333-8444-555555555555"
ANON_KEY_2 = "99999999-2222-4333-8444-555555555555"


# --- QA-S0 F10: the key format, and what a replay may return --------------


@pytest.mark.parametrize("key", ["1", "abc", "", " ", "00000000-0000-0000-0000", "x" * 36])
def test_an_anonymous_key_that_is_not_a_uuid_is_rejected(key):
    """QA-S0 F10, the first half.

    `idempotent()` accepted any truthy string, so `Idempotency-Key: 1` was a
    legal anonymous key — and anonymous keys share one global namespace, so a
    short key is another caller's key. API-CONTRACT §4.1's argument that "a
    collision requires guessing a UUIDv4" was false on this half; now it is
    true.
    """
    from apps.core.errors import ValidationFailed

    with pytest.raises((ValidationFailed, IdempotencyKeyRequired)):
        idempotent(None, key, "POST /api/v1/grievances", BODY)


def test_an_authenticated_key_need_not_be_a_uuid():
    """The format rule is scoped to the global namespace. An authenticated
    key is already scoped by `user_id`, so a short key collides only with the
    same user's own keys, which is their own problem and not a disclosure."""
    row = idempotent(1, "k-1", "POST /api/v1/offers", BODY)
    assert row.key == "k-1"


def test_an_anonymous_replay_never_returns_the_stored_body():
    """QA-S0 F10, the second half — **a demonstrated disclosure, not a 409.**

    With the same endpoint and the same body hash, the second anonymous caller
    received the first's stored `response_body` verbatim: QA measured
    `{"grievance_ref": "GRV-000123"}` reaching a stranger, on the endpoint a
    distressed non-user reaches us through.

    The retry still gets the right status and is still not re-executed; it just
    does not get a body it has no claim on.
    """
    row = idempotent(None, ANON_KEY, "POST /api/v1/grievances", BODY)
    store_idempotent_response(row, 202, {"grievance_ref": "GRV-000123"})

    with pytest.raises(Replay) as exc:
        idempotent(None, ANON_KEY, "POST /api/v1/grievances", BODY)
    assert exc.value.status == 202
    assert exc.value.body is None, "an anonymous replay must not hand over another caller's body"


def test_an_authenticated_replay_still_returns_its_own_body():
    """The narrowing must not break the mechanism it protects."""
    row = idempotent(1, "k-1", "POST /api/v1/offers", BODY)
    store_idempotent_response(row, 201, {"id": 42})
    with pytest.raises(Replay) as exc:
        idempotent(1, "k-1", "POST /api/v1/offers", BODY)
    assert exc.value.body == {"id": 42}


def test_an_anonymous_replay_replays_instead_of_claiming_a_second_row():
    """QA-S0 B3. `UNIQUE (user_id, key)` does not fire when `user_id` is NULL —
    NULLs are distinct on both engines — so an anonymous replay used to claim a
    **second** row rather than replay the first, and API-CONTRACT has anonymous
    POSTs (`/auth/magic-link`, `/auth/consume`, `/grievances`, the public
    copyright-notice form).

    The semantics chosen, deliberately and written down in
    `services.idempotent()`: anonymous keys share one global namespace, enforced
    by a partial unique index on `key` WHERE `user_id IS NULL` (migration 0004).
    Sound because the key is a client-generated UUIDv4; better than a sentinel
    `user_id = 0`, which breaks the FK S1 adds to `users`; and better than
    keying on IP, which breaks the retry it exists to serve the moment a phone
    changes network."""
    from apps.core.models import IdempotencyKey

    row = idempotent(None, ANON_KEY, "POST /api/v1/grievances", BODY)
    store_idempotent_response(row, 202, {"ticket_ref": "GRV-1"})

    with pytest.raises(Replay) as exc:
        idempotent(None, ANON_KEY, "POST /api/v1/grievances", BODY)
    # The status replays; the body does not (F10, asserted above).
    assert exc.value.status == 202
    assert IdempotencyKey.objects.filter(user_id=None, key=ANON_KEY).count() == 1


def test_an_anonymous_key_is_endpoint_scoped_too():
    idempotent(None, ANON_KEY, "POST /api/v1/grievances", BODY)
    with pytest.raises(IdempotencyKeyReused):
        idempotent(None, ANON_KEY, "POST /api/v1/legal/copyright-notice", BODY)


def test_two_different_anonymous_keys_do_not_collide():
    idempotent(None, ANON_KEY, "POST /api/v1/grievances", BODY)
    second = idempotent(None, ANON_KEY_2, "POST /api/v1/grievances", BODY)
    assert second.user_id is None


def test_an_anonymous_key_and_an_authenticated_key_are_separate_namespaces():
    idempotent(None, ANON_KEY, "POST /api/v1/grievances", BODY)
    row = idempotent(1, "k-1", "POST /api/v1/grievances", BODY)
    assert row.user_id == 1
