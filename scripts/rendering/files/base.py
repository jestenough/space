"""Base file renderer contract and generic page behavior"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from ... import content, routes
from ...config import SYSTEM_SECTION, ContentExtension, FileType
from ...localization import exact_text, strict_text
from ..context import (
    FileIndexContext,
    FilePageContext,
    FileShellContext,
    LocalizedMetaContext,
    RouteRender,
    SourceRenderContext,
)


class FileRenderer:
    file_type = FileType.PAGE

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
            body = context.convert_tex_to_html(source.path, item.path, item.section, item.slug)
        elif source.ext == ContentExtension.MARKDOWN:
            body = context.convert_markdown_to_html(source.path, item.path, item.section, item.slug)
        else:
            text = source.path.read_text(encoding="utf-8")
            body = f'<pre class="info-file-pre">{html.escape(text.rstrip())}</pre>'

        return f'<section class="file-document" data-source="{html.escape(str(source.path))}">{body}</section>\n'

    def render_page(self, context: FilePageContext) -> RouteRender:
        title = strict_text(
            context.item.get("title"), context.lang, f"{context.section_slug}.{context.item_slug}.title"
        )
        description = strict_text(
            context.item.get("description"), context.lang, f"{context.section_slug}.{context.item_slug}.description"
        )
        display_name = self.display_name(context)
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
                process_html=self.process_html(context, display_name),
                content_html=context.content_html,
                back_href=routes.generated_section_route(context.section, context.lang),
                download_text="download",
                download_href=context.item.get("downloadPath") if context.item.get("downloadPath") else None,
                show_zen=self.is_readable_source(context),
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
            shell=shell,
        )

    def template_context(self, _: FilePageContext) -> dict[str, str] | None:
        return None

    def display_name(self, context: FilePageContext) -> str:
        return exact_text(context.item.get("label"), context.lang) or context.item_slug

    def is_readable_source(self, context: FilePageContext) -> bool:
        source_path = str(context.localized_meta.get("sourcePath") or "")
        ext = Path(source_path).suffix.lower().lstrip(".")
        return ext in {"txt", "md", "tex"}

    def process_html(self, context: FilePageContext, display_name: str) -> str:
        stamp = f"{context.item.get('date') or '1970-01-01'} 00:00:00 +0000"
        cwd = context.service.cwd_for_section(context.section_slug)
        file_path = self.display_file_path(context.section_slug, display_name)

        return "".join(
            [
                context.service.shell_command_markup(f"stat {display_name}", cwd=cwd),
                context.service.stat_row("File", file_path),
                context.service.stat_row("Size", str(context.localized_meta.get("byteSize") or 0)),
                context.service.stat_row("Blocks", "8"),
                context.service.stat_row("IO", "4096 regular file"),
                context.service.stat_row("Device", "autophanyfs"),
                context.service.stat_row("Inode", "021"),
                context.service.stat_row("Links", "1"),
                context.service.stat_row("Access", "(0664/-rw-rw-r--)"),
                context.service.stat_row("Uid", "(0/root)"),
                context.service.stat_row("Gid", "(42/operators)"),
                context.service.stat_row("Birth", stamp),
                context.service.stat_row("Mtime", stamp),
                '<span class="meta-rule" aria-hidden="true"></span>',
                context.service.stat_row("name", display_name),
                context.service.stat_row("lang", context.lang),
                context.service.stat_row("langs", ", ".join(context.item.get("languages", []))),
                context.service.stat_row("type", str(context.item.get("type") or FileType.PAGE)),
                context.service.stat_row("format", str(context.item.get("format") or "text")),
            ]
        )

    @staticmethod
    def display_file_path(section: str, slug: str) -> str:
        return f"~/{slug}" if section == SYSTEM_SECTION else f"~/{section}/{slug}"

    def validate_item(self, _: content.Section, item: content.Item) -> None:
        return None
