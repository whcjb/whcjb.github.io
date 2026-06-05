#!/usr/bin/env python3
"""Extract footnote definitions from calvin_matai_make2.pdf page-bottom
blocks and append them as `<sup>N</sup>: text` lines to the corresponding
calvin/harmony-2-en/N.md chapter file.

PDF format: each page has footnote text at the bottom in small font
(size ≤ 9.5). Multiple footnotes concatenated, each starting with the
footnote number followed by space + content.

Chapter assignment: a footnote belongs to whichever chapter file
contains the `<sup>N</sup>` inline reference. We don't use kramdown
`[^N]: ` format because vol2 already uses `<sup>N</sup>` inline; for
visual continuity we emit the footnote list as HTML `<ol class="footnotes">`
at the bottom of each chapter."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import fitz

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
PDF = '/Users/yanpeifa/Documents/论文/calvin_matai_make2.pdf'
EN_DIR = ROOT / 'calvin/harmony-2-en'

FN_FONT_SIZE_MAX = 9.5     # any block with all spans <= this is footnote
FN_Y_MIN = 600             # only consider blocks below this y-position
FN_NUMBER_RE = re.compile(r'(?<!\d)(\d{1,4})\s+')


def page_footnote_text(page: fitz.Page) -> str:
    """Extract concatenated footnote-region text from a page, preserving order."""
    blocks = sorted(
        page.get_text('dict')['blocks'], key=lambda b: b['bbox'][1]
    )
    chunks: list[str] = []
    for b in blocks:
        if b['type'] != 0:
            continue
        if b['bbox'][1] < FN_Y_MIN:
            continue
        sizes: list[float] = []
        text_parts: list[str] = []
        for line in b.get('lines', []):
            for span in line.get('spans', []):
                if not span.get('text', '').strip():
                    continue
                sizes.append(span.get('size', 0))
                text_parts.append(span['text'])
        if not sizes or max(sizes) > FN_FONT_SIZE_MAX:
            continue
        chunks.append(' '.join(text_parts).strip())
    return ' '.join(chunks)


def parse_footnotes(text: str) -> list[tuple[int, str]]:
    """Split concatenated footnote text into (number, definition) pairs.
    Each footnote starts with the number, separated from the next by the
    NEXT footnote's number."""
    if not text.strip():
        return []
    # Walk through, finding monotonically increasing numbers
    out: list[tuple[int, str]] = []
    last_n = 0
    # Split positions: where a digit at start of word is BOTH > last_n
    # AND <= last_n + some tolerance
    positions: list[tuple[int, int]] = []  # (start_pos, number)
    for m in FN_NUMBER_RE.finditer(text):
        n = int(m.group(1))
        # Accept if n == last_n + 1 (strict sequential)
        if n == last_n + 1:
            positions.append((m.start(), n))
            last_n = n
    # Build defs from positions
    for i, (start, n) in enumerate(positions):
        # The number itself ends at the matched group end; content starts after
        m = FN_NUMBER_RE.match(text[start:])
        content_start = start + (m.end() if m else 0)
        if i + 1 < len(positions):
            content_end = positions[i + 1][0]
        else:
            content_end = len(text)
        content = text[content_start:content_end].strip()
        out.append((n, content))
    return out


def extract_all_footnotes(pdf_path: str) -> list[tuple[int, str]]:
    """Walk all pages; capture page-bottom footnote blocks per page, split
    each block at footnote-number markers, and merge across pages.

    A footnote-number marker is a 1-4 digit number whose font size is
    smaller than the surrounding text (superscript). We collect them
    span-by-span to detect size precisely instead of relying on text
    pattern matching."""
    doc = fitz.open(pdf_path)
    all_defs: dict[int, str] = {}
    for p in range(len(doc)):
        page = doc[p]
        defs = parse_page_footnotes(page)
        for n, content in defs:
            # Skip if number already seen (page-bottom blocks rarely
            # repeat — but if a footnote spans across pages, accumulate).
            if n in all_defs:
                all_defs[n] += ' ' + content
            else:
                all_defs[n] = content
    doc.close()
    return sorted(all_defs.items())


