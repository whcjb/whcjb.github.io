#!/usr/bin/env python3
"""
Process Matthew Henry's Bible Commentary PDFs into Jekyll markdown files.
Usage:
    python3 scripts/process_henry.py <book> <chapter>
    python3 scripts/process_henry.py genesis 1

PDF source: ~/Documents/论文/matthew_henry/
Output: reading/henry/<book>/<chapter>.md

Font conventions in the PDFs:
  FangSong  = regular body text
  KaiTi     = scripture quotation
  Calibri   = structural markers (I. II. 1. 2. (1) etc.) and numbers inline
"""

import os, re, sys
import fitz  # PyMuPDF

PDF_DIR = os.path.expanduser('~/Documents/论文/matthew_henry')
OUT_BASE = os.path.join(os.path.dirname(__file__), '../reading/henry')

# ── Book registry ───────────────────────────────────────────────────────────
BOOKS = {
    'genesis': {
        'pdf':        '01马太亨利完整圣经注释-创世记01-20.pdf',
        'title':      '创世记',
        'header_img': 'mhenry-book-1.jpg',
        # chapter -> (start_pdf_page, end_pdf_page)  1-indexed
        'chapters': {
            1:  (3, 11),
            2:  (12, 18),
            3:  (19, 26),
            # add more as needed
        },
    },
}

DATE = '2026-05-16 15:12'


# ── PDF text extraction ──────────────────────────────────────────────────────

def extract_chapter_paragraphs(pdf_path, start_page, end_page):
    """
    Extract paragraphs from PDF pages [start_page, end_page] (1-indexed).
    Each PDF block = one paragraph.
    Returns list of {'text': str, 'fonts': set}.
    """
    doc = fitz.open(pdf_path)
    paragraphs = []

    for page_idx in range(start_page - 1, end_page):
        page = doc[page_idx]
        blocks = page.get_text('dict')['blocks']

        for block in blocks:
            if block.get('type') != 0:
                continue

            block_text = ''
            block_fonts = set()

            for line in block.get('lines', []):
                line_spans = line.get('spans', [])
                line_text = ''.join(s['text'] for s in line_spans).strip()

                # Skip page header lines
                if re.match(r'^马太亨利完整圣经注释', line_text):
                    block_text = ''  # discard whole block
                    break
                if re.match(r'^第\d+\s*页\s*$', line_text):
                    block_text = ''
                    break
                if re.match(r'^第[一二三四五六七八九十百]+章\s*$', line_text):
                    block_text = ''
                    break

                for span in line_spans:
                    t = span['text']
                    if t.strip():
                        block_text += t
                        block_fonts.add(span['font'])

            text = block_text.strip()
            if text:
                paragraphs.append({'text': text, 'fonts': block_fonts})

    return paragraphs


# ── Structure detection ──────────────────────────────────────────────────────

# Section heading: line starting with Roman numeral from Calibri font
_ROMAN_SECTION_RE = re.compile(r'^(I{1,3}|IV|V?I{0,3}|VI{0,3}|IX|X{0,3})\.')
# Scripture date/label line: e.g. "创造（主前4004 年）"
_DATE_LABEL_RE = re.compile(r'^[^，。；：]+（主[前后]\d+\s*年）\s*$')
# Footnote marker in text: superscript digits at end (rendered as plain digit + small)
_FOOTNOTE_BOTTOM_RE = re.compile(r'^\d{1,2}[\s\u4e00-\u9fff].{4,}')  # "1 这是..." or "1这是..."


def classify_para(para_text):
    """Return one of: 'header', 'scripture', 'date_label', 'footnote', 'body'"""
    t = para_text.strip()
    if _DATE_LABEL_RE.match(t):
        return 'date_label'
    if _FOOTNOTE_BOTTOM_RE.match(t) and len(t) < 300:
        return 'footnote'
    return 'body'


def is_scripture_para(para):
    """KaiTi font = scripture quotation."""
    return 'KaiTi' in para['fonts'] and 'FangSong' not in para['fonts']


# ── HTML rendering ───────────────────────────────────────────────────────────

# Section structure markers inline in body text: "I.xxx" "1.xxx" "(1)xxx"
_INLINE_ROMAN_RE = re.compile(r'(?<!\w)(I{1,3}|IV|V?I{0,3}|VI{0,3}|IX|X{0,3})\.')
_INLINE_NUM_RE   = re.compile(r'(?<!\w)(\d{1,2})\.')
_INLINE_PAREN_RE = re.compile(r'（(\d+)）|(?<!\d)\((\d+)\)')


def soft_wrap(text):
    """Remove single soft line-breaks (OCR/PDF line-wrap) within a paragraph."""
    # Join lines that don't end with sentence-final punctuation
    lines = text.split('\n')
    merged = ''
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if merged and not merged[-1] in '。！？」』"）…':
            merged += line
        else:
            merged += line
    return merged


