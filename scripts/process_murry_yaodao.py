#!/usr/bin/env python3
"""
Process OCR text files for Murray's "正直生活要道" and generate Jekyll markdown files.
OCR source: ocr_output/murry_yaodao/page_XXXX.txt
Output: reading/murray/principles/*.md
"""

import os
import re

OCR_DIR = os.path.join(os.path.dirname(__file__), '../ocr_output/murry_yaodao')
OUT_DIR = os.path.join(os.path.dirname(__file__), '../reading/murray/principles')

# Page ranges (inclusive, 1-based PDF pages)
SECTIONS = [
    # (output_filename, section_key, section_title, start_page, end_page, header_skip_lines)
    ('foreword', 'foreword', '序（巴刻）',       4,   5,  2),
    ('preface',  'preface',  '前言（慕理）',      6,   9,  1),
    ('1',  '1',  '第一章　问题导入',              10,  22, 2),
    ('2',  '2',  '第二章　创造的条例',            23,  36, 2),
    ('3',  '3',  '第三章　婚姻条例与生养众多',    37,  63, 2),
    ('4',  '4',  '第四章　劳动的条例',            64,  81, 2),
    ('5',  '5',  '第五章　生命的神圣',            82,  93, 2),
    ('6',  '6',  '第六章　真理的神圣',            94, 113, 2),
    ('7',  '7',  '第七章　主的教训',             114, 137, 2),
    ('8',  '8',  '第八章　律法与恩典',           138, 153, 2),
    ('9',  '9',  '第九章　圣经伦理动力',         154, 173, 2),
    ('10', '10', '第十章　敬畏神',               174, 184, 2),
    ('11', '11', '附录一　神的儿子和人的女子（创世记6：1-4）',  185, 190, 2),
    ('12', '12', '附录二　对利未记18章16、18节的附加解释',     191, 196, 2),
    ('13', '13', '附录三　对哥林多前书5章1节的附加解释',       197, 198, 2),
    ('14', '14', '附录四　美国长老制教会与奴隶制度',           199, 202, 2),
    ('15', '15', '附录五　反律主义',                           203, 204, 2),
]

HEADER_IMGS = {
    'foreword': 'reading-murray-foreword.jpg',
    'preface':  'reading-murray-1.jpg',
}
DEFAULT_IMG = 'reading-murray-1.jpg'
DATE = '2026-05-15 13:23'

# Footnote starter patterns: superscript ¹²³⁴⁵⁶⁷⁸⁹ OR circled ①②③④⑤⑥⑦⑧⑨⑩
# OR plain digit(s) followed by space: "7 参见..." / "8 当然不用说..."
SUP_CHARS = '¹²³⁴⁵⁶⁷⁸⁹⁰'
CIRCLE_CHARS = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮'
ALL_FN_START = f'[{SUP_CHARS}{CIRCLE_CHARS}]'
FN_LINE_RE = re.compile(r'^(?:' + ALL_FN_START + r'|\d{1,2}\s)')

SUP_MAP = {'¹':'1','²':'2','³':'3','⁴':'4','⁵':'5',
           '⁶':'6','⁷':'7','⁸':'8','⁹':'9','⁰':'0'}
CIRCLE_MAP = {'①':'1','②':'2','③':'3','④':'4','⑤':'5',
              '⑥':'6','⑦':'7','⑧':'8','⑨':'9','⑩':'10',
              '⑪':'11','⑫':'12','⑬':'13','⑭':'14','⑮':'15'}


def marker_to_num(s):
    """Convert leading superscript/circled chars to decimal number string."""
    result = ''
    for c in s:
        if c in SUP_MAP:
            result += SUP_MAP[c]
        elif c in CIRCLE_MAP:
            return CIRCLE_MAP[c]  # circled = single digit
        else:
            break
    return result


def read_page(page_num):
    fname = os.path.join(OCR_DIR, f'page_{page_num:04d}.txt')
    if not os.path.exists(fname):
        return ''
    with open(fname, encoding='utf-8') as f:
        return f.read()


