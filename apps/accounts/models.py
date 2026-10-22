"""apps.accounts models — DATA-MODEL.md §2, plus §8's `personal_data_access_log`.

**This is the slice where the first real personal data enters the system**, so
three rules from `COMPLIANCE.md` §7 are enforced in the schema rather than in a
convention:

  * **No date of birth, in any column, in any state.** There is no
    `age_check_pending` table (DATA-MODEL amendment A-5 / PRD CG-5) and the
    ADR-003 §2.3 deny-list exception for `date_of_birth`/`dob`/`%birth%` was
    **withdrawn**, so the pattern is unconditional. `submit_age_declaration`
    takes a `date`, computes an age and writes an outcome; the date is a local
    variable that dies with the request.
  * **Deletion is tombstone-plus-purge.** `users` rows are never deleted;
    `user_tombstones` is the durable half and `person_pseudonym` survives,
    because the §9.2 repeat-transfer metric groups by it.
  * **Every column here cites its `COMPLIANCE.md` §7 row**, and a field with no
    row is a defect by that section's own standing rule.

Conventions are DATA-MODEL §0's and identical to `apps/core/models.py`: enums
are text + CHECK, never a native type; every timestamp is aware; `db_table` is
set explicitly so the P14 guard reads the same names the contract does.

Three places this file cannot match the contract's DDL on both engines are
recorded in `ENGINE-DIVERGENCE.md` §11: `users.email` (citext),
`personal_data_access_log.fields_accessed` (text[]) and the absence of DB-side
`DEFAULT now()`.
"""

import uuid

from django.db import models
from django.utils import timezone

# One definition per enum, shared by the field choices and the CHECK constraint
# so the two cannot drift (`CLAUDE.md` rule 10).
ROLES = ("STUDENT", "STAFF_SUPPORT", "STAFF_MODERATOR", "STAFF_ADMIN")
STAFF_ROLES = tuple(r for r in ROLES if r != "STUDENT")
USER_STATUSES = ("PENDING_VERIFICATION", "ACTIVE", "SUSPENDED", "TOMBSTONED")
LOCALES = ("en", "ta")
TOKEN_PURPOSES = ("LOGIN", "EMAIL_CHANGE", "STAFF_RECOVERY")
AGE_OUTCOMES = ("ADULT_CONFIRMED", "REJECTED_UNDER_18", "REVOKED_MINOR_DISCOVERED")
AGE_METHODS = ("SELF_DECLARED_DOB_SERVER_CHECKED", "STAFF_REVIEW")
CAMPUS_VERIFICATION_METHODS = ("INSTITUTIONAL_EMAIL", "STAFF_MANUAL")
#: DATA-MODEL §2 as amended by **A-25**, which adds `RANKING` and
#: `GRIEVANCE_PROCEDURE`. API-CONTRACT §5.1 already published both slugs
#: (`/legal/ranking` for r.5(3)(f), and the grievance-officer contact under
#: r.4(2)) while the enum had no value for either — so two legally required
#: pages had nowhere to be stored.
#:
#: **`GRIEVANCE_PROCEDURE` is the *procedure prose* and nothing else.** The
#: officer's name, designation, email, phone and the registered address are
#: already columns on `legal_entities`, and baking them into an immutable
#: versioned notice would create a second copy of a fact that changes without
#: the notice changing — and a stale grievance-officer contact is a direct
#: regulatory failure, not a cosmetic one. So that page **composes**: versioned
#: prose from here, officer fields interpolated from `legal_entities` at render
#: time. That is the same rule as the accepted-domains ruling — the value
#: arrives from the service, never baked into stored text — and noticing they
#: are the same rule is why the composition is right rather than fussy.
NOTICE_KINDS = (
    "PRIVACY", "TERMS", "SELLER_TERMS", "HANDOVER_GUIDANCE", "COMMUNITY_RULES",
    "RANKING", "GRIEVANCE_PROCEDURE",
)

