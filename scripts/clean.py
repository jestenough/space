"""
Build cleanup utilities.

Removes generated output, build directories, caches, generated public PDFs,
and generated public media assets.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from .config import DIST_DIR, GENERATED_DIR, PUBLIC_DIR, ROOT_DIR

logger = logging.getLogger(__name__)


class Clean:
    targets = (
        DIST_DIR,
        GENERATED_DIR,
        ROOT_DIR / ".cache",
        ROOT_DIR / ".vite",
    )

    def run(self) -> None:
        for target in self.targets:
            self.remove(target)

        self.remove_generated_public_files()
        logger.info("Removed generated output, caches, public PDFs and media assets.")

    @staticmethod
    def remove(path: Path) -> None:
        shutil.rmtree(path, ignore_errors=True)

    def remove_generated_public_files(self) -> None:
        if not PUBLIC_DIR.exists():
            return

        for pdf in PUBLIC_DIR.rglob("*.pdf"):
            pdf.unlink()

        self.remove(PUBLIC_DIR / "media")


def run() -> None:
    Clean().run()
