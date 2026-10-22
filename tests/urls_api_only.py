"""A root URLconf carrying **only** backend's routes, for backend's own tests.

`bookhop/urls.py` includes `web.urls` when that package exists, and `web/**` is
frontend-developer's tree, written concurrently with this slice. So the real
root URLconf's importability depends on another agent's work-in-progress: at the
time this file was written, `web/views.py` raised `ImportError` mid-edit, which
made **every** test that resolved a URL fail for a reason that had nothing to do
with the code under test.

Pointing backend's L2 tests at this module removes that coupling. It mounts
`apps.accounts.urls` at **the same `api/v1/` prefix the real root uses**, so the
paths under test are the real paths — this is an isolation of the *tree*, not of
the route.

`test_accounts_api.py::test_the_real_root_urlconf_mounts_the_l2_api` asserts the
real mount by reading `bookhop/urls.py`, so this isolation cannot hide a route
that was never wired.
"""

from django.urls import include, path

from apps.core import views as core_views

urlpatterns = [
    path("healthz", core_views.healthz, name="healthz"),
    path("readyz", core_views.readyz, name="readyz"),
    path("api/v1/", include("apps.accounts.urls")),
]
