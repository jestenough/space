"""Shared rendering contexts and route result objects"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .. import content
from ..config import FileType, FolderType
from ..templating import Templates


@dataclass(frozen=True)
class RouteRender:
    route: str
    lang: str
    title: str
    description: str
    canonical_path: str
    alternates: dict[str, str]
    og_type: str
    page: dict[str, Any]
    images: tuple[dict[str, str], ...] = ()
    structured_data: tuple[dict[str, Any], ...] = ()
    indexable: bool = True
    page_count: int = 1


@dataclass(frozen=True)
class Stat:
    key: str
    value: str = ""
    field: str | None = None
    tags: tuple[dict[str, str], ...] = ()
    rule: bool = False


@dataclass(frozen=True)
class TocItem:
    id: str
    text: str
    level: int


@dataclass(frozen=True)
class ListShellContext:
    lang: str
    sections: list[dict[str, Any]]
    active_section: str | None
    welcome_title: str
    welcome_lead: str
    render_command: str
    process: list[Stat]
    stage_html: str


@dataclass(frozen=True)
class FileShellContext:
    lang: str
    sections: list[dict[str, Any]]
    file_type: FileType
    active_section: str | None
    welcome_title: str
    welcome_lead: str
    welcome_command: str
    render_command: str
    process_command: str
    process: list[Stat]
    content_html: str
    back_href: str
    download_text: str
    download_href: str | None = None
    cite_value: str | None = None
    edit_href: str | None = None
    show_cite: bool = False
    show_edit: bool = False
    show_zen: bool = False
    toc: list[TocItem] = field(default_factory=list)
    show_toc: bool = False
    template_context: dict[str, Any] | None = None


@dataclass(frozen=True)
class FolderContext:
    lang: str
    section: dict[str, Any]
    items: list[dict[str, Any]]
    sections: list[dict[str, Any]]
    all_items: list[dict[str, Any]]
    site_meta: dict[str, Any]
    templates: Templates
    ui: dict[str, str]
    service: Any
    page_size: int
    tag: str | None = None
    tags_by_lang: dict[str, set[str]] = field(default_factory=dict)
    articles_by_slug: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def section_slug(self) -> str:
        return str(self.section["slug"])

    @property
    def folder_type(self) -> FolderType:
        return (
            FolderType.SYSTEM
            if self.section.get("system")
            else FolderType(str(self.section.get("kind") or FolderType.FILES))
        )


@dataclass(frozen=True)
class FileIndexContext:
    section: content.Section
    item: content.Item
    languages: list[str]
    tag_section_slug: str | None


@dataclass(frozen=True)
class SourceRenderContext:
    source: content.Source
    item: content.Item
    file_type: FileType
    templates: Templates
    convert_tex_to_html: Callable[[Path, Path, str, str, str], str]
    convert_markdown_to_html: Callable[[Path, Path, str, str], str]


@dataclass(frozen=True)
class LocalizedMetaContext:
    section: content.Section
    item: content.Item
    source: content.Source
    item_meta: dict[str, Any]
    stats: dict[str, int]


@dataclass(frozen=True)
class FilePageContext:
    lang: str
    section: dict[str, Any]
    item: dict[str, Any]
    localized_meta: dict[str, Any]
    content_html: str
    sections: list[dict[str, Any]]
    templates: Templates
    ui: dict[str, str]
    service: Any
    tag_section_slug: str | None

    @property
    def section_slug(self) -> str:
        return str(self.section["slug"])

    @property
    def item_slug(self) -> str:
        return str(self.item["slug"])
