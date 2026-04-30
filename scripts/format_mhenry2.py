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


_NORMALIZE_MAP = str.maketrans({
    '著': '着', '它': '他', '牠': '他', '祂': '他', '妳': '你', '裏': '里', '裡': '里',
    '麽': '么', '甚': '什', '衹': '只', '祇': '只', '噁': '恶',
})


def _strip_punct(s: str) -> str:
    return _PUNCT_RE.sub('', s).translate(_NORMALIZE_MAP)


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
    # 1. 2. 3. only after blank line (（N） kept inline, too many false positives)
    if after_blank:
        m = re.match(r'^(\d{1,2})\.\s*(?!\d|：)(.*)', s)
        if m:
            return 'l2', m.group(1) + '.', m.group(2)
    return None, None, s



def extract_fm_field(fm: str, field: str) -> str:
    m = re.search(r'^' + field + r':\s*(.+)$', fm, re.MULTILINE)
    return m.group(1).strip().strip('"\'') if m else ''


def _fulltext_find_end(haystack: str, needle_tail: str) -> int:
    """Find position right AFTER needle_tail ends in haystack (punct-stripped matching).
    Returns -1 if not found."""
    clean_h = _strip_punct(haystack)
    clean_n = _strip_punct(needle_tail)
    if not clean_n or len(clean_n) < 4:
        return -1
    idx = clean_h.find(clean_n)
    if idx < 0:
        return -1
    target_ci = idx + len(clean_n)
    ci = 0
    for oi, ch in enumerate(haystack):
        if _strip_punct(ch):
            ci += 1
            if ci == target_ci:
                pos = oi + 1
                while pos < len(haystack) and haystack[pos] in '。！？」）)\u3000 \n\r':
                    pos += 1
                return pos
    return -1


def _get_full_verses(book_id: str, chapter: int) -> list[str]:
    """Get simplified full text of each verse (0-indexed: [0]=verse1)."""
    bible = load_bible()
    abbrev = BOOK_ID_MAP.get(book_id)
    if not abbrev or abbrev not in bible:
        return []
    chapters = bible[abbrev]
    if chapter < 1 or chapter > len(chapters):
        return []
    return [_t2s.convert(v.replace(' ', '').replace('\u3000', '')) for v in chapters[chapter - 1]]


def _find_verse_regions(full_text: str, verses: list[str]) -> list[tuple[int, int]]:
    """Find all scripture quotation regions in full_text by matching each verse's
    start keyword against "N keyword" patterns in text, then using verse end text
    to find where each verse ends. Consecutive verses are merged into one region.
    Returns sorted list of (start_pos, end_pos)."""
    if not verses:
        return []

    total_v = len(verses)
    # Build start/end keywords per verse
    skws = [_strip_punct(v)[:10] for v in verses]
    ekws = [_strip_punct(v)[-10:] for v in verses]

    # Step 1: locate each verse's position by searching for "N <verse_start>"
    found: list[tuple[int, int, int]] = []  # (vnum_1based, start_pos, end_pos)

    for vi in range(total_v):
        vnum = vi + 1
        skw = skws[vi]
        if not skw or len(skw) < 4:
            continue
        # Search for verse number prefix pattern
        for m in re.finditer(r'(?:^|(?<=[\s，。；！？」）\]]))' + str(vnum) + r'\s+', full_text):
            after = _strip_punct(full_text[m.start():m.start() + 50])
            if skw[:5] in after[:25]:
                # Found verse start. Find end using last 15 chars of verse.
                search_start = m.start()
                max_range = int(len(verses[vi]) * 1.5) + 60
                region = full_text[search_start:search_start + max_range]
                v_tail = verses[vi][-20:] if len(verses[vi]) > 20 else verses[vi]
                e_off = _fulltext_find_end(region, v_tail)
                if e_off > 0:
                    found.append((vnum, m.start(), search_start + e_off))
                else:
                    # Fallback: approximate end
                    found.append((vnum, m.start(), search_start + min(len(verses[vi]) + 80, max_range)))
                break

    if not found:
        return []

    # Step 2: sort by position and merge consecutive verses into blocks
    found.sort(key=lambda x: x[1])
    blocks: list[tuple[int, int, int]] = []  # (start_pos, approx_end, last_vnum)
    cs, ce, cl = found[0][1], found[0][2], found[0][0]

    for vnum, s, e in found[1:]:
        if vnum <= cl + 2 and s <= ce + 80:
            ce = max(ce, e)
            cl = max(cl, vnum)
        else:
            blocks.append((cs, ce, cl))
            cs, ce, cl = s, e, vnum
    blocks.append((cs, ce, cl))

    # Step 3: for each block, re-find the precise end using last verse's full tail
    regions: list[tuple[int, int]] = []
    for bs, be, last_v in blocks:
        if last_v <= total_v:
            # Calculate total expected length of all verses in block
            block_verses_len = sum(len(verses[vi]) for vi in range(total_v) if any(
                f[0] == vi + 1 and f[1] >= bs and f[1] <= be for f in found
            ))
            max_range = int(block_verses_len * 1.5) + 100
            region = full_text[bs:bs + max_range]
            v_tail = verses[last_v - 1][-20:] if len(verses[last_v - 1]) > 20 else verses[last_v - 1]
            e_off = _fulltext_find_end(region, v_tail)
            if e_off > 0:
                regions.append((bs, min(bs + e_off, len(full_text))))
                continue
        # Fallback
        regions.append((bs, min(be, len(full_text))))

    return regions


