"""Content-addressed cache for fully rendered pages."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from functools import lru_cache

from .. import cache
from ..config import CACHE_DIR, CACHE_MAX_ENTRIES, ROOT_DIR, SITE_URL
from ..templating import Templates
from .context import RouteRender


@lru_cache(maxsize=1)
def code_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in sorted((ROOT_DIR / "scripts" / "rendering").rglob("*.py")):
        digest.update(path.read_bytes())
    digest.update((ROOT_DIR / "scripts" / "templating.py").read_bytes())
    return digest.hexdigest()


class PageCache:
    def __init__(self, templates: Templates) -> None:
        self.root = CACHE_DIR / "pages"
        self.templates = templates.fingerprint
        self.force = os.environ.get("FORCE_PAGES") == "1"
        self.hits = 0
        self.misses = 0

    def render(self, route: RouteRender, assets: dict[str, list[str]], build: Callable[[], str]) -> str:
        path = self.root / f"{self.key(route, assets)}.html"
        if not self.force and path.is_file():
            self.hits += 1
            return path.read_text(encoding="utf-8")

        self.misses += 1
        page = build()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page, encoding="utf-8")
        cache.prune(self.root, CACHE_MAX_ENTRIES)
        return page

    def key(self, route: RouteRender, assets: dict[str, list[str]]) -> str:
        digest = hashlib.sha256()
        digest.update(self.templates.encode())
        digest.update(code_fingerprint().encode())
        digest.update(SITE_URL.encode())
        digest.update(json.dumps(assets, sort_keys=True).encode())
        digest.update(repr(route).encode())
        return digest.hexdigest()

    def stats(self) -> str:
        return f"{self.hits} hit(s), {self.misses} miss(es)"
