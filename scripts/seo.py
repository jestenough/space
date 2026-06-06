"""SEO generation step"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from . import generated, routes
from .config import (
    DEFAULT_LANG,
    DIST_DIR,
    GENERATED_FILES_DIR,
    GENERATED_SITE_META_PATH,
    MEDIA_MANIFEST_PATH,
    NOT_FOUND_PAGE,
    SITE_URL,
    FileType,
    FolderType,
)
from .jsonio import read_json, read_object, read_text

XML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'
SITEMAP_ROOT = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'

logger = logging.getLogger(__name__)


class ArticleImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.capture(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.capture(tag, attrs)

    def capture(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return

        values = {key.lower(): (value or "") for key, value in attrs}
        src = values.get("src", "").strip()
        if not src.startswith("/media/"):
            return

        self.images.append({"src": src, "alt": values.get("alt", "").strip()})


class Seo:
    def __init__(self) -> None:
        self.media_manifest = self.read_media_manifest()

    def run(self) -> None:
        if not DIST_DIR.exists():
            raise RuntimeError("dist/ does not exist; run vite build before seo")

        site_meta = self.read_site_meta()
        sections = generated.sections()
        article_section = generated.first_section_slug(sections, FolderType.ARTICLES)
        tag_section = generated.first_section_slug(sections, FolderType.TAGS)
        files = generated.items(sections)
        articles = generated.articles(sections)
        languages = generated.item_languages(files)
        tags_by_lang = generated.collect_tags_by_lang(articles)

        sitemap = self.render_sitemap(self.build_sitemap_entries(articles, tags_by_lang, sections, files, tag_section))
        self.validate_xml(sitemap, "sitemap.xml")
        self.write_text(DIST_DIR / "sitemap.xml", sitemap)
        self.write_text(DIST_DIR / "robots.txt", self.render_robots())
        self.write_text(DIST_DIR / "_headers", self.render_headers(articles))
        self.write_text(DIST_DIR / "404.html", self.render_404(site_meta))

        for lang in languages:
            feed = self.render_feed(lang, articles, site_meta, article_section)
            self.validate_xml(feed, f"{lang}/feed.xml")
            self.write_text(DIST_DIR / lang / "feed.xml", feed)

        logger.info("Generated SEO files and %s feed(s).", len(languages))

    @staticmethod
    def read_site_meta() -> dict[str, Any]:
        return read_object(GENERATED_SITE_META_PATH, "generated site meta")

    @staticmethod
    def read_media_manifest() -> dict[str, dict[str, Any]]:
        if not MEDIA_MANIFEST_PATH.exists():
            return {}

        data = read_json(MEDIA_MANIFEST_PATH)
        if not isinstance(data, dict):
            raise RuntimeError(f"Media manifest must be an object: {MEDIA_MANIFEST_PATH}")

        return {str(key): value for key, value in data.items() if isinstance(value, dict)}

    def build_sitemap_entries(
        self,
        articles: list[dict[str, Any]],
        tags_by_lang: dict[str, set[str]],
        sections: list[dict[str, Any]],
        files: list[dict[str, Any]],
        tag_section: str | None,
    ) -> list[dict[str, Any]]:
        languages = generated.item_languages(files)
        latest = self.latest_date(articles)
        entries: list[dict[str, Any]] = []

        for section in sections:
            section_languages = generated.section_languages(section)
            for lang in section_languages:
                entries.append(
                    {
                        "path": routes.generated_section_route(section, lang),
                        "lastmod": latest,
                        "alternates": routes.alternates(
                            section_languages,
                            lambda item_lang, section=section: routes.generated_section_route(section, item_lang),
                        ),
                    }
                )

        for lang in languages:
            for tag in sorted(tags_by_lang.get(lang, set())):
                entries.append(
                    {
                        "path": routes.tag_route(tag_section or "tags", lang, tag),
                        "lastmod": self.latest_date(self.articles_with_tag(articles, lang, tag)),
                        "alternates": self.tag_alternates(tag_section or "tags", tag, tags_by_lang),
                    }
                )

        for article in articles:
            for lang in article["languages"]:
                entries.append(
                    {
                        "path": routes.generated_item_route(article, lang),
                        "lastmod": article["date"],
                        "alternates": self.article_alternates(article),
                        "images": self.article_images(article, lang),
                    }
                )

        for item in files:
            if item.get("type") == FileType.ARTICLE:
                continue
            for lang in item.get("languages", []):
                entries.append(
                    {
                        "path": routes.generated_item_route(item, lang),
                        "lastmod": item.get("date") or latest,
                        "alternates": self.item_alternates(item),
                    }
                )

        return entries

    def render_sitemap(self, entries: list[dict[str, Any]]) -> str:
        return "\n".join(
            [XML_HEADER, SITEMAP_ROOT, *(self.render_sitemap_entry(entry) for entry in entries), "</urlset>", ""]
        )

    @staticmethod
    def validate_xml(value: str, label: str) -> None:
        try:
            ET.fromstring(value)
        except ET.ParseError as exc:
            raise RuntimeError(f"{label} is not valid XML: {exc}") from exc

    def render_sitemap_entry(self, entry: dict[str, Any]) -> str:
        lines = [
            "  <url>",
            f"    <loc>{self.xml(routes.absolute_url(entry['path']))}</loc>",
            f"    <lastmod>{self.xml(entry['lastmod'])}</lastmod>",
        ]
        for hreflang, path in entry.get("alternates", {}).items():
            if path:
                lines.append(
                    f'    <xhtml:link rel="alternate" hreflang="{self.xml(hreflang)}" href="{self.xml(routes.absolute_url(path))}" />'
                )
        for image in entry.get("images", []):
            lines.append("    <image:image>")
            lines.append(f"      <image:loc>{self.xml(routes.absolute_url(image['src']))}</image:loc>")
            alt = self.meaningful_image_text(image.get("alt"))
            if alt:
                lines.append(f"      <image:title>{self.xml(alt)}</image:title>")
            lines.append("    </image:image>")
        lines.append("  </url>")
        return "\n".join(lines)

    @staticmethod
    def render_robots() -> str:
        return "\n".join(["User-agent: *", "Allow: /", "Disallow: /generated/", f"Sitemap: {SITE_URL}/sitemap.xml", ""])

    def render_headers(self, articles: list[dict[str, Any]]) -> str:
        lines = [
            "/*",
            "  X-Content-Type-Options: nosniff",
            "  Referrer-Policy: strict-origin-when-cross-origin",
            "  X-Frame-Options: DENY",
            "  Cache-Control: no-cache, must-revalidate",
            "",
            "/assets/*",
            "  Cache-Control: public, max-age=31536000, immutable",
            "",
            "/generated/*",
            "  X-Robots-Tag: noindex, nofollow",
            "  Cache-Control: no-store",
            "",
            "/media/*",
            "  Cache-Control: no-cache, must-revalidate",
            "",
            "/404.html",
            "  X-Robots-Tag: noindex, nofollow",
            "  Cache-Control: no-cache, must-revalidate",
            "",
        ]

        for article in articles:
            for lang in article["languages"]:
                article_path = routes.generated_item_route(article, lang)
                lines.extend(
                    [
                        self.article_pdf_path(article, lang),
                        f'  Link: <{routes.absolute_url(article_path)}>; rel="canonical"',
                        "  X-Robots-Tag: index, follow",
                        "  Cache-Control: no-cache, must-revalidate",
                        "",
                    ]
                )

        return "\n".join(lines)

    def render_404(self, site_meta: dict[str, Any]) -> str:
        title = self.page_value(site_meta, NOT_FOUND_PAGE, "title", DEFAULT_LANG)
        description = self.page_value(site_meta, NOT_FOUND_PAGE, "description", DEFAULT_LANG)
        return f"""<!doctype html>