#: DATA-MODEL §2 `consents.purpose_key` — **exactly** the reduced P6 set.
#: `payments` and `fee_billing` are dropped (ADR-003); nothing may be added here
#: without a privacy-compliance sign-off, because a new purpose is a new lawful
#: basis. `COMPLIANCE.md` §7 row 21 names `service_improvement` as the one that
#: would be needed if `search_events` ever carried an actor key, and it is
#: deliberately absent.
CONSENT_PURPOSES = (
    "account",
    "listing_publication",
    "location_proximity",
    "chat",
    "safety_moderation",
    "notifications",
)

#: Which purposes a student must have granted to act at all. API-CONTRACT §2.5
#: step 5 names `CONSENT_REQUIRED` and JOURNEYS J1 step 5 names the two:
#: *"Declines a required purpose (`account`, `listing_publication`): the screen
#: says which action that blocks and leaves the student signed in. Declining
#: `notifications` or `location_proximity` is fine and the product still
#: works."*
#:
#: `account` alone is required to *exist*; `listing_publication` is required to
#: publish, which is S2's guard and not S1's.
REQUIRED_CONSENT_PURPOSES = ("account",)

CONSENT_MECHANISMS = ("SIGNUP_FORM", "SETTINGS_TOGGLE", "STAFF_RECORDED")
TOMBSTONE_REASONS = ("USER_REQUEST", "MINOR_DISCOVERED", "STAFF_ENFORCEMENT")
DSR_KINDS = ("ACCESS", "CORRECTION", "ERASURE", "NOMINATION")


def _check_in(column, values):
    return models.Q(**{f"{column}__in": list(values)})


