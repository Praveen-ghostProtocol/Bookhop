"""ADR-002 §4 — the legal gate on discovery.

What is actually verified here, and what is not, is stated per test. The gate's
three parts are (a) the nullable column, (b) the evidence-gated command, and
(c) the seed/real separation. (a) and (b) exist in S0 and are verified. The part
of (c) that needs a `listings` table (S2) and a `transfers` table (S4) is
written and skipped with the slice named — see `test_non_seed_listing_*` and
tests/unit/test_seed_separation.py.
"""

import pytest
from django.core.management import CommandError, call_command
from django.db import DatabaseError, transaction

from django.utils.timezone import now as timezone_now

from apps.core.errors import GateClosed
from apps.core.models import Campus, GateAuthorisation
from apps.core.services import assert_discovery_open

pytestmark = pytest.mark.django_db


# --- (a) the column -------------------------------------------------------


def test_new_campus_defaults_to_closed(city, legal_entity):
    campus = Campus.objects.create(city=city, name="Fresh", slug="fresh", legal_entity=legal_entity)
    assert campus.discovery_enabled_at is None
    with pytest.raises(GateClosed):
        assert_discovery_open(campus)


def test_assert_discovery_open_raises_gate_closed_with_the_contract_code(closed_campus):
    with pytest.raises(GateClosed) as exc:
        assert_discovery_open(closed_campus)
    assert exc.value.code == "GATE_CLOSED"
    assert exc.value.http_status == 403


def test_assert_discovery_open_passes_once_opened(closed_campus):
    from django.utils import timezone

    closed_campus.discovery_enabled_at = timezone.now()
    assert_discovery_open(closed_campus)  # does not raise


def test_assert_discovery_open_rejects_a_missing_campus():
    with pytest.raises(GateClosed):
        assert_discovery_open(None)


# --- (b) the evidence-gated command --------------------------------------


def test_open_discovery_refuses_a_campus_with_no_authorisation(closed_campus):
    with pytest.raises(CommandError, match="GATE C NOT SATISFIED"):
        call_command("open_discovery", campus="closed")
    closed_campus.refresh_from_db()
    assert closed_campus.discovery_enabled_at is None


@pytest.mark.parametrize(
    "missing",
    ["counsel_engagement_ref", "takedown_sop_ref", "oncall_rota_ref",
     "breach_rehearsal_at", "campus_mou_ref", "notice_version_ids"],
)
@pytest.mark.parametrize("blank", ["", "   ", []])
def test_the_checklist_refuses_each_missing_or_blank_evidence_item(
    closed_campus, legal_entity, complete_evidence, missing, blank
):
    """The command's printed checklist, tested directly on an unsaved row.

    It used to be tested by saving an incomplete authorisation and running the
    command. **Migration 0005 now refuses that INSERT**, so the row cannot
    exist and the command's evidence branch is unreachable from the database —
    which is the control working, not the test becoming unnecessary: the
    checklist is what tells an operator *which* item to go and get, with its
    Gate number, instead of just refusing.

    S4's whitespace case is folded in here (`blank = "   "`), since
    `_present()` strips and the database now does too.
    """
    from apps.core.management.commands.open_discovery import checklist

    evidence = dict(complete_evidence)
    evidence[missing] = [] if missing == "notice_version_ids" and blank == [] else blank
    auth = GateAuthorisation(
        id=1, gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=evidence, authorised_by_human="A Human",
    )
    items, _ = checklist(closed_campus, auth=auth)
    failed = [label for ok, label, _detail in items if not ok]
    assert any(missing in label for label in failed), (
        f"the checklist passed a blank {missing!r}; failed items were {failed}"
    )


def test_the_checklist_passes_a_complete_authorisation(
    closed_campus, legal_entity, complete_evidence
):
    """The other half, so the test above cannot pass by the checklist failing
    everything."""
    from apps.core.management.commands.open_discovery import checklist

    auth = GateAuthorisation(
        id=1, gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=complete_evidence,
        authorised_by_human="A Human",
    )
    items, _ = checklist(closed_campus, auth=auth)
    assert [label for ok, label, _d in items if not ok] == []


@pytest.mark.parametrize("missing", ["cin", "inc20a_filed_at", "grievance_officer_email"])
def test_open_discovery_refuses_without_the_legal_entity_facts(
    closed_campus, legal_entity, complete_evidence, missing
):
    setattr(legal_entity, missing, None)
    legal_entity.save()
    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=complete_evidence, authorised_by_human="A Human",
    )
    with pytest.raises(CommandError, match=missing):
        call_command("open_discovery", campus="closed")


