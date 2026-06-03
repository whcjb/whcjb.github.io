#!/usr/bin/env python3
"""One-off: restructure calvin/john-scan/1.md to match harmony-1/1.md style.

Reads:
  - assets/cuv.json (clean CUV Chinese Bible text)
  - calvin_raw/john-scan/ocr/page_NNNN.md (per-page OCR commentary)

Writes:
  - calvin/john-scan/1.md  (single chapter file matching harmony-1 layout)

The chapter is split into 6 scripture-box sections, with page ranges
determined empirically by inspecting the OCR'd Calvin commentary:

  Section    Verses    Commentary pages
  ─────────  ────────  ─────────────────
  1:1-5      Word/Life  16–24
  1:6-13     John witness/Light/sons-of-God  24–31
  1:14-18    Word incarnate/grace upon grace  31–40
  1:19-28    John's testimony to priests     40–48
  1:29-34    Lamb of God / Spirit descent     48–56
  1:35-51    First disciples / Nathanael      56–65

After verification of look-and-feel, this script can be generalized
into a reusable structured publisher.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REPO = Path("/Users/yanpeifa/Documents/whcjb.github.io")
CUV = json.load(open(REPO / "assets/cuv.json"))
JOHN_1 = CUV["43"]["1"]  # book 43 chapter 1

SECTIONS = [
    {
        "verses": (1, 5),
        "title": "太初有道、生命与光",
        "pages": (16, 24),
    },
    {
        "verses": (6, 13),
        "title": "施洗约翰为光作见证；信子者得作神的儿女",
        "pages": (24, 31),
    },
    {
        "verses": (14, 18),
        "title": "道成了肉身；从他丰满的恩典里我们都领受了",
        "pages": (31, 40),
    },
    {
        "verses": (19, 28),
        "title": "约翰回答祭司：我不是基督",
        "pages": (40, 48),
    },
    {
        "verses": (29, 34),
        "title": "看哪，神的羔羊！圣灵仿佛鸽子降下",
        "pages": (48, 56),
    },
    {
        "verses": (35, 51),
        "title": "首批门徒；耶稣呼召拿但业",
        "pages": (56, 65),
    },
]


def scripture_box(verses_range: tuple[int, int]) -> str:
    """Render <div class="scripture-box"> for John 1 verses [a, b]."""
    a, b = verses_range
    inner = []
    for v in range(a, b + 1):
        text = JOHN_1[str(v)]
        inner.append(f"<strong>{v}.</strong>{text}")
    body = "".join(inner)
    ref = f"约翰福音 1:{a}-{b}"
    return (
        '<div class="scripture-box">\n'
        f'<p class="scripture-ref">{ref}</p>\n'
        f"<p>{body}</p>\n"
        "</div>"
    )


# Patterns to strip from OCR pages when used as commentary body.
RUNNING_HDR_PATTERNS = [
    re.compile(r"^#\s*加尔文文集.*约翰福音注释\s*$"),
    re.compile(r"^#\s*约翰福音注释\s*$"),
    re.compile(r"^#\s*第[一二三四五六七八九十百零〇0-9]+\s*章\s*\*?\s*$"),
    re.compile(r"^\d{1,3}\s*$"),  # bare page number
]


def fix_inline_h2(line: str) -> str:
    """OCR produced `## verseN.` heading + entire paragraph as one ## line.
    Convert to `**verseN-opener.**` bold + prose form (matches harmony-1).
    Only applies when `## XX` content is too long to be a real heading
    (>40 chars) — short ## lines (real sub-headings) pass through.
    """
    if not line.startswith("## "):
        return line
    content = line[3:].strip()
    if len(content) <= 40:
        return line  # genuine sub-heading, keep
    # Split at first 。 — bold the opener, keep the rest as prose.
    period = content.find("。")
    if period == -1 or period > 60:
        # No period in first 60 chars: bold first 30 chars as opener
        return f"**{content[:30]}**{content[30:]}"
    opener = content[:period + 1]
    rest = content[period + 1:]
    return f"**{opener}**{rest}"


def normalize_page(text: str) -> str:
    out = []
    for line in text.splitlines():
        if any(p.match(line.rstrip()) for p in RUNNING_HDR_PATTERNS):
            continue
        out.append(fix_inline_h2(line.rstrip()))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def load_pages(start: int, end: int) -> str:
    """Concatenate OCR'd pages [start, end] (1-based, inclusive)."""
    parts = []
    for p in range(start, end + 1):
        f = REPO / f"calvin_raw/john-scan/ocr/page_{p:04d}.md"
        if not f.exists():
            continue
        parts.append(normalize_page(f.read_text(encoding="utf-8")))
    return "\n\n".join(p for p in parts if p)


def build_chapter_md() -> str:
    fm = (
        "---\n"
        "layout: calvin-en\n"
        'book_id: john-scan\n'
        'book_name: "约翰福音（扫描版）"\n'
        "chapter: 1\n"
        "header-img: psalm-bg-mountain.jpg\n"
        "date: 2026-06-03 15:10\n"
        'prev_section: preface\n'
        'prev_label: "序言"\n'
        'next_section: 2\n'
        'next_label: "第二章"\n'
        "---\n\n"
    )
    body = ["# 约翰福音 1 —— 道成肉身\n"]
    for sec in SECTIONS:
        v_lo, v_hi = sec["verses"]
        body.append(f'## 约翰福音 1:{v_lo}-{v_hi} —— {sec["title"]}\n')
        body.append(scripture_box(sec["verses"]))
        body.append("")
        comm = load_pages(*sec["pages"])
        body.append(comm)
        body.append("")
    return fm + "\n".join(body) + "\n"


def main() -> int:
    out = REPO / "calvin/john-scan/1.md"
    content = build_chapter_md()
    out.write_text(content, encoding="utf-8")
    print(f"wrote {out} ({len(content):,} chars)")
    # quick stats
    n_sections = content.count("## 约翰福音 1:")
    n_boxes = content.count('<div class="scripture-box">')
    print(f"  sections: {n_sections}  scripture-boxes: {n_boxes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
