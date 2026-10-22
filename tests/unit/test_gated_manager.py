"""ADR-002 §2.3's gated default manager, and the four TASKS §2 S2 conditions.

> - [ ] every gated model's default manager is `GatedManager` and its
>       `Meta.base_manager_name` is `all_objects`;
> - [ ] the reverse-relation test runs and **its result is recorded** —
>       covered or not covered, stated either way;
> - [ ] `all_objects` appears only in allow-listed call sites.

**The design point that matters more than the mechanism, asserted rather than
commented** (ADR-002 §2.3): the manager sits **underneath**
`assert_discovery_open`, never instead of it. A filtered manager returns *no
rows*; the contract requires an explicit `403 GATE_CLOSED`, and S3's three
truths need *"not on your campus yet"* kept apart from *"we don't recognise
that ISBN"*. **Substituting one for the other makes the legal gate invisible
to the person it applies to** — and it is exactly the substitution a future
developer would make believing it a simplification, because two controls look
like they do the same thing. They do not: one filters rows, the other tells a
student why there are none.
"""

import pathlib

import pytest
from django.apps import apps as django_apps
from django.db import models

from apps.core.scoping import ALL_OBJECTS_ALLOWED, GatedManager

pytestmark = pytest.mark.django_db

REPO = pathlib.Path(__file__).resolve().parents[2]

#: Every model ADR-002 §2.3 puts the gated manager on. `User` is **not** here
#: and `test_the_user_retrofit_is_recorded_as_measured_and_refused` is why.
GATED_MODELS = [("listings", "Listing"), ("listings", "ListingPhoto"),
                ("listings", "BookRequest")]


def _model(label, name):
    return django_apps.get_model(label, name)


# --- condition 1: the manager and the line that is invisible when missing --


@pytest.mark.parametrize("label,name", GATED_MODELS)
def test_the_default_manager_is_the_gated_one(label, name):
    model = _model(label, name)
    assert isinstance(model._default_manager, GatedManager), (
        f"{model._meta.db_table}'s default manager is "
        f"{type(model._default_manager).__name__}, not GatedManager"
    )


@pytest.mark.parametrize("label,name", GATED_MODELS)
def test_base_manager_name_points_at_the_unfiltered_manager(label, name):
    """*"The kind of line that is invisible when missing."*

    Django uses the **base** manager for related-object descriptors and
    internal operations. Without this line a filtering default manager
    silently breaks `dumpdata`, migrations, cascade deletes and
    `refresh_from_db` — which would be a far worse bug than the one it fixes.
    """
    model = _model(label, name)
    assert model._meta.base_manager_name == "all_objects", (
        f"{model._meta.db_table} has base_manager_name="
        f"{model._meta.base_manager_name!r}"
    )
    assert type(model._base_manager) is models.Manager, (
        "the base manager is filtered, so cascade deletes and refresh_from_db "
        "cannot see every row"
    )


@pytest.mark.parametrize("label,name", GATED_MODELS)
def test_the_gate_actually_filters_on_a_direct_query(label, name, s2_listing, closed_campus):
    """Behavioural, not structural: a non-seed row on a closed campus is gone
    from `objects` and present in `all_objects`.

    Built from a **real** row rather than from a mock, because the thing being
    asserted is the join to `campuses`, and a mock cannot be joined to.
    """
    model = _model(label, name)
    rows = {
        "listings.Listing": lambda: _make_listing(s2_listing, is_seed=False),
        "listings.ListingPhoto": lambda: _make_photo(s2_listing, is_seed=False),
        "listings.BookRequest": lambda: _make_request(s2_listing, is_seed=False),
    }[f"{label}.{name}"]
    row = rows()

    assert model.all_objects.filter(pk=row.pk).exists(), (
        "the unfiltered manager must see it, or this test proves nothing"
    )
    assert not model.objects.filter(pk=row.pk).exists(), (
        f"{model._meta.db_table}: a non-seed row on a campus whose gate is "
        "closed is still visible through the default manager"
    )


