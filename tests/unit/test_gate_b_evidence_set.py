"""Gate B's evidence set is `CLOSED-TEST.md` §4.1's, item by item.

**Why this file exists.** The gate was built over two commits and the suite was
green after both, while the code read **nine** things and the tests measured
**three** — `GATE_B_BOUNDS`, plus the typed ceiling and expiry. Nothing
exercised `takedown_sop_ref`, `escalation_contact_ref`,
`incident_runbook_ref`, the FK resolution behind `notice_version_ids`, the
`legal_entities` columns, or the not-asserted side. Two of those were simply
**absent** from the code while §4.1 listed them as required, and the way that
was discovered was reading the document, not running the suite.

So this file does two things that `test_gate_b_account_creation.py` does not:

1. **Parametrises off the constants**, so an item added to
   `GATE_B_EVIDENCE_REFS` or `GATE_B_LEGAL_ENTITY_FIELDS` is covered the moment
   it is added rather than when somebody remembers to write its test.
2. **Derives the required set from §4.1's own table** and compares it with the
   code's. This is `CLAUDE.md` rule 11 applied to a rule that lives in a
   document: one definition, two readers. The alternative is the hand-copied
   list this project has already seen disagree three ways, where *"the agent
   whose job was to catch the divergence judged the control against its own
   copy"*.

**The two layers are not redundant, and that was measured rather than
argued.** Parametrising off a constant means an item **deleted** from the
constant takes its own test with it: dropping `incident_runbook_ref` from
`GATE_B_EVIDENCE_REFS` leaves `test_a_row_missing_any_required_ref...` green
with one fewer case, which is how a list *"gets edited when one entry
misfires, and coverage is silently lost with it"* (rule 11). Measured here:
that mutation turns **exactly one** test red, and it is
`test_the_required_set_is_the_documents_set`. Removing the cert-in half turns
four red, three of them from the parametrised layer. Neither layer sees both
mutations, which is rule 12's point — *layers do different jobs* — and this is
the pass that checked it instead of naming it.

**What this file cannot do.** §4.1 is prose and this reads its table, so an
item moved into the surrounding paragraphs becomes invisible here. The ceiling
is declared rather than hidden, and
`test_the_table_reader_reached_the_whole_table` asserts the reader's own reach
so the number it produces is quoted with the count actually read.
"""

import re
from pathlib import Path

import pytest

from apps.core.scoping import (
    GATE_B_BOUNDS,
    GATE_B_CERT_IN_FIELDS,
    GATE_B_EVIDENCE_REFS,
    GATE_B_GRIEVANCE_FIELDS,
    GATE_B_LEGAL_ENTITY_FIELDS,
    GATE_B_NOT_ASSERTED,
    GATE_B_NOTICE_KINDS,
    assert_real_account_allowed,
)
from apps.core.errors import GateClosed

from .test_gate_b_account_creation import _ABSENT, BEFORE_EXPIRY, gate_b

ROOT = Path(__file__).resolve().parents[2]
CLOSED_TEST = ROOT / "company" / "evidence" / "CLOSED-TEST.md"

#: The one item §4.1 puts in a column rather than in `evidence`. Its own test is
#: `test_gate_b_account_creation.py::test_the_smaller_gate_is_still_a_named_humans_signature`,
#: which carries the deny-list; this file only asserts that the document names
#: exactly this one and no second column crept in.
DOCUMENTED_COLUMNS = {"authorised_by_human"}

#: Evidence the gate reads that §4.1 does not list, each with the decision that
#: put it there. **Empty, and that is the point.** It held
#: `completes_purchases` for one commit, which was one hand-made copy of a rule
#: that already had two homes — so §4.1 was amended (2026-11-04) to carry the
#: row, and the copy went away rather than being maintained. `CLAUDE.md`
#: rule 11: one definition, many readers.
#:
#: An empty allow-list still does work: `test_the_required_set_is_the_documents_set`
#: asserts the difference **equals** this set, so the next item added to the
#: gate without a document row fails there and has to be either documented or
#: registered here with its decision.
CODE_ONLY_EVIDENCE = set()


