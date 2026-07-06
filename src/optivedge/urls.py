from django.urls import path

from optivedge.app_registry import optional_app_urlpatterns
from optivedge.views import ApplicationEnvironmentSettingsView, HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path(
        "environment/settings/",
        ApplicationEnvironmentSettingsView.as_view(),
        name="application_environment_settings",
    ),
]

urlpatterns += optional_app_urlpatterns()
