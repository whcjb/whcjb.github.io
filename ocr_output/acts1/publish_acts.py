#!/usr/bin/env python3
"""
Publish Calvin's Commentary on Acts (English) to the Jekyll site.
Reads acts1_raw.txt (Acts 1-13) and acts2_raw.txt (Acts 14-28),
combines them, and generates individual chapter files.
"""
import os
import re

RAW1 = "/Users/yanpeifa/Documents/whcjb.github.io/ocr_output/acts1/acts1_raw.txt"
RAW2 = "/Users/yanpeifa/Documents/whcjb.github.io/ocr_output/acts2/acts2_raw.txt"
OUT_DIR = "/Users/yanpeifa/Documents/whcjb.github.io/calvin/acts-en"
BOOK_ID = "acts-en"
BOOK_NAME = "Calvin on Acts"
TOTAL_CHAPTERS = 28
DATE = "2026-05-27 10:55"

# Footnote definitions: "364 “text”" or "364 "text""
# Footnote continuations: "366 but whosoever..." (number + lowercase)
FOOTNOTE_RE = re.compile(r'^\d+\s+[“”‘’"\'a-z]')
SECTION_HEADER_RE = re.compile(r'^## Acts (\d+):')

# Blocks to skip entirely
SKIP_TEXT = [
    "COMMENTARY UPON THE ACTS OF THE APOSTLES",
    "BY JOHN CALVIN",
    "EDITED FROM THE ORIGINAL ENGLISH TRANSLATION",
    "EDITORS PREFACE",
    "THE COMMENTARIES OF M. JOHN CALVIN UPON THE ACTES",
    "TO THE RIGHT HONORABLE",
    "TO THE MOST RENOWNED PRINCE",
    "THE EPISTLE TO THE READER",
    "THE ARGUMENT",
    "UPON THE ACTS OF THE APOSTLES",
]


def is_footnote_content(block):
    """Footnote definition blocks like: 1 "Expungere," ... 2 "text"..."""
    return bool(FOOTNOTE_RE.match(block.strip()))


def is_skip_block(block):
    t = block.strip()
    if not t:
        return True
    # Running headers like "COMMENTARY UPON THE ACTS OF THE APOSTLES. CHAPTER 1"
    if re.match(r'^COMMENTARY UPON THE ACTS', t):
        return True
    # Standalone chapter headings like "CHAPTER 14"
    if re.match(r'^CHAPTER\s+\d+$', t):
        return True
    # Skip dedication/preface blocks
    for skip in SKIP_TEXT:
        if t.startswith(skip):
            return True
    return False


def merge_split_paragraphs(blocks):
    """Merge blocks that are cross-page paragraph continuations.
    A block ending without sentence-ending punctuation followed by a block
    starting with lowercase is a continuation split by a page break.
    """
    merged = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        # Keep merging while the block looks like it continues on the next
        while i + 1 < len(blocks):
            next_block = blocks[i + 1]
            # Skip merge if either is a section header or verse block
            if block.startswith('##') or next_block.startswith('##'):
                break
            if block.startswith('**') and re.match(r'^\*\*\d+\.\*\*', block):
                break
            # Check if this block ends mid-sentence
            end_char = block.rstrip()[-1] if block.rstrip() else ''
            next_start = next_block.lstrip()[0] if next_block.lstrip() else ''
            if end_char not in '.!?;:"\')”' and next_start.islower():
                block = block.rstrip() + ' ' + next_block.lstrip()
                i += 1
            else:
                break
        merged.append(block)
        i += 1
    return merged


def read_raw(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_blocks(text):
    """Split text into blocks on double-newline."""
    raw_blocks = re.split(r'\n{2,}', text)
    return [b.strip() for b in raw_blocks if b.strip()]


def group_by_chapter(blocks):
    """Group blocks into chapters. Returns dict {chapter_num: [block, ...]}."""
    chapters = {}
    current_ch = None
    found_first = False

    for block in blocks:
        # Check if this is a section header
        m = SECTION_HEADER_RE.match(block)
        if m:
            found_first = True
            ch = int(m.group(1))
            current_ch = ch
            if ch not in chapters:
                chapters[ch] = []
            chapters[ch].append(block)
            continue

        if not found_first:
            # Skip everything before first Acts section
            continue

        if is_footnote_content(block):
            continue

        if is_skip_block(block):
            continue

        if current_ch is not None:
            chapters[current_ch].append(block)

    # Post-process: merge cross-page paragraph splits within each chapter
    for ch in chapters:
        chapters[ch] = merge_split_paragraphs(chapters[ch])

    return chapters


def write_chapter(ch, blocks, prev_ch=None, next_ch=None):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{ch}.md")

    front_matter = f"""---
layout: calvin-en
book_id: {BOOK_ID}
book_name: "{BOOK_NAME}"
chapter: {ch}
total_chapters: {TOTAL_CHAPTERS}
header-img: psalm-bg-mountain.jpg
date: {DATE}
"""
    if prev_ch:
        front_matter += f'prev_section: {prev_ch}\n'
        front_matter += f'prev_label: "Chapter {prev_ch}"\n'
    if next_ch:
        front_matter += f'next_section: {next_ch}\n'
        front_matter += f'next_label: "Chapter {next_ch}"\n'
    front_matter += "---\n"

    body = "\n\n".join(blocks)
    content = front_matter + "\n" + body + "\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Written: {path} ({len(blocks)} blocks)")


def write_index():
    path = os.path.join(OUT_DIR, "index.html")
    chapters_html = "\n".join(
        f'    <li><a href="{{{{ site.baseurl }}}}/calvin/acts-en/{i}/">Chapter {i}</a></li>'
        for i in range(1, TOTAL_CHAPTERS + 1)
    )
    content = f"""---
layout: calvin-en-book
book_id: {BOOK_ID}
book_name: "Calvin's Commentary on Acts (English)"
chapters: {TOTAL_CHAPTERS}
header-img: psalm-bg-mountain.jpg
date: {DATE}
---
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Written: {path}")


def main():
    print("Reading raw files...")
    text1 = read_raw(RAW1)
    text2 = read_raw(RAW2)

    print("Parsing blocks...")
    blocks1 = parse_blocks(text1)
    blocks2 = parse_blocks(text2)
    all_blocks = blocks1 + blocks2
    print(f"  Total blocks: {len(all_blocks)}")

    print("Grouping by chapter...")
    chapters = group_by_chapter(all_blocks)
    print(f"  Chapters found: {sorted(chapters.keys())}")

    print("Writing chapter files...")
    ch_nums = sorted(chapters.keys())
    for i, ch in enumerate(ch_nums):
        prev_ch = ch_nums[i - 1] if i > 0 else None
        next_ch = ch_nums[i + 1] if i < len(ch_nums) - 1 else None
        write_chapter(ch, chapters[ch], prev_ch, next_ch)

    print("Writing index.html...")
    write_index()

    print(f"\nDone! {len(ch_nums)} chapters written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