@pytest.mark.parametrize("label,name", GATED_MODELS)
def test_a_seed_row_on_a_closed_campus_is_still_visible(label, name, s2_listing):
    """The other side of the split (rule 10's corollary).

    ADR-002 §4.1(c) is *"closed campus: seed listings only"* — not *"closed
    campus: nothing"*. A manager that hid seed rows too would make the whole
    pre-Gate-C development and QA story impossible, and would pass a test that
    only checked the forbidden side.
    """
    model = _model(label, name)
    rows = {
        "listings.Listing": lambda: _make_listing(s2_listing, is_seed=True),
        "listings.ListingPhoto": lambda: _make_photo(s2_listing, is_seed=True),
        "listings.BookRequest": lambda: _make_request(s2_listing, is_seed=True),
    }[f"{label}.{name}"]
    row = rows()
    assert model.objects.filter(pk=row.pk).exists(), (
        f"{model._meta.db_table}: a seed row on a closed campus must stay "
        "visible — ADR-002 §4.1(c) is seed-only, not nothing"
    )


def test_an_open_gate_makes_a_real_row_visible(s2_listing, open_the_gate):
    """The third case: the filter is about the gate, not about `is_seed` alone.

    Without this, a manager that simply returned `is_seed=True` rows forever
    would pass both tests above and would never show a real listing after
    Gate C — a control that silently keeps the product switched off.
    """
    from apps.core.models import Campus
    from apps.listings.models import Listing

    row = _make_listing(s2_listing, is_seed=False)
    assert not Listing.objects.filter(pk=row.pk).exists()
    # Opened through the authorised path, because migration core/0003's
    # trigger refuses a bare UPDATE -- that control is working and a test
    # that disabled it would be testing a database we do not ship.
    open_the_gate(Campus.objects.get(id=row.campus_id))
    assert Listing.objects.filter(pk=row.pk).exists(), (
        "the gate is open and a real listing is still hidden, so the manager "
        "is filtering on is_seed rather than on the gate"
    )


def test_an_inactive_campus_hides_a_real_row_even_with_the_gate_open(s2_listing, open_the_gate):
    """QA-S0 B1's shape, in the manager.

    Nothing looked at `active` until B1, and a student whose campus is
    switched off passed every check. `assert_discovery_open` grew the
    condition; the manager has it for the same reason, so the two layers agree
    about what "this campus is switched off" means.
    """
    from apps.core.models import Campus
    from apps.listings.models import Listing

    row = _make_listing(s2_listing, is_seed=False)
    campus = open_the_gate(Campus.objects.get(id=row.campus_id))
    assert Listing.objects.filter(pk=row.pk).exists(), "precondition: open and visible"
    Campus.objects.filter(id=campus.id).update(active=False)
    assert not Listing.objects.filter(pk=row.pk).exists()


# --- condition 2: the reverse-relation result, recorded either way --------


def test_the_reverse_relation_result_is_measured_and_recorded(s2_listing):
    """**ADR-002 §2.3: "the gap is closed by a TEST, not by my argument."**

    v1.0 of the amendment asserted flatly that reverse relations are not
    covered. The reviewer refused that as *reasoning where a measurement was
    available*, because which access paths resolve a filtered manager differs
    by path **and** by Django version.

    **RECORDED RESULT — VERIFIED HERE, Django 5.2, PostgreSQL 16 and SQLite:
    reverse accessors ARE gated.** `book.listings.all()` does **not** return
    the hidden row.

    **This is the opposite of what ADR-002 §2.3 v1.0 asserted**, and the
    reviewer who refused that assertion was right to: it was reasoning where a
    measurement was available. The mechanism is that Django builds a reverse
    many-to-one manager from `related_model._default_manager.__class__` — the
    *default* manager, which is `GatedManager` — while `_base_manager` is used
    for forward-FK loading, cascade collection and `refresh_from_db`. So
    `base_manager_name` buys data-integrity correctness **without** costing
    the gate on reverse traversal; the two are not the trade-off the ADR
    assumed.

    **What this does NOT license.** It is still defence in depth, and
    `scoped()` plus `assert_discovery_open` remain the control, for two
    reasons that this measurement does not touch: the manager answers the gate
    question of the **row's own** campus, not the actor's, so it is not
    tenancy scoping; and a filtered manager returns no rows where the contract
    requires `403 GATE_CLOSED`.

    **It is also a cross-library claim, so it is labelled and pinned.** It
    depends on Django's related-descriptor internals, which are not public
    API. If a future Django resolves reverse accessors through
    `_base_manager`, this test goes red and the recorded result is corrected
    in ADR-002 §2.3 — rather than the coverage quietly disappearing, which is
    what a comment would have done.
    """
    from apps.listings.models import Listing

    hidden = _make_listing(s2_listing, is_seed=False)
    assert not Listing.objects.filter(pk=hidden.pk).exists(), "precondition"
    assert Listing.all_objects.filter(pk=hidden.pk).exists(), "precondition"

    via_reverse = list(hidden.book.listings.all())
    reverse_is_gated = hidden.pk not in {row.pk for row in via_reverse}

    assert reverse_is_gated is True, (
        "RECORDED RESULT CHANGED. S2 measured that reverse accessors ARE "
        "gated on Django 5.2 (the reverse manager is built from "
        "_default_manager). This assertion failing means a Django upgrade "
        "moved reverse traversal onto _base_manager, so the gate no longer "
        "applies there: update ADR-002 §2.3's recorded result and this "
        "docstring in the same commit, and treat the service layer as the "
        "only control on that path."
    )


