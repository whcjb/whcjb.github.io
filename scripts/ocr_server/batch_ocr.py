#!/usr/bin/env python3
"""
Batch OCR - 处理OCR输出的文本文件，按章节合并，生成网站md文件。
在client.py处理完PDF后运行此脚本。

用法:
  python batch_ocr.py --input /tmp/ocr_output/ --book john --book-name 约翰福音 --chapters 21 --start-page 9 --site-dir /path/to/whcjb.github.io/
"""

import argparse
import os
import re
from datetime import datetime
from pathlib import Path


def load_pages(input_dir: str) -> dict[int, str]:
    """Load all OCR'd page text files. Returns {page_num: text}."""
    pages = {}
    for f in Path(input_dir).glob("page_*.txt"):
        num = int(f.stem.split("_")[1])
        text = f.read_text(encoding="utf-8").strip()
        if text:
            pages[num] = text
    return pages


def find_chapter_boundaries(pages: dict[int, str], total_chapters: int) -> dict[int, tuple[int, int]]:
    """Auto-detect chapter boundaries by searching for '第X章' markers.
    Returns {chapter_num: (start_page, end_page)}."""
    chapter_pages = {}

    # Search for chapter markers in each page
    for page_num in sorted(pages.keys()):
        text = pages[page_num]
        # Match patterns like "第一章", "第二章", "第 一 章", "第1章" etc
        cn_nums = "一二三四五六七八九十"
        for ch in range(1, total_chapters + 1):
            # Build Chinese number
            if ch <= 10:
                cn = cn_nums[ch - 1]
            elif ch < 20:
                cn = "十" + (cn_nums[ch - 11] if ch > 10 else "")
            elif ch == 20:
                cn = "二十"
            else:
                cn = "二十" + cn_nums[ch - 21]

            patterns = [
                f"第{cn}章",
                f"第 {cn} 章",
                f"第{ch}章",
            ]
            for pat in patterns:
                if pat in text and ch not in chapter_pages:
                    chapter_pages[ch] = page_num
                    break

    # Convert to ranges
    chapters = sorted(chapter_pages.keys())
    ranges = {}
    for i, ch in enumerate(chapters):
        start = chapter_pages[ch]
        end = chapter_pages[chapters[i + 1]] - 1 if i + 1 < len(chapters) else max(pages.keys())
        ranges[ch] = (start, end)

    return ranges


def merge_pages(pages: dict[int, str], start: int, end: int) -> str:
    """Merge page texts from start to end (inclusive)."""
    texts = []
    for p in range(start, end + 1):
        if p in pages:
            text = pages[p]
            # Clean up common OCR artifacts
            text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)  # standalone page numbers
            text = re.sub(r"加尔文文集[·\s]*约翰福音注释[—\s]*", "", text)  # headers
            text = re.sub(r"[—一]+\s*加尔文文集[·\s]*.*?[—一]+", "", text)  # header bars
            texts.append(text.strip())
    return "\n\n".join(texts)


def generate_md(
    book_id: str,
    book_name: str,
    chapter: int,
    total_chapters: int,
    content: str,
    section_title: str = None,
) -> str:
    """Generate a markdown file with front matter."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = section_title or f"第{chapter}章"

    fm_lines = [
        "---",
        "layout: calvin-chapter",
        f"book_id: {book_id}",
        f"book_name: {book_name}",
        f"chapter: {chapter}",
        f"total_chapters: {total_chapters}",
    ]
    if section_title:
        fm_lines.append(f'section_title: "{section_title}"')
    fm_lines.extend([
        "header-img: psalm-bg-mountain.jpg",
        f"date: {now}",
        "---",
    ])

    return "\n".join(fm_lines) + "\n\n" + content + "\n"


def main():
    parser = argparse.ArgumentParser(description="Batch OCR to Markdown")
    parser.add_argument("--input", required=True, help="Directory with OCR page text files")
    parser.add_argument("--book", required=True, help="Book ID (e.g. 'john')")
    parser.add_argument("--book-name", required=True, help="Chinese book name (e.g. '约翰福音')")
    parser.add_argument("--chapters", type=int, required=True, help="Total chapters")
    parser.add_argument("--start-page", type=int, default=1, help="First content page (skip front matter)")
    parser.add_argument("--preface-pages", default=None, help="Preface page range, e.g. '7-8'")
    parser.add_argument("--site-dir", required=True, help="Path to whcjb.github.io root")
    parser.add_argument("--target", default="calvin", choices=["calvin", "reading"],
                        help="Target: calvin/ or reading/calvin/")
    args = parser.parse_args()

    # Load OCR pages
    pages = load_pages(args.input)
    print(f"Loaded {len(pages)} pages from {args.input}")

    if not pages:
        print("ERROR: No page files found")
        return

    # Detect chapter boundaries
    ranges = find_chapter_boundaries(pages, args.chapters)
    print(f"Detected {len(ranges)} chapter boundaries:")
    for ch, (s, e) in sorted(ranges.items()):
        print(f"  Chapter {ch}: pages {s}-{e}")

    # If not all chapters detected, ask user to provide manual ranges
    if len(ranges) < args.chapters:
        print(f"\nWARNING: Only {len(ranges)}/{args.chapters} chapters detected.")
        print("You may need to manually check and adjust.")

    # Output directory
    if args.target == "calvin":
        out_dir = Path(args.site_dir) / "calvin" / args.book
    else:
        out_dir = Path(args.site_dir) / "reading" / "calvin" / args.book
    out_dir.mkdir(parents=True, exist_ok=True)

    # Generate preface if specified
    if args.preface_pages:
        parts = args.preface_pages.split("-")
        ps, pe = int(parts[0]), int(parts[1]) if len(parts) > 1 else int(parts[0])
        preface_text = merge_pages(pages, ps, pe)
        if preface_text:
            md = generate_md(args.book, args.book_name, 0, args.chapters, preface_text, "纲要")
            (out_dir / "preface.md").write_text(md, encoding="utf-8")
            print(f"  preface.md: {len(preface_text)} chars")

    # Generate chapter files
    for ch, (start, end) in sorted(ranges.items()):
        content = merge_pages(pages, start, end)
        if not content:
            continue
        md = generate_md(args.book, args.book_name, ch, args.chapters, content)
        (out_dir / f"{ch}.md").write_text(md, encoding="utf-8")
        print(f"  {ch}.md: {len(content)} chars (pages {start}-{end})")

    # Generate index.html
    if args.target == "calvin":
        index_content = f"""---
layout: calvin-book
book_id: {args.book}
book_name: {args.book_name}
chapters: {args.chapters}
---
"""
    else:
        index_content = f"""---
layout: default
title: 加尔文{args.book_name}注释
---
"""

    (out_dir / "index.html").write_text(index_content, encoding="utf-8")
    print(f"\nDone! Files in {out_dir}/")
    print(f"Total: {len(ranges)} chapters + index.html")


if __name__ == "__main__":
    main()
