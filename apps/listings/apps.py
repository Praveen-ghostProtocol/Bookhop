from django.apps import AppConfig


class ListingsConfig(AppConfig):
    name = "apps.listings"
    label = "listings"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """Register this app's job handlers.

        `apps.core.services.enqueue` refuses a kind with no registered handler,
        so an unimported handler module is a refusal at enqueue time rather
        than a silent misdelivery. This import is what makes
        `listings.purge_photos` exist.
        """
        from . import jobs  # noqa: F401
