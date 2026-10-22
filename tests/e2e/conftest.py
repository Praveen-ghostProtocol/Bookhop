"""Fixtures for test-qa's own end-to-end tests.

Deliberately named apart from the fixtures in `tests/conftest.py` and built from
ADR-002 §4.1(b)'s evidence checklist directly, so that a change to the backend
agent's fixtures cannot quietly change what these tests assert.
"""

import pytest


@pytest.fixture
def qa_entity(db):
    """An incorporated legal entity: every Gate B item in ADR-002 §4.1(b) that
    lives on `legal_entities` is present and non-empty."""
    from apps.core.models import LegalEntity

    return LegalEntity.objects.create(
        legal_name="BookHop Private Limited",
        cin="U72900TN2026PTC000001",
        incorporation_date="2026-11-01",
        inc20a_filed_at="2026-11-05",
        grievance_officer_name="Grievance Officer",
        grievance_officer_email="grievance@bookhop.test",
        grievance_officer_phone="+919000000001",
    )


@pytest.fixture
def qa_city(db):
    from apps.core.models import City

    return City.objects.create(name="Chennai", state="Tamil Nadu")


@pytest.fixture
def qa_campus(db, qa_city, qa_entity):
    """A campus in the only lawful pre-Gate-C state: `discovery_enabled_at` NULL.

    ADR-002 §4.1(a): "Default for a new campus row is NULL. A campus is closed
    unless someone deliberately opened it."
    """
    from apps.core.models import Campus

    return Campus.objects.create(
        city=qa_city,
        name="QA Campus",
        slug="qa-campus",
        legal_entity=qa_entity,
        email_domains=["qa.example.test"],
    )


@pytest.fixture
def qa_evidence():
    """The six `evidence` keys ADR-002 §4.1(b) requires, all non-empty."""
    return {
        "counsel_engagement_ref": "ENG-C1-C3-2026-11",
        "takedown_sop_ref": "SOP-TAKEDOWN-v1",
        "oncall_rota_ref": "ROTA-2026-11",
        "breach_rehearsal_at": "2026-11-12",
        "campus_mou_ref": "MOU-QA-CAMPUS-2026",
        "notice_version_ids": [1, 2, 3],
    }


@pytest.fixture
def qa_authorisation(db, qa_campus, qa_entity, qa_evidence):
    """A complete Gate C authorisation for `qa_campus`, with a named human."""
    from apps.core.models import GateAuthorisation

    return GateAuthorisation.objects.create(
        gate="C",
        scope_type="CAMPUS",
        scope_id=qa_campus.id,
        legal_entity=qa_entity,
        evidence=qa_evidence,
        authorised_by_human="A Named Human",
    )


@pytest.fixture
def client_as(db):
    """A **fresh** Django test client signed in as `user`.

    One client reused across users measures nonsense: `client.session` mints a
    new key on each save while the cookie still points at the first, so every
    actor after the first is anonymous and every endpoint answers 401. QA paid
    for that once already and the fixture returns a new client each call so
    the actor is the only variable.
    """
    from django.test import Client

    from apps.accounts.sessions import SESSION_USER_KEY

    def _sign_in(user):
        client = Client()
        session = client.session
        session[SESSION_USER_KEY] = user.id
        session.save()
        return client

    return _sign_in
