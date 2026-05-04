"""Post-build output verification."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import DIST_DIR, GENERATED_ARTICLES_DIR, GENERATED_DIR, GENERATED_META_DIR, SITE_URL


logger = logging.getLogger(__name__)


class Verify:
    strict_pdf = os.environ.get("STRICT_PDF") == "1"
    required_dirs = (GENERATED_DIR, GENERATED_ARTICLES_DIR, GENERATED_META_DIR, DIST_DIR)
    required_files = (
        GENERATED_DIR / "site-meta.json",
        DIST_DIR / "sitemap.xml",
        DIST_DIR / "robots.txt",
        DIST_DIR / "_headers",
        DIST_DIR / "404.html",
        DIST_DIR / "generated" / "site-meta.json",
    )

    def __init__(self) -> None:
        self.warnings: list[str] = []

    def run(self) -> None:
        index = self.read_articles_index()
        self.check_generated_structure()
        self.check_articles(index)
        self.check_seo(index)
        for warning in self.warnings:
            logger.warning(warning)
        logger.info("Verified production build for %s article(s)%s.", len(index), f" with {len(self.warnings)} warning(s)" if self.warnings else "")

    def read_articles_index(self) -> list[dict[str, Any]]:
        path = GENERATED_DIR / "articles-index.json"
        if not path.is_file():
            raise RuntimeError(f"Missing generated articles index: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise RuntimeError(f"Generated articles index must be a list: {path}")
        return data

    def check_generated_structure(self) -> None:
        missing = [path for path in (*self.required_dirs, *self.required_files) if not path.exists()]
        if missing:
            raise RuntimeError("Missing generated paths: " + ", ".join(map(str, missing)))

    def check_articles(self, index: list[dict[str, Any]]) -> None:
        slugs: set[str] = set()
        titles: dict[str, str] = {}
        descriptions: dict[str, str] = {}
        for article in index:
            slug = article.get("slug")
            if not isinstance(slug, str) or not slug.strip():
                raise RuntimeError(f"Missing article slug: {article}")
            slug = slug.strip()
            if slug in slugs:
                raise RuntimeError(f"Duplicate article slug: {slug}")
            slugs.add(slug)
            for lang in self.get_languages(article, slug):
                self.check_article_language(article, slug, lang, titles, descriptions)

    def check_article_language(self, article: dict[str, Any], slug: str, lang: str, titles: dict[str, str], descriptions: dict[str, str]) -> None:
        title = self.get_localized_value(article, "title", lang)
        description = self.get_localized_value(article, "description", lang)
        self.push_unique(titles, title, f"{slug}.{lang}", "Duplicate title")
        self.push_unique(descriptions, description, f"{slug}.{lang}", "Duplicate description")
        self.check_html(GENERATED_ARTICLES_DIR / f"{slug}.{lang}.html", slug, lang)
        self.check_meta(GENERATED_META_DIR / f"{slug}.{lang}.json", slug, lang)
        self.check_pdf(self.dist_pdf_path(slug, lang))

    @staticmethod
    def get_languages(article: dict[str, Any], slug: str) -> tuple[str, ...]:
        languages = article.get("languages")
        if not isinstance(languages, list) or not languages:
            raise RuntimeError(f"Invalid or missing languages for article: {slug}")
        result = []
        for lang in languages:
            if not isinstance(lang, str) or not lang.strip():
                raise RuntimeError(f"Invalid language for article: {slug}")
            result.append(lang.strip())
        if len(result) != len(set(result)):
            raise RuntimeError(f"Duplicate languages for article: {slug}")
        return tuple(result)

    @staticmethod
    def get_localized_value(article: dict[str, Any], field: str, lang: str) -> str:
        value = article.get(field)
        if not isinstance(value, dict):
            raise RuntimeError(f"Missing `{field}` object for article: {article.get('slug')}")
        localized = value.get(lang)
        if not isinstance(localized, str) or not localized.strip():
            raise RuntimeError(f"Missing `{field}.{lang}` for article: {article.get('slug')}")
        return localized.strip()

    @staticmethod
    def push_unique(values: dict[str, str], value: str, location: str, message: str) -> None:
        key = value.strip().lower()
        if key in values:
            raise RuntimeError(f"{message}: {value} ({values[key]}, {location})")
        values[key] = location

    def check_html(self, path: Path, slug: str, lang: str) -> None:
        html = self.read_text(path, f"Missing generated HTML: {path}")

        if '<article class="article"' not in html:
            raise RuntimeError(f"Generated article has no article wrapper: {slug}.{lang}")

        if 'class="article__content"' not in html:
            raise RuntimeError(f"Generated article has no article content wrapper: {slug}.{lang}")

        if re.search(r"<h1\b", html, re.IGNORECASE):
            raise RuntimeError(
                f"Generated article fragment must not contain h1; "
                f"page h1 is rendered from metadata: {slug}.{lang}"
            )

        self.check_math_markers(html, slug, lang)

    @staticmethod
    def check_math_markers(html: str, slug: str, lang: str) -> None:
        has_math_markers = "\\[" in html or "\\(" in html

        if not has_math_markers:
            return

        if 'class="math' in html or "class='math" in html:
            return

        raise RuntimeError(
            f"Generated article contains raw math markers outside Pandoc math spans: "
            f"{slug}.{lang}"
        )

    def check_meta(self, path: Path, slug: str, lang: str) -> None:
        meta_text = self.read_text(path, f"Missing generated article metadata: {path}")
        meta = json.loads(meta_text)
        if meta.get("slug") != slug:
            raise RuntimeError(f"Metadata slug mismatch: {path}")
        if meta.get("lang") and meta.get("lang") != lang:
            raise RuntimeError(f"Metadata lang mismatch: {path}")
        if not isinstance(meta.get("canonicalPath"), str) or not meta["canonicalPath"].endswith(f"/articles/{slug}"):
            raise RuntimeError(f"Invalid canonicalPath in {path}")
        if not isinstance(meta.get("pdfPath"), str) or not meta["pdfPath"].endswith(f"/{slug}.pdf"):
            raise RuntimeError(f"Invalid pdfPath in {path}")
        for field in ("title", "description"):
            if not isinstance(meta.get(field), dict) or lang not in meta[field]:
                raise RuntimeError(f"Invalid `{field}` object in {path}")
        for field in ("title", "description"):
            if not isinstance(meta.get(field), dict) or lang not in meta[field]:
                raise RuntimeError(f"Invalid `{field}` object in {path}")
        if re.search(r"<(p|h1|article|section)\b", meta_text, re.I):
            raise RuntimeError(f"Article metadata must not contain HTML content: {path}")

    @staticmethod
    def dist_pdf_path(slug: str, lang: str) -> Path:
        return DIST_DIR / lang / "articles" / f"{slug}.pdf"

    def check_seo(self, index: list[dict[str, Any]]) -> None:
        sitemap = self.read_text(DIST_DIR / "sitemap.xml", "Missing dist/sitemap.xml")
        robots = self.read_text(DIST_DIR / "robots.txt", "Missing dist/robots.txt")
        headers = self.read_text(DIST_DIR / "_headers", "Missing dist/_headers")
        four_oh_four = self.read_text(DIST_DIR / "404.html", "Missing dist/404.html")
        if "Sitemap:" not in robots or SITE_URL not in robots:
            raise RuntimeError("robots.txt must reference sitemap.xml and SITE_URL")
        if "Disallow: /generated/" not in robots:
            raise RuntimeError("robots.txt should keep generated fragments out of the index")
        if "xmlns:xhtml=" not in sitemap:
            raise RuntimeError("Sitemap must declare xhtml hreflang namespace")
        for part in ("#/", "404", "/generated/"):
            if part in sitemap:
                raise RuntimeError(f"Sitemap must not contain: {part}")
        if not re.search(r"noindex", four_oh_four, re.I):
            raise RuntimeError("404.html must include noindex")
        sitemap_paths = self.extract_sitemap_paths(sitemap)
        headers_paths = self.extract_headers_paths(headers)
        for article in index:
            slug = article["slug"]
            for lang in self.get_languages(article, slug):
                canonical = f"/{lang}/articles/{slug}"
                pdf_route = f"/{lang}/articles/{slug}.pdf"
                if canonical not in sitemap_paths:
                    raise RuntimeError(f"Sitemap is missing canonical route: {canonical}")
                if pdf_route in sitemap_paths:
                    raise RuntimeError(f"Sitemap must not include PDF route: {pdf_route}")
                if pdf_route not in headers_paths:
                    raise RuntimeError(f"PDF canonical headers missing for {pdf_route}")

    @staticmethod
    def extract_sitemap_paths(sitemap: str) -> set[str]:
        return {urlparse(url).path.rstrip("/") for url in re.findall(r"<loc>([^<]+)</loc>", sitemap)}

    @staticmethod
    def extract_headers_paths(headers: str) -> set[str]:
        return set(re.findall(r"^(/\S+)", headers, re.M))

    def check_pdf(self, path: Path) -> None:
        if not path.is_file():
            if self.strict_pdf:
                raise RuntimeError(f"Missing PDF: {path}")
            self.warnings.append(f"Missing PDF: {path}")
            return
        if path.stat().st_size == 0:
            raise RuntimeError(f"Empty PDF: {path}")

    @staticmethod
    def read_text(path: Path, message: str) -> str:
        if not path.is_file():
            raise RuntimeError(message)
        return path.read_text(encoding="utf-8")


def run() -> None:
    Verify().run()
