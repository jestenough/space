"""Base file renderer contract and generic page behavior"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from ... import content, routes
from ...config import SYSTEM_SECTION, ContentExtension, FileType
from ...localization import exact_text, strict_text
from .. import code
from ..context import (
    FileIndexContext,
    FilePageContext,
    FileShellContext,
    LocalizedMetaContext,
    RouteRender,
    SourceRenderContext,
    Stat,
    TocItem,
)


class FileRenderer:
    file_type = FileType.PAGE
    tag_re = re.compile(r"<[^>]+>")
    heading_re = re.compile(
        r'<h([1-6])\b[^>]*\bid=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</h\1>', re.IGNORECASE
    )

    def index_meta(self, _: FileIndexContext) -> dict[str, Any]:
        return {}

    def localized_meta(self, _: LocalizedMetaContext) -> dict[str, Any]:
        return {}

    def postprocess_indexes(self, _: dict[str, list[dict[str, Any]]]) -> None:
        return None

    def render_source(self, context: SourceRenderContext) -> str:
        source = context.source
        item = context.item

        if source.ext == ContentExtension.TEX:
            body = context.convert_tex_to_html(source.path, item.path, item.section, item.slug, source.lang)
        elif source.ext == ContentExtension.MARKDOWN:
            body = context.convert_markdown_to_html(source.path, item.path, item.section, item.slug)
        else:
            content = context.templates.render(
                "parts/plain_text.html", text=source.path.read_text(encoding="utf-8").rstrip()
            )
            return context.templates.render("files/document.html", source_path=str(source.path), content=content)

        content = code.decorate(body, source.lang)
        return context.templates.render("files/document.html", source_path=str(source.path), content=content)

    def render_page(self, context: FilePageContext) -> RouteRender:
        title = strict_text(
            context.item.get("title"), context.lang, f"{context.section_slug}.{context.item_slug}.title"
        )
        description = strict_text(
            context.item.get("description"), context.lang, f"{context.section_slug}.{context.item_slug}.description"
        )
        display_name = self.display_name(context)
        toc = self.render_toc(context.content_html) if self.show_toc_for(context) else []
        shell = context.service.file_shell(
            FileShellContext(
                lang=context.lang,
                sections=context.sections,
                file_type=self.file_type,
                active_section=None if context.section.get("system") else context.section_slug,
                welcome_title=title,
                welcome_lead=description,
                welcome_command=f"sed -n '1,2p' {context.item_slug}.meta",
                render_command=f"cat {display_name}",
                process_command=f"stat {display_name}",
                process=self.process(context, display_name),
                content_html=context.content_html,
                back_href=routes.generated_section_route(context.section, context.lang),
                download_text="download",
                download_href=context.item.get("downloadPath") if context.item.get("downloadPath") else None,
                show_zen=self.is_readable_source(context),
                toc=toc,
                show_toc=bool(toc),
                template_context=self.template_context(context),
            )
        )

        return RouteRender(
            route=routes.generated_item_route(context.item, context.lang),
            lang=context.lang,
            title=title,
            description=description,
            canonical_path=routes.generated_item_route(context.item, context.lang),
            alternates=routes.alternates(
                context.item.get("languages", []),
                lambda item_lang: routes.generated_item_route(context.item, item_lang),
            ),
            og_type="website",
            page=shell,
        )

    def template_context(self, _: FilePageContext) -> dict[str, Any] | None:
        return None

    def display_name(self, context: FilePageContext) -> str:
        return exact_text(context.item.get("label"), context.lang) or context.item_slug

    def is_readable_source(self, context: FilePageContext) -> bool:
        source_path = str(context.localized_meta.get("sourcePath") or "")
        ext = Path(source_path).suffix.lower().lstrip(".")
        return ext in {"txt", "md", "tex"}

    def show_toc_for(self, context: FilePageContext) -> bool:
        source_path = str(context.localized_meta.get("sourcePath") or "")
        return Path(source_path).suffix.lower() == ".md"

    @classmethod
    def render_toc(cls, content_html: str) -> list[TocItem]:
        items = []
        for level, heading_id, _content in cls.heading_re.findall(content_html):
            text = html.unescape(cls.tag_re.sub("", _content)).replace("#", "").strip()
            if text:
                items.append(TocItem(id=heading_id, text=text, level=min(max(int(level), 1), 6)))
        return items

    def process(self, context: FilePageContext, display_name: str) -> list[Stat]:
        stamp = f"{context.item.get('date') or '1970-01-01'} 00:00:00 +0000"
        file_path = self.display_file_path(context.section_slug, display_name)

        return [
            Stat("File", file_path),
            Stat("Size", str(context.localized_meta.get("byteSize") or 0)),
            Stat("Blocks", "8"),
            Stat("IO", "4096 regular file"),
            Stat("Inode", "021"),
            Stat("Access", "(0664/-rw-rw-r--)"),
            Stat("Uid", "(1000/guest)"),
            Stat("Gid", "(1000/guest)"),
            Stat("Birth", stamp),
            Stat("Mtime", stamp),
            Stat("", rule=True),
            Stat("name", display_name),
            Stat("lang", context.lang),
            Stat("langs", ", ".join(context.item.get("languages", []))),
            Stat("type", str(context.item.get("type") or FileType.PAGE)),
        ]

    @staticmethod
    def display_file_path(section: str, slug: str) -> str:
        return f"~/{slug}" if section == SYSTEM_SECTION else f"~/{section}/{slug}"

    def validate_item(self, _: content.Section, item: content.Item) -> None:
        return None
