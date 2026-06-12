#!/usr/bin/env python3
"""Replace scripture-box cell content in 共观福音 ZH harmony chapters with
中文和合本 (CUV) verses. Preserve all footnote refs (<sup id="fnref:N">)
from Calvin's original quotation by appending them to the verse where
they appeared.

Layout per cell:
  <th>马太福音 21:10-22</th>             ← header determines book + chapter ranges
  <td><p>
    <strong>10.</strong> ...calvin's translated text... <sup id="fnref:1">1</sup> ...
    <strong>11.</strong> ...
  </p></td>

Process:
  1. Parse header → ordered list of (book, ch, verse) expected in this cell.
     E.g., "马可福音 9:49-50; 4:21" → [(mk,9,49), (mk,9,50), (mk,4,21)]
  2. Split cell body by <strong>N.</strong> markers → ordered (N, chunk) pairs
  3. Map each pair to expected (book,ch,verse) positionally
  4. Extract sup tags from chunk → footnote list
  5. New chunk = CUV verse text + concatenated sup tags
  6. Rebuild <p> as: <strong>N.</strong> {cuv_text} {sups} ... joined

Usage:
  python3 scripts/replace_harmony_cuv.py harmony-3            # all 9 chapters
  python3 scripts/replace_harmony_cuv.py harmony-3 --chapter 1
  python3 scripts/replace_harmony_cuv.py all                  # all 3 vols
  python3 scripts/replace_harmony_cuv.py all --dry-run        # preview
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
CUV_PATH = ROOT / 'assets' / 'cuv.json'

# Bible book ID in CUV JSON (per 联合圣经公会编号)
BOOK_ID = {
    '马太福音': '40', '马可福音': '41', '路加福音': '42', '约翰福音': '43',
    'matthew': '40', 'mark': '41', 'luke': '42', 'john': '43',
}

# Load CUV once
_CUV = json.load(CUV_PATH.open(encoding='utf-8'))


def cuv_verse(book_zh, chapter, verse):
    """Return CUV text for (book, chapter, verse) or None if missing."""
    book_id = BOOK_ID.get(book_zh)
    if not book_id or book_id not in _CUV:
        return None
    ch_dict = _CUV[book_id].get(str(chapter))
    if not ch_dict:
        return None
    return ch_dict.get(str(verse))


def parse_header(th_text):
    """Parse <th> text → ordered list of (book_zh, chapter, verse) tuples.

    Examples:
      "马太福音 21:10-22"           → [('马太福音',21,10), ..., ('马太福音',21,22)]
      "马可福音 9:49-50; 4:21"     → [('马可福音',9,49), ('马可福音',9,50),
                                       ('马可福音',4,21)]
      "路加福音 11:43, 45-46; 20:45-46"
         → [('路加福音',11,43), ('路加福音',11,45), ('路加福音',11,46),
            ('路加福音',20,45), ('路加福音',20,46)]
    """
    s = th_text.strip()
    # Find book prefix
    m = re.match(r'^(马太福音|马可福音|路加福音|约翰福音)\s+(.+)$', s)
    if not m:
        return []
    book = m.group(1)
    rest = m.group(2)
    out = []
    last_chap = None
    # Split by `;` or `；` to get sub-ranges
    for part in re.split(r'\s*[;；]\s*', rest):
        part = part.strip()
        # New chapter? "Ch:V" or "Ch:V-W" or "Ch:V, X" or "Ch:V, X-Y"
        m2 = re.match(r'^(\d+):(.+)$', part)
        if m2:
            chap = int(m2.group(1))
            spec = m2.group(2)
            last_chap = chap
        else:
            # Continuation of last chapter (e.g., "Ch:V-W; X-Y")
            if last_chap is None:
                continue
            chap = last_chap
            spec = part
        # spec is like "10-22" or "1, 7-9, 12"
        for chunk in re.split(r'\s*,\s*', spec):
            chunk = chunk.strip()
            m3 = re.match(r'^(\d+)\s*[-–]\s*(\d+)$', chunk)
            if m3:
                lo, hi = int(m3.group(1)), int(m3.group(2))
                for v in range(lo, hi + 1):
                    out.append((book, chap, v))
            elif chunk.isdigit():
                out.append((book, chap, int(chunk)))
    return out


def split_verses(cell_html):
    """Split cell HTML by <strong>N.</strong> markers.

    Returns list of (verse_num, chunk_html) pairs. Chunk includes everything
    AFTER the <strong>N.</strong> marker until the next marker.

    Leading text before first verse marker is returned as (None, lead_text).
    """
    parts = re.split(r'<strong>(\d+)\.</strong>', cell_html)
    # parts[0] = lead text before any verse marker
    # then alternating: verse_num, chunk_text, verse_num, chunk_text, ...
    out = []
    lead = parts[0].strip()
    if lead:
        out.append((None, lead))
    for i in range(1, len(parts), 2):
        v = int(parts[i])
        chunk = parts[i + 1] if i + 1 < len(parts) else ''
        out.append((v, chunk))
    return out


SUP_RE = re.compile(r'<sup\s+id="fnref:\d+"[^>]*>.*?</sup>')


def extract_sups(chunk_html):
    """Return list of <sup>...</sup> strings preserving order."""
    return SUP_RE.findall(chunk_html)


def rebuild_cell(th_text, cell_html, missing_log):
    """Return new cell HTML, with CUV verses replacing Calvin's translation
    but [^N] footnotes preserved (appended to each verse).

    Strategy: match each `**N.**` marker in cell to the FIRST not-yet-consumed
    (book, ch, v) tuple in expected sequence where v == N. This handles
    skipped verses (e.g. Luke 19:39, 40, 45, ...) and multi-chapter
    columns (e.g. Luke 11:43, 45-46; 20:45-46) correctly.
    """
    expected = parse_header(th_text)
    pairs = split_verses(cell_html)
    verse_pairs = [(v, c) for v, c in pairs if v is not None]

    consumed = [False] * len(expected)
    out_chunks = []
    for v_label, chunk in verse_pairs:
        # Find first un-consumed (book, ch, v) where v == v_label
        target = None
        for i, (book, ch, v) in enumerate(expected):
            if not consumed[i] and v == v_label:
                consumed[i] = True
                target = (book, ch, v)
                break
        sups = extract_sups(chunk)
        if target is None:
            # No match in expected — verse outside header range or already used
            new_text = chunk.strip()
        else:
            book, ch, vnum = target
            cuv = cuv_verse(book, ch, vnum)
            if not cuv:  # None OR empty string (CUV merges some verses)
                missing_log.append(f'{book} {ch}:{vnum}')
                # Keep Calvin's original chunk (still has its sups inline)
                new_text = chunk.strip()
            else:
                new_text = cuv
                if sups:
                    new_text += ' ' + ' '.join(sups)
        out_chunks.append(f'<strong>{v_label}.</strong> {new_text}')
    return ' '.join(out_chunks)


# Match the entire scripture-table tbody row, capturing each <th> + cell
TABLE_RE = re.compile(
    r'<table class="scripture-table">\s*'
    r'<thead><tr>(?P<thead>.*?)</tr></thead>\s*'
    r'<tbody><tr>(?P<tbody>.*?)</tr></tbody>',
    re.DOTALL,
)
TH_RE = re.compile(r'<th>([^<]+)</th>')
TD_RE = re.compile(r'<td><p>(.*?)</p></td>', re.DOTALL)

# Single-column scripture-box pattern (no <table>, just one <p class="scripture-ref"> + one <p> with verses)
SINGLE_BOX_RE = re.compile(
    r'(<div class="scripture-box">\s*'
    r'<p class="scripture-ref">)([^<]+)(</p>\s*'
    r'<p>)(.*?)(</p>\s*</div>)',
    re.DOTALL,
)


def process_md(path: Path, missing_log: list) -> tuple[int, int]:
    """Process one md. Returns (cells_total, cells_replaced)."""
    text = path.read_text(encoding='utf-8')
    cells_total = 0
    cells_replaced = 0

    def replace_table(m):
        nonlocal cells_total, cells_replaced
        thead = m.group('thead')
        tbody = m.group('tbody')
        ths = TH_RE.findall(thead)
        tds = list(TD_RE.finditer(tbody))
        if len(ths) != len(tds):
            return m.group(0)  # mismatch — skip
        new_tds = []
        for th_text, td_m in zip(ths, tds):
            cells_total += 1
            new_inner = rebuild_cell(th_text, td_m.group(1), missing_log)
            new_tds.append(f'<td><p>{new_inner}</p></td>')
            cells_replaced += 1
        new_tbody = '<tbody><tr>' + ''.join(new_tds) + '</tr></tbody>'
        # Rebuild the full match
        return m.group(0).replace(
            f'<tbody><tr>{tbody}</tr></tbody>', new_tbody
        )

    new_text = TABLE_RE.sub(replace_table, text)

    def replace_single(m):
        nonlocal cells_total, cells_replaced
        ref_text = m.group(2)
        body = m.group(4)
        # Single-col cells may have a multi-book ref like "马太福音 5:1-12"
        cells_total += 1
        new_inner = rebuild_cell(ref_text, body, missing_log)
        cells_replaced += 1
        return m.group(1) + ref_text + m.group(3) + new_inner + m.group(5)
    new_text = SINGLE_BOX_RE.sub(replace_single, new_text)

    if new_text != text:
        # chmod 644 if read-only, write, restore 444 if it was
        mode = path.stat().st_mode & 0o777
        if mode == 0o444:
            path.chmod(0o644)
        path.write_text(new_text, encoding='utf-8')
        if mode == 0o444:
            path.chmod(0o444)
    return cells_total, cells_replaced


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('book', help='harmony-1 | harmony-2 | harmony-3 | all')
    ap.add_argument('--chapter', type=int, default=None)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    if args.book == 'all':
        books = ['harmony-1', 'harmony-2', 'harmony-3']
    else:
        books = [args.book]

    missing = []
    total_cells = 0
    total_replaced = 0

    for book in books:
        book_dir = ROOT / 'calvin' / book
        if not book_dir.exists():
            print(f'skip {book}: dir missing')
            continue
        for path in sorted(book_dir.glob('*.md')):
            if not path.stem.isdigit():
                continue
            ch = int(path.stem)
            if args.chapter is not None and ch != args.chapter:
                continue
            if args.dry_run:
                # Just count cells, don't write
                text = path.read_text(encoding='utf-8')
                n_table = sum(len(TD_RE.findall(m.group('tbody')))
                              for m in TABLE_RE.finditer(text))
                n_single = len(SINGLE_BOX_RE.findall(text))
                print(f'  {book}/{path.name}: {n_table + n_single} cells '
                      f'(table={n_table}, single={n_single}) (dry-run)')
                total_cells += n_table + n_single
                continue
            tot, rep = process_md(path, missing)
            print(f'  {book}/{path.name}: {rep}/{tot} cells replaced')
            total_cells += tot
            total_replaced += rep

    print(f'\nTotal: {total_replaced}/{total_cells} cells replaced')
    if missing:
        miss_unique = sorted(set(missing))
        print(f'\nMissing CUV lookups ({len(missing)} occurrences, {len(miss_unique)} unique):')
        for m in miss_unique[:20]:
            print(f'  {m}')
        if len(miss_unique) > 20:
            print(f'  ... and {len(miss_unique) - 20} more')


if __name__ == '__main__':
    main()
