"""`manage.py seed_demo` — ADR-002 §4.1(c), TASKS S0 and S1.

Idempotent. Creates the tenancy rows S0 owns — one city, one campus (gate
**closed**, which is the correct default), the not-yet-incorporated
`legal_entities` row, the D-007 feature flags — **and, from S1, the accounts
rows that make the slice testable before Gate C**: the five notice versions, a
staff user, and two `is_seed` students.

**Every student it creates is `is_seed=true`** (ADR-002 §4.1(c)). Seed and real
data never mix, every metric view filters `is_seed = false`, and a closed campus
exposes seed rows only — so a seed student is the only actor that can exercise
S1 end to end before a campus is lawfully open.

It prints what it did **not** create, because a seed command that printed
"created 5 students" with no `users` table is the failure mode the engineering
standard is written against — and that is exactly what this command did in S0,
honestly, until this slice.
"""

from datetime import timedelta
from hashlib import sha256

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.models import Campus, City, FeatureFlag, LegalEntity

#: The five `notice_versions.kind` values (DATA-MODEL §2). The **body is a
#: placeholder and says so in its own text**: `COPY-DECK.md` is the source for
#: the real notices and the legal pages are frontend's, so a seed that invented
#: plausible privacy-policy prose would be backend writing copy — and worse,
#: copy that reads like a reviewed notice. `HANDOVER_GUIDANCE`, not
#: `HANDOVER_SAFETY` (amendment A-7).
#: Imported, never retyped (`CLAUDE.md` rule 10) — the seed and the CHECK
#: constraint must not be able to disagree about which notices exist.
from apps.accounts.models import NOTICE_KINDS  # noqa: E402

PLACEHOLDER_BODY = (
    "SEED PLACEHOLDER — not reviewed copy.\n\n"
    "The real text for this notice comes from company/design/COPY-DECK.md and "
    "ships as a frontend legal page. This row exists so that consent can be "
    "recorded against a notice version in a development database.\n"
)


