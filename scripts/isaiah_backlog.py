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
  待判         剩下的才是真要人判的，再按证人还有没有用分成三档：
               证人还有话说 / 证人对不上（锚撞车）/ 压根没证据
               后两档只能翻影像

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
HEB = [ROOT / 'alexander_raw/isaiah/hebrew_ocr.tsv',
       ROOT / 'alexander_raw/isaiah/hebrew_ocr_junk.tsv']
RESCAN = ROOT / 'alexander_raw/isaiah/english_rescan.tsv'
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


SHAPE_BAD = re.compile(r'[^aeiouy\'-]{4}', re.I)


def actionable(w, by_len, good_bigrams):
    """值得翻影像判的，只有「长得像英文却差一两个字母」的串。

    三代判据，前两代都太松：
      一代「有没有元音」——`ia` `xal` `TOV` `rov` 全有元音，却都是希腊文音译。
      二代「与某个高频正确词编辑距离 ≤2」——`nasna` 离 `nation` 也只差两步，
        希伯来音译一大半都能挂上某个英文词。
    三代加**字形**判据：词中不出现大写、不出现四连辅音、二元组合理性 ≥0.9
    （二元组表用本书自己的正确小写词统计，出现 ≥50 次的才算常见）。
    挡掉的是 `JtEsn` `mninx` `stB'n` `rviss` 这一类——它们在页面上本来就是
    希伯来活字，翻影像也变不出拉丁字母，列进待判只会虚增分母。
    """
    low = w.lower()
    if len(low) < 5 or not low.isascii():
        return False
    if re.search(r'[A-Z]', w[1:]) or "'" in w[1:-1]:
        return False
    if not re.search(r'[aeiouy]', low) or SHAPE_BAD.search(low):
        return False
    l = '^' + low + '$'
    bs = [l[i:i + 2] for i in range(len(l) - 1)]
    if sum(b in good_bigrams for b in bs) / len(bs) < 0.9:
        return False
    return any(dist_le(low, c, 2)
               for L in range(len(low) - 2, len(low) + 3)
               for c in by_len.get(L, ()))


def rescanned():
    """重扫过的串 → 它是外文还是英文。**这是证据，不是猜测。**

    前三代 `actionable` 都是靠字形猜「这串像不像英文」，猜错了就把希伯来
    活字算进待判，分母虚高。现在这些串已经被 tesseract 拿同一份 PDF 原图
    重认过一遍了：

      · heb/grc 模型读出了成串希伯来/希腊字母 → 页面上印的本来就是外文
      · eng 模型重认，读出来还是个非词        → 不是拉丁活字读错，同上

    两条都够硬，可以把它们从待判里摘出去，标明「已重扫·外文」。
    """
    lex = build()
    out = {}
    for path in HEB:
        if not path.exists():
            continue
        with open(path, encoding='utf-8') as f:
            for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
                for w in (r.get('garbage') or '').split():
                    out[w.strip(".,;:!?()[]'\"")] = 'heb'
    if RESCAN.exists():
        with open(RESCAN, encoding='utf-8') as f:
            for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
                g = (r.get('garbage') or '').strip(".,;:!?()[]'\"")
                reading = (r.get('reading') or '').strip(".,;:!?()[]'\"")
                if g and reading and not is_word(reading, lex):
                    out.setdefault(g, 'eng')
    return out


def main():
    lex = build()
    rescan = rescanned()
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
    # 二元组表只用本书的正确**小写**词统计，专名与外文不参与，
    # 否则希伯来音译里的怪组合会被当成常见的
    bigrams = Counter()
    for path in sorted(PUB.glob('*.md')):
        for w in TOKEN.findall(FRONT.sub('', path.read_text(encoding='utf-8'))):
            if is_word(w, lex) and w.isalpha() and w.islower():
                l = '^' + w + '$'
                for i in range(len(l) - 1):
                    bigrams[l[i:i + 2]] += 1
    good_bigrams = {b for b, c in bigrams.items() if c >= 50}

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
                elif not actionable(w, by_len, good_bigrams):
                    kind = '外文/残渣'
                elif w in rescan:
                    kind = '已重扫·外文'
                elif not v or not v['witness']:
                    kind = '待判·无证据'
                elif SequenceMatcher(None, w.lower(),
                                     v['witness'].lower()).ratio() < SIM_FLOOR:
                    kind = '待判·证人对不上'
                else:
                    kind = '待判·证人还有话说'
                counts[kind] += 1
                if kind.startswith('待判'):
                    rows.append((path.stem, w, v['witness'] if v else '',
                                 v['verdict'] if v else '无证据', kind))

    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('chapter\ttoken\twitness\tverdict\tbucket\n')
        for r in rows:
            f.write('\t'.join(r) + '\n')
    total = sum(counts.values())
    order = ('已核实原样', '外文/残渣', '已重扫·外文', '待判·证人还有话说',
             '待判·证人对不上', '待判·无证据')
    for k in order:
        print(f'  {k:<18} {counts[k]:>6}')
    print(f'  {"合计":<18} {total:>6}')
    pend = sum(counts[k] for k in order if k.startswith('待判'))
    print(f'  → 真正待判 {pend}（其中只能翻影像的 '
          f'{counts["待判·证人对不上"] + counts["待判·无证据"]}）')
    print(f'待判清单 → {OUT}')


if __name__ == '__main__':
    main()