class User(models.Model):
    """DATA-MODEL §2 `users`. §7 rows 1, 3, 4, 5, 6, 7.

    **No `phone` column in v1**, and that is a decision rather than an omission:
    there is no SMS vendor and handover coordination happens in-app (ADR-001
    §2.5), so §7 row 2 has no field to apply to. If a phone is ever added it
    needs a purge rule and a salted-hash retention path identical to row 2.

    **`password` is staff-only** (§7 row 4, ADR-001 §2.5) and is NULL for every
    student, because students have no password at all. **Nothing in S1 writes
    it:** staff sign-in is password + TOTP in the Django admin, and the admin
    lands with S2's moderation queue (see the slice note). The column exists
    now because `erase_account` must NULL it and because retrofitting a column
    onto `users` later is a migration across the whole database.

    **`is_seed` lands here and the gated default manager does not.** ADR-002
    §2.3 puts `GatedManager` on `User` in **S2**, retrofitted in the same commit
    as the `Listing` managers, and TASKS §2 S2 carries it as a checkable line
    item. Nothing in S1 reads users through the discovery gate, so landing half
    the mechanism now would be scaffolding with a false floor — a `GatedManager`
    on `User` without `Meta.base_manager_name = "all_objects"` is the kind of
    line that is invisible when missing.
    """

    #: Survives deletion. Every metric in DATA-MODEL §9 groups by this, which is
    #: what makes erasure and measurement coexist (§10.3 assertion (g)).
    person_pseudonym = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    #: §7 row 3. DATA-MODEL says `citext`; stored lower-cased in a plain text
    #: column instead, because SQLite has no citext and — more importantly —
    #: `LIKE` is case-sensitive on PostgreSQL and case-insensitive on SQLite, so
    #: a case-insensitive lookup written locally passes locally and changes
    #: meaning in production (QA-S0 §8 item 4). Normalising on write and
    #: comparing exactly removes the whole class. `normalise_email` is the one
    #: definition; nothing compares an email any other way.
    #: NULL after erasure.
    email = models.TextField(null=True, blank=True, unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    #: §7 row 1. First name + initial only, by policy. NULL after erasure.
    display_name = models.TextField(null=True, blank=True)

    #: §7 row 4. Staff only (argon2). NULL for every student.
    password = models.TextField(null=True, blank=True)

    campus = models.ForeignKey(
        "core.Campus", on_delete=models.PROTECT, db_column="campus_id", related_name="users"
    )
    #: Denormalised, ADR-002 §2. NOT NULL from day one: retrofitting a tenant
    #: key is a migration across the whole database plus a rewrite of every
    #: metric.
    city = models.ForeignKey(
        "core.City", on_delete=models.PROTECT, db_column="city_id", related_name="users"
    )

    role = models.TextField(default="STUDENT")
    status = models.TextField(default="PENDING_VERIFICATION")

    #: §7 row 7 — the durable age fact. The DOB that produced it is never
    #: stored, so this boolean plus `age_verification_events` is the whole
    #: record.
    adult_verified = models.BooleanField(default=False)
    #: §7 row 6.
    campus_verified = models.BooleanField(default=False)

    #: Mechanism built, threshold unset (DATA-MODEL §11.5, COMPLIANCE §2.4).
    #: Nothing computes it in v1.
    business_seller_flag = models.BooleanField(default=False)

    is_seed = models.BooleanField(default=False)
    locale = models.TextField(default="en")

    created_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    tombstoned_at = models.DateTimeField(null=True, blank=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = "users"
        indexes = [models.Index(fields=["campus", "status"], name="users_campus_status_idx")]
        constraints = [
            models.CheckConstraint(condition=_check_in("role", ROLES), name="users_role_chk"),
            models.CheckConstraint(condition=_check_in("status", USER_STATUSES), name="users_status_chk"),
            models.CheckConstraint(condition=_check_in("locale", LOCALES), name="users_locale_chk"),
        ]

    def __str__(self):
        return str(self.person_pseudonym)

    @property
    def is_staff_member(self):
        return self.role in STAFF_ROLES

    @property
    def campus_verification_method(self):
        """How this student's campus was verified, or `None`. §7 row 6.

        **REVIEW-S1: frontend reads this attribute and it existed nowhere**, so
        `getattr(user, "campus_verification_method", None)` was always `None`,
        `signed_in_with_college_email` always returned False, and
        `trust.campus_mail` — the disclosure a buyer is *owed* — could never
        render. A fail-closed control that fails closed unconditionally is
        indistinguishable from a missing feature.

        **Derived from `campus_verifications.method`, never from
        `users.campus_verified`.** `COMPLIANCE.md` §7 row 6 is explicit about
        that, and the reason is the whole point of the string: the boolean says
        *we verified this student somehow*, which includes `STAFF_MANUAL`, and
        telling a buyer that a staff-re-verified student "signed in with a
        college email address" would be a false statement about the one trust
        signal the product makes.

        **It returns the method and never the domain** — also §7 row 6. The
        domain is stored (it is the campus evidence) and is never rendered.

        The latest verification wins: a student re-verified by staff after an
        email sign-in is `STAFF_MANUAL` now, and the string correctly stops
        rendering.

        # ponytail: one query per access, uncached. Ceiling: an N+1 on a page
        # that lists many students — none exists; the string renders on the
        # account page about oneself and, from S2, on a listing about its
        # seller. Upgrade path: `select_related` is not available for a reverse
        # one-to-many, so it would be an annotation on the listing query, which
        # is S2's to add when there is a list to annotate.
        """
        row = (
            self.campus_verifications.order_by("-verified_at", "-id")
            .values_list("method", flat=True)
            .first()
        )
        return row


class EmailLoginToken(models.Model):
    """DATA-MODEL §2 `email_login_tokens`.

    **The plaintext token is never stored** — only `sha256` of it — so a
    database read cannot sign anyone in. The token itself exists in the email
    and in the URL the student clicks, and nowhere else.

    `user_agent_family` is a **soft** binding: a mismatch is logged, not
    blocked. A hard binding breaks on webmail link prefetching and on a student
    who opens the mail on a laptop and the link on a phone, which is the normal
    case rather than the edge case (ADR-001 §2.5).

    Purge: rows deleted 7 days after `expires_at` by `retention.purge`.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column="user_id", related_name="login_tokens"
    )
    token_hash = models.TextField(unique=True)
    purpose = models.TextField(default="LOGIN")
    user_agent_family = models.TextField(null=True, blank=True)
    requested_ip = models.GenericIPAddressField(null=True, blank=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "email_login_tokens"
        indexes = [models.Index(fields=["expires_at"], name="login_token_expires_idx")]
        constraints = [
            models.CheckConstraint(
                condition=_check_in("purpose", TOKEN_PURPOSES), name="login_token_purpose_chk"
            ),
        ]


class AgeVerificationEvent(models.Model):
    """DATA-MODEL §2 `age_verification_events` — append-only. §7 row 7.

    **`note` must not contain a date of birth.** DATA-MODEL calls that a code
    review item; it is also a test here (`test_age_declaration.py`) and a
    service-layer refusal, because a reviewer typing a date into a free-text box
    is the one remaining route by which a DOB could reach storage.

    `user_pseudonym` is the durable half: it survives erasure, so the audit
    trail for "we checked this account was an adult" outlives the account by the
    one year r.8(3) requires. `user_id` goes NULL on purge.

    Retention: account life **+ 1 year**. Never user-deletable, and the
    append-only trigger in migration accounts/0002 is what makes that a property
    of the database rather than of the service layer.
    """

    user_pseudonym = models.UUIDField()
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        db_column="user_id", related_name="age_events",
    )
    outcome = models.TextField()
    method = models.TextField()
    reviewer = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        db_column="reviewer_id", related_name="age_reviews",
    )
    occurred_at = models.DateTimeField(default=timezone.now)
    note = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "age_verification_events"
        indexes = [models.Index(fields=["user_pseudonym"], name="age_event_pseudonym_idx")]
        constraints = [
            models.CheckConstraint(condition=_check_in("outcome", AGE_OUTCOMES), name="age_outcome_chk"),
            models.CheckConstraint(condition=_check_in("method", AGE_METHODS), name="age_method_chk"),
        ]


class CampusVerification(models.Model):
    """DATA-MODEL §2 `campus_verifications`. §7 row 6.

    **No enrolment artefact is ever stored.** §7 row 6 requires the evidence be
    purged immediately on successful verification; the magic-link design means
    there is no artefact to purge — the method, the matched domain and the
    timestamp are the whole record. The cheapest compliance win in the schema.

    `email_domain` is **the domain, never the address**, and the disclosure
    string a counterparty sees is gated on `method='INSTITUTIONAL_EMAIL'` and
    **never renders the domain itself** (§7 row 6 as amended).

    > **Divergence raised to cto, not resolved here.** `COMPLIANCE.md` §7 row 6
    > writes that gate as `campus_verifications.method = 'EMAIL_DOMAIN'`.
    > DATA-MODEL §2's CHECK says `INSTITUTIONAL_EMAIL`, and API-CONTRACT §1
    > makes DATA-MODEL normative for field names and enums, so the enum here is
    > `INSTITUTIONAL_EMAIL`. One of the two documents has the wrong token and it
    > is a one-line correction, but it is not a developer's to make.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column="user_id", related_name="campus_verifications"
    )
    method = models.TextField()
    email_domain = models.TextField(null=True, blank=True)
    verified_at = models.DateTimeField(default=timezone.now)
    verifier = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        db_column="verifier_id", related_name="campus_verifications_performed",
    )

    class Meta:
        db_table = "campus_verifications"
        constraints = [
            models.CheckConstraint(
                condition=_check_in("method", CAMPUS_VERIFICATION_METHODS),
                name="campus_verification_method_chk",
            ),
        ]


