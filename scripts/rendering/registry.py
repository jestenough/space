"""Explicit renderer registry"""

from __future__ import annotations

from ..config import FileType, FolderType
from .files.article import ArticleFileRenderer
from .files.base import FileRenderer
from .files.page import PageFileRenderer
from .files.project import ProjectFileRenderer
from .folders.articles import ArticlesFolderRenderer
from .folders.base import FolderRenderer
from .folders.files import FilesFolderRenderer
from .folders.notes import NotesFolderRenderer
from .folders.projects import ProjectsFolderRenderer
from .folders.system import SystemFolderRenderer
from .folders.tags import TagsFolderRenderer

FOLDER_RENDERERS: dict[FolderType, FolderRenderer] = {
    FolderType.SYSTEM: SystemFolderRenderer(),
    FolderType.FILES: FilesFolderRenderer(),
    FolderType.ARTICLES: ArticlesFolderRenderer(),
    FolderType.NOTES: NotesFolderRenderer(),
    FolderType.PROJECTS: ProjectsFolderRenderer(),
    FolderType.TAGS: TagsFolderRenderer(),
}

FILE_RENDERERS: dict[FileType, FileRenderer] = {
    FileType.PAGE: PageFileRenderer(),
    FileType.ARTICLE: ArticleFileRenderer(),
    FileType.PROJECT: ProjectFileRenderer(),
}


def folder_renderer(folder_type: FolderType) -> FolderRenderer:
    try:
        return FOLDER_RENDERERS[folder_type]
    except KeyError as exc:
        raise RuntimeError(f"No folder renderer registered for `{folder_type}`") from exc


def file_renderer(file_type: FileType) -> FileRenderer:
    try:
        return FILE_RENDERERS[file_type]
    except KeyError as exc:
        raise RuntimeError(f"No file renderer registered for `{file_type}`") from exc


def postprocess_indexes(indexes: dict[str, list[dict]]) -> None:
    for renderer in FILE_RENDERERS.values():
        renderer.postprocess_indexes(indexes)
