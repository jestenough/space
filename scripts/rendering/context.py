"""Shared rendering contexts and route result objects"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .. import content
from ..config import FileType, FolderType
from ..templating import TemplateRenderer


@dataclass(frozen=True)
class RouteRender:
    route: str
    lang: str
    title: str
    description: str
    canonical_path: str
    alternates: dict[str, str]
    og_type: str
    shell: dict[str, Any]
    extra_head: str = ""


@dataclass(frozen=True)
class ListShellContext:
    lang: str
    sections: list[dict[str, Any]]
    active_section: str | None
    welcome_title: str
    welcome_lead: str
    render_command: str
    process_html: str
    stage_html: str
    tag: str | None = None


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
    process_html: str
    content_html: str
    back_href: str
    download_text: str
    download_href: str | None = None
    cite_value: str | None = None
    edit_href: str | None = None
    show_cite: bool = False
    show_edit: bool = False
    show_zen: bool = False
    toc_html: str = ""
    show_toc: bool = False
    template_context: dict[str, str] | None = None


@dataclass(frozen=True)
class FolderContext:
    lang: str
    section: dict[str, Any]
    items: list[dict[str, Any]]
    sections: list[dict[str, Any]]
    all_items: list[dict[str, Any]]
    site_meta: dict[str, Any]
    templates: TemplateRenderer
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
    convert_tex_to_html: Callable[[Path, Path, str, str], str]
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
    templates: TemplateRenderer
    ui: dict[str, str]
    service: Any
    tag_section_slug: str | None

    @property
    def section_slug(self) -> str:
        return str(self.section["slug"])

    @property
    def item_slug(self) -> str:
        return str(self.item["slug"])
