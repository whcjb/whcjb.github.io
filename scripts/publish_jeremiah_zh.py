#!/usr/bin/env python3
"""publish_jeremiah_zh.py — 加尔文《耶利米书注释》中译发布，两卷对齐英文。

- 卷一：耶利米书 1-23 → calvin/jeremiah-1/N.md
- 卷二：耶利米书 24-52 → calvin/jeremiah-2/N.md
- 章号用绝对值(与英文一致，切换 jeremiah-1↔jeremiah-1-en 对得上)。

英文源原有两处末章吞附录，已由 scripts/jeremiah_footnotes_restore.py 修好：
   jeremiah-1-en/24.md 613KB → 41KB（切出 596 条脚注定义，配回各章）
   jeremiah-2-en/52.md 482KB → 17KB（切出脚注 + 卷末「Calvin's Version」译本
     附录到 appendix-calvin-version.md）
   ch24 两卷都有，卷一那份是真 ch24 正文，卷二那份 13KB 是重复的开头，
   发布时以卷二为准（章号 24 归卷二区间）。

- calvin-en 布局；front matter 本地化；prev/next 只在已译章之间连。
- 已发布章保留原 date；新章用当前真实时间。

用法: python3 scripts/publish_jeremiah_zh.py        # 发布所有已翻译
      python3 scripts/publish_jeremiah_zh.py 1 3    # 只发布指定章
"""
import re, sys, datetime
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

VOLS = [
    (ROOT / 'calvin_raw/jeremiah-1/zh_chapters', ROOT / 'calvin/jeremiah-1',
     'jeremiah-1', '耶利米书（卷一）', 1, 23),
    (ROOT / 'calvin_raw/jeremiah-2/zh_chapters', ROOT / 'calvin/jeremiah-2',
     'jeremiah-2', '耶利米书（卷二）', 24, 52),
]
# 章边界与脚注已修好（jeremiah_footnotes_restore.py），无需跳过任何章
SKIP = set()


def clean_body(b):
    b = re.sub(r'<<<[^>]*?>>>', '', b)                 # BATCH 分段标记
    b = re.sub(r'\n[ \t]*\n[ \t]*\n', '\n\n', b)
    b = b.replace('****', '')                          # abut-bold
    b = b.replace('前往耶利米书', '前往 耶利米书')
    b = re.sub(r'[ \t]+([，。；：、？！）」』])', r'\1', b)
    b = re.sub(r'[ \t]+$', '', b, flags=re.M)
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
    for src_dir, out_dir, book_id, book_name, lo, hi in VOLS:
        out_dir.mkdir(parents=True, exist_ok=True)
        nums = sorted(int(p.stem) for p in src_dir.glob('*.md')
                      if p.stem.isdigit()) if src_dir.exists() else []
        translated = set(nums)
        for n in nums:
            if want and n not in want:
                continue
            if (book_id, n) in SKIP:
                print(f'  跳过 {book_id}/{n}（英文源章边界坏掉，见脚本 docstring）')
                continue
            raw = (src_dir / f'{n}.md').read_text(encoding='utf-8')
            m = re.match(r'^---\n.*?\n---\n(.*)$', raw, re.DOTALL)
            body = clean_body(m.group(1).strip('\n') if m else raw)
            fm = ['---', 'layout: calvin-en', f'book_id: {book_id}',
                  f'book_name: {book_name}', f'chapter: {n}',
                  'total_chapters: 52', f'title: "耶利米书 {n}"',
                  f'date: {chapter_date(out_dir, n)}']
            if n > lo and (n - 1) in translated:
                fm += [f'prev_section: {n-1}', f'prev_label: "耶利米书 {n-1}"']
            if n < hi and (n + 1) in translated:
                fm += [f'next_section: {n+1}', f'next_label: "耶利米书 {n+1}"']
            fm += ['---', '']
            (out_dir / f'{n}.md').write_text('\n'.join(fm) + '\n' + body + '\n',
                                             encoding='utf-8')
            print(f'  published {book_id}/{n}.md  耶利米书 {n}')
        if nums:
            (out_dir / 'index.html').write_text(
                '---\nlayout: calvin-book-modern\n'
                f'book_id: {book_id}\nbook_name: {book_name}\n'
                f'chapters: {hi}\nhas_preface: false\n---\n', encoding='utf-8')
            print(f'  {book_id} index.html 已写；该卷已译章: {nums}')
        else:
            print(f'  {book_id} 暂无译章, 跳过 index')


if __name__ == '__main__':
    main()
