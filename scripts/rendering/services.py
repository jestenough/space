"""Facade exposed to folder and file renderers during prerendering"""

from __future__ import annotations

from typing import Any

from ..templating import Templates
from .context import FileShellContext, ListShellContext, RouteRender
from .head import Head
from .media import Media
from .meta import Meta
from .pages import PageCache
from .shell import Shell


class Services:
    def __init__(self, templates: Templates, media: Media, languages: list[str] | None = None) -> None:
        self.templates = templates
        self.head = Head()
        self.media = media
        self.meta = Meta()
        self.shell = Shell(templates, languages)
        self.pages = PageCache(templates)

    def set_languages(self, languages: list[str]) -> None:
        self.shell.set_languages(languages)

    def page(self, route: RouteRender, assets: dict[str, list[str]]) -> str:
        return self.pages.render(
            route,
            assets,
            lambda: self.templates.render(
                "base.html",
                head=self.head.build(route, assets),
                page=route.page,
            ),
        )

    def page_stats(self) -> str:
        return self.pages.stats()

    def ui(self, lang: str) -> dict[str, str]:
        return self.shell.ui(lang)

    def list_shell(self, context: ListShellContext) -> dict[str, Any]:
        return self.shell.list(context)

    def file_shell(self, context: FileShellContext) -> dict[str, Any]:
        return self.shell.file(context)

    def cwd_for_section(self, section: str | None) -> str:
        return self.shell.cwd(section)

    def enhance_content_images(self, content_html: str) -> str:
        return self.media.enhance(content_html)

    def extract_content_images(self, content_html: str) -> list[dict[str, str]]:
        return self.media.images(content_html)

    def edit_href(self, localized_meta: dict[str, Any]) -> str | None:
        return self.meta.edit_href(localized_meta)

    def localized(self, value: Any, lang: str, path: str) -> str:
        return self.meta.localized(value, lang, path)

    def page_meta(self, site_meta: dict[str, Any], page: str, lang: str) -> dict[str, str]:
        return self.meta.page(site_meta, page, lang)

    def tag_page_meta(self, site_meta: dict[str, Any], lang: str, tag: str) -> dict[str, str]:
        return self.meta.tag_page(site_meta, lang, tag)

    def tag_alternates(self, section: str, tag: str, tags_by_lang: dict[str, set[str]]) -> dict[str, str]:
        return self.meta.tag_alternates(section, tag, tags_by_lang)
