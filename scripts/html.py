"""Generate HTML fragments, metadata, and section indexes."""

from __future__ import annotations

import html
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from . import content, routes
from .config import (
    FileType,
    FolderType,
    GENERATED_DIR, 
    GENERATED_FILE_META_NAME, 
    GENERATED_FILES_NAME, 
    GENERATED_SECTIONS_INDEX_FILE, 
    GENERATED_SECTIONS_NAME, 
    GENERATED_SITE_META_FILE, 
    HOME_PAGE, 
    ITEM_ASSETS_DIR, 
    MARKDOWN_FORMAT,
    NOT_FOUND_PAGE, 
    SYSTEM_SECTION, 
    TAG_PAGE, 
    TEX_FORMAT, 
    TEXT_FORMAT, 
    WORDS_PER_MINUTE
)
from .jsonio import write_json
from .localization import exact_text

logger = logging.getLogger(__name__)


class Html:
    asset_src_re = re.compile(rf'(?P<prefix>\b(?:src|href)=["\'])(?P<path>{re.escape(ITEM_ASSETS_DIR)}/[^"\']+)(?P<suffix>["\'])')

    def __init__(self, generated_dir: Path = GENERATED_DIR) -> None:
        self.generated_dir = generated_dir
        self.files_dir = generated_dir / GENERATED_FILES_NAME
        self.file_meta_dir = generated_dir / GENERATED_FILE_META_NAME
        self.sections_dir = generated_dir / GENERATED_SECTIONS_NAME
        self.tag_section_slug: str | None = None

    def run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="autophany-generated-", dir=GENERATED_DIR.parent) as temp_dir:
            output = Path(temp_dir) / GENERATED_DIR.name
            self.generated_dir = output
            self.files_dir = output / GENERATED_FILES_NAME
            self.file_meta_dir = output / GENERATED_FILE_META_NAME
            self.sections_dir = output / GENERATED_SECTIONS_NAME
            self.generate()
            self.publish(output)

    def generate(self) -> None:
        self.prepare()
        sections = content.sections()
        self.tag_section_slug = content.first_section_slug(sections, FolderType.TAGS)
        indexes: dict[str, list[dict[str, Any]]] = {}

        write_json(self.generated_dir / GENERATED_SECTIONS_INDEX_FILE, [self.section_meta(section) for section in sections])
        write_json(self.generated_dir / GENERATED_SITE_META_FILE, self.site_meta(sections))

        for section in sections:
            index = [self.item_meta(section, item) for item in section.items]
            indexes[section.slug] = index

        articles = [item for index in indexes.values() for item in index if item.get("type") == FileType.ARTICLE]
        self.link_neighbors(articles)

        for section in sections:
            index = indexes[section.slug]
            write_json(self.sections_dir / f"{section.slug}.json", index)

        for section in sections:
            index = indexes[section.slug]
            for item in section.items:
                meta = next(entry for entry in index if entry["slug"] == item.slug)
                self.generate_item(section, item, meta)
        logger.info("Generated indexes for %s section(s) and %s article(s).", len(sections), len(articles))

    def prepare(self) -> None:
        for path in (self.files_dir, self.file_meta_dir, self.sections_dir):
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def publish(output: Path) -> None:
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        for entry in GENERATED_DIR.iterdir():
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
        for entry in output.iterdir():
            shutil.move(str(entry), GENERATED_DIR / entry.name)

    @staticmethod
    def section_meta(section: content.Section) -> dict[str, Any]:
        return {
            "slug": section.slug,
            "kind": section.kind,
            "folderType": section.kind,
            "label": section.meta.get("label") or section.meta.get("title") or section.slug,
            "title": section.meta.get("title") or section.meta.get("label") or section.slug,
            "description": section.meta.get("description") or {},
            "system": section.system,
            "count": len(section.items),
        }

    @staticmethod
    def site_meta(sections: list[content.Section]) -> dict[str, Any]:
        pages: dict[str, Any] = {
            section.slug if section.slug != SYSTEM_SECTION else HOME_PAGE: {
                "title": section.meta.get("title") or section.meta.get("label") or section.slug,
                "description": section.meta.get("description") or {},
            }
            for section in sections
        }
        tags_section = next((section for section in sections if section.kind == FolderType.TAGS), None)
        tags = pages.get(tags_section.slug) if tags_section else None
        if tags:
            pages.setdefault(TAG_PAGE, Html.tag_page_meta(tags))
        if home := pages.get(HOME_PAGE):
            pages.setdefault(NOT_FOUND_PAGE, home)
        return {"pages": pages}

    def item_meta(self, section: content.Section, item: content.Item) -> dict[str, Any]:
        languages = content.langs(item.sources)
        kind = content.item_type(item)
        title = item.meta.get("title") or item.meta.get("label") or item.slug
        description = item.meta.get("description") or {}
        date = str(item.meta.get("date") or "")
        meta: dict[str, Any] = {
            "section": section.slug,
            "slug": item.slug,
            "label": item.meta.get("label") or title,
            "type": kind,
            "folderType": section.kind,
            "fileType": kind,
            "format": item.meta.get("format") or self.format_for(item),
            "date": date,
            "title": title,
            "description": description,
            "languages": languages,
            "translations": {lang: routes.item_route(section, lang, item.slug) for lang in languages},
            "canonicalPath": routes.item_route(section, languages[0], item.slug),
            "downloadPath": self.download_path(section, item, languages[0]) if self.is_downloadable(item) else None,
        }
        if kind == FileType.ARTICLE:
            meta["tags"] = self.string_list(item.meta.get("tags", []), f"{item.slug}.tags")
            meta["tagSection"] = self.tag_section_slug
            meta["pdfPath"] = f"{routes.item_route(section, languages[0], item.slug)}.pdf"
            meta["prev"] = None
            meta["next"] = None
        return meta

    @staticmethod
    def format_for(item: content.Item) -> str:
        ext = item.sources[0].ext if item.sources else "txt"
        if ext == TEX_FORMAT:
            return TEX_FORMAT
        if ext == "md":
            return MARKDOWN_FORMAT
        return TEXT_FORMAT

    @staticmethod
    def download_path(section: content.Section, item: content.Item, lang: str) -> str | None:
        source = next((candidate for candidate in item.sources if candidate.lang == lang), None)
        if not source:
            return None
        suffix = source.path.name.removeprefix(f"{item.slug}.{source.lang}.")
        base = f"/{lang}/{item.slug}.{suffix}" if section.system else f"/{lang}/{section.slug}/{item.slug}.{suffix}"
        return base

    def generate_item(self, section: content.Section, item: content.Item, meta: dict[str, Any]) -> None:
        for source in item.sources:
            html_text = self.render_source(source, item)
            out = self.files_dir / section.slug / f"{item.slug}.{source.lang}.html"
            meta_out = self.file_meta_dir / section.slug / f"{item.slug}.{source.lang}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            meta_out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(html_text, encoding="utf-8")
            item_meta = {**meta, "lang": source.lang, "canonicalPath": routes.item_route(section, source.lang, item.slug), "downloadPath": self.download_path(section, item, source.lang) if self.is_downloadable(item) else None}
            stats = self.text_stats(source.path.read_text(encoding="utf-8"))
            item_meta.update({
                "sourcePath": content.relative_path(source.path),
                "wordCount": stats["words"],
                "charCount": stats["chars"],
                "byteSize": source.path.stat().st_size,
            })
            if item_meta.get("type") == FileType.ARTICLE:
                item_meta.update({"pdfPath": f"{routes.item_route(section, source.lang, item.slug)}.pdf", "readingTime": max(1, round(stats["words"] / WORDS_PER_MINUTE))})
            write_json(meta_out, item_meta)

    @staticmethod
    def is_downloadable(item: content.Item) -> bool:
        return item.meta.get("download") is True

    def render_source(self, source: content.Source, item: content.Item) -> str:
        if source.ext == TEX_FORMAT:
            body = self.convert_tex_to_html(source.path, item.path, item.section, item.slug)
            return f"""<article class="article" lang="{html.escape(source.lang)}">
  <div class="article__content">
{body}
  </div>
</article>
"""
        if source.ext == "md":
            body = self.convert_markdown_to_html(source.path, item.path, item.section, item.slug)
        else:
            text = source.path.read_text(encoding="utf-8")
            body = f'<pre class="info-file-pre">{html.escape(text.rstrip())}</pre>'
        return f'<section class="file-document" data-source="{html.escape(str(source.path))}">{body}</section>\n'

    def convert_tex_to_html(self, source_path: Path, item_dir: Path, section: str, slug: str) -> str:
        command = ["pandoc", str(source_path), "--from", "latex", "--to", "html5", "--mathml", "--shift-heading-level-by=1", "--resource-path", str(item_dir)]
        try:
            result = subprocess.run(command, check=False, text=True, capture_output=True)
        except FileNotFoundError as exc:
            raise RuntimeError(f"Missing required build tool: pandoc\nCannot render TeX source: {source_path}\nInstall pandoc or run preflight before html generation.") from exc
        if result.returncode != 0:
            raise RuntimeError(
                f"Pandoc failed while rendering TeX source: {source_path}\n"
                f"Section/item: {section}/{slug}\n"
                f"Command exited with code {result.returncode}.\n"
                f"stderr:\n{result.stderr.strip() or '(empty)'}"
            )
        return self.rewrite_asset_paths(result.stdout.strip(), section, slug)

    def convert_markdown_to_html(self, source_path: Path, item_dir: Path, section: str, slug: str) -> str:
        command = ["pandoc", str(source_path), "--from", "gfm+tex_math_dollars", "--to", "html5", "--mathml", "--resource-path", str(item_dir)]
        try:
            result = subprocess.run(command, check=False, text=True, capture_output=True)
        except FileNotFoundError as exc:
            raise RuntimeError(f"Missing required build tool: pandoc\nCannot render Markdown source: {source_path}\nInstall pandoc or run preflight before html generation.") from exc
        if result.returncode != 0:
            raise RuntimeError(
                f"Pandoc failed while rendering Markdown source: {source_path}\n"
                f"Section/item: {section}/{slug}\n"
                f"Command exited with code {result.returncode}.\n"
                f"stderr:\n{result.stderr.strip() or '(empty)'}"
            )
        return self.rewrite_asset_paths(result.stdout.strip(), section, slug)

    def rewrite_asset_paths(self, value: str, section: str, slug: str) -> str:
        def replace(match: re.Match[str]) -> str:
            file_name = match.group("path").removeprefix(f"{ITEM_ASSETS_DIR}/")
            return f'{match.group("prefix")}/media/{html.escape(section, quote=True)}/{html.escape(slug, quote=True)}/{ITEM_ASSETS_DIR}/{html.escape(file_name, quote=True)}{match.group("suffix")}'
        return self.asset_src_re.sub(replace, value)

    @staticmethod
    def link_neighbors(articles: list[dict[str, Any]]) -> None:
        sorted_articles = sorted(articles, key=lambda item: (item.get("date") or "", item["slug"]), reverse=True)
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
        return {"title": exact_text(article["title"], lang), "path": routes.item_route(article["section"], lang, article["slug"], article["section"] == SYSTEM_SECTION)}

    @staticmethod
    def tag_page_meta(tags_page: dict[str, Any]) -> dict[str, Any]:
        title = tags_page.get("title") if isinstance(tags_page.get("title"), dict) else {}
        description = tags_page.get("description") if isinstance(tags_page.get("description"), dict) else {}
        return {
            "title": {lang: f"{text} #{{tag}}" for lang, text in title.items() if isinstance(text, str)},
            "description": description,
        }

    @staticmethod
    def string_list(value: Any, path: str) -> list[str]:
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise RuntimeError(f"{path} must be a string array")
        return list(dict.fromkeys(item.strip() for item in value))

    @staticmethod
    def text_stats(source_text: str) -> dict[str, int]:
        stripped = re.sub(r"%.*", "", source_text)
        stripped = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{([^{}]*)\})?", r" \1 ", stripped)
        stripped = re.sub(r"[^\wА-Яа-яЁё]+", " ", stripped, flags=re.UNICODE)
        words = [word for word in stripped.split() if word]
        return {
            "words": len(words), 
            "chars": len(source_text)
        }


def run() -> None:
    Html().run()
