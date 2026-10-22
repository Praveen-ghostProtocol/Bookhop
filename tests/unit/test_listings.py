"""`apps.listings` — the sell flow and the demand side. JOURNEYS J2 and J4.

The state machine is DATA-MODEL §6.1 and the preconditions are API-CONTRACT
§2.5 Stack M. What this file is mostly about is the half of each rule that a
CHECK constraint cannot express: an **affirmative** no-damage answer, a
version-exact seller-terms acceptance, and the two S4/S3 couplings that are
recorded as pending rather than left to be rediscovered.
"""

import pytest

from apps.core.errors import (
    ConsentRequired,
    NotPermitted,
    SellerTermsNotAccepted,
    TransitionNotAllowed,
    ValidationFailed,
    VersionConflict,
)
from apps.listings import services
from apps.listings.models import Listing

pytestmark = pytest.mark.django_db


def _create(seller, book, **overrides):
    kwargs = dict(
        book=book, asking_price_paise=30000, condition="GOOD",
        annotation_level="NONE", damage_flags=[], no_damage=True,
        language="en", category="PRESCRIBED_TEXTBOOK",
    )
    kwargs.update(overrides)
    return services.create_listing(seller, **kwargs)


# --- Stack M, and the two preconditions this slice is the first to need ---


def test_a_listing_needs_the_listing_publication_consent(student, book, seller_terms_notice):
    """JOURNEYS J1 step 5 names `listing_publication` as the second required
    purpose, and S1 deliberately left it to the slice with something to
    publish. A student who granted only `account` is refused here."""
    from apps.accounts.services import accept_seller_terms

    student.status = "ACTIVE"
    student.save(update_fields=["status"])
    accept_seller_terms(student, seller_terms_notice, None)
    with pytest.raises(ConsentRequired) as caught:
        _create(student, book)
    assert caught.value.context["purpose_key"] == "listing_publication"


def test_a_listing_needs_the_current_seller_terms(student, book, privacy_notice,
                                                  seller_terms_notice):
    """r.6(4)(a)'s prior written contract. JOURNEYS J2 step 6 renders this as
    the terms screen again, never as an error page."""
    from apps.accounts.services import grant_consent

    student.status = "ACTIVE"
    student.save(update_fields=["status"])
    grant_consent(student, "listing_publication", privacy_notice, "SIGNUP_FORM", None, "pytest")
    with pytest.raises(SellerTermsNotAccepted):
        _create(student, book)


def test_accepting_v1_does_not_cover_v2(seller, book, seller_terms_notice):
    """**Version-exact, and this is the test that makes "versioned" mean
    something.** A notice that can be changed under a student who already
    agreed is not a prior written contract — so publishing a new version
    re-asks, and the acceptance row names which one was shown.
    """
    from apps.accounts.models import NoticeVersion

    assert _create(seller, book)  # precondition: v1 is accepted
    NoticeVersion.objects.create(
        kind="SELLER_TERMS", version="2026-12-01.1", locale="en",
        body_md="# Seller terms v2", sha256="3" * 64,
    )
    with pytest.raises(SellerTermsNotAccepted):
        _create(seller, book)


def test_accepting_the_terms_twice_records_one_acceptance(seller, seller_terms_notice):
    """Idempotent by the unique key. A student who taps "I agree" twice has
    one acceptance; the second is not a second piece of evidence about the
    same consent."""
    from apps.accounts.models import SellerTermsAcceptance
    from apps.accounts.services import accept_seller_terms

    accept_seller_terms(seller, seller_terms_notice, None)
    assert SellerTermsAcceptance.objects.filter(
        user_pseudonym=seller.person_pseudonym
    ).count() == 1


# --- PRD AC-S3.2: damage must be affirmatively confirmed ------------------


