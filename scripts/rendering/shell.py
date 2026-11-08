"""Shell-style UI rendering for prerendered pages"""

from __future__ import annotations

from typing import Any

from .. import routes
from ..config import DEFAULT_LANG, FolderType
from ..localization import strict_text
from ..templating import Templates
from .context import FileShellContext, ListShellContext

ASCII_LOGO = """#                                                                                                             
#       mm            m                  #                                   mmmm                             
#       ##   m   m  mm#mm   mmm   mmmm   # mm    mmm   m mm   m   m         #\"   \" mmmm    mmm    mmm    mmm 
#      #  #  #   #    #    #\" \"#  #\" \"#  #\"  #  \"   #  #\"  #  \"m m\"         \"#mmm  #\" \"#  \"   #  #\"  \"  #\"  #
#      #mm#  #   #    #    #   #  #   #  #   #  m\"\"\"#  #   #   #m#             \"#  #   #  m\"\"\"#  #      #\"\"\"\" 
#     #    # \"mm\"#    \"mm  \"#m#\"  ##m#\"  #   #  \"mm\"#  #   #   \"#           \"mmm#\" ##m#\"  \"mm\"#  \"#mm\"  \"#mm\"
#                                 #                            m\"                  #                           
#                                 \"                           \"\"                   \"                         """

DEFAULT_UI = {
    "theme_label": "$ export THEME=",
    "lang_label": "$ localectl set-locale LANG=",
    "theme_reading": "paper",
    "theme_light": "day",
    "theme_system": "system",
    "theme_dark": "night",
    "footer_motto": "Follow your curiosity. Lead humanity forward",
    "search_placeholder": "pattern",
    "tag_search_placeholder": "tag",
    "sort_label": "sort:",
    "size_label": "size:",
    "tag_sort_label": "sort:",
    "tag_size_label": "head:",
    "page_prev": "[PREV]",
    "page_next": "[NEXT]",
    "toc_title": "headings",
    "window_session": "Settings",
    "window_navigation": "Navigation",
    "window_metainfo": "Info",
    "window_headings": "Headings",
    "window_systemnote": "System Note",
    "window_drawer": "Menu",
    "mobile_sections": "Navigation",
    "mobile_options": "Options",
    "mobile_contents": "Headings",
    "back_label": "!ls",
    "back_title": "Back to list",
    "cite_text": "cite",
    "copied_text": "copied",
    "copy_toast_success": "citation copied to clipboard",
    "copy_toast_failure": "copy failed",
    "edit_text": "edit",
    "zen_text": "zen",
    "date_desc_label": "mtime ↓",
    "date_asc_label": "mtime ↑",
    "title_asc_label": "name ↑",
    "title_desc_label": "name ↓",
    "name_asc_label": "name ↑",
    "name_desc_label": "name ↓",
    "count_desc_label": "count ↓",
    "count_asc_label": "count ↑",
}

UI_BY_LANG = {
    "ru": {
        "theme_reading": "paper/бумага",
        "theme_light": "day/день",
        "theme_system": "system/система",
        "theme_dark": "night/ночь",
        "footer_motto": "Следуй любопытству. Веди человечество вперёд",
        "window_session": "Настройки",
        "window_navigation": "Навигация",
        "window_metainfo": "Информация",
        "window_headings": "Заголовки",
        "window_systemnote": "Система",
        "window_drawer": "Меню",
        "mobile_sections": "Навигация",
        "mobile_options": "Опции",
        "mobile_contents": "Заголовки",
        "toc_title": "заголовки",
        "back_title": "Вернуться к списку",
        "copy_toast_success": "цитата скопирована в буфер обмена",
        "copy_toast_failure": "не удалось скопировать",
    },
}

LOCALE_REGIONS = {
    "en": "US",
    "ru": "RU",
}


