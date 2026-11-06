"""Small cache eviction helper."""

from __future__ import annotations

import shutil
from pathlib import Path


def prune(root: Path, limit: int) -> None:
    if not root.is_dir():
        return

    entries = list(root.iterdir())
    if len(entries) <= limit:
        return

    entries.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    for path in entries[limit:]:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
