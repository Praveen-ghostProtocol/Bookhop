"""Gate B — B9′ / A-35. A real account needs a named human's authorisation.

`ops/INCORPORATION-AND-BLOCKERS.md` §3.3 B9′ specified *"a
`gate_authorisations` row with `gate='B'`, and real account creation refused
without it"* and costed it at *"one function"*. It was never built, and
**nothing ever told us**, because an absent gate and a clean gate both produce
no refusal (`CLOSED-TEST.md` §1, A-35).

Three things are asserted here and the third is the one that cost four gates:

1. **Existence, by name** — so a future deletion fails saying which guard went
   missing rather than going quiet again (`CLAUDE.md` rule 9).
2. **Behaviour, by message text and not by exit status** (rule 10's sixth
   disguise), with **both sides of every split as rows**: the seed account
   that is allowed next to the real one that is refused, the clock before the
   expiry next to the clock after it, the headcount under the ceiling next to
   the headcount at it. A guard that always refused would satisfy half of
   each pair and nothing here would notice.
3. **The enumeration of the set the claim quantifies over.** The claim is
   *"a real account cannot be created without a live Gate B row"*; the set is
   **every path in `apps/**` that writes a `users` row**, and A-35 requires it
   written down rather than implied. `CREATION_PATHS` is that set and
   `test_the_enumeration_of_real_account_creation_paths_is_complete` fails the
   build when a new path appears.
"""

import ast
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone as dt_timezone
from pathlib import Path

import pytest

from apps.core.errors import GateClosed
from apps.core.scoping import (
    GATE_B_BOUNDS,
    GATE_B_NOTICE_KINDS,
    assert_real_account_allowed,
)

APPS = Path(__file__).resolve().parents[2] / "apps"


# --- the set the claim quantifies over -------------------------------------
#
# A **model-level hook** (`pre_save` on `User`) or a **database trigger** on
# `users` would express "every creation path" better than any walk over source
# can, because neither keys on a name. Measured before choosing this shape:
# either one refuses **12 existing call sites in 7 test files**, all of them
# owned by test-qa (`tests/contract/**`, `tests/a11y/**`) or red-team
# (`tests/redteam/**`), which create non-seed users directly. That is a
# coordinated change across three agents' trees, not a backend commit, and it
# is written up in the slice note rather than taken unilaterally.

#: Every path in `apps/**` that writes a `users` row, with how it is safe.
#: `guarded` means the enclosing function calls `assert_real_account_allowed`,
#: which is asserted below rather than taken on trust.
CREATION_PATHS = {
    ("apps/accounts/services.py", "request_magic_link"): "guarded",
    ("apps/core/management/commands/seed_demo.py", "_seed_accounts"): "guarded",
}

GUARD = "assert_real_account_allowed"

#: Manager and queryset methods that can insert a row. `save` is here for
#: `User(...).save()`; a bare `user.save()` on an existing instance is an
#: update and is correctly not matched, because the construction that made it
#: is matched instead.
WRITE_METHODS = {
    "create", "get_or_create", "update_or_create", "bulk_create",
    "acreate", "aget_or_create", "aupdate_or_create", "abulk_create", "save",
}

#: `\bUser\b`, so `UserTombstone` and `get_user_model` do not match.
#:
# ponytail: the walker keys on the **name** `User`, which is the weakness A-34
# measured in a different guard — a creation routed through
# `get_user_model()` or a model fetched by string would not be seen. Ceiling
# declared rather than hidden. The layer that still catches it: every write
# lives in `apps/*/services.py` by charter, and `apps/core/p14.py`'s source
# sweep plus code review read that tree. Upgrade path: the `pre_save` hook
# above, on the day QA's and red-team's 12 call sites can move in the same
# commit.
USER_NAME = re.compile(r"\bUser\b")
RAW_INSERT = re.compile(r"""insert\s+into\s+["'`\[]?users\b""", re.IGNORECASE)


def _writes_a_user_row(call, source):
    func = call.func
    if isinstance(func, ast.Name) and func.id == "User":
        return True
    if isinstance(func, ast.Attribute) and func.attr in WRITE_METHODS:
        return bool(USER_NAME.search(ast.get_source_segment(source, func.value) or ""))
    return False


