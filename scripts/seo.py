"""SEO generation step."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Callable
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

from .config import DEFAULT_LANG, DIST_DIR, GENERATED_DIR, SITE_META_PATH, SITE_URL

XML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'
SITEMAP_ROOT = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'

logger = logging.getLogger(__name__)


class Seo:
    def run(self) -> None:
        if not DIST_DIR.exists():
            raise RuntimeError("dist/ does not exist; run vite build before seo")

        site_meta = self.read_site_meta()
        articles = self.read_articles_index()
        languages = self.collect_languages(articles)
        tags_by_lang = self.collect_tags_by_lang(articles)

        self.write_text(DIST_DIR / "sitemap.xml", self.render_sitemap(self.build_sitemap_entries(articles, tags_by_lang)))
        self.write_text(DIST_DIR / "robots.txt", self.render_robots())
        self.write_text(DIST_DIR / "_headers", self.render_headers(articles))
        self.write_text(DIST_DIR / "404.html", self.render_404(site_meta))

        for lang in languages:
            self.write_text(DIST_DIR / lang / "feed.xml", self.render_feed(lang, articles, site_meta))

        logger.info("Generated SEO files and %s feed(s).", len(languages))

    @staticmethod
    def read_articles_index() -> list[dict[str, Any]]:
        data = json.loads((GENERATED_DIR / "articles-index.json").read_text(encoding="utf-8"))

        if not isinstance(data, list):
            raise RuntimeError("generated/articles-index.json must be a list")

        return data

    @staticmethod
    def read_site_meta() -> dict[str, Any]:
        data = json.loads(SITE_META_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError(f"{SITE_META_PATH} must be an object")
        return data

    def build_sitemap_entries(self, articles: list[dict[str, Any]], tags_by_lang: dict[str, set[str]]) -> list[dict[str, Any]]:
        languages = self.collect_languages(articles)
        latest = self.latest_date(articles)
        entries: list[dict[str, Any]] = []

        for lang in languages:
            entries.extend(
                [
                    {"path": f"/{lang}", "lastmod": latest, "alternates": self.section_alternates(languages, lambda item_lang: f"/{item_lang}")},
                    {"path": f"/{lang}/articles", "lastmod": latest, "alternates": self.section_alternates(languages, lambda item_lang: f"/{item_lang}/articles")},
                    {"path": f"/{lang}/tags", "lastmod": latest, "alternates": self.section_alternates(languages, lambda item_lang: f"/{item_lang}/tags")},
                ]
            )

        for lang in languages:
            for tag in sorted(tags_by_lang.get(lang, set())):
                entries.append(
                    {
                        "path": self.tag_path(lang, tag),
                        "lastmod": self.latest_date(self.articles_with_tag(articles, lang, tag)),
                        "alternates": self.tag_alternates(tag, tags_by_lang),
                    }
                )

        for article in articles:
            for lang in article["languages"]:
                entries.append(
                    {
                        "path": self.article_path(lang, article["slug"]),
                        "lastmod": article["date"],
                        "alternates": self.article_alternates(article),
                    }
                )

        return entries

    def render_sitemap(self, entries: list[dict[str, Any]]) -> str:
        return "\n".join([XML_HEADER, SITEMAP_ROOT, *(self.render_sitemap_entry(entry) for entry in entries), "</urlset>", ""])

    def render_sitemap_entry(self, entry: dict[str, Any]) -> str:
        lines = ["  <url>", f"    <loc>{self.xml(self.absolute_url(entry['path']))}</loc>", f"    <lastmod>{self.xml(entry['lastmod'])}</lastmod>"]
        for hreflang, path in entry.get("alternates", {}).items():
            if path:
                lines.append(f"    <xhtml:link rel=\"alternate\" hreflang=\"{self.xml(hreflang)}\" href=\"{self.xml(self.absolute_url(path))}\" />")
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
            "  Cache-Control: public, max-age=0, must-revalidate",
            "",
            "/assets/*",
            "  Cache-Control: public, max-age=31536000, immutable",
            "",
            "/media/*",
            "  Cache-Control: public, max-age=31536000, immutable",
            "",
            "/generated/*",
            "  X-Robots-Tag: noindex, nofollow",
            "  Cache-Control: public, max-age=3600, must-revalidate",
            "",
            "/404.html",
            "  X-Robots-Tag: noindex, nofollow",
            "  Cache-Control: public, max-age=0, must-revalidate",
            "",
        ]

        for article in articles:
            for lang in article["languages"]:
                article_path = self.article_path(lang, article["slug"])
                lines.extend([
                    self.article_pdf_path(lang, article["slug"]),
                    f"  Link: <{self.absolute_url(article_path)}>; rel=\"canonical\"",
                    "  X-Robots-Tag: index, follow",
                    "  Cache-Control: public, max-age=86400, must-revalidate",
                    "",
                ])

        return "\n".join(lines)

    def render_404(self, site_meta: dict[str, Any]) -> str:
        title = self.page_value(site_meta, "notFound", "title", DEFAULT_LANG)
        description = self.page_value(site_meta, "notFound", "description", DEFAULT_LANG)
        return f"""<!doctype html>