def test_an_empty_damage_list_without_the_affirmative_answer_is_refused(seller, book):
    """**AC-S3.2, and the reason it is a refusal and not a default.**

    JOURNEYS J2 step 4: *"an empty damage list that submits is an implied
    no-damage claim the seller never made."* The form's "none of these" tick
    is what distinguishes *asked and answered no* from *nobody asked*, and
    J6's disputed-condition journey turns on exactly that difference.
    """
    with pytest.raises(ValidationFailed) as caught:
        _create(seller, book, damage_flags=[], no_damage=False)
    assert "damage_flags" in caught.value.context["field_errors"]


def test_the_affirmative_answer_stores_an_empty_list_not_a_sentinel(seller, book):
    """No `NONE_OF_THESE` row in `damage_flags`: a value inside an enum of
    damage kinds that means "no damage" is a value that means "not a value"."""
    listing = _create(seller, book, damage_flags=[], no_damage=True)
    assert listing.damage_flags == []


def test_the_sellers_damage_answer_is_in_the_audit_row(seller, book):
    """The fact that they were asked, recorded where it outlives the listing.

    There is no `damage_confirmed_at` column — a fourth divergence from
    DATA-MODEL §3 for a fact already recorded would be a column that can
    disagree — so this asserts the record actually exists where the model
    comment says it does.
    """
    from apps.core.models import AuditLog

    listing = _create(seller, book, damage_flags=["WATER"], no_damage=False)
    row = AuditLog.objects.filter(
        action="listings.created", object_id=str(listing.id)
    ).first()
    assert row is not None
    assert row.after_hash, "the creation audit row carries no payload hash"


@pytest.mark.parametrize("bad", ["SOAKED", "none", "", "WATER_DAMAGE"])
def test_an_unknown_damage_kind_is_refused_with_the_permitted_values(seller, book, bad):
    """`CLAUDE.md` rule 12: a CHECK guarantees the stored state and does not
    detect a bad input — what the caller gets when it fires is a 500 with a
    CheckViolation, not a 400 naming the six values it could have sent."""
    with pytest.raises(ValidationFailed) as caught:
        _create(seller, book, damage_flags=[bad], no_damage=False)
    assert "WATER" in str(caught.value.context["detail"])


def test_a_repeated_damage_flag_is_refused(seller, book):
    with pytest.raises(ValidationFailed):
        _create(seller, book, damage_flags=["WATER", "WATER"], no_damage=False)


# --- the state machine ----------------------------------------------------


def test_a_new_listing_is_a_draft(seller, book):
    """JOURNEYS J2 step 7, and EC-13's whole affordance: `create_listing` and
    `publish_listing` being two calls is what makes a failed photo upload a
    resumable draft rather than a lost form."""
    listing = _create(seller, book)
    assert listing.status == "DRAFT"
    assert listing.published_at is None
    assert listing.price_fixed_at is not None


def test_publishing_at_pilot_goes_to_review_whatever_the_flag_says(seller, book, settings):
    """PRD AC-S4.3 and AC-S4.2–3: at pilot every listing is reviewed, and the
    copy is the same whether or not `suspect_reproduction_flag` is set — *no
    accusation, no implication of guilt.*"""
    settings.LISTING_REVIEW_ALL = True
    listing = _create(seller, book)
    listing = services.publish_listing(seller, listing, listing.version)
    assert listing.status == "PENDING_REVIEW"

    flagged = _create(seller, book, suspect_reproduction_flag=True)
    flagged = services.publish_listing(seller, flagged, flagged.version)
    assert flagged.status == "PENDING_REVIEW", (
        "a flagged listing must reach the same state by the same route; a "
        "different state is a different screen and therefore an accusation"
    )


def test_a_photocopy_flagged_listing_goes_to_review_even_with_the_flag_off(
    seller, book, staff, settings
):
    """S2's done-when: *"a photocopy-flagged listing goes to review"*.

    Asserted with `LISTING_REVIEW_ALL` **off**, because with it on every
    listing goes to review and the assertion would pass for a reason that has
    nothing to do with the flag — `CLAUDE.md` rule 10's vacuous-pass shape.
    """
    from apps.catalog.services import verify_book

    settings.LISTING_REVIEW_ALL = False
    verify_book(staff, book)
    book.refresh_from_db()

    clean = _create(seller, book)
    clean = services.publish_listing(seller, clean, clean.version)
    assert clean.status == "LIVE", (
        "precondition: with the flag off and a verified book, a clean listing "
        "goes straight to LIVE — otherwise the next assertion proves nothing"
    )

    suspect = _create(seller, book, suspect_reproduction_flag=True)
    suspect = services.publish_listing(seller, suspect, suspect.version)
    assert suspect.status == "PENDING_REVIEW"


