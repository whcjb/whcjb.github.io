#!/usr/bin/env python3
"""对剩下的待判串**逐个取证**：同一块活字，三个模型各读一遍，全部记下来。

到这一步还留在待判里的串，看上下文几乎都是希伯来/希腊活字（「Kimchi
explains X as…」「the cognate X」「Greek phrase *(X)*」），但 heb/grc 那两
遍没把它们收进结果——因为那两遍只写**被接受**的读数，没被接受的连记录都
没有，于是「试过但没读出来」和「压根没试」在账上长得一模一样。

这里补上这笔账：拿 ABBYY 给的坐标裁同一块图，heb / grc / eng 各读一遍，
三个读数连同置信度**全部落盘**，谁也不筛。有了它才能分清：

  · heb/grc 读出成串希伯来/希腊字母  → 页面上印的就是外文，不是错字
  · eng 读回来还是同一串拉丁字母    → 页面上印的确实是这几个拉丁字母，
                                     那才是真的要翻影像判的那一类

用法：
    python3 scripts/isaiah_residue_probe.py   # 读 backlog 的待判清单
"""
import csv
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from isaiah_hebrew_ocr import BODY, GREEK, HEBREW, NS, PAD, PDF, XML, DPI, line_tokens, ocr

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / 'logs/alexander_isaiah_backlog.tsv'
OUT = ROOT / 'logs/alexander_isaiah_residue_probe.tsv'


def probe(job):
    png = job['png']
    heb, ch = ocr(png, 'heb')
    grc, cg = ocr(png, 'grc')
    eng, ce = ocr(png, 'eng')
    Path(png).unlink(missing_ok=True)
    return (job['vol'], job['scan_page'], job['garbage'],
            heb, round(ch), len(HEBREW.findall(heb)),
            grc, round(cg), len(GREEK.findall(grc)),
            eng, round(ce))


def main():
    want = {r['token'] for r in csv.DictReader(open(BACKLOG, encoding='utf-8'),
                                               delimiter='\t')}
    print(f'待判串 {len(want)} 个')
    rows = []
    for vol in ('v1', 'v2'):
        lo, hi = BODY[vol]
        doc = fitz.open(PDF[vol])
        idx = 0
        for _, el in ET.iterparse(XML[vol], events=('end',)):
            if el.tag != NS + 'page':
                continue
            idx += 1
            if not (lo <= idx <= hi):
                el.clear()
                continue
            pw, ph = int(el.get('width')), int(el.get('height'))
            page = doc[idx - 1]
            sx, sy = page.rect.width / pw, page.rect.height / ph
            jobs = []
            for line in el.iter(NS + 'line'):
                for txt, box in line_tokens(line):
                    # 按**子串**认，不按整词。已发布正文那一侧的串是切过的
                    # （`•sfost)` 里的 `sfost`、`rranb^ybr` 里的 `rranb`），
                    # 按整词比对 55 个只对上 22 个。
                    if not any(w in txt for w in want):
                        continue
                    clip = fitz.Rect((box[0] - PAD) * sx, (box[1] - PAD) * sy,
                                     (box[2] + PAD) * sx, (box[3] + PAD) * sy)
                    if clip.width <= 0 or clip.height <= 0:
                        continue
                    with tempfile.NamedTemporaryFile(suffix='.png',
                                                     delete=False) as fh:
                        png = fh.name
                    page.get_pixmap(dpi=DPI, clip=clip).save(png)
                    jobs.append(dict(png=png, vol=vol, scan_page=idx,
                                     garbage=re.sub(r'\s+', ' ', txt).strip()))
            el.clear()
            if jobs:
                with ThreadPoolExecutor(8) as pool:
                    rows.extend(pool.map(probe, jobs))
        doc.close()
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('vol\tscan_page\tgarbage\theb\theb_conf\theb_n\t'
                'grc\tgrc_conf\tgrc_n\teng\teng_conf\n')
        for r in rows:
            f.write('\t'.join(str(x) for x in r) + '\n')
    print(f'取证 {len(rows)} 条 → {OUT}')


if __name__ == '__main__':
    main()
