from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'finance'
    verbose_name = 'Finance & Accounting'

    def ready(self):
        # Import signals to integrate with existing modules
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Avoid crashing app startup if migrations not ready
            pass
