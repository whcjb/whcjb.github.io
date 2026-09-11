#!/usr/bin/env python3
"""把诗篇正文里的希伯来文／希腊文活字**重新 OCR 回来**。

Alexander 逐节辨析希伯来原文，正文里希伯来活字与希腊文引文极密。IA 那遍
ABBYY 是按拉丁字母跑的，这些活字被读成一串拉丁乱码（`(^<J)`、`/v^H ynj<7`、
`D''ilD`），判词典、第二证人、页面影像三条路都救不了：证人是同样按拉丁
字母 OCR 的，影像只能告诉人「这里是希伯来文」。诗篇最后那 623 处
「外文与活字残渣」的大头就是它们。

解法与以赛亚线同：ABBYY XML 里每个字符都带坐标，据此从 PDF 原图按 600dpi
裁出那几个字，交给 tesseract 的 `heb` / `grc` 模型重读。判读逻辑（候选判据、
双引擎对比、置信度门槛）直接复用 `isaiah_hebrew_ocr`，本文件只提供诗篇的
页序标定与驱动——两本书的差别全在「哪一页对哪一页」上。

**页序标定**：PDF 584 页、XML 590 页，两者本身错位（PROVENANCE 记过，
不许拿页序号互相套）。实测 `pdf_index = xml_index - 2`，用页眉里印的
书页页码在 XML 第 100/200/500 页与 PDF 第 98/198/498 页上各核过一次。

用法：
    python3 scripts/psalms_hebrew_ocr.py --pages 100-120   # 先试一段
    python3 scripts/psalms_hebrew_ocr.py                   # 全书
"""
import argparse
import gzip
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_lexicon import build
from isaiah_hebrew_ocr import NS, crop, judge, line_tokens, looks_residue

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander_raw/psalms/src'
OUT = ROOT / 'alexander_raw/psalms/hebrew_ocr.tsv'
PDF = Path.home() / 'Documents/论文/alexander/psalms_1864_kregel.pdf'
XML_GZ = SRC / 'abbyy1864.xml.gz'

# 正文范围（XML 页序）：p14–21 著者序，p22–577 正文；p12–13 是 Kregel 1991 年
# 新写的 FOREWORD、p578 起是书目广告，两者都不在公有领域文本内，不扫。
BODY = (14, 577)

# pdf_index = xml_index + OFFSET。见模块说明里的标定。
OFFSET = -2


def unpack_xml():
    """XML 是 gz 的，iterparse 要个真文件；解到临时目录，跑完删。"""
    tmp = Path(tempfile.mkdtemp()) / 'abbyy1864.xml'
    with gzip.open(XML_GZ, 'rb') as fi, open(tmp, 'wb') as fo:
        shutil.copyfileobj(fi, fo)
    return tmp


def main(page_range=None, junk_only=False):
    lex = build()
    xml = unpack_xml()
    doc = fitz.open(PDF)
    rows = []
    n_page = 0
    lo, hi = BODY
    try:
        for _, el in ET.iterparse(xml, events=('end',)):
            if el.tag != NS + 'page':
                continue
            n_page += 1
            idx = n_page
            if not (lo <= idx <= hi) or (page_range and not
                                         (page_range[0] <= idx <= page_range[1])):
                el.clear()
                continue
            pdf_i = idx + OFFSET
            if not (0 <= pdf_i < doc.page_count):
                el.clear()
                continue
            pw, ph = int(el.get('width')), int(el.get('height'))
            page = doc[pdf_i]
            sx, sy = page.rect.width / pw, page.rect.height / ph
            jobs = []
            for line in el.iter(NS + 'line'):
                toks = line_tokens(line)
                run = []
                for txt, box in toks + [(None, None)]:
                    if (txt is not None and looks_residue(txt, lex, junk_only)
                            and len(run) < 4):
                        run.append((txt, box))
                        continue
                    if run:
                        j = crop(run, toks, page, sx, sy, 'psalms', idx)
                        if j:
                            jobs.append(j)
                        run = []
            el.clear()
            if jobs:
                with ThreadPoolExecutor(8) as pool:
                    rows.extend(r for r in pool.map(judge, jobs) if r)
            if idx % 25 == 0:
                print(f'扫描页 {idx}：累计读出 {len(rows)} 段', flush=True)
    finally:
        doc.close()
        shutil.rmtree(xml.parent, ignore_errors=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('book\tscan_page\tbefore\tgarbage\tafter\tscript\treading\tconf\n')
        for r in rows:
            f.write('\t'.join(str(x) for x in r) + '\n')
    print(f'读出 {len(rows)} 段 → {OUT}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', help='只跑这段扫描页，如 100-120')
    ap.add_argument('--junk', action='store_true', help='只跑带垃圾字符那一档')
    a = ap.parse_args()
    pr = tuple(int(x) for x in a.pages.split('-')) if a.pages else None
    main(pr, a.junk)
