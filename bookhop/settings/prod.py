"""Production. Postgres only, secrets from the environment, nothing optional."""

from .base import *  # noqa: F403
from .base import DATABASES, env

DEBUG = False
SECRET_KEY = env("BOOKHOP_SECRET_KEY", required=True)
ALLOWED_HOSTS = env("BOOKHOP_ALLOWED_HOSTS", required=True).split(",")

if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    # ADR-001 §2.2 is the stack decision, and it is not relaxed by the fact
    # that the development box cannot run it. SQLite in production would lose
    # the partial unique index semantics, the triggers and the concurrent
    # writers that the audit log, job runner and moderation queue depend on.
    raise RuntimeError("Production requires BOOKHOP_DB_ENGINE=postgres (ADR-001 §2.2)")

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
