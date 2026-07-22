"""PDF generation step"""

from __future__ import annotations

import logging
import os
import hashlib
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import content
from .config import CACHE_DIR, ITEM_ASSETS_DIR, PUBLIC_DIR, ROOT_DIR, SYSTEM_SECTION, ContentExtension, FileType


@dataclass(frozen=True)
class ArticleSource:
    section: str
    slug: str
    lang: str
    path: Path
    article_dir: Path
    meta_path: Path
    meta: dict[str, Any]


logger = logging.getLogger(__name__)


class Pdf:
    force = os.environ.get("FORCE_PDF") == "1"
    strict = os.environ.get("STRICT_PDF") == "1"
    REQUIRED_BINARIES = ("latexmk", "xelatex")

    def run(self) -> None:
        if not self.check_compiler():
            return

        sources = self.scan_sources()
        if not sources:
            raise RuntimeError("No article sources found")

        built = skipped = 0
        for source in sources:
            output = self.public_pdf_path(source)
            fingerprint = self.fingerprint(source)
            if not self.force and self.is_fresh(source, output, fingerprint):
                skipped += 1
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            self.build_pdf(source, output)
            fingerprint_path = self.fingerprint_path(source)
            fingerprint_path.parent.mkdir(parents=True, exist_ok=True)
            fingerprint_path.write_text(f"{fingerprint}\n", encoding="utf-8")
            built += 1

        logger.info("Generated %s PDF(s), skipped %s, total %s.", built, skipped, len(sources))

    @staticmethod
    def scan_sources() -> list[ArticleSource]:
        sources: list[ArticleSource] = []
        for section in content.sections():
            for item in section.items:
                if content.item_type(item) != FileType.ARTICLE:
                    continue

                for source in item.sources:
                    if source.ext == ContentExtension.TEX:
                        sources.append(
                            ArticleSource(
                                section=section.slug,
                                slug=item.slug,
                                lang=source.lang,
                                path=source.path,
                                article_dir=item.path,
                                meta_path=item.path / f"{item.slug}.meta",
                                meta=item.meta,
                            )
                        )
        return sorted(sources, key=lambda item: f"{item.section}.{item.slug}.{item.lang}")

    def check_compiler(self) -> bool:
        missing = [binary for binary in self.REQUIRED_BINARIES if shutil.which(binary) is None]
        if not missing:
            return True

        message = "Missing PDF build tools: " + ", ".join(missing)
        if self.strict:
            raise RuntimeError(message)

        logger.warning("Skipping PDF generation: %s", message)

        return False

    @classmethod
    def is_fresh(cls, source: ArticleSource, pdf_path: Path, fingerprint: str) -> bool:
        fingerprint_path = cls.fingerprint_path(source)
        return (
            pdf_path.exists()
            and pdf_path.stat().st_size > 0
            and fingerprint_path.is_file()
            and fingerprint_path.read_text(encoding="utf-8").strip() == fingerprint
        )

    @staticmethod
    def fingerprint_path(source: ArticleSource) -> Path:
        return CACHE_DIR / "pdf" / source.section / f"{source.slug}.{source.lang}.sha256"

    @classmethod
    def fingerprint(cls, source: ArticleSource) -> str:
        digest = hashlib.sha256()
        for path in cls.dependencies(source):
            relative = path.relative_to(ROOT_DIR) if path.is_relative_to(ROOT_DIR) else Path(path.name)
            digest.update(str(relative).encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
        return digest.hexdigest()

    @staticmethod
    def dependencies(source: ArticleSource) -> list[Path]:
        dependencies = [source.path, source.meta_path, Path(__file__)]
        bibliography = source.article_dir / f"references.{source.lang}.bib"
        if bibliography.is_file():
            dependencies.append(bibliography)
        assets = source.article_dir / ITEM_ASSETS_DIR
        if assets.is_dir():
            dependencies.extend(sorted(path for path in assets.rglob("*") if path.is_file()))
        return dependencies

    def build_pdf(self, source: ArticleSource, output: Path) -> None:
        with tempfile.TemporaryDirectory(prefix=f"autophany-{source.slug}-{source.lang}-") as temp_dir:
            work_dir = Path(temp_dir)
            source_text = source.path.read_text(encoding="utf-8")
            bibliography = source.article_dir / f"references.{source.lang}.bib"

            main_tex = work_dir / "main.tex"
            main_tex.write_text(
                source_text
                if self.is_standalone_latex(source_text)
                else self.wrap_latex_fragment(
                    source_text,
                    source.slug,
                    source.lang,
                    source.meta,
                    bibliography.is_file(),
                ),
                encoding="utf-8",
            )
            if bibliography.is_file():
                shutil.copy2(bibliography, work_dir / "references.bib")

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

    def wrap_latex_fragment(
        self,
        source_text: str,
        slug: str,
        lang: str,
        meta: dict[str, Any],
        has_bibliography: bool,
    ) -> str:
        byline = self.render_byline(meta, lang)
        bibliography = "\n\\bibliographystyle{unsrt}\n\\bibliography{references}" if has_bibliography else ""
        reference_name = r"\renewcommand{\refname}{Источники}" if lang == "ru" else ""
        document_language = "russian" if lang == "ru" else "english"
        return rf"""\documentclass[11pt]{{article}}
\usepackage[a4paper,margin=25mm]{{geometry}}
\usepackage{{fontspec}}
\usepackage[{document_language}]{{babel}}
\setmainfont{{DejaVu Serif}}
\setsansfont{{DejaVu Sans}}
\setmonofont{{DejaVu Sans Mono}}
\usepackage{{hyperref}}
\hypersetup{{colorlinks=true,linkcolor=blue,urlcolor=blue}}
\usepackage{{enumitem}}
\usepackage{{graphicx}}
\usepackage{{xparse}}
\setlist{{itemsep=0.25em}}
\ProvideDocumentCommand{{\citetext}}{{m o m}}{{#3~\IfNoValueTF{{#2}}{{\cite{{#1}}}}{{\cite[#2]{{#1}}}}}}
{reference_name}
\title{{{self.escape_latex(slug)}}}
\date{{}}
\begin{{document}}
{byline}
{source_text}
{bibliography}
\end{{document}}
"""

    def render_byline(self, meta: dict[str, Any], lang: str) -> str:
        author = meta.get("author")
        coauthors = meta.get("coAuthors")
        author_label = "Автор" if lang == "ru" else "Author"
        coauthors_label = "Соавторы" if lang == "ru" else "Co-Authors"
        lines: list[str] = []
        if isinstance(author, dict) and isinstance(author.get("name"), str) and author["name"].strip():
            lines.append(
                rf"\noindent\textbf{{{self.escape_latex(author_label)}:}} {self.person_latex(author)}\\"
            )
        if isinstance(coauthors, list):
            rendered = [self.person_latex(person) for person in coauthors if isinstance(person, dict)]
            if rendered:
                lines.append(
                    rf"\noindent\textbf{{{self.escape_latex(coauthors_label)}:}} {', '.join(rendered)}\\"
                )
        return "\n".join(lines) + ("\n\\medskip" if lines else "")

    def person_latex(self, person: dict[str, Any]) -> str:
        name = self.escape_latex(str(person.get("name") or ""))
        url = person.get("url")
        return rf"\href{{{str(url)}}}{{{name}}}" if isinstance(url, str) and url else name

    @staticmethod
    def escape_latex(value: str) -> str:
        return "".join(
            {
                "&": r"\&",
                "%": r"\%",
                "$": r"\$",
                "#": r"\#",
                "_": r"\_",
                "{": r"\{",
                "}": r"\}",
                "~": r"\textasciitilde{}",
                "^": r"\textasciicircum{}",
            }.get(char, char)
            for char in value
        )

    @staticmethod
    def copy_images(article_dir: Path, work_dir: Path) -> None:
        source_dir = article_dir / ITEM_ASSETS_DIR
        if source_dir.exists():
            shutil.copytree(source_dir, work_dir / ITEM_ASSETS_DIR, dirs_exist_ok=True)

    def run_compiler(self, work_dir: Path, main_tex: Path) -> None:
        command = [
            "latexmk",
            "-xelatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-outdir={work_dir}",
            str(main_tex),
        ]
        completed = subprocess.run(
            command,
            cwd=work_dir,
            text=True,
            capture_output=True,
            timeout=60,
        )

        pdf_path = work_dir / "main.pdf"
        if completed.returncode != 0 or not pdf_path.exists() or pdf_path.stat().st_size == 0:
            output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
            raise RuntimeError(
                "latexmk failed before producing main.pdf\n"
                f"Command: {' '.join(command)}\n"
                f"Compiler output:\n{output[-6000:] or '(empty)'}"
            )


def run() -> None:
    Pdf().run()
