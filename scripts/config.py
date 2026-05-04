"""Shared paths and constants for the build scripts."""

from __future__ import annotations

import os
from pathlib import Path


# Root

ROOT_DIR = Path(__file__).resolve().parents[1]


# Source content

CONTENT_DIR = ROOT_DIR / "content"
ARTICLES_DIR = CONTENT_DIR / "articles"
SITE_META_PATH = CONTENT_DIR / "site.json"


# Frontend source

SRC_DIR = ROOT_DIR / "src"
PUBLIC_DIR = ROOT_DIR / "public"

PACKAGE_JSON = ROOT_DIR / "package.json"
TSCONFIG = ROOT_DIR / "tsconfig.json"
VITE_CONFIG = ROOT_DIR / "vite.config.ts"


# Generated output

GENERATED_DIR = ROOT_DIR / "generated"
GENERATED_ARTICLES_DIR = GENERATED_DIR / "articles"
GENERATED_META_DIR = GENERATED_DIR / "articles-meta"

DIST_DIR = ROOT_DIR / "dist"


# Localization

SUPPORTED_LANGS = ("en", "ru")
DEFAULT_LANG = "en"


# Site

DEFAULT_SITE_URL = "https://autophany.space"
SITE_URL = (os.environ.get("SITE_URL") or DEFAULT_SITE_URL).rstrip("/")


# Dates

DATE_FORMAT = "%Y-%m-%d"
DATE_FORMAT_LABEL = "YYYY-MM-DD"
