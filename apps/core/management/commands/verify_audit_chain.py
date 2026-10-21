"""`manage.py verify_audit_chain` — DATA-MODEL §8.

Exits non-zero and names the first bad row if the chain does not verify.
Print the head hash somewhere outside the database (the daily digest email) to
close the gap named in the ponytail note on `verify_audit_chain`.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.core.errors import AuditChainBroken
from apps.core.services import verify_audit_chain


class Command(BaseCommand):
    help = "Recompute and verify the audit_log hash chain."

    def handle(self, *args, **options):
        try:
            checked, head = verify_audit_chain()
        except AuditChainBroken as exc:
            raise CommandError(str(exc))
        self.stdout.write(f"audit chain OK: {checked} rows, head={head}")
