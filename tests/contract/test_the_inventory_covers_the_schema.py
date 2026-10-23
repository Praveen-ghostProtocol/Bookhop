"""COMPLIANCE.md §7.1 and rows 26-28, asserted rather than claimed.

**Why this file exists.** §7's standing rule is *"every new personal-data field
needs a row here before it ships; a field without a row is a compliance defect
by definition."* The rule was enforced by a sentence in the same section
counting the free-text fields — *"there are now two free-text fields in the
system"* — and the count was wrong in both directions: it named two columns
that are specified and unbuilt (`search_events.query_norm`,
`support_work_log.note`) and missed three that are in the schema
(`book_requests.free_text_title`, `book_requests.course_code`,
`data_subject_requests.stated_problem`). A hand-maintained number has no reader
that can fail, which is `CLAUDE.md` rule 11's failure mode exactly. §7.1
replaces the number with a registry and this module is its reader.

Each test asserts a control **exists** (so a missing guard fails by name) and
that its property **holds**. Every `xfail` is `strict=True` and carries **one
subject**, never the module, so a second defect cannot hide inside the first —
and strict means none of them can pass silently: the day a fix ships the test
turns XPASS-as-failure and forces its own mark off in that commit.

Owned by `privacy-compliance`. Nothing here is a production fix.
"""

import inspect
import re
from pathlib import Path

import pytest
from django.apps import apps
from django.utils import timezone

REPO = Path(__file__).resolve().parents[2]
COMPLIANCE = REPO / "company" / "evidence" / "COMPLIANCE.md"
DELETE_CARD = REPO / "templates" / "delete_confirm.html"
STAFF_MODULE = REPO / "apps" / "listings" / "staff.py"

#: Django's own tables are not BookHop's inventory. `django_session` has a §7
#: retention rule and a purge limb, but its columns are the framework's.
_NOT_OURS = {"contenttypes", "sessions", "auth", "admin"}


def _measured_free_text_columns():
    """Every `table.column` in the live schema shaped like a free-text box.

    **The ceiling is declared in §7.1 beside the registry, not only here:** a
    nullable `TextField` with no `choices`. It does not see a non-null
    `CharField`, a `jsonb` column, or personal data held in a structured type.
    """
    found = set()
    for model in apps.get_models():
        if model._meta.app_label in _NOT_OURS:
            continue
        for field in model._meta.get_fields():
            if not getattr(field, "get_internal_type", None):
                continue
            if field.get_internal_type() != "TextField":
                continue
            if getattr(field, "choices", None) or not getattr(field, "null", False):
                continue
            found.add(f"{model._meta.db_table}.{field.name}")
    return found


def _registry():
    """Parse §7.1's ```inventory block into `{name: rhs}`. Skips if it is gone."""
    if not COMPLIANCE.is_file():
        pytest.skip(f"{COMPLIANCE} is not readable from this checkout")
    text = COMPLIANCE.read_text(encoding="utf-8")
    block = re.search(r"```inventory\n(.*?)\n```", text, re.S)
    assert block, (
        "COMPLIANCE.md §7.1's ```inventory block is gone. The registry is the "
        "only thing asserting the inventory is complete; deleting it is a "
        "compliance regression, not a tidy-up."
    )
    entries = {}
    for line in block.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, rhs = line.partition("->")
        assert rhs.strip(), f"§7.1 entry with no row or reason: {line!r}"
        entries[name.strip()] = rhs.strip()
    return entries, text


def _row_ids(doc):
    """The row numbers §7's table actually defines."""
    return {
        int(m.group(1))
        for m in re.finditer(r"^\| (\d+) \| \*\*", doc, re.M)
    }


