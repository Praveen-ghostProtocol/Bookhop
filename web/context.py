"""L3 request helpers — the signed-in actor, the locale gate, and nothing else.

`web/**` is L3 (`API-CONTRACT.md` §1): it calls L1 service functions directly
and **never touches the ORM**. Everything in this file exists because a view
needs something that is not a one-line service call.

NOTHING HERE RE-IMPLEMENTS A RULE THAT L1 OWNS. Earlier drafts of this module
carried a local `outstanding_steps`, a local consent-purpose list and a local
session helper, written while the service layer was still stubs. All three are
now imported instead, because `CLAUDE.md` rule 10 is exactly what they were:
one legal rule, hand-copied, free to diverge. The local consent list had in
fact already diverged — it marked four purposes required where
`REQUIRED_CONSENT_PURPOSES` is `("account",)` alone, which would have told a
student that declining `chat` blocked messaging when it does not.
"""

from django.conf import settings

from apps.accounts import sessions
from apps.accounts.services import (
    CONSENT_PURPOSES,
    REQUIRED_CONSENT_PURPOSES,
    accepted_email_domains,
    consent_state,
    current_notice,
    outstanding_steps,
)
from apps.core.services import flag

__all__ = [
    "CONSENT_PURPOSES",
    "REQUIRED_CONSENT_PURPOSES",
    "accepted_email_domains",
    "consent_state",
    "current_notice",
    "current_notice_label",
    "current_user",
    "locale_of",
    "next_step_url",
    "offered_locales",
    "read_notice",
    "sign_in",
    "sign_out",
    "signed_in_with_college_email",
]


# --- The signed-in actor ---------------------------------------------------
# `apps/accounts/sessions.py` is the single definition of what being signed in
# means, imported by both L2 and L3 for the reason its own docstring gives. L3
# adds nothing to it; these three names exist so views read as views.

current_user = sessions.session_user
sign_in = sessions.start_session
sign_out = sessions.end_session


def next_step_url(user):
    """Where a half-set-up account belongs, or None when set-up is finished.

    The order is `outstanding_steps`', which is `JOURNEYS.md` J1's order, so a
    student never meets the same screen twice. "campus" has no screen: the
    email domain matched, so nothing is asked (J1 step 6) and the fact is
    stated on the consent screen instead.
    """
    needs = outstanding_steps(user)
    if "age" in needs:
        return "/account/age"
    if "consent" in needs:
        return "/account/privacy"
    return None


# --- Notices ---------------------------------------------------------------

def read_notice(kind, locale=None):
    """The live notice for a kind, or None if it cannot be read.

    **Reads degrade; writes do not.** A GET of `/legal/privacy` must still
    render: these links are in the footer of every page, so a hard failure here
    takes the whole product down and takes the grievance-officer route with it,
    which is the one link that must survive an outage (`SYSTEM.md` §4.1
    `error`). The page then says the notice is not published, which is true,
    rather than rendering an empty page that looks like a published notice with
    nothing in it.

    The consent POST path calls `current_notice` directly and does **not**
    degrade, so a `consents` row is never written against a missing version —
    that would be a defective legal record, invisible until a data-subject
    request asked for it.
    """
    try:
        return current_notice(kind, locale or settings.LANGUAGE_CODE)
    except Exception:  # noqa: BLE001 — see docstring; a read is not a record
        return None


def current_notice_label(kind, locale=None):
    """The live notice version as a student-readable string, or None."""
    notice = read_notice(kind, locale)
    return getattr(notice, "version", None) if notice is not None else None


# --- Campus verification method -------------------------------------------

#: `COPY-DECK.md` §3.2 condition 3, `SYSTEM.md` §4.11a and acceptance criterion
#: 7h all require `trust.campus_mail` to render **only** when
#: `campus_verifications.method` says the student signed in with a college
#: email address, and to **fail closed** on anything else.
#:
#: THE THREE DOCUMENTS NAME A VALUE THAT DOES NOT EXIST. They say
#: `'EMAIL_DOMAIN'`. `DATA-MODEL.md` §2's CHECK allows only
#: `'INSTITUTIONAL_EMAIL'` and `'STAFF_MANUAL'`; `JOURNEYS.md` J1 step 6 says
#: `INSTITUTIONAL_EMAIL`; and `apps/accounts/services.py` now **writes**
#: `method="INSTITUTIONAL_EMAIL"` on every sign-in. So criterion 7h, written
#: literally, asserts a value nothing ever writes and the database forbids — it
#: can only ever pass vacuously, which `CLAUDE.md` rule 12 calls worse than no
#: guard because it is reported as coverage. Escalated to cto; this is rule 10's
#: shape, with the divergence now visible in running code.
#:
#: Until it is ruled, both spellings are accepted and **everything else fails
#: closed**. Per rule 14, the layer that still catches the thing this guards
#: against is the exclusion itself: `'STAFF_MANUAL'`, `None` and any unknown
#: value render nothing under either spelling, so the control — never tell a
#: buyer that a staff-re-verified student signed in with a college email
#: address — holds whichever way the rename goes.
EMAIL_METHODS = frozenset({"EMAIL_DOMAIN", "INSTITUTIONAL_EMAIL"})


def signed_in_with_college_email(method):
    """True only for a method that *is* a college-email sign-in. Fail closed."""
    return method in EMAIL_METHODS


# --- Locale ----------------------------------------------------------------

def locale_of(user):
    code = getattr(user, "locale", None) or settings.LANGUAGE_CODE
    return code if code in offered_locales() else settings.LANGUAGE_CODE


def offered_locales():
    """The locales a student may actually be served.

    `THREAT-MODEL.md` §6.1(c): Tamil is absent from the language switcher and
    from `Accept-Language` negotiation while
    `feature_flags['i18n.ta_enabled']` is false — which is its seeded value and
    stays false until a named native speaker signs off the blocking classes in
    `locale/ta/BLOCKING_CLASSES.toml`. Tamil strings are written and shipped
    **unserved**.

    English first, always: it is the fallback the gate falls back to.
    """
    codes = ["en"]
    if flag("i18n.ta_enabled"):
        codes.append("ta")
    return codes
