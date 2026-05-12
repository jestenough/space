"""PDF generation step."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import content
from .config import ARTICLE_TYPE, ITEM_ASSETS_DIR, PDF_REQUIRED_BINARIES, PUBLIC_DIR, SYSTEM_SECTION, TEX_FORMAT


@dataclass(frozen=True)
class ArticleSource:
    section: str
    slug: str
    lang: str
    path: Path
    article_dir: Path


logger = logging.getLogger(__name__)


class Pdf:
    force = os.environ.get("FORCE_PDF") == "1"
    strict = os.environ.get("STRICT_PDF") == "1"

    def run(self) -> None:
        if not self.check_compiler():
            return
        sources = self.scan_sources()
        if not sources:
            raise RuntimeError("No article sources found")

        built = skipped = 0
        for source in sources:
            output = self.public_pdf_path(source)
            if not self.force and self.is_fresh(source.path, output):
                skipped += 1
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            self.build_pdf(source, output)
            built += 1

        logger.info("Generated %s PDF(s), skipped %s, total %s.", built, skipped, len(sources))

    @staticmethod
    def scan_sources() -> list[ArticleSource]:
        sources: list[ArticleSource] = []
        for section in content.sections():
            for item in section.items:
                if content.item_type(item) != ARTICLE_TYPE:
                    continue
                for source in item.sources:
                    if source.ext == TEX_FORMAT:
                        sources.append(ArticleSource(section=section.slug, slug=item.slug, lang=source.lang, path=source.path, article_dir=item.path))
        return sorted(sources, key=lambda item: f"{item.section}.{item.slug}.{item.lang}")

    def check_compiler(self) -> bool:
        missing = [binary for binary in PDF_REQUIRED_BINARIES if shutil.which(binary) is None]
        if not missing:
            return True
        message = "Missing PDF build tools: " + ", ".join(missing)
        if self.strict:
            raise RuntimeError(message)
        logger.warning("Skipping PDF generation: %s", message)
        return False

    @staticmethod
    def is_fresh(source_path: Path, pdf_path: Path) -> bool:
        return pdf_path.exists() and pdf_path.stat().st_mtime >= source_path.stat().st_mtime

    def build_pdf(self, source: ArticleSource, output: Path) -> None:
        with tempfile.TemporaryDirectory(prefix=f"autophany-{source.slug}-{source.lang}-") as temp_dir:
            work_dir = Path(temp_dir)
            source_text = source.path.read_text(encoding="utf-8")
            main_tex = work_dir / "main.tex"
            main_tex.write_text(source_text if self.is_standalone_latex(source_text) else self.wrap_latex_fragment(source_text, source.slug), encoding="utf-8")
            self.copy_images(source.article_dir, work_dir)
            self.run_compiler(work_dir, main_tex)
            shutil.copy2(work_dir / "main.pdf", output)

    @staticmethod
    def public_pdf_path(source: ArticleSource) -> Path:
        if source.section == SYSTEM_SECTION:
            return PUBLIC_DIR / source.lang / f"{source.slug}.pdf"
        return PUBLIC_DIR / source.lang / source.section / f"{source.slug}.pdf"

    @staticmethod
    def is_standalone_latex(source_text: str) -> bool:
        return "\\documentclass" in source_text and "\\begin{document}" in source_text

    def wrap_latex_fragment(self, source_text: str, slug: str) -> str:
        return rf"""\documentclass[11pt]{{article}}
\usepackage[a4paper,margin=25mm]{{geometry}}
\usepackage{{fontspec}}
\setmainfont{{DejaVu Serif}}
\setsansfont{{DejaVu Sans}}
\setmonofont{{DejaVu Sans Mono}}
\usepackage{{hyperref}}
\hypersetup{{colorlinks=true,linkcolor=blue,urlcolor=blue}}
\usepackage{{enumitem}}
\usepackage{{graphicx}}
\setlist{{itemsep=0.25em}}
\title{{{self.escape_latex(slug)}}}
\date{{}}
\begin{{document}}
{source_text}
\end{{document}}
"""

    @staticmethod
    def escape_latex(value: str) -> str:
        return "".join({"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}.get(char, char) for char in value)

    @staticmethod
    def copy_images(article_dir: Path, work_dir: Path) -> None:
        source_dir = article_dir / ITEM_ASSETS_DIR
        if source_dir.exists():
            shutil.copytree(source_dir, work_dir / ITEM_ASSETS_DIR, dirs_exist_ok=True)

    def run_compiler(self, work_dir: Path, main_tex: Path) -> None:
        command = ["latexmk", "-xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-outdir={work_dir}", str(main_tex)]
        completed = subprocess.run(command, cwd=work_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        pdf_path = work_dir / "main.pdf"
        if completed.returncode != 0 or not pdf_path.exists() or pdf_path.stat().st_size == 0:
            raise RuntimeError("latexmk failed before producing main.pdf")


def run() -> None:
    Pdf().run()
