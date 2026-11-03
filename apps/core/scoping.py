"""Tenant scoping and the launch gates — ADR-002 §2 and §4, A-35.

One helper, used everywhere. Every service function that reads tenant data
takes an `actor` and calls `scoped()`. Views and API handlers never touch the
ORM, so this is the only place scoping can be forgotten, and
tests/unit/test_scoping.py fails CI if a tenant-scoped model lacks the keys or
the leading index.

**The gate guards live here, all of them**, which is the point of putting
`assert_real_account_allowed` in this file rather than in `apps.accounts`:
`grep -rn "def assert_" apps/` is the measurement CLOSED-TEST.md §1 and A-35
both used to find that Gate B had no guard, and the third guard should be
found by the same grep that found its absence.
"""

import logging
from datetime import datetime, time, timezone as dt_timezone

from django.db import models
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from .errors import GateClosed
from .models import Campus, GateAuthorisation

#: Gate refusals are a security-stream event: they are the audit answer to
#: "could a real student reach a listing before Gate C?" (ADR-002 §4.2).
log = logging.getLogger("bookhop.security")

#: The sentinel actor for job-runner and management-command work. SYSTEM is not
#: campus-scoped; it is also never a discovery reader, so it never reaches the
#: gate.
SYSTEM = "SYSTEM"

#: Every table that carries campus_id + city_id, from ADR-002 §2. Models land
#: slice by slice; test_scoping walks the ones that exist and asserts the keys,
#: and fails if this list names a model that exists without them.
TENANT_SCOPED_MODELS = [
    # (app_label, model_name, slice that creates it)
    ("accounts", "User", "S1"),
    ("accounts", "UserTombstone", "S1"),
    ("catalog", "PrescribedText", "S2"),
    ("listings", "Listing", "S2"),
    ("listings", "ListingPhoto", "S2"),
    ("listings", "BookRequest", "S2"),
    ("discovery", "SearchEvent", "S3"),
    ("transfers", "Transfer", "S4"),
    ("transfers", "HandoverPoint", "S5"),
    ("safety", "Report", "S6"),
    ("safety", "Dispute", "S6"),
    ("safety", "Grievance", "S6"),
    ("safety", "SafetyIncident", "S6"),
    ("support", "SupportTicket", "S6"),
    ("notify", "Notification", "S7"),
    # threads/messages are S5 and live in apps.transfers per API-CONTRACT §5.5
    ("transfers", "Thread", "S5"),
    ("transfers", "Message", "S5"),
]


def visible_campus_ids(actor):
    """The campuses this actor may read tenant data from.

    Today: exactly one. ADR-002 §5 widens this by data (`visibility_scope`),
    never by a schema change.
    """
    if actor is SYSTEM:
        return list(Campus.objects.filter(active=True).values_list("id", flat=True))
    campus_id = getattr(actor, "campus_id", None)
    if campus_id is None:
        return []
    return [campus_id]


def scoped(qs, actor):
    """Restrict `qs` to the actor's visible campuses. ADR-002 §2."""
    return qs.filter(campus_id__in=visible_campus_ids(actor))


def assert_discovery_open(campus):
    """ADR-002 §4.1(a). NULL `discovery_enabled_at` means closed.

    Every discovery read path begins with this call: search, listing index,
    listing detail of a listing you do not own, and the `book_requests` index.

    `active` is required too. QA-S0 B1 found that an `active=false` campus could
    still have an open gate, because nothing looked at `active`: a student whose
    `campus_id` points at a deactivated campus passed every check. No document
    says deactivating a campus closes discovery — that silence is routed to cto
    — but the only safe reading of "this campus is switched off" is that its
    listings are not browsable, and closing the read path costs one condition.
    The write half is in migration 0003 (an inactive campus cannot be opened);
    deactivating an already-open campus is still just an `active` flip, which is
    why the read check is the one that matters.
    """
    if campus is None or campus.discovery_enabled_at is None or not campus.active:
        slug = getattr(campus, "slug", None)
        reason = "no_campus" if campus is None else (
            "gate_closed" if campus.discovery_enabled_at is None else "campus_inactive"
        )
        log.info("gate.refused", extra={"campus": slug, "reason": reason})
        raise GateClosed("Listings are not open on this campus yet.", campus=slug, reason=reason)


# --- Gate B: one real person holds an account (B9′, A-35) ------------------

