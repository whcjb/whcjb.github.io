#!/usr/bin/env python3
"""
Inject mh-date-heading divs into Matthew Henry commentary chapter files.

Case 1: Files WITH mh-unit blocks but WITHOUT mh-date-heading
  → scan PDF(s), extract date labels per chapter, inject before each <div class="mh-unit">

Case 2: Files WITHOUT mh-unit blocks that contain plain-text date label lines
  → wrap standalone date-label lines with <div class="mh-date-heading">LINE</div>
"""

import os
import re
import sys

import fitz  # PyMuPDF

PDF_DIR = os.path.expanduser('~/Documents/论文/matthew_henry')
MHENRY_DIR = os.path.expanduser('~/Documents/whcjb.github.io/mhenry')

BOOK_PDF_MAP = {
    'genesis': ['01马太亨利完整圣经注释-创世记01-20.pdf', '01马太亨利完整圣经注释-创世记21-50.pdf'],
    'exodus': ['02马太亨利完整圣经注释-出埃及记.pdf'],
    'leviticus': ['03马太亨利完整圣经注释-利未记.pdf'],
    'numbers': ['04马太亨利完整圣经注释-民数记.pdf'],
    'deuteronomy': ['05马太亨利完整圣经注释-申命记.pdf'],
    'joshua': ['06马太亨利完整圣经注释-约书亚记.pdf'],
    'judges': ['07马太亨利完整圣经注释-士师记.pdf'],
    'ruth': ['08马太亨利完整圣经注释-路得记.pdf'],
    '1samuel': ['09马太亨利完整圣经注释-撒母耳记上.pdf'],
    '2samuel': ['10马太亨利完整圣经注释-撒母耳记下.pdf'],
    '1kings': ['11马太亨利完整圣经注释-列王纪上.pdf'],
    '2kings': ['12马太亨利完整圣经注释-列王纪下.pdf'],
    '1chronicles': ['13马太亨利完整圣经注释-历代志上.pdf'],
    '2chronicles': ['14马太亨利完整圣经注释-历代志下.pdf'],
    'ezra': ['15马太亨利完整圣经注释-以斯拉记.pdf'],
    'nehemiah': ['16马太亨利完整圣经注释-尼希米记.pdf'],
    'esther': ['17马太亨利完整圣经注释-以斯帖记.pdf'],
    'job': ['18马太亨利完整圣经注释 约伯记01-21.pdf', '18马太亨利完整圣经注释 约伯记22-42.pdf'],
    'psalms': [
        '19马太亨利完整圣经注释-诗篇（卷1）001-041.pdf',
        '19马太亨利完整圣经注释-诗篇（卷2）042-072.pdf',
        '19马太亨利完整圣经注释-诗篇（卷3）073-089.pdf',
        '19马太亨利完整圣经注释-诗篇（卷4）090-106.pdf',
        '19马太亨利完整圣经注释-诗篇（卷5）107-150.pdf',
    ],
    'proverbs': ['20马太亨利完整圣经注释 箴言01-16.pdf', '20马太亨利完整圣经注释 箴言17-31.pdf'],
    'ecclesiastes': ['21马太亨利完整圣经注释 传道书.pdf'],
    'songofsolomon': ['22马太亨利完整圣经注释 雅歌.pdf'],
    'isaiah': [
        '23马太亨利完整圣经注释-以赛亚书01-25.pdf',
        '23马太亨利完整圣经注释-以赛亚书26-47.pdf',
        '23马太亨利完整圣经注释-以赛亚书48-66.pdf',
    ],
    'jeremiah': ['24马太亨利完整圣经注释-耶利米书.pdf'],
    'lamentations': ['25马太亨利完整圣经注释-耶利米哀歌.pdf'],
    'ezekiel': ['26马太亨利完整圣经注释-以西结书.pdf'],
    'daniel': ['27马太亨利完整圣经注释-但以理书.pdf'],
    'hosea': ['28马太亨利完整圣经注释-何西阿书.pdf'],
    'joel': ['29马太亨利完整圣经注释-约珥书.pdf'],
    'amos': ['30马太亨利完整圣经注释-阿摩司书.pdf'],
    'obadiah': ['31马太亨利完整圣经注释-俄巴底亚书.pdf'],
    'jonah': ['32马太亨利完整圣经注释-约拿书.pdf'],
    'micah': ['33马太亨利完整圣经注释-弥迦书.pdf'],
    'nahum': ['34马太亨利完整圣经注释-那鸿书.pdf'],
    'habakkuk': ['马太亨利完整圣经注释-哈巴谷书.pdf'],
    'zephaniah': ['马太亨利完整圣经注释-西番雅书.pdf'],
    'haggai': ['马太亨利完整圣经注释-哈该书.pdf'],
    'zechariah': ['马太亨利完整圣经注释-撒迦利亚书.pdf'],
    'matthew': [
        '40马太亨利完整圣经注释-马太福音（01-10）.pdf',
        '40马太亨利完整圣经注释-马太福音（11-20）.pdf',
        '40马太亨利完整圣经注释-马太福音（21-28）.pdf',
    ],
    'mark': ['41马太亨利完整圣经注释-马可福音.pdf'],
    'luke': ['42马太亨利完整圣经注释-路加福音.pdf'],
    'john': ['43马太亨利圣经注释：约翰福音.pdf'],
    'acts': [
        '44马太亨利完整圣经注释-使徒行传（第01-14章）.pdf',
        '44马太亨利完整圣经注释-使徒行传（第15-28章）.pdf',
    ],
    'romans': ['45马太亨利圣经注释：罗马书.pdf'],
    '1corinthians': ['46马太亨利完整圣经注释（哥林多前书）.pdf'],
    '2corinthians': ['47马太亨利完整圣经注释（哥林多后书）.pdf'],
    'philemon': ['57马太亨利圣经注释：腓利门书.pdf'],
    'hebrews': ['58马太亨利完整圣经注释-希伯来书.pdf'],
    '1peter': ['60马太亨利完整圣经注释-彼得前书.pdf'],
    '2peter': ['61马太亨利完整圣经注释-彼得后书.pdf'],
    'revelation': ['66马太亨利完整圣经注释（启示录）.pdf'],
}

