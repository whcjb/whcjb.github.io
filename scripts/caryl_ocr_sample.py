#!/usr/bin/env python3
"""卡里尔缺部 OCR：抽一页实读（old-book-ocr §4.5），跳过 read_pages.tsv 里已读过的叶。

    /usr/bin/python3 scripts/caryl_ocr_sample.py p9 <seed> [图高=2600]   # 打印该页当前文字，渲一张整页图到 --out
    /usr/bin/python3 scripts/caryl_ocr_sample.py p9 --leaf 572 --text    # 只打印某叶的文字（已读过的叶用这个，不再出图）

读完把错处落 manual_fixes.tsv，叶号追记 read_pages.tsv。每页图只读一次。
"""
import argparse
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'caryl_raw' / 'job_ocr'
LEDGER = BASE / 'read_pages.tsv'


def read_leaves():
    out = set()
    for ln in LEDGER.read_text(encoding='utf-8').splitlines() if LEDGER.exists() else []:
        if ln.startswith('#') or not ln.strip():
            continue
        f = ln.split('\t')
        out.add((f[0], int(f[1])))
    return out


def pages(part):
    docs = {f.stem: f.read_text(encoding='utf-8') for f in (BASE / part / 'fixed').glob('*.md')}
    allp = []
    for slug, md in docs.items():
        for m in re.finditer(r'<span class="cy-pb" id="p(\d+)" data-p="[^"]+" data-leaf="(\d+)"', md):
            allp.append((int(m.group(1)), int(m.group(2)), slug))
    return docs, sorted(allp)


def page_text(md, leaf):
    a = md.index(f'data-leaf="{leaf}"')
    a = md.rindex('<span', 0, a)
    b = md.find('<span class="cy-pb"', a + 10)
    t = md[a:len(md) if b < 0 else b]
    t = re.sub(r'<span class="cy-pb"[^>]*></span>', '', t)
    t = re.sub(r'<span class="cy-ocr"[^>]*>(.*?)</span>', r'⟨\1⟩', t)
    t = re.sub(r'<span class="cy-margin">(.*?)</span>', r' [旁注: \1] ', t)
    return re.sub(r'<div class="commentary-anchor"[^>]*></div>', '', t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('part')
    ap.add_argument('seed', nargs='?', type=int, default=0)
    ap.add_argument('height', nargs='?', type=int, default=2600)
    ap.add_argument('--leaf', type=int)
    ap.add_argument('--text', action='store_true')
    ap.add_argument('--out', default='leaf.jpg')
    a = ap.parse_args()
    docs, allp = pages(a.part)
    done = read_leaves()
    if a.leaf is not None:
        hit = [x for x in allp if x[1] == a.leaf]
    else:
        random.seed(a.seed)
        hit = [random.choice([x for x in allp if (a.part, x[1]) not in done])]
    n, leaf, slug = hit[0]
    t = page_text(docs[slug], leaf)
    seen = (a.part, leaf) in done
    print('page', n, 'leaf', leaf, 'slug', slug, 'words', len(t.split()), '（已读过，不再出图）' if seen else '')
    print(t)
    if a.text or seen:
        return
    import cv2
    g = cv2.imread(str(BASE / a.part / 'img' / f'{leaf:04d}.jpg'), 0)
    s = a.height / g.shape[0]
    cv2.imwrite(a.out, cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])


if __name__ == '__main__':
    main()
