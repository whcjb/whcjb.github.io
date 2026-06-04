#!/usr/bin/env python3
"""Content-driven chapter restructure for john-scan (chapter 2-21).

Algorithm:
  1. Load all OCR pages in the chapter's page range.
  2. Run ch1's per-page pipeline (strip headers, extract fn defs,
     convert circled refs → kramdown [^N], promote verse openers).
  3. Concatenate body paragraphs across pages (with cross-page join).
  4. Detect each paragraph's verse number (via the bold opener
     `**约翰福音 N:V。**` or via fuzzy match of the first sentence).
  5. Bucket paragraphs into verse-range sections by content, not by
     page approximation. Each section gets a contiguous verse range
     (~6-8 verses).
  6. Output: front matter + `# 约翰福音 N` + per-section header +
     CUV scripture-box + collected paragraphs + footnotes at end.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from restructure_john_scan_ch1 import (
    process_page, _join_cross_page, _strip_corrupt_marker,
    _split_first_sentence, _normalize_for_match, _verse_for_opener,
    maybe_promote_verse_opener,
    split_long_paragraphs, _TERM_PUNCT, _now,
)


REPO = Path("/Users/yanpeifa/Documents/whcjb.github.io")
CUV = json.load(open(REPO / "assets/cuv.json"))

# Chapter → first OCR page (from `# 第N章` markers).
CHAPTER_PAGES = {
    1: 13, 2: 66, 3: 86, 4: 121, 5: 158, 6: 194, 7: 243, 8: 279,
    9: 320, 10: 347, 11: 375, 12: 404, 13: 442, 14: 465, 15: 489,
    16: 513, 17: 542, 18: 566, 19: 588, 20: 616, 21: 646, 22: 661,
}

# Verses per section heuristic
TARGET_VERSES_PER_SECTION = 7


def _swap_chapter_verses(chapter_verses):
    """Monkey-patch ch1.JOHN_1 so ch1.process_page uses our chapter."""
    import restructure_john_scan_ch1 as ch1mod
    saved = ch1mod.JOHN_1
    ch1mod.JOHN_1 = chapter_verses
    return saved


def _restore_chapter_verses(saved):
    import restructure_john_scan_ch1 as ch1mod
    ch1mod.JOHN_1 = saved


# Match `**约翰福音 N:V。**` prefix at the start of a paragraph.
_VERSE_PREFIX_RE = re.compile(r"^\*\*约翰福音 \d+:(\d+)。\*\*")


def detect_paragraph_verse(para: str, chapter_verses: dict) -> int | None:
    """Return verse number if paragraph appears to be (or could be promoted
    to) a verse opener. Used for section assignment, NOT for re-promote.
    """
    m = _VERSE_PREFIX_RE.match(para)
    if m:
        return int(m.group(1))
    if para.startswith(("[^", "<", "#")):
        return None
    stripped = _strip_corrupt_marker(para)
    first_sent, _ = _split_first_sentence(stripped)
    first_clean = _normalize_for_match(first_sent)
    if len(first_clean) < 3:
        return None
    return _verse_for_opener(first_clean, chapter_verses)


def chapter_page_range(chapter: int) -> tuple[int, int]:
    return CHAPTER_PAGES[chapter], CHAPTER_PAGES[chapter + 1] - 1


def section_ranges(chapter: int) -> list[tuple[int, int]]:
    """Divide chapter's verses into ~7-verse sections."""
    n = len(CUV["43"][str(chapter)])
    n_sec = max(3, (n + TARGET_VERSES_PER_SECTION - 1) // TARGET_VERSES_PER_SECTION)
    chunk = (n + n_sec - 1) // n_sec
    ranges = []
    for i in range(n_sec):
        lo = i * chunk + 1
        hi = min((i + 1) * chunk, n)
        if lo > n:
            break
        ranges.append((lo, hi))
    return ranges


def scripture_block(chapter: int, verses_range: tuple[int, int]) -> str:
    a, b = verses_range
    ref = f"约翰福音 {chapter}:{a}-{b}"
    anchor_id = f"john-{chapter}-{a}-{b}"
    inner = "".join(f"<strong>{v}.</strong>{CUV['43'][str(chapter)][str(v)]}"
                    for v in range(a, b + 1))
    return (
        f'<h2 class="scripture-anchor" id="{anchor_id}" data-ref="{ref}" style="display:none">{ref}</h2>\n\n'
        f'<div class="scripture-box" markdown="1">\n'
        f'<p class="scripture-ref">{ref}</p>\n\n'
        f'<p>{inner}</p>\n\n'
        f'</div>\n'
    )


def load_chapter_paragraphs(chapter: int) -> tuple[list[str], list[tuple[int, str]]]:
    """Run process_page on each OCR page in the chapter's range, join
    cross-page mid-sentence continuations, return list of body paragraphs
    plus list of footnote (gid, text) pairs.
    """
    chapter_verses = CUV["43"][str(chapter)]
    saved = _swap_chapter_verses(chapter_verses)
    try:
        page_lo, page_hi = chapter_page_range(chapter)
        body_parts: list[str] = []
        all_defs: list[tuple[int, str]] = []
        fn_counter = 0
        # Use a wide verse_range that covers entire chapter so promote
        # picks up all valid openers regardless of section boundary.
        all_vr = (1, len(chapter_verses))
        for p in range(page_lo, page_hi + 1):
            f = REPO / f"calvin_raw/john-scan/ocr/page_{p:04d}.md"
            if not f.exists():
                continue
            body, defs, fn_counter = process_page(
                f.read_text(encoding="utf-8"), fn_counter, all_vr
            )
            if not body:
                all_defs.extend(defs)
                continue
            if body_parts:
                merged_prev, body = _join_cross_page(body_parts[-1], body)
                body_parts[-1] = merged_prev
            if body:
                body_parts.append(body)
            all_defs.extend(defs)
        all_text = "\n\n".join(p for p in body_parts if p)
        all_text = split_long_paragraphs(all_text)
        paras = re.split(r"\n{2,}", all_text)
        paras = [p.strip() for p in paras if p.strip()]
        return paras, all_defs
    finally:
        _restore_chapter_verses(saved)


def bucket_paragraphs(paras: list[str], chapter: int,
                       sec_ranges: list[tuple[int, int]]) -> list[list[str]]:
    """Assign each paragraph to a section by detected verse number.
    Paragraphs without a detected verse attach to the SAME section as
    the most-recent paragraph that had one. Initial verseless paragraphs
    go to section 0.
    """
    chapter_verses = CUV["43"][str(chapter)]
    buckets: list[list[str]] = [[] for _ in sec_ranges]
    cur_sec = 0
    for p in paras:
        v = detect_paragraph_verse(p, chapter_verses)
        if v is not None:
            for idx, (lo, hi) in enumerate(sec_ranges):
                if lo <= v <= hi:
                    cur_sec = idx
                    break
        buckets[cur_sec].append(p)
    return buckets


_CN_NUM = ['零','一','二','三','四','五','六','七','八','九','十',
           '十一','十二','十三','十四','十五','十六','十七','十八','十九',
           '二十','二十一','二十二']


def _cn(n: int) -> str:
    return _CN_NUM[n] if 0 <= n < len(_CN_NUM) else str(n)


def build_chapter_md(chapter: int) -> str:
    chapter_verses = CUV["43"][str(chapter)]
    sec_ranges = section_ranges(chapter)
    paras, all_defs = load_chapter_paragraphs(chapter)
    buckets = bucket_paragraphs(paras, chapter, sec_ranges)

    prev_section = "preface" if chapter == 1 else (chapter - 1)
    prev_label = "序言" if chapter == 1 else f"第{_cn(chapter - 1)}章"
    next_section = (chapter + 1) if chapter < 21 else None
    next_label = f"第{_cn(chapter + 1)}章" if chapter < 21 else None

    fm = [
        "---",
        "layout: calvin-en",
        "book_id: john-scan",
        'book_name: "约翰福音（扫描版）"',
        f"chapter: {chapter}",
        "header-img: psalm-bg-mountain.jpg",
        f"date: {_now()}",
        f"prev_section: {prev_section}",
        f'prev_label: "{prev_label}"',
    ]
    if next_section is not None:
        fm += [
            f"next_section: {next_section}",
            f'next_label: "{next_label}"',
        ]
    fm.append("---\n\n")

    body = [f"# 约翰福音 {chapter}\n"]
    for (lo, hi), paras_in_sec in zip(sec_ranges, buckets):
        body.append(f"## 约翰福音 {chapter}:{lo}-{hi}\n")
        body.append(scripture_block(chapter, (lo, hi)))
        for p in paras_in_sec:
            body.append(p)
            body.append("")

    if all_defs:
        body.append("")
        for gid, text in all_defs:
            body.append(f"[^{gid}]: {text}")
            body.append("")

    return "\n".join(fm) + "\n".join(body) + "\n"


def process_chapter(chapter: int) -> dict:
    out_path = REPO / f"calvin/john-scan/{chapter}.md"
    content = build_chapter_md(chapter)
    out_path.write_text(content, encoding="utf-8")
    return {
        "boxes": content.count('class="scripture-box"'),
        "fns": len(re.findall(r"^\[\^[0-9]+\]: ", content, re.MULTILINE)),
        "verse_markers": len(set(re.findall(r"\*\*约翰福音 \d+:(\d+)。\*\*", content))),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("chapter", nargs="?", type=int)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    chapters = list(range(2, 22)) if args.all else [args.chapter]
    for ch in chapters:
        if not (1 <= ch <= 21):
            print(f"skip invalid chapter {ch}")
            continue
        stats = process_chapter(ch)
        print(f"  ch{ch:2d}: {stats['boxes']} boxes  {stats['fns']} fns  {stats['verse_markers']} verse markers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
