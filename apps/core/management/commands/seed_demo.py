"""`manage.py seed_demo` — ADR-002 §4.1(c), TASKS S0.

Idempotent. Creates the tenancy rows S0 owns: one city, one campus (gate
**closed**, which is the correct default), the not-yet-incorporated
`legal_entities` row, and the two D-007 feature flags set to false.

**It does not create the staff user or the `is_seed` students TASKS S0 lists.**
`users` is an S1 table (DATA-MODEL §2) and does not exist yet, so there is
nothing to insert into. Stated here rather than faked: a seed command that
printed "created 5 students" with no users table would be the exact failure
mode the engineering standard is written against. The user and listing fixtures
land with S1 and S2 in `fixtures/seed_*.json`.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Campus, City, FeatureFlag, LegalEntity


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
        for key in ("listings.swap_ui", "listings.general_reading_ui"):
            FeatureFlag.objects.get_or_create(
                key=key, defaults={"enabled": False, "updated_by": "seed_demo"}
            )

        self.stdout.write(f"city={city.id} campus={campus.id} ({'created' if created else 'existing'})")
        self.stdout.write(f"discovery_enabled_at={campus.discovery_enabled_at!r}  (NULL = closed)")
        self.stdout.write("staff user and is_seed students: NOT created — `users` is an S1 table")