#: ADR-002 §4.1(b) scopes Gate C **per campus**. Gate B is *"one real student
#: holds an account"* (`ops/INCORPORATION-AND-BLOCKERS.md` §3.3) and there is no
#: campus in that sentence, so the row is GLOBAL. CLOSED-TEST.md §2.6 measured
#: that `gate='B', scope_type='GLOBAL'` is already expressible against the
#: existing CHECK constraints: this guard needs no enum change and no migration.
GATE_B_SCOPE = {"gate": "B", "scope_type": "GLOBAL"}

#: **The Gate B evidence set, scope-typed to shape 1** (D-072 / A-37,
#: `CLOSED-TEST.md` §4.1). A-35 left this list empty on purpose, because the
#: founder had not chosen between the two shapes §4 specifies; D-072 chose
#: shape 1 — *friends list, search, browse and message, and no purchase
#: completes* — so the set is now decidable and is decided here, once.
#:
#: It is **four lists rather than one** because the four are checked by
#: different rules, and a flat list gets edited the day one entry misfires
#: (`CLAUDE.md` rule 11): the bounds carry typed values (one of which is
#: legitimately `False`, so presence is `in`, never truthiness), the refs are
#: free text that must contain a visible character, the notice ids must
#: *resolve*, and the legal-entity fields live on another table.
#:
#: `open_discovery.EVIDENCE_KEYS` / `LEGAL_ENTITY_FIELDS` stay Gate C's and are
#: untouched. Nothing here is a copy of them — Gate B's set and Gate C's set
#: are different sets, not two statements of one rule — and the one thing the
#: two gates genuinely share, *"is this evidence actually present?"*, is
#: imported from there rather than restated.
GATE_B_BOUNDS = ("participant_ceiling", "closed_test_expires_at", "completes_purchases")

#: Evidence that is a reference to something outside the database.
#:
#: **`incident_runbook_ref` was missing from this tuple for one commit** while
#: `CLOSED-TEST.md` §4.1 listed it as required, which is the plainest form of
#: `CLAUDE.md` rule 9's defect: a document naming a control the code does not
#: have. `test_the_required_set_is_the_documents_set` now derives the whole set
#: from §4.1's own table, so the two cannot disagree again without a red test.
GATE_B_EVIDENCE_REFS = (
    "notice_version_ids", "takedown_sop_ref", "escalation_contact_ref",
    "incident_runbook_ref",
)

#: The notice kinds `evidence.notice_version_ids` must actually resolve to.
#: **PRIVACY and TERMS only.** `SELLER_TERMS` carries the r.5(2) seller
#: undertaking, which is an E-Commerce Rules artefact; at shape 1 nothing is
#: sold, and requiring it would assert a relationship the test does not create
#: (A-37). This is the one gate item verifiable end to end in the database
#: (README §7) and shrinking the gate does not cost that.
GATE_B_NOTICE_KINDS = ("PRIVACY", "TERMS")

#: Read from the authorisation's **own** legal entity, for the reason
#: `open_discovery.checklist` gives: evidence belonging to a different entity
#: from the one that was authorised is not this row's evidence.
#:
#: **Two tuples, not one, because they are two obligations under two
#: instruments** and the refusal has to say which (`CLAUDE.md` rule 11 — a flat
#: list gets edited when one entry misfires, so each entry carries its own
#: match rule). Collapsing them would give an operator reading
#: `gate_b_grievance_officer_missing` in the security log the wrong statute to
#: go and read.
GATE_B_GRIEVANCE_FIELDS = (
    "grievance_officer_name", "grievance_officer_email", "grievance_officer_phone",
)

#: CERT-In Directions 2022, Direction (v). **`cert_in_poc_*` was missing from
#: the gate for one commit** although §4.1 lists it and the columns have
#: existed since migration 0001 — §4.1 is explicit that it *"replaces
#: `breach_rehearsal_at`"* because *"the obligation is the 6-hour
#: capability"*, and a 6-hour reporting capability with no named point of
#: contact is not a capability.
GATE_B_CERT_IN_FIELDS = (
    "cert_in_poc_name", "cert_in_poc_email", "cert_in_poc_phone",
)

#: One name for every `legal_entities` column Gate B reads, since the document
#: test and any future reader want the whole set and neither should rebuild it
#: by concatenating halves.
GATE_B_LEGAL_ENTITY_FIELDS = GATE_B_GRIEVANCE_FIELDS + GATE_B_CERT_IN_FIELDS

