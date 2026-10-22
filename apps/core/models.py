"""apps.core models — DATA-MODEL.md §1, §5 (idempotency_keys), §8 (audit_log, jobs).

Conventions taken from DATA-MODEL §0 and followed without exception:
  * enums are text + CHECK, never a native enum type;
  * every timestamp is aware (USE_TZ=True), stored UTC;
  * table names are the snake_case names in DATA-MODEL, set explicitly, so the
    deny-list test in tests/unit/test_forbidden_schema.py reads the same names
    the contract does.

Two places where this file cannot match the contract's DDL exactly on the
local engine are recorded in company/architecture/ENGINE-DIVERGENCE.md:
`campuses.email_domains` (text[] vs jsonb) and the absence of DB-side
`DEFAULT now()`.
"""

from django.db import models
from django.utils import timezone

# Enum value sets. One definition per enum, used by both the field choices and
# the CHECK constraint, so the two can never drift.
GATES = ("B", "C", "D")
SCOPE_TYPES = ("GLOBAL", "CAMPUS")
ACTOR_TYPES = ("USER", "STAFF", "SYSTEM")


def _check_in(column, values):
    return models.Q(**{f"{column}__in": list(values)})


class City(models.Model):
    """DATA-MODEL §1 `cities` — global, not tenant-scoped (ADR-002 §2)."""

    name = models.TextField()
    state = models.TextField()
    country_code = models.TextField(default="IN")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "cities"
        constraints = [models.UniqueConstraint(fields=["name", "state"], name="cities_name_state_uniq")]

    def __str__(self):
        return f"{self.name}, {self.state}"


class Campus(models.Model):
    """DATA-MODEL §1 `campuses`.

    `discovery_enabled_at` is the legal gate (ADR-002 §4). NULL means closed and
    NULL is the default, so a campus is closed unless a named human opened it
    with `manage.py open_discovery`. Do not add a settings flag, a property or a
    convenience setter that writes this column: the only writer is that command,
    and it refuses without a complete `gate_authorisations` row.
    """

    city = models.ForeignKey(City, on_delete=models.PROTECT, db_column="city_id", related_name="campuses")
    name = models.TextField()
    slug = models.TextField(unique=True)
    # DATA-MODEL says text[]. jsonb list here because SQLite has no array type;
    # the only operation is membership. See ENGINE-DIVERGENCE.md §2.1.
    email_domains = models.JSONField(default=list)
    legal_entity = models.ForeignKey(
        "LegalEntity", null=True, blank=True, on_delete=models.PROTECT,
        db_column="legal_entity_id", related_name="campuses",
    )
    discovery_enabled_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    timezone_name = models.TextField(default="Asia/Kolkata", db_column="timezone")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "campuses"

    def __str__(self):
        return self.slug

    @property
    def discovery_open(self):
        return self.discovery_enabled_at is not None


class LegalEntity(models.Model):
    """DATA-MODEL §1 `legal_entities`.

    Every column is nullable because the row exists before the company does.
    `registered_address` is the only address column permitted anywhere in the
    database (ADR-003 §2.3) and the deny-list test allows it here and nowhere
    else.
    """

    legal_name = models.TextField(null=True, blank=True)
    cin = models.TextField(null=True, blank=True)
    incorporation_date = models.DateField(null=True, blank=True)
    inc20a_filed_at = models.DateField(null=True, blank=True)
    registered_address = models.TextField(null=True, blank=True)
    grievance_officer_name = models.TextField(null=True, blank=True)
    grievance_officer_email = models.TextField(null=True, blank=True)
    grievance_officer_phone = models.TextField(null=True, blank=True)
    nodal_contact_name = models.TextField(null=True, blank=True)
    nodal_contact_email = models.TextField(null=True, blank=True)
    nodal_contact_phone = models.TextField(null=True, blank=True)
    cert_in_poc_name = models.TextField(null=True, blank=True)
    cert_in_poc_email = models.TextField(null=True, blank=True)
    cert_in_poc_phone = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "legal_entities"

    def __str__(self):
        return self.legal_name or "(not yet incorporated)"


