"""The staff moderation surface — J2-staff, as management commands.

> **ESCALATION, not a deferral by preference.** TASKS §2 S2 says *"the Django
> admin — backend deferred it from S1 and that is right, because the
> moderation queue it exists for is an S2 surface"*, and API-CONTRACT §5.7
> says moderation is *"Django admin screens … not L2 endpoints"*. **I have not
> installed `django.contrib.admin`, and the reasons are measured rather than
> predicted.** They are in the slice note in full; in short, four of them:
>
> 1. **`django_admin_log.action_flag` fails the P14 whitelist.** It is a
>    `PositiveSmallIntegerField`, so W1 inspects it, and `flag` is not in
>    `NON_MONETARY_WORDS`. Clearing it means an entry in
>    `DECLARED_NON_MONETARY` — a **widening of the whitelist**, which
>    `apps/core/p14.py` says carries a founder escalation. That is rule 13
>    arriving on a name that is **not ours to rename**, on a table we do not
>    own, for a feature with alternatives.
> 2. **`django_admin_log.change_message` and `object_repr` are free text that
>    will contain personal data**, in a table with no DATA-MODEL row, no
>    `COMPLIANCE.md` §7 row and therefore no retention rule. A field with no
>    §7 row is a defect by that section's own standing rule.
> 3. **The admin requires `django.contrib.auth`**, which ADR-001 §2.5
>    deliberately excludes — *"students have no password column at all"* — so
>    it means either a second user table or swapping `AUTH_USER_MODEL`, and
>    the second is a migration-level change to the table every other table
>    points at.
> 4. **API-CONTRACT §5.7 requires password + TOTP before any screen showing
>    personal data.** `django-otp` is listed in `requirements.txt` but is not
>    installed and this machine has no network, so shipping the admin now
>    means shipping it **without** the second factor — which is claiming a
>    control that does not exist.
>
> **What ships instead is the thing the queue is for**, because
> `moderate_listing` is an L1 service and §5.7's own note lists management
> commands as the staff channel for work that is not on HTTP: `run_jobs`,
> `open_discovery`, `retention_purge` and the rest already are. One listing,
> one decision, one logged reason (AC-M1.5), and the same `audit_log` row the
> admin action would have written.
>
> **What is NOT shipped, stated so it is a known gap rather than an assumed
> one:** the visible server timer (AC-M1.3) and the single-clock ordering
> (AC-M1.1). Both need `support_work_log` (S5) and the report clocks (S6).
> `work_seconds` is still recorded, into `audit_log`, so D-009's
> instrumentation ships with the behaviour and S6 has a source to backfill
> from.
"""

import logging
import pathlib
import shutil
import tempfile
import time

from apps.core.errors import NotPermitted

log = logging.getLogger(__name__)

__all__ = [
    "queue_rows", "staff_actor", "listing_for_review", "photos_for_review",
    "sweep_review_copies", "REVIEW_COPY_PREFIX", "REVIEW_COPY_TTL_SECONDS",
]

#: **One name rule, both modes.** Every directory `--photos` creates is
#: named with this prefix — in `gettempdir()` by default, and in a
#: `bookhop-review-*` subdirectory of an operator-chosen `DIR` otherwise —
#: so the sweep below has a single rule to apply rather than two that can
#: disagree (`CLAUDE.md` rule 11). The write side of the convention is in
#: `review_listings._write_photos`; this is the side that makes it
#: load-bearing rather than decorative.
REVIEW_COPY_PREFIX = "bookhop-review-"

#: `COMPLIANCE.md` §7 row 25. One working day, so a reviewer who opens a
#: listing at 5pm still has the files at 10am. **Arbitrary, and said to be**:
#: if a review legitimately spans longer, this number moves and the
#: mechanism does not.
REVIEW_COPY_TTL_SECONDS = 24 * 3600


