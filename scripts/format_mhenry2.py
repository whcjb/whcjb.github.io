#!/usr/bin/env python3
"""
Format Matthew Henry commentary .md files using a state-machine approach.
Properly opens/closes HTML div tags for outline hierarchy.
"""

from __future__ import annotations

import re
import os
import sys

import json
import opencc

_t2s = opencc.OpenCC('t2s')

MHENRY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mhenry')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Mapping from mhenry book_id to Bible JSON abbreviation
BOOK_ID_MAP = {
    'genesis': 'gn', 'exodus': 'ex', 'leviticus': 'lv', 'numbers': 'nm',
    'deuteronomy': 'dt', 'joshua': 'js', 'judges': 'jud', 'ruth': 'rt',
    '1samuel': '1sm', '2samuel': '2sm', '1kings': '1kgs', '2kings': '2kgs',
    '1chronicles': '1ch', '2chronicles': '2ch', 'ezra': 'ezr', 'nehemiah': 'ne',
    'esther': 'et', 'job': 'job', 'psalms': 'ps', 'proverbs': 'prv',
    'ecclesiastes': 'ec', 'songofsolomon': 'so', 'isaiah': 'is', 'jeremiah': 'jr',
    'lamentations': 'lm', 'ezekiel': 'ez', 'daniel': 'dn', 'hosea': 'ho',
    'joel': 'jl', 'amos': 'am', 'obadiah': 'ob', 'jonah': 'jn',
    'micah': 'mi', 'nahum': 'na', 'habakkuk': 'hk', 'zephaniah': 'zp',
    'haggai': 'hg', 'zechariah': 'zc', 'malachi': 'ml',
    'matthew': 'mt', 'mark': 'mk', 'luke': 'lk', 'john': 'jo',
    'acts': 'act', 'romans': 'rm', '1corinthians': '1co', '2corinthians': '2co',
    'galatians': 'gl', 'ephesians': 'eph', 'philippians': 'ph', 'colossians': 'cl',
    '1thessalonians': '1ts', '2thessalonians': '2ts', '1timothy': '1tm', '2timothy': '2tm',
    'titus': 'tt', 'philemon': 'phm', 'hebrews': 'hb', 'james': 'jm',
    '1peter': '1pe', '2peter': '2pe', '1john': '1jo', '2john': '2jo',
    '3john': '3jo', 'jude': 'jd', 'revelation': 're',
}

_bible_data: dict = {}


def load_bible() -> dict:
    """Load Bible JSON, return {abbrev: [[verse_texts_ch1], [verse_texts_ch2], ...]}"""
    global _bible_data
    if _bible_data:
        return _bible_data
    bible_path = os.path.join(SCRIPT_DIR, 'zh_cuv.json')
    with open(bible_path, 'r', encoding='utf-8-sig') as f:
        raw = json.load(f)
    for book in raw:
        abbrev = book['abbrev']
        # chapters is list of lists; each inner list = verse texts for that chapter
        _bible_data[abbrev] = book['chapters']
    return _bible_data


def get_verse_keywords(book_id: str, chapter: int) -> tuple[list[str], list[str]]:
    """Get start and end keywords for each verse.
    Returns (start_keywords, end_keywords), both 0-based (index 0 = verse 1)."""
    bible = load_bible()
    abbrev = BOOK_ID_MAP.get(book_id)
    if not abbrev or abbrev not in bible:
        return [], []
    chapters = bible[abbrev]
    if chapter < 1 or chapter > len(chapters):
        return [], []
    verses = chapters[chapter - 1]
    start_kw: list[str] = []
    end_kw: list[str] = []
    for v in verses:
        clean = _t2s.convert(v.replace(' ', '').replace('\u3000', ''))
        stripped = _strip_punct(clean)
        start_kw.append(stripped[:8])
        end_kw.append(stripped[-8:])
    return start_kw, end_kw


_PUNCT_RE = re.compile(r'[，。；：！？、「」『』（）\(\)【】""''《》〈〉·\s]')


def _strip_punct(s: str) -> str:
    return _PUNCT_RE.sub('', s)


