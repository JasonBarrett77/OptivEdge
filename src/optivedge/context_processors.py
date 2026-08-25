"""Shared template context processors."""

from .app_registry import health_indicators, sidebar_sections


def optional_app_navigation(request):
    return {
        "optional_sidebar_sections": sidebar_sections(),
        # Rendered by base.html on every page. Each entry means something is wrong; an
        # empty list means nothing is, and the shell shows no indicator at all.
        "app_health_indicators": health_indicators(),
    }