<html lang="{DEFAULT_LANG}" data-theme="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="robots" content="noindex,nofollow" />
    <meta name="description" content="{self.xml(description)}" />
    <title>{self.xml(title)}</title>
    <style>:root{{color-scheme:dark;--text:#d7dde7;--accent:#8ab4f8;--accent2:#66e3c4;--border:rgba(141,153,170,.22)}}*{{box-sizing:border-box}}body{{min-height:100vh;margin:0;display:grid;place-items:center;background:linear-gradient(180deg,#080a0f,#0c1118);color:var(--text);font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}}main{{width:min(92vw,40rem);padding:2rem;border:1px dashed var(--border);text-align:center}}h1{{margin:0 0 1rem;color:var(--accent);font-size:clamp(2rem,9vw,5rem);font-weight:700;text-transform:lowercase}}a{{color:var(--text);text-decoration:none;border-bottom:1px dashed var(--accent2)}}</style>
  </head>
  <body><main aria-label="404"><h1>signal lost</h1><p>{self.xml(description)}</p><a href="/">cd /</a></main></body>
</html>
"""

    def render_feed(self, lang: str, articles: list[dict[str, Any]], site_meta: dict[str, Any]) -> str:
        lang_articles = [article for article in articles if lang in article["languages"]]
        lang_articles.sort(key=lambda article: article["date"], reverse=True)
        items = []

        for article in lang_articles[:20]:
            url = self.absolute_url(self.article_path(lang, article["slug"]))
            items.append("\n".join([
                "    <item>",
                f"      <title>{self.xml(self.localized(article['title'], lang))}</title>",
                f"      <link>{self.xml(url)}</link>",
                f"      <guid>{self.xml(url)}</guid>",
                f"      <pubDate>{self.rfc2822_date(article['date'])}</pubDate>",
                f"      <description>{self.xml(self.localized(article['description'], lang))}</description>",
                "    </item>",
            ]))

        title = self.page_value(site_meta, "articles", "title", lang)
        description = self.page_value(site_meta, "articles", "description", lang)
        return "\n".join([
            XML_HEADER,
            '<rss version="2.0">',
            "  <channel>",
            f"    <title>{self.xml(title)}</title>",
            f"    <link>{self.xml(self.absolute_url(f'/{lang}/articles'))}</link>",
            f"    <description>{self.xml(description)}</description>",
            f"    <language>{self.xml(lang)}</language>",
            *items,
            "  </channel>",
            "</rss>",
            "",
        ])

    @staticmethod
    def page_value(site_meta: dict[str, Any], page: str, field: str, lang: str) -> str:
        value = site_meta.get("pages", {}).get(page, {}).get(field, {})
        if isinstance(value, dict):
            return str(value.get(lang) or value.get(DEFAULT_LANG) or next(iter(value.values()), "")).strip()
        return ""

    @staticmethod
    def collect_languages(articles: list[dict[str, Any]]) -> list[str]:
        return sorted({lang for article in articles for lang in article["languages"]})

    def collect_tags_by_lang(self, articles: list[dict[str, Any]]) -> dict[str, set[str]]:
        result = {lang: set() for lang in self.collect_languages(articles)}
        for article in articles:
            for lang in article["languages"]:
                result.setdefault(lang, set()).update(article["tags"])
        return result

    def article_alternates(self, article: dict[str, Any]) -> dict[str, str]:
        alternates = {lang: self.article_path(lang, article["slug"]) for lang in article["languages"]}
        alternates["x-default"] = alternates.get(DEFAULT_LANG) or alternates[article["languages"][0]]
        return alternates

    @staticmethod
    def section_alternates(languages: list[str], build_path: Callable[[str], str]) -> dict[str, str]:
        alternates = {lang: build_path(lang) for lang in languages}
        alternates["x-default"] = alternates.get(DEFAULT_LANG) or alternates[languages[0]]
        return alternates

    def tag_alternates(self, tag: str, tags_by_lang: dict[str, set[str]]) -> dict[str, str]:
        alternates = {lang: self.tag_path(lang, tag) for lang, tags in tags_by_lang.items() if tag in tags}
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
        return values.get(lang) or values.get(DEFAULT_LANG) or next(iter(values.values()), "")

    @staticmethod
    def rfc2822_date(value: str) -> str:
        return datetime.fromisoformat(f"{value}T00:00:00+00:00").strftime("%a, %d %b %Y %H:%M:%S GMT")

    @staticmethod
    def article_path(lang: str, slug: str) -> str:
        return f"/{lang}/articles/{quote(slug, safe='')}"

    def article_pdf_path(self, lang: str, slug: str) -> str:
        return f"{self.article_path(lang, slug)}.pdf"

    @staticmethod
    def tag_path(lang: str, tag: str) -> str:
        return f"/{lang}/tags/{quote(tag, safe='')}"

    @staticmethod
    def absolute_url(path: str) -> str:
        return f"{SITE_URL}/{path.lstrip('/')}"

    @staticmethod
    def xml(value: Any) -> str:
        return xml_escape(str(value), {"'": "&apos;", '"': "&quot;"})

    @staticmethod
    def write_text(path, value: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")


def run() -> None:
    Seo().run()
