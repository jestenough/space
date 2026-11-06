from __future__ import annotations

import unittest

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

    def test_base_template_uses_shared_boot_script(self) -> None:
        head = Head().build(self.route, {"scripts": [], "styles": []})
        html = self.templates.render("base.html", head=head, page=self.page)

        self.assertNotIn('data-panels="pending"', html)
        self.assertIn('src="/boot.js"', html)
        self.assertNotIn("applyThemeFromStorage", html)
