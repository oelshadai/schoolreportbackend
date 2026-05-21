from django.apps import AppConfig


class FinancialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'financial'

    def ready(self):
        # Load audit signal handlers when the financial app is ready
        from . import signals  # noqa: F401
