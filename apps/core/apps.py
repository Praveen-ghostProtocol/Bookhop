from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """Register the startup checks.

        `apps.core.checks.unapplied_migrations` refuses to start the app
        against a half-migrated database — written after the first browser walk
        of S1 hit a 500 on the first POST because the dev database was two
        migrations behind and nothing said so.
        """
        from . import checks  # noqa: F401
