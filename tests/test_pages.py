from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.config import TEMPLATES_DIR
from scripts.rendering import pages as pages_module
from scripts.rendering.context import ListShellContext, RouteRender
from scripts.rendering.pages import PageCache
from scripts.rendering.shell import Shell
from scripts.templating import Templates


class PageCacheTests(unittest.TestCase):
    def test_page_cache_reuses_matching_route(self) -> None:
        templates = Templates(TEMPLATES_DIR)
        shell = Shell(templates, ["en"])
        page = shell.list(
            ListShellContext(
                lang="en",
                sections=[],
                active_section=None,
                welcome_title="Title",
                welcome_lead="Lead",
                render_command="ls",
                process=[],
                stage_html="",
            )
        )
        route = RouteRender(
            route="/en",
            lang="en",
            title="Title",
            description="Lead",
            canonical_path="/en",
            alternates={"en": "/en"},
            og_type="website",
            page=page,
        )

        cache = PageCache(templates)
        with tempfile.TemporaryDirectory() as directory:
            cache.root = Path(directory)
            first = cache.render(route, {"scripts": [], "styles": []}, lambda: "first")
            second = cache.render(route, {"scripts": [], "styles": []}, lambda: "second")

        self.assertEqual(first, "first")
        self.assertEqual(second, "first")
        self.assertEqual(cache.hits, 1)
        self.assertEqual(cache.misses, 1)

    def test_page_cache_key_includes_site_url(self) -> None:
        templates = Templates(TEMPLATES_DIR)
        cache = PageCache(templates)
        route = RouteRender(
            route="/en",
            lang="en",
            title="Title",
            description="Lead",
            canonical_path="/en",
            alternates={"en": "/en"},
            og_type="website",
            page={},
        )
        original = pages_module.SITE_URL
        try:
            pages_module.SITE_URL = "https://one.example"
            first = cache.key(route, {"scripts": [], "styles": []})
            pages_module.SITE_URL = "https://two.example"
            second = cache.key(route, {"scripts": [], "styles": []})
        finally:
            pages_module.SITE_URL = original

        self.assertNotEqual(first, second)
