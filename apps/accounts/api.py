"""L2 — `/api/v1` accounts handlers. API-CONTRACT §5.1.

*"Thin `/api/v1/*` handlers that validate input, call L1, serialise"* (§1).
**Nothing here contains a business rule**, and nothing here touches the ORM
except through `apps.accounts.services`. The error shape, the idempotency key
handling and the method check are all `apps.core.api.endpoint`'s, so a handler
is a signature, a service call and a dict.

Two things in this file are contract requirements rather than choices, and both
are the kind that read as bugs if you do not know why:

**`POST /auth/magic-link` always answers 202.** Whatever L1 raises — an
unrecognised domain, a suspended account, nothing at all — the response is the
same bytes. *"A different response for an unknown address is an
account-enumeration oracle"* (§5.1). The rate limit is the **one** exception,
because a 429 is about the caller rather than about the address, and PRD AC-A1.2
is what stops the 202 being a silent dead end: the body names the accepted
domains generically, without echoing what was submitted.

**No response here carries a contact detail belonging to anyone but the
caller.** `GET /account` returns the signed-in student their own email, which
API-CONTRACT §5.1 requires; nothing returns another person's.
"""

from datetime import date

from django.views.decorators.http import require_safe

from apps.core.api import endpoint, json_response
from apps.core.errors import (
    EmailDomainNotRecognised,
    GateClosed,
    NotAuthenticated,
    NotFound,
    RateLimited,
    ServiceError,
    Suspended,
    ValidationFailed,
)
from apps.core.i18n import allowed_locale
from apps.core.ratelimit import ONE_DAY, ONE_HOUR, consume_quota, is_exempt

from . import services
from .models import CONSENT_PURPOSES
from .sessions import end_session, session_user, start_session


def _actor(request):
    return session_user(request)


def _signed_in(user):
    """§2.5 precondition 1 only. For a **read**.

    A read needs an identity and nothing else: `GET /account` must work for a
    student who is mid-signup and has not consented yet, because that is the
    screen telling them so.
    """
    if user is None:
        raise NotAuthenticated("Please sign in first.")
    return user


def _stack_s(user):
    """**Stack S** — authenticated, not tombstoned, idempotency. Nothing else.

    The cto ruling after S1 escalated what the single stack cost: *"a right
    that a precondition can switch off is not a right"*. Export, erasure,
    consent withdrawal, correction and locale are here, and the case that
    makes it a stack rather than an exception is not suspension at all — **a
    student who never finished campus verification and wanted their data
    deleted would have been refused erasure by a verification check.**

    Implemented as `require_actor(..., checks=STACK_S)` rather than as a bare
    `_signed_in`, because `require_actor` is where the unconditional
    not-tombstoned refusal lives and a second path around it is how the two
    would drift.
    """
    return services.require_actor(_signed_in(user), checks=services.STACK_S)


def _may_write(user, *, purposes=(), checks=None):
    """§2.5's standing preconditions, in order, for a **write**.

    **REVIEW-S1 B3, and it was an authorization bypass rather than an omission.**
    `services.require_actor` implemented §2.5 correctly and was called by
    nothing — it appeared in one comment and one test docstring. Measured by
    review: a **SUSPENDED** student could PATCH their profile, export and erase,
    all 200; a student who had **withdrawn the required `account` consent** could
    PATCH, 200. API-CONTRACT §2.5 specifies the check, JOURNEYS J1 step 5
    promises it, and `withdraw_consent`'s own docstring claimed *"`require_actor`
    is what then refuses the write"* — three documents describing a call that
    did not exist.

    So it is **one function, called by every write**, rather than a check each
    handler remembers. `test_standing_preconditions` (QA's) and
    `tests/api/test_preconditions.py` (backend's) both enumerate the writes, so
    a new endpoint that forgets this is a red test rather than a silent hole —
    which is what S2's listing writes and S4's offer writes inherit.
    """
    actor = _signed_in(user)
    if checks is None:
        return services.require_actor(actor, purposes=purposes)
    return services.require_actor(actor, purposes=purposes, checks=checks)


def _account_payload(user):
    """The §5.1 `GET /account` body.

    `email` is the **caller's own** address and is what the contract asks for.
    `person_pseudonym` is included because it is the identifier a student would
    quote in a support ticket and the one that survives their deletion.
    """
    return {
        "pseudonym": str(user.person_pseudonym),
        "email": user.email,
        "display_name": user.display_name,
        "campus_name": user.campus.name,
        "city_name": user.city.name,
        "locale": user.locale,
        "status": user.status,
        "adult_verified": user.adult_verified,
        "campus_verified": user.campus_verified,
        "needs": services.outstanding_steps(user),
        "version": user.version,
    }


