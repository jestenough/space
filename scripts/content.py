"""Section-based content scanner."""

from __future__ import annotations

from functools import lru_cache
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import CONTENT_DIR, DEFAULT_LANG, ITEM_ASSETS_DIR, ITEM_META_SUFFIX, SYSTEM_SECTION, TEXT_TYPE
from .jsonio import read_object
from .localization import norm_lang


@dataclass(frozen=True)
class Source:
    lang: str
    ext: str
    path: Path


@dataclass(frozen=True)
class Item:
    section: str
    slug: str
    path: Path
    meta: dict[str, Any]
    sources: tuple[Source, ...]


@dataclass(frozen=True)
class Section:
    slug: str
    path: Path
    meta: dict[str, Any]
    items: tuple[Item, ...]

    @property
    def system(self) -> bool:
        return bool(self.meta.get("system"))


@lru_cache(maxsize=1)
def sections() -> list[Section]:
    result: list[Section] = []
    for path in sorted(CONTENT_DIR.iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        slug = path.name
        meta = read_object(path / f"{slug}.{ITEM_META_SUFFIX}", "Meta")
        result.append(Section(slug=slug, path=path, meta=meta, items=tuple(items(slug, path))))
    return sorted(result, key=lambda section: (section.slug != SYSTEM_SECTION, section.slug))


def items(section: str, path: Path) -> list[Item]:
    result: list[Item] = []
    for item_dir in sorted(path.iterdir()):
        if not item_dir.is_dir() or item_dir.name == ITEM_ASSETS_DIR or item_dir.name.startswith("."):
            continue
        slug = item_dir.name
        meta = read_object(item_dir / f"{slug}.{ITEM_META_SUFFIX}", "Meta")
        result.append(Item(section=section, slug=slug, path=item_dir, meta=meta, sources=tuple(sources(item_dir, slug))))
    return result


def sources(path: Path, slug: str) -> list[Source]:
    result: list[Source] = []
    prefix = f"{slug}."
    for source in sorted(path.iterdir()):
        if not source.is_file() or not source.name.startswith(prefix) or source.name == f"{slug}.{ITEM_META_SUFFIX}":
            continue
        rest = source.name[len(prefix):]
        if "." not in rest:
            continue
        raw_lang, ext = rest.split(".", 1)
        result.append(Source(lang=norm_lang(raw_lang), ext=ext, path=source))
    return result


def langs(sources: tuple[Source, ...]) -> list[str]:
    values = sorted({source.lang for source in sources})
    return values or [DEFAULT_LANG]


def item_type(item: Item | dict[str, Any]) -> str:
    meta = item.meta if isinstance(item, Item) else item
    return str(meta.get("type") or TEXT_TYPE)


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(CONTENT_DIR.parent))
    except ValueError:
        return str(path)
