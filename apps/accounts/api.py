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

from apps.core.api import endpoint, json_response
from apps.core.errors import (
    EmailDomainNotRecognised,
    NotFound,
    RateLimited,
    ServiceError,
    Suspended,
    ValidationFailed,
)
from apps.core.ratelimit import ONE_DAY, ONE_HOUR, consume_quota, is_exempt

from . import services
from .models import CONSENT_PURPOSES
from .sessions import end_session, session_user, start_session


def _actor(request):
    return session_user(request)


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
    except (EmailDomainNotRecognised, Suspended):
        # Swallowed on purpose. §5.1: the same 202 for every outcome.
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
    if user is None:
        from apps.core.errors import NotAuthenticated

        raise NotAuthenticated("Please sign in first.")
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
    if user is None:
        from apps.core.errors import NotAuthenticated

        raise NotAuthenticated("Please sign in first.")
    notice = services.current_notice("PRIVACY", user.locale)
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
    if user is None:
        from apps.core.errors import NotAuthenticated

        raise NotAuthenticated("Please sign in first.")
    if purpose_key not in CONSENT_PURPOSES:
        raise NotFound("No such consent purpose.")
    granted = body.get("granted")
    if not isinstance(granted, bool):
        raise ValidationFailed(
            "Say whether you are granting or withdrawing.",
            field_errors={"granted": ["true or false."]},
        )
    ip = request.META.get("REMOTE_ADDR")
    agent = request.headers.get("User-Agent")
    if granted:
        notice = services.current_notice("PRIVACY", user.locale)
        services.grant_consent(user, purpose_key, notice, "SETTINGS_TOGGLE", ip, agent)
    else:
        services.withdraw_consent(user, purpose_key, "SETTINGS_TOGGLE", ip, agent)
    user.refresh_from_db()
    return 200, {
        "purpose_key": purpose_key,
        "granted": services.consent_state(user)[purpose_key],
    }


# --- profile, export, nominee, erase ---------------------------------------


@endpoint(methods=["GET", "PATCH"], idempotent_write="PATCH /api/v1/account", actor=_actor)
def account(request, body, user):
    """§5.1 `GET /account` and `PATCH /account` `{display_name?, locale?}`."""
    if user is None:
        from apps.core.errors import NotAuthenticated

        raise NotAuthenticated("Please sign in first.")
    if request.method == "PATCH":
        user = services.update_profile(
            user, display_name=body.get("display_name"), locale=body.get("locale")
        )
    return 200, _account_payload(user)


@endpoint(methods=["GET"], actor=_actor)
def export(request, body, user):
    """§5.1 `GET /account/export` — the s11 access right, generated live."""
    if user is None:
        from apps.core.errors import NotAuthenticated

        raise NotAuthenticated("Please sign in first.")
    return 200, services.export_account(user)


@endpoint(methods=["POST"], idempotent_write="POST /api/v1/account/nominee", actor=_actor)
def nominee(request, body, user):
    """§5.1 `POST /account/nominee` — the s14 nomination."""
    if user is None:
        from apps.core.errors import NotAuthenticated

        raise NotAuthenticated("Please sign in first.")
    row = services.record_nomination(user, body.get("nominee") or body)
    return 201, {"recorded": True, "kind": row.kind, "nominee_name": row.nominee["name"]}


@endpoint(methods=["POST"], idempotent_write="POST /api/v1/account/erase", actor=_actor)
def erase(request, body, user):
    """§5.1 `POST /account/erase`. Runs `erase_account`.

    *"Response states plainly which records are retained for one year and why"*
    (r.8(3)) — **the user learns it here, not from a support ticket.** The
    strings come from `RETAINED_AFTER_ERASURE` so the L3 page and this response
    cannot drift; the two-step confirmation is L3's and the second step is what
    calls this.
    """
    if user is None:
        from apps.core.errors import NotAuthenticated

        raise NotAuthenticated("Please sign in first.")
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


def notice(request, kind=None):
    """§5.1 `GET /api/v1/notices/{kind}` — **public, unauthenticated.**

    Not wrapped in `endpoint`: it takes no body, needs no key and no actor, and
    a reader with no account must be able to reach it (r.4(2)).
    """
    requested = NOTICE_SLUGS.get(str(kind))
    if requested is None:
        return json_response({"error": {"code": "NOT_FOUND", "message": "No such notice."}}, 404)
    locale = "ta" if request.headers.get("Accept-Language", "").startswith("ta") else "en"
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
    "account", "export", "nominee", "erase", "notice", "RETAINED_AFTER_ERASURE",
    "NOTICE_SLUGS",
]
