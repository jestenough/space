"""Readers and typed helpers for generated indexes."""

from __future__ import annotations

from typing import Any, TypedDict

from .config import (
    DEFAULT_LANG, 
    GENERATED_DIR, 
    GENERATED_FILE_META_DIR,
    GENERATED_SECTIONS_DIR, 
    GENERATED_SECTIONS_INDEX_FILE, 
    GENERATED_SECTIONS_NAME,
    FileType,
    FolderType,
)
from .jsonio import read_list, read_object
from .localization import language_list


class GeneratedSection(TypedDict, total=False):
    slug: str
    kind: FolderType
    label: dict[str, str]
    title: dict[str, str]
    description: dict[str, str]
    system: bool
    count: int


class GeneratedItem(TypedDict, total=False):
    section: str
    slug: str
    label: dict[str, str]
    type: FileType
    folderType: FolderType
    fileType: FileType
    format: str
    date: str
    title: dict[str, str]
    description: dict[str, str]
    languages: list[str]
    translations: dict[str, str]
    canonicalPath: str
    downloadPath: str | None
    tags: list[str]
    pdfPath: str


class GeneratedLocalizedItem(TypedDict, total=False):
    section: str
    slug: str
    lang: str
    type: FileType
    fileType: FileType
    canonicalPath: str
    downloadPath: str | None
    pdfPath: str
    sourcePath: str
    wordCount: int
    charCount: int
    readingTime: int
    byteSize: int


def sections() -> list[GeneratedSection]:
    path = GENERATED_DIR / GENERATED_SECTIONS_INDEX_FILE
    return [section for section in read_list(path, str(path)) if isinstance(section, dict)]


def section_items(section: str) -> list[GeneratedItem]:
    return [item for item in read_list(GENERATED_SECTIONS_DIR / f"{section}.json", f"generated/{GENERATED_SECTIONS_NAME}/{section}.json") if isinstance(item, dict)]


def items(sections_index: list[GeneratedSection] | None = None) -> list[GeneratedItem]:
    result: list[GeneratedItem] = []
    for section in sections_index or sections():
        slug = section.get("slug")
        if isinstance(slug, str):
            result.extend(section_items(slug))
    return result


def articles(sections_index: list[GeneratedSection] | None = None) -> list[GeneratedItem]:
    return [item for item in items(sections_index) if item.get("type") == FileType.ARTICLE]


def item_languages(items: list[GeneratedItem]) -> list[str]:
    languages = sorted({lang for item in items for lang in item.get("languages", []) if isinstance(lang, str)})
    return languages or [DEFAULT_LANG]


def section_languages(section: dict[str, Any]) -> list[str]:
    values: set[str] = set()
    for field in ("label", "title", "description"):
        value = section.get(field)
        if isinstance(value, dict):
            values.update(lang for lang in value if isinstance(lang, str))
    return language_list(values)


def collect_tags_by_lang(articles: list[GeneratedItem]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for article in articles:
        tags = [tag for tag in article.get("tags", []) if isinstance(tag, str)]
        for lang in article.get("languages", []):
            if isinstance(lang, str):
                result.setdefault(lang, set()).update(tags)
    return result


def first_section_slug(sections_index: list[GeneratedSection], kind: FolderType) -> str | None:
    for section in sections_index:
        section_kind = FolderType.SYSTEM if section.get("system") else section.get("kind")
        if section_kind == kind:
            slug = section.get("slug")
            if isinstance(slug, str):
                return slug
    return None


def localized_item(section: str, slug: str, lang: str) -> GeneratedLocalizedItem:
    path = GENERATED_FILE_META_DIR / section / f"{slug}.{lang}.json"
    return read_object(path, f"generated/files-meta/{section}/{slug}.{lang}.json")
