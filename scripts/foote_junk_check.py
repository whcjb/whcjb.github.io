#!/usr/bin/env python3
"""福特《路加福音讲义》第 ③ 层·残串看图：前一轮看图（foote_image_check.py）问不到的连串残字。

前一轮三种题（词 / 缝 / 跨）都要求残字两旁的词与转录同位相等、且只问 1–3 词的小截；
`*9suggestion,* and the inspiration of (i^ir<0(;^um-—` 这种一串连着烂的（残符号夹在词里、词里夹数字、
相邻几个词一起读崩）一题也出不来（2026-11-11 用户指出第 1 讲这一句）。

做法：链条终态（header_fixes 之后）逐页按白名单找残字——`^ < > • ■ « » | ~ { }`、字母里夹数字；
以残字为中心，左右各取最近一个与转录同位相等的词当锚（各至多 6 词内），两锚之间整段为一题：
A＝我们这段，B＝转录那段。仍是一页图只看一次，裁原生分辨率行条。
**只在答 B 时落**（转录与看图两次读印面一致）；答 `=` 与两边都不同的记 other 待人看，不落。

    python3 scripts/foote_junk_check.py --collect
    python3 scripts/foote_junk_check.py --run --sample 5
    python3 scripts/foote_junk_check.py --run --all     # 额度用尽退出码 42；已问过的按题目内容认，不重问
    python3 scripts/foote_junk_check.py --rules         # → junk_fixes.tsv
    python3 scripts/foote_junk_check.py --apply         # 链条最末（foote_image_check.py --apply 之后）
"""
import argparse
import csv
import json
import random
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_image_check as I  # noqa: E402
import foote_punct as P  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402

RAW = A.RAW
WORK = RAW / 'imgcheck'
# 按轮：第 n 轮在第 n-1 轮落盘后的状态上收题；各轮题目、规则表分开存，--apply 按轮序全落
ROUNDS = 2
CAND = WORK / 'junk_candidates.json'
ANS = WORK / 'junk_answers'
RULES = RAW / 'junk_fixes.tsv'
LOG = A.ROOT / 'logs' / 'foote_junk_check.tsv'


def use_round(n):
    global CAND, RULES, LOG
    sfx = '' if n == 1 else f'_r{n}'
    CAND = WORK / f'junk_candidates{sfx}.json'
    RULES = RAW / f'junk_fixes{sfx}.tsv'
    LOG = A.ROOT / 'logs' / f'foote_junk_check{sfx}.tsv'
COST = A.ROOT / 'logs' / 'foote_junk_check_cost.tsv'

BAD = re.compile(r"[\^<>•■«»|~{}]|[A-Za-z]\d|\d[A-Za-z]{2,}")
ORD = re.compile(r"\d+(st|nd|rd|th|d)\b")
FNM = A.FN_MARK
REACH = 6

SYSTEM = (
    'You are proof-reading a digitised 19th-century printed book against images of its printed lines. '
    'For each numbered question you get a line strip (native scan resolution) and a passage between two anchor words '
    '(shown in context) with two candidate readings A and B of the passage. Look at the strip and decide which reading '
    'matches what is actually printed, character for character: letters, digits, apostrophes, hyphens, dashes, and every '
    'punctuation mark including quotation marks. Asterisks *like this* only mark italics. '
    '⁽ⁿ⁾ stands for a footnote reference mark (any of * † ‡ § ‖ ¶) — treat it as matching whichever mark is printed. '
    'Answer each question on its own line exactly as  #n: A   or  #n: B   or, if neither matches the print,  '
    '#n: = <the printed text of the passage>  . If it cannot be made out, answer  #n: ?  . Output only the answer lines.'
)


def norm(w):
    return w.translate(I.G.LIG).replace('’', "'").lower()


