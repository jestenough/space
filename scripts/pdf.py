"""PDF generation step."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import ARTICLES_DIR, PUBLIC_DIR, ROOT_DIR


@dataclass(frozen=True)
class ArticleSource:
    slug: str
    lang: str
    path: Path
    article_dir: Path


logger = logging.getLogger(__name__)


class Pdf:
    force = os.environ.get("FORCE_PDF") == "1"
    strict = os.environ.get("STRICT_PDF") == "1"
    docker_image = os.environ.get("PDF_DOCKER_IMAGE", "autophany-space")
    polyglossia_languages = {"en": "english", "ru": "russian"}

    def run(self) -> None:
        compiler = self.resolve_compiler()
        sources = self.scan_sources()
        if not sources:
            raise RuntimeError("No article sources found")
        
        built = skipped = 0
        for source in sources:
            output = self.public_pdf_path(source.slug, source.lang)
            if not self.force and self.is_fresh(source.path, output):
                skipped += 1
                continue
            self.build_pdf(source, output, compiler)
            built += 1
        
        logger.info("Generated %s PDF(s), skipped %s, total %s.", built, skipped, len(sources))

    @staticmethod
    def scan_sources() -> list[ArticleSource]:
        sources: list[ArticleSource] = []
        for article_dir in sorted(ARTICLES_DIR.iterdir()):
            if not article_dir.is_dir():
                continue
            slug = article_dir.name
            for source in sorted(article_dir.glob(f"{slug}.*.tex")):
                lang = source.stem.removeprefix(f"{slug}.")
                sources.append(ArticleSource(slug=slug, lang=lang, path=source, article_dir=article_dir))
        return sorted(sources, key=lambda item: f"{item.slug}.{item.lang}")

    def resolve_compiler(self) -> str:
        if shutil.which("xelatex") is not None:
            return "xelatex"
        if self.docker_image_exists():
            logger.info("Using Docker PDF fallback (%s) because local xelatex is unavailable.", self.docker_image)
            return "docker"
        message = "xelatex is not installed; install texlive-xetex or build/use the Docker toolchain image"
        if self.strict:
            raise RuntimeError(message)
        logger.warning("Skipping PDF generation: %s", message)
        raise SystemExit(0)

    def docker_image_exists(self) -> bool:
        return shutil.which("docker") is not None and subprocess.run(["docker", "image", "inspect", self.docker_image], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

    @staticmethod
    def is_fresh(source_path: Path, pdf_path: Path) -> bool:
        return pdf_path.exists() and pdf_path.stat().st_mtime >= source_path.stat().st_mtime

    def build_pdf(self, source: ArticleSource, output: Path, compiler: str) -> None:
        with tempfile.TemporaryDirectory(prefix=f"autophany-{source.slug}-{source.lang}-") as temp_dir:
            work_dir = Path(temp_dir)
            source_text = source.path.read_text(encoding="utf-8")
            main_tex = work_dir / "main.tex"
            main_tex.write_text(source_text if self.is_standalone_latex(source_text) else self.wrap_latex_fragment(source_text, source.slug, source.lang), encoding="utf-8")
            self.copy_images(source.article_dir, work_dir)
            self.run_compiler(compiler, work_dir, main_tex)
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(work_dir / "main.pdf", output)

    @staticmethod
    def public_pdf_path(slug: str, lang: str) -> Path:
        return PUBLIC_DIR / lang / "articles" / f"{slug}.pdf"

    @staticmethod
    def is_standalone_latex(source_text: str) -> bool:
        return "\\documentclass" in source_text and "\\begin{document}" in source_text

    def wrap_latex_fragment(self, source_text: str, slug: str, lang: str) -> str:
        language = self.polyglossia_languages.get(lang.split("-", 1)[0], "english")
        return rf"""\documentclass[11pt]{{article}}
\usepackage[a4paper,margin=25mm]{{geometry}}
\usepackage{{fontspec}}
\setmainfont{{DejaVu Serif}}
\setsansfont{{DejaVu Sans}}
\setmonofont{{DejaVu Sans Mono}}
\usepackage{{polyglossia}}
\setdefaultlanguage{{{language}}}
\setotherlanguage{{english}}
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
        for directory_name in ("assets", "images"):
            source_dir = article_dir / directory_name
            if source_dir.exists():
                shutil.copytree(source_dir, work_dir / directory_name, dirs_exist_ok=True)

    def run_compiler(self, compiler: str, work_dir: Path, main_tex: Path) -> None:
        if compiler == "xelatex":
            command = ["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={work_dir}", str(main_tex)]
            cwd = work_dir
        else:
            command = ["docker", "run", "--rm", "-v", f"{work_dir}:/work", "-w", "/work", self.docker_image, "xelatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory=/work", "/work/main.tex"]
            cwd = ROOT_DIR
        completed = subprocess.run(command, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        pdf_path = work_dir / "main.pdf"
        if completed.returncode != 0 or not pdf_path.exists() or pdf_path.stat().st_size == 0:
            raise RuntimeError(f"{compiler} failed before producing main.pdf")


def run() -> None:
    Pdf().run()
