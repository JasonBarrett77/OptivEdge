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
    """The rail's sections, contributed by installed apps, MERGED BY LABEL and then ordered.

    A section is a heading in one rail, not one app's property. "Experimental" is named by
    Assessments and holds an item that lives in Integrations, and the reader should see one
    heading rather than two identical ones stacked. Merging by label is what lets each app keep
    declaring only its own items and its own URL names - the alternative is one app naming
    another's routes, which is the boundary this whole convention exists to hold.

    `order` (default 0) exists because merging alone puts a shared section wherever its FIRST
    contributor sits: Integrations is installed before Assessments, so a merged Experimental
    would otherwise land above the Assessments items rather than below them. The sort is
    stable, so a section that does not ask for a position keeps the one it had.

    A section's `active_names` gains its items' - a collapsible section needs to know whether
    the page being rendered is inside it, and asking every contributor to repeat its items'
    names at the section level is a list that would fall behind.
    """
    merged = {}
    for app_meta in iter_app_meta():
        declared = getattr(app_meta, "SIDEBAR_SECTION", None)
        if not declared:
            continue
        for section in (declared if isinstance(declared, list) else [declared]):
            items = list(section.get("items") or ())
            names = set(section.get("active_names") or ())
            for item in items:
                names |= set(item.get("active_names") or ())

            existing = merged.get(section["label"])
            if existing is None:
                # Copied, not referenced: these dicts are module-level in each app_meta, and
                # appending to one would grow the rail on every request.
                merged[section["label"]] = {
                    **section, "items": items, "active_names": names,
                    "collapsible": bool(section.get("collapsible")),
                    "order": section.get("order", 0),
                }
                continue
            existing["items"].extend(items)
            existing["active_names"] |= names
            existing["collapsible"] = existing["collapsible"] or bool(section.get("collapsible"))
            existing["order"] = max(existing["order"], section.get("order", 0))
    return sorted(merged.values(), key=lambda section: section["order"])
