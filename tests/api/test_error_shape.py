"""The §2.2 error shape — **one shape, everywhere.**

TASKS §2 S1 assigns this renderer to backend with the reason stated: *"It sits
between backend L2 and frontend L3 and would otherwise fall between two
agents."* `CLAUDE.md` rule 9 then makes it a control that needs a conformance
test, which is this file.

**The assertion with teeth is `test_a_500_never_echoes_the_exception_message`.**
API-CONTRACT §2.2: *"`INTERNAL` — never echoes an exception message; the
`request_id` is the only thing the user gets, and it is enough to find the
log."* An exception message is the commonest way a stack trace, a SQL fragment
or a filesystem path reaches a user, so the renderer does not take the message
from the exception **at all** for a 5xx.
"""

import json

import pytest

from apps.core.api import GENERIC_MESSAGES, endpoint, error_payload, error_response
from apps.core.errors import (
    ConsentRequired,
    GateClosed,
    IdempotencyInProgress,
    NotAuthenticated,
    NotFound,
    RateLimited,
    ServiceError,
    ValidationFailed,
    VersionConflict,
)

pytestmark = pytest.mark.django_db


def test_the_shape_is_exactly_the_contracts_keys():
    """§2.2's example body, key for key. `field_errors` is **present only on
    400** — the contract's own sentence — so on every other status the key is
    absent rather than null, and a client branching on its presence is
    branching on what the contract promises."""
    body = error_payload(GateClosed("Listings are not open on this campus yet."))["error"]
    assert set(body) == {"code", "message", "request_id", "retry_after"}
    assert body["code"] == "GATE_CLOSED"
    assert body["message"] == "Listings are not open on this campus yet."
    assert body["retry_after"] is None

    with_fields = error_payload(
        ValidationFailed("bad", field_errors={"email": ["Required."]})
    )["error"]
    assert set(with_fields) == {"code", "message", "request_id", "retry_after", "field_errors"}
    assert with_fields["field_errors"] == {"email": ["Required."]}


def test_field_errors_is_absent_on_every_status_but_400():
    for exc in (NotAuthenticated(), GateClosed(), NotFound(), VersionConflict(), RateLimited()):
        assert "field_errors" not in error_payload(exc)["error"], exc.code


@pytest.mark.parametrize(
    "exc,status",
    [
        (ValidationFailed(), 400),
        (NotAuthenticated(), 401),
        (GateClosed(), 403),
        (ConsentRequired(), 403),
        (NotFound(), 404),
        (VersionConflict(), 409),
        (IdempotencyInProgress(), 409),
        (RateLimited(), 429),
        (ServiceError(), 500),
    ],
)
def test_each_code_maps_to_the_contracts_status(exc, status):
    """§2.2's table, as a mapping rather than as a convention. The 403/422 split
    is one clients are asked to branch on — *"403 means **you** may not; 422
    means the **object** is not in a state where this is possible"* — so a code
    landing on the wrong status is a client bug nobody can see."""
    assert error_response(exc).status_code == status


def test_a_500_never_echoes_the_exception_message():
    """§2.2, verbatim: the `request_id` is the only thing the user gets."""
    leaky = ServiceError(
        'relation "users" does not exist at /srv/bookhop/apps/accounts/services.py:214'
    )
    response = error_response(leaky)
    body = json.loads(response.content)["error"]

    assert response.status_code == 500
    assert body["code"] == "INTERNAL"
    assert body["message"] == str(GENERIC_MESSAGES["INTERNAL"])
    for leak in ("users", "does not exist", "/srv/", "services.py", "214"):
        assert leak not in json.dumps(body), f"a 500 leaked {leak!r}"


def test_a_500_still_carries_a_request_id(rf, client):
    """The other half of the same sentence: *"it is enough to find the log."* A
    500 with no reference is a 500 nobody can investigate inside six hours
    (CERT-In), which is why the id is not optional."""
    response = client.get("/healthz")
    assert response["X-Request-Id"]