def parse_page_footnotes(page: fitz.Page) -> list[tuple[int, str]]:
    """Per-page parser: find page-bottom footnote blocks; within each block,
    split into footnotes by detecting superscript number markers (smaller
    font than surrounding text)."""
    blocks = sorted(
        page.get_text('dict')['blocks'], key=lambda b: b['bbox'][1]
    )
    out: list[tuple[int, str]] = []
    for b in blocks:
        if b['type'] != 0 or b['bbox'][1] < FN_Y_MIN:
            continue
        # Collect spans and their sizes
        spans_data: list[tuple[float, str]] = []  # (size, text)
        for line in b.get('lines', []):
            for span in line.get('spans', []):
                if not span.get('text', '').strip():
                    continue
                size = span.get('size', 0)
                spans_data.append((size, span['text']))
        if not spans_data:
            continue
        # Block-level filter: all spans must be small (≤ 9.5)
        if max(s for s, _ in spans_data) > FN_FONT_SIZE_MAX:
            continue
        # Detect footnote-number markers: smaller-font digit at start of
        # a new footnote. The marker is the SMALLEST size in the block.
        sizes = [s for s, _ in spans_data]
        min_size = min(sizes)
        # If all spans same size, fall back to text-pattern split
        if min_size == max(sizes):
            out.extend(_split_by_text_pattern(' '.join(t for _, t in spans_data)))
            continue
        # Marker spans: those whose size is at the minimum AND text is digits
        current_n: int | None = None
        current_text: list[str] = []
        for size, text in spans_data:
            if size == min_size and text.strip().isdigit():
                if current_n is not None:
                    out.append((current_n, ' '.join(current_text).strip()))
                current_n = int(text.strip())
                current_text = []
            else:
                current_text.append(text)
        if current_n is not None:
            out.append((current_n, ' '.join(current_text).strip()))
    # Clean: strip trailing page-numbers and empty
    cleaned: list[tuple[int, str]] = []
    for n, content in out:
        content = re.sub(r'\s+\d{1,4}\s*$', '', content).strip()
        if content:
            cleaned.append((n, content))
    return cleaned


def _split_by_text_pattern(text: str) -> list[tuple[int, str]]:
    """Fallback: split a uniform-size footnote block by looking for digit
    starts. Less reliable than size-based splitting."""
    parts: list[tuple[int, int]] = []
    for m in re.finditer(r'(?:^|\s)(\d{1,4})\s+(?=[“"\'\w])', text):
        parts.append((m.start(1), int(m.group(1))))
    out: list[tuple[int, str]] = []
    for i, (pos, n) in enumerate(parts):
        m = re.match(r'\d+\s+', text[pos:])
        cs = pos + (m.end() if m else 0)
        ce = parts[i + 1][0] if i + 1 < len(parts) else len(text)
        out.append((n, text[cs:ce].strip()))
    return out


def chapter_for_footnote(n: int, en_chapter_files: dict[int, str]) -> int | None:
    """Find which chapter file contains a `<sup>N</sup>` ref (raw or
    link-wrapped). If multiple chapters contain it, return the one with
    the most occurrences (the primary commentary location)."""
    counts: dict[int, int] = {}
    patterns = [f'<sup>{n}</sup>', f'<sup><a href="#fn:{n}">{n}</a></sup>']
    for ch, text in en_chapter_files.items():
        c = sum(text.count(p) for p in patterns)
        if c > 0:
            counts[ch] = c
    if not counts:
        return None
    # Return chapter with most occurrences
    return max(counts.items(), key=lambda x: x[1])[0]


def build_chapter_ranges(en_chapter_files: dict[int, str]) -> dict[int, tuple[int, int]]:
    """For each chapter, find min and max footnote numbers — matches both
    raw `<sup>N</sup>` and link-wrapped `<sup><a href="#fn:N">N</a></sup>`."""
    ranges: dict[int, tuple[int, int]] = {}
    pat = re.compile(r'<sup>(?:<a[^>]*>)?(\d+)(?:</a>)?</sup>')
    for ch, text in en_chapter_files.items():
        nums = [int(m.group(1)) for m in pat.finditer(text)]
        if nums:
            ranges[ch] = (min(nums), max(nums))
    return ranges


