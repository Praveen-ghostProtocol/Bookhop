"""The J2-staff moderation queue, as a command. See `apps/listings/staff.py`
for why this is not a Django admin screen — it is an escalation with four
measured reasons, not a preference.

    manage.py review_listings --staff staff@example.ac.in
    manage.py review_listings --staff ... --listing 12 \
        --action REVIEW_PASS --legal-basis "seller terms" --reason "..." --seconds 45

**No bulk mode, and the absence is the control** (PRD AC-M1.5): there is no
`--all`, no `--action-all` and no way to pass more than one listing id. One
listing, one decision, one logged reason.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.catalog.services import verify_book
from apps.core.errors import ServiceError
from apps.listings.services import MODERATION_ACTIONS, moderate_listing
from apps.listings.staff import (
    REVIEW_COPY_PREFIX, listing_for_review, photos_for_review, queue_rows,
    staff_actor, sweep_review_copies,
)


class Command(BaseCommand):
    help = "List the PENDING_REVIEW queue, or decide one listing."

    def add_arguments(self, parser):
        parser.add_argument("--staff", required=True, help="the staff member's email")
        parser.add_argument("--listing", type=int, help="decide this one listing")
        parser.add_argument("--action", choices=sorted(MODERATION_ACTIONS))
        parser.add_argument("--legal-basis", default="")
        parser.add_argument("--reason", default="")
        parser.add_argument("--seconds", type=int, default=0,
                            help="seconds spent reviewing; recorded in audit_log")
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument(
            "--verify-book", action="store_true",
            help="with --listing: stamp `books.staff_verified_at` on this "
                 "listing's catalogue row, after reading the title, authors, "
                 "publisher and edition printed by --listing. A-29 §2 means "
                 "REVIEW_PASS is refused until this is done, because an "
                 "unverified row's seller-written text reaches no buyer and "
                 "neither does a listing of it. Separate from --action: the "
                 "edition is a catalogue judgement and the listing is a "
                 "listing judgement, and one reviewer may want to make the "
                 "first without making the second",
        )
        parser.add_argument(
            "--photos", metavar="DIR", nargs="?", const="", default=None,
            help="with --listing: write that listing's photos where the "
                 "reviewer can open them, and print the paths. With no DIR, "
                 "a fresh private temporary directory. Either way the copies "
                 "go into a bookhop-review-* directory and the next run of "
                 "this command deletes them once they are 24h old "
                 "(COMPLIANCE.md §7 row 25) — so run it, and pass the DIR "
                 "you used, even when you are only listing the queue",
        )

    def handle(self, *args, **options):
        # **First, before anything can fail.** P15: the copies expire on a
        # clock, and the clock is this command — the same command, run by
        # the same person, that made them. It runs whether or not this
        # invocation writes any photos, because the invocation that cleans
        # up is rarely the one that made the mess.
        for path in sweep_review_copies(options["photos"]):
            self.stdout.write(
                f"swept {path} — a review copy over 24h old "
                "(COMPLIANCE.md §7 row 25)"
            )

        try:
            staff = staff_actor(options["staff"])
        except ServiceError as exc:
            raise CommandError(str(exc)) from None

        if options["listing"] is None:
            rows = queue_rows(staff, limit=options["limit"])
            if not rows:
                self.stdout.write("Nothing is waiting for review.")
                return
            for row in rows:
                # **Red Team F50.** `condition`, `damage_flags` and the
                # asking price were assembled (or, for the price, not even
                # that) and never printed, so the human who is the only
                # control between a photocopied textbook and a buyer was
                # deciding from an ISBN and a photo *count*. The claim and
                # the price are the two halves of the counterfeit signal:
                # neither is suspicious alone and the combination is.
                self.stdout.write(
                    f"#{row['id']}  {row['created_at']:%Y-%m-%d %H:%M}  "
                    f"{row['campus']}  {row['isbn13'] or 'no ISBN'}  "
                    f"{row['title'][:48]}  {_as_written(row['asking_price_paise'])}  "
                    f"{row['condition']}  "
                    f"damage={','.join(row['damage_flags']) or 'none'}  "
                    f"photos={row['photo_count']}  "
                    f"verified_book={row['book_staff_verified']}  "
                    f"suspect={row['suspect_reproduction_flag']}  "
                    f"seed={row['is_seed']}"
                )
            self.stdout.write(
                f"\n{len(rows)} waiting. Open one with --listing N --photos, "
                "then decide it with --action."
            )
            return

        try:
            listing = listing_for_review(staff, options["listing"])
        except ServiceError as exc:
            raise CommandError(f"{type(exc).__name__}: {exc}") from None

        # **THE TEXT PRECEDES THE STAMP, FOR EVERY `--listing` INVOCATION.**
        # This used to run only inside `if not options["action"]` below, after
        # the `--verify-book` block — so a single
        # `--listing N --verify-book --action REVIEW_PASS` stamped the book,
        # took the listing LIVE and served the seller's four strings to every
        # student of that ISBN with **none of that text ever printed**
        # (S2-R2-B2). A-29's whole layer is a named human having looked at it,
        # and on that path the human looked at a listing id. Printing first
        # also puts the condition and the asking price in front of a reviewer
        # who decides in one command, which is Red Team F50's point.
        self._show(listing)

        if options["photos"] is not None:
            self._write_photos(staff, listing, options["photos"])

        if options["verify_book"]:
            try:
                book = verify_book(staff, listing.book)
            except ServiceError as exc:
                raise CommandError(f"{type(exc).__name__}: {exc}") from None
            self.stdout.write(
                f"book {book.id} ({book.isbn13 or 'no ISBN'}) checked by "
                f"{staff.email} — its text is now served to every reader"
            )
            listing.refresh_from_db()

        if not options["action"]:
            # **Not an error any more.** `--listing` alone is "show me this
            # one", which is the step J2-staff step 3 describes and the step
            # that did not exist: the only way to name a listing was to
            # decide it in the same breath. The showing itself has moved
            # above, because it is not conditional on the absence of a
            # decision — it is the input to one.
            return
        try:
            updated = moderate_listing(
                staff, listing, options["action"],
                options["legal_basis"], options["reason"], options["seconds"],
            )
        except ServiceError as exc:
            raise CommandError(f"{type(exc).__name__}: {exc}") from None
        self.stdout.write(f"listing {updated.id} is now {updated.status}")

    def _show(self, listing):
        """One listing's claims, for the decision in J2-staff step 3.

        **`authors` prints here, and the whole title does.** QA found it
        reached no reviewer at all — not this method, not `queue_rows` — while
        rendering on four student-facing pages, so for that one field the
        layer A-28 named did not exist. It belongs on *this* output and not
        only on the queue line for a second reason QA gave: the queue line
        truncates the title to 48 characters, so anything past character 48
        is invisible there. Nothing on these lines is truncated.
        """
        self.stdout.write(
            f"#{listing.id}  {listing.status}  {listing.campus.slug}\n"
            f"  book          {listing.book.isbn13 or 'no ISBN'}  "
            f"{listing.book.title}\n"
            f"  authors       {', '.join(listing.book.authors or []) or '-'}\n"
            f"  edition       {listing.book.edition_label or '-'}  "
            f"{listing.book.publisher or '-'}  "
            f"{listing.book.publication_year or '-'}\n"
            f"  asking        {_as_written(listing.asking_price_paise)}\n"
            f"  condition     {listing.condition}  "
            f"annotations={listing.annotation_level}\n"
            f"  damage        {','.join(listing.damage_flags or []) or 'none claimed'}\n"
            f"  category      {listing.category}  language={listing.language}\n"
            f"  book verified {listing.book.staff_verified_at is not None}  "
            f"suspect={listing.suspect_reproduction_flag}  seed={listing.is_seed}"
        )

    def _write_photos(self, staff, listing, directory):
        """Put the images where the reviewer can open them.

        A file path and not a byte dump: the moderator's question is visual,
        and `photos_for_review` writes the `personal_data_access_log` row
        that makes this an *opening* rather than a list.

        **These copies are personal data outside every automated path that
        looks after it** (review R-R6). `COMPLIANCE.md` §7 row 9 governs
        listing photographs — *"Delete originals and derivatives from object
        store and CDN after 1 yr"* — and a copy in an operator's directory is
        in neither. `purge_media` cannot reach it; a DPDP erasure request
        cannot reach it; the retention clock does not run on it. The access
        **log** row shipped and the retention half did not.

        Two halves of the fix, and neither is a control:

          * the default is a **fresh private temporary directory**, so the
            copies land somewhere the operating system clears rather than in
            a working tree or a home directory where they accumulate;
          * the deletion command is printed **with** the paths, not in a
            manual, because the person who needs it is reading this output.

        # ponytail: the operator deletes them. Ceiling: nothing enforces it,
        # and `--photos DIR` into a chosen directory is still available
        # because a reviewer on a remote VM needs a path they can fetch
        # from. Upgrade path: the moderation screen that makes this command
        # unnecessary, which is where the queue is going anyway — a browser
        # renders the bytes without writing a second copy.
        """
        import pathlib
        import tempfile

        # **One `mkdtemp`, both modes** (P15). With no DIR the copies land in
        # the system temporary directory; with a DIR they land in a
        # `bookhop-review-*` subdirectory *of* it, never loose in the
        # directory itself — so `sweep_review_copies` has one name rule to
        # apply instead of two that can disagree (rule 11).
        root = None
        if directory:
            root = pathlib.Path(directory)
            root.mkdir(parents=True, exist_ok=True)
        target = pathlib.Path(tempfile.mkdtemp(prefix=REVIEW_COPY_PREFIX, dir=root))
        try:
            resolved = photos_for_review(staff, listing.id)
        except ServiceError as exc:
            raise CommandError(f"{type(exc).__name__}: {exc}") from None
        if not resolved:
            self.stdout.write("  photos        none on this listing")
            return
        written = []
        for index, (photo, data) in enumerate(resolved, start=1):
            if data is None:
                self.stdout.write(
                    f"  photo {index}       purged — the row survives, the bytes do not"
                )
                continue
            suffix = str(photo.storage_key).rsplit(".", 1)[-1].lower()
            path = target / f"listing-{listing.id}-{index}.{suffix}"
            path.write_bytes(data)
            written.append(path)
            self.stdout.write(
                f"  photo {index}       {path}  {photo.width}x{photo.height}  "
                f"{photo.bytes} bytes"
            )
        if written:
            self.stdout.write(
                f"  DELETE THESE   rm -rf {target}\n"
                "                 They are a student's photographs outside "
                "the object store: purge_media does not reach them, nor "
                "does an erasure request (COMPLIANCE.md §7 rows 9 and 25). "
                "The next run of this command sweeps them after 24h — that "
                "is the retention rule, not this line. Delete them sooner."
            )


def _as_written(asking):
    """The asking figure as a reviewer reads it.

    **Integer throughout** — the division is for the printed line only and
    nothing stores the result. The name avoids both W1b tokens on purpose
    (`CLAUDE.md` rule 13's first resort: rename our own name, which costs one
    rename and leaves the P14 source grep at full strength).
    """
    return "no asking figure" if asking is None else f"Rs {asking // 100}.{asking % 100:02d}"
