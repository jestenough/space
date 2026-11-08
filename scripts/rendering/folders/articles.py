"""Article index folder renderer"""

from __future__ import annotations

from typing import Any, override

from ... import routes
from ...config import FileType, FolderType
from ..context import FolderContext, Stat
from .base import FolderRenderer


class ArticlesFolderRenderer(FolderRenderer):
    folder_type = FolderType.ARTICLES
    expected_file_type = FileType.ARTICLE

    @override
    def command(self, _: FolderContext) -> str:
        return "ls -l -p | grep -v / | sort -k 6,7 -r | head -n 4"

    @override
    def stage_html(self, context: FolderContext) -> str:
        items, total_pages = self.paginate(context.items, context.lang, context.page_size)
        return context.templates.render(
            "folders/articles.html",
            list_title=self.title(context),
            search_placeholder=context.ui["search_placeholder"],
            sort_label=context.ui["sort_label"],
            size_label=context.ui["size_label"],
            date_desc_label=context.ui["date_desc_label"],
            date_asc_label=context.ui["date_asc_label"],
            title_asc_label=context.ui["title_asc_label"],
            title_desc_label=context.ui["title_desc_label"],
            cards=self.cards(items, context.lang, context.page_size),
            pager_class="pager-row hidden" if total_pages <= 1 else "pager-row",
            page_prev=context.ui["page_prev"],
            page_next=context.ui["page_next"],
            page_info=f"1/{total_pages}",
        )

    @override
    def page_count(self, context: FolderContext) -> int:
        return self.paginate(context.items, context.lang, context.page_size)[1]

    @override
    def process(self, context: FolderContext) -> list[Stat]:
        items, total_pages = self.paginate(context.items, context.lang, context.page_size)
        return self.list_process(context, min(context.page_size, len(items)), len(items), total_pages)

    @staticmethod
    def paginate(items: list[dict[str, Any]], lang: str, page_size: int) -> tuple[list[dict[str, Any]], int]:
        localized_items = [item for item in items if lang in item.get("languages", [])]
        sorted_items = sorted(
            localized_items,
            key=lambda item: (
                str(item.get("date") or ""),
                str(item.get("label", {}).get(lang) or item.get("title", {}).get(lang) or item.get("slug") or ""),
            ),
            reverse=True,
        )

        total_pages = max(1, (len(sorted_items) + page_size - 1) // page_size)
        return sorted_items, total_pages

    @staticmethod
    def cards(articles: list[dict[str, Any]], lang: str, page_size: int | None = None) -> list[dict[str, Any]]:
        rows = []
        for index, article in enumerate(articles):
            slug = str(article["slug"])
            title = str(article.get("title", {}).get(lang) or slug)
            label = str(article.get("label", {}).get(lang) or title)
            description = str(article.get("description", {}).get(lang) or "")
            tags = [str(tag) for tag in article.get("tags", [])]
            date = str(article.get("date") or "")
            rows.append(
                {
                    "href": routes.generated_item_route(article, lang),
                    "label": label,
                    "description": description,
                    "date": date,
                    "tags": tags,
                    "search": " ".join([slug, label, title, description, date, *tags]).lower(),
                    "hidden": page_size is not None and index >= page_size,
                }
            )
        return rows

    @staticmethod
    def list_process(
        context: FolderContext, visible_items: int, total_items: int, total_pages: int, tag: str | None = None
    ) -> list[Stat]:
        scope = f"tag:{tag}" if tag else context.section_slug
        return [
            Stat("Mounted on", f"/{context.lang}/{context.section_slug}"),
            Stat("Type", "section"),
            Stat("Flags", "ro, localized, indexed"),
            Stat("", rule=True),
            Stat("mode", context.section_slug),
            Stat("lang", context.lang),
            Stat("scope", scope),
            Stat("shown", str(visible_items), field="shown"),
            Stat("total", str(total_items), field="total"),
            Stat("page", "1", field="page"),
            Stat("pages", str(total_pages), field="pages"),
        ]
