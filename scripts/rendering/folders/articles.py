"""Article index folder renderer"""

from __future__ import annotations

import html
from typing import Any, override

from ... import routes
from ...config import FileType, FolderType
from ..context import FolderContext
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
            list_title=html.escape(self.title(context)),
            search_placeholder=html.escape(context.ui["search_placeholder"]),
            sort_label=html.escape(context.ui["sort_label"]),
            size_label=html.escape(context.ui["size_label"]),
            date_desc_label=html.escape(context.ui["date_desc_label"]),
            date_asc_label=html.escape(context.ui["date_asc_label"]),
            title_asc_label=html.escape(context.ui["title_asc_label"]),
            title_desc_label=html.escape(context.ui["title_desc_label"]),
            items_html=self.render_article_cards(items, context.lang),
            pager_class="pager-row hidden" if total_pages <= 1 else "pager-row",
            page_prev=html.escape(context.ui["page_prev"]),
            page_next=html.escape(context.ui["page_next"]),
            page_info=html.escape(f"1/{total_pages}"),
        )

    @override
    def process_html(self, context: FolderContext) -> str:
        items, total_pages = self.paginate(context.items, context.lang, context.page_size)
        return self.list_process_html(context, min(context.page_size, len(items)), len(items), total_pages)

    @staticmethod
    def paginate(items: list[dict[str, Any]], lang: str, page_size: int) -> tuple[list[dict[str, Any]], int]:
        localized_items = [item for item in items if lang in item.get("languages", [])]
        sorted_items = sorted(
            localized_items,
            key=lambda item: (
                str(item.get("date") or ""),
                str(item.get("title", {}).get(lang) or item.get("slug") or ""),
            ),
            reverse=True,
        )

        total_pages = max(1, (len(sorted_items) + page_size - 1) // page_size)
        return sorted_items, total_pages

    @staticmethod
    def render_article_cards(articles: list[dict[str, Any]], lang: str) -> str:
        rows = []
        for article in articles:
            slug = str(article["slug"])
            href = routes.generated_item_route(article, lang)
            title = str(article.get("title", {}).get(lang) or slug)
            description = str(article.get("description", {}).get(lang) or "")
            tags = " ".join(
                f'<span class="inline-tag">#{html.escape(str(tag))}</span>' for tag in article.get("tags", [])
            )
            search = " ".join(
                filter(
                    None,
                    [
                        slug,
                        title,
                        description,
                        str(article.get("date") or ""),
                        *(str(tag) for tag in article.get("tags", [])),
                    ],
                )
            ).lower()
            rows.append(
                f'<li class="article-card" data-list-item data-search="{html.escape(search, quote=True)}" data-sort-title="{html.escape(title.lower(), quote=True)}" data-sort-date="{html.escape(str(article.get("date") or ""), quote=True)}"><a class="article-card-link article-card-full" href="{html.escape(href, quote=True)}" data-internal="true"><strong>{html.escape(title)}</strong><div class="meta">{html.escape(str(article.get("date") or ""))} · {html.escape(description)}</div><div class="meta tag-line">{tags}</div></a></li>'
            )
        else:
            return "".join(rows)

    @staticmethod
    def list_process_html(
        context: FolderContext, visible_items: int, total_items: int, total_pages: int, tag: str | None = None
    ) -> str:
        cwd = context.service.cwd_for_section(context.section_slug)
        scope = f"tag:{tag}" if tag else context.section_slug
        return "".join(
            [
                context.service.shell_command_markup("statfs ~", cwd=cwd),
                context.service.stat_row("File system", "autophanyfs"),
                context.service.stat_row("Mounted on", f"/{context.lang}/{context.section_slug}"),
                context.service.stat_row("Type", "section"),
                context.service.stat_row("Flags", "ro, localized, indexed"),
                '<span class="meta-rule" aria-hidden="true"></span>',
                context.service.stat_row("mode", context.section_slug),
                context.service.stat_row("lang", context.lang),
                context.service.stat_row("scope", scope),
                context.service.stat_row_html("shown", f'<span data-process-field="shown">{visible_items}</span>'),
                context.service.stat_row_html("total", f'<span data-process-field="total">{total_items}</span>'),
                context.service.stat_row_html("page", '<span data-process-field="page">1</span>'),
                context.service.stat_row_html("pages", f'<span data-process-field="pages">{total_pages}</span>'),
            ]
        )