class GateAuthorisation(models.Model):
    """DATA-MODEL §1 `gate_authorisations` — append-only.

    **No agent writes this row.** It records a named human's authorisation plus
    the evidence checklist in ADR-002 §4.1(b). UPDATE is blocked by a trigger
    except for `revoked_at`/`revoked_reason`; DELETE is blocked outright
    (migration 0002).
    """

    gate = models.TextField()
    scope_type = models.TextField()
    scope_id = models.BigIntegerField(null=True, blank=True)
    legal_entity = models.ForeignKey(
        LegalEntity, on_delete=models.PROTECT, db_column="legal_entity_id",
        related_name="gate_authorisations",
    )
    evidence = models.JSONField()
    authorised_by_human = models.TextField()
    authorised_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "gate_authorisations"
        constraints = [
            models.CheckConstraint(condition=_check_in("gate", GATES), name="gate_auth_gate_chk"),
            models.CheckConstraint(condition=_check_in("scope_type", SCOPE_TYPES), name="gate_auth_scope_chk"),
        ]


class FeatureFlag(models.Model):
    """DATA-MODEL §1 `feature_flags`. Not the discovery gate — see Campus."""

    key = models.TextField(primary_key=True)
    enabled = models.BooleanField(default=False)
    scope_type = models.TextField(default="GLOBAL")
    scope_id = models.BigIntegerField(null=True, blank=True)
    updated_by = models.TextField()
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "feature_flags"
        constraints = [
            models.CheckConstraint(condition=_check_in("scope_type", SCOPE_TYPES), name="flag_scope_chk"),
        ]


