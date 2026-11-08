"""Structured data builders for prerendered pages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .. import routes
from ..config import SITE_URL

if TYPE_CHECKING:
    from .context import RouteRender

SITE_NAME = "Autophany Space"
PERSON_NAME = "Vyacheslav Dmitriev"
PERSON_URL = "https://github.com/jestenough"
PERSON_SAME_AS = ("https://github.com/jestenough", "https://t.me/jestenough")
DEFAULT_SOCIAL_IMAGE = "/icons/og-image.png"


def website_id() -> str:
    return f"{SITE_URL}/#website"


def person_id() -> str:
    return f"{SITE_URL}/#person"


def website(lang: str) -> dict[str, Any]:
    return {
        "@type": "WebSite",
        "@id": website_id(),
        "url": SITE_URL,
        "name": SITE_NAME,
        "inLanguage": lang,
    }


def person() -> dict[str, Any]:
    return {
        "@type": "Person",
        "@id": person_id(),
        "name": PERSON_NAME,
        "url": PERSON_URL,
        "sameAs": list(PERSON_SAME_AS),
    }


def web_page(route: RouteRender) -> dict[str, Any]:
    canonical = routes.absolute_url(route.canonical_path)
    return {
        "@type": "WebPage",
        "@id": f"{canonical}#webpage",
        "url": canonical,
        "name": route.title,
        "description": route.description,
        "inLanguage": route.lang,
        "isPartOf": {"@id": website_id()},
    }


def blog_posting(article: dict[str, Any], lang: str, images: list[dict[str, str]]) -> dict[str, Any]:
    canonical = routes.absolute_url(routes.generated_item_route(article, lang))
    payload: dict[str, Any] = {
        "@type": "BlogPosting",
        "@id": f"{canonical}#article",
        "headline": article["title"][lang],
        "description": article["description"][lang],
        "datePublished": str(article.get("date") or ""),
        "dateModified": str(article.get("date") or ""),
        "inLanguage": lang,
        "mainEntityOfPage": canonical,
        "url": canonical,
        "isPartOf": {"@id": website_id()},
        "publisher": {"@type": "Person", "name": PERSON_NAME, "url": PERSON_URL},
    }

    authors = [
        {
            key: value
            for key, value in {
                "@type": "Person",
                "name": str(person["name"]),
                "url": str(person.get("url") or ""),
            }.items()
            if value
        }
        for person in [article.get("author"), *article.get("coAuthors", [])]
        if isinstance(person, dict) and person.get("name")
    ]
    if authors:
        payload["author"] = authors

    image_urls = [
        routes.absolute_url(image["src"])
        for image in images
        if isinstance(image.get("src"), str) and image["src"].startswith("/media/")
    ]
    if image_urls:
        payload["image"] = image_urls

    return payload


def graph(*nodes: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@graph": [node for node in nodes if node],
    }