class Command(BaseCommand):
    help = "Create the S0 demo tenancy (one city, one campus with the gate closed)."

    @transaction.atomic
    def handle(self, *args, **options):
        city, _ = City.objects.get_or_create(name="Chennai", defaults={"state": "Tamil Nadu"})
        entity, _ = LegalEntity.objects.get_or_create(
            id=1, defaults={"legal_name": None}  # NULL until incorporation (Gate B1)
        )
        campus, created = Campus.objects.get_or_create(
            slug="demo-campus",
            defaults={
                "city": city,
                "name": "Demo Campus",
                "email_domains": [],  # empty = no self-service signup (DATA-MODEL §1)
                "legal_entity": entity,
                # discovery_enabled_at stays NULL. ADR-002 §4: a campus is
                # closed unless a named human opened it with open_discovery.
            },
        )
        # `i18n.ta_enabled` is seeded **false** and stays false until the
        # native-speaker review lands (THREAT-MODEL §6.1, TASKS S1). Tamil
        # strings may be written, and are; no student is offered the Tamil
        # locale while any blocking-class string is unreviewed. That is a gate
        # enforced by `tests/unit/test_locale_gate.py`, not a promise.
        for key in ("listings.swap_ui", "listings.general_reading_ui", "i18n.ta_enabled"):
            FeatureFlag.objects.get_or_create(
                key=key, defaults={"enabled": False, "updated_by": "seed_demo"}
            )

        notices = self._seed_notices()
        staff, students = self._seed_accounts(campus)
        catalogue = self._seed_catalogue(campus, staff)
        listings = self._seed_listings(campus, students, staff)

        self.stdout.write(f"city={city.id} campus={campus.id} ({'created' if created else 'existing'})")
        self.stdout.write(f"discovery_enabled_at={campus.discovery_enabled_at!r}  (NULL = closed)")
        self.stdout.write(f"email_domains={campus.email_domains!r}")
        self.stdout.write(f"notice_versions={notices}")
        self.stdout.write(f"staff={staff.email} (role={staff.role}, no password — admin is S2)")
        self.stdout.write(
            "is_seed students=" + ", ".join(f"{u.email} [{u.status}]" for u in students)
        )
        self.stdout.write(catalogue)
        self.stdout.write(listings)
        self.stdout.write("NOT created, and why:")
        self.stdout.write("  - listing photos: a seed photo would be an invented image file")
        self.stdout.write("  - transfers, threads, messages: S4/S5 tables")
        self.stdout.write("  - notifications, search_events: S3 tables")
        self.stdout.write("  - any real (non-seed) student: only a sign-in creates one")

    def _seed_notices(self):
        """One version per kind, in `en`. Idempotent on `(kind, version, locale)`.

        `ta` rows are deliberately **absent**: the Tamil notices are frontend's
        copy and the locale is gated off, so seeding an English body under a
        `ta` locale would put unreviewed Tamil-labelled text where
        `test_reviewed_locale.py` cannot see it. `current_notice` falls back to
        `en`, which is the correct behaviour for a gated locale.
        """
        from apps.accounts.models import NoticeVersion

        version = "2026-11-01.1"
        created = []
        for kind in NOTICE_KINDS:
            body = f"# {kind.replace('_', ' ').title()}\n\n{PLACEHOLDER_BODY}"
            row, made = NoticeVersion.objects.get_or_create(
                kind=kind, version=version, locale="en",
                defaults={
                    "body_md": body,
                    "sha256": sha256(body.encode("utf-8")).hexdigest(),
                    "published_at": timezone.now(),
                },
            )
            created.append(f"{kind}@{row.version}{'*' if made else ''}")
        return ", ".join(created)

    def _seed_accounts(self, campus):
        """A staff user and two `is_seed` students on the demo campus.

        The campus gains `example.ac.in` in `email_domains` so the magic-link
        flow is reachable at all — with an empty list there is no self-service
        signup (DATA-MODEL §1) and `request_magic_link` refuses every address,
        which is the correct production default and an untestable development
        one.

        **The staff user has no password**, because nothing in S1 can set one:
        staff sign-in is password + TOTP in the Django admin and the admin lands
        with S2's moderation queue. The row exists so `review_age` and
        `log_personal_data_access` have a staff actor to be called with, which
        is what makes their guards testable.

        One student is `ACTIVE` with every consent granted and one is
        `PENDING_VERIFICATION` with none, so both sides of §2.5's standing
        preconditions have a subject.
        """
        from apps.accounts.models import NoticeVersion, User
        from apps.accounts.services import grant_consent
        from apps.core.scoping import assert_real_account_allowed

        # A-35's permitted side, as a row rather than as a sentence. Every row
        # this method writes carries `is_seed=True`, and this is the call that
        # says so to the same function that refuses the other side — so the
        # seed branch is a live production call site, not a branch only a test
        # ever reaches.
        assert_real_account_allowed(is_seed=True)

        if "example.ac.in" not in (campus.email_domains or []):
            campus.email_domains = [*(campus.email_domains or []), "example.ac.in"]
            campus.save(update_fields=["email_domains"])

        staff, _ = User.objects.get_or_create(
            email="staff@example.ac.in",
            defaults={
                "campus": campus, "city_id": campus.city_id, "role": "STAFF_ADMIN",
                "status": "ACTIVE", "display_name": "Demo Staff",
                "adult_verified": True, "campus_verified": True, "is_seed": True,
            },
        )

        notice = NoticeVersion.objects.filter(kind="PRIVACY", locale="en").first()
        students = []
        for index, (local, status) in enumerate(
            (("seed.active", "ACTIVE"), ("seed.pending", "PENDING_VERIFICATION")), start=1
        ):
            student, made = User.objects.get_or_create(
                email=f"{local}@example.ac.in",
                defaults={
                    "campus": campus, "city_id": campus.city_id, "is_seed": True,
                    "display_name": f"Seed Student {index}",
                    "status": status,
                    "adult_verified": status == "ACTIVE",
                    "campus_verified": status == "ACTIVE",
                    "email_verified_at": timezone.now() - timedelta(days=1),
                },
            )
            if made and status == "ACTIVE" and notice is not None:
                for purpose in ("account", "listing_publication", "chat", "notifications"):
                    grant_consent(student, purpose, notice, "STAFF_RECORDED", None, "seed_demo")
            students.append(student)
        return staff, students

    def _seed_catalogue(self, campus, staff):
        """**One department's reading list — R-01's test.**

        `TASKS.md` §2 S2 asks for *"seed fixtures including one department's
        real reading list (R-01's test)"*, and DATA-MODEL §3 calls seeding it
        by hand *"the first thing in slice 2's fixtures"*. It is the product
        thesis made concrete: a syllabus-to-shelf layer is only testable
        against a syllabus.

        **The editions and ISBNs are real and checksum-valid** — they are
        standard first-year engineering texts — and `validate_isbn13` runs at
        insert, so a mistyped digit fails the seed rather than creating a book
        nobody can find.

        **The course codes are illustrative and the source is
        `STUDENT_REPORTED`, not `DEPT_CONFIRMED`.** No department has
        confirmed anything to us and `CLAUDE.md` rule 1 forbids a seed that
        implies one did — a `DEPT_CONFIRMED` row here would be a fabricated
        fact sitting in the column whose whole job is to say where the fact
        came from. A confirmed list arrives with a real MoU (J10-staff).
        """
        from apps.catalog.models import Book, PrescribedText
        from apps.catalog.services import normalise_title, validate_isbn13

        reading_list = [
            ("9788177589139", "Higher Engineering Mathematics", ["B S Grewal"],
             "44th edition", "Khanna Publishers", 2021,
             "MA8151", "Engineering Mathematics I"),
            ("9780131103627", "The C Programming Language",
             ["Brian W Kernighan", "Dennis M Ritchie"], "2nd edition",
             "Prentice Hall", 1988, "CS8251", "Programming in C"),
            ("9789332535091", "Engineering Physics", ["Gaur", "Gupta"],
             "8th edition", "Dhanpat Rai", 2019, "PH8151", "Engineering Physics"),
        ]
        made = 0
        for isbn, title, authors, edition, publisher, year, code, course in reading_list:
            digits = validate_isbn13(isbn)
            book, created = Book.objects.get_or_create(
                isbn13=digits,
                defaults={
                    "title": title, "title_norm": normalise_title(title),
                    "authors": authors, "edition_label": edition,
                    "publisher": publisher, "publication_year": year,
                    "language": "en", "staff_verified_at": timezone.now(),
                },
            )
            made += int(created)
            PrescribedText.objects.get_or_create(
                campus=campus, course_code=code, term_label="2026-ODD", book=book,
                defaults={
                    "city_id": campus.city_id, "course_title": course,
                    "source": "STUDENT_REPORTED",
                    "source_ref": "seed_demo: illustrative, not a confirmed list",
                    "added_by": staff,
                },
            )
        return (
            "books=%d (%d new, staff-verified), prescribed_texts=%d "
            "(source=STUDENT_REPORTED - no department has confirmed one)"
            % (Book.objects.count(), made, PrescribedText.objects.count())
        )

    def _seed_listings(self, campus, students, staff):
        """A browsable-by-staff dataset — S0's deferred "done when", now due.

        TASKS §2 S0: *"'seed_demo produces a browsable-by-staff dataset' moves
        to S2, which is the first slice in which a listing exists to browse."*

        Four listings, chosen so every S2 surface has a subject: one **LIVE**,
        one **PENDING_REVIEW** for the moderation queue, one **SWAP** and one
        **GENERAL_READING**. The last two are D-007's *"deferred, not
        deleted"* — representable, UI-hidden, and **seeded so they are known
        to work when swap returns**. A `swap_wants` row goes with the swap
        listing for the same reason, and an open `book_requests` row gives
        J4's demand side and §9.3's match rate something to count.

        Every row is `is_seed=True` **because its seller is a seed student**,
        not because this command sets a flag: ADR-002 §4.1(c)'s separation is
        a property of the actor, and a seed command that set the flag by hand
        would be the one place the two could disagree.
        """
        from apps.catalog.models import Book
        from apps.listings.models import BookRequest, Listing, SwapWant

        seller = next((s for s in students if s.status == "ACTIVE"), None)
        books = list(Book.objects.order_by("id")[:3])
        if seller is None or len(books) < 3:
            return "listings=0 (no ACTIVE seed student or no catalogue)"

        if not Listing.all_objects.filter(seller_pseudonym=seller.person_pseudonym).exists():
            shapes = [
                (books[0], "LIVE", "SELL", "PRESCRIBED_TEXTBOOK", 30000, False),
                (books[1], "PENDING_REVIEW", "SELL", "PRESCRIBED_TEXTBOOK", 22500, True),
                (books[2], "LIVE", "SWAP", "PRESCRIBED_TEXTBOOK", 0, False),
                (books[0], "LIVE", "SELL", "GENERAL_READING", 15000, False),
            ]
            for book, status, intent, category, minor_units, suspect in shapes:
                listing = Listing.all_objects.create(
                    seller=seller, seller_pseudonym=seller.person_pseudonym,
                    book=book, campus=campus, city_id=campus.city_id,
                    intent=intent, asking_price_paise=minor_units,
                    price_fixed_at=timezone.now(),
                    condition="GOOD", annotation_level="LIGHT_PENCIL",
                    damage_flags=[], category=category, language="en",
                    status=status, suspect_reproduction_flag=suspect,
                    is_seed=True,
                    published_at=timezone.now() if status == "LIVE" else None,
                )
                if intent == "SWAP":
                    SwapWant.objects.get_or_create(listing=listing, book=books[1])

        wanted = next((s for s in students if s.status != "ACTIVE"), seller)
        BookRequest.all_objects.get_or_create(
            requester_pseudonym=wanted.person_pseudonym, book=books[2], status="OPEN",
            defaults={
                "requester": wanted, "campus": campus, "city_id": campus.city_id,
                "course_code": "PH8151", "is_seed": True,
            },
        )
        return (
            "listings=%d (LIVE/PENDING_REVIEW/SWAP/GENERAL_READING, all is_seed), "
            "swap_wants=%d (UI-hidden, D-007), book_requests=%d"
            % (Listing.all_objects.count(), SwapWant.objects.count(),
               BookRequest.all_objects.count())
        )