#: **The other side of the split, as a row** (`CLAUDE.md` rule 10's corollary).
#: These are required at shape 2 and **cannot exist at shape 1** — there is no
#: company — so a gate that demanded them would be the `campus_mou_ref` defect
#: again: a criterion that cannot be satisfied. Asserted absent by
#: `test_gate_b_account_creation.py`, so a later widening is a red test rather
#: than a quiet one.
GATE_B_NOT_ASSERTED = (
    "cin", "incorporation_date", "inc20a_filed_at",
    # §4.1's "Not asserted" row names this fourth, and §1.1 is the finding
    # that it is **unsatisfiable at this scope**: there is no campus MOU for a
    # test among personal friends. It belongs on this side of the split for the
    # same reason as the other three.
    "campus_mou_ref",
)


def _live_gate_b_row():
    """The Gate B authorisation in force, or None. **Latest row wins.**

    `gate_authorisations` is append-only, so superseding an authorisation means
    writing a new row — the expiry refusal says exactly that — and the row in
    force is therefore the most recent one.

    **The `id` tiebreak is load-bearing, not tidiness.** `authorised_at`
    defaults to `timezone.now()`, whose granularity on the development machine
    was measured at ~1 ms (199,946 of 200,000 consecutive reads returned an
    identical value), so two rows written in the same millisecond tie and the
    ordering was undefined. Measured: with a fixture row and a test row written
    back to back, 21 of 40 runs tied, and **in all 21 the database returned the
    fixture row**, silently applying a different ceiling. That is A-36(c)'s
    flaky guard, and a guard on a legal gate that answers differently to the
    same data is worse than a missing one, because it is re-run until green.
    """
    return (
        GateAuthorisation.objects.filter(revoked_at__isnull=True, **GATE_B_SCOPE)
        .order_by("-authorised_at", "-id")
        .first()
    )


def _gate_b_refusal(reason, message, detail):
    """One refusal shape, so the security stream reads like the Gate C one."""
    log.info("gate.refused", extra={"campus": None, "reason": reason})
    return GateClosed(message, reason=reason, detail=detail)


def _as_aware_datetime(value):
    """A JSON string as an aware datetime, or None if it is not one.

    A bare date is read as **midnight at the start of that day, UTC**, which
    expires the test marginally early. That is the fail-closed direction and it
    is the only reason a date is accepted at all.
    """
    if not isinstance(value, str):
        return None
    try:
        # Django's parsers return None for "not a date shape" but **raise**
        # ValueError for a well-formed shape that is not a real date, e.g.
        # "2027-13-45". Both are the same answer to this function, and the
        # uncaught raise would have been a 500 on a path whose whole job is to
        # refuse cleanly.
        parsed = parse_datetime(value)
        if parsed is None:
            day = parse_date(value)
            parsed = datetime.combine(day, time.min) if day is not None else None
    except ValueError:
        return None
    if parsed is None:
        return None
    return parsed if timezone.is_aware(parsed) else parsed.replace(tzinfo=dt_timezone.utc)


