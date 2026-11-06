#!/usr/bin/env python3
"""福特《路加福音讲义》第 ④ 层：希腊活字按位置换回（skill old-book-ocr §1 第 ④ 层）。

ABBYY 与 tesseract eng 都读不出希腊活字，只吐拉丁乱码（`ats Uofn^tro`、`Ka»^«`）。
foote_greek_scan.py 对全书跑了 tesseract `eng+grc` 逐词 TSV（含置信度）。这里拿其中的英文词当锚，
与我们的正文对齐；两锚之间：

  grc 那截全是希腊词（标点可带）、每词置信度 ≥ 75     —— 换过去的是读得出的希腊文
  我们这截没有任何 ≥3 字母的英文真词                  —— 我们这截确实是读崩的活字，不是英文
  两截 token 数比 0.5–2、各 ≤ 12                       —— 不许整句吞吐
  我们这截的斜体星号只能在两端（成对）                  —— 原书希腊引文常排斜体，标记照留

**只当证人的规矩在这里放宽一档**：希腊文换回之后仍是 tesseract 的字。它是非生成式引擎，
读错只会是形近字母错，不会编词；置信度闸已挡住低质量读数。逐条记 logs/foote_greek.tsv 备查。
落成 foote_raw/luke/greek_fixes.tsv，`--apply` 每讲从后往前、恰好命中一次。链条位置：symbols 之后。

    python3 scripts/foote_greek.py            # 判 → 表 + 日志
    python3 scripts/foote_greek.py --apply
"""
import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_foote as F  # noqa: E402
from alexander_lexicon import build, is_word  # noqa: E402
from repair_alexander_ocr import foote_kjv_words  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'foote_raw' / 'luke'
SRC = RAW / 'en_chapters'
GRC = RAW / 'tess_grc'
RULES = RAW / 'greek_fixes.tsv'
LOG = ROOT / 'logs' / 'foote_greek.tsv'
GREEK = re.compile(r'[Ͱ-Ͽἀ-῿]')
LATIN = re.compile(r'^[A-Za-z]+$')
MINCONF = 75
BLOCK = re.compile(r'<!-- (?:PAGE |NOTE p\.)(\S*) -->\n?(.*?)(?=\n\n|\Z)', re.S)


def inv_pages(vol):
    d = json.load(open(RAW / 'src' / f'{F.VOLS[vol]}_page_numbers.json'))
    return {str(x['pageNumber']): x['leafNum'] for x in d['pages'] if x.get('pageNumber')}


def grc_words(vol, leaf, n=3):
    out = []
    for l in range(leaf, leaf + n):
        p = GRC / f'v{vol}' / f'{l:04d}.tsv'
        if not p.exists():
            continue
        for ln in p.read_text(encoding='utf-8').splitlines()[1:]:
            c = ln.split('\t')
            if len(c) < 12 or not c[11].strip():
                continue
            try:
                conf = float(c[10])
            except ValueError:
                continue
            out.append((c[11], conf))
    return out


def key(w):
    k = re.sub(r'[^A-Za-z]', '', w).lower()
    return k if len(k) >= 2 else None