def text_contains_verse_start(text: str, keywords: list[str], verse_num: int) -> bool:
    """Check if text contains the start of a specific verse number."""
    if verse_num < 1 or verse_num > len(keywords):
        return False
    kw = keywords[verse_num - 1]
    clean_text = _strip_punct(text.replace(' ', '').replace('\u3000', ''))
    return kw in clean_text


def split_frontmatter(text: str) -> tuple[str, str]:
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            return '---' + parts[1] + '---', parts[2]
    return '', text


def is_date_marker(line: str) -> bool:
    s = line.strip()
    return bool(re.match(r'^.{2,10}[（(]主[前后]\s*\d+\s*年[）)]$', s))


def is_chapter_heading(line: str) -> bool:
    return bool(re.match(r'^第[一二三四五六七八九十百零\d]+章\s*$', line.strip()))


def is_verse_start(line: str) -> bool:
    return bool(re.match(r'^\d{1,3}\s+\S', line.strip()))


def is_footnote_num(line: str) -> bool:
    return bool(re.match(r'^\d{1,2}\s*$', line.strip()))


def detect_marker(line: str, after_blank: bool = True) -> tuple[str | None, str | None, str]:
    """Detect outline marker at start of line.
    after_blank: True if the previous line was blank (new paragraph).
    Only detect numbered markers (1. 2. （1）) when after a blank line,
    to avoid false positives from mid-paragraph line breaks.
    Returns (level, label, rest_of_line) or (None, None, line)."""
    s = line.strip()
    # I. II. III. always detected (strong signal)
    m = re.match(r'^(I{1,3}V?|IV|VI{0,3}|[IVX]+)\.\s*(.*)', s)
    if m and len(m.group(1)) <= 4:
        return 'l1', m.group(1) + '.', m.group(2)
    # 1. 2. 3. and （1）（2） only after blank line
    if after_blank:
        m = re.match(r'^(\d{1,2})\.\s*(?!\d|：)(.*)', s)
        if m:
            return 'l2', m.group(1) + '.', m.group(2)
        m = re.match(r'^（(\d{1,2})）\s*(.*)', s)
        if m:
            return 'l3', '（' + m.group(1) + '）', m.group(2)
    return None, None, s


def extract_fm_field(fm: str, field: str) -> str:
    """Extract a field value from YAML front matter."""
    m = re.search(r'^' + field + r':\s*(.+)$', fm, re.MULTILINE)
    return m.group(1).strip().strip('"\'') if m else ''


