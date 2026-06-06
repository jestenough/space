"""System/home folder renderer"""

from __future__ import annotations

from ...config import FolderType
from .files import FilesFolderRenderer


class SystemFolderRenderer(FilesFolderRenderer):
    folder_type = FolderType.SYSTEM
