#!/usr/bin/env python3
"""按「像英文却不是英文词」的密度给书页排序，作为影像逐页排查的顺序。

`isaiah_page_suspects.py` 按可疑总数排，排在最前的却多半是希伯来活字残渣、
德文引文与希腊文——那些看影像也没用（页面上印的就是外文，OCR 读不出来是
必然的）。真正值得看影像的是**长得像英文、却差一两个字母**的串：
`hnes`(lines)、`Jield`(field) 这类，规则与证人都没救回来，人眼一看就知道。

判据：ASCII 字母、长度 ≥4、与本书某个高频正确词的编辑距离 ≤2。
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_lexicon import build, is_word

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/isaiah'
OUT = ROOT / 'logs/alexander_isaiah_page_english.tsv'

TOKEN = re.compile(r"[A-Za-z][A-Za-z'’]*")
FRONT = re.compile(r'^---.*?^---\n', re.S | re.M)
SEGMENT = re.compile(r'(<!--.*?-->|</?[A-Za-z][^<>]*>)', re.S)
PAGE = re.compile(r'<!-- PAGE (\d+) -->')
SECTION_VOL = {'preface': 'v1', 'introduction': 'v1',
               'later-preface': 'v2', 'later-introduction': 'v2'}


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


def main():
    lex = build()
    pages = defaultdict(list)
    vocab = Counter()
    for path in sorted(SRC.glob('*.md')):
        for w in TOKEN.findall(FRONT.sub('', path.read_text(encoding='utf-8'))):
            if is_word(w, lex):
                vocab[w.lower()] += 1
    common = [w for w, c in vocab.items() if c >= 5 and len(w) >= 4]
    by_len = defaultdict(list)
    for w in common:
        by_len[len(w)].append(w)

    for path in sorted(SRC.glob('*.md')):
        stem = path.stem
        vol = SECTION_VOL.get(stem)
        if vol is None:
            if not stem.isdigit():
                continue
            vol = 'v1' if int(stem) <= 39 else 'v2'
        raw = FRONT.sub('', path.read_text(encoding='utf-8'))
        page = None
        for seg in SEGMENT.split(raw):
            if seg.startswith('<!--'):
                m = PAGE.search(seg)
                if m:
                    page = int(m.group(1))
                continue
            if seg.startswith('<') or page is None:
                continue
            for w in TOKEN.findall(seg):
                low = w.lower()
                if len(low) < 4 or is_word(w, lex) or not low.isascii():
                    continue
                near = [c for L in (len(low) - 2, len(low) - 1, len(low),
                                    len(low) + 1, len(low) + 2)
                        for c in by_len.get(L, ()) if dist_le(low, c, 2)]
                if near:
                    pages[(vol, page, stem)].append(f'{w}→{near[0]}')

    rows = sorted(pages.items(), key=lambda kv: -len(kv[1]))
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('vol\tpage\tchapter\tn\tsuspects\n')
        for (vol, page, ch), lst in rows:
            f.write(f'{vol}\t{page}\t{ch}\t{len(lst)}\t{" ".join(lst)}\n')
    print(f'{len(rows)} 页有「像英文的可疑串」，合计 {sum(len(v) for v in pages.values())}')
    for (vol, page, ch), lst in rows[:20]:
        print(f'   {vol} p{page:>3} ch{ch:<4} {len(lst):>2} 处  {" ".join(lst[:7])}')
    print('→', OUT)


if __name__ == '__main__':
    main()