def assert_real_account_allowed(*, is_seed, now=None):
    """B9′ / A-35. A real account needs a live, signed, bounded, unexpired Gate B row.

    `ops/INCORPORATION-AND-BLOCKERS.md` §3.3 B9′: *"a `gate_authorisations` row
    with `gate='B'`, and real account creation refused without it"*. Until this
    function existed nothing refused a real account, and **nothing ever told us**
    — an absent gate and a clean gate both produce no refusal (A-35).

    **Both sides are rows.** `is_seed=True` returns, with no row and no
    database read: ADR-002 §4.1(c)'s seed/real split is what makes building
    before the gate lawful, and it is the reason this takes the flag rather
    than being called only on the path we happen to remember. `seed_demo` calls
    it with `True` and `request_magic_link` with `False`, so both branches are
    live production call sites rather than one branch plus a test.

    Raises `GateClosed`. Every refusal carries a distinct `reason` and a
    distinct operator `detail`; the tests assert that text, never the exception
    type alone (`CLAUDE.md` rule 10, sixth disguise).

    **The caller still answers 202** on the magic-link path, exactly as it does
    for `EmailDomainNotRecognised` — a different response would be an
    account-enumeration oracle (API-CONTRACT §5.1).
    """
    if is_seed:
        return None

    # Imported here, not at module scope: `open_discovery` imports
    # `apps.core.services`, which imports this module. One definition of
    # "is this a name?" (`CLAUDE.md` rule 11) is worth a function-local import.
    from apps.accounts.models import NoticeVersion, User
    from apps.core.management.commands.open_discovery import _present, has_visible_character

    now = now or timezone.now()
    auth = _live_gate_b_row()
    if auth is None:
        raise _gate_b_refusal(
            "no_gate_b_authorisation",
            "BookHop is not open for sign-ups yet.",
            "No live gate_authorisations row with gate='B', scope_type='GLOBAL'. "
            "B9′ (ops/INCORPORATION-AND-BLOCKERS.md §3.3): a named human authorises "
            "the first real account. No agent writes that row.",
        )

    if not has_visible_character(auth.authorised_by_human or ""):
        raise _gate_b_refusal(
            "gate_b_unsigned",
            "BookHop is not open for sign-ups yet.",
            f"gate_authorisations id={auth.id} carries no named human in "
            "authorised_by_human. A smaller gate is still a named human's signature "
            "(CLOSED-TEST.md §4.1).",
        )

    evidence = auth.evidence or {}
    for key in GATE_B_BOUNDS:
        if key not in evidence:
            raise _gate_b_refusal(
                "gate_b_unbounded",
                "BookHop is not open for sign-ups yet.",
                f"gate_authorisations id={auth.id} is missing evidence.{key}. A-35: a "
                "reduced gate not bounded by the words that justified it is a permanent "
                "downgrade wearing a temporary label.",
            )

    expires_at = _as_aware_datetime(evidence["closed_test_expires_at"])
    if expires_at is None:
        raise _gate_b_refusal(
            "gate_b_expiry_unreadable",
            "BookHop is not open for sign-ups yet.",
            f"gate_authorisations id={auth.id} has evidence.closed_test_expires_at = "
            f"{evidence['closed_test_expires_at']!r}, which is not a date or a timestamp. "
            "A clock that cannot be read is a clock nothing reads.",
        )
    if now >= expires_at:
        raise _gate_b_refusal(
            "gate_b_expired",
            "The closed test has ended.",
            f"gate_authorisations id={auth.id} expired at {expires_at.isoformat()}; it is "
            f"now {now.isoformat()}. A new named-human row is needed, not an edit — "
            "gate_authorisations is append-only (migration 0002).",
        )

    ceiling = evidence["participant_ceiling"]
    if isinstance(ceiling, bool) or not isinstance(ceiling, int) or ceiling < 1:
        raise _gate_b_refusal(
            "gate_b_ceiling_unreadable",
            "BookHop is not open for sign-ups yet.",
            f"gate_authorisations id={auth.id} has evidence.participant_ceiling = "
            f"{ceiling!r}, which is not a positive integer.",
        )

    completes = evidence["completes_purchases"]
    if not isinstance(completes, bool):
        raise _gate_b_refusal(
            "gate_b_completion_flag_unreadable",
            "BookHop is not open for sign-ups yet.",
            f"gate_authorisations id={auth.id} has evidence.completes_purchases = "
            f"{completes!r}, which is not true or false. D-072 is a shape the "
            "founder chose; it is not inferable from a string.",
        )

    for key in GATE_B_EVIDENCE_REFS:
        if not _present(evidence.get(key)):
            raise _gate_b_refusal(
                "gate_b_evidence_missing",
                "BookHop is not open for sign-ups yet.",
                f"gate_authorisations id={auth.id} has no evidence.{key}. "
                "CLOSED-TEST.md §4.1 lists it in the shape-1 set: a reduced gate "
                "is smaller, not emptier.",
            )

    # **The one item verifiable end to end in the database**, so it is verified
    # rather than counted. Non-integer entries simply fail to resolve, which is
    # the fail-closed direction and needs no second refusal.
    raw_ids = evidence["notice_version_ids"]
    raw_ids = raw_ids if isinstance(raw_ids, (list, tuple)) else []
    ids = [i for i in raw_ids if isinstance(i, int) and not isinstance(i, bool)]
    published = set(
        NoticeVersion.objects.filter(id__in=ids).values_list("kind", flat=True)
    )
    unpublished = [kind for kind in GATE_B_NOTICE_KINDS if kind not in published]
    if unpublished:
        raise _gate_b_refusal(
            "gate_b_notices_unpublished",
            "BookHop is not open for sign-ups yet.",
            f"gate_authorisations id={auth.id} has evidence.notice_version_ids = "
            f"{evidence['notice_version_ids']!r}, which resolves to no "
            f"notice_versions row of kind {', '.join(unpublished)}. SPDI r.4 and IT "
            "Rules r.3(1)(a) bind at any scale (CLOSED-TEST.md §3 row 5).",
        )

    # **Two loops, each naming its own instrument.** The refusal code is what
    # an operator greps for and what the security log carries, so a missing
    # CERT-In point of contact must not report itself as a grievance-officer
    # problem and send someone to the wrong statute.
    entity = auth.legal_entity
    for fields, reason, basis in (
        (
            GATE_B_GRIEVANCE_FIELDS,
            "gate_b_grievance_officer_missing",
            "IT Rules r.3(2)(a) is a functional test with no threshold and no "
            "company requirement — the clearest 'binds at any scale' item in "
            "CLOSED-TEST.md §3.",
        ),
        (
            GATE_B_CERT_IN_FIELDS,
            "gate_b_cert_in_poc_missing",
            "CERT-In Directions 2022 bind 'service providers, intermediaries, "
            "data centres, body corporate' with no scale threshold "
            "(CLOSED-TEST.md §2.4). §4.1 requires this in place of a breach "
            "rehearsal because the obligation is the 6-hour reporting "
            "capability, and a capability with no named point of contact is "
            "not one.",
        ),
    ):
        for field in fields:
            if not _present(getattr(entity, field, None)):
                raise _gate_b_refusal(
                    reason,
                    "BookHop is not open for sign-ups yet.",
                    f"legal_entities id={auth.legal_entity_id} has no {field}. {basis}",
                )

    # Tombstoned accounts are excluded: a participant who left frees their
    # place, and counting them would make the ceiling a high-water mark rather
    # than a headcount.
    #
    # ponytail: read-then-create, so two simultaneous sign-ups can both pass at
    # the ceiling. Ceiling: the test overshoots by at most the number of
    # concurrent requests — at twelve friends, by one. Upgrade path: a partial
    # unique index or a SELECT … FOR UPDATE on the authorisation row, the day
    # the number this bounds is one anybody is counting precisely.
    taken = User.all_objects.filter(is_seed=False).exclude(status="TOMBSTONED").count()
    if taken >= ceiling:
        raise _gate_b_refusal(
            "gate_b_ceiling_reached",
            "The closed test is full.",
            f"gate_authorisations id={auth.id} caps the closed test at {ceiling} "
            f"participants and {taken} real accounts exist.",
        )
    return auth


