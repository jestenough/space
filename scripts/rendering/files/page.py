"""Generic page file renderer"""

from __future__ import annotations

from ...config import FileType
from .base import FileRenderer


class PageFileRenderer(FileRenderer):
    file_type = FileType.PAGE
