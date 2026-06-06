"""Localized route metadata helpers"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from .. import routes
from ..config import DEFAULT_LANG, GITHUB_EDIT_BASE, TAG_PAGE
from ..localization import strict_text


class Meta:
    @staticmethod
    def edit_href(localized_meta: dict[str, Any]) -> str | None:
        source_path = localized_meta.get("sourcePath")
        if not isinstance(source_path, str) or not source_path:
            return None
        else:
            return f"{GITHUB_EDIT_BASE}/{quote(source_path.removeprefix('content/'), safe='/')}"

    @staticmethod
    def localized(value: Any, lang: str, path: str) -> str:
        return strict_text(value, lang, path)

    def page(self, site_meta: dict[str, Any], page: str, lang: str) -> dict[str, str]:
        data = site_meta.get("pages", {}).get(page)
        if not isinstance(data, dict):
            raise RuntimeError(f"Missing site metadata page: {page}")

        return {
            "title": self.localized(data.get("title"), lang, f"pages.{page}.title"),
            "description": self.localized(data.get("description"), lang, f"pages.{page}.description"),
        }

    def tag_page(self, site_meta: dict[str, Any], lang: str, tag: str) -> dict[str, str]:
        data = site_meta.get("pages", {}).get(TAG_PAGE)
        if not isinstance(data, dict):
            raise RuntimeError(f"Missing site metadata page: {TAG_PAGE}")

        return {
            "title": self.localized(data.get("title"), lang, f"pages.{TAG_PAGE}.title").format(tag=tag),
            "description": self.localized(data.get("description"), lang, f"pages.{TAG_PAGE}.description").format(
                tag=tag
            ),
        }

    @staticmethod
    def tag_alternates(section: str, tag: str, tags_by_lang: dict[str, set[str]]) -> dict[str, str]:
        alternates = {lang: routes.tag_route(section, lang, tag) for lang, tags in tags_by_lang.items() if tag in tags}
        alternates["x-default"] = alternates.get(DEFAULT_LANG) or next(iter(alternates.values()))

        return alternates