def assert_purchase_completion_allowed(*, to_status):
    """A-37 / D-072. No purchase completes during the closed test.

    **This is a legal position, not a product decision.** `CLOSED-TEST.md` §2.3
    establishes that the Consumer Protection (E-Commerce) Rules carry no
    turnover, user-count or transaction threshold, so at shape 2 a company is
    required at twelve users exactly as at two thousand. Shape 1 — nothing
    completes — is what takes incorporation off the critical path, and until
    now it was true only **by absence**: the transition map permits
    `RESERVED → CLOSED_TRANSFERRED` and nothing called into either state
    because the slice that would had not been written. The slice that builds
    reserve-and-complete would have moved this company into shape 2 with
    nobody deciding to, and `CLOSED-TEST.md` would still have read true.

    So the position is a value a named human signed, and this is the refusal
    that reads it. Called from `listings.services._transition` for A-29 §2's
    reason: every *transition* goes through that one function, so reserve,
    relist and every edge a later slice adds are one predicate rather than one
    check per caller.

    **It is not true that every write of `listings.status` goes through
    `_transition`, and an earlier draft of this docstring said it was.**
    `tests/unit/test_purchase_completion_gate.py` enumerates the writers and
    found three others on its first run: `create_listing` inserts at `DRAFT`,
    `seed_demo._seed_listings` inserts demo rows at a literal status, and
    `accounts.services._detach_listing_rows` withdraws an erased seller's open
    listings without consulting any state machine, deliberately, because an
    erasure must not be refusable. None of the three can write a completion
    status and all three are asserted unable to — which is the enumeration
    doing the work the sentence above was doing on trust (`CLAUDE.md` rule 9:
    a claim quantified over "every path" names the paths it was measured
    against).

    **No live row refuses.** Shape 1 is the fail-closed direction, and the
    absence of an authorisation is not an authorisation.

    Expiry is deliberately **not** re-read here: an expired row stops new
    accounts, which is `assert_real_account_allowed`'s job, and a row that says
    purchases complete exists only once the founder has decided shape 2 — at
    which point the question this guard asks has a different answer anyway.
    """
    auth = _live_gate_b_row()
    completes = (auth.evidence or {}).get("completes_purchases") if auth else None
    if completes is True:
        return auth
    raise _gate_b_refusal(
        "closed_test_completes_no_purchase",
        "Books are not changing hands through BookHop during the closed test.",
        (
            f"D-072 / A-37: listings.status -> {to_status!r} is a completion state and "
            + (
                f"gate_authorisations id={auth.id} says evidence.completes_purchases = "
                f"{completes!r}."
                if auth is not None
                else "no live gate_authorisations row with gate='B', scope_type='GLOBAL' "
                     "authorises one."
            )
            + " Completing a purchase makes BookHop a marketplace e-commerce entity "
            "under the Consumer Protection (E-Commerce) Rules, which have no "
            "user-count threshold. That is a founder decision, not a slice."
        ),
    )