# --- auth ------------------------------------------------------------------


@endpoint(methods=["POST"], idempotent_write="POST /api/v1/auth/magic-link")
def magic_link(request, body, user):
    """§5.1. Body `{email}`. **Always 202 whatever happens.**

    The idempotency key is required and is a UUID, because this is an anonymous
    POST and anonymous keys share one global namespace (§4.1 as amended). An L3
    form carries a server-generated one, so the student does nothing.
    """
    try:
        services.request_magic_link(
            body.get("email"), request.META.get("REMOTE_ADDR"), request.headers.get("User-Agent")
        )
    except RateLimited:
        # Not swallowed: a 429 is about the caller, not about whether the
        # address exists, so it leaks nothing and the client needs it.
        raise
    except ValidationFailed:
        # A malformed address is the caller's own input and is safe to report —
        # it says nothing about whether any account exists.
        raise
    except (EmailDomainNotRecognised, GateClosed, Suspended):
        # Swallowed on purpose. §5.1: the same 202 for every outcome.
        #
        # `GateClosed` joins the list with A-35's Gate B guard. It is raised
        # only when this request would **create** a real account, so a 403 here
        # would say "no account exists at this address yet" — the enumeration
        # oracle §5.1 exists to close, arriving by a new door. An existing seed
        # or real account still gets its link.
        pass
    return 202, {
        "accepted": True,
        "accepted_domains": services.accepted_email_domains(),
        "message": (
            "Check your email for a sign-in link. It works once and lasts ten minutes."
        ),
    }


@endpoint(methods=["POST"], idempotent_write="POST /api/v1/auth/consume")
def consume(request, body, user):
    """§5.1. Single use, 10-minute expiry. Rotates the session.

    The L3 form of this is `GET /auth/c/{token}`, which is §4.1's **one**
    idempotency-key exemption — a single-use token is idempotent by
    construction. The L2 POST carries a key like any other POST, which is what
    the contract says and is why this handler does.
    """
    signed_in = services.consume_magic_link(
        body.get("token"), request.META.get("REMOTE_ADDR"), request.headers.get("User-Agent")
    )
    start_session(request, signed_in)
    return 200, {"needs": services.outstanding_steps(signed_in),
                 "pseudonym": str(signed_in.person_pseudonym)}


@endpoint(methods=["POST"], idempotent_write="POST /api/v1/auth/logout", actor=_actor)
def logout(request, body, user):
    """§5.1, and **Stack S** per §2.5's table.

    Signing out is not a marketplace action, and refusing it would leave a
    suspended student holding a live session they cannot end — the opposite of
    every reason suspension exists.
    """
    _stack_s(user)
    end_session(request)
    return 200, {"signed_out": True}


# --- age -------------------------------------------------------------------


@endpoint(methods=["POST"], idempotent_write="POST /api/v1/account/age-declaration", actor=_actor)
def age_declaration(request, body, user):
    """§5.1. Body `{date_of_birth}`.

    **Under 18 ⇒ 403 `NOT_ADULT_VERIFIED` and the account is deleted
    immediately**; `age_verification_events` records the rejection; **the DOB is
    never persisted.**

    The declared date is parsed into a local `date`, passed as an argument, and
    is gone when this function returns. It is not logged, not audited and not
    echoed in the response — and the request body it arrived in is not stored
    either, because the idempotency row keeps a **hash** of the body and never
    the body (`idempotency_keys.request_hash`).
    """
    # **Stack M minus the two preconditions that would deadlock it.** This
    # endpoint *is* precondition 3, so it cannot require `adult`; and §5.1 puts
    # consent after age, so consent cannot be owed first. `status` and `campus`
    # both stay — a student declares their age after their campus email is
    # confirmed, and a suspended account has no business becoming verified.
    _may_write(user, checks=("status", "campus"))
    raw = body.get("date_of_birth")
    try:
        declared = date.fromisoformat(str(raw))
    except (TypeError, ValueError):
        raise ValidationFailed(
            "Enter your date of birth.",
            field_errors={"date_of_birth": ["Use the date picker, or type 2004-08-21."]},
        ) from None
    outcome = services.submit_age_declaration(user, declared, request.META.get("REMOTE_ADDR"))
    user.refresh_from_db()
    return 200, {"outcome": outcome, "needs": services.outstanding_steps(user)}


# --- consent ---------------------------------------------------------------


