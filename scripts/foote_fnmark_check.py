#!/usr/bin/env python3
"""福特《路加福音讲义》第 ③ 层·正文注号看图：转录在正文里记了注号（`[FN:†]`）、我们同位没有注号哨兵的地方。

2026-11-12 用户问第 3 讲 `of David.*` 的星号，顺查：正文注号 795、注区注条 1167——注号多读成字母
（`Paul.t` `tent."J` `readf`）、或干脆丢了。残串层（foote_junk_check）只找白名单残符号，`t` `f` `J` 是字母，看不见。

做法：链条终态逐页取转录正文里每个注号，左右各取最近一个与转录同位相等的词当锚（至多 REACH 词），两锚之间
我们这段若没有注号哨兵即一题：A＝我们、B＝转录（注号以 ⁽ⁿ⁾ 显示）。一页图只看一次，裁原生分辨率行条。
**只落 B**；不落规则同残串层（转录非词／自带残字／会丢注号／改后星号奇数）。问答、出规则、落盘全用 foote_junk_check 的。

    python3 scripts/foote_fnmark_check.py --collect
    python3 scripts/foote_fnmark_check.py --run --sample 3 | --run --all
    python3 scripts/foote_fnmark_check.py --rules       # → fnmark_fixes.tsv
    python3 scripts/foote_fnmark_check.py --apply       # 链条：notes_check 之后、greek_read 之前
"""
import argparse
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import foote_image_check as I  # noqa: E402
import foote_junk_check as J  # noqa: E402
import foote_punct as P  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402

J.ANS = J.WORK / 'fnmark_answers'
# 第 1 轮：转录有注号、我们没有（补号）；第 2 轮：我们有注号哨兵、转录同位没有（前面各层把残字认成注号：
# `remnan◆^` `*nn◆*` `Jesus'◆` `."◆*`），在第 1 轮落盘后的状态上收题
ROUNDS = 2
ROUND = ROUNDS


def use_round(n):
    global ROUND
    ROUND = n
    sfx = '' if n == 1 else f'_r{n}'
    J.CAND = J.WORK / f'fnmark_candidates{sfx}.json'
    J.RULES = J.RAW / f'fnmark_fixes{sfx}.tsv'
    J.LOG = J.A.ROOT / 'logs' / f'foote_fnmark_check{sfx}.tsv'


use_round(ROUNDS)
_hold = J.hold


def hold(q):
    h = _hold(q)
    return '' if ROUND == 2 and h == 'fn-mismatch' else h   # 第 2 轮本来就是要去掉多出的注号


J.hold = hold
J.COST = J.A.ROOT / 'logs' / 'foote_fnmark_check_cost.tsv'
FNM = J.FNM
REACH = 4
norm = J.norm


