"""Static route prerendering step"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import unquote

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
from .templating import Templates

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class State:
    assets: dict[str, list[str]]
    site_meta: dict[str, Any]
    sections: list[dict[str, Any]]
    section_items: dict[str, list[dict[str, Any]]]
    items: list[dict[str, Any]]
    languages: list[str]


class Prerender:
    def __init__(self) -> None:
        self.templates = Templates(TEMPLATES_DIR)
        self.service = Services(self.templates, Media.load(MEDIA_MANIFEST_PATH))

    def run(self) -> None:
        state = self.load_state()
        for page in self.pages(state):
            self.write_page(page, state.assets)

        self.write_root()
        localized_files = sum(len(item.get("languages", [])) for item in state.items)

        logger.info(
            "Prerendered %s section(s) and %s localized file item(s); page cache: %s.",
            len(state.sections),
            localized_files,
            self.service.page_stats(),
        )

    def load_state(self) -> State:
        sections = generated.sections()
        items = generated.items(sections)
        languages = generated.item_languages(items)
        self.service.set_languages(languages)

        section_items = {str(section["slug"]): generated.section_items(str(section["slug"])) for section in sections}
        site_meta = read_json(GENERATED_SITE_META_PATH)

        return State(self.load_assets(), site_meta, sections, section_items, items, languages)

    @staticmethod
    def load_assets() -> dict[str, list[str]]:
        manifest = read_json(DIST_DIR / ".vite" / "manifest.json")
        entry = manifest.get("index.html") if isinstance(manifest, dict) else None
        if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
            raise RuntimeError("Missing Vite index.html entry in dist/.vite/manifest.json")

        styles = entry.get("css")
        return {
            "scripts": [entry["file"]],
            "styles": [str(item) for item in styles] if isinstance(styles, list) else [],
        }

    def pages(self, state: State) -> Iterator[RouteRender]:
        for lang in state.languages:
            yield self.home_page(state, lang, f"/{lang}", f"/{lang}")

        yield from self.section_pages(state)
        yield from self.file_pages(state)

    def home_page(self, state: State, lang: str, route: str, canonical_path: str) -> RouteRender:
        page_meta = self.service.page_meta(state.site_meta, HOME_PAGE, lang)
        section = next(section for section in state.sections if section.get("system"))
        renderer = registry.folder_renderer(FolderType.SYSTEM)
        context = self.folder_context(state, lang, section)
        page = self.service.list_shell(
            ListShellContext(
                lang=lang,
                sections=state.sections,
                active_section=None,
                welcome_title=page_meta["title"],
                welcome_lead=page_meta["description"],
                render_command=renderer.command(context),
                process=renderer.process(context),
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
            page=page,
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

    def write_root(self) -> None:
        content = self.templates.render("system/root.html", lang=DEFAULT_LANG)
        (DIST_DIR / "index.html").write_text(content, encoding="utf-8")

    def write_page(self, page: RouteRender, assets: dict[str, list[str]]) -> None:
        self.write_route(page.route, self.service.page(page, assets))

    @staticmethod
    def write_route(route: str, content: str) -> None:
        if route == "/":
            relative = Path("index.html")
        else:
            parts = [part for part in unquote(route).strip("/").split("/") if part not in ("", ".")]
            if any(part == ".." or any(char in part for char in '\\:<>"?*|') for part in parts):
                raise RuntimeError(f"Unsafe prerender route: {route}")
            relative = Path(*parts, "index.html")

        path = DIST_DIR / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def run() -> None:
    Prerender().run()
