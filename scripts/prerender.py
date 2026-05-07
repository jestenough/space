"""
Static route prerendering step.

Creates SEO-friendly HTML files for localized routes after Vite build,
while preserving Vite-generated JS and CSS assets in the document head.
"""

from __future__ import annotations

import html
import logging
import re
from pathlib import Path
from typing import Any

from . import generated, routes
from .config import (
    ARTICLE_TYPE,
    ARTICLES_SECTION,
    DEFAULT_LANG,
    DIST_DIR,
    GENERATED_FILES_DIR,
    GENERATED_SITE_META_PATH,
    HOME_PAGE,
    SITE_URL,
    TAG_PAGE,
    TAGS_SECTION,
)
from .jsonio import read_json
from .localization import strict_text


logger = logging.getLogger(__name__)


class Prerender:
    article_content_re = re.compile(
        r'<div\s+id=["\']article-content["\'][^>]*>[\s\S]*?</div>',
        re.IGNORECASE,
    )

    runtime_head_tag_re = re.compile(
        r'^\s*(?:'
        r'<script\b(?=[^>]*\bsrc=)[^>]*></script>|'
        r'<link\b(?=[^>]*\brel=["\'](?:stylesheet|modulepreload|preload)["\'])[^>]*>'
        r')\s*$',
        re.IGNORECASE | re.MULTILINE,
    )

    def run(self) -> None:
        base_html = self.read_text(DIST_DIR / "index.html")
        site_meta = read_json(GENERATED_SITE_META_PATH)
        sections = generated.sections()
        files = generated.items(sections)
        articles = [item for item in files if item.get("type") == ARTICLE_TYPE]
        languages = generated.item_languages(files)
        tags_by_lang = self.collect_tags_by_lang(articles)

        self.render_root(base_html, site_meta, languages)
        self.render_language_pages(base_html, site_meta, languages)
        self.render_section_pages(base_html, sections)
        self.render_file_pages(base_html, sections)
        self.render_article_index_pages(base_html, site_meta, languages)
        self.render_tag_index_pages(base_html, site_meta, languages)
        self.render_article_pages(base_html, articles)
        self.render_tag_pages(base_html, site_meta, tags_by_lang)

        total_tags = sum(len(tags) for tags in tags_by_lang.values())

        logger.info("Prerendered %s section(s), %s article(s) and %s localized tag page(s).", len(sections), len(articles), total_tags)

    def render_section_pages(self, base_html: str, sections: list[dict[str, Any]]) -> None:
        for section in sections:
            if section.get("system"):
                continue
            for lang in generated.section_languages(section):
                route = routes.generated_section_route(section, lang)
                self.write_route(
                    route,
                    self.render_page(
                        base_html=base_html,
                        lang=lang,
                        title=self.localized(section.get("title"), lang, f"sections.{section.get('slug')}.title"),
                        description=self.localized(section.get("description"), lang, f"sections.{section.get('slug')}.description"),
                        canonical_path=route,
                        alternates=self.section_alternates(section),
                        og_type="website",
                    ),
                )

    def render_file_pages(self, base_html: str, sections: list[dict[str, Any]]) -> None:
        for section in sections:
            section_slug = str(section["slug"])
            for item in generated.section_items(section_slug):
                if item.get("type") == ARTICLE_TYPE:
                    continue
                for lang in item.get("languages", []):
                    route = routes.generated_item_route(item, lang)
                    content = self.read_text(GENERATED_FILES_DIR / section_slug / f"{item['slug']}.{lang}.html")
                    self.write_route(
                        route,
                        self.render_page(
                            base_html=base_html,
                            lang=lang,
                            title=self.localized(item.get("title"), lang, f"{section_slug}.{item.get('slug')}.title"),
                            description=self.localized(item.get("description"), lang, f"{section_slug}.{item.get('slug')}.description"),
                            canonical_path=route,
                            alternates=self.item_alternates(item),
                            article_html=content,
                            og_type="website",
                        ),
                    )

    def render_root(self, base_html: str, site_meta: dict[str, Any], languages: list[str]) -> None:
        lang = DEFAULT_LANG
        page_meta = self.page_meta(site_meta, HOME_PAGE, lang)

        self.write_route(
            "/",
            self.render_page(
                base_html=base_html,
                lang=lang,
                title=page_meta["title"],
                description=page_meta["description"],
                canonical_path="/",
                alternates=self.localized_alternates(languages, lambda item_lang: f"/{item_lang}"),
                og_type="website",
            ),
        )

    def render_language_pages(self, base_html: str, site_meta: dict[str, Any], languages: list[str]) -> None:
        for lang in languages:
            page_meta = self.page_meta(site_meta, HOME_PAGE, lang)

            self.write_route(
                f"/{lang}",
                self.render_page(
                    base_html=base_html,
                    lang=lang,
                    title=page_meta["title"],
                    description=page_meta["description"],
                    canonical_path=f"/{lang}",
                    alternates=self.localized_alternates(languages, lambda item_lang: f"/{item_lang}"),
                    og_type="website",
                ),
            )

    def render_article_index_pages(
        self,
        base_html: str,
        site_meta: dict[str, Any],
        languages: list[str],
    ) -> None:
        for lang in languages:
            page_meta = self.page_meta(site_meta, ARTICLES_SECTION, lang)

            self.write_route(
                routes.section_route(ARTICLES_SECTION, lang),
                self.render_page(
                    base_html=base_html,
                    lang=lang,
                    title=page_meta["title"],
                    description=page_meta["description"],
                    canonical_path=routes.section_route(ARTICLES_SECTION, lang),
                    alternates=self.localized_alternates(
                        languages,
                        lambda item_lang: routes.section_route(ARTICLES_SECTION, item_lang)
                    ),
                    og_type="website",
                ),
            )

    def render_tag_index_pages(self, base_html: str, site_meta: dict[str, Any], languages: list[str]) -> None:
        for lang in languages:
            page_meta = self.page_meta(site_meta, TAGS_SECTION, lang)

            self.write_route(
                routes.section_route(TAGS_SECTION, lang),
                self.render_page(
                    base_html=base_html,
                    lang=lang,
                    title=page_meta["title"],
                    description=page_meta["description"],
                    canonical_path=routes.section_route(TAGS_SECTION, lang),
                    alternates=self.localized_alternates(
                        languages,
                        lambda item_lang: routes.section_route(TAGS_SECTION, item_lang)
                    ),
                    og_type="website",
                ),
            )

    def render_article_pages(
        self,
        base_html: str,
        articles: list[dict[str, Any]],
    ) -> None:
        for article in articles:
            slug = article["slug"]

            for lang in article["languages"]:
                article_html = self.read_text(GENERATED_FILES_DIR / str(article["section"]) / f"{slug}.{lang}.html")

                self.write_route(
                    routes.generated_item_route(article, lang),
                    self.render_page(
                        base_html=base_html,
                        lang=lang,
                        title=article["title"][lang],
                        description=article["description"][lang],
                        canonical_path=routes.generated_item_route(article, lang),
                        alternates=self.article_alternates(article),
                        article_html=article_html,
                        og_type="article",
                    ),
                )

    def render_tag_pages(
        self,
        base_html: str,
        site_meta: dict[str, Any],
        tags_by_lang: dict[str, set[str]],
    ) -> None:
        for lang, tags in tags_by_lang.items():
            for tag in sorted(tags):
                page_meta = self.tag_page_meta(site_meta, lang, tag)

                self.write_route(
                    routes.tag_route(lang, tag),
                    self.render_page(
                        base_html=base_html,
                        lang=lang,
                        title=page_meta["title"],
                        description=page_meta["description"],
                        canonical_path=routes.tag_route(lang, tag),
                        alternates=self.tag_alternates(tag, tags_by_lang),
                        og_type="website",
                    ),
                )

    def render_page(
        self,
        base_html: str,
        lang: str,
        title: str,
        description: str,
        canonical_path: str,
        alternates: dict[str, str],
        og_type: str,
        article_html: str | None = None,
    ) -> str:
        head = self.render_head(
            lang=lang,
            title=title,
            description=description,
            canonical_path=canonical_path,
            alternates=alternates,
            og_type=og_type,
        )

        page = self.inject_head(base_html, head)

        if article_html is not None:
            page = self.inject_article_content(page, article_html)

        return page

    def render_head(
        self,
        lang: str,
        title: str,
        description: str,
        canonical_path: str,
        alternates: dict[str, str],
        og_type: str,
    ) -> str:
        canonical_url = self.absolute_url(canonical_path)

        lines = [
            '    <meta charset="UTF-8" />',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />',
            '    <meta name="robots" content="index,follow" />',
            f"    <title>{html.escape(title)}</title>",
            f'    <meta name="description" content="{html.escape(description, quote=True)}" />',
            f'    <link rel="canonical" href="{html.escape(canonical_url, quote=True)}" />',
            f'    <meta property="og:title" content="{html.escape(title, quote=True)}" />',
            f'    <meta property="og:description" content="{html.escape(description, quote=True)}" />',
            f'    <meta property="og:url" content="{html.escape(canonical_url, quote=True)}" />',
            f'    <meta property="og:type" content="{html.escape(og_type, quote=True)}" />',
            f'    <meta property="og:locale" content="{html.escape(lang, quote=True)}" />',
        ]

        for hreflang, path in alternates.items():
            lines.append(
                f'    <link rel="alternate" hreflang="{html.escape(hreflang, quote=True)}" '
                f'href="{html.escape(self.absolute_url(path), quote=True)}" />'
            )

        return "\n".join(lines)

    @classmethod
    def inject_head(cls, base_html: str, head: str) -> str:
        runtime_tags = cls.extract_runtime_head_tags(base_html)
        full_head = f"{head}\n{runtime_tags}" if runtime_tags else head

        return re.sub(
            r"<head>[\s\S]*?</head>",
            f"<head>\n{full_head}\n  </head>",
            base_html,
            count=1,
            flags=re.IGNORECASE,
        )

    @classmethod
    def extract_runtime_head_tags(cls, base_html: str) -> str:
        match = re.search(r"<head>([\s\S]*?)</head>", base_html, re.IGNORECASE)

        if not match:
            return ""

        return "\n".join(
            item.group(0).strip()
            for item in cls.runtime_head_tag_re.finditer(match.group(1))
        )

    @classmethod
    def inject_article_content(cls, page: str, article_html: str) -> str:
        replacement = f'<div id="article-content">\n{article_html}\n</div>'

        if not cls.article_content_re.search(page):
            raise RuntimeError("Cannot find #article-content placeholder in base HTML")

        return cls.article_content_re.sub(lambda _: replacement, page, count=1)

    def page_meta(self, site_meta: dict[str, Any], page: str, lang: str) -> dict[str, str]:
        pages = site_meta.get("pages")

        if not isinstance(pages, dict) or page not in pages:
            raise RuntimeError(f"Missing site metadata page: {page}")

        data = pages[page]

        return {
            "title": self.localized(data.get("title"), lang, f"pages.{page}.title"),
            "description": self.localized(
                data.get("description"),
                lang,
                f"pages.{page}.description",
            ),
        }

    def tag_page_meta(
        self,
        site_meta: dict[str, Any],
        lang: str,
        tag: str,
    ) -> dict[str, str]:
        data = site_meta.get("pages", {}).get(TAG_PAGE)

        if not isinstance(data, dict):
            raise RuntimeError(f"Missing site metadata page: {TAG_PAGE}")

        return {
            "title": self.localized(data.get("title"), lang, f"pages.{TAG_PAGE}.title").format(tag=tag),
            "description": self.localized(
                data.get("description"),
                lang,
                f"pages.{TAG_PAGE}.description",
            ).format(tag=tag),
        }

    @staticmethod
    def localized(value: Any, lang: str, path: str) -> str:
        return strict_text(value, lang, path)

    @staticmethod
    def localized_alternates(languages: list[str], route_factory) -> dict[str, str]:
        return routes.alternates(languages, route_factory)

    @staticmethod
    def article_alternates(article: dict[str, Any]) -> dict[str, str]:
        return routes.alternates(article["languages"], lambda lang: routes.generated_item_route(article, lang))

    @staticmethod
    def tag_alternates(tag: str, tags_by_lang: dict[str, set[str]]) -> dict[str, str]:
        alternates = {
            lang: routes.tag_route(lang, tag)
            for lang, tags in tags_by_lang.items()
            if tag in tags
        }

        alternates["x-default"] = alternates.get(DEFAULT_LANG) or next(iter(alternates.values()))
        return alternates

    @staticmethod
    def collect_tags_by_lang(articles: list[dict[str, Any]]) -> dict[str, set[str]]:
        tags_by_lang = {lang: set() for lang in generated.item_languages(articles)}

        for article in articles:
            for lang in article["languages"]:
                for tag in article["tags"]:
                    tags_by_lang[lang].add(tag)

        return tags_by_lang

    @staticmethod
    def item_alternates(item: dict[str, Any]) -> dict[str, str]:
        return routes.alternates(item.get("languages", []), lambda lang: routes.generated_item_route(item, lang))

    @staticmethod
    def section_alternates(section: dict[str, Any]) -> dict[str, str]:
        return routes.alternates(generated.section_languages(section), lambda lang: routes.generated_section_route(section, lang))

    @staticmethod
    def absolute_url(path: str) -> str:
        return f"{SITE_URL.rstrip('/')}/{path.lstrip('/')}"

    @staticmethod
    def read_text(path: Path) -> str:
        if not path.is_file():
            raise RuntimeError(f"Missing file: {path}")

        return path.read_text(encoding="utf-8")

    @staticmethod
    def write_route(route: str, content: str) -> None:
        if route == "/":
            path = DIST_DIR / "index.html"
        else:
            path = DIST_DIR / route.strip("/") / "index.html"

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def run() -> None:
    Prerender().run()
