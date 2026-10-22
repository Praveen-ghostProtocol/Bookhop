"""Settings common to every environment.

Production target is Postgres 16 (ADR-001 §2.2) and that is what this file
defaults to. The development/test path may be pointed at SQLite with
BOOKHOP_DB_ENGINE=sqlite, which is what makes the suite runnable on a machine
with neither Postgres nor Docker installed. Every behavioural difference
between the two engines for this schema is listed, with a verified/assumed
label, in company/architecture/ENGINE-DIVERGENCE.md. Read it before trusting a
green test.
"""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env(key, default=None, required=False):
    value = os.environ.get(key, default)
    if required and not value:
        raise RuntimeError(f"{key} must be set (see .env.example)")
    return value


# --- Core -----------------------------------------------------------------

SECRET_KEY = env("BOOKHOP_SECRET_KEY", "dev-only-insecure-key")
DEBUG = False
ALLOWED_HOSTS = [h for h in env("BOOKHOP_ALLOWED_HOSTS", "").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # X-Request-Id sits above everything that logs, so every line in a request
    # carries it. THREAT-MODEL §7.2: request_id is the investigation primitive
    # for the 6-hour CERT-In clock.
    "apps.core.middleware.RequestIdMiddleware",
    # CSP — THREAT-MODEL §4 B3, ASVS V1/V3 L2, assigned to S1 backend by
    # TASKS §2 with the instruction that it exist *before the first HTML page
    # ships*. Above SessionMiddleware so the nonce is on the request for every
    # view, including one that errors before a session is loaded.
    "apps.core.middleware.ContentSecurityPolicyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    # Immediately after LocaleMiddleware, because it corrects a decision that
    # middleware has already made. THREAT-MODEL §6.1(c): Tamil is absent from
    # `Accept-Language` negotiation while `i18n.ta_enabled` is false, and
    # API-CONTRACT §2.1 makes that header select the locale for the JSON API as
    # well as for pages — so the gate belongs here and not in a page helper.
    "apps.core.middleware.LocaleGateMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "bookhop.urls"
WSGI_APPLICATION = "bookhop.wsgi.application"

# templates/** and static/** are owned by frontend-developer (TASKS §1). They
# are configured here because settings are backend-owned; the directories may
# not exist yet and Django tolerates that.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
            ],
        },
    },
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Database -------------------------------------------------------------
# One key, two engines. Postgres is the default; nothing silently falls back.

_DB_ENGINE = env("BOOKHOP_DB_ENGINE", "postgres")

if _DB_ENGINE == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("BOOKHOP_DB_NAME", "bookhop"),
            "USER": env("BOOKHOP_DB_USER", "bookhop"),
            "PASSWORD": env("BOOKHOP_DB_PASSWORD", ""),
            "HOST": env("BOOKHOP_DB_HOST", "127.0.0.1"),
            "PORT": env("BOOKHOP_DB_PORT", "5432"),
            "ATOMIC_REQUESTS": False,
            # Two agents running the suite at once against one PostgreSQL
            # server share `test_<NAME>` by default, and the first teardown
            # drops the database out from under the second -- observed as
            # `FATAL: database "test_bookhop" does not exist` mid-run, in
            # errors that look like defects and are not. One env var makes a
            # parallel run isolated.
            "TEST": {"NAME": env("BOOKHOP_TEST_DB_NAME") or None},
        }
    }
elif _DB_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": env("BOOKHOP_DB_NAME", str(BASE_DIR / "dev.sqlite3")),
            "OPTIONS": {
                # Without this, SQLite does not enforce FK references at all.
                # Postgres always does; the local engine must not be laxer than
                # the one the assertions are about.
                "init_command": "PRAGMA foreign_keys=ON;",
                "transaction_mode": "IMMEDIATE",
            },
        }
    }
else:
    raise RuntimeError(f"BOOKHOP_DB_ENGINE must be 'postgres' or 'sqlite', got {_DB_ENGINE!r}")

# --- Time -----------------------------------------------------------------
# DATA-MODEL §0: all timestamps are aware, stored UTC, rendered Asia/Kolkata.
# Every SLA clock in §7 depends on this; there are no naive datetimes anywhere.
# Host clock accuracy itself (chrony -> NPL/NIC, CERT-In Direction (i)) is an
# INFRA.md/S8 deliverable and is NOT established by this file.
USE_TZ = True
TIME_ZONE = "Asia/Kolkata"

# --- i18n -----------------------------------------------------------------
USE_I18N = True
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("ta", "Tamil")]
LOCALE_PATHS = [BASE_DIR / "locale"]

# --- Static ---------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
if (BASE_DIR / "static").exists():
    STATICFILES_DIRS = [BASE_DIR / "static"]

# --- Session / CSRF (API-CONTRACT §2.1) -----------------------------------
SESSION_COOKIE_NAME = "bookhop_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 14 * 24 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = True  # 14-day *rolling* expiry
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"