def judge():
    lex = build() | foote_kjv_words()
    inv = {v: inv_pages(v) for v in (1, 2, 3)}
    rules, log = [], []
    stat = dict(swap=0, lowconf=0, english=0, ratio=0, stars=0)
    for n in range(1, 138):
        vol = next(v for v in (1, 2, 3) if F.FIRST_LECT[v] <= n <= F.LAST_LECT[v])
        text = (SRC / f'{n:03d}.md').read_text(encoding='utf-8')
        for m in BLOCK.finditer(text):
            page, para = m.group(1), m.group(2)
            leaf = inv[vol].get(page)
            if leaf is None:
                continue
            gw = grc_words(vol, leaf)
            if not any(GREEK.search(w) for w, _ in gw):
                continue
            ot = list(re.finditer(r'\S+', para))
            ok = [key(x.group(0)) for x in ot]
            gk = [key(w) if not GREEK.search(w) else None for w, _ in gw]
            # 只拿英文 token 对齐；None 用各不相同的占位，不会互相匹配
            a_seq = [k or f'\x00o{i}' for i, k in enumerate(ok)]
            b_seq = [k or f'\x00g{i}' for i, k in enumerate(gk)]
            blocks = [b for b in SequenceMatcher(None, a_seq, b_seq, autojunk=False).get_matching_blocks() if b.size >= 2]
            for b1, b2 in zip(blocks, blocks[1:]):
                a0, a1, t0, t1 = b1.a + b1.size, b2.a, b1.b + b1.size, b2.b
                if a1 <= a0 or t1 <= t0 or a1 - a0 > 12 or t1 - t0 > 12:
                    continue
                if abs((b2.b - b2.a) - (b1.b - b1.a)) > 4:
                    continue
                gseg = gw[t0:t1]
                if not any(GREEK.search(w) for w, _ in gseg):
                    continue
                if any(LATIN.match(re.sub(r'[^\w]', '', w)) for w, _ in gseg if re.sub(r'[^\w]', '', w)):
                    continue          # grc 那截里夹着英文词：不是纯希腊引文
                old = para[ot[a0].start():ot[a1 - 1].end()]
                if min(c for _, c in gseg) < MINCONF:
                    stat['lowconf'] += 1
                    log.append((f'{n:03d}', old, ' '.join(w for w, _ in gseg), 'lowconf'))
                    continue
                # 我们这截须**全是**读崩的活字：任一英文真词（含 a / O / As / of 这种一两字母的）都不换——
                # grc 会把英文短词读成希腊字母（a→ἃ、As→ΑΒ、of→οὗ），首轮 130 条几乎全是这类，一条没落
                letters = [re.sub(r'[^A-Za-z]', '', x.group(0)) for x in ot[a0:a1]]
                if any(l and is_word(l, lex) for l in letters) or not any(len(l) >= 3 for l in letters) \
                        or len(GREEK.findall(''.join(w for w, _ in gseg))) < 4:
                    stat['english'] += 1
                    log.append((f'{n:03d}', old, ' '.join(w for w, _ in gseg), 'english'))
                    continue
                if not (0.5 <= (t1 - t0) / (a1 - a0) <= 2):
                    stat['ratio'] += 1
                    continue
                stars = [s.start() for s in re.finditer(r'(?<!\\)\*', old)]
                lead = '*' if old.startswith('*') and not old.startswith('\\*') else ''
                tail = '*' if old.endswith('*') and not old.endswith('\\*') and len(old) > 1 else ''
                if len(stars) != len(lead) + len(tail):
                    stat['stars'] += 1
                    continue
                greek = ' '.join(w for w, _ in gseg).replace('“', '"').replace('”', '"')
                new = lead + greek + tail
                anchor = ' '.join(x.group(0) for x in ot[max(0, a0 - 2):a0])
                rules.append((f'{n:03d}', anchor, old, new))
                log.append((f'{n:03d}', old, new, 'swap'))
                stat['swap'] += 1
    with open(RULES, 'w', encoding='utf-8') as f:
        f.write('# lecture\tanchor(左两 token)\told\tnew(tesseract grc) —— foote_greek.py 生成；每讲从后往前落\n')
        for r in rules:
            f.write('\t'.join(r) + '\n')
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('lecture\tours\tgrc\tkind\n')
        for r in log:
            f.write('\t'.join(x.replace('\t', ' ').replace('\n', ' ') for x in r) + '\n')
    print('希腊活字：', stat, file=sys.stderr)


def apply():
    by = {}
    for ln in RULES.read_text(encoding='utf-8').splitlines():
        if ln.strip() and not ln.startswith('#'):
            lec, anchor, old, new = ln.split('\t')
            by.setdefault(lec, []).append((anchor, old, new))
    done = already = 0
    bad = []
    for lec, rs in by.items():
        path = SRC / f'{lec}.md'
        text = path.read_text(encoding='utf-8')
        for anchor, old, new in reversed(rs):
            c = text.count(anchor + ' ' + old) if anchor else text.count(old)
            if c == 1:
                text = text.replace(anchor + ' ' + old if anchor else old, (anchor + ' ' if anchor else '') + new)
                done += 1
            elif c == 0 and ((anchor + ' ' + new) if anchor else new) in text:
                already += 1
            else:
                bad.append((lec, anchor, old[:25], c))
        path.write_text(text, encoding='utf-8')
    print(f'希腊活字落盘 {done}；已落过 {already}；定位失败 {len(bad)} {bad[:4]}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    apply() if a.apply else judge()


if __name__ == '__main__':
    main()
