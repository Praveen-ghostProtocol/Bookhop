"""L2 routes for the catalogue — API-CONTRACT §5.2's first two rows.

Mounted at `/api/v1/` by `bookhop/urls.py`. The L3 equivalents
(`/sell/find-book`) are `web/urls.py`'s and are frontend-developer's; both
layers call the same L1 functions.
"""

from django.urls import path

from . import api

urlpatterns = [
    path("books", api.books, name="api-books"),
    path("books/<int:book_id>", api.book_detail, name="api-book-detail"),
]
