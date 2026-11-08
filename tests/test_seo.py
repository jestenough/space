from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from scripts.seo import Seo


class SeoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.seo = Seo()

    def test_sitemap_keeps_images_inside_url_entries(self) -> None:
        sitemap = self.seo.render_sitemap(
            [
                {
                    "path": "/en/articles/hello-world",
                    "lastmod": "2026-05-03",
                    "alternates": {"en": "/en/articles/hello-world", "ru": "/ru/articles/hello-world"},
                    "images": [{"src": "/media/articles/hello-world/assets/grid.webp", "alt": "Grid"}],
                }
            ]
        )
        root = ET.fromstring(sitemap)
        namespaces = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "image": "http://www.google.com/schemas/sitemap-image/1.1",
        }

        urls = root.findall("sm:url", namespaces)
        self.assertEqual(len(urls), 1)
        self.assertIsNone(root.find("image:loc", namespaces))
        image_loc = urls[0].find("image:image/image:loc", namespaces)
        self.assertIsNotNone(image_loc)
        self.assertEqual(image_loc.text, "https://autophany.space/media/articles/hello-world/assets/grid.webp")

    def test_feed_is_valid_rss(self) -> None:
        article = {
            "section": "articles",
            "slug": "hello-world",
            "languages": ["en"],
            "title": {"en": "Hello"},
            "description": {"en": "Description"},
            "date": "2026-05-03",
        }
        site_meta = {"pages": {"articles": {"title": {"en": "Articles"}, "description": {"en": "All articles"}}}}
        feed = self.seo.render_feed("en", [article], site_meta, "articles")
        root = ET.fromstring(feed)

        self.assertEqual(root.tag, "rss")
        item = root.find("channel/item")
        self.assertIsNotNone(item)
        self.assertEqual(item.findtext("title"), "Hello")
        self.assertEqual(item.findtext("link"), "https://autophany.space/en/articles/hello-world")

    def test_section_indexability_skips_empty_sections(self) -> None:
        files = [{"section": "articles", "languages": ["en"]}]
        by_section = self.seo.files_by_section_lang(files)
        tags_by_lang = {"en": {"tex"}}

        self.assertFalse(
            self.seo.section_is_indexable({"slug": "notes", "kind": "notes"}, "en", by_section, tags_by_lang)
        )
        self.assertTrue(
            self.seo.section_is_indexable({"slug": "articles", "kind": "articles"}, "en", by_section, tags_by_lang)
        )
        self.assertTrue(
            self.seo.section_is_indexable({"slug": "tags", "kind": "tags"}, "en", by_section, tags_by_lang)
        )


if __name__ == "__main__":
    unittest.main()
