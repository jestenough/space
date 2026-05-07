"""Language and localized text helpers."""

from __future__ import annotations

import re
from typing import Any

from .config import DEFAULT_LANG


LANG_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z]{2})?$")


def norm_lang(value: str) -> str:
    if not LANG_RE.fullmatch(value):
        raise RuntimeError(f"Invalid language code `{value}`. Use examples like `en`, `ru`, or `pt-BR`.")
    parts = value.split("-", 1)
    return parts[0].lower() if len(parts) == 1 else f"{parts[0].lower()}-{parts[1].upper()}"


def exact_text(value: Any, lang: str) -> str:
    if isinstance(value, dict):
        text = value.get(lang)
        return str(text).strip() if isinstance(text, str) else ""
    return str(value or "").strip()


def strict_text(value: Any, lang: str, path: str) -> str:
    if not isinstance(value, dict):
        raise RuntimeError(f"Missing localized object: {path}")
    text = value.get(lang)
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError(f"Missing localized value: {path}.{lang}")
    return text.strip()


def language_list(values: set[str]) -> list[str]:
    return sorted(values) or [DEFAULT_LANG]
