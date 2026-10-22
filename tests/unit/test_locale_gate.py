"""The Tamil locale gate — THREAT-MODEL §6.1(c), TASKS S1.

*"`feature_flags['i18n.ta_enabled']`, **default `false`**. Tamil is absent from
the language switcher **and from `Accept-Language` negotiation** while it is
false."*

**The leak, and why the layer matters.** `LocaleMiddleware` negotiates against
`settings.LANGUAGES`, which lists `ta`, so a plain `Accept-Language: ta` header
selected Tamil and shipped unreviewed strings to a student.
frontend-developer found it and closed it in its own page helper — the right
escalation, the wrong layer: a helper in `web/` covers only the pages that call
it, and **API-CONTRACT §2.1 makes `Accept-Language` select the locale for the
JSON API too**, whose handlers never call a `web/` helper. So it was closed on
six pages and open on every L2 endpoint, now and in every later slice.

**The required test is therefore the half the helper could never cover: the
JSON endpoint.** Both halves are here, side by side, because the pairing is the
finding.

TASKS S1 also assigns `test_locale_gate.py` to backend as one of the three
copy-enforcement tests, with the gate stated as *"the flag cannot be `true`
while any blocking-class `msgid` is unreviewed"*. That half needs
`locale/ta/BLOCKING_CLASSES.toml` and `locale/ta/REVIEWED.toml`, which are
**frontend-developer's** files (TASKS §1). Where they do not exist yet the
assertion **skips with the missing path named** — never passes — because a
manifest check over an absent manifest is the vacuous guard `CLAUDE.md` rule 12
is about.
"""

import pathlib

import pytest
from django.utils import translation

from apps.core.middleware import LocaleGateMiddleware
from apps.core.models import FeatureFlag

pytestmark = pytest.mark.django_db

REPO = pathlib.Path(__file__).resolve().parents[2]
LOCALE = REPO / "locale"
BLOCKING = LOCALE / "ta" / "BLOCKING_CLASSES.toml"
REVIEWED = LOCALE / "ta" / "REVIEWED.toml"

FLAG = "i18n.ta_enabled"


def _set_flag(enabled):
    FeatureFlag.objects.update_or_create(
        key=FLAG, scope_type="GLOBAL",
        defaults={"enabled": enabled, "scope_id": None, "updated_by": "pytest"},
    )


# --- the flag's default ---------------------------------------------------


def test_the_flag_is_absent_or_false_by_default():
    """DATA-MODEL §1: *"Absent key means off."* So Tamil is gated whether the
    row exists or not, and `seed_demo` seeds it explicitly `false` so an
    operator can see the gate rather than infer it from a missing row."""
    from apps.core.services import flag

    assert flag(FLAG) is False
    _set_flag(False)
    assert flag(FLAG) is False


# --- the gate, on both surfaces ------------------------------------------


@pytest.mark.urls("tests.urls_api_only")
def test_accept_language_ta_yields_english_on_a_json_endpoint(client, privacy_notice):
    """**The half frontend's page helper could never cover**, and the reason the
    gate is a middleware: an L2 handler never calls a `web/` helper, so before
    this middleware existed every JSON endpoint honoured `Accept-Language: ta`.
    """
    _set_flag(False)
    response = client.get("/api/v1/notices/privacy", headers={"Accept-Language": "ta"})
    assert response.status_code == 200
    assert response.json()["locale"] == "en", (
        "a JSON endpoint served the gated locale from an Accept-Language header"
    )


def test_accept_language_ta_yields_english_through_the_middleware(rf):
    """The HTML half, asserted on the middleware itself rather than on a page,
    because `web/**` is frontend's tree and this control must hold for a page
    that has not been written yet.
    """
    _set_flag(False)
    seen = {}

    def view(request):
        from django.http import HttpResponse

        seen["active"] = translation.get_language()
        seen["request_attr"] = getattr(request, "LANGUAGE_CODE", None)
        return HttpResponse("ok")

    request = rf.get("/", headers={"accept-language": "ta"})
    translation.activate("ta")  # what LocaleMiddleware would have left behind
    try:
        LocaleGateMiddleware(view)(request)
    finally:
        translation.deactivate()

    assert seen["active"] == "en"
    assert seen["request_attr"] == "en", (
        "`request.LANGUAGE_CODE` still said `ta`, so a template reading it would "
        "render the gated locale even though the catalogue was switched"
    )