# Regex for chapter headings in PDF text blocks
# Matches:
#   第一章        (standalone)
#   第X章         (possibly preceded by book name: 创世记第一章, 哥林多前书第一章, etc.)
CHAPTER_HEADING_RE = re.compile(
    r'(?:^|[\u4e00-\u9fff])第([一二三四五六七八九十百零]+)\s*章\s*$'
)
# Also match short standalone patterns
CHAPTER_HEADING_STRICT_RE = re.compile(r'^第([一二三四五六七八九十百零]+)\s*章\s*$')

# Psalms uses 篇 instead of 章
PSALM_HEADING_RE = re.compile(r'(?:^|[\u4e00-\u9fff])第([一二三四五六七八九十百零]+)\s*篇\s*$')
PSALM_HEADING_STRICT_RE = re.compile(r'^第([一二三四五六七八九十百零]+)\s*篇\s*$')

# Regex for date labels in PDF
DATE_LABEL_RE = re.compile(r'（主[前后]\s*\d+\s*年）')

# Regex for header/footer noise in PDFs
HEADER_NOISE_RE = re.compile(r'^马太亨利')
PAGE_NUM_RE = re.compile(r'^第\d+\s*页\s*$')

# Regex for plain-text date label lines in .md files (Case 2)
# Allow optional space between 前/后 and year digits
PLAIN_DATE_LINE_RE = re.compile(r'^.{4,80}（主[前后]\s*\d+\s*年）$')


def chinese_to_int(s: str) -> int:
    """Convert Chinese numeral string to integer. Handles up to 999."""
    cn = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100,
    }
    s = s.strip()
    if not s:
        return 0

    total = 0
    # Handle hundreds
    if '百' in s:
        parts = s.split('百', 1)
        hundreds_char = parts[0]
        hundreds = cn.get(hundreds_char, 0) if hundreds_char and hundreds_char != '零' else 1
        total += hundreds * 100
        s = parts[1]

    # Handle tens and units
    if '十' in s:
        parts = s.split('十', 1)
        tens_char = parts[0]
        units_char = parts[1]

        if not tens_char or tens_char == '零':
            tens = 1 if not tens_char else 0
        else:
            tens = cn.get(tens_char, 0)

        total += tens * 10
        if units_char:
            uc = units_char.lstrip('零')
            if uc:
                total += cn.get(uc, 0)
    else:
        s2 = s.lstrip('零')
        if s2:
            total += cn.get(s2, 0)

    return total