def chapter_for_unassigned_fn(n: int,
                                ranges: dict[int, tuple[int, int]],
                                all_defs_count: int) -> int | None:
    """Assign fn N to the chapter whose range contains it. If multiple
    chapters' ranges contain N (overlapping ranges from stray refs),
    prefer the chapter with the TIGHTEST range (more specific). If no
    range contains N, pick the closest chapter by distance to range."""
    candidates = [(ch, lo, hi) for ch, (lo, hi) in ranges.items() if lo <= n <= hi]
    if candidates:
        # Prefer smallest range (most specific)
        candidates.sort(key=lambda x: x[2] - x[1])
        return candidates[0][0]
    # Fallback: chapter whose range is closest to N
    best_ch = None
    best_dist = float('inf')
    for ch, (lo, hi) in ranges.items():
        if n < lo:
            dist = lo - n
        else:
            dist = n - hi
        if dist < best_dist:
            best_dist = dist
            best_ch = ch
    return best_ch


def append_footnotes_to_chapter(ch: int, defs: list[tuple[int, str]]) -> int:
    """Append a footnotes section to calvin/harmony-2-en/{ch}.md.

    Also wraps `<sup>N</sup>` inline refs into `<sup><a href="#fn:N">N</a></sup>`
    so users can click to jump.
    """
    path = EN_DIR / f'{ch}.md'
    text = path.read_text(encoding='utf-8')
    # Strip any prior footnote block we added
    text = re.sub(
        r'\n+<hr class="footnotes-sep">\n<ol class="footnotes">.*?</ol>\n*$',
        '\n',
        text, flags=re.DOTALL,
    )
    if not defs:
        path.write_text(text, encoding='utf-8')
        return 0

    # Wrap inline <sup>N</sup> refs as clickable links to the footnote def
    def_nums = {n for n, _ in defs}

    def link_sup(m: re.Match) -> str:
        n = int(m.group(1))
        if n in def_nums:
            return f'<sup><a href="#fn:{n}">{n}</a></sup>'
        return m.group(0)
    text = re.sub(r'<sup>(\d+)</sup>', link_sup, text)

    items = '\n'.join(
        f'  <li id="fn:{n}"><span class="fn-backref-num">{n}</span> {content}</li>'
        for n, content in sorted(defs)
    )
    block = (
        '\n<hr class="footnotes-sep">\n'
        '<ol class="footnotes">\n'
        f'{items}\n'
        '</ol>\n'
    )
    text = text.rstrip() + '\n' + block
    path.write_text(text, encoding='utf-8')
    return len(defs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    print(f'Extracting footnotes from {PDF}...')
    all_defs = extract_all_footnotes(PDF)
    print(f'Found {len(all_defs)} footnote definitions')

    # Load all en chapter texts
    en_chapter_files: dict[int, str] = {}
    for path in sorted(EN_DIR.glob('*.md')):
        if path.stem.isdigit():
            en_chapter_files[int(path.stem)] = path.read_text(encoding='utf-8')

    ranges = build_chapter_ranges(en_chapter_files)

    # Group defs by chapter: prefer DIRECT `<sup>N</sup>` ref match (most
    # accurate — the fn def goes to whichever chapter's commentary uses
    # it). Fall back to range-based when no ref found in any chapter.
    by_chapter: dict[int, list[tuple[int, str]]] = {}
    unassigned: list[tuple[int, str]] = []
    for n, content in all_defs:
        ch = chapter_for_footnote(n, en_chapter_files)
        if ch is None:
            ch = chapter_for_unassigned_fn(n, ranges, len(all_defs))
        if ch is None:
            unassigned.append((n, content))
        else:
            by_chapter.setdefault(ch, []).append((n, content))

    print(f'\nFootnotes by chapter:')
    for ch in sorted(by_chapter):
        print(f'  ch{ch}: {len(by_chapter[ch])} fns (range {by_chapter[ch][0][0]}–{by_chapter[ch][-1][0]})')
    if unassigned:
        print(f'  unassigned: {len(unassigned)} (no <sup>N</sup> ref found)')
        for n, c in unassigned[:5]:
            print(f'    fn {n}: {c[:80]}...')

    if args.dry_run:
        return

    for ch, defs in by_chapter.items():
        n = append_footnotes_to_chapter(ch, defs)
        print(f'  appended {n} fns to ch{ch}.md')


if __name__ == '__main__':
    main()
