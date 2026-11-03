"""D-072 / A-37 — no purchase completes during the closed test.

`CLOSED-TEST.md` §2.3 is the ruling this file enforces: the Consumer
Protection (E-Commerce) Rules carry **no** turnover, user-count or
transaction-volume threshold (r.2(1), verbatim, primary-verified), and r.4(1)(a)
then requires the e-commerce entity to *be a company*. The one route that takes
a four-week incorporation off the critical path is the factual one — *"if the
closed test completes no purchase, there is nothing for r.2(1) to attach to"*.

**Until this file existed, shape 1 was true only by absence.** The transition
map has always permitted `LIVE → RESERVED → CLOSED_TRANSFERRED`; nothing called
into either state because the slice that would had not been written. So the
slice that builds reserve-and-complete would have moved this company into shape
2 **with nobody deciding to**, and `CLOSED-TEST.md` would still have read true.
That is `CLAUDE.md` rule 10's fifth disguise — *from outside, "not yet running"
and "running and passing trivially" are indistinguishable* — and the inversion
it demands is what `test_the_guard_is_wired_into_the_one_function_every_transition_goes_through`
is: **once the owning code exists, a ruled path that does not resolve is a
failure.**

Four things are asserted, and the third is the one the commit that added the
guard got wrong:

1. **Existence, by name**, so a deletion fails saying which guard went missing.
2. **Behaviour, by message text rather than exit status** (rule 10's sixth
   disguise), with **both sides of every split as rows**: the completion
   statuses refused next to the non-completion ones that still move, the absent
   authorisation next to the live one, and `completes_purchases = false` next to
   `true`. A guard that refused every transition would satisfy half of each
   pair and only the other half notices.
3. **The wiring itself**, by AST — because the guard shipped with a docstring
   claiming `_transition` called it and nothing did. A behavioural test alone
   would not have caught that: with the guard unwired, a reservation simply
   succeeds, which is indistinguishable from shape 2 having been chosen.
4. **The enumeration of the set the claim quantifies over.** The claim is *"no
   purchase completes"*; the set is **every path in `apps/**` that writes
   `listings.status`**, and rule 9's four-gates-deep lesson is that the layer
   was real and the set was never written down. `STATUS_WRITE_PATHS` is that
   set. `_transition` is not the only member — `seed_demo._seed_listings`
   inserts listings at a literal status and never goes near the guard — so the
   enumeration is load-bearing rather than decorative.
"""

import ast
import re
from pathlib import Path

import pytest

from apps.core.errors import GateClosed, TransitionNotAllowed
from apps.listings import services
from apps.listings.models import LISTING_STATUSES, Listing
from apps.listings.services import COMPLETION_STATUSES

# One definition of "a listing, correctly shaped" (`CLAUDE.md` rule 11). A
# second copy of those seven kwargs here would drift the day the contract adds
# a required field, and drift in a *fixture* reads as a product failure.
from .test_listings import _create

ROOT = Path(__file__).resolve().parents[2]
APPS = ROOT / "apps"
GUARD = "assert_purchase_completion_allowed"

#: The other side of the split, as rows (`CLAUDE.md` rule 10's corollary).
#: Checking only the refused statuses would pass against a `_transition` that
#: refused everything, which is a broken marketplace and a green suite.
NOT_A_COMPLETION = frozenset(
    {"DRAFT", "PENDING_REVIEW", "LIVE", "WITHDRAWN", "REJECTED", "REMOVED_LEGAL"}
)

#: Every path in `apps/**` that writes `listings.status`, with how it is safe.
#: Asserted complete below rather than taken on trust.
#: How a registered path is safe. `GUARDED` means it routes through
#: `_transition`; `LITERAL` means it writes a status that is written down in
#: its own source, and `test_every_bypass_writes_only_non_completion_statuses`
#: reads those literals rather than trusting this label.
GUARDED = "routes through _transition and inherits the D-072 guard"
LITERAL = "writes a literal status, asserted non-completion below"

