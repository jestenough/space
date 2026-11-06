"""Project file renderer and project metadata helpers"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, override
from urllib.parse import urlparse

from ... import content, routes
from ...config import ContentExtension, FileType, FolderType
from ...localization import exact_text, strict_text
from ..context import FileIndexContext, FilePageContext, SourceRenderContext, Stat
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
        content = ""
        paragraphs: list[str] = []

        if source.ext == ContentExtension.TEX:
            content = context.convert_tex_to_html(source.path, item.path, item.section, item.slug, source.lang)
        elif source.ext == ContentExtension.MARKDOWN:
            content = context.convert_markdown_to_html(source.path, item.path, item.section, item.slug)
        else:
            paragraphs = ProjectPresenter.paragraphs(source.path.read_text(encoding="utf-8"))

        return context.templates.render(
            "files/project_body.html",
            source_path=str(source.path),
            content=content,
            paragraphs=paragraphs,
        )

    @override
    def template_context(self, context: FilePageContext) -> dict[str, Any]:
        return ProjectPresenter.file_context(context.item, context.lang)

    @override
    def display_name(self, context: FilePageContext) -> str:
        label = exact_text(context.item.get("label"), context.lang)
        title = exact_text(context.item.get("title"), context.lang)

        return label or title or context.item_slug

    @override
    def process(self, context: FilePageContext, display_name: str) -> list[Stat]:
        file_path = self.display_file_path(context.section_slug, display_name)
        stack = ", ".join(context.item.get("stack", []))

        return [
            Stat("File", file_path),
            Stat("Size", str(context.localized_meta.get("byteSize") or 0)),
            Stat("Stack", stack),
            Stat("lang", context.lang),
            Stat("type", str(context.item.get("type") or FileType.PROJECT)),
        ]

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
    def cards(cls, files: list[dict[str, Any]], lang: str, page_size: int) -> list[dict[str, Any]]:
        text = cls.labels(lang)
        localized = [item for item in files if lang in item.get("languages", [])]
        localized.sort(
            key=lambda item: (
                str(item.get("date") or ""),
                str(item.get("label", {}).get(lang) or item.get("slug") or ""),
            ),
            reverse=True,
        )
        rows = []
        for index, item in enumerate(localized, start=1):
            project = Project(item, lang)
            rows.append(
                {
                    "index": index,
                    "href": project.href,
                    "label": project.label,
                    "description": project.description,
                    "status": project.status,
                    "status_key": project.status_key,
                    "stack": project.stack,
                    "stack_label": text.stack_label,
                    "actions": cls.actions(project, text),
                    "date": project.sort_date,
                    "search": project.search,
                    "hidden": index > page_size,
                }
            )
        return rows

    @staticmethod
    def process_stats(files: list[dict[str, Any]]) -> list[Stat]:
        project_links = sum(1 for item in files if item.get("projectUrl"))
        stacks = sorted({stack for item in files for stack in Project.string_list(item.get("stack"))})

        return [
            Stat("project urls", str(project_links)),
            Stat("stack", ", ".join(stacks) or "n/a"),
        ]

    @staticmethod
    def total_pages(files: list[dict[str, Any]], lang: str, page_size: int) -> int:
        count = sum(1 for item in files if lang in item.get("languages", []))
        return max(1, (count + page_size - 1) // page_size)

    @classmethod
    def file_context(cls, item: dict[str, Any], lang: str) -> dict[str, Any]:
        project = Project(item, lang)
        text = cls.labels(lang)

        return {
            "project_status": project.status,
            "project_status_class": f"project-detail-kicker project-status project-status--{project.status_key}",
            "project_title": project.title,
            "project_description": project.description,
            "project_overview_label": text.overview_label,
            "project_stack_label": text.stack_label,
            "project_stack": project.stack,
            "project_actions": cls.actions(project, text),
        }

    @staticmethod
    def paragraphs(source_text: str) -> list[str]:
        return [paragraph.strip() for paragraph in source_text.strip().split("\n\n") if paragraph.strip()]

    @classmethod
    def actions(cls, project: "Project", text: ProjectText) -> list[dict[str, str]]:
        actions = []
        if project.project_url:
            actions.append({"href": project.project_url, "label": text.open_label})
        if project.source_url:
            actions.append({"href": project.source_url, "label": text.source_label})
        return actions


class Project:
    def __init__(self, item: dict[str, Any], lang: str) -> None:
        self.item = item
        self.lang = lang
        self.section = str(item["section"])
        self.slug = str(item["slug"])
        self.href = routes.generated_item_route(item, lang)
        self.label = exact_text(item.get("label"), lang) or self.slug
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
        values = [self.slug, self.label, self.title, self.description, self.status, *self.stack]
        return " ".join(filter(None, values)).lower()
