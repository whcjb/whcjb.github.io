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


# Map circled digit Unicode → arabic int (for v1-v20; v21+ use other code points
# and we'll match by content instead).
_CIRCLE_DIGIT = {chr(0x2460 + i): i + 1 for i in range(20)}  # ① to ⑳
_CIRCLE_DIGIT.update({chr(0x3251 + i): i + 21 for i in range(15)})  # ㉑ to ㉟
_CIRCLE_DIGIT.update({chr(0x32B1 + i): i + 36 for i in range(15)})  # ㊱ to ㊿


def _strip_leading_circle(s: str) -> str:
    """Drop any leading circled digit + whitespace."""
    s = s.lstrip()
    while s and s[0] in _CIRCLE_DIGIT:
        s = s[1:].lstrip()
    return s


def find_john_verse(opener_text: str, chapter_verses: dict[str, str]) -> int | None:
    """Fuzzy-match an OCR'd commentary opener against CUV John 1.

    Strategy: strip circled digits, take first ~8 chars of opener, find a
    verse whose text starts with these chars (or contains them in the
    first 12 chars). Returns verse number or None.
    """
    head = _strip_leading_circle(opener_text)
    head = re.sub(r"[，。、；：（）\s]", "", head)[:8]
    if not head:
        return None
    best = None
    for vstr, text in chapter_verses.items():
        ct = re.sub(r"[，。、；：（）　\s]", "", text)
        if ct.startswith(head):
            return int(vstr)
        # Allow opener to match early in the verse (verse marker prefix)
        if head[:6] in ct[:16]:
            if best is None:
                best = int(vstr)
    return best


def fix_inline_h2(line: str, john_1: dict[str, str]) -> str:
    """OCR produced `## verseN.` heading + entire paragraph as one ## line.
    Convert to `**约翰福音 1:N。** *opener。* prose...` form (matches
    harmony-1 verse-nav requirements: the JS regex
    `^书卷名 Ch:N[.。]$` triggers pill generation).

    Only applies when `## XX` content is too long to be a real heading
    (>40 chars).
    """
    if not line.startswith("## "):
        return line
    content = line[3:].strip()
    if len(content) <= 40:
        return line
    period = content.find("。")
    if period == -1 or period > 60:
        opener = content[:30]
        rest = content[30:]
    else:
        opener = content[:period + 1]
        rest = content[period + 1:]
    v = find_john_verse(opener, john_1)
    opener_clean = _strip_leading_circle(opener)
    if v is not None:
        return f"**约翰福音 1:{v}。** *{opener_clean}* {rest}"
    return f"**{opener_clean}** {rest}"


# A circled digit OR a Chinese opening phrase, followed by enough Chinese to
# look like a verse quote. Used to detect verse-opener paragraphs.
_CIRCLE_DIGITS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿"


def maybe_promote_verse_opener(para: str, john_1: dict[str, str]) -> str:
    """If a paragraph starts with a CUV-John-1 verse quote (with or without
    leading circled digit), reformat as `**约翰福音 1:N。** *quote* rest`
    so the calvin-en layout JS finds it for the Jump-to-verse pill nav.

    Skip:
      - footnote lines (start with `[^...]:`)
      - existing well-formed openers (already start with `**约翰福音`)
      - short paragraphs (likely captions / single line refs)
    """
    if not para or para.startswith("[^") or para.startswith("**约翰福音"):
        return para
    if len(para) < 30:
        return para
    head = para[:20]
    # Optional leading circled digit
    body = head
    if body and body[0] in _CIRCLE_DIGITS:
        body = body[1:].lstrip()
    # Try to match the first 4-12 chars against any verse's opening text.
    body_clean = re.sub(r"[，。、；：（）　\s\"“”]", "", body)[:10]
    if len(body_clean) < 4:
        return para
    best_v = None
    best_len = 0
    for vstr, text in john_1.items():
        text_clean = re.sub(r"[，。、；：（）　\s]", "", text)
        # Find common prefix length
        m = 0
        for i in range(min(len(body_clean), len(text_clean))):
            if body_clean[i] == text_clean[i]:
                m += 1
            else:
                break
        if m >= 4 and m > best_len:
            best_v = int(vstr)
            best_len = m
    if best_v is None:
        return para
    # Found a verse match. Split paragraph at first 。 (period) — opener is
    # the quoted verse text, rest is commentary.
    # Strip leading circle from para
    para_no_circ = para[1:].lstrip() if para[0] in _CIRCLE_DIGITS else para
    period = para_no_circ.find("。")
    if period == -1 or period > 40:
        # No period in first 40 chars — pick 12 chars as opener
        opener = para_no_circ[:12]
        rest = para_no_circ[12:]
    else:
        opener = para_no_circ[:period + 1]
        rest = para_no_circ[period + 1:]
    return f"**约翰福音 1:{best_v}。** *{opener}* {rest}".rstrip()


def normalize_page(text: str) -> str:
    out = []
    for line in text.splitlines():
        if any(p.match(line.rstrip()) for p in RUNNING_HDR_PATTERNS):
            continue
        out.append(fix_inline_h2(line.rstrip(), JOHN_1))
    text2 = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    # Second pass: paragraph-level promotion to verse-opener form.
    paras = re.split(r"\n{2,}", text2)
    promoted = [maybe_promote_verse_opener(p, JOHN_1) for p in paras]
    return "\n\n".join(promoted)


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