STATUS_WRITE_PATHS = {
    ("apps/listings/services.py", "_transition"): GUARDED,
    ("apps/listings/services.py", "create_listing"): LITERAL,
    ("apps/core/management/commands/seed_demo.py", "_seed_listings"): LITERAL,
    # **Found by the enumerator, not by hand.** This file's first run returned
    # a writer the author had not thought of: erasure withdraws every open
    # listing of an erased seller (DATA-MODEL §10.1 step 6) to start the
    # retention clock, and it deliberately bypasses `_transition` because a
    # state machine must not be able to block an erasure. Exactly the kind of
    # sibling path rule 9's four-gates lesson is about.
    ("apps/accounts/services.py", "_detach_listing_rows"): LITERAL,
}

WRITE_METHODS = {"create", "get_or_create", "update_or_create", "bulk_create", "update", "save"}
LISTING_NAME = re.compile(r"\bListing\b")
RAW_UPDATE = re.compile(r"""update\s+["'`\[]?listings\b""", re.IGNORECASE)


# --- 1. existence, by name -------------------------------------------------


def test_the_completion_guard_exists_by_name():
    """Fails by name, which is the point: with the guard deleted, every other
    test in this file would still pass if it only drove the public callers,
    because no public caller reaches a completion status yet."""
    from apps.core import scoping, services as core_services

    assert callable(scoping.assert_purchase_completion_allowed)
    assert core_services.assert_purchase_completion_allowed is (
        scoping.assert_purchase_completion_allowed
    ), (
        "API-CONTRACT §3 lists the gate guards on apps.core.services; a second "
        "definition there would be a copy of this one"
    )


# --- 2. the wiring, by AST -------------------------------------------------


def _calls_in(source, function):
    """The set of functions called **by name** inside `function`'s body.

    `None` when `function` does not exist, which is deliberately different from
    the empty set: a rename of `_transition` must fail the wiring test loudly
    rather than report "no calls found" and pass (rule 10 — a check that
    cannot fail is worse than no check).
    """
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function:
            return {
                call.func.id
                for call in ast.walk(node)
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
            }
    return None


def test_the_guard_is_wired_into_the_one_function_every_transition_goes_through():
    """**The test the guard shipped without.**

    `assert_purchase_completion_allowed` was committed with a docstring reading
    *"Called from `listings.services._transition`"* while `grep` returned only
    the definition and the re-export. The claim was in the tree, the control
    was not, and the suite was green.
    """
    source = (APPS / "listings" / "services.py").read_text(encoding="utf-8")
    calls = _calls_in(source, "_transition")
    assert calls is not None, (
        "apps/listings/services.py has no function named `_transition`. It was "
        "renamed or removed, and the single chokepoint this guard depends on "
        "went with it — re-point this test at the new one and check that every "
        "caller still routes through it"
    )
    assert GUARD in calls, (
        f"`_transition` does not call `{GUARD}`. D-072 shape 1 says no purchase "
        "completes during the closed test; with this call gone, a move to "
        "RESERVED or CLOSED_TRANSFERRED succeeds and the company is a "
        "marketplace e-commerce entity under rules with no user-count "
        "threshold (CLOSED-TEST.md §2.3), decided by nobody"
    )


def test_the_wiring_check_can_fail():
    """A guard for a guard, because the one above is the only thing standing
    between a deleted call and a silent shape change.

    Both failure branches are exercised: the call removed, and the enclosing
    function renamed. Asserting only that the real source passes would be a
    check that cannot fail — `CLAUDE.md` rule 10's corollary, and the guard
    written under it caught its own author's bug on its first run.
    """
    source = (APPS / "listings" / "services.py").read_text(encoding="utf-8")

    # **Replaced with `pass`, not deleted.** Deleting the line leaves
    # `if to_status in COMPLETION_STATUSES:` with no body, so `ast.parse`
    # raises `IndentationError` and this test fails for a reason that has
    # nothing to do with whether the detector works. Measured, on the first
    # run of this test.
    without_call = re.sub(
        rf"^(?P<indent>[ \t]*){GUARD}\(.*\)[ \t]*$",
        lambda m: m.group("indent") + "pass",
        source,
        flags=re.M,
    )
    assert without_call != source, "the call site is not on one line any more"
    assert GUARD not in _calls_in(without_call, "_transition"), (
        "the detector still reports the guard as called after the only call "
        "site was replaced, so it is not reading the call site it claims to"
    )

    assert _calls_in(source, "a_function_that_does_not_exist") is None


