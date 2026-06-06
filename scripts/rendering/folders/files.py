"""Generic files folder renderer."""

from __future__ import annotations

from ...config import FolderType
from .base import FolderRenderer


class FilesFolderRenderer(FolderRenderer):
    folder_type = FolderType.FILES
