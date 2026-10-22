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

from django.http import (
    Http404,
    HttpResponse,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import translation
from django.utils.translation import pgettext
from django.views.decorators.http import require_http_methods, require_safe

from apps.accounts import services as accounts
from apps.core import errors

from . import context as ctx
from .forms import (
    CONSENT_PURPOSES,
    REQUIRED_CONSENT_PURPOSES,
    AgeDeclarationForm,
    ConsentForm,
    NomineeForm,
    ProfileForm,
    SignInForm,
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
    """
    return _page(request, "offline.html", offline_mode=True)


@require_safe
def service_worker(request):
    """`GET /sw.js` — served from the root so its scope is the whole origin.

    A service worker's scope cannot exceed its own path, so this cannot live
    under `/static/`.
    """
    response = render(request, "sw.js", {}, content_type="text/javascript")
    response["Cache-Control"] = "no-cache"
    return response


@require_safe
def manifest(request):
    """`GET /manifest.webmanifest`. A template so its strings are translatable."""
    return render(
        request,
        "manifest.webmanifest",
        {"page_lang": ctx.offered_locales()[0]},
        content_type="application/manifest+json",
    )


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
