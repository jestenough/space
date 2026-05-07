"""Canonical public route builders."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import quote

from .config import DEFAULT_LANG, SYSTEM_SECTION


def item_route(section: Any, lang: str, slug: str, system: bool | None = None) -> str:
    section_slug = quote(section.slug if hasattr(section, "slug") else str(section), safe="")
    item_slug = quote(slug, safe="")
    is_system = bool(section.system) if hasattr(section, "system") else bool(system)
    return f"/{lang}/{item_slug}" if is_system else f"/{lang}/{section_slug}/{item_slug}"


def section_route(section: Any, lang: str, system: bool | None = None) -> str:
    section_slug = quote(section.slug if hasattr(section, "slug") else str(section), safe="")
    is_system = bool(section.system) if hasattr(section, "system") else bool(system)
    return f"/{lang}" if is_system else f"/{lang}/{section_slug}"


def generated_section_route(section: dict[str, Any], lang: str) -> str:
    slug = quote(str(section["slug"]), safe="")
    return f"/{lang}" if section.get("system") else f"/{lang}/{slug}"


def generated_item_route(item: dict[str, Any], lang: str) -> str:
    translations = item.get("translations")
    path = translations.get(lang) if isinstance(translations, dict) else None
    if isinstance(path, str):
        return path
    section = str(item["section"])
    slug = quote(str(item["slug"]), safe="")
    return f"/{lang}/{slug}" if section == SYSTEM_SECTION else f"/{lang}/{quote(section, safe='')}/{slug}"


def generated_pdf_route(item: dict[str, Any], lang: str) -> str:
    return f"{generated_item_route(item, lang)}.pdf"


def tag_route(lang: str, tag: str) -> str:
    return f"/{lang}/tags/{quote(tag, safe='')}"


def alternates(languages: Sequence[str], build_path: Callable[[str], str]) -> dict[str, str]:
    result = {lang: build_path(lang) for lang in languages}
    if result:
        result["x-default"] = result.get(DEFAULT_LANG) or next(iter(result.values()))
    return result
