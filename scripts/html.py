"""
HTML generation step.

Converts article TeX sources into generated HTML fragments, writes frontend-compatible
article metadata, copies article assets, and creates articles-index.json.
"""

from __future__ import annotations

import html
import json
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .config import (
    ARTICLES_DIR,
    GENERATED_ARTICLES_DIR,
    GENERATED_DIR,
    GENERATED_META_DIR,
    PUBLIC_DIR,
    SITE_META_PATH,
    SUPPORTED_LANGS,
)

logger = logging.getLogger(__name__)


class Html:
    asset_src_re = re.compile(r'(?P<prefix>\b(?:src|href)=["\'])(?P<path>assets/[^"\']+)(?P<suffix>["\'])')

    def run(self) -> None:
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        GENERATED_ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
        GENERATED_META_DIR.mkdir(parents=True, exist_ok=True)

        self.copy_site_meta()
        index = self.collect_articles()

        for previous in GENERATED_ARTICLES_DIR.glob("*.html"):
            previous.unlink()
        for previous in GENERATED_META_DIR.glob("*.json"):
            previous.unlink()

        for article in index:
            self.generate_article(article)

        self.write_json(GENERATED_DIR / "articles-index.json", index)
        logger.info("Generated HTML for %s article(s).", len(index))

    def copy_site_meta(self) -> None:
        if not SITE_META_PATH.is_file():
            raise RuntimeError(f"Missing site metadata: {SITE_META_PATH}")
        self.write_json(GENERATED_DIR / "site-meta.json", self.read_json(SITE_META_PATH))

    def collect_articles(self) -> list[dict[str, Any]]:
        articles: list[dict[str, Any]] = []

        for article_dir in sorted(ARTICLES_DIR.iterdir()):
            if not article_dir.is_dir():
                continue

            slug = article_dir.name
            meta = self.read_json(article_dir / f"{slug}.meta.json")
            languages = self.detect_languages(article_dir, slug)
            title = self.localized_record(meta["title"], languages, f"{slug}.title")
            description = self.localized_record(meta["description"], languages, f"{slug}.description")
            tags = self.string_list(meta["tags"], f"{slug}.tags")

            articles.append(
                {
                    "slug": slug,
                    "date": str(meta["date"]),
                    "tags": tags,
                    "title": title,
                    "description": description,
                    "languages": languages,
                    "translations": {
                        lang: self.article_path(lang, slug)
                        for lang in languages
                    },
                    "prev": None,
                    "next": None,
                }
            )

        self.link_neighbors(articles)
        return articles

    @staticmethod
    def detect_languages(article_dir: Path, slug: str) -> list[str]:
        languages = [
            lang
            for lang in SUPPORTED_LANGS
            if (article_dir / f"{slug}.{lang}.tex").is_file()
        ]

        if not languages:
            raise RuntimeError(f"No TeX sources found for article: {slug}")

        return languages

    @staticmethod
    def link_neighbors(articles: list[dict[str, Any]]) -> None:
        sorted_articles = sorted(articles, key=lambda item: (item["date"], item["slug"]), reverse=True)
        for index, article in enumerate(sorted_articles):
            previous_article = sorted_articles[index - 1] if index > 0 else None
            next_article = sorted_articles[index + 1] if index + 1 < len(sorted_articles) else None
            article["prev"] = Html.neighbor(previous_article, article["languages"]) if previous_article else None
            article["next"] = Html.neighbor(next_article, article["languages"]) if next_article else None

    @staticmethod
    def neighbor(article: dict[str, Any] | None, preferred_languages: list[str]) -> dict[str, str] | None:
        if article is None:
            return None
        lang = next((item for item in preferred_languages if item in article["languages"]), article["languages"][0])
        return {
            "title": article["title"][lang],
            "path": Html.article_path(lang, article["slug"]),
        }

    def generate_article(self, article: dict[str, Any]) -> None:
        slug = article["slug"]
        article_dir = ARTICLES_DIR / slug
        self.copy_article_assets(article_dir, slug)

        for lang in article["languages"]:
            source_path = article_dir / f"{slug}.{lang}.tex"
            html_path = GENERATED_ARTICLES_DIR / f"{slug}.{lang}.html"
            meta_path = GENERATED_META_DIR / f"{slug}.{lang}.json"

            body = self.convert_tex_to_html(source_path, article_dir, slug)
            page = self.wrap_article(body, article, lang)
            stats = self.text_stats(source_path.read_text(encoding="utf-8"))

            html_path.write_text(page, encoding="utf-8")
            self.write_json(meta_path, self.build_article_meta(article, lang, source_path, stats))

    def convert_tex_to_html(self, source_path: Path, article_dir: Path, slug: str) -> str:
        result = subprocess.run(
            [
                "pandoc",
                str(source_path),
                "--from",
                "latex",
                "--to",
                "html5",
                "--mathml",
                "--shift-heading-level-by=1",  # The page <h1> is rendered from article metadata in the layout, so Pandoc headings from TeX must start at <h2>.
                "--resource-path",
                str(article_dir),
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        return self.rewrite_asset_paths(result.stdout.strip(), slug)

    def rewrite_asset_paths(self, value: str, slug: str) -> str:
        def replace(match: re.Match[str]) -> str:
            raw_path = match.group("path")
            file_name = raw_path.removeprefix("assets/")
            return f'{match.group("prefix")}/media/articles/{html.escape(slug, quote=True)}/assets/{html.escape(file_name, quote=True)}{match.group("suffix")}'

        return self.asset_src_re.sub(replace, value)

    def wrap_article(self, body: str, article: dict[str, Any], lang: str) -> str:
        return f"""<article class="article" lang="{html.escape(lang)}">
  <div class="article__content">
{body}
  </div>
</article>
"""

    @staticmethod
    def build_article_meta(article: dict[str, Any], lang: str, source_path: Path, stats: dict[str, int]) -> dict[str, Any]:
        slug = article["slug"]

        return {
            "slug": slug,
            "lang": lang,
            "date": article["date"],
            "title": article["title"],
            "description": article["description"],
            "tags": article["tags"],
            "languages": article["languages"],
            "translations": article["translations"],
            "canonicalPath": Html.article_path(lang, slug),
            "pdfPath": Html.article_pdf_path(lang, slug),
            "sourcePath": str(source_path.relative_to(source_path.parents[3])),
            "wordCount": stats["words"],
            "readingTime": max(1, round(stats["words"] / 220)),
            "prev": article.get("prev"),
            "next": article.get("next"),
        }

    @staticmethod
    def localized(article: dict[str, Any], field: str, lang: str) -> str:
        return str(article[field][lang]).strip()

    @staticmethod
    def localized_record(value: Any, languages: list[str], path: str) -> dict[str, str]:
        if not isinstance(value, dict):
            raise RuntimeError(f"{path} must be an object")
        result: dict[str, str] = {}
        for lang in languages:
            text = value.get(lang)
            if not isinstance(text, str) or not text.strip():
                raise RuntimeError(f"Missing localized value: {path}.{lang}")
            result[lang] = text.strip()
        return result

    @staticmethod
    def string_list(value: Any, path: str) -> list[str]:
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise RuntimeError(f"{path} must be a non-empty string array")
        return list(dict.fromkeys(item.strip() for item in value))

    @staticmethod
    def read_json(path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RuntimeError(f"Missing JSON file: {path}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON: {path}") from exc

        if not isinstance(data, dict):
            raise RuntimeError(f"JSON must be an object: {path}")

        return data

    @staticmethod
    def write_json(path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def copy_article_assets(article_dir: Path, slug: str) -> None:
        source = article_dir / "assets"
        if not source.exists():
            return
        target = PUBLIC_DIR / "media" / "articles" / slug / "assets"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)

    @staticmethod
    def text_stats(source_text: str) -> dict[str, int]:
        stripped = re.sub(r"%.*", "", source_text)
        stripped = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{([^{}]*)\})?", r" \1 ", stripped)
        stripped = re.sub(r"[^\wА-Яа-яЁё]+", " ", stripped, flags=re.UNICODE)
        words = [word for word in stripped.split() if word]
        return {"words": len(words), "chars": len(source_text)}

    @staticmethod
    def article_path(lang: str, slug: str) -> str:
        return f"/{lang}/articles/{slug}"

    @staticmethod
    def article_pdf_path(lang: str, slug: str) -> str:
        return f"{Html.article_path(lang, slug)}.pdf"


def run() -> None:
    Html().run()