# --- Logging --------------------------------------------------------------
# One JSON object per line, each with a UTC ISO-8601 `ts` and a `log_class`.
# That is what makes the retention policy mechanical rather than a judgement
# call: a retention job (or logrotate) selects by `ts` and keeps each class for
# its own floor. CERT-In's 180 days is subsumed by DPDP r.8(3)/r.6(1)(e)'s one
# year (ADR-001 §2.7), so the floor applied is 365 days, not 180.
LOG_RETENTION_DAYS = {"app": 365, "security": 365}
LOG_LEVEL = env("BOOKHOP_LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "apps.core.logging.JsonFormatter"},
    },
    "filters": {
        "request_id": {"()": "apps.core.logging.RequestIdFilter"},
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_id"],
        },
    },
    "root": {"handlers": ["stdout"], "level": LOG_LEVEL},
    "loggers": {
        "django.request": {"handlers": ["stdout"], "level": "WARNING", "propagate": False},
        # bookhop.security is the CERT-In/DPDP-relevant stream: auth decisions,
        # gate decisions, staff data access, detection events.
        "bookhop.security": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
    },
}

# --- BookHop ---------------------------------------------------------------
# ADR-002 §4: a campus is closed unless someone deliberately opened it. There
# is deliberately no setting here that opens the gate -- the gate is a column
# plus an evidence-checked management command, and a settings flag would be a
# bypass. See apps/core/services.assert_discovery_open.
LISTING_REVIEW_ALL = True  # TASKS §6.4; one-line change once the data says so

# --- S1: the tombstone email salt ------------------------------------------
# COMPLIANCE.md §7 rows 3 and 24. The salt is a server-side secret that is
# **deliberately not in the database**, so a database-only compromise cannot
# re-identify a deleted student by rainbow table — a sha256 of a predictable
# institutional address is enumerable from a roll list.
#
# There is **no default and no fallback**: `erase_account` raises when it is
# unset, because a shared default salt makes every deployment's hashes
# identical and the control worthless. The name is the one already reserved in
# `.env.example` (CLAUDE.md rule 10: one name, not a second invention).
#
# The *version* is what makes §7 row 24's rotation procedure possible —
# "retire a version when no live tombstone references it" needs the tombstone
# to record which version hashed it.
TOMBSTONE_EMAIL_SALT = env("BOOKHOP_TOMBSTONE_EMAIL_SALT", "")
TOMBSTONE_EMAIL_SALT_VERSION = env("BOOKHOP_TOMBSTONE_EMAIL_SALT_VERSION", "v1")

# --- Rate limiting (API-CONTRACT §2.4, ADR-001 §2.4) ------------------------
# There is deliberately **no CACHES setting and no cache backend.** ADR-001 §2.4
# names "Django's database cache backend" for rate limiting, and the reason it
# gives is "it removes Redis" -- which a table in the database we already have
# satisfies equally. The limiter is `apps.core.models.RateLimitCounter`, with
# the deviation and its two reasons recorded on that model and raised to cto:
# Django's cache table has a column named `value`, which the P14 guard correctly
# refuses, and `CLAUDE.md` rule 13 says rename ours before exempting theirs.
#
# Nothing else in the codebase caches anything, so there is no second consumer
# to strand. A slice that needs one adds CACHES then, with a backend chosen for
# that need.

# --- Email (S1 sends the magic link; SES is S7) ----------------------------
# Console in development so a magic link is readable in the runserver output
# without a mail host. The bodies are templates under `templates/email/` and
# are frontend-developer's (TASKS §1); backend passes a context dict.
EMAIL_BACKEND = env(
    "BOOKHOP_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = env("BOOKHOP_EMAIL_FROM", "no-reply@bookhop.invalid")

# The origin an emailed link has to be absolute against. A job has no request,
# so when `accounts.send_magic_link` is enqueued outside one there is nothing to
# derive a scheme and host from. **There is deliberately no default**: a
# `localhost` default would email a student a link to their own machine, which
# is a plausible-looking value that fails only for the recipient and passes
# every test. `apps.core.request_context.public_origin` raises without it.
PUBLIC_ORIGIN = env("BOOKHOP_PUBLIC_ORIGIN", "")
JOB_MAX_ATTEMPTS = 5
# How long a claimed job may stay locked before another worker may take it.
# A conditional UPDATE claims a row but, unlike SELECT ... FOR UPDATE SKIP
# LOCKED, does not release it when the worker's connection dies, so without
# this a SIGKILLed worker loses its job permanently (ENGINE-DIVERGENCE §4.3).
# Generous relative to every S0-S7 handler, which are all sub-second.
JOB_LOCK_TIMEOUT = timedelta(minutes=15)
IDEMPOTENCY_RETENTION_HOURS = 24
