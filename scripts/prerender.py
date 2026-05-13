"""
Static route prerendering step.

Creates SEO-friendly HTML files for localized routes after Vite build,
while preserving Vite-generated JS and CSS assets in the document head.
"""

from __future__ import annotations

import html
import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from . import generated, routes
from .config import (
    DEFAULT_LANG,
    DIST_DIR,
    FileType,
    FolderType,
    GENERATED_FILES_DIR,
    GITHUB_EDIT_BASE,
    GENERATED_SITE_META_PATH,
    HOME_PAGE,
    TAG_PAGE,
    TEMPLATES_DIR,
)
from .jsonio import read_json, read_text
from .localization import exact_text, strict_text
from .templating import TemplateRenderer


logger = logging.getLogger(__name__)
PAGE_SIZE = 4
ASCII_LOGO = """#                                                                                                             
#       mm            m                  #                                   mmmm                             
#       ##   m   m  mm#mm   mmm   mmmm   # mm    mmm   m mm   m   m         #\"   \" mmmm    mmm    mmm    mmm 
#      #  #  #   #    #    #\" \"#  #\" \"#  #\"  #  \"   #  #\"  #  \"m m\"         \"#mmm  #\" \"#  \"   #  #\"  \"  #\"  #
#      #mm#  #   #    #    #   #  #   #  #   #  m\"\"\"#  #   #   #m#             \"# #   #  m\"\"\"#  #      #\"\"\"\" 
#     #    # \"mm\"#    \"mm  \"#m#\"  ##m#\"  #   #  \"mm\"#  #   #   \"#           \"mmm#\" ##m#\"  \"mm\"#  \"#mm\"  \"#mm\"
#                                 #                            m\"                 #                            
#                                 \"                           \"\"                  \"                         """


