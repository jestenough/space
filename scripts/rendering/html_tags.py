"""Small helpers for patching attributes on generated HTML tags."""

from __future__ import annotations

import html
import re
from functools import lru_cache

_CLASS_ATTR_RE = re.compile(r'''\sclass=(?:"(?P<double>[^"]*)"|'(?P<single>[^']*)')''', re.IGNORECASE)


@lru_cache(maxsize=32)
def _attr_pattern(attr: str) -> re.Pattern[str]:
    return re.compile(
        rf"""(?:\s{re.escape(attr)}="[^"]*"|\s{re.escape(attr)}='[^']*')""",
        re.IGNORECASE,
    )


def set_tag_attr(tag: str, attr: str, value: str) -> str:
    replacement = html.escape(value, quote=True)
    pattern = _attr_pattern(attr)
    if pattern.search(tag):
        return pattern.sub(f' {attr}="{replacement}"', tag, count=1)

    suffix = "/>" if tag.endswith("/>") else ">"
    prefix = tag[:-2].rstrip() if tag.endswith("/>") else tag[:-1].rstrip()
    return f'{prefix} {attr}="{replacement}"{suffix}'


def add_tag_class(tag: str, class_name: str) -> str:
    match = _CLASS_ATTR_RE.search(tag)
    if match:
        classes = (match.group("double") or match.group("single") or "").split()
        if class_name not in classes:
            classes.append(class_name)
        return _CLASS_ATTR_RE.sub(f' class="{html.escape(" ".join(classes), quote=True)}"', tag, count=1)

    suffix = "/>" if tag.endswith("/>") else ">"
    prefix = tag[:-2].rstrip() if tag.endswith("/>") else tag[:-1].rstrip()
    return f'{prefix} class="{html.escape(class_name, quote=True)}"{suffix}'
