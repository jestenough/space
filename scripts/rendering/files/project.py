"""Project file renderer and project metadata helpers"""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any, override
from urllib.parse import urlparse

from ... import content, routes
from ...config import ContentExtension, FileType, FolderType
from ...localization import exact_text, strict_text
from ..context import FileIndexContext, FilePageContext, SourceRenderContext
from .base import FileRenderer

META_KEYS = ("projectUrl", "sourceUrl", "stack", "status")
STATUS_KEYS = ("launched", "ready", "development", "planned")
STATUS_ALIASES = {
    "active": "launched",
    "live": "launched",
    "launched": "launched",
    "запущен": "launched",
    "ready": "ready",
    "done": "ready",
    "готов": "ready",
    "development": "development",
    "in development": "development",
    "в разработке": "development",
    "planned": "planned",
    "планируется": "planned",
}
STATUS_LABELS = {
    "default": {
        "launched": "Launched",
        "ready": "Ready",
        "development": "In development",
        "planned": "Planned",
    },
    "ru": {
        "launched": "Запущен",
        "ready": "Готов",
        "development": "В разработке",
        "planned": "Планируется",
    },
}


@dataclass(frozen=True)
class ProjectText:
    open_label: str
    source_label: str
    stack_label: str
    overview_label: str


class ProjectFileRenderer(FileRenderer):
    file_type = FileType.PROJECT

    @override
    def index_meta(self, context: FileIndexContext) -> dict[str, Any]:
        return {key: context.item.meta[key] for key in META_KEYS if key in context.item.meta}

    @override
    def render_source(self, context: SourceRenderContext) -> str:
        item = context.item

        source = context.source
        if source.ext == ContentExtension.TEX:
            body = context.convert_tex_to_html(source.path, item.path, item.section, item.slug)
        elif source.ext == ContentExtension.MARKDOWN:
            body = context.convert_markdown_to_html(source.path, item.path, item.section, item.slug)
        else:
            body = ProjectPresenter.render_plain_text(source.path.read_text(encoding="utf-8"))

        return f'<section class="file-document project-document" data-source="{html.escape(str(source.path))}">{body}</section>\n'

    @override
    def template_context(self, context: FilePageContext) -> dict[str, str]:
        return ProjectPresenter.file_context(context.item, context.lang)

    @override
    def display_name(self, context: FilePageContext) -> str:
        label = exact_text(context.item.get("label"), context.lang)
        title = exact_text(context.item.get("title"), context.lang)

        return label if label and label != title else context.item_slug

    @override
    def validate_item(self, section: content.Section, item: content.Item) -> None:
        if section.kind != FolderType.PROJECTS:
            raise RuntimeError(
                f'Project item `{item.section}/{item.slug}` must live in a section with `kind: "{FolderType.PROJECTS.value}"`.'
            )

        path = item.path / f"{item.slug}.meta"

        self.check_string_list(item.meta.get("stack"), path, "stack")
        self.check_status(item.meta.get("status"), path)
        self.check_url(item.meta.get("projectUrl"), path, "projectUrl", required=False)
        self.check_url(item.meta.get("sourceUrl"), path, "sourceUrl", required=False)

    @staticmethod
    def check_string_list(value: Any, path: object, field: str) -> None:
        if not isinstance(value, list) or not value:
            raise RuntimeError(f"`{field}` must be a non-empty string list in {path}")

        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise RuntimeError(f"`{field}` values must be non-empty strings in {path}")

            normalized = item.strip()

            if normalized in seen:
                raise RuntimeError(f"Duplicate `{field}` value `{normalized}` in {path}")

            seen.add(normalized)

    @staticmethod
    def check_localized_field(value: Any, field: str, path: object) -> None:
        if not isinstance(value, dict) or not value:
            raise RuntimeError(
                f'`{field}` must be a non-empty localized object in {path}\nExample: "{field}": {{"en": "Title"}}'
            )

        for lang, text in value.items():
            if not isinstance(lang, str) or not isinstance(text, str) or not text.strip():
                raise RuntimeError(f"`{field}.{lang}` must be a non-empty string in {path}")

    @staticmethod
    def check_url(value: Any, path: object, field: str, required: bool) -> None:
        if value is None and not required:
            return

        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"`{field}` must be a non-empty URL string in {path}")

        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError(f"`{field}` must be an absolute http(s) URL in {path}")

    @classmethod
    def check_status(cls, value: Any, path: object) -> None:
        if value is None:
            return

        values = value.values() if isinstance(value, dict) else [value]
        for item in values:
            if not isinstance(item, str) or not item.strip():
                raise RuntimeError(f"`status` values must be non-empty strings in {path}")

            if Project.normalize_status(item) not in STATUS_KEYS:
                raise RuntimeError(
                    f"Unsupported `status` value `{item}` in {path}. Expected one of: {', '.join(STATUS_KEYS)}"
                )


PROJECT_TEXT_BY_LANG = {
    "default": ProjectText("open", "source", "stack", "project brief"),
    "ru": ProjectText("открыть", "код", "стек", "карточка проекта"),
}


