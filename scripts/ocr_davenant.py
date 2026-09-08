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
import json
import os
import subprocess
import sys
import re
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
PDFS = {1: 'expositionofepis01dave.pdf', 2: 'expositionofepis02dave.pdf'}
DPI = 400


LINE_RE = re.compile(
    r"class='ocr_line' id='[^']*' title=\"([^\"]*)\">(.*?)(?=<span class='ocr_line'"
    r"|</div>|\Z)", re.S)


def parse_hocr(h):
    """hOCR → [{x0,y0,x1,y1,size,text}]

    要 bbox 与 x_size：本书**脚注靠字号分**（正文 x_size 37–45、脚注 30–35，
    阈值 36，vol1 p88 实测双峰分明），段落靠首行缩进分。纯文本流里这两样
    都没有，只能靠空行猜——猜错的代价是半页正文被吞进脚注（实测过）。
    """
    rows = []
    for title, inner in LINE_RE.findall(h):
        b = re.search(r'bbox (\d+) (\d+) (\d+) (\d+)', title)
        xs = re.search(r'x_size ([\d.]+)', title)
        txt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', inner)).strip()
        txt = (txt.replace('&amp;', '&').replace('&lt;', '<')
                  .replace('&gt;', '>').replace('&quot;', '"')
                  .replace('&#39;', "'"))
        if b and txt:
            rows.append({'x0': int(b.group(1)), 'y0': int(b.group(2)),
                         'x1': int(b.group(3)), 'y1': int(b.group(4)),
                         'size': round(float(xs.group(1)), 1) if xs else 0.0,
                         'text': txt})
    return rows


def ocr_page(args):
    pdf, idx = args
    doc = fitz.open(pdf)
    pix = doc[idx].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
    doc.close()
    with tempfile.TemporaryDirectory() as td:
        png = os.path.join(td, 'p.png')
        pix.save(png)
        out = os.path.join(td, 'o')
        r = subprocess.run(['tesseract', png, out, '-l', 'eng+lat', '--psm', '6',
                            'txt', 'hocr'], capture_output=True)
        if r.returncode != 0:
            return idx, f'!!OCR_FAIL rc={r.returncode}', []
        txt = open(out + '.txt', encoding='utf-8').read()
        rows = parse_hocr(open(out + '.hocr', encoding='utf-8').read())
        return idx, txt, rows


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
    # 试跑（--pages）写到 *_sample，**绝不覆盖整卷产物**
    tag = '_sample' if a.pages else ''
    out = RAW / f'vol{a.vol}_ocr{tag}.txt'
    print(f'▶ vol{a.vol}  {len(idxs)} 页  workers={a.workers}  → {out.name}', flush=True)

    res, geo = {}, {}
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for k, (idx, txt, rows) in enumerate(
                ex.map(ocr_page, [(pdf, i) for i in idxs]), 1):
            res[idx] = txt
            geo[idx] = rows
            if k % 25 == 0:
                print(f'  {k}/{len(idxs)}', flush=True)
    with out.open('w', encoding='utf-8') as fh:
        for i in idxs:
            fh.write(f'<!-- PAGE {i} -->\n{res[i].rstrip()}\n\n')
    gout = RAW / f'vol{a.vol}_lines{tag}.jsonl'
    with gout.open('w', encoding='utf-8') as fh:
        for i in idxs:
            fh.write(json.dumps({'page': i, 'lines': geo[i]},
                                ensure_ascii=False) + '\n')
    print(f'✓ 写出 {out}  {out.stat().st_size:,} 字节', flush=True)
    print(f'✓ 写出 {gout}  {gout.stat().st_size:,} 字节  '
          f'{sum(len(v) for v in geo.values())} 行', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
