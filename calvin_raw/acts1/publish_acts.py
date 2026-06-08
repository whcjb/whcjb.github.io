#!/usr/bin/env python3
"""Publish Calvin's Commentary on Acts (English) to the Jekyll site.

Per pdf-pipeline skill §03-publish-en.md:
- CCEL Acts uses harmony_utils._scripture_box + the standard helpers, but
  Acts commentary blocks lack the *italic* markers that the harmony_utils
  auto-classifier relies on, so we split scripture vs commentary EXPLICITLY:
  the first body block of each section is scripture (always multi-verse),
  the remainder is commentary.
- Inline footnote refs come through as `[^N]` from the extraction layer
  (sup-digit detection in ccel_acts_extract_block_rich).
- Footnote definitions come from TWO sources:
    1. Footer fn blocks already emitted as `[^N]: text` by extract_ccel_acts
    2. Body-flow fn-def blocks (`^N "..."` paragraphs in raw) that this
       publish layer recognizes + converts to `[^N]: text`
  Both are buffered per chapter and emitted at chapter end so kramdown can
  render them in a bordered footnote section with bidirectional nav.
- Preface (Fetherstone dedicatory + Calvin's dedication + ARGUMENT) is
  emitted as a separate preface.md file.
"""
import os
import re
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.harmony_utils import (
    _scripture_box,
    split_rich_by_verse,
    join_orphan_verse_numbers,
    merge_split_paragraphs,
    expand_verse_refs,
)

RAW1 = "/Users/yanpeifa/Documents/whcjb.github.io/calvin_raw/acts1/acts1_raw.txt"
RAW2 = "/Users/yanpeifa/Documents/whcjb.github.io/calvin_raw/acts2/acts2_raw.txt"
OUT_DIR = "/Users/yanpeifa/Documents/whcjb.github.io/calvin/acts-en"
BOOK_ID = "acts-en"
BOOK_NAME = "Calvin on Acts"
TOTAL_CHAPTERS = 28
DATE = "2026-06-08 14:30"

SECTION_HEADER_RE = re.compile(r'^##\s+Acts\s+(\d+):')
FN_DEF_LINE_RE = re.compile(r'^\[\^(\d+)\]:\s*(.+)$')


def _is_fn_def_block(block):
    """True if block consists of `[^N]: text` lines only (one or more)."""
    s = block.strip()
    if not s:
        return False
    lines = [ln for ln in s.split('\n') if ln.strip()]
    return bool(lines) and all(FN_DEF_LINE_RE.match(ln.strip()) for ln in lines)
# Body-flow fn-def block:  starts with `<digit>(space)"quotedtext"` —
# leading digit was preserved by extract because the block hadn't yet
# seen non-digit content (page-number-vs-fn-marker ambiguity).
BODY_FN_BLOCK_RE = re.compile(r'^(\d+)\s+["“]')
# Multi-fn inside a single body block: split point between defs. Don't
# require a leading quote on the NEXT def — some defs are bare prose
# (e.g. `[^48] More properly, For the Lord doth...`).
INNER_FN_BREAK_RE = re.compile(r'\s+\[\^(\d+)\]\s+')

PREFACE_SECTION_KEYS = [
    "TO THE RIGHT HONORABLE",
    "THE EPISTLE TO THE READER",
    "TO THE MOST RENOWNED PRINCE",
    "THE ARGUMENT",
]

SKIP_PATTERNS = [
    r'^COMMENTARY UPON THE ACTS',
    r'^CHAPTER\s+\d+$',
    r'^BY JOHN CALVIN$',
    r'^UPON THE ACTS OF THE APOSTLES\s*\.?$',
]


def is_running_header(block):
    t = block.strip()
    return any(re.match(p, t) for p in SKIP_PATTERNS)


