from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    label = "accounts"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """Register this app's job handlers.

        `apps.core.services.enqueue` refuses a kind with no registered handler
        (*"no handler registered for job kind ..."*), so an unimported handler
        module is not a silent misdelivery — it is a refusal at enqueue time.
        This import is what makes `accounts.send_magic_link` and
        `retention.purge` exist.
        """
        from . import jobs  # noqa: F401