def format_file(filepath: str) -> bool:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    fm, body = split_frontmatter(content)
    if not fm:
        return False

    # Get book_id and chapter from front matter for Bible matching
    book_id = extract_fm_field(fm, 'book_id')
    chapter_str = extract_fm_field(fm, 'chapter')
    chapter = int(chapter_str) if chapter_str.isdigit() else 0
    verse_start_kw, verse_end_kw = get_verse_keywords(book_id, chapter) if book_id and chapter else ([], [])
    total_verses = len(verse_start_kw)

    lines = body.split('\n')
    out: list[str] = []
    footnotes: list[tuple[str, str]] = []
    open_divs: list[str] = []  # stack of open div levels
    i = 0
    total = len(lines)

    def close_all_divs() -> None:
        while open_divs:
            open_divs.pop()
            out.append('</div>')
            out.append('')

    def close_to_level(target: str) -> None:
        """Close divs until we reach same or higher level than target."""
        level_order = {'l1': 1, 'l2': 2, 'l3': 3}
        target_n = level_order.get(target, 0)
        while open_divs and level_order.get(open_divs[-1], 0) >= target_n:
            open_divs.pop()
            out.append('</div>')
            out.append('')

    prev_blank = True  # treat start of file as after blank
    while i < total:
        line = lines[i]
        stripped = line.strip()

        # Empty line
        if not stripped:
            if out and out[-1] != '':
                out.append('')
            prev_blank = True
            i += 1
            continue

        # Remove PDF headers
        if is_date_marker(stripped):
            i += 1
            continue

        # Footnote number (standalone)
        if is_footnote_num(stripped):
            fn_num = stripped.strip()
            fn_found = False
            # Look backward for footnote text
            k = len(out) - 1
            while k >= 0 and out[k] == '':
                k -= 1
            if k >= 0 and len(out[k]) <= 160 and not out[k].startswith(('<', '>', '#')):
                fn_text = out[k]
                out[k] = ''
                footnotes.append((fn_num, fn_text))
                fn_found = True

            if not fn_found:
                # Look forward
                fn_lines: list[str] = []
                j = i + 1
                while j < total and not lines[j].strip():
                    j += 1
                while j < total:
                    ns = lines[j].strip()
                    if not ns or is_verse_start(lines[j]) or is_chapter_heading(ns):
                        break
                    fn_lines.append(ns)
                    j += 1
                    if len(fn_lines) >= 4:
                        break
                if fn_lines:
                    fn_text = ' '.join(fn_lines)
                    if len(fn_text) <= 300:
                        footnotes.append((fn_num, fn_text))
                        i = j
                        continue
            else:
                i += 1
                continue

        # Chapter heading
        if is_chapter_heading(stripped):
            close_all_divs()
            out.append('')
            out.append(f'## {stripped}')
            out.append('')
            i += 1
            continue

        # Verse block: use Bible text to determine boundaries
        if is_verse_start(stripped):
            verse_lines = [stripped]
            all_text = stripped
            # Find which verse number started this block
            m_start = re.match(r'^(\d{1,3})\s', stripped)
            start_verse = int(m_start.group(1)) if m_start else 1
            # Find highest verse num mentioned so far in accumulated text
            seen_nums = [int(x) for x in re.findall(r'(?:^|[\s。；！？」）\]])(\d{1,3})\s+', all_text)]
            max_seen = max(seen_nums) if seen_nums else start_verse

            j = i + 1
            while j < total:
                ns = lines[j].strip()
                if not ns:
                    # Skip blanks, but peek for more verses
                    pk = j + 1
                    while pk < total and not lines[pk].strip():
                        pk += 1
                    if pk < total and is_verse_start(lines[pk]):
                        j = pk
                        continue
                    break
                if is_verse_start(ns):
                    verse_lines.append(ns)
                    all_text += ' ' + ns
                    new_nums = [int(x) for x in re.findall(r'(?:^|[\s。；！？」）\]])(\d{1,3})\s+', ns)]
                    if new_nums:
                        max_seen = max(max_seen, max(new_nums))
                    j += 1
                elif not re.match(r'^\d', ns) and not is_chapter_heading(ns):
                    marker_check = detect_marker(ns)
                    if marker_check[0] is not None:
                        break
                    # Use Bible text: check if any remaining verse (max_seen+1 .. total_verses)
                    # starts in this line or the next few lines
                    should_absorb = False
                    # Build lookahead: include tail of last absorbed verse + this line + next lines
                    # (handles case where verse keyword spans the line break)
                    last_tail = verse_lines[-1].strip()[-30:]  # last 30 chars of previous line
                    lookahead = last_tail + ns
                    for la in range(1, 6):
                        if j + la < total and lines[j + la].strip():
                            lookahead += ' ' + lines[j + la].strip()
                    # Check if current verse (max_seen) content continues into this line
                    # by checking if the next verse (max_seen+1) keyword appears
                    # Check 1: does lookahead contain start of a next verse?
                    for vn in range(max_seen, min(max_seen + 10, total_verses + 1)):
                        if text_contains_verse_start(lookahead, verse_start_kw, vn):
                            should_absorb = True
                            break
                    # Check 2: does the current verse's end keyword appear in lookahead?
                    # (handles case where continuation is the tail of current verse)
                    if not should_absorb and max_seen >= 1 and max_seen <= len(verse_end_kw):
                        end_kw_check = verse_end_kw[max_seen - 1]
                        if end_kw_check and end_kw_check in _strip_punct(lookahead):
                            should_absorb = True
                    # Also absorb very short tail lines (< 15 chars)
                    if len(ns) <= 15:
                        should_absorb = True

                    if should_absorb:
                        verse_lines[-1] += ' ' + ns
                        all_text += ' ' + ns
                        new_nums = [int(x) for x in re.findall(r'(?:^|[\s。；！？」）\]])(\d{1,3})\s+', ns)]
                        if new_nums:
                            max_seen = max(max_seen, max(new_nums))
                        j += 1
                    else:
                        break
                else:
                    break

            # Post-trim: find the end of the last complete verse using end keywords
            # Join all verse text, find where last verse ends, split off trailing commentary
            full_verse_text = ' '.join(verse_lines)
            trimmed = full_verse_text
            leftover = ''
            if verse_end_kw and max_seen >= 1 and max_seen <= len(verse_end_kw):
                end_kw = verse_end_kw[max_seen - 1]
                clean_full = _strip_punct(full_verse_text)
                if end_kw and end_kw in clean_full:
                    # Find the position of end keyword in original text
                    # Map back: find each char of end_kw in full_verse_text
                    pos = 0
                    kw_idx = 0
                    for ci, ch in enumerate(full_verse_text):
                        if _strip_punct(ch) == '':
                            continue
                        if ch == end_kw[kw_idx] or _strip_punct(ch) == end_kw[kw_idx]:
                            kw_idx += 1
                            if kw_idx == len(end_kw):
                                pos = ci + 1
                                break
                        else:
                            kw_idx = 0
                            if ch == end_kw[0] or _strip_punct(ch) == end_kw[0]:
                                kw_idx = 1
                    if pos > 0:
                        # Find the next sentence-ending punctuation after pos
                        end_pos = pos
                        while end_pos < len(full_verse_text) and full_verse_text[end_pos] in '。」）) \n':
                            end_pos += 1
                        trimmed = full_verse_text[:end_pos].strip()
                        leftover = full_verse_text[end_pos:].strip()

            close_all_divs()
            out.append('')
            out.append('<div class="mh-verse">')
            out.append(trimmed)
            out.append('</div>')
            out.append('')
            if leftover:
                out.append(leftover)
                out.append('')
            i = j
            continue

        # Check for outline marker at start of line
        level, label, rest = detect_marker(stripped, after_blank=prev_blank)
        if level:
            close_to_level(level)
            out.append('')
            out.append(f'<div class="mh-{level}"><span class="mh-label">{label}</span>')
            out.append('')
            open_divs.append(level)
            if rest:
                out.append(rest)
            prev_blank = False
            i += 1
            continue

        # Regular text
        out.append(stripped)
        prev_blank = False
        i += 1

    close_all_divs()

    # Footnotes
    if footnotes:
        out.append('')
        out.append('<aside class="mhenry-footnotes">')
        for fn_num, fn_text in footnotes:
            out.append(f'<p><sup>{fn_num}</sup> {fn_text}</p>')
        out.append('</aside>')

    # Clean consecutive blanks
    cleaned: list[str] = []
    prev_blank = False
    for line in out:
        if line == '':
            if not prev_blank:
                cleaned.append('')
            prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False

    new_content = fm + '\n\n' + '\n'.join(cleaned).strip() + '\n'
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False


def main() -> None:
    if len(sys.argv) > 1:
        target = sys.argv[1]
        fp = os.path.join(MHENRY_DIR, target)
        if not os.path.exists(fp):
            print(f'Not found: {fp}')
            return
        files = [fp]
    else:
        import glob
        files = sorted(glob.glob(os.path.join(MHENRY_DIR, '**', '*.md'), recursive=True))

    print(f'Processing {len(files)} file(s)')
    changed = 0
    for fp in files:
        try:
            if format_file(fp):
                changed += 1
                print(f'  formatted: {os.path.relpath(fp, MHENRY_DIR)}')
        except Exception as e:
            print(f'  ERROR {os.path.relpath(fp, MHENRY_DIR)}: {e}')
    print(f'Done. {changed}/{len(files)} updated.')


if __name__ == '__main__':
    main()