def creation_sites(source, label):
    """`{(label, enclosing function)}` for every `users` write in `source`."""
    found = set()

    def visit(node, enclosing):
        for child in ast.iter_child_nodes(node):
            name = enclosing
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = child.name
            elif isinstance(child, ast.Call) and _writes_a_user_row(child, source):
                found.add((label, enclosing))
            visit(child, name)

    visit(ast.parse(source), "<module>")
    if RAW_INSERT.search(source):
        found.add((label, "<raw SQL>"))
    return found


def app_modules():
    return [p for p in sorted(APPS.rglob("*.py")) if "__pycache__" not in p.parts]


def _walk_the_tree():
    sites, sources = set(), {}
    for path in app_modules():
        label = path.relative_to(APPS.parent).as_posix()
        source = path.read_text(encoding="utf-8")
        sources[label] = source
        sites |= creation_sites(source, label)
    return sites, sources


# --- 1. existence, by name -------------------------------------------------


def test_the_gate_b_guard_exists_by_name():
    """`grep -rn "def assert_" apps/` returned two guards and B9′ needed three.

    This fails by name, which is the whole point: the previous state of the
    world produced no refusal and no failure of any kind.
    """
    from apps.core import scoping, services

    assert callable(scoping.assert_real_account_allowed)
    assert services.assert_real_account_allowed is scoping.assert_real_account_allowed, (
        "API-CONTRACT §3 lists the gate guards on apps.core.services; a second "
        "definition there would be a copy of this one"
    )


# --- 2. behaviour, by message text, both sides of every split --------------


def published_notice_ids():
    """`GATE_B_NOTICE_KINDS` as real rows, so `notice_version_ids` resolves.

    **This is the fixture half of rule 10's third disguise.** D-072's guard
    does not count the list, it *resolves* it — and the moment it did,
    `tests/conftest.py`'s hardcoded `[1, 2]` stopped matching anything and took
    75 tests down with it. A helper that published no notices could only ever
    produce the refused side of this split.

    `get_or_create` because more than one row per test calls it, and
    `notice_versions` is unique on `(kind, version, locale)` and immutable.
    """
    from apps.accounts.models import NoticeVersion

    return [
        NoticeVersion.objects.get_or_create(
            kind=kind, version="gate-b-evidence.1", locale="en",
            defaults={
                "body_md": f"# {kind}",
                "sha256": hashlib.sha256(kind.encode()).hexdigest(),
            },
        )[0].id
        for kind in GATE_B_NOTICE_KINDS
    ]


def gate_b(legal_entity, *, human="A Human", **evidence):
    """A row carrying the **whole** shape-1 evidence set, minus what a caller
    removes with `_ABSENT`.

    The default has to be a *passing* row or every test below measures the
    wrong thing: a helper whose default was already short of the evidence set
    would make `test_a_live_row_lets_a_real_account_through` fail for a reason
    that has nothing to do with what it asserts.
    """
    from apps.core.models import GateAuthorisation

    payload = {
        "participant_ceiling": 12,
        "closed_test_expires_at": "2027-01-01T00:00:00+00:00",
        # D-072 shape 1. `False` is a *value*, so the guard tests presence with
        # `in` and not truthiness — which is why this key sits in
        # `GATE_B_BOUNDS` rather than in the refs loop.
        "completes_purchases": False,
        "takedown_sop_ref": "SOP-TD-1",
        "escalation_contact_ref": "A Human <oncall@example.test>",
        "incident_runbook_ref": "RUNBOOK-1",
        "notice_version_ids": published_notice_ids(),
    }
    payload.update(evidence)
    for key, value in list(payload.items()):
        if value is _ABSENT:
            del payload[key]
    return GateAuthorisation.objects.create(
        gate="B", scope_type="GLOBAL", scope_id=None, legal_entity=legal_entity,
        evidence=payload, authorised_by_human=human,
    )


_ABSENT = object()
BEFORE_EXPIRY = datetime(2026, 12, 1, tzinfo=dt_timezone.utc)
AFTER_EXPIRY = datetime(2027, 6, 1, tzinfo=dt_timezone.utc)


@pytest.mark.parametrize("is_seed", [True, False])
def test_both_sides_of_the_seed_split_are_rows(db, is_seed):
    """ADR-002 §4.1(c)'s split, as two rows rather than one.

    A seed account still succeeds with **no** authorisation row — that is what
    makes building before the gate lawful — and a real one is refused with
    none. Testing only the refused side would pass against a guard that
    refuses everything, and testing only the permitted side would pass against
    no guard at all.
    """
    if is_seed:
        assert assert_real_account_allowed(is_seed=True) is None
        return
    with pytest.raises(GateClosed) as raised:
        assert_real_account_allowed(is_seed=False)
    assert str(raised.value) == "BookHop is not open for sign-ups yet."
    assert "No live gate_authorisations row with gate='B'" in raised.value.context["detail"]


