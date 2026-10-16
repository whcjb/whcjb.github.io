#!/usr/bin/env python3
"""帕金斯《加拉太书注释》第二证人：IA 1604 扫描件自带的 OCR（hOCR）。

    python3 scripts/perkins_witness.py build     # hOCR → leaves.json + 印本页→leaf 对照
    python3 scripts/perkins_witness.py gaps      # 每处 TCP 缺字 → 证人在同一位置读出什么

为什么是它（old-book-ocr §1 第 ② 层）：TCP 录入用的就是这套 EEBO 缩微胶片的
页图，IA 那份 `bim_…_perkins-william_1604` 是同一版次（剑桥 Legat 1604，
755 叶 = TCP 378 张对开图 ×2）。它的 OCR 是 tesseract 出的——**非生成式**，
读不清只吐乱码、不编词——所以它给的候选可以当证据用，但只在

  1. 它与 TCP 在缺口两侧的词**按位置对齐**（左右各 ≥2 个词完全一致），
  2. 它读出的词与 TCP 已录的残字**逐字母相容**（`th•` 只接受 th?），
  3. 这个词在 TCP 全书里**另有出现**（语料自证，§1 第 ① 层）

三条同时成立时才落成候选；任何一条不满足就转去裁页图人工判读（第 ③ 层）。
"""
import html
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'perkins_raw' / 'galatians'
W = RAW / 'witness_1604'
ID = 'bim_early-english-books-1475-1640_a-commentarie-_perkins-william_1604'
HOCR = W / f'{ID}_hocr.html'
LEAVES = W / 'leaves.json'
PAGEMAP = RAW / 'pagemap.json'
SRC = RAW / 'en_chapters'

RE_PAGE = re.compile(r'<div class="ocr_page" id="page_(\d+)"')
RE_LINE = re.compile(r'<span class="ocr_line" id="([^"]+)" title="bbox (\d+) (\d+) (\d+) (\d+)')
RE_WORD = re.compile(r'<span class="ocrx_word" id="[^"]+" title="bbox (\d+) (\d+) (\d+) (\d+); x_wconf (\d+)[^"]*">([^<]*)</span>')


def nw(w):
    """归一化：长 s → s，u/v、i/j 不动（TCP 保留原拼法），只留字母。"""
    w = w.replace('ſ', 's').replace('ﬅ', 'st').replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    return re.sub(r'[^a-z]', '', w.lower())


def build():
    text = HOCR.read_text(encoding='utf-8')
    starts = [m.start() for m in RE_PAGE.finditer(text)] + [len(text)]
    leaves = []
    for i in range(len(starts) - 1):
        chunk = text[starts[i]:starts[i + 1]]
        words = []
        for lm in RE_LINE.finditer(chunk):
            end = chunk.find('</span>\n     </span>', lm.end())
            seg = chunk[lm.end(): end if end > 0 else lm.end() + 20000]
            seg = seg.split('class="ocr_line"')[0]
            for wm in RE_WORD.finditer(seg):
                x0, y0, x1, y1, conf, w = wm.groups()
                words.append([html.unescape(w), int(x0), int(y0), int(x1), int(y1),
                              int(conf), lm.group(1)])
        leaves.append(words)
    LEAVES.write_text(json.dumps(leaves), encoding='utf-8')
    print(f'{len(leaves)} 叶，{sum(map(len, leaves))} 词', file=sys.stderr)

    # 印本页 → leaf：拿 TCP 每页正文的词序列与相邻 leaf 比相似度。
    pages = page_texts()
    lw = [[nw(w[0]) for w in L if nw(w[0])] for L in leaves]
    mapping = {}
    guess = 0
    for key, words in pages:
        best = (0, None)
        lo, hi = max(0, guess - 6), min(len(lw), guess + 30)
        for j in range(lo, hi):
            r = SequenceMatcher(None, words[:150], lw[j][:220], autojunk=False).ratio()
            if r > best[0]:
                best = (r, j)
        if best[0] < 0.35:   # 搜不到就全书搜一遍
            for j in range(len(lw)):
                r = SequenceMatcher(None, words[:80], lw[j][:120], autojunk=False).ratio()
                if r > best[0]:
                    best = (r, j)
        mapping[key] = {'leaf': best[1], 'ratio': round(best[0], 3)}
        if best[1] is not None:
            guess = best[1] + 1
    PAGEMAP.write_text(json.dumps(mapping, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    weak = {k: v for k, v in mapping.items() if v['ratio'] < 0.5}
    print(f'{len(mapping)} 页已对上，相似度 <0.5 的 {len(weak)} 页：{list(weak)[:20]}', file=sys.stderr)


ORDER = ['dedication', 'reader', '1', '2', '3', '4', '5', 'supplement', '6', 'conclusion']
RE_PB = re.compile(r'<span class="pk-pb" id="p([^"]+)" data-p="[^"]+" data-facs="(\d+)"></span>')


def plain_words(s):
    s = re.sub(r'<span class="pk-margin"[^>]*>.*?</span>', ' ', s)   # 旁注另算
    s = re.sub(r'<[^>]+>', ' ', s)
    return [nw(w) for w in s.split() if nw(w)]


def page_texts():
    """按 pk-pb 切开全书 → [(key, 词序列)]。key = 篇名:印本页号（补编页号从头起）。"""
    out = []
    for slug in ORDER:
        s = (SRC / f'{slug}.md').read_text(encoding='utf-8')
        parts = RE_PB.split(s)
        # parts: [前导, n, facs, 正文, n, facs, 正文…]
        for i in range(1, len(parts), 3):
            out.append((f'{slug}:{parts[i]}', plain_words(parts[i + 2])))
    return out


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'build':
        build()
    else:
        print(__doc__)
