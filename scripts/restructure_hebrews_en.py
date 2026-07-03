#!/usr/bin/env python3
"""restructure_hebrews_en.py — 把 calvin/hebrews-en/*.md 从

    ## Hebrews C:V(-V')?

    <table class="calvin-scripture">
    <thead><tr><th colspan="2" style="text-align:center">Hebrews C:V(-V')?</th></tr></thead>
    <tbody>
    <tr><td><strong>N.</strong> English</td><td><strong>N.</strong>Latin</td></tr>
    ...
    </tbody>
    </table>

转换为 scripture-box + scripture-bilingual 金标准:

    <div class="scripture-box scripture-box--bilingual" markdown="1">
    <p class="scripture-ref">...</p>
    <h2 class="scripture-anchor" ...>...</h2>

    <table class="scripture-bilingual">
    <tbody>
    <tr><td class="scripture-en">...</td><td class="scripture-la">...</td></tr>
    ...
    </tbody>
    </table>
    </div>

用法: python3 scripts/restructure_hebrews_en.py [chapter ...]
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / 'calvin/hebrews-en'
BOOK_NUM = 58
TITLE = 'Hebrews'
UPPER = 'HEBREWS'
ANCHOR_PREFIX = 'hebrews'


BLOCK_RE = re.compile(
    r'^##\s+Hebrews\s+(\d+):(\d+)(?:-(\d+))?\s*\n+'
    r'<table class="calvin-scripture">\s*\n'
    r'<thead>.*?</thead>\s*\n'
    r'<tbody>\s*\n'
    r'((?:<tr><td>.+?</td><td>.+?</td></tr>\s*\n)+)'
    r'</tbody>\s*\n</table>',
    re.M | re.S,
)

ROW_RE = re.compile(
    r'<tr><td>(.+?)</td><td>(.+?)</td></tr>',
    re.S,
)


def md_to_html(s: str) -> str:
    s = s.strip()
    s = re.sub(r'\*\*(\d+)\.\*\*', r'<strong>\1.</strong>', s)
    s = re.sub(r'\*\*([^*]+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', s)
    return s


def convert_block(m: re.Match) -> str:
    ch = int(m.group(1))
    v_from = int(m.group(2))
    v_to = int(m.group(3)) if m.group(3) else v_from
    rows_raw = m.group(4)

    ages_code = f'{BOOK_NUM}{ch:02d}{v_from:02d}'
    vrange = f'{v_from}' if v_from == v_to else f'{v_from}-{v_to}'
    anchor_id = f'{ANCHOR_PREFIX}-{ch}-{v_from}' + (
        f'-{v_to}' if v_from != v_to else ''
    )
    data_ref = f'{UPPER} {ch}:{vrange}'

    new_rows = []
    for rm in ROW_RE.finditer(rows_raw):
        en = md_to_html(rm.group(1))
        la = md_to_html(rm.group(2))
        # Ensure `<strong>N.</strong>` followed by space (hebrews Latin 常无空格贴)
        la = re.sub(r'(<strong>\d+\.</strong>)(?=\S)', r'\1 ', la)
        new_rows.append(
            f'<tr><td class="scripture-en">{en}</td>'
            f'<td class="scripture-la">{la}</td></tr>'
        )

    lines = [
        '<div class="scripture-box scripture-box--bilingual" markdown="1">',
        (f'<p class="scripture-ref"><span class="ages-code">&lt;{ages_code}&gt;</span>'
         f'<span class="book-name">{TITLE}</span> '
         f'<span class="verse-range">{ch}:{vrange}</span></p>'),
        (f'<h2 class="scripture-anchor" id="{anchor_id}" '
         f'data-ref="{data_ref}" style="display:none">{data_ref}</h2>'),
        '',
        '<table class="scripture-bilingual">',
        '<tbody>',
    ] + new_rows + [
        '</tbody>',
        '</table>',
        '',
        '</div>',
    ]
    return '\n'.join(lines)


def process(path: Path) -> int:
    text = path.read_text(encoding='utf-8')
    new_text, n = BLOCK_RE.subn(convert_block, text)
    if n:
        path.write_text(new_text, encoding='utf-8')
    return n


def main():
    args = sys.argv[1:]
    if args:
        files = [SRC_DIR / f'{c}.md' for c in args]
    else:
        files = sorted(
            SRC_DIR.glob('[0-9]*.md'),
            key=lambda p: int(p.stem),
        )
    total = 0
    for f in files:
        if not f.exists():
            print(f'  {f}: 不存在, 跳过')
            continue
        n = process(f)
        print(f'  {f.name}: {n} blocks')
        total += n
    print(f'\nTOTAL: {total} blocks converted')


if __name__ == '__main__':
    main()
