#!/usr/bin/env python3
"""卡里尔缺部 OCR 第 ① 层纠错：字形混淆 + 判词典（TCP 卡里尔 8 部 + 钦定本全本，带词频）。

    /usr/bin/python3 scripts/caryl_ocr_fix.py 4            # 试跑：统计、列改动样例
    /usr/bin/python3 scripts/caryl_ocr_fix.py 4 --apply    # en/ → fixed/，改动记 fixes.tsv

只处理**非词**（词表里没有的 token），真词误读（mike/make）留给第 ② 层（对照本按位置判读）。
候选由 kraken 的已知混淆对生成（第 3、4 部实测：斜体 h→b、a↔i、w→m/u、c↔e、J→T/I/F/D、长 s 残留 f…），最多改两处；
守卫（old-book-ocr §0「宁可不判」）：
  - 候选须在词表出现 ≥ 3 次，且频次 ≥ 次优候选的 5 倍，否则不改（oun 可作 our 也可作 own，3 倍闸放过了）；
  - 小写候选只认小写出现过的（Tob 是专名、iniquis 是拉丁，不能给 fob、iniquit 当候选）；
  - 一两个字母的 token 不碰（词表对它天生不可靠，§3.2 ④）；
  - 旁注（.cy-margin，多为拉丁文）、HTML 标签、经文框出处行不碰；
  - 粘连词（tothe、inthe）拆成两个词，两半各须 ≥ 200 次（只拆常见虚词，forgetfullnesse 这类当时拼法的真词不拆）；
  - 少改优先：有只改一处的候选就不看改两处的（thec → thee，不是 that）。
幂等：对 fixed/ 再跑一遍应零改动（§4.1b）。
"""
import argparse
import collections
import functools
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'caryl_raw' / 'job_ocr'
TCP_MD = ROOT / 'caryl_raw' / 'job' / 'en_chapters'
KJV_DIR = ROOT / 'foote_raw' / 'luke' / 'src' / 'kjv'
# kraken 字形混淆（误读 → 原字）
CONF = [('b', 'h'), ('h', 'b'), ('i', 'a'), ('a', 'i'), ('m', 'w'), ('u', 'w'), ('n', 'u'), ('u', 'n'), ('c', 'e'),
        ('e', 'c'), ('f', 's'), ('rn', 'm'), ('m', 'rn'), ('cl', 'd'), ('li', 'h'), ('ii', 'u'), ('o', 'e'), ('e', 'o'),
        ('t', 'r'), ('r', 't'), ('l', 'i'), ('i', 'l'), ('v', 'u'), ('u', 'v'), ('k', 'h'), ('c', 't'), ('t', 'c'),
        ('ɇ', 'e'), ('é', 'e'), ('è', 'e'), ('à', 'a'), ('n', 'h'), ('h', 'n'), ('ſ', 's'), ('s', 'f'), ('y', 'v'),
        ('in', 'm'), ('ni', 'm'), ('iu', 'm'), ('w', 'm'), ('d', 'cl'), ('r', 'n'), ('n', 'r'), ('a', 'e'), ('e', 'a'),
        ('b', 'k'), ('h', 'k'), ('t', 'f'), ('f', 't'), ('l', 't'), ('c', 'o'),
        ('I', 'l'), ('a', 'u'), ('u', 'h'), ('s', 'c'), ('x', 'u'), ('z', 'n'), ('o', 'a'), ('R', 'W'), ("'", 'h')]
HEAD = [('T', 'J'), ('I', 'J'), ('F', 'J'), ('D', 'J'), ('l', 'J'), ('T', 'I'), ('H', 'W'), ('R', 'W'), ('M', 'W'),
        ('V', 'U'), ('A', 'M'), ('T', 'Y'), ('F', 'H')]


def lexicon():
    """→ (按小写计频, 按原样计频)。小写候选只认小写出现过的——Tob（专名）、iniquis（拉丁）不能给 fob、iniquit 当候选。"""
    c, e = collections.Counter(), collections.Counter()
    for f in glob.glob(str(TCP_MD / '*.md')):
        t = re.sub(r'<[^>]+>|\{:[^}]*\}', ' ', Path(f).read_text(encoding='utf-8')).replace('*', '')
        for w in re.findall(r"[A-Za-z]+", t):
            c[w.lower()] += 1
            e[w] += 1
    for f in KJV_DIR.glob('*.usfm'):
        t = re.sub(r'\|[^\\]*', '', f.read_text(encoding='utf-8'))
        t = re.sub(r'\\\+?\w+\*?', ' ', t)
        for w in re.findall(r"[A-Za-z]+", t):
            c[w.lower()] += 1
            e[w] += 1
    return c, e