class NoticeVersion(models.Model):
    """DATA-MODEL §2 `notice_versions` — immutable.

    *"We can show what a user agreed to on a given date"* (`COMPLIANCE.md` §8.1)
    requires that a published notice can never be edited, so UPDATE and DELETE
    are blocked by a trigger and a correction is a **new version**.

    `HANDOVER_GUIDANCE`, not `HANDOVER_SAFETY` — API-CONTRACT amendment A-7,
    *"the identifier is where a label comes from"*.
    """

    kind = models.TextField()
    version = models.TextField()
    locale = models.TextField()
    body_md = models.TextField()
    sha256 = models.TextField()
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "notice_versions"
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "version", "locale"], name="notice_kind_version_locale_uniq"
            ),
            models.CheckConstraint(condition=_check_in("kind", NOTICE_KINDS), name="notice_kind_chk"),
            models.CheckConstraint(condition=_check_in("locale", LOCALES), name="notice_locale_chk"),
        ]

    def __str__(self):
        return f"{self.kind} {self.version} [{self.locale}]"


class Consent(models.Model):
    """DATA-MODEL §2 `consents` — append-only. §7 row 18.

    **Never updated in place.** A withdrawal **inserts** a row with
    `withdrawn_at` set, and the current state is the latest row per
    `(user_id, purpose_key)`. That is enforced by the trigger in migration
    accounts/0002, not by a convention, because this is the record that the
    deletion itself was lawful and it has to resist the application as well as
    the user — the same argument DATA-MODEL §8 makes for `audit_log`.

    **No pre-ticked boxes** (E-Com r.4(9), in force now) and **withdrawal is a
    settings toggle, not an email** (DPDP r.3(c)(i)). Both are UI contracts;
    the schema half is that a grant and a withdrawal are the same shape of row,
    so a withdrawal cannot be more expensive to record than a grant.

    Retention: account life **+ 1 year**. Not user-deletable.
    """

    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        db_column="user_id", related_name="consents",
    )
    user_pseudonym = models.UUIDField()
    purpose_key = models.TextField()
    notice_version = models.ForeignKey(
        NoticeVersion, on_delete=models.PROTECT,
        db_column="notice_version_id", related_name="consents",
    )
    granted_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    mechanism = models.TextField()
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "consents"
        indexes = [
            models.Index(fields=["user_pseudonym", "purpose_key"], name="consent_subject_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=_check_in("purpose_key", CONSENT_PURPOSES), name="consent_purpose_chk"
            ),
            models.CheckConstraint(
                condition=_check_in("mechanism", CONSENT_MECHANISMS), name="consent_mechanism_chk"
            ),
            #: A row is a grant **or** a withdrawal, never both and never
            #: neither. Without this, a row with both timestamps NULL is a
            #: consent record that says nothing, and the "latest row wins"
            #: reading of current state would silently treat it as a grant.
            models.CheckConstraint(
                condition=(
                    models.Q(granted_at__isnull=False, withdrawn_at__isnull=True)
                    | models.Q(granted_at__isnull=True, withdrawn_at__isnull=False)
                ),
                name="consent_grant_xor_withdrawal_chk",
            ),
        ]


