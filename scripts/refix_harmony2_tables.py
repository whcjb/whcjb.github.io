#!/usr/bin/env python3
"""Re-process harmony2 raw multi-row tables into clean single-row scripture
tables + extracted commentary paragraphs. Replaces sections in
calvin/harmony-2-en/N.md in-place.

Strategy (Plan B):
  1. Parse `## SECTION HEADER` to get verse ranges per gospel column.
  2. For each `<tbody>` row, classify cells as Bible vs Commentary by:
     - verse-prefix-in-range + content-length-per-prefix heuristic
     - cells already-seen-in-Bible are treated as commentary
  3. Concatenate per-column Bible cells → single-row scripture-table.
  4. Emit Commentary cells as `**Book N:V.** *opener.* rest` paragraphs,
     keyed by the verse number the commentary opens with.

This does NOT attempt to repair column-mix inside Bible cells (e.g.
"and 23. And he swore" leaked from Mark 6:23 into Matt 14:11). That
needs PDF-level re-extraction.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import NamedTuple

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
RAW_FILE = ROOT / 'calvin_raw/harmony2/harmony2_raw.txt'
EN_DIR = ROOT / 'calvin/harmony-2-en'

GOSPEL_RE = re.compile(
    r'(MATTHEW|MARK|LUKE|JOHN)\s+(\d+):(\d+)(?:[\-,\s]+(\d+))?',
    re.I,
)
GOSPEL_DISPLAY = {
    'MATTHEW': 'Matthew', 'MARK': 'Mark', 'LUKE': 'Luke', 'JOHN': 'John',
}

VERSE_PREFIX_RE = re.compile(r'(?<!\d)(\d{1,2})\.\s+')


class ColSpec(NamedTuple):
    book: str       # 'Matthew'
    chapter: int    # 14
    verses: set[int]  # {3,4,5,6,7,8,9,10,11,12}


def parse_header_cols(header: str) -> list[ColSpec]:
    """Parse `## MATTHEW 14:3-12; MARK 6:17-29` into ColSpec list.

    Multiple verse refs separated by ',' or ';' for the same gospel are
    merged into the SAME column. New gospel = new column.
    """
    s = re.sub(r'^##\s*', '', header).strip()
    parts = re.split(r'\s*;\s*', s)
    cols: list[ColSpec] = []
    last_book: str | None = None
    for part in parts:
        m = re.match(r'(MATTHEW|MARK|LUKE|JOHN)\s+(\d+):(.+)$', part.strip(), re.I)
        if m:
            last_book = GOSPEL_DISPLAY[m.group(1).upper()]
            chapter = int(m.group(2))
            verse_spec = m.group(3)
            cols.append(ColSpec(last_book, chapter, _expand_verse_spec(verse_spec)))
        else:
            # Continuation of last gospel, e.g. "MARK 9:49-50; 4:21"
            m2 = re.match(r'(\d+):(.+)$', part.strip())
            if m2 and last_book is not None:
                chapter = int(m2.group(1))
                verses = _expand_verse_spec(m2.group(2))
                # merge into last col (assume same chapter for simplicity)
                merged = cols[-1].verses | verses
                cols[-1] = ColSpec(last_book, cols[-1].chapter, merged)
    return cols


def _expand_verse_spec(spec: str) -> set[int]:
    """`3-12` → {3..12}; `1, 7-9, 12` → {1,7,8,9,12}."""
    out: set[int] = set()
    for chunk in re.split(r'\s*,\s*', spec):
        chunk = chunk.strip()
        m = re.match(r'(\d+)\s*[-–]\s*(\d+)$', chunk)
        if m:
            out.update(range(int(m.group(1)), int(m.group(2)) + 1))
        elif chunk.isdigit():
            out.add(int(chunk))
    return out


def parse_rows(tbody_html: str) -> list[list[tuple[int, str]]]:
    """Parse `<tbody>...` into list of rows; each row is list of (colspan, content)."""
    rows: list[list[tuple[int, str]]] = []
    for tr_m in re.finditer(r'<tr[^>]*>(.*?)</tr>', tbody_html, re.DOTALL):
        row: list[tuple[int, str]] = []
        for td_m in re.finditer(
            r'<td(?:\s+colspan="(\d+)")?[^>]*>(.*?)</td>',
            tr_m.group(1), re.DOTALL,
        ):
            cs = int(td_m.group(1)) if td_m.group(1) else 1
            content = re.sub(r'\s+', ' ', td_m.group(2)).strip()
            row.append((cs, content))
        if row:
            rows.append(row)
    return rows


def _verse_prefixes_in(text: str) -> list[tuple[int, int]]:
    """Return [(position, verse_number), ...] sorted by position."""
    return [(m.start(), int(m.group(1))) for m in VERSE_PREFIX_RE.finditer(text)]


def _bible_endpos(text: str, allowed_verses: set[int],
                    seen_verses: set[int]) -> int:
    """Return the index AFTER the Bible portion of `text`.

    Algorithm:
      1. Find all `\\d+\\. ` verse-prefix positions.
      2. Walk through; record the LAST in-range, not-yet-seen prefix.
         Out-of-range or repeat prefixes are SKIPPED (treated as column
         leaks — Bible continues past them).
      3. Bible ends at the next non-bible prefix AFTER the last in-range
         one, OR (if no more prefixes) at the first `. ` followed by a
         capital letter (commentary sentence opener).
    """
    prefixes = _verse_prefixes_in(text)
    if not prefixes:
        return 0
    # Find last in-range, not-yet-seen prefix and update seen
    last_in_range_pos = -1
    found_indices: list[int] = []
    for i, (pos, n) in enumerate(prefixes):
        if n in allowed_verses and n not in seen_verses:
            last_in_range_pos = pos
            found_indices.append(i)
            seen_verses.add(n)
    if last_in_range_pos < 0:
        return 0
    # Find first sentence-break after the last in-range verse's prefix
    # that is followed by capital letter (start of new sentence). If the
    # next character is a digit (like "15. 16. The Law"), keep going — the
    # next verse-prefix is a continuation marker, not commentary, but
    # we still want to stop at the start of the NEXT prefix.
    prefix_m = re.match(r'\d+\.\s+', text[last_in_range_pos:])
    chunk_start = last_in_range_pos + (prefix_m.end() if prefix_m else 0)
    chunk = text[chunk_start:]
    # Match `. ` followed by either:
    #   - a capital letter (sentence start of commentary), OR
    #   - a digit followed by `.` (next verse-prefix that's a real boundary
    #     — but only if not preceded by `:` which indicates a citation
    #     like "Luke 8:12.")
    m = re.search(
        r'\.\s+(?=[A-Z“"\']|\d+\.\s)',
        chunk,
    )
    if m:
        return chunk_start + m.start() + 1
    # No sentence break found within the cell text → Bible runs to end
    return len(text)


def cell_is_pure_commentary(text: str, col_spec: ColSpec,
                              seen_verses: set[int]) -> bool:
    """A cell is pure commentary if it starts with `N. ` AND has only one
    in-range, not-yet-seen verse prefix AND is long (>800 chars).

    A cell that has SEVERAL distinct in-range verse-prefixes is more likely a
    Bible cell (possibly with commentary tail) — process normally."""
    if len(text) < 800:
        return False
    if not VERSE_PREFIX_RE.match(text):
        return False
    prefixes = _verse_prefixes_in(text)
    new_in_range = [
        n for _, n in prefixes
        if n in col_spec.verses and n not in seen_verses
    ]
    # Heuristic: >=2 new in-range verses → it's a multi-verse Bible passage
    # (with possible commentary tail). 0-1 new verses + long cell → commentary.
    return len(new_in_range) <= 1


def classify_cell(text: str, col_spec: ColSpec,
                    seen_verses: set[int]) -> tuple[str, str, str, int]:
    """Classify a single cell.

    Returns (bible_part, commentary_part, opener_verse_kind, opener_verse_num):
      - bible_part: portion of `text` that is Bible verses
      - commentary_part: remainder (possibly empty)
      - opener_verse_kind: which book the commentary opens (this col's book by
        default; could be different if verse number doesn't fit this col)
      - opener_verse_num: verse number commentary opens with (0 if none)
    """
    if cell_is_pure_commentary(text, col_spec, seen_verses):
        return '', text.strip(), col_spec.book, 0
    end = _bible_endpos(text, col_spec.verses, seen_verses)
    bible = text[:end].strip()
    comm = text[end:].strip()
    opener_num = 0
    opener_book = col_spec.book
    if comm:
        m = VERSE_PREFIX_RE.match(comm)
        if m:
            opener_num = int(m.group(1))
            # if opener verse not in this col's range, it might be the OTHER col
            if opener_num not in col_spec.verses:
                opener_book = ''  # caller resolves
    return bible, comm, opener_book, opener_num


def _emit_commentary_para(book: str, chapter: int, text: str) -> str:
    """Format a commentary chunk as `**Book Ch:V.** *opener.* rest`."""
    text = text.strip()
    m = VERSE_PREFIX_RE.match(text)
    if not m:
        # No verse marker at start — emit as plain paragraph (no header)
        return text
    verse = int(m.group(1))
    rest = text[m.end():]
    # opener = up to first `.` (sentence end)
    sm = re.match(r'(.+?\.)\s+(.*)$', rest, re.DOTALL)
    if sm:
        opener = sm.group(1).strip()
        body = sm.group(2).strip()
        return f'**{book} {chapter}:{verse}.** *{opener}* {body}'
    return f'**{book} {chapter}:{verse}.** {rest}'


def _resolve_commentary_book(verse_num: int, cols: list[ColSpec]) -> ColSpec | None:
    """Find which gospel column's verse range contains `verse_num`."""
    for col in cols:
        if verse_num in col.verses:
            return col
    return None


def process_section_box_only(header: str, table_html: str) -> str:
    """Return ONLY the cleaned `<div class="scripture-box ...">...</div>`
    block; commentary paragraphs from existing en file are kept in place."""
    body = process_section(header, table_html)
    # Strip the header + commentary; keep only the scripture-box
    m = re.search(r'<div class="scripture-box[^"]*">.*?</div>', body, re.DOTALL)
    return m.group(0) if m else ''


def process_section(header: str, table_html: str) -> str:
    """Convert a `## MATTHEW X:Y; ...` + raw multi-row table into a clean
    scripture-box + commentary paragraphs block."""
    cols = parse_header_cols(header)
    if not cols:
        return f'{header}\n\n{table_html}'

    tbody_m = re.search(r'<tbody[^>]*>(.*?)</tbody>', table_html, re.DOTALL)
    if not tbody_m:
        return f'{header}\n\n{table_html}'

    rows = parse_rows(tbody_m.group(1))
    n_cols = len(cols)

    # Per-column Bible accumulator + commentary list
    bible_per_col: list[list[str]] = [[] for _ in range(n_cols)]
    seen_per_col: list[set[int]] = [set() for _ in range(n_cols)]
    commentary: list[str] = []

    for row in rows:
        # Compute total colspan to map cells to column slots
        if len(row) == 1 and row[0][0] >= 2:
            # full-width row → classify by verse number
            _, content = row[0]
            # detect Bible vs commentary by checking if opener verse is unseen+in-range
            m = VERSE_PREFIX_RE.match(content)
            if m:
                opener_num = int(m.group(1))
                # find which col this verse belongs to
                target_col = _resolve_commentary_book(opener_num, cols)
                if target_col is not None and opener_num not in seen_per_col[cols.index(target_col)]:
                    # Bible continuation (unseen verse in some col)
                    ci = cols.index(target_col)
                    bible, comm, _, _ = classify_cell(content, target_col, seen_per_col[ci])
                    if bible:
                        bible_per_col[ci].append(bible)
                    if comm:
                        # rest is commentary on the same book
                        para = _emit_commentary_para(target_col.book, target_col.chapter, comm)
                        commentary.append(para)
                else:
                    # Pure commentary — figure out which book
                    if target_col is None:
                        # verse not in any range — fallback to first col's book
                        target_col = cols[0]
                    para = _emit_commentary_para(target_col.book, target_col.chapter, content)
                    commentary.append(para)
            else:
                # No verse marker — just append as plain commentary
                commentary.append(content)
        else:
            # parallel row → cells map to col slots positionally (accounting for colspans)
            ci = 0
            for cs, content in row:
                if ci >= n_cols:
                    break
                col_spec = cols[ci]
                bible, comm, _, _ = classify_cell(content, col_spec, seen_per_col[ci])
                if bible:
                    bible_per_col[ci].append(bible)
                if comm:
                    # commentary in this col: opener verse decides book
                    m = VERSE_PREFIX_RE.match(comm)
                    if m:
                        opener_num = int(m.group(1))
                        target = _resolve_commentary_book(opener_num, cols) or col_spec
                    else:
                        target = col_spec
                    para = _emit_commentary_para(target.book, target.chapter, comm)
                    commentary.append(para)
                ci += cs  # advance by colspan

    # Build the scripture-box
    display_ref = '; '.join(
        f'{c.book} {c.chapter}:{_format_verse_range(c.verses)}' for c in cols
    )
    thead = ''.join(
        f'<th>{c.book} {c.chapter}:{_format_verse_range(c.verses)}</th>' for c in cols
    )
    tds: list[str] = []
    for ci, col_spec in enumerate(cols):
        joined = ' '.join(bible_per_col[ci]).strip()
        tds.append(f'<td><p>{joined}</p></td>')

    box = (
        '<div class="scripture-box scripture-box--multi">\n'
        f'<p class="scripture-ref">{display_ref}</p>\n'
        '<table class="scripture-table">\n'
        f'<thead><tr>{thead}</tr></thead>\n'
        f'<tbody><tr>{"".join(tds)}</tr></tbody>\n'
        '</table>\n'
        '</div>'
    )
    return f'{header}\n\n{box}\n\n' + '\n\n'.join(commentary)


def _format_verse_range(verses: set[int]) -> str:
    """{3,4,5,6,7,8,9,10,11,12} → '3-12'; {1,7,8,9,12} → '1, 7-9, 12'."""
    if not verses:
        return ''
    sorted_v = sorted(verses)
    chunks: list[str] = []
    i = 0
    while i < len(sorted_v):
        start = sorted_v[i]
        end = start
        while i + 1 < len(sorted_v) and sorted_v[i + 1] == end + 1:
            end = sorted_v[i + 1]
            i += 1
        chunks.append(f'{start}-{end}' if end > start else f'{start}')
        i += 1
    return ', '.join(chunks)


def collect_raw_sections() -> list[tuple[str, str]]:
    """Return [(header, full table HTML), ...] from raw file."""
    raw = RAW_FILE.read_text(encoding='utf-8')
    blocks = re.split(r'\n{2,}', raw)
    sections: list[tuple[str, str]] = []
    pending_header: str | None = None
    for blk in blocks:
        s = blk.strip()
        if s.startswith('## ') and re.search(r'(MATTHEW|MARK|LUKE|JOHN)', s, re.I):
            pending_header = s
        elif s.startswith('<table class="calvin-scripture">') and pending_header:
            sections.append((pending_header, s))
            pending_header = None
    return sections


def patch_chapter(ch: int, section_blocks: list[tuple[str, str]]) -> int:
    """In each section of calvin/harmony-2-en/{ch}.md:
      - Replace the `<div class="scripture-box ...">...</div>` with the
        cleaned single-row Bible version.
      - If the en file has NO commentary paragraphs between `</div>` and
        the next `##` header (i.e. the section's commentary got swallowed
        into the original merged table), inject the commentary extracted
        from the raw multi-row table at that gap."""
    path = EN_DIR / f'{ch}.md'
    if not path.exists():
        print(f'skip ch{ch}: no file')
        return 0
    text = path.read_text(encoding='utf-8')

    patched = 0
    for header, raw_table in section_blocks:
        h_pat = re.escape(header)
        m_hdr = re.search(h_pat + r'\n', text)
        if not m_hdr:
            print(f'  ch{ch}: header NOT found in en file: {header[:60]}')
            continue
        m_div = re.search(
            r'<div class="scripture-box[^"]*">.*?</div>',
            text[m_hdr.end():], re.DOTALL,
        )
        if not m_div:
            print(f'  ch{ch}: scripture-box not found after {header[:50]}')
            continue
        div_start = m_hdr.end() + m_div.start()
        div_end = m_hdr.end() + m_div.end()

        clean_box = process_section_box_only(header, raw_table)
        if not clean_box:
            print(f'  ch{ch}: failed to generate clean box for {header[:50]}')
            continue

        # Determine if this section is missing commentary paragraphs.
        # Find end of section: next `\n## ` header or end of text.
        next_hdr_m = re.search(r'\n##\s+[A-Z]', text[div_end:])
        section_end = div_end + next_hdr_m.start() if next_hdr_m else len(text)
        after_div = text[div_end:section_end]
        existing_commentary_count = len(re.findall(
            r'^\*\*(Matthew|Mark|Luke|John)\s+\d+:\d+\.\*\*', after_div, re.M,
        ))

        if existing_commentary_count == 0:
            # Section commentary was swallowed — extract from raw and inject
            full_block = process_section(header, raw_table)
            # `process_section` returns: header + box + commentary paragraphs
            # Extract just the commentary portion (after the </div>)
            m_box_in_block = re.search(
                r'</div>\s*\n\n(.*)$', full_block, re.DOTALL,
            )
            commentary_text = m_box_in_block.group(1).rstrip() if m_box_in_block else ''
            if commentary_text:
                # Insert: clean_box + \n\n + commentary + then existing after
                replacement = clean_box + '\n\n' + commentary_text + '\n'
                text = text[:div_start] + replacement + text[div_end:]
            else:
                text = text[:div_start] + clean_box + text[div_end:]
        else:
            text = text[:div_start] + clean_box + text[div_end:]
        patched += 1

    path.write_text(text, encoding='utf-8')
    return patched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chapter', type=int, default=None,
                    help='Process only this chapter; default: all')
    ap.add_argument('--dry-run', action='store_true',
                    help='Print what would change without writing')
    args = ap.parse_args()

    sections = collect_raw_sections()
    print(f'Found {len(sections)} sections in raw')

    # Group sections by chapter (Matt chapter from header). Sections without
    # an explicit Matt reference inherit the most recently seen Matt chapter
    # from the surrounding sections in raw order — that's how Calvin's harmony
    # is organized: Luke-only sections appear interleaved with Matt chapters.
    by_chapter: dict[int, list[tuple[str, str]]] = {}
    current_matt_ch: int | None = None
    for header, table in sections:
        cols = parse_header_cols(header)
        if not cols:
            continue
        matt_col = next((c for c in cols if c.book == 'Matthew'), None)
        if matt_col is not None:
            current_matt_ch = matt_col.chapter
        ch = current_matt_ch if current_matt_ch is not None else cols[0].chapter
        by_chapter.setdefault(ch, []).append((header, table))

    # ch14 has already been manually repaired (column-mix cleaned via PDF
    # reference); skip to preserve those hand-edits unless explicitly asked.
    skip_chapters = {14} if args.chapter is None else set()
    chapters_to_do = [args.chapter] if args.chapter else sorted(by_chapter)
    for ch in chapters_to_do:
        if ch in skip_chapters:
            print(f'ch{ch}: SKIP (already hand-repaired)')
            continue
        if ch not in by_chapter:
            continue
        if args.dry_run:
            print(f'\nch{ch}: {len(by_chapter[ch])} sections')
            for hdr, tbl in by_chapter[ch][:2]:
                print(f'  {hdr}')
                out = process_section(hdr, tbl)
                print('  ' + out[:300].replace('\n', ' '))
                print('  ...')
        else:
            n = patch_chapter(ch, by_chapter[ch])
            print(f'ch{ch}: patched {n} sections')


if __name__ == '__main__':
    main()