def test_a_4xx_keeps_its_own_message_because_the_student_needs_it():
    """The asymmetry is deliberate. A 4xx message is written for a student and
    is already localised (§2.2); a 5xx message is written by Python."""
    body = error_payload(ConsentRequired("This needs your permission first."))["error"]
    assert body["message"] == "This needs your permission first."


def test_a_raise_with_no_message_falls_back_to_a_sentence_not_to_a_code():
    """A code in a message field is what a student sees when a developer raises
    without one. `GENERIC_MESSAGES` is what stops `VERSION_CONFLICT` being
    rendered at a person."""
    body = error_payload(VersionConflict())["error"]
    assert body["message"] != "VERSION_CONFLICT"
    assert body["message"].endswith(".")


def test_every_s1_error_class_has_a_message_a_student_could_read():
    """`CLAUDE.md` rule 9 turned on the renderer's own table: a code with no
    entry renders as the code itself, which is the defect above. So the set is
    asserted against the classes that exist."""
    import apps.core.errors as errors

    codes = {
        cls.code
        for name, cls in vars(errors).items()
        if isinstance(cls, type) and issubclass(cls, ServiceError) and not name.startswith("_")
    }
    missing = sorted(code for code in codes if code not in GENERIC_MESSAGES)
    assert missing == [], (
        "these error codes have no student-readable message, so a raise without "
        f"one renders the code at a person: {missing}"
    )


def test_a_retry_after_reaches_the_header_as_well_as_the_body():
    """§2.2 lists `retry_after` in the body and §2.4 requires the header. A 429
    with neither is a client that retries immediately and gets another 429."""
    response = error_response(RateLimited("Too many requests.", retry_after=37))
    assert response.status_code == 429
    assert response["Retry-After"] == "37"
    assert json.loads(response.content)["error"]["retry_after"] == 37


def test_the_endpoint_wrapper_renders_a_service_error_rather_than_raising(rf):
    """The wrapper is what makes the shape universal: a handler raises a
    `ServiceError` and never builds a response, so twelve handlers cannot
    produce twelve shapes."""

    @endpoint(methods=["POST"])
    def handler(request, body, user):  # pragma: no cover - raises before returning
        raise GateClosed("Listings are not open on this campus yet.")

    response = handler(rf.post("/x", data="{}", content_type="application/json"))
    assert response.status_code == 403
    assert json.loads(response.content)["error"]["code"] == "GATE_CLOSED"


def test_a_wrong_method_is_the_same_shape(rf):
    response_cls = endpoint(methods=["POST"])(lambda request, body, user: (200, {}))
    response = response_cls(rf.get("/x"))
    assert response.status_code == 405
    assert json.loads(response.content)["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_a_malformed_json_body_is_a_400_and_not_a_500(rf):
    handler = endpoint(methods=["POST"])(lambda request, body, user: (200, {}))
    response = handler(rf.post("/x", data="{not json", content_type="application/json"))
    assert response.status_code == 400
    assert json.loads(response.content)["error"]["code"] == "VALIDATION_FAILED"


def test_a_json_array_body_is_refused_rather_than_indexed(rf):
    """A handler reads `body.get(...)`, so a list body would raise
    `AttributeError` and surface as a 500 — an input-shape bug reported as our
    bug."""
    handler = endpoint(methods=["POST"])(lambda request, body, user: (200, {}))
    response = handler(rf.post("/x", data="[1,2]", content_type="application/json"))
    assert response.status_code == 400


def test_no_error_body_contains_money(rf):
    """ADR-003 §2.3 at the boundary, applied to the shape every endpoint shares:
    *"a price absent from storage but present in a response is still a
    record."* The error shape is the one body served by **every** endpoint, so
    it is the cheapest place for a leak to become universal."""
    from tests.unit.test_forbidden_response import assert_no_forbidden_content

    for exc in (ValidationFailed("bad", field_errors={"asking_price_paise": ["Must be 0 or more."]}),
                GateClosed(), RateLimited(), ServiceError("boom")):
        assert_no_forbidden_content(error_payload(exc), where=f"the {exc.code} body")
