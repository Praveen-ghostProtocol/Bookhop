r"""P15's sweep: the boundary, both sides of the name rule, and early failure.

`apps/listings/staff.py` says *"the clock is an age, not a name"* and
`tests/contract/test_the_review_copies_expire.py` asserts that one stale
directory goes and one fresh directory stays, in both modes. This file asks
the three questions that leaves, which are the ones the caller named:

1. **Where exactly is the boundary?** Two points do not locate a threshold.
   A sweep with the comparison inverted, or reading a 24-*minute* constant,
   passes a 25h-goes / 60s-stays pair.
2. **Does the name rule have a second side?** `CLAUDE.md` rule 10's
   corollary: *"where a rule splits a set, both sides are rows."* A sweep
   that `rm -rf`'d every stale thing in `gettempdir()` satisfies every
   assertion in the sibling file — and `gettempdir()` on a developer's box
   holds pytest's own directories, pip's build trees and the operating
   system's. The permitted side (ours goes) is covered; the forbidden side
   (nothing else goes) is not.
3. **Does it run when the invocation fails?** The design claim is that the
   sweep is *"first, before anything can fail"*, because *"the invocation
   that cleans up is rarely the one that made the mess"* — and the most
   likely way a review invocation fails is a mistyped `--staff`. If the
   sweep sat after that, the copies would expire only on a successful run,
   which is not a clock.

**These copies are a student's bedroom photographs on an operator's laptop**
(`COMPLIANCE.md` §7 row 25), so the fixtures here contain four bytes of
JPEG and no personal data of any kind.
"""

import pathlib
import shutil
import tempfile
import time

import pytest
from django.core.management import CommandError, call_command

pytestmark = pytest.mark.django_db

HOUR = 3600


@pytest.fixture
def temp_root():
    """A private root that stands in for `gettempdir()`.

    `sweep_review_copies` takes an `extra_root`, which is the `--photos DIR`
    mode, so the sweep can be aimed at a directory this test owns. Aiming it
    at the real `gettempdir()` to assert *what it does not delete* would mean
    planting decoys among the developer's own files.
    """
    root = pathlib.Path(tempfile.mkdtemp(prefix="qa-p15-root-"))
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _aged(parent, name, age_seconds, as_file=False):
    parent.mkdir(parents=True, exist_ok=True)
    target = pathlib.Path(parent) / name
    if as_file:
        target.write_bytes(b"\xff\xd8\xff\xd9")
    else:
        target.mkdir()
        (target / "listing-1-1.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    when = time.time() - age_seconds
    for path in sorted(target.rglob("*"), reverse=True) if target.is_dir() else []:
        __import__("os").utime(path, (when, when))
    __import__("os").utime(target, (when, when))
    return target


# --- 1 · the boundary -------------------------------------------------------


@pytest.mark.parametrize(
    "age,survives,why",
    [
        (0, True, "created this instant — the moderator is opening it"),
        (30 * 60, True, "half an hour into a review"),
        (23 * HOUR, True, "opened at 5pm yesterday, read at 4pm today"),
        (24 * HOUR - 60, True, "one minute inside the ceiling"),
        (24 * HOUR + 60, False, "one minute past the ceiling"),
        (25 * HOUR, False, "the stated stale case"),
        (30 * 24 * HOUR, False, "a month of unswept photographs"),
    ],
)
def test_the_ceiling_is_twenty_four_hours_from_both_directions(
    temp_root, age, survives, why
):
    """Seven points across the threshold, each its own subject.

    One assertion over a list would let a second wrong answer hide inside
    the first (rule 10's corollary on marks).
    """
    from apps.listings.staff import REVIEW_COPY_TTL_SECONDS, sweep_review_copies

    assert REVIEW_COPY_TTL_SECONDS == 24 * HOUR, (
        "COMPLIANCE.md §7 row 25 rules one working day; the constant says "
        f"{REVIEW_COPY_TTL_SECONDS}s, so the rows above test a different rule"
    )
    target = _aged(temp_root, "bookhop-review-boundary", age)
    sweep_review_copies(str(temp_root))

    assert target.exists() is survives, (
        f"a review copy {age}s old ({why}) was "
        f"{'deleted' if survives else 'kept'}; the ceiling is "
        f"{REVIEW_COPY_TTL_SECONDS}s and the comparison must be an age"
    )


# --- 2 · the other side of the name rule ------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "pytest-of-praveen",
        "pip-build-env-x7",
        "bookhop-export-stale",
        "review-bookhop-stale",
        "bookhopreview-stale",
    ],
)
def test_a_stale_directory_that_is_not_a_review_copy_is_left_alone(temp_root, name):
    """The forbidden side of the split, which nothing asserted.

    Every name here is older than the ceiling, so an age-only sweep takes
    all of them. `bookhop-export-stale` and `review-bookhop-stale` are the
    near misses that a sloppy `in` test would catch; the upper-case one is
    there because a case-insensitive match on Windows would be a different
    rule from the one the module documents.
    """
    from apps.listings.staff import sweep_review_copies

    bystander = _aged(temp_root, name, 30 * 24 * HOUR)
    ours = _aged(temp_root, "bookhop-review-stale", 30 * 24 * HOUR)

    removed = sweep_review_copies(str(temp_root))

    assert not ours.exists(), "the premise failed: our own stale copy survived"
    assert bystander.exists(), (
        f"the sweep deleted {name!r}, which it does not own. The rule is "
        "a prefix *and* an age; an age-only sweep inside gettempdir() "
        "deletes other programs' working directories"
    )
    assert bystander not in removed


