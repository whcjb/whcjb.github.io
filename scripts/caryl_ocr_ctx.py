#!/usr/bin/env python3
"""卡里尔缺部 OCR 第 ③ 层：短词上下文纠错（真词误读）。

    /usr/bin/python3 scripts/caryl_ocr_ctx.py 9            # 试跑：改动计数与样例
    /usr/bin/python3 scripts/caryl_ocr_ctx.py 9 --apply    # fixed/ 就地改，改动记 ctx.tsv

抽读第 9 部印本第 569 页（2026-11-24）：一页 16 处错里约 10 处是斜体虚词读成了**别的真词**——If→Is（三次）、
or→er、of→ef、the→ibe/toe、saw→sam、was→mas。第 ①② 层只查非词，碰不到它们。
语料自证：TCP 卡里尔 8 部 250 万词（同一作者、同一批印工）统计二元搭配。只动 ≤ 4 字母的词：
候选 = 第 ① 层混淆对改一处（caryl_ocr_fix.step）得到的、本书出现 ≥ 100 次的词；
守卫：候选与前词、与后词两组搭配在语料里**都出现过**，且「前词·候选」「候选·后词」两项概率之积 ≥ 原词的 50 倍；
原词本身是本书常见词（≥ 200 次）的一概不碰（nor→not、may→way、fell→fall 在 2000 倍门槛下仍会改错）；
单字母不碰；前后词须是本书 ≥ 20 次的完整词（ly、hill 这类残片做邻词时统计不可靠）。
专名、旁注、标签、经文框出处行不碰（同 caryl_ocr_fix.RE_PROTECT）。
"""
import argparse
import collections
import glob
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import caryl_ocr_fix as fx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'caryl_raw' / 'job_ocr'
RE_W = re.compile(r"[A-Za-z]+")


def corpus():
    uni, bi = collections.Counter(), collections.Counter()
    for f in glob.glob(str(fx.TCP_MD / '*.md')):
        t = re.sub(r'<span class="cy-margin"[^>]*>.*?</span>|<[^>]+>|\{:[^}]*\}', ' ', Path(f).read_text(encoding='utf-8'))
        t = t.replace('*', '')
        for sent in re.split(r'[.;:?!()\[\]]', t):
            ws = [w.lower() for w in RE_W.findall(sent)]
            uni.update(ws)
            bi.update(zip(ws, ws[1:]))
    return uni, bi


UNI, BI = corpus()
N = sum(UNI.values())


def p_bi(a, b):
    return (BI.get((a, b), 0) + 0.01) / (UNI.get(a, 0) + 1)


def cands(t):
    out = set()
    for v in fx.step({t}) | fx.step({t.lower()}):
        lv = v.lower()
        if lv != t.lower() and UNI.get(lv, 0) >= 100:
            out.add(lv)
    return out


def fix_md(md, log, slug):
    prot = [(m.start(), m.end()) for m in fx.RE_PROTECT.finditer(md)]
    toks, k = [], 0
    for m in RE_W.finditer(md):
        while k < len(prot) and prot[k][1] <= m.start():
            k += 1
        if k < len(prot) and prot[k][0] <= m.start() < prot[k][1]:
            continue
        toks.append(m)
    edits = {}
    for i in range(1, len(toks) - 1):
        m = toks[i]
        t = m.group(0)
        if len(t) > 4 or len(t) < 2:
            continue
        pv, nx = toks[i - 1], toks[i + 1]
        # 前后词须与本词在同一句（中间只隔空白、逗号）
        if re.search(r'[.;:?!()\[\]<>]', md[pv.end():m.start()]) or re.search(r'[.;:?!()\[\]<>]', md[m.end():nx.start()]):
            continue
        a, b, lt = pv.group(0).lower(), nx.group(0).lower(), t.lower()
        if UNI.get(a, 0) < 20 or UNI.get(b, 0) < 20 or len(a) < 2 or len(b) < 2:
            continue                        # 前后词是残片（ly、hill）时搭配统计不可靠
        base = p_bi(a, lt) * p_bi(lt, b)
        best, bs = None, base
        for c in cands(t):
            if BI.get((a, c), 0) == 0 or BI.get((c, b), 0) == 0:
                continue
            s = p_bi(a, c) * p_bi(c, b)
            if s > bs:
                best, bs = c, s
        if UNI.get(lt, 0) >= 200:
            continue                        # 常见真词（nor、may、fell、man…）一概不碰：2000 倍门槛也拦不住 nor→not、may→way
        thr = 50
        if best and bs >= thr * base:
            new = best.capitalize() if t[0].isupper() else best
            edits[(m.start(), m.end())] = new
            log.append((slug, f'{a} [{t}] {b}', new, f'{math.log10(bs / base):.1f}'))
    out, last = [], 0
    for (s, e), new in sorted(edits.items()):
        out.append(md[last:s])
        out.append(new)
        last = e
    out.append(md[last:])
    return ''.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('part', type=int)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    d = BASE / f'p{a.part}' / 'fixed'
    log, outs = [], {}
    for f in sorted(d.glob('*.md')):
        outs[f] = fix_md(f.read_text(encoding='utf-8'), log, f.stem)
    c = collections.Counter((re.search(r'\[(.*?)\]', x[1]).group(1).lower(), x[2].lower()) for x in log)
    print(f'第 {a.part} 部：改 {len(log):,} 处', file=sys.stderr)
    print('  ' + '；'.join(f'{w}→{n} {k}' for (w, n), k in c.most_common(40)), file=sys.stderr)
    if a.apply:
        for f, md in outs.items():
            f.write_text(md, encoding='utf-8')
        (BASE / f'p{a.part}' / 'ctx.tsv').write_text(''.join('\t'.join(x) + '\n' for x in log), encoding='utf-8')
    return log


if __name__ == '__main__':
    main()
