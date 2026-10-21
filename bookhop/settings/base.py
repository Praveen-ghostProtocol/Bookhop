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
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
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
JOB_MAX_ATTEMPTS = 5
# How long a claimed job may stay locked before another worker may take it.
# A conditional UPDATE claims a row but, unlike SELECT ... FOR UPDATE SKIP
# LOCKED, does not release it when the worker's connection dies, so without
# this a SIGKILLed worker loses its job permanently (ENGINE-DIVERGENCE §4.3).
# Generous relative to every S0-S7 handler, which are all sub-second.
JOB_LOCK_TIMEOUT = timedelta(minutes=15)
IDEMPOTENCY_RETENTION_HOURS = 24