def restrict_when_gate_closed(qs, campus):
    """ADR-002 §4.1(c): a closed campus exposes seed rows only.

    The SQL in the ADR is `(:discovery_open OR is_seed)`. This is that predicate,
    written once so no caller reimplements it. Applies to any queryset over a
    model with an `is_seed` column.

    Callers still call `assert_discovery_open` first: a *real* student on a
    closed campus gets 403 GATE_CLOSED and never reaches a query. This filter is
    the second line, for staff and seed actors who legitimately read a closed
    campus and must see seed rows only.

    Applied to a model with no `is_seed` column this raises `FieldError` rather
    than returning everything, which is the behaviour the test asserts: a gate
    filter that silently no-ops is worse than one that is absent.
    """
    if campus is not None and campus.discovery_enabled_at is not None and campus.active:
        return qs
    return qs.filter(is_seed=True)


# --- the gated default manager (ADR-002 §2.3, S2) --------------------------


def gate_open_or_seed_q():
    """The gate rule as a row-wise predicate. **One definition** (rule 10).

    `restrict_when_gate_closed` asks the same question about the *actor's*
    campus, which it is handed. A manager has no actor, so it asks it of the
    **row's own** campus — which is the only form of the question a manager can
    ask, and the correct one for a `visibility_scope='CAMPUS'` row.

    A row is visible when it is seed data, or when the campus it belongs to has
    a gate that is open **and** is active. `active` is here for the reason
    `assert_discovery_open` has it (QA-S0 B1): nothing else looked at it, and
    "this campus is switched off" has to mean its rows are not browsable.
    """
    return models.Q(is_seed=True) | models.Q(
        campus__discovery_enabled_at__isnull=False, campus__active=True
    )


class GatedManager(models.Manager):
    """ADR-002 §2.3. The default manager on every model carrying `is_seed`.

    **It sits UNDERNEATH `assert_discovery_open`, never instead of it**, and
    that is the design point the ADR calls more important than the mechanism.
    A filtered manager makes a closed campus return **no rows**;
    `API-CONTRACT.md` §2.5 step 7 and §5.3 require a real student on a closed
    campus to receive `403 GATE_CLOSED`, and S3's three truths need *"not on
    your campus yet"* kept apart from *"we don't recognise that ISBN"*.
    Substituting one for the other does not simplify anything — **one filters
    rows, the other tells a student why there are none** — and it makes the
    legal gate invisible to the person it applies to. Deleting
    `assert_discovery_open` because this exists is a Code Review escalation,
    not a cleanup.

    Every model using it also declares `all_objects = models.Manager()` and
    `Meta.base_manager_name = "all_objects"`, so cascade deletes,
    `refresh_from_db`, `dumpdata` and related descriptors keep seeing every
    row. Without that line a filtering default manager silently breaks data
    integrity operations, which is a worse bug than the one it fixes —
    `tests/unit/test_scoping.py` asserts the line is present on each model and
    `tests/unit/test_gated_manager.py` asserts the behaviour it buys.

    # ponytail: one JOIN to `campuses` on every default query. Ceiling: a query
    # that would otherwise be a primary-key lookup becomes a join; at pilot
    # volume that is free, and `all_objects` is there for the paths that must
    # not join. Upgrade path: Postgres RLS (ADR-002 §6 step 2), which is the
    # only thing that closes raw SQL as well.
    """

    def get_queryset(self):
        return super().get_queryset().filter(gate_open_or_seed_q())


