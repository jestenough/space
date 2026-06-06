"""Command-line entry point for the local build pipeline."""

from __future__ import annotations

import argparse
import importlib
import logging
import sys
from collections.abc import Callable, Sequence
from types import ModuleType

logger = logging.getLogger(__name__)

Handler = Callable[[argparse.Namespace], None]


class AutophanyCLI:
    modules = {
        "preflight": "scripts.preflight",
        "html": "scripts.html",
        "pdf": "scripts.pdf",
        "prerender": "scripts.prerender",
        "seo": "scripts.seo",
        "verify": "scripts.verify",
        "clean": "scripts.clean",
    }

    def __init__(self) -> None:
        self.parser = self.build_parser()

    def run(self, args: Sequence[str] | None = None) -> int:
        parsed_args = self.parser.parse_args(args)

        try:
            logger.info("Running command: %s", parsed_args.command)
            parsed_args.handler(parsed_args)
        except KeyboardInterrupt:
            logger.warning("Interrupted.")
            return 130
        except Exception as exc:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Command failed.")
            else:
                logger.error("Command failed: %s", exc)
            return 1

        logger.info("Done.")

        return 0

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="autophany.space",
            description="Local build tools for autophany.space.",
            epilog="Example: python3 -m scripts.cli preflight",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")

        subparsers = parser.add_subparsers(title="commands", dest="command", required=True)
        self.add_command(subparsers, "preflight", "Check source project before build.")
        self.add_command(subparsers, "html", "Generate article HTML fragments and metadata.")
        self.add_command(subparsers, "pdf", "Generate article PDF files.")
        self.add_command(subparsers, "prerender", "Prerender static HTML routes.")
        self.add_command(subparsers, "seo", "Generate SEO files.")
        self.add_command(subparsers, "verify", "Verify generated production output.")
        self.add_command(subparsers, "clean", "Remove generated files and caches.")

        return parser

    def add_command(self, subparsers: argparse._SubParsersAction, name: str, description: str) -> None:
        command_parser = subparsers.add_parser(name, help=description)
        command_parser.set_defaults(handler=self.run_command(name))

    def run_command(self, name: str) -> Handler:
        def handler(_: argparse.Namespace) -> None:
            self.load_module(name).run()

        return handler

    @classmethod
    def load_module(cls, name: str) -> ModuleType:
        return importlib.import_module(cls.modules[name])


def main(args: Sequence[str] | None = None) -> int:
    argv = list(args) if args is not None else sys.argv[1:]

    verbose = "-v" in argv or "--verbose" in argv
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(levelname)s: %(message)s")

    return AutophanyCLI().run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
