"""Simple optional app registry helpers.

Installed apps may expose a small `app_meta.py` module with:

- `URL_MOUNT = {"prefix": "...", "module": "..."}`
- `SIDEBAR_SECTION = {...}`
- `HEALTH_INDICATOR = {"check": "module.path:callable"}`
"""

from __future__ import annotations

from importlib import import_module

from django.apps import apps
from django.urls import include, path


def iter_app_meta():
    for app_config in apps.get_app_configs():
        module_name = f"{app_config.name}.app_meta"
        try:
            yield import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name == module_name:
                continue
            raise


def optional_app_urlpatterns():
    patterns = []
    for app_meta in iter_app_meta():
        mount = getattr(app_meta, "URL_MOUNT", None)
        if not mount:
            continue
        patterns.append(path(mount["prefix"], include(mount["module"])))
    return patterns


def health_indicators():
    """Health indicators contributed by installed apps, for the shell to render.

    An app exposes `HEALTH_INDICATOR = {"check": "module.path:callable"}`. The callable
    takes no arguments and returns either **None** when everything is fine, or a dict with
    `label` and `url`.

    Returning None when healthy is the contract, not an optimisation: the shell shows
    nothing at all in that case, so the indicator's *presence* is the signal. There is
    deliberately no count - a number invites a threshold, and no amount of broken data is
    an acceptable amount.

    A check that raises is reported rather than swallowed. An indicator that fails silently
    is worse than none, since its absence would read as "all clear".
    """
    indicators = []
    for app_meta in iter_app_meta():
        spec = getattr(app_meta, "HEALTH_INDICATOR", None)
        if not spec:
            continue
        module_path, _, attribute = spec["check"].partition(":")
        try:
            result = getattr(import_module(module_path), attribute)()
        except Exception as exc:  # noqa: BLE001 - a broken check must not hide itself
            indicators.append({
                "label": f"Health check failed: {type(exc).__name__}",
                "url": "",
            })
            continue
        if result:
            indicators.append(result)
    return indicators


def sidebar_sections():
    sections = []
    for app_meta in iter_app_meta():
        section = getattr(app_meta, "SIDEBAR_SECTION", None)
        if section:
            if isinstance(section, list):
                sections.extend(section)
            else:
                sections.append(section)
    return sections
