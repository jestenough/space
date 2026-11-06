"""Check external build tools for local and Docker runs."""

from __future__ import annotations

import importlib.util
import shutil
import sys

REQUIRED = {
    "host": ("node", "npm", "pandoc", "latexmk", "xelatex"),
    "content": ("python3", "pandoc"),
    "pdf": ("python3", "latexmk", "xelatex"),
}


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else "host"
    required = REQUIRED.get(target)
    if required is None:
        print(f"Unknown tool target: {target}", file=sys.stderr)
        return 2

    missing = [binary for binary in required if shutil.which(binary) is None]
    if missing:
        print(f"Missing required build tools for {target}: {', '.join(missing)}", file=sys.stderr)
        return 1

    if target in {"host", "content"} and importlib.util.find_spec("jinja2") is None:
        print("Missing required Python package: jinja2", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
