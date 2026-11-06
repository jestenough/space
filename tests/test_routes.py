from __future__ import annotations

import unittest

from scripts import routes


class RouteTests(unittest.TestCase):
    def test_system_routes_skip_section_slug(self) -> None:
        self.assertEqual(routes.item_route("site", "en", "readme"), "/en/readme")
        self.assertEqual(routes.section_route("site", "en"), "/en")

    def test_section_routes_keep_section_slug(self) -> None:
        self.assertEqual(routes.item_route("profile", "ru", "gpg"), "/ru/profile/gpg")
        self.assertEqual(routes.section_route("profile", "ru"), "/ru/profile")

    def test_tag_routes_are_encoded(self) -> None:
        self.assertEqual(routes.tag_route("tags", "ru", "тег"), "/ru/tags/%D1%82%D0%B5%D0%B3")

    def test_alternates_include_default_language(self) -> None:
        self.assertEqual(
            routes.alternates(["en", "ru"], lambda lang: f"/{lang}"),
            {"en": "/en", "ru": "/ru", "x-default": "/en"},
        )
