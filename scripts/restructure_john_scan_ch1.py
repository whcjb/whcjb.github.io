#!/usr/bin/env python3
"""Restructure calvin/john-scan/1.md to match calvin/john-en/1.md layout.

Targets every check in pdf-pipeline:refs:audit-gates:
  - Gate 1: no ****, <<<END, split italics
  - Gate 5: footnote refs/defs paired in kramdown `[^N]` / `[^N]: text` form
  - Gate 6: no paragraph > 1500 chars
  - Plus scripture-anchor h2 before each scripture-box for verse-nav JS
  - Plus drops the manual `## 脚注` heading (kramdown auto-renders fn section)

Reads:
  - assets/cuv.json (clean CUV Chinese Bible text)
  - calvin_raw/john-scan/ocr/page_NNNN.md (per-page OCR)

Writes:
  - calvin/john-scan/1.md
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REPO = Path("/Users/yanpeifa/Documents/whcjb.github.io")
CUV = json.load(open(REPO / "assets/cuv.json"))
JOHN_1 = CUV["43"]["1"]


# 6 scripture-box sections — page ranges match Calvin's commentary structure.
SECTIONS = [
    {"verses": (1, 5),   "title": "太初有道、生命与光",                  "pages": (16, 24)},
    {"verses": (6, 13),  "title": "施洗约翰为光作见证；信子者得作神的儿女",  "pages": (24, 31)},
    {"verses": (14, 18), "title": "道成了肉身；从他丰满的恩典里我们都领受了", "pages": (31, 40)},
    {"verses": (19, 28), "title": "约翰回答祭司：我不是基督",              "pages": (40, 48)},
    {"verses": (29, 34), "title": "看哪，神的羔羊！圣灵仿佛鸽子降下",        "pages": (48, 56)},
    {"verses": (35, 51), "title": "首批门徒；耶稣呼召拿但业",                "pages": (56, 65)},
]


_CIRCLE_DIGITS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿"
_CIRCLE_TO_INT: dict[str, int] = {}
for i, ch in enumerate(_CIRCLE_DIGITS, 1):
    _CIRCLE_TO_INT[ch] = i


def _strip_leading_circle(s: str) -> str:
    s = s.lstrip()
    while s and s[0] in _CIRCLE_TO_INT:
        s = s[1:].lstrip()
    return s


# ────────────────────────────────────────────────────────────────────────
# Bible verse scripture-box (one per section, with hidden anchor h2)
# ────────────────────────────────────────────────────────────────────────

def scripture_block(verses_range: tuple[int, int]) -> str:
    a, b = verses_range
    ref = f"约翰福音 1:{a}-{b}"
    anchor_id = f"john-1-{a}-{b}"
    inner = "".join(f"<strong>{v}.</strong>{JOHN_1[str(v)]}" for v in range(a, b + 1))
    return (
        f'<h2 class="scripture-anchor" id="{anchor_id}" data-ref="{ref}" style="display:none">{ref}</h2>\n\n'
        f'<div class="scripture-box" markdown="1">\n'
        f'<p class="scripture-ref">{ref}</p>\n\n'
        f'<p>{inner}</p>\n\n'
        f'</div>\n'
    )


# ────────────────────────────────────────────────────────────────────────
# Per-page: identify footnote defs, build local circled→global map
# ────────────────────────────────────────────────────────────────────────

RUNNING_HDR_PATTERNS = [
    re.compile(r"^#\s*加尔文文集.*约翰福音注释\s*$"),
    re.compile(r"^#\s*约翰福音注释\s*$"),
    re.compile(r"^#\s*第[一二三四五六七八九十百零〇0-9]+\s*章\s*\*?\s*$"),
    re.compile(r"^\d{1,3}\s*$"),
]

_FN_DEF_RE = re.compile(r"^([" + _CIRCLE_DIGITS + r"])[ 　](.+)$")


def find_john_verse(opener_text: str, chapter_verses: dict[str, str]) -> int | None:
    head = _strip_leading_circle(opener_text)
    head = re.sub(r"[，。、；：（）\s]", "", head)[:8]
    if not head:
        return None
    for vstr, text in chapter_verses.items():
        ct = re.sub(r"[，。、；：（）　\s]", "", text)
        if ct.startswith(head):
            return int(vstr)
    return None


def fix_inline_h2(line: str, john_1: dict[str, str]) -> str:
    """OCR sometimes puts the verse-opener line as `## XXX...` (a long h2).
    Convert to verse-anchor bold form for verse-nav JS pickup.
    """
    if not line.startswith("## "):
        return line
    content = line[3:].strip()
    if len(content) <= 40:
        return line
    period = content.find("。")
    if period == -1 or period > 60:
        opener, rest = content[:30], content[30:]
    else:
        opener, rest = content[: period + 1], content[period + 1 :]
    v = find_john_verse(opener, john_1)
    opener_clean = _strip_leading_circle(opener)
    if v is not None:
        return f"**约翰福音 1:{v}。** *{opener_clean}* {rest}"
    return f"**{opener_clean}** {rest}"


def maybe_promote_verse_opener(para: str, john_1: dict[str, str]) -> str:
    """Detect a paragraph that opens with a CUV John 1 verse quote and
    rewrite it as `**约翰福音 1:N。** *quote。* commentary` (verse-nav).
    """
    if not para or para.startswith("[^") or para.startswith("**约翰福音"):
        return para
    if len(para) < 30:
        return para
    body = para[1:].lstrip() if para[0] in _CIRCLE_TO_INT else para
    body_clean = re.sub(r"[，。、；：（）　\s\"“”]", "", body)[:10]
    if len(body_clean) < 4:
        return para
    best_v = None
    best_len = 0
    for vstr, text in john_1.items():
        text_clean = re.sub(r"[，。、；：（）　\s]", "", text)
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
    para_no_circ = para[1:].lstrip() if para[0] in _CIRCLE_TO_INT else para
    period = para_no_circ.find("。")
    if period == -1 or period > 40:
        opener, rest = para_no_circ[:12], para_no_circ[12:]
    else:
        opener, rest = para_no_circ[: period + 1], para_no_circ[period + 1 :]
    return f"**约翰福音 1:{best_v}。** *{opener}* {rest}".rstrip()


# ────────────────────────────────────────────────────────────────────────
# Page-level processing with fn mapping
# ────────────────────────────────────────────────────────────────────────

def process_page(text: str, fn_counter: int) -> tuple[str, list[tuple[int, str]], int]:
    """Process one OCR'd page.

    Returns:
      body_md - body text with `[^N]` kramdown refs in place of `①②③`
      fn_defs - list of (global_id, text) tuples for this page's footnotes
      next_counter - updated global fn counter

    Strategy:
      1) Normalize lines (drop running headers, transform long `## ` lines).
      2) Promote verse-opener paragraphs.
      3) Extract footnote def paragraphs (split multi-line concat blocks).
      4) Assign sequential global IDs to defs.
      5) In remaining body, replace circled digits with `[^N]` refs using
         per-page-local→global mapping.
    """
    # Step 1: line-level normalization
    out_lines: list[str] = []
    for line in text.splitlines():
        if any(p.match(line.rstrip()) for p in RUNNING_HDR_PATTERNS):
            continue
        out_lines.append(fix_inline_h2(line.rstrip(), JOHN_1))
    text2 = re.sub(r"\n{3,}", "\n\n", "\n".join(out_lines)).strip()

    # Step 2-3: paragraph promote + fn extract
    paras = re.split(r"\n{2,}", text2)
    body_paras: list[str] = []
    fn_defs: list[tuple[int, str]] = []      # (global_id, text)
    local_to_global: dict[int, int] = {}     # page-local fn number → global id

    for p in paras:
        if not p:
            continue
        promoted = maybe_promote_verse_opener(p, JOHN_1)
        if promoted != p or promoted.startswith("**约翰福音"):
            body_paras.append(promoted)
            continue
        # Check if it's a footnote-def block
        first = p.splitlines()[0]
        m = _FN_DEF_RE.match(first)
        if not m:
            body_paras.append(p)
            continue
        # Multi-line fn block: split each line that starts with circled digit
        cur_lines: list[str] = []
        cur_local: int | None = None
        for line in p.splitlines():
            mline = _FN_DEF_RE.match(line)
            if mline:
                if cur_lines and cur_local is not None:
                    fn_counter += 1
                    local_to_global[cur_local] = fn_counter
                    fn_defs.append((fn_counter, " ".join(cur_lines).strip()))
                circ = mline.group(1)
                cur_local = _CIRCLE_TO_INT[circ]
                cur_lines = [mline.group(2)]
            else:
                cur_lines.append(line.strip())
        if cur_lines and cur_local is not None:
            fn_counter += 1
            local_to_global[cur_local] = fn_counter
            fn_defs.append((fn_counter, " ".join(cur_lines).strip()))

    body = "\n\n".join(body_paras)

    # Step 5: replace inline circled digits in body with `[^N]` refs.
    # We process digits in descending order so larger numbers don't
    # accidentally match a substring of smaller ones (though circled
    # digits are single Unicode chars, this is just defensive).
    def replace_circle(ch: str) -> str:
        local = _CIRCLE_TO_INT.get(ch)
        if local is None:
            return ch
        g = local_to_global.get(local)
        if g is None:
            # Orphan ref — no matching def on this page. Strip.
            return ""
        return f"[^{g}]"

    body = "".join(replace_circle(c) if c in _CIRCLE_TO_INT else c for c in body)

    return body, fn_defs, fn_counter


def load_pages(start: int, end: int, fn_counter: int) -> tuple[str, list[tuple[int, str]], int]:
    body_parts: list[str] = []
    all_defs: list[tuple[int, str]] = []
    for p in range(start, end + 1):
        f = REPO / f"calvin_raw/john-scan/ocr/page_{p:04d}.md"
        if not f.exists():
            continue
        body, defs, fn_counter = process_page(
            f.read_text(encoding="utf-8"), fn_counter
        )
        if body:
            body_parts.append(body)
        all_defs.extend(defs)
    return "\n\n".join(body_parts), all_defs, fn_counter


# ────────────────────────────────────────────────────────────────────────
# Long-paragraph splitting (Gate 6)
# ────────────────────────────────────────────────────────────────────────

def split_long_paragraphs(text: str, max_len: int = 1400) -> str:
    """Split paragraphs longer than max_len at sentence boundaries (。).

    Targets pdf-pipeline Gate 6: no line > 1500 chars (we use 1400 as a
    safer threshold).
    """
    paras = re.split(r"\n{2,}", text)
    out: list[str] = []
    for p in paras:
        if len(p) <= max_len or "\n" in p.strip():
            out.append(p)
            continue
        # Split into sentences keeping the 。 attached.
        sentences = re.split(r"(?<=。)", p)
        chunks: list[str] = []
        cur = ""
        for s in sentences:
            if len(cur) + len(s) > max_len and cur:
                chunks.append(cur)
                cur = s
            else:
                cur += s
        if cur:
            chunks.append(cur)
        out.extend(chunks)
    return "\n\n".join(out)


# ────────────────────────────────────────────────────────────────────────
# Main assemble
# ────────────────────────────────────────────────────────────────────────

def build_chapter_md() -> str:
    fm = (
        "---\n"
        "layout: calvin-en\n"
        'book_id: john-scan\n'
        'book_name: "约翰福音（扫描版）"\n'
        "chapter: 1\n"
        "header-img: psalm-bg-mountain.jpg\n"
        "date: 2026-06-03 16:00\n"
        'prev_section: preface\n'
        'prev_label: "序言"\n'
        'next_section: 2\n'
        'next_label: "第二章"\n'
        "---\n\n"
    )
    body = ["# 约翰福音 1 —— 道成肉身\n"]
    all_defs: list[tuple[int, str]] = []
    fn_counter = 0
    for sec in SECTIONS:
        v_lo, v_hi = sec["verses"]
        body.append(f'## 约翰福音 1:{v_lo}-{v_hi} —— {sec["title"]}\n')
        body.append(scripture_block(sec["verses"]))
        comm, sec_defs, fn_counter = load_pages(*sec["pages"], fn_counter)
        comm = split_long_paragraphs(comm)
        body.append(comm)
        body.append("")
        all_defs.extend(sec_defs)

    # Footnote definitions — kramdown auto-renders them as a numbered list
    # at the very bottom with backlinks. Two leading newlines before defs
    # avoid the setext-h2 ambiguity (—— vs ---).
    if all_defs:
        body.append("")
        for gid, text in all_defs:
            body.append(f"[^{gid}]: {text}")
            body.append("")
    return fm + "\n".join(body) + "\n"


def main() -> int:
    out = REPO / "calvin/john-scan/1.md"
    content = build_chapter_md()
    out.write_text(content, encoding="utf-8")
    n_sections = content.count("## 约翰福音 1:")
    n_boxes = content.count('class="scripture-box"')
    n_anchors = content.count('class="scripture-anchor"')
    n_fn_refs = len(set(re.findall(r"\[\^(\d+)\](?!:)", content)))
    n_fn_defs = len(re.findall(r"^\[\^(\d+)\]: ", content, re.MULTILINE))
    long_lines = [
        (i + 1, len(line))
        for i, line in enumerate(content.splitlines())
        if i > 20 and len(line) > 1500
    ]
    print(f"wrote {out} ({len(content):,} chars)")
    print(f"  sections={n_sections}  boxes={n_boxes}  anchors={n_anchors}")
    print(f"  fn refs unique={n_fn_refs}  fn defs={n_fn_defs}")
    print(f"  long lines>1500: {len(long_lines)} {long_lines[:3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
