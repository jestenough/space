from __future__ import annotations

import unittest
from dataclasses import replace

from scripts.config import TEMPLATES_DIR
from scripts.rendering.context import ListShellContext, RouteRender
from scripts.rendering.head import Head
from scripts.rendering.shell import Shell
from scripts.templating import Templates


class TemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.templates = Templates(TEMPLATES_DIR)
        self.shell = Shell(self.templates, ["en"])
        self.page = self.shell.list(
            ListShellContext(
                lang="en",
                sections=[],
                active_section=None,
                welcome_title="A <script> title",
                welcome_lead="Lead & text",
                render_command="ls -l",
                process=[],
                stage_html="",
            )
        )
        self.route = RouteRender(
            route="/en",
            lang="en",
            title="A <script> title",
            description="Lead & text",
            canonical_path="/en",
            alternates={"en": "/en"},
            og_type="website",
            page=self.page,
        )

    def test_base_template_escapes_values(self) -> None:
        head = Head().build(self.route, {"scripts": ["assets/app.js"], "styles": ["assets/app.css"]})
        html = self.templates.render("base.html", head=head, page=self.page)

        self.assertIn("A &lt;script&gt; title", html)
        self.assertIn("Lead &amp; text", html)
        self.assertIn("/assets/app.js", html)
        self.assertIn("/assets/app.css", html)
        self.assertIn("guest@cray-1:~", html)
        self.assertIn('rel="icon" type="image/svg+xml"', html)
        self.assertIn('property="og:image"', html)
        self.assertIn('name="twitter:card"', html)
        self.assertIn('type="application/rss+xml"', html)
        self.assertIn('"@type":"WebSite"', html)
        self.assertIn('"@type":"Person"', html)
        self.assertIn("[rss]", html)
        self.assertNotIn('id="error-view"', html)

    def test_head_supports_noindex_and_pagination(self) -> None:
        route = replace(self.route, indexable=False, page_count=2)
        head = Head().build(route, {"scripts": [], "styles": []})
        html = self.templates.render("base.html", head=head, page=self.page)

        self.assertIn('content="noindex,follow"', html)
        self.assertIn('rel="next"', html)

    def test_social_image_falls_back_to_png_for_webp(self) -> None:
        self.assertEqual(
            Head.social_image({"url": "https://autophany.space/media/x.webp", "alt": "X"}),
            "https://autophany.space/icons/og-image.png",
        )
        self.assertEqual(
            Head.social_image({"url": "https://autophany.space/media/x.png", "alt": "X"}),
            "https://autophany.space/media/x.png",
        )

    def test_head_renders_page_structured_data(self) -> None:
        route = replace(
            self.route,
            structured_data=(
                {
                    "@type": "BlogPosting",
                    "headline": "Post",
                    "url": "https://autophany.space/en/post",
                },
            ),
        )
        head = Head().build(route, {"scripts": [], "styles": []})
        html = self.templates.render("base.html", head=head, page=self.page)

        self.assertIn('"@type":"BlogPosting"', html)

    def test_base_template_uses_shared_boot_script(self) -> None:
        head = Head().build(self.route, {"scripts": [], "styles": []})
        html = self.templates.render("base.html", head=head, page=self.page)

        self.assertNotIn('data-panels="pending"', html)
        self.assertIn('src="/boot.js"', html)
        self.assertNotIn("applyThemeFromStorage", html)
