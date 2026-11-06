"""Document head data for prerendered routes."""

from __future__ import annotations

import json
from typing import Any

from .. import routes
from .context import RouteRender

FONTS = {
    "en": (
        "/fonts/inter/inter-latin.woff2",
        "/fonts/jetbrains-mono/jetbrains-mono-latin.woff2",
    ),
    "ru": (
        "/fonts/inter/inter-cyrillic.woff2",
        "/fonts/jetbrains-mono/jetbrains-mono-cyrillic.woff2",
        "/fonts/inter/inter-latin.woff2",
        "/fonts/jetbrains-mono/jetbrains-mono-latin.woff2",
    ),
}


class Head:
    def build(self, route: RouteRender, assets: dict[str, list[str]]) -> dict[str, Any]:
        images = [
            {"url": url, "alt": str(image.get("alt") or "")}
            for image in route.images
            if (url := self.image_url(image.get("src")))
        ]

        return {
            "lang": route.lang,
            "title": route.title,
            "description": route.description,
            "canonical": routes.absolute_url(route.canonical_path),
            "alternates": {
                lang: routes.absolute_url(path) for lang, path in route.alternates.items()
            },
            "og_type": route.og_type,
            "og_locale": route.lang,
            "scripts": assets.get("scripts", []),
            "styles": assets.get("styles", []),
            "fonts": FONTS.get(route.lang, FONTS["en"]),
            "images": images,
            "json_ld": self.json_ld(route.json_ld),
        }

    @staticmethod
    def image_url(value: Any) -> str:
        src = str(value or "").strip()
        if src.startswith(("http://", "https://")):
            return src
        if src.startswith("/"):
            return routes.absolute_url(src)
        return ""

    @staticmethod
    def json_ld(payload: dict[str, Any] | None) -> str | None:
        if not payload:
            return None

        return (
            json.dumps(payload, ensure_ascii=False)
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026")
        )
