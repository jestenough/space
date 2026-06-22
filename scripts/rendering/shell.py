"""Shell-style UI rendering for prerendered pages"""

from __future__ import annotations

import html
import re
from typing import Any

from .. import routes
from ..localization import strict_text
from ..templating import TemplateRenderer
from . import dom
from .context import FileShellContext, ListShellContext

ASCII_LOGO = """#                                                                                                             
#       mm            m                  #                                   mmmm                             
#       ##   m   m  mm#mm   mmm   mmmm   # mm    mmm   m mm   m   m         #\"   \" mmmm    mmm    mmm    mmm 
#      #  #  #   #    #    #\" \"#  #\" \"#  #\"  #  \"   #  #\"  #  \"m m\"         \"#mmm  #\" \"#  \"   #  #\"  \"  #\"  #
#      #mm#  #   #    #    #   #  #   #  #   #  m\"\"\"#  #   #   #m#             \"# #   #  m\"\"\"#  #      #\"\"\"\" 
#     #    # \"mm\"#    \"mm  \"#m#\"  ##m#\"  #   #  \"mm\"#  #   #   \"#           \"mmm#\" ##m#\"  \"mm\"#  \"#mm\"  \"#mm\"
#                                 #                            m\"                 #                           
#                                 \"                           \"\"                  \"                         """

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
    def __init__(self, templates: TemplateRenderer, languages: list[str] | None = None) -> None:
        self.templates = templates
        self.languages = languages or []

    def set_languages(self, languages: list[str]) -> None:
        self.languages = languages

    def ui(self, lang: str) -> dict[str, str]:
        return {**DEFAULT_UI, **UI_BY_LANG.get(lang, {})}

    def apply(self, page: str, shell: dict[str, Any]) -> str:
        lang = str(shell["lang"])
        ui = self.ui(lang)
        cwd = str(shell.get("cwd") or "~")
        page = dom.set_html_lang(page, lang)
        page = dom.replace_inner(page, "ascii-logo", html.escape(ASCII_LOGO), tag="pre")
        page = dom.replace_inner(page, "pwd-line", self.command("tree -d -L 1 .", cwd="~"), tag="p")
        page = dom.replace_inner(page, "theme-label", html.escape(ui["theme_label"]), tag="span")
        page = dom.replace_inner(page, "lang-label", html.escape(ui["lang_label"]), tag="span")
        page = dom.replace_inner(page, "session-title", html.escape(ui["window_session"]), tag="summary")
        page = dom.replace_inner(page, "navigation-title", html.escape(ui["window_navigation"]), tag="summary")
        page = dom.replace_inner(page, "metainfo-title", html.escape(ui["window_metainfo"]), tag="summary")
        page = dom.replace_inner(page, "systemnote-title", html.escape(ui["window_systemnote"]), tag="summary")
        page = dom.replace_inner(page, "drawer-title", html.escape(ui["window_drawer"]), tag="summary")
        page = dom.replace_inner(page, "mobile-sections-btn", html.escape(ui["mobile_sections"]), tag="button")
        page = dom.replace_inner(page, "mobile-options-btn", html.escape(ui["mobile_options"]), tag="button")
        page = dom.replace_inner(page, "mobile-contents-btn", html.escape(ui["mobile_contents"]), tag="button")
        page = dom.replace_inner(page, "mobile-sections-title", html.escape(ui["mobile_sections"]), tag="h2")
        page = dom.replace_inner(page, "mobile-options-title", html.escape(ui["mobile_options"]), tag="h2")
        page = dom.replace_inner(page, "mobile-contents-title", html.escape(ui["mobile_contents"]), tag="h2")
        page = dom.replace_option(page, "reading", ui["theme_reading"])
        page = dom.replace_option(page, "light", ui["theme_light"])
        page = dom.replace_option(page, "system", ui["theme_system"])
        page = dom.replace_option(page, "dark", ui["theme_dark"])
        page = dom.replace_inner(page, "lang-switcher", self.language_options(lang), tag="select")
        page = dom.replace_inner(page, "welcome-command", self.command(str(shell["welcome_command"]), cwd=cwd))
        page = dom.replace_inner(page, "welcome-title", html.escape(str(shell["welcome_title"])))
        page = dom.replace_inner(page, "welcome-lead", html.escape(str(shell["welcome_lead"])))
        page = dom.replace_inner(page, "welcome-body", html.escape(str(shell.get("welcome_body") or "")))
        page = dom.replace_inner(page, "render-indicator", self.command(str(shell["render_command"]), cwd=cwd))
        page = dom.replace_inner(page, "process-log", str(shell["process_html"]))
        page = dom.replace_inner(page, "content-list-view", str(shell.get("list_stage_html") or ""), tag="section")
        page = dom.replace_inner(page, "file-view", str(shell.get("file_stage_html") or ""), tag="article")
        page = dom.replace_inner(
            page,
            "toc-panel",
            f'<summary class="window-title">{html.escape(ui["window_headings"])}</summary><div class="side-window-body"><h3 class="toc-title">{html.escape(ui["toc_title"])}</h3><ul id="toc-list" class="toc-list">{shell.get("toc_html") or ""}</ul></div>',
            tag="details",
        )
        page = dom.replace_inner(page, "footer-motto", html.escape(ui["footer_motto"]), tag="p")
        page = dom.set_attr(page, "brand-link", "href", f"/{shell['lang']}")
        page = self.quick_nav(page, shell)

        return self.view_classes(page, shell)

    def quick_nav(self, page: str, shell: dict[str, Any]) -> str:
        links = []
        active_section = shell.get("active_section")
        lang = str(shell["lang"])

        for section in shell["sections"]:
            if section.get("system"):
                continue

            classes = "quick-link is-active" if section.get("slug") == active_section else "quick-link"
            href = routes.generated_section_route(section, lang)
            label = strict_text(section.get("label"), lang, f"sections.{section.get('slug')}.label")
            links.append(
                f'<a class="{classes}" href="{html.escape(href, quote=True)}" data-internal="true">{html.escape(label)}</a>'
            )
        else:
            return re.sub(
                r'(<nav\b[^>]*class="quick-nav"[^>]*aria-label="Sections"[^>]*>)([\s\S]*?)(</nav>)',
                lambda match: f"{match.group(1)}{''.join(links)}{match.group(3)}",
                page,
                count=1,
            )

    @staticmethod
    def view_classes(page: str, shell: dict[str, Any]) -> str:
        view = str(shell.get("view") or "list")
        page = dom.set_attr(page, "content-list-view", "class", "list-stage hidden" if view != "list" else "list-stage")
        page = dom.set_attr(page, "file-view", "class", "file-stage" if view == "article" else "file-stage hidden")
        page = dom.set_attr(page, "error-view", "class", "file-stage" if view == "error" else "file-stage hidden")

        return dom.set_attr(page, "toc-panel", "class", "side-window toc-panel" if shell.get("show_toc") else "side-window toc-panel hidden")

    def list(self, context: ListShellContext) -> dict[str, Any]:
        return {
            "lang": context.lang,
            "cwd": self.cwd(context.active_section),
            "sections": context.sections,
            "active_section": context.active_section,
            "view": "list",
            "tag": context.tag,
            "welcome_title": context.welcome_title,
            "welcome_lead": context.welcome_lead,
            "welcome_body": "",
            "welcome_command": self.left_info_command(context.active_section),
            "render_command": context.render_command,
            "process_html": context.process_html,
            "list_stage_html": context.stage_html,
            "show_toc": False,
        }

    def file(self, context: FileShellContext) -> dict[str, Any]:
        return {
            "lang": context.lang,
            "cwd": self.cwd(context.active_section),
            "sections": context.sections,
            "active_section": context.active_section,
            "view": "article",
            "welcome_title": context.welcome_title,
            "welcome_lead": context.welcome_lead,
            "welcome_body": "",
            "welcome_command": context.welcome_command,
            "render_command": context.render_command,
            "process_html": context.process_html,
            "file_stage_html": self.file_stage(context),
            "toc_html": context.toc_html,
            "show_toc": context.show_toc,
        }

    def file_stage(self, shell: FileShellContext) -> str:
        ui = self.ui(shell.lang)
        context = {
            "back_href": html.escape(shell.back_href, quote=True),
            "back_label": html.escape(ui["back_label"]),
            "back_title": html.escape(ui["back_title"], quote=True),
            "download_class": "download-btn action-chip" if shell.download_href else "download-btn action-chip hidden",
            "download_href": html.escape(shell.download_href or "", quote=True),
            "download_text": html.escape(shell.download_text),
            "cite_class": "download-btn action-chip"
            if shell.show_cite and shell.cite_value
            else "download-btn action-chip hidden",
            "cite_value": html.escape(shell.cite_value or "", quote=True).replace("\n", "&#10;"),
            "cite_text": html.escape(ui["cite_text"]),
            "copied_text": html.escape(ui["copied_text"]),
            "copy_toast_success": html.escape(ui["copy_toast_success"]),
            "copy_toast_failure": html.escape(ui["copy_toast_failure"]),
            "edit_class": "download-btn action-chip"
            if shell.show_edit and shell.edit_href
            else "download-btn action-chip hidden",
            "edit_href": html.escape(shell.edit_href or "", quote=True),
            "edit_text": html.escape(ui["edit_text"]),
            "zen_class": "download-btn action-chip" if shell.show_zen else "download-btn action-chip hidden",
            "zen_text": html.escape(ui["zen_text"]),
            "content_html": shell.content_html,
        }
        if shell.template_context:
            context.update(shell.template_context)

        return self.templates.render(f"files/{shell.file_type.value}.html", **context)

    def language_options(self, active_lang: str) -> str:
        options = []
        for lang in self.languages:
            selected = ' selected="selected"' if lang == active_lang else ""
            options.append(
                f'<option value="{html.escape(lang, quote=True)}"{selected}>{html.escape(self.locale_name(lang))}</option>'
            )
        else:
            return "".join(options)

    @staticmethod
    def command(command: str, cwd: str = "~") -> str:
        prompt = f"guest@cray-1:{cwd}"
        return f'<span class="stat-command"><span class="shell-prompt"><span class="shell-prompt-text">{html.escape(prompt)}</span><span class="shell-prompt-sign">$</span></span><span class="shell-gap"> </span><span class="shell-cmd">{html.escape(command)}</span></span>'

    @staticmethod
    def stat_row(key: str, value: str) -> str:
        return Shell.stat_row_html(key, html.escape(value))

    @staticmethod
    def stat_row_html(key: str, value_html: str) -> str:
        return f'<span class="stat-row"><span class="stat-key">{html.escape(key)}</span><span class="stat-sep">:</span><span class="stat-value">{value_html}</span></span>'

    @staticmethod
    def left_info_command(active_section: str | None) -> str:
        return "sed -n '1,2p' .meta" if not active_section else f"sed -n '1,2p' {active_section}.meta"

    @staticmethod
    def cwd(section: str | None) -> str:
        return "~" if not section or section == "site" else f"~/{section}"

    @staticmethod
    def locale_name(lang: str) -> str:
        if "-" in lang:
            return f"{lang.replace('-', '_')}.UTF-8"
        else:
            return f"{lang}_{LOCALE_REGIONS.get(lang, lang.upper())}.UTF-8"