# --- the document's table, as data ----------------------------------------


def _expand(names):
    """`[a_name, _email, _phone]` → `[a_name, a_email, a_phone]`.

    §4.1 writes the two triples as ``grievance_officer_name`` / ``_email`` /
    ``_phone``, which is how a human reads it and not how a set compares. A
    leading-underscore token is a suffix on the first name's stem.
    """
    out, stem = [], None
    for name in names:
        if name.startswith("_"):
            assert stem is not None, f"{name} is a suffix with nothing to attach to"
            out.append(stem + name)
        else:
            out.append(name)
            stem = name.rsplit("_", 1)[0]
    return out


def section_4_1():
    """`{item: where it lives}` read out of §4.1's table.

    `where` is the table's own second cell, normalised to `evidence`,
    `legal_entities`, `column` or `not asserted`.
    """
    text = CLOSED_TEST.read_text(encoding="utf-8")
    body = text[text.index("### 4.1 "):text.index("### 4.2 ")]
    rows = {}
    for line in body.splitlines():
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells[0] == "Item":
            continue
        if "Not asserted" in cells[0]:
            # The items are in the note cell, and only in its first sentence:
            # `counsel_engagement_ref` follows as "recommended, not required",
            # which is neither asserted nor forbidden and is not a member of
            # either side of the split.
            required_absent = cells[2].split(". ")[0]
            for name in _expand(re.findall(r"`([^`]+)`", required_absent)):
                rows[name] = "not asserted"
            continue
        where = cells[1]
        where = (
            "legal_entities" if "legal_entities" in where
            else "evidence" if "evidence" in where
            else "column" if "column" in where
            else where
        )
        for name in _expand(re.findall(r"`([^`]+)`", cells[0])):
            rows[name] = where
    return rows


def _documented(where):
    return {item for item, lives in section_4_1().items() if lives == where}


def test_the_table_reader_reached_the_whole_table():
    """The instrument asserts its own reach (`CLAUDE.md` rule 10's fourth
    disguise). A reader that silently returned `{}` would make every
    comparison below pass against any code at all.
    """
    rows = section_4_1()
    assert len(rows) >= 14, f"read only {len(rows)} items out of §4.1's table: {sorted(rows)}"
    assert set(rows.values()) == {"evidence", "legal_entities", "column", "not asserted"}, (
        f"§4.1's 'where it lives' column has an unrecognised value: {sorted(set(rows.values()))}"
    )
    # Three items whose cells have different shapes: a plain one, one written
    # as a triple with suffix shorthand, and one that lives in the note cell.
    assert rows["takedown_sop_ref"] == "evidence"
    assert rows["cert_in_poc_phone"] == "legal_entities"
    assert rows["campus_mou_ref"] == "not asserted"


def test_the_suffix_shorthand_expands_the_way_the_document_writes_it():
    assert _expand(["grievance_officer_name", "_email", "_phone"]) == [
        "grievance_officer_name", "grievance_officer_email", "grievance_officer_phone",
    ]
    assert _expand(["cert_in_poc_name", "_email"]) == ["cert_in_poc_name", "cert_in_poc_email"]
    with pytest.raises(AssertionError):
        _expand(["_orphan"])


# --- the code's set is the document's set ---------------------------------


def test_the_required_set_is_the_documents_set():
    """**The assertion whose absence let two items go missing.**

    `incident_runbook_ref` and `cert_in_poc_name`/`_email`/`_phone` were listed
    as required in §4.1 and read by nothing. The suite was green, because a
    control that does not exist refuses nothing and breaks no test.
    """
    code = set(GATE_B_BOUNDS) | set(GATE_B_EVIDENCE_REFS)
    documented = _documented("evidence")

    assert not documented - code, (
        f"CLOSED-TEST.md §4.1 requires evidence the gate does not read: "
        f"{sorted(documented - code)}. A document's claim is not evidence "
        "(CLAUDE.md rule 9) — either read it in assert_real_account_allowed or "
        "amend §4.1 and say why."
    )
    assert code - documented == CODE_ONLY_EVIDENCE, (
        f"the gate reads evidence §4.1 does not require: "
        f"{sorted(code - documented - CODE_ONLY_EVIDENCE)}. A gate stricter "
        "than its ruling is a widening nobody ratified; add it to §4.1 or to "
        "CODE_ONLY_EVIDENCE with the decision that put it there."
    )


