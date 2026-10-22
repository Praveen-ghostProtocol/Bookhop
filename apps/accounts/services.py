"""apps.accounts service layer (L1) — API-CONTRACT §3, accounts block.

**The real contract** (API-CONTRACT §1): all business rules, all guards, all DB
access, all audit writes. L2 (`apps/accounts/api.py`) and L3 (`web/views.py`,
frontend's) both call these and neither touches the ORM.

Every mutating function here: **one database transaction**, with its `audit_log`
row written **inside** it, and notifications enqueued only `on_commit` so a
rolled-back change never sends an email.

Three rules this module exists to make true, not to describe:

**1. No date of birth is persisted anywhere, in any state.**
`submit_age_declaration` takes a `date`, computes an age, writes an outcome and
lets the date die with the request. There is no `age_check_pending` table
(DATA-MODEL amendment A-5 / PRD CG-5), the ADR-003 §2.3 deny-list exception for
`date_of_birth`/`dob`/`%birth%` is **withdrawn**, and `review_age` refuses a
`note` that looks like a date — because a reviewer typing one into a free-text
box is the last route by which a DOB could reach storage.

**2. Deletion is tombstone-plus-purge.** `erase_account` never issues
`DELETE FROM users`. The one place this module deletes a `users` row is the
under-18 rejection, where DATA-MODEL §2 is explicit that it must — see the note
on `submit_age_declaration`, which states the apparent conflict rather than
leaving a reader to find it.

**3. Consent is a ledger.** A grant and a withdrawal are the same shape of row,
appended, never updated — enforced by the trigger in migration accounts/0002.

Email comparison: **`normalise_email` is the only way an address is compared.**
`LIKE` is case-sensitive on PostgreSQL and case-insensitive on SQLite, so a
case-insensitive lookup written locally changes meaning in production (QA-S0 §8
item 4). Normalising on write and comparing exactly removes the class.
"""

import hashlib
import logging
import secrets
import unicodedata
from datetime import date, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.errors import (
    ConsentRequired,
    EmailDomainNotRecognised,
    NotAdultVerified,
    NotAuthenticated,
    NotCampusVerified,
    NotPermitted,
    Suspended,
    TokenAlreadyUsed,
    TokenExpired,
    TokenInvalid,
    UnderEighteen,
    ValidationFailed,
)
from apps.core.models import Campus, PurgeLog
from apps.core.request_context import public_origin
from apps.core.ratelimit import consume_quota
from apps.core.services import SYSTEM, enqueue, record_audit

from .models import (
    CONSENT_PURPOSES,
    LOCALES,
    REQUIRED_CONSENT_PURPOSES,
    AgeVerificationEvent,
    CampusVerification,
    Consent,
    DataSubjectRequest,
    EmailLoginToken,
    NoticeVersion,
    PersonalDataAccessLog,
    User,
    UserTombstone,
)

log = logging.getLogger("bookhop.security")

#: ADR-001 §2.5 and API-CONTRACT §5.1: a magic link is single-use with a
#: 10-minute expiry.
TOKEN_TTL = timedelta(minutes=10)

#: DATA-MODEL §2: `email_login_tokens` rows are deleted 7 days after
#: `expires_at` by the retention job. Kept past expiry because an abuse
#: investigation into "who requested links for this address" needs the
#: `requested_ip` for longer than ten minutes.
TOKEN_PURGE_AFTER = timedelta(days=7)

#: DATA-MODEL §2 `data_subject_requests`: **7 days, not 90.** `COMPLIANCE.md`
#: §1.8 — 90 is DPDP's ceiling and the tightest applicable clock governs. One
#: definition, imported by the model's callers and by the metric query.
#:
#: Named `DSR_DEADLINE` and not `DSR_DUE_AFTER`, which was the first draft:
#: `due` is a W1b money token and the ratified shape exemption is `due_at`, not
#: `due_after`, so W1c's source grep caught it. `CLAUDE.md` rule 13's order of
#: resort says **rename ours first** — it cost one rename, left the control at
#: full strength and added nothing to any document, where an exemption would
#: have widened `MONEY_TOKEN_SHAPE_EXEMPTIONS` database-wide.
DSR_DEADLINE = timedelta(days=7)

#: How long a **finished** `jobs` row survives — RED TEAM ENGINEERING-MEMO §2.
#:
#: Short on purpose. A finished job row is diagnostic residue, not a record:
#: what actually happened is in `audit_log` (append-only, hash-chained) and in
#: the structured log, both of which have their own one-year floor. Seven days
#: is long enough to read a failure the morning after a weekend outage and short
#: enough that an unredacted payload — the defect this constant exists because
#: of — cannot sit in a nightly `pg_dump` for a month.
JOB_RETENTION = timedelta(days=7)

#: DPDP r.8(3). The floor on everything personal, and the single number behind
#: `user_tombstones.purge_due_at`.
RETENTION_FLOOR = timedelta(days=365)

#: `COMPLIANCE.md` §1.4: adults only, checked on the server.
ADULT_AGE = 18


# --- email -----------------------------------------------------------------


def normalise_email(raw):
    """The one definition of what two addresses being "the same" means.

    NFKC first: `ＰＲＩＹＡ@example.ac.in` in fullwidth codepoints is the same
    mailbox as `priya@example.ac.in` to the receiving server, and would
    otherwise be a second account on the same address — which matters because
    `users.email` is the account identity and the campus evidence at once.
    """
    if not raw or not isinstance(raw, str):
        raise ValidationFailed("Enter your college email address.", field_errors={"email": ["Required."]})
    cleaned = unicodedata.normalize("NFKC", raw).strip().lower()
    if cleaned.count("@") != 1 or cleaned.startswith("@") or cleaned.endswith("@"):
        raise ValidationFailed(
            "That does not look like an email address.",
            field_errors={"email": ["Enter an address like you@example.ac.in."]},
        )
    local, _, domain = cleaned.partition("@")
    if "." not in domain or any(ch.isspace() for ch in cleaned):
        raise ValidationFailed(
            "That does not look like an email address.",
            field_errors={"email": ["Enter an address like you@example.ac.in."]},
        )
    return f"{local}@{domain}"


def email_domain(address):
    return address.partition("@")[2]


def campus_for_email(address):
    """The campus whose `email_domains` accepts this address, or None.

    # ponytail: fetch the active campuses and match in Python. Ceiling: linear
    # in the number of campuses. At the pilot's 2–3, and at a hundred, that is
    # one small indexed scan against a jsonb containment query that SQLite and
    # PostgreSQL spell differently — and a query whose two spellings must agree
    # is the engine-divergence class this project keeps paying for. Upgrade
    # path: a `campus_email_domains` table with a unique index on the domain,
    # the day a city has enough campuses for it to matter.
    """
    domain = email_domain(address)
    for campus in Campus.objects.filter(active=True).only("id", "city_id", "email_domains"):
        domains = campus.email_domains or []
        if any(normalise_email(f"x@{d}").partition("@")[2] == domain for d in domains if "." in str(d)):
            return campus
    return None