def collect():
    V.EDGE = False
    pages, nq, nloc, skip = [], 0, 0, Counter()
    for vol, leaf, texts, ours, vs, vt, _ts, _tt in P.page_pairs():
        if not ours:
            continue
        ow = [t for *_, t in ours]
        vw = [norm(x[2]) for x in vt]
        vm = V.align_map([norm(x) for x in ow], vw)
        eq = lambda i: i in vm and vw[vm[i]] == norm(ow[i])
        qs, seen = [], set()
        by_lec = {}
        for i, (lec, s, e, _t) in enumerate(ours):
            by_lec.setdefault(lec, []).append(i)
        for lec, idx in by_lec.items():
            text = texts[lec]
            lo, hi = ours[idx[0]][1], ours[idx[-1]][2]
            notes = text.find('\n---\n')
            tags = [(t.start(), t.end()) for t in re.finditer(r'<!--.*?-->', text)]
            for m in BAD.finditer(text, lo, hi):
                if notes >= 0 and m.start() > notes:
                    break                                  # 注区另做
                if any(a <= m.start() < b for a, b in tags):
                    continue
                if m.group() == '>' and text[m.start() - 1] == '\n':
                    continue                               # 经文段的 markdown 引用符
                # 左锚：残字之前最近的、与转录相等的词（不得含残字本身）
                left = [i for i in idx if ours[i][2] <= m.start()][-REACH:]
                right = [i for i in idx if ours[i][1] >= m.end()][:REACH]
                il = next((i for i in reversed(left) if eq(i) and not BAD.search(ours[i][3])), None)
                ir = next((i for i in right if eq(i) and not BAD.search(ours[i][3])), None)
                if il is None or ir is None:
                    skip['无锚'] += 1
                    continue
                if (il, ir) in seen:
                    continue
                seen.add((il, ir))
                s0, e0 = ours[il][2], ours[ir][1]
                o = text[s0:e0]
                vj, vk = vm[il], vm[ir]
                if vk <= vj or vk - vj > 2 * REACH:
                    skip['转录错位'] += 1
                    continue
                v = vs[vt[vj][1]:vt[vk][0]]
                if '\n\n' in o or '<!--' in o:
                    # 段首残字（`*^^Now it came`）：左锚在上一段。改问「本段行首 → 右锚」那截，转录取右锚所在行的行首起；
                    # 上一段末词须与转录同位相等、且两边这截词数一样，才认定转录那行就是段首行
                    ps = text.rfind('\n', 0, m.start()) + 1
                    if text.startswith('> ', ps):
                        ps += 2                            # 经文段：引用符留着
                    pre = [i for i in idx if ours[i][2] <= ps]
                    mid = [i for i in idx if ps <= ours[i][1] and ours[i][2] <= ours[ir][1] and i != ir]
                    vl = vs.rfind('\n', 0, vt[vk][0]) + 1
                    vmid = [x for x in vt if vl <= x[0] < vt[vk][0]]
                    if (not pre or not eq(pre[-1]) or len(mid) != len(vmid) or vk - vm[pre[-1]] != len(mid) + 1
                            or ps >= ours[ir][1] or text[ps:ps + 4] == '<!--' or len(text[ps:ours[ir][1]]) > 60):
                        skip['跨段'] += 1
                        continue
                    if ('P', ps, ir) in seen:
                        continue
                    seen.add(('P', ps, ir))
                    v = vs[vl:vt[vk][0]]
                    if V.SENT in v:
                        skip['转录读不出'] += 1
                        continue
                    qs.append({'kind': 'junk', 'lec': f'{lec:03d}', 's': ps, 'e': ours[ir][1], 'i': ir,
                               'left': text[text.rfind('\n', 0, ps):ps],
                               'right': text[ours[ir][1]:ours[ir][2]], 'ours': text[ps:ours[ir][1]], 'vlm': v.lstrip().replace('’', "'")})
                    continue
                if V.SENT in v:
                    skip['转录读不出'] += 1
                    continue
                if ORD.fullmatch(m.group()) or re.fullmatch(r'\s*\d+(st|nd|rd|th|d)\s*', o):
                    continue
                qs.append({'kind': 'junk', 'lec': f'{lec:03d}', 's': s0, 'e': e0, 'i': il, 'left': text[ours[il][1]:ours[il][2]],
                           'right': text[ours[ir][1]:ours[ir][2]], 'ours': o, 'vlm': re.sub(r'[ \t]*\n[ \t]*', ' ', v).replace('’', "'")})
        if not qs:
            continue
        # 行定位：同 foote_image_check（我们的词 ↔ tess_grc 逐词框），两锚所在行合成一框
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
                key = tw[j][5]
                line = [x for x in tw if x[5] == key]
                boxes.append((min(x[1] for x in line), min(x[2] for x in line),
                              max(x[1] + x[3] for x in line), max(x[2] + x[4] for x in line)))
            if not boxes:
                skip['定位不到行'] += 1
                continue
            q['box'] = [min(b[0] for b in boxes), min(b[1] for b in boxes),
                        max(b[2] for b in boxes), max(b[3] for b in boxes)]
            if q['box'][3] - q['box'][1] > 400:          # 两锚隔了好几行：多半错位
                skip['框太高'] += 1
                continue
            text = texts[int(q['lec'])]
            q['ctx'] = (text[max(0, q['s'] - 60 - len(q['left'])):q['s']] + '⟦' + q['ours'] + '⟧'
                        + text[q['e']:q['e'] + 60]).replace('\n', ' ')
            keep.append(q)
            nloc += 1
        if keep:
            pages.append({'vol': vol, 'leaf': leaf, 'qs': keep})
            nq += len(keep)
    WORK.mkdir(parents=True, exist_ok=True)
    CAND.write_text(json.dumps(pages, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'残串题 {nq}  页 {len(pages)}  跳过 {dict(skip)} → {CAND}', file=sys.stderr)


def show(q):
    a = f"{q['left']}{q['ours']}{q['right']}".replace(FNM, '⁽ⁿ⁾').lstrip('\n> ')
    b = f"{q['left']}{q['vlm']}{q['right']}".replace(P.FN, '⁽ⁿ⁾').lstrip('\n> ')
    return re.sub(r'\s+', ' ', a), re.sub(r'\s+', ' ', b)


def ask(vol, leaf, qs):
    old_sys, old_show = I.SYSTEM, I.show
    I.SYSTEM, I.show = SYSTEM, show
    try:
        return I.ask(vol, leaf, qs)
    finally:
        I.SYSTEM, I.show = old_sys, old_show


def qkey(q):
    return (q['lec'], q['ours'], q['vlm'], q['ctx'])


def answered():
    got = {}
    for f in sorted(ANS.glob('v*/*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        for n, q in enumerate(d['qs'], 1):
            a = d['ans'].get(str(n), '')
            if q.get('swap') and a in ('A', 'B'):
                a = 'B' if a == 'A' else 'A'
            got[qkey(q)] = a
    return got


def run(sample, all_):
    pages = json.loads(CAND.read_text(encoding='utf-8'))
    got = answered()
    todo = []
    for p in pages:
        qs = [q for q in p['qs'] if qkey(q) not in got]
        rnd = random.Random(f"junk-{p['vol']}-{p['leaf']}")
        for q in qs:
            q['swap'] = rnd.random() < 0.5
        if qs:
            todo.append(dict(p, qs=qs))
    if not all_:
        random.seed(20261111)
        todo = random.sample(todo, min(sample or 5, len(todo)))
    total, fails = 0.0, 0
    with open(COST, 'a', encoding='utf-8') as fh:
        for n, p in enumerate(todo, 1):
            try:
                res, cost = ask(p['vol'], p['leaf'], p['qs'])
            except Exception as e:                     # noqa: BLE001
                fails += 1
                print(f"v{p['vol']} {p['leaf']:4d} 失败 {e}", file=sys.stderr, flush=True)
                if 'limit' in str(e).lower():
                    print('⛔ 额度用尽，中止', file=sys.stderr, flush=True)
                    sys.exit(42)
                if fails >= 5:
                    print('⛔ 连续失败过多，中止', file=sys.stderr, flush=True)
                    sys.exit(3)
                continue
            fails = 0
            total += cost
            ans = {int(m.group(1)): m.group(2) for m in re.finditer(r'^\s*#(\d+):\s*(.*?)\s*$', res, re.M)}
            d = ANS / f"v{p['vol']}"
            d.mkdir(parents=True, exist_ok=True)
            k = 1
            while (d / f"{p['leaf']:04d}_{k}.json").exists():
                k += 1
            (d / f"{p['leaf']:04d}_{k}.json").write_text(
                json.dumps({'raw': res, 'ans': ans, 'qs': p['qs']}, ensure_ascii=False), encoding='utf-8')
            fh.write(f"{p['vol']}\t{p['leaf']}\t{len(p['qs'])}\t{len(ans)}\t{cost:.4f}\n")
            fh.flush()
            print(f"v{p['vol']} {p['leaf']:4d} 问 {len(p['qs']):2d} 答 {len(ans):2d}  ${cost:.4f}  累计 ${total:.2f}  "
                  f"({n}/{len(todo)})", file=sys.stderr, flush=True)


def verdict(q, a):
    if a in ('A', 'B'):
        return a
    if not a.startswith('='):
        return 'other'
    f = lambda t: re.sub(r'[\s*†‡§‖¶]|⁽ⁿ⁾', '', t.replace('’', "'").replace('“', '"').replace('”', '"'))
    sa, sb = show(q)
    x = a[1:].strip()
    x, sa, sb = f(x).lower(), f(sa).lower(), f(sb).lower()
    return 'B' if x == sb else 'A' if x == sa else 'other'


def hold(q):
    """B 不落的：转录那段有判词典不认、全书别处也没见过的词（模型会照着转录的错字答 B）；
    转录那段自己还带残符号；注号个数对不上；改后本段斜体星号成奇数。"""
    v = q['vlm']
    if BAD.search(ORD.sub('', v.replace(P.FN, ''))):
        return 'vlm-junk'
    for w in re.findall(r"[A-Za-zæœÆŒ']+", v):
        w = w.strip("'")
        if w and not (A._isword(w) or re.search('[æœÆŒ]', w) or I._corpus_has(w)):
            return 'vlm-nonword'
    if q['ours'].count(FNM) > v.count(P.FN):      # 会丢注号的不落；转录多出的注号（我们读成 f / j; / +）照转录补上
        return 'fn-mismatch'
    text = I.src_text(q['lec'])
    a = text.rfind('\n\n', 0, q['s'])
    b = text.find('\n\n', q['e'])
    para = text[a + 2 if a >= 0 else 0:q['s']] + v + text[q['e']:b if b >= 0 else len(text)]
    if len(re.findall(r'(?<!\\)\*', para)) % 2:
        return 'odd-star'
    return ''


def joinable(q):
    m = re.fullmatch(r"\s*([A-Za-z]+)-?\s*[\^<>«»~•]+-?\s*([A-Za-z]+)([,.;:]?)\s*|\s*([A-Za-z]+)-?[\^<>«»~•]+\s+([A-Za-z]+)([,.;:]?)\s*",
                     q['ours'])
    if not m:
        return False
    g = [x for x in m.groups() if x is not None]
    w = g[0] + g[1]
    return q['vlm'].strip() == w + g[2] and A._isword(w)


def rules():
    pages = json.loads(CAND.read_text(encoding='utf-8'))
    got = answered()
    rows, edits = [], []
    for p in pages:
        for q in p['qs']:
            a = got.get(qkey(q))
            if a is None:
                rows.append(('unasked', q['lec'], p['vol'], p['leaf'], q['ours'], q['vlm'], '', q['ctx']))
                continue
            if I.src_text(q['lec'])[q['s']:q['e']] != q['ours']:
                rows.append(('stale', q['lec'], p['vol'], p['leaf'], q['ours'], q['vlm'], a, q['ctx']))
                continue
            v = verdict(q, a)
            if v == 'A' and joinable(q):
                v = 'B'          # 断词并回：印面行末断开（答 A 如实），转录读整词、两截间只隔残符号——同 manual_spans 口径
            h = hold(q) if v == 'B' else ''
            if h:
                v = 'B-hold:' + h
            rows.append((v, q['lec'], p['vol'], p['leaf'], q['ours'], q['vlm'], a, q['ctx']))
            if v == 'B':
                # 锚词一并带上，串才唯一；注号按转录位置放回
                nv = q['vlm'].replace(P.FN, FNM).translate(str.maketrans('“”‘’', '""\'\''))   # 全书用直引号
                nv = re.sub(r'^" \*(?=[A-Za-z]|$)', '"*', nv)       # 段首 `" *And` → `"*And`（转录把开引号与斜体分开写）
                edits.append((q['lec'], q['left'] + q['ours'] + q['right'], q['left'] + nv + q['right']))
    out, txt = [], {}
    for lec, o, n in edits:
        t = txt.setdefault(lec, I.src_text(lec))
        # 同串在本讲出现不止一处（段首 `*^^And`）：两边一起往后扩，直到唯一
        while t.count(o) > 1:
            at = t.find(o)
            k = at + len(o)
            if k >= len(t) or t[k] == '\n':
                break
            o, n = o + t[k], n + t[k]
        if t.count(o) != 1 or o in n:
            rows.append(('X', lec, '', '', o, n, 'not-unique', ''))
            continue
        t = t.replace(o, n)
        if t.count(o):
            rows.append(('X', lec, '', '', o, n, 'not-idempotent', ''))
            continue
        txt[lec] = t
        out.append((lec, o, n))
    with open(LOG, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['verdict', 'lecture', 'vol', 'leaf', 'ours', 'vlm', 'answer', 'ctx'])
        w.writerows(rows)
    RULES.write_text('# lecture\t原串(逐字)\t改作 —— foote_junk_check.py 生成（残串看图答 B＝转录）；\\n 表换行\n'
                     + ''.join('\t'.join(x.replace('\n', '\\n') for x in r) + '\n' for r in out), encoding='utf-8')
    print(dict(Counter(r[0] for r in rows)), f'规则 {len(out)} → {RULES}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--collect', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--rules', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--round', type=int, default=ROUNDS, help='收题/问/出规则用第几轮（默认最新一轮）')
    a = ap.parse_args()
    use_round(a.round)
    if a.collect:
        collect()
    elif a.run:
        run(a.sample, a.all)
    elif a.rules:
        rules()
    elif a.apply:
        for n in range(1, ROUNDS + 1):
            use_round(n)
            if RULES.exists():
                I.apply_multiline(RULES)


if __name__ == '__main__':
    main()
