r"""`listings/0004`'s backfill refuses — and the refusal has to be usable.

`CLAUDE.md` rule 10's sixth disguise is a refusal that fires on the wrong
signal, and its instruction is to *"exercise every refusal path and assert
the message text, not the exit status."* Backend's
`test_photo_storage_key.py` asserts the exception type and two fragments of
the message on one of the refusal's three reachable causes. This file asks
the three questions that leaves open, and they are QA's questions rather
than a second copy of backend's:

1. **Is every clause of the message there?** Two substrings out of a message
   that offers two different recoveries is a check that still passes if one
   recovery disappears. Each clause gets its own assertion so it fails by
   name.
2. **Does the refusal hold on the causes the existing test does not reach?**
   A stray file in the listing directory whose bytes are *not* this row's —
   the branch where adopting would attach some other photograph to this row —
   and a media directory that is gone entirely, which is the `INFRA.md` §3
   restore the message's first recovery is written for.
3. **Does the recovery the message prints actually work?** A message is only
   actionable if doing what it says converges. Recovery (1) — *"null it and
   re-run"* — is executed here, on a listing where one photograph is
   recoverable and one is not, and the surviving photograph's bytes are
   asserted byte-for-byte afterwards. That is the half that a message-text
   assertion cannot reach and that an operator at 3am will discover.

Written from `API-CONTRACT.md` A-25, `CLAUDE.md` rule 10 and
`COMPLIANCE.md` §7 row 9. The fixtures are reused rather than copied
(rule 11); nothing here reads the migration's source to decide what to
assert.
"""

import importlib
import io

import pytest

from tests.contract.test_photo_storage_key import (  # noqa: F401 — fixtures
    photo_on_a_live_listing,
    second_student,
)

pytestmark = pytest.mark.django_db


def _backfill():
    return importlib.import_module("apps.listings.migrations.0004_photo_storage_token")


def _unbackfill(photo):
    """Put one row back into the pre-A-25 state the backfill walks."""
    from apps.listings.models import ListingPhoto

    ListingPhoto.all_objects.filter(id=photo.id).update(storage_token=None)


def _refuse(photo):
    """Run the backfill and return the message it refused with."""
    from django.apps import apps as live_apps

    with pytest.raises(RuntimeError) as caught:
        _backfill().forward(live_apps, None)
    return str(caught.value)


# --- 1 · every clause, each failing by its own name --------------------------

#: One clause, one reason it has to be in the message. The operator reading
#: this is holding a failed migration on a production box.
CLAUSES = {
    "row ": "which row to look at",
    "will not mint a token": "why it stopped instead of continuing",
    "purge_media": "why a wrong token is not a cosmetic problem",
    "erasure": "the obligation that a lost object breaches",
    "NULL storage_key": "recovery 1 — the restore-without-media state",
    "re-run": "that either recovery ends by running this again",
    "put it back": "recovery 2 — the rolled-back-apply state",
    "INFRA.md": "where the backup scope that causes recovery 1 is written",
}


@pytest.mark.parametrize("clause", sorted(CLAUSES))
def test_the_refusal_carries_every_clause_an_operator_needs(
    photo_on_a_live_listing, clause
):
    """One parametrised subject per clause, not one assertion over all of them.

    Rule 10's corollary: *"a mark must be as narrow as the gap it marks"* —
    an aggregate assertion lets a second missing clause hide inside the
    first, and the failure says "the message changed" rather than "recovery 2
    is gone".
    """
    from apps.listings.storage import delete_object

    _listing, photo = photo_on_a_live_listing
    delete_object(photo.storage_key)
    _unbackfill(photo)

    message = _refuse(photo)
    assert clause in message, (
        f"the refusal does not say {clause!r}, which is {CLAUSES[clause]}. "
        f"The whole message was:\n{message}"
    )


def test_the_refusal_names_this_row_and_this_listing_and_this_key(
    photo_on_a_live_listing
):
    """The three identifiers, interpolated rather than described.

    A message that said "a row" would pass every clause check above and tell
    an operator with four thousand photographs nothing.
    """
    from apps.listings.storage import delete_object

    listing, photo = photo_on_a_live_listing
    key = photo.storage_key
    delete_object(key)
    _unbackfill(photo)

    message = _refuse(photo)
    for value, what in (
        (str(photo.pk), "the row id"),
        (str(listing.id), "the listing id, which is the directory to look in"),
        (key, "the key that does not resolve"),
    ):
        assert value in message, (
            f"the refusal does not name {what} ({value!r}), so the operator "
            f"cannot act on it:\n{message}"
        )