def test_a_live_row_lets_a_real_account_through(db, legal_entity):
    row = gate_b(legal_entity)
    assert assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY) == row


def test_a_revoked_row_does_not_authorise_anything(db, legal_entity):
    from django.utils import timezone

    from apps.core.models import GateAuthorisation

    row = gate_b(legal_entity)
    # Revocation is the one UPDATE migration 0002 permits; the row itself can
    # never be deleted, which is why "no row" and "a revoked row" are separate
    # tests rather than the same one written twice.
    GateAuthorisation.objects.filter(id=row.id).update(
        revoked_at=timezone.now(), revoked_reason="closed test ended"
    )
    with pytest.raises(GateClosed) as raised:
        assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY)
    assert "No live gate_authorisations row" in raised.value.context["detail"]


@pytest.mark.parametrize(
    ("human", "allowed"),
    [("A Human", True), ("", False), ("   ", False), ("​", False), ("﻿ ", False)],
)
def test_the_smaller_gate_is_still_a_named_humans_signature(db, legal_entity, human, allowed):
    """CLOSED-TEST.md §4.1: *"Unchanged, same deny-list, non-negotiable."*

    The invisible forms are here because they are the ones that defeat a
    length check and a `.strip()` respectively; the definition is imported
    from `open_discovery`, so this guard and the Gate C command cannot drift
    (`CLAUDE.md` rule 11).
    """
    gate_b(legal_entity, human=human)
    if allowed:
        assert assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY) is not None
        return
    with pytest.raises(GateClosed) as raised:
        assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY)
    assert "carries no named human in authorised_by_human" in raised.value.context["detail"]


@pytest.mark.parametrize("missing", GATE_B_BOUNDS)
def test_a_row_without_its_bounds_does_not_open_the_gate(db, legal_entity, missing):
    """A-35: a gate justified by *"twelve known adults for six weeks"* and not
    bounded by those words in the row is a permanent downgrade wearing a
    temporary label. Parametrised over the bounds themselves, so adding one to
    `GATE_B_BOUNDS` adds its test rather than needing one written."""
    gate_b(legal_entity, **{missing: _ABSENT})
    with pytest.raises(GateClosed) as raised:
        assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY)
    assert f"missing evidence.{missing}" in raised.value.context["detail"]


@pytest.mark.parametrize(
    ("now", "refused"), [(BEFORE_EXPIRY, False), (AFTER_EXPIRY, True)]
)
def test_the_expiry_is_read(db, legal_entity, now, refused):
    """**The same row, two clocks, opposite outcomes.**

    A clock nothing reads is a check that cannot fail (`CLAUDE.md` rule 10),
    and so is a clock whose only test is the refusing side — that one passes
    against a guard that refuses unconditionally.
    """
    gate_b(legal_entity, closed_test_expires_at="2027-01-01T00:00:00+00:00")
    if not refused:
        assert assert_real_account_allowed(is_seed=False, now=now) is not None
        return
    with pytest.raises(GateClosed) as raised:
        assert_real_account_allowed(is_seed=False, now=now)
    assert str(raised.value) == "The closed test has ended."
    assert "expired at 2027-01-01T00:00:00+00:00" in raised.value.context["detail"]


@pytest.mark.parametrize("expiry", ["six weeks", "", "2027-13-45", 1767225600, None])
def test_an_unreadable_expiry_fails_closed(db, legal_entity, expiry):
    gate_b(legal_entity, closed_test_expires_at=expiry)
    with pytest.raises(GateClosed) as raised:
        assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY)
    assert "is not a date or a timestamp" in raised.value.context["detail"]


@pytest.mark.parametrize(("ceiling", "refused"), [(2, False), (1, True)])
def test_the_participant_ceiling_is_read(db, legal_entity, signup_campus, ceiling, refused):
    """One real account already exists; the same world refuses at a cap of one
    and allows at a cap of two. Compliance would not endorse the reduced gate
    without the ceiling, and a ceiling nothing reads is not a ceiling."""
    from apps.accounts.models import User

    User.objects.create(
        email="first.friend@example.ac.in", campus=signup_campus,
        city_id=signup_campus.city_id, is_seed=False, status="ACTIVE",
    )
    gate_b(legal_entity, participant_ceiling=ceiling)
    if not refused:
        assert assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY) is not None
        return
    with pytest.raises(GateClosed) as raised:
        assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY)
    assert str(raised.value) == "The closed test is full."
    assert "caps the closed test at 1 participants and 1 real accounts exist" in (
        raised.value.context["detail"]
    )


