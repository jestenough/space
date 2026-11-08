"""Projects folder renderer"""

from __future__ import annotations

from typing import override

from ...config import FileType, FolderType
from ..context import FolderContext, Stat
from ..files import project as project_file
from .base import FolderRenderer


class ProjectsFolderRenderer(FolderRenderer):
    folder_type = FolderType.PROJECTS
    expected_file_type = FileType.PROJECT

    @override
    def command(self, _: FolderContext) -> str:
        return "ls -l -p | grep -v / | sort -k 6,7 -r | head -n 4"

    @override
    def stage_html(self, context: FolderContext) -> str:
        total_pages = project_file.ProjectPresenter.total_pages(context.items, context.lang, context.page_size)
        return context.templates.render(
            "folders/projects.html",
            list_title=self.title(context),
            sort_label=context.ui["sort_label"],
            size_label=context.ui["size_label"],
            date_desc_label=context.ui["date_desc_label"],
            date_asc_label=context.ui["date_asc_label"],
            title_asc_label=context.ui["title_asc_label"],
            title_desc_label=context.ui["title_desc_label"],
            cards=project_file.ProjectPresenter.cards(context.items, context.lang, context.page_size),
            pager_class="pager-row hidden" if total_pages <= 1 else "pager-row",
            page_prev=context.ui["page_prev"],
            page_next=context.ui["page_next"],
            page_info=f"1/{total_pages}",
        )

    @override
    def page_count(self, context: FolderContext) -> int:
        return project_file.ProjectPresenter.total_pages(context.items, context.lang, context.page_size)

    @override
    def extra_stats(self, context: FolderContext) -> list[Stat]:
        return project_file.ProjectPresenter.process_stats(context.items)
