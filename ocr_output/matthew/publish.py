#!/usr/bin/env python3
"""
Publish Calvin's Commentary on the Harmony of the Evangelists (Vol. 2) to Jekyll.
Reads matthew_raw.txt and generates one file per Matthew chapter.
Sections without Matthew are assigned to the last seen Matthew chapter.
"""
import os
import re
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.harmony_utils import (
    split_rich_by_verse, join_orphan_verse_numbers,
    merge_split_paragraphs, expand_verse_refs,
)

RAW = "/Users/yanpeifa/Documents/whcjb.github.io/ocr_output/matthew/matthew_raw.txt"
OUT_DIR = "/Users/yanpeifa/Documents/whcjb.github.io/calvin/matthew-en"
BOOK_ID = "matthew-en"
BOOK_NAME = "Calvin on Matthew (Vol. 2)"
DATE = "2026-05-27 15:06"

SECTION_HEADER_RE = re.compile(r'^## MATTHEW (\d+):')

CHAPTER_TITLES = {
    11: "Matthew 11 — John the Baptist's Question and Christ's Reply",
    12: "Matthew 12 — Sabbath Controversies and Pharisaic Opposition",
    13: "Matthew 13 — Parables of the Kingdom",
    14: "Matthew 14 — Death of John and the Feeding of the Multitude",
    15: "Matthew 15 — Jewish Traditions and Gentile Faith",
    16: "Matthew 16 — Peter's Confession and the Keys of the Kingdom",
    17: "Matthew 17 — The Transfiguration",
    18: "Matthew 18 — Humility, Offense, and Forgiveness",
    19: "Matthew 19 — Marriage, Children, and Riches",
    20: "Matthew 20 — The Vineyard Parable and Servant Leadership",
    21: "Matthew 21 — The Triumphal Entry and Temple Cleansing",
    22: "Matthew 22 — Controversies with Scribes and Pharisees",
    25: "Matthew 25 — Parables of the Last Judgment",
}


def is_footnote_content(block):
    return bool(re.match(r'^\d+\s+[""''"\'a-z]', block.strip()))


def is_skip_block(block):
    t = block.strip()
    return not t


def read_raw(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_blocks(text):
    raw_blocks = re.split(r'\n{2,}', text)
    return [b.strip() for b in raw_blocks if b.strip()]


def group_by_chapter(blocks):
    chapters = {}
    current_ch = None

    for block in blocks:
        m = SECTION_HEADER_RE.match(block)
        if m:
            ch = int(m.group(1))
            current_ch = ch
            if ch not in chapters:
                chapters[ch] = []
            chapters[ch].append(block)
            continue

        if current_ch is None:
            continue

        if is_footnote_content(block):
            continue

        if is_skip_block(block):
            continue

        chapters[current_ch].append(block)

    for ch in chapters:
        chapters[ch] = split_rich_by_verse(chapters[ch])
        chapters[ch] = join_orphan_verse_numbers(chapters[ch])
        chapters[ch] = merge_split_paragraphs(chapters[ch])
        chapters[ch] = expand_verse_refs(chapters[ch])

    return chapters


def ch_short_label(ch):
    title = CHAPTER_TITLES.get(ch, f"Matthew {ch}")
    return title.split(" — ")[0]


def write_chapter(ch, blocks, prev_ch=None, next_ch=None):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{ch}.md")

    front_matter = f"""---
layout: calvin-en
book_id: {BOOK_ID}
book_name: "{BOOK_NAME}"
chapter: {ch}
header-img: psalm-bg-mountain.jpg
date: {DATE}
"""
    if prev_ch:
        front_matter += f'prev_section: {prev_ch}\n'
        front_matter += f'prev_label: "{ch_short_label(prev_ch)}"\n'
    if next_ch:
        front_matter += f'next_section: {next_ch}\n'
        front_matter += f'next_label: "{ch_short_label(next_ch)}"\n'
    front_matter += "---\n"

    title = CHAPTER_TITLES.get(ch, f"Matthew {ch}")
    body = "\n\n".join(blocks)
    content = front_matter + "\n" + f"# {title}\n\n" + body + "\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Written: {path} ({len(blocks)} blocks)")


def write_index(chapter_nums):
    """Generate custom index.html with chapter pills."""
    path = os.path.join(OUT_DIR, "index.html")
    pills = "\n".join(
        f'        <a href="{{{{ site.baseurl }}}}/calvin/{BOOK_ID}/{ch}/" class="ch-pill"'
        f' data-title="{CHAPTER_TITLES.get(ch, f"Matthew {ch}")}">Ch {ch}</a>'
        for ch in sorted(chapter_nums)
    )
    content = f"""---
layout: default
book_id: {BOOK_ID}
book_name: "Calvin's Commentary on the Harmony of the Evangelists (Vol. 2)"
header-img: psalm-bg-mountain.jpg
date: {DATE}
---

<div class="container" style="padding-top: 70px;">
  <div class="row">
    <div class="col-lg-8 col-lg-offset-2 col-md-10 col-md-offset-1">

      <div style="margin: 32px 0 24px;">
        <a href="{{{{ site.baseurl }}}}/calvin/">&larr; 返回书卷列表</a>
      </div>

      <h2 style="border-bottom: 2px solid #0085a1; padding-bottom:8px; margin-bottom:24px;">
        Calvin's Commentary on the Harmony of the Evangelists (Vol. 2)
      </h2>

      <div class="ch-pills">
{pills}
      </div>

    </div>
  </div>
</div>

<style>
.ch-pills {{
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
}}
.ch-pill {{
  position: relative;
  display: inline-block;
  padding: 7px 18px;
  background: #e8f5e9;
  border: 1px solid #a5d6a7;
  border-radius: 20px;
  font-size: 14px;
  font-family: Georgia, serif;
  color: #2e7d32;
  text-decoration: none;
  transition: background 0.15s;
}}
.ch-pill:hover {{
  background: #4caf50;
  border-color: #4caf50;
  color: #fff;
  text-decoration: none;
}}
.ch-pill::after {{
  content: attr(data-title);
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  background: #333;
  color: #fff;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-family: Georgia, serif;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s;
  z-index: 10;
}}
.ch-pill:hover::after {{
  opacity: 1;
}}
</style>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Written: {path}")


def main():
    print("Reading raw file...")
    text = read_raw(RAW)

    print("Parsing blocks...")
    blocks = parse_blocks(text)
    print(f"  Total blocks: {len(blocks)}")

    print("Grouping by chapter...")
    chapters = group_by_chapter(blocks)
    ch_nums = sorted(chapters.keys())
    print(f"  Chapters found: {ch_nums}")

    print("Writing chapter files...")
    for i, ch in enumerate(ch_nums):
        prev_ch = ch_nums[i - 1] if i > 0 else None
        next_ch = ch_nums[i + 1] if i < len(ch_nums) - 1 else None
        write_chapter(ch, chapters[ch], prev_ch, next_ch)

    print("Writing index.html...")
    write_index(ch_nums)

    print(f"\nDone! {len(ch_nums)} chapters written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