def test_a_tombstoned_participant_frees_their_place(db, legal_entity, signup_campus):
    """The ceiling is a headcount, not a high-water mark. Stated in the guard
    and asserted here, because the opposite reading is equally plausible and
    the difference only shows up after someone deletes their account."""
    from apps.accounts.models import User

    User.objects.create(
        email=None, campus=signup_campus, city_id=signup_campus.city_id,
        is_seed=False, status="TOMBSTONED",
    )
    gate_b(legal_entity, participant_ceiling=1)
    assert assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY) is not None


@pytest.mark.parametrize("ceiling", ["twelve", 0, -1, True, None, 12.0])
def test_an_unreadable_ceiling_fails_closed(db, legal_entity, ceiling):
    gate_b(legal_entity, participant_ceiling=ceiling)
    with pytest.raises(GateClosed) as raised:
        assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY)
    assert "is not a positive integer" in raised.value.context["detail"]


# --- the guard at the real call site ---------------------------------------


def test_request_magic_link_creates_no_account_when_gate_b_is_absent(db, city, legal_entity):
    """The refusal measured where it matters: no `users` row, no token, no job.

    `signup_campus` is deliberately **not** used — it carries `gate_b_open`,
    and a fixture that cannot produce the condition is the defect this is
    guarding against (`CLAUDE.md` rule 10).
    """
    from apps.accounts.models import EmailLoginToken, User
    from apps.accounts.services import request_magic_link
    from apps.core.models import Campus, Job

    Campus.objects.create(
        city=city, name="Unauthorised Campus", slug="unauthorised",
        legal_entity=legal_entity, email_domains=["example.ac.in"],
    )
    with pytest.raises(GateClosed) as raised:
        request_magic_link("first.friend@example.ac.in", "203.0.113.9", "Mozilla/5.0 (Android)")

    assert "B9′" in raised.value.context["detail"]
    assert User.all_objects.count() == 0
    assert EmailLoginToken.objects.count() == 0
    assert Job.objects.filter(kind="accounts.send_magic_link").count() == 0


def test_an_existing_account_still_signs_in_with_no_gate_b_row(db, city, legal_entity):
    """The gate is on **creation**. ADR-002 §4.1(c)'s seed actors must still be
    able to exercise every slice before Gate B opens, or the seed/real split
    that makes building lawful stops working the day its guard lands."""
    from apps.accounts.models import EmailLoginToken, User
    from apps.accounts.services import request_magic_link
    from apps.core.models import Campus

    campus = Campus.objects.create(
        city=city, name="Unauthorised Campus", slug="unauthorised",
        legal_entity=legal_entity, email_domains=["example.ac.in"],
    )
    User.objects.create(
        email="seed.student@example.ac.in", campus=campus, city_id=campus.city_id,
        is_seed=True, status="ACTIVE",
    )
    request_magic_link("seed.student@example.ac.in", None, None)
    assert EmailLoginToken.objects.count() == 1


