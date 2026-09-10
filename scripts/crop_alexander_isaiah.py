#!/usr/bin/env python3
"""把以赛亚书某一书页渲染成图，供人（或视觉模型）直接读页面判字。

多证人判读能解决的是「另一份扫描件读对了」的那些。剩下两类它救不了：
  · 几份证人在同一处**都读崩**——多数表决多数崩的还是崩的；
  · 底本整个词没 OCR 出来——逐 token 比对看不见「少了一个词」。
这两类只能看页面影像。

页码换算（实测，两卷都零偏移）：
    卷一 书页 P → PDF 第 P+78 页      正文书页 1–652
    卷二 书页 P → PDF 第 P+46 页      正文书页 1–501

用法：
    python3 scripts/crop_alexander_isaiah.py 145            # 卷一书页 145
    python3 scripts/crop_alexander_isaiah.py 33 --vol v2    # 卷二书页 33
    python3 scripts/crop_alexander_isaiah.py --find "gratuitous assumption"

**优先用 --find。** 正文里的 `<!-- PAGE n -->` 标的是**段落起始页**，一个长段
能横跨两三页，按它去翻页经常翻错（第 34 章那句「gratuitous assumption」段首
在书页 559，句子本身在 561）。`--find` 直接拿这句话去 PDF 的文本层里搜——
文本层与 en_chapters 同出一份 ABBYY OCR，同一串字一模一样，命中最准。
搜不到时把串截短些再试（斜体标记、连字符不在文本层里）。

输出到 --out（默认写进本会话 scratchpad），打印实际路径。
"""
import argparse
import os
from pathlib import Path

import fitz

PDF = {
    'v1': Path.home() / 'Documents/论文/alexander/propheciesisaiah01alexuoft.pdf',
    'v2': Path.home() / 'Documents/论文/alexander/propheciesisaiah02alexuoft.pdf',
}
OFFSET = {'v1': 78, 'v2': 46}
# 卷一 1–39 章、卷二 40–66 章；书页号两卷各自从 1 起，所以必须显式给卷
BODY_PAGES = {'v1': (1, 652), 'v2': (1, 501)}


def render(printed=None, vol='v1', dpi=170, out_dir=None, pdf_index=None):
    """printed = 书页页码；pdf_index = PDF 里的第几页（1 起，给前言/导论用，
    那部分印的是罗马数字页码，换算不过来）。"""
    if pdf_index is None:
        lo, hi = BODY_PAGES[vol]
        if not (lo <= printed <= hi):
            raise SystemExit(f'{vol} 正文书页范围是 {lo}-{hi}，给的是 {printed}')
        pdf_index = printed + OFFSET[vol]
    doc = fitz.open(PDF[vol])
    page = doc[pdf_index - 1]
    out_dir = Path(out_dir or os.environ.get('SCRATCHPAD', '/tmp'))
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f'p{printed}' if printed is not None else f'pdf{pdf_index}'
    path = out_dir / f'isaiah_{vol}_{tag}.png'
    page.get_pixmap(dpi=dpi).save(path)
    doc.close()
    return path


def find(needle, vol=None):
    """在 PDF 文本层里搜一句话 → [(卷, PDF 页序, 书页或 None)]"""
    hits = []
    for v in ([vol] if vol else ('v1', 'v2')):
        doc = fitz.open(PDF[v])
        for i in range(len(doc)):
            if needle in ' '.join(doc[i].get_text().split()):
                pdf_index = i + 1
                printed = pdf_index - OFFSET[v]
                lo, hi = BODY_PAGES[v]
                hits.append((v, pdf_index, printed if lo <= printed <= hi else None))
        doc.close()
    return hits


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('page', type=int, nargs='?')
    ap.add_argument('--vol', choices=('v1', 'v2'))
    ap.add_argument('--dpi', type=int, default=170)
    ap.add_argument('--out')
    ap.add_argument('--find', dest='needle')
    a = ap.parse_args()
    if a.needle:
        hits = find(' '.join(a.needle.split()), a.vol)
        if not hits:
            raise SystemExit('文本层里没搜到，把串截短些再试')
        for v, pdf_index, printed in hits:
            where = f'书页 {printed}' if printed else f'PDF 第 {pdf_index} 页（前置件）'
            print(v, where, '→',
                  render(printed, v, a.dpi, a.out, None if printed else pdf_index))
    else:
        print(render(a.page, a.vol or 'v1', a.dpi, a.out))