def test_the_legal_entity_columns_are_the_documents_columns():
    assert set(GATE_B_LEGAL_ENTITY_FIELDS) == _documented("legal_entities")
    assert set(GATE_B_LEGAL_ENTITY_FIELDS) == (
        set(GATE_B_GRIEVANCE_FIELDS) | set(GATE_B_CERT_IN_FIELDS)
    ), "the whole-set name must stay the union of its halves, not a third copy"
    assert not set(GATE_B_GRIEVANCE_FIELDS) & set(GATE_B_CERT_IN_FIELDS)


def test_the_not_asserted_side_is_the_documents_too():
    """Both sides of the split are rows (`CLAUDE.md` rule 10's corollary), and
    this is the side a future widening would quietly cross."""
    assert set(GATE_B_NOT_ASSERTED) == _documented("not asserted")


def test_the_document_names_exactly_one_column_item():
    assert _documented("column") == DOCUMENTED_COLUMNS


# --- every required item, refused when it is missing ----------------------


@pytest.mark.parametrize("missing", sorted(GATE_B_EVIDENCE_REFS))
def test_a_row_missing_any_required_ref_does_not_open_the_gate(db, legal_entity, missing):
    """Parametrised off the constant, so the next item added to it is covered
    by this test on the commit that adds it rather than on some later one."""
    gate_b(legal_entity, **{missing: _ABSENT})
    with pytest.raises(GateClosed) as raised:
        assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY)
    detail = raised.value.context["detail"]
    assert f"no evidence.{missing}" in detail, detail
    assert raised.value.context["reason"] in {
        "gate_b_evidence_missing", "gate_b_unbounded"
    }, raised.value.context["reason"]


@pytest.mark.parametrize("missing", sorted(GATE_B_EVIDENCE_REFS))
@pytest.mark.parametrize(
    ("blank", "what"),
    [
        ("", "empty"),
        ("   ", "spaces"),
        ("​", "zero-width space"),
        ("\t\n", "whitespace"),
    ],
)
def test_a_ref_without_a_visible_character_is_not_evidence(
    db, legal_entity, missing, blank, what
):
    """*"A string of spaces is not evidence of a signed MoU"*, and neither is a
    zero-width space — which is a **format** character, so it survives a strip
    and renders as nothing. `CLAUDE.md` rule 11 records a whitespace list that
    could never have caught it; `has_visible_character` is the one definition
    that does, and this asserts Gate B actually routes through it.
    """
    gate_b(legal_entity, **{missing: blank})
    with pytest.raises(GateClosed) as raised:
        assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY)
    assert missing in raised.value.context["detail"], f"{what} accepted for {missing}"


