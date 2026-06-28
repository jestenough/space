"""Base file renderer contract and generic page behavior"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from ... import content, routes
from ...config import DEFAULT_LANG, SYSTEM_SECTION, ContentExtension, FileType
from ...localization import exact_text, strict_text
from ..context import (
    FileIndexContext,
    FilePageContext,
    FileShellContext,
    LocalizedMetaContext,
    RouteRender,
    SourceRenderContext,
)


class FileRenderer:
    file_type = FileType.PAGE
    code_block_re = re.compile(r"<pre\b[^>]*>[\s\S]*?</pre>", re.IGNORECASE)
    pre_parts_re = re.compile(r"^(?P<pre_start><pre\b[^>]*>)(?P<body>[\s\S]*?)(?P<pre_end></pre>)$", re.IGNORECASE)
    code_parts_re = re.compile(r"^(?P<code_start>\s*<code\b[^>]*>)(?P<body>[\s\S]*?)(?P<code_end></code>\s*)$", re.IGNORECASE)
    class_attr_re = re.compile(r"\bclass=[\"']([^\"']+)[\"']", re.IGNORECASE)
    tag_re = re.compile(r"<[^>]+>")
    ignored_language_classes = frozenset({"code", "code-line", "hljs", "info-file-pre", "numbersource", "sourcecode"})
    language_aliases = {
        "bash": "shell",
        "js": "javascript",
        "jsx": "javascript jsx",
        "py": "python",
        "sh": "shell",
        "ts": "typescript",
        "tsx": "typescript jsx",
    }
    code_copy_ui_by_lang = {
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

    def index_meta(self, _: FileIndexContext) -> dict[str, Any]:
        return {}

    def localized_meta(self, _: LocalizedMetaContext) -> dict[str, Any]:
        return {}

    def postprocess_indexes(self, _: dict[str, list[dict[str, Any]]]) -> None:
        return None

    def render_source(self, context: SourceRenderContext) -> str:
        source = context.source
        item = context.item

        if source.ext == ContentExtension.TEX:
            body = context.convert_tex_to_html(source.path, item.path, item.section, item.slug)
        elif source.ext == ContentExtension.MARKDOWN:
            body = context.convert_markdown_to_html(source.path, item.path, item.section, item.slug)
        else:
            text = source.path.read_text(encoding="utf-8")
            return self.wrap_document(source, f'<pre class="info-file-pre">{html.escape(text.rstrip())}</pre>')

        return self.wrap_document(source, self.decorate_code_blocks(body, source.lang))

    @staticmethod
    def wrap_document(source: content.Source, body: str) -> str:
        return f'<section class="file-document" data-source="{html.escape(str(source.path))}">{body}</section>\n'

    def decorate_code_blocks(self, value: str, lang: str) -> str:
        ui = self.code_copy_ui(lang)

        def replace(match: re.Match[str]) -> str:
            pre_html = match.group(0)
            if "data-code-copy-block" in pre_html:
                return pre_html

            copy_text = self.pre_text(pre_html).rstrip("\n")
            if not copy_text.strip():
                return pre_html
            pre_with_lines = self.decorate_code_lines(pre_html, copy_text, ui)
            language = self.code_language(pre_html) or ui["label"]

            return (
                '<div class="code-copy-block" data-code-copy-block>'
                '<div class="code-copy-bar">'
                f'<span class="code-copy-label">{html.escape(language)}</span>'
                '<button class="code-copy-btn" type="button" '
                f'data-copy-text="{self.attribute_value(copy_text)}" '
                f'data-copy-label="{html.escape(ui["copy"], quote=True)}" '
                f'data-copy-success="{html.escape(ui["copied"], quote=True)}" '
                f'data-copy-toast-success="{html.escape(ui["toast_success"], quote=True)}" '
                f'data-copy-toast-failure="{html.escape(ui["toast_failure"], quote=True)}">'
                f'{html.escape(ui["copy"])}'
                "</button>"
                "</div>"
                f"{pre_with_lines}"
                "</div>"
            )

        return self.code_block_re.sub(replace, value)

    def decorate_code_lines(self, pre_html: str, copy_text: str, ui: dict[str, str]) -> str:
        pre_match = self.pre_parts_re.match(pre_html)
        if not pre_match:
            return pre_html

        body = pre_match.group("body")
        code_match = self.code_parts_re.match(body)
        code_start = code_match.group("code_start") if code_match else ""
        code_body = code_match.group("body") if code_match else body
        code_end = code_match.group("code_end") if code_match else ""
        lines_html = self.render_code_lines(copy_text, ui, code_body)

        return "".join(
            [
                pre_match.group("pre_start"),
                code_start,
                lines_html,
                code_end,
                pre_match.group("pre_end"),
            ]
        )

    def render_code_lines(self, value: str, ui: dict[str, str], html_value: str | None = None) -> str:
        lines = value.split("\n")
        html_lines = html_value.rstrip("\n").split("\n") if html_value is not None else []
        if len(html_lines) != len(lines):
            html_lines = [html.escape(line) for line in lines]

        return "".join(self.render_code_line(line, ui, html_lines[index]) for index, line in enumerate(lines))

    def render_code_line(self, line: str, ui: dict[str, str], line_html: str) -> str:
        if not line.strip():
            return '<span class="code-line code-line-empty" data-code-line><span class="code-line-text"> </span></span>'

        return (
            '<span class="code-line" data-code-line role="button" tabindex="0" '
            f'aria-label="{html.escape(ui["line_copy"], quote=True)}" '
            f'title="{html.escape(ui["line_copy"], quote=True)}" '
            f'data-copy-value="{self.attribute_value(line)}" '
            f'data-copy-toast-success="{html.escape(ui["line_toast_success"], quote=True)}" '
            f'data-copy-toast-failure="{html.escape(ui["toast_failure"], quote=True)}">'
            f'<span class="code-line-text">{line_html or " "}</span>'
            "</span>"
        )

    def code_language(self, pre_html: str) -> str | None:
        candidates = self.tag_classes(pre_html, "code") + self.tag_classes(pre_html, "pre")
        for value in candidates:
            candidate = self.normalize_language_class(value)
            if not candidate:
                continue
            return self.language_aliases.get(candidate, candidate)

        return None

    def normalize_language_class(self, value: str) -> str | None:
        candidate = value.strip()
        for prefix in ("language-", "lang-"):
            if candidate.startswith(prefix):
                candidate = candidate.removeprefix(prefix)
                break

        candidate = candidate.lower()
        return None if not candidate or candidate in self.ignored_language_classes else candidate

    def tag_classes(self, value: str, tag: str) -> list[str]:
        classes: list[str] = []
        for tag_match in re.finditer(rf"<{tag}\b[^>]*>", value, re.IGNORECASE):
            class_match = self.class_attr_re.search(tag_match.group(0))
            if class_match:
                classes.extend(class_match.group(1).split())
        return classes

    @classmethod
    def pre_text(cls, value: str) -> str:
        inner = re.sub(r"^<pre\b[^>]*>|</pre>$", "", value, flags=re.IGNORECASE)
        return html.unescape(cls.tag_re.sub("", inner))

    @staticmethod
    def attribute_value(value: str) -> str:
        return html.escape(value, quote=True).replace("\r", "").replace("\n", "&#10;")

    @staticmethod
    def code_copy_ui(lang: str) -> dict[str, str]:
        try:
            return FileRenderer.code_copy_ui_by_lang[lang]
        except KeyError as exc:
            raise RuntimeError(
                f"Missing code-copy UI translations for language `{lang}`. "
                "Add this language to FileRenderer.code_copy_ui_by_lang in scripts/rendering/files/base.py."
            ) from exc

    def render_page(self, context: FilePageContext) -> RouteRender:
        title = strict_text(
            context.item.get("title"), context.lang, f"{context.section_slug}.{context.item_slug}.title"
        )
        description = strict_text(
            context.item.get("description"), context.lang, f"{context.section_slug}.{context.item_slug}.description"
        )
        display_name = self.display_name(context)
        toc_html = self.render_toc(context.content_html) if self.show_toc_for(context) else ""
        shell = context.service.file_shell(
            FileShellContext(
                lang=context.lang,
                sections=context.sections,
                file_type=self.file_type,
                active_section=None if context.section.get("system") else context.section_slug,
                welcome_title=title,
                welcome_lead=description,
                welcome_command=f"sed -n '1,2p' {context.item_slug}.meta",
                render_command=f"cat {display_name}",
                process_html=self.process_html(context, display_name),
                content_html=context.content_html,
                back_href=routes.generated_section_route(context.section, context.lang),
                download_text="download",
                download_href=context.item.get("downloadPath") if context.item.get("downloadPath") else None,
                show_zen=self.is_readable_source(context),
                toc_html=toc_html,
                show_toc=bool(toc_html),
                template_context=self.template_context(context),
            )
        )

        return RouteRender(
            route=routes.generated_item_route(context.item, context.lang),
            lang=context.lang,
            title=title,
            description=description,
            canonical_path=routes.generated_item_route(context.item, context.lang),
            alternates=routes.alternates(
                context.item.get("languages", []),
                lambda item_lang: routes.generated_item_route(context.item, item_lang),
            ),
            og_type="website",
            shell=shell,
        )

    def template_context(self, _: FilePageContext) -> dict[str, str] | None:
        return None

    def display_name(self, context: FilePageContext) -> str:
        return exact_text(context.item.get("label"), context.lang) or context.item_slug

    def is_readable_source(self, context: FilePageContext) -> bool:
        source_path = str(context.localized_meta.get("sourcePath") or "")
        ext = Path(source_path).suffix.lower().lstrip(".")
        return ext in {"txt", "md", "tex"}

    def show_toc_for(self, context: FilePageContext) -> bool:
        source_path = str(context.localized_meta.get("sourcePath") or "")
        return Path(source_path).suffix.lower() == ".md"

    @staticmethod
    def render_toc(content_html: str) -> str:
        items = []
        for level, heading_id, _content in re.findall(
            r'<h([1-6])\b[^>]*\bid=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</h\1>', content_html, re.IGNORECASE
        ):
            text = html.unescape(re.sub(r"<[^>]+>", "", _content)).replace("#", "").strip()
            if text:
                depth = min(max(int(level), 1), 6)
                items.append(
                    f'<li class="toc-item toc-level-{depth}"><a href="#{html.escape(heading_id, quote=True)}" data-heading-id="{html.escape(heading_id, quote=True)}">{html.escape(text)}</a></li>'
                )
        else:
            return "".join(items)

    def process_html(self, context: FilePageContext, display_name: str) -> str:
        stamp = f"{context.item.get('date') or '1970-01-01'} 00:00:00 +0000"
        cwd = context.service.cwd_for_section(context.section_slug)
        file_path = self.display_file_path(context.section_slug, display_name)

        return "".join(
            [
                context.service.shell_command_markup(f"stat {display_name}", cwd=cwd),
                context.service.stat_row("File", file_path),
                context.service.stat_row("Size", str(context.localized_meta.get("byteSize") or 0)),
                context.service.stat_row("Blocks", "8"),
                context.service.stat_row("IO", "4096 regular file"),
                context.service.stat_row("Inode", "021"),
                context.service.stat_row("Access", "(0664/-rw-rw-r--)"),
                context.service.stat_row("Uid", "(1000/guest)"),
                context.service.stat_row("Gid", "(1000/guest)"),
                context.service.stat_row("Birth", stamp),
                context.service.stat_row("Mtime", stamp),
                '<span class="meta-rule" aria-hidden="true"></span>',
                context.service.stat_row("name", display_name),
                context.service.stat_row("lang", context.lang),
                context.service.stat_row("langs", ", ".join(context.item.get("languages", []))),
                context.service.stat_row("type", str(context.item.get("type") or FileType.PAGE)),
            ]
        )

    @staticmethod
    def display_file_path(section: str, slug: str) -> str:
        return f"~/{slug}" if section == SYSTEM_SECTION else f"~/{section}/{slug}"

    def validate_item(self, _: content.Section, item: content.Item) -> None:
        return None
