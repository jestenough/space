"""Code block decoration for generated HTML."""

from __future__ import annotations

import html
import re

from ..config import DEFAULT_LANG

BLOCK_RE = re.compile(r"<pre\b[^>]*>[\s\S]*?</pre>", re.IGNORECASE)
PRE_RE = re.compile(r"^(?P<start><pre\b[^>]*>)(?P<body>[\s\S]*?)(?P<end></pre>)$", re.IGNORECASE)
CODE_RE = re.compile(r"^(?P<start>\s*<code\b[^>]*>)(?P<body>[\s\S]*?)(?P<end></code>\s*)$", re.IGNORECASE)
CLASS_RE = re.compile(r"\bclass=[\"']([^\"']+)[\"']", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
PRE_WRAP_RE = re.compile(r"^<pre\b[^>]*>|</pre>$", re.IGNORECASE)

IGNORED_CLASSES = frozenset({"code", "code-line", "hljs", "info-file-pre", "numbersource", "sourcecode"})
ALIASES = {
    "bash": "shell",
    "js": "javascript",
    "jsx": "javascript jsx",
    "py": "python",
    "sh": "shell",
    "ts": "typescript",
    "tsx": "typescript jsx",
}
UI = {
    DEFAULT_LANG: {
        "label": "code",
        "copy": "copy",
        "copied": "copied",
        "line_copy": "copy line",
        "toast_success": "code copied to clipboard",
        "line_toast_success": "line copied to clipboard",
        "toast_failure": "copy failed",
    },
    "ru": {
        "label": "код",
        "copy": "копировать",
        "copied": "скопировано",
        "line_copy": "копировать строку",
        "toast_success": "код скопирован в буфер обмена",
        "line_toast_success": "строка скопирована в буфер обмена",
        "toast_failure": "не удалось скопировать",
    },
}


def decorate(value: str, lang: str) -> str:
    labels = ui(lang)

    def replace(match: re.Match[str]) -> str:
        pre_html = match.group(0)
        if "data-code-copy-block" in pre_html:
            return pre_html

        text = pre_text(pre_html).rstrip("\n")
        if not text.strip():
            return pre_html

        lines = decorate_lines(pre_html, text, labels)
        language = language_for(pre_html) or labels["label"]
        return (
            '<div class="code-copy-block" data-code-copy-block>'
            '<div class="code-copy-bar">'
            f'<span class="code-copy-label">{html.escape(language)}</span>'
            '<button class="code-copy-btn" type="button" '
            f'data-copy-text="{attribute(text)}" '
            f'data-copy-label="{html.escape(labels["copy"], quote=True)}" '
            f'data-copy-success="{html.escape(labels["copied"], quote=True)}" '
            f'data-copy-toast-success="{html.escape(labels["toast_success"], quote=True)}" '
            f'data-copy-toast-failure="{html.escape(labels["toast_failure"], quote=True)}">'
            f'{html.escape(labels["copy"])}'
            "</button>"
            "</div>"
            f"{lines}"
            "</div>"
        )

    return BLOCK_RE.sub(replace, value)


def decorate_lines(pre_html: str, text: str, labels: dict[str, str]) -> str:
    pre = PRE_RE.match(pre_html)
    if not pre:
        return pre_html

    body = pre.group("body")
    code = CODE_RE.match(body)
    start = code.group("start") if code else ""
    code_body = code.group("body") if code else body
    end = code.group("end") if code else ""
    return "".join([pre.group("start"), start, lines(text, labels, code_body), end, pre.group("end")])


def lines(value: str, labels: dict[str, str], html_value: str | None = None) -> str:
    plain_lines = value.split("\n")
    html_lines = html_value.rstrip("\n").split("\n") if html_value is not None else []
    if len(html_lines) != len(plain_lines):
        html_lines = [html.escape(line) for line in plain_lines]
    return "".join(
        line(plain_lines[index], labels, html_lines[index]) for index in range(len(plain_lines))
    )


def line(value: str, labels: dict[str, str], line_html: str) -> str:
    if not value.strip():
        return '<span class="code-line code-line-empty" data-code-line><span class="code-line-text"> </span></span>'

    return (
        '<span class="code-line" data-code-line role="button" tabindex="0" '
        f'aria-label="{html.escape(labels["line_copy"], quote=True)}" '
        f'title="{html.escape(labels["line_copy"], quote=True)}" '
        f'data-copy-value="{attribute(value)}" '
        f'data-copy-toast-success="{html.escape(labels["line_toast_success"], quote=True)}" '
        f'data-copy-toast-failure="{html.escape(labels["toast_failure"], quote=True)}">'
        f'<span class="code-line-text">{line_html or " "}</span>'
        "</span>"
    )


def language_for(pre_html: str) -> str | None:
    candidates = classes(pre_html, "code") + classes(pre_html, "pre")
    for value in candidates:
        candidate = normalize_language(value)
        if candidate:
            return ALIASES.get(candidate, candidate)
    return None


def normalize_language(value: str) -> str | None:
    candidate = value.strip()
    for prefix in ("language-", "lang-"):
        if candidate.startswith(prefix):
            candidate = candidate.removeprefix(prefix)
            break
    candidate = candidate.lower()
    return None if not candidate or candidate in IGNORED_CLASSES else candidate


def classes(value: str, tag: str) -> list[str]:
    result: list[str] = []
    for match in re.finditer(rf"<{tag}\b[^>]*>", value, re.IGNORECASE):
        class_match = CLASS_RE.search(match.group(0))
        if class_match:
            result.extend(class_match.group(1).split())
    return result


def pre_text(value: str) -> str:
    inner = PRE_WRAP_RE.sub("", value)
    return html.unescape(TAG_RE.sub("", inner))


def attribute(value: str) -> str:
    return html.escape(value, quote=True).replace("\r", "").replace("\n", "&#10;")


def ui(lang: str) -> dict[str, str]:
    try:
        return UI[lang]
    except KeyError as exc:
        raise RuntimeError(
            f"Missing code-copy UI translations for language `{lang}`. "
            "Add this language to scripts/rendering/code.py."
        ) from exc
