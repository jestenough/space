"""Projects folder renderer"""

from __future__ import annotations

import html
from typing import override

from ...config import FileType, FolderType
from ..context import FolderContext
from ..files import project as project_file
from .base import FolderRenderer


class ProjectsFolderRenderer(FolderRenderer):
    folder_type = FolderType.PROJECTS
    expected_file_type = FileType.PROJECT

    @override
    def stage_html(self, context: FolderContext) -> str:
        total_pages = project_file.ProjectPresenter.total_pages(context.items, context.lang, context.page_size)
        return context.templates.render(
            "folders/projects.html",
            list_title=html.escape(self.title(context)),
            sort_label=html.escape(context.ui["sort_label"]),
            size_label=html.escape(context.ui["size_label"]),
            date_desc_label=html.escape(context.ui["date_desc_label"]),
            date_asc_label=html.escape(context.ui["date_asc_label"]),
            title_asc_label=html.escape(context.ui["title_asc_label"]),
            title_desc_label=html.escape(context.ui["title_desc_label"]),
            items_html=project_file.ProjectPresenter.render_index(context.items, context.lang),
            pager_class="pager-row hidden" if total_pages <= 1 else "pager-row",
            page_prev=html.escape(context.ui["page_prev"]),
            page_next=html.escape(context.ui["page_next"]),
            page_info=html.escape(f"1/{total_pages}"),
        )

    @override
    def extra_stats(self, context: FolderContext) -> list[tuple[str, str]]:
        return project_file.ProjectPresenter.process_stats(context.items)
