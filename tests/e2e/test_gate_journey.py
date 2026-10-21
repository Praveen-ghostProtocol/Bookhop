"""The discovery gate, verified from ADR-002 §4 / PRD AC-M6.1 / JOURNEYS J11.

The gate is the control that keeps BookHop from operating a platform before the
company is permitted to operate one (`INCORPORATION-AND-BLOCKERS.md` A0, Gate
C). It is the single most legally load-bearing thing S0 ships, so it is tested
here by driving the real commands and the real service function, from the
contract, not from the implementation.

What S0 lets this file reach, and what it does not, is stated plainly in
`test_a_real_student_cannot_reach_a_real_listing` — which skips, because the
tables the journey needs are S1's and S2's.
"""

import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, transaction
from django.db.models import BooleanField, Case, Value, When
from django.utils import timezone

from apps.core.errors import GateClosed
from apps.core.models import AuditLog, Campus, GateAuthorisation
from apps.core.scoping import (
    assert_discovery_open,
    restrict_when_gate_closed,
    visible_campus_ids,
)
from apps.core.services import SYSTEM, verify_audit_chain

pytestmark = pytest.mark.django_db


def _run(command, **kwargs):
    out = io.StringIO()
    call_command(command, stdout=out, stderr=out, **kwargs)
    return out.getvalue()


# --------------------------------------------------------------------------
# 1. NULL means closed, and NULL is the default
# --------------------------------------------------------------------------


def test_a_new_campus_is_closed_without_anyone_deciding_so(qa_city, qa_entity):
    """ADR-002 §4.1(a): a campus is closed unless someone deliberately opened it.

    Asserted on a campus created with no mention of the column at all, because
    the property that matters is the default, not what a fixture passes.
    """
    campus = Campus.objects.create(city=qa_city, name="Fresh", slug="fresh",
                                   legal_entity=qa_entity)
    campus.refresh_from_db()
    assert campus.discovery_enabled_at is None
    with pytest.raises(GateClosed):
        assert_discovery_open(campus)


def test_the_gate_refusal_is_the_contract_error(qa_campus):
    """API-CONTRACT §2.2: a real student on a closed campus gets
    `403 GATE_CLOSED`, and the message is the user-facing one, not a traceback."""
    with pytest.raises(GateClosed) as exc:
        assert_discovery_open(qa_campus)
    assert exc.value.code == "GATE_CLOSED"
    assert exc.value.http_status == 403
    assert str(exc.value).strip() != ""
    assert "Traceback" not in str(exc.value)


def test_no_campus_at_all_is_treated_as_closed():
    """Defensive: an actor with no campus must not fall through the gate open.
    ADR-002 §4.1(a) only specifies the NULL case; a None campus reaching this
    function is a bug upstream, and the safe answer is still 403."""
    with pytest.raises(GateClosed):
        assert_discovery_open(None)


def test_seed_demo_leaves_the_gate_closed():
    """TASKS §2 S0 and ADR-002 §4: the seed command must not open anything.
    A seed path that opens the gate would be the gate's most likely bypass."""
    _run("seed_demo")
    assert Campus.objects.filter(discovery_enabled_at__isnull=False).count() == 0
    _run("seed_demo")  # idempotent, still closed
    assert Campus.objects.filter(discovery_enabled_at__isnull=False).count() == 0


# --------------------------------------------------------------------------
# 2. opening the gate requires the whole checklist
# --------------------------------------------------------------------------


def test_open_discovery_refuses_with_no_authorisation_row(qa_campus):
    """ADR-002 §4.1(b): the command refuses unless a `gate_authorisations` row
    exists. And it must change nothing when it refuses."""
    with pytest.raises(CommandError) as exc:
        _run("open_discovery", campus=qa_campus.slug)
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None
    assert "gate_authorisations" in str(exc.value) or "GATE C NOT SATISFIED" in str(exc.value)


