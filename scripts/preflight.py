"""Pre-build project validation."""

from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Any

from .config import (
    ARTICLES_DIR,
    CONTENT_DIR,
    DATE_FORMAT_LABEL,
    PACKAGE_JSON,
    ROOT_DIR,
    SITE_META_PATH,
    SRC_DIR,
    SUPPORTED_LANGS,
    TSCONFIG,
    VITE_CONFIG,
)


logger = logging.getLogger(__name__)


class Preflight:
    required_binaries = ("node", "npm", "pandoc", "latexmk", "xelatex")
    required_paths = (
        ROOT_DIR,
        CONTENT_DIR,
        SITE_META_PATH,
        SRC_DIR,
        ARTICLES_DIR,
        PACKAGE_JSON,
        TSCONFIG,
        VITE_CONFIG,
    )
    slug_re = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    source_re = re.compile(r"^(.+)\.([a-z]{2,3}(?:-[A-Za-z]{2})?)\.tex$")
    iso_date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def run(self) -> None:
        self.check_binaries()
        self.check_project_structure()
        self.check_site_meta()
        self.check_articles()
        logger.info("Preflight checks passed.")

    def check_binaries(self) -> None:
        if missing := [
            binary
            for binary in self.required_binaries
            if shutil.which(binary) is None
        ]:
            raise RuntimeError(f"Missing required binaries: {', '.join(missing)}")

    def check_project_structure(self) -> None:
        if missing := [path for path in self.required_paths if not path.exists()]:
            raise RuntimeError("Missing required paths: " + ", ".join(map(str, missing)))

        if (CONTENT_DIR / "articles-index.json").exists():
            raise RuntimeError("content/articles-index.json must not be used")

        if root_tex := sorted(path.name for path in ARTICLES_DIR.glob("*.tex")):
            raise RuntimeError(
                "Article sources must live in content/articles/<slug>/ folders. "
                "Found root .tex: " + ", ".join(root_tex)
            )


    def check_site_meta(self) -> None:
        meta = self.read_meta(SITE_META_PATH)
        pages = meta.get("pages")

        if not isinstance(pages, dict):
            raise RuntimeError(f"Missing `pages` object in {SITE_META_PATH}")

        for page in ("home", "articles", "tags", "tag", "notFound"):
            if page not in pages:
                raise RuntimeError(f"Missing `pages.{page}` in {SITE_META_PATH}")
            page_data = pages[page]
            if not isinstance(page_data, dict):
                raise RuntimeError(f"`pages.{page}` must be an object in {SITE_META_PATH}")
            for field in ("title", "description"):
                self.check_site_localized_field(page_data.get(field), f"pages.{page}.{field}", SITE_META_PATH)

    @staticmethod
    def check_site_localized_field(value: Any, field: str, path: Path) -> None:
        if not isinstance(value, dict):
            raise RuntimeError(f"`{field}` must be an object in {path}")

        for lang in SUPPORTED_LANGS:
            if lang not in value:
                raise RuntimeError(f"Missing `{field}.{lang}` in {path}")
            if not isinstance(value[lang], str) or not value[lang].strip():
                raise RuntimeError(f"`{field}.{lang}` must be a non-empty string in {path}")

    def check_articles(self) -> None:
        found = False

        for article_dir in sorted(ARTICLES_DIR.iterdir()):
            if not article_dir.is_dir():
                continue

            found = True
            self.check_article(article_dir)

        if not found:
            raise RuntimeError("No articles found")

    def check_article(self, article_dir: Path) -> None:
        slug = article_dir.name
        self.check_slug(slug)

        languages = self.read_source_languages(article_dir, slug)
        meta_path = self.source_meta_path(slug)

        if not meta_path.is_file():
            raise RuntimeError(f"Missing article metadata: {meta_path}")

        self.check_meta(self.read_meta(meta_path), slug, languages, meta_path)

        for lang in languages:
            self.check_tex_file(self.source_path(slug, lang))

    def read_source_languages(self, article_dir: Path, slug: str) -> tuple[str, ...]:
        languages: list[str] = []

        for path in sorted(article_dir.iterdir()):
            if not path.is_file() or path.suffix != ".tex":
                continue

            match = self.source_re.fullmatch(path.name)

            if not match:
                raise RuntimeError(f"Article source filename must be <slug>.<lang>.tex: {path}")

            file_slug, raw_lang = match.groups()
            lang = self.normalize_lang(raw_lang)

            if file_slug != slug:
                raise RuntimeError(f"Article source filename must start with folder slug: {path}")

            if lang in languages:
                raise RuntimeError(f"Duplicate language source: {slug}.{lang}")

            languages.append(lang)

        if not languages:
            raise RuntimeError(f"Missing article sources: {article_dir}/*.tex")

        return tuple(sorted(languages))

    @staticmethod
    def normalize_lang(value: str) -> str:
        parts = value.split("-", 1)
        lang = parts[0].lower() if len(parts) == 1 else f"{parts[0].lower()}-{parts[1].upper()}"

        if lang not in SUPPORTED_LANGS:
            raise RuntimeError(f"Unsupported article language: {lang}")

        return lang

    def check_slug(self, slug: str) -> None:
        if not self.slug_re.fullmatch(slug):
            raise RuntimeError(f"Invalid slug: {slug}")

    @staticmethod
    def read_meta(path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON: {path}") from exc

        if not isinstance(data, dict):
            raise RuntimeError(f"meta.json must be an object: {path}")

        return data

    def check_meta(
        self,
        meta: dict[str, Any],
        slug: str,
        languages: tuple[str, ...],
        path: Path,
    ) -> None:
        for key in ("slug", "date", "title", "description", "tags"):
            if key not in meta:
                raise RuntimeError(f"Missing `{key}` in {path}")

        if "languages" in meta:
            raise RuntimeError(f"Do not set languages manually in {path}")

        if meta["slug"] != slug:
            raise RuntimeError(
                f"Article slug mismatch: folder is `{slug}`, meta is `{meta['slug']}`"
            )

        self.check_date(meta["date"], path)
        self.check_tags(meta["tags"], path)

        for field in ("title", "description"):
            self.check_localized_field(meta[field], field, languages, path)

    def check_date(self, value: Any, path: Path) -> None:
        if not isinstance(value, str):
            raise RuntimeError(f"`date` must be a string in {path}")

        if not self.iso_date_re.fullmatch(value):
            raise RuntimeError(f"`date` must use {DATE_FORMAT_LABEL} format in {path}")

        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise RuntimeError(f"Invalid calendar date in {path}: {value}") from exc

    @staticmethod
    def check_tags(tags: Any, path: Path) -> None:
        if not isinstance(tags, list) or not tags:
            raise RuntimeError(f"`tags` must be a non-empty list in {path}")

        seen: set[str] = set()

        for tag in tags:
            if not isinstance(tag, str) or not tag.strip():
                raise RuntimeError(f"Tags must be non-empty strings in {path}")

            normalized = tag.strip()

            if normalized in seen:
                raise RuntimeError(f"Duplicate tag `{normalized}` in {path}")

            seen.add(normalized)

    @staticmethod
    def check_localized_field(
        value: Any,
        field: str,
        languages: tuple[str, ...],
        path: Path,
    ) -> None:
        if not isinstance(value, dict):
            raise RuntimeError(f"`{field}` must be an object in {path}")

        for lang in languages:
            if lang not in value:
                raise RuntimeError(f"Missing `{field}.{lang}` in {path}")

            if not isinstance(value[lang], str) or not value[lang].strip():
                raise RuntimeError(f"`{field}.{lang}` must be a non-empty string in {path}")

    @staticmethod
    def check_tex_file(path: Path) -> None:
        if not path.is_file():
            raise RuntimeError(f"Missing TeX file: {path}")

        if not path.read_text(encoding="utf-8").strip():
            raise RuntimeError(f"Empty TeX file: {path}")

    @staticmethod
    def source_meta_path(slug: str) -> Path:
        return ARTICLES_DIR / slug / f"{slug}.meta.json"

    @staticmethod
    def source_path(slug: str, lang: str) -> Path:
        return ARTICLES_DIR / slug / f"{slug}.{lang}.tex"


def run() -> None:
    Preflight().run()