def format_file(filepath: str) -> bool:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    fm, body = split_frontmatter(content)
    if not fm:
        return False

    book_id = extract_fm_field(fm, 'book_id')
    chapter_str = extract_fm_field(fm, 'chapter')
    chapter = int(chapter_str) if chapter_str.isdigit() else 0
    verses = _get_full_verses(book_id, chapter) if book_id and chapter else []

    lines = body.split('\n')

    # --- Pass 1: remove date markers, collect footnotes ---
    clean_lines: list[str] = []
    footnotes: list[tuple[str, str]] = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if is_date_marker(s):
            i += 1
            continue
        if is_footnote_num(s):
            fn_num = s
            k = len(clean_lines) - 1
            while k >= 0 and clean_lines[k].strip() == '':
                k -= 1
            if k >= 0 and len(clean_lines[k].strip()) <= 160 and not clean_lines[k].strip().startswith(('<', '>', '#')):
                footnotes.append((fn_num, clean_lines[k].strip()))
                clean_lines[k] = ''
                i += 1
                continue
            fl: list[str] = []
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            while j < len(lines):
                ns = lines[j].strip()
                if not ns or is_chapter_heading(ns):
                    break
                fl.append(ns)
                j += 1
                if len(fl) >= 4:
                    break
            if fl and len(' '.join(fl)) <= 300:
                footnotes.append((fn_num, ' '.join(fl)))
                i = j
                continue
        clean_lines.append(lines[i])
        i += 1

    clean_text = '\n'.join(clean_lines)

    # --- Pass 2: find verse regions ---
    regions = _find_verse_regions(clean_text, verses)

    # --- Pass 3: split into segments ---
    segments: list[tuple[str, str]] = []
    last_pos = 0
    for rs, re_ in regions:
        if rs > last_pos:
            segments.append(('text', clean_text[last_pos:rs]))
        segments.append(('verse', clean_text[rs:re_]))
        last_pos = re_
    if last_pos < len(clean_text):
        segments.append(('text', clean_text[last_pos:]))

    # --- Pass 4: format output ---
    out: list[str] = []
    open_divs: list[str] = []
    prev_blank = True

    def close_all() -> None:
        while open_divs:
            open_divs.pop()
            out.append('</div>')
            out.append('')

    def close_to(target: str) -> None:
        order = {'l1': 1, 'l2': 2, 'l3': 3}
        tn = order.get(target, 0)
        while open_divs and order.get(open_divs[-1], 0) >= tn:
            open_divs.pop()
            out.append('</div>')
            out.append('')

    in_unit = False

    def close_unit() -> None:
        nonlocal in_unit
        if in_unit:
            close_all()
            out.append('</div>')  # close mh-unit-body
            out.append('</div>')  # close mh-unit
            out.append('')
            in_unit = False

    first_verse_seen = False

    for si, (seg_type, seg_content) in enumerate(segments):
        seg_content = seg_content.strip()
        if not seg_content:
            continue

        # Wrap text before first verse as overview
        if seg_type == 'text' and not first_verse_seen:
            # Process line by line, but wrap non-heading content in overview div
            text_lines = seg_content.split('\n')
            overview_lines: list[str] = []
            for tl in text_lines:
                tl = tl.strip()
                if not tl:
                    continue
                if is_chapter_heading(tl):
                    close_all()
                    out.append('')
                    out.append(f'## {tl}')
                    out.append('')
                    prev_blank = True
                else:
                    overview_lines.append(tl)
            if overview_lines:
                out.append('')
                out.append('<div class="mh-overview">')
                out.append(' '.join(overview_lines))
                out.append('</div>')
                out.append('')
            prev_blank = True
            continue

        if seg_type == 'verse':
            first_verse_seen = True
            close_unit()
            close_all()
            verse_text = ' '.join(seg_content.split())
            # Check if next segment is commentary (text) — if so, wrap in unit
            has_following_text = (si + 1 < len(segments) and segments[si + 1][0] == 'text'
                                 and segments[si + 1][1].strip())
            if has_following_text:
                out.append('')
                out.append('<div class="mh-unit">')
                out.append('<div class="mh-verse">')
                out.append(verse_text)
                out.append('</div>')
                out.append('<div class="mh-unit-body">')
                out.append('')
                in_unit = True
            else:
                out.append('')
                out.append('<div class="mh-verse">')
                out.append(verse_text)
                out.append('</div>')
                out.append('')
            prev_blank = True
        else:
            for tl in seg_content.split('\n'):
                tl = tl.strip()
                if not tl:
                    if out and out[-1] != '':
                        out.append('')
                    prev_blank = True
                    continue
                if is_chapter_heading(tl):
                    close_unit()
                    close_all()
                    out.append('')
                    out.append(f'## {tl}')
                    out.append('')
                    prev_blank = True
                    continue
                level, label, rest = detect_marker(tl, after_blank=prev_blank)
                if level:
                    close_to(level)
                    out.append('')
                    out.append(f'<div class="mh-{level}"><span class="mh-label">{label}</span>')
                    out.append('')
                    open_divs.append(level)
                    if rest:
                        out.append(rest)
                    prev_blank = False
                else:
                    out.append(tl)
                    prev_blank = False

    close_unit()
    close_all()

    if footnotes:
        out.append('')
        out.append('<aside class="mhenry-footnotes">')
        for fn_num, fn_text in footnotes:
            out.append(f'<p><sup>{fn_num}</sup> {fn_text}</p>')
        out.append('</aside>')

    cleaned: list[str] = []
    pb = False
    for line in out:
        if line == '':
            if not pb:
                cleaned.append('')
            pb = True
        else:
            cleaned.append(line)
            pb = False

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
        except Exception as e:
            print(f'  ERROR {os.path.relpath(fp, MHENRY_DIR)}: {e}')
    print(f'Done. {changed}/{len(files)} updated.')


if __name__ == '__main__':
    main()