@endpoint(methods=["GET"], actor=_actor)
def consents(request, body, user):
    """§5.1. Current state per purpose + the notice version.

    The notice version is in the response because PRD AC-A3.3 requires the
    screen to name *"the exact `notice_versions` version the student is agreeing
    to"*, and a client cannot name what it was not told.
    """
    _signed_in(user)
    # The same gate: `users.locale` is a stored preference and API-CONTRACT
    # §2.1 lets it win over the header, which means it is a second way to ask
    # for a gated locale. A student whose `locale` is `ta` with the flag off
    # gets English here, not an unreviewed notice.
    notice = services.current_notice("PRIVACY", allowed_locale(user.locale))
    return 200, {
        "purposes": [
            {"purpose_key": key, "granted": granted}
            for key, granted in services.consent_state(user).items()
        ],
        "required": list(services.REQUIRED_CONSENT_PURPOSES),
        "notice_version": notice.version if notice else None,
        "notice_kind": "PRIVACY",
    }


@endpoint(methods=["PUT"], idempotent_write="PUT /api/v1/account/consents", actor=_actor)
def set_consent(request, body, user, purpose_key=None):
    """§5.1 `PUT /account/consents/{purpose_key}`. Body `{granted}`.

    **A toggle, not an email** (DPDP r.3(c)(i)). Appends a row, never updates
    one — the trigger in migration accounts/0002 makes that a property of the
    database, so this handler could not update one if it tried.
    """
    # **Both stacks, chosen by direction — and the direction is the whole
    # distinction the ruling draws.**
    #
    #   * **Withdrawing is Stack S.** The ruling names consent withdrawal, and
    #     the principle is *a right that a precondition can switch off is not a
    #     right*. A suspended or never-verified student must be able to
    #     withdraw.
    #   * **Granting is Stack M**, minus the consent limb this endpoint
    #     establishes. Granting is not a right being exercised, it is
    #     processing being **enabled**, and a suspended account enabling new
    #     purposes is an action rather than a remedy.
    #
    # DPDP r.3(c)(i)'s *"as easy as granting"* is about **mechanism parity** —
    # same route, same shape, same number of taps — and that is preserved
    # exactly. It does not require the two directions to share an
    # authorization, and reading it that way would make the easier direction
    # the one that unlocks things.
    #
    # The consent limb is dropped from the grant stack because this endpoint
    # *is* precondition 5: a student mid-signup has granted nothing yet, and
    # requiring it here would deadlock J1 step 5.
    _signed_in(user)
    if purpose_key not in CONSENT_PURPOSES:
        raise NotFound("No such consent purpose.")
    granted = body.get("granted")
    if not isinstance(granted, bool):
        raise ValidationFailed(
            "Say whether you are granting or withdrawing.",
            field_errors={"granted": ["true or false."]},
        )
    # The stack, now that the direction is known. Declared as data in
    # CONSENT_DIRECTION_STACKS so a reader sees both directions at once rather
    # than inferring one from the absence of the other.
    services.require_actor(user, checks=CONSENT_DIRECTION_STACKS[granted])

    ip = request.META.get("REMOTE_ADDR")
    agent = request.headers.get("User-Agent")
    if granted:
        notice = services.current_notice("PRIVACY", allowed_locale(user.locale))
        services.grant_consent(user, purpose_key, notice, "SETTINGS_TOGGLE", ip, agent)
    else:
        services.withdraw_consent(user, purpose_key, "SETTINGS_TOGGLE", ip, agent)
    user.refresh_from_db()
    return 200, {
        "purpose_key": purpose_key,
        "granted": services.consent_state(user)[purpose_key],
    }


# --- profile, export, nominee, erase ---------------------------------------

#: Which stack each direction of the consent toggle sits in. Granting is Stack
#: M **minus the consent limb this endpoint establishes**; withdrawing is
#: Stack S. Data rather than an `if`, because an authorization decision behind
#: a boolean is the shape this slice has been bitten by twice.
CONSENT_DIRECTION_STACKS = {
    True: ("status", "adult", "campus"),
    False: (),
}

#: Which stack each `PATCH /account` field sits in (cto's two-stack ruling).
#: Data rather than a branch, so a new field has to declare its stack and
#: cannot inherit whichever one the `if` happened to take.
PROFILE_FIELD_STACKS = {
    "display_name": "M",
    "locale": "S",
}