# --- 2 · the causes the existing test does not reach ------------------------


def test_it_refuses_rather_than_adopting_a_file_that_is_not_this_rows_bytes(
    photo_on_a_live_listing
):
    """**The branch where a wrong adoption would be worse than a refusal.**

    `_adopt` identifies an orphan by content hash. The branch nothing
    exercised is the one where a file *is* sitting in the listing directory
    and is **not** this row's bytes — a half-finished upload, an operator's
    copy, or another student's photograph on a listing that was reassigned.
    Adopting it would point this row at somebody else's image and stamp it
    `exif_stripped_at`.

    The stray file must also survive: a migration that deleted what it would
    not adopt would destroy the evidence an operator needs.
    """
    from apps.listings.storage import delete_object, media_root

    listing, photo = photo_on_a_live_listing
    before_key = photo.storage_key
    delete_object(before_key)
    _unbackfill(photo)

    stray = media_root() / "listings" / str(listing.id) / ("cd" * 16 + ".jpeg")
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_bytes(b"\xff\xd8\xff\xd9 not this row's photograph")

    message = _refuse(photo)
    assert "hashes to its" in message or "sha256" in message, (
        f"the refusal must say the content check is what failed:\n{message}"
    )
    photo.refresh_from_db()
    assert photo.storage_token is None and photo.storage_key == before_key, (
        "the row was changed on the way to refusing"
    )
    assert stray.exists(), (
        "the backfill deleted a file it declined to adopt; an operator "
        "following recovery 2 now has nothing to put back"
    )


def test_it_refuses_when_the_media_directory_is_gone_entirely(
    photo_on_a_live_listing
):
    """`INFRA.md` §3: the database was restored and the media was not.

    This is the state the message's first recovery is written for, and it is
    a different code path from a single missing file — `_adopt` returns on
    `directory.is_dir()` before it reads anything. A refusal that only
    covered the single-file case would 500 here, inside a migration, on a
    restore.
    """
    import shutil

    from apps.listings.storage import media_root

    _listing, photo = photo_on_a_live_listing
    _unbackfill(photo)
    shutil.rmtree(media_root() / "listings")

    message = _refuse(photo)
    assert "NULL storage_key" in message, (
        f"the restore recovery is not in the message for the restore "
        f"state:\n{message}"
    )


# --- 3 · does the printed recovery converge? -------------------------------


def test_following_recovery_one_converges_and_keeps_the_other_photograph(
    photo_on_a_live_listing
):
    """**The assertion a message-text check cannot make.**

    Two photographs on one listing. One file is gone for good; the other is
    intact. The backfill refuses, the operator does exactly what the message
    says — *"null it and re-run"* — and the questions are: does the re-run
    complete, does the surviving photograph still open, and is its row
    consistent with where its bytes actually are?

    If the answer to any of those is no, the message is an instruction that
    does not work, which rule 10's sixth disguise is specifically about: the
    refusal looks like the guard working.
    """
    from apps.listings import services
    from apps.listings.models import ListingPhoto
    from apps.listings.storage import delete_object, read_object
    from tests.contract.test_photo_storage_key import _jpeg

    listing, keeper = photo_on_a_live_listing
    buf = io.BytesIO(_jpeg(width=20, height=15))
    buf.name = "q.jpg"
    doomed = services.add_photo(listing.seller, listing, buf)
    original = read_object(keeper.storage_key)
    assert original, "the keeper must have bytes, or this proves nothing"

    delete_object(doomed.storage_key)
    _unbackfill(keeper)
    _unbackfill(doomed)

    message = _refuse(doomed)
    assert "NULL storage_key" in message

    # Recovery 1, verbatim: null the unrecoverable row's key and re-run.
    ListingPhoto.all_objects.filter(id=doomed.id).update(storage_key=None)
    from django.apps import apps as live_apps

    _backfill().forward(live_apps, None)

    keeper.refresh_from_db()
    doomed.refresh_from_db()
    assert keeper.storage_token, "the re-run skipped the row it could do"
    assert read_object(keeper.storage_key) == original, (
        "the surviving photograph is no longer at the key its row names — "
        "the recovery the refusal prints loses the photograph it was "
        "protecting"
    )
    assert doomed.storage_key is None, (
        "the nulled row was given a key again, which is how purge_media "
        "loses track of bytes that do not exist"
    )
    assert ListingPhoto.all_objects.exclude(storage_key=None).filter(
        listing_id=listing.id, storage_token=None
    ).count() == 0, "a row with bytes came out of the re-run without a token"
