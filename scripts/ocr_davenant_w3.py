#!/usr/bin/env python3
"""第三证人：把两卷正文页按**另一套预处理与另一档参数**重新 OCR 一遍。

为什么还要第三份
----------------
第一份是我们自己那遍（`ocr_davenant.py`：400 dpi、`eng+lat`、`--psm 6`），
第二份是 PDF 自带的 IA 文本层（`davenant_witness.py`）。两份都是 tesseract
出的，绝大多数错不重叠，但**重叠的那一部分修不动**——用户圈出来的
`have xot seen my face, Kc.` 就是标本：我们读 `xot` / `Kc.`，IA 读
`iiot` / `&,c.`，两边都花，两两相校无解。

这一份刻意与前两份都不同（见 memory「不要用生成式模型做OCR」里实测过的配置）：

    渲染   600 dpi（前一份是 400；这一本的 PDF 页只有 326×564 pt，
           按原生分辨率渲出来才 326 px 宽，整页读成乱码，实测过）
    预处理 cv2.medianBlur(3)  去扫描噪点，OOV 率 8.6% → 6.0%
    参数   -l eng+lat --psm 4（单栏逐行；前一份用的 psm 6 整块）

输出 davenant_raw/colossians/vol{1,2}_w3.jsonl，每行一页 {page, text}。

用法:
    python3 scripts/ocr_davenant_w3.py --vol 1 --pages 420-425   # 试跑
    python3 scripts/ocr_davenant_w3.py                           # 两卷正文页
"""
import argparse
import json
import os
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
# 覆盖到卷二末尾：附卷《论基督之死》、法国之争与六种索引都在 318 页之后，
# 只跑到 317 的话那一半书拿不到第三证人（附卷同样有词内数字与撇号的错）。
RANGES = {1: (86, 631), 2: (14, 620)}


def ocr_page(args):
    pdf, idx = args
    doc = fitz.open(pdf)
    pix = doc[idx].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
    doc.close()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    img = cv2.medianBlur(img, 3)
    with tempfile.TemporaryDirectory() as td:
        png = os.path.join(td, 'p.png')
        cv2.imwrite(png, img)
        out = os.path.join(td, 'o')
        r = subprocess.run(['tesseract', png, out, '-l', 'eng+lat', '--psm', '4'],
                           capture_output=True)
        if r.returncode != 0:
            return idx, ''
        return idx, open(out + '.txt', encoding='utf-8').read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', type=int, choices=(1, 2))
    ap.add_argument('--pages', help='如 420-425（0-based，含两端）')
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    for vol in ([a.vol] if a.vol else (1, 2)):
        lo, hi = RANGES[vol]
        if a.pages:
            lo, hi = (int(x) for x in a.pages.split('-'))
        pdf = str(RAW / PDFS[vol])
        idxs = list(range(lo, hi + 1))
        tag = '_sample' if a.pages else ''
        out = RAW / f'vol{vol}_w3{tag}.jsonl'
        print(f'▶ vol{vol}  {len(idxs)} 页  workers={a.workers} → {out.name}',
              flush=True)
        res = {}
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            for k, (idx, txt) in enumerate(
                    ex.map(ocr_page, [(pdf, i) for i in idxs]), 1):
                res[idx] = txt
                if k % 25 == 0:
                    print(f'  {k}/{len(idxs)}', flush=True)
        with out.open('w', encoding='utf-8') as fh:
            for i in idxs:
                fh.write(json.dumps({'page': i, 'text': res[i]},
                                    ensure_ascii=False) + '\n')
        print(f'[ok] → {out.name}  {out.stat().st_size:,} 字节', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