@endpoint(methods=["GET", "PATCH"], idempotent_write="PATCH /api/v1/account", actor=_actor)
def account(request, body, user):
    """§5.1 `GET /account` and `PATCH /account` `{display_name?, locale?}`.

    `GET` is **Stack S**: it is the screen that tells a student which step is
    outstanding, so refusing it for an unmet precondition would hide the only
    page that explains the refusal.

    **`PATCH` is the one endpoint that spans both stacks**, per the ruling:

      * **`display_name` is Stack M.** Correction is a statutory right, but it
        is not a right to a public-facing handle while suspended — changing
        the name counterparties recognise is an evasion vector after a safety
        report. The right itself is served by a staff-reviewed correction
        endpoint, which is Stack S.
      * **`locale` is Stack S.** Which language the product speaks to you in
        is not a marketplace action and cannot be a lever.

    So the stack is chosen **by the fields present in the body**, and the
    stricter one wins when both are. That is a branch, which is the thing this
    slice has been bitten by twice — so it is written as a derivation over a
    declared field→stack map rather than as an `if`, and
    `tests/api/test_preconditions.py` enumerates both fields and the
    both-at-once case.
    """
    _stack_s(user)
    if request.method == "PATCH":
        fields = [name for name in PROFILE_FIELD_STACKS if name in body]
        if any(PROFILE_FIELD_STACKS[name] == "M" for name in fields):
            _may_write(user)
        user = services.update_profile(
            user, display_name=body.get("display_name"), locale=body.get("locale")
        )
    return 200, _account_payload(user)


@endpoint(methods=["GET"], actor=_actor)
def export(request, body, user):
    """§5.1 `GET /account/export` — the s11 access right, generated live."""
    # **Stack S** — the s11 access right. This is the escalation S1 raised and
    # the ruling answered: it previously refused a suspended student, and would
    # have refused an unverified one.
    _stack_s(user)
    return 200, services.export_account(user)


@endpoint(methods=["POST"], idempotent_write="POST /api/v1/account/nominee", actor=_actor)
def nominee(request, body, user):
    """§5.1 `POST /account/nominee` — the s14 nomination."""
    # **Stack S. `API-CONTRACT.md` §2.5 line 176 lists `POST /account/nominee`
    # (s14) in the Stack S row**, between consent withdrawal and correction.
    #
    # Recorded because the mistake is the instructive part, and because an
    # earlier version of this comment got the *correction* wrong too. I placed
    # it in S by analogy with s11/s12 and flagged that as an inference; when
    # QA's matrix had no derived reason for it I moved it to M. Both moves were
    # reasoning about a question the contract had already answered: **I had
    # read the ruling's prose summary, which names five examples, rather than
    # the table, which is the normative list.** The table did not change.
    # Nothing here needed an analogy.
    #
    # The lesson is not about nominations. **My own tests enumerate the code's
    # stacks, so they agree with the code by construction** — which is why they
    # were green through both wrong placements and QA, deriving membership from
    # the table, found it in one pass. A test written from the implementation
    # cannot discover that the implementation read the wrong document.
    _stack_s(user)
    row = services.record_nomination(user, body.get("nominee") or body)
    return 201, {"recorded": True, "kind": row.kind, "nominee_name": row.nominee["name"]}


@endpoint(
    methods=["POST"], idempotent_write="POST /api/v1/account/correction", actor=_actor
)
def correction(request, body, user):
    """§5.1 / §2.5 `POST /account/correction` — s12(1)–(2). **Stack S.**

    **QA-S1 F24's gap, closed.** §2.5 named this route twice — once in the
    Stack S table and once as *the justification for putting `display_name` in
    Stack M* — and nothing implemented it, so a suspended student could
    neither rename themselves (correctly refused) nor exercise the correction
    right (absent). Until this was green, §2.5's `display_name` reasoning
    could not be quoted as satisfied in any packet, ADR or report.

    Stack S in full: a suspended student, a student who never finished campus
    verification and a student who withdrew every optional consent can all
    reach it. *A right that a precondition can switch off is not a right.*

    The body is `{stated_problem}` — the student's own words, free text. It
    lands in `data_subject_requests.stated_problem` and **never in
    `nominee`**, which holds a third party's data (DATA-MODEL A-29).
    """
    _stack_s(user)
    row = services.request_correction(user, stated_problem=body.get("stated_problem"))
    return 201, {
        "recorded": True,
        "kind": row.kind,
        "due_at": row.due_at,
        "message": (
            "We have your request. Someone will look at it and reply within seven days."
        ),
    }