def test_open_discovery_refuses_a_revoked_authorisation(closed_campus, legal_entity, complete_evidence):
    from django.utils import timezone

    auth = GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=complete_evidence, authorised_by_human="A Human",
    )
    GateAuthorisation.objects.filter(id=auth.id).update(
        revoked_at=timezone.now(), revoked_reason="withdrawn"
    )
    with pytest.raises(CommandError, match="gate_authorisations row"):
        call_command("open_discovery", campus="closed")


def test_the_checklist_refuses_a_blank_named_human(closed_campus, legal_entity, complete_evidence):
    """Also unreachable from the database since migration 0005, so tested on an
    unsaved row — see the note on the evidence checklist above."""
    from apps.core.management.commands.open_discovery import checklist

    auth = GateAuthorisation(
        id=1, gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=complete_evidence, authorised_by_human="   ",
    )
    items, _ = checklist(closed_campus, auth=auth)
    assert any("authorised_by_human" in label for ok, label, _d in items if not ok)


def test_open_discovery_opens_with_complete_evidence_and_writes_an_audit_row(
    closed_campus, legal_entity, complete_evidence
):
    from apps.core.models import AuditLog

    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=complete_evidence, authorised_by_human="A Human",
    )
    call_command("open_discovery", campus="closed")
    closed_campus.refresh_from_db()
    assert closed_campus.discovery_enabled_at is not None
    row = AuditLog.objects.get(action="discovery.open")
    assert row.object_type == "Campus" and row.object_id == str(closed_campus.id)


def test_close_discovery_closes_and_revokes(closed_campus, legal_entity, complete_evidence):
    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=complete_evidence, authorised_by_human="A Human",
    )
    call_command("open_discovery", campus="closed")
    call_command("close_discovery", campus="closed", reason="pilot paused")
    closed_campus.refresh_from_db()
    assert closed_campus.discovery_enabled_at is None
    auth = GateAuthorisation.objects.get()
    assert auth.revoked_at is not None and auth.revoked_reason == "pilot paused"


# --- the gate authorisation row is append-only ---------------------------


@pytest.mark.parametrize(
    "label,mutate",
    [
        ("empty evidence", lambda e: {}),
        ("missing campus_mou_ref", lambda e: {k: v for k, v in e.items() if k != "campus_mou_ref"}),
        ("blank campus_mou_ref", lambda e: dict(e, campus_mou_ref="   ")),
        ("empty notice_version_ids", lambda e: dict(e, notice_version_ids=[])),
        ("missing counsel_engagement_ref", lambda e: {k: v for k, v in e.items()
                                                      if k != "counsel_engagement_ref"}),
    ],
)
def test_an_incomplete_gate_c_authorisation_cannot_be_written_at_all(
    closed_campus, legal_entity, complete_evidence, label, mutate
):
    """QA-S0 F8. The 0003 trigger checked that an authorisation *existed*, not
    that it was *complete*, so an `INSERT` with `evidence={}` plus an ORM update
    opened the gate with an empty checklist and no audit row.

    ADR-002 §4.1(b)'s six evidence items lived only in the command; migration
    0005 moves them into the database, which is what "the floor beneath it"
    should have meant.
    """
    with pytest.raises(DatabaseError, match="ADR-002"):
        with transaction.atomic():
            GateAuthorisation.objects.create(
                gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
                legal_entity=legal_entity, evidence=mutate(complete_evidence),
                authorised_by_human="A Human",
            )
    assert not GateAuthorisation.objects.exists()


#: REVIEW-S0 C1's twelve forms, each with its codepoint, because the finding was
#: that four characters is not the list.
BLANK_FORMS = [
    ("empty", ""),
    ("space U+0020", " "),
    ("tab U+0009", "\t"),
    ("line feed U+000A", "\n"),
    ("carriage return U+000D", "\r"),
    ("vertical tab U+000B", "\x0b"),
    ("form feed U+000C", "\x0c"),
    ("NBSP U+00A0", " "),
    ("ogham space U+1680", " "),
    ("figure space U+2007", " "),
    ("zero-width space U+200B", "​"),
    ("BOM U+FEFF", "﻿"),
]