def sweep_review_copies(extra_root=None):
    """Delete `--photos` working copies older than 24h. Returns what it took.

    **P15, and the argument that decides it is not DPDP s8(7)** — though that
    applies. It is that `COPY-DECK.md` replaced *"Everything else goes now"*
    with an **enumeration** of what survives deletion; that enumeration is a
    representation to the student; and these copies are not in it and
    `erase_account` cannot reach them. The honest disclosure would read *"a
    staff member may still have copies of your photographs on their own
    computer; we don't know how many, or where, and nothing deletes them."*
    Nobody ships that sentence, so the copies go and the notice stands.

    A printed `rm -rf` was not a retention period: it is an instruction, and
    an instruction with no event that ends it is indefinite retention of
    photographs taken inside a student's room, on an unknown number of
    laptops.

    **The clock is an age, not a name.** A sweep that deleted every
    `bookhop-review-*` directory would pass the first half of its own test
    and `rm -rf` the copies the moderator is reading at that moment. Both
    sides are asserted in `tests/contract/test_the_review_copies_expire.py`.

    **The residual, named rather than closed:** an operator who runs
    `--photos DIR` once and never runs the command again is never swept.
    The layer that catches that is the `personal_data_access_log` row
    `photos_for_review` writes — we know which operator opened which
    listing, so an erasure request is answerable by asking one named person.

    # ponytail: no daemon, no cron, no state file, no new table. The sweep
    # runs at the top of the same command, run by the same person, that made
    # the copies. Ceiling: it is the residual above. Upgrade path: the
    # moderation screen, where the browser renders the bytes and no second
    # copy is written at all.
    """
    roots, seen = [], set()
    for candidate in (tempfile.gettempdir(), extra_root):
        if not candidate:
            continue
        root = pathlib.Path(candidate)
        try:
            key = root.resolve()
        except OSError:
            continue
        if key not in seen and root.is_dir():
            seen.add(key)
            roots.append(root)

    cutoff = time.time() - REVIEW_COPY_TTL_SECONDS
    removed = []
    for root in roots:
        for child in sorted(root.glob(f"{REVIEW_COPY_PREFIX}*")):
            try:
                if not child.is_dir() or child.stat().st_mtime >= cutoff:
                    continue
                shutil.rmtree(child)
            except OSError:
                # A directory another operator holds open, or one that went
                # away between the glob and the stat. The next run retries;
                # a sweep that died here would stop the queue.
                log.warning("listings.review_copy_sweep_failed", exc_info=True)
                continue
            removed.append(child)
            log.info(
                "listings.review_copy_swept",
                extra={"event": "listings.review_copy_swept", "path": str(child)},
            )
    return removed


def staff_actor(email):
    """Resolve a staff member by email, for a management command.

    `all_objects` and allow-listed: this is the staff surface, which ADR-002
    §2.3 names in its own list of permitted call sites. A staff account on a
    campus whose gate is closed is the normal case before Gate C, and a
    moderator who cannot be found is a moderator who cannot clear the queue.
    """
    from apps.accounts.services import normalise_email
    from apps.accounts.models import User

    user = User.all_objects.filter(email=normalise_email(email)).first()
    if user is None or not user.is_staff_member:
        raise NotPermitted("That is a staff-only action.")
    return user


def queue_rows(staff, limit=50):
    """J2-staff step 1's rows, as plain dicts a command can print.

    **No photo bytes and no seller identity**: the reviewer's judgement in
    J2-staff step 3 is about the book and the images, and a command that
    printed a student's display name beside a moderation decision would make
    `personal_data_access_log` owe a row for every queue listing rather than
    for every listing opened. The images are `photos_for_review`, which is a
    per-listing read and writes that row.

    **`asking_price_paise` is here** (Red Team F50). It was in no key of this
    dict and on no line of the command, and price against edition is the
    cheapest counterfeit signal there is — a ₹900 prescribed textbook offered
    at ₹60 is the campus-gate photocopy price. It is the **asking** price,
    which ADR-003 §2.1 is explicit is not a consideration, and it is the one
    money column that exists.
    """
    from .services import review_queue

    # **The raw seller-written title, deliberately** (A-29 §1). This and
    # `review_listings._show` are the two *staff* readers the gate names: a
    # review step whose reader is served the neutral label would be a review
    # step that cannot review. `review_queue` refuses a non-staff actor
    # before any row is read, which is the clause `may_read_unverified_text`
    # asks for.
    return [
        {
            "id": listing.id,
            "asking_price_paise": listing.asking_price_paise,
            "created_at": listing.created_at,
            "campus": listing.campus.slug,
            "isbn13": listing.book.isbn13,
            "title": listing.book.title,
            "book_staff_verified": listing.book.staff_verified_at is not None,
            "suspect_reproduction_flag": listing.suspect_reproduction_flag,
            "condition": listing.condition,
            "damage_flags": list(listing.damage_flags or []),
            "photo_count": listing.photos.count(),
            "is_seed": listing.is_seed,
        }
        for listing in review_queue(staff, limit=limit)
    ]