@endpoint(methods=["POST"], idempotent_write="POST /api/v1/account/erase", actor=_actor)
def erase(request, body, user):
    """§5.1 `POST /account/erase`. Runs `erase_account`.

    *"Response states plainly which records are retained for one year and why"*
    (r.8(3)) — **the user learns it here, not from a support ticket.** The
    strings come from `RETAINED_AFTER_ERASURE` so the L3 page and this response
    cannot drift; the two-step confirmation is L3's and the second step is what
    calls this.
    """
    # **Stack S** — the s12 erasure right, and the clearest case in the
    # ruling: a student who never finished campus verification and wants their
    # data deleted must not be refused by a verification check.
    _stack_s(user)
    if not is_exempt(user):
        consume_quota("account.erase", user.id, limit=3, window=ONE_DAY)
    services.erase_account(user)
    end_session(request)
    return 200, {"erased": True, "retained": RETAINED_AFTER_ERASURE}


#: PRD AC-X1.2 / `COMPLIANCE.md` §7 row 11. Plain language, no hedging, and the
#: chat sentence is the one the student *must* learn before the point of no
#: return rather than from a support ticket afterwards.
RETAINED_AFTER_ERASURE = [
    "The record of transfers you already completed is kept without your name for "
    "one year, because the law requires us to keep it.",
    "Chat content is not deleted. It is removed one year after the last message in "
    "the conversation.",
    "The record that you agreed to our notices, and that this deletion happened, is "
    "kept for one year. That is the record showing the deletion itself was lawful.",
]


# --- notices (public, unauthenticated) -------------------------------------

#: §5.1's slugs, mapped to `notice_versions.kind`. `handover-guidance`, not
#: `handover-safety` (amendment A-7): the identifier is where a label comes
#: from, so the enum and the slug were renamed together.
NOTICE_SLUGS = {
    "privacy": "PRIVACY",
    "terms": "TERMS",
    "seller-terms": "SELLER_TERMS",
    "community-rules": "COMMUNITY_RULES",
    "handover-guidance": "HANDOVER_GUIDANCE",
    # DATA-MODEL A-25. API-CONTRACT §5.1 already published both slugs while the
    # enum had no value for either, so two legally required pages had nowhere to
    # be stored: `/legal/ranking` is r.5(3)(f)/r.4(11)(c)'s ranking disclosure,
    # and the grievance page is r.4(2)'s.
    "ranking": "RANKING",
    "grievance": "GRIEVANCE_PROCEDURE",
}


@require_safe
def notice(request, kind=None):
    """§5.1 `GET /api/v1/notices/{kind}` — **public, unauthenticated.**

    Not wrapped in `endpoint`: it takes no body, needs no key and no actor, and
    a reader with no account must be able to reach it (r.4(2)).

    `require_safe` **is** `require_http_methods(["GET", "HEAD"])`, so the pair
    cannot be split by someone editing one of the two names — the same
    guarantee `endpoint` derives for the wrapped handlers, and the same one
    frontend used for this omission in its tree. Without it this route answered
    every method including POST, which for a public unauthenticated page is a
    write surface that does not need to exist.
    """
    requested = NOTICE_SLUGS.get(str(kind))
    if requested is None:
        return json_response({"error": {"code": "NOT_FOUND", "message": "No such notice."}}, 404)
    # **REVIEW-S1 B4 — this line was the bypass.** It re-derived the locale
    # from the raw `Accept-Language` header, so it ignored the decision
    # `LocaleGateMiddleware` had already made one layer above and served an
    # unreviewed Tamil legal notice with the flag off. The gate now has one
    # definition and this is a reader of it (`CLAUDE.md` rule 10).
    locale = allowed_locale(request.headers.get("Accept-Language"))
    try:
        row = services.current_notice(requested, locale)
    except ServiceError as exc:  # pragma: no cover - current_notice does not raise today
        from apps.core.api import error_response

        return error_response(exc)
    if row is None:
        return json_response(
            {"error": {"code": "NOT_FOUND", "message": "That notice has not been published yet."}},
            404,
        )
    return json_response(
        {
            "kind": row.kind,
            "version": row.version,
            "locale": row.locale,
            "body_md": row.body_md,
            "sha256": row.sha256,
            "published_at": row.published_at,
        }
    )


# --- staff -----------------------------------------------------------------
#
# API-CONTRACT §5.7: *"Moderation, age review, takedown clocks … are all
# **Django admin screens** … They are L1 calls behind admin actions, not L2
# endpoints."* So the age-review queue has **no L2 endpoint here on purpose**,
# and `services.age_review_queue` / `services.review_age` are the L1 calls the
# admin action will make. The admin itself lands with S2's moderation queue —
# see the slice note, which states the deferral rather than leaving the
# reviewer path undiscoverable.

__all__ = [
    "magic_link", "consume", "logout", "age_declaration", "consents", "set_consent",
    "account", "export", "nominee", "correction", "erase", "notice",
    "RETAINED_AFTER_ERASURE",
    "NOTICE_SLUGS",
]
