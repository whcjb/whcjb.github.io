#!/usr/bin/env python3
"""
Propagate to all OT chapter files:
1. .mh-verse CSS: font → Ma Shan Zheng, harmonized dark color, size/weight/spacing
2. verse block content → Traditional Chinese 繁体和合本
"""

import os, re, json, colorsys, glob

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mhenry')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load zh_cuv.json
with open(os.path.join(SCRIPT_DIR, 'zh_cuv.json'), encoding='utf-8-sig') as f:
    cuv_list = json.load(f)
CUV = {b['abbrev']: b for b in cuv_list}

# Directory name → zh_cuv abbreviation
BOOK_ABBREV = {
    'genesis': 'gn',    'exodus': 'ex',     'leviticus': 'lv',  'numbers': 'nm',
    'deuteronomy': 'dt','joshua': 'js',      'judges': 'jud',    'ruth': 'rt',
    '1samuel': '1sm',   '2samuel': '2sm',   '1kings': '1kgs',   '2kings': '2kgs',
    '1chronicles': '1ch','2chronicles': '2ch','ezra': 'ezr',     'nehemiah': 'ne',
    'esther': 'et',     'job': 'job',        'psalms': 'ps',     'proverbs': 'prv',
    'ecclesiastes': 'ec','songofsolomon': 'so','isaiah': 'is',   'jeremiah': 'jr',
    'lamentations': 'lm','ezekiel': 'ez',    'daniel': 'dn',     'hosea': 'ho',
    'joel': 'jl',       'amos': 'am',        'obadiah': 'ob',    'jonah': 'jn',
    'micah': 'mi',      'nahum': 'na',       'habakkuk': 'hk',   'zephaniah': 'zp',
    'haggai': 'hg',     'zechariah': 'zc',   'malachi': 'ml',
}

OT_BOOKS = set(BOOK_ABBREV.keys())


# ── helpers ──────────────────────────────────────────────────────────────────

def hsl_to_hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    return '#{:02X}{:02X}{:02X}'.format(round(r * 255), round(g * 255), round(b * 255))


def get_verse_color(content):
    """Derive a readable dark verse color from the book's main text color."""
    m = re.search(r'#mhenry-col \{ color: (#[0-9A-Fa-f]{6})', content)
    if m:
        hx = m.group(1).lstrip('#')
        r, g, b = [int(hx[i:i+2], 16) / 255 for i in (0, 2, 4)]
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        # Keep hue, push to S=58% L=26% for rich readable dark color
        return hsl_to_hex(h * 360, 58, 26)
    return '#1B3A6B'


def replace_verse_content(verse_text, book_dir, chapter_num):
    """Replace simplified Chinese verse text with Traditional Chinese 繁体和合本."""
    abbrev = BOOK_ABBREV.get(book_dir)
    if not abbrev:
        return verse_text
    book = CUV.get(abbrev)
    if not book or chapter_num > len(book['chapters']):
        return verse_text

    chapter = book['chapters'][chapter_num - 1]

    # Extract verse numbers: digit(s) immediately or optionally-space before Chinese char
    verse_nums = list(dict.fromkeys(
        int(m) for m in re.findall(r'(?<!\d)(\d+)\s*[\u4e00-\u9fff]', verse_text)
    ))
    if not verse_nums:
        return verse_text

    verse_nums.sort()
    parts = []
    for v in verse_nums:
        if 1 <= v <= len(chapter):
            text = chapter[v - 1].replace(' ', '').replace('\u3000', '')
            parts.append(f'{v} {text}')

    return ' '.join(parts) if parts else verse_text


# ── per-file processing ───────────────────────────────────────────────────────

def process_file(filepath):
    book_dir = os.path.basename(os.path.dirname(filepath))
    stem = os.path.splitext(os.path.basename(filepath))[0]
    if not stem.isdigit():
        return False
    chapter_num = int(stem)

    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    original = content

    # ── 1. CSS: .mh-verse font / color ──────────────────────────────────────
    verse_color = get_verse_color(content)

    # Replace the 5-line block inside .mh-verse:
    #   color: <any hex>;
    #   font-size: 0.97em;
    #   font-family: "Klee One", ...;
    #   font-weight: 600;
    #   letter-spacing: 0.03em;
    # → updated values
    css_old = (
        r'(\.mh-unit > \.mh-verse \{(?:[^\}]*?\n)*?    )color: #[0-9A-Fa-f]{6};\n'
        r'    font-size: 0\.97em;\n'
        r'    font-family: "Klee One", "STKaiti", "KaiTi", "楷体", serif !important;\n'
        r'    font-weight: 600;\n'
        r'    letter-spacing: 0\.03em;'
    )
    css_new = (
        r'\g<1>color: ' + verse_color + r';\n'
        r'    font-size: 1.05em;\n'
        r'    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", serif !important;\n'
        r'    font-weight: 400;\n'
        r'    letter-spacing: 0.05em;'
    )
    content = re.sub(css_old, css_new, content, count=1, flags=re.DOTALL)

    # ── 2. Verse content → Traditional Chinese ───────────────────────────────
    # Match each <div class="mh-verse"> ... </div> block (single line content)
    def verse_replacer(m):
        inner = m.group(1).strip()
        new_inner = replace_verse_content(inner, book_dir, chapter_num)
        return f'<div class="mh-verse">\n{new_inner}\n</div>'

    content = re.sub(
        r'<div class="mh-verse">\n(.*?)\n</div>',
        verse_replacer,
        content,
        flags=re.DOTALL
    )

    if content == original:
        return False

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    updated = []
    skipped = []
    errors = []

    for book_dir in sorted(OT_BOOKS):
        book_path = os.path.join(BASE, book_dir)
        if not os.path.isdir(book_path):
            continue
        for filepath in sorted(glob.glob(os.path.join(book_path, '*.md'))):
            stem = os.path.splitext(os.path.basename(filepath))[0]
            if not stem.isdigit():
                continue
            try:
                changed = process_file(filepath)
                if changed:
                    updated.append(filepath.replace(BASE + '/', ''))
                else:
                    skipped.append(filepath.replace(BASE + '/', ''))
            except Exception as e:
                errors.append(f'{filepath}: {e}')

    print(f'Updated: {len(updated)} files')
    print(f'Skipped (no change): {len(skipped)} files')
    if errors:
        print(f'Errors: {len(errors)}')
        for e in errors[:20]:
            print(' ', e)
    if updated:
        print('\nSample updated files:')
        for f in updated[:10]:
            print(' ', f)

if __name__ == '__main__':
    main()
