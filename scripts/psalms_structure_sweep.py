#!/usr/bin/env python3
"""四条一次跑完的结构性体检——都很便宜，每轮改动之后跑一遍。

  书页连续    `<!-- PAGE N -->` 在 14–572 之间不许缺号。缺号＝那一页的页码
              没被认出来（诗 2 的书页 24 就是这么丢的：正文在、只缺标记），
              裁图定位会因此落到隔壁页
  近距重出    10 词之内重复出现的 5-gram。**绝大多数是希伯来诗的平行句**
              （`The voice of Jehovah in power, The voice of Jehovah in majesty`），
              所以这条是「看一眼」的，不是「照单改」的
  并词        长非词能拆成两个真词（`Andbrought` → And + brought）
  非拉丁混拉丁 希伯来/希腊词里混进拉丁字母或噪点（`εὐαγγελί(ζο[μαι`）

用法：python3 scripts/psalms_structure_sweep.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import alexander_lexicon as L

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
TAG = re.compile(r'<[^<>]+>')
WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")
# 希伯来/希腊词后面紧跟标点再接英文是**正常行文**（`צום.—The last clause`），
# 所以扫到标点就停，只看词里面有没有混进拉丁字母或噪点。
FOREIGN = re.compile(r'[֐-׿Ͱ-Ͽἀ-῿][^\s()\[\].,;:—–\-]{0,24}')
NOISE = re.compile(r'[A-Za-z0-9^\]\[|}{<>~`\\]')


def main():
    files = sorted(SRC.glob('*.md'), key=lambda p: (p.stem != 'preface', p.stem))
    bad = 0

    pages = []
    for f in files:
        pages += [int(m.group(1)) for m in
                  re.finditer(r'<!-- PAGE (\d+) -->', f.read_text(encoding='utf-8'))]
    s = set(pages)
    miss = [p for p in range(min(s), max(s) + 1) if p not in s]
    print(f'① 书页 {min(s)}–{max(s)}：' + (f'缺 {miss}' if miss else '连续 ✓'))
    bad += bool(miss)

    rep = []
    for f in files:
        w = WORD.findall(TAG.sub(' ', f.read_text(encoding='utf-8')))
        seen, hit = {}, []
        for i in range(len(w) - 5):
            g = tuple(x.lower() for x in w[i:i + 5])
            if g in seen and i - seen[g] <= 10:
                hit.append((seen[g], i))
            seen[g] = i
        merged = []
        for a, b in sorted(set(hit)):
            if merged and a <= merged[-1][1] + 2:
                merged[-1] = (merged[-1][0], max(merged[-1][1], b))
                continue
            merged.append((a, b))
        for a, b in merged:
            rep.append((f.stem, ' '.join(w[max(0, a - 4):b + 9])))
    print(f'② 近距重出 5-gram：{len(rep)} 处（多为平行句，逐条看，别照单改）')

    lex = L.build()
    join = []
    for f in files:
        t = TAG.sub(' ', f.read_text(encoding='utf-8'))
        for m in re.finditer(r"\b[A-Za-z][A-Za-z']{11,}\b", t):
            w = m.group(0)
            if L.is_word(w, lex):
                continue
            for k in range(3, len(w) - 2):
                if L.is_word(w[:k], lex) and L.is_word(w[k:], lex):
                    join.append((f.stem, w, w[:k], w[k:]))
                    break
    print(f'③ 并词：{len(join)} 处')
    for sec, w, a, b in join:
        print(f'    [{sec}] {w} → {a} + {b}')
    bad += bool(join)

    heads = []
    # 必须有「阿拉伯数字 + 冒号」：页眉写 `Psalm 113:1-3`，正文引用写
    # `Ps. cxiii. 1`，而 `Psalms (xcvi. 7, 8)` 这种正常行文没有冒号。
    HEAD = re.compile(r'\*?\s*Psalms?\s*[\]\[|)(}{]?\s*\d{1,3}\s*:\s*[\d\-–,\s]{1,12}\*?')
    for f in files:
        t2 = TAG.sub(' ', f.read_text(encoding='utf-8'))
        for m in HEAD.finditer(t2):
            heads.append((f.stem, m.group(0).strip()))
    # 页眉的排法是 `Psalm 113:1-3`，正文里的引用一律写作 `Ps. cxiii. 1`，
    # 所以「Psalm + 阿拉伯数字 + 冒号」出现在正文里就是页眉串进来了。
    # 判据要认得 OCR 把它读坏的样子（`*Psalm] 13:1-3*`），只认冒号那一种会漏。
    print(f'⑤ 页眉串进正文：{len(heads)} 处')
    for sec, s in heads:
        print(f'    [{sec}] {s!r}')
    bad += bool(heads)

    mix = []
    for f in files:
        t = f.read_text(encoding='utf-8')
        for m in FOREIGN.finditer(t):
            if NOISE.search(m.group(0)):
                mix.append((f.stem, m.group(0)))
    print(f'④ 希伯来/希腊里混拉丁：{len(mix)} 处')
    for sec, s2 in mix:
        print(f'    [{sec}] {s2!r}')
    bad += bool(mix)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