# --- 3. the classification is total ---------------------------------------


def test_every_listing_status_is_classified_as_a_completion_or_not():
    """The ceiling `COMPLETION_STATUSES` declares, enforced here.

    That set is a hand-written list because there is no property to ask: a
    status is a completion because of what it means legally, not because of its
    shape in `LISTING_TRANSITIONS` (`WITHDRAWN` is equally terminal and is not
    a sale; `RESERVED` is a sale and is not terminal). A list gets *edited*,
    and a status added to the schema and to neither side of this split would
    otherwise be unguarded in silence.
    """
    assert COMPLETION_STATUSES | NOT_A_COMPLETION == set(LISTING_STATUSES), (
        "a listings.status exists that is classified neither as a completion "
        "nor as a non-completion. Decide which it is: if a sale is agreed or "
        "concluded in that status it belongs in COMPLETION_STATUSES, and "
        "CLOSED-TEST.md §2.3 is the test — does a sale happen?"
    )
    assert not COMPLETION_STATUSES & NOT_A_COMPLETION


def test_the_statuses_the_document_names_are_both_in_the_set():
    """Rule 9: the control is asserted at the boundary **the document claims**.

    §2.3's finding is *"whether a sale happens at all"*, not whether a book is
    delivered, so `RESERVED` — an accepted offer, which concludes a contract of
    sale whether or not the book has moved — is inside the gate. A future
    narrowing to `CLOSED_TRANSFERRED` alone is a legal decision and goes to
    counsel beside Q-CT1; it is not a refactor, and this assertion is here so
    that it cannot be made as one.
    """
    assert COMPLETION_STATUSES == {"RESERVED", "CLOSED_TRANSFERRED"}


# --- 4. behaviour, both sides of every split, by message text -------------


def _attempt(seller, book, to_status):
    """Drive `_transition` into `to_status` from a status the edge exists from.

    Directly, as `test_no_buyer_reachable_status_is_reachable_on_an_unverified_book`
    does, because no public caller can express the move yet — which is exactly
    why the guard had to go in the chokepoint rather than in a caller.
    """
    listing = _create(seller, book)
    from_status = next(
        s for s, to in services.LISTING_TRANSITIONS.items() if to_status in to
    )
    Listing.all_objects.filter(id=listing.id).update(status=from_status)
    listing.refresh_from_db()
    return services._transition(
        listing, to_status, listing.version, actor=seller, action="test.d072"
    )


def _authorise_purchases(legal_entity, *, completes):
    """A **newer** Gate B row, because `gate_authorisations` cannot be deleted.

    This is also the only test that exercises the `-id` tiebreak in
    `_live_gate_b_row`: `authorised_at` defaults to `timezone.now()`, whose
    granularity was measured at ~1 ms, so this row and the fixture's tie on the
    timestamp and the guard must still read **this** one.
    """
    from apps.core.models import GateAuthorisation

    return GateAuthorisation.objects.create(
        gate="B", scope_type="GLOBAL", scope_id=None, legal_entity=legal_entity,
        evidence={
            "participant_ceiling": 1000,
            "closed_test_expires_at": "2099-01-01T00:00:00+00:00",
            "takedown_sop_ref": "SOP-TD-1",
            "escalation_contact_ref": "A Human <oncall@example.test>",
            "notice_version_ids": [],
            "completes_purchases": completes,
        },
        authorised_by_human="A Human",
    )


