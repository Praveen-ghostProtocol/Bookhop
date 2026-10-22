"""No job row retains a credential — RED TEAM ENGINEERING-MEMO §2, CRITICAL.

**The defect this file exists because of, stated plainly so it is not repeated.**
S1 put the raw single-use sign-in token into `jobs.payload`, which is a jsonb
column in the production database, and licensed it with a docstring saying *"the
row is deleted on completion"*. **Nothing in `apps/**` deleted a `Job` row and
`purge_expired` did not walk `jobs`.** So every magic link ever issued stayed in
the database in plaintext, a failed job parked live tokens for every student
caught by a mail outage, and `INFRA.md`'s nightly `pg_dump` was a file of
working sign-in links for named students.

`CLAUDE.md` rule 9 is the lesson and the file it was broken in is the point: a
document asserted a property, **nothing checked it**, and it was false — inside
the credential path, which is the one place the rule mattered most. These are
the checks. The memo named two of them; the rest follow from the same question
asked of each surface a payload can reach.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.services import JOB_RETENTION, purge_expired
from apps.core.jobs import redacted, run_pending_jobs
from apps.core.models import Job, PurgeLog

pytestmark = pytest.mark.django_db


@pytest.fixture
def sent_link(signup_campus, django_capture_on_commit_callbacks):
    """Request a link, run the queue, and hand back the raw token."""
    from apps.accounts.services import request_magic_link

    with django_capture_on_commit_callbacks(execute=True):
        request_magic_link("priya@example.ac.in", "198.51.100.7", "pytest")
    job = Job.objects.get(kind="accounts.send_magic_link")
    raw = job.payload["token"]
    run_pending_jobs(limit=5)
    return raw


# --- the memo's two named tests -------------------------------------------


def test_no_job_row_retains_a_credential_after_the_job_completes(sent_link):
    """The memo's `test_no_job_row_retains_a_credential`.

    Asserted on the **value**, not on the key name: a future handler that calls
    its credential `link` or `secret` would pass a key-name check and fail this
    one.
    """
    rows = list(Job.objects.values_list("id", "kind", "payload", "last_error"))
    assert rows, "no job rows at all — this test would pass vacuously"
    for job_id, kind, payload, last_error in rows:
        blob = f"{payload}{last_error}"
        assert sent_link not in blob, (
            f"jobs row {job_id} ({kind}) still holds the raw sign-in token. "
            "jobs.payload is jsonb in the production database and pg_dump copies "
            "it nightly (RED TEAM §2)."
        )


def test_purge_expired_covers_jobs(student):
    """The memo's second named check. `jobs` had **no retention rule at all**,
    which also made it a standing contradiction of `COMPLIANCE.md` §8.3 as
    quoted in `PurgeLog`'s own docstring."""
    done = Job.objects.create(
        kind="core.noop", payload={"a": 1},
        completed_at=timezone.now() - JOB_RETENTION - timedelta(days=1),
    )
    failed = Job.objects.create(
        kind="core.noop", payload={"a": 1},
        failed_at=timezone.now() - JOB_RETENTION - timedelta(days=1),
    )
    recent = Job.objects.create(kind="core.noop", payload={"a": 1}, completed_at=timezone.now())
    pending = Job.objects.create(kind="core.noop", payload={"a": 1})

    counts = purge_expired(job_run_id="r")

    assert counts["jobs"] == 2
    assert not Job.objects.filter(id__in=[done.id, failed.id]).exists()
    assert Job.objects.filter(id=recent.id).exists()
    assert Job.objects.filter(id=pending.id).exists(), (
        "a job still waiting to run was deleted; for `retention.purge` itself "
        "that would stop the purge ever running again"
    )
    assert PurgeLog.objects.filter(table_name="jobs").count() == 2


# --- the redaction, from each side ----------------------------------------