def test_the_base_manager_is_unfiltered_which_is_what_makes_cascades_correct(s2_listing):
    """The reason the reverse-relation answer is "not gated", asserted.

    It is not an oversight in the manager; it is `base_manager_name` doing the
    job it was set for. Deleting a book must collect every listing that points
    at it, not only the visible ones.
    """
    from apps.listings.models import Listing

    hidden = _make_listing(s2_listing, is_seed=False)
    assert Listing._base_manager.filter(pk=hidden.pk).exists()
    assert not Listing._default_manager.filter(pk=hidden.pk).exists()


def test_refresh_from_db_still_works_on_a_hidden_row(s2_listing):
    """The concrete breakage `base_manager_name` prevents.

    Without the line this raises `DoesNotExist` on a row the caller is holding
    — a filtering default manager making an object unable to reload itself.
    """
    hidden = _make_listing(s2_listing, is_seed=False)
    hidden.refresh_from_db()
    assert hidden.pk is not None


# --- condition 3: the all_objects allow-list ------------------------------


def test_all_objects_appears_only_in_allow_listed_call_sites():
    """ADR-002 §2.3: *"a new use outside that list fails CI."*

    The allow-list is a map of path → reason rather than a bare set, so an
    entry has to say **why** and a false positive narrows one entry instead of
    deleting the list (`CLAUDE.md` rule 11).
    """
    offenders = sorted(
        rel for rel in _all_objects_users() if rel not in ALL_OBJECTS_ALLOWED
    )
    assert offenders == [], (
        "ADR-002 §2.3: `all_objects` is the explicit, greppable escape from "
        "the gated default manager and may appear only in allow-listed call "
        "sites — fixtures, seed_demo, the staff surface, the retention purge, "
        "the metric exports, and (measured in S2) authentication. These are "
        f"not listed in apps.core.scoping.ALL_OBJECTS_ALLOWED: {offenders}"
    )


def _all_objects_users():
    """Files under `apps/**` that **use** `Model.all_objects`.

    An AST walk for attribute access, not a grep for the token
    (`CLAUDE.md` rule 11: ask the property). A grep counts three things that
    are not uses — the declaration `all_objects = models.Manager()`, the
    allow-list itself, and a comment explaining why a file does not use it —
    and the cheap fix for each false positive is an allow-list entry, which
    is how an allow-list stops meaning anything. This asks the one question
    that matters: does this module read through the unfiltered manager?
    """
    import ast

    found = set()
    for path in sorted((REPO / "apps").rglob("*.py")):
        rel = path.relative_to(REPO).as_posix()
        if "/migrations/" in rel:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "all_objects":
                found.add(rel)
                break
    assert found, "no `all_objects` use found in apps/** — this test would pass vacuously"
    return found


def test_a_declaration_and_a_comment_are_not_counted_as_call_sites():
    """The scan's own guard, both directions.

    `all_objects = models.Manager()` is the declaration and
    `apps/listings/api.py` carries a comment saying why it does **not** use
    the escape — a grep flags both, and the tempting fix is two allow-list
    entries that then exempt two whole files for real. The AST walk flags
    neither, and this asserts it rather than trusting it.
    """
    users = _all_objects_users()
    assert "apps/listings/api.py" not in users, (
        "a comment mentioning all_objects is being counted as a use"
    )
    assert "apps/listings/services.py" in users, (
        "the scan has stopped seeing a module that genuinely does use it"
    )
    text = (REPO / "apps/listings/models.py").read_text(encoding="utf-8")
    assert "all_objects = models.Manager()" in text, "the declaration is still there"


