#!/usr/bin/env python3
"""
Publish Calvin's Commentary on Hebrews (English) to the Jekyll site.
Reads heb_raw.txt and generates individual chapter files.
"""
import os
import re

RAW = "/Users/yanpeifa/Documents/whcjb.github.io/ocr_output/heb/heb_raw.txt"
OUT_DIR = "/Users/yanpeifa/Documents/whcjb.github.io/calvin/hebrews-en"
BOOK_ID = "hebrews-en"
BOOK_NAME = "Calvin on Hebrews"
TOTAL_CHAPTERS = 13
DATE = "2026-05-27 13:47"

SECTION_HEADER_RE = re.compile(r'^## Hebrews (\d+):')


def is_footnote_content(block):
    """Footnote reference lines: start with a number followed by quoted or lowercase text."""
    return bool(re.match(r'^\d+\s+[""''"\'a-z]', block.strip()))


def is_skip_block(block):
    t = block.strip()
    if not t:
        return True
    if re.match(r'^CHAPTER\s+\d+', t.upper()):
        return True
    return False


def join_orphan_verse_numbers(blocks):
    """Join standalone **N.** blocks with the following commentary block."""
    result = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        if re.match(r'^\*\*\d+\.\*\*$', block.strip()):
            if i + 1 < len(blocks) and not blocks[i + 1].startswith('##'):
                result.append(block.strip() + ' ' + blocks[i + 1].lstrip())
                i += 2
                continue
        result.append(block)
        i += 1
    return result


def merge_split_paragraphs(blocks):
    """Merge cross-page splits: next block starts lowercase = continuation."""
    merged = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        while i + 1 < len(blocks):
            next_block = blocks[i + 1]
            if block.startswith('##') or next_block.startswith('##'):
                break
            next_start = next_block.lstrip()[:1]
            if next_start.islower():
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
    raw_blocks = re.split(r'\n{2,}', text)
    return [b.strip() for b in raw_blocks if b.strip()]


PREFACE_SKIP = {
    "BY JOHN CALVIN",
    "COMMENTARIES ON THE EPISTLE OF PAUL THE APOSTLE TO THE HEBREWS",
    "EPISTLE OF ST. PAUL TO THE",
}

def get_preface_blocks(blocks):
    """Return all blocks before the first ## Hebrews header, post-processed."""
    preface = []
    for b in blocks:
        if re.match(r'^## Hebrews', b):
            break
        t = b.strip()
        if not t:
            continue
        # Skip title-page lines
        if any(t.startswith(sk) for sk in PREFACE_SKIP):
            continue
        preface.append(t)
    # Join orphan **N.** blocks, then merge lowercase-start splits
    return merge_split_paragraphs(join_orphan_verse_numbers(preface))


def write_preface(blocks):
    preface_blocks = get_preface_blocks(blocks)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "preface.md")
    front_matter = f"""---
layout: calvin-en
book_id: {BOOK_ID}
book_name: "{BOOK_NAME}"
title: "Translator's Preface & The Argument"
date: {DATE}
next_section: 1
next_label: "Chapter 1"
---

"""
    body = "\n\n".join(preface_blocks)
    with open(path, "w", encoding="utf-8") as f:
        f.write(front_matter + body + "\n")
    print(f"  Written: {path} ({len(preface_blocks)} blocks)")


def group_by_chapter(blocks):
    chapters = {}
    current_ch = None
    found_first = False

    for block in blocks:
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
            continue  # skip translator's preface and other front matter

        if is_footnote_content(block):
            continue

        if is_skip_block(block):
            continue

        if current_ch is not None:
            chapters[current_ch].append(block)

    for ch in chapters:
        chapters[ch] = join_orphan_verse_numbers(chapters[ch])
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
    content = f"""---
layout: calvin-en-book
book_id: {BOOK_ID}
book_name: "Calvin's Commentary on Hebrews (English)"
chapters: {TOTAL_CHAPTERS}
header-img: psalm-bg-mountain.jpg
date: {DATE}
---
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
    print(f"  Chapters found: {sorted(chapters.keys())}")

    print("Writing chapter files...")
    ch_nums = sorted(chapters.keys())
    for i, ch in enumerate(ch_nums):
        prev_ch = ch_nums[i - 1] if i > 0 else None
        next_ch = ch_nums[i + 1] if i < len(ch_nums) - 1 else None
        write_chapter(ch, chapters[ch], prev_ch, next_ch)

    print("Writing preface.md...")
    write_preface(blocks)

    print("Writing index.html...")
    write_index()

    print(f"\nDone! {len(ch_nums)} chapters written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
