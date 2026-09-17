#!/usr/bin/env python3
"""**真词错**——两边都是真词，判词典永远失效的那一类。

`he` 与 `be`、`first-horn` 与 `first-born`、`hands` 与 `bands`、`Hock` 与 `Rock`：
1864 这副字模里 h/b、r/R、l/U、v/T 常互串，串完仍是英文词，于是
  · `repair` 的三道闸不动它（`is_word` 直接放行）
  · `adjudicate_alexander_ocr` 也不查它（它只判「不是真词」的 token）
整页比对里这一类占了报出来的一多半。

办法：把第二证人（1850 三卷本）**对每一个词**都查一遍，不只查非词。
证人在同一位置印的若是另一个词，且两词只差一两个字母，就列为待判。

三道闸，任何一道不过就不报：
  锚      目标词前后各取 3-gram，命中处读数必须一致（沿用 adjudicate 的 look_up）
  形近    与我们这个词的编辑距离 ≤ 2，且长度相近——证人锚偶尔会落错位置，
          读出来的是隔壁的词，那种差得远，靠这条挡掉
  字形    两词的差异得落在这副字模确实会串的字母对上（h/b、r/n、l/i…），
          不然就是两版用词不同，不是我们读错

出的是**待判清单**，不直接落盘——最后仍要影像定案。

用法：
    python3 scripts/psalms_realword_witness.py            # 出清单
    python3 scripts/psalms_realword_witness.py --apply    # 落盘（只落过三道闸的）
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_alexander_ocr as A
import alexander_lexicon as L

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
RAW = ROOT / 'alexander_raw/psalms/en_chapters'
OUT = ROOT / 'logs/alexander_psalms_realword.tsv'

# 这副字模真正会串的字母对（从前面几轮已核定的错里归纳出来的）
SWAPS = {frozenset('hb'), frozenset('rn'), frozenset('li'), frozenset('lI'),
         frozenset('vy'), frozenset('cе'), frozenset('ce'), frozenset('oa'),
         frozenset('nu'), frozenset('fs'), frozenset('tf'), frozenset('gy'),
         frozenset('mrn'), frozenset('wv'), frozenset('ec'), frozenset('ao'),
         frozenset('il'), frozenset('ts'), frozenset('pq'), frozenset('dcl')}
CASE_ONLY = False       # 只差大小写的不报：两版的大小写体例本来就不同
                        #（`Scriptures`/`scriptures`、`see`/`See`），噪音太大


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


def glyph_plausible(ours, wit):
    """两词的差异是不是这副字模会犯的。"""
    if ours.lower() == wit.lower():
        return CASE_ONLY
    if len(ours) != len(wit):
        return edit(ours, wit) == 1        # 多一个/少一个字母也算（断字、并字）
    diff = [(a, b) for a, b in zip(ours, wit) if a != b]
    if len(diff) > 2:
        return False
    return all(frozenset((a.lower(), b.lower())) in SWAPS or a.lower() == b.lower()
               for a, b in diff)


def main(apply=False):
    lex = L.build()
    words, wtext = A.load_witness()
    idx, wlow = A.build_index(words)
    print(f'证人词流 {len(words)} 词')
    # 全书二元组：拿**我们自己的正文**统计，不用证人（证人有它自己的错）
    big = Counter()
    corpus = []
    for f in sorted(SRC.glob('*.md')):
        corpus += [t[0].lower() for t in A.chapter_tokens(f.read_text(encoding='utf-8'))]
    for k in range(len(corpus) - 1):
        big[(corpus[k], corpus[k + 1])] += 1
    # 证人语料也计进来：它有自己的错，但错法与我们不同，二元组这种宽统计
    # 不会被少数几处带偏，反倒把「这个搭配在英语里站不站得住」问得更准
    wl = [w.lower() for w in words]
    for k in range(len(wl) - 1):
        big[(wl[k], wl[k + 1])] += 1
    print(f'全书二元组 {len(big)}')
    stat, rows = Counter(), []
    for f in sorted(SRC.glob('*.md')):
        text = f.read_text(encoding='utf-8')
        toks = A.chapter_tokens(text)
        stream = [t[0] for t in toks]
        for i, (w, a, b) in enumerate(toks):
            if len(w) < 2 or not L.is_word(w, lex):
                continue                        # 非词那一路另有脚本
            reading = A.look_up(stream, i, idx, wlow, words)
            if not reading or reading == w:
                stat['证人一致或无读数'] += 1
                continue
            if not L.is_word(reading, lex):
                stat['证人读数不是词'] += 1
                continue
            d = edit(w, reading)
            if d == 0 or d > 2 or abs(len(w) - len(reading)) > 1:
                stat['差得太远'] += 1
                continue
            if not glyph_plausible(w, reading):
                stat['不是这副字模会串的'] += 1
                continue
            # 第三道闸：**语料支持**。证人自己也是 OCR，它读崩的地方一样多
            # （`his`→`bis`、`shall`→`hall`、`are`→`arc`），光靠形近分不开
            # 「我们错了」和「证人错了」。判据是这本书自己的二元组：
            # 换上证人那个词之后，与左右邻居的搭配必须在书里站得住，
            # 而我们现在这个搭配几乎不出现。`my hone cleaves` vs `my bone cleaves`
            # 一眼就分开了；`with his food` vs `with bis food` 也是。
            prev = stream[i - 1].lower() if i else ''
            nxt = stream[i + 1].lower() if i + 1 < len(stream) else ''
            ours_sup = big[(prev, w.lower())] + big[(w.lower(), nxt)]
            wit_sup = big[(prev, reading.lower())] + big[(reading.lower(), nxt)]
            # ours_sup 里含它**自己**那一处的两个二元组（语料就是我们的正文），门槛要减掉
            if not (wit_sup >= 3 and ours_sup <= 2):
                stat['语料不支持'] += 1
                continue
            stat['待判'] += 1
            ctx = re.sub(r'\s+', ' ', re.sub(A.TAG, '', text[max(0, a - 45):b + 40]))
            rows.append((f.stem, w, reading, ctx))
    print('，'.join(f'{k} {v}' for k, v in stat.most_common()))
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open('w', encoding='utf-8') as fh:
        fh.write('篇\t我们\t证人\t上下文\n')
        for r in rows:
            fh.write('\t'.join(r) + '\n')
    print(f'待判 {len(rows)} 处 → {OUT}')
    if not apply:
        for sec, w, r, ctx in rows[:40]:
            print(f'  [{sec}] {w!r} → {r!r}   …{ctx[:70]}…')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    main(ap.parse_args().apply)