def is_chapter_heading(text: str, use_pian: bool = False) -> int:
    """
    Check if text block is a chapter heading.
    Returns chapter number (int) or 0 if not a heading.

    Handles formats:
      第一章            → strict match
      创世记第一章      → book name prefix
      哥林多前书第一章  → book name prefix
    Also handles 篇 for psalms if use_pian=True.
    """
    text = text.strip()

    heading_re = PSALM_HEADING_STRICT_RE if use_pian else CHAPTER_HEADING_STRICT_RE
    broader_re = PSALM_HEADING_RE if use_pian else CHAPTER_HEADING_RE

    # Strict match: exactly "第X章" (maybe with leading 第X章 after book name)
    m = heading_re.match(text)
    if m:
        n = chinese_to_int(m.group(1))
        return n

    # Broader: ends with 第X章, and block is short (< 15 chars)
    if len(text) <= 15:
        m = broader_re.search(text)
        if m:
            n = chinese_to_int(m.group(1))
            return n

    return 0


def extract_chapter_labels_from_pdfs(book: str) -> dict:
    """
    Scan all PDFs for a book sequentially.
    Returns dict: {chapter_number (int): [label_string, ...]}
    """
    pdf_files = BOOK_PDF_MAP.get(book, [])
    chapter_labels: dict[int, list[str]] = {}
    current_chapter = 0
    use_pian = (book == 'psalms')

    for pdf_name in pdf_files:
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        if not os.path.exists(pdf_path):
            print(f'  WARNING: PDF not found: {pdf_path}')
            continue

        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text('blocks')
            for block in blocks:
                # block = (x0, y0, x1, y1, text, block_no, block_type)
                text = block[4].strip()
                if not text:
                    continue

                # Skip header/footer noise
                if HEADER_NOISE_RE.search(text):
                    continue
                if PAGE_NUM_RE.match(text):
                    continue

                # Detect chapter heading
                ch_num = is_chapter_heading(text, use_pian=use_pian)
                if ch_num > 0:
                    current_chapter = ch_num
                    continue

                # Collect date labels (only if we've seen a chapter heading)
                if current_chapter > 0:
                    for line in text.split('\n'):
                        line = line.strip()
                        if DATE_LABEL_RE.search(line):
                            # Label should be reasonably short (not body text)
                            if len(line) <= 80:
                                if current_chapter not in chapter_labels:
                                    chapter_labels[current_chapter] = []
                                chapter_labels[current_chapter].append(line)

        doc.close()

    return chapter_labels


def apply_case1(book: str, book_dir: str, chapter_labels: dict) -> int:
    """
    For each chapter file: inject mh-date-heading divs before mh-unit blocks.
    Returns count of files modified.
    """
    modified = 0
    chapter_files = sorted(
        [f for f in os.listdir(book_dir) if f.endswith('.md') and f != 'preface.md'],
        key=lambda x: int(x.replace('.md', ''))
    )

    for fname in chapter_files:
        ch_num = int(fname.replace('.md', ''))
        fpath = os.path.join(book_dir, fname)

        with open(fpath, encoding='utf-8') as f:
            content = f.read()

        # Skip if already has mh-date-heading
        if 'mh-date-heading' in content:
            continue

        # Check if file has mh-unit blocks
        unit_count = content.count('<div class="mh-unit">')
        if unit_count == 0:
            continue

        # Get labels for this chapter
        labels = chapter_labels.get(ch_num, [])
        if len(labels) == 0:
            print(f'  [{book}] Chapter {ch_num}: no labels found in PDF, skipping')
            continue

        if len(labels) > unit_count:
            print(f'  WARNING [{book}] Chapter {ch_num}: {len(labels)} labels > {unit_count} units, skipping')
            continue

        # Inject: replace each '<div class="mh-unit">' with date-heading + unit div
        result = []
        remaining = content
        label_idx = 0
        unit_marker = '<div class="mh-unit">'

        while unit_marker in remaining and label_idx < len(labels):
            pos = remaining.index(unit_marker)
            result.append(remaining[:pos])
            result.append(f'<div class="mh-date-heading">{labels[label_idx]}</div>\n\n')
            result.append(unit_marker)
            remaining = remaining[pos + len(unit_marker):]
            label_idx += 1

        result.append(remaining)
        new_content = ''.join(result)

        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f'  [{book}] Chapter {ch_num}: injected {len(labels)} label(s)')
        modified += 1

    return modified


