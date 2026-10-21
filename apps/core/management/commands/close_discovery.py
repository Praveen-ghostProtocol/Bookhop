"""`manage.py close_discovery --campus <slug> --reason <text>` — ADR-002 §4.1(b).

Closing is one command and writes a `revoked_at`. It is deliberately easier
than opening: a wrong close costs a day of discovery, a wrong open is operating
an e-commerce platform the company is not yet permitted to operate.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.core.management.commands.open_discovery import has_visible_character
from apps.core.models import Campus, GateAuthorisation
from apps.core.services import record_audit


class Command(BaseCommand):
    help = "Close the discovery gate for one campus and revoke its authorisation."

    def add_arguments(self, parser):
        parser.add_argument("--campus", required=True, help="campuses.slug")
        parser.add_argument("--reason", required=True)
        parser.add_argument("--by", default="", help="the human running this command (audit_log)")

    def handle(self, *args, **options):
        slug, reason = options["campus"], options["reason"]
        # Deliberately not required, unlike open_discovery's: a close must never
        # be the thing that fails for want of an argument.
        supplied = (options["by"] or "").strip()
        operator = supplied if has_visible_character(supplied) else "unnamed"
        try:
            campus = Campus.objects.get(slug=slug)
        except Campus.DoesNotExist:
            raise CommandError(f"no campus with slug {slug!r}")

        was_open = campus.discovery_enabled_at
        now = timezone.now()
        with transaction.atomic():
            campus.discovery_enabled_at = None
            campus.save(update_fields=["discovery_enabled_at"])
            # revoked_at/revoked_reason are the only columns the append-only
            # trigger lets an UPDATE touch (migration 0002).
            revoked = GateAuthorisation.objects.filter(
                gate="C", scope_type="CAMPUS", scope_id=campus.id, revoked_at__isnull=True
            ).update(revoked_at=now, revoked_reason=reason)
            record_audit(
                None, "discovery.close", campus,
                before={"discovery_enabled_at": was_open},
                after={"discovery_enabled_at": None, "reason": reason,
                       "authorisations_revoked": revoked,
                       "closed_by_operator": operator},
            )
        self.stdout.write(f"discovery CLOSED for {slug}; {revoked} authorisation(s) revoked")
