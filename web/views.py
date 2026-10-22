"""L3 HTML routes — S1: first run, sign-in, age, consent, profile, deletion.

`API-CONTRACT.md` §1: these views validate input, call **L1 service functions
directly**, and render templates. They never import a model, never call L2 over
HTTP, and never implement a business rule. Every route here works as a plain
form POST with JavaScript disabled — that is a contract term, not a preference.

**No JavaScript is shipped by any route in this slice.** htmx is an enhancement
over a working baseline (`SYSTEM.md` §1 rule 1) and S1's flows are five
single-field forms and a confirmation; a fragment swap would add bytes to a
metered connection and buy nothing. The only script in the product today is
`static/js/sw-register.js`, which registers the service worker and does nothing
else.

**EVERY ROUTE THAT ANSWERS `GET` ALSO ANSWERS `HEAD`.** RFC 9110 requires it —
`HEAD` is `GET` without a body — and it is not a theoretical nicety: link
checkers, uptime monitors, some proxies and several messaging apps send `HEAD`
before they will render a preview, and a `405` makes a shared BookHop link look
broken before anyone clicks it. Read-only views therefore use Django's
`require_safe`, which *is* `require_http_methods(["GET", "HEAD"])` and names the
pair so it cannot be split by accident; the four form views spell out
`["GET", "HEAD", "POST"]`. **A new read route uses `require_safe`, never
`require_http_methods(["GET"])`.** Found by walking the product in a real
browser, which no test here does.

ERROR HANDLING IS ONE BRANCH ON ONE ATTRIBUTE. Every accounts exception is an
`apps.core.errors.ServiceError` carrying `.code` and `.http_status`
(`API-CONTRACT.md` §2.2), so `_service_problem` maps codes to pages and no view
catches a class name. Every failure renders the normal page shell with a notice
inside `<main>` — never a bare framework page, because a 500 still has to show
the grievance-officer link in the footer (`SYSTEM.md` §4.1 `error`).
"""

