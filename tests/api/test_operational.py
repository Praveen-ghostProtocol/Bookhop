"""Operational endpoints and the request-id contract — API-CONTRACT §2.1, §5.8."""

import json

import pytest

pytestmark = pytest.mark.django_db


def test_healthz_is_unauthenticated_and_leaks_nothing(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.content.decode()
    assert body == "ok"  # no version, no detail


def test_readyz_returns_a_bare_readiness_signal(client):
    """S12. The body used to carry `migrations_applied` and `jobs_overdue`,
    telling an anonymous caller whether a deploy was half-applied and how deep
    the queue was. API-CONTRACT §5.8 reserves counters for the token-protected
    `/metricsz`; ASVS V13 wants the exposed surface minimal. The detail is
    logged instead."""
    response = client.get("/readyz")
    payload = json.loads(response.content)
    assert response.status_code == 200
    assert payload == {"ready": True}


def test_readyz_is_not_ready_when_jobs_are_overdue(client, caplog):
    from datetime import timedelta

    from django.utils import timezone

    from apps.core.models import Job

    Job.objects.create(kind="core.noop", payload={}, run_after=timezone.now() - timedelta(hours=1))
    with caplog.at_level("WARNING", logger="apps.core.views"):
        response = client.get("/readyz")
    assert response.status_code == 503
    assert json.loads(response.content) == {"ready": False}
    # the detail an operator needs is in the log, not in the response
    assert any(r.message == "readyz.not_ready" for r in caplog.records)
    assert any(getattr(r, "checks", {}).get("job_runner") is False for r in caplog.records)


def test_request_id_is_generated_and_echoed(client):
    response = client.get("/healthz")
    assert response["X-Request-Id"]


def test_a_client_supplied_request_id_is_echoed(client):
    response = client.get("/healthz", headers={"X-Request-Id": "abc-123"})
    assert response["X-Request-Id"] == "abc-123"


@pytest.mark.parametrize(
    "hostile",
    [
        "abc\ninjected: yes",   # mid-string newline — the only case tested before
        "abc\n",                # S1: `match` + `$` accepted this; `fullmatch` does not
        "abc\r",
        "abc\r\n",
        "abc def",
        "a" * 65,
        "abc\x00",
    ],
)
def test_a_hostile_request_id_is_replaced_not_echoed(client, hostile):
    """A client-supplied id lands in logs and in `audit_log.request_id`.

    S1: the trailing newline was the one position that got through, because
    `re.match` with `$` matches before a trailing `\\n`. The consequence was
    narrower than the comment claimed — `json.dumps` escapes the log line and a
    conformant server rejects LF in a header — but the echo raises Django's
    BadHeaderError, i.e. a 500, and the value reached the audit trail.
    """
    response = client.get("/healthz", headers={"X-Request-Id": hostile})
    echoed = response["X-Request-Id"]
    assert echoed != hostile
    assert "\n" not in echoed and "\r" not in echoed
    assert len(echoed) <= 64


def test_the_log_class_cannot_be_overwritten_by_extra():
    """S2. `log_class` is what makes the 365-day retention floor mechanical
    rather than a judgement call, and `event` is what a CERT-In investigation
    reads. `_RESERVED` was derived only from a live LogRecord, so neither was
    protected: `extra={"log_class": "app", "event": "nothing happened"}` on a
    `bookhop.security` record relabelled the line and replaced its message."""
    import json as _json
    import logging

    from apps.core.logging import JsonFormatter

    record = logging.LogRecord(
        "bookhop.security", logging.INFO, __file__, 1, "gate.refused", (), None
    )
    record.log_class = "app"
    record.event = "nothing happened"
    record.campus = "closed"

    payload = _json.loads(JsonFormatter().format(record))
    assert payload["log_class"] == "security"
    assert payload["event"] == "gate.refused"
    assert payload["campus"] == "closed"  # genuine extras still ride along
    assert payload["ts"].endswith("Z")


def test_request_id_reaches_the_audit_row(client, city):
    """Not via HTTP yet -- no mutating endpoint exists in S0 -- so assert the
    contextvar plumbing directly."""
    from apps.core.request_context import reset_request, set_request
    from apps.core.services import record_audit

    token = set_request(request_id="rid-1", ip="203.0.113.7", user_agent="probe/1.0")
    try:
        row = record_audit(None, "test.one", city)
    finally:
        reset_request(token)
    assert row.request_id == "rid-1"
    assert row.ip == "203.0.113.7"
    assert row.user_agent == "probe/1.0"