# Patterns for detecting unmarked bibliography/footnote paragraphs
_BIBLIO_INLINE_RE = re.compile(
    r'[（【][^）】]*\d{4}[^）】]*[）】]|'  # (... year ...) or 【... year ...】
    r'第\d+[卷页册]|'                       # 第N卷/页/册
    r'，\d+-\d+\s*页|'                      # ，xxx-xxx页
    r'\d{4}\s*年[）】,，。；]'              # 1921年）or 1921年, or 1949年】
)
_ORPHAN_FN_START_RE = re.compile(r'^(参阅[：:]|参见|同上|同前|ibid|op\.?\s*cit)', re.IGNORECASE)
_CONTINUATION_RE = re.compile(r'^[城页卷册，；）]|^[而然]，')  # mid-word or connective continuation


_CITE_VERB_RE = re.compile(r'参阅[：:]|参见|同上|同前')


def _is_orphan_footnote_para(para):
    """Detect bibliography/footnote paragraphs that have no superscript marker."""
    s = para.strip()
    if not s:
        return False
    if _ORPHAN_FN_START_RE.match(s):
        return True
    if _CONTINUATION_RE.match(s) and len(s) < 300:
        return True
    hits = len(_BIBLIO_INLINE_RE.findall(s))
    if hits >= 2 and len(s) < 500:
        return True
    # One citation marker is enough if paragraph also contains a "参阅/参见" verb
    if hits >= 1 and _CITE_VERB_RE.search(s) and len(s) < 500:
        return True
    # Long bibliography paragraphs (multi-entry footnote lists, no length cap)
    if hits >= 4:
        return True
    # Continuation of a footnote starting with Latin text (e.g. "Post-Nicene Fathers）...")
    if re.match(r'^[A-Za-z]', s) and hits >= 1:
        return True
    return False


def split_page_body_footnotes(text):
    """
    Split a single page's text into (body_text, footnote_text).
    Primary: footnote section starts at first paragraph with a superscript/circled marker.
    Fallback: scan from end for consecutive bibliography/orphan footnote paragraphs.
    """
    paragraphs = re.split(r'\n{2,}', text.strip())
    if not paragraphs:
        return '', ''

    # Primary: find the FIRST paragraph that starts with a footnote marker
    first_fn_idx = None
    for i, para in enumerate(paragraphs):
        stripped = para.strip()
        if stripped and FN_LINE_RE.match(stripped):
            first_fn_idx = i
            break

    if first_fn_idx is not None:
        # Also absorb any orphan footnote paragraphs immediately before first_fn_idx
        extended_idx = first_fn_idx
        for i in range(first_fn_idx - 1, -1, -1):
            if _is_orphan_footnote_para(paragraphs[i]):
                extended_idx = i
            else:
                break
        body_paras = paragraphs[:extended_idx]
        fn_paras = paragraphs[extended_idx:]
        return '\n\n'.join(p.strip() for p in body_paras if p.strip()), \
               '\n\n'.join(p.strip() for p in fn_paras if p.strip())

    # Fallback: scan from end for orphan bibliography paragraphs
    first_orphan = None
    for i in range(len(paragraphs) - 1, -1, -1):
        if _is_orphan_footnote_para(paragraphs[i]):
            first_orphan = i
        else:
            break
    if first_orphan is not None and first_orphan > 0:
        body_paras = paragraphs[:first_orphan]
        fn_paras = paragraphs[first_orphan:]
        return '\n\n'.join(p.strip() for p in body_paras if p.strip()), \
               '\n\n'.join(p.strip() for p in fn_paras if p.strip())

    return text.strip(), ''


# Characters that mark a definite sentence ending
SENTENCE_END = set('。！？」』"）')
# Characters that are definitely mid-sentence (comma, dash, ellipsis, etc.)
MID_SENTENCE = set('，、；…—')