class AuditLog(models.Model):
    """DATA-MODEL §8 `audit_log` — append-only, tamper-evident hash chain.

    `row_hash = sha256(prev_hash || canonical_json(row minus hashes))`.

    The chain is kept linear by `prev_hash` being UNIQUE: two concurrent
    appenders that read the same chain head cannot both commit, so the loser
    retries against the new head instead of forking the chain. That replaces a
    lock and works the same on both engines.

    UPDATE and DELETE are blocked by a database trigger (migration 0002), so
    "append-only" is a property of the database and not of the service layer.
    """

    actor_type = models.TextField()
    # FK to users lands in S1 with the users table (expand-then-contract,
    # INFRA §4). Nullable bigint until then, as DATA-MODEL specifies NULL.
    actor_id = models.BigIntegerField(null=True, blank=True)
    actor_pseudonym = models.UUIDField(null=True, blank=True)
    action = models.TextField()
    object_type = models.TextField()
    object_id = models.TextField(null=True, blank=True)
    before_hash = models.TextField(null=True, blank=True)
    after_hash = models.TextField(null=True, blank=True)
    request_id = models.TextField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    prev_hash = models.TextField(unique=True)
    row_hash = models.TextField()

    class Meta:
        db_table = "audit_log"
        indexes = [
            models.Index(fields=["occurred_at"], name="audit_occurred_idx"),
            models.Index(fields=["object_type", "object_id"], name="audit_object_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=_check_in("actor_type", ACTOR_TYPES), name="audit_actor_type_chk"),
        ]


class Job(models.Model):
    """DATA-MODEL §8 `jobs`. At-least-once, so every handler is idempotent."""

    kind = models.TextField()
    payload = models.JSONField(default=dict)
    run_after = models.DateTimeField(default=timezone.now)
    attempts = models.SmallIntegerField(default=0)
    max_attempts = models.SmallIntegerField(default=5)
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.TextField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "jobs"
        indexes = [
            models.Index(
                fields=["run_after"],
                name="jobs_due_idx",
                condition=models.Q(completed_at__isnull=True, failed_at__isnull=True),
            ),
        ]


class RateLimitCounter(models.Model):
    """A fixed-window request counter — API-CONTRACT §2.4, ADR-001 §2.4.

    **A deviation from ADR-001 §2.4's stated mechanism, raised to cto rather
    than taken silently.** The ADR says *"Rate limiting and the small amount of
    caching use **Django's database cache backend**, for the same reason: it
    removes Redis."* This is a table instead, for two reasons:

    1. **`CLAUDE.md` rule 13.** Django's `DatabaseCache` table has a column
       literally named `value`, which is a W1b money token, so the P14 schema
       guard went red on a table created by a migration — on a *mandated*
       mechanism, with the tempting fix being an entry in `MONEY_WORDS_EXEMPT`
       that would then exempt the name **database-wide, including on a model**.
       Rule 13's first resort is *rename our own name*; owning the table is how
       a name becomes ours to choose. Three columns, no exemption, control at
       full strength.
    2. **The increment becomes atomic.** The cache backend's `incr` is a
       read-then-write, so N simultaneous requests can each read the same count
       and all pass. `UPDATE … SET hit_count = hit_count + 1` is atomic on both
       engines, which removes the looser of the two ceilings ADR-001 §2.4's own
       note records.

    The ADR's *reason* — no Redis — is unaffected: this is one small table in
    the database we already have. Nothing else in the codebase uses a cache, so
    the backend is removed rather than replaced.

    # ponytail: fixed window, one row per (bucket, subject, window). Ceiling:
    # window edges are sloppy, so a caller can get up to 2× the limit across a
    # boundary — 10 in a bad minute for a 5/hour limit, which is ADR-001 §2.4's
    # documented cost of a fixed window over a sliding one. Upgrade path: the
    # ADR names it, a Redis token bucket, and the trigger is a measured abuse
    # incident rather than a feeling.
    """

    bucket = models.TextField()
    #: A **hash** of the subject, never the subject. An email address or an IP
    #: in a rate-limit row is personal data in a table nobody thinks of as
    #: holding any, and `COMPLIANCE.md` §7's standing rule makes a field with no
    #: §7 row a defect. The hash is one-way and the row is purged with its
    #: window, so there is nothing to inventory.
    subject_hash = models.TextField()
    window_started_at = models.DateTimeField()
    hit_count = models.IntegerField(default=0)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "rate_limit_counters"
        constraints = [
            models.UniqueConstraint(
                fields=["bucket", "subject_hash", "window_started_at"],
                name="rate_limit_window_uniq",
            ),
        ]
        indexes = [models.Index(fields=["expires_at"], name="rate_limit_expires_idx")]


class PurgeLog(models.Model):
    """DATA-MODEL §8 `purge_log` — S1. Proof the expiry job ran.

    `COMPLIANCE.md` §8.3: *"Retaining beyond the purpose without a legal basis
    is its own breach. Build the expiry job at the same time as the
    retention."* This table is how we prove it to G3/G4 — without it, "we purge
    after a year" is a claim about a cron job nobody can audit.

    It lives in `apps.core` beside `jobs` and `audit_log` rather than in
    `apps.accounts`, because every later slice's retention writes to it and
    `apps.core` is the one app nothing else may depend on in the other
    direction.

    `object_pk` is **text**, not a bigint: `user_tombstones`'s primary key is a
    uuid, and a column that could hold either is a column that holds the
    printed form of both.
    """

    table_name = models.TextField()
    object_pk = models.TextField()
    purge_due_at = models.DateTimeField(null=True, blank=True)
    purged_at = models.DateTimeField(default=timezone.now)
    job_run_id = models.TextField(null=True, blank=True)
    mode = models.TextField()

    class Meta:
        db_table = "purge_log"
        indexes = [
            models.Index(fields=["table_name", "purged_at"], name="purge_log_table_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=_check_in("mode", ("PURGE", "PSEUDONYMISE")), name="purge_log_mode_chk"
            ),
        ]


class IdempotencyKey(models.Model):
    """DATA-MODEL §5 `idempotency_keys`. Semantics in API-CONTRACT §4.1.

    The insert of the row *is* the lock: UNIQUE (user_id, key) means two
    simultaneous retries cannot both execute the handler.
    """

    # FK to users lands in S1 (expand-then-contract).
    user_id = models.BigIntegerField(null=True, blank=True)
    key = models.TextField()
    endpoint = models.TextField()
    request_hash = models.TextField()
    response_status = models.SmallIntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "idempotency_keys"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "key"], name="idempotency_user_key_uniq"),
            # QA-S0 B3. `UNIQUE (user_id, key)` does not fire when user_id is
            # NULL -- NULLs are distinct on both engines -- so an anonymous
            # replay claimed a second row instead of replaying the first, and
            # API-CONTRACT §5.1/§5.6 have anonymous POSTs. Anonymous keys share
            # one global namespace; the key is a client UUIDv4, so that is
            # sound. Reasoning in full in services.idempotent().
            models.UniqueConstraint(
                fields=["key"],
                condition=models.Q(user_id__isnull=True),
                name="idempotency_anon_key_uniq",
            ),
        ]
        indexes = [models.Index(fields=["expires_at"], name="idempotency_expires_idx")]
