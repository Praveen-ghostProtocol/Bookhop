"""L2 routes for listings and book requests — API-CONTRACT §5.2.

Mounted at `/api/v1/` by `bookhop/urls.py`. `listings/mine` is declared before
`listings/<int:listing_id>` because Django resolves in order and `mine` would
otherwise never be reached — it is not an int, so it would fall through to the
404 rather than to the list, which is a silent 404 on a contract route.
"""

from django.urls import path

from . import api

urlpatterns = [
    path("listings", api.listings, name="api-listings"),
    path("listings/mine", api.my_listings, name="api-listings-mine"),
    path("listings/<int:listing_id>", api.listing_detail, name="api-listing-detail"),
    path("listings/<int:listing_id>/photos", api.listing_photos, name="api-listing-photos"),
    path(
        "listings/<int:listing_id>/photos/<str:sha256>",
        api.photo_bytes,
        name="api-listing-photo-bytes",
    ),
    path("listings/<int:listing_id>/publish", api.publish, name="api-listing-publish"),
    path("listings/<int:listing_id>/withdraw", api.withdraw, name="api-listing-withdraw"),
    path("requests", api.requests_, name="api-requests"),
    path("requests/<int:request_id>", api.request_detail, name="api-request-detail"),
]
