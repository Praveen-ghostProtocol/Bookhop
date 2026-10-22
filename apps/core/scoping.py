"""Tenant scoping and the discovery gate — ADR-002 §2 and §4.

One helper, used everywhere. Every service function that reads tenant data
takes an `actor` and calls `scoped()`. Views and API handlers never touch the
ORM, so this is the only place scoping can be forgotten, and
tests/unit/test_scoping.py fails CI if a tenant-scoped model lacks the keys or
the leading index.
"""

import logging

from django.db import models

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
    "apps/listings/jobs.py": "the retention purge (DATA-MODEL §10.2)",
    "apps/listings/staff.py": "the staff moderation surface (API-CONTRACT §5.7)",
}

#: Paths that may **never** be allow-listed, whatever a future slice wants.
#: ADR-002 §4's gate is a control on discovery reads, so a discovery read that
#: needs `all_objects` is a discovery read that is bypassing the gate.
ALL_OBJECTS_FORBIDDEN_PREFIXES = ("apps/discovery/",)
