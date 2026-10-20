#!/usr/bin/env python3
"""以赛亚书：按页面影像判读过的外文（希伯来/希腊）落回发布页——链条最后一步。

前面几道（闭集选词、tesseract + 视觉证人逐字一致）救不回来的外文，发布页上
要么是 `[Heb.]` / `[Gk.]` 占位，要么是根本没被认出来的拉丁乱码（`bloxJujQia)`、
`ta`、`OQOS`），要么整串丢了（14:15 末 `τὰ θεμέλια.`）。这些只能回到印面。

底图是 IA 原始扫描（与 ABBYY XML 同一坐标系，2696×4394 量级，比 PDF 里的
167 dpi 降采样图清楚三倍）；每条都是裁图看过的，依据写在 basis 列：

    img=wit    影像判读 = 视觉证人先前的读数（同位、逐字母）
    img=tess   影像判读 = tesseract 对高分辨率裁图的某一路读数
    img+wlc    影像判读，且每个词都在马所拉文本词形表里（希伯来）
    img+lxx    影像判读，且每个词都在七十士译本/新约词形表里（希腊）
    auto       视觉证人 = 高分辨率 tesseract（两家同位逐字一致，未另看图）

表 alexander_raw/isaiah/foreign_image.tsv：
    chapter  before  old  new  basis  vol  page
按**字面串** before+old 在该章 md 里替换成 before+new；before+old 必须在该章唯一。
已经是 before+new 的跳过（幂等）。找不到、不唯一都报出来，不落。

    python3 scripts/isaiah_apply_image.py           # 只报告
    python3 scripts/isaiah_apply_image.py --apply   # 落盘
"""
import argparse
import collections
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / 'alexander_raw/isaiah/foreign_image.tsv'
PUB = ROOT / 'alexander/isaiah'


def load():
    rows = []
    with TSV.open(encoding='utf-8') as f:
        for r in csv.DictReader((ln for ln in f if not ln.startswith('#')), delimiter='\t',
                                quoting=csv.QUOTE_NONE):
            rows.append(r)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    rows = load()
    by_ch = collections.defaultdict(list)
    for r in rows:
        by_ch[r['chapter']].append(r)
    stat = collections.Counter()
    bad = []
    for ch, rs in sorted(by_ch.items()):
        path = PUB / f'{ch}.md'
        text = path.read_text(encoding='utf-8')
        orig = text
        for r in rs:
            b = r['before'].replace('\\t', '\t').replace('\\n', '\n')
            old, new = r['old'], r['new']
            if b + new in text and (b + old) not in text:
                stat['已落'] += 1
                continue
            n = text.count(b + old)
            if n == 1:
                text = text.replace(b + old, b + new)
                stat['落'] += 1
            else:
                stat['找不到' if n == 0 else '不唯一'] += 1
                bad.append((ch, n, b[-30:], old, new))
        if a.apply and text != orig:
            path.write_text(text, encoding='utf-8')
    print('影像判读外文:', dict(stat))
    for x in bad[:40]:
        print('  ✗', x)
    if bad and a.apply:
        raise SystemExit(f'{len(bad)} 条没落上（见上）——修复表与发布页对不上，先查清再提交')


if __name__ == '__main__':
    main()
