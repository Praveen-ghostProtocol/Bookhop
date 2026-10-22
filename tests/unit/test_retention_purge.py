"""The expiry job — DATA-MODEL §10.2, `COMPLIANCE.md` §8.3.

*"Retaining beyond the purpose without a legal basis is its own breach. Build
the expiry job at the same time as the retention."* That sentence is the reason
deletion is in S1 at all and the reason this file exists in the same commit as
`erase_account`.

`purge_log` is how the claim is **proved** rather than asserted: *"This table is
how we prove it to G3/G4."* So every assertion here checks the row count **and**
the `purge_log` entry — a purge with no log is a purge nobody can audit, which
is the same as no purge at all from a reviewer's point of view.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import EmailLoginToken, PersonalDataAccessLog, UserTombstone
from apps.accounts.services import (
    PURGE_SKIP_LIST,
    RETENTION_FLOOR,
    TOKEN_PURGE_AFTER,
    erase_account,
    purge_expired,
)
from apps.core.models import IdempotencyKey, Job, PurgeLog

pytestmark = pytest.mark.django_db


def _log_for(table):
    return list(PurgeLog.objects.filter(table_name=table))


# --- each retention rule ---------------------------------------------------


def test_a_token_is_purged_seven_days_after_it_expires(student):
    """DATA-MODEL §2. Kept past expiry on purpose: an abuse investigation into
    "who requested links for this address" needs `requested_ip` for longer than
    ten minutes."""
    assert TOKEN_PURGE_AFTER == timedelta(days=7)
    fresh = EmailLoginToken.objects.create(
        user=student, token_hash="a" * 64, expires_at=timezone.now() - timedelta(days=1)
    )
    stale = EmailLoginToken.objects.create(
        user=student, token_hash="b" * 64, expires_at=timezone.now() - timedelta(days=8)
    )

    counts = purge_expired(job_run_id="run-1")

    assert counts["email_login_tokens"] == 1
    assert EmailLoginToken.objects.filter(id=fresh.id).exists(), "a token inside its window was purged"
    assert not EmailLoginToken.objects.filter(id=stale.id).exists()
    logged = _log_for("email_login_tokens")
    assert [row.object_pk for row in logged] == [str(stale.id)]
    assert logged[0].job_run_id == "run-1"
    assert logged[0].mode == "PURGE"


def test_an_expired_idempotency_key_is_purged(student):
    """DATA-MODEL §5's 24-hour retention. **Nothing else deletes them**, and a
    table that only grows is a retention breach by default."""
    live = IdempotencyKey.objects.create(
        user_id=student.id, key="live", endpoint="POST /x", request_hash="h",
        expires_at=timezone.now() + timedelta(hours=1),
    )
    dead = IdempotencyKey.objects.create(
        user_id=student.id, key="dead", endpoint="POST /x", request_hash="h",
        expires_at=timezone.now() - timedelta(minutes=1),
    )

    counts = purge_expired()

    assert counts["idempotency_keys"] == 1
    assert IdempotencyKey.objects.filter(id=live.id).exists()
    assert not IdempotencyKey.objects.filter(id=dead.id).exists()
    assert [row.object_pk for row in _log_for("idempotency_keys")] == [str(dead.id)]


def test_an_access_log_row_is_purged_at_one_year(staff, student):
    """§7 row 16: *"Rotated and erased at 1 yr."*"""
    old = PersonalDataAccessLog.objects.create(
        staff=staff, subject_pseudonym=student.person_pseudonym,
        fields_accessed=["email"], purpose="support",
        occurred_at=timezone.now() - RETENTION_FLOOR - timedelta(days=1),
    )
    recent = PersonalDataAccessLog.objects.create(
        staff=staff, subject_pseudonym=student.person_pseudonym,
        fields_accessed=["email"], purpose="support",
    )

    counts = purge_expired()

    assert counts["personal_data_access_log"] == 1
    assert not PersonalDataAccessLog.objects.filter(id=old.id).exists()
    assert PersonalDataAccessLog.objects.filter(id=recent.id).exists()


def test_the_tombstone_hash_goes_at_one_year_and_the_pseudonym_stays(student, salt):
    """§7 row 3 and §10.1. **The tombstone row itself stays**: the pseudonym is
    what the transaction record refers to, so purging the row would destroy the
    thing erasure was designed to preserve. Only the `email_hash` expires."""
    erase_account(student)
    tombstone = UserTombstone.objects.get()
    UserTombstone.objects.filter(person_pseudonym=tombstone.person_pseudonym).update(
        purge_due_at=timezone.now() - timedelta(seconds=1)
    )

    counts = purge_expired()
    tombstone.refresh_from_db()

    assert counts["user_tombstones"] == 1
    assert tombstone.email_hash is None
    assert tombstone.salt_version is None, (
        "a salt version with no hash cannot be retired; §7 row 24's CHECK is both-or-neither"
    )
    assert tombstone.purged_at is not None
    assert tombstone.person_pseudonym is not None
    assert UserTombstone.objects.count() == 1
    assert _log_for("user_tombstones")[0].object_pk == str(tombstone.person_pseudonym)


def test_a_tombstone_inside_its_year_is_untouched(student, salt):
    erase_account(student)
    counts = purge_expired()
    assert counts["user_tombstones"] == 0
    assert UserTombstone.objects.get().email_hash is not None
    assert _log_for("user_tombstones") == []


# --- the job ---------------------------------------------------------------


def test_the_job_is_idempotent_under_at_least_once_delivery(student, salt):
    """API-CONTRACT §4.4. Every rule is a timestamp comparison, so a second run
    finds nothing left and writes **no** second `purge_log` row — which matters
    because `purge_log` is the evidence, and duplicated evidence is wrong
    evidence."""
    EmailLoginToken.objects.create(
        user=student, token_hash="c" * 64, expires_at=timezone.now() - timedelta(days=9)
    )
    first = purge_expired(job_run_id="a")
    logged = PurgeLog.objects.count()

    second = purge_expired(job_run_id="b")

    assert first["email_login_tokens"] == 1
    assert second["email_login_tokens"] == 0
    assert PurgeLog.objects.count() == logged


def test_the_handler_reschedules_itself(student, db):
    """A standing recurring job, which is also what closes the ceiling
    `apps/core/views.readyz` records: with an empty queue a dead runner reads as
    ready, and from S1 there is always something scheduled."""
    from apps.accounts.jobs import PURGE_INTERVAL_HOURS, retention_purge

    retention_purge({"reschedule": True})
    nxt = Job.objects.filter(kind="retention.purge").order_by("-id").first()
    assert nxt is not None
    assert nxt.run_after > timezone.now() + timedelta(hours=PURGE_INTERVAL_HOURS - 1)


def test_the_job_kind_is_registered_so_enqueue_cannot_silently_drop_it():
    """`apps.core.services.enqueue` refuses an unregistered kind. An unimported
    handler module would therefore be a refusal at enqueue time rather than a
    job that never runs — but only if the import actually happens, which is
    `AccountsConfig.ready`'s job."""
    from apps.core.jobs import REGISTRY

    assert "retention.purge" in REGISTRY
    assert "accounts.send_magic_link" in REGISTRY


