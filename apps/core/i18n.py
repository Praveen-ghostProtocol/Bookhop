"""The locale gate, as **one** definition — THREAT-MODEL §6.1(c).

*"Tamil is absent from the language switcher **and from `Accept-Language`
negotiation** while `i18n.ta_enabled` is false."*

**REVIEW-S1 B4, and it is `CLAUDE.md` rule 10 exactly.** The gate was
implemented three times by three readers, each doing the obvious thing:

  * frontend-developer closed it in a `web/` page helper — right escalation,
    wrong layer, because it covers only the pages that call it;
  * `LocaleGateMiddleware` closed it for every request — but only by correcting
    `translation.get_language()`;
  * `apps/accounts/api.notice` **re-derived the locale from the raw
    `Accept-Language` header**, ignoring what the middleware had just decided,
    and `consents` used `user.locale` directly. Measured by review: with the
    flag off and a `ta` notice published, `GET /api/v1/notices/privacy` with
    `Accept-Language: ta` **served the unreviewed Tamil legal notice.**

So the decision is one function here, and both the middleware and the service
layer are readers of it. A fourth reader that spells it itself is the next
instance of the same defect; a fourth reader that calls `allowed_locale` cannot
be.
"""

#: Always available, flag or no flag.
UNGATED_LANGUAGES = frozenset({"en"})

#: language code -> the `feature_flags` key that opens it. A per-entry rule
#: rather than a flat list (`CLAUDE.md` rule 11), so a future locale with a
#: different gate can be added without rewriting the check.
GATED_LANGUAGES = {"ta": "i18n.ta_enabled"}

#: What a gated request falls back to. `settings.LANGUAGE_CODE` would be a
#: second source of truth for the same fact and could be set to a gated
#: language, which would make the fallback the leak.
FALLBACK_LANGUAGE = "en"


def base_language(code):
    """`ta-IN` -> `ta`, `TA` -> `ta`. A gate with a spelling is not a gate."""
    return (code or "").split("-")[0].split("_")[0].strip().lower()


def is_gated(code):
    """Is this language behind a flag at all? No database read."""
    return base_language(code) in GATED_LANGUAGES


def allowed_locale(requested, campus=None):
    """The locale that may actually be served for `requested`.

    Returns `FALLBACK_LANGUAGE` when `requested` is gated and its flag is off,
    and `requested`'s base language otherwise. **Every** locale decision in the
    codebase goes through this — a template's, a middleware's, a notice
    lookup's — so there is one answer to "may this student be served Tamil?".

    Reads the flag per call and does not cache: `flag()`'s own note applies, and
    a cache-invalidation bug here ships unreviewed Tamil to a student.
    """
    from .services import flag

    code = base_language(requested) or FALLBACK_LANGUAGE
    gate_key = GATED_LANGUAGES.get(code)
    if gate_key is not None and not flag(gate_key, campus=campus):
        return FALLBACK_LANGUAGE
    return code
