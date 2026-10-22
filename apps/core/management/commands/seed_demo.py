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

        self.stdout.write(f"city={city.id} campus={campus.id} ({'created' if created else 'existing'})")
        self.stdout.write(f"discovery_enabled_at={campus.discovery_enabled_at!r}  (NULL = closed)")
        self.stdout.write(f"email_domains={campus.email_domains!r}")
        self.stdout.write(f"notice_versions={notices}")
        self.stdout.write(f"staff={staff.email} (role={staff.role}, no password — admin is S2)")
        self.stdout.write(
            "is_seed students=" + ", ".join(f"{u.email} [{u.status}]" for u in students)
        )
        self.stdout.write("NOT created, and why:")
        self.stdout.write("  - listings, books, photos: S2 tables")
        self.stdout.write("  - transfers, threads, messages: S4/S5 tables")
        self.stdout.write("  - a browsable-by-staff dataset: S2, the first slice with a listing")
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