def test_open_discovery_succeeds_with_the_complete_checklist(qa_campus, qa_authorisation):
    out = _run("open_discovery", campus=qa_campus.slug)
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is not None
    assert "OPEN" in out
    assert_discovery_open(qa_campus)  # does not raise


@pytest.mark.parametrize(
    "missing_key",
    ["counsel_engagement_ref", "takedown_sop_ref", "oncall_rota_ref",
     "breach_rehearsal_at", "campus_mou_ref", "notice_version_ids"],
)
@pytest.mark.parametrize("how", ["absent", "blank", "empty_list"])
def test_each_missing_evidence_item_cannot_even_be_recorded(
    qa_campus, qa_entity, qa_evidence, missing_key, how
):
    """**REGRESSION for QA-S0 F8**, and the floor rising under an existing test.

    This test used to create an incomplete `gate='C'` row and assert that
    `open_discovery` refused, naming the item. Migration 0005 moved ADR-002
    §4.1(b)'s checklist into the database, so **the row can no longer be saved
    at all** and the command never gets the chance to refuse.

    That is the control working, and QA verified it rather than accepting it:
    the failure is an `IntegrityError` carrying the ADR-002 4.1(b) message, not
    an unrelated error that happened to land in the same place. Each of the six
    items is still attacked one at a time — a checklist that only checks the
    first item is not a checklist — and now in three shapes each, because
    "missing" has three spellings and a guard that only knew one would be a
    guard with two holes:

    * the key is **absent**;
    * the key is present and **blank** (whitespace only, which `trim()` on both
      engines strips to nothing);
    * the key is present and an **empty list**, which is the shape
      `notice_version_ids` actually takes.

    The *printed* checklist — the thing that tells an operator which item to go
    and get, with its Gate number — is no longer reachable from the database and
    is tested on an unsaved row by
    `test_the_printed_checklist_still_names_each_missing_item`.
    """
    evidence = dict(qa_evidence)
    if how == "absent":
        evidence.pop(missing_key)
    elif how == "blank":
        evidence[missing_key] = "   \t "
    else:
        evidence[missing_key] = []

    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            GateAuthorisation.objects.create(
                gate="C", scope_type="CAMPUS", scope_id=qa_campus.id,
                legal_entity=qa_entity, evidence=evidence,
                authorised_by_human="A Named Human",
            )
    assert "4.1(b)" in str(exc.value), (
        f"the row was refused, but not by the ADR-002 §4.1(b) guard: {exc.value}"
    )
    assert not GateAuthorisation.objects.exists()
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None


@pytest.mark.parametrize(
    "missing_key",
    ["counsel_engagement_ref", "takedown_sop_ref", "oncall_rota_ref",
     "breach_rehearsal_at", "campus_mou_ref", "notice_version_ids"],
)
def test_the_printed_checklist_still_names_each_missing_item(
    qa_campus, qa_entity, qa_evidence, missing_key
):
    """ENGINE-DIVERGENCE §9 item 11 is right that the command's per-item branch
    is now unreachable from the database, and right that this does not make it
    pointless: it is what tells an operator *which* item to go and get, with its
    Gate number. Unreachable code is still code, so QA asserts it directly, on a
    row the database will not accept, through the injectable `auth` argument.

    Without this, the six branches would be dead and nothing would notice if a
    future edit dropped one.
    """
    from apps.core.management.commands.open_discovery import checklist
    from apps.core.models import GateAuthorisation as GA

    evidence = dict(qa_evidence)
    evidence.pop(missing_key)
    unsaved = GA(
        gate="C", scope_type="CAMPUS", scope_id=qa_campus.id,
        legal_entity=qa_entity, evidence=evidence,
        authorised_by_human="A Named Human",
    )
    items, _auth = checklist(qa_campus, auth=unsaved)
    failed = [(ok, label) for ok, label, _detail in items if not ok]
    assert failed, "the checklist passed a row with a missing evidence item"
    assert any(missing_key in label for _ok, label in failed), (
        f"the checklist does not name {missing_key!r}: {failed}"
    )