@pytest.mark.urls("tests.urls_api_only")
def test_the_api_still_answers_202_when_gate_b_is_shut(client, db, city, legal_entity):
    """A 403 here would say *"no account exists at this address yet"* — the
    account-enumeration oracle API-CONTRACT §5.1's unconditional 202 exists to
    close, arriving through a new door."""
    from apps.core.models import Campus

    Campus.objects.create(
        city=city, name="Unauthorised Campus", slug="unauthorised",
        legal_entity=legal_entity, email_domains=["example.ac.in"],
    )
    response = client.post(
        "/api/v1/auth/magic-link",
        data=json.dumps({"email": "first.friend@example.ac.in"}),
        content_type="application/json",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 202, response.content
    assert b"GATE_CLOSED" not in response.content


# --- 3. the enumeration, and the instrument that produces it ---------------


def test_the_enumeration_of_real_account_creation_paths_is_complete():
    """A-35: *"a guard on the one path we remember is the same defect with a
    smaller blast radius."*

    If this fails, a new path writes `users` rows. Add it to `CREATION_PATHS`
    **and** make it safe — the registry is the set the Gate B claim quantifies
    over, not a list of exceptions to it.
    """
    sites, _ = _walk_the_tree()
    assert sites == set(CREATION_PATHS), (
        "the set of paths that write a users row has changed.\n"
        f"  unregistered: {sorted(sites - set(CREATION_PATHS))}\n"
        f"  registered but gone: {sorted(set(CREATION_PATHS) - sites)}"
    )


@pytest.mark.parametrize(("site", "how"), sorted(CREATION_PATHS.items()))
def test_every_registered_creation_path_calls_the_guard(site, how):
    """The registry's claim, checked rather than trusted. Each entry names a
    function; this asserts that function's own source calls the guard."""
    assert how == "guarded"
    module, function = site
    source = (APPS.parent / module).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function:
            body = ast.get_source_segment(source, node) or ""
            assert GUARD in body, f"{module}::{function} writes a users row without calling {GUARD}"
            return
    pytest.fail(f"{module} has no function named {function!r}")


PLANTED = '''
class Seeder:
    def makes_one(self):
        User.objects.create(email="x")

    def makes_one_the_long_way(self):
        row = User(email="y")
        row.save()

    def updates_one(self, user):
        user.save()

    def makes_a_tombstone(self):
        UserTombstone.objects.create()

    def makes_something_else(self):
        Listing.objects.create()
'''

PLANTED_SQL = '''
def backfill(cursor):
    cursor.execute("INSERT INTO users (email) VALUES (%s)", ["x"])
'''


def test_the_enumerator_detects_what_it_claims_to_detect():
    """**A guard for the guard** (`CLAUDE.md` rule 10's corollary).

    The completeness test above is an equality against a set the walker
    produces. If the walker silently found nothing, that test would pass the
    day someone deleted the guard's only call site — `sites` and the registry
    would both shrink to nothing only if the registry shrank too, but a walker
    that matched *nothing at all* would fail loudly, and one that matched the
    wrong things would not. So the instrument is measured on planted input:
    both positives, and three negatives that are easy to match by accident.
    """
    found = {function for _, function in creation_sites(PLANTED, "planted.py")}
    assert found == {"makes_one", "makes_one_the_long_way"}, found
    assert creation_sites(PLANTED_SQL, "sql.py") == {("sql.py", "<raw SQL>")}


def test_no_account_creation_path_exists_outside_the_tree_that_was_walked():
    """A-35 names four members of the set and the walk above can only see
    three of them: *"the signup view, the API, any management command, any
    staff-created account, and any fixture path reachable outside tests."*

    **A staff-created account and a `loaddata` fixture are paths in Django,
    not paths in `apps/**`** — `manage.py createsuperuser` and the admin's add
    form write rows without any source of ours being involved, so a walk over
    our tree cannot rule them out and saying "there are none" in prose would
    be the unwritten set all over again. They are ruled out by configuration,
    and this is that configuration asserted: no `django.contrib.auth`, no
    admin, the default `AUTH_USER_MODEL`, and no fixture directory for
    `loaddata` to find.

    If any of those changes, this fails and the registry above needs a new
    kind of entry — not a new line.
    """
    from django.conf import settings

    installed = set(settings.INSTALLED_APPS)
    assert "django.contrib.auth" not in installed, (
        "django.contrib.auth brings createsuperuser and a User the Gate B "
        "guard has never seen"
    )
    assert "django.contrib.admin" not in installed, "the admin can add a user row"
    assert settings.AUTH_USER_MODEL == "auth.User", (
        "apps.accounts.User is a plain model, not the auth user; if that "
        "changes, Django's own creation paths join the set"
    )
    assert not list(APPS.rglob("fixtures/*.json")), (
        "a loaddata fixture is a creation path outside every function this "
        "file enumerates"
    )


def test_the_enumerator_reached_the_whole_app_tree():
    """An instrument asserts its own reach, and any number it produces is
    quoted with the count actually reached (`CLAUDE.md` rule 10, fourth
    disguise). A walk that silently parsed four files of seventy-eight would
    report an empty, complete-looking enumeration."""
    modules = app_modules()
    assert len(modules) >= 70, f"only {len(modules)} modules under apps/ were parsed"
    _, sources = _walk_the_tree()
    assert len(sources) == len(modules)
    assert "apps/accounts/services.py" in sources
