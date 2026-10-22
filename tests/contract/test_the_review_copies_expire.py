r"""P15 — moderation working copies of listing photographs expire on a clock.

`review_listings --photos` writes decrypted copies of a student's
photographs — taken, for a used textbook, inside that student's room — onto
an operator's filesystem. Review R-R6 shipped the access half (a
`personal_data_access_log` row) and a printed `rm -rf`. `COMPLIANCE.md` §7
row 25 rules that **a printed reminder is not a retention period**: the
purpose is served when the decision is logged, DPDP s8(7) requires erasure
once it is, and the copies are the one category of personal data in the
inventory with no clock on it.

The ruling is a **bounded lifetime, 24 hours**, enforced by a sweep that runs
at the top of every `review_listings` invocation — the same command, run by
the same person, that made the copies in the first place.

**These two tests were written `xfail(strict=True)` before the sweep
existed, and the marks came off in the commit that built it** — which is
the mechanism working rather than a formality. Both turned
**XPASS-as-failure** on the first run against `sweep_review_copies`, which
is how a forward-dated check is kept distinguishable from one passing
trivially (`CLAUDE.md` rule 10's fifth disguise). Each mark sat on one
subject, not on the module, so a second defect could not have hidden inside
the first. They are ordinary tests now and they go red if the sweep stops.

Both tests assert existence *and* behaviour, and the behaviour assertion has
two sides: the stale directory goes, **and a fresh one stays**. A sweep that
only satisfied the first side would be `rm -rf` on the temporary directory,
which deletes the copies of the listing the moderator is looking at right now.
"""

import os
import pathlib
import tempfile
import time

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db

STALE = 25 * 3600  # older than the 24h ceiling in COMPLIANCE.md §7 row 25


def _aged_copy_dir(parent, name, age_seconds):
    """A directory shaped exactly like one `--photos` leaves behind."""
    target = pathlib.Path(parent) / name
    target.mkdir(parents=True)
    (target / "listing-1-1.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    when = time.time() - age_seconds
    os.utime(target / "listing-1-1.jpg", (when, when))
    os.utime(target, (when, when))
    return target


def test_a_stale_default_copy_directory_is_swept_by_the_next_run(staff, capsys):
    """The default path: `--photos` with no DIR lands in `gettempdir()`."""
    from apps.listings.staff import sweep_review_copies  # noqa: F401 — existence

    stale = _aged_copy_dir(tempfile.gettempdir(), "bookhop-review-stale-p15", STALE)
    fresh = _aged_copy_dir(tempfile.gettempdir(), "bookhop-review-fresh-p15", 60)
    try:
        call_command("review_listings", "--staff", staff.email)
        out = capsys.readouterr().out

        assert not stale.exists(), "a copy older than 24h survived the sweep"
        assert fresh.exists(), (
            "the sweep took the directory the moderator is working in — "
            "the ceiling is an age, not the name"
        )
        assert str(stale) in out, "the sweep must say what it deleted"
    finally:
        for path in (stale, fresh):
            if path.exists():
                __import__("shutil").rmtree(path)


def test_an_operator_chosen_directory_is_swept_too(staff, tmp_path, capsys):
    """`--photos DIR` stays — a reviewer on a remote VM needs a fetchable
    path — but it writes into a `bookhop-review-*` subdirectory of DIR, so
    **one** name rule covers both modes and the sweep reaches the chosen root
    as well. The alternative was a second rule, and two copies of one rule
    disagree (`CLAUDE.md` rule 11).

    The write side of that convention is asserted by the sibling test
    `test_the_command_writes_the_photos_where_a_human_can_open_them`, which
    is backend's file; this one asserts the sweep side, which is what makes
    the convention load-bearing rather than decorative.
    """
    from apps.listings.staff import sweep_review_copies  # noqa: F401 — existence

    chosen = tmp_path / "vm-review"
    stale = _aged_copy_dir(chosen, "bookhop-review-stale-p15", STALE)
    fresh = _aged_copy_dir(chosen, "bookhop-review-fresh-p15", 60)

    call_command("review_listings", "--staff", staff.email, "--photos", str(chosen))
    out = capsys.readouterr().out

    assert not stale.exists(), (
        "an operator-chosen root is not swept, so the copies there are "
        "unbounded — the mode the ruling was written about"
    )
    assert fresh.exists(), "the ceiling is an age, not the name"
    assert str(stale) in out
