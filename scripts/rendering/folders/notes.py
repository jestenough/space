"""Notes folder renderer."""

from __future__ import annotations

from typing import Any, override

from ... import routes
from ...config import DEFAULT_LANG, FolderType
from ..context import FolderContext, Stat
from .base import FolderRenderer


class NotesFolderRenderer(FolderRenderer):
    folder_type = FolderType.NOTES
    note_ui_by_lang = {
        DEFAULT_LANG: {"note": "note", "undated": "undated", "empty": "No notes yet."},
        "ru": {"note": "заметка", "undated": "без даты", "empty": "Пока нет заметок."},
    }

    @override
    def command(self, _: FolderContext) -> str:
        return "ls -l -p | grep -v / | sort -k 6,7 -r | head -n 4"

    @override
    def stage_html(self, context: FolderContext) -> str:
        notes, total_pages = self.paginate(context.items, context.lang, context.page_size)
        return context.templates.render(
            "folders/notes.html",
            list_title=self.title(context),
            search_placeholder=context.ui["search_placeholder"],
            sort_label=context.ui["sort_label"],
            size_label=context.ui["size_label"],
            date_desc_label=context.ui["date_desc_label"],
            date_asc_label=context.ui["date_asc_label"],
            title_asc_label=context.ui["title_asc_label"],
            title_desc_label=context.ui["title_desc_label"],
            cards=self.cards(notes, context.lang, context.page_size),
            empty_text=self.note_ui(context.lang)["empty"],
            pager_class="pager-row hidden" if total_pages <= 1 else "pager-row",
            page_prev=context.ui["page_prev"],
            page_next=context.ui["page_next"],
            page_info=f"1/{total_pages}" if total_pages else "0/0",
        )

    @override
    def page_count(self, context: FolderContext) -> int:
        return self.paginate(context.items, context.lang, context.page_size)[1]

    @override
    def process(self, context: FolderContext) -> list[Stat]:
        notes, total_pages = self.paginate(context.items, context.lang, context.page_size)
        shown = min(context.page_size, len(notes))
        return [
            Stat("Mounted on", f"/{context.lang}/{context.section_slug}"),
            Stat("Type", "notes-section"),
            Stat("Flags", "ro, localized, indexed, snippets"),
            Stat("", rule=True),
            Stat("mode", context.section_slug),
            Stat("lang", context.lang),
            Stat("shown", str(shown), field="shown"),
            Stat("total", str(len(notes)), field="total"),
            Stat("page", "1" if total_pages else "0", field="page"),
            Stat("pages", str(total_pages), field="pages"),
        ]

    @staticmethod
    def paginate(items: list[dict[str, Any]], lang: str, page_size: int) -> tuple[list[dict[str, Any]], int]:
        localized_items = [item for item in items if lang in item.get("languages", [])]
        sorted_items = sorted(
            localized_items,
            key=lambda item: (
                str(item.get("date") or ""),
                str(item.get("label", {}).get(lang) or item.get("title", {}).get(lang) or item.get("slug") or ""),
            ),
            reverse=True,
        )
        total_pages = (len(sorted_items) + page_size - 1) // page_size if sorted_items else 0
        return sorted_items, total_pages

    @staticmethod
    def cards(notes: list[dict[str, Any]], lang: str, page_size: int | None = None) -> list[dict[str, Any]]:
        rows = []
        ui = NotesFolderRenderer.note_ui(lang)
        for index, note in enumerate(notes):
            slug = str(note["slug"])
            title = str(note.get("title", {}).get(lang) or slug)
            label = str(note.get("label", {}).get(lang) or title)
            description = str(note.get("description", {}).get(lang) or "")
            date = str(note.get("date") or "")
            rows.append(
                {
                    "href": routes.generated_item_route(note, lang),
                    "label": label,
                    "description": description,
                    "date": date,
                    "date_label": date or ui["undated"],
                    "kicker": ui["note"],
                    "search": " ".join(filter(None, [slug, label, title, description, date])).lower(),
                    "hidden": page_size is not None and index >= page_size,
                }
            )
        return rows

    @staticmethod
    def note_ui(lang: str) -> dict[str, str]:
        try:
            return NotesFolderRenderer.note_ui_by_lang[lang]
        except KeyError as exc:
            raise RuntimeError(
                f"Missing notes UI translations for language `{lang}`. "
                "Add this language to NotesFolderRenderer.note_ui_by_lang in scripts/rendering/folders/notes.py."
            ) from exc
