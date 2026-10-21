"""Tenant scoping and the discovery gate — ADR-002 §2 and §4.

One helper, used everywhere. Every service function that reads tenant data
takes an `actor` and calls `scoped()`. Views and API handlers never touch the
ORM, so this is the only place scoping can be forgotten, and
tests/unit/test_scoping.py fails CI if a tenant-scoped model lacks the keys or
the leading index.
"""

import logging

from .errors import GateClosed
from .models import Campus

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
