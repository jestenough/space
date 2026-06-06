"""Facade exposed to folder and file renderers during prerendering"""

from __future__ import annotations

from typing import Any

from ..templating import TemplateRenderer
from .context import FileShellContext, ListShellContext, RouteRender
from .head import Head
from .media import Media
from .meta import Meta
from .shell import Shell


class Services:
    def __init__(self, templates: TemplateRenderer, media: Media, languages: list[str] | None = None) -> None:
        self.head = Head()
        self.media = media
        self.meta = Meta()
        self.shell = Shell(templates, languages)

    def set_languages(self, languages: list[str]) -> None:
        self.shell.set_languages(languages)

    def page(self, base_html: str, route: RouteRender) -> str:
        head = self.head.render(
            route.lang,
            route.title,
            route.description,
            route.canonical_path,
            route.alternates,
            route.og_type,
            route.extra_head,
        )
        return self.shell.apply(self.head.inject(base_html, head), route.shell)

    def ui(self, lang: str) -> dict[str, str]:
        return self.shell.ui(lang)

    def list_shell(self, context: ListShellContext) -> dict[str, Any]:
        return self.shell.list(context)

    def file_shell(self, context: FileShellContext) -> dict[str, Any]:
        return self.shell.file(context)

    def shell_command_markup(self, command: str, cwd: str = "~") -> str:
        return self.shell.command(command, cwd)

    def stat_row(self, key: str, value: str) -> str:
        return self.shell.stat_row(key, value)

    def stat_row_html(self, key: str, value_html: str) -> str:
        return self.shell.stat_row_html(key, value_html)

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
