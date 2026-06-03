#!/usr/bin/env python3
"""Publish a OCR-assembled Chinese commentary to calvin/<book>-scan/.

Reads `calvin_raw/<book>-scan/calvin_<book>_zh.md` (produced by
`ocr_assemble.py`), splits it on `# 第N章` chapter headings, and writes:

    calvin/<book>-scan/preface.md   ← everything before chapter 1
    calvin/<book>-scan/1.md ... N.md ← per-chapter
    calvin/<book>-scan/index.html

Front-matter uses `layout: calvin-chapter` matching the existing
`calvin/<book>/` Chinese books on the site.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path


CHAPTER_RE = re.compile(r"^#\s*第([一二三四五六七八九十百零〇0-9]+)\s*章\s*$", re.MULTILINE)

CN_NUM_MAP = {
    '零': 0, '〇': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9,
}


def cn_to_int(s: str) -> int:
    s = s.strip()
    if s.isdigit():
        return int(s)
    # Handle 十/十一/二十/二十一 patterns
    if s == '十':
        return 10
    if s.startswith('十'):
        return 10 + cn_to_int(s[1:]) if len(s) > 1 else 10
    if '十' in s:
        a, _, b = s.partition('十')
        tens = CN_NUM_MAP.get(a, 1) * 10
        ones = cn_to_int(b) if b else 0
        return tens + ones
    return CN_NUM_MAP.get(s, 0)


def split_chapters(text: str) -> list[tuple[int, str, str]]:
    """Return list of (chapter_num, heading_line, body)."""
    matches = list(CHAPTER_RE.finditer(text))
    if not matches:
        return []
    parts = []
    for i, m in enumerate(matches):
        ch_label = m.group(1)
        ch_num = cn_to_int(ch_label)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        heading = text[m.start():m.end()].strip()
        body = text[m.end():end].strip()
        parts.append((ch_num, heading, body))
    return parts


def front_matter(book_id: str, book_name: str, chapter: int | str,
                 total: int, header_img: str, now: str,
                 title: str | None = None) -> str:
    fm = [
        "---",
        "layout: calvin-chapter",
        f"book_id: {book_id}",
        f"book_name: {book_name}",
    ]
    if title:
        fm.append(f"title: {title}")
    fm += [
        f"chapter: {chapter}",
        f"total_chapters: {total}",
        f"header-img: {header_img}",
        f"date: {now}",
        "---",
    ]
    return "\n".join(fm) + "\n\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True, help="e.g. john (uses john-scan/ paths)")
    ap.add_argument("--book-name", required=True, help="Display name e.g. 约翰福音")
    ap.add_argument("--book-id", default=None, help="default = {book}-scan")
    ap.add_argument("--out-dir", default=None,
                    help="default = calvin/{book}-scan")
    ap.add_argument("--raw-dir", default=None,
                    help="default = calvin_raw/{book}-scan")
    ap.add_argument("--header-img", default="img/post-bg-2015.jpg")
    args = ap.parse_args()

    book_id = args.book_id or f"{args.book}-scan"
    out_dir = Path(args.out_dir or f"calvin/{args.book}-scan")
    raw_dir = Path(args.raw_dir or f"calvin_raw/{args.book}-scan")

    src = raw_dir / f"calvin_{args.book}_zh.md"
    if not src.exists():
        print(f"[publish] missing source: {src}", file=sys.stderr)
        return 1
    text = src.read_text(encoding="utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)

    chapters = split_chapters(text)
    if not chapters:
        print("[publish] no `# 第N章` chapter headings found", file=sys.stderr)
        return 1
    total = max(c[0] for c in chapters)
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Preface = everything BEFORE the first chapter heading
    first_match = CHAPTER_RE.search(text)
    preface_body = text[:first_match.start()].strip() if first_match else text
    preface_path = out_dir / "preface.md"
    preface_path.write_text(
        front_matter(book_id, args.book_name, "preface", total,
                     args.header_img, now, title="序言") + preface_body + "\n",
        encoding="utf-8",
    )
    print(f"  → preface.md ({len(preface_body):,} chars)")

    for ch_num, heading, body in chapters:
        ch_path = out_dir / f"{ch_num}.md"
        ch_path.write_text(
            front_matter(book_id, args.book_name, ch_num, total,
                         args.header_img, now)
            + f"**{heading.lstrip('#').strip()}**\n\n{body}\n",
            encoding="utf-8",
        )
        print(f"  → {ch_num}.md ({len(body):,} chars)")

    index_path = out_dir / "index.html"
    index_path.write_text(
        "---\n"
        "layout: calvin-book\n"
        f"book_id: {book_id}\n"
        f"book_name: {args.book_name}\n"
        f"chapters: {total}\n"
        "has_preface: true\n"
        "---\n",
        encoding="utf-8",
    )
    print(f"  → index.html (chapters: {total})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
