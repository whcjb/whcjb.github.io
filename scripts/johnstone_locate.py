#!/usr/bin/env python3
"""约翰斯通：拿一段正文片段 → 找到它在哪张印面、哪几行 → 裁出那几行的影像。

逐处按影像判读时用。定位靠 ABBYY XML 的行坐标（每行一个 bbox），比按页高
百分比瞎裁准；文字比对只用小写字母，标点、引号、斜体一概不管——要查的
正是这些符号，拿它们去对就对不上了。

    python3 scripts/johnstone_locate.py "and He was faithful to Him" [-o out.png] [--pad 1]

输出：leaf、行号、那几行的 ABBYY 文本，并写出裁图。找不到就直说。
"""
import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, 'johnstone_raw', 'philippians')
IMG = os.path.join(RAW, 'src', 'images')
XML = os.path.join(RAW, 'src', 'abbyy1875.xml')
CACHE = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'johnstone_lines.json')
NS = '{http://www.abbyy.com/FineReader_xml/FineReader6-schema-v1.xml}'


def key(s):
    return re.sub(r'[^a-z]', '', s.lower())


def load_lines():
    if os.path.exists(CACHE) and os.path.getmtime(CACHE) > os.path.getmtime(XML):
        return json.load(open(CACHE))
    pages = []
    for _, el in ET.iterparse(XML, events=('end',)):
        if el.tag != NS + 'page':
            continue
        lines = []
        for ln in el.iter(NS + 'line'):
            txt = ''.join(cp.text or '' for cp in ln.iter(NS + 'charParams'))
            lines.append([txt, int(ln.get('l')), int(ln.get('t')),
                          int(ln.get('r')), int(ln.get('b'))])
        pages.append(lines)
        el.clear()
    json.dump(pages, open(CACHE, 'w'))
    return pages


def locate(snippet, pages):
    """返回 [(leaf, i0, i1)]：leaf 是 0 起的页序（与 images/NNNN.jp2 同号）。"""
    k = key(snippet)
    hits = []
    for leaf, lines in enumerate(pages):
        keys = [key(l[0]) for l in lines]
        flat = ''.join(keys)
        start = 0
        while True:
            p = flat.find(k, start)
            if p < 0:
                break
            # 字符偏移 → 行号
            acc, i0, i1 = 0, None, None
            for i, kk in enumerate(keys):
                if i0 is None and acc + len(kk) > p:
                    i0 = i
                if acc + len(kk) >= p + len(k):
                    i1 = i
                    break
                acc += len(kk)
            hits.append((leaf, i0, i1))
            start = p + 1
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('snippet')
    ap.add_argument('-o', '--out')
    ap.add_argument('--pad', type=int, default=1, help='上下各多带几行')
    a = ap.parse_args()
    pages = load_lines()
    hits = locate(a.snippet, pages)
    if not hits:
        print('NOT FOUND'); sys.exit(1)
    for n, (leaf, i0, i1) in enumerate(hits):
        lines = pages[leaf]
        j0, j1 = max(0, i0 - a.pad), min(len(lines) - 1, i1 + a.pad)
        print(f'leaf {leaf:04d} lines {i0}-{i1}')
        for j in range(j0, j1 + 1):
            print('   ', lines[j][0])
        if a.out:
            from PIL import Image
            im = Image.open(os.path.join(IMG, f'{leaf:04d}.jp2'))
            box = (0, max(0, min(l[2] for l in lines[j0:j1 + 1]) - 12), im.size[0],
                   min(im.size[1], max(l[4] for l in lines[j0:j1 + 1]) + 12))
            out = a.out if n == 0 else re.sub(r'(\.\w+)$', rf'_{n}\1', a.out)
            im.crop(box).save(out)
            print('   →', out)


if __name__ == '__main__':
    main()
