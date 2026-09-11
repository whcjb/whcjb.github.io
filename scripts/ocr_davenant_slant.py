#!/usr/bin/env python3
"""量出每个词的**笔画倾角**，把原书的斜体找回来。

为什么要单做一遍
----------------
本卷的斜体承担三种实义（DIAGNOSIS §3，已核原图）：被注释的词句、圣经引语、
拉丁词句——抽样页上一次能占十来行。可两个现成的文本源都给不出字体信息：
IA 那层是 `GlyphLessFont` 隐形文本，我们这遍 tesseract 用的是 LSTM 引擎
（`--oem 1`），它根本不报字体属性；legacy 引擎（`--oem 0`）会报，但本机
tessdata 里没有 legacy 组件。所以不靠模型，直接**从像素上量**。

怎么量
------
斜体的竖笔是斜的。把词的二值图按一组剪切角逐个"扶正"，哪个角度下**列投影
最集中**（竖笔叠成一柱），哪个就是这个词的倾角：

    正体   -4° ~ +2°
    斜体   +9° ~ +19°        （vol2 p119 实测，同页正斜两种都有）

渲染参数与 ocr_davenant.py 完全一致（400 dpi、eng+lat、psm 6），所以 hOCR
里的行序、行文本与 vol{N}_lines.jsonl 一一对应，下游可以按 (页, 行号, 词号)
直接取用。

输出 davenant_raw/colossians/vol{1,2}_slant.jsonl
     每行一页 {page, lines:[{text, words:[[词, 倾角], …]}, …]}

用法:
    python3 scripts/ocr_davenant_slant.py --vol 2 --pages 119-119   # 试跑
    python3 scripts/ocr_davenant_slant.py                           # 两卷
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import fitz
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
PDFS = {1: 'expositionofepis01dave.pdf', 2: 'expositionofepis02dave.pdf'}
RANGES = {1: (86, 631), 2: (14, 620)}
DPI = 400
ANGLES = np.arange(-6.0, 25.0, 1.0)

LINE_RE = re.compile(r"class='ocr_line'[^>]*>(.*?)(?=<span class='ocr_line'|</div>|\Z)",
                     re.S)
WORD_RE = re.compile(r"class='ocrx_word'[^>]*title='bbox (\d+) (\d+) (\d+) (\d+)"
                     r"[^']*'[^>]*>(.*?)</span>", re.S)


def unescape(t):
    return (t.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
             .replace('&quot;', '"').replace('&#39;', "'"))


def slant(crop):
    """→ 倾角（度），量不了返回 None。

    判据是**列投影的集中度** sum(col^2)/sum(col)^2：竖笔扶正后叠在同一列，
    这个值最大。比 Hough 找直线稳——铅印的竖笔又短又粗，Hough 在 400 dpi
    下几乎找不到成形的线段。
    """
    h, w = crop.shape
    if h < 10 or w < 14:
        return None                       # 太小，噪声压过信号
    best, bs = None, -1.0
    for deg in ANGLES:
        k = float(np.tan(np.deg2rad(deg)))
        m = np.float32([[1, k, -k * h / 2], [0, 1, 0]])
        sh = cv2.warpAffine(crop, m, (int(w + abs(k) * h) + 2, h),
                            flags=cv2.INTER_NEAREST)
        col = sh.sum(axis=0).astype(np.float64)
        tot = col.sum()
        if tot <= 0:
            continue
        sc = (col ** 2).sum() / tot ** 2
        if sc > bs:
            best, bs = float(deg), sc
    return best


def page_slant(args):
    pdf, idx = args
    doc = fitz.open(pdf)
    pix = doc[idx].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
    doc.close()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    den = cv2.medianBlur(img, 3)
    bw = cv2.threshold(den, 0, 255,
                       cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    with tempfile.TemporaryDirectory() as td:
        png = os.path.join(td, 'p.png')
        cv2.imwrite(png, den)
        out = os.path.join(td, 'o')
        r = subprocess.run(['tesseract', png, out, '-l', 'eng+lat',
                            '--psm', '6', 'hocr'], capture_output=True)
        if r.returncode != 0:
            return idx, []
        h = open(out + '.hocr', encoding='utf-8').read()
    lines = []
    for inner in LINE_RE.findall(h):
        ws = []
        for m in WORD_RE.finditer(inner):
            txt = unescape(re.sub(r'<[^>]+>', '', m.group(5))).strip()
            if not txt:
                continue
            x0, y0, x1, y1 = (int(m.group(i)) for i in range(1, 5))
            ws.append([txt, slant(bw[y0:y1, x0:x1])])
        if ws:
            lines.append({'text': ' '.join(w[0] for w in ws), 'words': ws})
    return idx, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', type=int, choices=(1, 2))
    ap.add_argument('--pages')
    ap.add_argument('--workers', type=int, default=8)
    a = ap.parse_args()
    for vol in ([a.vol] if a.vol else (1, 2)):
        lo, hi = RANGES[vol]
        if a.pages:
            lo, hi = (int(x) for x in a.pages.split('-'))
        pdf = str(RAW / PDFS[vol])
        idxs = list(range(lo, hi + 1))
        tag = '_sample' if a.pages else ''
        out = RAW / f'vol{vol}_slant{tag}.jsonl'
        print(f'▶ vol{vol}  {len(idxs)} 页  workers={a.workers} → {out.name}',
              flush=True)
        res = {}
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            for k, (idx, lines) in enumerate(
                    ex.map(page_slant, [(pdf, i) for i in idxs]), 1):
                res[idx] = lines
                if k % 25 == 0:
                    print(f'  {k}/{len(idxs)}', flush=True)
        with out.open('w', encoding='utf-8') as fh:
            for i in idxs:
                fh.write(json.dumps({'page': i, 'lines': res[i]},
                                    ensure_ascii=False) + '\n')
        print(f'[ok] → {out.name}  {out.stat().st_size:,} 字节', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
