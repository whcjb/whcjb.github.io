#!/usr/bin/env python3
"""Relocate misplaced verse-commentary paragraphs in OCR-published harmony /
calvin chapter md files.

When OCR doesn't preserve `**{书卷} N:V。**` bold prefix, Calvin's
verse-commentary paragraphs appear as bare `数字 + 空格 + 汉字` openers
(e.g., "32 他们虽知道上帝判定..."). The publish-time section bucketing
heuristic (restructure_scan_book.py) can mis-assign these — putting a v.32
paragraph into section 1:22-28 instead of 1:29-32.

This script:
  1. Parses each chapter md into sections `## {书卷} N:LO-HI`.
  2. For each section's body, finds paragraphs starting with bare
     verse-opener `^(\d+)[ 、.]<CJK>...`.
  3. If verse number K is OUT of [LO, HI] AND K is a valid verse in this
     bible chapter, MOVES the paragraph to the section containing K
     (inserts AFTER the scripture-box).
  4. Filters out false positives via a verse-count table (e.g. Rom 12 max
     verse = 21; paragraph starting "22 X" can't be v.22 of Rom 12).

Usage:
  python3 scripts/relocate_misplaced_verse_commentary.py \
    --book romans --book-cn 罗马书 \
    --dir calvin/romans
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path

# Max verse number per chapter for each bible book (CUV verse counts).
# Populated for books we OCR. Add more as needed.
VERSE_COUNTS = {
    '罗马书': {
        1: 32, 2: 29, 3: 31, 4: 25, 5: 21, 6: 23, 7: 25, 8: 39,
        9: 33, 10: 21, 11: 36, 12: 21, 13: 14, 14: 23, 15: 33, 16: 27,
    },
    # Add other books when applicable
}


def parse_sections(text: str, book_cn: str) -> list[dict]:
    """Return list of {start, end, header, lo, hi, chapter} dicts.

    start/end are line indices (inclusive start, exclusive end) into
    text.split('\n').
    """
    lines = text.split('\n')
    hdr_re = re.compile(
        rf'^## {re.escape(book_cn)} (\d+):(\d+)(?:-(\d+))?'
    )
    sections = []
    for i, ln in enumerate(lines):
        m = hdr_re.match(ln)
        if m:
            ch = int(m.group(1))
            lo = int(m.group(2))
            hi = int(m.group(3)) if m.group(3) else lo
            sections.append({
                'start': i,
                'end': len(lines),  # placeholder, set in next loop
                'header': ln,
                'chapter': ch,
                'lo': lo,
                'hi': hi,
            })
    # Set end as start of next section (or EOF)
    for j in range(len(sections) - 1):
        sections[j]['end'] = sections[j + 1]['start']
    return sections


def find_misplaced_paragraphs(
    lines: list[str], sec: dict, max_verse: int
) -> list[tuple[int, int, int]]:
    """Within section body, return [(verse_num, para_start_line, para_end_line)]
    for paragraphs whose opener verse number is OUT of section range.

    A paragraph is delimited by blank lines (or section boundaries).
    """
    out = []
    # Walk body line by line, group into paragraphs
    i = sec['start'] + 1  # skip header
    while i < sec['end']:
        # Skip blank lines and html anchors / scripture-box / fnref-stub
        if not lines[i].strip():
            i += 1
            continue
        if lines[i].lstrip().startswith(('<h2', '<div', '<a ', '</div>', '<p ', '[^', '{:.')):
            # Walk to end of this html-ish block (next blank line)
            while i < sec['end'] and lines[i].strip():
                i += 1
            continue
        # Found a body paragraph start. Find its end (next blank line).
        para_start = i
        while i < sec['end'] and lines[i].strip():
            i += 1
        para_end = i  # exclusive

        # Check opener
        first_line = lines[para_start]
        m = re.match(r'^(\d{1,3})[ 、.]\s*[一-鿿]', first_line)
        if not m:
            continue
        v = int(m.group(1))
        if v < 1 or v > max_verse:
            continue  # not a valid verse number for this chapter
        if sec['lo'] <= v <= sec['hi']:
            continue  # already in correct section
        out.append((v, para_start, para_end))
    return out


def process_chapter(path: Path, book_cn: str, verse_counts: dict) -> tuple[int, int]:
    """Returns (n_misplaced_found, n_moved)."""
    text = path.read_text(encoding='utf-8')
    lines = text.split('\n')
    sections = parse_sections(text, book_cn)
    if not sections:
        return 0, 0
    # All sections should share the same chapter number (per-file)
    chapter = sections[0]['chapter']
    max_verse = verse_counts.get(book_cn, {}).get(chapter, 999)

    # Step 1: find all misplaced paragraphs across all sections
    misplaced = []  # list of (target_section_idx, verse, source_lines)
    # Process sections in reverse order so line indices stay stable when we
    # remove paragraphs from later sections first.
    paragraphs_to_remove = []  # (start_line, end_line) inclusive/exclusive
    paragraphs_to_insert = {}  # section_idx -> list of (verse, paragraph_lines)
    for sec_idx, sec in enumerate(sections):
        items = find_misplaced_paragraphs(lines, sec, max_verse)
        for v, ps, pe in items:
            # Find target section containing v in this chapter
            target_idx = None
            for ti, tsec in enumerate(sections):
                if tsec['lo'] <= v <= tsec['hi']:
                    target_idx = ti
                    break
            if target_idx is None:
                continue  # no matching section — leave as is
            para_lines = lines[ps:pe]
            paragraphs_to_remove.append((ps, pe))
            paragraphs_to_insert.setdefault(target_idx, []).append((v, para_lines))

    if not paragraphs_to_remove:
        return 0, 0

    # Step 2: rebuild lines list. Remove misplaced (in reverse order so
    # indices stay valid), then insert into targets.
    # We need to track section boundaries through removals — use marker lines.
    # Simpler approach: rebuild by walking sections, dropping misplaced and
    # appending inserts at end of each target section's body (before next
    # section header).
    remove_set = set()
    for ps, pe in paragraphs_to_remove:
        for j in range(ps, pe):
            remove_set.add(j)

    # Determine insertion position for each target section: end of body
    # (just before next section header, or EOF). We insert at sec['end'].
    # But we need to map old line indices through removals — use a different
    # approach: collect (insert_after_old_index, paragraph_lines) entries
    # using the old end-of-section line index; then while emitting in order
    # we drop removed lines and emit insertions at the marker.

    insert_at_end_of_section = {}  # old_end_idx → list of [verse, lines]
    for target_idx, items in paragraphs_to_insert.items():
        end_idx = sections[target_idx]['end']
        insert_at_end_of_section.setdefault(end_idx, []).extend(items)

    out_lines = []
    for i, ln in enumerate(lines):
        if i in remove_set:
            continue
        out_lines.append(ln)
        if (i + 1) in insert_at_end_of_section:
            # Insertions happen just before the next section header (which is
            # at line i+1 in old indexing). The blank line preceding the
            # header is at line i.
            for v, para_lines in insert_at_end_of_section[i + 1]:
                # ensure blank line separator
                if out_lines and out_lines[-1].strip():
                    out_lines.append('')
                out_lines.extend(para_lines)
                out_lines.append('')

    # Tail insertions: if any insertions targeted the final section's end
    # (which == len(lines)), append at end
    if len(lines) in insert_at_end_of_section:
        for v, para_lines in insert_at_end_of_section[len(lines)]:
            if out_lines and out_lines[-1].strip():
                out_lines.append('')
            out_lines.extend(para_lines)
            out_lines.append('')

    new_text = '\n'.join(out_lines)
    # Collapse 3+ blank lines → 2
    new_text = re.sub(r'\n{3,}', '\n\n', new_text)
    path.write_text(new_text, encoding='utf-8')
    n_misplaced = len(paragraphs_to_remove)
    return n_misplaced, n_misplaced


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book-cn', required=True)
    ap.add_argument('--dir', required=True, help='e.g. calvin/romans')
    args = ap.parse_args()

    book_cn = args.book_cn
    dir_path = Path(args.dir).expanduser().resolve()
    if not dir_path.exists():
        raise SystemExit(f'dir not found: {dir_path}')

    if book_cn not in VERSE_COUNTS:
        print(f'⚠ no VERSE_COUNTS for {book_cn}; max_verse falls back to 999 (false positives may occur)')

    total_found = total_moved = 0
    for path in sorted(dir_path.glob('*.md')):
        if not path.stem.isdigit():
            continue
        found, moved = process_chapter(path, book_cn, VERSE_COUNTS)
        if found:
            print(f'  {path.name}: relocated {moved} paragraphs')
        total_found += found
        total_moved += moved
    print(f'\nTotal: relocated {total_moved} misplaced verse-commentary paragraphs across {dir_path}')


if __name__ == '__main__':
    main()