def accepted_email_domains(campus=None):
    """The domains to name on the "check your email" page (PRD AC-A1.2).

    **Generic, and never echoing the submitted address.** Without this line the
    enumeration-proof 202 and `EmailDomainNotRecognised` combine into a silent
    dead end, which the PRD calls the most likely first-run failure in the
    product — so it is a service-layer function rather than a template constant.
    """
    queryset = Campus.objects.filter(active=True)
    if campus is not None:
        queryset = queryset.filter(id=campus.id)
    domains = []
    for row in queryset.only("email_domains"):
        for domain in row.email_domains or []:
            if domain not in domains:
                domains.append(str(domain))
    return domains


# --- magic link ------------------------------------------------------------


def _token_hash(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _user_agent_family(user_agent):
    """A coarse family, not a fingerprint. Soft binding only (DATA-MODEL §2)."""
    if not user_agent:
        return None
    lowered = user_agent.lower()
    for family in ("android", "iphone", "ipad", "macintosh", "windows", "linux"):
        if family in lowered:
            return family
    return "other"


def request_magic_link(email: str, ip, user_agent) -> None:
    """ADR-001 §2.5. Raises RateLimited, EmailDomainNotRecognised.

    **The caller always answers 202, whatever this raises** (API-CONTRACT §5.1):
    a different response for an unknown address is an account-enumeration
    oracle. So every raise here is a signal to the caller *not to send an
    email*, never a message for the student.

    Creates the account on first request, in `PENDING_VERIFICATION`. The address
    having matched a campus `email_domains` entry **is** the campus evidence
    (ADR-001 §2.5 dividend 1), so no enrolment artefact is ever collected and
    §7 row 6 is satisfied by a boolean, a method and a timestamp.
    """
    address = normalise_email(email)

    # API-CONTRACT §2.4: 5/hour per email, 20/hour per IP. Checked before the
    # campus lookup so an attacker cannot use the rate limiter's own timing to
    # distinguish a recognised domain from an unrecognised one.
    consume_quota("auth.magic_link.email", address, limit=5, window=timedelta(hours=1))
    if ip:
        consume_quota("auth.magic_link.ip", str(ip), limit=20, window=timedelta(hours=1))

    campus = campus_for_email(address)
    if campus is None:
        log.info("auth.magic_link.domain_unrecognised", extra={"domain": email_domain(address)})
        raise EmailDomainNotRecognised(
            f"No active campus accepts {email_domain(address)!r}. The caller still "
            "answers 202 (API-CONTRACT §5.1); name the accepted domains instead "
            "(PRD AC-A1.2, accepted_email_domains())."
        )

    raw = secrets.token_urlsafe(32)
    with transaction.atomic():
        user = User.objects.filter(email=address).first()
        if user is None:
            user = User.objects.create(
                email=address, campus=campus, city_id=campus.city_id,
                status="PENDING_VERIFICATION",
            )
            record_audit(SYSTEM, "accounts.user_created", user, after={"campus": campus.slug})
        elif user.status == "SUSPENDED":
            # Not a message to the student — the caller still answers 202. A
            # suspended account must not be handed a working session.
            log.info("auth.magic_link.suspended", extra={"pseudonym": str(user.person_pseudonym)})
            raise Suspended("This account cannot sign in.")
        elif user.status == "TOMBSTONED":  # pragma: no cover - email is NULL after erasure
            raise Suspended("This account has been deleted.")

        token = EmailLoginToken.objects.create(
            user=user,
            token_hash=_token_hash(raw),
            purpose="LOGIN",
            user_agent_family=_user_agent_family(user_agent),
            requested_ip=ip or None,
            expires_at=timezone.now() + TOKEN_TTL,
        )
        record_audit(SYSTEM, "accounts.magic_link_requested", token)

        # on_commit: a rolled-back transaction must never send a working link.
        #
        # `scheme` and `host` are captured here, inside the request, because a
        # job has none and the email carries an **absolute** URL. Without them
        # frontend's template renders `://` and the student gets a dead link.
        scheme, host = public_origin()
        transaction.on_commit(
            lambda: enqueue(
                "accounts.send_magic_link",
                {
                    "token_id": token.id,
                    "token": raw,
                    "locale": user.locale,
                    "scheme": scheme,
                    "host": host,
                },
            )
        )


def consume_magic_link(token: str, ip, user_agent):
    """Returns User. Raises TokenInvalid, TokenExpired, TokenAlreadyUsed.

    **Single use is enforced by the database, not by a read-then-write.** The
    claim is a conditional UPDATE filtered on `consumed_at IS NULL`; two
    simultaneous clicks mean one row affected and one zero, so the loser gets
    `TokenAlreadyUsed` instead of a second session. That is also why this
    endpoint is API-CONTRACT §4.1's one idempotency-key exemption in its L3
    `GET /auth/c/{token}` form: **a single-use token is idempotent by
    construction**, which is the same property by a cheaper mechanism.

    A `user_agent_family` mismatch is **logged, not blocked** (DATA-MODEL §2):
    webmail link prefetching and "mail on the laptop, link on the phone" are
    the normal case, so a hard binding would break sign-in for ordinary use.
    """
    if not token or not isinstance(token, str):
        raise TokenInvalid("That sign-in link is not valid. Ask for a new one.")

    row = EmailLoginToken.objects.filter(token_hash=_token_hash(token)).select_related("user").first()
    if row is None:
        log.info("auth.consume.unknown_token")
        raise TokenInvalid("That sign-in link is not valid. Ask for a new one.")
    if row.consumed_at is not None:
        log.info("auth.consume.replayed", extra={"token_id": row.id})
        raise TokenAlreadyUsed("That link has already been used. Ask for a new one.")
    if row.expires_at <= timezone.now():
        log.info("auth.consume.expired", extra={"token_id": row.id})
        raise TokenExpired("That link has expired. Ask for a new one.")

    now = timezone.now()
    with transaction.atomic():
        claimed = EmailLoginToken.objects.filter(id=row.id, consumed_at__isnull=True).update(
            consumed_at=now
        )
        if not claimed:
            raise TokenAlreadyUsed("That link has already been used. Ask for a new one.")

        user = User.objects.select_for_update().get(id=row.user_id) if _supports_locking() else (
            User.objects.get(id=row.user_id)
        )
        if user.status == "SUSPENDED":
            raise Suspended("This account cannot sign in.")

        expected = _user_agent_family(user_agent)
        if row.user_agent_family and expected and row.user_agent_family != expected:
            log.info(
                "auth.consume.user_agent_mismatch",
                extra={"requested": row.user_agent_family, "used": expected},
            )

        fields = ["last_seen_at"]
        user.last_seen_at = now
        if user.email_verified_at is None:
            user.email_verified_at = now
            fields.append("email_verified_at")
        if not user.campus_verified:
            # ADR-001 §2.5 dividend 1: the domain match *is* the evidence.
            CampusVerification.objects.create(
                user=user,
                method="INSTITUTIONAL_EMAIL",
                email_domain=email_domain(user.email) if user.email else None,
                verified_at=now,
            )
            user.campus_verified = True
            fields.append("campus_verified")
        user.save(update_fields=fields)
        record_audit(user, "accounts.signed_in", user, after={"method": "MAGIC_LINK"})
    return user


def _supports_locking():
    from django.db import connection

    return connection.features.has_select_for_update


def outstanding_steps(user):
    """API-CONTRACT §5.1: `{needs: ["age","consent","campus"]}`.

    In JOURNEYS J1's order, so the client routes to the first outstanding one
    and the student does not meet the same screen twice.
    """
    needs = []
    if not user.adult_verified:
        needs.append("age")
    missing = missing_consents(user)
    if missing:
        needs.append("consent")
    if not user.campus_verified:
        needs.append("campus")
    return needs


# --- age (no DOB persisted, anywhere, in any state) ------------------------


def age_on(dob, today=None):
    """Whole years, computed on the server. `COMPLIANCE.md` §1.4 item 1: *"a
    date field, not a checkbox"* — a checkbox is not evidence."""
    today = today or timezone.localdate()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def submit_age_declaration(user, dob, ip):
    """Returns the outcome string. Raises UnderEighteen.

    **The declared date exists only inside this call.** It is a parameter, it
    is compared, and it is discarded. Nothing writes it to a table, a log, a
    cache or an audit payload — `record_audit` hashes its payloads, and the
    payload here does not contain the date either.

    **On the under-18 path the `users` row is deleted.** That looks like a
    violation of *"`DELETE FROM users` is never the answer"* and it is not, so
    the reasoning is here rather than in a reviewer's head:

      * DATA-MODEL §2 is explicit — *"**Under 18** ⇒ `403 NOT_ADULT_VERIFIED`,
        an `age_verification_events` row with `outcome='REJECTED_UNDER_18'`,
        **and the `users` row is deleted in the same transaction**"* — and PRD
        AC-A2.1 asserts the absence: *"after the request, there is **no `users`
        row** … for that email."*
      * Tombstone-plus-purge exists so that **an established account's
        transaction record survives erasure**. A rejected minor has no
        transaction record, and a tombstone would *retain* the fact that a
        specific email address belonged to a child — for a year, keyed to a
        hash of that address. That is the worse outcome, and it is the one the
        tombstone path would produce.
      * What survives is the audit trail §1.4 asks for: one
        `age_verification_events` row with the outcome, the method and the
        timestamp, carrying `user_pseudonym` and **no FK**, so nothing has to
        be rewritten when the row it pointed at goes.

    **Reachable only from `PENDING_VERIFICATION`,** which is not a convenience:
    `consents` and `age_verification_events` are append-only by trigger, so a
    cascade that tried to NULL their FKs would be *refused by the database*. A
    guard that keeps the delete to a user with no appended rows is the honest
    way to have both properties. A student who has already declared is done,
    which is also what JOURNEYS J1 describes.

    **The honest limitation, stated in the product and not only in a risk
    file:** this is a server-checked *declaration*. A 17-year-old who types an
    adult date is admitted and we cannot detect it (R-28). The controls for
    that are `review_age`'s `REVOKED_MINOR_DISCOVERED` path and the standing
    suspend-erase-log instruction — not the storage of the date.
    """
    if not isinstance(dob, date):
        raise ValidationFailed(
            "Enter your date of birth.",
            field_errors={"date_of_birth": ["Enter a date like 2004-08-21."]},
        )
    today = timezone.localdate()
    if dob > today:
        raise ValidationFailed(
            "That date is in the future.",
            field_errors={"date_of_birth": ["Check the year."]},
        )
    if user.adult_verified or user.status != "PENDING_VERIFICATION":
        raise ValidationFailed("Your age is already confirmed on this account.")

    pseudonym = user.person_pseudonym
    if age_on(dob, today) < ADULT_AGE:
        with transaction.atomic():
            AgeVerificationEvent.objects.create(
                user_pseudonym=pseudonym,
                user=None,  # the row this would point at is deleted below
                outcome="REJECTED_UNDER_18",
                method="SELF_DECLARED_DOB_SERVER_CHECKED",
                occurred_at=timezone.now(),
                note=None,  # never a date, and here never anything
            )
            record_audit(
                SYSTEM, "accounts.age_rejected", "User",
                after={"pseudonym": str(pseudonym), "outcome": "REJECTED_UNDER_18"},
            )
            User.objects.filter(id=user.id).delete()
        log.info("accounts.age_rejected", extra={"pseudonym": str(pseudonym)})
        raise UnderEighteen("BookHop is for students aged 18 and over.")

    with transaction.atomic():
        AgeVerificationEvent.objects.create(
            user_pseudonym=pseudonym,
            user=user,
            outcome="ADULT_CONFIRMED",
            method="SELF_DECLARED_DOB_SERVER_CHECKED",
            occurred_at=timezone.now(),
        )
        user.adult_verified = True
        user.version += 1
        user.save(update_fields=["adult_verified", "version"])
        record_audit(user, "accounts.age_confirmed", user, after={"adult_verified": True})
        _activate_if_ready(user)
    return "ADULT_CONFIRMED"


#: A `note` on an age review may not contain a date. DATA-MODEL §2 calls this a
#: code review item; it is a refusal as well, because the reviewer's free-text
#: box is the last route by which a DOB could reach storage and a review is the
#: one place someone would be tempted to write one down.
#:
#: # ponytail: three date shapes, not a date parser. Ceiling: "born in the
#: # winter of oh-four" passes. Upgrade path: none — the control that matters is
#: # that no column can hold a date (ADR-003 §2.3, unconditional) and this is
#: # the detection layer above it (`CLAUDE.md` rule 18). A reviewer determined
#: # to record a date in prose is the residual, and it is named in the slice
#: # note rather than claimed closed.
_DATE_SHAPES = (
    r"\b\d{4}-\d{1,2}-\d{1,2}\b",     # 2004-08-21
    r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b",  # 21/08/2004, 21.8.04
    r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",  # 21 Aug
)


def review_age(staff, user, outcome: str, note: str) -> None:
    """Raises NotPermitted. `note` must not contain a date of birth.

    **The reviewer reviews the account, not a date** (DATA-MODEL §2, amendment
    A-5). With no identity document collected a reviewer cannot verify a
    declared date against anything, so storing the date would buy the review no
    information and cost a week of DOB retention. What the reviewer sees is the
    adult-status outcome, the verifying email domain, the campus match and the
    account's behaviour; what is recorded is the reviewer, the outcome and the
    timestamp.

    `REVOKED_MINOR_DISCOVERED` is the EC-12 path. It writes the event and
    **does not** itself suspend, erase or raise the `safety_incidents` row —
    `safety_incidents` is an S6 table, so the POCSO limb cannot be written yet.
    The caller is left with a suspended account and an explicit escalation in
    the log rather than a silent half-procedure; see the slice note.
    """
    import re

    if staff is None or not getattr(staff, "is_staff_member", False):
        raise NotPermitted("Only staff can review an age decision.")
    if outcome not in ("ADULT_CONFIRMED", "REVOKED_MINOR_DISCOVERED"):
        raise ValidationFailed(
            f"{outcome!r} is not a reviewable outcome. A staff review confirms an "
            "adult or revokes on discovering a minor; REJECTED_UNDER_18 is written "
            "by the server at declaration time and is not a review outcome."
        )
    if not (note or "").strip():
        raise ValidationFailed("A review needs a reason. An unexplained decision is not a review.")
    for shape in _DATE_SHAPES:
        if re.search(shape, note, re.IGNORECASE):
            raise ValidationFailed(
                "An age-review note may not contain a date of birth (DATA-MODEL §2: "
                "no DOB is persisted anywhere, in any state). Record what you "
                "reviewed about the account, not a date."
            )

    with transaction.atomic():
        AgeVerificationEvent.objects.create(
            user_pseudonym=user.person_pseudonym,
            user=user,
            outcome=outcome,
            method="STAFF_REVIEW",
            reviewer=staff,
            occurred_at=timezone.now(),
            note=note.strip(),
        )
        if outcome == "REVOKED_MINOR_DISCOVERED":
            user.adult_verified = False
            user.status = "SUSPENDED"
            user.version += 1
            user.save(update_fields=["adult_verified", "status", "version"])
            log.warning(
                "accounts.minor_discovered",
                extra={
                    "pseudonym": str(user.person_pseudonym),
                    "next_step": "POCSO duty (IT Rules r.3(1)(c)(iii)): raise a "
                                 "safety_incidents row with minor_involved=true. "
                                 "That table is S6; until then this is an operator "
                                 "action, not an automated one.",
                },
            )
        else:
            user.adult_verified = True
            user.version += 1
            user.save(update_fields=["adult_verified", "version"])
        record_audit(staff, "accounts.age_reviewed", user, after={"outcome": outcome})
        if outcome == "ADULT_CONFIRMED":
            _activate_if_ready(user)


def age_review_queue(staff, limit=50):
    """The accounts a staff reviewer would look at. Raises NotPermitted.

    **Not a table and not a new column** — the queue is a query over
    `age_verification_events`, which is what DATA-MODEL §2 leaves after deleting
    `age_check_pending`. JOURNEYS J1 says staff see *"an
    `age_verification_events` row they never need to open unless a revocation
    happens"*, so the useful queue is the one thing that is not routine: an
    account confirmed by self-declaration that no human has looked at.
    """
    if staff is None or not getattr(staff, "is_staff_member", False):
        raise NotPermitted("Only staff can read the age-review queue.")
    reviewed = AgeVerificationEvent.objects.filter(method="STAFF_REVIEW").values_list(
        "user_pseudonym", flat=True
    )
    return list(
        AgeVerificationEvent.objects.filter(
            method="SELF_DECLARED_DOB_SERVER_CHECKED", outcome="ADULT_CONFIRMED"
        )
        .exclude(user_pseudonym__in=list(reviewed))
        .order_by("occurred_at")[:limit]
    )


# --- notices and consent ---------------------------------------------------


def current_notice(kind, locale="en"):
    """The latest published version of a notice, in a locale.

    Falls back to `en` when a locale has no version: `i18n.ta_enabled` is
    seeded **false** and stays false until a native speaker signs off
    (THREAT-MODEL §6.1), so a Tamil notice may legitimately not exist yet. A
    fallback is the right behaviour; a missing legal page is not.
    """
    row = (
        NoticeVersion.objects.filter(kind=kind, locale=locale).order_by("-published_at", "-id").first()
        or NoticeVersion.objects.filter(kind=kind, locale="en").order_by("-published_at", "-id").first()
    )
    return row


def consent_state(user):
    """`{purpose_key: bool}` for all six purposes. API-CONTRACT §5.1.

    **The current state is the latest row per `(user_pseudonym, purpose_key)`**
    — DATA-MODEL §2 — because the table is append-only and a withdrawal is a new
    row rather than an edit. Computed here once so no caller re-derives it; a
    second implementation of "which row wins" is how a withdrawal silently stops
    counting.
    """
    latest = {}
    rows = Consent.objects.filter(user_pseudonym=user.person_pseudonym).order_by("created_at", "id")
    for row in rows:
        latest[row.purpose_key] = row.granted_at is not None
    return {purpose: latest.get(purpose, False) for purpose in CONSENT_PURPOSES}


def missing_consents(user):
    """The required purposes this user has not granted (API-CONTRACT §2.5 step 5)."""
    state = consent_state(user)
    return [purpose for purpose in REQUIRED_CONSENT_PURPOSES if not state.get(purpose)]


def grant_consent(user, purpose_key, notice_version, mechanism, ip, user_agent) -> None:
    """Appends a `consents` row. Never updates one (DATA-MODEL §2)."""
    _append_consent(user, purpose_key, notice_version, mechanism, ip, user_agent, granted=True)


def withdraw_consent(user, purpose_key, mechanism, ip, user_agent) -> None:
    """Appends a new row with `withdrawn_at` set. **A toggle, not an email.**

    DPDP r.3(c)(i) requires withdrawal to be as easy as granting, which is why
    this takes the same arguments and writes the same shape of row. The notice
    version is carried over from the row being withdrawn, so the ledger records
    *which* notice the student is stepping out of.

    Withdrawing a **required** purpose is permitted and is not an error:
    JOURNEYS J1 step 5 says the student stays signed in and is told which action
    it blocks. `require_actor` is what then refuses the write, with the missing
    `purpose_key` in the body.
    """
    state = consent_state(user)
    if purpose_key not in state:
        raise ValidationFailed(f"{purpose_key!r} is not one of the six consent purposes.")
    previous = (
        Consent.objects.filter(user_pseudonym=user.person_pseudonym, purpose_key=purpose_key)
        .order_by("-created_at", "-id")
        .first()
    )
    if previous is None or not state[purpose_key]:
        # Idempotent: withdrawing something never granted is a no-op, not a
        # second row. A ledger whose rows can be appended by a client loop is a
        # ledger nobody can read.
        return
    _append_consent(
        user, purpose_key, previous.notice_version, mechanism, ip, user_agent, granted=False
    )


def _append_consent(user, purpose_key, notice_version, mechanism, ip, user_agent, *, granted):
    if purpose_key not in CONSENT_PURPOSES:
        raise ValidationFailed(
            f"{purpose_key!r} is not one of the six consent purposes in DATA-MODEL §2. "
            "A new purpose is a new lawful basis and needs privacy-compliance sign-off."
        )
    if notice_version is None:
        raise ValidationFailed(
            "A consent row must name the notice version the student agreed to "
            "(DATA-MODEL §2; PRD AC-A3.3). No PRIVACY notice is published — run "
            "`manage.py seed_demo` or publish one."
        )
    now = timezone.now()
    with transaction.atomic():
        row = Consent.objects.create(
            user=user,
            user_pseudonym=user.person_pseudonym,
            purpose_key=purpose_key,
            notice_version=notice_version,
            granted_at=now if granted else None,
            withdrawn_at=None if granted else now,
            mechanism=mechanism,
            ip=ip or None,
            user_agent=(user_agent or None),
            created_at=now,
        )
        record_audit(
            user,
            "accounts.consent_granted" if granted else "accounts.consent_withdrawn",
            row,
            after={"purpose_key": purpose_key, "notice_version_id": notice_version.id},
        )
        if granted:
            _activate_if_ready(user)


def _activate_if_ready(user):
    """`PENDING_VERIFICATION → ACTIVE` once J1's three gates are passed.

    Not a state machine — `users.status` has no transition table in DATA-MODEL
    §6 — so this is one guarded assignment in one place rather than a check
    repeated at every call site.
    """
    if user.status != "PENDING_VERIFICATION":
        return
    if user.adult_verified and user.campus_verified and not missing_consents(user):
        user.status = "ACTIVE"
        user.version += 1
        user.save(update_fields=["status", "version"])
        record_audit(user, "accounts.activated", user, after={"status": "ACTIVE"})


def accept_seller_terms(user, notice_version, ip) -> None:
    """r.6(4)(a)'s prior written contract. **S2, not S1.**

    `seller_terms_acceptances` is an S2 table (DATA-MODEL §2) because the
    listing-create service is what refuses without it. The frozen signature is
    here from S0 and stays; the body lands with `apps/listings`.
    """
    raise NotImplementedError(
        "apps.accounts.services.accept_seller_terms() lands in S2 with the "
        "`seller_terms_acceptances` table (DATA-MODEL §2) and `create_listing`, "
        "which is the caller that refuses without it. The frozen signature is "
        "API-CONTRACT.md §3. Do not work around this."
    )


# --- profile, export, nomination ------------------------------------------


def update_profile(user, *, display_name=None, locale=None):
    """API-CONTRACT §5.1 `PATCH /api/v1/account`. §7 row 1.

    Assigns both fields by name rather than looping with `setattr`. That is not
    style: ADR-003 §2.3 W1c's source grep sees **bindings**, and a name built
    at runtime is the one shape it cannot see — which is W5's declared ceiling.
    `tests/unit/test_forbidden_source.py::test_apps_contains_no_dynamic_attribute_construction`
    asserts `apps/**` contains none, and it caught this function's first draft.
    """
    fields = []
    before = {"display_name": user.display_name, "locale": user.locale}

    if display_name is not None:
        cleaned = " ".join(str(display_name).split())
        if not _has_visible_character(cleaned):
            raise ValidationFailed(
                "Enter a name other students will recognise at a handover.",
                field_errors={"display_name": ["Required."]},
            )
        if len(cleaned) > 60:
            raise ValidationFailed(
                "That name is too long.", field_errors={"display_name": ["60 characters at most."]}
            )
        user.display_name = cleaned
        fields.append("display_name")

    if locale is not None:
        if locale not in LOCALES:
            raise ValidationFailed(f"{locale!r} is not an available language.")
        user.locale = locale
        fields.append("locale")

    if not fields:
        return user

    with transaction.atomic():
        user.version += 1
        user.save(update_fields=[*fields, "version"])
        record_audit(
            user, "accounts.profile_updated", user,
            before=before,
            after={"display_name": user.display_name, "locale": user.locale},
        )
    return user


def _has_visible_character(text):
    """Is any character printable and not a Unicode format character?

    `CLAUDE.md` rule 15, and the same invariant `open_discovery._present` uses —
    one definition would be better still, and it is flagged in the slice note.
    A list of whitespace characters cannot catch zero-width space or a byte
    order mark, because those are *format* characters: they survive `.strip()`
    and render as nothing, so a display name made of them is an empty name that
    passes a length check.
    """
    return any(
        ch.isprintable() and unicodedata.category(ch) != "Cf" and not ch.isspace()
        for ch in text or ""
    )


def export_account(user):
    """API-CONTRACT §5.1 `GET /account/export` — the s11 access right.

    *"Generated live, with no staff step"* (PRD AC-X2.1), which is why it is a
    read-only service function and not a job: a human in the loop is how a
    seven-day clock gets missed.

    It reports **processing activities as well as data**, because s11 asks for
    both and because the activities are the half a student cannot reconstruct
    from the screens. It also states what is retained after deletion and why,
    so the §7 row 11 disclosure is in two places rather than only in the
    deletion flow.
    """
    verifications = CampusVerification.objects.filter(user=user).order_by("verified_at")
    age_events = AgeVerificationEvent.objects.filter(
        user_pseudonym=user.person_pseudonym
    ).order_by("occurred_at")
    consents = Consent.objects.filter(user_pseudonym=user.person_pseudonym).order_by("created_at")
    requests = DataSubjectRequest.objects.filter(
        user_pseudonym=user.person_pseudonym
    ).order_by("received_at")

    with transaction.atomic():
        row = DataSubjectRequest.objects.create(
            user=user,
            user_pseudonym=user.person_pseudonym,
            kind="ACCESS",
            due_at=timezone.now() + DSR_DEADLINE,
            completed_at=timezone.now(),
            outcome="SELF_SERVICE_EXPORT",
        )
        record_audit(user, "accounts.exported", row)

    return {
        "pseudonym": str(user.person_pseudonym),
        "account": {
            "email": user.email,
            "display_name": user.display_name,
            "campus": user.campus.name,
            "city": user.city.name,
            "locale": user.locale,
            "status": user.status,
            "created_at": user.created_at,
            "last_seen_at": user.last_seen_at,
        },
        "age_check": {
            "adult_verified": user.adult_verified,
            "date_of_birth_held": False,
            "note": (
                "We asked your date of birth once to check you are 18 or over. "
                "We did not keep it, and there is no column anywhere in the "
                "database that could hold it."
            ),
            "events": [
                {"outcome": e.outcome, "method": e.method, "occurred_at": e.occurred_at}
                for e in age_events
            ],
        },
        "campus_verification": [
            {"method": v.method, "domain": v.email_domain, "verified_at": v.verified_at}
            for v in verifications
        ],
        "consents": [
            {
                "purpose_key": c.purpose_key,
                "granted_at": c.granted_at,
                "withdrawn_at": c.withdrawn_at,
                "mechanism": c.mechanism,
                "notice_version": c.notice_version.version,
            }
            for c in consents
        ],
        "consent_state_now": consent_state(user),
        "rights_requests": [
            {"kind": r.kind, "received_at": r.received_at, "due_at": r.due_at,
             "completed_at": r.completed_at, "outcome": r.outcome}
            for r in requests
        ],
        "processing_activities": [
            "Signing you in by emailing a single-use link.",
            "Confirming your college email domain matches your campus.",
            "Recording that you are 18 or over, without keeping the date.",
            "Recording what you agreed to, and when, and what you withdrew.",
            "Keeping security and access logs for one year, which the law requires.",
        ],
        "retained_if_you_delete": [
            "The record of transfers you completed, without your name, for one year.",
            "Chat content is not deleted and is removed one year after the last message.",
            "The record that you consented, and that your deletion was lawful.",
        ],
    }


def record_nomination(user, nominee):
    """API-CONTRACT §5.1 `POST /account/nominee` — the s14 nomination.

    *"In the Act, built once, nobody else builds it."* Deliberately **not
    promoted as a feature** (PRD AC-X2.2): a student who came to find a textbook
    does not need a nominee flow in their way, so it is one field in privacy
    settings and a `data_subject_requests` row of kind `NOMINATION`.

    The nominee is stored in `data_subject_requests.nominee` jsonb, which is the
    only place DATA-MODEL §2 puts it. **Name and email only** — a nominee's
    phone or address would be personal data about a third party with no §7 row,
    so the shape is closed rather than free.
    """
    if not isinstance(nominee, dict):
        raise ValidationFailed("Enter the name and email of the person you nominate.")
    allowed = {"name", "email"}
    extra = set(nominee) - allowed
    if extra:
        raise ValidationFailed(
            f"A nomination holds a name and an email and nothing else; got {sorted(extra)}. "
            "A third party's other details would be personal data with no "
            "COMPLIANCE.md §7 row."
        )
    name = " ".join(str(nominee.get("name", "")).split())
    if not _has_visible_character(name):
        raise ValidationFailed(
            "Enter the name of the person you nominate.",
            field_errors={"name": ["Required."]},
        )
    address = normalise_email(nominee.get("email"))

    with transaction.atomic():
        row = DataSubjectRequest.objects.create(
            user=user,
            user_pseudonym=user.person_pseudonym,
            kind="NOMINATION",
            due_at=timezone.now() + DSR_DEADLINE,
            completed_at=timezone.now(),
            outcome="RECORDED",
            nominee={"name": name, "email": address},
        )
        record_audit(user, "accounts.nominee_recorded", row)
    return row


# --- staff data access -----------------------------------------------------


def log_personal_data_access(staff, subject_pseudonym, fields, purpose) -> None:
    """DPDP r.6(1)(c). Every staff view of a student's data writes a row.

    **And the screen says so to the staff member**, which is most of the control
    (THREAT-MODEL §5.8) — a log nobody knows about deters nobody. The UI half is
    frontend's and the admin's; this is the row.

    It writes an `audit_log` row too, because *"access to the logs is itself
    logged"* (§7 row 16) and the access log is exactly such a log.
    """
    from apps.core.request_context import current_request

    if staff is None or not getattr(staff, "is_staff_member", False):
        raise NotPermitted("Only staff can read another person's personal data.")
    if not fields:
        raise ValidationFailed(
            "A personal-data access row must name the fields read. A row that "
            "names none provides no visibility, which is the whole point of "
            "DPDP r.6(1)(c)."
        )
    if not (purpose or "").strip():
        raise ValidationFailed("A personal-data access row must state a purpose.")

    with transaction.atomic():
        row = PersonalDataAccessLog.objects.create(
            staff=staff,
            subject_pseudonym=subject_pseudonym,
            fields_accessed=list(fields),
            purpose=purpose.strip(),
            request_id=current_request().get("request_id"),
        )
        record_audit(
            staff, "accounts.personal_data_accessed", row,
            after={"subject": str(subject_pseudonym), "fields": sorted(fields)},
        )


# --- erasure ---------------------------------------------------------------


def _email_salt():
    """The server-side secret that salts `user_tombstones.email_hash`.

    `COMPLIANCE.md` §7 rows 3 and 24: it is **not in the database**, so a
    database-only compromise cannot re-identify by rainbow table — a sha256 of a
    predictable institutional address is enumerable from a roll list.

    **Raises when unset rather than falling back.** A default salt would make
    every deployment's hashes identical and the control worthless, and a silent
    empty salt is the shape of defect that passes every test.
    """
    salt = getattr(settings, "TOMBSTONE_EMAIL_SALT", "") or ""
    version = getattr(settings, "TOMBSTONE_EMAIL_SALT_VERSION", "") or ""
    if not salt or not version:
        raise RuntimeError(
            "BOOKHOP_TOMBSTONE_EMAIL_SALT and BOOKHOP_TOMBSTONE_EMAIL_SALT_VERSION "
            "must be set before an account can be erased (COMPLIANCE.md §7 rows 3 "
            "and 24). The salt is a server-side secret that is deliberately NOT in "
            "the database; without it `email_hash` is an enumerable hash of a "
            "predictable address. There is no default."
        )
    return salt, version


def email_hash(address):
    """Salted sha256 of a normalised address, plus the salt version that made it."""
    salt, version = _email_salt()
    digest = hashlib.sha256(f"{salt}:{normalise_email(address)}".encode("utf-8")).hexdigest()
    return digest, version


def erase_account(user, reason="USER_REQUEST") -> None:
    """DATA-MODEL §10.1, **one transaction**. Tombstone-plus-purge, never DELETE.

    `COMPLIANCE.md` §7: *"'Delete my account' never means `DELETE FROM users`.
    It means: purge rows 1–9 and 15, pseudonymise 10–13, and leave 14 and 16–18
    alone."* The eight steps, and which of them S1 can execute:

      1. insert `user_tombstones` — pseudonym, campus, city, **salted**
         `email_hash` + `salt_version`, `purge_due_at = now + 1 year`;
      2. `users`: NULL `email`, `display_name`, `password`;
         `status='TOMBSTONED'`; `tombstoned_at=now()`;
      3. delete `email_login_tokens` and the student's **sessions**.
         `push_subscriptions` and `notification_preferences` are S7 tables and
         are named in the registry below so the step is not forgotten;
      4. delete `campus_verifications`; `users.campus_verified` **stays** as a
         boolean, because the fact of eligibility outlives the evidence;
      5. `listing_photos` — S2;
      6. `listings`, `book_requests`, `transfers`, `threads`, `messages`,
         `reports`, `disputes`, `support_*`: NULL the FK, **keep the
         pseudonym**, set `purge_due_at` — S2 onwards;
      7. **untouched:** `repeat_infringer_records`, `audit_log`,
         `personal_data_access_log`, `age_verification_events`, `consents`;
      8. `data_subject_requests` row completed, `audit_log` row written.

    **Pseudonymisation is one-way.** The retained record carries only the
    pseudonym and the pseudonym→identity mapping is destroyed in step 2, which
    is why `person_pseudonym` is never rewritten here: destroying it would
    destroy the transaction record's only remaining reference and break both the
    counterparty's dispute and the §9.2 metric.

    **Steps 5 and 6 have no tables yet, and that is stated rather than silently
    skipped**: `ERASURE_STEPS` below is the registry, each entry carrying the
    slice that lands it, and `test_erasure.py` asserts every entry is either
    executed or explicitly pending. A step that exists only in a docstring is a
    step that gets forgotten in S4.
    """
    if user.status == "TOMBSTONED":
        return  # idempotent: a second delete is not a second tombstone

    address = user.email
    now = timezone.now()
    with transaction.atomic():
        digest, salt_version = (email_hash(address) if address else (None, None))
        UserTombstone.objects.update_or_create(
            person_pseudonym=user.person_pseudonym,
            defaults={
                "campus_id": user.campus_id,
                "city_id": user.city_id,
                "email_hash": digest,
                "salt_version": salt_version,
                "tombstoned_at": now,
                "purge_due_at": now + RETENTION_FLOOR,
                "reason": reason,
            },
        )

        before = {"status": user.status, "had_email": address is not None}
        user.email = None
        user.display_name = None
        user.password = None
        user.status = "TOMBSTONED"
        user.tombstoned_at = now
        user.version += 1
        user.save(
            update_fields=["email", "display_name", "password", "status", "tombstoned_at", "version"]
        )

        EmailLoginToken.objects.filter(user=user).delete()
        CampusVerification.objects.filter(user=user).delete()
        _delete_sessions_for(user)

        DataSubjectRequest.objects.create(
            user=user,
            user_pseudonym=user.person_pseudonym,
            kind="ERASURE",
            received_at=now,
            due_at=now + DSR_DEADLINE,
            completed_at=now,
            outcome="COMPLETED",
        )
        record_audit(
            user, "accounts.erased", user,
            before=before,
            after={"status": "TOMBSTONED", "reason": reason, "purge_due_at": now + RETENTION_FLOOR},
        )
    log.info("accounts.erased", extra={"pseudonym": str(user.person_pseudonym), "reason": reason})


def _delete_sessions_for(user):
    """Invalidate every session this student holds. DATA-MODEL §10.1 step 3.

    # ponytail: scan the session table and decode. Ceiling: O(unexpired
    # sessions), which at the pilot's few hundred accounts is a few hundred rows
    # on a path that runs at most 3 times a day per user (API-CONTRACT §2.4's
    # erase limit). Upgrade path: a `user_id` column on a sessions table we own,
    # which is a new table and a new migration for a property this gets today.
    # Server-side invalidation is an ASVS V7 L2 requirement, so "the cookie will
    # expire eventually" is not an option.
    """
    from django.contrib.sessions.models import Session

    from .sessions import SESSION_USER_KEY

    for row in Session.objects.filter(expire_date__gte=timezone.now()).iterator():
        try:
            if row.get_decoded().get(SESSION_USER_KEY) == user.id:
                row.delete()
        except Exception:  # pragma: no cover - a corrupt session is not this path's problem
            continue


#: DATA-MODEL §10.1's steps, as data rather than as prose.
#:
#: `(step, what, slice, executed_here)`. The registry exists because steps 5
#: and 6 name tables no slice has built, and *"a deferral recorded only in a
#: docstring is how an ownerless control becomes an unwritten one"* — the same
#: failure mode TASKS R-1 records against the default manager.
#: `tests/unit/test_erasure.py` asserts the executed entries actually run and
#: that every pending one names a slice.
ERASURE_STEPS = (
    (1, "insert user_tombstones with a salted email_hash", "S1", True),
    (2, "NULL users.email / display_name / password; status TOMBSTONED", "S1", True),
    (3, "delete email_login_tokens and sessions", "S1", True),
    (3, "delete push_subscriptions, notification_preferences", "S7", False),
    (4, "delete campus_verifications; campus_verified stays", "S1", True),
    (5, "schedule listing_photos object deletion at closed_at + 1 year", "S2", False),
    (6, "NULL the FK and keep the pseudonym on listings, book_requests", "S2", False),
    (6, "NULL the FK and keep the pseudonym on transfers", "S4", False),
    (6, "NULL the FK and keep the pseudonym on threads, messages, support_*", "S5", False),
    (6, "NULL the FK and keep the pseudonym on reports, disputes", "S6", False),
    (7, "leave audit_log, personal_data_access_log, age_verification_events, consents", "S1", True),
    (7, "leave repeat_infringer_records", "S6", False),
    (8, "data_subject_requests ERASURE row completed; audit_log row", "S1", True),
)


# --- §2.5 standing preconditions ------------------------------------------


def require_actor(user, *, purposes=()):
    """API-CONTRACT §2.5, in its stated order, so the student sees the most
    useful error rather than the first one a developer happened to check.

    Steps 6 and 7 — campus scope and the discovery gate — are **not** here:
    they take an object and a campus, and `apps.core.scoping.scoped` and
    `assert_discovery_open` are their one definition. This is steps 1 to 5,
    which are properties of the actor alone.
    """
    if user is None:
        raise NotAuthenticated("Please sign in first.")
    if user.status == "TOMBSTONED":
        raise Suspended("This account has been deleted.")
    if user.status != "ACTIVE":
        if user.status == "SUSPENDED":
            raise Suspended("This account cannot do that at the moment.")
        # PENDING_VERIFICATION: say which step is outstanding, in J1's order,
        # instead of a generic refusal the student cannot act on.
        if not user.adult_verified:
            raise NotAdultVerified("BookHop is for students aged 18 and over.")
        if not user.campus_verified:
            raise NotCampusVerified("Confirm your college email address first.")
        missing = missing_consents(user)
        if missing:
            raise ConsentRequired(
                "This needs your permission first. You can change it any time.",
                purpose_key=missing[0],
            )
    if not user.adult_verified:
        raise NotAdultVerified("BookHop is for students aged 18 and over.")
    if not user.campus_verified:
        raise NotCampusVerified("Confirm your college email address first.")
    for purpose in (*REQUIRED_CONSENT_PURPOSES, *purposes):
        if not consent_state(user).get(purpose):
            raise ConsentRequired(
                "This needs your permission first. You can change it any time.",
                purpose_key=purpose,
            )
    return user


# --- retention -------------------------------------------------------------


def purge_expired(job_run_id=None):
    """DATA-MODEL §10.2's nightly expiry. Returns `{table: rows}`.

    **Built in the same slice as the retention it expires**, which is the whole
    reason deletion is in S1: *"Retaining beyond the purpose without a legal
    basis is its own breach"* (`COMPLIANCE.md` §8.3). Every row purged writes a
    `purge_log` row, which is how we prove to G3/G4 that the job ran rather than
    claiming it.

    **Idempotent under at-least-once delivery** (API-CONTRACT §4.4): every rule
    is driven by a timestamp comparison and a second run finds nothing left.

    # ponytail: nightly table-walk delete. Ceiling: when a purge run takes
    # longer than the night. Upgrade path: monthly range partitions on the three
    # unbounded tables (ADR-002 §6 step 4), then DROP PARTITION.
    """
    now = timezone.now()
    counts = {}

    # DATA-MODEL §2: tokens are deleted 7 days after `expires_at`.
    stale_tokens = list(
        EmailLoginToken.objects.filter(expires_at__lt=now - TOKEN_PURGE_AFTER).values_list(
            "id", flat=True
        )
    )
    if stale_tokens:
        EmailLoginToken.objects.filter(id__in=stale_tokens).delete()
        _log_purge("email_login_tokens", stale_tokens, None, now, job_run_id, "PURGE")
    counts["email_login_tokens"] = len(stale_tokens)

    # DATA-MODEL §5: 24-hour retention on idempotency keys. Nothing else deletes
    # them, and a table that only grows is a retention breach by default.
    from apps.core.models import IdempotencyKey

    stale_keys = list(IdempotencyKey.objects.filter(expires_at__lt=now).values_list("id", flat=True))
    if stale_keys:
        IdempotencyKey.objects.filter(id__in=stale_keys).delete()
        _log_purge("idempotency_keys", stale_keys, None, now, job_run_id, "PURGE")
    counts["idempotency_keys"] = len(stale_keys)

    # §7 row 16: access logs rotated and erased at 1 year.
    stale_access = list(
        PersonalDataAccessLog.objects.filter(occurred_at__lt=now - RETENTION_FLOOR).values_list(
            "id", flat=True
        )
    )
    if stale_access:
        PersonalDataAccessLog.objects.filter(id__in=stale_access).delete()
        _log_purge("personal_data_access_log", stale_access, None, now, job_run_id, "PURGE")
    counts["personal_data_access_log"] = len(stale_access)

    # RED TEAM ENGINEERING-MEMO §2: `jobs` had **no retention rule at all**,
    # which made it a standing contradiction of `COMPLIANCE.md` §8.3 as quoted
    # in `PurgeLog`'s own docstring — and, because `accounts.send_magic_link`
    # carried a raw sign-in token, an unbounded store of live credentials.
    # `run_pending_jobs` now redacts a finished payload, so this is the second
    # layer (`CLAUDE.md` rule 14): even a row whose redaction somehow did not
    # run is gone within the window.
    #
    # Only finished rows. A row still waiting or still retrying is work, not
    # residue, and deleting it would silently drop a scheduled job — which for
    # `retention.purge` itself would stop the purge from ever running again.
    from apps.core.models import Job

    stale_jobs = list(
        Job.objects.filter(completed_at__lt=now - JOB_RETENTION).values_list("id", flat=True)
    ) + list(Job.objects.filter(failed_at__lt=now - JOB_RETENTION).values_list("id", flat=True))
    if stale_jobs:
        Job.objects.filter(id__in=stale_jobs).delete()
        _log_purge("jobs", stale_jobs, None, now, job_run_id, "PURGE")
    counts["jobs"] = len(stale_jobs)

    # §7 row 3 / §10.1: the tombstone's `email_hash` lives one year, then goes.
    # The tombstone row itself **stays** — the pseudonym is what the transaction
    # record refers to, so purging the row would break the thing erasure was
    # designed to preserve.
    due = list(
        UserTombstone.objects.filter(purge_due_at__lte=now, purged_at__isnull=True).values_list(
            "person_pseudonym", flat=True
        )
    )
    if due:
        UserTombstone.objects.filter(person_pseudonym__in=due).update(
            email_hash=None, salt_version=None, purged_at=now
        )
        _log_purge("user_tombstones", due, now, now, job_run_id, "PURGE")
    counts["user_tombstones"] = len(due)

    return counts


def _log_purge(table, keys, purge_due_at, purged_at, job_run_id, mode):
    PurgeLog.objects.bulk_create(
        [
            PurgeLog(
                table_name=table, object_pk=str(key), purge_due_at=purge_due_at,
                purged_at=purged_at, job_run_id=job_run_id, mode=mode,
            )
            for key in keys
        ]
    )


#: DATA-MODEL §10.2's **explicit skip-list**, as data. A table here is one the
#: purge job must never touch, with the reason, so S6 does not have to remember
#: it and so a reviewer can see that the omission is a decision.
PURGE_SKIP_LIST = {
    "repeat_infringer_records": "E-Com r.5(5) — survives account deletion, never purged (S6)",
    "audit_log": "append-only and tamper-evident (DATA-MODEL §8); 1-year floor is logrotate's, S8",
    "consents": (
        "append-only by trigger (migration accounts/0002) and §10.1 step 7 leaves it "
        "untouched. Its stated retention is 'account life + 1 year', which the trigger "
        "makes undeletable — a contract conflict raised to cto, not resolved here"
    ),
    "age_verification_events": (
        "same conflict as `consents`: append-only by trigger, retention 'account life "
        "+ 1 year'. Raised to cto"
    ),
    "notice_versions": "immutable; a notice is the evidence of what was agreed (§8.1)",
}
