"""Generate HTML fragments, metadata, and section indexes"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import cache, citations, content, routes
from .config import (
    CACHE_DIR,
    CACHE_MAX_ENTRIES,
    DEFAULT_LANG,
    GENERATED_DIR,
    GENERATED_FILE_META_NAME,
    GENERATED_FILES_NAME,
    GENERATED_SECTIONS_INDEX_FILE,
    GENERATED_SECTIONS_NAME,
    GENERATED_SITE_META_FILE,
    HOME_PAGE,
    ITEM_ASSETS_DIR,
    NOT_FOUND_PAGE,
    ROOT_DIR,
    SYSTEM_SECTION,
    TAG_PAGE,
    TEMPLATES_DIR,
    FileType,
    FolderType,
)
from .jsonio import write_json
from .rendering import registry
from .templating import Templates
from .rendering.context import FileIndexContext, LocalizedMetaContext, SourceRenderContext

logger = logging.getLogger(__name__)


class Html:
    asset_src_re = re.compile(
        rf'(?P<prefix>\b(?:src|href)=["\'])(?P<path>{re.escape(ITEM_ASSETS_DIR)}/[^"\']+)(?P<suffix>["\'])'
    )
    comment_re = re.compile(r"%.*")
    tex_command_re = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{([^{}]*)\})?")
    non_word_re = re.compile(r"[^\wА-Яа-яЁё]+")

    def __init__(self, generated_dir: Path = GENERATED_DIR) -> None:
        self.generated_dir = generated_dir
        self.files_dir = generated_dir / GENERATED_FILES_NAME
        self.file_meta_dir = generated_dir / GENERATED_FILE_META_NAME
        self.sections_dir = generated_dir / GENERATED_SECTIONS_NAME
        self.templates = Templates(TEMPLATES_DIR)
        self.tag_section_slug: str | None = None
        self.cache_hits = 0
        self.cache_misses = 0
        self.force = os.environ.get("FORCE_HTML") == "1"

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

        write_json(
            self.generated_dir / GENERATED_SECTIONS_INDEX_FILE, [self.section_meta(section) for section in sections]
        )
        write_json(self.generated_dir / GENERATED_SITE_META_FILE, self.site_meta(sections))

        for section in sections:
            index = [self.item_meta(section, item) for item in section.items]
            indexes[section.slug] = index

        registry.postprocess_indexes(indexes)
        articles = [item for index in indexes.values() for item in index if item.get("type") == FileType.ARTICLE]

        for section in sections:
            index = indexes[section.slug]
            write_json(self.sections_dir / f"{section.slug}.json", index)

        for section in sections:
            index_by_slug = {str(entry["slug"]): entry for entry in indexes[section.slug]}
            for item in section.items:
                self.generate_item(section, item, index_by_slug[item.slug])

        logger.info(
            "Generated indexes for %s section(s) and %s article(s); HTML cache: %s hit(s), %s miss(es).",
            len(sections),
            len(articles),
            self.cache_hits,
            self.cache_misses,
        )

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
        canonical_lang = DEFAULT_LANG if DEFAULT_LANG in languages else languages[0]
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
            "date": date,
            "title": title,
            "description": description,
            "languages": languages,
            "translations": {lang: routes.item_route(section, lang, item.slug) for lang in languages},
            "canonicalPath": routes.item_route(section, canonical_lang, item.slug),
            "downloadPath": self.download_path(section, item, canonical_lang) if self.is_downloadable(item) else None,
            "downloadPaths": {
                lang: path
                for lang in languages
                if self.is_downloadable(item) and (path := self.download_path(section, item, lang))
            },
        }
        meta.update(
            registry.file_renderer(kind).index_meta(
                FileIndexContext(
                    section=section, item=item, languages=languages, tag_section_slug=self.tag_section_slug
                )
            )
        )
        return meta

    @staticmethod
    def download_path(section: content.Section, item: content.Item, lang: str) -> str | None:
        source = next((candidate for candidate in item.sources if candidate.lang == lang), None)
        if not source:
            return None

        suffix = source.ext
        base = f"/{lang}/{item.slug}.{suffix}" if section.system else f"/{lang}/{section.slug}/{item.slug}.{suffix}"

        return base

    def render_source(self, renderer: Any, context: SourceRenderContext) -> str:
        key = self.fingerprint(context)
        cached = CACHE_DIR / "html" / f"{key}.html"
        if not self.force and cached.is_file():
            self.cache_hits += 1
            return cached.read_text(encoding="utf-8")

        self.cache_misses += 1
        rendered = renderer.render_source(context)
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(rendered, encoding="utf-8")
        cache.prune(cached.parent, CACHE_MAX_ENTRIES)
        return rendered

    @classmethod
    def fingerprint(cls, context: SourceRenderContext) -> str:
        digest = hashlib.sha256()
        digest.update(cls.renderer_fingerprint().encode())
        digest.update(context.file_type.value.encode())
        digest.update(str(context.source.path).encode())
        digest.update(context.source.lang.encode())
        digest.update(context.source.path.read_bytes())
        digest.update(json.dumps(context.item.meta, sort_keys=True, ensure_ascii=False, default=str).encode())
        bibliography = context.item.path / f"references.{context.source.lang}.bib"
        if bibliography.is_file():
            digest.update(bibliography.read_bytes())
        return digest.hexdigest()

    @staticmethod
    @lru_cache(maxsize=1)
    def pandoc_version() -> str:
        try:
            result = subprocess.run(["pandoc", "--version"], check=False, text=True, capture_output=True)
        except FileNotFoundError:
            return "missing"
        return (result.stdout.splitlines()[0] if result.stdout else "unknown").strip()

    @classmethod
    @lru_cache(maxsize=1)
    def renderer_fingerprint(cls) -> str:
        digest = hashlib.sha256()
        for path in sorted((ROOT_DIR / "scripts").rglob("*.py")):
            digest.update(path.read_bytes())
        for path in sorted(TEMPLATES_DIR.rglob("*.html")):
            digest.update(path.read_bytes())
        requirements = ROOT_DIR / "requirements.txt"
        if requirements.is_file():
            digest.update(requirements.read_bytes())
        digest.update(cls.pandoc_version().encode())
        return digest.hexdigest()

    def generate_item(self, section: content.Section, item: content.Item, meta: dict[str, Any]) -> None:
        item_type = content.item_type(item)
        renderer = registry.file_renderer(item_type)
        for source in item.sources:
            context = SourceRenderContext(
                source=source,
                item=item,
                file_type=item_type,
                templates=self.templates,
                convert_tex_to_html=self.convert_tex_to_html,
                convert_markdown_to_html=self.convert_markdown_to_html,
            )
            html_text = self.render_source(renderer, context)
            out = self.files_dir / section.slug / f"{item.slug}.{source.lang}.html"
            meta_out = self.file_meta_dir / section.slug / f"{item.slug}.{source.lang}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            meta_out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(html_text, encoding="utf-8")
            item_meta = {
                **meta,
                "lang": source.lang,
                "canonicalPath": routes.item_route(section, source.lang, item.slug),
                "downloadPath": self.download_path(section, item, source.lang) if self.is_downloadable(item) else None,
            }
            stats = self.text_stats(source.path.read_text(encoding="utf-8"))
            item_meta.update(
                {
                    "sourcePath": content.relative_path(source.path),
                    "wordCount": stats["words"],
                    "charCount": stats["chars"],
                    "byteSize": source.path.stat().st_size,
                }
            )
            item_meta.update(
                renderer.localized_meta(
                    LocalizedMetaContext(section=section, item=item, source=source, item_meta=item_meta, stats=stats)
                )
            )
            write_json(meta_out, item_meta)

    @staticmethod
    def is_downloadable(item: content.Item) -> bool:
        return item.meta.get("download") is True

    BIB_FILE = "references.{lang}.bib"

    def convert_tex_to_html(
        self,
        source_path: Path,
        item_dir: Path,
        section: str,
        slug: str,
        lang: str,
    ) -> str:
        bib_path = item_dir / self.BIB_FILE.format(lang=lang)
        source_text = source_path.read_text(encoding="utf-8")

        citations_list: list[citations.Citation] = []
        bib_entries: dict[str, dict[str, str]] = {}
        refs: list[citations.Reference] = []

        if bib_path.is_file() and citations.has_citetext(source_text):
            cleaned_tex, citations_list = citations.preprocess_tex(source_text)
            bib_entries = citations.read_bib(bib_path)
            refs = citations.format_references(bib_entries, citations_list, lang)

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".tex", encoding="utf-8", delete=False
            ) as tmp:
                tmp.write(cleaned_tex)
                tex_input = Path(tmp.name)
        else:
            tex_input = source_path

        command = [
            "pandoc",
            str(tex_input),
            "--from",
            "latex",
            "--to",
            "html5",
            "--mathml",
            "--shift-heading-level-by=1",
            "--resource-path",
            str(item_dir),
        ]
        try:
            result = subprocess.run(command, check=False, text=True, capture_output=True)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Missing required build tool: pandoc\nCannot render TeX source: {source_path}\nInstall pandoc or run `make toolchain` before html generation."
            ) from exc
        finally:
            if tex_input != source_path and tex_input.exists():
                tex_input.unlink(missing_ok=True)

        if result.returncode != 0:
            raise RuntimeError(
                f"Pandoc failed while rendering TeX source: {source_path}\n"
                f"Section/item: {section}/{slug}\n"
                f"Command exited with code {result.returncode}.\n"
                f"stderr:\n{result.stderr.strip() or '(empty)'}"
            )

        html_output = self.rewrite_asset_paths(result.stdout.strip(), section, slug)

        if citations_list:
            html_output = citations.postprocess_html(html_output, citations_list, refs, lang)

        return html_output

    def convert_markdown_to_html(self, source_path: Path, item_dir: Path, section: str, slug: str) -> str:
        command = [
            "pandoc",
            str(source_path),
            "--from",
            "gfm+tex_math_dollars",
            "--to",
            "html5",
            "--mathml",
            "--resource-path",
            str(item_dir),
        ]
        try:
            result = subprocess.run(command, check=False, text=True, capture_output=True)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Missing required build tool: pandoc\nCannot render Markdown source: {source_path}\nInstall pandoc or run `make toolchain` before html generation."
            ) from exc

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
            return f"{match.group('prefix')}/media/{html.escape(section, quote=True)}/{html.escape(slug, quote=True)}/{ITEM_ASSETS_DIR}/{html.escape(file_name, quote=True)}{match.group('suffix')}"

        return self.asset_src_re.sub(replace, value)

    @staticmethod
    def tag_page_meta(tags_page: dict[str, Any]) -> dict[str, Any]:
        title = tags_page.get("title") if isinstance(tags_page.get("title"), dict) else {}
        description = tags_page.get("description") if isinstance(tags_page.get("description"), dict) else {}

        return {
            "title": {lang: f"{text} #{{tag}}" for lang, text in title.items() if isinstance(text, str)},
            "description": description,
        }

    @classmethod
    def text_stats(cls, source_text: str) -> dict[str, int]:
        stripped = cls.comment_re.sub("", source_text)
        stripped = cls.tex_command_re.sub(r" \1 ", stripped)
        stripped = cls.non_word_re.sub(" ", stripped)
        words = [word for word in stripped.split() if word]

        return {"words": len(words), "chars": len(source_text)}


def run() -> None:
    Html().run()
