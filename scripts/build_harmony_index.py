#!/usr/bin/env python3
"""Build a scripture-verse index for Calvin's Harmony of the Evangelists
(EN, vols 1-3). The harmony volumes reorganize Matthew/Mark/Luke
chronologically rather than by chapter order, so locating a specific
verse requires this lookup table.

Reads all section headers `## MATTHEW X:Y-Z; MARK A:B-C; LUKE D:E-F`
from calvin/harmony-{1,2,3}-en/*.md, parses per-book verse ranges, and
writes calvin/harmony-index-en/index.html — a sorted table mapping each
Bible book's chapter+verse to its Harmony location with anchor link.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
OUT = ROOT / 'calvin/harmony-index-en/index.html'

BOOK_RE = re.compile(r'(MATTHEW|MARK|LUKE|JOHN)\s+(\d+)\s*:\s*([0-9,\s\-–]+)', re.I)
SECTION_HEADER_RE = re.compile(r'^##\s+(.+)$', re.M)


def kramdown_id(text: str) -> str:
    """Reproduce kramdown's auto_id slugifier for the input header text."""
    s = text.lower()
    s = re.sub(r'[^\w\s-]', '', s)            # strip punctuation
    s = re.sub(r'\s+', '-', s.strip())        # whitespace → hyphen
    s = re.sub(r'-{2,}', '-', s)              # collapse multiple hyphens
    return s


def parse_verse_spec(spec: str) -> list[tuple[int, int]]:
    """`3-12` → [(3,12)]; `1, 7-9, 12` → [(1,1),(7,9),(12,12)]."""
    out: list[tuple[int, int]] = []
    for chunk in re.split(r'\s*,\s*', spec.strip()):
        chunk = chunk.strip().rstrip('.')
        if not chunk:
            continue
        m = re.match(r'(\d+)\s*[-–]\s*(\d+)$', chunk)
        if m:
            out.append((int(m.group(1)), int(m.group(2))))
        elif chunk.isdigit():
            n = int(chunk)
            out.append((n, n))
    return out


def parse_header(header: str) -> list[tuple[str, int, list[tuple[int, int]]]]:
    """Parse `## MATTHEW 14:3-12; MARK 6:17-29` into list of
    (book, chapter, [verse_ranges]). Handles continuations like
    `MARK 4:1-12, 24-25` and `LUKE 8:1-10, 18; 10:23-24`."""
    parts = re.split(r'\s*;\s*', header)
    out: list[tuple[str, int, list[tuple[int, int]]]] = []
    last_book: str | None = None
    for part in parts:
        m = BOOK_RE.match(part.strip())
        if m:
            last_book = m.group(1).upper()
            chapter = int(m.group(2))
            ranges = parse_verse_spec(m.group(3))
            out.append((last_book, chapter, ranges))
        else:
            # Continuation form `N:M-K` for the same book
            m2 = re.match(r'(\d+)\s*:\s*([0-9,\s\-–]+)', part.strip())
            if m2 and last_book:
                chapter = int(m2.group(1))
                ranges = parse_verse_spec(m2.group(2))
                out.append((last_book, chapter, ranges))
    return out


def scan_vol(vol_num: int) -> list[dict]:
    """Return list of {vol, ch, header, anchor, books: [...]}."""
    en_dir = ROOT / f'calvin/harmony-{vol_num}-en'
    entries = []
    for path in sorted(en_dir.glob('*.md'), key=lambda p: int(p.stem) if p.stem.isdigit() else 999):
        if not path.stem.isdigit():
            continue
        ch_num = int(path.stem)
        text = path.read_text(encoding='utf-8')
        for m in SECTION_HEADER_RE.finditer(text):
            header = m.group(1).strip()
            if not re.search(r'(MATTHEW|MARK|LUKE|JOHN)', header, re.I):
                continue
            anchor = kramdown_id(header)
            books = parse_header(header)
            entries.append({
                'vol': vol_num,
                'ch': ch_num,
                'header': header,
                'anchor': anchor,
                'books': books,
            })
    return entries