def test_a_book_with_no_isbn_cannot_be_self_published(seller, student, settings, staff):
    """PRD AC-S4.4: *"an ISBN is required. A listing with no ISBN needs staff
    approval and cannot be self-published."*"""
    from apps.catalog.models import Book
    from apps.catalog.services import normalise_title

    settings.LISTING_REVIEW_ALL = False
    pre_isbn = Book.objects.create(
        isbn13=None, title="A pre-ISBN book", title_norm=normalise_title("A pre-ISBN book"),
        staff_verified_at=None,
    )
    from django.utils import timezone

    Book.objects.filter(id=pre_isbn.id).update(staff_verified_at=timezone.now())
    pre_isbn.refresh_from_db()

    listing = _create(seller, pre_isbn)
    listing = services.publish_listing(seller, listing, listing.version)
    assert listing.status == "PENDING_REVIEW", (
        "a staff-verified book with no ISBN still cannot be self-published"
    )


def test_an_unverified_book_sends_the_listing_to_review(seller, book, settings):
    """DATA-MODEL §6.1: review is required when the `books` row is unverified."""
    settings.LISTING_REVIEW_ALL = False
    assert book.staff_verified_at is None
    listing = _create(seller, book)
    listing = services.publish_listing(seller, listing, listing.version)
    assert listing.status == "PENDING_REVIEW"


def test_published_at_is_set_once_and_never_rewritten(seller, book, staff, settings):
    """*"The start of time-to-match"* (§9.3). A relisted book is a new row, so
    this timestamp is never moved — a metric that silently restarts its clock
    is worse than one that is absent."""
    settings.LISTING_REVIEW_ALL = False
    from apps.catalog.services import verify_book

    verify_book(staff, book)
    book.refresh_from_db()
    listing = services.publish_listing(seller, _create(seller, book), 1)
    first = listing.published_at
    assert first is not None

    Listing.all_objects.filter(id=listing.id).update(status="RESERVED", version=listing.version + 1)
    listing.refresh_from_db()
    listing = services._transition(
        listing, "LIVE", listing.version, actor=seller, action="test.relive"
    )
    assert listing.published_at == first


@pytest.mark.parametrize(
    "terminal", ["WITHDRAWN", "REJECTED", "CLOSED_TRANSFERRED", "REMOVED_LEGAL"]
)
def test_a_terminal_state_has_no_exit(seller, book, terminal):
    """DATA-MODEL §6.1's four terminal states, derived from the map rather
    than retyped — so the test and the machine cannot disagree."""
    assert services.LISTING_TRANSITIONS[terminal] == set()
    assert terminal in services.TERMINAL_STATUSES


def test_withdrawing_sets_the_retention_clock(seller, book):
    """`purge_due_at = closed_at + 1 year` (r.8(3)), set by the event rather
    than by a later job — otherwise a listing closed today has no clock until
    something notices."""
    from apps.accounts.services import RETENTION_FLOOR

    listing = _create(seller, book)
    listing = services.withdraw_listing(seller, listing, listing.version)
    assert listing.status == "WITHDRAWN"
    assert listing.closed_at is not None
    assert listing.purge_due_at == listing.closed_at + RETENTION_FLOOR


def test_a_stale_expected_version_is_a_conflict(seller, book):
    """API-CONTRACT §4.2, and it is a conditional UPDATE rather than a
    read-then-write: two writers who both read version 1 cannot both win."""
    listing = _create(seller, book)
    services.publish_listing(seller, listing, listing.version)
    with pytest.raises(VersionConflict):
        services.withdraw_listing(seller, listing, 1)