#: Where `all_objects` may legitimately be used (ADR-002 §2.3), as
#: `module path -> the reason`. **Enforced in CI** by
#: `tests/unit/test_scoping.py::test_all_objects_appears_only_in_allow_listed_call_sites`,
#: which greps `apps/**`. A new use outside this map fails the build.
#:
#: The ADR names five: *"fixtures, `seed_demo`, the staff/admin surface, the
#: retention purge and the metric exports."* **A sixth was added on a
#: measurement rather than an argument, and it is the one that matters:**
#: retrofitting `GatedManager` onto `User` gates **authentication**, because
#: `session_user` and `request_magic_link` both read `users` by identity on a
#: campus whose gate is lawfully closed — which is every campus before Gate C.
#: Measured: with the gate applied, a real (non-seed) student could not sign in
#: and `request_magic_link` tried to re-create their account, hitting the
#: unique index on `email`. S1's own "done when" — *"an adult can sign in by
#: email … and delete their account"* — would have been false.
#:
#: **Which other layer still catches a user-discovery read** (`CLAUDE.md`
#: rule 14, asked before the allowance rather than after): `scoped()` plus
#: `assert_discovery_open`, which are the control ADR-002 §4 actually names.
#: And there is nothing for the manager to have caught here: v1 has no user
#: directory, no member search and no discovery of people — ADR-002 §2.3 says
#: so itself when it explains why the retrofit was deferred out of S1. **The
#: gate is a discovery control; authentication is not discovery.** Raised to
#: cto in the slice note, because the retrofit instruction and §2.5's
#: sign-in-on-a-closed-campus requirement cannot both be met without this.
#: **The boundary that makes this list mean something is which app is NOT on
#: it.** Discovery — the one kind of read the gate exists for — lives in
#: `apps/discovery/**` (S3: `search_listings`, `get_listing`, the browse and
#: wanted indexes, API-CONTRACT §5.3). Nothing under that path is listed or
#: may be, so the first discovery read that types `all_objects` fails CI.
#: `test_gated_manager.py::test_no_discovery_module_is_ever_allow_listed`
#: asserts that forward, and is inverted per `CLAUDE.md` rule 10 so it starts
#: failing the day the app exists rather than skipping forever.
#:
#: `apps/listings/services.py` is listed and `apps/discovery/services.py`
#: will not be, which is the whole distinction: **this app reads the seller's
#: own rows and writes**, every function filtering by `seller_pseudonym`,
#: `requester_pseudonym`, a known primary key, or a staff check. None of them
#: is a read of other people's listings. That claim is checked, not asserted —
#: `test_every_all_objects_read_in_listings_is_owned_or_staff_gated`.
ALL_OBJECTS_ALLOWED = {
    "apps/accounts/sessions.py": "authentication — resolving the signed-in principal",
    "apps/accounts/services.py": (
        "authentication, identity and erasure: sign-in by email, the magic-link "
        "consume, and the erasure steps that must reach every row a student "
        "owns including the ones the gate hides"
    ),
    "apps/core/management/commands/seed_demo.py": "fixtures (ADR-002 §4.1(c))",
    "apps/listings/services.py": (
        "the seller's own rows and every write — no discovery read lives here; "
        "discovery is apps/discovery/** (S3) and is deliberately not listed"
    ),
    "apps/core/scoping.py": (
        "the Gate B participant ceiling (A-35) — it counts real accounts across "
        "every campus, including the ones a closed gate hides, and counting with "
        "a gated manager would undercount and under-enforce the cap. Not a read "
        "of anybody's data: a COUNT(*) with no row ever returned"
    ),
    "apps/listings/jobs.py": "the retention purge (DATA-MODEL §10.2)",
    "apps/listings/staff.py": "the staff moderation surface (API-CONTRACT §5.7)",
}

#: Paths that may **never** be allow-listed, whatever a future slice wants.
#: ADR-002 §4's gate is a control on discovery reads, so a discovery read that
#: needs `all_objects` is a discovery read that is bypassing the gate.
ALL_OBJECTS_FORBIDDEN_PREFIXES = ("apps/discovery/",)
