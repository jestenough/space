"""Base folder renderer contract and shared section behavior"""

from __future__ import annotations

import html
from typing import Any

from ... import content, generated, routes
from ...config import FileType, FolderType
from ...localization import exact_text
from ..context import FolderContext, ListShellContext, RouteRender


class FolderRenderer:
    folder_type = FolderType.FILES
    expected_file_type: FileType | None = None

    def command(self, _: FolderContext) -> str:
        return "ls -l -p | grep -v /"

    def stage_html(self, context: FolderContext) -> str:
        return context.templates.render(
            f"folders/{self.folder_type.value}.html", items_html=self.render_items(context.items, context.lang)
        )

    def render_items(self, items: list[dict[str, Any]], lang: str) -> str:
        rows = []
        for item in items:
            slug = str(item["slug"])
            href = routes.generated_item_route(item, lang)
            label = exact_text(item.get("label"), lang) or slug
            description = exact_text(item.get("description"), lang)
            date = str(item.get("date") or "----------")
            rows.append(
                f'<li class="info-file-row"><a class="info-file-link" href="{html.escape(href, quote=True)}" data-info-file-slug="{html.escape(slug, quote=True)}" data-internal="true" aria-label="{html.escape(f"{slug}: {description}", quote=True)}"><span class="info-file-perms">-rw-rw-r--  root  {html.escape(date)}</span>  <span class="info-file-name">{html.escape(label or slug)}</span></a></li>'
            )
        return f'<ul class="info-file-tree">{"".join(rows)}</ul>' if rows else ""

    def title(self, context: FolderContext) -> str:
        return context.service.localized(
            context.section.get("title"), context.lang, f"sections.{context.section_slug}.title"
        )

    def description(self, context: FolderContext) -> str:
        return context.service.localized(
            context.section.get("description"), context.lang, f"sections.{context.section_slug}.description"
        )

    def process_html(self, context: FolderContext) -> str:
        rows = (
            self.base_stats(context)
            + self.extra_stats(context)
            + [("index", f"generated/sections/{context.section_slug}.json")]
        )

        return "".join(
            [
                context.service.shell_command_markup(
                    "statfs ~",
                    cwd=context.service.cwd_for_section(
                        None if context.section.get("system") else context.section_slug
                    ),
                ),
                render_stat_rows(context.service, rows),
            ]
        )

    def base_stats(self, context: FolderContext) -> list[tuple[str, str]]:
        items = context.items
        languages = sorted({item_lang for item in items for item_lang in item.get("languages", [])})
        translated = sum(1 for item in items if context.lang in item.get("languages", []))
        raw_files = sum(1 for item in items if item.get("format") != "tex")
        tex_files = sum(1 for item in items if item.get("format") == "tex")
        articles = sum(1 for item in items if item.get("type") == FileType.ARTICLE)
        downloads = sum(1 for item in items if item.get("downloadPath"))

        return [
            ("File system", "autophanyfs"),
            (
                "Mounted on",
                f"/{context.lang}" if context.section.get("system") else f"/{context.lang}/{context.section_slug}",
            ),
            ("Type", "system-section" if context.section.get("system") else "section"),
            ("Flags", "ro, localized, indexed"),
            ("__rule__", ""),
            ("mode", context.section_slug if not context.section.get("system") else "home"),
            ("lang", context.lang),
            ("files", str(len(items))),
            ("languages", ", ".join(languages) or context.lang),
            ("translated", f"{translated}/{len(items)}"),
            ("raw files", str(raw_files)),
            ("tex files", str(tex_files)),
            ("articles", str(articles)),
            ("downloads", str(downloads)),
        ]

    def extra_stats(self, _: FolderContext) -> list[tuple[str, str]]:
        return []

    def pages(self, context: FolderContext) -> list[RouteRender]:
        title = self.title(context)
        description = self.description(context)
        shell = context.service.list_shell(
            ListShellContext(
                lang=context.lang,
                sections=context.sections,
                active_section=None if context.section.get("system") else context.section_slug,
                welcome_title=title,
                welcome_lead=description,
                render_command=self.command(context),
                process_html=self.process_html(context),
                stage_html=self.stage_html(context),
            )
        )
        route = routes.generated_section_route(context.section, context.lang)

        return [
            RouteRender(
                route=route,
                lang=context.lang,
                title=title,
                description=description,
                canonical_path=route,
                alternates=routes.alternates(
                    generated.section_languages(context.section),
                    lambda item_lang: routes.generated_section_route(context.section, item_lang),
                ),
                og_type="website",
                shell=shell,
            )
        ]

    def extra_pages(self, _: FolderContext) -> list[RouteRender]:
        return []

    def validate_item_membership(self, section: content.Section, item: content.Item, file_type: FileType) -> None:
        if self.expected_file_type and file_type != self.expected_file_type:
            raise RuntimeError(
                f'Section `{section.slug}` items must set `type: "{self.expected_file_type.value}"` in {item.path / f"{item.slug}.meta"}'
            )


def render_stat_rows(service: Any, rows: list[tuple[str, str]]) -> str:
    rendered = []
    for key, value in rows:
        rendered.append(
            '<span class="meta-rule" aria-hidden="true"></span>' if key == "__rule__" else service.stat_row(key, value)
        )
    else:
        return "".join(rendered)
