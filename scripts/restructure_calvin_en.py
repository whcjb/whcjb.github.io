#!/usr/bin/env python3
"""restructure_calvin_en.py — 把 calvin/<book>-en/*.md 中已存在 scripture-anchor
h2 + `<table class="scripture-table calvin-parallel">` 结构（1john / jude / philemon
/ 2timothy / 2thess 系）以及 OLD-Ages 无表结构（1thess/1timothy/titus 系）
统一转换成 1cor gold 结构：

    <div class="scripture-box scripture-box--bilingual" markdown="1">
    <p class="scripture-ref"><span class="ages-code">&lt;NNCCVV&gt;</span>
      <span class="book-name">{TITLE}</span> <span class="verse-range">{C:V}</span></p>
    <h2 class="scripture-anchor" id="..." data-ref="..." style="display:none">...</h2>

    <table class="scripture-bilingual">
    <tbody>
    <tr><td class="scripture-en"><strong>N.</strong> English</td>
        <td class="scripture-la"><strong>N.</strong> Latin</td></tr>
    ...
    </tbody>
    </table>

    </div>

同时把首节裸对 (`**N.** English` + `<p text-align:right>N. Latin</p>`) 合并进
table。

用法:
    python3 scripts/restructure_calvin_en.py 1timothy 2timothy titus \\
        philemon 1john jude 2thess
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BOOKS = {
    '1thess':   {'num': 52, 'title': '1 Thessalonians', 'upper': '1 THESSALONIANS', 'anchor': '1-thessalonians'},
    '2thess':   {'num': 53, 'title': '2 Thessalonians', 'upper': '2 THESSALONIANS', 'anchor': '2-thessalonians'},
    '1timothy': {'num': 54, 'title': '1 Timothy',       'upper': '1 TIMOTHY',       'anchor': '1-timothy'},
    '2timothy': {'num': 55, 'title': '2 Timothy',       'upper': '2 TIMOTHY',       'anchor': '2-timothy'},
    'titus':    {'num': 56, 'title': 'Titus',           'upper': 'TITUS',           'anchor': 'titus'},
    'philemon': {'num': 57, 'title': 'Philemon',        'upper': 'PHILEMON',        'anchor': 'philemon'},
    '1john':    {'num': 62, 'title': '1 John',          'upper': '1 JOHN',          'anchor': '1-john'},
    'jude':     {'num': 65, 'title': 'Jude',            'upper': 'JUDE',            'anchor': 'jude'},
}

BOOK_DIR = {
    '1thess': 'calvin/1thessalonians-en',
    '2thess': 'calvin/2thessalonians-en',
    '1timothy': 'calvin/1timothy-en',
    '2timothy': 'calvin/2timothy-en',
    'titus': 'calvin/titus-en',
    'philemon': 'calvin/philemon-en',
    '1john': 'calvin/1john-en',
    'jude': 'calvin/jude-en',
}


def md_to_html(s: str) -> str:
    s = re.sub(r'^\*\*(\d+)\.\*\*', r'<strong>\1.</strong>', s)
    # 也处理裸 `N.` 起首 (Latin 列常见, 如 `1. Filioli mei`)
    s = re.sub(r'^(\d+)\.\s+', r'<strong>\1.</strong> ', s)
    s = re.sub(r'\*\*([^*]+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', s)
    return s


def strip_p_wrap(s: str) -> str:
    """Remove surrounding <p>...</p> from a td cell body."""
    m = re.match(r'^<p>(.+?)</p>$', s.strip(), re.S)
    return m.group(1) if m else s


# ── Format A: 已有 <h2 scripture-anchor> + `<table class="scripture-table calvin-parallel">`
#    结构 (1john, jude, philemon, 2timothy 系)
# ── 目标: 转换为 scripture-box wrapper + scripture-bilingual table
BLOCK_RE = re.compile(
    r'<h2 class="scripture-anchor"\s+id="([^"]+)"\s+data-ref="([^"]+)"'
    r'\s+style="display:none">[^<]+</h2>\s*\n+'
    r'(?:<p class="scripture-ref">.*?</p>\s*\n+)?'  # 可选 scripture-ref <p>
    r'<table class="scripture-table calvin-parallel">\s*\n'
    r'<tbody>\s*\n'
    r'((?:<tr><td><p>.+?</p></td><td><p>.+?</p></td></tr>\s*\n)+)'
    r'</tbody>\s*\n</table>',
    re.S,
)


def convert_parallel_block(m: re.Match, cfg: dict) -> str:
    anchor_id = m.group(1)
    data_ref = m.group(2)
    rows_raw = m.group(3)

    # data_ref 形如 "1 JOHN 1:1-2" 或 "PHILEMON 1-7" 或 "1 JOHN 2:1-2"
    # 抽取 chapter + verse_from
    m_ref = re.match(rf'^{re.escape(cfg["upper"])} (?:(\d+):)?(\d+)(?:-(\d+))?$', data_ref)
    if not m_ref:
        return m.group(0)  # skip if unrecognized
    ch = int(m_ref.group(1)) if m_ref.group(1) else 1
    v_from = int(m_ref.group(2))
    v_to = int(m_ref.group(3)) if m_ref.group(3) else v_from
    ages_code = f'{cfg["num"]}{ch:02d}{v_from:02d}'
    verse_range = f'{v_from}' if v_from == v_to else f'{v_from}-{v_to}'

    # 提取行
    ROW_RE = re.compile(
        r'<tr><td><p>(.+?)</p></td><td><p>(.+?)</p></td></tr>',
        re.S,
    )
    new_rows = []
    for rm in ROW_RE.finditer(rows_raw):
        left = rm.group(1).strip()
        right = rm.group(2).strip()
        # convert leading **N.** → <strong>N.</strong>
        left = md_to_html(left)
        right = md_to_html(right)
        new_rows.append(
            f'<tr><td class="scripture-en">{left}</td>'
            f'<td class="scripture-la">{right}</td></tr>'
        )

    lines = [
        '<div class="scripture-box scripture-box--bilingual" markdown="1">',
        (f'<p class="scripture-ref"><span class="ages-code">&lt;{ages_code}&gt;</span>'
         f'<span class="book-name">{cfg["title"]}</span> '
         f'<span class="verse-range">{ch}:{verse_range}</span></p>'),
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


def process(book_key: str) -> int:
    cfg = BOOKS[book_key]
    src_dir = ROOT / BOOK_DIR[book_key]
    total_blocks = 0
    for f in sorted(src_dir.glob('*.md')):
        if f.stem == 'preface':
            continue
        text = f.read_text(encoding='utf-8')
        new_text, n = BLOCK_RE.subn(lambda m: convert_parallel_block(m, cfg), text)
        if n:
            f.write_text(new_text, encoding='utf-8')
            print(f'  {f.name}: {n} blocks converted')
            total_blocks += n
    return total_blocks


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    total = 0
    for b in args:
        if b not in BOOKS:
            print(f'skip unknown book: {b}')
            continue
        print(f'=== {b} ===')
        n = process(b)
        print(f'  TOTAL: {n} blocks')
        total += n
    print(f'\nGRAND TOTAL: {total} blocks converted')


if __name__ == '__main__':
    main()
