#!/usr/bin/env python3
"""抽一张印面，把页面影像与我们这一页的正文摆到一起，只问「哪里对不上」。

与以赛亚那支（isaiah_page_proofread.py）同一个道理，但**锚定方式简单得多**：
以赛亚要拿 PDF 文本层去正文里找锚点（段落常横跨三页），这里我们手上就有
**逐页的 OCR 产物**，`extract_johnstone.page_text` 能直接还原「这一页是哪些
字」，拿它的首尾若干词去最终产物里切片即可。

    python3 scripts/johnstone_page_proofread.py --leaves 60,140,220
    python3 scripts/johnstone_page_proofread.py --sample 6
"""
import argparse
import difflib
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alexander_abbyy as A
import extract_johnstone as E

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'johnstone', 'philippians')
IMG = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'src', 'images')
WORD = re.compile(r"[A-Za-zÆæ][A-Za-zÆæ0-9'’-]*")


def published_text():
    buf = []
    for f in sorted(os.listdir(OUT)):
        if f.endswith('.md'):
            buf.append(open(os.path.join(OUT, f), encoding='utf-8')
                       .read().split('---', 2)[-1])
    return '\n\n'.join(buf)


def page_slice(leaf, ab, ocr, first, shapes, whole):
    """这一页在最终产物里的那一段。锚不上就直说，不硬切。"""
    raw = E.page_text([p['text'] for p in ab[leaf]['pars']], ocr[leaf],
                      first.get(leaf, ''), shapes)
    # ⚠️ 锚点**只拿词做定位，切片要切回原文**——早先直接返回「只剩词」的
    # 串，读出来的差异里一半是标点和数字被我自己抹掉的假象
    # （`In the 3rd verse` 显示成 `In the rd verse`）。
    ws = WORD.findall(raw.replace('*', ''))
    if len(ws) < 30:
        return None, raw
    def locate(words, text, start=0):
        pos, idx = start, 0
        for w in words:
            k = text.find(w, pos)
            if k < 0:
                return None
            if idx == 0:
                first = k
            pos = k + len(w)
            idx += 1
        return first, pos
    a1 = locate(ws[:6], whole)
    if not a1:
        return None, raw
    a2 = locate(ws[-6:], whole, a1[1])
    if not a2:
        return None, raw
    return whole[a1[0]:a2[1]], raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--leaves', default='')
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--seed', type=int, default=20261009)
    a = ap.parse_args()

    ab = A.parse_pages(E.load_xml())
    ocr = E.ocr_pages()
    for lf in E.drop_duplicate_leaves(ocr):
        del ocr[lf]
    first, shapes = E.learn_heads(ocr)
    sec = E.assign_leaves(ocr)
    whole = published_text()

    body = [l for l in sorted(ocr)
            if sec.get(l) not in ('front', None) and len(ocr[l]) > 20]
    if a.leaves:
        leaves = [int(x) for x in a.leaves.split(',')]
    else:
        random.seed(a.seed)
        leaves = sorted(random.sample(body, a.sample or 6))

    for leaf in leaves:
        got, raw = page_slice(leaf, ab, ocr, first, shapes, whole)
        png = os.path.join('/private/tmp/claude-502/-Users-yanpeifa-Documents-'
                           'whcjb-github-io/fd4418bf-65e5-4437-b2e8-bc716e2fae9d/'
                           'scratchpad', f'pp{leaf:04d}.png')
        try:
            from PIL import Image
            im = Image.open(os.path.join(IMG, f'{leaf:04d}.jp2'))
            im.resize((int(im.width * .62), int(im.height * .62))).save(png)
        except Exception as e:
            png = f'(裁图失败 {e})'
        print(f'===== leaf {leaf:04d}  节 {sec.get(leaf)}  影像 {png}')
        print('--- 我们的正文 ---')
        print(got if got else f'⚠️ 锚不上，原始页文：\n{raw[:600]}')
        print()


if __name__ == '__main__':
    main()
