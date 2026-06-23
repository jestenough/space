"""Interactive content creation command."""

from __future__ import annotations

import argparse
from enum import StrEnum, auto
import logging
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from .config import CONTENT_DIR, DEFAULT_LANG, ContentExtension, FileType, FolderType
from .jsonio import read_object, write_json
from .localization import norm_lang

logger = logging.getLogger(__name__)


class ContentTarget(StrEnum):
    SECTION = auto()
    ITEM = auto()


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class ExistingSection:
    slug: str
    path: Path
    meta: dict[str, Any]
    kind: FolderType


@dataclass(frozen=True)
class PlannedFile:
    path: Path
    content: str | dict[str, Any]


def configure_parser(parser: argparse.ArgumentParser) -> None:
    parser.description = "Create content sections, items, source files, and metadata"
    parser.epilog = "Example: python3 -m scripts.cli create item --section articles --slug new-post --langs en,ru"
    parser.formatter_class = argparse.RawDescriptionHelpFormatter

    parser.add_argument("target", nargs="?", type=ContentTarget, choices=list(ContentTarget), help="What to create")
    parser.add_argument("--dry-run", action="store_true", help="Print planned files without writing them")
    parser.add_argument("-y", "--yes", action="store_true", help="Don't ask for final confirmation")

    parser.add_argument("--section", help="Existing section slug for a new item")
    parser.add_argument("--slug", help="Slug for the section or item")
    parser.add_argument("--langs", help="Comma-separated source languages, for example en,ru")

    parser.add_argument("--kind", type=FolderType, choices=list(FolderType), help="Section kind")
    parser.add_argument("--type", type=FileType, choices=list(FileType), help="Item file type")
    parser.add_argument("--ext", type=ContentExtension, help="Source file extension. Defaults to tex, md, or txt")
    parser.add_argument("--date", help="Item date in YYYY-MM-DD. Defaults to today in interactive mode")
    parser.add_argument("--no-date", action="store_true", help="Don't add a date field to item metadata")
    parser.add_argument("--tags", help="Comma-separated article tags")
    parser.add_argument("--download", action="store_true", help="Expose raw localized source routes for this item")

    parser.add_argument("--label", action="append", default=[], help="Localized label as LANG=TEXT. May repeat")
    parser.add_argument("--title", action="append", default=[], help="Localized title as LANG=TEXT. May repeat")
    parser.add_argument(
        "--description", action="append", default=[], help="Localized description as LANG=TEXT. May repeat"
    )

    parser.add_argument("--stack", help="Comma-separated project stack values")
    parser.add_argument("--status", help="Project status: launched, ready, development, or planned")
    parser.add_argument("--project-url", help="Project URL for project items.")
    parser.add_argument("--source-url", help="Source URL for project items")


