"""Pre-build project validation"""

from __future__ import annotations

import logging
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Any

from . import content, routes
from .config import (
    CONTENT_DIR,
    DATE_FORMAT_LABEL,
    FILE_TYPES,
    FOLDER_TYPES,
    PACKAGE_JSON,
    REQUIRED_BINARIES,
    ROOT_DIR,
    SRC_DIR,
    SYSTEM_SECTION,
    TSCONFIG,
    VITE_CONFIG,
    ContentExtension,
    FileType,
    FolderType,
)
from .localization import norm_lang
from .rendering import registry

logger = logging.getLogger(__name__)


class Preflight:
    required_binaries = REQUIRED_BINARIES
    required_paths = (ROOT_DIR, CONTENT_DIR, SRC_DIR, PACKAGE_JSON, TSCONFIG, VITE_CONFIG)
    slug_re = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    iso_date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def run(self) -> None:
        self.check_invariants()
        self.check_project_structure()
        self.check_sections()
        self.check_binaries()

        logger.info("Preflight checks passed.")

    @staticmethod
    def check_invariants() -> None:
        if norm_lang("pt-br") != "pt-BR":
            raise RuntimeError("Language normalization invariant failed")

        for actual, expected in {
            routes.item_route(SYSTEM_SECTION, "en", "readme", system=True): "/en/readme",
            routes.item_route("about", "ru", "gpg.asc"): "/ru/about/gpg.asc",
            routes.section_route(SYSTEM_SECTION, "en", system=True): "/en",
            routes.generated_pdf_route(
                {"section": "articles", "slug": "hello-world"}, "en"
            ): "/en/articles/hello-world.pdf",
        }.items():
            if actual != expected:
                raise RuntimeError(f"Route invariant failed: expected {expected}, got {actual}")

        if (
            content.item_type({}) != FileType.PAGE
            or content.item_type({"type": FileType.ARTICLE.value}) != FileType.ARTICLE
        ):
            raise RuntimeError("Item type invariant failed")

        if (
            content.section_kind({"kind": FolderType.PROJECTS.value}) != FolderType.PROJECTS
            or content.item_type({"type": FileType.PROJECT.value}) != FileType.PROJECT
        ):
            raise RuntimeError("Project type invariant failed")

    def check_binaries(self) -> None:
        if missing := [binary for binary in self.required_binaries if shutil.which(binary) is None]:
            raise RuntimeError(
                "Missing required build tools:\n"
                + "\n".join(f"- {binary}" for binary in missing)
                + "\nInstall them before running the full content pipeline."
            )

    def check_project_structure(self) -> None:
        if missing := [path for path in self.required_paths if not path.exists()]:
            raise RuntimeError("Missing required project paths:\n" + "\n".join(f"- {path}" for path in missing))

    def check_sections(self) -> None:
        sections = content.sections()
        if not sections:
            raise RuntimeError("No content sections found")

        systems = [section.slug for section in sections if section.system]
        if systems != [SYSTEM_SECTION]:
            raise RuntimeError(
                f"Exactly one system section is required and it must be `{SYSTEM_SECTION}`. Found: {systems or 'none'}"
            )

        for section in sections:
            self.check_slug(section.slug)
            self.check_meta(
                section.meta, section.slug, section.path / f"{section.slug}.{ContentExtension.META}", section_meta=True
            )
            for item in section.items:
                self.check_item(section, item)

    def check_item(self, section: content.Section, item: content.Item) -> None:
        self.check_slug(item.slug)
        if not item.sources:
            raise RuntimeError(
                f"Missing sources for item `{item.section}/{item.slug}`.\nExpected files like: {item.path / f'{item.slug}.en.txt'} or {item.path / f'{item.slug}.en.tex'}"
            )

        if len({source.lang for source in item.sources}) != len(item.sources):
            langs = [source.lang for source in item.sources]
            raise RuntimeError(
                f"Duplicate language source in `{item.section}/{item.slug}`: {langs}\nKeep only one source file per language."
            )

        for source in item.sources:
            if not source.path.read_text(encoding="utf-8").strip():
                raise RuntimeError(
                    f"Empty source file: {source.path}\nAdd content or remove this source file and its meta language."
                )

        meta_path = item.path / f"{item.slug}.{ContentExtension.META}"
        self.check_meta(item.meta, item.slug, meta_path, section_meta=False)
        self.check_download(item.meta.get("download"), meta_path)
        self.check_item_languages(item)

        kind = content.item_type(item)
        registry.folder_renderer(section.kind).validate_item_membership(section, item, kind)
        registry.file_renderer(kind).validate_item(section, item)

    def check_meta(self, meta: dict[str, Any], slug: str, path: Path, section_meta: bool) -> None:
        for key in ("slug", "label", "title", "description"):
            if key not in meta:
                raise RuntimeError(f"Missing required meta field `{key}` in {path}")

        if section_meta:
            self.check_section_kind(meta.get("kind"), meta.get("system"), path)

        if meta["slug"] != slug:
            raise RuntimeError(
                f"Slug mismatch in {path}\nFolder slug: `{slug}`\nMeta slug: `{meta['slug']}`\nMake them identical."
            )

        for field in ("label", "title", "description"):
            self.check_localized_field(meta[field], field, path)

        if not section_meta and "date" in meta:
            self.check_date(meta["date"], path)

        if not section_meta:
            self.check_file_type(meta.get("type"), path)

    def check_item_languages(self, item: content.Item) -> None:
        source_langs = {source.lang for source in item.sources}
        meta_path = item.path / f"{item.slug}.{ContentExtension.META}"
        for field in ("label", "title", "description", "status"):
            value = item.meta.get(field)
            if not isinstance(value, dict):
                continue

            meta_langs = {norm_lang(lang) for lang in value.keys()}

            missing_sources = sorted(meta_langs - source_langs)
            if missing_sources:
                expected = [item.path / f"{item.slug}.{lang}.<ext>" for lang in missing_sources]
                raise RuntimeError(
                    f"Meta/source language mismatch in {meta_path}\n"
                    f"Field `{field}` declares languages without source files: {', '.join(missing_sources)}\n"
                    f"Add source files like:\n" + "\n".join(f"- {path}" for path in expected)
                )

            missing_meta = sorted(source_langs - meta_langs)
            if missing_meta:
                sources = [source.path for source in item.sources if source.lang in missing_meta]
                raise RuntimeError(
                    f"Meta/source language mismatch in {meta_path}\n"
                    f"Source files exist, but field `{field}` is missing languages: {', '.join(missing_meta)}\n"
                    f"Either add these languages to `{field}` or remove source files:\n"
                    + "\n".join(f"- {path}" for path in sources)
                )

    def check_slug(self, slug: str) -> None:
        if not self.slug_re.fullmatch(slug):
            raise RuntimeError(
                f"Invalid slug `{slug}`. Use lowercase letters, numbers and hyphens only, for example `hello-world`."
            )

    def check_date(self, value: Any, path: Path) -> None:
        if not isinstance(value, str) or not self.iso_date_re.fullmatch(value):
            raise RuntimeError(f"Invalid `date` in {path}: {value!r}\nUse {DATE_FORMAT_LABEL}, for example 2026-05-07.")

        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise RuntimeError(f"Invalid calendar date in {path}: {value}") from exc

    @staticmethod
    def check_localized_field(value: Any, field: str, path: Path) -> None:
        if not isinstance(value, dict) or not value:
            raise RuntimeError(
                f'`{field}` must be a non-empty localized object in {path}\nExample: "{field}": {{"en": "Title"}}'
            )

        for lang, text in value.items():
            norm_lang(lang)
            if not isinstance(text, str) or not text.strip():
                raise RuntimeError(f"`{field}.{lang}` must be a non-empty string in {path}")

    @staticmethod
    def check_download(value: Any, path: Path) -> None:
        if value is not None and not isinstance(value, bool):
            raise RuntimeError(
                f'`download` must be boolean in {path}\nUse `"download": true` only for files that should expose a raw download route.'
            )

    @staticmethod
    def check_section_kind(kind: Any, system: Any, path: Path) -> None:
        expected = FolderType.SYSTEM if system is True else None
        if kind is None and expected is None:
            return

        if not isinstance(kind, str) or kind not in {value.value for value in FOLDER_TYPES}:
            raise RuntimeError(f"`kind` must be one of {', '.join(value.value for value in FOLDER_TYPES)} in {path}")

        if expected and kind != expected:
            raise RuntimeError(f'System section must use `kind: "{FolderType.SYSTEM.value}"` in {path}')

        if system is not True and kind == FolderType.SYSTEM:
            raise RuntimeError(f'Only the system section may use `kind: "{FolderType.SYSTEM.value}"` in {path}')

    @staticmethod
    def check_file_type(value: Any, path: Path) -> None:
        if value is None:
            return

        if not isinstance(value, str) or value not in {item.value for item in FILE_TYPES}:
            raise RuntimeError(f"`type` must be one of {', '.join(item.value for item in FILE_TYPES)} in {path}")


def run() -> None:
    Preflight().run()
