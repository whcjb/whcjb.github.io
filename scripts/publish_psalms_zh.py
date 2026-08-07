#!/usr/bin/env python3
"""publish_psalms_zh.py — 诗篇中译发布，**两卷**对齐英文(psalms-1-en / psalms-2-en)。

- 卷一：诗篇 1-78 → calvin/psalms-1/N.md (book_id psalms-1, 诗篇（卷一）)
- 卷二：诗篇 79-150 → calvin/psalms-2/N.md (book_id psalms-2, 诗篇（卷二）)
- 篇号用绝对值(与英文一致，切换 psalms-1↔psalms-1-en 对得上)。
- calvin-en 布局；front matter 本地化；prev/next 卷内 N±1。
- 已发布章保留原 date；新章用当前真实时间。
- index.html: calvin-book-modern（chapter 字段使 titled_book 为真, 只渲染已译篇）。
用法: python3 scripts/publish_psalms_zh.py            # 发布所有已翻译
      python3 scripts/publish_psalms_zh.py 1 3        # 只发布指定篇号
"""
import re, sys, datetime
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

# 每卷: (源 zh_chapters, 输出目录, book_id, book_name, 篇号下限, 篇号上限, index chapters)
VOLS = [
    (ROOT / 'calvin_raw/psalms-1/zh_chapters', ROOT / 'calvin/psalms-1',
     'psalms-1', '诗篇（卷一）', 1, 78, 78),
    (ROOT / 'calvin_raw/psalms-2/zh_chapters', ROOT / 'calvin/psalms-2',
     'psalms-2', '诗篇（卷二）', 79, 150, 150),
]


def clean_body(b):
    b = re.sub(r'<<<[^>]*?>>>', '', b)
    b = re.sub(r'\n[ \t]*\n[ \t]*\n', '\n\n', b)
    b = b.replace('前往诗篇', '前往 诗篇')
    return b


def chapter_date(out_dir, n):
    p = out_dir / f'{n}.md'
    if p.exists():
        m = re.search(r'^date:\s*(.+)$', p.read_text(encoding='utf-8'), re.M)
        if m:
            return m.group(1).strip()
    return now


def main():
    want = set(int(a) for a in sys.argv[1:]) if len(sys.argv) > 1 else None
    for src_dir, out_dir, book_id, book_name, lo, hi, idx_chapters in VOLS:
        out_dir.mkdir(parents=True, exist_ok=True)
        nums = sorted(int(p.stem) for p in src_dir.glob('*.md')
                      if p.stem.isdigit()) if src_dir.exists() else []
        for n in nums:
            if want and n not in want:
                continue
            raw = (src_dir / f'{n}.md').read_text(encoding='utf-8')
            m = re.match(r'^---\n.*?\n---\n(.*)$', raw, re.DOTALL)
            body = clean_body(m.group(1).strip('\n')) if m else clean_body(raw)
            fm = ['---', 'layout: calvin-en', f'book_id: {book_id}',
                  f'book_name: {book_name}', f'chapter: {n}',
                  'total_chapters: 150', f'title: "诗篇 {n}"',
                  f'date: {chapter_date(out_dir, n)}']
            if n > lo:
                fm += [f'prev_section: {n-1}', f'prev_label: "诗篇 {n-1}"']
            if n < hi:
                fm += [f'next_section: {n+1}', f'next_label: "诗篇 {n+1}"']
            fm += ['---', '']
            (out_dir / f'{n}.md').write_text('\n'.join(fm) + '\n' + body + '\n',
                                             encoding='utf-8')
            print(f'  published {book_id}/{n}.md  诗篇 {n}')
        # index.html: 仅当该卷已有译章时写(空卷写了会渲染满屏 404 占位;
        # 主页会把无内容的卷显示为 pending 非链接)。
        if nums:
            (out_dir / 'index.html').write_text(
                '---\nlayout: calvin-book-modern\n'
                f'book_id: {book_id}\nbook_name: {book_name}\n'
                f'chapters: {idx_chapters}\nhas_preface: false\n---\n', encoding='utf-8')
            print(f'  {book_id} index.html 已写；该卷已译篇: {nums}')
        else:
            print(f'  {book_id} 暂无译章, 跳过 index(主页显示为 pending)')


if __name__ == '__main__':
    main()
