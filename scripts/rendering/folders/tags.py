"""Tags index and tag detail folder renderer"""

from __future__ import annotations

import html
from typing import Any, override

from ... import routes
from ...config import FolderType
from ..context import FolderContext, ListShellContext, RouteRender
from .articles import ArticlesFolderRenderer
from .base import FolderRenderer


class TagsFolderRenderer(FolderRenderer):
    folder_type = FolderType.TAGS

    @override
    def command(self, _: FolderContext) -> str:
        return 'grep -R "tag:" . | cut -d: -f2 | cut -d" " -f1 | sort -f | head -n 4'

    @override
    def stage_html(self, context: FolderContext) -> str:
        tags = self.tag_counts(context.all_items, context.lang)
        page_items, total_pages = self.paginate(tags, context.page_size)

        return self.render_template(
            context, tags=page_items, articles=[], tag=None, article_total_pages=1, tag_total_pages=total_pages
        )

    @override
    def process_html(self, context: FolderContext) -> str:
        tags = self.tag_counts(context.all_items, context.lang)
        page_items, total_pages = self.paginate(tags, context.page_size)

        return ArticlesFolderRenderer.list_process_html(
            context, min(context.page_size, len(page_items)), len(page_items), total_pages
        )

    @override
    def extra_pages(self, context: FolderContext) -> list[RouteRender]:
        pages = []
        articles_by_slug = self.articles_by_slug(context.all_items)

        tags_by_lang = self.collect_tags_by_lang(context.all_items)
        for tag in sorted(tags_by_lang.get(context.lang, set())):
            tag_articles = [
                article
                for article in articles_by_slug.values()
                if context.lang in article.get("languages", []) and tag in article.get("tags", [])
            ]
            page_items, total_pages = ArticlesFolderRenderer.paginate(tag_articles, context.lang, context.page_size)
            title = self.tag_title(context, tag)
            description = self.tag_description(context, tag)
            shell = context.service.list_shell(
                ListShellContext(
                    lang=context.lang,
                    sections=context.sections,
                    active_section=context.section_slug,
                    welcome_title=title,
                    welcome_lead=description,
                    render_command=f'grep -R "tag:{html.escape(tag, quote=True)}" . | sort -k 6,7 -r | head -n 4',
                    process_html=ArticlesFolderRenderer.list_process_html(
                        context, min(context.page_size, len(page_items)), len(page_items), total_pages, tag=tag
                    ),
                    stage_html=self.render_template(
                        context,
                        tags=[],
                        articles=page_items,
                        tag=tag,
                        article_total_pages=total_pages,
                        tag_total_pages=1,
                    ),
                    tag=tag,
                )
            )
            pages.append(
                RouteRender(
                    route=routes.tag_route(context.section_slug, context.lang, tag),
                    lang=context.lang,
                    title=title,
                    description=description,
                    canonical_path=routes.tag_route(context.section_slug, context.lang, tag),
                    alternates=context.service.tag_alternates(context.section_slug, tag, tags_by_lang),
                    og_type="website",
                    shell=shell,
                )
            )
        else:
            return pages

    def render_template(
        self,
        context: FolderContext,
        *,
        tags: list[dict[str, Any]],
        articles: list[dict[str, Any]],
        tag: str | None,
        article_total_pages: int,
        tag_total_pages: int,
    ) -> str:
        title = f"#{tag}" if tag else self.title(context)
        return context.templates.render(
            "folders/tags.html",
            content_panel_class="panel directory-panel" if tag else "panel hidden directory-panel",
            list_title=html.escape(title),
            search_placeholder=html.escape(context.ui["search_placeholder"]),
            sort_label=html.escape(context.ui["sort_label"]),
            size_label=html.escape(context.ui["size_label"]),
            date_desc_label=html.escape(context.ui["date_desc_label"]),
            date_asc_label=html.escape(context.ui["date_asc_label"]),
            title_asc_label=html.escape(context.ui["title_asc_label"]),
            title_desc_label=html.escape(context.ui["title_desc_label"]),
            articles_html=ArticlesFolderRenderer.render_article_cards(articles, context.lang),
            pager_class="pager-row hidden" if article_total_pages <= 1 else "pager-row",
            page_prev=html.escape(context.ui["page_prev"]),
            page_next=html.escape(context.ui["page_next"]),
            page_info=html.escape(f"1/{article_total_pages}"),
            tags_panel_class="panel hidden directory-panel" if tag else "panel directory-panel",
            tags_headline=html.escape(title),
            tag_search_placeholder=html.escape(context.ui["tag_search_placeholder"]),
            tag_sort_label=html.escape(context.ui["tag_sort_label"]),
            tag_size_label=html.escape(context.ui["tag_size_label"]),
            name_asc_label=html.escape(context.ui["name_asc_label"]),
            name_desc_label=html.escape(context.ui["name_desc_label"]),
            count_desc_label=html.escape(context.ui["count_desc_label"]),
            count_asc_label=html.escape(context.ui["count_asc_label"]),
            tags_html=self.render_tags(tags, context.lang, tag, context.section_slug),
            tag_pager_class="pager-row tag-pager-row hidden" if tag_total_pages <= 1 else "pager-row tag-pager-row",
            tag_page_info=html.escape(f"1/{tag_total_pages}"),
        )

    @staticmethod
    def tag_counts(articles: list[dict[str, Any]], lang: str) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for article in articles:
            if article.get("type") != "article" and str(article.get("type")) != "article":
                continue

            if lang not in article.get("languages", []):
                continue

            for tag in article.get("tags", []):
                counts[str(tag)] = counts.get(str(tag), 0) + 1
        else:
            return [{"name": name, "count": count} for name, count in sorted(counts.items(), key=lambda item: item[0])]

    @staticmethod
    def articles_by_slug(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {
            str(item["slug"]): item
            for item in items
            if item.get("type") == "article" or str(item.get("type")) == "article"
        }

    @staticmethod
    def collect_tags_by_lang(items: list[dict[str, Any]]) -> dict[str, set[str]]:
        result: dict[str, set[str]] = {}
        for article in items:
            if article.get("type") != "article" and str(article.get("type")) != "article":
                continue

            tags = [tag for tag in article.get("tags", []) if isinstance(tag, str)]
            for lang in article.get("languages", []):
                if isinstance(lang, str):
                    result.setdefault(lang, set()).update(tags)
        else:
            return result

    @staticmethod
    def paginate(tags: list[dict[str, Any]], page_size: int) -> tuple[list[dict[str, Any]], int]:
        total_pages = max(1, (len(tags) + page_size - 1) // page_size)
        return tags, total_pages

    @staticmethod
    def render_tags(
        tags: list[dict[str, Any]], lang: str, active_tag: str | None = None, tag_section: str | None = None
    ) -> str:
        rows = []
        for tag in tags:
            name = str(tag["name"])
            count = int(tag["count"])
            active = " is-active" if active_tag == name else ""
            href = routes.tag_route(tag_section or "tags", lang, name)
            rows.append(
                f'<li class="tag-card" data-list-item data-search="{html.escape(name.lower(), quote=True)}" data-sort-name="{html.escape(name.lower(), quote=True)}" data-sort-count="{count}"><a class="tag-row{active}" href="{html.escape(href, quote=True)}" data-tag="{html.escape(name, quote=True)}" data-internal="true"><span class="tag-name">#{html.escape(name)}</span><span class="tag-count">{count} file{"" if count == 1 else "s"}</span></a></li>'
            )
        else:
            return "".join(rows)

    def tag_title(self, context: FolderContext, tag: str) -> str:
        return context.service.tag_page_meta(context.site_meta, context.lang, tag)["title"]

    def tag_description(self, context: FolderContext, tag: str) -> str:
        return context.service.tag_page_meta(context.site_meta, context.lang, tag)["description"]
