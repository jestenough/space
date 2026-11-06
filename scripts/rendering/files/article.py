"""Article file renderer"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from ... import content, generated, routes
from ...config import DEFAULT_LANG, SYSTEM_SECTION, WORDS_PER_MINUTE, ContentExtension, FileType, FolderType
from ...localization import exact_text, strict_text
from ..context import (
    FileIndexContext,
    FilePageContext,
    FileShellContext,
    LocalizedMetaContext,
    RouteRender,
    SourceRenderContext,
    Stat,
)
from .. import code
from ..head import Head
from .base import FileRenderer

BYLINE_UI = {
    DEFAULT_LANG: {"author": "Author", "coauthors": "Co-Authors"},
    "ru": {"author": "Автор", "coauthors": "Соавторы"},
}


class ArticleFileRenderer(FileRenderer):
    file_type = FileType.ARTICLE
    bibtex_key_re = re.compile(r"[^a-z0-9]+")

    def index_meta(self, context: FileIndexContext) -> dict[str, Any]:
        author, coauthors = self.article_people(
            context.item.meta,
            context.item.path / f"{context.item.slug}.meta",
        )
        canonical_lang = DEFAULT_LANG if DEFAULT_LANG in context.languages else context.languages[0]
        return {
            "tags": self.string_list(context.item.meta.get("tags", []), f"{context.item.slug}.tags"),
            "author": author,
            "coAuthors": coauthors,
            "tagSection": context.tag_section_slug,
            "pdfPath": f"{routes.item_route(context.section, canonical_lang, context.item.slug)}.pdf",
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
        body = code.decorate(
            context.convert_tex_to_html(source.path, item.path, item.section, item.slug, source.lang),
            source.lang,
        )
        byline = context.templates.render(
            "parts/byline.html", **self.byline_data(item.meta, source.lang, item.path / f"{item.slug}.meta")
        )
        return context.templates.render(
            "files/article_body.html", lang=source.lang, byline=byline, content=body
        )

    def render_page(self, context: FilePageContext) -> RouteRender:
        article_html = context.content_html
        tag_section = (
            context.tag_section_slug
            or generated.first_section_slug(context.sections, FolderType.TAGS)
            or context.section_slug
        )
        decorated_html = context.templates.render(
            "parts/article_nav.html",
            content=article_html,
            **self.nav_data(context.lang, context.item, tag_section),
        )
        toc = self.render_toc(article_html)
        cite_value = self.tex_citation(context.item, context.lang)
        article_images = context.service.extract_content_images(article_html)
        schema = self.schema(context.item, context.lang, article_images)
        title = context.item["title"][context.lang]
        description = context.item["description"][context.lang]
        shell = context.service.file_shell(
            FileShellContext(
                lang=context.lang,
                sections=context.sections,
                file_type=FileType.ARTICLE,
                active_section=None if context.section.get("system") else context.section_slug,
                welcome_title=title,
                welcome_lead=description,
                welcome_command=f"sed -n '1,2p' {context.item_slug}.meta",
                render_command=f"cat {context.item_slug}.tex",
                process_command=f"stat {context.item_slug}.tex",
                process=self.process(context),
                content_html=decorated_html,
                back_href=routes.generated_section_route(context.section, context.lang),
                download_text="pdf",
                download_href=routes.generated_pdf_route(context.item, context.lang),
                cite_value=cite_value,
                edit_href=context.service.edit_href(context.localized_meta),
                show_cite=True,
                show_edit=True,
                show_zen=True,
                toc=toc,
                show_toc=bool(toc),
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
            page=shell,
            images=tuple(article_images),
            json_ld=schema,
        )

    def process(self, context: FilePageContext) -> list[Stat]:  # type: ignore[override]
        stamp = f"{context.item.get('date') or '1970-01-01'} 00:00:00 +0000"
        file_path = (
            f"~/{context.item['slug']}.tex"
            if context.section.get("system")
            else f"~/{context.item['section']}/{context.item['slug']}.tex"
        )
        tag_section = str(context.item.get("tagSection") or context.item["section"])
        tags = tuple(
            {
                "href": routes.tag_route(tag_section, context.lang, str(tag)),
                "label": f"#{tag}",
            }
            for tag in context.item.get("tags", [])
        )
        return [
            Stat("File", file_path),
            Stat("Size", str(context.localized_meta.get("byteSize") or 0)),
            Stat("Blocks", "8"),
            Stat("IO", "4096 regular file"),
            Stat("Inode", "042"),
            Stat("Access", "(0664/-rw-rw-r--)"),
            Stat("Uid", "(1000/guest)"),
            Stat("Gid", "(1000/guest)"),
            Stat("Birth", stamp),
            Stat("Mtime", stamp),
            Stat("", rule=True),
            Stat("slug", str(context.item["slug"])),
            Stat("lang", context.lang),
            Stat("langs", ", ".join(context.item.get("languages", []))),
            Stat("tags", tags=tags),
            Stat("words", str(context.localized_meta.get("wordCount") or 0)),
            Stat("chars", str(context.localized_meta.get("charCount") or 0)),
            Stat(
                "pdf",
                str(context.localized_meta.get("pdfPath") or routes.generated_pdf_route(context.item, context.lang)),
            ),
        ]

    def validate_item(self, _: content.Section, item: content.Item) -> None:
        for source in item.sources:
            if source.ext != ContentExtension.TEX:
                raise RuntimeError(
                    f"Article item `{item.section}/{item.slug}` has non-TeX source: {source.path}\nItems with type `{FileType.ARTICLE.value}` must use .tex sources only."
                )

        self.check_tags(item.meta.get("tags"), item.path / f"{item.slug}.meta")
        self.article_people(item.meta, item.path / f"{item.slug}.meta")

    def schema(self, article: dict[str, Any], lang: str, images: list[dict[str, str]]) -> dict[str, Any]:
        image_urls = [url for image in images if (url := Head.image_url(image.get("src")))]
        payload: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": strict_text(
                article.get("title"), lang, f"{article.get('section')}.{article.get('slug')}.title"
            ),
            "description": strict_text(
                article.get("description"), lang, f"{article.get('section')}.{article.get('slug')}.description"
            ),
            "datePublished": article.get("date") or "",
            "dateModified": article.get("date") or "",
            "inLanguage": lang,
            "mainEntityOfPage": routes.absolute_url(routes.generated_item_route(article, lang)),
            "url": routes.absolute_url(routes.generated_item_route(article, lang)),
        }

        people = [article.get("author"), *article.get("coAuthors", [])]
        authors = []
        for person in people:
            if not isinstance(person, dict) or not person.get("name"):
                continue
            author: dict[str, str] = {"@type": "Person", "name": str(person["name"])}
            if person.get("url"):
                author["url"] = str(person["url"])
            authors.append(author)
        if authors:
            payload["author"] = authors

        if image_urls:
            payload["image"] = image_urls

        return payload

    def tex_citation(self, article: dict[str, Any], lang: str) -> str:
        title = strict_text(
            article.get("title"), lang, f"{article.get('section')}.{article.get('slug')}.title"
        )
        year = str(article.get("date") or "").split("-", 1)[0] or "n.d."
        article_url = routes.absolute_url(routes.generated_item_route(article, lang))
        access_date = datetime.now(UTC).date().isoformat()
        key = f"autophany-{self.bibtex_key(str(article['slug']))}-{self.bibtex_key(lang)}"

        lines = [f"@misc{{{key},", f"  title = {{{self.escape_tex(title)}}},"]
        people = [article.get("author"), *article.get("coAuthors", [])]
        authors = [str(person["name"]) for person in people if isinstance(person, dict) and person.get("name")]
        if authors:
            lines.append(f"  author = {{{self.escape_tex(' and '.join(authors))}}},")
        lines.extend(
            [
                f"  year = {{{self.escape_tex(year)}}},",
                f"  howpublished = {{\\url{{{article_url}}}}},",
                f"  note = {{{self.escape_tex(f'Article on autophany.space; accessed {access_date}')}}},",
                f"  language = {{{self.escape_tex(lang)}}},",
                "}",
            ]
        )
        return "\n".join(lines)

    @classmethod
    def bibtex_key(cls, value: str) -> str:
        return cls.bibtex_key_re.sub("-", value.lower()).strip("-") or "item"

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
    def nav_data(lang: str, article: dict[str, Any], tag_section: str) -> dict[str, Any]:
        section_slug = str(article["section"])
        neighbors = []
        for key, label in (("prev", "previous"), ("next", "next")):
            value = article.get(key)
            if isinstance(value, dict) and value.get("path") and value.get("title"):
                neighbors.append({"href": str(value["path"]), "label": f"{label}: {value['title']}"})

        return {
            "lang": lang,
            "slug": str(article["slug"]),
            "section": section_slug,
            "section_href": routes.section_route(section_slug, lang),
            "tags": [
                {
                    "href": routes.tag_route(tag_section, lang, str(tag)),
                    "label": f"#{tag}",
                }
                for tag in article.get("tags", [])
            ],
            "pdf_href": routes.generated_pdf_route(article, lang),
            "neighbors": neighbors,
        }

    @classmethod
    def byline_data(cls, meta: dict[str, Any], lang: str, path: object) -> dict[str, Any]:
        ui = BYLINE_UI.get(lang)
        if ui is None:
            raise RuntimeError(
                f"Missing article byline translations for language `{lang}` in scripts/rendering/files/article.py"
            )

        author, coauthors = cls.article_people(meta, path)
        return {
            "author": author,
            "coauthors": coauthors,
            "labels": {"author": ui["author"], "coauthors": ui["coauthors"]},
        }

    @classmethod
    def article_people(cls, meta: dict[str, Any], path: object) -> tuple[dict[str, str], list[dict[str, str]]]:
        author = cls.person(meta.get("author"), f"{path}: author")
        raw_coauthors = meta.get("coAuthors")
        if not isinstance(raw_coauthors, list):
            raise RuntimeError(f"{path}: `coAuthors` must be an array of author objects")

        coauthors = [cls.person(value, f"{path}: coAuthors[{index}]") for index, value in enumerate(raw_coauthors)]
        names = [author["name"], *(person["name"] for person in coauthors)]
        if len(set(names)) != len(names):
            raise RuntimeError(f"{path}: author and co-author names must be unique")
        return author, coauthors

    @staticmethod
    def person(value: Any, path: str) -> dict[str, str]:
        if not isinstance(value, dict):
            raise RuntimeError(f"{path} must be an object with a non-empty `name` and optional `url`")

        name = value.get("name")
        if not isinstance(name, str) or not name.strip():
            raise RuntimeError(f"{path}.name must be a non-empty string")

        person = {"name": name.strip()}
        url = value.get("url")
        if url is not None:
            if not isinstance(url, str) or not url.strip():
                raise RuntimeError(f"{path}.url must be a non-empty string when present")
            normalized_url = url.strip()
            if not (
                normalized_url.startswith(("https://", "http://", "mailto:"))
                or (normalized_url.startswith("/") and not normalized_url.startswith("//"))
            ):
                raise RuntimeError(f"{path}.url must be an absolute http(s), mailto, or root-relative URL")
            person["url"] = normalized_url
        return person

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