def test_every_free_text_column_has_an_inventory_entry():
    """§7.1 covers the live schema in **both** directions.

    A column with no entry fails by name. An entry for a column that no longer
    exists also fails, so the registry cannot rot into a list that is merely
    longer than the schema — which is how a stale allow-list reports coverage
    it does not have.
    """
    measured = _measured_free_text_columns()
    entries, doc = _registry()

    # The instrument asserts its own reach (rule 10). A schema read that found
    # nothing would make every assertion below vacuously true.
    assert len(measured) >= 10, (
        f"only {len(measured)} free-text columns measured from the live schema; "
        "the model introspection is broken, so this test is not measuring "
        "anything and must not be read as coverage"
    )
    assert entries, "§7.1's registry parsed to zero entries"

    wildcards = {n.split(".", 1)[0] for n in entries if n.endswith(".*")}
    exact = {n for n in entries if not n.endswith(".*")}

    missing = sorted(
        c for c in measured
        if c not in exact and c.split(".", 1)[0] not in wildcards
    )
    assert not missing, (
        "free-text columns in the schema with no §7.1 entry, so no stated "
        f"purpose and no retention period: {missing}. §7's standing rule is "
        "that a field without a row is a compliance defect."
    )

    measured_tables = {c.split(".", 1)[0] for c in measured}
    stale = sorted(
        [n for n in exact if n not in measured]
        + [n for n in entries if n.endswith(".*") and n.split(".", 1)[0] not in measured_tables]
    )
    assert not stale, (
        f"§7.1 entries for columns that no longer exist: {stale}. Remove them "
        "in the commit that removes the column, or the registry starts "
        "claiming coverage of a schema it has stopped describing."
    )

    # Every entry resolves: a row number that §7 really defines, or NOT-PD with
    # a reason. Each entry carries its own rule, so fixing one cannot silently
    # delete the coverage of another (rule 11).
    defined = _row_ids(doc)
    assert {1, 3, 26, 27, 28} <= defined, (
        f"§7's table does not define the rows this test reads: {sorted(defined)}"
    )
    for name, rhs in sorted(entries.items()):
        if rhs.isdigit():
            assert int(rhs) in defined, f"{name} points at §7 row {rhs}, which does not exist"
        else:
            assert rhs.startswith("NOT-PD"), f"{name}: {rhs!r} is neither a row number nor NOT-PD"
            assert len(rhs.split(":", 1)[-1].strip()) >= 20, (
                f"{name} is excluded with no usable reason: {rhs!r}. An exemption "
                "without a reason is a widening, not a classification."
            )


@pytest.mark.django_db
def test_an_erased_want_is_purged_when_its_clock_runs_out(student):
    """A due want loses its text. **A want that is not yet due keeps it.**

    Both sides are rows (rule 10's corollary). Asserting only the first would
    be satisfied by a purge limb that empties the table, which is a worse
    defect than the one this test exists for: R-01 — *"a want with no supply is
    the measurement that tells us the campus is illiquid"* — needs the row for
    a year.
    """
    from apps.accounts.services import erase_account
    from apps.core.jobs import REGISTRY
    from apps.listings.models import BookRequest
    from apps.listings.services import create_request

    due = create_request(student, free_text_title="Kannan hostel room 214", course_code="ma8151")
    fresh = create_request(student, free_text_title="A want still inside its year", course_code="cs1")
    erase_account(student)

    now = timezone.now()
    BookRequest.all_objects.filter(id=due.id).update(purge_due_at=now - timezone.timedelta(days=1))
    BookRequest.all_objects.filter(id=fresh.id).update(purge_due_at=now + timezone.timedelta(days=200))

    for kind in ("retention.purge", "listings.purge_media"):
        if kind in REGISTRY:
            REGISTRY[kind]({"reschedule": False, "run_id": "pytest"})

    due.refresh_from_db()
    fresh.refresh_from_db()
    assert due.free_text_title is None and due.course_code is None, (
        "a want past its purge_due_at still carries the student's own words "
        "after they deleted their account"
    )
    assert fresh.free_text_title == "A want still inside its year", (
        "the purge took a row that was not due — R-01's measurement needs the "
        "want for its full year"
    )


def test_the_want_is_on_one_side_of_the_purge_split():
    """The **existence** half of the control above, so it fails by name.

    `PURGE_SKIP_LIST`'s own docstring: *"a table here is one the purge job must
    never touch, **with the reason**, so S6 does not have to remember it and so
    a reviewer can see that the omission is a decision."* A clocked table in
    neither set has no decision recorded either way.
    """
    from apps.accounts.services import PURGE_SKIP_LIST
    from apps.core.jobs import REGISTRY

    clocked = {
        m._meta.db_table
        for m in apps.get_models()
        if any(getattr(f, "name", None) == "purge_due_at" for f in m._meta.get_fields())
    }
    assert "book_requests" in clocked, "book_requests lost its retention clock entirely"

    if "book_requests" in PURGE_SKIP_LIST:
        assert len(PURGE_SKIP_LIST["book_requests"].strip()) >= 20, (
            "book_requests is skip-listed with no usable reason"
        )
        return

    # Source-level, and deliberately so: this is the existence diagnosis. The
    # behaviour is asserted by the test above, against a real row and a real
    # clock, because a handler that names the table proves nothing about what
    # it does to it.
    walked = any(
        "book_requests" in inspect.getsource(fn) or "BookRequest" in inspect.getsource(fn)
        for kind, fn in REGISTRY.items()
        if "purge" in kind or "retention" in kind
    )
    assert walked, (
        "no purge handler names book_requests and PURGE_SKIP_LIST does not "
        "either. §7 rows 26-27 state a one-year retention; nothing enforces it."
    )


