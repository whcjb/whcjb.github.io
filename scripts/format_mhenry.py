#!/usr/bin/env python3
"""
Batch format Matthew Henry commentary .md files.
Adds proper Markdown structure: headings, blockquotes for scripture,
footnotes, and clean paragraph separation.
"""

import re
import os
import glob

MHENRY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mhenry')


def split_frontmatter(text):
    """Split YAML front matter from body content."""
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            return '---' + parts[1] + '---', parts[2]
    return '', text


def is_chapter_heading(line):
    """Detect chapter headings like '第一章'."""
    return bool(re.match(r'^第[一二三四五六七八九十百零\d]+章\s*$', line.strip()))


def is_section_title(line):
    """Detect short section titles (non-numbered, short, no punctuation ending)."""
    s = line.strip()
    if not s or len(s) > 25 or len(s) < 2:
        return False
    if re.match(r'^[\d\(（\[I]', s):
        return False
    if s[-1] in '。，；：！？、）)】]"\'':
        return False
    if re.search(r'[。，；]', s):
        return False
    # Short line without ending punctuation -> likely a title
    return True


def is_verse_block_start(line):
    """Detect scripture verse lines: start with number(s) followed by text."""
    return bool(re.match(r'^\d{1,3}\s+\S', line.strip()))


def is_footnote_number(line):
    """Detect standalone footnote number like '1' or '2'."""
    return bool(re.match(r'^\d{1,2}\s*$', line.strip()))


def is_outline_roman(line):
    """Detect outline markers like I. II. III."""
    s = line.strip()
    return bool(re.match(r'^(I{1,3}V?|IV|VI{0,3}|[IVX]+)\.\s', s))


def is_date_marker(line):
    """Detect date markers like '创造（主前 4004 年）'."""
    s = line.strip()
    return bool(re.match(r'^.{2,8}（主[前后]\s*\d+\s*年）$', s))


def format_body(body: str) -> str:
    """Minimal formatting: remove headers, blockquote verses, collect footnotes.
    Outline hierarchy (I. 1. (1)) is handled by client-side JS."""
    lines = body.split('\n')
    result: list[str] = []
    footnotes: list[tuple[str, str]] = []
    i = 0
    total = len(lines)

    while i < total:
        stripped = lines[i].strip()

        if not stripped:
            if result and result[-1] != '':
                result.append('')
            i += 1
            continue

        # Remove PDF running headers
        if is_date_marker(stripped):
            i += 1
            continue

        # Footnote: standalone number + preceding or following short text
        if is_footnote_number(stripped):
            fn_num = stripped
            # Look ahead for footnote content
            fn_lines: list[str] = []
            j = i + 1
            while j < total and not lines[j].strip():
                j += 1
            while j < total:
                ns = lines[j].strip()
                if not ns or is_verse_block_start(lines[j]) or is_chapter_heading(ns):
                    break
                fn_lines.append(ns)
                j += 1
                if len(fn_lines) >= 4:
                    break
            # Check backward: previous short line might be footnote text
            if not fn_lines:
                k = len(result) - 1
                while k >= 0 and result[k] == '':
                    k -= 1
                if k >= 0 and len(result[k]) <= 150 and not result[k].startswith(('>', '#', '<')):
                    fn_text = result.pop(k)
                    # clean trailing blanks
                    while result and result[-1] == '':
                        result.pop()
                    footnotes.append((fn_num, fn_text))
                    i += 1
                    continue
            if fn_lines:
                fn_text = ' '.join(fn_lines)
                if len(fn_text) <= 300:
                    footnotes.append((fn_num, fn_text))
                    i = j
                    continue

        # Chapter heading
        if is_chapter_heading(stripped):
            result.append('')
            result.append(f'## {stripped}')
            result.append('')
            i += 1
            continue

        # Scripture verse block
        if is_verse_block_start(stripped):
            verse_parts = [stripped]
            j = i + 1
            while j < total:
                ns = lines[j].strip()
                if not ns:
                    k = j + 1
                    while k < total and not lines[k].strip():
                        k += 1
                    if k < total and is_verse_block_start(lines[k]):
                        j = k
                        continue
                    break
                if is_verse_block_start(ns):
                    verse_parts.append(ns)
                    j += 1
                elif not re.match(r'^\d', ns) and not is_chapter_heading(ns) and not is_section_title(ns):
                    peek = j + 1
                    if peek < total and lines[peek].strip() and not is_verse_block_start(lines[peek]):
                        break
                    verse_parts[-1] += ' ' + ns
                    j += 1
                else:
                    break
            result.append('')
            for vp in verse_parts:
                result.append(f'> {vp}')
            result.append('')
            i = j
            continue

        # Section title
        if is_section_title(stripped):
            result.append('')
            result.append(f'### {stripped}')
            result.append('')
            i += 1
            continue

        # Regular text
        result.append(stripped)
        i += 1

    # Footnotes at end
    if footnotes:
        result.append('')
        result.append('<aside class="mhenry-footnotes">')
        for fn_num, fn_text in footnotes:
            result.append(f'<p><sup>{fn_num}</sup> {fn_text}</p>')
        result.append('</aside>')

    # Clean consecutive blank lines
    cleaned: list[str] = []
    prev_blank = False
    for line in result:
        if line == '':
            if not prev_blank:
                cleaned.append('')
            prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False

    return '\n'.join(cleaned).strip()


def process_file(filepath):
    """Process a single .md file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    frontmatter, body = split_frontmatter(content)
    if not frontmatter:
        return False

    formatted = format_body(body)
    new_content = frontmatter + '\n\n' + formatted + '\n'

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False


def main():
    import sys
    # If argument given, process only that file; otherwise process all
    if len(sys.argv) > 1:
        target = sys.argv[1]
        filepath = os.path.join(MHENRY_DIR, target)
        if not os.path.exists(filepath):
            print(f'File not found: {filepath}')
            return
        md_files = [filepath]
    else:
        md_files = sorted(glob.glob(os.path.join(MHENRY_DIR, '**', '*.md'), recursive=True))

    print(f'Processing {len(md_files)} file(s)')

    changed = 0
    errors = 0
    for filepath in md_files:
        try:
            if process_file(filepath):
                changed += 1
                print(f'  formatted: {os.path.relpath(filepath, MHENRY_DIR)}')
        except Exception as e:
            errors += 1
            print(f'  ERROR: {os.path.relpath(filepath, MHENRY_DIR)}: {e}')

    print(f'Done. {changed}/{len(md_files)} files updated, {errors} errors.')


if __name__ == '__main__':
    main()
