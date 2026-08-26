#!/usr/bin/env python3
"""publish_nahum_zh.py — 加尔文《那鸿书注释》中译发布。

共 3 章，章号与英文 calvin/nahum-en/ 对齐。

- calvin-en 布局；front matter 本地化；prev/next 只在已译章之间连。
- 已发布章保留原 date；新章用当前真实时间。
- 末尾重写 index.html（calvin-book-modern）。

用法: python3 scripts/publish_nahum_zh.py        # 发布所有已翻译
      python3 scripts/publish_nahum_zh.py 1 3    # 只发布指定章
"""
import re, sys, datetime
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

SRC_DIR = ROOT / 'calvin_raw/nahum/zh_chapters'
OUT_DIR = ROOT / 'calvin/nahum'
BOOK_ID = 'nahum'
BOOK_NAME = '那鸿书'
TOTAL = 3


def clean_body(b):
    b = re.sub(r'<<<[^>]*?>>>', '', b)                 # BATCH 分段标记
    b = re.sub(r'\n[ \t]*\n[ \t]*\n', '\n\n', b)
    b = b.replace('****', '')                          # abut-bold
    b = b.replace('前往那鸿书', '前往 那鸿书')
    b = re.sub(r'[ \t]+([，。；：、？！）」』])', r'\1', b)
    b = re.sub(r'[ \t]+$', '', b, flags=re.M)
    return b


def chapter_date(n):
    p = OUT_DIR / f'{n}.md'
    if p.exists():
        m = re.search(r'^date:\s*(.+)$', p.read_text(encoding='utf-8'), re.M)
        if m:
            return m.group(1).strip()
    return now


def main():
    want = set(int(a) for a in sys.argv[1:]) if len(sys.argv) > 1 else None
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    nums = sorted(int(p.stem) for p in SRC_DIR.glob('*.md')
                  if p.stem.isdigit()) if SRC_DIR.exists() else []
    translated = set(nums)
    for n in nums:
        if want and n not in want:
            continue
        raw = (SRC_DIR / f'{n}.md').read_text(encoding='utf-8')
        m = re.match(r'^---\n.*?\n---\n(.*)$', raw, re.DOTALL)
        body = clean_body(m.group(1).strip('\n') if m else raw)
        fm = ['---', 'layout: calvin-en', f'book_id: {BOOK_ID}',
              f'book_name: {BOOK_NAME}', f'chapter: {n}',
              f'total_chapters: {TOTAL}', f'title: "那鸿书 {n}"',
              f'date: {chapter_date(n)}']
        if n > 1 and (n - 1) in translated:
            fm += [f'prev_section: {n-1}', f'prev_label: "那鸿书 {n-1}"']
        if n < TOTAL and (n + 1) in translated:
            fm += [f'next_section: {n+1}', f'next_label: "那鸿书 {n+1}"']
        fm += ['---', '']
        (OUT_DIR / f'{n}.md').write_text('\n'.join(fm) + '\n' + body + '\n',
                                         encoding='utf-8')
        print(f'  published {BOOK_ID}/{n}.md  那鸿书 {n}')
    if nums:
        (OUT_DIR / 'index.html').write_text(
            '---\nlayout: calvin-book-modern\n'
            f'book_id: {BOOK_ID}\nbook_name: {BOOK_NAME}\n'
            f'chapters: {TOTAL}\nhas_preface: false\n---\n', encoding='utf-8')
        print(f'  {BOOK_ID} index.html 已写；已译章: {nums}')
    else:
        print(f'  {BOOK_ID} 暂无译章, 跳过 index')


if __name__ == '__main__':
    main()