def read_raw(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_blocks(text):
    raw_blocks = re.split(r'\n{2,}', text)
    return [b.strip() for b in raw_blocks if b.strip()]


def convert_body_fn_block(block):
    """If `block` is a body-flow fn-def aggregate like
        '39 "Haesissent attoniti," might have stood astonished. [^40] "Quam in edito..."'
    return a list of `[^N]: text` def lines. Otherwise return None.
    """
    m = BODY_FN_BLOCK_RE.match(block.strip())
    if not m:
        return None
    n = m.group(1)
    rest = block.strip()[m.end(1):].lstrip()
    # Now split on inner ` [^M] ` markers preceding quotes
    parts = INNER_FN_BREAK_RE.split(rest)
    # parts: [first_def_text, num2, def2_text, num3, def3_text, ...]
    defs = [(n, parts[0].strip())]
    for i in range(1, len(parts), 2):
        if i + 1 >= len(parts):
            break
        defs.append((parts[i], parts[i + 1].strip()))
    return [f'[^{num}]: {txt}' for num, txt in defs]


def split_preface_and_chapters(blocks):
    """Return (preface_blocks, {ch_num: [blocks]}).
    Footnote-def lines (`[^N]: ...`) and body-flow fn-def blocks are
    collected per chapter into the chapter's block list (publish stage
    will sort + emit them as a chapter-end FOOTNOTES section).
    """
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
        if is_running_header(block):
            continue
        if current_ch is not None:
            chapters[current_ch].append(block)
    return preface_blocks, chapters


def format_section(header, body_blocks, chapter_fn_defs):
    """Render one `## Acts N:M-K` section.

    body_blocks[0] = scripture (a single block w/ multiple **N.** markers
                     concatenated, possibly with inline [^N] refs)
    body_blocks[1:] = commentary blocks; fn-def-block fragments are
                      extracted into chapter_fn_defs (mutated in place).

    Returns a list of markdown blocks (no header — the header is added
    by the caller).
    """
    out = []
    if not body_blocks:
        return out

    # Pull scripture (first block) — also strip any fn-def fragments from
    # the front of the block list in case the raw started with a stray
    # body-flow fn def before scripture (shouldn't happen but defensive).
    scripture_block = None
    rest = []
    for b in body_blocks:
        fn_lines = convert_body_fn_block(b)
        if fn_lines:
            chapter_fn_defs.extend(fn_lines)
            continue
        if _is_fn_def_block(b):
            # block consists of one or more `[^N]: text` def lines —
            # split per line so each def is tracked individually.
            for ln in b.strip().split('\n'):
                ln = ln.strip()
                if FN_DEF_LINE_RE.match(ln):
                    chapter_fn_defs.append(ln)
            continue
        if scripture_block is None:
            scripture_block = b
        else:
            rest.append(b)

    if scripture_block is None:
        return out

    out.append(_scripture_box(header, scripture_block))

    # Process remaining commentary blocks (extract fn-defs as we go)
    commentary_blocks = []
    for b in rest:
        fn_lines = convert_body_fn_block(b)
        if fn_lines:
            chapter_fn_defs.extend(fn_lines)
            continue
        if _is_fn_def_block(b):
            for ln in b.strip().split('\n'):
                ln = ln.strip()
                if FN_DEF_LINE_RE.match(ln):
                    chapter_fn_defs.append(ln)
            continue
        commentary_blocks.append(b)

    if commentary_blocks:
        comm_all = [f'## {header}'] + commentary_blocks
        comm_all = split_rich_by_verse(comm_all)
        comm_all = join_orphan_verse_numbers(comm_all)
        comm_all = merge_split_paragraphs(comm_all)
        comm_all = expand_verse_refs(comm_all)
        if comm_all and comm_all[0].startswith('## '):
            comm_all = comm_all[1:]
        out.extend(comm_all)

    return out


def format_chapter(blocks):
    """blocks: list of blocks for a single chapter, starting with
    `## Acts N:M` headers. Returns the chapter body markdown."""
    # Group: [(header, body_blocks), ...]
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

    chapter_fn_defs = []
    out = []
    for header, body_blocks in sections:
        out.append(f'## {header}')
        out.extend(format_section(header, body_blocks, chapter_fn_defs))

    # De-dup fn defs (keep first occurrence), sort numerically for tidy
    seen = set()
    unique_defs = []
    for line in chapter_fn_defs:
        m = FN_DEF_LINE_RE.match(line)
        if not m:
            continue
        n = m.group(1)
        if n in seen:
            continue
        seen.add(n)
        unique_defs.append((int(n), line))
    unique_defs.sort(key=lambda x: x[0])

    # Footnote defs MUST be separated from preceding body by a blank line
    # AND by a `\n---\n` rule (matches harmony3 style). They're emitted as
    # ordinary `[^N]: text` lines so kramdown generates the auto-footnotes
    # section with bidirectional nav.
    if unique_defs:
        out.append('\n\n---\n')
        out.append('\n'.join(line for _, line in unique_defs))

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

    body = format_chapter(blocks)
    with open(path, "w", encoding="utf-8") as f:
        f.write(front_matter + body + "\n")
    print(f"  Written: {path}")


def write_preface(preface_blocks):
    """Position-based split: each PREFACE_SECTION_KEYS occurrence opens a
    new section; title runs until the first `. <word> <lowercase-3+>` boundary.
    """
    clean = []
    for b in preface_blocks:
        t = b.strip()
        if not t:
            continue
        if is_running_header(t):
            continue
        if re.match(r'^John Calvin Comm', t):
            continue
        if re.match(r'^\d{1,4}\s*$', t):
            continue
        # Drop fn-def fragments and `[^N]: text` lines from preface
        m = FN_DEF_LINE_RE.match(t)
        if m:
            continue
        clean.append(t)
    full = '\n\n'.join(clean)

    positions = []
    for key in PREFACE_SECTION_KEYS:
        for m in re.finditer(re.escape(key), full):
            positions.append((m.start(), key))
    positions.sort()
    if not positions:
        print("  WARN: no preface sections found")
        return

    # Find body start: period + word + (0-3 words) + 3+ lowercase letters
    title_end_re = re.compile(r'\.\s+\S+(?:\s+\S+){0,3}?\s+[a-z]{3,}')

    sections = []
    for i, (start, key) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(full)
        chunk = full[start:end].strip()
        m = title_end_re.search(chunk)
        if m:
            title_end = m.start() + 1
            title = chunk[:title_end].rstrip(' .,').strip()
            body = chunk[m.start() + 2:].strip()
        else:
            title = chunk
            body = ''
        title = re.sub(r'\s+', ' ', title).strip().rstrip('.,').strip()
        paras = re.split(r'\n{2,}', body) if body else []
        paras = [re.sub(r'\s+', ' ', p).strip() for p in paras if p.strip()]
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