@pytest.mark.parametrize("to_status", sorted(COMPLETION_STATUSES))
def test_shape_1_refuses_every_completion_status(db, seller, book, to_status):
    with pytest.raises(GateClosed) as caught:
        _attempt(seller, book, to_status)
    assert str(caught.value) == (
        "Books are not changing hands through BookHop during the closed test."
    )
    detail = caught.value.context["detail"]
    assert "D-072 / A-37" in detail
    assert repr(to_status) in detail
    assert "completes_purchases = False" in detail


@pytest.mark.parametrize("to_status", sorted(COMPLETION_STATUSES))
def test_an_absent_authorisation_is_not_an_authorisation(db, seller, book, to_status):
    """Fail-closed, and the direction matters more than the message.

    With no live row the guard could plausibly have let the transition through
    on the grounds that nothing forbids it. It refuses, because shape 1 is the
    safe side and `CLOSED-TEST.md` §2.3's exposure runs the other way.
    """
    from django.utils import timezone

    from apps.core.models import GateAuthorisation

    GateAuthorisation.objects.filter(gate="B").update(revoked_at=timezone.now())
    with pytest.raises(GateClosed) as caught:
        _attempt(seller, book, to_status)
    assert "no live gate_authorisations row" in caught.value.context["detail"]


@pytest.mark.parametrize("to_status", sorted(COMPLETION_STATUSES))
def test_a_row_that_authorises_purchases_lets_the_transition_through(
    db, seller, book, legal_entity, to_status
):
    """**The permitted side.** Without this, a `_transition` that refused every
    move into a completion state unconditionally would pass every other test
    here, and shape 2 would be unreachable the day the founder chose it —
    a guard with no off switch is rule 10's second disguise, a requirement
    that cannot be satisfied.
    """
    _authorise_purchases(legal_entity, completes=True)
    listing = _attempt(seller, book, to_status)
    assert listing.status == to_status


@pytest.mark.parametrize("completes", [False, None, "yes", 1])
def test_only_a_real_true_authorises(db, seller, book, legal_entity, completes):
    """`completes_purchases` is read as a boolean `is True`, not for truthiness.

    `1` and `"yes"` are the shapes a hand-edited JSON blob produces, and a gate
    whose answer depends on Python's truthiness rules is not a gate a founder
    decision can be recorded in.
    """
    _authorise_purchases(legal_entity, completes=completes)
    with pytest.raises(GateClosed):
        _attempt(seller, book, "RESERVED")


@pytest.mark.parametrize("to_status", sorted(NOT_A_COMPLETION - {"DRAFT"}))
def test_shape_1_does_not_touch_a_non_completion_transition(db, seller, book, to_status):
    """The main journey must keep working, or the gate is rule 10's second
    disguise from the other end: a criterion broader than its own rationale,
    which the thing it protects has to violate to function.

    A listing still drafts, publishes, is reviewed, rejected, withdrawn and
    taken down while no purchase completes — that *is* shape 1, which
    `CLOSED-TEST.md` §2.3 calls *"probably the better experiment"* precisely
    because browsing and matching need no money to change hands.
    """
    listing = _create(seller, book)
    from_status = next(
        (s for s, to in services.LISTING_TRANSITIONS.items() if to_status in to), None
    )
    if from_status is None:
        pytest.skip(f"no edge into {to_status} in LISTING_TRANSITIONS")
    Listing.all_objects.filter(id=listing.id).update(status=from_status)
    listing.refresh_from_db()
    moved = services._transition(
        listing, to_status, listing.version, actor=seller, action="test.d072.allowed"
    )
    assert moved.status == to_status


def test_the_refusal_is_a_gate_and_not_a_state_machine_error(db, seller, book):
    """`GateClosed`, not `TransitionNotAllowed`, and the distinction is
    API-CONTRACT §2.2's: 422 says *the object is not in a state where this is
    possible* and would tell a student to try again later, when the truth is
    that the platform does not do this at all right now.
    """
    with pytest.raises(GateClosed) as caught:
        _attempt(seller, book, "RESERVED")
    assert not isinstance(caught.value, TransitionNotAllowed)


