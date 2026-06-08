#!/usr/bin/env python3
"""Publish Calvin's Commentary on Acts (English) to the Jekyll site.

Per pdf-pipeline skill §03-publish-en.md:
- CCEL Acts uses harmony_utils.process_section_blocks pipeline
- Scripture passages get <div class="scripture-box"> wrap with cyan border
- Preface (Fetherstone dedicatory + Calvin's dedication + The Argument) is
  emitted as a separate preface.md file (not skipped)

Reads acts1_raw.txt (Acts 1-13) + acts2_raw.txt (Acts 14-28), groups by
chapter, calls process_section_blocks per section, writes 28 chapter
files + 1 preface.md + index.html with has_preface: true.
"""
import os
import re
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.harmony_utils import process_section_blocks

RAW1 = "/Users/yanpeifa/Documents/whcjb.github.io/calvin_raw/acts1/acts1_raw.txt"
RAW2 = "/Users/yanpeifa/Documents/whcjb.github.io/calvin_raw/acts2/acts2_raw.txt"
OUT_DIR = "/Users/yanpeifa/Documents/whcjb.github.io/calvin/acts-en"
BOOK_ID = "acts-en"
BOOK_NAME = "Calvin on Acts"
TOTAL_CHAPTERS = 28
DATE = "2026-06-08 14:30"

FOOTNOTE_RE = re.compile(r'^\d+\s+[“”‘’"\'a-z]')
SECTION_HEADER_RE = re.compile(r'^##\s+Acts\s+(\d+):')

# Pre-Acts-1 front matter sections — captured into preface.md instead of skipped.
PREFACE_SECTION_KEYS = [
    "TO THE RIGHT HONORABLE",
    "THE EPISTLE TO THE READER",
    "TO THE MOST RENOWNED PRINCE",
    "THE ARGUMENT",
]

# Running-header / chapter-marker blocks to drop unconditionally
SKIP_PATTERNS = [
    r'^COMMENTARY UPON THE ACTS',
    r'^CHAPTER\s+\d+$',
    r'^BY JOHN CALVIN$',
    r'^UPON THE ACTS OF THE APOSTLES\s*\.?$',
]


def is_footnote_def(block):
    return bool(FOOTNOTE_RE.match(block.strip()))


def is_running_header(block):
    t = block.strip()
    return any(re.match(p, t) for p in SKIP_PATTERNS)


