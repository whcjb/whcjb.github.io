#!/usr/bin/env python3
"""
Publish Calvin's Commentary on the Harmony of the Evangelists (Vol. 3) to Jekyll.
Reads harmony3_raw.txt and generates 9 chapter pages + index.html.

Chapters:
  1  Matthew 21    — Temple Controversies
  2  Matthew 22    — Conflicts with Religious Leaders
  3  Matthew 23    — Woes to the Pharisees
  4  Matthew 24    — The Olivet Discourse
  5  Matthew 25    — Parables of the Kingdom's End
  6  Matthew 26:1–56  — The Last Supper and Gethsemane
  7  Matthew 26:57 – 27:26 — The Trials of Jesus
  8  Matthew 27:27–66 — The Crucifixion and Burial
  9  Matthew 28; Mark 16; Luke 24 — The Resurrection and Ascension
"""
import os
import re
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.harmony_utils import process_section_blocks

RAW = "/Users/yanpeifa/Documents/whcjb.github.io/ocr_output/harmony3/harmony3_raw.txt"
OUT_DIR = "/Users/yanpeifa/Documents/whcjb.github.io/calvin/harmony-3-en"
BOOK_ID = "harmony-3-en"
BOOK_NAME = "Calvin on the Harmony of the Evangelists (Vol. 3)"
DATE = "2026-05-27 16:53"

# Each tuple: (chapter_num, first_section_header_normalized, chapter_title)
CHAPTER_STARTS = [
    (1, "MATTHEW 21:10-22; MARK 11:11-24; LUKE 19:39-48",
     "Matthew 21 — Temple Controversies"),
    (2, "MATTHEW 22:15-22; MARK 12:13-17; LUKE 20:20-26",
     "Matthew 22 — Conflicts with Religious Leaders"),
    (3, "MATTHEW 23:1-12; MARK 12:38-39; LUKE 11:43, 45-46; 20:45-46",
     "Matthew 23 — Woes to the Pharisees"),
    (4, "MARK 12:41-44; LUKE 21:1-4",
     "Matthew 24 — The Olivet Discourse"),
    (5, "MATTHEW 25:1-13",
     "Matthew 25 — Parables of the Kingdom's End"),
    (6, "MATTHEW 26:1-13; MARK 14:1-9; LUKE 22:1-2",
     "Matthew 26:1–56 — The Last Supper and Gethsemane"),
    (7, "MATTHEW 26:57-61; MARK 14:53-59; LUKE 22:54",
     "Matthew 26:57 – 27:26 — The Trials of Jesus"),
    (8, "MATTHEW 27:24-32; MARK 15:15-21; LUKE 23:24-32",
     "Matthew 27:27–66 — The Crucifixion and Burial"),
    (9, "MATTHEW 28:1-7; MARK 16:1-7; LUKE 24:1-8",
     "Matthew 28; Mark 16; Luke 24 — The Resurrection and Ascension"),
]


def normalize_ref(text):
    text = re.sub(r':\s+(\d)', r':\1', text)
    return re.sub(r'\s+', ' ', text).strip()


def read_raw(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_sections(text):
    """Return list of (header, body) for each ## section."""
    parts = re.split(r'\n## ([^\n]+)\n', text)
    sections = []
    i = 1
    while i < len(parts) - 1:
        header = normalize_ref(parts[i].strip())
        body = parts[i + 1].strip()
        sections.append((header, body))
        i += 2
    return sections


def assign_chapters(sections):
    """Assign each section to a chapter number."""
    boundaries = [(ch, normalize_ref(hdr)) for ch, hdr, _ in CHAPTER_STARTS]
    chapter_map = {}
    current_chapter = None

    for header, body in sections:
        for ch_num, boundary_hdr in boundaries:
            if header == boundary_hdr:
                current_chapter = ch_num
                break
        if current_chapter is None:
            current_chapter = 1
        if current_chapter not in chapter_map:
            chapter_map[current_chapter] = []
        chapter_map[current_chapter].append((header, body))

    return chapter_map


def format_chapter_content(sections_list):
    """Format chapter content with full processing pipeline."""
    chapter_blocks = []
    for header, body in sections_list:
        chapter_blocks.append(f'## {header}')
        chapter_blocks.extend(process_section_blocks(header, body))
    return "\n\n".join(chapter_blocks)


def ch_short_label(ch):
    for c, _, title in CHAPTER_STARTS:
        if c == ch:
            return title.split(" — ")[0]
    return f"Ch {ch}"


def write_chapter(ch, content, title, prev_ch=None, next_ch=None):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{ch}.md")

    front = f"""---
layout: calvin-en
book_id: {BOOK_ID}
book_name: "{BOOK_NAME}"
chapter: {ch}
header-img: psalm-bg-mountain.jpg
date: {DATE}
"""
    if prev_ch:
        front += f'prev_section: {prev_ch}\n'
        front += f'prev_label: "{ch_short_label(prev_ch)}"\n'
    if next_ch:
        front += f'next_section: {next_ch}\n'
        front += f'next_label: "{ch_short_label(next_ch)}"\n'
    front += "---\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(front + "\n")
        f.write(f"# {title}\n\n")
        f.write(content + "\n")
    print(f"  Written: {path}")


def write_index(chapter_data):
    """Generate index.html with chapter pills."""
    path = os.path.join(OUT_DIR, "index.html")

    pills = []
    for ch_num, _, ch_title in CHAPTER_STARTS:
        pill = (f'        <a href="{{{{ site.baseurl }}}}/calvin/{BOOK_ID}/{ch_num}/" '
                f'class="ch-pill" data-title="{ch_title}">Ch {ch_num}</a>')
        pills.append(pill)
    chapter_pills = "\n".join(pills)

    content = f"""---
layout: default
book_id: {BOOK_ID}
book_name: "{BOOK_NAME}"
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
        {BOOK_NAME}
      </h2>

      <div class="ch-pills">
{chapter_pills}
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

    print("Parsing sections...")
    sections = parse_sections(text)
    print(f"  Total sections: {len(sections)}")

    print("Assigning chapters...")
    chapter_map = assign_chapters(sections)
    ch_nums = sorted(chapter_map.keys())
    print(f"  Chapters: {ch_nums}")
    for ch in ch_nums:
        print(f"  Ch {ch}: {len(chapter_map[ch])} sections")

    print("Writing chapter files...")
    for i, ch in enumerate(ch_nums):
        prev_ch = ch_nums[i - 1] if i > 0 else None
        next_ch = ch_nums[i + 1] if i < len(ch_nums) - 1 else None
        ch_title = next(t for c, _, t in CHAPTER_STARTS if c == ch)
        content = format_chapter_content(chapter_map[ch])
        write_chapter(ch, content, ch_title, prev_ch, next_ch)

    print("Writing index.html...")
    write_index(chapter_map)

    print(f"\nDone! {len(ch_nums)} chapters written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