import hashlib
import pathlib
from django.contrib.staticfiles import finders
from django.http import (
    Http404,
    HttpResponse,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone, translation
from django.utils.translation import pgettext
from django.views.decorators.http import require_http_methods, require_safe

from apps.accounts import services as accounts
from apps.core import errors
from apps.core.services import assert_discovery_open

from . import context as ctx
from .forms import (
    CONSENT_PURPOSES,
    MAX_PHOTOS,
    REQUIRED_CONSENT_PURPOSES,
    AgeDeclarationForm,
    BookDetailsForm,
    ConsentForm,
    IsbnForm,
    ListingForm,
    NomineeForm,
    PhotoForm,
    ProfileForm,
    SignInForm,
    WantedForm,
    seller_words,
)

#: `GET /legal/{slug}` — the seven public notice **routes** of
#: `API-CONTRACT.md` §5.1. Routes are L3's to own, which is why this list lives
#: here; what a notice is *stored* as is not, which is why nothing below copies
#: `notice_versions.kind`'s enum.
#:
#: `handover-guidance`, not `handover-safety` (amendment A-7) — a slug is a
#: route, but an identifier is where a label comes from.
NOTICE_SLUGS = (
    "privacy",
    "terms",
    "seller-terms",
    "community-rules",
    "handover-guidance",
    "ranking",
    "grievance-officer",
)


#: The one slug whose kind is not its own name in UPPER_SNAKE, with the reason
#: beside it. `CLAUDE.md` rule 11: a rule that cannot express its own
#: exceptions gets replaced by a hand-maintained list the first time one
#: appears, and then the list silently stops matching. So the derivation below
#: stays the default and this is a declared exception of one.
#:
#: `/legal/grievance-officer` is the route a student is sent to for the
#: contact; `GRIEVANCE_PROCEDURE` is the notice kind, and it holds the
#: *procedure prose only* (DATA-MODEL A-25). The names differ because the page
#: is not the notice: it composes versioned prose with officer fields read live
#: from `legal_entities`. See `legal()`.
NOTICE_KIND_OVERRIDES = {"grievance-officer": "GRIEVANCE_PROCEDURE"}


def _notice_kind(slug):
    """The `notice_versions.kind` a route slug asks for.

    A RULE PLUS ONE DECLARED EXCEPTION, not a list (`CLAUDE.md` rules 11 and
    15). `notice_versions.kind` is an UPPER_SNAKE enum and the routes are
    lower-kebab, so the mapping is mechanical for six of the seven; copying all
    seven values here would be a second definition of the enum in a file that
    may not import the model (rule 10), and an eighth kind would need an edit.

    The derivation is not validated against the enum, deliberately: the
    database is asked for the notice, and a kind it has never heard of simply
    has none, which renders the same honest "not published yet" page as a kind
    that exists but is unpublished. The student needs the same sentence either
    way.
    """
    return NOTICE_KIND_OVERRIDES.get(slug) or slug.upper().replace("-", "_")

#: Which action a refused consent blocks, for `JOURNEYS.md` J1 step 5's "the
#: screen says which action that blocks". Data rather than prose in a template,
#: and keyed off the imported purpose list so a new purpose shows up here as a
#: missing key rather than as silence.
BLOCKED_BY_REFUSING = {
    "account": "consent.blocks.account",
    "listing_publication": "consent.blocks.listing_publication",
    "chat": "consent.blocks.chat",
    "safety_moderation": "consent.blocks.safety_moderation",
}


# --- plumbing --------------------------------------------------------------

def _ip_ua(request):
    """The two values every audited service call takes.

    Read off the request rather than out of `apps.core.request_context`: that
    contextvar is set by `RequestIdMiddleware` for logging, and a view already
    holds the request, so going through a contextvar would be a second source
    for one fact.
    """
    return request.META.get("REMOTE_ADDR"), (request.headers.get("User-Agent") or "")[:400]


def _page(request, template, status=200, **extra):
    """Render a page in a locale the student may actually be served.

    **This is where the Tamil gate bites.** `LocaleMiddleware` negotiates
    against `settings.LANGUAGES`, which lists `ta`, so an `Accept-Language: ta`
    request would otherwise be served with `<html lang="ta">`. While
    `feature_flags['i18n.ta_enabled']` is false that is wrong twice over: it
    breaks `THREAT-MODEL.md` §6.1(c) ("Tamil is absent from the language
    switcher **and from `Accept-Language` negotiation**"), and it is a SC 3.1.1
    failure in its own right, because the strings served would still be
    English — and a Tamil-tagged English page is what TalkBack turns into
    gibberish. So the locale is re-activated to an offered one before anything
    renders, and the response says so at the HTTP level too.
    """
    locales = extra.setdefault("locales", ctx.offered_locales())
    # The masthead's two marketplace links render only for a signed-in
    # student, because `/sell` and `/wanted` redirect to sign-in otherwise and
    # a nav item that bounces you is worse than one that is not there.
    # `JOURNEYS.md` J2's entry point is *"GET /sell from the main
    # navigation"*, so this is the journey's own requirement rather than
    # decoration — without it the sell flow is only reachable by typing a URL.
    extra.setdefault("signed_in", ctx.current_user(request) is not None)
    lang = getattr(request, "LANGUAGE_CODE", "en")
    lang = lang if lang in locales else locales[0]
    translation.activate(lang)
    extra.setdefault("page_lang", lang)
    extra.setdefault("notice_slugs", NOTICE_SLUGS)
    response = render(request, template, extra, status=status)
    response["Content-Language"] = lang
    return response


def _problem(request, status, heading_key, heading, body_key=None, body=None):
    """The `error` state of the page shell (`SYSTEM.md` §4.1, §4.7)."""
    return _page(
        request,
        "problem.html",
        status=status,
        heading=pgettext(heading_key, heading),
        body=pgettext(body_key, body) if body_key else None,
    )


def _service_problem(request, exc):
    """Render a `ServiceError` as a page, or None if this view should re-raise."""
    code = getattr(exc, "code", None)
    if code == "GATE_CLOSED":
        # SYSTEM.md §4.22: a full-page notice, no listing data, and **no date**,
        # because we do not have one (`gate.closed.body`).
        return _page(request, "gate_closed.html", status=403)
    if code == "RATE_LIMITED":
        page = _problem(
            request,
            429,
            "sys.rate_limited.h",
            "Too many tries",
            "sys.rate_limited.body",
            "Wait a little and try again. Nothing was lost.",
        )
        retry = getattr(exc, "retry_after", None) or exc.context.get("retry_after")
        if retry:
            page["Retry-After"] = str(int(retry))
        return page
    if code in ("NOT_AUTHENTICATED", "SUSPENDED"):
        return HttpResponseRedirect("/auth/start")
    if code == "VALIDATION_FAILED":
        return _problem(
            request,
            400,
            "sys.rejected.h",
            "That didn't go through",
            "sys.unchanged",
            "That didn't go through. Nothing has changed.",
        )
    if code in ("NOT_FOUND", "GONE"):
        # §2.2: not found **or** not visible to this actor, same body — a 403
        # would confirm the row exists and leak the catalogue. So this renders
        # the ordinary 404 page and says nothing about which it was.
        return not_found(request)
    return None


def _consent_rows(user):
    """One row per purpose: `(key, granted, required)`.

    Assembled here rather than in the template because a Django template cannot
    subscript a dict by a loop variable, and the alternative — a nested
    `{% for k, v in state.items %}{% if k == key %}` inside every row — is the
    kind of markup nobody reads at 3am. The order is `CONSENT_PURPOSES`', which
    is the order `DATA-MODEL.md` §2's CHECK lists them.
    """
    state = accounts.consent_state(user)
    return [
        (key, state.get(key, False), key in REQUIRED_CONSENT_PURPOSES)
        for key in CONSENT_PURPOSES
    ]


class _NeedsSignIn(Exception):
    pass


def _require_user(request):
    user = ctx.current_user(request)
    if user is None:
        raise _NeedsSignIn()
    return user


def _signed_in_only(view):
    def wrapped(request, *a, **kw):
        try:
            return view(request, *a, **kw)
        except _NeedsSignIn:
            return HttpResponseRedirect("/auth/start")

    wrapped.__name__ = view.__name__
    wrapped.__doc__ = view.__doc__
    return wrapped


# --- J1 · first run --------------------------------------------------------

@require_safe
def first_run(request):
    """`GET /` — `JOURNEYS.md` J1 step 1.

    One sentence on what BookHop is, one action. No carousel and no tour
    (`PRD.md` EX-8, `COPY-DECK.md` §4), because three screens of nothing on a
    metered connection is the first reason to leave.
    """
    user = ctx.current_user(request)
    if user is not None:
        return HttpResponseRedirect(ctx.next_step_url(user) or "/account")
    return _page(request, "first_run.html")


# --- magic link ------------------------------------------------------------

@require_http_methods(["GET", "HEAD", "POST"])
def auth_start(request):
    """`GET /auth/start` renders the form; `POST /auth/start` requests the link.

    **Always ends on the same page whatever happens.** `request_magic_link`
    raises `EmailDomainNotRecognised` for an unknown domain and `Suspended` for
    a suspended account, and both are swallowed here on purpose: the endpoint
    answers 202 regardless, because a different response for an unknown address
    is an account-enumeration oracle (`API-CONTRACT.md` §5.1, AC-A1.1). Only
    `RATE_LIMITED` is surfaced, and that is keyed on request volume rather than
    on whether the address exists, so it leaks nothing.

    There is **no code-entry step and no CAPTCHA**. SC 3.3.8 (Accessible
    Authentication) is satisfied by construction by the emailed link
    (`SYSTEM.md` §2.7); a typed code *is* a cognitive function test and adding
    one would break it. Abuse control is the server-side rate limit.
    """
    form = SignInForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        ip, ua = _ip_ua(request)
        try:
            accounts.request_magic_link(email, ip, ua)
        except errors.RateLimited as exc:
            return _service_problem(request, exc)
        except (errors.EmailDomainNotRecognised, errors.Suspended):
            # Deliberately indistinguishable from success. AC-A1.1 asserts
            # byte-identical responses for a known address, an unknown address
            # at a recognised domain, and a gmail address — so nothing may be
            # recorded in the session here either.
            pass
        # Post/redirect/get, and the address goes in the session rather than a
        # query string: personal data never travels in a URL.
        request.session["link_sent_to"] = email
        return HttpResponseRedirect("/auth/sent")
    return _page(request, "sign_in.html", form=form)


@require_safe
def auth_sent(request):
    """`GET /auth/sent` — a terminal page, not a spinner (`SYSTEM.md` §4.25).

    TWO THINGS ON THIS PAGE ARE REQUIRED BY NAME AND THEY PULL IN OPPOSITE
    DIRECTIONS, SO BOTH ARE SPELLED OUT HERE.

    1. **It echoes the address the student just submitted.** Acceptance
       criterion 7k is a *positive* assertion for exactly this line: criteria
       7f/7g forbid rendering a counterparty's email domain, and the obvious
       way to over-comply is to strip the echo from the one page where the
       student needs it — breaking sign-in while believing a control was
       tightened. This is the student's own submitted address, shown to
       themselves. It is not a disclosure.

    2. **It names the domains this campus accepts, generically.** `PRD.md`
       AC-A1.2 calls this "a product requirement, not polish": without it the
       enumeration-proof 202 and L1's `EmailDomainNotRecognised` combine into a
       silent dead end, which the PRD names as the most likely first-run
       failure in the product. EC-11 adds the empty case — no MoU yet, so no
       domains — where the page says the campus is not open for sign-ups.

    The domain list is read from `accepted_email_domains()` and is **not**
    derived from the submitted address, which is the part AC-A1.2 forbids:
    saying "we can't email @gmail.com" would confirm the student's own input
    back to them as a rejection and defeat the 202. It is campus
    configuration — identical for every visitor, disclosing nothing about any
    person. See the hand-back note on criterion 7f, whose wording is broader
    than its own rationale and which I have escalated rather than quietly
    picked a side on.

    No auto-polling (`SYSTEM.md` §4.25): polling on 3G for an email spends a
    student's money to learn nothing.
    """
    email = request.session.get("link_sent_to")
    if not email:
        return HttpResponseRedirect("/auth/start")
    return _page(
        request,
        "link_sent.html",
        email=email,
        accepted_domains=accounts.accepted_email_domains(),
    )


@require_safe
def auth_consume(request, token):
    """`GET /auth/c/{token}` — single use, 10-minute expiry.

    Any token failure renders one page: `auth.expired` covers used *and*
    expired in a single sentence, because distinguishing them tells the holder
    of a leaked link which it was and helps nobody who merely typed it. That is
    also the page a mail-scanner prefetch lands on — the token is burned, soft
    user-agent binding is logged and not enforced (`THREAT-MODEL.md` §5.5), so
    the answer is simply to ask for another.
    """
    ip, ua = _ip_ua(request)
    try:
        user = accounts.consume_magic_link(token, ip, ua)
    except (errors.TokenInvalid, errors.TokenExpired, errors.TokenAlreadyUsed):
        return _page(request, "link_dead.html", status=400)
    except errors.ServiceError as exc:
        page = _service_problem(request, exc)
        if page is not None:
            return page
        raise
    ctx.sign_in(request, user)
    # Redirect immediately so the token leaves the address bar and the browser
    # history (`THREAT-MODEL.md` §5.5).
    return HttpResponseRedirect(ctx.next_step_url(user) or "/account")


@require_http_methods(["POST"])
def auth_logout(request):
    ctx.sign_out(request)
    return HttpResponseRedirect("/")


# --- J1 · age gate ---------------------------------------------------------

@require_http_methods(["GET", "HEAD", "POST"])
@_signed_in_only
def account_age(request):
    """`POST /account/age` — `JOURNEYS.md` J1 step 4, `PRD.md` US-A2.

    Under 18: `submit_age_declaration` deletes the account immediately and
    **no date of birth is persisted anywhere** (`DATA-MODEL.md` §2, amendment
    A-5 removed the table that would have held it). The page states the rule
    and stops — AC-A2.3 forbids suggesting a workaround, inviting the student
    back with a different date, or leading with "sorry", so there is no button
    on that page at all. The session is flushed because the account it pointed
    at no longer exists.
    """
    user = _require_user(request)
    form = AgeDeclarationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ip, _ua = _ip_ua(request)
        try:
            accounts.submit_age_declaration(user, form.cleaned_data["date_of_birth"], ip)
        except errors.UnderEighteen:
            ctx.sign_out(request)
            return _page(request, "age_rejected.html", status=403)
        except errors.ServiceError as exc:
            page = _service_problem(request, exc)
            if page is not None:
                return page
            raise
        return HttpResponseRedirect(ctx.next_step_url(user) or "/account")
    return _page(request, "age.html", form=form)


# --- J1 · consent, and the privacy settings screen -------------------------

@require_http_methods(["GET", "HEAD", "POST"])
@_signed_in_only
def account_privacy(request):
    """`GET`/`POST /account/privacy` — the consent screen and the withdrawal
    toggles, which are the same six purposes and so are one route.

    Two shapes, because they are two different jobs:

    * **First run** (`outstanding_steps` still contains "consent"): six
      checkboxes, one per purpose, **none pre-ticked**, one submit. E-Com
      r.4(9) and AC-A3.1 — the guarantee is in `ConsentForm`, because a
      template is the wrong place to hold a legal rule.
    * **Settings**: one row per purpose showing its current state from
      `consent_state(user)`, with a single button that flips it. Withdrawal is
      one tap, exactly as easy as granting (DPDP r.3(c)(i)), and it is a toggle
      in settings, never an email.

    Each toggle is its own `<form>` with a hidden purpose and a hidden
    decision, so it works with JavaScript off and no row depends on another.
    `grant_consent`/`withdraw_consent` append rows and never update one, so
    this screen cannot destroy the history it is reading.
    """
    user = _require_user(request)
    setup = "consent" in accounts.outstanding_steps(user)
    ip, ua = _ip_ua(request)
    form = ConsentForm()

    if request.method == "POST":
        # Strict, not degrading: a consents row written against a missing
        # notice version is a defective legal record (AC-A3.3).
        notice = accounts.current_notice(_notice_kind("privacy"), ctx.locale_of(user))
        if notice is None:
            return _problem(
                request,
                503,
                "consent.no_notice.h",
                "The privacy notice isn't published yet",
                "consent.no_notice.body",
                "BookHop cannot ask for your choices until the notice is published.",
            )
        try:
            if setup:
                form = ConsentForm(request.POST)
                if form.is_valid():
                    for key in CONSENT_PURPOSES:
                        if form.cleaned_data.get(key):
                            accounts.grant_consent(user, key, notice, "SIGNUP_FORM", ip, ua)
                    request.session["consent_refused"] = [
                        k for k in REQUIRED_CONSENT_PURPOSES if not form.cleaned_data.get(k)
                    ]
                    return HttpResponseRedirect(ctx.next_step_url(user) or "/account")
            else:
                key = request.POST.get("purpose")
                if key not in CONSENT_PURPOSES:
                    raise Http404
                if request.POST.get("decision") == "grant":
                    accounts.grant_consent(user, key, notice, "SETTINGS_TOGGLE", ip, ua)
                    flash = pgettext("consent.granted", "That is now allowed.")
                else:
                    accounts.withdraw_consent(user, key, "SETTINGS_TOGGLE", ip, ua)
                    flash = pgettext("consent.withdrawn", "That is now not allowed.")
                request.session["flash"] = flash
                return HttpResponseRedirect("/account/privacy")
        except errors.ServiceError as exc:
            page = _service_problem(request, exc)
            if page is not None:
                return page
            raise

    return _page(
        request,
        "privacy.html",
        form=form if setup else None,
        setup=setup,
        rows=_consent_rows(user),
        blocked_by_refusing=BLOCKED_BY_REFUSING,
        notice_version=ctx.current_notice_label(_notice_kind("privacy"), ctx.locale_of(user)),
        refused=request.session.pop("consent_refused", None),
        flash=request.session.pop("flash", None),
        nominee_form=NomineeForm(),
    )


# --- profile ---------------------------------------------------------------

@require_http_methods(["GET", "HEAD", "POST"])
@_signed_in_only
def account(request):
    """`GET`/`POST /account` — profile, and the entry point to J8.

    `trust.campus_mail` is rendered here about the student themselves, gated on
    the verification **method** and failing closed on anything unknown
    (`web/context.py signed_in_with_college_email`).

    **It does not render today, and that is the fail-closed branch working
    rather than a bug.** There is no L1 function that returns a user's
    `campus_verifications.method` — `export_account` reads it but writes a
    `data_subject_requests` row, which is not something a profile GET may do.
    So the method resolves to None, the line is absent, and **no substitute
    string and no comment on the absence** appears: not "not available", not a
    greyed placeholder, not a tooltip. "Verified by BookHop staff" is the
    single worst string that could exist in this product. Escalated to cto with
    the enum-value divergence, since the seller block in S2 needs the same read.
    """
    user = _require_user(request)
    locales = ctx.offered_locales()
    if request.method == "POST":
        form = ProfileForm(request.POST, locales=locales)
        if form.is_valid():
            try:
                accounts.update_profile(
                    user,
                    display_name=form.cleaned_data["display_name"] or None,
                    locale=form.cleaned_data["locale"],
                )
            except errors.ServiceError as exc:
                page = _service_problem(request, exc)
                if page is not None:
                    return page
                raise
            request.session["flash"] = pgettext("profile.saved", "Your profile is updated.")
            return HttpResponseRedirect("/account")
    else:
        form = ProfileForm(
            initial={
                "display_name": getattr(user, "display_name", "") or "",
                "locale": ctx.locale_of(user),
            },
            locales=locales,
        )
    return _page(
        request,
        "account.html",
        form=form,
        user_obj=user,
        college_email_signin=ctx.signed_in_with_college_email(
            getattr(user, "campus_verification_method", None)
        ),
        flash=request.session.pop("flash", None),
    )


# --- US-X2 · access and nomination -----------------------------------------

@require_safe
@_signed_in_only
def account_export(request):
    """`GET /account/export` — the s11 access right (`PRD.md` AC-X2.1).

    A JSON download, generated live, with no staff step. It is served as a
    file rather than rendered as a page for one reason that matters: s11 is a
    right to *a copy*, and a copy a student can keep is a file, not a screen
    they have to photograph. `Content-Disposition: attachment` is what makes
    the browser offer to save it.

    It is deliberately not styled, paginated or summarised. The service decides
    what the export contains, including the §7 row 11 retention disclosure;
    this view adds nothing and omits nothing.
    """
    user = _require_user(request)
    try:
        payload = accounts.export_account(user)
    except errors.ServiceError as exc:
        page = _service_problem(request, exc)
        if page is not None:
            return page
        raise
    response = JsonResponse(payload, json_dumps_params={"indent": 2, "default": str})
    response["Content-Disposition"] = 'attachment; filename="bookhop-my-data.json"'
    response["Cache-Control"] = "no-store"
    return response


@require_http_methods(["POST"])
@_signed_in_only
def account_nominee(request):
    """`POST /account/nominee` — the s14 nomination.

    Name and email only; `record_nomination` refuses any other key, because a
    nominee's phone or address would be personal data about a third party with
    no `COMPLIANCE.md` §7 row.
    """
    user = _require_user(request)
    form = NomineeForm(request.POST)
    if form.is_valid():
        try:
            accounts.record_nomination(
                user, {"name": form.cleaned_data["name"], "email": form.cleaned_data["email"]}
            )
        except errors.ServiceError as exc:
            page = _service_problem(request, exc)
            if page is not None:
                return page
            raise
        request.session["flash"] = pgettext(
            "nominee.saved", "That person is recorded as your nominee."
        )
        return HttpResponseRedirect("/account/privacy")
    return _page(
        request,
        "privacy.html",
        status=400,
        form=None,
        setup=False,
        rows=_consent_rows(user),
        blocked_by_refusing=BLOCKED_BY_REFUSING,
        notice_version=ctx.current_notice_label(_notice_kind("privacy"), ctx.locale_of(user)),
        nominee_form=form,
    )


# --- J8 · deletion ---------------------------------------------------------

@require_http_methods(["GET", "HEAD", "POST"])
@_signed_in_only
def account_delete(request):
    """`GET`/`POST /account/delete` — `JOURNEYS.md` J8, `PRD.md` US-X1.

    Two steps: arriving on this page is step 1 and it carries **the whole truth
    before the point of no return** (AC-X1.2) — what goes now, that the record
    of completed transfers is kept without their name for one year and why, and
    that chat content is not deleted and is purged one year after the last
    message. Pressing the destructive button is step 2.

    The retention sentences are on the page and not behind a link because
    `COMPLIANCE.md` §7 row 11 requires the student to learn this here rather
    than from a support ticket. "Deleted" does not mean "erased", and the page
    says so in the student's own terms: tombstone-plus-purge means their
    transfers survive under a pseudonym — which is also what makes the
    counterparty's dispute and the repeat-transfer metric possible (AC-X1.3).
    """
    user = _require_user(request)
    if request.method == "POST":
        try:
            accounts.erase_account(user)
        except errors.ServiceError as exc:
            page = _service_problem(request, exc)
            if page is not None:
                return page
            raise
        ctx.sign_out(request)
        return _page(request, "deleted.html")
    return _page(request, "delete_confirm.html", user_obj=user)


# --- J9 · in-app help ------------------------------------------------------

@require_safe
def help_page(request):
    """`GET /help` — `JOURNEYS.md` J9 steps 2, 3, 6, 7.

    **Static copy and no ticket form, because there is no door to open one.**
    J9 is marked ⛔ BLOCKED (CG-2): every support L1 function takes `staff`,
    no endpoint exists, and nothing stores what a student writes. A form that
    posted nowhere would be worse than no form, and inventing an endpoint is
    not mine to do. What ships is what is buildable and honest: what we can and
    cannot do, stated **before** the student types anything (AC-H6.5), the
    commonest questions as static prose, and the statutory routes that do
    exist.

    **No phone number and no WhatsApp number appears here or anywhere else**
    (AC-H6.4): an unlogged channel makes support minutes unmeasurable, which is
    what D-009's mitigation runs on.

    The link to this page is in the same place in the footer of every single
    page — SC 3.2.6 Consistent Help, new in WCAG 2.2, and the only mechanism a
    student who is stuck mid-handover has.
    """
    return _page(request, "help.html")


# ===========================================================================
# S2 · the sell flow, the listing page, and the want
# ===========================================================================
#
# THE L1 MODULES ARE IMPORTED AT CALL TIME, NOT AT MODULE IMPORT, AND THAT IS
# DELIBERATE RATHER THAN LAZY.
#
# `web/urls.py` is imported by the root URLconf, so a module-level
# `from apps.listings import services` turns a service layer that is still
# landing into a 500 on **every route in the product**, including the
# grievance-officer page that `SYSTEM.md` §4.1 says must survive an outage.
# Imported here, a missing S2 service breaks exactly the S2 route that needs
# it and nothing else. `sys.modules` caches after the first call, so the cost
# is a dict lookup.
#
# NOTHING BELOW STUBS A MISSING SERVICE. If a name is not there yet the
# `ImportError`/`AttributeError` propagates and the route 500s honestly. A
# placeholder that returned `[]` would render an empty page that looks like an
# answer, which is the shape `CLAUDE.md` rule 10 calls worse than no check.


def _catalog():
    from apps.catalog import services  # noqa: PLC0415 — see the block comment

    return services


def _listings():
    from apps.listings import services  # noqa: PLC0415

    return services



#: SIX READS `API-CONTRACT.md` §3 DOES NOT NAME, AND BACKEND HAS SHIPPED
#: FIVE OF THEM. Recorded because the contract is still short of the code and
#: the next reader of §3 will not find these:
#:
#:   apps.listings.services.my_listings(actor, cursor=None, limit=20) -> Page
#:   apps.listings.services.get_own_listing(actor, listing_id) -> Listing  # NotFound
#:   apps.listings.services.my_requests(actor, cursor=None, limit=20) -> Page
#:   apps.listings.services.seller_block(listing) -> dict
#:   apps.listings.services.get_photo_for_download(actor, listing_id, sha256) -> ListingPhoto
#:   apps.listings.services.photo_response(photo) -> HttpResponse
#:
#: The last two are A-25's HTML twin, `GET /listing/{id}/photo/{sha256}`.
#: §5.2 names the *route* and A-25 freezes its spelling; neither names the
#: pair of service functions the route is built from, and both already exist
#: because the L2 twin calls the same two. `listing_photo` adds nothing to
#: them — same call, same order, same authorisation.
#:
#: Why `discovery.get_listing` could not have served the first two: it is a
#: **discovery** call, so it runs `assert_discovery_open` and is scoped to
#: what is visible (`API-CONTRACT.md` §5.3). A `DRAFT` is visible to nobody —
#: that is what `DRAFT` means — so a seller could not reach their own
#: half-finished listing to add a photo to it, and on a campus whose gate is
#: lawfully closed they could not reach any of their listings at all.
#: `PRD.md` AC-S1.3 makes resuming from `GET /sell` a failable criterion.
#: `get_own_listing`'s docstring makes the same argument from the other side.
#:
#: The fourth read, closing a want, needs no function: `close_request` already
#: accepts an id where it documents an object.
#:
#: **`apps.discovery` does not exist** — it is S3 — so `/listing/{id}` reads
#: through `get_own_listing` in this slice. See `listing_detail`.
#:
#: cto: §3 needs these four names added. Nothing here invents one.


def _items(page):
    """The rows out of a `Page` (`API-CONTRACT.md` §2.3: `{items, next_cursor}`).

    Tolerant of an object or a mapping because `Page` has no concrete
    definition in the contract yet — one expression, not a compatibility
    shim, and it collapses to `page.items` the moment there is a class.
    """
    if hasattr(page, "items") and not callable(getattr(page, "items")):
        return list(page.items)
    if isinstance(page, dict):
        return list(page.get("items", ()))
    return list(page)


#: Plain words for `listings.status` (`DATA-MODEL.md` §6.1).
#:
#: **No raw state name ever reaches a student** — `JOURNEYS.md` Appendix A
#: lists `AWAITING_CONFIRMATION` by name as the thing never shown, and
#: `PRD.md` AC-H1.4 makes it failable. A value that is not here renders **no
#: chip at all** rather than its own identifier: showing less than we know is
#: the safe direction, and a missing word is a visible gap a reviewer notices
#: where `REMOVED_LEGAL` on a student's screen is a defect they would not.
STATUS_WORDS = {
    "DRAFT": ("sell.status.DRAFT", "Not on the list yet"),
    "PENDING_REVIEW": ("sell.status.PENDING_REVIEW", "Waiting to be looked at"),
    "LIVE": ("sell.status.LIVE", "On the list"),
    "RESERVED": ("sell.status.RESERVED", "Someone is collecting this one"),
    "CLOSED_TRANSFERRED": ("sell.status.CLOSED_TRANSFERRED", "This one changed hands"),
    "WITHDRAWN": ("sell.status.WITHDRAWN", "Taken down"),
    "REJECTED": ("sell.status.REJECTED", "Not put on the list"),
    "REMOVED_LEGAL": ("sell.status.REMOVED_LEGAL", "Taken down after a legal notice"),
}

#: The two states in which a listing is a thing other students can reach.
#: A seller's `DRAFT` links to its own photo step instead.
PUBLIC_STATUSES = ("LIVE", "RESERVED")

#: `SYSTEM.md` §4.11 `stale`. Not a warning about a seller; a statement about
#: elapsed time, and `COMPETITORS.md` §3.5 calls listing staleness the
#: category's oldest failure mode.
STALE_AFTER_DAYS = 21


def _rupees(paise):
    """A rupee figure as a string, with paise shown only when there are any.

    The intake accepts whole rupees and refuses a decimal (`web/forms.py`
    `clean_asking_price_rupees`), so the second branch is reachable only from
    seed or staff-created data. It renders rather than rounding, for the same
    reason the intake refuses rather than rounding: **a rounded money value is
    a wrong value that looks right** (`CLAUDE.md` rule 12).

    The label is never attached here. `price.label.full` lives in the template
    beside the figure, because a helper that returned "Seller's asking price
    ₹280" as one string would put a legal control inside a formatter.
    """
    if paise is None:
        return None
    whole, part = divmod(int(paise), 100)
    return f"{whole:,}" if part == 0 else f"{whole:,}.{part:02d}"


def _book_of(book):
    """The bibliographic identity of a `books` row, as plain values.

    Reading `listing.book` at the call site is an attribute hop on the object
    L1 returned, which is what `account()` already does for
    `campus_verification_method`. It is **not** a query L3 composed: no
    filter, no manager, no `.objects`.
    """
    authors = getattr(book, "authors", None) or []
    return {
        "title": getattr(book, "title", None),
        "authors": ", ".join(str(a) for a in authors),
        "edition": getattr(book, "edition_label", None),
        "publisher": getattr(book, "publisher", None),
        "year": getattr(book, "publication_year", None),
        "isbn": getattr(book, "isbn13", None),
    }


def _listing_row(listing, today=None):
    """One listing as the values a template renders, and nothing more.

    The template maps no enum and formats no money. Every judgement — which
    word a status gets, whether a listing is stale, whether it has a public
    URL — is made here once, where it can be read in one place.
    """
    status = getattr(listing, "status", None)
    word = STATUS_WORDS.get(status)
    # THREE DIFFERENT AGES, AND THEY ANSWER THREE DIFFERENT QUESTIONS.
    #
    # `trust.attribution` — *"— Priya S, 3 days ago"* — is **when the seller
    # said this**, which is `created_at`. It must render on a listing that has
    # not been published, because the words are theirs from the moment they
    # typed them. Unaffected by the gate.
    #
    # `trust.stale_listing` — *"Listed 24 days ago — this may be gone"* — is
    # **how long it has been on the list where someone could take it**, and
    # that is NOT `published_at`.
    #
    # **THE GATE IS WHY.** `assert_discovery_open` is a *read* control
    # (cto, S2): a seller may publish on a campus whose gate is closed, and
    # the row sits at `LIVE` with `published_at` set and **nobody able to see
    # it**. On the day a campus finally opens, every listing in its backlog
    # would have carried "Listed 40 days ago — this may be gone" on the first
    # morning a buyer could see it — a hint drawn from elapsed time about
    # availability, on a listing nobody could ever have taken. The sentence
    # would have been wrong in both halves: it was not *listed* in the sense a
    # student reads, and nothing *may be gone*.
    #
    # So the clock is elapsed **visible** time: the later of publication and
    # the campus opening. A listing on a closed campus has been visible for no
    # time at all, which is exactly true, and the approved string is unchanged
    # — the defect was the number, not the words.
    written = getattr(listing, "created_at", None)
    published = getattr(listing, "published_at", None)
    opened = getattr(getattr(listing, "campus", None), "discovery_enabled_at", None)
    now = timezone.now()
    visible_since = (
        max(published, opened) if published is not None and opened is not None else None
    )
    days = (now - visible_since).days if visible_since is not None else None
    wrote_days = (now - written).days if written is not None else None
    return {
        "id": getattr(listing, "id", None),
        "book": _book_of(getattr(listing, "book", None)),
        "status": status,
        "status_word": pgettext(*word) if word else None,
        "price": _rupees(getattr(listing, "asking_price_paise", None)),
        "version": getattr(listing, "version", None),
        "published_at": published,
        "days_visible": days,
        "wrote_days_ago": wrote_days,
        "stale": days is not None and days > STALE_AFTER_DAYS,
        "public": status in PUBLIC_STATUSES,
        "words": seller_words(
            getattr(listing, "condition", None),
            getattr(listing, "annotation_level", None),
            getattr(listing, "damage_flags", None),
        ),
    }


def _save_data(request):
    """Is the student's data-saver setting on, and have they not overridden it?

    `SYSTEM.md` §4.16 `disabled` and criterion 9: under `Save-Data: on` **no
    `<img>` is emitted at all**, replaced by a link naming the real byte cost.
    `?photos=1` is that link — the student's own explicit opt-in, on a
    different URL, so the bare route still emits nothing.

    The header is a single token (`Save-Data: on`), not a list, so this is a
    comparison rather than a parse.
    """
    if request.GET.get("photos") == "1":
        return False
    return request.headers.get("Save-Data", "").strip().lower() == "on"


def _photo_rows(listing):
    """The photos on a listing, as `{id, sha256, width, height, bytes, kb}`.

    **CONTRACT GAP, smaller than the four above and recorded in the same
    breath:** `API-CONTRACT.md` §3 has no accessor for a listing's photos, so
    this hops the reverse relation on the object L1 returned. It is the one
    place in `web/**` that touches a related manager, it is confined to this
    function so a future `listings.services.photos_for(listing)` is a one-line
    change, and it fails closed — no relation, no photos, and the page renders
    its `empty` state rather than raising.

    The byte total is what `SYSTEM.md` §4.16's `Save-Data` link names, and it
    is **computed from the stored sizes rather than estimated**, which is the
    whole point of telling a student what an image will cost them.

    `width` and `height` are the **stored intrinsic pixels**, not a thumbnail
    size: they go straight onto the `<img>` so the browser reserves the right
    box before a byte of image arrives, and the CSS scales it down. That is
    the whole of the no-reflow requirement, in two attributes and no script.
    """
    try:
        rows = list(getattr(listing, "photos").all())
    except Exception:  # noqa: BLE001 — a missing relation is zero photos
        return []
    # ORDER IS A CORRECTNESS PROPERTY HERE, NOT A PREFERENCE. `ListingPhoto`
    # declares no `Meta.ordering`, so the related manager's order is whatever
    # the engine returns and can differ between two requests. The alt text is
    # **"Photo 2 of 4"** — a positional claim — so an unstable order makes it
    # false on the second page load, and the seller who photographed the
    # cover first would find it somewhere else each time.
    #
    # Sorted here rather than asking backend for `Meta.ordering`: this is a
    # presentation decision about four rows already in memory, and it is the
    # one place `web/**` reads them. `uploaded_at` is the seller's own
    # sequence; `id` breaks a same-millisecond tie so the sort is total.
    rows.sort(key=lambda p: (getattr(p, "uploaded_at", None), getattr(p, "id", 0)))
    # KB rounds UP, never down. `SYSTEM.md` §4.16 words the figure as "about
    # {kb} KB" and it is a **cost to the student**, so the honest direction is
    # the one that cannot under-state what they will pay. Rounding to nearest
    # also prints "0 KB" for anything under 512 bytes, which reads as broken.
    return [
        {
            "id": getattr(p, "id", None),
            "sha256": getattr(p, "sha256", "") or "",
            "width": getattr(p, "width", 0) or 0,
            "height": getattr(p, "height", 0) or 0,
            "bytes": getattr(p, "bytes", 0) or 0,
            "kb": -(-(getattr(p, "bytes", 0) or 0) // 1024),
        }
        for p in rows
        # A purged row survives its bytes (`DATA-MODEL.md` §10.2) and there is
        # nothing to point an `<img>` at: `get_photo_for_download` 404s on a
        # NULL `storage_key`, so rendering it would be a guaranteed broken
        # image. The row is dropped here, which also keeps "{i} of {n}" and
        # the byte total counting only photos that can actually be served.
        #
        # KNOWN CONSEQUENCE, NAMED RATHER THAN CODED AROUND: `sell_photos`
        # derives `room_for_more` from this list, so a listing with four rows
        # of which one is purged offers the upload control again. The limit
        # itself is `add_photo`'s and stays `add_photo`'s (rule 11) — a fifth
        # row is refused there with `sell.photos.full`, which is a sentence
        # rather than a crash. Ceiling: the seller is offered a control that
        # may refuse. Upgrade path: a service accessor that reports both
        # counts, when `API-CONTRACT.md` §3 gains one.
        if getattr(p, "storage_key", None)
    ]


def _seller_block(listing):
    """`SYSTEM.md` §4.11a — and every branch in it fails closed.

    Returns `{name, campus, college_email_signin}`.

    **THE VERIFICATION-METHOD TEST IS L1's, NOT MINE.**
    `listings.services.seller_block` decides `signed_in_with_college_email`
    from `campus_verifications.method`, and it is the one definition
    (`CLAUDE.md` rule 11) — L3 does not re-derive it and does not reach for
    `users.campus_verified`, which includes `STAFF_MANUAL` and would make the
    string a false statement about a person. That is condition 3 of
    `COMPLIANCE.md` §2.5a and criterion 7h. L1 also decides what a seller
    identity contains: three keys and no fourth, so no address, phone, email
    or coordinate can reach a template even by accident.

    **L3 ADDS THE SECOND CONDITION, WHICH L1 CANNOT SEE.** Condition 2 /
    criterion 7g: showing the fact to a counterparty is a *different
    processing operation* from verifying it, so the line must not render until
    `consent.listing_publication.disclosure` is live in the privacy notice.
    That is a question about a `notice_versions` row, not about a listing, and
    `_disclosure_is_notified` asks it here. Two independent layers over one
    string, which is `CLAUDE.md` rule 12 rather than belt and braces: either
    one alone would ship the line in a case the other refuses.

    **When it is false the line and its qualifier are both absent, with no
    substitute string and no comment on the absence.** Not "not available",
    not a greyed placeholder, not a tooltip, and above all not "Verified by
    BookHop staff" — BookHop asserting something about a person is the single
    worst string that could exist in this product (`COPY-DECK.md` §3.2).

    **No part of `campuses.email_domains` reaches any template** (criterion
    7f): `seller_block` does not return a domain and nothing here adds one.
    """
    block = _listings().seller_block(listing)
    return {
        "name": (block.get("display_name") or "").strip() or None,
        "campus": block.get("campus_name"),
        "college_email_signin": (
            bool(block.get("signed_in_with_college_email")) and _disclosure_is_notified()
        ),
    }


#: `COPY-DECK.md` §10.4 `consent.listing_publication.disclosure`, and criterion
#: 7g's gate. Written once, read twice: rendered to the student on the consent
#: screen, and compared against the live privacy notice here. **Not a
#: hand-copy** (`CLAUDE.md` rule 11) — both readers evaluate the same gettext
#: call, so a reword cannot move one without the other.
def _disclosure_sentence():
    return pgettext(
        "consent.listing_publication.disclosure",
        "When you put a book on the list, other students on your campus see "
        "your display name, your campus, and that you signed in with a college "
        "email address.",
    )


def _disclosure_is_notified():
    """True when the disclosure is actually in the live privacy notice.

    Criterion 7g as a runtime gate rather than as a note in a review. The
    notice body is backend's (`notice_versions`), so this asks the notice
    instead of assuming it, and **it fails closed**: no notice, no match, no
    sign-in line. Today that is the expected answer and the seller block
    correctly renders nothing — which is the control working, not a bug.
    """
    notice = ctx.read_notice("PRIVACY")
    body = getattr(notice, "body", None) or getattr(notice, "body_text", None) or ""
    return _disclosure_sentence() in str(body)


# --- J2 · listing a book ---------------------------------------------------

@require_http_methods(["GET", "HEAD", "POST"])
@_signed_in_only
def sell(request):
    """`GET /sell` — my listings. `POST /sell` — create one.

    One path, two methods, because `API-CONTRACT.md` §5.2 names one path for
    both and a no-JS browser posts back to where the contract says.

    `GET` is `PRD.md` AC-S1.3's resume point: *"an abandoned listing stays
    `DRAFT` and is resumable from `GET /sell` with every entered field and
    every uploaded photo intact."* Nothing here is cached and nothing is
    optimistic — the rows are whatever L1 last confirmed.
    """
    user = _require_user(request)
    if request.method == "POST":
        return _sell_create(request, user)
    try:
        mine = _listings().my_listings(user)
    except errors.ServiceError as exc:
        page = _service_problem(request, exc)
        if page is not None:
            return page
        raise
    return _page(
        request,
        "sell.html",
        rows=[_listing_row(listing) for listing in _items(mine)],
        flash=request.session.pop("flash", None),
    )


def _sell_create(request, user):
    """`POST /sell` — J2 steps 3 to 7, in one transaction of the student's time.

    **The book is re-resolved from the posted ISBN rather than carried in the
    session.** Two reasons, and the second is the one that matters: a session
    makes the flow un-resumable across a dropped connection, which is the
    normal case on 3G; and between the lookup and the submit another student
    may have created the same `books` row, so re-resolving is also how the
    race resolves itself instead of becoming a `DUPLICATE_ISBN` the seller
    cannot act on.

    **Seller terms are accepted before the listing is created**, because
    `create_listing` raises `SellerTermsNotAccepted` otherwise and J2 step 6
    says that is rendered as the terms screen again, never as an error page.
    """
    isbn = "".join(ch for ch in request.POST.get("isbn", "") if ch.isdigit())
    form = ListingForm(request.POST)
    details = BookDetailsForm(request.POST) if request.POST.get("title") else None
    ip, _ua = _ip_ua(request)

    if not form.is_valid() or (details is not None and not details.is_valid()):
        return _find_book_page(request, isbn, form=form, details=details, status=400)

    try:
        book = _catalog().find_book_by_isbn(isbn) if isbn else None
        if book is None:
            if details is None:
                # The ISBN resolved when the form was rendered and does not
                # now. Send the student back to step 2 rather than guessing a
                # catalogue row on their behalf — a wrong edition is the one
                # failure this product cannot afford.
                return HttpResponseRedirect("/sell/find-book")
            book = _catalog().create_book(
                user,
                isbn13=isbn,
                title=details.cleaned_data["title"],
                authors=details.cleaned_data["authors"],
                edition_label=details.cleaned_data["edition_label"],
                publisher=details.cleaned_data["publisher"],
                publication_year=details.cleaned_data["publication_year"],
                language=form.cleaned_data["language"],
            )
        notice = accounts.current_notice("SELLER_TERMS", ctx.locale_of(user))
        if notice is None:
            # Strict, not degrading, for the same reason the consent POST is:
            # a `seller_terms_acceptances` row against a missing version is a
            # defective legal record, and r.6(4)(a) wants a real one.
            return _problem(
                request,
                503,
                "sell.terms.missing.h",
                "The seller terms aren't published yet",
                "sell.terms.missing.body",
                "BookHop cannot take a listing until they are.",
            )
        accounts.accept_seller_terms(user, notice, ip)
        listing = _listings().create_listing(
            user,
            book=book,
            # `clean_asking_price_rupees` returns **paise**: the field is what
            # the student types, the cleaned value is what the column holds,
            # and `listings.services.parse_rupees_to_minor_units` is the one
            # thing that converts between them (QA F42).
            asking_price_paise=form.cleaned_data["asking_price_rupees"],
            condition=form.cleaned_data["condition"],
            annotation_level=form.cleaned_data["annotation_level"],
            damage_flags=form.cleaned_data["damage_flags"],
            language=form.cleaned_data["language"],
            category=form.cleaned_data["category"],
            # AC-S3.2's affirmative half, which the column cannot carry: an
            # empty `damage_flags` means two different things, and `no_damage`
            # is which one. L1 refuses an empty list without it, so the
            # sentinel is never stored and silence is never read as a claim.
            no_damage=not form.cleaned_data["damage_flags"],
        )
    except errors.ServiceError as exc:
        code = getattr(exc, "code", None)
        if code == "DUPLICATE_ISBN":
            # J2 step 2's "is this the one?" screen, which is where a seller
            # holding a book belongs when the catalogue already knows it.
            return HttpResponseRedirect(f"/sell/find-book?isbn={isbn}")
        if code == "SELLER_TERMS_NOT_ACCEPTED":
            form.add_error("seller_terms", pgettext(
                "sell.terms.required",
                "BookHop cannot take a listing until you have read the seller terms.",
            ))
            return _find_book_page(request, isbn, form=form, details=details, status=403)
        if code == "VALIDATION_FAILED":
            return _find_book_page(request, isbn, form=form, details=details, status=400)
        page = _service_problem(request, exc)
        if page is not None:
            return page
        raise
    return HttpResponseRedirect(f"/sell/{listing.id}/photos")


@require_safe
@_signed_in_only
def sell_find_book(request):
    """`GET /sell/find-book` — J2 steps 1 to 6.

    Three shapes on one route, because they are one question asked in
    sequence and a separate URL for each would cost a round trip on 3G:

    1. **no `isbn`** — the single ISBN field (J2 step 1);
    2. **`isbn` resolves** — the book, "Is this the one?", and the intake form;
    3. **`isbn` does not resolve** — `sell.isbn.notfound`, the add-a-book
       fields, and the same intake form below them. Never a dead end.

    A `GET` with the ISBN in the query string, so the resolved book is a URL
    the student can reload, share with themselves, and reach with the back
    button after a dropped connection. **An ISBN is not personal data** — it
    identifies an edition, not a person — so the privacy rule about query
    strings does not bite here.

    `API-CONTRACT.md` §5.2 calls this an htmx typeahead that degrades to a
    submit button. **It ships as the submit button and no htmx**, which is the
    baseline the contract requires the enhancement to degrade to; a typeahead
    that fires a request per keystroke on a metered connection is the wrong
    default for this device, and the enhancement can be added later without
    changing a single route.

    ### THE CREATE FLOW SURFACES NO OTHER STUDENT'S ROW, INCLUDING A COUNT

    A hard interface constraint, ruled with the gate (cto, S2), and **this is
    the page where it will be tempted**: *"3 others are selling this"*, *"most
    sellers ask around ₹200"*, *"2 people are looking for this"*. Every one of
    them is cheap to add here and every one is forbidden. cto's phrase is the
    test to apply — **that is a read wearing a write's clothing**, and the
    gate is shut for reads. An aggregate is not an exception: a count is a
    read of every row it counts.

    What this page may show is the **catalogue**: a `books` row is global
    rather than tenant-scoped (`ADR-002` §2) and carries no listing, no price
    and no person. Title, authors, edition, publisher, year and ISBN are the
    edition, not anybody's copy of it.

    It also keeps EX-3 out by construction: a suggested price would need a
    settled-price history, which P14 forbids, and a *range* would be derived
    from other sellers' asking prices, which this rule forbids separately.

    **Audited across the whole create flow** — `/sell`, `/sell/find-book`,
    `POST /sell`, `/sell/{id}/photos` — every service call is own-rows-only
    (`my_listings`, `get_own_listing`, `my_requests` all carry an ownership
    predicate in L1) or catalogue-only (`find_book_by_isbn`, `create_book`),
    and no template renders a count of anything. Stated here rather than only
    in a report, because the next person to add a helpful number will read
    this file and not that one.
    """
    _require_user(request)
    raw = request.GET.get("isbn")
    return _find_book_page(request, raw)


def _find_book_page(request, raw_isbn, form=None, details=None, status=200):
    """Render step 1/2/3 of the sell flow. Shared by the GET and the failed POST.

    One renderer, so a validation failure comes back on the page the student
    was looking at with every value they typed still in it (`SYSTEM.md` §4.4
    `error`: *"the typed value is never cleared"*).
    """
    isbn_form = IsbnForm({"isbn": raw_isbn} if raw_isbn else None)
    book = None
    not_found_isbn = None
    checksum_error = False

    if raw_isbn and isbn_form.is_valid():
        try:
            book = _catalog().find_book_by_isbn(isbn_form.cleaned_data["isbn"])
        except errors.ServiceError as exc:
            if getattr(exc, "code", None) != "VALIDATION_FAILED":
                raise
            # The only validation the service can still refuse after this
            # form's 13-digit check is the **checksum** — which is L1's rule
            # and is deliberately not re-implemented in `web/forms.py`
            # (`CLAUDE.md` rule 11). The sentence is ours so it stays inside
            # the copy deny-list; the judgement is L1's.
            checksum_error = True
            isbn_form.add_error("isbn", pgettext(
                "sell.isbn.checksum",
                "That ISBN doesn't look right — check the digits.",
            ))
        if book is None and not checksum_error:
            not_found_isbn = isbn_form.cleaned_data["isbn"]

    resolved = book is not None or not_found_isbn is not None
    return _page(
        request,
        "sell_find.html",
        status=status,
        isbn_form=isbn_form,
        isbn=(book and getattr(book, "isbn13", None)) or not_found_isbn or "",
        book=_book_of(book) if book is not None else None,
        not_found=not_found_isbn,
        form=(form or ListingForm()) if resolved else None,
        details=(details or BookDetailsForm()) if not_found_isbn else None,
    )


@require_http_methods(["GET", "HEAD", "POST"])
@_signed_in_only
def sell_photos(request, listing_id):
    """`GET`/`POST /sell/{id}/photos` — J2 step 8, and the riskiest screen here.

    **ONE FILE PER REQUEST.** `SYSTEM.md` §4.5: *"on 3G a 4-file request that
    dies at 90% loses all four; four requests lose one."* With JavaScript off
    that property is free rather than engineered — one input, one submit, one
    round trip — and the page that comes back **is** the resumable state, so
    there is no queue to lose and nothing is ever shown as uploaded that the
    server has not confirmed (rule 9 of `SYSTEM.md` §1).

    **The listing already exists as a `DRAFT` before any photo is sent**, so
    the typed description, the price and the ISBN are never at risk from a
    photo failure. That is EC-13 and AC-S1.3, and it is why `create_listing`
    and `publish_listing` are two calls.

    THE FOUR FAILURE STATES, AND WHAT THE STUDENT SEES IN EACH:

    * **too big** — refused by `PhotoForm` before a byte is read, with the
      size named. The student is told rather than meeting a proxy's 413 after
      paying for the upload;
    * **not an image we can read** — `UNSUPPORTED_IMAGE`/`VALIDATION_FAILED`
      from `add_photo`, with the format list, because J2 step 8 requires it;
    * **a fifth photo** — `TOO_MANY_PHOTOS`, rendered as §4.5's `disabled`
      state: the control goes away and the reason is in text beside it, never
      a dead control with no explanation;
    * **the upload dies mid-flight** — the browser's own network error, and on
      return this page shows exactly what landed. Nothing is queued and
      nothing claims to be saved that is not (`ADR-001` §6 excludes offline
      writes).

    The consecutive-failure count is in the session so §4.5's *"after 3
    failures the row offers Publish without this photo"* is a real affordance
    rather than a specification. **Publishing is available at every count** —
    photos are not required — so the count changes what is said, never what
    is possible.

    # ponytail: with JavaScript off a retry re-opens the file picker, because
    # §4.5's "the row keeps the chosen file" cannot be done — no browser
    # repopulates a file input, by design. Ceiling stated rather than hidden;
    # the upgrade path is the htmx enhancement, which keeps the `File` object
    # in memory and re-POSTs it.
    """
    user = _require_user(request)
    fails = request.session.get("photo_fails") or {}
    key = str(listing_id)
    form = PhotoForm()
    try:
        listing = _listings().get_own_listing(user, listing_id)
        if request.method == "POST":
            form = PhotoForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    _listings().add_photo(user, listing, form.cleaned_data["photo"])
                except errors.ServiceError as exc:
                    code = getattr(exc, "code", None)
                    if code not in ("TOO_MANY_PHOTOS", "VALIDATION_FAILED"):
                        raise
                    fails[key] = fails.get(key, 0) + 1
                    request.session["photo_fails"] = fails
                    form.add_error("photo", _photo_error(code))
                else:
                    fails.pop(key, None)
                    request.session["photo_fails"] = fails
                    return HttpResponseRedirect(f"/sell/{listing_id}/photos")
            else:
                fails[key] = fails.get(key, 0) + 1
                request.session["photo_fails"] = fails
            listing = _listings().get_own_listing(user, listing_id)
    except errors.ServiceError as exc:
        page = _service_problem(request, exc)
        if page is not None:
            return page
        raise

    photos = _photo_rows(listing)
    return _page(
        request,
        "sell_photos.html",
        status=400 if form.errors else 200,
        row=_listing_row(listing),
        form=form,
        photos=photos,
        photo_count=len(photos),
        max_photos=MAX_PHOTOS,
        room_for_more=len(photos) < MAX_PHOTOS,
        repeated_failures=fails.get(key, 0) >= 3,
        save_data=_save_data(request),
        photo_kb=_photo_kb_total(photos),
    )


def _photo_kb_total(photos):
    """What the whole strip costs, in KB, rounded **up**.

    The figure `SYSTEM.md` §4.16's data-saver link names. Summed from the
    stored byte counts and rounded once at the end — rounding each photo up
    and then adding would over-state a four-photo strip by up to 4 KB, and a
    cost quoted to a student has to be the real one in both directions.
    """
    return -(-sum(p["bytes"] for p in photos) // 1024)


def _photo_error(code):
    """The sentence for a refused photo. Two codes, two different next actions."""
    if code == "TOO_MANY_PHOTOS":
        return pgettext(
            "sell.photos.full",
            "This listing already has four photos, which is the most BookHop takes.",
        )
    return pgettext(
        "sell.photos.unsupported",
        "BookHop couldn't read that file. It takes JPEG, PNG and WebP photos.",
    )


@require_http_methods(["POST"])
@_signed_in_only
def sell_publish(request, listing_id):
    """`POST /sell/{id}/publish` — J2 step 9.

    **No success sentence is flashed about where the listing went**, and that
    is AC-S4.3 satisfied structurally rather than by discipline. At pilot
    `LISTING_REVIEW_ALL=true` puts every listing in `PENDING_REVIEW`; with the
    config off `publish_listing` may reach `LIVE` directly. A flash saying
    *"we'll look at this"* would be false in the second case and a flash
    saying *"it's on the list"* false in the first — so the redirect lands on
    `/sell`, where each listing's own status word is read from what L1
    returned. **Turning the config off changes no string**, which is what the
    criterion asks for.

    `expected_version` comes from a hidden field rendered off the object, so
    two tabs produce a `409` rather than one silently overwriting the other
    (`API-CONTRACT.md` §4.2).
    """
    return _transition(request, listing_id, "publish_listing")


@require_http_methods(["POST"])
@_signed_in_only
def sell_withdraw(request, listing_id):
    """`POST /sell/{id}/withdraw` — J2 step 11, behind a `<details>` confirm.

    Native disclosure, no JavaScript, no modal, no focus trap: the destructive
    button is not reachable by one stray tap and is never adjacent to a
    primary action (`SYSTEM.md` §5.1).
    """
    return _transition(request, listing_id, "withdraw_listing")


def _transition(request, listing_id, service_name):
    """Publish or withdraw — the same five lines twice would be the divergence.

    A `409` is rendered as `SYSTEM.md` §4.18's wording rather than as an error
    page: the listing changed, here it is as it stands now, nothing you did
    was lost.
    """
    user = _require_user(request)
    try:
        version = int(request.POST.get("expected_version", ""))
    except ValueError:
        version = None
    try:
        listing = _listings().get_own_listing(user, listing_id)
        listing = getattr(_listings(), service_name)(user, listing, version)
    except errors.ServiceError as exc:
        code = getattr(exc, "code", None)
        if code == "VERSION_CONFLICT":
            request.session["flash"] = pgettext(
                "sys.conflict.listing",
                "This listing changed while you were looking at it. "
                "Here it is as it stands now.",
            )
            return HttpResponseRedirect("/sell")
        if code == "TRANSITION_NOT_ALLOWED":
            request.session["flash"] = pgettext(
                "sell.transition.no",
                "That isn't something this listing can do from where it is now.",
            )
            return HttpResponseRedirect("/sell")
        page = _service_problem(request, exc)
        if page is not None:
            return page
        raise
    if service_name == "withdraw_listing":
        request.session["flash"] = pgettext("sell.withdrawn.done", "Taken down.")
    else:
        request.session["flash"] = _published_flash(listing)
    return HttpResponseRedirect("/sell")


def _published_flash(listing):
    """What a seller is told at the moment of publishing.

    **THE GATE IS A READ CONTROL, SO PUBLISHING ONTO A CLOSED CAMPUS SUCCEEDS
    AND NOBODY CAN SEE THE RESULT.** cto settled that in S2 and treated the
    obvious objection — a student doing work that cannot pay off — as *a
    disclosure problem* rather than dismissing it. This is the disclosure, and
    it has to reach the seller **here**, at publish, rather than in a help
    page nobody opens.

    Both branches are a fact about the product and neither predicts anything.
    The closed branch reuses `gate.closed.body`'s approved mechanism clause —
    *"BookHop opens listings one campus at a time"* — and, like that string,
    **names no date, because we do not have one** (`COPY-DECK.md` v1.5). It
    stops short of the coordinator's own suggested wording, *"listings open
    when BookHop launches on your campus"*, which reads as an undertaking that
    the campus will open; that is the safe direction on a sentence whose
    purpose is to stop a seller feeling tricked.

    Asked through `assert_discovery_open` rather than by reading
    `discovery_enabled_at` here: the gate is one definition and L3 does not
    get a second opinion about it (`CLAUDE.md` rule 11). It also catches
    `active=false`, which a NULL check alone would miss.

    **Known residual, named rather than solved:** a seller who comes back a
    week later sees "Waiting to be looked at" and is **not re-told about the
    gate.** That status word is honest — it does not claim the listing is
    live — so nobody is misled, and a standing notice on `/sell` was not added
    because the instruction was specific about the moment. Raised in the
    slice note as a question rather than decided here.
    """
    try:
        assert_discovery_open(getattr(listing, "campus", None))
    except errors.GateClosed:
        return pgettext(
            "sell.published.gate_closed",
            "Saved. Nobody can see this yet — BookHop opens listings one campus "
            "at a time, and yours isn't open.",
        )
    except errors.ServiceError:
        # Any other refusal is not ours to interpret into a sentence about the
        # gate. Fall through to the plain confirmation, which is true either
        # way, rather than guessing at a reason.
        pass
    return pgettext("sell.published", "Saved.")


# --- the listing page ------------------------------------------------------

@require_safe
@_signed_in_only
def listing_detail(request, listing_id):
    """`GET /listing/{id}` — **two labelled blocks, and the structure is a
    compliance control rather than a layout preference.**

    `SYSTEM.md` §4.11 and `COPY-DECK.md` §3.2: *"About this book"* holds the
    bibliographic identity, the asking price with its negotiability sentence,
    and the seller's attributed quotation; *"About this seller"* holds the
    display name, the campus, and — only when true — the sign-in fact with its
    qualifier immediately after it. **No trust sentence appears outside the
    block whose scope it names**, because compliance flagged that an unscoped
    "nothing here is checked" beside "signed in with a college email address"
    reads as the product arguing with itself.

    **There is no offer form on this page in S2 and that is not an omission.**
    `POST /offers` is `apps/transfers`, slice S4. A button that posted nowhere
    would be the shape `COPY-DECK.md` §14 withdrew five strings for. The page
    states the fact instead, in the register `help.no_channel` established: a
    statement about the product, not a promise about our future conduct.

    **THE READ IS `get_own_listing`, NOT `discovery.get_listing`, AND ONLY
    UNTIL S3.** `apps/discovery` does not exist — `API-CONTRACT.md` §5.3 puts
    every discovery read in S3 — so in this slice the only student who can
    reach a listing is the one who wrote it, arriving from `/sell` to see what
    the page looks like. `get_own_listing` is **strictly tighter** than the
    discovery read it stands in for: scoped, plus an ownership predicate, so
    nobody sees a listing they could not already see. Anyone else gets the
    404 that `API-CONTRACT.md` §2.2 requires for an invisible row.

    S3 swaps one line. The page itself does not change, which is the point of
    building it now: the buyer-facing listing exists and has been looked at
    before a buyer can reach it.

    **Criterion 9 — "no `<img>` when `Save-Data: on`" — stopped being vacuous
    in this slice, and that is the point of the change.** It used to pass
    because the page emitted no image under any header: no route served a
    stored photo, so there was nothing for the criterion to gate
    (`CLAUDE.md` rule 10's second disguise — a check that cannot fail).
    `API-CONTRACT.md` A-25 froze the URL, `listing_photo` below serves the
    HTML twin, and the strip now emits one `<img>` per stored photo **unless**
    `Save-Data: on` is set, in which case it emits a link naming the real byte
    cost. `tests/a11y/test_s2_photos.py` asserts both sides of that split, on
    a listing that actually has photos — because a criterion tested only on
    the page with none is the vacuous version wearing a test.
    """
    user = _require_user(request)
    try:
        listing = _listings().get_own_listing(user, listing_id)
    except errors.ServiceError as exc:
        page = _service_problem(request, exc)
        if page is not None:
            return page
        raise
    photos = _photo_rows(listing)
    return _page(
        request,
        "listing.html",
        row=_listing_row(listing),
        seller=_seller_block(listing),
        photos=photos,
        save_data=_save_data(request),
        photo_kb=_photo_kb_total(photos),
    )


@require_safe
@_signed_in_only
def listing_photo(request, listing_id, sha256):
    """`GET /listing/{id}/photo/{sha256}` — the HTML twin, frozen in A-25.

    **This view authorises nothing and decides nothing.** Both calls are the
    service layer's: `get_photo_for_download` applies scope, the discovery
    gate and listing status (and logs the gate refusal before converting it
    to a `404`), and `photo_response` produces the bytes or the
    `X-Accel-Redirect` that makes nginx produce them. L3 does what L3 does —
    turn a URL into a service call and a service result into a response.

    **Why a twin at all, rather than pointing `<img src>` at the L2 path.**
    The L2 route is `/api/v1/...`; an HTML page linking into the JSON API's
    namespace makes the API surface part of the page contract, and A-25 names
    the twin precisely so it is not. Same service, same authorisation, same
    bytes; one URL for documents and one for machines.

    **The error page is not an error page.** A `ServiceError` here is almost
    always `NOT_FOUND`, and the consumer is an `<img>` — rendering the full
    404 shell would send a few kilobytes of HTML to something that will
    display a broken-image icon regardless. An empty 404 is the honest and
    the cheap answer, and the *page* a student navigated to (the full-size
    view, same URL) gets the browser's own "cannot display" rather than
    ours. Named as a deliberate corner: a student who taps a thumb for a
    photo that was purged between page render and tap sees the browser's
    message, not BookHop's.
    """
    user = _require_user(request)
    try:
        photo = _listings().get_photo_for_download(user, listing_id, sha256)
        return _listings().photo_response(photo)
    except errors.ServiceError as exc:
        if getattr(exc, "code", None) in ("NOT_FOUND", "GONE"):
            return HttpResponse(b"", status=404, content_type="text/plain")
        page = _service_problem(request, exc)
        if page is not None:
            return page
        raise


# --- J4 · the book that is not there ---------------------------------------

@require_http_methods(["GET", "HEAD", "POST"])
@_signed_in_only
def wanted(request):
    """`GET`/`POST /wanted` — `JOURNEYS.md` J4 steps 2 and 6.

    **This page promises nothing** (AC-B2.5). It records a row and says so.
    J4 step 3 — *"a matching listing is published and the student is told"* —
    is ⛔ BLOCKED on CG-4: there is no `WANT_MATCHED` kind and no scan job, so
    **the student is never told anything**, and the page says that in one
    sentence rather than leaving them to infer a notification that will not
    come. `COPY-DECK.md` §1.7 rule 2: the first-person-plural verb in *"we'll
    tell you when someone lists it"* has no function behind it, so the string
    waits for the slice that writes one.

    An ISBN we do not recognise is carried as `free_text_title` rather than
    refused (EC-17) — one of the few places the product learns something about
    a syllabus nobody told us about.
    """
    user = _require_user(request)
    form = WantedForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        isbn = form.cleaned_data["isbn"]
        title = form.cleaned_data["title"]
        book = None
        try:
            if isbn:
                try:
                    book = _catalog().find_book_by_isbn(isbn)
                except errors.ServiceError as exc:
                    if getattr(exc, "code", None) != "VALIDATION_FAILED":
                        raise
                    book = None
            _listings().create_request(
                user,
                book=book,
                free_text_title=None if book is not None else (title or isbn),
                course_code=form.cleaned_data["course_code"] or None,
            )
        except errors.ServiceError as exc:
            page = _service_problem(request, exc)
            if page is not None:
                return page
            raise
        request.session["flash"] = pgettext(
            "wanted.recorded",
            "That is on your list below. BookHop does not tell you when a copy "
            "is listed — there is no way for it to yet.",
        )
        return HttpResponseRedirect("/wanted")

    try:
        mine = _listings().my_requests(user)
    except errors.ServiceError as exc:
        page = _service_problem(request, exc)
        if page is not None:
            return page
        raise
    return _page(
        request,
        "wanted.html",
        status=400 if form.errors else 200,
        form=form,
        rows=[_request_row(r) for r in _items(mine)],
        flash=request.session.pop("flash", None),
    )


def _request_row(req):
    """One `book_requests` row as display values. Open rows are the only ones
    with an action; a closed one is history and says which kind."""
    book = getattr(req, "book", None)
    status = getattr(req, "status", None)
    word = {
        "OPEN": ("wanted.status.OPEN", "Still looking"),
        "FULFILLED": ("wanted.status.FULFILLED", "You got this one"),
        "WITHDRAWN": ("wanted.status.WITHDRAWN", "You closed this"),
        "EXPIRED": ("wanted.status.EXPIRED", "Closed at the end of term"),
    }.get(status)
    return {
        "id": getattr(req, "id", None),
        "title": getattr(book, "title", None) or getattr(req, "free_text_title", None),
        "isbn": getattr(book, "isbn13", None),
        "course_code": getattr(req, "course_code", None),
        "status": status,
        "status_word": pgettext(*word) if word else None,
        "open": status == "OPEN",
    }


@require_http_methods(["POST"])
@_signed_in_only
def wanted_close(request, request_id):
    """`POST /wanted/{id}/close` — J4 step 6, "I don't need this any more"."""
    user = _require_user(request)
    try:
        # `close_request` documents a `BookRequest` and accepts an id where it
        # looks one up, scoped and ownership-checked. Passing the id is one
        # call rather than two and cannot read a row this student may not
        # close — so no `get_my_request` is needed and none is proposed.
        _listings().close_request(user, request_id)
    except errors.ServiceError as exc:
        page = _service_problem(request, exc)
        if page is not None:
            return page
        raise
    request.session["flash"] = pgettext("wanted.closed", "Taken off your list.")
    return HttpResponseRedirect("/wanted")


# --- public notices --------------------------------------------------------

@require_safe
def legal(request, kind):
    """`GET /legal/{kind}` — public, unauthenticated (`API-CONTRACT.md` §5.1).

    The text is the archived `notice_versions` body, so this view renders
    whatever the notice service returns and writes no legal copy of its own.

    **`grievance-officer` is the one page that composes rather than stores.**
    `GRIEVANCE_PROCEDURE` holds the versioned procedure prose; the officer's
    name, designation, email, phone and the registered address are columns on
    `legal_entities` and are read **at render time** (DATA-MODEL A-25).
    Freezing them into an immutable notice would be a second copy of a fact
    that changes without the notice changing, and a stale grievance contact is
    a direct regulatory failure. It is the same rule as the accepted-domains
    line on the link-sent page: the value arrives from the service, never
    baked into stored text.

    The contact is **never** hard-coded here. r.4(2) requires real published
    details and there are none yet — `INCORPORATION-AND-BLOCKERS.md` §4.1 is
    explicit that "BookHop Private Limited" and any CIN are misrepresentations
    today — so until the legal entity is filled in the page says the notice is
    not published, which is true.
    """
    if kind not in NOTICE_SLUGS:
        raise Http404
    # Reads, so they degrade rather than raising: these seven links are in the
    # footer of every page, and a notice that cannot be read must not take the
    # grievance-officer route down with it.
    return _page(
        request,
        "legal.html",
        kind=kind,
        notice=ctx.read_notice(_notice_kind(kind)),
        contact=ctx.grievance_contact() if kind == "grievance-officer" else None,
    )


# --- PWA shell -------------------------------------------------------------

@require_safe
def offline(request):
    """`GET /offline` — the service worker's fallback (`SYSTEM.md` §4.27).

    Shows the notice, and **never a queued-action list**: `ADR-001` §6 excludes
    offline writes, and a UI implying a queued write is a lie about durability.
    Footer links that need the network render as plain text saying so.

    **THIS PAGE MUST NOT VARY BY SESSION, AND THAT IS NOW LOad-BEARING RATHER
    THAN TIDY.** The service worker precaches it, and `shell_version` hashes
    what it serves — so if `/offline` rendered one thing for a signed-out
    visitor and another for a signed-in one, the cache name would change at
    sign-in and throw away a student's precached shell, re-downloading about
    11 KB on a metered connection at the worst possible moment.

    It holds today by construction: `offline_mode=True` suppresses the only
    session-dependent markup in `base.html` (the two marketplace nav links),
    and nothing else on the page reads the actor. **Measured**, not assumed —
    the anonymous and signed-in renders are byte-identical and so are their
    cache names. One assertion for whoever owns a suite:
    `client.get("/offline").content` is identical with and without a session.
    """
    return _page(request, "offline.html", offline_mode=True)


@require_safe
def manifest(request):
    """`GET /manifest.webmanifest`. A template so its strings are translatable."""
    return render(
        request,
        "manifest.webmanifest",
        {"page_lang": ctx.offered_locales()[0]},
        content_type="application/manifest+json",
    )


#: The PWA shell: four static files the browser fetches by URL, and two routes
#: whose bytes a **view** produces. One list, so `sw.js`'s precache set and the
#: cache name it is stored under cannot disagree (`CLAUDE.md` rule 11).
#:
#: A route entry names the view, not a template, and that distinction is the
#: whole correction below.
SHELL_STATIC = ("css/tokens.css", "css/app.css", "js/sw-register.js", "icons/bookhop.svg")
SHELL_ROUTES = (("/offline", offline), ("/manifest.webmanifest", manifest))


def shell_version(request):
    """A cache name derived from exactly the bytes the shell serves.

    ### Why this is the second version of this function

    `VERSION = 'bookhop-s1-1'` was a hand-typed string whose own comment
    claimed *"a stale one cannot outlive a deploy"* — true only while somebody
    remembered to edit it. It failed the first time it was tested: an
    `app.css` change was invisible in the browser because the worker kept
    serving the precached copy, and **a student with the PWA installed would
    have kept the old stylesheet indefinitely.**

    **The first fix hashed template SOURCE for the two route entries, and that
    was the same defect one level down.** `/offline` extends `base.html` and
    renders through `{% translate %}`, so its served bytes change when the page
    shell changes, when the footer changes, when a string changes, or when the
    locale changes — and **none of those touches `offline.html`.** A copy
    change would have left an installed app serving stale text under an
    unchanged cache name. Reported by the S2 gate, in the words that matter:
    *a cache that cannot notice it is stale.*

    So a route is now hashed by **calling its view and reading the response**.
    `SHELL_ROUTES` names `offline` and `manifest` themselves, so there is no
    second description of what those URLs return that could drift from the
    first — the digest is downstream of every input the response has, known
    and unknown, including ones added later by somebody who never reads this.

    ### What this costs, measured rather than assumed

    Four file reads and two template renders per `/sw.js`, which the browser
    requests about once per navigation because the response carries
    `Cache-Control: no-cache`. Measured at **well under a millisecond** on the
    target single VM. **There is deliberately no cache**: a cache keyed on
    anything cheaper than the output is a proxy for the output, and a proxy for
    the output is exactly what both previous versions got wrong.

    It also removes the locale question rather than answering it. Each visitor
    gets a name that is a function of the bytes *their own* browser will
    precache, so when `i18n.ta_enabled` is eventually turned on, a Tamil
    student's shell cache is keyed by Tamil bytes with nothing to remember.

    ### Failure is absorbed, not raised, and here is what that produces

    A missing static file, or a view that raises, contributes a marker instead
    of bytes. `/sw.js` must not 500 because an icon moved — that would take
    the whole offline shell down to protect a hash.

    The two failure modes, named rather than waved at, because "absorbed" is
    the kind of word that hides one:

    * **a route that always raises** gives a stable marker — and `addAll`
      fails on that route anyway, so there is nothing cached for the name to
      be wrong about;
    * **a route that raises intermittently** makes the name flip between two
      values, so the shell is re-fetched on alternating navigations. Wasteful
      on 3G, self-correcting, and visible.

    Neither is the silent staleness this function exists to prevent: that
    needs a render to *succeed* with content the digest cannot see, and there
    is no such path now that the digest is the output.
    """
    digest = hashlib.sha256()
    for name in SHELL_STATIC:
        try:
            digest.update(pathlib.Path(finders.find(name)).read_bytes())
        except (OSError, TypeError):
            digest.update(b"\x00missing:" + name.encode())
    for route, view in SHELL_ROUTES:
        try:
            digest.update(view(request).content)
        except Exception:  # noqa: BLE001 — see "Failure is absorbed", above
            digest.update(b"\x00unrenderable:" + route.encode())
    return "bookhop-" + digest.hexdigest()[:16]


@require_safe
def service_worker(request):
    """`GET /sw.js` — served from the root so its scope is the whole origin.

    A service worker's scope cannot exceed its own path, so this cannot live
    under `/static/`.

    The precache list and the cache name both come from `SHELL_STATIC` and
    `SHELL_ROUTES`, so what is cached and the version it is cached under cannot
    drift apart.
    """
    response = render(
        request,
        "sw.js",
        {
            "version": shell_version(request),
            "shell_static": SHELL_STATIC,
            "shell_routes": [route for route, _view in SHELL_ROUTES],
        },
        content_type="text/javascript",
    )
    response["Cache-Control"] = "no-cache"
    return response


@require_safe
def robots(request):
    """`Disallow: /` — no listing is ever indexed (`API-CONTRACT.md` §5.8)."""
    return HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain")


@require_safe
def favicon(request):
    """`/favicon.ico` — the conventional path, for clients that ask for it.

    **The primary fix is in `base.html`, not here.** Every page declares
    `<link rel="icon">`, so a browser that renders a BookHop page never
    requests this path. This route exists for the clients that ask anyway —
    link previewers, feed readers, a bare `curl` — and for the first request a
    browser makes to a URL whose response it has not parsed yet.

    A **permanent** redirect rather than serving the bytes: the browser caches
    the redirect, so the cost is one round trip ever rather than one per
    navigation, and the icon stays a single file in `static/icons/` rather than
    a second copy behind a second URL. The SVG is already in the service
    worker's precache and is referenced by the manifest, so by the time anyone
    follows this redirect the target is usually already in cache.

    # ponytail: no `/apple-touch-icon.png`. Ceiling — iOS Safari requests it
    # and will 404. The target device is a mid-range Android (`ADR-001`), the
    # fix is a raster file we do not have, and a redirect to an SVG would not
    # satisfy it. Add it with the PNG pair named in `static/icons/bookhop.svg`
    # if iOS ever becomes a measured share of traffic.
    """
    response = HttpResponsePermanentRedirect(static("icons/bookhop.svg"))
    response["Cache-Control"] = "public, max-age=604800"
    return response


# --- not found -------------------------------------------------------------

def not_found(request):
    """The catch-all at the end of `web/urls.py`.

    `handler404` has to be declared in the root URLconf, and `bookhop/urls.py`
    is backend's and is "not touched again by anyone" (`TASKS.md` §1). So the
    404 is a route instead, which keeps it inside my own tree and gets the
    thing that actually matters: a 404 renders the normal shell **with the
    footer**, because the grievance-officer contact is a regulatory requirement
    and an outage is exactly when someone needs it (`SYSTEM.md` §4.1 `error`).
    """
    return _problem(
        request,
        404,
        "sys.not_found.h",
        "That page isn't here",
        "sys.not_found.body",
        "The address may be wrong, or the page may have been taken down.",
    )