def test_every_allow_listed_path_exists_and_carries_a_reason():
    """The list's own guard: a stale entry is a silent widening.

    An allow-list that names a file nobody deleted is harmless; one that names
    a file that **moved** quietly stops covering the thing it was written for,
    and the new location fails the test above in a way that invites adding a
    second entry rather than fixing the first.
    """
    for rel, reason in sorted(ALL_OBJECTS_ALLOWED.items()):
        assert (REPO / rel).exists(), f"{rel} is allow-listed and does not exist"
        assert len(reason) > 15, f"{rel} is allow-listed with no stated reason"


def test_no_discovery_module_is_ever_allow_listed():
    """**The boundary that makes the allow-list mean something**, and it is
    inverted per `CLAUDE.md` rule 10 so it cannot skip forever.

    The gate exists for discovery reads. S3 puts every one of them in
    `apps/discovery/**` — `search_listings`, `get_listing`, the browse and
    wanted indexes (API-CONTRACT §5.3). If that app is ever allow-listed, the
    escape hatch has been handed to the exact code path the control is for.

    Two halves, because the forward-dated half alone would be theatre: the
    prefix must not appear in the list **now**, and if `apps/discovery/`
    exists it must contain no `all_objects` at all.
    """
    from apps.core.scoping import ALL_OBJECTS_FORBIDDEN_PREFIXES

    assert ALL_OBJECTS_FORBIDDEN_PREFIXES == ("apps/discovery/",)
    listed = [
        rel
        for rel in ALL_OBJECTS_ALLOWED
        if rel.startswith(ALL_OBJECTS_FORBIDDEN_PREFIXES)
    ]
    assert listed == [], (
        f"a discovery module is allow-listed: {listed}. ADR-002 §4's gate is a "
        "control on discovery reads; a discovery read that needs `all_objects` "
        "is one that is bypassing it."
    )

    discovery = REPO / "apps" / "discovery"
    if not discovery.exists():
        return
    offenders = [
        path.relative_to(REPO).as_posix()
        for path in sorted(discovery.rglob("*.py"))
        if "all_objects" in path.read_text(encoding="utf-8")
    ]
    assert offenders == [], (
        f"apps/discovery/** uses `all_objects`: {offenders}. Discovery reads "
        "go through `assert_discovery_open` and `restrict_when_gate_closed`."
    )