def listing_for_review(staff, listing_id):
    """One listing by id, for a staff decision. Raises `NotFound`.

    Here rather than in the management command for the same reason views
    never touch the ORM: the command is a presentation layer too, and
    `all_objects` belongs behind the allow-listed staff surface rather than
    in every caller that wants a row.

    **`all_objects` and not `objects`, deliberately.** The moderation queue's
    entire job is listings on a campus whose gate is closed — that is the only
    lawful state before Gate C — so a gated read would hand the reviewer an
    empty queue. This is the staff-surface entry in ADR-002 §2.3's own
    allow-list, and the layer that still applies is `moderate_listing`'s
    staff check, which refuses a non-staff actor before any row is touched.
    """
    from apps.core.errors import NotFound
    from .models import Listing

    if not getattr(staff, "is_staff_member", False):
        raise NotPermitted("That is a staff-only action.")
    row = Listing.all_objects.filter(id=listing_id).select_related("book").first()
    if row is None:
        raise NotFound("Not found.")
    return row


def photos_for_review(staff, listing_id):
    """`[(photo, bytes_or_None), …]` for one listing. A **staff** read.

    Red Team F50: *"the reviewer's judgement … is about the book **and the
    images**"* was the documented job, and no shipped surface resolved a
    photo for a moderator. `get_photo_for_download` refuses them correctly —
    it authorises on *ownership or an open discovery gate*, and a moderator
    before Gate C is neither — and **widening it would have been the wrong
    fix**: a staff read is a different authorisation with a different
    justification and a different log, not a wider student read. So it is a
    different function. `get_photo_for_download` is untouched.

    What this does that the student path does not:

      * **it asks `is_staff_member`** and nothing else — no gate, no scope,
        no ownership, because the queue's entire job is listings on a campus
        whose gate is lawfully closed (the ADR-002 §2.3 staff allow-list, the
        same entry `listing_for_review` sits in);
      * **it writes `personal_data_access_log`**, one row per listing opened,
        naming `listing_photos` as the field read. The photo is the student's
        data — the whole reason EXIF is stripped is that a photo of a book on
        a desk is a photo of where that student lives — so a staff view of it
        is DPDP r.6(1)(c) access and owes a row. `queue_rows` does not write
        one and must not: it is a list, this is an opening.

    The bytes are `None` where the object has been purged (DATA-MODEL §10.2);
    the row survives its file, and the caller says so rather than crashing.
    """
    from apps.accounts.services import log_personal_data_access

    from .models import ListingPhoto
    from .storage import read_object

    listing = listing_for_review(staff, listing_id)
    rows = list(
        ListingPhoto.all_objects.filter(listing_id=listing.id).order_by("uploaded_at", "id")
    )
    if rows:
        log_personal_data_access(
            staff,
            listing.seller_pseudonym,
            # What the moderator read is the **photograph**. After A-25
            # `storage_key` is the one part of this row that is not personal
            # data — it is a random token — so logging it named the field
            # that carries no personal data and omitted the one that does.
            # A DPDP r.6(1)(c) reader auditing this log could not tell an
            # image had been viewed.
            ["listing_photos.image"],
            f"moderation review of listing {listing.id}",
        )
    return [(row, read_object(row.storage_key) if row.storage_key else None) for row in rows]