@pytest.mark.parametrize(
    "field",
    ["cin", "inc20a_filed_at", "grievance_officer_name",
     "grievance_officer_email", "grievance_officer_phone"],
)
def test_each_missing_legal_entity_fact_blocks_the_open(
    qa_campus, qa_authorisation, field
):
    """ADR-002 §4.1(b) maps `cin` to Gate B1, `inc20a_filed_at` to the s10A bar
    on commencing business, and the grievance officer to Gate B4 / r.3(2)(a).
    Each is a separate legal obligation, so each must block on its own."""
    entity = qa_campus.legal_entity
    setattr(entity, field, None)
    entity.save(update_fields=[field])
    with pytest.raises(CommandError) as exc:
        _run("open_discovery", campus=qa_campus.slug)
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None
    assert field in str(exc.value)


@pytest.mark.parametrize("name", ["", "   ", "\t", "\n", " \t\r\n "])
def test_an_unnamed_human_cannot_be_recorded(qa_campus, qa_entity, qa_evidence, name):
    """ADR-002 §4.1(b): "A named human, recorded. No agent writes this row."

    **REGRESSION for QA-S0 F8**: previously the command refused; now the row
    cannot be saved. Parametrised over the whitespace characters because a bare
    `trim()`/`btrim()` strips **spaces only** on both engines, so a single tab
    passed as a named human until the guard named the characters explicitly —
    the migration says so, and this is QA checking it rather than reading it.
    """
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            GateAuthorisation.objects.create(
                gate="C", scope_type="CAMPUS", scope_id=qa_campus.id,
                legal_entity=qa_entity, evidence=qa_evidence,
                authorised_by_human=name,
            )
    assert "4.1(b)" in str(exc.value)
    assert not GateAuthorisation.objects.exists()


def test_a_complete_authorisation_is_still_accepted(qa_campus, qa_entity, qa_evidence):
    """The other half of every guard: the legitimate row must still save, or the
    control has replaced a hole with an outage."""
    auth = GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=qa_campus.id,
        legal_entity=qa_entity, evidence=qa_evidence,
        authorised_by_human="A Named Human",
    )
    assert auth.pk is not None
    _run("open_discovery", campus=qa_campus.slug)
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is not None


@pytest.mark.parametrize("gate", ["B", "D"])
def test_an_incomplete_authorisation_for_another_gate_is_still_permitted(
    qa_campus, qa_entity, gate
):
    """Migration 0005 constrains `gate='C'` only, and says so: ADR-002 §4.1(b)
    specifies the checklist for Gate C, and inventing one for gates nothing
    opens would be scaffolding. Asserted so the scope of the constraint is a
    tested fact rather than a comment — and because a Gate B row is how
    incorporation evidence will be recorded in S1."""
    auth = GateAuthorisation.objects.create(
        gate=gate, scope_type="GLOBAL", scope_id=None,
        legal_entity=qa_entity, evidence={}, authorised_by_human="",
    )
    assert auth.pk is not None


def test_an_incomplete_gate_c_row_cannot_be_laundered_through_another_gate(
    qa_campus, qa_entity
):
    """The obvious way round a `gate='C'`-only constraint: save an unconstrained
    `gate='B'` row, then update it to `C`.

    Two guards have to hold for this to be closed, and both are asserted: the
    0005 UPDATE trigger fires on `NEW.gate = 'C'`, and 0002's append-only
    trigger refuses the UPDATE outright. Belt and braces, and QA checked that
    both braces exist rather than assuming the first.
    """
    auth = GateAuthorisation.objects.create(
        gate="B", scope_type="CAMPUS", scope_id=qa_campus.id,
        legal_entity=qa_entity, evidence={}, authorised_by_human="",
    )
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            GateAuthorisation.objects.filter(pk=auth.pk).update(gate="C")
    auth.refresh_from_db()
    assert auth.gate == "B"
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None


