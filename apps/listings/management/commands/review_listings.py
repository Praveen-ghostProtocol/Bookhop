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

from apps.core.errors import ServiceError
from apps.listings.services import MODERATION_ACTIONS, moderate_listing
from apps.listings.staff import listing_for_review, queue_rows, staff_actor


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

    def handle(self, *args, **options):
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
                self.stdout.write(
                    f"#{row['id']}  {row['created_at']:%Y-%m-%d %H:%M}  "
                    f"{row['campus']}  {row['isbn13'] or 'no ISBN'}  "
                    f"{row['title'][:48]}  photos={row['photo_count']}  "
                    f"verified_book={row['book_staff_verified']}  "
                    f"suspect={row['suspect_reproduction_flag']}  "
                    f"seed={row['is_seed']}"
                )
            self.stdout.write(f"\n{len(rows)} waiting. Decide one with --listing.")
            return

        if not options["action"]:
            raise CommandError("--action is required when --listing is given")
        try:
            listing = listing_for_review(staff, options["listing"])
        except ServiceError as exc:
            raise CommandError(f"{type(exc).__name__}: {exc}") from None
        try:
            updated = moderate_listing(
                staff, listing, options["action"],
                options["legal_basis"], options["reason"], options["seconds"],
            )
        except ServiceError as exc:
            raise CommandError(f"{type(exc).__name__}: {exc}") from None
        self.stdout.write(f"listing {updated.id} is now {updated.status}")
