"""Small file-based HTML template renderer"""

from __future__ import annotations

import re
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


class TemplateRenderer:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._cache: dict[str, tuple[Path, str]] = {}

    def render(self, relative_path: str, **context: object) -> str:
        cached = self._cache.get(relative_path)
        if cached is None:
            template_path = self.root / relative_path
            cached = (template_path, template_path.read_text(encoding="utf-8"))
            self._cache[relative_path] = cached
        template_path, template = cached

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in context:
                raise RuntimeError(f"Missing template variable `{key}` for {template_path}")
            return str(context[key])

        return PLACEHOLDER_RE.sub(replace, template)