def test_whether_the_prefix_match_is_case_sensitive(temp_root):
    """NOT VERIFIABLE ON THIS PLATFORM, and it skips rather than passes.

    `pathlib.Path.glob` inherits the filesystem's case rules, so
    `bookhop-review-*` matches `BOOKHOP-REVIEW-x` on Windows and NTFS and
    does not on Linux and ext4 — the deployment target (`INFRA.md` §1). The
    two cases cannot even coexist as directories here, which is why the row
    came out of the parametrised list above rather than being quietly
    dropped.

    Nothing creates such a name today, so this is a recorded divergence and
    not a defect: `REVIEW_COPY_PREFIX` is the only writer. It is written down
    because a future `--photos` on a case-preserving share would make the
    sweep's reach differ between the operator's laptop and the VM, and
    "it works on my machine" is the symptom.
    """
    pytest.skip(
        "NOT VERIFIABLE ON THIS PLATFORM (platform=win32/NTFS, slice=S2): "
        "the filesystem is case-insensitive, so a directory whose prefix "
        "differs only in case cannot be created alongside ours and "
        "`Path.glob` would match it anyway. On the ext4 deployment target "
        "it would not match. ASSUMED THERE, not verified here."
    )


def test_a_stale_file_with_the_prefix_is_not_a_directory_and_survives(temp_root):
    """`is_dir()` is load-bearing, so it gets a row.

    `--photos` only ever creates directories, so a *file* with the prefix is
    something else — and `shutil.rmtree` on it would raise, which the sweep
    catches and logs, leaving the real stale copies in the same root
    unswept if the error had not been caught per child.
    """
    from apps.listings.staff import sweep_review_copies

    decoy = _aged(temp_root, "bookhop-review-notadirectory", 30 * 24 * HOUR, as_file=True)
    ours = _aged(temp_root, "bookhop-review-stale", 30 * 24 * HOUR)

    sweep_review_copies(str(temp_root))

    assert decoy.exists(), "the sweep deleted a file it does not own"
    assert not ours.exists(), (
        "a non-directory with the prefix stopped the sweep reaching the "
        "real stale copy beside it"
    )


# --- 3 · the clock runs on a failed invocation ------------------------------


def test_the_sweep_runs_even_when_the_command_fails_on_its_first_argument(
    temp_root, capsys
):
    """A mistyped `--staff` must not postpone the retention clock.

    The design claim is *"first, before anything can fail"*. The most likely
    failure of a review invocation is the staff email, and if the sweep ran
    after it the copies would expire only on successful runs — which means
    an operator who typo'd their own address twice has photographs on disk
    for as long as the typing lasts.
    """
    from apps.listings.staff import sweep_review_copies  # noqa: F401 — existence

    stale = _aged(temp_root, "bookhop-review-stale", 30 * 24 * HOUR)

    with pytest.raises(CommandError):
        call_command(
            "review_listings",
            "--staff", "nobody@nowhere.invalid",
            "--photos", str(temp_root),
        )

    assert not stale.exists(), (
        "the command failed on --staff and the stale review copies survived, "
        "so the 24h clock only runs on invocations that succeed"
    )
    assert str(stale) in capsys.readouterr().out, (
        "the sweep deleted a student's photographs and printed nothing, so "
        "the operator cannot tell it happened"
    )


def test_a_fresh_copy_survives_an_invocation_that_fails(temp_root):
    """Both sides, on the early-failure path too.

    The early sweep is the one most likely to be written as `rm -rf` on the
    way out of a failing command.
    """
    fresh = _aged(temp_root, "bookhop-review-fresh", 60)

    with pytest.raises(CommandError):
        call_command(
            "review_listings",
            "--staff", "nobody@nowhere.invalid",
            "--photos", str(temp_root),
        )

    assert fresh.exists(), (
        "the failing invocation took the copies the moderator is reading"
    )
