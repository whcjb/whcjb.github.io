#!/usr/bin/env python3
"""达文南特《歌罗西书注释》（Allport 英译 1831，两卷）扫描件 OCR。

底本是 Internet Archive 的扫描件（普林斯顿神学院藏本），自带的 OCR 层是
IA 用 tesseract 生成的 `GlyphLessFont` 隐形文本，**不含任何字形信息**，
且小型大写全部塌成小写（`EPISTLE TO THE COLOSSIANS` → `to the colossians`）、
词间双空格、错字略多（`saints` → `sai?its`）。故重新 OCR。

语言包：`eng+lat`。**不要加 grc**——实测会把小型大写的页眉 `Ver. 3.`
读成希腊字母 `Ρεν, 8.`。本书希腊词零散出现，另行处理（见 DIAGNOSIS.md）。

用法:
    python3 scripts/ocr_davenant.py --vol 1 --pages 80-120   # 试跑
    python3 scripts/ocr_davenant.py --vol 1                  # 整卷
"""
import argparse
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
PDFS = {1: 'expositionofepis01dave.pdf', 2: 'expositionofepis02dave.pdf'}
DPI = 400


def ocr_page(args):
    pdf, idx = args
    doc = fitz.open(pdf)
    pix = doc[idx].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
    doc.close()
    with tempfile.TemporaryDirectory() as td:
        png = os.path.join(td, 'p.png')
        pix.save(png)
        out = os.path.join(td, 'o')
        r = subprocess.run(['tesseract', png, out, '-l', 'eng+lat', '--psm', '6'],
                           capture_output=True)
        if r.returncode != 0:
            return idx, f'!!OCR_FAIL rc={r.returncode}'
        return idx, open(out + '.txt', encoding='utf-8').read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', type=int, required=True, choices=(1, 2))
    ap.add_argument('--pages', help='如 80-120（0-based，含两端）')
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()

    pdf = str(RAW / PDFS[a.vol])
    doc = fitz.open(pdf); n = doc.page_count; doc.close()
    if a.pages:
        lo, hi = (int(x) for x in a.pages.split('-'))
    else:
        lo, hi = 0, n - 1
    idxs = list(range(lo, min(hi, n - 1) + 1))
    out = RAW / f'vol{a.vol}_ocr.txt'
    print(f'▶ vol{a.vol}  {len(idxs)} 页  workers={a.workers}  → {out.name}', flush=True)

    res = {}
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for k, (idx, txt) in enumerate(ex.map(ocr_page, [(pdf, i) for i in idxs]), 1):
            res[idx] = txt
            if k % 25 == 0:
                print(f'  {k}/{len(idxs)}', flush=True)
    with out.open('w', encoding='utf-8') as fh:
        for i in idxs:
            fh.write(f'<!-- PAGE {i} -->\n{res[i].rstrip()}\n\n')
    print(f'✓ 写出 {out}  {out.stat().st_size:,} 字节', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