def render_inline(text):
    """Escape HTML special chars (minimal)."""
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return text


def para_to_html(para):
    """Convert a paragraph dict to HTML string(s)."""
    t = soft_wrap(para['text'])

    # Scripture font check takes priority over all text-pattern checks
    if is_scripture_para(para):
        # Scripture: may contain verse numbers like "1 起初，神创造天地。2 地是..."
        # Split into individual verses
        # Verse numbers are plain digits at word boundaries
        parts = re.split(r'(?<!\d)(\d{1,3})\s+', t)
        if len(parts) > 1:
            html = '<div class="henry-scripture">\n'
            i = 1
            while i < len(parts):
                vnum = parts[i]
                vtext = parts[i+1].strip() if i+1 < len(parts) else ''
                html += f'<span class="verse"><sup class="vnum">{vnum}</sup>{render_inline(vtext)}</span> '
                i += 2
            html += '\n</div>\n'
            return html
        else:
            return f'<div class="henry-scripture">{render_inline(t)}</div>\n'

    kind = classify_para(t)
    if kind == 'date_label':
        return f'<p class="henry-date-label">{render_inline(t)}</p>\n'

    if kind == 'footnote':
        m = re.match(r'^(\d{1,2})\s*(.*)', t, re.DOTALL)
        if m:
            num, body = m.group(1), soft_wrap(m.group(2))
            return f'<p class="henry-footnote"><sup>{num}</sup> {render_inline(body)}</p>\n'
        return f'<p class="henry-footnote">{render_inline(t)}</p>\n'

    # Body paragraph — detect structural markers
    # Check if paragraph starts with Roman numeral section (I. / II. / III.)
    m = re.match(r'^((?:I{1,3}|IV|V?I{0,3}|VI{0,3}|IX|X{0,3}))\.\s*(.*)', t, re.DOTALL)
    if m:
        roman, rest = m.group(1), soft_wrap(m.group(2))
        return (f'<h3 class="henry-section">{roman}.</h3>\n'
                f'<p>{render_inline(rest)}</p>\n')

    # Numbered list item: "1.xxx" or "2.xxx"
    m = re.match(r'^(\d{1,2})\.\s*(.*)', t, re.DOTALL)
    if m:
        num, rest = m.group(1), soft_wrap(m.group(2))
        return (f'<div class="henry-list-item"><span class="list-num">{num}.</span>'
                f'<p>{render_inline(rest)}</p></div>\n')

    return f'<p>{render_inline(t)}</p>\n'


def build_html(paragraphs):
    html_parts = []
    footnote_parts = []

    for para in paragraphs:
        t = para['text'].strip()
        if not t:
            continue

        # Scripture font takes priority over any text-pattern classification
        if is_scripture_para(para):
            html_parts.append(para_to_html(para))
            continue

        kind = classify_para(t)
        if kind == 'footnote':
            footnote_parts.append(para_to_html(para))
        else:
            html_parts.append(para_to_html(para))

    if footnote_parts:
        html_parts.append('<div class="henry-footnotes">\n')
        html_parts.extend(footnote_parts)
        html_parts.append('</div>\n')

    return ''.join(html_parts)


# ── Front matter ─────────────────────────────────────────────────────────────

def make_front_matter(book_key, book_info, chapter_num):
    return f"""---
layout: reading-chapter
author_id: henry
author_name: 马太亨利
book_id: {book_key}
book_title: {book_info['title']}注释
section: "{chapter_num}"
section_title: "第{chapter_num}章"
header-img: {book_info.get('header_img', 'mhenry-book-1.jpg')}
date: {DATE}
---

"""


# ── Main ─────────────────────────────────────────────────────────────────────

def process_chapter(book_key, chapter_num):
    book = BOOKS[book_key]
    ch = book['chapters'].get(chapter_num)
    if not ch:
        print(f'Chapter {chapter_num} not defined for {book_key}')
        sys.exit(1)

    pdf_path = os.path.join(PDF_DIR, book['pdf'])
    start_p, end_p = ch

    print(f'Extracting {book_key} ch.{chapter_num} pages {start_p}-{end_p}...')
    paragraphs = extract_chapter_paragraphs(pdf_path, start_p, end_p)
    print(f'  {len(paragraphs)} paragraphs')

    html = build_html(paragraphs)

    out_dir = os.path.join(OUT_BASE, book_key)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'{chapter_num}.md')

    front = make_front_matter(book_key, book, chapter_num)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(front)
        f.write(html)

    print(f'  写入 {out_path}')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    book_key    = sys.argv[1].lower()
    chapter_num = int(sys.argv[2])
    process_chapter(book_key, chapter_num)
