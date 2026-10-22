"""L2 routes for the accounts block — API-CONTRACT §5.1's left-hand column.

Mounted at `/api/v1/` by `bookhop/urls.py`. The L3 equivalents (`/auth/start`,
`/account/privacy`, …) are `web/urls.py`'s and are frontend-developer's; both
layers call the same L1 functions, which is what makes two agents working at
once safe (§1).
"""

from django.urls import path

from . import api

urlpatterns = [
    path("auth/magic-link", api.magic_link, name="api-auth-magic-link"),
    path("auth/consume", api.consume, name="api-auth-consume"),
    path("auth/logout", api.logout, name="api-auth-logout"),
    path("account/age-declaration", api.age_declaration, name="api-account-age"),
    path("account/consents", api.consents, name="api-account-consents"),
    path("account/consents/<str:purpose_key>", api.set_consent, name="api-account-consent-set"),
    path("account/export", api.export, name="api-account-export"),
    path("account/nominee", api.nominee, name="api-account-nominee"),
    path("account/correction", api.correction, name="api-account-correction"),
    path("account/erase", api.erase, name="api-account-erase"),
    path("account", api.account, name="api-account"),
    path("notices/<str:kind>", api.notice, name="api-notice"),
]
