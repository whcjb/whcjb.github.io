#!/usr/bin/env python3
"""全书 OCR 交叉验证：找出 PDF 文字层与印刷字形不一致的字。

背景：这本《箴言书注释》PDF 的正文字体 ToUnicode 表有坏映射，导出的文字层
里若干汉字被指到了别的字上（缄=终、缂=细、绿=练…）。**以 PDF 印出来的字
为准**，文字层不可信。

做法：逐页 300dpi 渲染 → tesseract chi_sim OCR → 与文字层逐字比对。
OCR 自身错误率约 5%（它把「箴」读成「艇」），所以不能拿 OCR 当依据，只用
它筛候选。映射错的特征是：

    某个字**每次**出现都与 OCR 不一致，且 OCR **每次都读成同一个字**

相对地「忏→慎」「谬→廖」「诫→诚」也是 100% 分歧，但忏悔/谬误/诫命本身
通顺，那是 OCR 读错。所以候选出来之后必须逐个裁 PDF 字形肉眼定夺，
确认了才写进 extract_bridges_proverbs.py 的 GLYPH_FIX。

用法：
    python3 scripts/bridges_ocr_audit.py            # 全书
    python3 scripts/bridges_ocr_audit.py 100 200    # 只跑 p100-200（0-based）
产物：$BRIDGES_OCR_OUT/pN.txt，以及末尾打印的候选表。
图片 OCR 完即删，982 页否则要占几个 G。
"""
import fitz, os, re, subprocess, sys, difflib
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

PDF = '/Users/yanpeifa/Documents/论文/改革宗经典文献/Final-PDF-Proverbs箴言.pdf'
# 不要放 /tmp：那里 python 写的 png，tesseract 子进程看不到（沙箱隔离），
# 表现为 Leptonica 'image file not found'，产出一堆 0 字节 txt。
OUT = os.environ.get('BRIDGES_OCR_OUT', '/private/tmp/claude-502/-Users-yanpeifa-Documents-whcjb-github-io/7fb9d2ac-c7bb-4de0-b1b0-a6ac52a4e174/scratchpad/bridges_ocr')


def ocr_page(p):
    out = f'{OUT}/p{p}'
    if os.path.exists(out + '.txt'):
        return p
    doc = fitz.open(PDF)                       # 每个子进程各开一次，句柄不能跨进程
    png = f'{OUT}/p{p}.png'
    doc[p].get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72)).save(png)
    subprocess.run(['tesseract', png, out, '-l', 'chi_sim', '--psm', '6'],
                   capture_output=True)
    os.remove(png)                             # 边跑边删，否则几个 G
    return p


def main():
    os.makedirs(OUT, exist_ok=True)
    doc = fitz.open(PDF)
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else doc.page_count
    pages = list(range(lo, hi))
    print(f'OCR {len(pages)} 页 …', flush=True)
    with ProcessPoolExecutor(max_workers=6) as ex:
        for i, _ in enumerate(ex.map(ocr_page, pages), 1):
            if i % 50 == 0:
                print(f'  {i}/{len(pages)}', flush=True)

    han = lambda s: ''.join(c for c in s if '一' <= c <= '鿿')
    pair, total, pgs = Counter(), Counter(), defaultdict(set)
    for p in pages:
        f = f'{OUT}/p{p}.txt'
        if not os.path.exists(f):
            continue
        L, O = han(doc[p].get_text()), han(open(f, encoding='utf-8', errors='replace').read())
        total.update(L)
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, L, O, autojunk=False).get_opcodes():
            if tag == 'replace' and i2 - i1 == 1 and j2 - j1 == 1:
                pair[(L[i1], O[j1])] += 1
                pgs[(L[i1], O[j1])].add(p)

    print('\n★ 候选（该字每次出现都与 OCR 不一致，且 OCR 读法一致）：')
    cand = [(a, b, n, len(pgs[(a, b)]), total[a])
            for (a, b), n in pair.items() if total[a] >= 3 and n == total[a]]
    for a, b, n, np_, t in sorted(cand, key=lambda x: -x[2]):
        print(f'   「{a}」→OCR「{b}」 {n}/{t} 次，{np_} 页')
    print('\n次级候选（分歧率 ≥85%，需人工看）：')
    for (a, b), n in sorted(pair.items(), key=lambda x: -x[1]):
        if total[a] >= 5 and n < total[a] and n / total[a] >= .85:
            print(f'   「{a}」→OCR「{b}」 {n}/{total[a]} 次，{len(pgs[(a,b)])} 页')


if __name__ == '__main__':
    main()