@pytest.mark.parametrize("label,who", BLANK_FORMS, ids=[label for label, _ in BLANK_FORMS])
def test_a_gate_c_authorisation_needs_a_visible_named_human_in_the_database(
    closed_campus, legal_entity, complete_evidence, label, who
):
    """ADR-002 §4.1(b): *"A named human, recorded. No agent writes this row."*

    REVIEW-S0 C1. The first fix trimmed four characters, and a trim-based blank
    check is a whitespace deny-list: vertical tab, form feed, **NBSP — what a
    paste from Word produces** — figure space and ogham space all passed the
    floor while the command above it blocked them, which is QA's F8 complaint
    recurring one level down inside the fix for F8. **Zero-width space and BOM
    passed both layers**, so the one field whose entire purpose is naming an
    accountable human could be satisfied by something that renders as nothing
    in the audit row and in the go/no-go packet.
    """
    with pytest.raises(DatabaseError, match="named human"):
        with transaction.atomic():
            GateAuthorisation.objects.create(
                gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
                legal_entity=legal_entity, evidence=complete_evidence,
                authorised_by_human=who,
            )


@pytest.mark.parametrize("label,blank", BLANK_FORMS, ids=[label for label, _ in BLANK_FORMS])
def test_evidence_is_not_present_in_any_of_the_blank_forms(
    closed_campus, legal_entity, complete_evidence, label, blank
):
    """The same twelve forms against an evidence value: the reviewer measured
    that `campus_mou_ref` was accepted as a signed MoU for all of them."""
    with pytest.raises(DatabaseError, match="ADR-002"):
        with transaction.atomic():
            GateAuthorisation.objects.create(
                gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
                legal_entity=legal_entity,
                evidence=dict(complete_evidence, campus_mou_ref=blank),
                authorised_by_human="A Human",
            )


@pytest.mark.parametrize(
    "invisible",
    ["‌", "‍", "⁠", "᠎", "­"],
    ids=["ZWNJ U+200C", "ZWJ U+200D", "word joiner U+2060",
         "Mongolian vowel separator U+180E", "soft hyphen U+00AD"],
)
def test_the_invariant_catches_invisibles_the_database_list_does_not(invisible):
    """The point of C1, generalised: **a blank check should assert the value
    contains at least one visible character, not that it lacks the whitespace
    we remembered.**

    `has_visible_character` asks Python's Unicode database per character, so it
    needs no list and gains none — these five are not in migration 0005's
    enumerated set and are caught anyway. Neither engine can express the test
    (SQLite has no regex; Postgres's `[[:graph:]]` is locale-dependent), so the
    floor enumerates and the command generalises. That asymmetry is the right
    one: the floor catches every form anyone has measured, and the layer above
    catches the ones nobody has.
    """
    from apps.core.management.commands.open_discovery import _present, has_visible_character

    assert not has_visible_character(invisible)
    assert not _present(invisible)
    assert not _present([invisible])
    # and it still accepts a real name, including a non-Latin one
    assert has_visible_character("A Human")
    assert has_visible_character("தமிழ்")
    assert has_visible_character(f"{invisible}A{invisible}")


def test_an_incomplete_authorisation_cannot_be_used_to_open_the_gate(
    closed_campus, legal_entity, complete_evidence
):
    """The end-to-end shape of F8: forge a row, then try the ORM update.

    The forgery is refused at the INSERT, so the gate stays closed and the
    column guard is never even reached.
    """
    from django.utils import timezone

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            GateAuthorisation.objects.create(
                gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
                legal_entity=legal_entity, evidence={}, authorised_by_human="",
            )
    with pytest.raises(DatabaseError, match="ADR-002"):
        with transaction.atomic():
            Campus.objects.filter(pk=closed_campus.pk).update(discovery_enabled_at=timezone.now())
    closed_campus.refresh_from_db()
    assert closed_campus.discovery_enabled_at is None


def test_a_non_gate_c_authorisation_is_not_evidence_constrained(legal_entity):
    """Scoped on purpose. ADR-002 §4.1(b) specifies the checklist for Gate C;
    inventing one for B or D would be scaffolding for a gate nothing opens."""
    GateAuthorisation.objects.create(
        gate="B", scope_type="GLOBAL", legal_entity=legal_entity,
        evidence={}, authorised_by_human="A Human",
    )
    assert GateAuthorisation.objects.filter(gate="B").exists()


