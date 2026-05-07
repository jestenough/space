"""JSON file IO with consistent build errors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON file: {path}\n{exc.msg} at line {exc.lineno}, column {exc.colno}.") from exc


def read_object(path: Path, label: str = "JSON") -> dict[str, Any]:
    data = read_json(path)
    if not isinstance(data, dict):
        raise RuntimeError(f"{label} must be an object: {path}")
    return data


def read_list(path: Path, label: str = "JSON") -> list[Any]:
    data = read_json(path)
    if not isinstance(data, list):
        raise RuntimeError(f"{label} must be a list: {path}")
    return data


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