class Creator:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.interactive = sys.stdin.isatty()
        self.supplied = {
            "label": self.parse_localized_pairs(args.label, "label"),
            "title": self.parse_localized_pairs(args.title, "title"),
            "description": self.parse_localized_pairs(args.description, "description"),
        }

    def run(self) -> None:
        target: str = self.args.target or self.ask_choice("Create", choices=ContentTarget, default=ContentTarget.ITEM)

        planned: PlannedFile | None = None
        if target == ContentTarget.SECTION:
            planned = self.plan_section()
        elif target == ContentTarget.ITEM:
            planned = self.plan_item()
        else:
            raise ValueError("Not handled new target unexpected")

        self.check_conflicts(planned)
        self.print_plan(planned, dry_run=self.args.dry_run)

        if self.args.dry_run:
            return

        should_write: bool = self.args.yes or self.confirm("Write these files?", default=True)
        if not should_write:
            logger.info("Cancelled")
            return

        self.write_files(planned)

        logger.info("Created %s file(s).", len(planned))

    def plan_section(self) -> list[PlannedFile]:
        slug: str = self.slug("Section slug", self.args.slug)
        kind: FolderType = self.args.kind or self.ask_choice("Section kind", FolderType, default=FolderType.FILES)
        path = CONTENT_DIR / slug

        system_section_exist: bool = any(section.kind == FolderType.SYSTEM for section in self.existing_sections())
        if kind == FolderType.SYSTEM and system_section_exist:
            raise RuntimeError("A system section already exists. Don't create a second system section")

        langs: list[str] = self.languages()
        localized = self.localized_fields(
            langs,
            slug=slug,
            label_default=f"{slug}/",
            title_default=self.title_from_slug(slug),
            description_default=f"{self.title_from_slug(slug)} section.",
        )

        meta: dict[str, Any] = {"slug": slug}
        if kind != FolderType.FILES:
            meta["kind"] = kind.value
        if kind == FolderType.SYSTEM:
            meta["system"] = True
        meta.update(localized)

        return [PlannedFile(path / f"{slug}.meta", meta)]

    def plan_item(self) -> list[PlannedFile]:
        sections = self.existing_sections()
        if not sections:
            raise RuntimeError("No content sections found. Create a section first with `create section`")

        section: ExistingSection = self.select_section(sections)
        slug: str = self.slug("Item slug", self.args.slug)
        item_type: FileType = self.item_type(section)
        ext: ContentExtension = self.source_extension(item_type)

        langs = self.languages()

        localized = self.localized_fields(
            langs,
            slug=slug,
            label_default=self.default_item_label(slug, item_type, ext),
            title_default=self.title_from_slug(slug),
            description_default=f"TODO: describe {self.title_from_slug(slug)}.",
        )

        meta: dict[str, Any] = {"slug": slug, "type": item_type.value}
        if item_type == FileType.PROJECT:
            meta.update(self.project_meta(langs))
        if not self.args.no_date:
            meta["date"] = self.item_date()
        if item_type == FileType.ARTICLE:
            meta["tags"] = self.tags()
        if self.args.download:
            meta["download"] = True
        meta.update(localized)

        item_dir = section.path / slug
        planned = [PlannedFile(item_dir / f"{slug}.meta", meta)]
        for lang in langs:
            title = localized["title"][lang]
            planned.append(PlannedFile(item_dir / f"{slug}.{lang}.{ext}", self.template(item_type, title)))

        return planned

    def select_section(self, sections: list[ExistingSection]) -> ExistingSection:
        if self.args.section:
            for section in sections:
                if section.slug == self.args.section:
                    return section
            raise RuntimeError(
                f"Unknown section `{self.args.section}`. Existing sections: {', '.join(s.slug for s in sections)}"
            )

        slug = self.ask_choice("Section", [section.slug for section in sections], FolderType.ARTICLES)

        return next(section for section in sections if section.slug == slug)

    def item_type(self, section: ExistingSection) -> FileType:
        if section.kind == FolderType.ARTICLES:
            if self.args.type and self.args.type != FileType.ARTICLE:
                raise RuntimeError(f'Section `{section.slug}` requires `type: "{FileType.ARTICLE.value}"`')
            return FileType.ARTICLE

        if section.kind == FolderType.PROJECTS:
            if self.args.type and self.args.type != FileType.PROJECT:
                raise RuntimeError(f'Section `{section.slug}` requires `type: "{FileType.PROJECT.value}"`')
            return FileType.PROJECT

        choices = [FileType.PAGE.value, FileType.ARTICLE.value]
        value = self.args.type or self.ask_choice("Item type", choices, FileType.PAGE)
        item_type = FileType(value)

        if item_type == FileType.PROJECT:
            raise RuntimeError(f'Project items must live in a section with `kind: "{FolderType.PROJECTS.value}"`')

        return item_type

    def source_extension(self, item_type: FileType) -> ContentExtension:
        ext = self.args.ext or self.ask_choice("Extension", ContentExtension, ContentExtension.TXT)

        if item_type == FileType.ARTICLE and ext != ContentExtension.TEX:
            raise RuntimeError("Article items must use .tex sources only")

        return ext

    def project_meta(self, langs: list[str]) -> dict[str, Any]:
        stack = self.csv_values(self.args.stack) or self.csv_values(self.ask("Project stack", "Python"))
        if not stack:
            raise RuntimeError("Project `stack` must contain at least one value")

        status = self.args.status or self.ask("Project status", "planned")
        meta: dict[str, Any] = {
            "stack": stack,
            "status": {lang: status for lang in langs},
        }

        project_url = (
            self.args.project_url if self.args.project_url is not None else self.ask("Project URL", "", required=False)
        )
        source_url = (
            self.args.source_url if self.args.source_url is not None else self.ask("Source URL", "", required=False)
        )
        if project_url:
            meta["projectUrl"] = project_url
        if source_url:
            meta["sourceUrl"] = source_url

        return meta

    def localized_fields(
        self,
        langs: list[str],
        *,
        slug: str,
        label_default: str,
        title_default: str,
        description_default: str,
    ) -> dict[str, dict[str, str]]:
        result = {"label": {}, "title": {}, "description": {}}
        for lang in langs:
            title = self.supplied["title"].get(lang) or self.ask(f"Title [{lang}]", title_default, required=True)
            label = self.supplied["label"].get(lang) or self.ask(
                f"Label [{lang}]", label_default if label_default else title, required=True
            )
            description = self.supplied["description"].get(lang) or self.ask(
                f"Description [{lang}]", description_default, required=True
            )

            result["title"][lang] = title
            result["label"][lang] = label
            result["description"][lang] = description.replace("{slug}", slug)

        return result

    def languages(self) -> list[str]:
        raw = self.args.langs or self.ask("Languages", ",".join(self.detect_languages()))

        langs = [norm_lang(item.strip()) for item in raw.split(",") if item.strip()]
        if not langs:
            raise RuntimeError("At least one language is required")

        return list(dict.fromkeys(langs))

    def item_date(self) -> str:
        today = date.today().isoformat()
        raw = self.args.date if self.args.date is not None else self.ask("Date YYYY-MM-DD", today, required=False)
        if raw in {"", "-", "none"}:
            return today

        try:
            return date.fromisoformat(raw).isoformat()
        except ValueError as exc:
            raise RuntimeError(f"Invalid date `{raw}`. Use YYYY-MM-DD, for example {today}") from exc

    def tags(self) -> list[str]:
        tags = (
            self.csv_values(self.args.tags)
            if self.args.tags is not None
            else self.csv_values(self.ask("Tags", "notes"))
        )
        if not tags:
            raise RuntimeError("Article `tags` must contain at least one value.")

        return tags

    def slug(self, label: str, value: str | None) -> str:
        slug: str = value or self.ask(label, required=True)

        if not SLUG_RE.fullmatch(slug):
            raise RuntimeError(f"Invalid slug `{slug}`. Use lowercase letters, numbers, and hyphens only")

        return slug

    def ask(self, label: str, default: str | None = None, *, required: bool = True) -> str:
        if not self.interactive:
            if default is not None:
                return default

            if required:
                raise RuntimeError(f"Missing required value: {label}. Pass it as an option or run interactively")

            return ""

        suffix = f" [{default}]" if default is not None else ""
        while True:
            value = input(f"{label}{suffix}: ").strip()
            if value:
                return value

            if default is not None:
                return default

            if not required:
                return ""

            print("Value is required.")

    def ask_choice(self, label: str, choices: Iterable[str], default: str) -> str:
        choices = tuple(choices)

        if default not in choices:
            default = choices[0]

        choices_text = "/".join(choices)

        while True:
            value = self.ask(f"{label} ({choices_text})", default)
            if value in choices:
                return value

            if not self.interactive:
                raise RuntimeError(f"Invalid {label.lower()} `{value}`. Expected one of: {', '.join(choices)}")

            print(f"Expected one of: {', '.join(choices)}")

    def confirm(self, label: str, *, default: bool) -> bool:
        default_text = "Y/n" if default else "y/N"
        value = self.ask(f"{label} ({default_text})", "y" if default else "n", required=False).lower()
        return value in {"y", "yes"}

    @staticmethod
    def parse_localized_pairs(values: list[str], field: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for raw in values:
            if "=" not in raw:
                raise RuntimeError(f"Invalid --{field} value `{raw}`. Use LANG=TEXT, for example en=Hello.")
            lang, text = raw.split("=", 1)
            lang = norm_lang(lang.strip())
            text = text.strip()
            if not text:
                raise RuntimeError(f"Invalid --{field} value `{raw}`. Text must not be empty.")
            result[lang] = text

        return result

    @staticmethod
    def csv_values(raw: str | None) -> list[str]:
        return [item.strip() for item in (raw or "").split(",") if item.strip()]

    @staticmethod
    def title_from_slug(slug: str) -> str:
        return " ".join(part.capitalize() for part in slug.split("-"))

    @staticmethod
    def default_item_label(slug: str, item_type: FileType, ext: str) -> str:
        if item_type == FileType.PAGE:
            return f"{slug}.{ext}"
        return slug

    @staticmethod
    def template(item_type: FileType, title: str) -> str:
        if item_type == FileType.ARTICLE:
            return f"\\section{{{title}}}\n\nWrite the article here.\n"
        elif item_type == FileType.PAGE:
            return f"# {title}\n\nWrite the page here.\n"
        else:
            return f"{title}\n\nWrite the text here.\n"

    @staticmethod
    def existing_sections() -> list[ExistingSection]:
        sections: list[ExistingSection] = []
        if not CONTENT_DIR.exists():
            return sections

        for path in sorted(CONTENT_DIR.iterdir()):
            if not path.is_dir() or path.name.startswith("."):
                continue

            meta = read_object(path / f"{path.name}.meta", "Meta")
            if meta.get("system") is True:
                kind = FolderType.SYSTEM
            else:
                kind = FolderType(str(meta.get("kind") or FolderType.FILES.value))
            sections.append(ExistingSection(slug=path.name, path=path, meta=meta, kind=kind))

        return sections

    @staticmethod
    def detect_languages() -> list[str]:
        if not CONTENT_DIR.exists():
            return [DEFAULT_LANG]

        langs: set[str] = set()

        for meta_path in CONTENT_DIR.rglob("*.meta"):
            try:
                meta = read_object(meta_path, "Meta")
            except RuntimeError:
                continue

            for field in ("label", "title", "description"):
                value = meta.get(field)

                if not isinstance(value, dict):
                    continue

                for lang in value:
                    langs.add(norm_lang(str(lang)))

        return sorted(langs) or [DEFAULT_LANG]

    @staticmethod
    def check_conflicts(planned: list[PlannedFile]) -> None:
        existing = [file.path for file in planned if file.path.exists()]
        if existing:
            raise RuntimeError("Refusing to overwrite existing paths:\n" + "\n".join(f"- {path}" for path in existing))

    @staticmethod
    def print_plan(planned: list[PlannedFile], *, dry_run: bool) -> None:
        prefix = "Would create" if dry_run else "Creating"
        logger.info("%s:", prefix)
        for file in planned:
            logger.info("- %s", file.path.relative_to(CONTENT_DIR.parent))

    @staticmethod
    def write_files(planned: list[PlannedFile]) -> None:
        for file in planned:
            if isinstance(file.content, dict):
                write_json(file.path, file.content)
            else:
                file.path.parent.mkdir(parents=True, exist_ok=True)
                file.path.write_text(file.content, encoding="utf-8")


def run(args: argparse.Namespace | None = None) -> None:
    if args is None:
        parser = argparse.ArgumentParser(prog="python3 -m scripts.create")
        configure_parser(parser)
        args = parser.parse_args()

    Creator(args).run()