def test_the_database_floor_does_not_check_whether_the_evidence_is_true(
    closed_campus, legal_entity
):
    """The bound on F8's fix, asserted so the floor is not overread.

    QA-S0 B2: `campus_mou_ref='TODO'` and `breach_rehearsal_at='not yet'` still
    open the gate. ADR-002 §4.2 already says this design makes the position
    auditable, not correct, and a CHECK cannot read a counsel engagement letter.
    This test exists so that a reader of the go/no-go packet knows the
    difference between "every box was filled" and "every box was true".

    REVIEW-S0 C1 extends the sentence to cover shape as well as content:
    "filled" used to include "filled with nothing visible", because a
    zero-width space passed both layers. `test_the_gate_cannot_be_opened_by_an_invisible_name`
    below is that case, and it now refuses — so the bound of this test is
    "every box holds something visible that nobody checked the truth of",
    which is the honest claim.
    """
    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity,
        evidence={
            "counsel_engagement_ref": "-", "takedown_sop_ref": "TODO",
            "oncall_rota_ref": "TODO", "breach_rehearsal_at": "not yet",
            "campus_mou_ref": "TODO", "notice_version_ids": ["none"],
        },
        authorised_by_human="agent",
    )
    call_command("open_discovery", campus="closed")
    closed_campus.refresh_from_db()
    assert closed_campus.discovery_enabled_at is not None


def test_the_gate_cannot_be_opened_by_an_invisible_name(closed_campus, legal_entity):
    """REVIEW-S0 C1's second consequence, which is the one that mattered.

    Before this fix `authorised_by_human = "\\u200b"` with an otherwise
    complete checklist opened the gate — and rendered as an empty name in the
    audit row, in `gate_authorisations` and in the go/no-go packet. Not a
    bypass: the complete evidence set, the live scoped authorisation, `active`,
    the legal-entity match and the five legal-entity facts all still held. But
    the one field carrying "a named human signed this" could be satisfied by
    something invisible, and the artefact a human reads at a launch gate would
    have shown nobody's name.
    """
    evidence = {
        "counsel_engagement_ref": "ENG-1", "takedown_sop_ref": "SOP-1",
        "oncall_rota_ref": "ROTA-1", "breach_rehearsal_at": "2026-11-10",
        "campus_mou_ref": "MOU-1", "notice_version_ids": [1, 2, 3],
    }
    with pytest.raises(DatabaseError, match="named human"):
        with transaction.atomic():
            GateAuthorisation.objects.create(
                gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
                legal_entity=legal_entity, evidence=evidence,
                authorised_by_human="​",
            )
    assert not GateAuthorisation.objects.exists()
    with pytest.raises(CommandError, match="gate_authorisations row"):
        call_command("open_discovery", campus="closed")
    closed_campus.refresh_from_db()
    assert closed_campus.discovery_enabled_at is None


def test_gate_authorisation_cannot_be_deleted(closed_campus, legal_entity, complete_evidence):
    auth = GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=complete_evidence, authorised_by_human="A Human",
    )
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            GateAuthorisation.objects.filter(id=auth.id).delete()
    assert GateAuthorisation.objects.filter(id=auth.id).exists()


def test_gate_authorisation_evidence_cannot_be_rewritten(
    closed_campus, legal_entity, complete_evidence
):
    auth = GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=complete_evidence, authorised_by_human="A Human",
    )
    rewritten = dict(complete_evidence, campus_mou_ref="MOU-FORGED")
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            GateAuthorisation.objects.filter(id=auth.id).update(evidence=rewritten)
    auth.refresh_from_db()
    assert auth.evidence == complete_evidence


# --- (a) again: the column's own write guard (M0) ------------------------
#
# REVIEW-S0 §6.0 is the lesson these tests exist for: 21 green assertions that
# all drove the front door, none of which asked whether the column those
# commands guard could be written by anything else. It could. Migration 0003
# closes it; these assert the closure rather than the command.


def test_an_orm_update_cannot_open_the_gate(closed_campus, engine):
    """ADR-002 §4.1(b): "Discovery cannot be opened by `UPDATE campuses SET
    discovery_enabled_at = now()`." Now true, enforced by the database."""
    from django.utils import timezone

    from apps.core.models import AuditLog

    audit_before = AuditLog.objects.count()
    with pytest.raises(DatabaseError, match="ADR-002"):
        with transaction.atomic():
            Campus.objects.filter(pk=closed_campus.pk).update(discovery_enabled_at=timezone.now())
    closed_campus.refresh_from_db()
    assert closed_campus.discovery_enabled_at is None, f"the gate was opened on {engine}"
    assert AuditLog.objects.count() == audit_before


