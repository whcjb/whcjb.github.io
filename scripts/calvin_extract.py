#!/usr/bin/env python3
"""
scripts/calvin_extract.py — Unified Calvin commentary PDF extraction

All Calvin commentary volumes use this single script.
Usage: python scripts/calvin_extract.py <volume>

Available volumes:
  matthew1   – Harmony Vol. 1 (CCEL single-column, Matthew 1–11)
  harmony3   – Harmony Vol. 3 (CCEL single-column, passion/resurrection)
  matthew    – Harmony Vol. 2 (CCEL parallel gospel columns)
  acts1      – Acts Vol. 1 (CCEL single-column, Acts 1–13)
  acts2      – Acts Vol. 2 (CCEL single-column, Acts 14–28)
  heb        – Hebrews (Ages Digital Library bilingual)
  1cor-vol1  – 1 Corinthians Vol. 1 (Ages Digital Library bilingual)
  1cor-vol2  – Corinthians Vol. 2 (Ages Digital Library bilingual)
  phil       – Philippians (Ages Digital Library, intermediate tagged format)
"""

import fitz
import re
import os
import sys
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root

# ── Volume configurations ──────────────────────────────────────────────────────
VOLUMES = {
    'matthew1': {
        'format': 'ccel_harmony',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_matai_make1.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/matthew1/matthew1_raw.txt'),
        'skip_pages': 29,
        'header_y_max': 62,
        'footnote_size_max': 9.5,
        'page_num_x_min': 450,
        'page_w': 612.0,
        'body_left': 108.0,
        'body_right': 504.0,
        'centering': True,
        'extract_footnotes': True,
        # Hebrew/Greek mojibake fixes: the embedded font in this PDF lacks a
        # ToUnicode map, so PyMuPDF returns U+FFFD for every Hebrew glyph.
        # Each entry's left side is the mojibake-with-context string as it
        # appears in the raw output; the right side is the correct Hebrew
        # (verified by Qwen2.5-VL OCR on rendered pages where readable, and
        # by linguistic context + char count elsewhere). Char counts match.
        'mojibake_fixes': [
            # Luke 1:6 — חקים (chuqqim, "statutes/decrees")
            ('Hebrew word ����, which signifies statutes or decrees',
             'Hebrew word חקים, which signifies statutes or decrees'),
            ('in Scripture ���� usually denotes those services',
             'in Scripture חקים usually denotes those services'),
            # Luke 1:13 — יהוחנן (Yehohanan, "John" in 1 Chr 3:15)
            ('the authority of his office. ������, (1 Chronicles 3:15,)',
             'the authority of his office. יהוחנן, (1 Chronicles 3:15,)'),
            # Luke 1:15 — שכר (shekar, "strong drink" = Greek σίκερα)
            ('like the Hebrew word ���, it denotes any sort of manufactured wine',
             'like the Hebrew word שכר, it denotes any sort of manufactured wine'),
            # Luke 1:31 — ישע (yesha, "salvation") + יושיע (yoshia', Hiphil "to save")
            ('It is derived from the Hebrew word ���, salvation',
             'It is derived from the Hebrew word ישע, salvation'),
            ('salvation, from which comes �����, which signifies to save',
             'salvation, from which comes יושיע, which signifies to save'),
            # Luke 1:31 — יהושוע (Yehoshua, "Joshua")
            ('that it differs from the Hebrew name ������, (Jehoshua or Joshua.)',
             'that it differs from the Hebrew name יהושוע, (Jehoshua or Joshua.)'),
            # Luke 1:79 — שלום (shalom, "peace")
            ('But as the Hebrew word ����, *peace,* denotes every kind of prosperity',
             'But as the Hebrew word שלום, *peace,* denotes every kind of prosperity'),
            # Matthew 1:21 — יהוה (YHWH, "Jehovah")
            ('the two words ᾿Ιησοῦς and ����*, Jesus* and *Jehovah,*',
             'the two words ᾿Ιησοῦς and יהוה*, Jesus* and *Jehovah,*'),
            # Matthew 1:21 — יושיע (yoshia', Hiphil verb)
            ('in the Hiphil conjugation, �����, which signifies *to save*',
             'in the Hiphil conjugation, יושיע, which signifies *to save*'),
            # Matthew 1:21 — יהושוע (Yehoshua)
            ('the Hebrew word ������, *Jehoshua,* or *Joshua,*',
             'the Hebrew word יהושוע, *Jehoshua,* or *Joshua,*'),
            # Matthew 1:23 — עלמה (almah, "virgin") + בעלמה (b'almah, "with a maid")
            ('the Hebrew word ����*, virgin*',
             'the Hebrew word עלמה*, virgin*'),
            ('“the way of a man with a maids,” �����,',
             '“the way of a man with a maids,” בעלמה,'),
            # Luke 2:14 — רצון (ratzon, "good-will" = Greek εὐδοκία)
            ('in Scripture in the sense of the Hebrew word ����, the old translator',
             'in Scripture in the sense of the Hebrew word רצון, the old translator'),
            # Matthew 2:23 — נזיר (nazir, "Nazirite") + נזר (nazar, "to separate") + נצר (netzer, "branch/flower")
            ('The word ����, or *Nazarite,* signifies *holy and devoted to God,*',
             'The word נזיר, or *Nazarite,* signifies *holy and devoted to God,*'),
            ('and is derived from ���, *to separate.*',
             'and is derived from נזר, *to separate.*'),
            ('The noun ���, indeed, signifies a *flower:*',
             'The noun נצר, indeed, signifies a *flower:*'),
            # Matthew 4:18 — כנרת (Kinneret, "Chinnereth")
            ('lake among the ancient Hebrews was ����, (*Chinnereth*;)',
             'lake among the ancient Hebrews was כנרת, (*Chinnereth*;)'),
            # Mark 3:17 — בני רגש (b'nei regesh, "sons of thunder" = Boanerges)
            ('the full pronunciation would be ��� ���, *(Benae-regesh;)*',
             'the full pronunciation would be בני רגש, *(Benae-regesh;)*'),
            # Matthew 5:20 — פרושים (Perushim, "Pharisees" / "Expounders")
            ('They were called ������, that is, *Expound-* *ers,*',
             'They were called פרושים, that is, *Expound-* *ers,*'),
            # Matthew 5:22 — גיא (gei, "valley" → Gehenna/Ge-Hinnom)
            ('foreign word. ���(*Ge*) is the Hebrew word for a valley',
             'foreign word. גיא (*Ge*) is the Hebrew word for a valley'),
            # Matthew 10:10 — שבט (shebet, "rod/staff")
            ('ambiguity in the use of the Hebrew word ���, *(shebet;)*',
             'ambiguity in the use of the Hebrew word שבט, *(shebet;)*'),
            # Matthew 10:12 — שלום (shalom, again)
            ('As the Hebrew word ����, *(shalom,) peace,*',
             'As the Hebrew word שלום, *(shalom,) peace,*'),
        ],
    },
    'harmony3': {
        'format': 'ccel_harmony',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_matai_make3.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/harmony3/harmony3_raw.txt'),
        'skip_pages': 8,
        'header_y_max': 62,
        'footnote_size_max': 9.5,
        'page_num_x_min': 450,
        'page_w': 612.0,
        'body_left': 108.0,
        'body_right': 504.0,
        'centering': False,
    },
    'matthew': {
        'format': 'ccel_parallel',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_matai_make2.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/matthew/matthew_raw.txt'),
        'skip_pages': 7,
        'header_y_max': 55,
        'footnote_size_max': 7.5,
    },
    'acts1': {
        'format': 'ccel_acts',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_acts1.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/acts1/acts1_raw.txt'),
        'skip_pages': 6,
        'header_y_max': 55,
        'footer_y_min': 705,
    },
    'acts2': {
        'format': 'ccel_acts',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_acts2.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/acts2/acts2_raw.txt'),
        'skip_pages': 6,
        'header_y_max': 55,
        'footer_y_min': 705,
    },
    'heb': {
        'format': 'ages_heb',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_xibolaishu.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/heb/heb_raw.txt'),
        'skip_pages': 8,
        'header_y_max': 55,
        'latin_x_min': 200,
    },
    '1cor-vol1': {
        'format': 'ages_corinth',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_gelinduo1.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/1cor-vol1/calvin_1cor-vol1.md'),
        'table_split_x': 305,
        'skip_pages': set(range(6)) | {6, 19},
        'stop_page': 301,
        'greek': False,
        'verse_period': True,   # verse nums as "1." (with period)
    },
    '1cor-vol2': {
        'format': 'ages_corinth',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_gelinduo2.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/1cor-vol2/calvin_corinth-vol2.md'),
        'table_split_x': 305,
        'skip_pages': set(range(6)),
        'stop_page': None,
        'greek': True,
        'verse_period': False,  # verse nums "1" or "1." (normalized)
    },
    'phil': {
        'format': 'ages_phil',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_filibi.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/phil/calvin_filibi_structured.txt'),
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# SHARED UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def get_first_span(block):
    lines = block.get('lines', [])
    if not lines:
        return None
    spans = lines[0].get('spans', [])
    return spans[0] if spans else None


def get_block_text(block):
    return '\n'.join(
        ''.join(s['text'] for s in line.get('spans', []))
        for line in block.get('lines', [])
    )


def _make_sub_block(orig, lines):
    if not lines:
        return orig
    y0 = lines[0]['bbox'][1]
    y1 = lines[-1]['bbox'][3]
    return {'type': 0, 'bbox': [orig['bbox'][0], y0, orig['bbox'][2], y1], 'lines': lines}


def write_txt_output(blocks, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        for block in blocks:
            f.write(block + '\n\n')
    print(f'Written: {out_path}')
    print(f'Total blocks: {len(blocks)}')


# ══════════════════════════════════════════════════════════════════════════════
# CCEL HARMONY FORMAT  (matthew1, harmony3)
# Single-column CCEL PDF; gospel book name headers; optional centering detection
# ══════════════════════════════════════════════════════════════════════════════

_LINE_BREAK = {'__line_break__': True}


def ccel_spans_to_md(lines, fn_size_max=None):
    """Convert block lines to Markdown, normalising bold verse numbers → **N.**

    When `fn_size_max` is provided, superscript digit spans below that font size
    are rewritten as Kramdown footnote references (`[^N]`)."""
    all_spans = []
    for li, line in enumerate(lines):
        all_spans.extend(line.get('spans', []))
        if li < len(lines) - 1:
            all_spans.append(_LINE_BREAK)

    parts = []
    i = 0
    while i < len(all_spans):
        span = all_spans[i]
        if span is _LINE_BREAK:
            if parts and not parts[-1].endswith(' '):
                parts.append(' ')
            i += 1
            continue

        t = span['text']
        flags = span.get('flags', 0)
        is_bold   = bool(flags & 16)
        is_italic = bool(flags & 2)
        is_sup    = bool(flags & 1)

        # Inline footnote reference: small-font digit span (CCEL inconsistently
        # sets the superscript flag — detect by font size instead).
        if (fn_size_max is not None and t.strip().isdigit()
                and span.get('size', 99) < fn_size_max + 1):
            # Strip any trailing space on previous part — Markdown ref glues to word
            if parts and parts[-1].endswith(' '):
                parts[-1] = parts[-1].rstrip()
            parts.append(f'[^{t.strip()}]')
            i += 1
            continue

        # Normalise verse number: bold digit(s) → **N.**
        if is_bold and re.match(r'^\d+$', t.strip()):
            num = t.strip()
            j = i + 1
            while j < len(all_spans) and all_spans[j] is _LINE_BREAK:
                j += 1
            # consume optional non-bold period
            if (j < len(all_spans) and all_spans[j] is not _LINE_BREAK
                    and all_spans[j]['text'].strip() in ('.', '.\xa0', '')
                    and not (all_spans[j]['flags'] & 16)):
                j += 1
            while j < len(all_spans) and all_spans[j] is _LINE_BREAK:
                j += 1
            # consume optional bold NBSP
            while (j < len(all_spans) and all_spans[j] is not _LINE_BREAK
                   and not all_spans[j]['text'].strip()
                   and (all_spans[j]['flags'] & 16)):
                j += 1
            parts.append(f'**{num}.**')
            i = j
            continue

        stripped = t.strip()
        if not stripped:
            if t and parts and not parts[-1].endswith(' '):
                parts.append(' ')
            i += 1
            continue

        lead = t[:len(t) - len(t.lstrip())]
        tail = t[len(t.rstrip()):]
        if is_bold and is_italic:
            parts.append(f'{lead}***{stripped}***{tail}')
        elif is_bold:
            parts.append(f'{lead}**{stripped}**{tail}')
        elif is_italic:
            parts.append(f'{lead}*{stripped}*{tail}')
        else:
            parts.append(t)
        i += 1

    result = ''.join(parts)
    return re.sub(r' {2,}', ' ', result).strip()


def ccel_fix_hyphenation(text):
    return re.sub(r'-\s+([a-z])', r'\1', text)


def ccel_harmony_is_running_header(block, cfg):
    if block['bbox'][1] > cfg['header_y_max']:
        return False
    span = get_first_span(block)
    return span is not None and bool(span.get('flags', 0) & 2)


def ccel_harmony_is_page_number(block, cfg):
    if not re.match(r'^\d+$', get_block_text(block).strip()):
        return False
    return block['bbox'][0] > cfg['page_num_x_min']


def ccel_harmony_is_footnote(block, cfg):
    span = get_first_span(block)
    return span is not None and span.get('size', 0) < cfg['footnote_size_max']


def parse_ccel_footnote_block(block):
    """Parse a CCEL footnote block into a list of (num, text) tuples.

    A footnote block at the bottom of a page contains 1+ footnotes laid out as:
        <num>
        text line 1
        text line 2
        <next num>
        text…
    The leading `<num>` is a separate line whose stripped text is just digits.

    The printed page number (a stray digit line at the very end of the block)
    is dropped; entries without any body text are also dropped (avoids spurious
    "[^N]: " entries when a continuation block ends with the page number)."""
    raw_lines = []
    for line in block.get('lines', []):
        spans = [s for s in line.get('spans', []) if s['text'].strip()]
        if not spans:
            continue
        raw_lines.append(''.join(s['text'] for s in spans).strip())

    # Trailing standalone digit = printed page number, not a footnote start
    while raw_lines and raw_lines[-1].isdigit():
        raw_lines.pop()

    entries = []
    cur_num = None
    cur_lines = []
    for line_text in raw_lines:
        if line_text.isdigit() and (cur_num is None or cur_lines):
            if cur_num is not None and cur_lines:
                entries.append((cur_num, ' '.join(cur_lines).strip()))
            cur_num = line_text
            cur_lines = []
        else:
            cur_lines.append(line_text)
    if cur_num is not None and cur_lines:
        entries.append((cur_num, ' '.join(cur_lines).strip()))
    return entries


def ccel_harmony_is_index_start(block):
    return bool(re.match(
        r'^(Indexes?$|Index of (Scripture|Greek|Hebrew|Latin|French))',
        get_block_text(block).strip(), re.I))


def ccel_harmony_is_section_header(block):
    span = get_first_span(block)
    if not span or span.get('color', 0) != 0 or span.get('size', 0) < 10.0:
        return False
    first = span['text'].strip()
    return bool(first) and first == first.upper() and bool(
        re.match(r'^(MATTHEW|MARK|LUKE|JOHN)\b', first))


def ccel_harmony_is_blue_label(block):
    span = get_first_span(block)
    if not span:
        return False
    return span.get('color', 0) == 255 and not (span.get('flags', 0) & 16)


def ccel_harmony_norm(text):
    text = re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()
    return re.sub(r':\s+(\d)', r':\1', text)


def classify_lines_by_centering(lines, cfg):
    """Split lines into groups of [is_centered, [line, ...]].
    Promotes preceding closing-quote line into the same centered group."""
    body_w  = cfg['body_right'] - cfg['body_left']
    page_cx = cfg['page_w'] / 2

    classified = []
    line_lms   = []
    for line in lines:
        spans = [s for s in line['spans'] if s['text'].strip()]
        if not spans:
            continue
        lx0  = spans[0]['bbox'][0]
        lx1  = spans[-1]['bbox'][2]
        w    = lx1 - lx0
        cx   = (lx0 + lx1) / 2
        text = ''.join(s['text'] for s in spans).strip()
        left_margin  = lx0 - cfg['body_left']
        right_margin = cfg['body_right'] - lx1
        is_c = (
            abs(cx - page_cx) < 3
            and left_margin  > 2
            and right_margin > 2
        )
        classified.append([is_c, line, text])
        line_lms.append(left_margin)

    # Reject uniform-margin runs: a justified block quote (e.g. CCEL chapter
    # scripture heading rendered in a narrower column) gives every line the
    # same lm/rm and would otherwise look centered. A genuine centered block
    # has at least one line with substantial left margin (>10px) — usually a
    # short last line or citation. Without such an anchor, drop the run.
    n = len(classified)
    i = 0
    while i < n:
        if classified[i][0]:
            j = i
            while j < n and classified[j][0]:
                j += 1
            if not any(line_lms[k] > 10 for k in range(i, j)):
                for k in range(i, j):
                    classified[k][0] = False
            i = j
        else:
            i += 1

    for i in range(1, len(classified)):
        if classified[i][0] and not classified[i - 1][0]:
            if classified[i - 1][2].endswith(('"', ',"', ';"', '."', '"', ',"')):
                classified[i - 1][0] = True

    groups = []
    for is_c, line, _ in classified:
        if groups and groups[-1][0] == is_c:
            groups[-1][1].append(line)
        else:
            groups.append([is_c, [line]])
    return groups


def extract_ccel_harmony(cfg):
    doc   = fitz.open(cfg['pdf'])
    total = len(doc)
    print(f"Total pages: {total}, processing {cfg['skip_pages'] + 1}–{total}")

    output_blocks    = []
    last_section_upper = None

    for page_idx in range(cfg['skip_pages'], total):
        page   = doc[page_idx]
        blocks = sorted(
            page.get_text('dict', flags=fitz.TEXT_PRESERVE_WHITESPACE)['blocks'],
            key=lambda b: b['bbox'][1])

        for block in blocks:
            if block['type'] != 0:
                continue
            if ccel_harmony_is_running_header(block, cfg):
                continue
            if ccel_harmony_is_page_number(block, cfg):
                continue
            if ccel_harmony_is_footnote(block, cfg):
                if cfg.get('extract_footnotes'):
                    for num, fn_text in parse_ccel_footnote_block(block):
                        output_blocks.append(f'[^{num}]: {fn_text}')
                continue
            text = get_block_text(block).strip()
            if not text:
                continue

            if ccel_harmony_is_index_start(block):
                print(f'Stopping at index on page {page_idx + 1}')
                doc.close()
                if cfg.get('mojibake_fixes'):
                    output_blocks = [apply_mojibake_fixes(b, cfg['mojibake_fixes']) for b in output_blocks]
                write_txt_output(output_blocks, cfg['out'])
                print(f"Sections: {sum(1 for b in output_blocks if b.startswith(chr(10) + '## '))}")
                return

            if ccel_harmony_is_section_header(block):
                norm = ccel_harmony_norm(text).upper()
                output_blocks.append(f'\n## {norm}\n')
                last_section_upper = norm
                continue

            if ccel_harmony_is_blue_label(block):
                label = ccel_harmony_norm(text).upper()
                if not re.match(r'^(MATTHEW|MARK|LUKE|JOHN)\b', label):
                    continue
                x0 = block['bbox'][0]
                if x0 > 118:
                    if label != last_section_upper:
                        output_blocks.append(f'\n## {label}\n')
                        last_section_upper = label
                else:
                    if last_section_upper is None:
                        output_blocks.append(f'\n## {label}\n')
                        last_section_upper = label
                continue

            # Body block
            if cfg.get('centering'):
                for is_c, grp_lines in classify_lines_by_centering(block.get('lines', []), cfg):
                    md = ccel_fix_hyphenation(ccel_spans_to_md(grp_lines, cfg.get('footnote_size_max')))
                    if not md:
                        continue
                    output_blocks.append(f'<p style="text-align:center">{md}</p>' if is_c else md)
            else:
                md = ccel_fix_hyphenation(ccel_spans_to_md(block.get('lines', []), cfg.get('footnote_size_max')))
                if md:
                    output_blocks.append(md)

    doc.close()
    if cfg.get('mojibake_fixes'):
        output_blocks = [apply_mojibake_fixes(b, cfg['mojibake_fixes']) for b in output_blocks]
    write_txt_output(output_blocks, cfg['out'])
    print(f"Sections: {sum(1 for b in output_blocks if b.startswith(chr(10) + '## '))}")


def apply_mojibake_fixes(text, fixes):
    """Replace each context-anchored mojibake span with its correct Unicode.

    Embedded Hebrew/Greek fonts in some CCEL PDFs have no ToUnicode map, so
    PyMuPDF returns U+FFFD for every glyph. We restore them by matching the
    surrounding English context, identified by OCR + linguistic knowledge.
    """
    for needle, replacement in fixes:
        text = text.replace(needle, replacement)
    return text


# ══════════════════════════════════════════════════════════════════════════════
# CCEL PARALLEL GOSPEL FORMAT  (matthew)
# Multi-column parallel gospel verses; dynamic column detection
# ══════════════════════════════════════════════════════════════════════════════

def ccel_pg_spans_to_md(block, fn_size_max):
    all_spans = []
    lines = block.get('lines', [])
    for li, line in enumerate(lines):
        all_spans.extend(line.get('spans', []))
        if li < len(lines) - 1:
            all_spans.append(_LINE_BREAK)

    parts = []
    i = 0
    while i < len(all_spans):
        span = all_spans[i]
        if span is _LINE_BREAK:
            if parts and not parts[-1].endswith(' '):
                parts.append(' ')
            i += 1
            continue
        t     = span['text']
        flags = span.get('flags', 0)
        is_sup    = bool(flags & 1)
        is_bold   = bool(flags & 16)
        is_italic = bool(flags & 2)
        stripped = t.strip()
        if not stripped:
            if t and parts and not parts[-1].endswith(' '):
                parts.append(' ')
            i += 1
            continue
        if is_sup and stripped.isdigit() and span.get('size', 99) < fn_size_max + 2:
            parts.append(f'<sup>{stripped}</sup>')
            i += 1
            continue
        lead = t[:len(t) - len(t.lstrip())]
        tail = t[len(t.rstrip()):]
        if is_bold and is_italic:
            parts.append(f'{lead}***{stripped}***{tail}')
        elif is_bold:
            parts.append(f'{lead}**{stripped}**{tail}')
        elif is_italic:
            parts.append(f'{lead}*{stripped}*{tail}')
        else:
            parts.append(t)
        i += 1
    return re.sub(r' {2,}', ' ', ''.join(parts)).strip()


def ccel_pg_is_page_header(block, cfg):
    if block['bbox'][1] > cfg['header_y_max']:
        return False
    text = get_block_text(block).strip()
    return 'John Calvin' in text or bool(re.match(r'^\d+$', text))


def ccel_pg_is_page_number(block):
    if not re.match(r'^\d+$', get_block_text(block).strip()):
        return False
    span = get_first_span(block)
    return span is not None and span.get('size', 0) <= 10


def ccel_pg_is_footnote(block, cfg):
    span = get_first_span(block)
    return span is not None and span.get('size', 0) < cfg['footnote_size_max']


def ccel_pg_is_section_header(block):
    span = get_first_span(block)
    if not span or span.get('size', 0) < 18 or block['bbox'][0] < 100:
        return False
    return bool(re.search(r'(MATTHEW|MARK|LUKE|JOHN|HARMONY)',
                           get_block_text(block).strip().upper()))


def ccel_pg_is_col_label(block):
    span = get_first_span(block)
    if not span:
        return False
    size  = span.get('size', 0)
    flags = span.get('flags', 0)
    return (14 <= size <= 17 and bool(flags & 16) and block['bbox'][0] >= 50
            and bool(re.search(r'(Matthew|Mark|Luke|John)\s+\d+:\d+',
                               get_block_text(block).strip())))


def ccel_pg_extract_col_info(block):
    cols = []
    for line in block.get('lines', []):
        text = ''.join(s['text'] for s in line.get('spans', [])).strip()
        if text:
            cols.append((text, line['bbox'][0]))
    return sorted(cols, key=lambda c: c[1])


def ccel_pg_is_verse_block(block):
    span = get_first_span(block)
    if not span or not (span.get('flags', 0) & 16):
        return False
    size = span.get('size', 0)
    if size < 10 or size > 14:
        return False
    return bool(re.match(r'^\d+([.\xa0]|$)', span['text'].strip()))


def ccel_pg_is_index_start(block):
    text = get_block_text(block).strip()
    return (bool(re.match(r'^Indexes?$', text, re.I))
            or bool(re.match(r'^Index of ', text, re.I))
            or text.startswith('•'))


def ccel_pg_is_decoration(block):
    return get_block_text(block).strip().lstrip('\xa0').strip() in (
        'COMMENTARY', 'ON A', 'VOLUME SECOND')


def ccel_pg_build_verse_table(section_header, verse_blocks, col_info):
    if len(col_info) >= 2:
        xs     = [x for _, x in col_info]
        splits = [(xs[i] + xs[i + 1]) / 2 for i in range(len(xs) - 1)]
    else:
        splits = [290]
    n_cols    = len(splits) + 1
    col_lines = [[] for _ in range(n_cols)]

    for block in verse_blocks:
        for line in block.get('lines', []):
            line_text = re.sub(r'\s+', ' ',
                ''.join(s['text'] for s in line.get('spans', [])).replace('\xa0', ' ')).strip()
            if not line_text:
                continue
            ci = sum(1 for s in splits if line['bbox'][0] >= s)
            col_lines[ci].append((bool(re.match(r'^\d+\.?\s', line_text)), line_text))

    def lines_to_rows(lines):
        rows, cur = [], []
        for is_start, text in lines:
            if cur and is_start:
                rows.append(' '.join(cur))
                cur = [text]
            else:
                cur.append(text)
        if cur:
            rows.append(' '.join(cur))
        return rows

    col_rows = [lines_to_rows(lines) for lines in col_lines]
    if not any(col_rows):
        return ''
    max_rows = max(len(r) for r in col_rows)
    for r in col_rows:
        r += [''] * (max_rows - len(r))

    col_labels = [c[0] for c in col_info] if col_info else [''] * n_cols
    html = [
        '<table class="calvin-scripture">',
        f'<thead><tr><th colspan="{n_cols}" style="text-align:center">{section_header}</th></tr></thead>',
    ]
    if any(col_labels):
        html.append('<thead><tr>' + ''.join(f'<th>{l}</th>' for l in col_labels) + '</tr></thead>')
    html.append('<tbody>')
    for ri in range(max_rows):
        cells    = [col_rows[ci][ri] for ci in range(n_cols)]
        non_empty = sum(1 for c in cells if c)
        if not non_empty:
            continue
        if non_empty == 1 and n_cols > 1:
            cell = next(c for c in cells if c)
            html.append(f'<tr><td colspan="{n_cols}">{cell}</td></tr>')
        else:
            html.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
    html.append('</tbody></table>')
    return '\n'.join(html)


def extract_ccel_parallel(cfg):
    doc   = fitz.open(cfg['pdf'])
    total = len(doc)
    print(f"Total pages: {total}, skipping first {cfg['skip_pages']}")

    output_blocks       = []
    pending_continuation = None
    in_verse_section    = False
    current_header      = None
    current_col_info    = []
    verse_buf           = []
    fn_size_max         = cfg['footnote_size_max']

    def get_first_nonempty_span(block):
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                if span.get('text', '').strip():
                    return span
        return None

    def flush():
        nonlocal verse_buf
        if verse_buf and current_header:
            tbl = ccel_pg_build_verse_table(current_header, verse_buf, current_col_info)
            if tbl:
                output_blocks.append(tbl)
        verse_buf = []

    def handle_commentary(block):
        nonlocal pending_continuation
        rich = ccel_pg_spans_to_md(block, fn_size_max)
        rich = re.sub(r'-\s+([a-z])', r'\1', rich)
        if not rich:
            return
        if rich.endswith('-'):
            pending_continuation = (pending_continuation or '') + rich[:-1]
        else:
            if pending_continuation:
                rich = pending_continuation + rich
                pending_continuation = None
            output_blocks.append(rich)

    for page_idx in range(cfg['skip_pages'], total):
        page   = doc[page_idx]
        blocks = sorted(
            page.get_text('dict', flags=fitz.TEXT_PRESERVE_WHITESPACE)['blocks'],
            key=lambda b: b['bbox'][1])

        for block in blocks:
            if block['type'] != 0:
                continue
            if ccel_pg_is_page_header(block, cfg):
                continue
            if ccel_pg_is_page_number(block):
                continue
            if ccel_pg_is_footnote(block, cfg):
                continue
            if ccel_pg_is_decoration(block):
                continue
            text = get_block_text(block).strip()
            if not text:
                continue

            if ccel_pg_is_index_start(block):
                print(f'Stopping at index on page {page_idx + 1}')
                flush()
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                doc.close()
                write_txt_output(output_blocks, cfg['out'])
                tbl_marker = '<table class="calvin-scripture">'
                print(f"Tables: {sum(1 for b in output_blocks if tbl_marker in b)}")
                return

            if ccel_pg_is_section_header(block):
                flush()
                current_header   = re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()
                current_col_info = []
                output_blocks.append(f'\n## {current_header}\n')
                in_verse_section = True
            elif ccel_pg_is_col_label(block):
                current_col_info = ccel_pg_extract_col_info(block)
            elif in_verse_section and ccel_pg_is_verse_block(block):
                verse_buf.append(block)
            elif in_verse_section:
                first_span = get_first_nonempty_span(block)
                if verse_buf and first_span and not bool(first_span.get('flags', 0) & 16):
                    verse_buf.append(block)
                else:
                    flush()
                    in_verse_section = False
                    handle_commentary(block)
            else:
                handle_commentary(block)

    flush()
    if pending_continuation:
        output_blocks.append(pending_continuation)
    doc.close()
    write_txt_output(output_blocks, cfg['out'])
    tbl_marker = '<table class="calvin-scripture">'
    print(f"Tables: {sum(1 for b in output_blocks if tbl_marker in b)}")


# ══════════════════════════════════════════════════════════════════════════════
# CCEL ACTS FORMAT  (acts1, acts2)
# "Acts N:M" bold-italic headers; verse blocks identified by x-position
# ══════════════════════════════════════════════════════════════════════════════

def ccel_acts_is_scripture_header(block):
    span = get_first_span(block)
    if not span:
        return False
    x = block['bbox'][0]
    return (span.get('size', 0) >= 14 and bool(span.get('flags', 0) & 20)
            and 180 < x < 360
            and bool(re.match(r'^Acts\s+\d+:\d+', get_block_text(block).strip())))


def ccel_acts_is_page_header(block, cfg):
    if block['bbox'][1] > cfg['header_y_max']:
        return False
    text = get_block_text(block).strip()
    return ('John Calvin' in text or 'Comm on Acts' in text
            or 'Commentary on Acts' in text or bool(re.match(r'^\d+$', text)))


def ccel_acts_is_page_number(block):
    if not re.match(r'^\d+$', get_block_text(block).strip()):
        return False
    span = get_first_span(block)
    return span is not None and span.get('size', 0) <= 10


def ccel_acts_is_footnote(block, cfg):
    if block['bbox'][1] < cfg['footer_y_min']:
        return False
    span = get_first_span(block)
    if span and span.get('size', 0) < 8:
        return True
    return not get_block_text(block).strip()


def ccel_acts_is_verse_block(block):
    x0 = block['bbox'][0]
    if x0 < 65 or x0 > 85:
        return False
    lines = block.get('lines', [])
    if not lines:
        return False
    first_spans = lines[0].get('spans', [])
    if not first_spans:
        return False
    fs = first_spans[0]
    return bool(fs.get('flags', 0) & 4) and bool(re.match(r'^\d+\.$', fs['text'].strip()))


def ccel_acts_extract_block_rich(block):
    parts = []
    for line in block.get('lines', []):
        lp = []
        for span in line.get('spans', []):
            t = span['text'].strip()
            if bool(span.get('flags', 0) & 4) and re.match(r'^\d+\.$', t):
                lp.append(f'**{t}**')
            else:
                lp.append(span['text'])
        parts.append(''.join(lp))
    return ' '.join(parts).strip()


def ccel_acts_split_rich_by_verse(rich):
    parts = re.split(r'(?<=\S)\s+(\*\*\d+\.\*\*)', rich)
    if len(parts) == 1:
        return [rich]
    result = []
    i = 0
    while i < len(parts):
        chunk = parts[i].strip()
        if i + 1 < len(parts) and re.match(r'^\*\*\d+\.\*\*$', parts[i + 1]):
            if chunk:
                result.append(chunk)
            combined = parts[i + 1]
            if i + 2 < len(parts):
                combined += ' ' + parts[i + 2].lstrip()
            result.append(combined.strip())
            i += 3
        else:
            if chunk:
                result.append(chunk)
            i += 1
    return result if result else [rich]


def extract_ccel_acts(cfg):
    doc   = fitz.open(cfg['pdf'])
    total = len(doc)
    print(f"Total pages: {total}, skipping first {cfg['skip_pages']}")

    output_blocks        = []
    pending_continuation = None

    for page_idx in range(cfg['skip_pages'], total):
        page   = doc[page_idx]
        blocks = sorted(
            page.get_text('dict', flags=fitz.TEXT_PRESERVE_WHITESPACE)['blocks'],
            key=lambda b: b['bbox'][1])

        for block in blocks:
            if block['type'] != 0:
                continue
            if ccel_acts_is_page_header(block, cfg):
                continue
            if ccel_acts_is_page_number(block):
                continue
            if ccel_acts_is_footnote(block, cfg):
                continue
            text = get_block_text(block).strip()
            if not text:
                continue

            if text.strip().upper() in ('INDEX', 'INDEX OF SCRIPTURE REFERENCES',
                                         'SUBJECT INDEX', 'INDEX OF SUBJECTS'):
                print(f'Stopping at index page {page_idx + 1}')
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                    pending_continuation = None
                doc.close()
                write_txt_output(output_blocks, cfg['out'])
                return

            if ccel_acts_is_scripture_header(block):
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                    pending_continuation = None
                output_blocks.append(f'\n## {text.replace(chr(10), " ").strip()}\n')
            elif ccel_acts_is_verse_block(block):
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                    pending_continuation = None
                output_blocks.append(ccel_acts_extract_block_rich(block))
            else:
                rich = ccel_acts_extract_block_rich(block)
                if rich.endswith('-'):
                    pending_continuation = (pending_continuation or '') + rich[:-1]
                else:
                    if pending_continuation:
                        rich = pending_continuation + rich
                        pending_continuation = None
                    for sub in ccel_acts_split_rich_by_verse(rich):
                        output_blocks.append(sub)

    if pending_continuation:
        output_blocks.append(pending_continuation)
    doc.close()
    write_txt_output(output_blocks, cfg['out'])


# ══════════════════════════════════════════════════════════════════════════════
# AGES DIGITAL LIBRARY — HEBREWS FORMAT  (heb)
# Bilingual English/Latin; simpler line-level extraction; outputs raw .txt
# ══════════════════════════════════════════════════════════════════════════════

def heb_is_page_header(block, cfg):
    if block['bbox'][1] > cfg['header_y_max']:
        return False
    text = get_block_text(block).strip()
    return ('John Calvin' in text or 'Comm on Hebrews' in text
            or 'Commentary on Hebrews' in text or bool(re.match(r'^\d+$', text)))


def heb_is_page_number(block):
    if not re.match(r'^\d+$', get_block_text(block).strip()):
        return False
    span = get_first_span(block)
    return span is not None and span.get('size', 0) <= 10


def heb_is_footnote(block):
    span = get_first_span(block)
    if span and span.get('size', 0) < 10:
        return True
    return not get_block_text(block).strip()


def heb_is_decorative_header(block):
    span = get_first_span(block)
    if not span or span.get('size', 0) < 14:
        return False
    text = get_block_text(block).strip().upper()
    return any(re.match(p, text) for p in [
        r'^COMMENTAR', r'^CHAPTER\s+\d', r'^THE\s+ARGUMENT',
        r'^TRANSLATOR', r'^DEDICATOR', r'^TO\s+THE\s+', r'^EPISTLE\s+', r'^PREFACE'])


def heb_is_scripture_header(block, cfg):
    span = get_first_span(block)
    if not span:
        return False
    x0 = block['bbox'][0]
    return (span.get('size', 0) >= 14 and bool(span.get('flags', 0) & 20)
            and 80 < x0 < 300
            and bool(re.match(r'^Hebrews\s+(Chapter\s+)?\d+:\d+',
                               get_block_text(block).strip())))


def heb_extract_line_rich(line):
    spans = [s for s in line.get('spans', []) if s.get('text', '')]
    if not spans:
        return ''
    parts     = []
    skip_dot  = False
    for span in spans:
        text  = span['text']
        flags = span.get('flags', 0)
        size  = span.get('size', 0)
        t     = text.strip()
        if skip_dot:
            skip_dot = False
            if text.startswith('.'):
                text = text[1:]
            parts.append(text)
            continue
        if bool(flags & 4) and size >= 10 and re.match(r'^\d+\.?$', t):
            num = t.rstrip('.')
            parts.append(f'**{num}.**')
            if not t.endswith('.'):
                skip_dot = True
        else:
            parts.append(text)
    return ''.join(parts).strip()


def heb_extract_english_lines(block, latin_x_min):
    parts = []
    for line in block.get('lines', []):
        if line['bbox'][0] >= latin_x_min:
            continue
        text = heb_extract_line_rich(line)
        if text:
            parts.append(text)
    return ' '.join(parts).strip()


def heb_build_verse_table(section_header, verse_blocks, latin_x_min):
    verses = {}
    for block in verse_blocks:
        cur_en = cur_la = None
        for line in block.get('lines', []):
            spans = [s for s in line.get('spans', []) if s.get('text', '').strip()]
            if not spans:
                continue
            lx        = line['bbox'][0]
            line_text = heb_extract_line_rich(line)
            if not line_text:
                continue
            vn_m = re.match(r'\*\*(\d+)\.\*\*', line_text)
            if lx >= latin_x_min:
                if vn_m:
                    cur_la = int(vn_m.group(1))
                if cur_la is not None:
                    verses.setdefault(cur_la, {'en': [], 'la': []})['la'].append(line_text)
            else:
                if vn_m:
                    cur_en = int(vn_m.group(1))
                if cur_en is not None:
                    verses.setdefault(cur_en, {'en': [], 'la': []})['en'].append(line_text)

    if not verses:
        return ''

    def md_to_html(text):
        text = text.replace('|', '&#124;')
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*',   r'<em>\1</em>', text)
        return text

    html = [
        '<table class="calvin-scripture">',
        f'<thead><tr><th colspan="2" style="text-align:center">{section_header}</th></tr></thead>',
        '<tbody>',
    ]
    for vn in sorted(verses.keys()):
        en = md_to_html(' '.join(verses[vn].get('en', [])))
        la = md_to_html(' '.join(verses[vn].get('la', [])))
        html.append(f'<tr><td>{en}</td><td>{la}</td></tr>')
    html += ['</tbody>', '</table>']
    return '\n'.join(html)


def heb_split_rich_by_verse(rich):
    parts = re.split(r'(?<=\S)\s+(\*\*\d+\.\*\*)', rich)
    if len(parts) == 1:
        return [rich]
    result = []
    i = 0
    while i < len(parts):
        chunk = parts[i].strip()
        if i + 1 < len(parts) and re.match(r'^\*\*\d+\.\*\*$', parts[i + 1]):
            if chunk:
                result.append(chunk)
            combined = parts[i + 1]
            if i + 2 < len(parts):
                combined += ' ' + parts[i + 2].lstrip()
            result.append(combined.strip())
            i += 3
        else:
            if chunk:
                result.append(chunk)
            i += 1
    return result if result else [rich]


def extract_ages_heb(cfg):
    doc   = fitz.open(cfg['pdf'])
    total = len(doc)
    latin_x_min = cfg['latin_x_min']
    print(f"Total pages: {total}, skipping first {cfg['skip_pages']}")

    output_blocks        = []
    pending_continuation = None
    in_verse_section     = False
    current_header       = None
    verse_buf            = []

    def flush():
        nonlocal verse_buf
        if verse_buf and current_header:
            tbl = heb_build_verse_table(current_header, verse_buf, latin_x_min)
            if tbl:
                output_blocks.append(tbl)
        verse_buf = []

    def handle_commentary(rich):
        nonlocal pending_continuation
        if rich.endswith('-'):
            pending_continuation = (pending_continuation or '') + rich[:-1]
        else:
            if pending_continuation:
                rich = pending_continuation + rich
                pending_continuation = None
            for sub in heb_split_rich_by_verse(rich):
                output_blocks.append(sub)

    for page_idx in range(cfg['skip_pages'], total):
        page   = doc[page_idx]
        blocks = sorted(
            page.get_text('dict', flags=fitz.TEXT_PRESERVE_WHITESPACE)['blocks'],
            key=lambda b: b['bbox'][1])

        for block in blocks:
            if block['type'] != 0:
                continue
            if heb_is_page_header(block, cfg):
                continue
            if heb_is_page_number(block):
                continue
            if heb_is_footnote(block):
                continue
            if heb_is_decorative_header(block):
                continue
            text = get_block_text(block).strip()
            if not text:
                continue

            if re.match(r'^(APPENDIX|INDEX)', text.upper()):
                print(f'Stopping at appendix/index on page {page_idx + 1}')
                flush()
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                doc.close()
                write_txt_output(output_blocks, cfg['out'])
                return

            if heb_is_scripture_header(block, cfg):
                flush()
                current_header = re.sub(r'^(Hebrews)\s+Chapter\s+', r'\1 ',
                                         text.replace('\n', ' ').strip())
                output_blocks.append(f'\n## {current_header}\n')
                in_verse_section = True
            elif in_verse_section and (block['bbox'][0] >= latin_x_min
                                       or any(line['bbox'][0] < latin_x_min
                                              and line.get('spans', [{}])[0].get('flags', 0) & 4
                                              for line in block.get('lines', []))):
                # verse block (English or Latin column)
                verse_buf.append(block)
            elif in_verse_section:
                flush()
                in_verse_section = False
                rich = heb_extract_english_lines(block, latin_x_min)
                if not rich:
                    rich = get_block_text(block).replace('\n', ' ').strip()
                if rich:
                    handle_commentary(rich)
            else:
                if block['bbox'][0] >= latin_x_min:
                    continue
                rich = heb_extract_english_lines(block, latin_x_min)
                if not rich:
                    rich = get_block_text(block).replace('\n', ' ').strip()
                if rich:
                    handle_commentary(rich)

    flush()
    if pending_continuation:
        output_blocks.append(pending_continuation)
    doc.close()
    write_txt_output(output_blocks, cfg['out'])


# ══════════════════════════════════════════════════════════════════════════════
# AGES DIGITAL LIBRARY — CORINTHIANS FORMAT  (1cor-vol1, 1cor-vol2)
# Full bilingual pipeline: footnotes, Stage 1.5/1.6, direct .md output
# ══════════════════════════════════════════════════════════════════════════════

def convert_ages_greek(text):
    VMAP = {'a':'α','e':'ε','h':'η','i':'ι','o':'ο','u':'υ','w':'ω',
            'A':'Α','E':'Ε','H':'Η','I':'Ι','O':'Ο','U':'Υ','W':'Ω'}
    CONSMAP = {'b':'β','g':'γ','d':'δ','z':'ζ','q':'θ','k':'κ','l':'λ','m':'μ',
               'n':'ν','x':'ξ','p':'π','r':'ρ','s':'σ','v':'ς','t':'τ','f':'φ',
               'c':'χ','y':'ψ','B':'Β','G':'Γ','D':'Δ','Z':'Ζ','Q':'Θ','K':'Κ',
               'L':'Λ','M':'Μ','N':'Ν','X':'Ξ','P':'Π','R':'Ρ','S':'Σ','T':'Τ',
               'F':'Φ','C':'Χ','Y':'Ψ'}

    def convert_token(token):
        if not re.search(r'[><~|j]', token):
            return token
        result, i, chars = [], 0, list(token)
        while i < len(chars):
            c = chars[i]
            if c == 'j':
                i += 1
                continue
            if c in VMAP:
                base, j = VMAP[c], i + 1
                diacritics = []
                while j < len(chars) and chars[j] in '><~|j':
                    diacritics.append(chars[j])
                    j += 1
                i = j
                combined = base
                for d in diacritics:
                    combined += {'>':'́','<':'̀','~':'͂','|':'ͅ'}.get(d,'')
                result.append(unicodedata.normalize('NFC', combined))
            elif c in CONSMAP:
                result.append(CONSMAP[c])
                i += 1
            elif c in '><~|':
                i += 1
            else:
                result.append(c)
                i += 1
        return ''.join(result)

    parts = re.split(r'(<[a-zA-Z/!][^>]*>)', text)
    out = []
    for part in parts:
        if part.startswith('<'):
            out.append(part)
        else:
            out.append(re.sub(
                r'[a-zA-Z][a-zA-Z><~|j]*(?:[><~|j][a-zA-Z]*)*',
                lambda m: convert_token(m.group()) if re.search(r'[><~|j]', m.group()) else m.group(),
                part))
    return ''.join(out)


def cor_is_bold(span):       return bool(span['flags'] & 16)
def cor_is_italic(span):     return bool(span['flags'] & 2)
def cor_is_superscript(span):return bool(span['flags'] & 1)

def cor_is_footnote_ref(span):
    t = span['text'].strip()
    if not t.isdigit():
        return False
    return (cor_is_superscript(span) and span['size'] < 8) or (6.4 <= span['size'] <= 7.5)

def cor_is_footnote_def_block(block):
    spans = [s for l in block['lines'] for s in l['spans'] if s['text'].strip()]
    if not spans or not all(s['size'] <= 9.5 for s in spans):
        return False
    return any(s['size'] < 7 and s['text'].strip().isdigit() and not cor_is_superscript(s)
               for s in spans)

def cor_is_running_header(block): return block['bbox'][1] < 58

def cor_is_page_number(block):
    if block['bbox'][1] < 725:
        return False
    return bool(re.match(r'^\d+$',
        ''.join(s['text'] for l in block['lines'] for s in l['spans']).strip()))

def cor_block_has_right_col(block, tsx):
    for line in block['lines']:
        fs = [s for s in line['spans'] if s['text'].strip()]
        if fs and fs[0]['bbox'][0] >= tsx:
            return True
    return False

def cor_block_is_full_width(block, tsx):
    spans = [s for l in block['lines'] for s in l['spans'] if s['text'].strip()]
    return bool(spans) and not cor_block_has_right_col(block, tsx) and block['bbox'][2] > 400

def cor_split_by_size(block):
    lws = [(l, next((s for s in l['spans'] if s['text'].strip()), None))
           for l in block['lines']]
    sizes = [fs['size'] for _, fs in lws if fs]
    if sizes and sizes[0] < 14 and max(sizes) >= 24:
        h1 = [l for l, fs in lws if fs and fs['size'] >= 24]
        if h1:
            return [_make_sub_block(block, h1)]
    groups, cur_lines, cur_sz = [], [], None
    for line in block['lines']:
        fs = next((s for s in line['spans'] if s['text'].strip()), None)
        if fs is None:
            cur_lines.append(line)
            continue
        sz = fs['size']
        if cur_sz is not None and abs(sz - cur_sz) > 2:
            if cur_lines:
                groups.append(_make_sub_block(block, cur_lines))
            cur_lines = [line]
        else:
            cur_lines.append(line)
        cur_sz = sz
    if cur_lines:
        groups.append(_make_sub_block(block, cur_lines))
    return groups if groups else [block]

def cor_split_by_verse_number(block, tsx):
    if cor_block_has_right_col(block, tsx) or not cor_block_is_full_width(block, tsx):
        return [block]
    groups, cur = [], []
    for i, line in enumerate(block['lines']):
        fs = [s for s in line['spans'] if s['text'].strip()]
        if i > 0 and fs:
            s = fs[0]
            if (bool(s['flags'] & 16) and not bool(s['flags'] & 2)
                    and re.match(r'^\d+\.$', s['text'].strip())):
                if cur:
                    groups.append(_make_sub_block(block, cur))
                cur = [line]
                continue
        cur.append(line)
    if cur:
        groups.append(_make_sub_block(block, cur))
    return groups if len(groups) > 1 else [block]

def cor_split_by_paragraph_indent(block, tsx):
    if cor_block_has_right_col(block, tsx) or not cor_block_is_full_width(block, tsx):
        return [block]
    bx0 = block['bbox'][0]
    INDENT_LOW, INDENT_HIGH, SIZE_MIN = 10, 60, 11.0
    groups, cur, first_seen, prev_deep = [], [], False, False
    for line in block['lines']:
        spans = [s for s in line['spans'] if s['text'].strip()]
        if not spans:
            cur.append(line)
            continue
        x0    = spans[0]['bbox'][0]
        size  = spans[0]['size']
        indent = x0 - bx0
        is_deep = indent > INDENT_HIGH and size >= SIZE_MIN
        fc      = spans[0]['text'].lstrip()[:1]
        is_para = (first_seen and size >= SIZE_MIN and (
            (INDENT_LOW <= indent <= INDENT_HIGH)
            or (is_deep and not prev_deep and not fc.islower())))
        if is_para and cur:
            groups.append(_make_sub_block(block, cur))
            cur = []
        cur.append(line)
        first_seen = True
        prev_deep  = is_deep
    if cur:
        groups.append(_make_sub_block(block, cur))
    return groups if len(groups) > 1 else [block]

def cor_is_table_header(block):
    if not block['lines'] or not block['lines'][0]['spans']:
        return False
    return abs(block['lines'][0]['spans'][0]['size'] - 16.8) < 0.6

def cor_is_h1(block):
    if not block['lines'] or not block['lines'][0]['spans']:
        return False
    return block['lines'][0]['spans'][0]['size'] >= 24

def cor_is_h2(block):
    if not block['lines'] or not block['lines'][0]['spans']:
        return False
    s = block['lines'][0]['spans'][0]['size']
    return 14 <= s < 24

def cor_collect_footnote_defs(blocks):
    defs = {}
    for b in blocks:
        if not cor_is_footnote_def_block(b):
            continue
        cur_num, cur_parts = None, []
        for line in b['lines']:
            for span in line['spans']:
                t = span['text'].strip()
                if not t:
                    continue
                if t.isdigit() and span['size'] < 7 and not cor_is_superscript(span):
                    if cur_num is not None:
                        defs[cur_num] = ' '.join(cur_parts).strip()
                    cur_num, cur_parts = t, []
                else:
                    cur_parts.append(t)
        if cur_num is not None:
            defs[cur_num] = ' '.join(cur_parts).strip()
    return defs

def cor_format_span(span):
    t = span['text']
    if not t.strip():
        return t
    if cor_is_footnote_ref(span):
        return f'[^{t.strip()}]'
    lead = t[:len(t) - len(t.lstrip())]
    tail = t[len(t.rstrip()):]
    inner = t.strip()
    if cor_is_bold(span) and cor_is_italic(span):
        return f'{lead}***{inner}***{tail}'
    if cor_is_bold(span):
        return f'{lead}**{inner}**{tail}'
    if cor_is_italic(span):
        return f'{lead}*{inner}*{tail}'
    return t

def cor_spans_to_text(spans):
    parts = []
    for span in spans:
        part = cor_format_span(span)
        if not part:
            continue
        if parts:
            prev = parts[-1]
            if (prev and not prev[-1].isspace()
                    and not part[0].isspace()
                    and part[0] not in '.,;:!?)\'"_-'):
                parts.append(' ')
        parts.append(part)
    return re.sub(r' {2,}', ' ', ''.join(parts)).strip()

def cor_fnref_to_html(text):
    text = re.sub(r'\[\^(\d+)\]',
        lambda m: f'<sup><a href="#fn:{m.group(1)}" id="fnref:{m.group(1)}">{m.group(1)}</a></sup>',
        text)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<em><strong>\1</strong></em>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*',   r'<em>\1</em>', text)
    return text

def cor_build_table(header_text, rows):
    hdr = header_text.strip().upper()
    lines = ['', '<table class="calvin-scripture">',
             f'<thead><tr><th colspan="2" style="text-align:center">{hdr}</th></tr></thead>',
             '<tbody>']
    for en, la in rows:
        en_e = cor_fnref_to_html(en.replace('|', '&#124;'))
        la_e = cor_fnref_to_html(la.replace('|', '&#124;'))
        lines.append(f'<tr><td>{en_e}</td><td>{la_e}</td></tr>')
    lines += ['</tbody>', '</table>', '']
    return '\n'.join(lines)

def cor_extract_scripture(header_block, verse_blocks, cfg):
    tsx  = cfg['table_split_x']
    header_text = ' '.join(s['text'] for l in header_block['lines'] for s in l['spans']).strip()

    all_spans = sorted(
        [s for b in verse_blocks for l in b['lines'] for s in l['spans'] if s['text'].strip()],
        key=lambda s: (s['bbox'][1], s['bbox'][0]))

    left  = [s for s in all_spans if s['bbox'][0] <  tsx]
    right = [s for s in all_spans if s['bbox'][0] >= tsx]

    if cfg.get('verse_period', True):
        # vol1: verse nums "1." (with period); row format: "1. text"
        def parse(spans):
            verses, cur_num, cur_parts = [], None, []
            for span in spans:
                t = span['text'].strip()
                if cor_is_bold(span) and re.match(r'^\d+\.$', t):
                    if cur_num is not None:
                        verses.append((cur_num, cor_spans_to_text(cur_parts)))
                    cur_num, cur_parts = t, []
                else:
                    cur_parts.append(span)
            if cur_num is not None:
                verses.append((cur_num, cor_spans_to_text(cur_parts)))
            return verses

        en_d = {v[0]: v[1] for v in parse(left)}
        la_d = {v[0]: v[1] for v in parse(right)}
        nums = sorted(set(list(en_d) + list(la_d)), key=lambda x: int(x.rstrip('.')))
        rows = [(f'{n} {en_d.get(n,"")}'.strip(), f'{n} {la_d.get(n,"")}'.strip())
                for n in nums]
    else:
        # vol2: verse nums "1" or "1." (normalised); strip leading ". " from text
        def parse(spans):
            verses, cur_num, cur_parts = [], None, []
            for span in spans:
                t = span['text'].strip()
                if cor_is_bold(span) and re.match(r'^\d+\.?$', t):
                    if cur_num is not None:
                        verses.append((cur_num, cor_spans_to_text(cur_parts)))
                    cur_num, cur_parts = t.rstrip('.'), []
                else:
                    cur_parts.append(span)
            if cur_num is not None:
                verses.append((cur_num, cor_spans_to_text(cur_parts)))
            return verses

        en_d = {v[0]: v[1] for v in parse(left)}
        la_d = {v[0]: v[1] for v in parse(right)}
        nums = sorted(set(list(en_d) + list(la_d)), key=lambda x: int(x))
        rows = []
        for n in nums:
            er = en_d.get(n, '')
            lr = la_d.get(n, '')
            if er.startswith('. '): er = er[2:]
            if lr.startswith('. '): lr = lr[2:]
            rows.append((f'{n}. {er}'.strip() if er else f'{n}.',
                         f'{n}. {lr}'.strip() if lr else f'{n}.'))

    return cor_build_table(header_text, rows)

def cor_process_page(page, pending_header, cfg):
    tsx    = cfg['table_split_x']
    blocks = page.get_text('dict')['blocks']

    body_blocks, fn_def_blocks = [], []
    for b in blocks:
        if b['type'] != 0:
            continue
        if cor_is_running_header(b):
            continue
        if cor_is_page_number(b):
            continue
        if cor_is_footnote_def_block(b):
            fn_def_blocks.append(b)
        else:
            for s in cor_split_by_size(b):
                for s2 in cor_split_by_verse_number(s, tsx):
                    body_blocks.extend(cor_split_by_paragraph_indent(s2, tsx))

    footnote_defs = cor_collect_footnote_defs(fn_def_blocks)
    body_blocks.sort(key=lambda b: b['bbox'][1])

    pending_out  = None
    carried_table = None
    if pending_header is not None:
        if isinstance(pending_header, dict) and 'header' in pending_header:
            carry_hdr, prev_verses = pending_header['header'], pending_header['verses']
        else:
            carry_hdr, prev_verses = pending_header, []

        new_verses = []
        for b in body_blocks:
            if cor_is_table_header(b) or cor_is_h1(b) or cor_is_h2(b):
                break
            if cor_block_is_full_width(b, tsx):
                break
            new_verses.append(b)

        all_verses = prev_verses + new_verses
        carried_table = {'type': 'TABLE', 'html': cor_extract_scripture(carry_hdr, all_verses, cfg)}
        body_blocks   = body_blocks[len(new_verses):]

    items = []
    if carried_table:
        items.append(carried_table)

    page_h1_count = 0
    i = 0
    while i < len(body_blocks):
        b = body_blocks[i]
        if cor_is_h1(b):
            if page_h1_count > 0:
                i += 1
                continue
            items.append({'type': 'H1', 'text': ' '.join(
                s['text'] for l in b['lines'] for s in l['spans']).strip()})
            page_h1_count += 1
            i += 1
        elif cor_is_table_header(b):
            hdr_block  = b
            verse_blks = []
            j          = i + 1
            hit_comm   = False
            while j < len(body_blocks):
                nb = body_blocks[j]
                if cor_is_table_header(nb) or cor_is_h1(nb) or cor_is_h2(nb):
                    hit_comm = True
                    break
                if cor_block_has_right_col(nb, tsx):
                    verse_blks.append(nb)
                    j += 1
                elif cor_block_is_full_width(nb, tsx):
                    hit_comm = True
                    break
                else:
                    verse_blks.append(nb)
                    j += 1
            if not hit_comm and verse_blks:
                pending_out = {'header': hdr_block, 'verses': verse_blks}
            elif not hit_comm and not verse_blks:
                pending_out = hdr_block
            else:
                if verse_blks:
                    items.append({'type': 'TABLE',
                                  'html': cor_extract_scripture(hdr_block, verse_blks, cfg)})
            i = j
        elif cor_is_h2(b):
            h2_lines  = [l for l in b['lines']
                          if next((s for s in l['spans'] if s['text'].strip()), None)
                          and next((s for s in l['spans'] if s['text'].strip()), {}).get('size', 0) >= 14]
            body_lines = [l for l in b['lines'] if l not in h2_lines]
            h2_text    = ' '.join(s['text'] for l in h2_lines for s in l['spans']).strip()
            if h2_text:
                items.append({'type': 'H2', 'text': h2_text})
            if body_lines:
                body_text = cor_spans_to_text([s for l in body_lines for s in l['spans']])
                if body_text:
                    fi = 0
                    for line in body_lines:
                        ls = [s for s in line['spans'] if s['text'].strip()]
                        if ls:
                            fi = round(ls[0]['bbox'][0] - b['bbox'][0])
                            break
                    items.append({'type': 'BODY', 'text': body_text, 'indent': fi})
            i += 1
        else:
            text = cor_spans_to_text([s for l in b['lines'] for s in l['spans']])
            if text:
                fi = 0
                for line in b['lines']:
                    ls = [s for s in line['spans'] if s['text'].strip()]
                    if ls:
                        fi = round(ls[0]['bbox'][0] - b['bbox'][0])
                        break
                items.append({'type': 'BODY', 'text': text, 'indent': fi})
            i += 1

    return items, footnote_defs, pending_out


def cor_is_sentence_end(text):
    s = text.rstrip().rstrip('"\'')
    return not s or s[-1] in '.!?…'


def extract_ages_corinth(cfg):
    doc        = fitz.open(cfg['pdf'])
    skip_pages = cfg['skip_pages']
    stop_page  = cfg.get('stop_page')
    use_greek  = cfg.get('greek', False)

    all_items    = []
    all_fn_defs  = {}
    pending_hdr  = None

    for page_num in range(len(doc)):
        if page_num in skip_pages:
            continue
        if stop_page is not None and page_num >= stop_page:
            break
        page = doc[page_num]
        items, fn_defs, pending_hdr = cor_process_page(page, pending_hdr, cfg)
        all_items.append({'type': 'PAGE', 'num': page_num + 1})
        all_items.extend(items)
        all_fn_defs.update(fn_defs)

    doc.close()

    # Stage 1.5: merge paragraph fragments across page/block boundaries
    PARA_INDENT_LOW = 10
    idx = 0
    while idx < len(all_items):
        if all_items[idx]['type'] == 'BODY':
            j = idx + 1
            while j < len(all_items) and all_items[j]['type'] == 'PAGE':
                j += 1
            if j < len(all_items) and all_items[j]['type'] == 'BODY':
                cur = all_items[idx]['text']
                nxt = all_items[j]['text']
                nxt_indent = all_items[j].get('indent', 0)
                open_paren = bool(re.search(r'\([^)]*$', cur.rstrip()))
                if (nxt_indent < PARA_INDENT_LOW and not cor_is_sentence_end(cur)) \
                        or (open_paren and not cor_is_sentence_end(cur)):
                    all_items[idx]['text'] = cur.rstrip() + ' ' + nxt.lstrip()
                    all_items[idx]['indent'] = min(
                        all_items[idx].get('indent', 0), all_items[j].get('indent', 0))
                    del all_items[j]
                    continue
        idx += 1

    # Stage 1.6: relocate leading footnote refs to previous paragraph end
    idx = 0
    while idx < len(all_items):
        if all_items[idx]['type'] == 'BODY':
            text    = all_items[idx]['text']
            m_pre   = re.match(r'^(\[\^\d+\])\s+', text)
            m_solo  = re.match(r'^(\[\^\d+\])$', text.strip())
            if m_pre or m_solo:
                fn_ref = (m_pre or m_solo).group(1)
                rest   = text[m_pre.end():] if m_pre else ''
                pi     = idx - 1
                while pi >= 0 and all_items[pi]['type'] == 'PAGE':
                    pi -= 1
                if pi >= 0 and all_items[pi]['type'] == 'BODY':
                    all_items[pi]['text'] = all_items[pi]['text'].rstrip() + fn_ref
                    if rest:
                        all_items[idx]['text'] = rest
                    else:
                        del all_items[idx]
                        continue
        idx += 1

    # Render to Markdown
    md_lines = []
    for item in all_items:
        t = item['type']
        if t == 'PAGE':
            md_lines.append(f'\n<!-- PAGE {item["num"]} -->\n')
        elif t == 'H1':
            md_lines.append(f'\n# {item["text"]}\n')
        elif t == 'H2':
            md_lines.append(f'\n## {item["text"]}\n')
        elif t == 'TABLE':
            md_lines.append(item['html'])
        elif t == 'BODY':
            text = item['text']
            if use_greek:
                text = convert_ages_greek(text)
            text = re.sub(r'^(\d+)\. ', lambda m: f'{m.group(1)}\\. ', text)
            if '<table' not in text and '<tr' not in text:
                text = text.replace('|', '\\|')
            md_lines.append(f'\n{text}\n')
            if item.get('indent', 0) > 20:
                md_lines.append('{: style="text-align: center"}\n')

    if all_fn_defs:
        md_lines.append('\n---\n')
        for num in sorted(all_fn_defs.keys(), key=lambda x: int(x)):
            fn_text = all_fn_defs[num]
            if use_greek:
                fn_text = convert_ages_greek(fn_text)
            fn_text = fn_text.replace('|', '\\|')
            md_lines.append(f'\n[^{num}]: {fn_text}\n')

    out_path = cfg['out']
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(''.join(md_lines))
    print(f'Done. Written to {out_path}')
    print(f"Pages: {sum(1 for i in all_items if i['type']=='PAGE')}  "
          f"Tables: {sum(1 for i in all_items if i['type']=='TABLE')}  "
          f"Body: {sum(1 for i in all_items if i['type']=='BODY')}  "
          f"Footnotes: {len(all_fn_defs)}")


# ══════════════════════════════════════════════════════════════════════════════
# AGES DIGITAL LIBRARY — PHILIPPIANS FORMAT  (phil)
# Intermediate tagged output: [H1] / [H2] / [BODY] / [FOOTNOTE] lines
# ══════════════════════════════════════════════════════════════════════════════

def phil_dominant_class(line_spans):
    sizes = [s['size'] for s in line_spans if s['text'].strip()]
    if not sizes:
        return 'BODY', 12.0
    ms = max(sizes)
    if ms >= 22:   return 'H1', ms
    if ms >= 16:   return 'H2', ms
    if ms == 11:   return 'VERSE', ms
    return 'BODY', ms


def phil_reconstruct_page(page):
    page_height = page.rect.height
    blocks      = [b for b in page.get_text('dict')['blocks'] if b['type'] == 0]
    blocks.sort(key=lambda b: b['bbox'][1])

    output_lines  = []
    prev_block_y1 = None

    for block in blocks:
        if prev_block_y1 is not None and block['bbox'][1] - prev_block_y1 > 8:
            output_lines.append('')
        prev_block_y1 = block['bbox'][3]

        block_lines_output = []
        for line in block['lines']:
            non_empty = [s for s in line['spans'] if s['text'].strip()]
            if not non_empty:
                continue
            line_class, ms = phil_dominant_class(non_empty)
            full_text = ''.join(s['text'] for s in line['spans'])
            if not full_text.strip():
                continue
            if non_empty[0]['size'] <= 8:
                if re.match(r'^[Ff]t?\d+$|^<\d+>$', non_empty[0]['text'].strip()):
                    line_class = 'FOOTNOTE'
            stripped = full_text.strip()
            if ms >= 16 and any(kw in stripped for kw in ('PHILIPPIANS','COLOSSIANS','THESSALONIANS')):
                if re.search(r'\d+:\d+', stripped):
                    line_class = 'VERSE'
            block_lines_output.append((line_class, full_text))

        if not block_lines_output:
            continue

        cur_cls, cur_texts = block_lines_output[0]
        for cls, txt in block_lines_output[1:]:
            if cls == cur_cls:
                prev = cur_texts[-1] if isinstance(cur_texts, list) else cur_texts
                if (prev if isinstance(prev, str) else '').rstrip().endswith('-'):
                    cur_texts = (cur_texts[:-1] if isinstance(cur_texts, list) else []) + \
                                [(prev if isinstance(prev, str) else '').rstrip()[:-1] + txt.lstrip()]
                else:
                    if isinstance(cur_texts, str):
                        cur_texts = [cur_texts]
                    cur_texts.append(txt)
            else:
                texts = cur_texts if isinstance(cur_texts, list) else [cur_texts]
                merged = ' '.join(t.strip() for t in texts if t.strip())
                if merged.strip():
                    output_lines.append(f'[{cur_cls}] {merged}')
                cur_cls, cur_texts = cls, txt

        texts  = cur_texts if isinstance(cur_texts, list) else [cur_texts]
        merged = ' '.join(t.strip() for t in texts if t.strip())
        if merged.strip():
            output_lines.append(f'[{cur_cls}] {merged}')

    return output_lines


def extract_ages_phil(cfg):
    doc   = fitz.open(cfg['pdf'])
    total = len(doc)
    print(f"Processing {total} pages...")

    all_output = []
    for page_num in range(total):
        all_output.append(f'\n--- PAGE {page_num + 1} ---\n')
        all_output.extend(phil_reconstruct_page(doc[page_num]))

    doc.close()
    out_path = cfg['out']
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_output) + '\n')
    print(f'Done! Written to: {out_path}')
    print(f'Total lines: {len(all_output)}')


# ══════════════════════════════════════════════════════════════════════════════
# DISPATCH
# ══════════════════════════════════════════════════════════════════════════════

DISPATCH = {
    'ccel_harmony':  extract_ccel_harmony,
    'ccel_parallel': extract_ccel_parallel,
    'ccel_acts':     extract_ccel_acts,
    'ages_heb':      extract_ages_heb,
    'ages_corinth':  extract_ages_corinth,
    'ages_phil':     extract_ages_phil,
}


def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/calvin_extract.py <volume>')
        print('Volumes:', ', '.join(sorted(VOLUMES)))
        sys.exit(1)
    vol = sys.argv[1]
    if vol not in VOLUMES:
        print(f'Unknown volume: {vol!r}')
        print('Volumes:', ', '.join(sorted(VOLUMES)))
        sys.exit(1)
    cfg = VOLUMES[vol]
    print(f'Extracting {vol} [{cfg["format"]}]...')
    DISPATCH[cfg['format']](cfg)


if __name__ == '__main__':
    main()
