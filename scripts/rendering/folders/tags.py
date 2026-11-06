"""Tags index and tag detail folder renderer"""

from __future__ import annotations

from typing import Any, override

from ... import generated, routes
from ...config import FileType, FolderType
from ..context import FolderContext, ListShellContext, RouteRender, Stat
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
    def process(self, context: FolderContext) -> list[Stat]:
        tags = self.tag_counts(context.all_items, context.lang)
        page_items, total_pages = self.paginate(tags, context.page_size)

        return ArticlesFolderRenderer.list_process(
            context, min(context.page_size, len(page_items)), len(page_items), total_pages
        )

    @override
    def extra_pages(self, context: FolderContext) -> list[RouteRender]:
        pages = []
        articles_by_slug = self.articles_by_slug(context.all_items)
        article_list = list(articles_by_slug.values())
        tags_by_lang = generated.collect_tags_by_lang(article_list)
        tag_articles_by_lang = generated.tag_articles_by_lang(article_list)

        for tag in sorted(tags_by_lang.get(context.lang, set())):
            tag_articles = tag_articles_by_lang.get(context.lang, {}).get(tag, [])
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
                    render_command=f'grep -R "tag:{tag}" . | sort -k 6,7 -r | head -n 4',
                    process=ArticlesFolderRenderer.list_process(
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
                    page=shell,
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
            article_command_base=f'grep -R "tag:{tag}" .' if tag else "",
            list_title=title,
            search_placeholder=context.ui["search_placeholder"],
            sort_label=context.ui["sort_label"],
            size_label=context.ui["size_label"],
            date_desc_label=context.ui["date_desc_label"],
            date_asc_label=context.ui["date_asc_label"],
            title_asc_label=context.ui["title_asc_label"],
            title_desc_label=context.ui["title_desc_label"],
            articles=ArticlesFolderRenderer.cards(articles, context.lang, context.page_size),
            pager_class="pager-row hidden" if article_total_pages <= 1 else "pager-row",
            page_prev=context.ui["page_prev"],
            page_next=context.ui["page_next"],
            page_info=f"1/{article_total_pages}",
            tags_panel_class="panel hidden directory-panel" if tag else "panel directory-panel",
            tags_headline=title,
            tag_search_placeholder=context.ui["tag_search_placeholder"],
            tag_sort_label=context.ui["tag_sort_label"],
            tag_size_label=context.ui["tag_size_label"],
            name_asc_label=context.ui["name_asc_label"],
            name_desc_label=context.ui["name_desc_label"],
            count_desc_label=context.ui["count_desc_label"],
            count_asc_label=context.ui["count_asc_label"],
            tags=self.tag_cards(tags, context.lang, tag, context.section_slug, context.page_size),
            tag_pager_class="pager-row tag-pager-row hidden" if tag_total_pages <= 1 else "pager-row tag-pager-row",
            tag_page_info=f"1/{tag_total_pages}",
        )

    @staticmethod
    def tag_counts(articles: list[dict[str, Any]], lang: str) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for article in articles:
            if str(article.get("type")) != FileType.ARTICLE.value or lang not in article.get("languages", []):
                continue

            for tag in article.get("tags", []):
                counts[str(tag)] = counts.get(str(tag), 0) + 1

        return [{"name": name, "count": count} for name, count in sorted(counts.items(), key=lambda item: item[0])]

    @staticmethod
    def articles_by_slug(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {str(item["slug"]): item for item in items if str(item.get("type")) == FileType.ARTICLE.value}

    @staticmethod
    def paginate(tags: list[dict[str, Any]], page_size: int) -> tuple[list[dict[str, Any]], int]:
        total_pages = max(1, (len(tags) + page_size - 1) // page_size)
        return tags, total_pages

    @staticmethod
    def tag_cards(
        tags: list[dict[str, Any]],
        lang: str,
        active_tag: str | None = None,
        tag_section: str | None = None,
        page_size: int | None = None,
    ) -> list[dict[str, Any]]:
        rows = []
        for index, tag in enumerate(tags):
            name = str(tag["name"])
            rows.append(
                {
                    "href": routes.tag_route(tag_section or "tags", lang, name),
                    "name": name,
                    "count": int(tag["count"]),
                    "active": active_tag == name,
                    "hidden": page_size is not None and index >= page_size,
                }
            )
        return rows

    def tag_title(self, context: FolderContext, tag: str) -> str:
        return context.service.tag_page_meta(context.site_meta, context.lang, tag)["title"]

    def tag_description(self, context: FolderContext, tag: str) -> str:
        return context.service.tag_page_meta(context.site_meta, context.lang, tag)["description"]
