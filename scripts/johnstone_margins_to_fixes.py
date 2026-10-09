#!/usr/bin/env python3
"""「修订译文」那一节的边码 → manual_fixes_extra.tsv

原书这一节是圣经体例：节号排在文字块**左侧页边**，不在行内。抽取时它们
被当成噪点清掉了（整节只剩 28 个，而腓立比书有 104 节）。

边码是单独问出来的（scratchpad/margins.py：只问「每个边码贴着哪五个词」），
拿「贴着的那几个词」在正文里定位、把号码插到它前面。定位不唯一就跳过并记账，
不硬插 —— 插错位置比缺号更糟。

    python3 scripts/johnstone_margins_to_fixes.py --src <margins.txt>
    python3 scripts/johnstone_margins_to_fixes.py --src <...> --write
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'en_chapters',
                   'translation.md')
TBL = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'manual_fixes_extra.tsv')
QUOTE = str.maketrans({'‘': "'", '’': "'", '“': '"', '”': '"', '—': '-', '–': '-'})


def norm(s):
    return re.sub(r'\s+', ' ', s.translate(QUOTE).replace('*', '')).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    text = open(SRC, encoding='utf-8').read()
    flat = norm(text)
    rows, skip = [], []
    leaf = '?'
    for line in open(a.src, encoding='utf-8'):
        if line.startswith('====='):
            leaf = line.split()[2]
            continue
        if '|||' not in line:
            continue
        fig, anchor = (x.strip() for x in line.split('|||', 1))
        na = norm(anchor)
        if len(na) < 12:
            skip.append((fig, anchor, '锚点太短')); continue
        n = flat.count(na)
        if n != 1:
            skip.append((fig, anchor, f'定位 {n} 处')); continue
        # 号码已经在前面了就不重复插
        at = flat.find(na)
        lead = flat[max(0, at - 14):at]
        if re.search(re.escape(fig.replace(' ', '')) + r'\W*$',
                     lead.replace(' ', '')):
            skip.append((fig, anchor, '已经有了')); continue
        rows.append(('translation.md', leaf, na, f'{fig} {na}'))

    print(f'可插 {len(rows)} 个边码，跳过 {len(skip)} 个')
    for fig, anchor, why in skip:
        print(f'  跳过 {fig:>6s}  {why:10s}  {anchor[:46]}')
    if a.write:
        with open(TBL, 'w', encoding='utf-8') as fh:
            fh.write('# 「修订译文」一节的边码。每行：文件\tleaf\t我们的\t印面的\n')
            fh.write('# 由 scripts/johnstone_margins_to_fixes.py 生成。\n')
            for r in rows:
                fh.write('\t'.join(r) + '\n')
        print(f'→ {TBL}')


if __name__ == '__main__':
    main()
