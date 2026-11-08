"""Base folder renderer contract and shared section behavior"""

from __future__ import annotations

from typing import Any

from ... import content, generated, routes
from ...config import FileType, FolderType
from ...localization import exact_text
from ..context import FolderContext, ListShellContext, RouteRender, Stat


class FolderRenderer:
    folder_type = FolderType.FILES
    expected_file_type: FileType | None = None

    def command(self, _: FolderContext) -> str:
        return "ls -l -p | grep -v /"

    def stage_html(self, context: FolderContext) -> str:
        return context.templates.render(
            f"folders/{self.folder_type.value}.html",
            rows=self.file_rows(context.items, context.lang),
        )

    def file_rows(self, items: list[dict[str, Any]], lang: str) -> list[dict[str, str]]:
        rows = []
        for item in items:
            slug = str(item["slug"])
            label = exact_text(item.get("label"), lang) or slug
            rows.append(
                {
                    "href": routes.generated_item_route(item, lang),
                    "slug": slug,
                    "label": label,
                    "description": exact_text(item.get("description"), lang),
                    "date": str(item.get("date") or "----------"),
                }
            )
        return rows

    def title(self, context: FolderContext) -> str:
        return context.service.localized(
            context.section.get("title"), context.lang, f"sections.{context.section_slug}.title"
        )

    def description(self, context: FolderContext) -> str:
        return context.service.localized(
            context.section.get("description"), context.lang, f"sections.{context.section_slug}.description"
        )

    def process(self, context: FolderContext) -> list[Stat]:
        return self.base_stats(context) + self.extra_stats(context)

    def base_stats(self, context: FolderContext) -> list[Stat]:
        items = context.items
        languages = sorted({item_lang for item in items for item_lang in item.get("languages", [])})
        translated = sum(1 for item in items if context.lang in item.get("languages", []))

        return [
            Stat("File system", "cray-1"),
            Stat(
                "Mounted on",
                f"/{context.lang}" if context.section.get("system") else f"/{context.lang}/{context.section_slug}",
            ),
            Stat("Type", "system-section" if context.section.get("system") else "section"),
            Stat("Flags", "ro, localized, indexed"),
            Stat("", rule=True),
            Stat("mode", context.section_slug if not context.section.get("system") else "home"),
            Stat("lang", context.lang),
            Stat("files", str(len(items))),
            Stat("languages", ", ".join(languages) or context.lang),
            Stat("translated", f"{translated}/{len(items)}"),
        ]

    def extra_stats(self, _: FolderContext) -> list[Stat]:
        return []

    def page_count(self, _: FolderContext) -> int:
        return 1

    def indexable(self, context: FolderContext) -> bool:
        return any(context.lang in item.get("languages", []) for item in context.items)

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
                process=self.process(context),
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
                page=shell,
                indexable=self.indexable(context),
                page_count=self.page_count(context),
            )
        ]

    def extra_pages(self, _: FolderContext) -> list[RouteRender]:
        return []

    def validate_item_membership(self, section: content.Section, item: content.Item, file_type: FileType) -> None:
        if self.expected_file_type and file_type != self.expected_file_type:
            raise RuntimeError(
                f'Section `{section.slug}` items must set `type: "{self.expected_file_type.value}"` in {item.path / f"{item.slug}.meta"}'
            )