class UserTombstone(models.Model):
    """DATA-MODEL §2 `user_tombstones` — the durable half of tombstone-plus-purge.

    `person_pseudonym` is the primary key and it **survives**, because
    repeat-transfer-@90d groups by it (§9.2) and because the counterparty's
    dispute needs the transaction record to keep referring to someone.

    **`email_hash` is salted with a server-side secret that is not in the
    database** (§7 rows 3 and 24), so a database-only compromise cannot
    re-identify by rainbow table — a sha256 of a predictable institutional
    address is otherwise enumerable from a roll list.

    `salt_version` is **not in DATA-MODEL §2's column list and is added here on
    `COMPLIANCE.md` §7 row 24's instruction**: *"Version it; keep at most two
    versions; retire a version when no live tombstone references it."* A
    tombstone that does not record which version hashed it cannot be found when
    that version is retired or compromised, so row 24's rotation procedure is
    unimplementable without this column. Raised to cto as a one-line DATA-MODEL
    §2 amendment rather than taken silently; it is not personal data (row 24
    says so) and `user_tombstones` is not a frozen table.

    **A restore to a new box loses hash matching, and that is expected.** The
    salt lives in the environment, not in the dump, so a restored database
    cannot match an `email_hash` it did not have the salt for. That is the
    property the external salt exists to produce, not a failure of the restore
    (`INFRA.md` §3.3's rehearsal should assert it rather than be surprised by
    it).

    **`email_hash` is for ban-evasion detection and dispute linkage only.**
    Using it to link a re-registered student to their old pseudonym would be
    purpose creep, so repeat-transfer-@90d undercounts delete-and-rejoin users
    and §9.2 says so out loud.
    """

    person_pseudonym = models.UUIDField(primary_key=True)
    #: §7 row 5 — the coarse campus code survives. FKs rather than bare bigints
    #: because ADR-002 §2's index requirement comes free with them and a campus
    #: is never deleted (PROTECT).
    campus = models.ForeignKey(
        "core.Campus", on_delete=models.PROTECT, db_column="campus_id", related_name="tombstones"
    )
    city = models.ForeignKey(
        "core.City", on_delete=models.PROTECT, db_column="city_id", related_name="tombstones"
    )
    email_hash = models.TextField(null=True, blank=True)
    salt_version = models.TextField(null=True, blank=True)
    tombstoned_at = models.DateTimeField(default=timezone.now)
    purge_due_at = models.DateTimeField()
    purged_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField()

    class Meta:
        db_table = "user_tombstones"
        indexes = [models.Index(fields=["purge_due_at"], name="tombstone_purge_due_idx")]
        constraints = [
            models.CheckConstraint(
                condition=_check_in("reason", TOMBSTONE_REASONS), name="tombstone_reason_chk"
            ),
            #: An `email_hash` with no `salt_version` cannot be retired or
            #: re-hashed, which is §7 row 24's whole procedure. Either both or
            #: neither.
            models.CheckConstraint(
                condition=(
                    models.Q(email_hash__isnull=True, salt_version__isnull=True)
                    | models.Q(email_hash__isnull=False, salt_version__isnull=False)
                ),
                name="tombstone_hash_has_salt_version_chk",
            ),
        ]