def test_a_campus_with_no_legal_entity_cannot_be_opened(qa_city, qa_entity, qa_evidence):
    """`DATA-MODEL.md` §1: `campuses.legal_entity_id` "must be non-NULL before
    the gate can open"."""
    campus = Campus.objects.create(city=qa_city, name="Unattached", slug="unattached")
    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=campus.id, legal_entity=qa_entity,
        evidence=qa_evidence, authorised_by_human="A Named Human",
    )
    with pytest.raises(CommandError):
        _run("open_discovery", campus=campus.slug)
    campus.refresh_from_db()
    assert campus.discovery_enabled_at is None


@pytest.mark.parametrize("gate", ["B", "D"])
def test_an_authorisation_for_another_gate_does_not_open_discovery(
    qa_campus, qa_entity, qa_evidence, gate
):
    """ADR-002 §4.1(b) names `gate='C'` specifically. Gate B is incorporation;
    opening discovery on a Gate B row would skip Gate C's own items."""
    GateAuthorisation.objects.create(
        gate=gate, scope_type="CAMPUS", scope_id=qa_campus.id,
        legal_entity=qa_entity, evidence=qa_evidence,
        authorised_by_human="A Named Human",
    )
    with pytest.raises(CommandError):
        _run("open_discovery", campus=qa_campus.slug)
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None


def test_another_campuses_authorisation_does_not_open_this_one(
    qa_campus, qa_city, qa_entity, qa_evidence
):
    """Gate C is per campus (`scope_type='CAMPUS'`), because the MoU is per
    campus. One campus's authorisation must not open its neighbour."""
    other = Campus.objects.create(city=qa_city, name="Other", slug="other",
                                  legal_entity=qa_entity)
    GateAuthorisation.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=other.id, legal_entity=qa_entity,
        evidence=qa_evidence, authorised_by_human="A Named Human",
    )
    with pytest.raises(CommandError):
        _run("open_discovery", campus=qa_campus.slug)
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None


def test_a_global_authorisation_does_not_open_a_campus(
    qa_campus, qa_entity, qa_evidence
):
    """`scope_type='GLOBAL'` is a company-level authorisation. Gate C1 is a
    signed MoU with one campus and cannot be granted globally."""
    GateAuthorisation.objects.create(
        gate="C", scope_type="GLOBAL", scope_id=None, legal_entity=qa_entity,
        evidence=qa_evidence, authorised_by_human="A Named Human",
    )
    with pytest.raises(CommandError):
        _run("open_discovery", campus=qa_campus.slug)
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None


def test_a_revoked_authorisation_does_not_open_the_gate(qa_campus, qa_authorisation):
    """A revoked authorisation is a closed gate, or revocation means nothing."""
    GateAuthorisation.objects.filter(pk=qa_authorisation.pk).update(
        revoked_at=timezone.now(), revoked_reason="MoU withdrawn"
    )
    with pytest.raises(CommandError):
        _run("open_discovery", campus=qa_campus.slug)
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None


def test_open_discovery_on_an_unknown_campus_is_an_error():
    with pytest.raises(CommandError):
        _run("open_discovery", campus="no-such-campus")


# --------------------------------------------------------------------------
# 3. opening and closing is audited
# --------------------------------------------------------------------------


def test_opening_the_gate_writes_an_audit_row_and_a_named_human_survives(
    qa_campus, qa_authorisation
):
    """ADR-002 §4: "data plus a server-side guard plus an audit row".

    Note what the audit row does and does not hold: `DATA-MODEL.md` §8 gives
    `audit_log` a `before_hash`/`after_hash` pair, not the before and after
    values, so the row proves *that* the gate opened and *when*, and the named
    human is recoverable from the append-only `gate_authorisations` row the
    command read. Both halves are asserted here, because the go/no-go packet
    needs both and neither alone is the artefact.
    """
    _run("open_discovery", campus=qa_campus.slug)
    row = AuditLog.objects.filter(action="discovery.open").order_by("-id").first()
    assert row is not None, "opening the gate wrote no audit_log row"
    assert row.object_type == "Campus"
    assert row.object_id == str(qa_campus.id)
    assert row.after_hash is not None, "the audit row records no after-state hash"
    assert row.occurred_at is not None
    qa_authorisation.refresh_from_db()
    assert qa_authorisation.authorised_by_human == "A Named Human"
    checked, _head = verify_audit_chain()
    assert checked >= 1


