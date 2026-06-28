"""Article file renderer"""

from __future__ import annotations

import html
import json
import re
from datetime import UTC, datetime
from typing import Any

from ... import content, routes
from ...config import SYSTEM_SECTION, WORDS_PER_MINUTE, ContentExtension, FileType, FolderType
from ...localization import exact_text, strict_text
from ..context import (
    FileIndexContext,
    FilePageContext,
    FileShellContext,
    LocalizedMetaContext,
    RouteRender,
    SourceRenderContext,
)
from .base import FileRenderer


class ArticleFileRenderer(FileRenderer):
    file_type = FileType.ARTICLE

    def index_meta(self, context: FileIndexContext) -> dict[str, Any]:
        return {
            "tags": self.string_list(context.item.meta.get("tags", []), f"{context.item.slug}.tags"),
            "tagSection": context.tag_section_slug,
            "pdfPath": f"{routes.item_route(context.section, context.languages[0], context.item.slug)}.pdf",
            "prev": None,
            "next": None,
        }

    def localized_meta(self, context: LocalizedMetaContext) -> dict[str, Any]:
        return {
            "pdfPath": f"{routes.item_route(context.section, context.source.lang, context.item.slug)}.pdf",
            "readingTime": max(1, round(context.stats["words"] / WORDS_PER_MINUTE)),
        }

    def postprocess_indexes(self, indexes: dict[str, list[dict[str, Any]]]) -> None:
        articles = [item for index in indexes.values() for item in index if item.get("type") == FileType.ARTICLE]
        sorted_articles = sorted(articles, key=lambda item: (item.get("date") or "", item["slug"]), reverse=True)
        for index, article in enumerate(sorted_articles):
            previous_article = sorted_articles[index - 1] if index > 0 else None
            next_article = sorted_articles[index + 1] if index + 1 < len(sorted_articles) else None
            article["prev"] = self.neighbor(previous_article, article["languages"]) if previous_article else None
            article["next"] = self.neighbor(next_article, article["languages"]) if next_article else None

    def render_source(self, context: SourceRenderContext) -> str:
        source = context.source
        item = context.item
        body = self.decorate_code_blocks(context.convert_tex_to_html(source.path, item.path, item.section, item.slug), source.lang)
        return f"""<article class="article" lang="{html.escape(source.lang)}">
  <div class="article__content">
{body}
  </div>
</article>
"""

    def render_page(self, context: FilePageContext) -> RouteRender:
        article_html = context.content_html
        tag_section = (
            context.tag_section_slug
            or self.first_section_slug(context.sections, FolderType.TAGS)
            or context.section_slug
        )
        decorated_html = self.decorate_html(context.lang, context.item, article_html, tag_section)
        toc_html = self.render_toc(article_html)
        cite_value = self.tex_citation(context.item, context.lang)
        article_images = context.service.extract_content_images(article_html)
        title = context.item["title"][context.lang]
        description = context.item["description"][context.lang]
        shell = context.service.file_shell(
            FileShellContext(
                lang=context.lang,
                sections=context.sections,
                file_type=FileType.ARTICLE,
                active_section=str(context.item.get("section")),
                welcome_title=title,
                welcome_lead=description,
                welcome_command=f"sed -n '1,2p' {context.item_slug}.meta",
                render_command=f"cat {context.item_slug}.tex",
                process_html=self.process_html(context),
                content_html=decorated_html,
                back_href=routes.section_route(str(context.item["section"]), context.lang),
                download_text="pdf",
                download_href=routes.generated_pdf_route(context.item, context.lang),
                cite_value=cite_value,
                edit_href=context.service.edit_href(context.localized_meta),
                show_cite=True,
                show_edit=True,
                show_zen=True,
                toc_html=toc_html,
                show_toc=bool(toc_html),
            )
        )
        return RouteRender(
            route=routes.generated_item_route(context.item, context.lang),
            lang=context.lang,
            title=title,
            description=description,
            canonical_path=routes.generated_item_route(context.item, context.lang),
            alternates=routes.alternates(
                context.item["languages"], lambda item_lang: routes.generated_item_route(context.item, item_lang)
            ),
            og_type="article",
            shell=shell,
            extra_head=self.head_extras(context.item, context.lang, article_images),
        )

    def process_html(self, context: FilePageContext) -> str:  # type: ignore[override]
        stamp = f"{context.item.get('date') or '1970-01-01'} 00:00:00 +0000"
        cwd = context.service.cwd_for_section(str(context.item["section"]))
        file_name = f"{context.item['slug']}.tex"
        file_path = f"~/{context.item['section']}/{context.item['slug']}.tex"
        tags_html = " ".join(
            f'<a class="meta-tag-link" href="{html.escape(routes.tag_route(str(context.item.get("tagSection") or context.item["section"]), context.lang, str(tag)), quote=True)}" data-internal="true">#{html.escape(str(tag))}</a>'
            for tag in context.item.get("tags", [])
        )
        return "".join(
            [
                context.service.shell_command_markup(f"stat {file_name}", cwd=cwd),
                context.service.stat_row("File", file_path),
                context.service.stat_row("Size", str(context.localized_meta.get("byteSize") or 0)),
                context.service.stat_row("Blocks", "8"),
                context.service.stat_row("IO", "4096 regular file"),
                context.service.stat_row("Inode", "042"),
                context.service.stat_row("Access", "(0664/-rw-rw-r--)"),
                context.service.stat_row("Uid", "(1000/guest)"),
                context.service.stat_row("Gid", "(1000/guest)"),
                context.service.stat_row("Birth", stamp),
                context.service.stat_row("Mtime", stamp),
                '<span class="meta-rule" aria-hidden="true"></span>',
                context.service.stat_row("slug", str(context.item["slug"])),
                context.service.stat_row("lang", context.lang),
                context.service.stat_row("langs", ", ".join(context.item.get("languages", []))),
                context.service.stat_row_html("tags", tags_html),
                context.service.stat_row("words", str(context.localized_meta.get("wordCount") or 0)),
                context.service.stat_row("chars", str(context.localized_meta.get("charCount") or 0)),
                context.service.stat_row(
                    "pdf",
                    str(
                        context.localized_meta.get("pdfPath") or routes.generated_pdf_route(context.item, context.lang)
                    ),
                ),
            ]
        )

    def validate_item(self, _: content.Section, item: content.Item) -> None:
        for source in item.sources:
            if source.ext != ContentExtension.TEX:
                raise RuntimeError(
                    f"Article item `{item.section}/{item.slug}` has non-TeX source: {source.path}\nItems with type `{FileType.ARTICLE.value}` must use .tex sources only."
                )

        self.check_tags(item.meta.get("tags"), item.path / f"{item.slug}.meta")

    def head_extras(self, article: dict[str, Any], lang: str, images: list[dict[str, str]]) -> str:
        lines: list[str] = []

        first_image = images[0] if images else None
        if first_image:
            image_url = routes.absolute_url(first_image["src"])
            lines.append(f'    <meta property="og:image" content="{html.escape(image_url, quote=True)}" />')
            lines.append(f'    <meta name="twitter:image" content="{html.escape(image_url, quote=True)}" />')
            lines.append('    <meta name="twitter:card" content="summary_large_image" />')
            if first_image.get("alt"):
                lines.append(
                    f'    <meta property="og:image:alt" content="{html.escape(first_image["alt"], quote=True)}" />'
                )

        payload: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": strict_text(article.get("title"), lang, f"articles.{article.get('slug')}.title"),
            "description": strict_text(article.get("description"), lang, f"articles.{article.get('slug')}.description"),
            "datePublished": article.get("date") or "",
            "dateModified": article.get("date") or "",
            "inLanguage": lang,
            "mainEntityOfPage": routes.absolute_url(routes.generated_item_route(article, lang)),
            "url": routes.absolute_url(routes.generated_item_route(article, lang)),
        }

        image_urls = [routes.absolute_url(image["src"]) for image in images if image.get("src")]
        if image_urls:
            payload["image"] = image_urls

        lines.append('    <script type="application/ld+json">')
        lines.append(json.dumps(payload, ensure_ascii=False))
        lines.append("    </script>")

        return "\n".join(lines)

    def tex_citation(self, article: dict[str, Any], lang: str) -> str:
        title = strict_text(article.get("title"), lang, f"articles.{article.get('slug')}.title")
        year = str(article.get("date") or "").split("-", 1)[0] or "n.d."
        article_url = routes.absolute_url(routes.generated_item_route(article, lang))
        access_date = datetime.now(UTC).date().isoformat()
        key = f"autophany-{self.bibtex_key(str(article['slug']))}-{self.bibtex_key(lang)}"

        return "\n".join(
            [
                f"@misc{{{key},",
                f"  title = {{{self.escape_tex(title)}}},",
                f"  year = {{{self.escape_tex(year)}}},",
                f"  howpublished = {{\\url{{{article_url}}}}},",
                f"  note = {{{self.escape_tex(f'Article on autophany.space; accessed {access_date}')}}},",
                f"  language = {{{self.escape_tex(lang)}}},",
                "}",
            ]
        )

    @staticmethod
    def bibtex_key(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"

    @staticmethod
    def escape_tex(value: str) -> str:
        replacements = {
            "\\": r"\\textbackslash{}",
            "{": r"\{",
            "}": r"\}",
            "#": r"\#",
            "$": r"\$",
            "%": r"\%",
            "&": r"\&",
            "_": r"\_",
        }

        return "".join(replacements.get(char, char) for char in value)

    @staticmethod
    def decorate_html(lang: str, article: dict[str, Any], article_html: str, tag_section: str) -> str:
        slug = str(article["slug"])
        top_nav = (
            '<nav class="article-breadcrumbs" aria-label="Breadcrumbs">'
            f'<a href="/{html.escape(lang, quote=True)}" data-internal="true">root</a>'
            " / "
            f'<a href="{html.escape(routes.section_route(str(article["section"]), lang), quote=True)}" data-internal="true">articles</a>'
            " / "
            f"<span>{html.escape(slug)}</span>"
            "</nav>"
        )
        tags = " ".join(
            f'<a class="meta-tag-link" href="{html.escape(routes.tag_route(tag_section, lang, str(tag)), quote=True)}" data-internal="true">#{html.escape(str(tag))}</a>'
            for tag in article.get("tags", [])
        )
        files = f'<p class="article-file-links"><a href="{html.escape(routes.generated_pdf_route(article, lang), quote=True)}" target="_blank" rel="noopener noreferrer">download PDF</a></p>'

        neighbors = []
        previous = article.get("prev")
        next_article = article.get("next")
        if isinstance(previous, dict) and previous.get("path") and previous.get("title"):
            neighbors.append(
                f'<a href="{html.escape(str(previous["path"]), quote=True)}" data-internal="true">previous: {html.escape(str(previous["title"]))}</a>'
            )
        if isinstance(next_article, dict) and next_article.get("path") and next_article.get("title"):
            neighbors.append(
                f'<a href="{html.escape(str(next_article["path"]), quote=True)}" data-internal="true">next: {html.escape(str(next_article["title"]))}</a>'
            )
        neighbors_html = f'<p class="article-neighbor-links">{" · ".join(neighbors)}</p>' if neighbors else ""
        bottom_nav = (
            '<nav class="article-seo-links" aria-label="Article links">'
            f'<p class="article-tag-links">tags: {tags}</p>'
            f"{files}"
            f"{neighbors_html}"
            "</nav>"
        )

        return f"{top_nav}{article_html}{bottom_nav}"

    @staticmethod
    def neighbor(article: dict[str, Any] | None, preferred_languages: list[str]) -> dict[str, str] | None:
        if article is None:
            return None
        else:
            lang = next((item for item in preferred_languages if item in article["languages"]), article["languages"][0])
            return {
                "title": exact_text(article["title"], lang),
                "path": routes.item_route(
                    article["section"], lang, article["slug"], article["section"] == SYSTEM_SECTION
                ),
            }

    @staticmethod
    def first_section_slug(sections: list[dict[str, Any]], kind: FolderType) -> str | None:
        for section in sections:
            section_kind = FolderType.SYSTEM if section.get("system") else section.get("kind")
            if section_kind == kind:
                slug = section.get("slug")
                if isinstance(slug, str):
                    return slug
        else:
            return None

    @staticmethod
    def string_list(value: Any, path: str) -> list[str]:
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise RuntimeError(f"{path} must be a string array")
        else:
            return list(dict.fromkeys(item.strip() for item in value))

    @staticmethod
    def check_tags(tags: Any, path: object) -> None:
        if not isinstance(tags, list) or not tags:
            raise RuntimeError(
                f'`tags` must be a non-empty string list in {path}\nExample: "tags": ["notes", "performance"]'
            )

        seen: set[str] = set()
        for tag in tags:
            if not isinstance(tag, str) or not tag.strip():
                raise RuntimeError(f"Tags must be non-empty strings in {path}")

            normalized = tag.strip()
            if normalized in seen:
                raise RuntimeError(f"Duplicate tag `{normalized}` in {path}")

            seen.add(normalized)
