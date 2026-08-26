#!/usr/bin/env python3
"""把末章里的「加尔文经文译本」附录切成独立页面。

AGES 版好几卷在注释正文之后附了整卷经文（按加尔文注释订正的译本），标题形如

    A TRANSLATION OF
    CALVIN'S VERSION OF
    THE BOOK OF ZECHARIAH.

或 daniel 的

    A CONNECTED TRANSLATION OF
    THE PROPHECIES OF DANIEL

提取时它们落在末章，于是末章体积暴涨（zechariah ch14 曾是其余章的 3.1 倍），
中译还会把整卷经文翻一遍——那是经文不是注释，中文版不需要。

本脚本把「A TRANSLATION OF / A CONNECTED TRANSLATION OF」到「FOOTNOTES」之间
切出来，写成 appendix-*.md 单独成页（英文保留，prev 指回末章），并：
  - 把附录引用、而正文不再引用的脚注定义一并搬到附录页；
  - 清掉 FOOTNOTES 之后残留的附录标题与 CHAPTER 目录行（publish_calvin_en
    收集脚注时会把它们一起带进来）。

⚠️ 必须放在 publish_calvin_en.py 之后跑：那一步从合并 md 重新生成章节文件，
会把附录又塞回末章。流水线顺序是
    calvin_extract → structured_to_md → publish_calvin_en
    → decode_ages_hebrew → split_verse_appendix

用法:
    python3 scripts/split_verse_appendix.py              # 处理所有已知卷
    python3 scripts/split_verse_appendix.py hosea daniel # 只处理指定卷
    python3 scripts/split_verse_appendix.py --dry-run
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 卷 → (末章号, 书名, 附录页 slug)
BOOKS = {
    'habakkuk':  ('3',  'Habakkuk',  'appendix-calvins-version'),
    'zephaniah': ('3',  'Zephaniah', 'appendix-calvins-version'),
    'haggai':    ('2',  'Haggai',    'appendix-calvins-version'),
    'zechariah': ('14', 'Zechariah', 'appendix-calvins-version'),
    'malachi':   ('4',  'Malachi',   'appendix-calvins-version'),
    'hosea':     ('14', 'Hosea',     'appendix-calvins-version'),
    'daniel':    ('12', 'Daniel',    'appendix-connected-translation'),
}

START_RE = re.compile(r'A (?:CONNECTED )?TRANSLATION OF')
DROP_RE = re.compile(r'^(?:A (?:CONNECTED )?TRANSLATION OF CALVIN.S VERSION'
                     r'|A (?:CONNECTED )?TRANSLATION OF|CHAPTER \d+)$')


def plain(line: str) -> str:
    return re.sub(r'<[^>]*>', '', line).strip()


def split_one(book: str, dry: bool = False) -> str:
    ch, name, slug = BOOKS[book]
    f = ROOT / f'calvin/{book}-en/{ch}.md'
    if not f.exists():
        return f'{book}: 末章 {ch}.md 不存在，跳过'
    lines = f.read_text(encoding='utf-8').split('\n')

    starts = [i for i, l in enumerate(lines) if START_RE.search(plain(l))]
    if not starts:
        return f'{book}: 末章里没有经文译本附录（可能已切过）'
    start = starts[0]
    ends = [i for i, l in enumerate(lines) if i > start and plain(l) == 'FOOTNOTES']
    if not ends:
        return f'{book}: 找不到 FOOTNOTES 边界，跳过（需人工看）'
    end = ends[0]

    appendix = lines[start:end]
    rest = lines[:start] + lines[end:]

    cleaned, dropped = [], 0
    for l in rest:
        if not l.startswith('[^') and DROP_RE.match(plain(l)):
            dropped += 1
            continue
        cleaned.append(l)

    refs = set(re.findall(r'\[\^(f\w+)\]', '\n'.join(appendix)))
    body_refs = set(re.findall(r'\[\^(f\w+)\]', '\n'.join(
        l for l in cleaned if not re.match(r'^\[\^f\w+\]:', l))))
    move = refs - body_refs
    moved, final = [], []
    for l in cleaned:
        m = re.match(r'^\[\^(f\w+)\]:', l)
        (moved if (m and m.group(1) in move) else final).append(l)

    if dry:
        return (f'{book}: 会切出 {len(appendix)} 行，搬脚注 {len(move)} 条，'
                f'清理残留 {dropped} 行（dry-run）')

    fm = ['---', 'layout: calvin-en', f'book_id: {book}-en',
          f'book_name: "Calvin on {name}"',
          f'title: "Appendix — Calvin\'s Version of {name}"',
          'date: 2026-06-02 18:13', f'prev_section: {ch}',
          f'prev_label: "Chapter {ch}"', '---', '']
    body = '\n'.join(appendix)
    if moved:
        body += '\n\n' + '\n\n'.join(moved)
    (ROOT / f'calvin/{book}-en/{slug}.md').write_text(
        '\n'.join(fm) + body.rstrip('\n') + '\n', encoding='utf-8')

    txt = re.sub(r'\n{3,}', '\n\n', '\n'.join(final)).rstrip('\n') + '\n'
    f.write_text(txt, encoding='utf-8')
    return (f'{book}/{ch}: {len(lines)} → {len(txt.split(chr(10)))} 行，'
            f'附录 {len(appendix)} 行，搬脚注 {len(move)} 条，清残留 {dropped} 行')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('books', nargs='*', help='只处理这些卷（默认全部）')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    todo = args.books or list(BOOKS)
    for b in todo:
        if b not in BOOKS:
            print(f'  未知卷 {b!r}，已知：{", ".join(BOOKS)}', file=sys.stderr)
            continue
        print('  ' + split_one(b, args.dry_run))


if __name__ == '__main__':
    main()
