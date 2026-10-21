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