@pytest.mark.parametrize("header", ["ta", "ta-IN", "ta;q=0.9,en;q=0.1", "TA"])
def test_every_spelling_of_the_gated_language_is_closed(rf, header):
    """A gate that closes `ta` and not `ta-IN` is a gate with a spelling. The
    region subtag is stripped before the lookup, which is what makes the check
    about the *language* rather than about a string."""
    _set_flag(False)
    seen = {}

    def view(request):
        from django.http import HttpResponse

        seen["active"] = translation.get_language()
        return HttpResponse("ok")

    translation.activate("ta")
    try:
        LocaleGateMiddleware(view)(rf.get("/", headers={"accept-language": header}))
    finally:
        translation.deactivate()
    assert seen["active"] == "en"


def test_the_gate_opens_when_the_flag_is_on(rf):
    """The other half, so the test above cannot pass by pinning English
    permanently — which would be a gate that can never be opened, i.e. a gate
    nobody can use and therefore one that gets deleted."""
    _set_flag(True)
    seen = {}

    def view(request):
        from django.http import HttpResponse

        seen["active"] = translation.get_language()
        return HttpResponse("ok")

    translation.activate("ta")
    try:
        LocaleGateMiddleware(view)(rf.get("/", headers={"accept-language": "ta"}))
    finally:
        translation.deactivate()
    assert seen["active"] == "ta"


def test_an_ungated_language_is_never_touched(rf):
    _set_flag(False)
    seen = {}

    def view(request):
        from django.http import HttpResponse

        seen["active"] = translation.get_language()
        return HttpResponse("ok")

    translation.activate("en")
    try:
        LocaleGateMiddleware(view)(rf.get("/", headers={"accept-language": "en"}))
    finally:
        translation.deactivate()
    assert seen["active"] == "en"


def test_ta_stays_in_settings_languages():
    """**Removing it is the wrong fix and this is where that stays written
    down.** `makemessages` needs it to extract a Tamil catalogue at all, staff
    rendering needs it once the flag is on, and a static setting cannot read a
    database flag at import time. The flag is the gate; the middleware is where
    it is applied."""
    from django.conf import settings

    assert "ta" in dict(settings.LANGUAGES)


def test_the_middleware_runs_immediately_after_the_locale_middleware():
    """Order is load-bearing: it corrects a decision `LocaleMiddleware` has
    already made, so running before it would simply be overwritten."""
    from django.conf import settings

    order = list(settings.MIDDLEWARE)
    locale = order.index("django.middleware.locale.LocaleMiddleware")
    gate = order.index("apps.core.middleware.LocaleGateMiddleware")
    assert gate == locale + 1, (
        f"LocaleGateMiddleware is at {gate} and LocaleMiddleware at {locale}; it "
        "must be immediately after, or the negotiated language is restored after "
        "the gate has corrected it"
    )


# --- the manifest half (frontend's files) ---------------------------------


def _require_manifests():
    missing = [path for path in (BLOCKING, REVIEWED) if not path.exists()]
    if missing:
        pytest.skip(
            "NOT VERIFIABLE YET (slice=S1): "
            + ", ".join(str(path.relative_to(REPO)) for path in missing)
            + " does not exist. Those files are frontend-developer's (TASKS.md §1) "
            "and a reviewed-hash check over an absent manifest asserts nothing — "
            "it is the vacuous guard CLAUDE.md rule 12 names. The flag-gate half "
            "of this file runs and passes regardless."
        )


def test_the_flag_cannot_be_true_while_a_blocking_class_string_is_unreviewed():
    """THREAT-MODEL §6.1(c) item 2, and the one assertion that needs frontend's
    manifests. The set of blocking msgids is declared in
    `locale/ta/BLOCKING_CLASSES.toml` and each reviewed string carries a
    reviewer-signed hash in `locale/ta/REVIEWED.toml`.

    **The reviewer named inside them is a human, not an agent** (TASKS A-9), and
    frontend owns the manifests while backend owns this test — *"neither agent
    can both write a sign-off and write the test that checks it."*
    """
    import tomllib

    _require_manifests()
    from apps.core.services import flag

    blocking = tomllib.loads(BLOCKING.read_text(encoding="utf-8"))
    reviewed = tomllib.loads(REVIEWED.read_text(encoding="utf-8"))
    blocking_ids = set(blocking.get("blocking", {}).get("msgids", [])) or set(blocking)
    assert blocking_ids, (
        "BLOCKING_CLASSES.toml declares no msgids, so this check would pass "
        "vacuously whatever REVIEWED.toml says"
    )

    unreviewed = sorted(
        msgid for msgid in blocking_ids
        if msgid not in reviewed or not reviewed[msgid].get("sha256")
    )
    if unreviewed:
        assert not flag(FLAG), (
            "i18n.ta_enabled is true while blocking-class Tamil strings are "
            f"unreviewed, which is the gate THREAT-MODEL §6.1(c) forbids: {unreviewed}"
        )