def test_a_model_save_cannot_open_the_gate(closed_campus):
    from django.utils import timezone

    closed_campus.discovery_enabled_at = timezone.now()
    with pytest.raises(DatabaseError, match="ADR-002"):
        with transaction.atomic():
            closed_campus.save(update_fields=["discovery_enabled_at"])
    closed_campus.refresh_from_db()
    assert closed_campus.discovery_enabled_at is None


def test_a_campus_cannot_be_created_already_open(city, legal_entity):
    from django.utils import timezone

    with pytest.raises(DatabaseError, match="ADR-002"):
        with transaction.atomic():
            Campus.objects.create(
                city=city, name="Preset", slug="preset", legal_entity=legal_entity,
                discovery_enabled_at=timezone.now(),
            )
    assert not Campus.objects.filter(slug="preset").exists()


def test_another_campuss_authorisation_cannot_open_this_one(
    closed_campus, city, legal_entity, complete_evidence
):
    """S9. The command filters on `scope_id`; nothing tested that it must."""
    from django.utils import timezone

    neighbour = Campus.objects.create(
        city=city, name="Neighbour", slug="neighbour", legal_entity=legal_entity
    )
    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=neighbour.id,
        legal_entity=legal_entity, evidence=complete_evidence, authorised_by_human="A Human",
    )
    with pytest.raises(CommandError, match="gate_authorisations row"):
        call_command("open_discovery", campus="closed")
    with pytest.raises(DatabaseError, match="ADR-002"):
        with transaction.atomic():
            Campus.objects.filter(pk=closed_campus.pk).update(discovery_enabled_at=timezone.now())


@pytest.mark.parametrize(
    "gate,scope_type", [("B", "CAMPUS"), ("D", "CAMPUS"), ("C", "GLOBAL")]
)
def test_only_a_gate_c_campus_scoped_authorisation_counts(
    closed_campus, legal_entity, complete_evidence, gate, scope_type
):
    """S9. All three selectors matter, and none of them was tested."""
    from django.utils import timezone

    GateAuthorisation.objects.create(
        gate=gate, scope_type=scope_type, scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=complete_evidence, authorised_by_human="A Human",
    )
    with pytest.raises(CommandError, match="gate_authorisations row"):
        call_command("open_discovery", campus="closed")
    with pytest.raises(DatabaseError, match="ADR-002"):
        with transaction.atomic():
            Campus.objects.filter(pk=closed_campus.pk).update(discovery_enabled_at=timezone.now())


def test_closing_the_gate_is_always_permitted(closed_campus, legal_entity, complete_evidence):
    """The guard must never be what stops a close. A campus that cannot be
    closed is a worse failure than one that was opened carelessly."""
    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=complete_evidence, authorised_by_human="A Human",
    )
    call_command("open_discovery", campus="closed")
    closed_campus.refresh_from_db()
    assert closed_campus.discovery_enabled_at is not None
    # Even a bare ORM write, and even with every authorisation revoked.
    GateAuthorisation.objects.filter(scope_id=closed_campus.id).update(
        revoked_at=timezone_now(), revoked_reason="x"
    )
    Campus.objects.filter(pk=closed_campus.pk).update(discovery_enabled_at=None)
    closed_campus.refresh_from_db()
    assert closed_campus.discovery_enabled_at is None


def test_an_inactive_campus_cannot_be_opened(closed_campus, legal_entity, complete_evidence):
    """QA-S0 B1, write half."""
    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=complete_evidence, authorised_by_human="A Human",
    )
    Campus.objects.filter(pk=closed_campus.pk).update(active=False)
    with pytest.raises(CommandError, match="campuses.active"):
        call_command("open_discovery", campus="closed")


def test_an_inactive_campus_with_an_open_gate_still_refuses_readers(closed_campus):
    """QA-S0 B1, read half — and the half that matters, because deactivating an
    already-open campus is just an `active` flip that no trigger sees."""
    from django.utils import timezone

    closed_campus.discovery_enabled_at = timezone.now()
    closed_campus.active = False
    with pytest.raises(GateClosed) as exc:
        assert_discovery_open(closed_campus)
    assert exc.value.context["reason"] == "campus_inactive"


