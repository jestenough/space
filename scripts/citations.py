"""Citation pre/post processing for TeX articles.

Parses \\citetext{key}{text} from TeX sources, reads references.<lang>.bib,
assigns sequential numbers, and injects interactive citation markup
into the pandoc-generated HTML.

Markers used between pre-processing and post-processing:
  __CSN__  — cited-text start (N = citation number)
  __CEN__  — cited-text end
  __CRN__  — citation reference marker → replaced with [N] link
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import NamedTuple

REFERENCE_UI = {
    "en": {
        "heading": "References",
        "copied": "reference copied",
        "copy_failed": "copy failed",
        "pages": "pp.",
        "edition": "ed.",
        "in": "In",
    },
    "ru": {
        "heading": "Источники",
        "copied": "источник скопирован",
        "copy_failed": "не удалось скопировать",
        "pages": "с.",
        "edition": "изд.",
        "in": "В",
    },
}


class Citation(NamedTuple):
    num: int
    key: str
    text: str
    loc: str = ""  # optional page/location, e.g. "p. 42"


class Reference(NamedTuple):
    key: str
    html: str
    url: str = ""
    plain: str = ""  # plain-text one-liner for tooltip


CS_PREFIX = "__CS"
CE_PREFIX = "__CE"
CR_PREFIX = "__CR"
SUFFIX = "__"
_START_RE = re.compile(rf"{re.escape(CS_PREFIX)}(\d+){re.escape(SUFFIX)}")
_END_RE = re.compile(rf"{re.escape(CE_PREFIX)}(\d+){re.escape(SUFFIX)}")
_REF_RE = re.compile(rf"{re.escape(CR_PREFIX)}(\d+)(?::([^{re.escape(SUFFIX)}]*))?{re.escape(SUFFIX)}")


def marker_start(num: int) -> str:
    return f"{CS_PREFIX}{num}{SUFFIX}"


def marker_end(num: int) -> str:
    return f"{CE_PREFIX}{num}{SUFFIX}"


def marker_ref(num: int, loc: str = "") -> str:
    if loc:
        return f"{CR_PREFIX}{num}:{loc}{SUFFIX}"
    return f"{CR_PREFIX}{num}{SUFFIX}"


def has_citetext(source: str) -> bool:
    """Check if the TeX source contains any \\citetext commands."""
    return "\\citetext{" in source


def preprocess_tex(source: str) -> tuple[str, list[Citation]]:
    """Replace \\citetext{key}{text} with marker-wrapped text + ref marker.

    Returns (cleaned_tex, citations) where citations are numbered 1..N
    in order of appearance.
    """
    citations: list[Citation] = []
    seen: dict[str, int] = {}
    result: list[str] = []
    pos = 0

    while True:
        m = _find_citetext(source, pos)
        if m is None:
            result.append(source[pos:])
            break

        cmd_start, key, loc, text, cmd_end = m
        result.append(source[pos:cmd_start])

        num = seen.get(key)
        if num is None:
            num = len(seen) + 1
            seen[key] = num

        result.append(marker_start(num))
        result.append(text)
        result.append(marker_end(num))
        result.append(marker_ref(num, loc))

        citations.append(Citation(num=num, key=key, text=text, loc=loc))
        pos = cmd_end

    return "".join(result), citations


def _find_citetext(source: str, start: int) -> tuple[int, str, str, str, int] | None:
    """Find next \\citetext{key}[loc]{text} in source starting at `start`.

    Returns (command_start, key, loc, text, end_pos) or None.
    loc is optional and may be empty.
    """
    needle = "\\citetext{"
    idx = source.find(needle, start)
    if idx == -1:
        return None

    cmd_start = idx
    pos = idx + len(needle)

    end = _matching_brace(source, pos)
    if end == -1:
        return None
    key = source[pos:end].strip()
    pos = end + 1

    # Optional [loc]
    loc = ""
    if pos < len(source) and source[pos] == "[":
        bracket_end = source.find("]", pos + 1)
        if bracket_end != -1:
            loc = source[pos + 1 : bracket_end].strip()
            pos = bracket_end + 1

    if pos >= len(source) or source[pos] != "{":
        return None
    pos += 1

    end = _matching_brace(source, pos)
    if end == -1:
        return None
    text = source[pos:end]
    cmd_end = end + 1

    return (cmd_start, key, loc, text, cmd_end)


def _matching_brace(source: str, start: int) -> int:
    """Return index of matching '}' for '{' at `start-1`. Returns -1 on failure."""
    depth = 1
    i = start
    while i < len(source):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def read_bib(path: Path) -> dict[str, dict[str, str]]:
    """Parse a BibTeX file into {key: {field: value}}.

    Handles @article, @book, @misc, @inproceedings, @techreport.
    """
    if not path.is_file():
        return {}

    text = path.read_text(encoding="utf-8")
    entries: dict[str, dict[str, str]] = {}

    pos = 0
    while True:
        m = re.search(r"@(\w+)\s*\{\s*([^,]+)\s*,", text[pos:], re.IGNORECASE)
        if m is None:
            break

        entry_type = m.group(1).lower()
        key = m.group(2).strip()

        # Position of the opening { for this entry
        open_brace = text.index("{", pos + m.start())
        body_start = pos + m.end()  # after "key," — the field definitions
        body_end = _matching_brace(text, open_brace + 1)
        if body_end == -1:
            pos += m.end()
            continue

        body = text[body_start:body_end]
        fields = _bib_fields(body)
        fields["_type"] = entry_type
        entries[key] = fields
        pos = body_end + 1

    return entries


def _bib_fields(body: str) -> dict[str, str]:
    """Parse field = {value} or field = \"value\" pairs from BibTeX entry body.

    Handles nested braces in values.
    """
    fields: dict[str, str] = {}
    pos = 0

    while pos < len(body):
        m = re.compile(r"(\w+)\s*=\s*", re.IGNORECASE).search(body, pos)
        if m is None:
            break

        name = m.group(1).lower().strip()
        val_start = m.end()
        if val_start >= len(body):
            break

        if body[val_start] == "{":
            val_end = _matching_brace(body, val_start + 1)
            if val_end == -1:
                break
            value = body[val_start + 1 : val_end]
            pos = val_end + 1
        elif body[val_start] == '"':
            val_end = body.find('"', val_start + 1)
            if val_end == -1:
                break
            value = body[val_start + 1 : val_end]
            pos = val_end + 1
        else:
            pos = val_start
            continue

        value = re.sub(r"\s+", " ", value.strip())
        fields[name] = value

        # Skip trailing comma
        while pos < len(body) and body[pos] in " \t\n\r,":
            pos += 1

    return fields


def format_references(
    bib: dict[str, dict[str, str]],
    citations: list[Citation],
    lang: str,
) -> list[Reference]:
    """Build formatted reference entries for each unique cited key.

    Returns references ordered by citation number, with url and plain-tooltip fields.
    """
    key_to_num = {c.key: c.num for c in citations}
    ordered = sorted(key_to_num.items(), key=lambda x: x[1])

    ui = REFERENCE_UI.get(lang)
    if ui is None:
        raise RuntimeError(f"Missing reference translations for language `{lang}` in scripts/citations.py")

    refs: list[Reference] = []
    for key, num in ordered:
        fields = bib.get(key)
        if fields is None:
            refs.append(Reference(key=key, html=f"[{num}] Unknown reference: {html.escape(key)}"))
            continue

        url = _extract_url(fields)
        plain = _fmt_plain(num, fields)
        refs.append(Reference(key=key, html=_format_entry(num, fields, ui), url=url, plain=plain))

    return refs


def _extract_url(fields: dict[str, str]) -> str:
    """Extract a URL from bib fields if one exists."""
    for field_name in ("url", "doi", "howpublished"):
        value = fields.get(field_name, "")
        url_match = re.search(r"https?://[^\s}]+", value)
        if url_match:
            return url_match.group(0)
    return ""


def _fmt_plain(num: int, fields: dict[str, str]) -> str:
    """One-line plain-text reference for tooltip display."""
    authors = _clean_tex(fields.get("author", ""))
    title = _clean_tex(fields.get("title", ""))
    year = fields.get("year", "n.d.")
    if authors:
        first_author = authors.split(" and ")[0].split(",")[0].strip()
        return f"{first_author}. {title}. {year}."
    return f"{title}. {year}."


def _format_entry(num: int, fields: dict[str, str], ui: dict[str, str]) -> str:
    """Format a single bibliography entry as HTML."""
    entry_type = fields.get("_type", "misc")

    if entry_type == "article":
        formatted = _fmt_article(num, fields, ui)
    elif entry_type == "book":
        formatted = _fmt_book(num, fields, ui)
    elif entry_type in ("inproceedings", "incollection"):
        formatted = _fmt_inproceedings(num, fields, ui)
    else:
        formatted = _fmt_misc(num, fields)

    return f'<span class="ref-marker">[{num}]</span> {formatted}'


def _fmt_author_year(fields: dict[str, str]) -> tuple[str, str]:
    """Return (authors_html, year) from bib fields."""
    authors = _fmt_authors(fields.get("author", ""))
    year = fields.get("year", "n.d.")
    return authors, year


def _fmt_authors(raw: str) -> str:
    """Format BibTeX author string into readable HTML.

    Handles "Last, First" and "First Last" formats.
    """
    if not raw:
        return ""

    raw = re.sub(r"\{|\}", "", raw)
    raw = raw.replace("\\&", "&")

    names = [n.strip() for n in raw.split(" and ")]
    formatted: list[str] = []
    for name in names:
        if "," in name:
            parts = [p.strip() for p in name.split(",", 1)]
            formatted.append(f"{parts[1]} {parts[0]}" if len(parts) == 2 else name)
        else:
            formatted.append(name)

    if len(formatted) == 1:
        return html.escape(formatted[0])
    if len(formatted) == 2:
        return f"{html.escape(formatted[0])} &amp; {html.escape(formatted[1])}"
    return ", ".join(html.escape(n) for n in formatted[:-1]) + f", &amp; {html.escape(formatted[-1])}"


def _fmt_title(raw: str) -> str:
    """Format a title, preserving TeX markup as italics where appropriate."""
    if not raw:
        return ""
    clean = _clean_tex(raw)
    return f"<i>{html.escape(clean)}</i>"


def _fmt_clean(raw: str) -> str:
    """Clean TeX markup from text (no HTML escaping)."""
    if not raw:
        return ""
    return _clean_tex(raw)


# TeX symbolic commands to preserve as text
_TEX_SYMBOLS: dict[str, str] = {
    "\\TeX": "TeX",
    "\\LaTeX": "LaTeX",
    "\\LaTeXe": "LaTeX2e",
    "\\BibTeX": "BibTeX",
    "\\AmS": "AMS",
    "\\AmSLaTeX": "AMS-LaTeX",
}


def _clean_tex(raw: str) -> str:
    """Strip basic TeX markup from text, preserving symbolic commands as plain text."""
    # Preserve TeX symbols
    for cmd, replacement in _TEX_SYMBOLS.items():
        raw = raw.replace(f"{cmd}{{}}", replacement)
        raw = re.sub(rf"{re.escape(cmd)}\b", replacement, raw)

    raw = raw.replace("\\&", "&")
    raw = raw.replace("\\ ", " ")
    raw = re.sub(r"\\url\{([^}]*)\}", r"\1", raw)
    raw = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", raw)
    raw = re.sub(r"\\textit\{([^}]*)\}", r"\1", raw)
    raw = re.sub(r"\\textbf\{([^}]*)\}", r"\1", raw)
    raw = re.sub(r"\\emph\{([^}]*)\}", r"\1", raw)
    raw = re.sub(r"\\[a-zA-Z]+\*?(?:\{[^}]*\})*", "", raw)
    raw = re.sub(r"[{}]", "", raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def _fmt_article(num: int, fields: dict[str, str], ui: dict[str, str]) -> str:
    authors, year = _fmt_author_year(fields)
    title = _clean_tex(fields.get("title", ""))
    journal = _clean_tex(fields.get("journal", ""))
    volume = fields.get("volume", "")
    number = fields.get("number", "")
    pages = fields.get("pages", "")

    parts = [authors, f"<i>{html.escape(title)}</i>"]
    if journal:
        vol_issue = f"<i>{html.escape(journal)}</i>"
        if volume:
            vol_issue += f" {html.escape(volume)}"
            if number:
                vol_issue += f" ({html.escape(number)})"
        parts.append(vol_issue)
    if pages:
        parts.append(f"{html.escape(ui['pages'])} {html.escape(pages)}")
    parts.append(html.escape(year))
    return _join_parts(parts)


def _fmt_book(num: int, fields: dict[str, str], ui: dict[str, str]) -> str:
    authors, year = _fmt_author_year(fields)
    title = _fmt_title(fields.get("title", ""))
    publisher = _fmt_clean(fields.get("publisher", ""))
    edition = fields.get("edition", "")

    parts = [authors, title]
    if edition:
        parts.append(f"{html.escape(edition)} {html.escape(ui['edition'])}")
    if publisher:
        parts.append(html.escape(publisher))
    parts.append(html.escape(year))
    return _join_parts(parts)


def _fmt_inproceedings(num: int, fields: dict[str, str], ui: dict[str, str]) -> str:
    authors, year = _fmt_author_year(fields)
    title = _clean_tex(fields.get("title", ""))
    booktitle = _clean_tex(fields.get("booktitle", ""))
    pages = fields.get("pages", "")

    parts = [authors, f"<i>{html.escape(title)}</i>"]
    if booktitle:
        parts.append(f"{html.escape(ui['in'])} <i>{html.escape(booktitle)}</i>")
    if pages:
        parts.append(f"{html.escape(ui['pages'])} {html.escape(pages)}")
    parts.append(html.escape(year))
    return _join_parts(parts)


def _fmt_misc(num: int, fields: dict[str, str]) -> str:
    authors, year = _fmt_author_year(fields)
    title = _fmt_title(fields.get("title", ""))
    howpublished = _fmt_clean(fields.get("howpublished", ""))
    note = _fmt_clean(fields.get("note", ""))

    parts = [authors, title]
    if howpublished:
        parts.append(html.escape(howpublished))
    parts.append(html.escape(year))
    if note:
        parts.append(html.escape(note))
    return _join_parts(parts)


def _join_parts(parts: list[str]) -> str:
    """Join parts with period-space, ensuring exactly one trailing period."""
    clean = [p.rstrip(".") for p in parts if p]
    return ". ".join(clean) + "."


def synthesize_references(references: list[Reference], lang: str) -> str:
    """Produce the references <ol> HTML block."""
    if not references:
        return ""

    ui = REFERENCE_UI.get(lang)
    if ui is None:
        raise RuntimeError(f"Missing reference translations for language `{lang}` in scripts/citations.py")

    items: list[str] = []
    for i, ref in enumerate(references, 1):
        url_attr = f' data-url="{html.escape(ref.url, quote=True)}"' if ref.url else ""
        title_attr = f' title="{html.escape(ref.plain, quote=True)}"' if ref.plain else ""
        if ref.url:
            target = ' target="_blank" rel="noopener noreferrer"' if ref.url.startswith(("http://", "https://")) else ""
            action = (
                f'<a class="ref-action" href="{html.escape(ref.url, quote=True)}"{target}>'
                f"{ref.html}</a>"
            )
        else:
            action = f'<button class="ref-action" type="button" data-reference-copy>{ref.html}</button>'
        items.append(
            f'<li id="ref-{i}" class="ref-item" data-ref="{i}"{url_attr}{title_attr}>{action}</li>'
        )

    return (
        '<section class="article-references" '
        f'data-copy-success="{html.escape(ui["copied"], quote=True)}" '
        f'data-copy-failure="{html.escape(ui["copy_failed"], quote=True)}">'
        f'<h2 class="ref-heading">{html.escape(ui["heading"])}</h2>'
        f'<ol class="ref-list">{"".join(items)}</ol></section>'
    )


def postprocess_html(
    html_text: str,
    citations: list[Citation],
    references: list[Reference],
    lang: str,
) -> str:
    """Replace marker tokens in pandoc HTML output with interactive citation markup.

    __CSN__text__CEN____CRN__ becomes:
      <span class="cited" data-ref="N">text</span>
      <a class="citation" data-ref="N" href="#ref-N" title="Ref info">[N]</a>

    __CRN:loc__ additionally appends the location to the marker display.

    Also appends the reference list.
    """
    # Build lookup: num → ref tooltip text
    ref_plain: dict[int, str] = {}
    for ref in references:
        for c in citations:
            if c.key == ref.key and c.num not in ref_plain:
                ref_plain[c.num] = ref.plain
                break

    # Replace start markers
    html_text = _START_RE.sub(
        lambda m: f'<span class="cited" data-ref="{m.group(1)}">', html_text
    )
    # Replace end markers
    html_text = _END_RE.sub("</span>", html_text)
    # Replace ref markers with citation links
    html_text = _REF_RE.sub(
        lambda m: _citation_link(m.group(1), m.group(2), ref_plain),
        html_text,
    )

    refs_html = synthesize_references(references, lang)
    if not refs_html:
        return html_text

    # Insert reference list before closing tags
    closing = re.search(r"(</article>|</div>\s*$)", html_text, re.IGNORECASE)
    if closing:
        pos = closing.start()
        return html_text[:pos] + refs_html + html_text[pos:]

    return html_text + refs_html


def _citation_link(num: str, loc: str | None, ref_plain: dict[int, str]) -> str:
    """Build <a class="citation"> element with optional location and tooltip."""
    n = int(num)
    label = f"[{n}"
    if loc:
        label += f", {html.escape(loc)}"
    label += "]"

    title = ""
    if n in ref_plain:
        title = f' title="{html.escape(ref_plain[n], quote=True)}"'

    return (
        f'<a class="citation" data-ref="{num}" href="#ref-{num}"{title}>{label}</a>'
    )
