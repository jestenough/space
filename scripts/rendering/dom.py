"""Small HTML string patch helpers for prerendered pages"""

from __future__ import annotations

import html
import re
from functools import lru_cache
from typing import Mapping

_HTML_TAG_RE = re.compile(
    r"<(?P<closing>/)?(?P<tag>[a-zA-Z][\w:-]*)\b(?P<attrs>[^>]*)>",
    re.DOTALL,
)
_ID_ATTR_RE = re.compile(r'''\bid=(?:"(?P<double>[^"]*)"|'(?P<single>[^']*)')''', re.IGNORECASE)
_VOID_TAGS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
)


def set_html_lang(page: str, lang: str) -> str:
    return re.sub(r'<html\s+lang="[^"]+"', f'<html lang="{html.escape(lang, quote=True)}"', page, count=1)


def replace_inners(page: str, replacements: Mapping[str, str]) -> str:
    """Replace id-addressed element bodies with a nesting-aware tag scan."""
    if not replacements:
        return page

    stack: list[tuple[str, int, str | None]] = []
    slots: list[tuple[int, int, str]] = []

    for match in _HTML_TAG_RE.finditer(page):
        tag = match.group("tag").lower()
        if match.group("closing"):
            if not stack or stack[-1][0] != tag:
                continue
            _, content_start, element_id = stack.pop()
            if element_id is not None:
                slots.append((content_start, match.start(), element_id))
            continue

        attrs = match.group("attrs")
        if tag in _VOID_TAGS or attrs.rstrip().endswith("/"):
            continue
        id_match = _ID_ATTR_RE.search(attrs)
        element_id = (id_match.group("double") or id_match.group("single")) if id_match else None
        stack.append((tag, match.end(), element_id if element_id in replacements else None))

    for start, end, element_id in sorted(slots, reverse=True):
        page = f"{page[:start]}{replacements[element_id]}{page[end:]}"
    return page


@lru_cache(maxsize=8)
def _options_pattern(values: tuple[str, ...]) -> re.Pattern[str]:
    options = "|".join(re.escape(value) for value in values)
    return re.compile(
        rf'(<option value="(?P<value>{options})">)([\s\S]*?)(</option>)',
        re.IGNORECASE,
    )


def replace_options(page: str, replacements: Mapping[str, str]) -> str:
    """Replace several option labels in one page scan."""
    if not replacements:
        return page

    pattern = _options_pattern(tuple(sorted(replacements)))
    return pattern.sub(
        lambda match: f"{match.group(1)}{html.escape(replacements[match.group('value')])}{match.group(4)}",
        page,
    )


@lru_cache(maxsize=8)
def _element_tags_pattern(element_ids: tuple[str, ...]) -> re.Pattern[str]:
    ids = "|".join(re.escape(element_id) for element_id in element_ids)
    return re.compile(rf'<[^>]*\bid="(?P<id>{ids})"[^>]*>', re.IGNORECASE)


def set_attrs(page: str, replacements: Mapping[str, Mapping[str, str]]) -> str:
    """Update attributes on several id-addressed opening tags in one page scan."""
    if not replacements:
        return page

    pattern = _element_tags_pattern(tuple(sorted(replacements)))

    def replace(match: re.Match[str]) -> str:
        tag = match.group(0)
        for attr, value in replacements[match.group("id")].items():
            tag = set_tag_attr(tag, attr, value)
        return tag

    return pattern.sub(replace, page)


def set_tag_attr(tag: str, attr: str, value: str) -> str:
    replacement = html.escape(value, quote=True)
    pattern = re.compile(
        rf"""(?:\s{re.escape(attr)}="[^"]*"|\s{re.escape(attr)}='[^']*')""",
        re.IGNORECASE,
    )
    if pattern.search(tag):
        return pattern.sub(f' {attr}="{replacement}"', tag, count=1)

    suffix = "/>" if tag.endswith("/>") else ">"
    prefix = tag[:-2].rstrip() if tag.endswith("/>") else tag[:-1].rstrip()

    return f'{prefix} {attr}="{replacement}"{suffix}'


def add_tag_class(tag: str, class_name: str) -> str:
    class_re = re.compile(r'''\sclass=(?:"(?P<double>[^"]*)"|'(?P<single>[^']*)')''', re.IGNORECASE)
    match = class_re.search(tag)
    if match:
        classes = (match.group("double") or match.group("single") or "").split()
        if class_name not in classes:
            classes.append(class_name)

        return class_re.sub(f' class="{html.escape(" ".join(classes), quote=True)}"', tag, count=1)

    suffix = "/>" if tag.endswith("/>") else ">"
    prefix = tag[:-2].rstrip() if tag.endswith("/>") else tag[:-1].rstrip()

    return f'{prefix} class="{html.escape(class_name, quote=True)}"{suffix}'
