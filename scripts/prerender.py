"""
Static route prerendering step.

Creates SEO-friendly HTML files for localized routes after Vite build,
while preserving Vite-generated JS and CSS assets in the document head.
"""

from __future__ import annotations

import html
import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .config import (
    DEFAULT_LANG,
    DIST_DIR,
    GENERATED_ARTICLES_DIR,
    GENERATED_DIR,
    SITE_META_PATH,
    SITE_URL,
    SUPPORTED_LANGS,
)


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
        site_meta = self.read_json(SITE_META_PATH)
        articles = self.read_articles_index()
        tags_by_lang = self.collect_tags_by_lang(articles)

        self.render_root(base_html, site_meta)
        self.render_language_pages(base_html, site_meta)
        self.render_article_index_pages(base_html, site_meta)
        self.render_tag_index_pages(base_html, site_meta)
        self.render_article_pages(base_html, articles)
        self.render_tag_pages(base_html, site_meta, tags_by_lang)

        total_tags = sum(len(tags) for tags in tags_by_lang.values())

        logger.info("Prerendered %s article(s) and %s localized tag page(s).", len(articles), total_tags)

    def render_root(self, base_html: str, site_meta: dict[str, Any]) -> None:
        lang = DEFAULT_LANG
        page_meta = self.page_meta(site_meta, "home", lang)

        self.write_route(
            "/",
            self.render_page(
                base_html=base_html,
                lang=lang,
                title=page_meta["title"],
                description=page_meta["description"],
                canonical_path="/",
                alternates=self.localized_alternates(lambda item_lang: f"/{item_lang}"),
                og_type="website",
            ),
        )

    def render_language_pages(self, base_html: str, site_meta: dict[str, Any]) -> None:
        for lang in SUPPORTED_LANGS:
            page_meta = self.page_meta(site_meta, "home", lang)

            self.write_route(
                f"/{lang}",
                self.render_page(
                    base_html=base_html,
                    lang=lang,
                    title=page_meta["title"],
                    description=page_meta["description"],
                    canonical_path=f"/{lang}",
                    alternates=self.localized_alternates(lambda item_lang: f"/{item_lang}"),
                    og_type="website",
                ),
            )

    def render_article_index_pages(
        self,
        base_html: str,
        site_meta: dict[str, Any],
    ) -> None:
        for lang in SUPPORTED_LANGS:
            page_meta = self.page_meta(site_meta, "articles", lang)

            self.write_route(
                f"/{lang}/articles",
                self.render_page(
                    base_html=base_html,
                    lang=lang,
                    title=page_meta["title"],
                    description=page_meta["description"],
                    canonical_path=f"/{lang}/articles",
                    alternates=self.localized_alternates(
                        lambda item_lang: f"/{item_lang}/articles"
                    ),
                    og_type="website",
                ),
            )

    def render_tag_index_pages(self, base_html: str, site_meta: dict[str, Any]) -> None:
        for lang in SUPPORTED_LANGS:
            page_meta = self.page_meta(site_meta, "tags", lang)

            self.write_route(
                f"/{lang}/tags",
                self.render_page(
                    base_html=base_html,
                    lang=lang,
                    title=page_meta["title"],
                    description=page_meta["description"],
                    canonical_path=f"/{lang}/tags",
                    alternates=self.localized_alternates(
                        lambda item_lang: f"/{item_lang}/tags"
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
                article_html = self.read_text(GENERATED_ARTICLES_DIR / f"{slug}.{lang}.html")

                self.write_route(
                    self.article_route(lang, slug),
                    self.render_page(
                        base_html=base_html,
                        lang=lang,
                        title=article["title"][lang],
                        description=article["description"][lang],
                        canonical_path=self.article_route(lang, slug),
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
                    self.tag_route(lang, tag),
                    self.render_page(
                        base_html=base_html,
                        lang=lang,
                        title=page_meta["title"],
                        description=page_meta["description"],
                        canonical_path=self.tag_route(lang, tag),
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
        data = site_meta.get("pages", {}).get("tag")

        if not isinstance(data, dict):
            raise RuntimeError("Missing site metadata page: tag")

        return {
            "title": self.localized(data.get("title"), lang, "pages.tag.title").format(tag=tag),
            "description": self.localized(
                data.get("description"),
                lang,
                "pages.tag.description",
            ).format(tag=tag),
        }

    @staticmethod
    def localized(value: Any, lang: str, path: str) -> str:
        if not isinstance(value, dict):
            raise RuntimeError(f"Missing localized object: {path}")

        text = value.get(lang) or value.get(DEFAULT_LANG)

        if not isinstance(text, str) or not text.strip():
            raise RuntimeError(f"Missing localized value: {path}.{lang}")

        return text.strip()

    @staticmethod
    def localized_alternates(route_factory) -> dict[str, str]:
        alternates = {
            lang: route_factory(lang)
            for lang in SUPPORTED_LANGS
        }

        alternates["x-default"] = alternates[DEFAULT_LANG]
        return alternates

    @staticmethod
    def article_alternates(article: dict[str, Any]) -> dict[str, str]:
        alternates = {
            lang: Prerender.article_route(lang, article["slug"])
            for lang in article["languages"]
        }

        alternates["x-default"] = alternates.get(DEFAULT_LANG) or next(iter(alternates.values()))
        return alternates

    @staticmethod
    def tag_alternates(tag: str, tags_by_lang: dict[str, set[str]]) -> dict[str, str]:
        alternates = {
            lang: Prerender.tag_route(lang, tag)
            for lang, tags in tags_by_lang.items()
            if tag in tags
        }

        alternates["x-default"] = alternates.get(DEFAULT_LANG) or next(iter(alternates.values()))
        return alternates

    def read_articles_index(self) -> list[dict[str, Any]]:
        path = GENERATED_DIR / "articles-index.json"
        data = self.read_json(path)

        if not isinstance(data, list):
            raise RuntimeError(f"Articles index must be a list: {path}")

        return data

    @staticmethod
    def collect_tags_by_lang(articles: list[dict[str, Any]]) -> dict[str, set[str]]:
        tags_by_lang = {lang: set() for lang in SUPPORTED_LANGS}

        for article in articles:
            for lang in article["languages"]:
                for tag in article["tags"]:
                    tags_by_lang[lang].add(tag)

        return tags_by_lang

    @staticmethod
    def article_route(lang: str, slug: str) -> str:
        return f"/{lang}/articles/{quote(slug, safe='')}"

    @staticmethod
    def tag_route(lang: str, tag: str) -> str:
        return f"/{lang}/tags/{quote(tag, safe='')}"

    @staticmethod
    def absolute_url(path: str) -> str:
        return f"{SITE_URL.rstrip('/')}/{path.lstrip('/')}"

    @staticmethod
    def read_text(path: Path) -> str:
        if not path.is_file():
            raise RuntimeError(f"Missing file: {path}")

        return path.read_text(encoding="utf-8")

    @staticmethod
    def read_json(path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RuntimeError(f"Missing JSON file: {path}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON file: {path}") from exc

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