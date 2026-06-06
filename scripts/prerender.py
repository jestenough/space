"""Static route prerendering step"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterator

from . import generated, routes
from .config import (
    DEFAULT_LANG,
    DIST_DIR,
    GENERATED_FILES_DIR,
    GENERATED_SITE_META_PATH,
    HOME_PAGE,
    LIST_PAGE_SIZE,
    MEDIA_MANIFEST_PATH,
    TEMPLATES_DIR,
    FileType,
    FolderType,
)
from .jsonio import read_json, read_text
from .rendering import registry
from .rendering.context import FilePageContext, FolderContext, ListShellContext, RouteRender
from .rendering.media import Media
from .rendering.services import Services
from .templating import TemplateRenderer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class State:
    base_html: str
    site_meta: dict[str, Any]
    sections: list[dict[str, Any]]
    section_items: dict[str, list[dict[str, Any]]]
    items: list[dict[str, Any]]
    languages: list[str]


class Prerender:
    def __init__(self) -> None:
        self.templates = TemplateRenderer(TEMPLATES_DIR)
        self.service = Services(self.templates, Media.load(MEDIA_MANIFEST_PATH))

    def run(self) -> None:
        state = self.load_state()
        for page in self.pages(state):
            self.write_page(state.base_html, page)

        localized_files = sum(len(item.get("languages", [])) for item in state.items)

        logger.info("Prerendered %s section(s) and %s localized file item(s).", len(state.sections), localized_files)

    def load_state(self) -> State:
        sections = generated.sections()
        items = generated.items(sections)
        languages = generated.item_languages(items)
        self.service.set_languages(languages)

        section_items = {str(section["slug"]): generated.section_items(str(section["slug"])) for section in sections}
        base_html = read_text(DIST_DIR / "index.html", "Missing dist/index.html; run vite build before prerender")
        site_meta = read_json(GENERATED_SITE_META_PATH)

        return State(base_html, site_meta, sections, section_items, items, languages)

    def pages(self, state: State) -> Iterator[RouteRender]:
        yield self.home_page(state, DEFAULT_LANG, "/", "/")

        for lang in state.languages:
            yield self.home_page(state, lang, f"/{lang}", f"/{lang}")

        yield from self.section_pages(state)
        yield from self.file_pages(state)

    def home_page(self, state: State, lang: str, route: str, canonical_path: str) -> RouteRender:
        page_meta = self.service.page_meta(state.site_meta, HOME_PAGE, lang)
        section = next(section for section in state.sections if section.get("system"))
        renderer = registry.folder_renderer(FolderType.SYSTEM)
        context = self.folder_context(state, lang, section)
        shell = self.service.list_shell(
            ListShellContext(
                lang=lang,
                sections=state.sections,
                active_section=None,
                welcome_title=page_meta["title"],
                welcome_lead=page_meta["description"],
                render_command=renderer.command(context),
                process_html=renderer.process_html(context),
                stage_html=renderer.stage_html(context),
            )
        )

        return RouteRender(
            route=route,
            lang=lang,
            title=page_meta["title"],
            description=page_meta["description"],
            canonical_path=canonical_path,
            alternates=routes.alternates(state.languages, lambda item_lang: f"/{item_lang}"),
            og_type="website",
            shell=shell,
        )

    def section_pages(self, state: State) -> Iterator[RouteRender]:
        for section in state.sections:
            if section.get("system"):
                continue

            folder_type = FolderType(str(section.get("kind") or FolderType.FILES))
            renderer = registry.folder_renderer(folder_type)

            for lang in generated.section_languages(section):
                context = self.folder_context(state, lang, section)
                yield from renderer.pages(context)
                yield from renderer.extra_pages(context)

    def file_pages(self, state: State) -> Iterator[RouteRender]:
        for section in state.sections:
            section_slug = str(section["slug"])
            for item in state.section_items[section_slug]:
                file_type = FileType(str(item.get("type") or FileType.PAGE))
                renderer = registry.file_renderer(file_type)
                for lang in item.get("languages", []):
                    content_html = self.service.enhance_content_images(
                        read_text(GENERATED_FILES_DIR / section_slug / f"{item['slug']}.{lang}.html")
                    )
                    localized_meta = generated.localized_item(section_slug, str(item["slug"]), lang)
                    context = FilePageContext(
                        lang,
                        section,
                        item,
                        localized_meta,
                        content_html,
                        state.sections,
                        self.templates,
                        self.service.ui(lang),
                        self.service,
                        None,
                    )
                    yield renderer.render_page(context)

    def folder_context(self, state: State, lang: str, section: dict[str, Any], tag: str | None = None) -> FolderContext:
        section_slug = str(section["slug"])
        return FolderContext(
            lang,
            section,
            state.section_items[section_slug],
            state.sections,
            state.items,
            state.site_meta,
            self.templates,
            self.service.ui(lang),
            self.service,
            LIST_PAGE_SIZE,
            tag,
        )

    def write_page(self, base_html: str, page: RouteRender) -> None:
        self.write_route(page.route, self.service.page(base_html, page))

    @staticmethod
    def write_route(route: str, content: str) -> None:
        path = DIST_DIR / "index.html" if route == "/" else DIST_DIR / route.strip("/") / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def run() -> None:
    Prerender().run()
