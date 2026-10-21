"""`manage.py run_jobs [--once]` — ADR-001 §2.4. A systemd timer runs this every minute."""

from django.core.management.base import BaseCommand

from apps.core.jobs import run_pending_jobs


class Command(BaseCommand):
    help = "Claim and run due jobs, then exit."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="accepted for symmetry; this always exits")
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        ok, failed = run_pending_jobs(limit=options["limit"])
        self.stdout.write(f"jobs: {ok} succeeded, {failed} failed")