def test_the_runner_executes_the_purge_end_to_end(student, salt):
    """Through `run_pending_jobs`, not by calling the handler — so the
    registration, the claim and the handler are exercised together."""
    from apps.core.jobs import run_pending_jobs
    from apps.core.services import enqueue

    EmailLoginToken.objects.create(
        user=student, token_hash="d" * 64, expires_at=timezone.now() - timedelta(days=9)
    )
    enqueue("retention.purge", {"reschedule": False})

    ok, failed = run_pending_jobs(limit=5)

    assert (ok, failed) == (1, 0)
    assert not EmailLoginToken.objects.filter(token_hash="d" * 64).exists()
    assert PurgeLog.objects.filter(table_name="email_login_tokens").exists()


# --- the skip-list ---------------------------------------------------------


def test_the_skip_list_names_a_reason_for_every_table():
    """DATA-MODEL §10.2's *"explicit skip-list"*, as data rather than as prose,
    so S6 does not have to remember `repeat_infringer_records` and a reviewer
    can see that each omission is a decision."""
    assert "repeat_infringer_records" in PURGE_SKIP_LIST
    assert "r.5(5)" in PURGE_SKIP_LIST["repeat_infringer_records"]
    for table, reason in PURGE_SKIP_LIST.items():
        assert len(reason) > 20, f"{table} is skipped with no stated reason"


def test_the_append_only_tables_are_skipped_and_the_conflict_is_recorded():
    """**An open contract conflict, named here rather than coded around.**

    DATA-MODEL §2 gives `consents` and `age_verification_events` a retention of
    *"account life + 1 year"*, and §10.1 step 7 lists both as **untouched** by
    erasure. Both are append-only by the trigger the contract itself asks for —
    so *nothing can ever delete them*, and the stated retention is
    unimplementable as written.

    The charter is explicit that a contract that cannot be implemented as
    written is an escalation to cto and *"never resolve a contract conflict by
    coding around it"*. So the job skips them, the skip states the conflict, and
    this test keeps it visible until cto rules. Dropping the trigger to satisfy
    the retention would be the coding-around.
    """
    for table in ("consents", "age_verification_events"):
        assert table in PURGE_SKIP_LIST
        assert "conflict" in PURGE_SKIP_LIST[table] or "Raised to cto" in PURGE_SKIP_LIST[table], (
            f"{table}'s skip no longer records the retention-vs-append-only conflict"
        )


def test_no_skip_listed_table_is_purged(student, staff, salt):
    """The skip-list, as behaviour. A list nothing checks is a comment."""
    from apps.accounts.models import AgeVerificationEvent, Consent, NoticeVersion

    erase_account(student)
    before = {
        "consents": Consent.objects.count(),
        "age_verification_events": AgeVerificationEvent.objects.count(),
        "notice_versions": NoticeVersion.objects.count(),
    }
    UserTombstone.objects.update(purge_due_at=timezone.now() - timedelta(seconds=1))

    purge_expired()

    assert Consent.objects.count() == before["consents"]
    assert AgeVerificationEvent.objects.count() == before["age_verification_events"]
    assert NoticeVersion.objects.count() == before["notice_versions"]
    purged_tables = set(PurgeLog.objects.values_list("table_name", flat=True))
    assert purged_tables.isdisjoint(PURGE_SKIP_LIST), (
        f"the purge touched a skip-listed table: {purged_tables & set(PURGE_SKIP_LIST)}"
    )
