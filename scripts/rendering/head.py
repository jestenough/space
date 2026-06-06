"""Document head rendering for prerendered routes"""

from __future__ import annotations

import html
import re

from .. import routes


class Head:
    runtime_tag_re = re.compile(
        r"^\s*(?:"
        r'<meta\b(?=[^>]*\bname=["\']color-scheme["\'])[^>]*>|'
        r"<script\b(?![^>]*\bsrc=)[^>]*>[\s\S]*?</script>|"
        r"<script\b(?=[^>]*\bsrc=)[^>]*></script>|"
        r'<link\b(?=[^>]*\brel=["\'](?:stylesheet|modulepreload|preload)["\'])[^>]*>'
        r")\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    def render(
        self,
        lang: str,
        title: str,
        description: str,
        canonical_path: str,
        alternates: dict[str, str],
        og_type: str,
        extra_head: str = "",
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
            '    <link rel="apple-touch-icon" sizes="152x152" href="/icons/apple-touch-icon.png" />',
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
                f'    <link rel="alternate" hreflang="{html.escape(hreflang, quote=True)}" href="{html.escape(routes.absolute_url(path), quote=True)}" />'
            )

        if extra_head:
            lines.append(extra_head)

        return "\n".join(lines)

    def inject(self, base_html: str, head: str) -> str:
        runtime_tags = self.runtime_tags(base_html)
        full_head = f"{head}\n{runtime_tags}" if runtime_tags else head

        return re.sub(
            r"<head>[\s\S]*?</head>", f"<head>\n{full_head}\n  </head>", base_html, count=1, flags=re.IGNORECASE
        )

    def runtime_tags(self, base_html: str) -> str:
        match = re.search(r"<head>([\s\S]*?)</head>", base_html, re.IGNORECASE)
        if not match:
            return ""
        else:
            return "\n".join(item.group(0).strip() for item in self.runtime_tag_re.finditer(match.group(1)))