@pytest.mark.parametrize("field", sorted(GATE_B_LEGAL_ENTITY_FIELDS))
@pytest.mark.parametrize("blank", ["", "   ", "​", None])
def test_a_blank_legal_entity_column_does_not_open_the_gate(db, legal_entity, field, blank):
    from apps.core.models import LegalEntity

    gate_b(legal_entity)
    LegalEntity.objects.filter(id=legal_entity.id).update(**{field: blank})
    with pytest.raises(GateClosed) as raised:
        assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY)
    assert f"has no {field}" in raised.value.context["detail"]


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        *((f, "gate_b_grievance_officer_missing") for f in sorted(GATE_B_GRIEVANCE_FIELDS)),
        *((f, "gate_b_cert_in_poc_missing") for f in sorted(GATE_B_CERT_IN_FIELDS)),
    ],
)
def test_the_refusal_names_the_instrument_that_was_breached(db, legal_entity, field, reason):
    """**The reason code is the whole point of two loops instead of one.**

    It is what the `bookhop.security` stream carries and what an operator greps
    for, so a missing CERT-In point of contact reporting itself as a
    grievance-officer problem sends someone to IT Rules r.3(2)(a) to fix a
    CERT-In Directions obligation.
    """
    from apps.core.models import LegalEntity

    gate_b(legal_entity)
    LegalEntity.objects.filter(id=legal_entity.id).update(**{field: ""})
    with pytest.raises(GateClosed) as raised:
        assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY)
    assert raised.value.context["reason"] == reason


@pytest.mark.parametrize("field", sorted(GATE_B_NOT_ASSERTED))
def test_an_unincorporated_entity_still_opens_the_gate(db, legal_entity, field):
    """**The permitted side, and it is the reason the reduced gate exists.**

    §4.1 does not read `cin`, `incorporation_date` or `inc20a_filed_at`, and
    §1.1 found `campus_mou_ref` *unsatisfiable at this scope*. A gate that
    demanded any of them at shape 1 would be rule 10's second disguise — a
    criterion that cannot be satisfied — and the four-week incorporation that
    `CLOSED-TEST.md` exists to take off the critical path would be back on it.
    """
    from apps.core.models import LegalEntity

    gate_b(legal_entity)
    if field in {f.name for f in LegalEntity._meta.get_fields()}:
        LegalEntity.objects.filter(id=legal_entity.id).update(**{field: None})
    assert assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY) is not None


# --- the one item verifiable end to end -----------------------------------


@pytest.mark.parametrize("kind", GATE_B_NOTICE_KINDS)
def test_a_notice_kind_that_resolves_to_nothing_does_not_open_the_gate(db, legal_entity, kind):
    """§4.1 calls this *"the one end-to-end verifiable item"*, so it is the one
    item tested by resolution rather than by presence. Each required kind is
    withheld in turn: publishing one and counting the list would pass.
    """
    from apps.accounts.models import NoticeVersion

    published = [
        NoticeVersion.objects.create(
            kind=other, version="resolve.1", locale="en",
            body_md=f"# {other}", sha256=str(abs(hash(other)))[:64].ljust(64, "0"),
        ).id
        for other in GATE_B_NOTICE_KINDS
        if other != kind
    ]
    gate_b(legal_entity, notice_version_ids=published)
    with pytest.raises(GateClosed) as raised:
        assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY)
    detail = raised.value.context["detail"]
    assert raised.value.context["reason"] == "gate_b_notices_unpublished"
    assert kind in detail, detail


@pytest.mark.parametrize(
    "ids",
    [
        [999999, 999998],
        ["1", "2"],
        [True, False],
        [None],
        "1,2",
        {"privacy": 1},
    ],
)
def test_ids_that_cannot_resolve_fail_closed(db, legal_entity, ids):
    """Non-integer and dangling ids resolve to nothing, which is the
    fail-closed direction and needs no second refusal.

    `[True, False]` is here because `bool` is an `int` in Python: without the
    explicit `not isinstance(i, bool)` in the guard, `True` would be read as
    primary key 1 and a notice could be "published" by a JSON `true`.
    """
    gate_b(legal_entity, notice_version_ids=ids)
    with pytest.raises(GateClosed) as raised:
        assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY)
    assert raised.value.context["reason"] in {
        "gate_b_notices_unpublished", "gate_b_evidence_missing"
    }


def test_a_resolving_pair_opens_the_gate(db, legal_entity):
    """The permitted side of the resolution split. Without it, a guard that
    refused every list would pass every test above.
    """
    row = gate_b(legal_entity)
    assert assert_real_account_allowed(is_seed=False, now=BEFORE_EXPIRY) == row
