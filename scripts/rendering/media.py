"""Image metadata and post-processing for generated HTML fragments"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from ..jsonio import read_json
from . import dom


class Media:
    image_tag_re = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
    image_src_re = re.compile(r'\bsrc=(?P<quote>["\'])(?P<value>[^"\']+)(?P=quote)', re.IGNORECASE)

    def __init__(self, manifest: dict[str, dict[str, Any]] | None = None) -> None:
        self.manifest = manifest or {}

    @classmethod
    def load(cls, path: Path) -> "Media":
        if not path.exists():
            return cls()

        data = read_json(path)
        if not isinstance(data, dict):
            raise RuntimeError(f"Media manifest must be an object: {path}")

        return cls({str(key): value for key, value in data.items() if isinstance(value, dict)})

    def enhance(self, content_html: str) -> str:
        if "<img" not in content_html:
            return content_html

        image_index = 0

        def replace(match: re.Match[str]) -> str:
            nonlocal image_index
            tag = match.group(0)
            src_match = self.image_src_re.search(tag)
            if not src_match:
                return tag
            original_src = html.unescape(src_match.group("value"))
            manifest = self.manifest.get(original_src)
            tag = dom.set_tag_attr(tag, "src", str(manifest.get("src") if manifest else original_src))
            first_image = image_index == 0
            image_index += 1
            tag = dom.set_tag_attr(tag, "loading", "eager" if first_image else "lazy")
            tag = dom.set_tag_attr(tag, "decoding", "async")
            tag = dom.set_tag_attr(tag, "fetchpriority", "high" if first_image else "low")
            if manifest:
                tag = self.apply_manifest(tag, manifest)

            if original_src.startswith("/media/"):
                tag = dom.set_tag_attr(tag, "data-zoomable-image", "true")
                tag = dom.set_tag_attr(tag, "data-full-image", str(manifest.get("src") if manifest else original_src))
                tag = dom.add_tag_class(tag, "zoomable-image")

            return tag

        return self.image_tag_re.sub(replace, content_html)

    @staticmethod
    def apply_manifest(tag: str, manifest: dict[str, Any]) -> str:
        width = manifest.get("width")
        height = manifest.get("height")
        if isinstance(width, int) and width > 0:
            tag = dom.set_tag_attr(tag, "width", str(width))

        if isinstance(height, int) and height > 0:
            tag = dom.set_tag_attr(tag, "height", str(height))

        tag = dom.set_tag_attr(tag, "sizes", "(max-width: 900px) 100vw, 72ch")
        variants = manifest.get("variants")
        if isinstance(variants, list) and variants:
            srcset = ", ".join(
                f"{item['src']} {item['width']}w"
                for item in variants
                if isinstance(item, dict) and isinstance(item.get("src"), str) and isinstance(item.get("width"), int)
            )

            if srcset:
                tag = dom.set_tag_attr(tag, "srcset", srcset)

        return tag

    def images(self, content_html: str) -> list[dict[str, str]]:
        images: list[dict[str, str]] = []
        for tag in self.image_tag_re.findall(content_html):
            src_match = self.image_src_re.search(tag)
            if not src_match:
                continue

            src = html.unescape(src_match.group("value"))
            alt_match = re.search(r'\balt=(?P<quote>["\'])(?P<value>[^"\']*)(?P=quote)', tag, re.IGNORECASE)
            images.append({"src": src, "alt": html.unescape(alt_match.group("value")) if alt_match else ""})
        else:
            return images