class Prerender:
    runtime_head_tag_re = re.compile(
        r'^\s*(?:'
        r'<meta\b(?=[^>]*\bname=["\']color-scheme["\'])[^>]*>|'
        r'<script\b(?![^>]*\bsrc=)[^>]*>[\s\S]*?</script>|'
        r'<script\b(?=[^>]*\bsrc=)[^>]*></script>|'
        r'<link\b(?=[^>]*\brel=["\'](?:stylesheet|modulepreload|preload)["\'])[^>]*>'
        r')\s*$',
        re.IGNORECASE | re.MULTILINE,
    )

    def __init__(self) -> None:
        self.templates = TemplateRenderer(TEMPLATES_DIR)
        self.languages: list[str] = [DEFAULT_LANG]

    def run(self) -> None:
        base_html = read_text(DIST_DIR / "index.html", "Missing dist/index.html; run vite build before prerender")
        site_meta = read_json(GENERATED_SITE_META_PATH)
        sections = generated.sections()
        files = generated.items(sections)
        articles = [item for item in files if item.get("type") == FileType.ARTICLE]
        articles_by_slug = {str(article["slug"]): article for article in articles}
        section_files = {str(section["slug"]): generated.section_items(str(section["slug"])) for section in sections}
        article_section = generated.first_section_slug(sections, FolderType.ARTICLES)
        tag_section = generated.first_section_slug(sections, FolderType.TAGS)
        languages = generated.item_languages(files)
        self.languages = languages
        tags_by_lang = generated.collect_tags_by_lang(articles)

        self.render_root(base_html, site_meta, sections, section_files, languages)
        self.render_language_pages(base_html, site_meta, sections, section_files, languages)
        self.render_section_pages(base_html, sections, section_files)
        self.render_file_pages(base_html, sections, section_files)
        self.render_article_index_pages(base_html, site_meta, languages, article_section, sections)
        self.render_tag_index_pages(base_html, site_meta, languages, article_section, tag_section, sections)
        self.render_article_pages(base_html, articles, sections, articles_by_slug, article_section, tag_section)
        self.render_tag_pages(base_html, site_meta, tags_by_lang, sections, articles_by_slug, tag_section)

        total_tags = sum(len(tags) for tags in tags_by_lang.values())

        logger.info("Prerendered %s section(s), %s article(s) and %s localized tag page(s).", len(sections), len(articles), total_tags)

    def render_section_pages(self, base_html: str, sections: list[dict[str, Any]], section_files: dict[str, list[dict[str, Any]]]) -> None:
        for section in sections:
            if section.get("system"):
                continue
            for lang in generated.section_languages(section):
                route = routes.generated_section_route(section, lang)
                shell = self.list_shell(
                    lang=lang,
                    sections=sections,
                    folder_type=FolderType.FILES,
                    active_section=str(section["slug"]),
                    welcome_title=self.localized(section.get("title"), lang, f"sections.{section.get('slug')}.title"),
                    welcome_lead=self.localized(section.get("description"), lang, f"sections.{section.get('slug')}.description"),
                    home_files=section_files[str(section["slug"])],
                    render_command="ls -p | grep -v /",
                    process_html=self.section_process_html(lang, str(section["slug"]), section_files[str(section["slug"])]),
                )
                self.write_route(
                    route,
                    self.render_page(
                        base_html=base_html,
                        lang=lang,
                        title=self.localized(section.get("title"), lang, f"sections.{section.get('slug')}.title"),
                        description=self.localized(section.get("description"), lang, f"sections.{section.get('slug')}.description"),
                        canonical_path=route,
                        alternates=routes.alternates(generated.section_languages(section), lambda item_lang, section=section: routes.generated_section_route(section, item_lang)),
                        og_type="website",
                        shell=shell,
                    ),
                )

    def render_file_pages(self, base_html: str, sections: list[dict[str, Any]], section_files: dict[str, list[dict[str, Any]]]) -> None:
        for section in sections:
            section_slug = str(section["slug"])
            for item in generated.section_items(section_slug):
                if item.get("type") == FileType.ARTICLE:
                    continue
                for lang in item.get("languages", []):
                    route = routes.generated_item_route(item, lang)
                    content = read_text(GENERATED_FILES_DIR / section_slug / f"{item['slug']}.{lang}.html")
                    localized_meta = generated.localized_item(section_slug, str(item["slug"]), lang)
                    title = self.localized(item.get("title"), lang, f"{section_slug}.{item.get('slug')}.title")
                    description = self.localized(item.get("description"), lang, f"{section_slug}.{item.get('slug')}.description")
                    display_name = exact_text(item.get("label"), lang) or str(item["slug"])
                    shell = self.article_shell(
                        lang=lang,
                        sections=sections,
                        file_type=FileType.PAGE,
                        active_section=None if section.get("system") else section_slug,
                        welcome_title=title,
                        welcome_lead=description,
                        welcome_command=f"sed -n '1,2p' {item['slug']}.meta",
                        render_command=f"cat {display_name}",
                        process_html=self.info_file_process_html(lang, section_slug, str(item["slug"]), display_name, item, localized_meta),
                        content_html=content,
                        back_href=routes.generated_section_route(section, lang),
                        download_text="download",
                        download_href=item.get("downloadPath") if item.get("downloadPath") else None,
                    )
                    self.write_route(
                        route,
                        self.render_page(
                            base_html=base_html,
                            lang=lang,
                            title=title,
                            description=description,
                            canonical_path=route,
                            alternates=routes.alternates(item.get("languages", []), lambda item_lang, item=item: routes.generated_item_route(item, item_lang)),
                            og_type="website",
                            shell=shell,
                        ),
                    )

    def render_root(self, base_html: str, site_meta: dict[str, Any], sections: list[dict[str, Any]], section_files: dict[str, list[dict[str, Any]]], languages: list[str]) -> None:
        self.render_home_page(base_html, site_meta, sections, section_files, languages, DEFAULT_LANG, "/", "/")

    def render_language_pages(self, base_html: str, site_meta: dict[str, Any], sections: list[dict[str, Any]], section_files: dict[str, list[dict[str, Any]]], languages: list[str]) -> None:
        for lang in languages:
            self.render_home_page(base_html, site_meta, sections, section_files, languages, lang, f"/{lang}", f"/{lang}")

    def render_home_page(
        self,
        base_html: str,
        site_meta: dict[str, Any],
        sections: list[dict[str, Any]],
        section_files: dict[str, list[dict[str, Any]]],
        languages: list[str],
        lang: str,
        route: str,
        canonical_path: str,
    ) -> None:
        page_meta = self.page_meta(site_meta, HOME_PAGE, lang)
        system_section = next(section for section in sections if section.get("system"))
        system_slug = str(system_section["slug"])
        shell = self.list_shell(
            lang=lang,
            sections=sections,
            folder_type=FolderType.SYSTEM,
            active_section=None,
            welcome_title=page_meta["title"],
            welcome_lead=page_meta["description"],
            home_files=section_files[system_slug],
            render_command="ls -p | grep -v /",
            process_html=self.section_process_html(lang, system_slug, section_files[system_slug], system=True),
        )

        self.write_route(
            route,
            self.render_page(
                base_html=base_html,
                lang=lang,
                title=page_meta["title"],
                description=page_meta["description"],
                canonical_path=canonical_path,
                alternates=routes.alternates(languages, lambda item_lang: f"/{item_lang}"),
                og_type="website",
                shell=shell,
            ),
        )

    def render_article_index_pages(
        self,
        base_html: str,
        site_meta: dict[str, Any],
        languages: list[str],
        article_section: str | None,
        sections: list[dict[str, Any]],
    ) -> None:
        if not article_section:
            return
        articles = generated.section_items(article_section)
        for lang in languages:
            page_meta = self.page_meta(site_meta, article_section, lang)
            page_items, total_pages = self.paginate_articles(articles, lang)
            shell = self.list_shell(
                lang=lang,
                sections=sections,
                folder_type=FolderType.ARTICLES,
                active_section=article_section,
                welcome_title=page_meta["title"],
                welcome_lead=page_meta["description"],
                articles=page_items,
                list_title=page_meta["title"],
                article_page=1,
                article_total_pages=total_pages,
                render_command="ls -p | grep -v / | sort -k 6,7 -r | head -n 4",
                process_html=self.list_process_html(lang, article_section, min(PAGE_SIZE, len(page_items)), len(page_items), total_pages),
            )

            self.write_route(
                routes.section_route(article_section, lang),
                self.render_page(
                    base_html=base_html,
                    lang=lang,
                    title=page_meta["title"],
                    description=page_meta["description"],
                    canonical_path=routes.section_route(article_section, lang),
                    alternates=routes.alternates(
                        languages,
                        lambda item_lang: routes.section_route(article_section, item_lang)
                    ),
                    og_type="website",
                    shell=shell,
                ),
            )

    def render_tag_index_pages(self, base_html: str, site_meta: dict[str, Any], languages: list[str], article_section: str | None, tag_section: str | None, sections: list[dict[str, Any]]) -> None:
        if not article_section or not tag_section:
            return
        articles = generated.section_items(article_section)
        for lang in languages:
            page_meta = self.page_meta(site_meta, tag_section, lang)
            tags = self.tag_counts(articles, lang)
            page_items, total_pages = self.paginate_tags(tags)
            shell = self.list_shell(
                lang=lang,
                sections=sections,
                folder_type=FolderType.TAGS,
                active_section=tag_section,
                welcome_title=page_meta["title"],
                welcome_lead=page_meta["description"],
                tags=page_items,
                tags_headline=page_meta["title"],
                tag_page=1,
                tag_total_pages=total_pages,
                render_command='grep -R "tag:" . | cut -d: -f2 | cut -d" " -f1 | sort -f | head -n 4',
                process_html=self.list_process_html(lang, tag_section, min(PAGE_SIZE, len(page_items)), len(page_items), total_pages),
            )

            self.write_route(
                routes.section_route(tag_section, lang),
                self.render_page(
                    base_html=base_html,
                    lang=lang,
                    title=page_meta["title"],
                    description=page_meta["description"],
                    canonical_path=routes.section_route(tag_section, lang),
                    alternates=routes.alternates(
                        languages,
                        lambda item_lang: routes.section_route(tag_section, item_lang)
                    ),
                    og_type="website",
                    shell=shell,
                ),
            )

    def render_article_pages(
        self,
        base_html: str,
        articles: list[dict[str, Any]],
        sections: list[dict[str, Any]],
        articles_by_slug: dict[str, dict[str, Any]],
        article_section: str | None,
        tag_section: str | None,
    ) -> None:
        for article in articles:
            slug = article["slug"]

            for lang in article["languages"]:
                article_html = read_text(GENERATED_FILES_DIR / str(article["section"]) / f"{slug}.{lang}.html")
                localized_meta = generated.localized_item(str(article["section"]), str(slug), lang)
                decorated_html = self.decorate_article_html(lang, article, article_html, tag_section or str(article["section"]))
                toc_html = self.render_toc(article_html)
                cite_value = self.tex_citation(article, lang)
                shell = self.article_shell(
                    lang=lang,
                    sections=sections,
                    file_type=FileType.ARTICLE,
                    active_section=article_section or str(article["section"]),
                    welcome_title=article["title"][lang],
                    welcome_lead=article["description"][lang],
                    welcome_command=f"sed -n '1,2p' {slug}.meta",
                    render_command=f"cat {slug}.tex",
                    process_html=self.article_process_html(lang, article, localized_meta),
                    content_html=decorated_html,
                    back_href=routes.section_route(str(article["section"]), lang),
                    download_text="pdf",
                    download_href=routes.generated_pdf_route(article, lang),
                    cite_value=cite_value,
                    edit_href=self.edit_href(localized_meta),
                    show_cite=True,
                    show_edit=True,
                    show_zen=True,
                    toc_html=toc_html,
                    show_toc=bool(toc_html),
                )

                self.write_route(
                    routes.generated_item_route(article, lang),
                    self.render_page(
                        base_html=base_html,
                        lang=lang,
                        title=article["title"][lang],
                        description=article["description"][lang],
                        canonical_path=routes.generated_item_route(article, lang),
                        alternates=routes.alternates(article["languages"], lambda item_lang, article=article: routes.generated_item_route(article, item_lang)),
                        og_type="article",
                        shell=shell,
                    ),
                )

    def render_tag_pages(
        self,
        base_html: str,
        site_meta: dict[str, Any],
        tags_by_lang: dict[str, set[str]],
        sections: list[dict[str, Any]],
        articles_by_slug: dict[str, dict[str, Any]],
        tag_section: str | None,
    ) -> None:
        if not tag_section:
            return
        for lang, tags in tags_by_lang.items():
            for tag in sorted(tags):
                page_meta = self.tag_page_meta(site_meta, lang, tag)
                tag_articles = [article for article in articles_by_slug.values() if lang in article.get("languages", []) and tag in article.get("tags", [])]
                page_items, total_pages = self.paginate_articles(tag_articles, lang)
                shell = self.list_shell(
                    lang=lang,
                    sections=sections,
                    folder_type=FolderType.TAGS,
                    active_section=tag_section,
                    welcome_title=page_meta["title"],
                    welcome_lead=page_meta["description"],
                    articles=page_items,
                    list_title=f"#{tag}",
                    tags_headline=f"#{tag}",
                    article_page=1,
                    article_total_pages=total_pages,
                    tag=tag,
                    render_command=f'grep -R "tag:{html.escape(tag, quote=True)}" . | sort -k 6,7 -r | head -n 4',
                    process_html=self.list_process_html(lang, tag_section, min(PAGE_SIZE, len(page_items)), len(page_items), total_pages, tag=tag),
                )

                self.write_route(
                    routes.tag_route(tag_section, lang, tag),
                    self.render_page(
                        base_html=base_html,
                        lang=lang,
                        title=page_meta["title"],
                        description=page_meta["description"],
                        canonical_path=routes.tag_route(tag_section, lang, tag),
                        alternates=self.tag_alternates(tag_section, tag, tags_by_lang),
                        og_type="website",
                        shell=shell,
                    ),
                )

    def render_page(
        self,
        base_html: str,
        lang: str,
        title: str,
        description: str,
        canonical_path: str,
        alternates: dict[str, str],
        og_type: str,
        shell: dict[str, Any] | None = None,
    ) -> str:
        head = self.render_head(
            lang=lang,
            title=title,
            description=description,
            canonical_path=canonical_path,
            alternates=alternates,
            og_type=og_type,
        )

        page = self.inject_head(base_html, head)

        if shell is not None:
            page = self.apply_shell(page, shell)

        return page

    def apply_shell(self, page: str, shell: dict[str, Any]) -> str:
        ui = self.shell_ui(str(shell["lang"]))
        cwd = str(shell.get("cwd") or "~")
        page = self.set_html_lang(page, str(shell["lang"]))
        page = self.replace_inner_html(page, "ascii-logo", html.escape(ASCII_LOGO), tag="pre")
        page = self.replace_inner_html(page, "pwd-line", self.shell_command_markup("ls -d */", cwd="~"), tag="p")
        page = self.replace_inner_html(page, "theme-label", html.escape(ui["theme_label"]), tag="span")
        page = self.replace_inner_html(page, "lang-label", html.escape(ui["lang_label"]), tag="span")
        page = self.replace_option_text(page, "reading", ui["theme_reading"])
        page = self.replace_option_text(page, "light", ui["theme_light"])
        page = self.replace_option_text(page, "system", ui["theme_system"])
        page = self.replace_option_text(page, "dark", ui["theme_dark"])
        page = self.replace_inner_html(page, "lang-switcher", self.render_language_options(str(shell["lang"])), tag="select")
        page = self.replace_inner_html(page, "welcome-command", self.shell_command_markup(str(shell["welcome_command"]), cwd=cwd))
        page = self.replace_inner_html(page, "welcome-title", html.escape(str(shell["welcome_title"])))
        page = self.replace_inner_html(page, "welcome-lead", html.escape(str(shell["welcome_lead"])))
        page = self.replace_inner_html(page, "welcome-body", html.escape(str(shell.get("welcome_body") or "")))
        page = self.replace_inner_html(page, "render-indicator", self.shell_command_markup(str(shell["render_command"]), cwd=cwd))
        page = self.replace_inner_html(page, "process-log", str(shell["process_html"]))
        page = self.replace_inner_html(page, "content-list-view", str(shell.get("list_stage_html") or ""), tag="section")
        page = self.replace_inner_html(page, "file-view", str(shell.get("file_stage_html") or ""), tag="article")
        page = self.replace_inner_html(
            page,
            "toc-panel",
            f'<h3 class="toc-title">{html.escape(ui["toc_title"])}</h3><ul id="toc-list" class="toc-list">{shell.get("toc_html") or ""}</ul>',
            tag="section",
        )
        page = self.replace_inner_html(page, "footer-motto", html.escape(ui["footer_motto"]), tag="p")
        page = self.set_element_attr(page, "brand-link", "href", f"/{shell['lang']}")
        page = self.replace_quick_nav(page, shell)
        page = self.apply_view_classes(page, shell)
        return page

    def replace_quick_nav(self, page: str, shell: dict[str, Any]) -> str:
        links = []
        active_section = shell.get("active_section")
        lang = str(shell["lang"])
        for section in shell["sections"]:
            if section.get("system"):
                continue
            classes = "quick-link is-active" if section.get("slug") == active_section else "quick-link"
            href = routes.generated_section_route(section, lang)
            label = self.localized(section.get("label"), lang, f"sections.{section.get('slug')}.label")
            links.append(f'<a class="{classes}" href="{html.escape(href, quote=True)}" data-internal="true">{html.escape(label)}</a>')
        return re.sub(
            r'(<nav\b[^>]*class="quick-nav"[^>]*aria-label="Sections"[^>]*>)([\s\S]*?)(</nav>)',
            lambda match: f"{match.group(1)}{''.join(links)}{match.group(3)}",
            page,
            count=1,
        )

    def apply_view_classes(self, page: str, shell: dict[str, Any]) -> str:
        view = str(shell.get("view") or "list")
        page = self.set_element_attr(page, "content-list-view", "class", "list-stage hidden" if view != "list" else "list-stage")
        page = self.set_element_attr(page, "file-view", "class", "file-stage" if view == "article" else "file-stage hidden")
        page = self.set_element_attr(page, "error-view", "class", "file-stage" if view == "error" else "file-stage hidden")
        page = self.set_element_attr(page, "toc-panel", "class", "toc-panel" if shell.get("show_toc") else "toc-panel hidden")
        return page

    def list_shell(
        self,
        *,
        lang: str,
        sections: list[dict[str, Any]],
        folder_type: FolderType,
        active_section: str | None,
        welcome_title: str,
        welcome_lead: str,
        render_command: str,
        process_html: str,
        home_files: list[dict[str, Any]] | None = None,
        articles: list[dict[str, Any]] | None = None,
        tags: list[dict[str, Any]] | None = None,
        list_title: str = "articles",
        tags_headline: str = "Tags",
        article_page: int = 1,
        article_total_pages: int = 1,
        tag_page: int = 1,
        tag_total_pages: int = 1,
        tag: str | None = None,
    ) -> dict[str, Any]:
        stage_html = self.render_folder_stage(
            folder_type=folder_type,
            lang=lang,
            home_files=home_files or [],
            articles=articles or [],
            tags=tags or [],
            list_title=list_title,
            tags_headline=tags_headline,
            article_page=article_page,
            article_total_pages=article_total_pages,
            tag_page=tag_page,
            tag_total_pages=tag_total_pages,
            tag=tag,
            active_section=active_section,
        )
        return {
            "lang": lang,
            "cwd": self.cwd_for_section(active_section),
            "sections": sections,
            "active_section": active_section,
            "view": "list",
            "tag": tag,
            "welcome_title": welcome_title,
            "welcome_lead": welcome_lead,
            "welcome_body": "",
            "welcome_command": self.left_info_command(active_section),
            "render_command": render_command,
            "process_html": process_html,
            "list_stage_html": stage_html,
            "show_toc": False,
        }

    def article_shell(
        self,
        *,
        lang: str,
        sections: list[dict[str, Any]],
        file_type: FileType,
        active_section: str | None,
        welcome_title: str,
        welcome_lead: str,
        welcome_command: str,
        render_command: str,
        process_html: str,
        content_html: str,
        back_href: str,
        download_text: str,
        download_href: str | None = None,
        cite_value: str | None = None,
        edit_href: str | None = None,
        show_cite: bool = False,
        show_edit: bool = False,
        show_zen: bool = False,
        toc_html: str = "",
        show_toc: bool = False,
    ) -> dict[str, Any]:
        stage_html = self.render_file_stage(
            file_type=file_type,
            lang=lang,
            back_href=back_href,
            download_text=download_text,
            download_href=download_href,
            cite_value=cite_value,
            edit_href=edit_href,
            content_html=content_html,
            show_cite=show_cite,
            show_edit=show_edit,
            show_zen=show_zen,
        )
        return {
            "lang": lang,
            "cwd": self.cwd_for_section(active_section),
            "sections": sections,
            "active_section": active_section,
            "view": "article",
            "welcome_title": welcome_title,
            "welcome_lead": welcome_lead,
            "welcome_body": "",
            "welcome_command": welcome_command,
            "render_command": render_command,
            "process_html": process_html,
            "file_stage_html": stage_html,
            "toc_html": toc_html,
            "show_toc": show_toc,
        }

    def section_process_html(self, lang: str, section: str, files: list[dict[str, Any]], system: bool = False) -> str:
        cwd = self.cwd_for_section(None if system else section)
        languages = sorted({item_lang for file in files for item_lang in file.get("languages", [])})
        translated = sum(1 for file in files if lang in file.get("languages", []))
        raw_files = sum(1 for file in files if file.get("format") != "tex")
        tex_files = sum(1 for file in files if file.get("format") == "tex")
        articles = sum(1 for file in files if file.get("type") == FileType.ARTICLE)
        downloads = sum(1 for file in files if file.get("downloadPath"))
        return "".join([
            self.shell_command_markup("statfs ~", cwd=cwd),
            self.stat_row("File system", "autophanyfs"),
            self.stat_row("Mounted on", f"/{lang}" if system else f"/{lang}/{section}"),
            self.stat_row("Type", "system-section" if system else "section"),
            self.stat_row("Flags", "ro, localized, indexed"),
            '<span class="meta-rule" aria-hidden="true"></span>',
            self.stat_row("mode", section if not system else "home"),
            self.stat_row("lang", lang),
            self.stat_row("files", str(len(files))),
            self.stat_row("languages", ", ".join(languages) or lang),
            self.stat_row("translated", f"{translated}/{len(files)}"),
            self.stat_row("raw files", str(raw_files)),
            self.stat_row("tex files", str(tex_files)),
            self.stat_row("articles", str(articles)),
            self.stat_row("downloads", str(downloads)),
            self.stat_row("index", f"generated/sections/{section}.json"),
        ])

    def list_process_html(self, lang: str, section: str, visible_items: int, total_items: int, total_pages: int, tag: str | None = None) -> str:
        cwd = self.cwd_for_section(section)
        scope = f"tag:{tag}" if tag else section
        return "".join([
            self.shell_command_markup("statfs ~", cwd=cwd),
            self.stat_row("File system", "autophanyfs"),
            self.stat_row("Mounted on", f"/{lang}/{section}"),
            self.stat_row("Type", "section"),
            self.stat_row("Flags", "ro, localized, indexed"),
            '<span class="meta-rule" aria-hidden="true"></span>',
            self.stat_row("mode", section),
            self.stat_row("lang", lang),
            self.stat_row("scope", scope),
            self.stat_row_html("shown", f'<span data-process-field="shown">{visible_items}</span>'),
            self.stat_row_html("total", f'<span data-process-field="total">{total_items}</span>'),
            self.stat_row_html("page", '<span data-process-field="page">1</span>'),
            self.stat_row_html("pages", f'<span data-process-field="pages">{total_pages}</span>'),
        ])

    def article_process_html(self, lang: str, article: dict[str, Any], localized_meta: dict[str, Any]) -> str:
        stamp = f"{article.get('date') or '1970-01-01'} 00:00:00 +0000"
        cwd = self.cwd_for_section(str(article["section"]))
        file_name = f"{article['slug']}.tex"
        file_path = f"~/{article['section']}/{article['slug']}.tex"
        tags_html = " ".join(
            f'<a class="meta-tag-link" href="{html.escape(routes.tag_route(str(article.get("tagSection") or article["section"]), lang, str(tag)), quote=True)}" data-internal="true">#{html.escape(str(tag))}</a>'
            for tag in article.get("tags", [])
        )
        return "".join([
            self.shell_command_markup(f"stat {file_name}", cwd=cwd),
            self.stat_row("File", file_path),
            self.stat_row("Size", str(localized_meta.get("byteSize") or 0)),
            self.stat_row("Blocks", "8"),
            self.stat_row("IO", "4096 regular file"),
            self.stat_row("Device", "autophanyfs"),
            self.stat_row("Inode", "042"),
            self.stat_row("Links", "1"),
            self.stat_row("Access", "(0664/-rw-rw-r--)"),
            self.stat_row("Uid", "(0/root)"),
            self.stat_row("Gid", "(42/operators)"),
            self.stat_row("Birth", stamp),
            self.stat_row("Mtime", stamp),
            '<span class="meta-rule" aria-hidden="true"></span>',
            self.stat_row("slug", str(article["slug"])),
            self.stat_row("lang", lang),
            self.stat_row("langs", ", ".join(article.get("languages", []))),
            self.stat_row_html("tags", tags_html),
            self.stat_row("words", str(localized_meta.get("wordCount") or 0)),
            self.stat_row("chars", str(localized_meta.get("charCount") or 0)),
            self.stat_row("pdf", str(localized_meta.get("pdfPath") or routes.generated_pdf_route(article, lang))),
        ])

    def info_file_process_html(self, lang: str, section: str, slug: str, display_name: str, item: dict[str, Any], localized_meta: dict[str, Any]) -> str:
        stamp = f"{item.get('date') or '1970-01-01'} 00:00:00 +0000"
        cwd = self.cwd_for_section(section)
        file_path = self.display_file_path(section, display_name)
        return "".join([
            self.shell_command_markup(f"stat {display_name}", cwd=cwd),
            self.stat_row("File", file_path),
            self.stat_row("Size", str(localized_meta.get("byteSize") or 0)),
            self.stat_row("Blocks", "8"),
            self.stat_row("IO", "4096 regular file"),
            self.stat_row("Device", "autophanyfs"),
            self.stat_row("Inode", "021"),
            self.stat_row("Links", "1"),
            self.stat_row("Access", "(0664/-rw-rw-r--)"),
            self.stat_row("Uid", "(0/root)"),
            self.stat_row("Gid", "(42/operators)"),
            self.stat_row("Birth", stamp),
            self.stat_row("Mtime", stamp),
            '<span class="meta-rule" aria-hidden="true"></span>',
            self.stat_row("name", display_name),
            self.stat_row("lang", lang),
            self.stat_row("langs", ", ".join(item.get("languages", []))),
            self.stat_row("type", str(item.get("type") or FileType.PAGE)),
            self.stat_row("format", str(item.get("format") or "text")),
        ])

    def paginate_articles(self, articles: list[dict[str, Any]], lang: str) -> tuple[list[dict[str, Any]], int]:
        localized_articles = [article for article in articles if lang in article.get("languages", [])]
        sorted_articles = sorted(localized_articles, key=lambda article: (str(article.get("date") or ""), self.localized(article.get("title"), lang, f"articles.{article.get('slug')}.title")), reverse=True)
        total_pages = max(1, (len(sorted_articles) + PAGE_SIZE - 1) // PAGE_SIZE)
        return sorted_articles, total_pages

    def tag_counts(self, articles: list[dict[str, Any]], lang: str) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for article in articles:
            if lang not in article.get("languages", []):
                continue
            for tag in article.get("tags", []):
                counts[str(tag)] = counts.get(str(tag), 0) + 1
        return [{"name": name, "count": count} for name, count in sorted(counts.items(), key=lambda item: item[0])]

    def paginate_tags(self, tags: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
        total_pages = max(1, (len(tags) + PAGE_SIZE - 1) // PAGE_SIZE)
        return tags, total_pages

    def render_info_files(self, files: list[dict[str, Any]], lang: str) -> str:
        rows = []
        for file in files:
            slug = str(file["slug"])
            href = routes.generated_item_route(file, lang)
            label = exact_text(file.get("label"), lang) or slug
            description = exact_text(file.get("description"), lang)
            date = str(file.get("date") or "----------")
            rows.append(
                f'<li class="info-file-row"><a class="info-file-link" href="{html.escape(href, quote=True)}" data-info-file-slug="{html.escape(slug, quote=True)}" data-internal="true" aria-label="{html.escape(f"{slug}: {description}", quote=True)}"><span class="info-file-perms">-rw-rw-r--  root  {html.escape(date)}</span>  <span class="info-file-name">{html.escape(label or slug)}</span></a></li>'
            )
        return f'<ul class="info-file-tree">{"".join(rows)}</ul>' if rows else ""

    def render_articles(self, articles: list[dict[str, Any]], lang: str) -> str:
        rows = []
        for article in articles:
            slug = str(article["slug"])
            href = routes.generated_item_route(article, lang)
            title = self.localized(article.get("title"), lang, f"articles.{slug}.title")
            description = self.localized(article.get("description"), lang, f"articles.{slug}.description")
            tags = " ".join(f'<span class="inline-tag">#{html.escape(str(tag))}</span>' for tag in article.get("tags", []))
            search = " ".join(filter(None, [slug, title, description, str(article.get("date") or ""), *(str(tag) for tag in article.get("tags", []))])).lower()
            rows.append(
                f'<li class="article-card" data-list-item data-search="{html.escape(search, quote=True)}" data-sort-title="{html.escape(title.lower(), quote=True)}" data-sort-date="{html.escape(str(article.get("date") or ""), quote=True)}"><a class="article-card-link article-card-full" href="{html.escape(href, quote=True)}" data-internal="true"><strong>{html.escape(title)}</strong><div class="meta">{html.escape(str(article.get("date") or ""))} · {html.escape(description)}</div><div class="meta tag-line">{tags}</div></a></li>'
            )
        return "".join(rows)

    def render_tags(self, tags: list[dict[str, Any]], lang: str, active_tag: str | None = None, tag_section: str | None = None) -> str:
        rows = []
        for tag in tags:
            name = str(tag["name"])
            count = int(tag["count"])
            active = " is-active" if active_tag == name else ""
            href = routes.tag_route(tag_section or "tags", lang, name)
            rows.append(
                f'<li class="tag-card" data-list-item data-search="{html.escape(name.lower(), quote=True)}" data-sort-name="{html.escape(name.lower(), quote=True)}" data-sort-count="{count}"><a class="tag-row{active}" href="{html.escape(href, quote=True)}" data-tag="{html.escape(name, quote=True)}" data-internal="true"><span class="tag-name">#{html.escape(name)}</span><span class="tag-count">{count} file{"" if count == 1 else "s"}</span></a></li>'
            )
        return "".join(rows)

    def render_folder_stage(
        self,
        *,
        folder_type: FolderType,
        lang: str,
        home_files: list[dict[str, Any]],
        articles: list[dict[str, Any]],
        tags: list[dict[str, Any]],
        list_title: str,
        tags_headline: str,
        article_page: int,
        article_total_pages: int,
        tag_page: int,
        tag_total_pages: int,
        tag: str | None,
        active_section: str | None,
    ) -> str:
        ui = self.shell_ui(lang)
        if folder_type in {FolderType.SYSTEM, FolderType.FILES}:
            return self.templates.render(
                f"folders/{folder_type.value}.html",
                items_html=self.render_info_files(home_files, lang),
            )
        if folder_type == FolderType.ARTICLES:
            return self.templates.render(
                "folders/articles.html",
                list_title=html.escape(list_title),
                search_placeholder=html.escape(ui["search_placeholder"]),
                sort_label=html.escape(ui["sort_label"]),
                size_label=html.escape(ui["size_label"]),
                date_desc_label=html.escape(ui["date_desc_label"]),
                date_asc_label=html.escape(ui["date_asc_label"]),
                title_asc_label=html.escape(ui["title_asc_label"]),
                title_desc_label=html.escape(ui["title_desc_label"]),
                items_html=self.render_articles(articles, lang),
                pager_class="pager-row hidden" if article_total_pages <= 1 else "pager-row",
                page_prev=html.escape(ui["page_prev"]),
                page_next=html.escape(ui["page_next"]),
                page_info=html.escape(f"{article_page}/{article_total_pages}"),
            )
        return self.templates.render(
            "folders/tags.html",
            content_panel_class="panel directory-panel" if tag else "panel hidden directory-panel",
            list_title=html.escape(list_title),
            search_placeholder=html.escape(ui["search_placeholder"]),
            sort_label=html.escape(ui["sort_label"]),
            size_label=html.escape(ui["size_label"]),
            date_desc_label=html.escape(ui["date_desc_label"]),
            date_asc_label=html.escape(ui["date_asc_label"]),
            title_asc_label=html.escape(ui["title_asc_label"]),
            title_desc_label=html.escape(ui["title_desc_label"]),
            articles_html=self.render_articles(articles, lang),
            pager_class="pager-row hidden" if article_total_pages <= 1 else "pager-row",
            page_prev=html.escape(ui["page_prev"]),
            page_next=html.escape(ui["page_next"]),
            page_info=html.escape(f"{article_page}/{article_total_pages}"),
            tags_panel_class="panel hidden directory-panel" if tag else "panel directory-panel",
            tags_headline=html.escape(tags_headline),
            tag_search_placeholder=html.escape(ui["tag_search_placeholder"]),
            tag_sort_label=html.escape(ui["tag_sort_label"]),
            tag_size_label=html.escape(ui["tag_size_label"]),
            name_asc_label=html.escape(ui["name_asc_label"]),
            name_desc_label=html.escape(ui["name_desc_label"]),
            count_desc_label=html.escape(ui["count_desc_label"]),
            count_asc_label=html.escape(ui["count_asc_label"]),
            tags_html=self.render_tags(tags, lang, tag, active_section),
            tag_pager_class="pager-row tag-pager-row hidden" if tag_total_pages <= 1 else "pager-row tag-pager-row",
            tag_page_info=html.escape(f"{tag_page}/{tag_total_pages}"),
        )

    def render_file_stage(
        self,
        *,
        file_type: FileType,
        lang: str,
        back_href: str,
        download_text: str,
        download_href: str | None,
        cite_value: str | None,
        edit_href: str | None,
        content_html: str,
        show_cite: bool,
        show_edit: bool,
        show_zen: bool,
    ) -> str:
        ui = self.shell_ui(lang)
        return self.templates.render(
            f"files/{file_type.value}.html",
            back_href=html.escape(back_href, quote=True),
            back_label=html.escape(ui["back_label"]),
            download_class="download-btn action-chip" if download_href else "download-btn action-chip hidden",
            download_href=html.escape(download_href or "", quote=True),
            download_text=html.escape(download_text),
            cite_class="download-btn action-chip" if show_cite and cite_value else "download-btn action-chip hidden",
            cite_value=html.escape(cite_value or "", quote=True).replace("\n", "&#10;"),
            cite_text=html.escape(ui["cite_text"]),
            copied_text=html.escape(ui["copied_text"]),
            copy_toast_success=html.escape(ui["copy_toast_success"]),
            copy_toast_failure=html.escape(ui["copy_toast_failure"]),
            edit_class="download-btn action-chip" if show_edit and edit_href else "download-btn action-chip hidden",
            edit_href=html.escape(edit_href or "", quote=True),
            edit_text=html.escape(ui["edit_text"]),
            zen_class="download-btn action-chip" if show_zen else "download-btn action-chip hidden",
            zen_text=html.escape(ui["zen_text"]),
            content_html=content_html,
        )

    def decorate_article_html(self, lang: str, article: dict[str, Any], article_html: str, tag_section: str) -> str:
        slug = str(article["slug"])
        top_nav = (
            '<nav class="article-breadcrumbs" aria-label="Breadcrumbs">'
            f'<a href="/{html.escape(lang, quote=True)}" data-internal="true">root</a>'
            ' / '
            f'<a href="{html.escape(routes.section_route(str(article["section"]), lang), quote=True)}" data-internal="true">articles</a>'
            ' / '
            f'<span>{html.escape(slug)}</span>'
            '</nav>'
        )
        tags = " ".join(
            f'<a class="meta-tag-link" href="{html.escape(routes.tag_route(tag_section, lang, str(tag)), quote=True)}" data-internal="true">#{html.escape(str(tag))}</a>'
            for tag in article.get("tags", [])
        )
        files = f'<p class="article-file-links"><a href="{html.escape(routes.generated_pdf_route(article, lang), quote=True)}" target="_blank" rel="noopener noreferrer">download PDF</a></p>'
        neighbors = []
        previous = article.get("prev")
        next_article = article.get("next")
        if isinstance(previous, dict) and previous.get("path") and previous.get("title"):
            neighbors.append(f'<a href="{html.escape(str(previous["path"]), quote=True)}" data-internal="true">previous: {html.escape(str(previous["title"]))}</a>')
        if isinstance(next_article, dict) and next_article.get("path") and next_article.get("title"):
            neighbors.append(f'<a href="{html.escape(str(next_article["path"]), quote=True)}" data-internal="true">next: {html.escape(str(next_article["title"]))}</a>')
        neighbors_html = f'<p class="article-neighbor-links">{" · ".join(neighbors)}</p>' if neighbors else ""
        bottom_nav = (
            '<nav class="article-seo-links" aria-label="Article links">'
            f'<p class="article-tag-links">tags: {tags}</p>'
            f'{files}'
            f'{neighbors_html}'
            '</nav>'
        )
        return f"{top_nav}{article_html}{bottom_nav}"

    def render_toc(self, article_html: str) -> str:
        items = []
        for level, heading_id, content in re.findall(r'<h([1-6])\b[^>]*\bid=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</h\1>', article_html, re.IGNORECASE):
            text = html.unescape(re.sub(r"<[^>]+>", "", content)).replace("#", "").strip()
            if not text:
                continue
            depth = min(max(int(level), 1), 6)
            items.append(
                f'<li class="toc-item toc-level-{depth}"><a href="#{html.escape(heading_id, quote=True)}" data-heading-id="{html.escape(heading_id, quote=True)}">{html.escape(text)}</a></li>'
            )
        return "".join(items)

    @staticmethod
    def shell_command_markup(command: str, cwd: str = "~") -> str:
        prompt = f"guest@cray-1:{cwd}"
        return f'<span class="stat-command"><span class="shell-prompt"><span class="shell-prompt-text">{html.escape(prompt)}</span><span class="shell-prompt-sign">$</span></span><span class="shell-gap"> </span><span class="shell-cmd">{html.escape(command)}</span></span>'

    @staticmethod
    def stat_row(key: str, value: str) -> str:
        return Prerender.stat_row_html(key, html.escape(value))

    @staticmethod
    def stat_row_html(key: str, value_html: str) -> str:
        return f'<span class="stat-row"><span class="stat-key">{html.escape(key)}</span><span class="stat-sep">:</span><span class="stat-value">{value_html}</span></span>'

    @staticmethod
    def left_info_command(active_section: str | None) -> str:
        if not active_section:
            return "sed -n '1,2p' .meta"
        return f"sed -n '1,2p' {active_section}.meta"

    @staticmethod
    def display_file_path(section: str, slug: str) -> str:
        return f"~/{slug}" if section == "site" else f"~/{section}/{slug}"

    @staticmethod
    def cwd_for_section(section: str | None) -> str:
        if not section or section == "site":
            return "~"
        return f"~/{section}"

    @staticmethod
    def shell_ui(lang: str) -> dict[str, str]:
        if lang == "ru":
            return {
                "theme_label": "$ export THEME=",
                "lang_label": "$ localectl set-locale LANG=",
                "theme_reading": "paper/бумага",
                "theme_light": "day/день",
                "theme_system": "system/система",
                "theme_dark": "night/ночь",
                "footer_motto": "Следуй любопытству. Веди человечество вперёд",
                "search_placeholder": "pattern",
                "tag_search_placeholder": "tag",
                "sort_label": "sort:",
                "size_label": "size:",
                "tag_sort_label": "sort:",
                "tag_size_label": "head:",
                "page_prev": "[PREV]",
                "page_next": "[NEXT]",
                "toc_title": "headings",
                "back_label": "cd ..",
                "cite_text": "cite",
                "copied_text": "copied",
                "copy_toast_success": "цитата скопирована в буфер обмена",
                "copy_toast_failure": "не удалось скопировать",
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
        return {
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
            "back_label": "cd ..",
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

    def render_language_options(self, active_lang: str) -> str:
        options = []
        for lang in self.languages:
            selected = ' selected="selected"' if lang == active_lang else ""
            locale = f"{lang}_{('RU' if lang == 'ru' else 'US')}.UTF-8" if "-" not in lang else lang.replace("-", "_") + ".UTF-8"
            options.append(f'<option value="{html.escape(lang, quote=True)}"{selected}>{html.escape(locale)}</option>')
        return "".join(options)

    @staticmethod
    def edit_href(localized_meta: dict[str, Any]) -> str | None:
        source_path = localized_meta.get("sourcePath")
        if not isinstance(source_path, str) or not source_path:
            return None
        relative = source_path.removeprefix("content/")
        return f"{GITHUB_EDIT_BASE}/{quote(relative, safe='/')}"

    @staticmethod
    def set_html_lang(page: str, lang: str) -> str:
        return re.sub(r'<html\s+lang="[^"]+"', f'<html lang="{html.escape(lang, quote=True)}"', page, count=1)

    @staticmethod
    def replace_inner_html(page: str, element_id: str, inner_html: str, tag: str | None = None) -> str:
        tag_pattern = tag or r"[^\s>]+"
        pattern = re.compile(rf'(<(?P<tag>{tag_pattern})[^>]*\bid="{re.escape(element_id)}"[^>]*>)([\s\S]*?)(</(?P=tag)>)', re.IGNORECASE)
        return pattern.sub(lambda match: f"{match.group(1)}{inner_html}{match.group(4)}", page, count=1)

    @staticmethod
    def replace_option_text(page: str, value: str, text: str) -> str:
        return re.sub(rf'(<option value="{re.escape(value)}">)([\s\S]*?)(</option>)', lambda match: f"{match.group(1)}{html.escape(text)}{match.group(3)}", page, count=1)

    @staticmethod
    def set_element_attr(page: str, element_id: str, attr: str, value: str) -> str:
        pattern = re.compile(rf'(<[^>]*\bid="{re.escape(element_id)}"[^>]*)(>)', re.IGNORECASE)

        def replace(match: re.Match[str]) -> str:
            start = match.group(1)
            attr_pattern = re.compile(rf'\s{re.escape(attr)}="[^"]*"', re.IGNORECASE)
            replacement = f' {attr}="{html.escape(value, quote=True)}"'
            if attr_pattern.search(start):
                start = attr_pattern.sub(replacement, start, count=1)
            else:
                start = f"{start}{replacement}"
            return f"{start}{match.group(2)}"

        return pattern.sub(replace, page, count=1)

    def render_head(
        self,
        lang: str,
        title: str,
        description: str,
        canonical_path: str,
        alternates: dict[str, str],
        og_type: str,
    ) -> str:
        canonical_url = routes.absolute_url(canonical_path)

        lines = [
            '    <meta charset="UTF-8" />',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />',
            '    <meta name="robots" content="index,follow" />',
            f"    <title>{html.escape(title)}</title>",
            f'    <meta name="description" content="{html.escape(description, quote=True)}" />',
            '    <link rel="icon" type="image/png" sizes="96x96" href="/icons/favicon-96x96.png" />',
            '    <link rel="shortcut icon" href="/icons/favicon.ico" />',
            '    <link rel="apple-touch-icon" sizes="180x180" href="/icons/apple-touch-icon.png" />',
            '    <link rel="manifest" href="/icons/site.webmanifest" />',
            f'    <link rel="canonical" href="{html.escape(canonical_url, quote=True)}" />',
            f'    <meta property="og:title" content="{html.escape(title, quote=True)}" />',
            f'    <meta property="og:description" content="{html.escape(description, quote=True)}" />',
            f'    <meta property="og:url" content="{html.escape(canonical_url, quote=True)}" />',
            f'    <meta property="og:type" content="{html.escape(og_type, quote=True)}" />',
            f'    <meta property="og:locale" content="{html.escape(lang, quote=True)}" />',
        ]

        for hreflang, path in alternates.items():
            lines.append(
                f'    <link rel="alternate" hreflang="{html.escape(hreflang, quote=True)}" '
                f'href="{html.escape(routes.absolute_url(path), quote=True)}" />'
            )

        return "\n".join(lines)

    @classmethod
    def inject_head(cls, base_html: str, head: str) -> str:
        runtime_tags = cls.extract_runtime_head_tags(base_html)
        full_head = f"{head}\n{runtime_tags}" if runtime_tags else head

        return re.sub(
            r"<head>[\s\S]*?</head>",
            f"<head>\n{full_head}\n  </head>",
            base_html,
            count=1,
            flags=re.IGNORECASE,
        )

    @classmethod
    def extract_runtime_head_tags(cls, base_html: str) -> str:
        match = re.search(r"<head>([\s\S]*?)</head>", base_html, re.IGNORECASE)

        if not match:
            return ""

        return "\n".join(
            item.group(0).strip()
            for item in cls.runtime_head_tag_re.finditer(match.group(1))
        )

    def page_meta(self, site_meta: dict[str, Any], page: str, lang: str) -> dict[str, str]:
        pages = site_meta.get("pages")

        if not isinstance(pages, dict) or page not in pages:
            raise RuntimeError(f"Missing site metadata page: {page}")

        data = pages[page]

        return {
            "title": self.localized(data.get("title"), lang, f"pages.{page}.title"),
            "description": self.localized(
                data.get("description"),
                lang,
                f"pages.{page}.description",
            ),
        }

    def tag_page_meta(
        self,
        site_meta: dict[str, Any],
        lang: str,
        tag: str,
    ) -> dict[str, str]:
        data = site_meta.get("pages", {}).get(TAG_PAGE)

        if not isinstance(data, dict):
            raise RuntimeError(f"Missing site metadata page: {TAG_PAGE}")

        return {
            "title": self.localized(data.get("title"), lang, f"pages.{TAG_PAGE}.title").format(tag=tag),
            "description": self.localized(
                data.get("description"),
                lang,
                f"pages.{TAG_PAGE}.description",
            ).format(tag=tag),
        }

    @staticmethod
    def localized(value: Any, lang: str, path: str) -> str:
        return strict_text(value, lang, path)

    @staticmethod
    def tag_alternates(section: str, tag: str, tags_by_lang: dict[str, set[str]]) -> dict[str, str]:
        alternates = {
            lang: routes.tag_route(section, lang, tag)
            for lang, tags in tags_by_lang.items()
            if tag in tags
        }

        alternates["x-default"] = alternates.get(DEFAULT_LANG) or next(iter(alternates.values()))
        return alternates

    def tex_citation(self, article: dict[str, Any], lang: str) -> str:
        title = self.localized(article.get("title"), lang, f"articles.{article.get('slug')}.title")
        year = str(article.get("date") or "").split("-", 1)[0] or "n.d."
        article_url = routes.absolute_url(routes.generated_item_route(article, lang))
        access_date = datetime.now(UTC).date().isoformat()
        key = f"autophany-{self.bibtex_key(str(article['slug']))}-{self.bibtex_key(lang)}"
        return "\n".join([
            f"@misc{{{key},",
            f"  title = {{{self.escape_tex(title)}}},",
            f"  year = {{{self.escape_tex(year)}}},",
            f"  howpublished = {{\\url{{{article_url}}}}},",
            f"  note = {{{self.escape_tex(f'Article on autophany.space; accessed {access_date}')}}},",
            f"  language = {{{self.escape_tex(lang)}}},",
            "}",
        ])

    @staticmethod
    def bibtex_key(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"

    @staticmethod
    def escape_tex(value: str) -> str:
        replacements = {
            "\\": r"\\textbackslash{}",
            "{": r"\\{",
            "}": r"\\}",
            "#": r"\\#",
            "$": r"\\$",
            "%": r"\\%",
            "&": r"\\&",
            "_": r"\\_",
        }
        return "".join(replacements.get(char, char) for char in value)


    @staticmethod
    def write_route(route: str, content: str) -> None:
        if route == "/":
            path = DIST_DIR / "index.html"
        else:
            path = DIST_DIR / route.strip("/") / "index.html"

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def run() -> None:
    Prerender().run()
