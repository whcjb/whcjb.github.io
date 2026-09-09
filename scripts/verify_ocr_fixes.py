#!/usr/bin/env python3
"""回填后的第二证人：把底本那一页**高分辨率重 OCR**，看它站哪一边。

为什么需要
----------
约翰福音那本 PDF 自带一层文本（另一次独立 OCR），可以当第二证人。罗马书这本
是纯扫描，`get_text()` 返回空，这条路没有。而判读（模型看图）会出**纯误读**：
p236 报「最→既」，800 dpi 渲染出来白纸黑字是「又因为他最配称为」，模型连
「配」都读成了「被」。这种错必须挡在回填之前。

做法：用 tesseract 以 450 dpi 重新 OCR 该页（`calvin_raw/*-scan/ocr` 那份是
早先低分辨率跑的，两者是**不同样本**），然后看这一页里出现的是影像侧还是文本侧：

    新串在、旧串不在  → 支持判读，放行
    旧串在、新串不在  → 否证判读，拦下
    都在 / 都不在      → 判不了，标出来人工看图

判据只在**页**这一级；落点仍由 apply_ocr_fixes4 的页区间 + 上下文负责。

用法：
    python3 scripts/verify_ocr_fixes.py --pdf <底本.pdf> --tsv logs/applied4_romans.tsv \
        [--dpi 450] [--out logs/verify4_romans.tsv]
"""
import argparse
import csv
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import fitz

CJK = re.compile(r'[一-鿿]')


def cj(s):
    return ''.join(CJK.findall(s))


def ocr_page(doc, pg, dpi, lang='chi_sim'):
    pm = doc[pg - 1].get_pixmap(dpi=dpi)
    with tempfile.TemporaryDirectory() as td:
        img = f'{td}/p.png'
        pm.save(img)
        out = subprocess.run(['tesseract', img, 'stdout', '-l', lang, '--psm', '6'],
                             capture_output=True, text=True).stdout
    return cj(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--tsv', required=True)
    ap.add_argument('--dpi', type=int, default=450)
    ap.add_argument('--out')
    a = ap.parse_args()

    doc = fitz.open(a.pdf)
    rows = [l.rstrip('\n').split('\t') for l in
            Path(a.tsv).read_text(encoding='utf-8').splitlines() if l.strip()]
    cache, stat, out = {}, Counter(), []
    for i, r in enumerate(rows, 1):
        pg, old, new = int(r[0]), cj(r[2]), cj(r[3])
        if not old or not new:
            stat['跳过·无汉字'] += 1
            continue
        if pg not in cache:
            cache[pg] = ocr_page(doc, pg, a.dpi)
            if len(cache) % 20 == 0:
                print(f'  …已重 OCR {len(cache)} 页（第 {i}/{len(rows)} 条）', flush=True)
        t = cache[pg]
        has_new, has_old = new in t, old in t
        if has_new and not has_old:
            v = '支持'
        elif has_old and not has_new:
            v = '否证'
        elif has_new and has_old:
            v = '两者皆在'
        else:
            v = '皆不在'
        stat[v] += 1
        out.append((r[0], r[1], r[2], r[3], v, r[4] if len(r) > 4 else ''))

    for k, v in stat.most_common():
        print(f'  {k}: {v}')
    if a.out:
        Path(a.out).write_text(
            '\n'.join('\t'.join(x) for x in out) + '\n', encoding='utf-8')
        print(f'明细 → {a.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
