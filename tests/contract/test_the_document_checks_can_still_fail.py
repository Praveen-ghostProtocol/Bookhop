r"""Guards for the guards that read a document.

`CLAUDE.md` rule 10, corollary: *"write a guard for a guard when the guard is
forward-dated or silent."* A check that decides a finding by searching a
specification document is silent in exactly that way — it goes green when the
document gains the word it looks for, whoever added it and for whatever
reason.

**That happened on this commit.** F44's media check read
`re.search(r"\bmedia\b|tarball|tar -|photo", restore)` over `INFRA.md` §3.3.
An unrelated edit — step 6b, a `curl` asserting the `/media/` nginx location
is `internal`, which is access control and opens no archive — put the words
"media" and "photo" into that section, and **the finding reported itself
closed while nothing about the backup's media half had changed.** cto
narrowed the check to ask for the control (extract an archive **and** resolve
a stored file reference). This file is the guard on that narrowing, and on
one other instrument found by inspecting every test in the tree that reads a
document.

Nothing here reads `INFRA.md` with a regex of its own: the first test drives
**the real check** and asserts it still fails with its own words, so there is
one definition of the control and this file cannot drift from it (rule 11).
"""

import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]


def test_the_f44_media_check_still_fails_and_still_says_why():
    """**Inverted, per rule 10's fifth disguise.**

    From outside, *"the finding is closed"* and *"the check went green for an
    unrelated reason"* are indistinguishable — which is the precise failure
    this commit contains. So the assertion is the other way round: while the
    restore test does not open the media archive, the check **must** fail,
    and it must fail with the sentence that names the gap.

    **This test goes red on the commit that genuinely closes F44**, and that
    is the design: at that moment the restore test does open the tarball, the
    probe passes, this fails by name, and whoever closed it deletes this test
    in the same diff. A greening for any other reason fails here first.
    """
    from tests.e2e.test_s2_sell_journey import (
        test_the_backup_scope_and_the_restore_test_cover_the_same_things as probe,
    )

    with pytest.raises(AssertionError) as caught:
        probe()
    message = str(caught.value)
    assert "never opens it" in message, (
        "F44's check failed for a different reason than the open finding. "
        "Either the media half was closed and this guard is now stale, or "
        f"§3.1's backup scope changed, which is a bigger finding:\n{message}"
    )


def test_the_word_grep_this_replaced_would_be_green_right_now():
    """The measurement that justifies the narrowing, kept as a measurement.

    The pattern below is **dead** — it is the pre-narrowing regex, reproduced
    here and nowhere else, so that the claim *"this check had stopped being
    able to fail"* is a number rather than a story. If it ever stops matching,
    the narrowing's rationale has expired and this test says so.
    """
    infra = (REPO / "company" / "architecture" / "INFRA.md").read_text(encoding="utf-8")
    restore = infra[infra.index("### 3.3"): infra.index("### 3.4")]
    retired = re.search(r"\bmedia\b|tarball|tar -|photo", restore, re.I)
    assert retired, (
        "the retired word-grep no longer matches §3.3, so the recorded "
        "reason for narrowing it — that an unrelated edit made it pass — is "
        "no longer demonstrable. Re-measure before trusting the note."
    )
    assert not re.search(r"\btar\b[^\n]*\s-[a-zA-Z]*x|\bunzip\b|\bzcat\b", restore, re.I), (
        "§3.3 now extracts an archive, so F44's media half may be closed and "
        "the guard above is the test to read, not this one"
    )


def test_the_narrowed_check_is_satisfiable_at_all():
    """Rule 10's second disguise: *a requirement that cannot be satisfied.*

    A control written so that no reachable document can meet it is as bad as
    one that cannot fail — it just fails in the honest direction, and gets
    deleted under schedule pressure instead of edited. So the fix cto
    describes — *"extract the tarball and assert that a sample of
    `listing_photos.storage_key` resolves to a file"* — is written out here
    and shown to pass both halves of the predicate.
    """
    proposed = (
        "5b. Extract the media archive and resolve a sample of the rows:\n"
        "    tar -xzf media-<UTC-ts>.tar.gz -C /var/lib/bookhop/\n"
        "    for every sampled listing_photos.storage_key, assert the file "
        "exists and its sha256 matches the row.\n"
    )
    extracts = re.search(r"\btar\b[^\n]*\s-[a-zA-Z]*x|\bunzip\b|\bzcat\b", proposed, re.I)
    resolves = re.search(r"storage_key|storage_token|listing_photos\b", proposed, re.I)
    assert extracts and resolves, (
        "the step cto proposes as the fix does not satisfy the narrowed "
        "check, so the check asks for something nobody can write and will be "
        "edited rather than met (CLAUDE.md rule 13's prediction)"
    )


def test_the_open_critical_citation_is_asserted_on_the_reason_not_the_file():
    """A second instance of the same shape, found by inspection, closed here.

    `tests/contract/test_open_criticals_are_honest.py` extracts the two
    `xfail` marks out of `test_least_privilege.py`, asserts both are
    `strict=True` — and then asserts the memo citation with
    `re.search(r"ENGINEERING-MEMO\\s*§1", source)` over the **whole file**.
    Measured: `ENGINEERING-MEMO` occurs twice in that file, once in the
    module docstring (line 3) and once in the `xfail` reason (line 136). **The
    docstring alone satisfies it**, so the reason could lose the citation and
    the assertion the test's own message describes — *"the xfail reason no
    longer cites the memo section it tracks"* — would still pass.

    **And the regex instrument cannot be fixed by moving the search**, which
    is the second half of the finding: both marks are written
    `reason=LIVE_CRITICAL`, a module constant, so the citation is not in the
    decorator text at all. A substring check over the extracted marks would
    go red on correct code. The reason has to be **resolved**, which is what
    this does: parse the module, take each `xfail` decorator's `reason`, bind
    a `Name` to its module-level assignment, and assert the string a reader
    actually sees on a skipped test.

    This is additive and green, not a correction to their file.
    """
    import ast

    source = (REPO / "tests" / "unit" / "test_least_privilege.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    constants = {
        target.id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
        for target in node.targets
        if isinstance(target, ast.Name) and isinstance(node.value.value, str)
    }

    reasons = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for deco in node.decorator_list:
            if not (isinstance(deco, ast.Call) and getattr(deco.func, "attr", "") == "xfail"):
                continue
            for keyword in deco.keywords:
                if keyword.arg != "reason":
                    continue
                if isinstance(keyword.value, ast.Constant):
                    reasons.append((node.name, keyword.value.value))
                elif isinstance(keyword.value, ast.Name):
                    reasons.append((node.name, constants.get(keyword.value.id, "")))

    assert len(reasons) == 2, (
        "expected the two tracked criticals with a resolvable reason; "
        f"resolved {len(reasons)}. A reason this walk cannot resolve is a "
        "reason a reader cannot read either."
    )
    for name, reason in reasons:
        assert re.search(r"ENGINEERING-MEMO\s*§1", reason), (
            f"{name}()'s xfail reason — the sentence a reader sees on the "
            "skipped test — does not cite the memo section it tracks. A "
            "citation elsewhere in the file satisfies the sibling guard and "
            f"does not help that reader: {reason!r}"
        )
