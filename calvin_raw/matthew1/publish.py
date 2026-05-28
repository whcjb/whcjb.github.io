#!/usr/bin/env python3
"""
Publish Calvin's Commentary on the Harmony of the Evangelists (Vol. 1) to Jekyll.
Reads matthew1_raw.txt and generates 10 chapter pages + index.html.

Chapters group sections by narrative unit:
  1  Luke 1          — Birth announcement of John the Baptist
  2  Matthew 1       — Genealogy and birth of Jesus
  3  Luke 2; Matt 2  — The Nativity
  4  Matthew 3       — John the Baptist
  5  Matthew 4       — Temptation and beginning of ministry
  6  Matthew 5       — Sermon on the Mount (Part 1)
  7  Matthew 6       — Sermon on the Mount (Part 2)
  8  Matthew 7       — Sermon on the Mount (Part 3)
  9  Matthew 8–9     — Miracles and healings
  10 Matthew 10      — Sending of the Twelve
"""
import os
import re
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.harmony_utils import process_section_blocks

RAW = "/Users/yanpeifa/Documents/whcjb.github.io/calvin_raw/matthew1/matthew1_raw.txt"
OUT_DIR = "/Users/yanpeifa/Documents/whcjb.github.io/calvin/harmony-1-en"
BOOK_ID = "harmony-1-en"
BOOK_NAME = "Calvin on the Harmony of the Evangelists (Vol. 1)"
DATE = "2026-05-27 15:48"

# Each tuple: (chapter_num, first_section_header_normalized, chapter_title)
# The chapter starts at the given section header and ends just before the next.
CHAPTER_STARTS = [
    (1,  "LUKE 1:1-4",
     "Luke 1 — Birth Announcement of John the Baptist"),
    (2,  "MATTHEW 1:1-17; LUKE 3:23-38",
     "Matthew 1 — Genealogy and the Birth of Jesus"),
    (3,  "LUKE 2:1-7",
     "Luke 2; Matthew 2 — The Nativity"),
    (4,  "MATTHEW 3:1-6; MARK 1:1-6; LUKE 3:1-6",
     "Matthew 3 — John the Baptist"),
    (5,  "MATTHEW 4:1-4; MARK 1:12-13; LUKE 4:1-4",
     "Matthew 4 — The Temptation and Beginning of Ministry"),
    (6,  "MATTHEW 5:1-12; LUKE 6:20-26",
     "Matthew 5 — Sermon on the Mount (Part 1)"),
    (7,  "MATTHEW 6:1-4",
     "Matthew 6 — Sermon on the Mount (Part 2)"),
    (8,  "MATTHEW 7:1-5; MARK 4:24; LUKE 6:37-42",
     "Matthew 7 — Sermon on the Mount (Part 3)"),
    (9,  "MATTHEW 8:1-4; MARK 1:40-45; LUKE 5:12-16",
     "Matthew 8–9 — Miracles and Healings"),
    (10, "MATTHEW 10:1-8; MARK 6:7; LUKE 9:1-2",
     "Matthew 10 — Sending of the Twelve"),
]


def normalize_ref(text):
    """Normalize scripture reference: remove spaces after colons, collapse spaces."""
    text = re.sub(r':\s+(\d)', r':\1', text)
    return re.sub(r'\s+', ' ', text).strip()


def read_raw(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_sections(text):
    """Return list of (header, body) for each ## section."""
    # Split on section headers
    parts = re.split(r'\n## ([^\n]+)\n', text)
    # parts[0] is any preamble before first ##, then alternating header/body
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
    # Build boundary list: (chapter_num, normalized_start_header)
    boundaries = [(ch, normalize_ref(hdr)) for ch, hdr, _ in CHAPTER_STARTS]

    chapter_map = {}  # chapter_num → [(header, body)]
    current_chapter = None

    for header, body in sections:
        # Check if this section starts a new chapter
        for ch_num, boundary_hdr in boundaries:
            if header == boundary_hdr:
                current_chapter = ch_num
                break
        if current_chapter is None:
            # Shouldn't happen with correct CHAPTER_STARTS, but fallback
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
        # Get title for this chapter
        ch_title = next(t for c, _, t in CHAPTER_STARTS if c == ch)
        content = format_chapter_content(chapter_map[ch])
        write_chapter(ch, content, ch_title, prev_ch, next_ch)

    print("Writing index.html...")
    write_index(chapter_map)

    print(f"\nDone! {len(ch_nums)} chapters written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
