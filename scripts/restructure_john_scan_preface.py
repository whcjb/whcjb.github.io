#!/usr/bin/env python3
"""Restructure calvin/john-scan/preface.md to match harmony-1 layout.

Reads:  calvin_raw/john-scan/ocr/page_NNNN.md (pages 1-12)
Writes: calvin/john-scan/preface.md

Cleans:
- Strip running header `# 加尔文文集·约翰福音注释` (and standalone
  `加尔文文集·约翰福音注释`).
- Strip page-number-only lines.
- Strip `---` horizontal rules between body and footnotes.
- Join cross-page mid-sentence continuations.
- Promote 总序 / 图书在版编目 / etc. as proper `## ` sub-headings.

Front matter uses `layout: calvin-en` (matches ch1 style), with
`next_section: 1` for "前往第一章" navigation.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


REPO = Path("/Users/yanpeifa/Documents/whcjb.github.io")
PREFACE_PAGES = (1, 12)  # inclusive

RUNNING_HDR_PATTERNS = [
    re.compile(r"^#\s*加尔文文集\s*[·•‧]\s*约翰福音注释\s*$"),
    re.compile(r"^#\s*约翰福音注释\s*$"),
    re.compile(r"^加尔文文集\s*[·•‧]\s*约翰福音注释\s*$"),
    re.compile(r"^约翰福音注释\s*$"),
    re.compile(r"^\d{1,3}\s*$"),
    re.compile(r"^-{3,}\s*$"),
    re.compile(r"^—{3,}\s*$"),
]

_TERM_PUNCT = "。？！」』\""


def normalize_page(text: str) -> str:
    out: list[str] = []
    for line in text.splitlines():
        if any(p.match(line.rstrip()) for p in RUNNING_HDR_PATTERNS):
            continue
        out.append(line.rstrip())
    text2 = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    return text2


def _join_pages(parts: list[str]) -> str:
    """Join cross-page mid-sentence continuations within preface."""
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        if out:
            prev = out[-1]
            prev_paras = re.split(r"\n{2,}", prev)
            cur_paras = re.split(r"\n{2,}", p)
            last = prev_paras[-1].rstrip() if prev_paras else ""
            first = cur_paras[0].lstrip() if cur_paras else ""
            if (last and first
                    and last[-1] not in _TERM_PUNCT
                    and not first.startswith(("# ", "## ", "[^", "<", "**"))
                    and "一" <= first[0] <= "鿿"):
                prev_paras[-1] = last + first
                out[-1] = "\n\n".join(prev_paras)
                cur_paras = cur_paras[1:]
                p = "\n\n".join(cur_paras)
        if p:
            out.append(p)
    return "\n\n".join(out)


def build_preface_md() -> str:
    fm = (
        "---\n"
        "layout: calvin-en\n"
        'book_id: john-scan\n'
        'book_name: "约翰福音（扫描版）"\n'
        "chapter: 0\n"
        "header-img: psalm-bg-mountain.jpg\n"
        'title: "序言"\n'
        "date: 2026-06-03 17:30\n"
        'next_section: 1\n'
        'next_label: "第一章"\n'
        "---\n\n"
    )
    parts: list[str] = []
    for p in range(PREFACE_PAGES[0], PREFACE_PAGES[1] + 1):
        f = REPO / f"calvin_raw/john-scan/ocr/page_{p:04d}.md"
        if not f.exists():
            continue
        page = normalize_page(f.read_text(encoding="utf-8"))
        if page:
            parts.append(page)
    body = _join_pages(parts)
    title = "# 加尔文文集·约翰福音注释\n"
    return fm + title + "\n" + body + "\n"


def main() -> int:
    out_path = REPO / "calvin/john-scan/preface.md"
    content = build_preface_md()
    out_path.write_text(content, encoding="utf-8")
    print(f"wrote {out_path} ({len(content):,} chars)")
    print(f"  h2 sections: {content.count(chr(10) + '## ')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
