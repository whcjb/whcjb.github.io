#!/usr/bin/env python3
"""把 psalms-2-en 末章 ch150 里夹带的两个附录拆成独立页。

ch150 原本 969 KB，实际是三段拼在一起：
  1. 诗篇 150 的注释本身（约 5 KB）
  2. 《诗篇新译》附录 —— 全 150 篇的韵文体新译（约 351 KB）
  3. FOOTNOTES 脚注附录（约 627 KB）
和卷一 ch78 吞掉脚注附录是同一类缺陷：末章没有终止边界。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EN = ROOT / 'calvin/psalms-2-en'
FM_DATE = '2026-06-02 18:13'          # 沿用原文件的 date，不改已有时间戳


def front_matter(title, prev, prev_label, nxt=None, next_label=None):
    fm = ('---\nlayout: calvin-en\nbook_id: psalms-2-en\n'
          'book_name: "Calvin on Psalms (Vol. 2)"\n'
          f'title: "{title}"\ndate: {FM_DATE}\n'
          f'prev_section: {prev}\nprev_label: "{prev_label}"\n')
    if nxt:
        fm += f'next_section: {nxt}\nnext_label: "{next_label}"\n'
    return fm + '---\n'


def main():
    p = EN / '150.md'
    fm, body = re.match(r'(---\n.*?\n---\n)(.*)$', p.read_text(encoding='utf-8'), re.S).groups()
    if 'FOOTNOTES' not in body:
        print('ch150 已拆分过，跳过')
        return

    i_new = body.rfind('<p class="title-block-h2"', 0, body.find('A NEW TRANSLATION OF'))
    i_fn = body.find('<p class="title-block-h1"', body.find('FOOTNOTES') - 300)
    if min(i_new, i_fn) < 0 or not i_new < i_fn:
        raise SystemExit(f'切点异常: 新译 {i_new}, 脚注 {i_fn}')

    def back_to_page(idx):
        """把紧邻切点前的 <!-- PAGE N --> 归给后一段"""
        m = re.search(r'(<!-- PAGE \d+ -->\s*)$', body[:idx])
        return m.start() if m else idx

    i_new, i_fn = back_to_page(i_new), back_to_page(i_fn)

    head = fm.rstrip('-\n').rstrip() + (
        '\nnext_section: new-translation\n'
        'next_label: "A New Translation of the Psalms"\n---\n')
    p.write_text(head + '\n' + body[:i_new].strip() + '\n', encoding='utf-8')
    (EN / 'new-translation.md').write_text(
        front_matter('A New Translation of the Psalms', 150, 'Chapter 150',
                     'footnotes', 'Footnotes')
        + '\n' + body[i_new:i_fn].strip() + '\n', encoding='utf-8')
    (EN / 'footnotes.md').write_text(
        front_matter('Footnotes', 'new-translation', 'A New Translation of the Psalms')
        + '\n' + body[i_fn:].strip() + '\n', encoding='utf-8')

    for name in ('150.md', 'new-translation.md', 'footnotes.md'):
        print(f'  {name}: {(EN / name).stat().st_size} 字节')


if __name__ == '__main__':
    main()
