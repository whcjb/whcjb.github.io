#!/usr/bin/env python3
"""alexander_raw/psalms/en_chapters/*.md → 站内 alexander/psalms/*.md（英文版）。

做三件事：
  1. 补 front matter（layout / 上下篇导航 / 真实时间戳）
  2. 节号段落 → 锚点 + `.ax-vnum`，供章顶 verse-nav 与经文索引取用
  3. 生成书卷首页 index.html

节号的两套编号：`7 (6).` 前者是希伯来文本的节号，括号里是英文圣经的节号。
诗篇题注（"A Psalm of David"）在希伯来文里算第 1 节、英译不算，所以两者常
差一节。**锚点一律取英文节号**——站内其他注释、经文索引、和合本都按英文
编号，取希伯来节号会让同一节在不同注释之间对不上。
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander_raw/psalms/en_chapters'
OUT = ROOT / 'alexander/psalms'
BOOK_ID = 'psalms'
BOOK_NAME = 'Alexander on the Psalms'

# 节号段落。分三段捕获，好把两套编号分别着色：
#   g1  主编号，可能是范围或列表：'7'  '21, 22'  '31-33'
#   g2  括号内的英文编号（可缺）：'6'  '30—32'
#   g3  收尾标点
VERSE = re.compile(
    r'^(?P<lead>\*?)'
    r'(?P<g1>\d{1,3}(?:\s*[-–—,]\s*\d{1,3})*)'
    r'(?:\s*\(\s*(?P<g2>\d{1,3}(?:\s*[-–—,]\s*\d{1,3})*)\s*\.?\s*\))?'
    r'(?P<g3>[.,:])?(?=\s)')

FIRST_NUM = re.compile(r'\d{1,3}')


def render_verse(m, psalm, num):
    """把节号本身包起来。lead 的 `*` 要移到节号之后，否则斜体跨过节号，
    读者会以为编号也是经文的一部分（原书的斜体只包译文）。"""
    g1, g2, g3 = m.group('g1'), m.group('g2'), m.group('g3') or '.'
    inner = g1
    if g2:
        inner += f' <span class="ax-veng">({g2}){g3}</span>'
    else:
        inner += g3
    anchor = f'<span class="ax-anchor" id="psalms-{psalm}-{num}"></span>'
    return f'{anchor}<span class="ax-vnum">{inner}</span>' + (' *' if m.group('lead') else '')


def transform(body, psalm):
    out, n_anchor = [], 0
    for line in body.split('\n'):
        if not line.strip() or line.startswith('<!--'):
            out.append(line)
            continue
        m = VERSE.match(line)
        if m:
            src = m.group('g2') or m.group('g1')
            num = FIRST_NUM.search(src).group(0)
            out.append(render_verse(m, psalm, num) + line[m.end():])
            n_anchor += 1
        else:
            # kramdown 会把 `* ` 开头的行当无序列表。正文不该有，防一手。
            out.append('\\' + line if line.startswith('* ') else line)
    return '\n'.join(out), n_anchor


def main():
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True,
                         text=True, check=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)

    sections = ['preface'] + [str(i) for i in range(1, 151)]
    labels = {'preface': 'Preface'}
    labels.update({str(i): f'Psalm {i}' for i in range(1, 151)})

    total_anchors = 0
    for k, sec in enumerate(sections):
        raw = (SRC / f'{sec}.md').read_text(encoding='utf-8')
        body, n = transform(raw.strip(), sec)
        total_anchors += n
        fm = [
            '---',
            'layout: alexander-chapter',
            f'book_id: {BOOK_ID}',
            f'book_name: "{BOOK_NAME}"',
        ]
        if sec != 'preface':
            fm.append(f'chapter: {sec}')
        fm += [f'title: "{labels[sec]}"', f'date: {now}']
        if k > 0:
            fm += [f'prev_section: {sections[k - 1]}',
                   f'prev_label: "{labels[sections[k - 1]]}"']
        if k + 1 < len(sections):
            fm += [f'next_section: {sections[k + 1]}',
                   f'next_label: "{labels[sections[k + 1]]}"']
        fm.append('---')
        # 正文里不再重复一个 h1：layout 顶部已经用 page.title 打了标题，
        # 两处都写「Psalm 1」是同一串字连着出现两遍。
        (OUT / f'{sec}.md').write_text(
            '\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    (OUT / 'index.html').write_text(
        '---\n'
        'layout: alexander-book\n'
        f'book_id: {BOOK_ID}\n'
        f'book_name: "{BOOK_NAME}"\n'
        'chapters: 150\n'
        '---\n', encoding='utf-8')

    print(f'发布 {len(sections)} 篇（含序），节号锚点 {total_anchors} 个 → {OUT}')


if __name__ == '__main__':
    main()