LEX, EXACT = lexicon()
NOSPLIT = {'th', 'st', 'nd', 'rd', 'ye', 'ly', 'es', 'ed'}


def freq(v):
    """小写词只计小写出现；首字母大写的词按小写合计（句首）。"""
    return EXACT.get(v, 0) if v.islower() else LEX.get(v.lower(), 0)


def step(vs):
    out = set()
    for v in vs:
        for a, b in CONF:
            i = v.find(a)
            while i >= 0:
                out.add(v[:i] + b + v[i + len(a):])
                i = v.find(a, i + 1)
        for a, b in HEAD:
            if v.startswith(a):
                out.add(b + v[len(a):])
    return out


def pick(cands):
    """{候选: 频次} → 最优候选或 None（≥ 3 次，且 ≥ 次优的 3 倍；仅大小写不同的不算竞争）。"""
    if not cands:
        return None
    b, fb = max(cands.items(), key=lambda kv: kv[1])
    f2 = max([f for v, f in cands.items() if v.lower() != b.lower()], default=0)
    return b if fb >= 3 and fb >= 5 * f2 else None


@functools.lru_cache(maxsize=None)
def best_fix(w):
    """→ 改成的词，或 None。w 保留原大小写。
    次序：① 只改一处的字形候选；② 拆成两个常见词（tothe、tobe、inthe，两半各 ≥ 200 次）；③ 改两处的。
    拆分排在单处替换之后：heheld 先试 h→b 得 beheld，不能先拆成 he held。
    少改优先——thec 改一处是 thee，改两处才是 that，不能因为 that 频次高就选它。"""
    lw = w.lower()
    if len(w) <= 2 or LEX.get(lw, 0) > 0:
        return None
    seen, frontier = {w}, {w}
    for depth in range(2):
        frontier = step(frontier) - seen
        seen |= frontier
        cands = {v: freq(v) for v in frontier if freq(v)}
        if cands:
            return pick(cands)
        if depth == 0:
            for k in range(2, len(lw) - 1):
                a, c = lw[:k], lw[k:]
                if LEX.get(a, 0) >= 200 and LEX.get(c, 0) >= 200 and a not in NOSPLIT and c not in NOSPLIT:
                    return w[:k] + ' ' + w[k:]
    return None


RE_PROTECT = re.compile(r'<span class="cy-margin">.*?</span>|<[^>]+>|\{:[^}]*\}|^.*\n\{: \.cy-vlabel\}', re.S | re.M)


def fix_text(md, log, slug):
    parts, last = [], 0
    for m in RE_PROTECT.finditer(md):
        parts.append(('t', md[last:m.start()]))
        parts.append(('p', m.group(0)))
        last = m.end()
    parts.append(('t', md[last:]))
    out = []
    for kind, s in parts:
        if kind == 'p':
            out.append(s)
            continue

        def rep(m):
            w = m.group(0)
            f = best_fix(w)
            if f and f != w:
                log.append((slug, w, f))
                return f
            return w
        out.append(re.sub(r"[A-Za-zſɇéèà]+", rep, s))
    return ''.join(out)


def nonword_rate(md):
    t = RE_PROTECT.sub(' ', md)
    ws = [w.lower() for w in re.findall(r"[A-Za-z]{3,}", t)]
    return len(ws), sum(1 for w in ws if not LEX.get(w))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('part', type=int)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--src', default='en')
    a = ap.parse_args()
    d = BASE / f'p{a.part}'
    src = d / a.src
    log, before, after = [], [0, 0], [0, 0]
    outs = {}
    for f in sorted(src.glob('*.md')):
        md = f.read_text(encoding='utf-8')
        n, b = nonword_rate(md)
        before[0] += n
        before[1] += b
        new = fix_text(md, log, f.stem)
        n2, b2 = nonword_rate(new)
        after[0] += n2
        after[1] += b2
        outs[f.name] = new
    c = collections.Counter((w, f) for _, w, f in log)
    print(f'第 {a.part} 部：非词率 {before[1] / before[0]:.2%} → {after[1] / after[0]:.2%}（词 {before[0]:,}）；改 {len(log):,} 处，'
          f'{len(c):,} 种', file=sys.stderr)
    for (w, f), k in c.most_common(40):
        print(f'  {k:4d}  {w} → {f}', file=sys.stderr)
    if a.apply:
        out = d / 'fixed'
        out.mkdir(exist_ok=True)
        for name, md in outs.items():
            (out / name).write_text(md, encoding='utf-8')
        (d / 'fixes.tsv').write_text(''.join(f'{s}\t{w}\t{f}\n' for s, w, f in log), encoding='utf-8')
        print(f'写入 → {out}', file=sys.stderr)


if __name__ == '__main__':
    main()