def read_raw(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_blocks(text):
    raw_blocks = re.split(r'\n{2,}', text)
    return [b.strip() for b in raw_blocks if b.strip()]


def split_preface_and_chapters(blocks):
    """Walk blocks; collect everything BEFORE first `## Acts N:M` as preface
    candidate, then group remainder by chapter."""
    preface_blocks = []
    chapters = {}
    current_ch = None
    seen_first_acts = False
    for block in blocks:
        m = SECTION_HEADER_RE.match(block)
        if m:
            seen_first_acts = True
            ch = int(m.group(1))
            current_ch = ch
            chapters.setdefault(ch, []).append(block)
            continue
        if not seen_first_acts:
            preface_blocks.append(block)
            continue
        if is_footnote_def(block) or is_running_header(block):
            continue
        if current_ch is not None:
            chapters[current_ch].append(block)
    return preface_blocks, chapters


def format_chapter_content(blocks):
    """blocks starts with `## Acts N:M-K` headers. Split into sections,
    run process_section_blocks on each, concatenate."""
    # Group: list of (header, body_lines)
    sections = []
    current_header = None
    current_body = []
    for block in blocks:
        m = SECTION_HEADER_RE.match(block)
        if m:
            if current_header is not None:
                sections.append((current_header, current_body))
            current_header = block[len('## '):].strip()
            current_body = []
        else:
            current_body.append(block)
    if current_header is not None:
        sections.append((current_header, current_body))

    out = []
    for header, body_blocks in sections:
        out.append(f'## {header}')
        body_text = '\n\n'.join(body_blocks)
        out.extend(process_section_blocks(header, body_text))
    return '\n\n'.join(out)


def write_chapter(ch, blocks, prev_ch=None, next_ch=None):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{ch}.md")
    front_matter = (
        f"---\n"
        f"layout: calvin-en\n"
        f"book_id: {BOOK_ID}\n"
        f"book_name: \"{BOOK_NAME}\"\n"
        f"chapter: {ch}\n"
        f"total_chapters: {TOTAL_CHAPTERS}\n"
        f"header-img: psalm-bg-mountain.jpg\n"
        f"date: {DATE}\n"
    )
    if prev_ch:
        front_matter += f'prev_section: {prev_ch}\n'
        front_matter += f'prev_label: "Chapter {prev_ch}"\n'
    elif ch == 1:
        front_matter += 'prev_section: preface\n'
        front_matter += 'prev_label: "Preface"\n'
    if next_ch:
        front_matter += f'next_section: {next_ch}\n'
        front_matter += f'next_label: "Chapter {next_ch}"\n'
    front_matter += "---\n\n"

    body = format_chapter_content(blocks)
    with open(path, "w", encoding="utf-8") as f:
        f.write(front_matter + body + "\n")
    print(f"  Written: {path}")


def write_preface(preface_blocks):
    """Emit calvin/acts-en/preface.md from pre-Acts-1 blocks.

    Preface sections often appear as ONE long paragraph where the
    ALL-CAPS title sits inline with body text (e.g. "TO THE RIGHT
    HONORABLE ... HAPPY DAYS. If that (Right Honorable) ..."). So we
    can't rely on per-block upper-ratio; instead we:
      1. Concatenate all preface text
      2. Locate each PREFACE_SECTION_KEYS position
      3. For each section, split title → body at the first
         `. <Capital-word> <lowercase-word>` sentence boundary
    """
    # Drop noise blocks and concatenate
    clean = []
    for b in preface_blocks:
        t = b.strip()
        if not t:
            continue
        if is_running_header(t) or is_footnote_def(t):
            continue
        # Page-footer noise like "John Calvin Comm on Acts (V1)" or bare page numbers
        if re.match(r'^John Calvin Comm', t):
            continue
        if re.match(r'^\d{1,4}\s*$', t):
            continue
        clean.append(t)
    full = '\n\n'.join(clean)

    # Find each section key position in order
    positions = []  # (start_idx, key)
    for key in PREFACE_SECTION_KEYS:
        for m in re.finditer(re.escape(key), full):
            positions.append((m.start(), key))
    positions.sort()
    if not positions:
        print("  WARN: no preface sections found")
        return

    # Title→body splitter: a period, then within the next 0-3 words a 3+
    # letter lowercase token. Handles "If that", "THOU hast", "WHEREAS I have"
    # — body sentences whose first one or two tokens may themselves be
    # all-caps or single-letter pronouns before normal prose kicks in.
    title_end_re = re.compile(r'\.\s+\S+(?:\s+\S+){0,3}?\s+[a-z]{3,}')

    sections = []
    for i, (start, key) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(full)
        chunk = full[start:end].strip()
        m = title_end_re.search(chunk)
        if m:
            # Title is everything up to and including the period
            title_end = m.start() + 1  # include the `.`
            title = chunk[:title_end].rstrip(' .,').strip()
            body = chunk[m.start() + 2:].strip()  # skip ". "
        else:
            # No body in this section (e.g. THE ARGUMENT might be title only)
            title = chunk
            body = ''
        # Normalize whitespace in title and body
        title = re.sub(r'\s+', ' ', title).strip().rstrip('.,').strip()
        # Split body into paragraphs on \n\n
        paras = re.split(r'\n{2,}', body) if body else []
        paras = [re.sub(r'\s+', ' ', p).strip() for p in paras if p.strip()]
        # De-hyphenate
        paras = [re.sub(r'-\s+([a-z])', r'\1', p) for p in paras]
        sections.append((title, paras))

    out_parts = []
    for title, paras in sections:
        out_parts.append(f'## {title}')
        if paras:
            out_parts.append('\n\n'.join(paras))

    body = '\n\n'.join(out_parts)

    front_matter = (
        '---\n'
        f'layout: calvin-en\n'
        f'book_id: {BOOK_ID}\n'
        f'book_name: "{BOOK_NAME}"\n'
        f'title: "Preface"\n'
        f'header-img: psalm-bg-mountain.jpg\n'
        f'date: {DATE}\n'
        f'next_section: 1\n'
        f'next_label: "Chapter 1"\n'
        '---\n\n'
        '# Preface\n\n'
    )
    path = os.path.join(OUT_DIR, "preface.md")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(front_matter + body + '\n')
    print(f"  Written: {path}")


def write_index():
    path = os.path.join(OUT_DIR, "index.html")
    content = (
        '---\n'
        f'layout: calvin-en-book\n'
        f'book_id: {BOOK_ID}\n'
        f'book_name: "Calvin\'s Commentary on Acts (English)"\n'
        f'chapters: {TOTAL_CHAPTERS}\n'
        'has_preface: true\n'
        f'header-img: psalm-bg-mountain.jpg\n'
        f'date: {DATE}\n'
        '---\n'
    )
    with open(path, 'w', encoding='utf-8') as f:
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

    print("Splitting preface vs chapters...")
    preface_blocks, chapters = split_preface_and_chapters(all_blocks)
    print(f"  Preface blocks: {len(preface_blocks)}, Chapters: {sorted(chapters.keys())}")

    print("Writing preface...")
    write_preface(preface_blocks)

    print("Writing chapter files...")
    ch_nums = sorted(chapters.keys())
    for i, ch in enumerate(ch_nums):
        prev_ch = ch_nums[i - 1] if i > 0 else None
        next_ch = ch_nums[i + 1] if i < len(ch_nums) - 1 else None
        write_chapter(ch, chapters[ch], prev_ch, next_ch)

    print("Writing index.html...")
    write_index()

    print(f"\nDone! {len(ch_nums)} chapters + preface written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