class ProjectPresenter:
    @staticmethod
    def labels(lang: str) -> ProjectText:
        return PROJECT_TEXT_BY_LANG.get(lang, PROJECT_TEXT_BY_LANG["default"])

    @classmethod
    def render_index(cls, files: list[dict[str, Any]], lang: str) -> str:
        text = cls.labels(lang)
        rows = []
        for index, item in enumerate([item for item in files if lang in item.get("languages", [])], start=1):
            rows.append(cls.render_card(Project(item, lang), index, text))

        return "".join(rows)

    @staticmethod
    def process_stats(files: list[dict[str, Any]]) -> list[tuple[str, str]]:
        project_links = sum(1 for item in files if item.get("projectUrl"))
        stacks = sorted({stack for item in files for stack in Project.string_list(item.get("stack"))})

        return [
            ("project urls", str(project_links)),
            ("stack", ", ".join(stacks) or "n/a"),
        ]

    @staticmethod
    def total_pages(files: list[dict[str, Any]], lang: str, page_size: int) -> int:
        count = sum(1 for item in files if lang in item.get("languages", []))
        return max(1, (count + page_size - 1) // page_size)

    @classmethod
    def render_card(cls, project: "Project", index: int, text: ProjectText) -> str:
        stack = "".join(cls.render_stack_chip(name) for name in project.stack)
        actions = cls.render_actions(project, text)

        return (
            f'<article class="project-card" data-list-item data-search="{html.escape(project.search, quote=True)}" data-sort-title="{html.escape(project.title.lower(), quote=True)}" data-sort-date="{html.escape(project.sort_date, quote=True)}">'
            f'<a class="project-card-main" href="{html.escape(project.href, quote=True)}" data-internal="true">'
            f'<span class="project-orbit" aria-hidden="true">{index:02d}</span>'
            f'<span class="project-kicker project-status project-status--{html.escape(project.status_key, quote=True)}">{html.escape(project.kicker)}</span>'
            f'<strong class="project-title">{html.escape(project.title)}</strong>'
            f'<span class="project-description">{html.escape(project.description)}</span>'
            "</a>"
            f'<div class="project-stack" aria-label="{html.escape(text.stack_label)}">{stack}</div>'
            f'<div class="project-actions">{actions}</div>'
            "</article>"
        )

    @classmethod
    def file_context(cls, item: dict[str, Any], lang: str) -> dict[str, str]:
        project = Project(item, lang)
        text = cls.labels(lang)

        return {
            "project_status": html.escape(project.status),
            "project_status_class": f"project-detail-kicker project-status project-status--{html.escape(project.status_key, quote=True)}",
            "project_title": html.escape(project.title),
            "project_description": html.escape(project.description),
            "project_overview_label": html.escape(text.overview_label),
            "project_stack_label": html.escape(text.stack_label),
            "project_stack_html": "".join(cls.render_stack_chip(name) for name in project.stack),
            "project_actions_html": cls.render_actions(project, text),
        }

    @staticmethod
    def render_plain_text(source_text: str) -> str:
        paragraphs = [paragraph.strip() for paragraph in source_text.strip().split("\n\n") if paragraph.strip()]
        return "".join(f"<p>{html.escape(paragraph)}</p>" for paragraph in paragraphs)

    @staticmethod
    def render_stack_chip(name: str) -> str:
        return f'<span class="project-stack-chip">{html.escape(name)}</span>'

    @classmethod
    def render_actions(cls, project: "Project", text: ProjectText) -> str:
        return "".join(
            [
                cls.external_link(project.project_url, text.open_label),
                cls.external_link(project.source_url, text.source_label),
            ]
        )

    @staticmethod
    def external_link(href: str, label: str) -> str:
        if not href:
            return ""
        else:
            return f'<a class="project-link" href="{html.escape(href, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(label)}</a>'


class Project:
    def __init__(self, item: dict[str, Any], lang: str) -> None:
        self.item = item
        self.lang = lang
        self.section = str(item["section"])
        self.slug = str(item["slug"])
        self.href = routes.generated_item_route(item, lang)
        self.title = strict_text(item.get("title"), lang, f"{self.section}.{self.slug}.title")
        self.description = strict_text(item.get("description"), lang, f"{self.section}.{self.slug}.description")
        raw_status = self.localized(item.get("status"), lang) or "planned"
        self.status_key = self.normalize_status(raw_status)
        self.status = self.status_label(self.status_key, lang)
        self.date = str(item.get("date") or "")
        self.stack = self.string_list(item.get("stack"))
        self.project_url = str(item.get("projectUrl") or "")
        self.source_url = str(item.get("sourceUrl") or "")

    @staticmethod
    def localized(value: Any, lang: str) -> str | None:
        if isinstance(value, dict):
            return exact_text(value, lang)
        elif isinstance(value, str) and value.strip():
            return value.strip()
        else:
            return None

    @staticmethod
    def string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        else:
            return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def normalize_status(value: str) -> str:
        return STATUS_ALIASES.get(value.strip().lower(), value.strip().lower())

    @staticmethod
    def status_label(status_key: str, lang: str) -> str:
        labels = STATUS_LABELS.get(lang, STATUS_LABELS["default"])
        return labels.get(status_key, status_key)

    @property
    def sort_date(self) -> str:
        return self.date

    @property
    def kicker(self) -> str:
        return self.status

    @property
    def search(self) -> str:
        values = [self.slug, self.title, self.description, self.status, *self.stack]
        return " ".join(filter(None, values)).lower()
