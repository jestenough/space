"""Small file-based HTML template renderer"""

from __future__ import annotations

import re
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


class TemplateRenderer:
    def __init__(self, root: Path) -> None:
        self.root = root

    def render(self, relative_path: str, **context: object) -> str:
        template_path = self.root / relative_path
        template = template_path.read_text(encoding="utf-8")

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in context:
                raise RuntimeError(f"Missing template variable `{key}` for {template_path}")
            return str(context[key])

        return PLACEHOLDER_RE.sub(replace, template)
