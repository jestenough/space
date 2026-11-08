"""Document head data for prerendered routes."""

from __future__ import annotations

import json
from typing import Any

from .. import routes
from . import schema
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
        primary_image = images[0] if images else None
        og_image = self.social_image(primary_image)
        og_image_alt = (primary_image.get("alt") if primary_image else "") or route.title
        payload = schema.graph(
            schema.website(route.lang),
            schema.person(),
            schema.web_page(route),
            *route.structured_data,
        )

        return {
            "lang": route.lang,
            "site_name": schema.SITE_NAME,
            "title": route.title,
            "description": route.description,
            "canonical": routes.absolute_url(route.canonical_path),
            "alternates": {
                lang: routes.absolute_url(path) for lang, path in route.alternates.items()
            },
            "robots": "index,follow" if route.indexable else "noindex,follow",
            "og_type": route.og_type,
            "og_locale": route.lang,
            "og_image": og_image,
            "og_image_alt": og_image_alt,
            "feed": routes.absolute_url(f"/{route.lang}/feed.xml"),
            "list_next": routes.absolute_url(f"{route.canonical_path}?page=2") if route.page_count > 1 else None,
            "scripts": assets.get("scripts", []),
            "styles": assets.get("styles", []),
            "fonts": FONTS.get(route.lang, FONTS["en"]),
            "json_ld": self.json_ld(payload),
        }

    @staticmethod
    def social_image(image: dict[str, str] | None) -> str:
        if image and not image["url"].split("?", 1)[0].lower().endswith(".webp"):
            return image["url"]
        return routes.absolute_url(schema.DEFAULT_SOCIAL_IMAGE)

    @staticmethod
    def image_url(value: Any) -> str:
        src = str(value or "").strip()
        if src.startswith(("http://", "https://")):
            return src
        if src.startswith("/"):
            return routes.absolute_url(src)
        return ""

    @staticmethod
    def json_ld(payload: dict[str, Any]) -> str:
        return (
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026")
        )