def main():
    all_entries: list[dict] = []
    for vol in (1, 2, 3):
        all_entries.extend(scan_vol(vol))
    print(f'Collected {len(all_entries)} sections')

    # Build per-book index: book → chapter → list of (verse_range, entry_url, header)
    index: dict[str, dict[int, list[tuple[int, int, str, str]]]] = defaultdict(lambda: defaultdict(list))
    for entry in all_entries:
        url = f"/calvin/harmony-{entry['vol']}-en/{entry['ch']}/#{entry['anchor']}"
        label = f"卷{entry['vol']} 第{entry['ch']}章"
        for book, ch, ranges in entry['books']:
            for v_lo, v_hi in ranges:
                index[book][ch].append((v_lo, v_hi, url, label))

    # Sort each chapter's verse list
    for book in index:
        for ch in index[book]:
            index[book][ch].sort()

    # Generate HTML
    book_zh = {'MATTHEW': 'Matthew', 'MARK': 'Mark', 'LUKE': 'Luke', 'JOHN': 'John'}
    book_display_order = ['MATTHEW', 'MARK', 'LUKE', 'JOHN']

    rows_html = []
    for book in book_display_order:
        if book not in index:
            continue
        rows_html.append(f'<h2 id="{book.lower()}">{book_zh[book]}</h2>\n')
        rows_html.append('<div class="verse-index-table">')
        for ch in sorted(index[book]):
            for v_lo, v_hi, url, label in index[book][ch]:
                verse_ref = f'{ch}:{v_lo}' if v_lo == v_hi else f'{ch}:{v_lo}-{v_hi}'
                rows_html.append(
                    f'<div class="verse-row">'
                    f'<span class="verse-ref">{book_zh[book]} {verse_ref}</span>'
                    f'<a class="verse-link" href="{{{{ site.baseurl }}}}{url}">{label}</a>'
                    f'</div>'
                )
        rows_html.append('</div>\n')

    nav_html = ' &middot; '.join(
        f'<a href="#{b.lower()}">{book_zh[b]}</a>'
        for b in book_display_order if b in index
    )

    html = f'''---
layout: default
title: "Harmony of the Evangelists — Scripture Index"
---

<div class="container" style="padding-top: 70px;">
  <div class="row">
    <div class="col-lg-8 col-lg-offset-2 col-md-10 col-md-offset-1">

      <div style="margin: 32px 0 24px;">
        <a href="{{{{ site.baseurl }}}}/calvin/">&larr; 返回书卷列表</a>
      </div>

      <h1 style="border-bottom: 2px solid #0085a1; padding-bottom:8px; margin-bottom:16px;">
        Calvin's Harmony of the Evangelists — Scripture Index
      </h1>

      <p style="color:#666; margin-bottom:24px;">
        共观福音注释三卷按主题顺序排列，非圣经章节顺序。本索引列出每节经文在 Harmony 三卷中的位置，点击链接直达对应段落。
      </p>

      <p class="verse-index-nav">{nav_html}</p>

{chr(10).join(rows_html)}

    </div>
  </div>
</div>

<style>
.verse-index-nav {{
  margin: 24px 0;
  font-size: 15px;
}}
.verse-index-nav a {{
  color: #0085a1;
  font-weight: bold;
}}
.calvin-en-content h2,
[class*="verse-index"] ~ h2 {{
  margin-top: 28px;
  padding-bottom: 4px;
  border-bottom: 1px solid #ddd;
}}
.verse-index-table {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 4px 16px;
  margin-bottom: 20px;
}}
.verse-row {{
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 4px 0;
  border-bottom: 1px dashed #eee;
  font-size: 14px;
}}
.verse-ref {{
  font-family: Georgia, serif;
  color: #444;
  white-space: nowrap;
}}
.verse-link {{
  color: #0085a1;
  text-decoration: none;
  font-size: 13px;
  white-space: nowrap;
}}
.verse-link:hover {{
  text-decoration: underline;
}}
</style>
'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding='utf-8')
    total_entries = sum(
        len(index[b][c]) for b in index for c in index[b]
    )
    print(f'Wrote {OUT} ({total_entries} verse-range entries)')


if __name__ == '__main__':
    main()
