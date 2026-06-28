"""Shared paths and constants for the build scripts"""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path

# Backend sources
ROOT_DIR = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT_DIR / "content"

# Frontend source
SRC_DIR = ROOT_DIR / "src"
PUBLIC_DIR = ROOT_DIR / "public"
PACKAGE_JSON = ROOT_DIR / "package.json"
TSCONFIG = ROOT_DIR / "tsconfig.json"
VITE_CONFIG = ROOT_DIR / "vite.config.ts"

# Content model
SYSTEM_SECTION = os.environ.get("SYSTEM_SECTION", "site")


class FolderType(StrEnum):
    SYSTEM = "system"
    FILES = "files"
    ARTICLES = "articles"
    NOTES = "notes"
    PROJECTS = "projects"
    TAGS = "tags"


class FileType(StrEnum):
    PAGE = "page"
    ARTICLE = "article"
    PROJECT = "project"


class ContentExtension(StrEnum):
    TEX = "tex"
    MARKDOWN = "md"
    TXT = "txt"
    META = "meta"


FOLDER_TYPES = tuple(FolderType)
FILE_TYPES = tuple(FileType)
ITEM_ASSETS_DIR = "assets"
HOME_PAGE = "home"
TAG_PAGE = "tag"
NOT_FOUND_PAGE = "notFound"
WORDS_PER_MINUTE = 220
LIST_PAGE_SIZE = 4

# Generated output
GENERATED_FILES_NAME = "files"
GENERATED_FILE_META_NAME = "files-meta"
GENERATED_SECTIONS_NAME = "sections"
GENERATED_SECTIONS_INDEX_FILE = "sections-index.json"
GENERATED_SITE_META_FILE = "site-meta.json"
GENERATED_DIR = ROOT_DIR / "generated"
GENERATED_FILES_DIR = GENERATED_DIR / GENERATED_FILES_NAME
GENERATED_FILE_META_DIR = GENERATED_DIR / GENERATED_FILE_META_NAME
GENERATED_SECTIONS_DIR = GENERATED_DIR / GENERATED_SECTIONS_NAME
GENERATED_SITE_META_PATH = GENERATED_DIR / GENERATED_SITE_META_FILE
DIST_DIR = ROOT_DIR / "dist"
TEMPLATES_DIR = ROOT_DIR / "templates"
CACHE_DIR = ROOT_DIR / ".cache"
MEDIA_MANIFEST_PATH = CACHE_DIR / "media-manifest.json"

# Localization
DEFAULT_LANG = "en"

# Site
DEFAULT_SITE_URL = "https://autophany.space"
SITE_URL = (os.environ.get("SITE_URL") or DEFAULT_SITE_URL).rstrip("/")
GITHUB_EDIT_BASE = "https://github.com/jestenough/space/edit/master/content"

# Dates
DATE_FORMAT = "%Y-%m-%d"
DATE_FORMAT_LABEL = "YYYY-MM-DD"
