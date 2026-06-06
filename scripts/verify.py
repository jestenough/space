"""Post-build output verification"""

from __future__ import annotations

import logging
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import content, generated, routes
from .config import (
    DIST_DIR,
    GENERATED_DIR,
    GENERATED_FILE_META_DIR,
    GENERATED_FILES_DIR,
    GENERATED_SECTIONS_DIR,
    GENERATED_SECTIONS_INDEX_FILE,
    GENERATED_SITE_META_FILE,
    MEDIA_MANIFEST_PATH,
    SITE_URL,
    FileType,
)
from .jsonio import read_json, read_text

logger = logging.getLogger(__name__)


class Verify:
    strict_pdf = os.environ.get("STRICT_PDF") == "1"
    required_dirs = (
        GENERATED_DIR,
        GENERATED_FILES_DIR,
        GENERATED_FILE_META_DIR,
        GENERATED_SECTIONS_DIR,
        DIST_DIR,
    )
    required_files = (
        GENERATED_DIR / GENERATED_SITE_META_FILE,
        GENERATED_DIR / GENERATED_SECTIONS_INDEX_FILE,
        DIST_DIR / "sitemap.xml",
        DIST_DIR / "robots.txt",
        DIST_DIR / "_headers",
        DIST_DIR / "404.html",
        DIST_DIR / GENERATED_DIR.name / GENERATED_SITE_META_FILE,
        DIST_DIR / GENERATED_DIR.name / GENERATED_SECTIONS_INDEX_FILE,
    )

    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.media_manifest = self.read_media_manifest()

    def run(self) -> None:
        index = self.read_articles()

        self.check_generated_structure()
        self.check_no_generated_artifacts()
        self.check_no_dist_artifacts()
        self.check_generated_items()
        self.check_content_index(index)
        self.check_articles(index)
        self.check_seo(index)

        for warning in self.warnings:
            logger.warning(warning)

        logger.info(
            "Verified production build for %s article(s)%s.",
            len(index),
            f" with {len(self.warnings)} warning(s)" if self.warnings else "",
        )

    @staticmethod
    def read_media_manifest() -> dict[str, dict[str, Any]]:
        if not MEDIA_MANIFEST_PATH.exists():
            return {}

        data = read_json(MEDIA_MANIFEST_PATH)
        if not isinstance(data, dict):
            raise RuntimeError(f"Media manifest must be an object: {MEDIA_MANIFEST_PATH}")

        return {str(key): value for key, value in data.items() if isinstance(value, dict)}

    def read_articles(self) -> list[dict[str, Any]]:
        return generated.articles()

    def check_generated_structure(self) -> None:
        missing = [path for path in (*self.required_dirs, *self.required_files) if not path.exists()]
        if missing:
            raise RuntimeError("Missing generated paths: " + ", ".join(map(str, missing)))

    def check_no_generated_artifacts(self) -> None:
        forbidden = [
            GENERATED_DIR / "articles-index.json",
            GENERATED_DIR / "articles",
            GENERATED_DIR / "articles-meta",
        ]
        stale = [path for path in forbidden if path.exists()]
        stale.extend(path for path in GENERATED_DIR.glob("*-index.json") if path.name != GENERATED_SECTIONS_INDEX_FILE)
        stale.extend(GENERATED_DIR.rglob("*.br"))
        if stale:
            raise RuntimeError("Forbidden generated artifacts: " + ", ".join(str(path) for path in sorted(set(stale))))

    @staticmethod
    def check_no_dist_artifacts() -> None:
        forbidden = [
            DIST_DIR / GENERATED_DIR.name / "files-meta",
            DIST_DIR / "info",
        ]
        stale = [path for path in forbidden if path.exists()]
        if stale:
            raise RuntimeError("Forbidden dist artifacts: " + ", ".join(str(path) for path in sorted(stale)))

    def check_generated_items(self) -> None:
        for item in generated.items():
            section = self.required_string(item, "section")
            slug = self.required_string(item, "slug")
            languages = self.get_languages(item, f"{section}/{slug}")
            for lang in languages:
                html_path = GENERATED_FILES_DIR / section / f"{slug}.{lang}.html"
                meta_path = GENERATED_FILE_META_DIR / section / f"{slug}.{lang}.json"
                read_text(html_path, f"Missing generated item HTML: {html_path}")
                self.check_item_meta(meta_path, item, lang)
            self.check_download_paths(item)

    def check_item_meta(self, path: Path, item: dict[str, Any], lang: str) -> None:
        meta = read_json(path)
        for field in ("section", "slug", "lang", "canonicalPath"):
            if not isinstance(meta.get(field), str) or not meta[field]:
                raise RuntimeError(f"Invalid `{field}` in {path}")

        if meta["section"] != item.get("section") or meta["slug"] != item.get("slug") or meta["lang"] != lang:
            raise RuntimeError(f"Generated metadata mismatch: {path}")

        if meta["canonicalPath"] != routes.generated_item_route(item, lang):
            raise RuntimeError(f"Invalid canonicalPath in {path}")

        for field in ("label", "title", "description"):
            value = meta.get(field)
            if not isinstance(value, dict) or lang not in value:
                raise RuntimeError(f"Invalid `{field}.{lang}` in {path}")

    def check_download_paths(self, item: dict[str, Any]) -> None:
        languages = self.get_languages(item, str(item.get("slug") or "item"))
        source_item = self.content_item(str(item.get("section") or ""), str(item.get("slug") or ""))
        downloadable = source_item is not None and source_item.meta.get("download") is True
        for lang in languages:
            path = read_json(GENERATED_FILE_META_DIR / str(item["section"]) / f"{item['slug']}.{lang}.json").get(
                "downloadPath"
            )
            if path is None:
                continue

            if not downloadable:
                raise RuntimeError(
                    f'Unexpected downloadPath for {item.get("section")}/{item.get("slug")}.{lang}: add `"download": true` to item meta or regenerate output.'
                )

            if not isinstance(path, str) or not path.startswith(f"/{lang}/"):
                raise RuntimeError(
                    f"Invalid downloadPath for {item.get('section')}/{item.get('slug')}.{lang}: {path!r}"
                )

    @staticmethod
    def content_item(section_slug: str, item_slug: str) -> content.Item | None:
        for section in content.sections():
            if section.slug != section_slug:
                continue
            return next((item for item in section.items if item.slug == item_slug), None)
        return None

    @staticmethod
    def required_string(item: dict[str, Any], field: str) -> str:
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"Generated item is missing `{field}`: {item}")
        return value.strip()

    def check_content_index(self, index: list[dict[str, Any]]) -> None:
        source_slugs = {
            item.slug
            for section in content.sections()
            for item in section.items
            if content.item_type(item) == FileType.ARTICLE
        }
        indexed_slugs = {article.get("slug") for article in index if isinstance(article.get("slug"), str)}

        missing = sorted(source_slugs - indexed_slugs)
        stale = sorted(indexed_slugs - source_slugs)

        if missing:
            raise RuntimeError("Articles missing from generated sections: " + ", ".join(missing))

        if stale:
            raise RuntimeError("Stale articles left in generated sections: " + ", ".join(stale))

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

    def check_article_language(
        self,
        article: dict[str, Any],
        slug: str,
        lang: str,
        titles: dict[str, str],
        descriptions: dict[str, str],
    ) -> None:
        title = self.get_localized_value(article, "title", lang)
        description = self.get_localized_value(article, "description", lang)
        self.push_unique(titles, title, f"{slug}.{lang}", "Duplicate title")
        self.push_unique(descriptions, description, f"{slug}.{lang}", "Duplicate description")

        section = str(article.get("section") or "")
        self.check_html(GENERATED_FILES_DIR / section / f"{slug}.{lang}.html", slug, lang)
        self.check_meta(GENERATED_FILE_META_DIR / section / f"{slug}.{lang}.json", slug, lang)
        self.check_pdf(self.dist_pdf_path(article, lang))

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
        html = read_text(path, f"Missing generated HTML: {path}")

        if '<article class="article"' not in html:
            raise RuntimeError(f"Generated article has no article wrapper: {slug}.{lang}")

        if 'class="article__content"' not in html:
            raise RuntimeError(f"Generated article has no article content wrapper: {slug}.{lang}")

        if re.search(r"<h1\b", html, re.IGNORECASE):
            raise RuntimeError(
                f"Generated article fragment must not contain h1; page h1 is rendered from metadata: {slug}.{lang}"
            )

        self.check_math_markers(html, slug, lang)
        self.check_article_media_links(html, slug, lang)

    @staticmethod
    def check_math_markers(html: str, slug: str, lang: str) -> None:
        has_math_markers = "\\[" in html or "\\(" in html

        if not has_math_markers:
            return

        if 'class="math' in html or "class='math" in html:
            return

        raise RuntimeError(f"Generated article contains raw math markers outside Pandoc math spans: {slug}.{lang}")

    def check_article_media_links(self, html: str, slug: str, lang: str) -> None:
        paths = re.findall(r"(?:src|href)=[\"'](/media/[^\"']+)", html)

        for public_path in paths:
            resolved_path = public_path
            if not (DIST_DIR / public_path.lstrip("/")).is_file():
                manifest_entry = self.media_manifest.get(public_path)
                if manifest_entry:
                    candidate = manifest_entry.get("src")
                    if isinstance(candidate, str) and candidate.startswith("/media/"):
                        resolved_path = candidate
            dist_path = DIST_DIR / resolved_path.lstrip("/")
            if not dist_path.is_file():
                raise RuntimeError(f"Missing article media asset for {slug}.{lang}: {public_path}")

    def check_meta(self, path: Path, slug: str, lang: str) -> None:
        meta_text = read_text(path, f"Missing generated article metadata: {path}")
        meta = read_json(path)
        if meta.get("slug") != slug:
            raise RuntimeError(f"Metadata slug mismatch: {path}")

        if meta.get("lang") and meta.get("lang") != lang:
            raise RuntimeError(f"Metadata lang mismatch: {path}")

        if not isinstance(meta.get("canonicalPath"), str) or not meta["canonicalPath"].endswith(f"/{slug}"):
            raise RuntimeError(f"Invalid canonicalPath in {path}")

        if not isinstance(meta.get("pdfPath"), str) or not meta["pdfPath"].endswith(f"/{slug}.pdf"):
            raise RuntimeError(f"Invalid pdfPath in {path}")

        for field in ("title", "description"):
            if not isinstance(meta.get(field), dict) or lang not in meta[field]:
                raise RuntimeError(f"Invalid `{field}` object in {path}")

        if re.search(r"<(p|h1|article|section)\b", meta_text, re.I):
            raise RuntimeError(f"Article metadata must not contain HTML content: {path}")

    @staticmethod
    def dist_pdf_path(article: dict[str, Any], lang: str) -> Path:
        return DIST_DIR / routes.generated_pdf_route(article, lang).lstrip("/")

    def check_seo(self, index: list[dict[str, Any]]) -> None:
        sitemap = read_text(DIST_DIR / "sitemap.xml", "Missing dist/sitemap.xml")
        self.validate_xml(sitemap, "sitemap.xml")

        if "xmlns:xhtml=" not in sitemap:
            raise RuntimeError("Sitemap must declare xhtml hreflang namespace")
        if "xmlns:xhtml=" not in sitemap:
            raise RuntimeError("Sitemap must declare xhtml hreflang namespace")
        if "xmlns:image=" not in sitemap:
            raise RuntimeError("Sitemap must declare image namespace")

        headers = read_text(DIST_DIR / "_headers", "Missing dist/_headers")
        self.check_cache_headers(headers)

        robots = read_text(DIST_DIR / "robots.txt", "Missing dist/robots.txt")
        if "Sitemap:" not in robots or SITE_URL not in robots:
            raise RuntimeError("robots.txt must reference sitemap.xml and SITE_URL")
        if "Disallow: /generated/" not in robots:
            raise RuntimeError("robots.txt should keep generated fragments out of the index")

        for part in ("#/", "404", "/generated/"):
            if part in sitemap:
                raise RuntimeError(f"Sitemap must not contain: {part}")

        four_oh_four = read_text(DIST_DIR / "404.html", "Missing dist/404.html")
        if not re.search(r"noindex", four_oh_four, re.I):
            raise RuntimeError("404.html must include noindex")

        files = generated.items(generated.sections())
        for lang in generated.item_languages(files):
            self.validate_xml(
                read_text(
                    DIST_DIR / lang / "feed.xml",
                    f"Missing feed: {DIST_DIR / lang / 'feed.xml'}",
                ),
                f"{lang}/feed.xml",
            )

        headers_paths = self.extract_headers_paths(headers)
        sitemap_paths = self.extract_sitemap_paths(sitemap)
        self.check_section_routes(sitemap_paths)
        for article in index:
            slug = article["slug"]
            for lang in self.get_languages(article, slug):
                canonical = routes.generated_item_route(article, lang)
                pdf_route = routes.generated_pdf_route(article, lang)
                if canonical not in sitemap_paths:
                    raise RuntimeError(f"Sitemap is missing canonical route: {canonical}")
                if pdf_route in sitemap_paths:
                    raise RuntimeError(f"Sitemap must not include PDF route: {pdf_route}")
                if pdf_route not in headers_paths:
                    raise RuntimeError(f"PDF canonical headers missing for {pdf_route}")

    def check_section_routes(self, sitemap_paths: set[str]) -> None:
        for section in generated.sections():
            slug = section.get("slug")
            if not isinstance(slug, str):
                raise RuntimeError("Section entry is missing slug")

            section_index_path = GENERATED_SECTIONS_DIR / f"{slug}.json"
            if not section_index_path.is_file():
                raise RuntimeError(f"Missing section index: {section_index_path}")

            for lang in generated.section_languages(section):
                route = routes.generated_section_route(section, lang)
                if route.rstrip("/") not in sitemap_paths:
                    raise RuntimeError(f"Sitemap is missing section route: {route}")

    @staticmethod
    def check_cache_headers(headers: str) -> None:
        media_block = re.search(r"^/media/\*\n(?P<body>(?:  .+\n)+)", headers, re.M)
        if media_block and "immutable" in media_block.group("body").lower():
            raise RuntimeError("Article media must not be cached with immutable headers")

        generated_block = re.search(r"^/generated/\*\n(?P<body>(?:  .+\n)+)", headers, re.M)
        if not generated_block or "no-store" not in generated_block.group("body").lower():
            raise RuntimeError("Generated JSON/HTML assets must use Cache-Control: no-store")

    @staticmethod
    def extract_sitemap_paths(sitemap: str) -> set[str]:
        root = ET.fromstring(sitemap)
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        return {
            urlparse((loc.text or "").strip()).path.rstrip("/")
            for loc in root.findall("sm:url/sm:loc", namespace)
            if (loc.text or "").strip()
        }

    @staticmethod
    def validate_xml(value: str, label: str) -> None:
        try:
            ET.fromstring(value)
        except ET.ParseError as exc:
            raise RuntimeError(f"{label} is not valid XML: {exc}") from exc

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


def run() -> None:
    Verify().run()
