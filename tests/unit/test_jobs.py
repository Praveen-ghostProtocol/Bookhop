"""The Postgres-backed job runner — ADR-001 §2.4, API-CONTRACT §4.4."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone

from apps.core import jobs as jobs_module
from apps.core.jobs import run_pending_jobs
from apps.core.models import Job
from apps.core.services import enqueue

pytestmark = pytest.mark.django_db


@pytest.fixture
def counter():
    calls = []

    @jobs_module.handler("test.counting")
    def _handler(payload):
        calls.append(payload)

    yield calls
    del jobs_module.REGISTRY["test.counting"]


@pytest.fixture
def exploding():
    @jobs_module.handler("test.exploding")
    def _handler(payload):
        raise ValueError("nope")

    yield
    del jobs_module.REGISTRY["test.exploding"]


def test_enqueue_refuses_an_unregistered_kind():
    with pytest.raises(ValueError, match="no handler registered"):
        enqueue("test.nothing_listens", {})


def test_a_due_job_runs_once_and_is_marked_complete(counter):
    enqueue("test.counting", {"n": 1})
    assert run_pending_jobs() == (1, 0)
    assert counter == [{"n": 1}]
    assert run_pending_jobs() == (0, 0)  # not run twice
    assert Job.objects.get().completed_at is not None


def test_a_future_job_is_not_run(counter):
    enqueue("test.counting", {}, run_after=timezone.now() + timedelta(minutes=10))
    assert run_pending_jobs() == (0, 0)
    assert counter == []


def test_a_failing_job_retries_with_backoff_then_fails_permanently(exploding):
    job_id = enqueue("test.exploding", {})
    Job.objects.filter(id=job_id).update(max_attempts=2)

    assert run_pending_jobs() == (0, 1)
    job = Job.objects.get(id=job_id)
    assert job.attempts == 1 and job.failed_at is None
    assert job.run_after > timezone.now()
    assert "ValueError" in job.last_error

    Job.objects.filter(id=job_id).update(run_after=timezone.now())
    assert run_pending_jobs() == (0, 1)
    job = Job.objects.get(id=job_id)
    assert job.attempts == 2 and job.failed_at is not None

    Job.objects.filter(id=job_id).update(run_after=timezone.now())
    assert run_pending_jobs() == (0, 0)  # a failed job is not picked up again


def test_a_job_with_no_handler_fails_loudly_rather_than_silently(counter):
    Job.objects.create(kind="test.unregistered", payload={}, max_attempts=1)
    assert run_pending_jobs() == (0, 1)
    job = Job.objects.get()
    assert job.failed_at is not None
    assert "no handler registered" in job.last_error


def test_a_job_locked_by_a_live_worker_is_skipped(counter):
    """Claiming is a compare-and-swap, so a lock another worker holds is left
    alone. **This test used to stop here**, and what it demonstrated was M4: a
    job locked by a worker that died was never run again. The companion test
    below is the half that was missing."""
    job_id = enqueue("test.counting", {})
    Job.objects.filter(id=job_id).update(locked_at=timezone.now(), locked_by="other-worker")
    assert run_pending_jobs() == (0, 0)
    assert counter == []


def test_a_job_whose_lock_has_expired_is_reclaimed_and_run(counter):
    """M4. `SELECT ... FOR UPDATE SKIP LOCKED` releases its lock when the
    connection dies; a `locked_at` column does not. Without expiry, a worker
    killed by SIGKILL, OOM, power loss or a deploy mid-handler delivers the job
    **zero** times, permanently and silently — against the at-least-once
    guarantee in ADR-001 §2.4 and API-CONTRACT §4.4. From S1 that is
    `retention.purge`, a DPDP r.8(3) obligation that would stop running with no
    error."""
    job_id = enqueue("test.counting", {"n": 7})
    dead = timezone.now() - settings.JOB_LOCK_TIMEOUT - timedelta(minutes=1)
    Job.objects.filter(id=job_id).update(locked_at=dead, locked_by="dead-worker", attempts=1)

    assert run_pending_jobs() == (1, 0)
    assert counter == [{"n": 7}]
    job = Job.objects.get(id=job_id)
    assert job.completed_at is not None
    assert job.locked_by != "dead-worker", "the reclaiming worker must own the lock it took"


def test_a_lock_exactly_at_the_timeout_boundary_is_not_yet_stale(counter):
    """The boundary, so the timeout is a real number rather than a direction."""
    job_id = enqueue("test.counting", {})
    just_inside = timezone.now() - settings.JOB_LOCK_TIMEOUT + timedelta(seconds=30)
    Job.objects.filter(id=job_id).update(locked_at=just_inside, locked_by="live-worker")
    assert run_pending_jobs() == (0, 0)
    assert counter == []


def test_an_expired_lock_does_not_resurrect_a_completed_or_failed_job(counter):
    job_id = enqueue("test.counting", {})
    dead = timezone.now() - settings.JOB_LOCK_TIMEOUT - timedelta(hours=1)
    Job.objects.filter(id=job_id).update(locked_at=dead, completed_at=timezone.now())
    assert run_pending_jobs() == (0, 0)

    Job.objects.filter(id=job_id).update(completed_at=None, failed_at=timezone.now())
    assert run_pending_jobs() == (0, 0)
    assert counter == []


def test_worker_ids_are_distinct():
    """S3. The previous generator returned one distinct value in 200 tries."""
    from apps.core.jobs import new_worker_id

    assert len({new_worker_id() for _ in range(200)}) == 200
