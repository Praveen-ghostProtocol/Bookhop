"""Root URLconf.

TASKS §1: this file includes `web.urls` **once, in S0**, and is not touched
again by anyone. frontend-developer only ever edits `web/urls.py`.
"""

import importlib.util

from django.urls import include, path

from apps.core import views as core_views

urlpatterns = [
    path("healthz", core_views.healthz, name="healthz"),
    path("readyz", core_views.readyz, name="readyz"),
]

# `web/**` is frontend-developer's tree and is written concurrently, so S0 must
# boot before it exists. `find_spec` asks the one question that matters -- is
# the module there? -- and leaves a genuine ImportError *inside* `web.urls` to
# propagate. A `try/except ModuleNotFoundError` around the include would have
# swallowed that as "not there yet", which is a silent outage of the entire
# student-facing surface (REVIEW-S0 N4). Nothing here needs deleting later, so
# this file is not touched again (TASKS §1).
if importlib.util.find_spec("web") is not None:
    urlpatterns += [path("", include("web.urls"))]