def test_a_completed_payload_keeps_its_key_names_and_no_values(sent_link):
    """Key names, not a redaction of known-secret keys (`CLAUDE.md` rule 15):
    *"which of these values is a credential?"* has no reliable answer, and
    *"does this finished job still need its input?"* does."""
    job = Job.objects.get(kind="accounts.send_magic_link")
    assert job.completed_at is not None
    assert set(job.payload) == {"_redacted_keys"}
    assert job.payload["_redacted_keys"] == ["host", "locale", "scheme", "token", "token_id"]


def test_a_terminally_failed_payload_is_redacted_too():
    """The failure path is where the old defect was worst: a failed row was
    **retained** with `last_error` set, parking live tokens for every student
    caught by a mail outage."""
    from apps.core.jobs import handler

    name = "test.always_fails"
    if name not in __import__("apps.core.jobs", fromlist=["REGISTRY"]).REGISTRY:
        @handler(name)
        def _boom(payload):
            raise RuntimeError(f"cannot send to {payload['token']}")

    Job.objects.create(
        kind=name, payload={"token": "a-very-secret-token-value"}, attempts=0, max_attempts=1
    )
    run_pending_jobs(limit=2)

    job = Job.objects.get(kind=name)
    assert job.failed_at is not None, "the job did not reach a terminal failure"
    assert set(job.payload) == {"_redacted_keys"}
    assert "a-very-secret-token-value" not in f"{job.payload}{job.last_error}", (
        "a terminally failed job kept its credential, which is the exact shape "
        "of the original defect"
    )


def test_last_error_is_scrubbed_of_every_payload_value():
    """`last_error` is a text column in the same database as `payload`, so a
    traceback carrying a payload value reinstates the credential the redaction
    just removed. Scrubbed **by value**, so a handler that interpolated the
    token into its own exception message is covered."""
    from apps.core.jobs import REGISTRY, handler

    name = "test.leaks_into_the_message"
    if name not in REGISTRY:
        @handler(name)
        def _leak(payload):
            raise RuntimeError(f"SMTP refused the recipient for {payload['token']}")

    Job.objects.create(
        kind=name, payload={"token": "another-secret-token-value"}, max_attempts=1
    )
    run_pending_jobs(limit=2)

    job = Job.objects.get(kind=name)
    assert job.last_error
    assert "another-secret-token-value" not in job.last_error
    assert "[redacted]" in job.last_error
    assert "RuntimeError" in job.last_error, (
        "the scrub removed the diagnosis as well as the secret"
    )


def test_a_retryable_failure_keeps_its_payload_because_the_retry_needs_it():
    """The stated residual, asserted as a deliberate choice rather than left to
    be discovered. A retry with a redacted payload could not run at all.

    The window is bounded by the token's own 10-minute expiry, after which the
    retained string is dead and `send_magic_link` refuses to deliver it — which
    `test_magic_link.py::test_a_stale_retry_does_not_deliver_a_dead_link`
    covers.
    """
    from apps.core.jobs import REGISTRY, handler

    name = "test.fails_once"
    if name not in REGISTRY:
        @handler(name)
        def _once(payload):
            raise RuntimeError("transient")

    Job.objects.create(kind=name, payload={"token": "x" * 20}, max_attempts=5)
    run_pending_jobs(limit=2)

    job = Job.objects.get(kind=name)
    assert job.failed_at is None, "a retryable failure was treated as terminal"
    assert job.payload["token"] == "x" * 20


def test_the_redaction_is_not_vacuous():
    """`CLAUDE.md` rule 12: the assertions above are about absences, and an
    absence is what a broken redactor reports."""
    assert redacted({"token": "s", "locale": "en"}) == {"_redacted_keys": ["locale", "token"]}
    assert redacted({}) == {"_redacted_keys": []}
    assert redacted(None) == {"_redacted_keys": []}


def test_the_docstring_no_longer_claims_the_row_is_deleted():
    """**The fourth part of the fix** — the memo is explicit that *"correcting
    the docstring is part of the fix, not a separate task"*, because the
    docstring was the thing that was false.

    Asserted rather than trusted, because the next reader will believe it again.
    """
    import apps.accounts.jobs as module

    text = module.send_magic_link.__doc__
    # Whitespace-normalised: the phrase wraps across lines in the source.
    assert "redacts the payload the moment it finishes" in " ".join(text.split()), (
        "the docstring no longer states what the code actually does"
    )