def test_a_missing_expected_version_is_refused_rather_than_defaulted(seller, book):
    listing = _create(seller, book)
    with pytest.raises(ValidationFailed):
        services.publish_listing(seller, listing, None)


def test_another_students_listing_is_a_404_not_a_403(seller, book, pending_student):
    """API-CONTRACT §2.2: *"the same body either way; a 403 would confirm
    existence and leak the catalogue."*"""
    from apps.core.errors import NotFound

    listing = _create(seller, book)
    pending_student.status = "ACTIVE"
    pending_student.adult_verified = True
    pending_student.save(update_fields=["status", "adult_verified"])
    with pytest.raises(NotFound) as caught:
        services.get_own_listing(pending_student, listing.id)
    assert caught.value.http_status == 404


# --- moderation -----------------------------------------------------------


def test_only_staff_can_moderate(seller, book):
    listing = services.publish_listing(seller, _create(seller, book), 1)
    with pytest.raises(NotPermitted):
        services.moderate_listing(seller, listing, "REVIEW_PASS", "terms", "fine", 10)


def test_a_moderation_decision_needs_a_basis_and_a_non_empty_reason(seller, book, staff):
    """PRD AC-M1.4. The reason is shown **verbatim to the seller**, so a blank
    one is refused rather than defaulted — AC-M1.4 also says the rejection
    reason is never blank."""
    listing = services.publish_listing(seller, _create(seller, book), 1)
    with pytest.raises(ValidationFailed):
        services.moderate_listing(staff, listing, "REVIEW_PASS", "terms", "   ", 10)
    with pytest.raises(ValidationFailed):
        services.moderate_listing(staff, listing, "REVIEW_PASS", "", "looks fine", 10)


def test_review_pass_makes_it_live_and_records_the_work_seconds(seller, book, staff):
    """D-009's instrumentation ships with the behaviour (TASKS §0 rule 4).

    `moderation_actions` is an S6 table, so the number goes into `audit_log`
    now and S6 has a source to backfill from — recorded rather than deferred
    into a slice that would have to invent it.
    """
    from apps.core.models import AuditLog

    listing = services.publish_listing(seller, _create(seller, book), 1)
    updated = services.moderate_listing(
        staff, listing, "REVIEW_PASS", "seller terms accepted", "Photos match the edition.", 45
    )
    assert updated.status == "LIVE"
    assert updated.published_at is not None
    assert AuditLog.objects.filter(action="listings.moderated.review_pass").exists()


def test_the_review_queue_is_staff_only_and_holds_pending_listings(seller, book, staff):
    listing = services.publish_listing(seller, _create(seller, book), 1)
    with pytest.raises(NotPermitted):
        services.review_queue(seller)
    assert listing.id in {row.id for row in services.review_queue(staff)}


def test_there_is_no_bulk_approve(staff):
    """PRD AC-M1.5, asserted on the signature rather than on the UI: one
    listing, one decision, one logged reason. A signature that took a list
    would be a bulk approve whatever the screen looked like."""
    import inspect

    params = inspect.signature(services.moderate_listing).parameters
    assert list(params) == ["staff", "listing", "action", "legal_basis", "reason", "work_seconds"]


# --- book requests, the demand side ---------------------------------------


def test_a_want_names_a_book_or_a_title(seller, book):
    """DATA-MODEL §3's CHECK, detected above the schema."""
    with pytest.raises(ValidationFailed):
        services.create_request(seller)
    assert services.create_request(seller, book=book).status == "OPEN"
    assert services.create_request(seller, free_text_title="Some unknown title").status == "OPEN"


def test_the_same_want_twice_is_one_want(seller, book):
    """The match rate counts people, not taps."""
    first = services.create_request(seller, book=book)
    second = services.create_request(seller, book=book)
    assert first.id == second.id


def test_closing_a_want_is_withdrawn_and_never_fulfilled(seller, book):
    """**Only a completed transfer may write FULFILLED** (amendment A-3, S4).

    The match rate's numerator is *transfers that closed a want*; a student
    tidying their list is not one, and conflating them would make the metric
    report liquidity that did not happen.
    """
    row = services.create_request(seller, book=book)
    closed = services.close_request(seller, row)
    assert closed.status == "WITHDRAWN"
    assert closed.closed_at is not None