class Shell:
    def __init__(self, templates: Templates, languages: list[str] | None = None) -> None:
        self.templates = templates
        self.languages = languages or []
        self._language_options: dict[str, list[dict[str, Any]]] = {}
        self._ui_cache: dict[str, dict[str, str]] = {}

    def set_languages(self, languages: list[str]) -> None:
        self.languages = languages
        self._language_options.clear()

    def ui(self, lang: str) -> dict[str, str]:
        cached = self._ui_cache.get(lang)
        if cached is not None:
            return cached

        if lang == DEFAULT_LANG:
            cached = dict(DEFAULT_UI)
        elif lang in UI_BY_LANG:
            cached = {**DEFAULT_UI, **UI_BY_LANG[lang]}
        else:
            raise RuntimeError(
                f"Missing shell UI translations for language `{lang}`. "
                "Add this language to UI_BY_LANG in scripts/rendering/shell.py."
            )

        self._ui_cache[lang] = cached
        return cached

    def nav(self, sections: list[dict[str, Any]], lang: str, active: str | None) -> list[dict[str, Any]]:
        links = []
        for section in sections:
            if section.get("system"):
                continue
            if (
                str(section.get("kind")) != FolderType.TAGS.value
                and int(section.get("count") or 0) <= 0
            ):
                continue

            slug = str(section.get("slug"))
            links.append(
                {
                    "href": routes.generated_section_route(section, lang),
                    "label": strict_text(section.get("label"), lang, f"sections.{slug}.label"),
                    "active": slug == active,
                }
            )
        return links

    def list(self, context: ListShellContext) -> dict[str, Any]:
        return {
            "lang": context.lang,
            "cwd": self.cwd(context.active_section),
            "view": "list",
            "welcome_title": context.welcome_title,
            "welcome_lead": context.welcome_lead,
            "welcome_command": self.left_info_command(context.active_section),
            "render_command": context.render_command,
            "process_command": "statfs ~",
            "process": context.process,
            "list_stage_html": context.stage_html,
            "toc": [],
            "show_toc": False,
            "ascii_logo": ASCII_LOGO,
            "nav": self.nav(context.sections, context.lang, context.active_section),
            "languages": self.language_options(context.lang),
            "ui": self.ui(context.lang),
        }

    def file(self, context: FileShellContext) -> dict[str, Any]:
        return {
            "lang": context.lang,
            "cwd": self.cwd(context.active_section),
            "view": "article",
            "welcome_title": context.welcome_title,
            "welcome_lead": context.welcome_lead,
            "welcome_command": context.welcome_command,
            "render_command": context.render_command,
            "process_command": context.process_command,
            "process": context.process,
            "file_stage_html": self.file_stage(context),
            "toc": context.toc,
            "show_toc": context.show_toc,
            "ascii_logo": ASCII_LOGO,
            "nav": self.nav(context.sections, context.lang, context.active_section),
            "languages": self.language_options(context.lang),
            "ui": self.ui(context.lang),
        }

    def file_stage(self, shell: FileShellContext) -> str:
        ui = self.ui(shell.lang)
        context = {
            "back_href": shell.back_href,
            "back_label": ui["back_label"],
            "back_title": ui["back_title"],
            "download_class": "download-btn action-chip" if shell.download_href else "download-btn action-chip hidden",
            "download_href": shell.download_href or "",
            "download_text": shell.download_text,
            "cite_class": "download-btn action-chip"
            if shell.show_cite and shell.cite_value
            else "download-btn action-chip hidden",
            "cite_value": shell.cite_value or "",
            "cite_text": ui["cite_text"],
            "copied_text": ui["copied_text"],
            "copy_toast_success": ui["copy_toast_success"],
            "copy_toast_failure": ui["copy_toast_failure"],
            "edit_class": "download-btn action-chip"
            if shell.show_edit and shell.edit_href
            else "download-btn action-chip hidden",
            "edit_href": shell.edit_href or "",
            "edit_text": ui["edit_text"],
            "zen_class": "download-btn action-chip" if shell.show_zen else "download-btn action-chip hidden",
            "zen_text": ui["zen_text"],
            "content_html": shell.content_html,
        }
        if shell.template_context:
            context.update(shell.template_context)

        return self.templates.render(f"files/{shell.file_type.value}.html", **context)

    def language_options(self, active_lang: str) -> list[dict[str, Any]]:
        cached = self._language_options.get(active_lang)
        if cached is not None:
            return cached

        options = [
            {"value": lang, "label": self.locale_name(lang), "selected": lang == active_lang}
            for lang in self.languages
        ]
        self._language_options[active_lang] = options
        return options

    @staticmethod
    def left_info_command(active_section: str | None) -> str:
        return "sed -n '1,2p' .meta" if not active_section else f"sed -n '1,2p' {active_section}.meta"

    @staticmethod
    def cwd(section: str | None) -> str:
        return "~" if not section or section == "site" else f"~/{section}"

    @staticmethod
    def locale_name(lang: str) -> str:
        if lang not in LOCALE_REGIONS and "-" not in lang:
            raise RuntimeError(
                f"Missing locale region for language `{lang}`. "
                "Add this language to LOCALE_REGIONS in scripts/rendering/shell.py or use a regional tag like `pt-BR`."
            )

        if "-" in lang:
            return f"{lang.replace('-', '_')}.UTF-8"
        else:
            return f"{lang}_{LOCALE_REGIONS[lang]}.UTF-8"