def collect():
    V.EDGE = False
    pages, nq, skip = [], 0, Counter()
    for vol, leaf, texts, ours, vs, vt, _ts, _tt in P.page_pairs():
        if not ours or P.FN not in vs:
            continue
        ow = [t for *_, t in ours]
        vw = [norm(x[2]) for x in vt]
        vm = V.align_map([norm(x) for x in ow], vw)
        inv = {j: i for i, j in vm.items() if vw[j] == norm(ow[i])}
        qs, seen = [], set()
        oi = {i: j for j, i in inv.items()}
        if ROUND == 1:
            spots = []
            for m in re.finditer(P.FN, vs):
                jl = [j for j in range(len(vt)) if vt[j][1] <= m.start()][-REACH:]
                jr = [j for j in range(len(vt)) if vt[j][0] >= m.end()][:REACH]
                spots.append((next((j for j in reversed(jl) if j in inv), None), next((j for j in jr if j in inv), None)))
        else:
            spots = []
            for lec in {o[0] for o in ours}:
                idx = [i for i, o in enumerate(ours) if o[0] == lec]
                lo, hi = ours[idx[0]][1], ours[idx[-1]][2]
                for m in re.finditer(FNM, texts[lec][lo:hi]):
                    p_ = lo + m.start()
                    L = [i for i in idx if ours[i][2] <= p_][-REACH:]
                    R = [i for i in idx if ours[i][1] > p_][:REACH]
                    il = next((i for i in reversed(L) if i in oi), None)
                    ir = next((i for i in R if i in oi), None)
                    spots.append((oi.get(il), oi.get(ir)))
        for vj, vk in spots:
            if vj is None or vk is None:
                skip['无锚'] += 1
                continue
            il, ir = inv[vj], inv[vk]
            if ir <= il or ours[il][0] != ours[ir][0]:
                skip['错位'] += 1
                continue
            if (il, ir) in seen:
                continue
            seen.add((il, ir))
            lec = ours[il][0]
            text = texts[lec]
            s0, e0 = ours[il][2], ours[ir][1]
            o, v = text[s0:e0], vs[vt[vj][1]:vt[vk][0]]
            if ROUND == 1 and FNM in o:
                skip['已有'] += 1
                continue
            if ROUND == 2 and (P.FN in v or o.count(FNM) == 0):
                skip['转录也有'] += 1
                continue
            if V.SENT in v or '\n\n' in o or '<!--' in o or len(o) > 80:
                skip['跨段/读不出'] += 1
                continue
            qs.append({'kind': f'fnmark{ROUND}', 'lec': f'{lec:03d}', 's': s0, 'e': e0, 'i': il,
                       'left': text[ours[il][1]:ours[il][2]], 'right': text[ours[ir][1]:ours[ir][2]],
                       'ours': o, 'vlm': re.sub(r'[ \t]*\n[ \t]*', ' ', v).replace('’', "'")})
        if not qs:
            continue
        # 行定位：同 foote_junk_check（我们的词 ↔ tess_grc 逐词框）
        tw = I.tsv_words(vol, leaf)
        tm = {}
        sm = SequenceMatcher(None, [norm(x) for x in ow], [x[0] for x in tw], autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'equal' or (op == 'replace' and i2 - i1 == j2 - j1):
                for k in range(i2 - i1):
                    tm[i1 + k] = j1 + k
        keep = []
        for q in qs:
            ir = next(i for i in range(q['i'], len(ow)) if ours[i][1] == q['e'])
            boxes = []
            for k in sorted({q['i'], ir}):
                j = tm.get(k)
                if j is None:
                    continue
                line = [x for x in tw if x[5] == tw[j][5]]
                boxes.append((min(x[1] for x in line), min(x[2] for x in line),
                              max(x[1] + x[3] for x in line), max(x[2] + x[4] for x in line)))
            if not boxes:
                skip['定位不到行'] += 1
                continue
            q['box'] = [min(b[0] for b in boxes), min(b[1] for b in boxes),
                        max(b[2] for b in boxes), max(b[3] for b in boxes)]
            if q['box'][3] - q['box'][1] > 400:
                skip['框太高'] += 1
                continue
            text = texts[int(q['lec'])]
            q['ctx'] = (text[max(0, q['s'] - 60 - len(q['left'])):q['s']] + '⟦' + q['ours'] + '⟧'
                        + text[q['e']:q['e'] + 60]).replace('\n', ' ').replace(FNM, '⁽ⁿ⁾')
            keep.append(q)
        if keep:
            pages.append({'vol': vol, 'leaf': leaf, 'qs': keep})
            nq += len(keep)
    J.WORK.mkdir(parents=True, exist_ok=True)
    J.CAND.write_text(json.dumps(pages, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'注号题 {nq}  页 {len(pages)}  跳过 {dict(skip)} → {J.CAND}', file=sys.stderr)


# 看图后人工定的个别改作（原生分辨率裁图读定）：转录把注号后一粒墨点也记成了句点
OVERRIDE = {('132', 'justification."\ue010. The'): 'justification."\ue010 The'}
# 第 1 轮加了、第 2 轮看图又判掉的（两轮答案相抵，留着会二跑反复）：第 1 轮这条不出
DROP = {('089', 'Go and sit down to meat? 8')}


def post():
    """规则表按本书写法归一：注号紧贴前一字符（转录常在注号前留空格）；开引号后的空格照我们原样
    （全书 `" The` 1247 处、`"The` 395 处，原串是 `" X` 就保留）。"""
    lines = J.RULES.read_text(encoding='utf-8').splitlines(keepends=True)
    out = [lines[0]]
    for ln in lines[1:]:
        lec, o, n = ln.rstrip('\n').split('\t')
        if ROUND == 1 and (lec, o) in DROP:
            continue
        n = re.sub(r'[ \t]+' + FNM, FNM, n)
        if re.search(r'" [A-Za-z]', o):
            n = re.sub(r'(^|\s)"(?=[A-Za-z])', r'\1" ', n)
        for (k, a), b in OVERRIDE.items():
            if lec == k:
                n = n.replace(a, b)
        out.append('\t'.join((lec, o, n)) + '\n')
    out[0] = out[0].replace('foote_junk_check.py 生成（残串看图答 B＝转录）', 'foote_fnmark_check.py 生成（正文注号看图答 B＝转录）')
    J.RULES.write_text(''.join(out), encoding='utf-8')


SYMS = J.RAW / 'fn_symbols.json'


def symbols():
    """链条终态：正文每个注号哨兵按序配上转录同位注号的页码与印本符号 → fn_symbols.json
    {讲: [[页, 符号] | null, …]}（按本讲正文里哨兵出现顺序）。发布时据此把号与注条按「同页同符号」配对。"""
    V.EDGE = False
    got = {}
    for vol, leaf, texts, ours, vs, vt, _ts, _tt in P.page_pairs():
        if not ours or P.FN not in vs:
            continue
        raw = (V.VLM / f'v{vol}' / f'{leaf:04d}.txt').read_text(encoding='utf-8')
        raw = '\n'.join(ln for ln in raw.splitlines() if not ln.startswith('[HEAD]'))
        raw = re.split(r'\n\s*\[FN:', raw)[0]
        marks = re.findall(r'\[FN:([^\]]*)\]', raw)
        fpos = [m.start() for m in re.finditer(P.FN, vs)]
        if len(marks) != len(fpos):
            continue
        pg = V.leaf_pages(vol).get(leaf, '')
        ow = [t for *_, t in ours]
        vw = [norm(x[2]) for x in vt]
        vm = V.align_map([norm(x) for x in ow], vw)
        oi = {i: j for i, j in vm.items() if vw[j] == norm(ow[i])}
        for lec in {o[0] for o in ours}:
            text = texts[lec]
            body_end = text.find('\n---\n')
            idx = [i for i, o in enumerate(ours) if o[0] == lec]
            lo, hi = ours[idx[0]][1], ours[idx[-1]][2]
            for m in re.finditer(FNM, text[lo:hi]):
                p_ = lo + m.start()
                if 0 <= body_end < p_:
                    continue
                L = [i for i in idx if ours[i][2] <= p_][-REACH:]
                R = [i for i in idx if ours[i][1] > p_][:REACH]
                il = next((i for i in reversed(L) if i in oi), None)
                ir = next((i for i in R if i in oi), None)
                if il is None or ir is None:
                    continue
                a, b = vt[oi[il]][1], vt[oi[ir]][0]
                ks = [k for k, f in enumerate(fpos) if a <= f < b]
                if len(ks) == 1 and text[ours[il][2]:ours[ir][1]].count(FNM) == 1:
                    got[(lec, p_)] = [str(pg), marks[ks[0]]]
    out, n, k = {}, 0, 0
    for lec in sorted({l for l, _ in got} | set(range(1, 138))):
        text = (J.A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8')
        body = text.partition('\n---\n')[0]
        row = [got.get((lec, m.start())) for m in re.finditer(FNM, body)]
        out[str(lec)] = row
        n += len(row)
        k += sum(x is not None for x in row)
    SYMS.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'注号定符 {k}/{n} → {SYMS}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--collect', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--rules', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--round', type=int, default=ROUNDS)
    ap.add_argument('--symbols', action='store_true', help='链条最末、发布前：注号哨兵配转录页码与符号 → fn_symbols.json')
    a = ap.parse_args()
    use_round(a.round)
    if a.symbols:
        symbols()
    elif a.collect:
        collect()
    elif a.run:
        J.run(a.sample, a.all)
    elif a.rules:
        J.rules()
        post()
    elif a.apply:
        for n in range(1, ROUNDS + 1):
            use_round(n)
            if J.RULES.exists():
                I.apply_multiline(J.RULES)


if __name__ == '__main__':
    main()
