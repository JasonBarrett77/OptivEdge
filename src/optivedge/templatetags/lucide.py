from __future__ import annotations

import re
from functools import lru_cache
from importlib.resources import files

from django import template
from django.utils.safestring import mark_safe


register = template.Library()

SVG_CLASS_RE = re.compile(r'\sclass="[^"]*"')
SVG_OPEN_RE = re.compile(r"<svg\b")


def _attr_re(name: str) -> re.Pattern[str]:
    return re.compile(rf'\s{re.escape(name)}="[^"]*"')


@lru_cache(maxsize=None)
def _read_icon(name: str) -> str:
    icon_path = files("optivedge").joinpath(
        "templates",
        "components",
        "icons",
        f"{name}.svg",
    )
    return icon_path.read_text(encoding="utf-8").strip()


@register.simple_tag
def lucide(name: str, **attrs: str) -> str:
    """Render an icon SVG, overriding or adding attributes on the root `<svg>`.

    Every keyword is applied, not just `class`. It previously accepted `**attrs` and
    silently dropped all of them except `class`, so `{% lucide "x" stroke_width="2.5" %}`
    looked correct, rendered, and did nothing.

    Underscores become hyphens, because Django's `simple_tag` parses keywords as Python
    identifiers and `stroke-width="2.5"` is a syntax error in a template tag. So write
    `stroke_width` for `stroke-width`, `stroke_linecap` for `stroke-linecap`, and so on.

    An attribute already on the SVG is replaced rather than duplicated - lucide icons ship
    with `stroke-width="2"`, and two of the same attribute is invalid markup whose winner
    is parser-defined.
    """
    svg = _read_icon(name)

    for key, value in attrs.items():
        attribute = key.replace("_", "-")
        rendered = f' {attribute}="{value}"'
        existing = _attr_re(attribute)
        if existing.search(svg):
            svg = existing.sub(rendered, svg, count=1)
        else:
            svg = SVG_OPEN_RE.sub(f"<svg{rendered}", svg, count=1)

    if "aria-hidden" not in svg:
        svg = SVG_OPEN_RE.sub('<svg aria-hidden="true"', svg, count=1)

    return mark_safe(svg)