# --- 5. the set the claim quantifies over ---------------------------------


def _writes_a_listing_row(call, source):
    func = call.func
    if isinstance(func, ast.Name) and func.id == "Listing":
        return True
    if isinstance(func, ast.Attribute) and func.attr in WRITE_METHODS:
        return bool(LISTING_NAME.search(ast.get_source_segment(source, func.value) or ""))
    return False


def status_write_sites(source, label):
    """`{(label, enclosing function)}` for every `listings` write in `source`."""
    found = set()

    def visit(node, enclosing):
        for child in ast.iter_child_nodes(node):
            name = enclosing
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = child.name
            elif isinstance(child, ast.Call) and _writes_a_listing_row(child, source):
                found.add((label, enclosing))
            visit(child, name)

    visit(ast.parse(source), "<module>")
    if RAW_UPDATE.search(source):
        found.add((label, "<raw SQL>"))
    return found


def _walk_the_tree():
    sites, reached = set(), []
    for path in sorted(APPS.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        label = path.relative_to(APPS.parent).as_posix()
        sites |= status_write_sites(path.read_text(encoding="utf-8"), label)
        reached.append(label)
    return sites, reached


def test_the_enumeration_of_listing_status_writers_is_complete():
    """A new writer of `listings.status` fails the build here.

    This is the assertion `CLAUDE.md` rule 9's four-gates-deep lesson asks
    for: the guard in `_transition` is real and measured, but *"the set it
    quantified over was never written down"* is how a substring predicate over
    a derived column let a phone number out. A path that inserts a listing at
    `CLOSED_TRANSFERRED` without touching `_transition` would complete a
    purchase with the guard sitting there, passing.
    """
    sites, _ = _walk_the_tree()
    assert sites == set(STATUS_WRITE_PATHS), (
        "the set of paths that write `listings.status` has changed.\n\n"
        f"  new:     {sorted(sites - set(STATUS_WRITE_PATHS))}\n"
        f"  missing: {sorted(set(STATUS_WRITE_PATHS) - sites)}\n\n"
        "Every writer either routes through `_transition` (and inherits the "
        "D-072 guard) or inserts at a literal non-completion status. Register "
        "it above with which one it is."
    )


def _function(path, name):
    source = (ROOT / path).read_text(encoding="utf-8")
    node = next(
        (n for n in ast.walk(ast.parse(source))
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name),
        None,
    )
    assert node is not None, f"{path} has no function named {name}"
    return node


def _status_values_written(node):
    """The statuses a function **writes**, read out of its own source.

    *Writes*, not mentions, and the difference is load-bearing:
    `_detach_listing_rows` names `CLOSED_TRANSFERRED` in an
    `.exclude(status__in=...)` — it reads the status to skip rows already
    closed — and a check that collected every string constant in the function
    would flag that read as a completed sale. Rule 13: a guard that fires on
    the code it protects gets edited rather than obeyed.

    Where the written value is **computed** rather than literal (`seed_demo`
    passes `status=status` out of a table of shapes), the value cannot be read
    any more precisely, so this widens to every listing-status-shaped constant
    in the function. Over-broad on purpose — the failure direction has to be
    *flags a mention* and never *misses a write*.
    """
    written, computed = set(), False

    def record(value):
        nonlocal computed
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            written.add(value.value)
        else:
            computed = True

    for child in ast.walk(node):
        if isinstance(child, ast.keyword) and child.arg == "status":
            record(child.value)
        elif isinstance(child, ast.Dict):
            for key, value in zip(child.keys, child.values):
                if isinstance(key, ast.Constant) and key.value == "status":
                    record(value)
    if computed:
        written |= {
            c.value
            for c in ast.walk(node)
            if isinstance(c, ast.Constant) and c.value in set(LISTING_STATUSES)
        }
    return written


@pytest.mark.parametrize(
    ("path", "function"),
    sorted(k for k, how in STATUS_WRITE_PATHS.items() if how == LITERAL),
)
def test_every_bypass_writes_only_non_completion_statuses(path, function):
    """The registered paths that do **not** route through `_transition`, with
    their own literals read back.

    This is the half of the enumeration that does work. Registering a bypass
    path would otherwise be a comment: `seed_demo` could grow a
    `CLOSED_TRANSFERRED` row — a completed purchase written straight into the
    database, authorised by a list in a management command — and the
    enumeration test would still pass, because the path is registered.
    """
    written = _status_values_written(_function(path, function))
    assert written, f"no status write found in {path}::{function}; the path is misregistered"
    assert not written & COMPLETION_STATUSES, (
        f"{path}::{function} writes {sorted(written & COMPLETION_STATUSES)}, which is "
        "an agreed or completed sale reaching listings.status without passing "
        "the D-072 guard in `_transition`"
    )


#: Planted sources for the test below, as triple-quoted literals with real
#: newlines, because a one-line string with escaped newlines in it is a thing
#: to get wrong in a file whose whole job is noticing things got wrong.
#: in a file whose whole job is to notice things that were got wrong.
PLANTED_WRITE = '''
def f():
    Listing.objects.create(status='CLOSED_TRANSFERRED')
'''

PLANTED_MENTION = '''
def f():
    Listing.objects.exclude(status__in=('CLOSED_TRANSFERRED',)).update(seller=None)
'''

PLANTED_COMPUTED = '''
def f():
    for s in ('LIVE', 'RESERVED'):
        Listing.objects.create(status=s)
'''


def test_the_literal_reader_distinguishes_a_write_from_a_mention():
    """The instrument, measured on all three shapes it has to tell apart.

    Without this, `test_every_bypass_writes_only_non_completion_statuses`
    could pass by reading nothing at all — and the mention case is the one
    that matters, because `_detach_listing_rows` contains exactly that shape
    and a false positive there would get this control edited rather than
    obeyed.
    """
    def read(source):
        return _status_values_written(ast.parse(source).body[0])

    assert read(PLANTED_WRITE) == {"CLOSED_TRANSFERRED"}
    assert read(PLANTED_MENTION) == set(), "a read of a status was counted as a write"
    assert read(PLANTED_COMPUTED) == {"LIVE", "RESERVED"}, (
        "a computed status did not widen to the literals in its function"
    )


def test_the_enumerator_detects_what_it_claims_to_detect():
    """The instrument, measured. A detector that found nothing would make
    `test_the_enumeration_of_listing_status_writers_is_complete` pass against
    an empty `STATUS_WRITE_PATHS` and report that as coverage.
    """
    planted = (
        "def smuggle(listing):\n"
        "    Listing.all_objects.filter(id=listing.id).update(status='CLOSED_TRANSFERRED')\n"
    )
    assert status_write_sites(planted, "planted.py") == {("planted.py", "smuggle")}

    raw = "def smuggle(c):\n    c.execute('UPDATE listings SET status = 1')\n"
    assert ("raw.py", "<raw SQL>") in status_write_sites(raw, "raw.py")

    assert status_write_sites("def innocent():\n    return 1\n", "clean.py") == set()


def test_the_enumerator_reached_the_whole_app_tree():
    """An instrument asserts its own reach, and any number it produces is
    quoted with the count actually reached (`CLAUDE.md` rule 10's fourth
    disguise — the accessibility harness reached four pages of eleven and
    reported coverage for a slice).
    """
    _, reached = _walk_the_tree()
    on_disk = [
        p.relative_to(APPS.parent).as_posix()
        for p in APPS.rglob("*.py")
        if "__pycache__" not in p.parts
    ]
    assert sorted(reached) == sorted(on_disk)
    assert "apps/listings/services.py" in reached
    assert len(reached) > 20, f"walked only {len(reached)} modules under apps/"