def last_para_last_char(body_str):
    """Return the last non-empty character of the last paragraph in body_str."""
    paras = re.split(r'\n{2,}', body_str.strip())
    for para in reversed(paras):
        s = para.strip()
        if s:
            return s[-1]
    return ''


def merge_broken_paragraphs(body_text):
    """Post-process: merge adjacent paragraphs where the first ends mid-sentence.

    Rules:
      - Always merge if previous para ends with ，、；…— (clearly mid-sentence)
      - Merge if previous para is long (>25 chars) and ends with a CJK character
        (catches word-breaks like 干犯, 考, 这, 我们 etc.)
      - Do NOT merge short standalone phrases (<= 15 chars) — these are subheadings
    """
    paras = re.split(r'\n{2,}', body_text.strip())
    result = []
    for para in paras:
        para = para.strip()
        if not para:
            continue
        if result:
            prev = result[-1]
            last = prev[-1] if prev else ''
            is_mid = (
                last in MID_SENTENCE
                or (last not in SENTENCE_END
                    and len(prev) > 25
                    and '\u4e00' <= last <= '\u9fff')  # CJK char in long para
            )
            if is_mid:
                result[-1] = prev + para
                continue
        result.append(para)
    return '\n\n'.join(result)


def collect_section(start_page, end_page, skip_header_lines):
    """Collect body text and footnotes for all pages in a section."""
    body_parts = []
    all_footnotes = []

    for pg in range(start_page, end_page + 1):
        text = read_page(pg)
        if not text.strip():
            continue

        lines = text.split('\n')
        while lines and not lines[-1].strip():
            lines.pop()

        if pg == start_page and skip_header_lines > 0:
            lines = lines[skip_header_lines:]

        page_text = '\n'.join(lines)
        body, footnotes = split_page_body_footnotes(page_text)
        if body:
            if body_parts:
                # Check last paragraph of previous body (not just last char,
                # to avoid footnote-continuation text masking the real truncation)
                last_char = last_para_last_char(body_parts[-1])
                if last_char and last_char not in SENTENCE_END:
                    body_parts[-1] = body_parts[-1].rstrip() + '\n' + body
                else:
                    body_parts.append(body)
            else:
                body_parts.append(body)
        if footnotes:
            all_footnotes.append(footnotes)

    combined = '\n\n'.join(body_parts)
    combined = merge_broken_paragraphs(combined)
    return combined, '\n\n'.join(all_footnotes)


def parse_footnotes_block(raw):
    """Parse concatenated footnote text into list of (num_str, text) tuples."""
    if not raw.strip():
        return []

    # Merge all footnote text
    lines = raw.split('\n')
    footnotes = []
    current_num = None
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_lines:
                current_lines.append('')
            continue

        m = re.match(r'^([' + SUP_CHARS + CIRCLE_CHARS + r']+)(.*)', stripped)
        m2 = re.match(r'^(\d{1,2})\s+(.*)', stripped) if not m else None
        if m or m2:
            if current_num is not None:
                text = ' '.join(t for t in current_lines if t)
                footnotes.append((current_num, text))
            if m:
                marker = m.group(1)
                current_num = marker_to_num(marker)
                rest = m.group(2).strip()
            else:
                current_num = m2.group(1)
                rest = m2.group(2).strip()
            current_lines = [rest] if rest else []
        else:
            if current_num is not None:
                current_lines.append(stripped)

    if current_num is not None:
        text = ' '.join(t for t in current_lines if t)
        footnotes.append((current_num, text))

    # Deduplicate by number (keep last occurrence = most complete)
    seen = {}
    for num, text in footnotes:
        seen[num] = text
    # Return in order of appearance
    result = []
    seen_nums = set()
    for num, text in footnotes:
        if num not in seen_nums:
            result.append((num, seen[num]))
            seen_nums.add(num)
    return result


