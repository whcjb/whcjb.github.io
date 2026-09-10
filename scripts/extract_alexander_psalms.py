#!/usr/bin/env python3
"""J. A. Alexander《诗篇注释》：ABBYY XML → 逐篇英文 raw markdown。

底本：Internet Archive `commentaryonpsal00alex`——1864 年 Scribner 单卷修订版
的影印重排。选它不选 1850 年三卷本（psalmstranslated0{1,2,3}alex）的理由：
同一部书，这一版扫描字号大、ABBYY 误识率低一个数量级，且篇题已是阿拉伯数字
"Psalm 1"，不必再跟罗马数字的 OCR 变体缠斗。1850 三卷本留作**第二证人**，
见 adjudicate_alexander_ocr.py。

不收录的部分：
    p12–13  Kregel 1991 年新写的 FOREWORD —— 版权在世，只有 Alexander 本人
            的文字是公有领域
    p578–  出版社书目广告
"""
import pickle
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_common import (bare, check_page_sequence, collect_compounds,
                              printed_page_numbers, slice_pars, write_chapter)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander_raw/psalms/src'
OUT = ROOT / 'alexander_raw/psalms/en_chapters'

PREFACE_PAGES = range(14, 22)      # Alexander 自序（Kregel 的 foreword 在 12–13，不取）
BODY_START = 22

# 页眉：'570 Psalm 149:1 - 6' / 'Psalm 150:1,2 571' / '10 Preface' / 'Preface 11'
#
# 章节号与页码之间的分隔符 OCR 出来有 ':' 也有 '.'，数字还常被读成 J / l / I /
# O / ] / [。第一版只认 ':' + 纯数字，17 条页眉因此漏网**混进正文**，还把跨页
# 断词 'connec- tion' 撑开成两截。宁可把字符类放宽，也不能让页眉进正文。
_D = r'[\dJjIl\]\[O]'
RUNHEAD = re.compile(
    r'^\s*(?:' + _D + r'{1,3}\s+)?'
    r'(?:Psalm\s*' + _D + r'{1,3}\s*[:.]\s*[' + _D[1:-1] + r',.\s\-–—]*'
    r'|Preface|Foreword|THE\s+PSALMS)'
    r'\s*(?:' + _D + r'{1,3})?\s*$', re.I)
HEAD = re.compile(r'^Psalm\s*(\d{1,3})\s*$', re.I)
VERSE_START = re.compile(r'^\s*(\d{1,3})\s*(?:\(\d{1,3}\.?\)\s*)?\.')


def main():
    pages = pickle.load(open(SRC / 'pages1864.pkl', 'rb'))
    by_index = {p['index']: p for p in pages}
    compounds = collect_compounds(pages)
    OUT.mkdir(parents=True, exist_ok=True)

    # ── 篇题定位 ──────────────────────────────────────────
    heads = {}
    for pg in pages:
        if pg['index'] < BODY_START:
            continue
        for i, par in enumerate(pg['pars']):
            if par['nlines'] != 1:
                continue
            m = HEAD.match(bare(par['text']).strip())
            if m:
                n = int(m.group(1))
                if 1 <= n <= 150 and n not in heads:
                    heads[n] = (pg['index'], i)
    missing = [n for n in range(1, 151) if n not in heads]
    if missing:
        raise SystemExit(f'篇题缺失: {missing}')

    def write(name, chunk, header, pmap=None):
        return write_chapter(OUT / f'{name}.md', header, chunk, VERSE_START,
                             pmap, compounds)

    # ── 自序 ──────────────────────────────────────────────
    chunk = []
    for idx in PREFACE_PAGES:
        pg = by_index.get(idx)
        if not pg:
            continue
        for par in pg['pars']:
            if par['nlines'] == 1 and RUNHEAD.match(bare(par['text']).strip()):
                continue
            if bare(par['text']).strip().upper() == 'PREFACE':
                continue
            chunk.append((idx, par))
    n = write('preface', chunk, '<!-- preface | 扫描页 14-21 -->')
    print(f'preface: {n} paragraphs')

    # ── 150 篇 ────────────────────────────────────────────
    pmap = printed_page_numbers(pages, (BODY_START, 577), RUNHEAD, first_page=17)
    breaks = check_page_sequence(pmap)
    if breaks:
        print(f'⚠ 页码不连续 {len(breaks)} 处: {breaks[:5]}')

    order = sorted(heads.items())
    total = 0
    for k, (num, (pg0, pi0)) in enumerate(order):
        if k + 1 < len(order):
            pg1, pi1 = order[k + 1][1]
        else:
            pg1, pi1 = 577, 10 ** 6
        chunk = slice_pars(by_index, pg0, pi0, pg1, pi1, RUNHEAD)
        c = write(str(num), chunk,
                  f'<!-- psalm {num} | 书页 {pmap.get(pg0)}-{pmap.get(pg1)} '
                  f'| 扫描页 {pg0}-{pg1} -->', pmap)
        total += c
    print(f'psalms 1-150: {total} paragraphs')


if __name__ == '__main__':
    main()