def test_the_deletion_card_enumerates_the_want():
    """The enumeration is the assertion, so an omission is a false statement.

    COPY-DECK v1.4 withdrew *"Everything else goes now."* because it claimed
    more was deleted than is, and replaced it with a list: *"the card asserts
    only what it enumerates, and the list is the assertion."* Wants survive
    `erase_account` and are not in the list.

    Keyed on a **named `msgctxt`**, never a keyword, so it cannot go green on a
    reword of an existing item.
    """
    if not DELETE_CARD.is_file():
        pytest.skip(f"{DELETE_CARD} is not in this checkout")
    card = DELETE_CARD.read_text(encoding="utf-8")

    # Reach: if the card were moved or rewritten, a bare absence check below
    # would pass for the wrong reason.
    known = [f"erase.retained.{k}" for k in
             ("transfers", "chat", "reports", "email_hash", "account", "age", "audit", "consents")]
    present = [k for k in known if k in card]
    assert len(present) >= 8, (
        f"only {len(present)} of the eight known erase.retained.* items found in "
        f"{DELETE_CARD}; this test is not reading the card it thinks it is"
    )

    assert "erase.retained.wants" in card, (
        "the deletion card does not enumerate the wants a student typed, which "
        "survive erase_account with their free text intact"
    )


@pytest.mark.django_db
def test_the_want_box_has_a_bound_on_every_path(student):
    """The bound is asserted at **the service**, not at the form.

    The boundary §7 claims is *"a bound in the service that writes it"*, and
    that is where this asserts it — not at the boundary the implementation
    happens to have chosen. Asserting it on `WantedForm` would be green today
    and would say nothing about the API path, which has no cap at all.
    """
    from apps.core.errors import ValidationFailed
    from apps.listings.services import create_request

    with pytest.raises(ValidationFailed):
        create_request(student, free_text_title="x" * 5000, course_code=None)


def test_no_staff_path_reads_the_want_text():
    """**Inverted guard.** Green today, and built to go red (rule 10).

    Rows 26-27's access-logging condition cannot be asserted as *"the log
    fires"*, because the EC-17 staff view that `PRD.md` and `JOURNEYS.md` both
    claim for `free_text_title` does not exist: there is nothing to log, and a
    test for it would skip for ever while *"not yet running"* and *"running and
    passing trivially"* stayed indistinguishable from outside.

    So the ruled path is inverted: **the day `apps/listings/staff.py` reads a
    `BookRequest`, this fails**, and the `personal_data_access_log` row lands in
    the same commit as the first reader.
    """
    if not STAFF_MODULE.is_file():
        pytest.skip(f"{STAFF_MODULE} is not in this checkout")
    source = STAFF_MODULE.read_text(encoding="utf-8")

    # A guard for the guard: prove this grep would find a model reference if
    # there were one. Without it, a renamed module or an import-free rewrite
    # makes the assertion below pass for the wrong reason.
    assert "Listing" in source, (
        f"{STAFF_MODULE} does not mention Listing, so this grep is not looking "
        "at the staff console and its silence about BookRequest means nothing"
    )

    reads_wants = [
        line.strip()
        for line in source.splitlines()
        if ("BookRequest" in line or "book_requests" in line) and not line.strip().startswith("#")
    ]
    assert not reads_wants, (
        "a staff path now reaches the want rows: "
        f"{reads_wants}. §7 rows 26-27 require a personal_data_access_log row "
        "on the first staff reader of free_text_title or course_code, and "
        "aggregate-only display. Write the log, then narrow this guard."
    )
