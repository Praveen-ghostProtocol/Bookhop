"""The statutory grievance contact — E-Com r.4(2)/r.4(4), IT Rules r.3(2)(a).

A signature frontend named for the publication page. **It composes rather than
stores**, and that is the same ruling as the accepted-domain list and the
`GRIEVANCE_PROCEDURE` notice: versioned prose lives in `notice_versions`, and
the officer's details are read from `legal_entities` **at render time**.

The reason is not tidiness. Baking the officer's name and email into an
immutable versioned notice would create a second copy of a fact that changes
without the notice changing — and **a stale grievance-officer contact is a
direct regulatory failure**, not a cosmetic one.
"""

import pytest

from apps.core.services import GRIEVANCE_OFFICER_DESIGNATION, grievance_contact

pytestmark = pytest.mark.django_db


def test_it_returns_the_five_published_fields(legal_entity):
    contact = grievance_contact()
    assert set(contact) == {"name", "designation", "email", "phone", "address"}
    assert contact["name"] == "A Human"
    assert contact["email"] == "grievance@example.test"
    assert contact["designation"] == GRIEVANCE_OFFICER_DESIGNATION


def test_it_degrades_to_none_before_incorporation(db):
    """Every column on `legal_entities` is nullable because the row exists
    before the company does, and the row itself may not exist yet. The page is
    linked from every footer, so it must render correct and empty rather than
    break — *"it must survive an outage of the thing it describes."*"""
    assert grievance_contact() is None


def test_an_incorporated_entity_with_no_officer_yet_returns_nulls_not_an_error(db):
    """Gate B4 appoints the officer. Between B1 and B4 the row exists and the
    fields do not, and frontend guards each field individually."""
    from apps.core.models import LegalEntity

    LegalEntity.objects.create(legal_name="BookHop Pvt Ltd")
    contact = grievance_contact()
    assert contact is not None
    assert contact["name"] is None and contact["email"] is None
    assert contact["designation"] == GRIEVANCE_OFFICER_DESIGNATION


def test_the_contact_is_never_baked_into_a_notice_body(legal_entity, db):
    """The composition rule, as a test. A `GRIEVANCE_PROCEDURE` notice that
    contained the officer's email would be a second copy of a fact that
    changes without the notice changing — and `notice_versions` is immutable
    by trigger, so the stale copy could never be corrected in place."""
    from apps.accounts.models import NoticeVersion

    body = "# Grievance procedure\n\nHow to complain, and the clocks that apply."
    NoticeVersion.objects.create(
        kind="GRIEVANCE_PROCEDURE", version="2026-11-01.1", locale="en",
        body_md=body, sha256="2" * 64,
    )
    for row in NoticeVersion.objects.filter(kind="GRIEVANCE_PROCEDURE"):
        assert "grievance@example.test" not in row.body_md
        assert "A Human" not in row.body_md


def test_the_address_published_here_is_the_only_one_in_the_database(legal_entity):
    """`registered_address` is the **only** address column permitted anywhere
    (ADR-003 §2.3), and this is the one place it is published — which the rules
    require. Asserted against `apps/core/p14.py` rather than retyped, so the
    exception stays scoped to one column rather than to the table."""
    from apps.core.p14 import CONDITIONAL_COLUMNS

    assert CONDITIONAL_COLUMNS["address"] == ("legal_entities", "registered_address")
    assert CONDITIONAL_COLUMNS["street"] is None
    assert CONDITIONAL_COLUMNS["pincode"] is None
