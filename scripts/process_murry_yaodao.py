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

# Footnote starter patterns: superscript ¹²³⁴⁵⁶⁷⁸⁹ OR circled ①②③④⑤⑥⑦⑧⑨⑩...
SUP_CHARS = '¹²³⁴⁵⁶⁷⁸⁹⁰'
CIRCLE_CHARS = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮'
ALL_FN_START = f'[{SUP_CHARS}{CIRCLE_CHARS}]'
FN_LINE_RE = re.compile(r'^' + ALL_FN_START)

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


def split_page_body_footnotes(text):
    """
    Split a single page's text into (body_text, footnote_text).
    Footnote section starts at the LAST block that begins with a footnote marker.
    A "block" is separated by blank lines.
    """
    # Split into paragraphs
    paragraphs = re.split(r'\n{2,}', text.strip())
    if not paragraphs:
        return '', ''

    # Find the FIRST paragraph that starts with a footnote marker
    first_fn_idx = None
    for i, para in enumerate(paragraphs):
        stripped = para.strip()
        if stripped and FN_LINE_RE.match(stripped):
            first_fn_idx = i
            break

    if first_fn_idx is None:
        return text.strip(), ''

    # Everything from first_fn_idx onward is footnotes
    body_paras = paragraphs[:first_fn_idx]
    fn_paras = paragraphs[first_fn_idx:]
    return '\n\n'.join(p.strip() for p in body_paras if p.strip()), \
           '\n\n'.join(p.strip() for p in fn_paras if p.strip())


# Characters that mark a sentence ending (used to detect mid-sentence page breaks)
SENTENCE_END = '。！？」』"'

def collect_section(start_page, end_page, skip_header_lines):
    """Collect body text and footnotes for all pages in a section.

    When a page ends mid-sentence (last char is not a sentence-ending punctuation),
    the next page's first paragraph is merged into the same paragraph rather than
    starting a new one.
    """
    body_parts = []
    all_footnotes = []

    for pg in range(start_page, end_page + 1):
        text = read_page(pg)
        if not text.strip():
            continue

        lines = text.split('\n')
        # Remove trailing blank lines
        while lines and not lines[-1].strip():
            lines.pop()

        # Skip chapter header lines on first page
        if pg == start_page and skip_header_lines > 0:
            lines = lines[skip_header_lines:]

        page_text = '\n'.join(lines)
        body, footnotes = split_page_body_footnotes(page_text)
        if body:
            if body_parts:
                # Check if previous body ended mid-sentence
                prev = body_parts[-1].rstrip()
                last_char = prev[-1] if prev else ''
                if last_char and last_char not in SENTENCE_END:
                    # Merge: strip trailing newlines from prev and prepend next body
                    # with single newline so they stay in the same paragraph block
                    body_parts[-1] = prev + '\n' + body
                else:
                    body_parts.append(body)
            else:
                body_parts.append(body)
        if footnotes:
            all_footnotes.append(footnotes)

    return '\n\n'.join(body_parts), '\n\n'.join(all_footnotes)


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
        if m:
            if current_num is not None:
                text = ' '.join(t for t in current_lines if t)
                footnotes.append((current_num, text))
            marker = m.group(1)
            current_num = marker_to_num(marker)
            rest = m.group(2).strip()
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


def build_body_html(body_text):
    """Convert body text to HTML paragraphs and numbered list items."""
    blocks = re.split(r'\n{2,}', body_text.strip())
    html_parts = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Check if block is a numbered list item (starts with digit + dot + space)
        m = re.match(r'^(\d+)\.\s+(.*)', block, re.DOTALL)
        if m:
            num = m.group(1)
            content = re.sub(r'\s+', ' ', m.group(2)).strip()
            html_parts.append(
                f'<div class="reading-list-item"><span class="list-num">{num}.</span>'
                f'<p>{content}</p></div>'
            )
        else:
            content = re.sub(r'\s+', ' ', block).strip()
            html_parts.append(f'<p>{content}</p>')
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
