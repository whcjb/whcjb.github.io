#!/usr/bin/env python3
"""把「还剩多少要判」算清楚——分母不算准，排期就是瞎猜。

判读跑完之后账上还有一堆非词，但它们不是同一回事：

  已核实原样   证人与我们一致 —— 底本就这么印的，不必再挖
  活字残渣     希伯来/希腊活字读崩的两三字母串 —— 页面上印的就是外文，
               看影像也变不出拉丁字母，除非真去转写
  证人对不上   证人给了读数，但跟我们这串**毫无相似之处**
               （`Carchemish → some`、`Ctesiphon → which`）——
               那是锚落错了地方，不是证人读崩。证人这条路在这些位置
               已经走到头，翻影像也只是重新认一遍我们已经认得的字
  待判         剩下的才是真要人判的

先前把「证人对不上」算进待判，分母虚高。这个区分是诗篇线那边先提的
（他们 435 条 divergent 里 211 条属于此类），本脚本按同一口径算以赛亚书。
"""
import csv
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_lexicon import build, is_word

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / 'alexander/isaiah'
LOG = ROOT / 'logs/alexander_isaiah_adjudicate.tsv'
OUT = ROOT / 'logs/alexander_isaiah_backlog.tsv'

TOKEN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’]*")
FRONT = re.compile(r'^---.*?^---\n', re.S | re.M)
SEGMENT = re.compile(r'(<!--.*?-->|</?[A-Za-z][^<>]*>)', re.S)
VOWEL = re.compile(r'[aeiouyAEIOUY]')
SIM_FLOOR = 0.3          # 低于这个相似度＝锚撞车，不是读崩


def dist_le(a, b, k):
    if abs(len(a) - len(b)) > k:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > k:
            return False
        prev = cur
    return prev[-1] <= k


def actionable(w, by_len):
    """值得翻影像判的，只有「长得像英文却差一两个字母」的串。

    先前按「有没有元音」区分残渣，太粗——`ia` `xal` `TOV` `rov` 全有元音，
    却是希腊文与希伯来文的音译残渣，翻影像也只能确认「页面上印的就是外文」。
    真正可判的判据是：ASCII、长度 ≥5、且与本书某个高频正确词的编辑距离 ≤2。
    """
    low = w.lower()
    if len(low) < 5 or not low.isascii():
        return False
    return any(dist_le(low, c, 2)
               for L in range(len(low) - 2, len(low) + 3)
               for c in by_len.get(L, ()))


def main():
    lex = build()
    verdict = {}
    for r in csv.DictReader(open(LOG, encoding='utf-8'), delimiter='\t'):
        verdict.setdefault((r['chapter'], r['ours']), []).append(r)

    # 本书里出现 ≥5 次的正确词，作为「像不像英文」的比对基准
    vocab = Counter()
    for path in sorted(PUB.glob('*.md')):
        for w in TOKEN.findall(FRONT.sub('', path.read_text(encoding='utf-8'))):
            if is_word(w, lex):
                vocab[w.lower()] += 1
    by_len = {}
    for w, c in vocab.items():
        if c >= 5 and len(w) >= 4:
            by_len.setdefault(len(w), []).append(w)

    counts = Counter()
    rows = []
    for path in sorted(PUB.glob('*.md')):
        raw = FRONT.sub('', path.read_text(encoding='utf-8'))
        for seg in SEGMENT.split(raw):
            if seg.startswith('<'):
                continue
            for w in TOKEN.findall(seg):
                if is_word(w, lex):
                    continue
                recs = verdict.get((path.stem, w), [])
                v = recs[0] if recs else None
                if v and v['verdict'] == 'confirm':
                    kind = '已核实原样'
                elif not actionable(w, by_len):
                    kind = '外文/残渣'
                elif v and v['witness'] and \
                        SequenceMatcher(None, w.lower(),
                                        v['witness'].lower()).ratio() < SIM_FLOOR:
                    kind = '证人对不上'
                else:
                    kind = '待判'
                counts[kind] += 1
                if kind == '待判':
                    rows.append((path.stem, w, v['witness'] if v else '',
                                 v['verdict'] if v else '无证据'))

    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('chapter\ttoken\twitness\tverdict\n')
        for r in rows:
            f.write('\t'.join(r) + '\n')
    total = sum(counts.values())
    for k in ('已核实原样', '外文/残渣', '证人对不上', '待判'):
        print(f'  {k:<10} {counts[k]:>6}')
    print(f'  {"合计":<10} {total:>6}')
    print(f'待判清单 → {OUT}')


if __name__ == '__main__':
    main()
