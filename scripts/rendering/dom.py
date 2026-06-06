"""Small HTML string patch helpers for prerendered pages"""

from __future__ import annotations

import html
import re


def set_html_lang(page: str, lang: str) -> str:
    return re.sub(r'<html\s+lang="[^"]+"', f'<html lang="{html.escape(lang, quote=True)}"', page, count=1)


def replace_inner(page: str, element_id: str, inner_html: str, tag: str | None = None) -> str:
    tag_pattern = tag or r"[^\s>]+"
    pattern = re.compile(
        rf'(<(?P<tag>{tag_pattern})[^>]*\bid="{re.escape(element_id)}"[^>]*>)([\s\S]*?)(</(?P=tag)>)', re.IGNORECASE
    )

    return pattern.sub(lambda match: f"{match.group(1)}{inner_html}{match.group(4)}", page, count=1)


def replace_option(page: str, value: str, text: str) -> str:
    return re.sub(
        rf'(<option value="{re.escape(value)}">)([\s\S]*?)(</option>)',
        lambda match: f"{match.group(1)}{html.escape(text)}{match.group(3)}",
        page,
        count=1,
    )


def set_attr(page: str, element_id: str, attr: str, value: str) -> str:
    pattern = re.compile(rf'(<[^>]*\bid="{re.escape(element_id)}"[^>]*)(>)', re.IGNORECASE)

    def replace(match: re.Match[str]) -> str:
        start = match.group(1)
        attr_pattern = re.compile(rf'\s{re.escape(attr)}="[^"]*"', re.IGNORECASE)
        replacement = f' {attr}="{html.escape(value, quote=True)}"'
        return f"{attr_pattern.sub(replacement, start, count=1) if attr_pattern.search(start) else start + replacement}{match.group(2)}"

    return pattern.sub(replace, page, count=1)


def set_tag_attr(tag: str, attr: str, value: str) -> str:
    replacement = html.escape(value, quote=True)
    pattern = re.compile(rf'\s{re.escape(attr)}=["\'][^"\']*["\']', re.IGNORECASE)
    updated = pattern.sub(f' {attr}="{replacement}"', tag, count=1)
    if updated != tag:
        return updated

    suffix = "/>" if tag.endswith("/>") else ">"
    prefix = tag[:-2].rstrip() if tag.endswith("/>") else tag[:-1].rstrip()

    return f'{prefix} {attr}="{replacement}"{suffix}'


def add_tag_class(tag: str, class_name: str) -> str:
    class_re = re.compile(r'\sclass=["\']([^"\']*)["\']', re.IGNORECASE)
    match = class_re.search(tag)
    if match:
        classes = match.group(1).split()
        if class_name not in classes:
            classes.append(class_name)

        return class_re.sub(f' class="{html.escape(" ".join(classes), quote=True)}"', tag, count=1)

    suffix = "/>" if tag.endswith("/>") else ">"
    prefix = tag[:-2].rstrip() if tag.endswith("/>") else tag[:-1].rstrip()

    return f'{prefix} class="{html.escape(class_name, quote=True)}"{suffix}'