def test_closing_the_gate_closes_it_and_revokes_the_authorisation(
    qa_campus, qa_authorisation
):
    """ADR-002 §4.1(b): "Closing discovery again is one command and writes a
    `revoked_at`." Closing must be reversible-by-reopening only through the
    checklist, so the authorisation is revoked, not left armed."""
    _run("open_discovery", campus=qa_campus.slug)
    _run("close_discovery", campus=qa_campus.slug, reason="QA test")
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None
    with pytest.raises(GateClosed):
        assert_discovery_open(qa_campus)
    qa_authorisation.refresh_from_db()
    assert qa_authorisation.revoked_at is not None
    assert qa_authorisation.revoked_reason == "QA test"
    assert AuditLog.objects.filter(action="discovery.close").exists()
    # And re-opening now needs a fresh authorisation from a named human.
    with pytest.raises(CommandError):
        _run("open_discovery", campus=qa_campus.slug)


def test_the_audit_chain_verifies_after_a_full_open_and_close_cycle(
    qa_campus, qa_authorisation
):
    """TASKS §2 S0 "done when ... `verify_audit_chain` passes", exercised over
    rows the gate commands wrote rather than rows a test wrote."""
    _run("open_discovery", campus=qa_campus.slug)
    _run("close_discovery", campus=qa_campus.slug, reason="QA cycle")
    out = _run("verify_audit_chain")
    assert "audit chain OK" in out
    assert AuditLog.objects.count() >= 2


# --------------------------------------------------------------------------
# 4. a closed campus exposes seed rows only
# --------------------------------------------------------------------------