class DataSubjectRequest(models.Model):
    """DATA-MODEL §2 `data_subject_requests`.

    `due_at = received_at + 7 days` — **not 90**. `COMPLIANCE.md` §1.8 is
    explicit that 90 days is DPDP's ceiling and the operative number is 7
    because the tightest applicable clock governs. The 7 is in
    `services.DSR_DUE_AFTER`, imported, not retyped.

    **Nomination (s14) is included** because it is in the Act and nobody builds
    it (PRD US-X2).
    """

    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        db_column="user_id", related_name="subject_requests",
    )
    user_pseudonym = models.UUIDField()
    kind = models.TextField()
    received_at = models.DateTimeField(default=timezone.now)
    due_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    outcome = models.TextField(null=True, blank=True)
    nominee = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "data_subject_requests"
        indexes = [models.Index(fields=["due_at"], name="dsr_due_idx")]
        constraints = [
            models.CheckConstraint(condition=_check_in("kind", DSR_KINDS), name="dsr_kind_chk"),
        ]


class PersonalDataAccessLog(models.Model):
    """DATA-MODEL §8 `personal_data_access_log`. §7 row 16.

    DPDP r.6(1)(c) requires *"visibility on the accessing of such personal
    data"*. Every staff view of a student's profile, chat thread or report
    detail writes a row — **and the screen says so to the staff member**, which
    is most of the control (THREAT-MODEL §5.8).

    `subject_pseudonym`, not `subject_id`: the log outlives the account, and a
    log that pointed at a purged row would lose the thing it is evidence about.

    Not user-deletable; rotated and erased at 1 year. Access to the logs is
    itself logged — by `audit_log`, which this slice writes on every staff read.
    """

    staff = models.ForeignKey(
        User, on_delete=models.PROTECT, db_column="staff_id", related_name="data_accesses"
    )
    subject_pseudonym = models.UUIDField()
    #: DATA-MODEL says `text[]`. JSONField list, for the reason
    #: `campuses.email_domains` is one (DATA-MODEL §1 amendment A-16): SQLite
    #: cannot express an array and the only operation is membership on a short
    #: list. ENGINE-DIVERGENCE §11.
    fields_accessed = models.JSONField(default=list)
    purpose = models.TextField()
    request_id = models.TextField(null=True, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "personal_data_access_log"
        indexes = [
            models.Index(fields=["subject_pseudonym"], name="pdal_subject_idx"),
            models.Index(fields=["occurred_at"], name="pdal_occurred_idx"),
        ]