def test_nothing_in_apps_claims_a_job_row_is_deleted_on_completion():
    """The same claim could reappear in any docstring. One grep, over the tree
    that would make it, rather than one assertion per file.

    **The guard fired on its own explanation first** — the docstrings describing
    the defect quoted the false sentence verbatim, so the grep matched the
    account of the bug as well as the bug. `CLAUDE.md` rule 13's order of
    resort: the prose was paraphrased (ours to change) rather than the match
    narrowed (which would have weakened the control for every future file).
    """
    import pathlib

    apps_dir = pathlib.Path(__file__).resolve().parents[2] / "apps"
    files = list(apps_dir.rglob("*.py"))
    assert files, "no source files found — this test would pass vacuously"
    offenders = [
        path.relative_to(apps_dir.parent).as_posix()
        for path in files
        if "row is deleted on completion" in path.read_text(encoding="utf-8")
    ]
    assert offenders == [], (
        "RED TEAM §2: a Job row is **not** deleted on completion — its payload is "
        f"redacted and the row is purged after {JOB_RETENTION.days} days: {offenders}"
    )


# --- the link the email carries -------------------------------------------


def test_the_payload_carries_a_scheme_and_host_so_the_link_is_absolute(
    signup_campus, django_capture_on_commit_callbacks
):
    """**A job has no request, so it has no scheme or host.** Frontend's
    `templates/email/magic_link.body.txt` builds
    `{{ scheme }}://{{ host }}/auth/c/{{ token }}`, and both rendered empty —
    so the primary journey's first email contained a broken link.

    Backend passes the **two pieces**, not a built URL, and that is an
    ownership line rather than a preference: `/auth/c/{token}` is a route in
    `web/urls.py`, which is frontend-developer's, and backend building the path
    would hard-code another agent's URL into a Python file they cannot edit.
    """
    from apps.accounts.services import request_magic_link

    with django_capture_on_commit_callbacks(execute=True):
        request_magic_link("priya@example.ac.in", None, "pytest")

    payload = Job.objects.get(kind="accounts.send_magic_link").payload
    assert payload["scheme"] in ("http", "https")
    assert payload["host"]
    assert "://" not in payload["host"]


def test_the_payload_carries_no_name_or_campus(signup_campus, django_capture_on_commit_callbacks):
    """Frontend's reasoning, kept as a test so it is not undone by a future
    "helpful" addition: **a sign-in email can arrive at an address whose owner
    never requested it**, so greeting them by name would move the enumeration
    leak the 202 response exists to prevent into the mailbox. A payload carrying
    a name is also one more thing a retained job row discloses."""
    from apps.accounts.services import request_magic_link

    with django_capture_on_commit_callbacks(execute=True):
        request_magic_link("priya@example.ac.in", None, "pytest")

    payload = Job.objects.get(kind="accounts.send_magic_link").payload
    assert "display_name" not in payload
    assert "campus_name" not in payload


def test_an_absolute_origin_is_refused_rather_than_defaulted(settings):
    """**No `localhost` default.** A default would email a student a link to
    their own machine — a plausible-looking value that fails only for the
    recipient and passes every test, which is the defect class this project
    keeps finding."""
    from apps.core.request_context import public_origin, reset_request, set_request

    settings.PUBLIC_ORIGIN = ""
    token = set_request(request_id="r")
    try:
        with pytest.raises(RuntimeError, match="BOOKHOP_PUBLIC_ORIGIN"):
            public_origin()
    finally:
        reset_request(token)


def test_a_configured_origin_is_used_outside_a_request(settings):
    from apps.core.request_context import public_origin, reset_request, set_request

    settings.PUBLIC_ORIGIN = "https://bookhop.example/"
    token = set_request(request_id="r")
    try:
        assert public_origin() == ("https", "bookhop.example")
    finally:
        reset_request(token)