def test_a_closed_campus_restricts_a_queryset_to_seed_rows(qa_campus, qa_city, qa_entity):
    """ADR-002 §4.1(c)'s predicate: `(:discovery_open OR is_seed)`.

    The real subject of this property is `listings`, which slice S2 creates, so
    this exercises the predicate against an annotated queryset instead: the rows
    marked `is_seed` survive the filter on a closed campus and all rows survive
    on an open one. That verifies the filter, **not** the journey — the journey
    is `test_a_real_student_cannot_reach_a_real_listing` below, and it skips.
    """
    Campus.objects.create(city=qa_city, name="Seeded", slug="seed-row",
                          legal_entity=qa_entity)
    qs = Campus.objects.annotate(
        is_seed=Case(
            When(slug__startswith="seed-", then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )
    closed = list(restrict_when_gate_closed(qs, qa_campus).values_list("slug", flat=True))
    assert closed == ["seed-row"], (
        "a closed campus must expose seed rows only (ADR-002 §4.1(c)); "
        f"got {closed}"
    )

    qa_campus.discovery_enabled_at = timezone.now()
    opened = set(restrict_when_gate_closed(qs, qa_campus).values_list("slug", flat=True))
    assert {"seed-row", qa_campus.slug} <= opened


def test_scoping_is_not_the_gate_and_the_gate_is_not_scoping(qa_campus):
    """ADR-002 §2 and §4 are two mechanisms. `scoped()` answers "which campus",
    `assert_discovery_open` answers "is this campus open". A reader that calls
    only the first is still behind no gate, which is why every discovery path has
    to call both (API-CONTRACT §2.5 steps 6 and 7)."""

    class Actor:
        campus_id = qa_campus.id

    assert visible_campus_ids(Actor()) == [qa_campus.id]
    # Scoping happily returns the campus whose gate is shut.
    with pytest.raises(GateClosed):
        assert_discovery_open(qa_campus)


def test_system_actor_sees_every_active_campus_but_is_never_a_gate_reader(qa_campus):
    """`apps/core/scoping.py`'s SYSTEM sentinel is not campus-scoped. The gate
    still applies to anything it reads on a student's behalf, so this records
    that SYSTEM's breadth is deliberate and bounded by `active`."""
    assert qa_campus.id in visible_campus_ids(SYSTEM)
    qa_campus.active = False
    qa_campus.save(update_fields=["active"])
    assert qa_campus.id not in visible_campus_ids(SYSTEM)


# --------------------------------------------------------------------------
# 5. behaviours the contracts do not specify — reported, not failed
# --------------------------------------------------------------------------


def test_regression_an_inactive_campus_is_closed_on_both_paths(
    qa_campus, qa_authorisation
):
    """**REGRESSION for QA-S0 B1** — was a characterisation test of a
    specification silence, now the fixed behaviour, asserted on both halves.

    B1 measured that `campuses.active` and `discovery_enabled_at` were
    independent: a campus with `active=false` and a non-NULL
    `discovery_enabled_at` passed `assert_discovery_open`, so a student whose
    `campus_id` pointed at a deactivated campus was behind no gate.

    Both halves are now closed and both are asserted here, because they are
    enforced in different places and a fix to one would not catch a regression
    in the other:

    * the **read** path — `assert_discovery_open` requires `active`;
    * the **write** path — migration 0003's trigger refuses to open an inactive
      campus at all.

    The specification silence itself is unchanged: no document says deactivating
    a campus closes discovery. It stays routed to cto as B1, now as a wording
    item rather than an exposure.
    """
    _run("open_discovery", campus=qa_campus.slug)
    qa_campus.refresh_from_db()
    assert_discovery_open(qa_campus)  # open and active: no exception

    qa_campus.active = False
    qa_campus.save(update_fields=["active"])
    qa_campus.refresh_from_db()
    assert qa_campus.active is False
    assert qa_campus.discovery_enabled_at is not None, (
        "deactivating a campus is still just an `active` flip; the read check is "
        "the one that has to hold"
    )
    with pytest.raises(GateClosed) as exc:
        assert_discovery_open(qa_campus)
    assert exc.value.code == "GATE_CLOSED"
    assert exc.value.context.get("reason") == "campus_inactive", (
        "the refusal reason distinguishes an inactive campus from a closed gate, "
        f"which is what an audit of a 403 needs: {exc.value.context}"
    )


def test_regression_an_inactive_campus_cannot_be_opened(qa_campus, qa_authorisation):
    """**REGRESSION for QA-S0 B1**, the write half (migration 0003)."""
    qa_campus.active = False
    qa_campus.save(update_fields=["active"])
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            Campus.objects.filter(pk=qa_campus.pk).update(
                discovery_enabled_at=timezone.now()
            )
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None


def test_the_write_guard_refuses_an_insert_that_arrives_already_open(
    qa_city, qa_entity
):
    """Migration 0003, the INSERT half: a new campus is created closed.

    This is the route the UPDATE guard alone would not close — `INSERT INTO
    campuses (..., discovery_enabled_at) VALUES (..., now())` never performs an
    update, so a guard written only for UPDATE would have let the gate open at
    birth.
    """
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            Campus.objects.create(
                city=qa_city, name="Born Open", slug="born-open",
                legal_entity=qa_entity, discovery_enabled_at=timezone.now(),
            )
    assert not Campus.objects.filter(slug="born-open").exists()


def test_the_write_guard_always_permits_closing(qa_campus, qa_authorisation):
    """Migration 0003: setting the column to NULL is always permitted.

    The property that matters operationally: a campus that cannot be closed is a
    worse failure than one that was opened carelessly. Asserted with the
    authorisation **revoked first**, which is the state `close_discovery` leaves
    behind and the state in which a naive guard would refuse the close.
    """
    _run("open_discovery", campus=qa_campus.slug)
    GateAuthorisation.objects.filter(pk=qa_authorisation.pk).update(
        revoked_at=timezone.now(), revoked_reason="revoked before closing"
    )
    Campus.objects.filter(pk=qa_campus.pk).update(discovery_enabled_at=None)
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None


def test_the_write_guard_permits_an_unrelated_update_on_an_open_campus(
    qa_campus, qa_authorisation
):
    """A trigger that fires on every UPDATE to the table, rather than on a change
    to the guarded column, would make an open campus unrenameable. Asserted
    because `close_discovery` and S1's campus admin both update other columns.
    """
    _run("open_discovery", campus=qa_campus.slug)
    Campus.objects.filter(pk=qa_campus.pk).update(name="Renamed While Open")
    qa_campus.refresh_from_db()
    assert qa_campus.name == "Renamed While Open"
    assert qa_campus.discovery_enabled_at is not None


def test_the_write_guard_refuses_a_reopen_after_close_without_a_new_authorisation(
    qa_campus, qa_authorisation
):
    """The strongest property the trigger buys, and the one the command alone
    could not: after `close_discovery`, the authorisation is revoked, so **no
    code path at all** can reopen the campus until a named human writes a new
    `gate_authorisations` row.

    Before migration 0003 this was true of the command and false of the ORM.
    """
    _run("open_discovery", campus=qa_campus.slug)
    _run("close_discovery", campus=qa_campus.slug, reason="pilot paused")
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            Campus.objects.filter(pk=qa_campus.pk).update(
                discovery_enabled_at=timezone.now()
            )
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None


@pytest.mark.parametrize(
    "mutation,label",
    [
        ({"gate": "B"}, "a Gate B authorisation"),
        ({"scope_type": "GLOBAL", "scope_id": None}, "a GLOBAL authorisation"),
        ({"scope_id": 999999}, "another campus's authorisation"),
    ],
)
def test_the_write_guard_refuses_every_wrong_authorisation_shape(
    qa_campus, qa_entity, qa_evidence, mutation, label
):
    """The trigger's predicate is `gate='C' AND scope_type='CAMPUS' AND
    scope_id=NEW.id AND revoked_at IS NULL`. Each conjunct is attacked on its
    own, because a trigger that checked only `gate='C'` would let one campus's
    MoU open every campus — and Gate C1 is a per-campus signed MoU.
    """
    fields = dict(
        gate="C", scope_type="CAMPUS", scope_id=qa_campus.id,
        legal_entity=qa_entity, evidence=qa_evidence,
        authorised_by_human="A Named Human",
    )
    fields.update(mutation)
    GateAuthorisation.objects.create(**fields)
    with pytest.raises(DatabaseError), transaction.atomic():
        Campus.objects.filter(pk=qa_campus.pk).update(
            discovery_enabled_at=timezone.now()
        )
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None, f"{label} opened the gate"


def test_the_write_guard_raises_rather_than_silently_not_persisting(
    qa_campus
):
    """**REGRESSION for QA-S0 F3**, and a property worth asserting separately.

    A guard that silently dropped the write would leave application code
    believing the gate was open. The guard fails loud, the column stays NULL,
    and no `audit_log` row is written — so the failure is visible to the caller
    and leaves no trace suggesting the gate ever opened.

    Caught as `django.db.DatabaseError`: SQLite's `RAISE(ABORT)` surfaces as
    `IntegrityError` and PostgreSQL's `RAISE EXCEPTION` as `InternalError`
    (ENGINE-DIVERGENCE §3.8).
    """
    audit_before = AuditLog.objects.count()
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            Campus.objects.filter(pk=qa_campus.pk).update(
                discovery_enabled_at=timezone.now()
            )
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None
    assert AuditLog.objects.count() == audit_before


def test_regression_an_incomplete_authorisation_cannot_be_created_at_all(
    qa_campus, qa_entity
):
    """**REGRESSION for QA-S0 F8** — the finding, re-run as the fixed behaviour.

    F8 measured that `GateAuthorisation.objects.create(gate='C',
    scope_type='CAMPUS', scope_id=campus.id, evidence={},
    authorised_by_human='')` followed by an ORM update **opened the gate** with
    an empty checklist, an unnamed authoriser and no `audit_log` row — because
    migration 0003's trigger asked only whether an authorisation existed.

    Migration 0005 moves ADR-002 §4.1(b)'s evidence checklist into the database.
    The exact DDL F8 used now fails at the INSERT, so the forged authorisation
    never exists and the gate stays shut. Both halves asserted.
    """
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            GateAuthorisation.objects.create(
                gate="C", scope_type="CAMPUS", scope_id=qa_campus.id,
                legal_entity=qa_entity, evidence={}, authorised_by_human="",
            )
    assert not GateAuthorisation.objects.exists()

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            Campus.objects.filter(pk=qa_campus.pk).update(
                discovery_enabled_at=timezone.now()
            )
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is None


def test_finding_the_gate_floor_still_does_not_check_whether_the_evidence_is_true(
    qa_campus, qa_entity
):
    """**FINDING B2, narrowed and still open.** Migration 0005 moved ADR-002
    §4.1(b)'s checklist into the database, so the floor now requires every
    evidence item to be *present and non-blank*. It does not — and a row trigger
    cannot — check whether any of them is *true*.

    Measured here: `campus_mou_ref="TODO"`, `breach_rehearsal_at="not yet"`,
    `counsel_engagement_ref="-"`, `notice_version_ids=["none"]` and
    `authorised_by_human="agent"` save cleanly and open the gate. `cin` is
    likewise any non-empty string, not a CIN.

    The migration says this itself, which is the right way to ship a partial
    control, and ADR-002 §4.2 already says the design makes the position
    auditable rather than correct. QA keeps the test because the go/no-go packet
    must not be read as stronger evidence than it is — **the gate records a
    claim by a named human; it does not verify one.** Two items are cheaply
    checkable and are not: `breach_rehearsal_at` is specified as a date, and
    `authorised_by_human` is the field the rule "no agent writes this row" rests
    on.
    """
    from apps.core.models import GateAuthorisation as GA

    GA.objects.create(
        gate="C", scope_type="CAMPUS", scope_id=qa_campus.id,
        legal_entity=qa_entity,
        evidence={
            "counsel_engagement_ref": "-",
            "takedown_sop_ref": "TODO",
            "oncall_rota_ref": "n/a",
            "breach_rehearsal_at": "not yet",
            "campus_mou_ref": "TODO",
            "notice_version_ids": ["none"],
        },
        authorised_by_human="agent",
    )
    _run("open_discovery", campus=qa_campus.slug)
    qa_campus.refresh_from_db()
    assert qa_campus.discovery_enabled_at is not None  # the finding


# --------------------------------------------------------------------------
# 6. the journey this slice cannot reach
# --------------------------------------------------------------------------


def test_a_real_student_cannot_reach_a_real_listing(engine):
    pytest.skip(
        f"NOT VERIFIABLE IN S0 (engine={engine}): the charter's gate test — "
        "'a real (non-seed) student on a campus with discovery_enabled_at IS "
        "NULL sees no listing data anywhere' (PRD AC-M6.1, JOURNEYS J11 step 1) "
        "— needs `users` (S1) and `listings` (S2). Neither table exists at the "
        "end of S0, so there is no real student and no listing to hide. The "
        "S0-verifiable halves are the gate guard and the seed predicate above; "
        "the journey itself is S3's QA item in TASKS §2."
    )


def test_a_closed_campus_never_notifies_a_real_student(engine):
    pytest.skip(
        f"NOT VERIFIABLE IN S0 (engine={engine}): TASKS §2 S3's gate test on "
        "`requests.match_scan` needs `notifications` and `book_requests` (S3, "
        "S2). The job registry exists in S0 but no handler can cross a gate yet."
    )
