#!/usr/bin/env python3
"""publish_psalms_zh.py — 把 calvin_raw/psalms-{1,2}/zh_chapters/N.md 发布到
calvin/psalms/N.md（N=诗篇篇号，两卷合并为统一书卷 psalms）。

- 严格遵循 pdf-pipeline skill：calvin-en 布局，front matter 本地化
  (book_id psalms-{1,2}-en→psalms, book_name→诗篇, title「Chapter N」→「诗篇 N」)。
- prev/next 按篇号 N±1(1..150)，过渡期与旧格式章节导航仍连通。
- clean: 剥 <<<...>>>，「前往诗篇」补空格。
- 已发布章保留原 date(不改历史时间戳)；新章用当前真实时间。
- 不重建 index.html（诗篇全卷重做时另行处理，避免打乱现存章节列表）。
用法: python3 scripts/publish_psalms_zh.py            # 发布所有已翻译 zh raw
      python3 scripts/publish_psalms_zh.py 1 3 5     # 只发布指定篇号
"""
import re, sys, datetime
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
SRC_DIRS = [ROOT / 'calvin_raw/psalms-1/zh_chapters',
            ROOT / 'calvin_raw/psalms-2/zh_chapters']
OUT = ROOT / 'calvin/psalms'
BOOK_ID = 'psalms'
BOOK_NAME = '诗篇'
TOTAL = 150
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')


def clean_body(b):
    b = re.sub(r'<<<[^>]*?>>>', '', b)
    b = re.sub(r'\n[ \t]*\n[ \t]*\n', '\n\n', b)
    b = b.replace('前往诗篇', '前往 诗篇')
    return b


def chapter_date(n):
    p = OUT / f'{n}.md'
    if p.exists():
        m = re.search(r'^date:\s*(.+)$', p.read_text(encoding='utf-8'), re.M)
        if m:
            return m.group(1).strip()
    return now


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # 收集所有已翻译的篇号 → 源文件
    src_by_n = {}
    for d in SRC_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.glob('*.md')):
            if p.stem.isdigit():
                src_by_n[int(p.stem)] = p
    want = [int(a) for a in sys.argv[1:]] if len(sys.argv) > 1 else sorted(src_by_n)
    for n in want:
        if n not in src_by_n:
            print(f'  跳过 {n}（无 zh raw）')
            continue
        raw = src_by_n[n].read_text(encoding='utf-8')
        m = re.match(r'^---\n.*?\n---\n(.*)$', raw, re.DOTALL)
        body = clean_body(m.group(1).strip('\n')) if m else clean_body(raw)
        fm = ['---', 'layout: calvin-en', f'book_id: {BOOK_ID}',
              f'book_name: {BOOK_NAME}', f'chapter: {n}',
              f'total_chapters: {TOTAL}', f'title: "诗篇 {n}"',
              f'date: {chapter_date(n)}']
        if n > 1:
            fm += [f'prev_section: {n-1}', f'prev_label: "诗篇 {n-1}"']
        if n < TOTAL:
            fm += [f'next_section: {n+1}', f'next_label: "诗篇 {n+1}"']
        fm += ['---', '']
        (OUT / f'{n}.md').write_text('\n'.join(fm) + '\n' + body + '\n', encoding='utf-8')
        print(f'  published psalms/{n}.md  诗篇 {n}')
    print(f'  完成，已翻译篇号: {sorted(src_by_n)}')


if __name__ == '__main__':
    main()