<html lang="{DEFAULT_LANG}" data-theme="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="robots" content="noindex,nofollow" />
    <meta name="description" content="{self.xml(description)}" />
    <title>{self.xml(title)}</title>
    <link rel="icon" type="image/png" sizes="96x96" href="/icons/favicon-96x96.png" />
    <link rel="shortcut icon" href="/icons/favicon.ico" />
    <link rel="apple-touch-icon" sizes="152x152" href="/icons/apple-touch-icon.png" />
    <link rel="manifest" href="/icons/site.webmanifest" />
    <style>:root{{color-scheme:dark;--text:#d7dde7;--accent:#8ab4f8;--accent2:#66e3c4;--border:rgba(141,153,170,.22)}}*{{box-sizing:border-box}}body{{min-height:100vh;margin:0;display:grid;place-items:center;background:linear-gradient(180deg,#080a0f,#0c1118);color:var(--text);font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}}main{{width:min(92vw,40rem);padding:2rem;border:1px dashed var(--border);text-align:center}}h1{{margin:0 0 1rem;color:var(--accent);font-size:clamp(2rem,9vw,5rem);font-weight:700;text-transform:lowercase}}a{{color:var(--text);text-decoration:none;border-bottom:1px dashed var(--accent2)}}</style>
  </head>
  <body><main aria-label="404"><h1>signal lost</h1><p>{self.xml(description)}</p><a href="/">cd /</a></main></body>
</html>
"""

    def render_feed(
        self,
        lang: str,
        articles: list[dict[str, Any]],
        site_meta: dict[str, Any],
        article_section: str | None,
        feed_limit: int = 20,
    ) -> str:
        lang_articles = [article for article in articles if lang in article["languages"]]
        lang_articles.sort(key=lambda article: article["date"], reverse=True)
        items = []

        for article in lang_articles[:feed_limit]:
            url = routes.absolute_url(routes.generated_item_route(article, lang))
            items.append(
                "\n".join(
                    [
                        "    <item>",
                        f"      <title>{self.xml(self.localized(article['title'], lang))}</title>",
                        f"      <link>{self.xml(url)}</link>",
                        f"      <guid>{self.xml(url)}</guid>",
                        f"      <pubDate>{self.rfc2822_date(article['date'])}</pubDate>",
                        f"      <description>{self.xml(self.localized(article['description'], lang))}</description>",
                        "    </item>",
                    ]
                )
            )

        page_key = article_section or "articles"
        title = self.page_value(site_meta, page_key, "title", lang)
        description = self.page_value(site_meta, page_key, "description", lang)
        return "\n".join(
            [
                XML_HEADER,
                '<rss version="2.0">',
                "  <channel>",
                f"    <title>{self.xml(title)}</title>",
                f"    <link>{self.xml(routes.absolute_url(routes.section_route(page_key, lang)))}</link>",
                f"    <description>{self.xml(description)}</description>",
                f"    <language>{self.xml(lang)}</language>",
                *items,
                "  </channel>",
                "</rss>",
                "",
            ]
        )

    @staticmethod
    def page_value(site_meta: dict[str, Any], page: str, field: str, lang: str) -> str:
        value = site_meta.get("pages", {}).get(page, {}).get(field, {})
        if isinstance(value, dict):
            text = value.get(lang)
            if isinstance(text, str) and text.strip():
                return text.strip()
        return ""

    def article_alternates(self, article: dict[str, Any]) -> dict[str, str]:
        return routes.alternates(article["languages"], lambda lang: routes.generated_item_route(article, lang))

    def tag_alternates(self, section: str, tag: str, tags_by_lang: dict[str, set[str]]) -> dict[str, str]:
        alternates = {lang: routes.tag_route(section, lang, tag) for lang, tags in tags_by_lang.items() if tag in tags}
        alternates["x-default"] = alternates.get(DEFAULT_LANG) or next(iter(alternates.values()), "/")
        return alternates

    @staticmethod
    def articles_with_tag(articles: list[dict[str, Any]], lang: str, tag: str) -> list[dict[str, Any]]:
        return [article for article in articles if lang in article["languages"] and tag in article["tags"]]

    @staticmethod
    def latest_date(articles: list[dict[str, Any]]) -> str:
        if not articles:
            raise RuntimeError("Cannot calculate latest date: no articles")
        return max(article["date"] for article in articles)

    @staticmethod
    def localized(values: dict[str, str], lang: str) -> str:
        return values.get(lang, "")

    @staticmethod
    def rfc2822_date(value: str) -> str:
        return datetime.fromisoformat(f"{value}T00:00:00+00:00").strftime("%a, %d %b %Y %H:%M:%S GMT")

    def item_alternates(self, item: dict[str, Any]) -> dict[str, str]:
        return routes.alternates(item.get("languages", []), lambda lang: routes.generated_item_route(item, lang))

    def article_pdf_path(self, article: dict[str, Any], lang: str) -> str:
        return routes.generated_pdf_route(article, lang)

    def article_images(self, article: dict[str, Any], lang: str) -> list[dict[str, str]]:
        fragment_path = GENERATED_FILES_DIR / str(article["section"]) / f"{article['slug']}.{lang}.html"
        if not fragment_path.is_file():
            return []

        parser = ArticleImageParser()
        parser.feed(read_text(fragment_path, f"Missing generated article fragment: {fragment_path}"))
        images: list[dict[str, str]] = []
        seen: set[str] = set()
        for image in parser.images:
            src = image.get("src") or ""
            resolved = self.media_manifest.get(src, {}).get("src") or src
            if not isinstance(resolved, str) or not resolved.startswith("/media/") or resolved in seen:
                continue
            images.append({"src": resolved, "alt": self.meaningful_image_text(image.get("alt"))})
            seen.add(resolved)

        return images

    @staticmethod
    def meaningful_image_text(value: Any) -> str:
        if not isinstance(value, str):
            return ""

        text = value.strip()
        if text.lower() in {"image", "img", "figure", "photo", "picture"}:
            return ""

        return text

    @staticmethod
    def xml(value: Any) -> str:
        return xml_escape(str(value), {"'": "&apos;", '"': "&quot;"})

    @staticmethod
    def write_text(path: Path, value: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")


def run() -> None:
    Seo().run()