def test_closing_someone_elses_want_is_a_404(seller, book, pending_student, privacy_notice):
    """§2.5 precondition 6 before precondition anything-else: a want that is
    not yours is **not found**, not forbidden.

    The second student is given the full Stack M so the refusal is the
    ownership one and not a consent one — otherwise this would pass for the
    wrong reason, which is the shape `CLAUDE.md` rule 10 names.
    """
    from apps.accounts.services import grant_consent
    from apps.core.errors import NotFound

    row = services.create_request(seller, book=book)
    pending_student.status = "ACTIVE"
    pending_student.adult_verified = True
    pending_student.save(update_fields=["status", "adult_verified"])
    grant_consent(pending_student, "account", privacy_notice, "SIGNUP_FORM", None, "pytest")
    with pytest.raises(NotFound):
        services.close_request(pending_student, row)


def test_closing_a_closed_want_is_a_422(seller, book):
    row = services.create_request(seller, book=book)
    services.close_request(seller, row)
    with pytest.raises(TransitionNotAllowed):
        services.close_request(seller, row)


# --- the two couplings that belong to later slices, recorded -------------


def test_the_match_scan_enqueue_is_recorded_as_s3():
    """API-CONTRACT §3 puts `requests.match_scan` on `publish_listing`;
    TASKS §2 amendment A-4 puts the job in **S3**.

    Wiring it now would be a `ValueError` on every publish, because
    `enqueue` refuses a kind with no registered handler. **This is the
    inverted guard** (`CLAUDE.md` rule 10): the day the handler is registered
    without `publish_listing` enqueueing it, this fails — rather than a
    comment that skips forever.
    """
    import inspect

    from apps.core.jobs import REGISTRY

    if "requests.match_scan" in REGISTRY:
        source = inspect.getsource(services.publish_listing)
        assert "requests.match_scan" in source, (
            "the S3 handler is registered and publish_listing still does not "
            "enqueue it, so a published listing never matches a want "
            "(API-CONTRACT §3, amendment A-4)"
        )
    else:
        assert "requests.match_scan" not in REGISTRY


def test_the_fulfilment_column_is_recorded_as_pending():
    """DATA-MODEL §3 gives `book_requests` a `fulfilled_by_transfer_id`; a FK
    to `transfers` cannot exist before S4 creates the table.

    Inverted the same way: once `apps.transfers` is installed, the column has
    to be there, because A-3's `confirm_handover` is what writes it and the
    request-side match rate returns zero permanently without it.
    """
    from django.apps import apps as django_apps
    from django.conf import settings

    from apps.listings.models import BookRequest

    columns = {f.column for f in BookRequest._meta.concrete_fields}
    if "apps.transfers" in settings.INSTALLED_APPS:
        assert "fulfilled_by_transfer_id" in columns, (
            "apps.transfers exists, so book_requests must now carry "
            "fulfilled_by_transfer_id — amendment A-3's confirm_handover is "
            "the only writer and §9.3's match rate is unreadable without it"
        )
    else:
        assert "fulfilled_by_transfer_id" not in columns
        assert not django_apps.is_installed("apps.transfers")


def test_the_open_offer_cancellation_is_recorded_as_s4():
    """JOURNEYS J2 step 11 / EC-2: withdrawing a listing with an open offer
    must cancel the transfer and tell the buyer plainly. `transfers` is S4,
    so the listing side is complete here and the transfer side is named."""
    import inspect

    from django.conf import settings

    if "apps.transfers" in settings.INSTALLED_APPS:
        source = inspect.getsource(services.withdraw_listing)
        assert "transfer" in source.lower(), (
            "apps.transfers exists and withdraw_listing still does not cancel "
            "an open offer (JOURNEYS J2 step 11, EC-2) — the buyer is left "
            "with a silent disappearance"
        )
