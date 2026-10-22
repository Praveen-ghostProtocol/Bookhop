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
    # S2 — catalogue and listings. API-CONTRACT §5.2's L3 column, exactly.
    #
    # `/sell` is one path answering GET and POST because the contract names one
    # path for the seller's list and for creating a listing, and a no-JS
    # browser posts back to where it came from.
    #
    # `/sell/find-book` is a GET with the ISBN in the query string. An ISBN
    # identifies an edition, not a person, so the rule about personal data in
    # URLs does not bite — and making it a URL is what lets a student reload,
    # bookmark and back-button their way through a dropped 3G connection.
    path("sell", views.sell, name="sell"),
    path("sell/find-book", views.sell_find_book, name="sell-find-book"),
    path("sell/<int:listing_id>/photos", views.sell_photos, name="sell-photos"),
    path("sell/<int:listing_id>/publish", views.sell_publish, name="sell-publish"),
    path("sell/<int:listing_id>/withdraw", views.sell_withdraw, name="sell-withdraw"),
    path("listing/<int:listing_id>", views.listing_detail, name="listing"),
    # S2 — the demand side. `GET /wanted` is JOURNEYS J4's named entry point;
    # `GET /wanted/all` is the campus-wide list and is S3, so it is absent
    # rather than stubbed.
    path("wanted", views.wanted, name="wanted"),
    path("wanted/<int:request_id>/close", views.wanted_close, name="wanted-close"),
    # Help — the footer link that is in the same place on every page (SC 3.2.6)
    path("help", views.help_page, name="help"),
    # Public notices
    path("legal/<slug:kind>", views.legal, name="legal"),
    # PWA shell + operational — API-CONTRACT §5.8
    path("offline", views.offline, name="offline"),
    path("sw.js", views.service_worker, name="service-worker"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("robots.txt", views.robots, name="robots"),
    # The conventional icon path. base.html declares `<link rel="icon">` so a
    # browser never asks for this; the route is for clients that do anyway.
    path("favicon.ico", views.favicon, name="favicon"),
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