def test_an_authorisation_for_a_different_legal_entity_is_refused(
    closed_campus, legal_entity, complete_evidence
):
    """S5. A row authorised against entity A could open a campus whose CIN and
    INC-20A facts were read from entity B, and nothing compared them."""
    from apps.core.models import LegalEntity

    other = LegalEntity.objects.create(cin="OTHER", inc20a_filed_at="2026-11-01",
                                       grievance_officer_name="B", grievance_officer_email="b@x.test",
                                       grievance_officer_phone="+91")
    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=other, evidence=complete_evidence, authorised_by_human="A Human",
    )
    with pytest.raises(CommandError, match="legal_entity_id"):
        call_command("open_discovery", campus="closed")


def test_the_audit_row_always_names_a_human(closed_campus, legal_entity, complete_evidence):
    """N5. The audit row for the most legally significant action in the system
    used to read `actor_type='SYSTEM'` with no human on it at all.

    `--by` is optional and defaults to the authorising human, so the row names
    someone whether or not the operator passes it — rather than requiring a new
    argument and breaking every existing caller.
    """
    from apps.core.models import AuditLog

    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=complete_evidence, authorised_by_human="A Human",
    )
    call_command("open_discovery", campus="closed")  # no --by
    first = AuditLog.objects.get(action="discovery.open").after_hash
    assert first  # the payload is hashed, not stored (DATA-MODEL §8, QA-S0 B4)

    call_command("close_discovery", campus="closed", reason="pilot paused")
    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=complete_evidence, authorised_by_human="A Human",
    )
    call_command("open_discovery", campus="closed", by="Someone Else")
    second = AuditLog.objects.filter(action="discovery.open").order_by("-id").first().after_hash

    # Same campus, same authorising human, different operator -> different
    # payload hash, which is what proves the operator is in the recorded row.
    assert first != second


# --- (c) the part S0 cannot verify ---------------------------------------


@pytest.mark.skip(
    reason="NOT VERIFIED IN S0. Asserting that a non-seed listing is never returned "
    "for a campus with discovery_enabled_at IS NULL needs the `listings` table "
    "(S2) and search_listings (S3). The helper the query will use is "
    "apps.core.scoping.restrict_when_gate_closed; the tests below exercise both "
    "of its branches against real querysets, and the end-to-end property is "
    "S3's and test-qa's gate journey."
)
def test_non_seed_listing_is_unreachable_while_the_gate_is_closed():
    raise AssertionError("unreachable; see skip reason")


def test_restrict_when_gate_closed_fails_loudly_on_a_model_without_is_seed(closed_campus):
    """Replaces a test that asserted against a hand-written `FakeQuerySet`.

    Both REVIEW-S0 §6.4 and QA-S0 §7 named that version: it proved the helper
    called `.filter(is_seed=True)` and nothing about any real query, and it
    touched no database. This uses a **real** queryset, and asserts the property
    that actually protects us — that applying the gate filter to a model with no
    `is_seed` column raises rather than silently returning everything. A gate
    filter that quietly no-ops is worse than one that is absent.

    No S0 model has an `is_seed` column (`users` and `listings` are S1/S2), so
    the row-level assertion is `test_non_seed_listing_*` above, skipped to S3.
    """
    from django.core.exceptions import FieldError

    from apps.core.scoping import restrict_when_gate_closed

    with pytest.raises(FieldError):
        list(restrict_when_gate_closed(Campus.objects.all(), closed_campus))


def test_restrict_when_gate_closed_leaves_an_open_campus_untouched(
    closed_campus, legal_entity, complete_evidence
):
    """The open branch, against a real queryset that really executes."""
    from apps.core.scoping import restrict_when_gate_closed

    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=closed_campus.id,
        legal_entity=legal_entity, evidence=complete_evidence, authorised_by_human="A Human",
    )
    call_command("open_discovery", campus="closed")
    closed_campus.refresh_from_db()

    qs = Campus.objects.all()
    assert list(restrict_when_gate_closed(qs, closed_campus)) == list(qs)


def test_restrict_when_gate_closed_treats_an_inactive_campus_as_closed(closed_campus):
    """QA-S0 B1 again: `active=false` must not leave the filter off."""
    from django.core.exceptions import FieldError
    from django.utils import timezone

    from apps.core.scoping import restrict_when_gate_closed

    closed_campus.discovery_enabled_at = timezone.now()
    closed_campus.active = False
    with pytest.raises(FieldError):
        list(restrict_when_gate_closed(Campus.objects.all(), closed_campus))