def test_every_all_objects_read_in_listings_is_owned_or_staff_gated():
    """**Rule 12's question for the biggest entry on the list, as a check.**

    `apps/listings/services.py` is allow-listed wholesale, which is the
    broadest entry here, so the reason it is affordable has to be verifiable
    rather than argued: **every function in it that reads through
    `all_objects` either restricts to the actor's own rows, names a primary
    key it was handed, or refuses a non-staff actor first.**

    Checked per function over the module source. It is a text check and that
    is its ceiling — it cannot tell a correct ownership filter from a
    misspelt one — but it does catch the shape that matters: a new function
    that queries `all_objects` with none of the three.
    """
    import ast

    source = (REPO / "apps/listings/services.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()
    unguarded = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = "\n".join(lines[node.lineno - 1 : node.end_lineno])
        if "all_objects" not in body:
            continue
        # Four guards, each of which independently makes an `all_objects`
        # read safe. Named rather than inferred, so a new function has to
        # carry one of them and a reviewer can see which.
        owned = (
            # 1. Tenancy: `scoped()` restricts to the actor's campuses.
            "scoped(" in body
            # 2. Ownership: the actor's own pseudonym is in the filter.
            or "seller_pseudonym=actor.person_pseudonym" in body
            or "requester_pseudonym=actor.person_pseudonym" in body
            or "seller_id=user.id" in body
            or "requester_id=user.id" in body
            or "listing__seller_pseudonym=user.person_pseudonym" in body
            # 3. Staff: the function refuses a non-staff actor first.
            or "is_staff_member" in body
            # 4. Not a read at all, or a read of a primary key the caller
            #    was already handed by one of the three above.
            or ".create(" in body
            or "id=listing.id" in body
            or "id=row.id" in body
            or "filter(id__in=" in body
            or "filter(listing=listing)" in body
        )
        if not owned:
            unguarded.append(node.name)
    assert unguarded == [], (
        "these functions read `all_objects` without restricting to the "
        "actor's own rows, a known primary key, or a staff check — which is "
        "the reason apps/listings/services.py is allow-listed at all: "
        f"{unguarded}"
    )


# --- the User retrofit: the measurement, recorded -------------------------


def test_the_user_retrofit_is_recorded_as_measured_and_refused(student, signup_campus):
    """**ESCALATION, as a test rather than as a paragraph.**

    ADR-002 §2.3 and TASKS §2 S2 both require `GatedManager` on `User`. It was
    applied exactly as specified and **26 tests failed in test-qa's tree
    alone**, every one on `User.objects.get(email=…)` returning nothing for a
    student who exists. `sessions.session_user` resolved nobody and
    `request_magic_link` tried to re-create an account and hit the unique
    index on `email`.

    This asserts the mechanism that causes it, so the escalation rests on a
    measurement rather than on a recollection: a **real** student on a campus
    whose gate is closed — the only lawful state before Gate C — disappears
    from a queryset filtered by the gate predicate.

    `all_objects` and `base_manager_name` **are** applied, so if cto rules the
    other way it is one line.
    """
    from apps.accounts.models import User
    from apps.core.scoping import gate_open_or_seed_q

    student.is_seed = False
    student.save(update_fields=["is_seed"])
    assert signup_campus.discovery_enabled_at is None, "precondition: the gate is closed"

    gated = User.all_objects.filter(gate_open_or_seed_q())
    assert not gated.filter(pk=student.pk).exists(), (
        "the gate predicate no longer hides a real student on a closed campus, "
        "so the escalation's premise has changed and ADR-002 §2.3's User "
        "retrofit should be re-examined"
    )
    assert User.objects.filter(pk=student.pk).exists(), (
        "User.objects is gated. Sign-in is broken for every real student "
        "before Gate C — see the escalation on apps.accounts.models.User."
    )


def test_user_still_has_the_two_companion_lines():
    """So the retrofit is one line away, not an audit away."""
    from apps.accounts.models import User

    assert User._meta.base_manager_name == "all_objects"
    assert isinstance(User.all_objects, models.Manager)


# --- the design point: underneath, never instead of ----------------------


def test_a_closed_campus_refuses_rather_than_returning_an_empty_list(student, signup_campus):
    """**The substitution ADR-002 §2.3 warns about, asserted.**

    `assert_discovery_open` must raise `GateClosed`. If a future developer
    deletes it because *"the manager already filters"*, a real student on a
    closed campus gets an empty page instead of the gate page — and the legal
    gate becomes invisible to the person it applies to. The manager returning
    nothing is **not** a substitute for the refusal, and this is the test that
    says so.
    """
    from apps.core.errors import GateClosed
    from apps.core.scoping import assert_discovery_open

    with pytest.raises(GateClosed) as caught:
        assert_discovery_open(signup_campus)
    assert caught.value.code == "GATE_CLOSED"
    assert caught.value.http_status == 403, (
        "a closed campus must be a 403 the student can be shown a page for, "
        "not a 200 with no rows"
    )


# --- helpers ---------------------------------------------------------------


def _make_listing(template, *, is_seed):
    from apps.listings.models import Listing

    return Listing.all_objects.create(
        seller=template.seller,
        seller_pseudonym=template.seller_pseudonym,
        book=template.book,
        campus_id=template.campus_id,
        city_id=template.city_id,
        asking_price_paise=12345,
        condition="GOOD",
        annotation_level="NONE",
        damage_flags=[],
        language="en",
        status="LIVE",
        is_seed=is_seed,
    )


def _make_photo(template, *, is_seed):
    """A photo whose seed flag is `is_seed` — **on a parent that agrees**.

    The first version of this helper hung the photo off `template` and set
    the flag independently, which is exactly the inconsistency ADR-002 §2's
    composite FK now makes unwritable: it started failing with a
    `ForeignKeyViolation` the moment the constraint landed. **That is the
    control catching this file's own fixture**, which is the thing the ADR
    said a service-routed test could never do — so the parent is built to
    match instead.
    """
    from django.utils import timezone

    from apps.listings.models import ListingPhoto

    parent = _make_listing(template, is_seed=is_seed)
    return ListingPhoto.all_objects.create(
        listing=parent,
        campus_id=parent.campus_id,
        city_id=parent.city_id,
        is_seed=parent.is_seed,
        storage_key=f"test/{is_seed}/{parent.id}.jpeg",
        sha256="0" * 64,
        width=10,
        height=10,
        bytes=100,
        exif_stripped_at=timezone.now(),
    )


def _make_request(template, *, is_seed):
    from apps.listings.models import BookRequest

    return BookRequest.all_objects.create(
        requester=template.seller,
        requester_pseudonym=template.seller_pseudonym,
        book=template.book,
        campus_id=template.campus_id,
        city_id=template.city_id,
        status="OPEN",
        is_seed=is_seed,
    )
