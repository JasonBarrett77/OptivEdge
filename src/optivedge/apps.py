from django.apps import AppConfig


class OptivEdgeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "optivedge"
    label = "optivedge"

    def ready(self):
        # Connects the first-request receiver that sends `server_started`.
        from . import lifecycle  # noqa: F401
