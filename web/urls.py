"""L3 routes. The only URLconf frontend-developer edits (`TASKS.md` §1).

Paths are exactly the L3 column of `API-CONTRACT.md` §5.1 and §5.8. Where the
contract names one path for a form and its submission (`POST /account/age`),
the GET that renders that form lives on the same path — one route, two methods,
so a no-JS browser posts back to where it came from.

Routes for S2+ slices are absent rather than stubbed: a route that renders a
placeholder is how a half-built flow reaches a student.
"""

from django.urls import path, re_path

from . import views

urlpatterns = [
    path("", views.first_run, name="first-run"),
    # Auth — API-CONTRACT §5.1
    path("auth/start", views.auth_start, name="auth-start"),
    path("auth/sent", views.auth_sent, name="auth-sent"),
    path("auth/c/<str:token>", views.auth_consume, name="auth-consume"),
    path("auth/logout", views.auth_logout, name="auth-logout"),
    # Account
    path("account", views.account, name="account"),
    path("account/age", views.account_age, name="account-age"),
    path("account/privacy", views.account_privacy, name="account-privacy"),
    path("account/export", views.account_export, name="account-export"),
    path("account/nominee", views.account_nominee, name="account-nominee"),
    path("account/delete", views.account_delete, name="account-delete"),
    # Help — the footer link that is in the same place on every page (SC 3.2.6)
    path("help", views.help_page, name="help"),
    # Public notices
    path("legal/<slug:kind>", views.legal, name="legal"),
    # PWA shell + operational — API-CONTRACT §5.8
    path("offline", views.offline, name="offline"),
    path("sw.js", views.service_worker, name="service-worker"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("robots.txt", views.robots, name="robots"),
    # LAST, AND NOTHING MAY FOLLOW IT.
    #
    # `handler404` must be declared in the root URLconf, which is backend's and
    # is "not touched again by anyone" (`TASKS.md` §1). So the 404 is a
    # catch-all route here instead, which keeps it in my tree and gets the
    # thing that matters: a 404 renders the normal shell *with the footer*,
    # because the grievance-officer contact is a regulatory requirement and an
    # outage is exactly when someone needs it (`SYSTEM.md` §4.1 `error`).
    #
    # THE HAZARD THIS CREATES, NAMED SO IT IS NOT DISCOVERED THE HARD WAY.
    # `bookhop/urls.py` mounts `web.urls` at `""` **after** its own routes, so
    # `/healthz`, `/readyz` and `/api/v1/*` all match first and are unaffected
    # — verified by resolving each one. But a future include added to the root
    # URLconf *below* the web include would be swallowed whole by this pattern,
    # and the symptom would be "the new API 404s" with nothing pointing here.
    # If that happens the fix is the include order in the root URLconf, not
    # deleting this route.
    re_path(r"^.*$", views.not_found, name="not-found"),
]