def apply_case2(book: str, book_dir: str) -> int:
    """
    For files: wrap plain-text date label lines with mh-date-heading divs.
    Only applies to lines that are standalone date labels (not in body text).
    Returns count of files modified.
    """
    modified = 0
    chapter_files = sorted(
        [f for f in os.listdir(book_dir) if f.endswith('.md') and f != 'preface.md'],
        key=lambda x: int(x.replace('.md', ''))
    )

    for fname in chapter_files:
        fpath = os.path.join(book_dir, fname)

        with open(fpath, encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        file_changed = False

        for line in lines:
            stripped = line.rstrip('\n')
            # Check if this is a plain-text date label line (not already wrapped)
            if PLAIN_DATE_LINE_RE.match(stripped):
                # Make sure it's not already in a div
                if not stripped.startswith('<div') and not stripped.startswith('</div'):
                    new_line = f'<div class="mh-date-heading">{stripped}</div>\n'
                    new_lines.append(new_line)
                    file_changed = True
                    continue
            new_lines.append(line)

        if file_changed:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f'  [{book}] {fname}: wrapped plain-text date labels (Case 2)')
            modified += 1

    return modified


def process_book(book: str) -> int:
    """Process one book. Returns total files modified."""
    book_dir = os.path.join(MHENRY_DIR, book)
    if not os.path.isdir(book_dir):
        return 0

    # Check if book has chapter files
    chapter_files = [f for f in os.listdir(book_dir)
                     if f.endswith('.md') and f != 'preface.md']
    if not chapter_files:
        return 0

    print(f'\nProcessing: {book}')
    total_modified = 0

    if book in BOOK_PDF_MAP:
        # Extract chapter labels from PDF(s)
        print(f'  Scanning PDFs...')
        chapter_labels = extract_chapter_labels_from_pdfs(book)
        chaps_with_labels = sorted(chapter_labels.keys())
        if len(chaps_with_labels) > 10:
            print(f'  Found labels for {len(chaps_with_labels)} chapters: {chaps_with_labels[:10]}...')
        else:
            print(f'  Found labels for chapters: {chaps_with_labels}')

        # Case 1: inject into mh-unit files
        modified1 = apply_case1(book, book_dir, chapter_labels)
        total_modified += modified1

        # Case 2: also apply to any files without mh-unit (may have plain-text labels)
        modified2 = apply_case2(book, book_dir)
        total_modified += modified2
    else:
        # No PDF mapping - only apply Case 2
        print(f'  No PDF mapping - applying Case 2 only')
        modified2 = apply_case2(book, book_dir)
        total_modified += modified2

    if total_modified == 0:
        print(f'  No changes needed.')

    return total_modified


def main():
    print('=== inject_date_headings.py ===')
    print(f'MHENRY_DIR: {MHENRY_DIR}')
    print(f'PDF_DIR:    {PDF_DIR}')
    print()

    total_files = 0
    books_processed = 0

    all_books = sorted([
        d for d in os.listdir(MHENRY_DIR)
        if os.path.isdir(os.path.join(MHENRY_DIR, d))
    ])

    for book in all_books:
        # Skip malachi (already has mh-date-heading)
        if book == 'malachi':
            print(f'\nSkipping malachi (already processed)')
            continue

        n = process_book(book)
        if n > 0:
            total_files += n
            books_processed += 1

    print(f'\n=== DONE ===')
    print(f'Total files modified: {total_files} across {books_processed} books')


if __name__ == '__main__':
    main()
