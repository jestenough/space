from __future__ import annotations

import unittest
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "deploy" / "nginx" / "autophany.space.conf"
PREVIEW = Path(__file__).resolve().parents[1] / "deploy" / "nginx" / "preview.conf"


class NginxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = CONFIG.read_text(encoding="utf-8")

    def test_root_redirects_to_default_language(self) -> None:
        self.assertIn("location = /", self.config)
        self.assertIn("return 302 /en;", self.config)

    def test_directory_routes_do_not_redirect(self) -> None:
        self.assertIn("try_files $uri $uri/index.html =404;", self.config)

    def test_security_headers_are_present(self) -> None:
        self.assertIn("Strict-Transport-Security", self.config)
        self.assertIn("Content-Security-Policy", self.config)
        self.assertIn("script-src-attr 'none'", self.config)

    def test_http2_and_quoted_pdf_regex(self) -> None:
        self.assertIn("listen 443 ssl http2;", self.config)
        self.assertNotIn("http2 on;", self.config)
        self.assertIn('location ~ "^/(?<lang>', self.config)

    def test_cache_locations_are_protected_from_regex_override(self) -> None:
        for path in ("/assets/", "/media/", "/fonts/"):
            self.assertIn(f"location ^~ {path}", self.config)

    def test_gzip_static_and_generated_removal(self) -> None:
        self.assertIn("gzip_static on;", self.config)
        self.assertNotIn("/generated/", self.config)

    def test_preview_keeps_directory_routes_without_redirects(self) -> None:
        preview = PREVIEW.read_text(encoding="utf-8")
        self.assertIn("absolute_redirect off;", preview)
        self.assertIn("try_files $uri $uri/index.html =404;", preview)
        self.assertIn("error_page 404 /404.html;", preview)