def is_subheading(block):
    """Return True if block looks like a section subheading rather than body text.

    Heuristics:
    - Short (≤ 20 chars after stripping)
    - No sentence-ending punctuation that would indicate a complete statement
    - Not a numbered list item
    - Not purely Latin/English (OCR artifact)
    """
    text = block.strip()
    if len(text) > 20:
        return False
    if re.match(r'^\d+\.\s', text):   # numbered list
        return False
    if re.match(r'^[A-Za-z\s,.\-()（）]+$', text):  # pure Latin text
        return False
    # Must contain at least one CJK character
    if not re.search(r'[\u4e00-\u9fff]', text):
        return False
    return True


def build_body_html(body_text):
    """Convert body text to HTML paragraphs, numbered list items, and subheadings."""
    blocks = [b.strip() for b in re.split(r'\n{2,}', body_text.strip()) if b.strip()]

    # Pass 1: classify each block
    classified = []
    for block in blocks:
        if is_subheading(block):
            classified.append(('heading', None, None, block))
        elif re.match(r'^(\d+)\.\s', block):
            m = re.match(r'^(\d+)\.\s+(.*)', block, re.DOTALL)
            classified.append(('list', m.group(1), '.', m.group(2)))
        elif re.match(r'^（(\d+)）', block):
            m = re.match(r'^（(\d+)）(.*)', block, re.DOTALL)
            classified.append(('list', m.group(1), '()', m.group(2)))
        else:
            classified.append(('plain', None, None, block))

    # Pass 2: merge plain paragraphs sandwiched between two list items into the preceding item
    merged = []
    for i, item in enumerate(classified):
        if item[0] == 'plain':
            prev_is_list = merged and merged[-1][0] == 'list'
            next_is_list = (i + 1 < len(classified) and classified[i + 1][0] == 'list')
            if prev_is_list and next_is_list:
                prev = merged[-1]
                merged[-1] = ('list', prev[1], prev[2], prev[3] + ' ' + item[3])
                continue
        merged.append(item)

    # Pass 3: render HTML
    html_parts = []
    for kind, num, style, content in merged:
        if kind == 'heading':
            html_parts.append(f'<h3 class="reading-subheading">{content}</h3>')
        elif kind == 'list':
            text = re.sub(r'\s+', ' ', content).strip()
            label = f'{num}.' if style == '.' else f'({num})'
            html_parts.append(
                f'<div class="reading-list-item"><span class="list-num">{label}</span>'
                f'<p>{text}</p></div>'
            )
        else:
            text = re.sub(r'\s+', ' ', content).strip()
            html_parts.append(f'<p>{text}</p>')
    return '\n\n'.join(html_parts)


def build_footnotes_html(footnotes):
    """Build footnotes HTML block."""
    if not footnotes:
        return ''
    lines = ['<aside class="reading-footnotes">']
    for num, text in footnotes:
        lines.append(f'<p><sup>{num}</sup> {text}</p>')
    lines.append('</aside>')
    return '\n'.join(lines)


def generate_file(filename, section_key, section_title, start_page, end_page, skip_header_lines):
    body_raw, footnotes_raw = collect_section(start_page, end_page, skip_header_lines)
    body_html = build_body_html(body_raw)
    footnotes = parse_footnotes_block(footnotes_raw)
    footnotes_html = build_footnotes_html(footnotes)

    img = HEADER_IMGS.get(section_key, DEFAULT_IMG)

    content = f"""---
layout: reading-chapter
author_id: murray
author_name: 约翰·慕理
book_id: principles
book_title: 正直生活要道
section: "{section_key}"
section_title: "{section_title}"
header-img: {img}
date: {DATE}
---

{body_html}
"""
    if footnotes_html:
        content += '\n' + footnotes_html + '\n'

    out_path = os.path.join(OUT_DIR, f'{filename}.md')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  写入 {filename}.md  ({start_page}-{end_page}页，body {len(body_html)}字符，脚注 {len(footnotes)}条)')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f'处理 正直生活要道 OCR → {OUT_DIR}')
    for row in SECTIONS:
        generate_file(*row)
    print('完成。')


if __name__ == '__main__':
    main()
