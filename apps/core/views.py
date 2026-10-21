"""Operational endpoints — API-CONTRACT §5.8.

These are the only views backend-developer owns. Every student-facing page is
`web/views.py` (frontend-developer) and calls L1 directly.
"""

import json
import logging
from datetime import timedelta

from django.db import connection
from django.http import HttpResponse
from django.utils import timezone

from .models import Job

log = logging.getLogger(__name__)


def _json(payload, status=200):
    return HttpResponse(json.dumps(payload), status=status, content_type="application/json")


def healthz(request):
    """Process liveness. No version, no detail (nothing to fingerprint)."""
    return HttpResponse("ok", content_type="text/plain")


def readyz(request):
    """DB reachable, migrations applied, the job runner is keeping up.

    **The body is `{"ready": bool}` and nothing else (REVIEW-S0 S12).** The
    per-check detail used to be in the response, which told an anonymous caller
    whether a deploy was half-applied and how deep the job queue was.
    API-CONTRACT §5.8 reserves counters for the token-protected `/metricsz` and
    specifies this as a readiness signal; ASVS V13 wants the exposed surface
    minimal. The detail is logged instead, where the operator reads it.

    # ponytail: the third check is "no job is overdue by more than five
    # minutes" rather than API-CONTRACT §5.8's "last job run < 5 min ago",
    # because the literal check needs a heartbeat job and there is no scheduler
    # to run one, so it would report not-ready forever -- and a probe that is
    # always red gets disabled. Ceiling: **until S1 lands, a green /readyz says
    # nothing at all about the runner**, because with an empty queue a dead
    # runner reads as ready. It closes itself in S1, not S8: `retention.purge`
    # is a standing recurring job, so from S1 a dead runner always leaves
    # something overdue. Upgrade path: once S8's systemd timer exists, a
    # heartbeat row makes this the literal check in two lines.
    """
    checks = {}

    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        checks["db"] = True
    except Exception:
        checks["db"] = False

    try:
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        checks["migrations_applied"] = not executor.migration_plan(executor.loader.graph.leaf_nodes())
    except Exception:
        checks["migrations_applied"] = False

    overdue = Job.objects.filter(
        run_after__lt=timezone.now() - timedelta(minutes=5),
        completed_at__isnull=True,
        failed_at__isnull=True,
    ).count()
    checks["job_runner"] = overdue == 0
    checks["jobs_overdue"] = overdue

    ready = checks["db"] and checks["migrations_applied"] and checks["job_runner"]
    if not ready:
        log.warning("readyz.not_ready", extra={"checks": checks})
    return _json({"ready": ready}, status=200 if ready else 503)
