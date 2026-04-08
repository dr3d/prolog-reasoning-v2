#!/usr/bin/env python3
"""
Render research ledger markdown files into themed standalone HTML pages.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "scripts/templates/research-ledger-page.template.html"

DEFAULT_TARGETS = [
    (
        ROOT / "docs/research/fact-ingestion-dialog-battery.md",
        ROOT / "docs/research/fact-ingestion-dialog-battery.html",
        "Fact Ingestion Dialog Battery",
    ),
    (
        ROOT / "docs/research/fact-extraction-steering-matrix.md",
        ROOT / "docs/research/fact-extraction-steering-matrix.html",
        "Fact Extraction Steering Matrix",
    ),
]


INLINE_CODE_RE = re.compile(r"`([^`]+)`")
INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
ORDERED_LIST_RE = re.compile(r"^\d+\.\s+")


def _render_inline(text: str) -> str:
    placeholders: list[str] = []

    def reserve(fragment: str) -> str:
        marker = f"@@MARKER_{len(placeholders)}@@"
        placeholders.append(fragment)
        return marker

    with_code = INLINE_CODE_RE.sub(
        lambda match: reserve(f"<code>{html.escape(match.group(1))}</code>"),
        text,
    )

    def replace_link(match: re.Match[str]) -> str:
        label = html.escape(match.group(1))
        destination = match.group(2).strip()
        if " " in destination:
            destination = destination.split(" ", 1)[0]
        href = html.escape(destination, quote=True)
        return reserve(f'<a href="{href}">{label}</a>')

    with_markup = INLINE_LINK_RE.sub(replace_link, with_code)
    escaped = html.escape(with_markup)

    for index, fragment in enumerate(placeholders):
        marker = f"@@MARKER_{index}@@"
        escaped = escaped.replace(marker, fragment)

    return escaped


def _flush_paragraph(buffer: list[str], out: list[str]) -> None:
    if not buffer:
        return
    text = " ".join(line.strip() for line in buffer if line.strip())
    if text:
        out.append(f"<p>{_render_inline(text)}</p>")
    buffer.clear()


def _render_table(lines: list[str], out: list[str]) -> None:
    if len(lines) < 2:
        return
    rows: list[list[str]] = []
    for raw in lines:
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(cells)
    if len(rows) < 2:
        return

    header = rows[0]
    body = rows[2:] if len(rows) > 2 else []

    out.append("<div class=\"table-wrap\">")
    out.append("<table>")
    out.append("<thead><tr>")
    for cell in header:
        out.append(f"<th>{html.escape(cell)}</th>")
    out.append("</tr></thead>")
    out.append("<tbody>")
    for row in body:
        out.append("<tr>")
        for cell in row:
            out.append(f"<td>{html.escape(cell)}</td>")
        out.append("</tr>")
    out.append("</tbody>")
    out.append("</table>")
    out.append("</div>")


def markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    out: list[str] = []
    paragraph_buf: list[str] = []
    list_open: str | None = None
    code_open = False
    table_buf: list[str] = []

    def close_list() -> None:
        nonlocal list_open
        if list_open == "ul":
            out.append("</ul>")
        elif list_open == "ol":
            out.append("</ol>")
        list_open = None

    def open_list(kind: str) -> None:
        nonlocal list_open
        if list_open == kind:
            return
        close_list()
        out.append(f"<{kind}>")
        list_open = kind

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()

        if stripped.startswith("```"):
            _flush_paragraph(paragraph_buf, out)
            close_list()
            if table_buf:
                _render_table(table_buf, out)
                table_buf.clear()
            if code_open:
                out.append("</code></pre>")
                code_open = False
            else:
                language = stripped[3:].strip()
                if language:
                    out.append(f"<pre><code class=\"language-{html.escape(language)}\">")
                else:
                    out.append("<pre><code>")
                code_open = True
            continue

        if code_open:
            out.append(html.escape(line))
            continue

        if stripped.startswith("|"):
            _flush_paragraph(paragraph_buf, out)
            close_list()
            table_buf.append(line)
            continue
        elif table_buf:
            _render_table(table_buf, out)
            table_buf.clear()

        if not stripped:
            _flush_paragraph(paragraph_buf, out)
            close_list()
            continue

        if stripped.startswith("#"):
            _flush_paragraph(paragraph_buf, out)
            close_list()
            level = 0
            while level < len(stripped) and stripped[level] == "#":
                level += 1
            level = max(1, min(6, level))
            content = stripped[level:].strip()
            out.append(f"<h{level}>{_render_inline(content)}</h{level}>")
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            _flush_paragraph(paragraph_buf, out)
            open_list("ul")
            out.append(f"<li>{_render_inline(stripped[2:].strip())}</li>")
            continue

        if ORDERED_LIST_RE.match(stripped):
            _flush_paragraph(paragraph_buf, out)
            open_list("ol")
            content = ORDERED_LIST_RE.sub("", stripped, count=1).strip()
            out.append(f"<li>{_render_inline(content)}</li>")
            continue

        close_list()
        paragraph_buf.append(line)

    if table_buf:
        _render_table(table_buf, out)
    _flush_paragraph(paragraph_buf, out)
    close_list()
    if code_open:
        out.append("</code></pre>")

    return "\n".join(out)


def _strip_duplicate_h1(markdown_text: str, title: str) -> str:
    lines = markdown_text.splitlines()
    index = 0

    while index < len(lines) and not lines[index].strip():
        index += 1

    if index >= len(lines):
        return markdown_text

    first = lines[index].strip()
    if not first.startswith("# "):
        return markdown_text

    heading = first[2:].strip().casefold()
    if heading != title.strip().casefold():
        return markdown_text

    trimmed = lines[:index] + lines[index + 1 :]
    while index < len(trimmed) and not trimmed[index].strip():
        del trimmed[index]
    return "\n".join(trimmed)


def _load_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def render_page(
    *,
    template: str,
    title: str,
    body_html: str,
    source_name: str,
    theme_key: str,
) -> str:
    generated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    replacements = {
        "{{PAGE_TITLE}}": html.escape(title),
        "{{PAGE_DESCRIPTION}}": html.escape(f"Rendered ledger from {source_name}."),
        "{{NAV_RESEARCH_INDEX}}": "README.md",
        "{{NAV_DOCS_HUB}}": "../docs-hub.html",
        "{{NAV_REPO}}": "https://github.com/dr3d/prolog-reasoning",
        "{{GENERATED_META}}": html.escape(f"Source: {source_name} | Rendered: {generated}"),
        "{{CONTENT_HTML}}": body_html,
        "{{THEME_STORAGE_KEY}}": html.escape(theme_key),
    }

    page = template
    for token, value in replacements.items():
        page = page.replace(token, value)
    return page


def render_one(source: Path, target: Path, title: str, template: str) -> None:
    text = source.read_text(encoding="utf-8-sig")
    normalized = _strip_duplicate_h1(text, title=title)
    body = markdown_to_html(normalized)
    theme_key = f"research_ledger_theme_{target.stem}"
    page = render_page(
        template=template,
        title=title,
        body_html=body,
        source_name=source.name,
        theme_key=theme_key,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render research markdown ledgers to standalone HTML.")
    parser.add_argument(
        "--only",
        nargs="*",
        default=[],
        help="Optional source markdown file names to render (for example fact-ingestion-dialog-battery.md).",
    )
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE),
        help="Path to HTML template file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    only = {name.strip() for name in args.only if name.strip()}
    template_path = Path(args.template).resolve()
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    template = _load_template(template_path)

    for source, target, title in DEFAULT_TARGETS:
        if only and source.name not in only:
            continue
        if not source.exists():
            print(f"SKIP missing source: {source}")
            continue
        render_one(source=source, target=target, title=title, template=template)
        print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
