"""Notes folder renderer."""

from __future__ import annotations

import html
from typing import Any, override

from ... import routes
from ...config import DEFAULT_LANG, FolderType
from ..context import FolderContext
from .base import FolderRenderer


class NotesFolderRenderer(FolderRenderer):
    folder_type = FolderType.NOTES
    note_ui_by_lang = {
        DEFAULT_LANG: {"note": "note", "undated": "undated", "empty": "No notes yet."},
        "ru": {"note": "заметка", "undated": "без даты", "empty": "Пока нет заметок."},
    }

    @override
    def command(self, _: FolderContext) -> str:
        return "ls -lt | head -n 4"

    @override
    def stage_html(self, context: FolderContext) -> str:
        notes, total_pages = self.paginate(context.items, context.lang, context.page_size)
        return context.templates.render(
            "folders/notes.html",
            list_title=html.escape(self.title(context)),
            search_placeholder=html.escape(context.ui["search_placeholder"]),
            sort_label=html.escape(context.ui["sort_label"]),
            size_label=html.escape(context.ui["size_label"]),
            date_desc_label=html.escape(context.ui["date_desc_label"]),
            date_asc_label=html.escape(context.ui["date_asc_label"]),
            title_asc_label=html.escape(context.ui["title_asc_label"]),
            title_desc_label=html.escape(context.ui["title_desc_label"]),
            items_html=self.render_note_cards(notes, context.lang, context.page_size),
            pager_class="pager-row hidden" if total_pages <= 1 else "pager-row",
            page_prev=html.escape(context.ui["page_prev"]),
            page_next=html.escape(context.ui["page_next"]),
            page_info=html.escape(f"1/{total_pages}" if total_pages else "0/0"),
        )

    @override
    def process_html(self, context: FolderContext) -> str:
        notes, total_pages = self.paginate(context.items, context.lang, context.page_size)
        shown = min(context.page_size, len(notes))
        cwd = context.service.cwd_for_section(context.section_slug)
        return "".join(
            [
                context.service.shell_command_markup("statfs ~", cwd=cwd),
                context.service.stat_row("Mounted on", f"/{context.lang}/{context.section_slug}"),
                context.service.stat_row("Type", "notes-section"),
                context.service.stat_row("Flags", "ro, localized, indexed, snippets"),
                '<span class="meta-rule" aria-hidden="true"></span>',
                context.service.stat_row("mode", context.section_slug),
                context.service.stat_row("lang", context.lang),
                context.service.stat_row_html("shown", f'<span data-process-field="shown">{shown}</span>'),
                context.service.stat_row_html("total", f'<span data-process-field="total">{len(notes)}</span>'),
                context.service.stat_row_html("page", f'<span data-process-field="page">{1 if total_pages else 0}</span>'),
                context.service.stat_row_html("pages", f'<span data-process-field="pages">{total_pages}</span>'),
            ]
        )

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
    def render_note_cards(notes: list[dict[str, Any]], lang: str, page_size: int | None = None) -> str:
        rows = []
        ui = NotesFolderRenderer.note_ui(lang)
        for index, note in enumerate(notes):
            slug = str(note["slug"])
            href = routes.generated_item_route(note, lang)
            title = str(note.get("title", {}).get(lang) or slug)
            label = str(note.get("label", {}).get(lang) or title)
            description = str(note.get("description", {}).get(lang) or "")
            date = str(note.get("date") or "")
            hidden = " hidden" if page_size is not None and index >= page_size else ""
            search = " ".join(filter(None, [slug, label, title, description, date])).lower()
            rows.append(
                f'<li class="note-card"{hidden} data-list-item data-search="{html.escape(search, quote=True)}" data-sort-title="{html.escape(label.lower(), quote=True)}" data-sort-date="{html.escape(date, quote=True)}"><a class="note-card-link" href="{html.escape(href, quote=True)}" data-internal="true"><span class="note-card-kicker">{html.escape(ui["note"])}</span><strong class="note-card-title">{html.escape(label)}</strong><span class="note-card-description">{html.escape(description)}</span><span class="note-card-date">{html.escape(date or ui["undated"])}</span></a></li>'
            )
        return "".join(rows) or f'<li class="note-empty">{html.escape(ui["empty"])}</li>'

    @staticmethod
    def note_ui(lang: str) -> dict[str, str]:
        try:
            return NotesFolderRenderer.note_ui_by_lang[lang]
        except KeyError as exc:
            raise RuntimeError(
                f"Missing notes UI translations for language `{lang}`. "
                "Add this language to NotesFolderRenderer.note_ui_by_lang in scripts/rendering/folders/notes.py."
            ) from exc
