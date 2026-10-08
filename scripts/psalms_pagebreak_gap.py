#!/usr/bin/env python3
"""页边界上有没有词被吞掉——前面所有闸子都看不见的一类。

抽取是按页拼的，一页的最后几个词或下一页的头几个词丢失，拼出来的句子往往
**仍然通顺**：判词典每个词都认得、标点不成双、斜体也配得上、节号照样连号。
只有把两边接起来去问「中间是不是少了几个词」才查得出来。

判法：每个 `<!-- PAGE N -->` 处取前 14 词与后 8 词，拿 1850 三卷本当尺子——
  · 在**前 14 词里滑动**挑一个最独特的 3–6 词锚（命中 1–3 次），
    不要死用紧挨边界的前 3 词：`of the` 这种常用串必然「锚不唯一」，
    2026-10-08 之前 558 个边界只覆盖得了 216 个（39%）
  · 锚定位之后，把锚后的词按顺序在证人那段里找，**准许 2 个找不到**
    （证人自己也是 OCR，且是另一版排印，逐词全中是不现实的要求）
  · 边界左右各取第一个对上的词，中间隔几个词，那几个词就是候选

**证人自己的噪音占压倒多数**，出清单前先滤掉三类，否则全是假阳性：
  · 证人页眉（`PSALM CV`、读坏成 `PbALM LXXXVI`）
  · 证人把同一个词重出或拆开（我们页末是 `themselves`，证人作 `them selves`；
    `interpretation` 拆成 `in terpretation`；`Selah`→`SeZah`；`&c.`→`etc`）
  · 1850 与 1864 本来就不同的读法（`Oh Jehovah` ↔ `O Jehovah`、`ver.` ↔ `vs.`）
滤法是**编辑距离**：候选词若与边界两侧任一个词近似，就是证人重出，不是我们丢字。

2026-10-08 跑：覆盖 421 / 558 个边界，疑似 42 处，滤掉证人噪音后**真吞词 0**。

用法：python3 scripts/psalms_pagebreak_gap.py [--all]   # --all 连证人噪音一起列
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_alexander_ocr as A

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
OUT = ROOT / 'logs/alexander_psalms_pagebreak.tsv'
PAGE = re.compile(r'<!-- PAGE (\d+) -->')
WORD = re.compile(r"[A-Za-zæœÆŒ][A-Za-zæœÆŒ'-]*")
HEB = re.compile(r'[֐-׿Ͱ-Ͽἀ-῿]')
BEFORE, AFTER = 14, 8       # 边界两侧各取几个词
MISS_OK = 2                 # 对齐时准许几个词在证人里找不到
WIN = 46                    # 在证人里往后看多少词
HEAD = re.compile(r'(?:PSALMS?|P\s*[bB]?\s*A\s*L\s*M)|^[A-Za-z]$|^[A-Z]{1,2}$|^[^A-Za-z]*$',
                  re.I)
# 1850 与 1864 本来就不同的读法，不是我们丢的字
EDITION = re.compile(r'^(oh|vs|v|etc|forever)$', re.I)
# 逐处核过、确认是证人自己噪音的，记下来不再报（「已有结论的桶不再被后续判据覆盖」）
LEDGER = ROOT / 'alexander_raw/psalms/pagebreak_witness_noise.tsv'


def load_ledger():
    d = set()
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding='utf-8').splitlines()[1:]:
            f = line.split('\t')
            if len(f) >= 3:
                d.add((f[0], f[1], f[2]))
    return d


def edit(a, b):
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def norm(s):
    return re.sub(r'[^a-z]', '', s.lower())


def witness_noise(miss, before, after):
    """候选词是不是证人自己的噪音（页眉／重出／拆词／版本异读）。"""
    mw = norm(miss)
    if not mw or HEAD.search(miss.strip()):
        return '证人页眉'
    if EDITION.fullmatch(mw):
        return '两版异读'
    pool = [norm(w) for w in before[-3:] + after[:3] if norm(w)]
    # 与边界两侧任一词近似 → 证人把同一个词重出或拆开了
    for w in pool:
        if edit(mw, w) <= max(1, len(w) // 3):
            return '证人重出同一个词'
    # 拆成两段的（them selves / in terpretation）：拼起来再比
    joined = norm(''.join(miss.split()))
    for w in pool:
        if edit(joined, w) <= max(1, len(w) // 3):
            return '证人把一个词拆成两段'
    return ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true', help='连滤掉的证人噪音一起列')
    a = ap.parse_args()
    ledger = load_ledger()
    words, _ = A.load_witness()
    low = [w.lower() for w in words]
    idx = {}
    for n in (3, 4, 5, 6):
        for i in range(len(low) - n):
            idx.setdefault(tuple(low[i:i + n]), []).append(i)
    print(f'证人词流 {len(words)} 词')

    stat, rows, noise = Counter(), [], []
    for p in sorted(SRC.glob('*.md'), key=lambda x: (x.stem != 'preface', x.stem)):
        plain = re.sub(r'<(?!!--)[^<>]*>', ' ', p.read_text(encoding='utf-8'))
        for m in PAGE.finditer(plain):
            if HEB.search(plain[max(0, m.start() - 40):m.start()]):
                stat['页末是希伯来词'] += 1
                continue
            before = WORD.findall(plain[max(0, m.start() - 500):m.start()])[-BEFORE:]
            after = WORD.findall(plain[m.end():m.end() + 320])[:AFTER]
            if len(before) < 6 or len(after) < AFTER:
                stat['两侧词不够'] += 1
                continue
            anchor = None
            for n in (6, 5, 4, 3):
                for st in range(len(before) - n, -1, -1):
                    hits = idx.get(tuple(w.lower() for w in before[st:st + n]), [])
                    if 1 <= len(hits) <= 3:
                        anchor = (st, n, hits)
                        break
                if anchor:
                    break
            if not anchor:
                stat['锚不唯一或无'] += 1
                continue
            st, n, hits = anchor
            rest = [w.lower() for w in before[st + n:] + after]
            k = len(before) - (st + n)
            best = None
            for h in hits:
                seg = low[h:h + WIN]
                pos, miss_n, where = n, 0, []
                for w in rest:
                    try:
                        q = seg.index(w, pos)
                    except ValueError:
                        miss_n += 1
                        where.append(None)
                        if miss_n > MISS_OK:
                            break
                        continue
                    pos = q + 1
                    where.append(q)
                if miss_n > MISS_OK:
                    continue
                li = next((where[i] for i in range(k - 1, -1, -1)
                           if where[i] is not None), n - 1)
                ri = next((where[i] for i in range(k, len(where))
                           if where[i] is not None), None)
                if ri is None:
                    continue
                if best is None or ri - li - 1 < best[0]:
                    best = (ri - li - 1, h, li, ri)
            if best is None:
                stat['证人对不上'] += 1
                continue
            gap, h, li, ri = best
            if gap <= 0:
                stat['接得上'] += 1
                continue
            miss = ' '.join(words[h + li + 1:h + ri])
            why = witness_noise(miss, before, after)
            row = (p.stem, m.group(1), str(gap), ' '.join(before[-5:]),
                   ' '.join(after[:5]), miss)
            if why:
                stat[why] += 1
                noise.append(row + (why,))
                continue
            if (p.stem, m.group(1), miss) in ledger:
                stat['台账：证人噪音'] += 1
                noise.append(row + ('台账：证人噪音',))
                continue
            if len(miss.split()) > 6:
                stat['差太多（多半锚落错）'] += 1
                continue
            stat['疑似吞词'] += 1
            rows.append(row)
    cover = stat['接得上'] + stat['疑似吞词'] + sum(
        v for k, v in stat.items()
        if k.startswith(('证人页眉', '证人重出', '证人把', '两版', '台账')))
    print('，'.join(f'{k} {v}' for k, v in stat.most_common()))
    print(f'覆盖了 {cover} 个页边界')
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open('w', encoding='utf-8') as fh:
        fh.write('篇\t书页\t隔了几个词\t页末\t页首\t证人里中间那几个词\n')
        for r in rows:
            fh.write('\t'.join(r) + '\n')
    print(f'页边界疑似吞词 {len(rows)} 处 → {OUT}')
    for sec, pg, gap, b, af, miss in rows[:40]:
        print(f'  [{sec:>4} p{pg}] 隔 {gap}：…{b} ⟦{miss}⟧ {af}…')
    if a.all:
        print(f'--- 滤掉的证人噪音 {len(noise)} 处 ---')
        for sec, pg, gap, b, af, miss, why in noise:
            print(f'  [{sec:>4} p{pg}] {why}：…{b} ⟦{miss}⟧ {af}…')
    return 1 if rows else 0


if __name__ == '__main__':
    sys.exit(main())
