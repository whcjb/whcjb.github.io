#!/usr/bin/env python3
"""亚历山大《马太福音释义》：录入本（Precept Austin）错字候选。

三份扫描本各自与录入本逐词对齐（extract_alexander_matthew.align），录入本某词与三份扫描本同位词不同、
而三份扫描本彼此一致、且读出的是真词（在录入本全书词表里出现过）→ 候选。候选只是线索，
逐条看原图确认后才落 body_fixes.tsv（memory feedback_ocr_repair_three_gates）。

    python3 scripts/alexander_matthew_body_candidates.py   → alexander_raw/matthew/work/body_candidates.tsv
"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_alexander_matthew as X  # noqa: E402


def witness_words(ident):
    out = []
    for pg, pars in X.load_abbyy(ident):
        for p in pars:
            t = ' '.join(w for w, _ in p['words'])
            if p['head'] or p['small'] or X.RUNHEAD.match(t):
                continue
            out += [(w, pg) for w, _ in p['words'] if X.key(w)]
    return out


def main():
    secs = X.load_pa()
    mtoks = [(si, pi, w) for si, s in enumerate(secs) for pi, p in enumerate(s['paras']) for w in p.split(' ')]
    vocab = Counter(X.key(w) for _, _, w in mtoks)
    mi = [i for i, t in enumerate(mtoks) if X.key(t[2])]
    mk = [X.key(mtoks[i][2]) for i in mi]
    per = []
    for ident in X.ITALIC_WITNESSES:
        ws = witness_words(ident)
        ok = [X.key(w) for w, _ in ws]
        start = next((j for j in range(len(ok)) if ok[j:j + 8] == mk[:8]), 0)
        pairs, _ = X.align(mk, ok[start:])
        per.append({mi[a]: ws[start + b] for a, b in pairs.items()})
        print(ident, len(pairs), file=sys.stderr)
    rows = []
    for k, i in enumerate(mi):
        reads = [p.get(i) for p in per]
        if any(r is None for r in reads):
            continue
        keys = {X.key(r[0]) for r in reads}
        if len(keys) != 1:
            continue
        o = keys.pop()
        if o == mk[k] or vocab[o] < 2 or not o.isalpha():
            continue
        si, pi, w = mtoks[i]
        ctx = ' '.join(t[2] for t in mtoks[max(i - 4, 0):i + 5])
        sec = secs[si]
        rows.append(f'{sec.get("ch", sec["kind"])}\t{w}\t{reads[0][0]}\t{reads[0][1]}\t{ctx}')
    out = X.WORK / 'body_candidates.tsv'
    out.write_text('# 章\t录入本\t扫描本(主)\t主扫描本页\t录入本上下文\n' + '\n'.join(rows) + '\n', encoding='utf-8')
    print(f'候选 {len(rows)} → {out}', file=sys.stderr)


if __name__ == '__main__':
    main()
