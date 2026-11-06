"""Jinja2 environment for all build-time templates."""

from __future__ import annotations

import hashlib
import html
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup


def attr(value: object) -> Markup:
    return Markup(html.escape(str(value or ""), quote=True).replace("\n", "&#10;"))


class Templates:
    def __init__(self, root: Path) -> None:
        self.env = Environment(
            loader=FileSystemLoader(root),
            autoescape=select_autoescape(("html",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.filters["attr"] = attr
        self.fingerprint = self._fingerprint(root)

    @staticmethod
    def _fingerprint(root: Path) -> str:
        digest = hashlib.sha256()
        for path in sorted(root.rglob("*.html")):
            digest.update(path.read_bytes())
        requirements = root.parent / "requirements.txt"
        if requirements.is_file():
            digest.update(requirements.read_bytes())
        return digest.hexdigest()

    def render(self, name: str, **context: object) -> str:
        return self.env.get_template(name).render(**context)
