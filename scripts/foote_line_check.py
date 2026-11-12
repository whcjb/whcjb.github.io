#!/usr/bin/env python3
"""福特《路加福音讲义》正文残字·逐处重定位看图（2026-11-12 用户令「继续处理，把错误都处理」）。

前三轮残串看图（foote_junk_check）出题要靠 V.align_map 把我们的词流与转录词流整页对齐，再取「与转录同位相等」的词作锚；
页首页尾被 trim 掉的、整页对不齐的、锚词本身读花的，一题也出不来——剩下的正文残字约 270 处，抽看 p.440、p.685、p.395
印面都干净，是 OCR 读错而不是墨渍（真被墨渍盖住的只有卷一 5 页，转录也记 [?]，另由第 3 版补）。

这层换定位法（同 foote_junk_ed3）：残字两旁各取至多 3 个不带残符号的词，按字母串在该页（及前后各一页）转录里找，
左锚唯一命中、右锚紧随其后（至多 80 字母）——两锚间就是转录同位读法（B）。图：tess_grc 逐词框里左锚末词、右锚首词
所在行合成一条，裁原生分辨率。题型、问法、闸（vlm-nonword / fn-mismatch / odd-star→keep_stars）、出规则全照
foote_junk_check 第 3 轮。只落答 B。

    python3 scripts/foote_line_check.py --collect     # 链条位置：foote_heads --apply 之后
    python3 scripts/foote_line_check.py --run --sample 3 | --run --all
    python3 scripts/foote_line_check.py --rules       # → line_fixes.tsv
    python3 scripts/foote_line_check.py --apply
"""
import argparse
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_image_check as I  # noqa: E402
import foote_junk_check as J  # noqa: E402
import foote_punct as P  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402

J.use_round(3)                      # keep_stars 等第 3 轮口径
J.CAND = J.WORK / 'line_candidates.json'
J.ANS = J.WORK / 'line_answers'
J.RULES = J.RAW / 'line_fixes.tsv'
J.LOG = A.ROOT / 'logs' / 'foote_line_check.tsv'
ORD = re.compile(r'\b\d+(st|nd|rd|th|d)\b')
TOK = re.compile(r'\S+')
REACH = 3


def letters(t):
    return re.sub(r'[^a-z]', '', t.lower())


def bad(w):
    return bool(J.BAD.search(ORD.sub('', w)))


def lstream(s):
    pos = [i for i, c in enumerate(s) if c.isascii() and c.isalpha()]
    return ''.join(s[i].lower() for i in pos), pos


def vol_stream(vol):
    """整卷转录 → 全文（叶间 \\n）、字母流、字母→全文位置、全文位置→叶号。"""
    parts, leaves = [], []
    for f in sorted((V.VLM / f'v{vol}').glob('*.txt')):
        t = P.clean_vlm(f.read_text(encoding='utf-8')) + '\n'
        parts.append(t)
        leaves += [int(f.stem)] * len(t)
    vs = ''.join(parts)
    low, pos = lstream(vs)
    return vs, low, pos, leaves


def find_box(tw, ctx_toks, il, ir):
    """我们残字前后一段词（ctx_toks，字母小写）与该叶 tess_grc 逐词整段序列对齐，取左锚末词 il、右锚首词 ir 所在行。
    先认长度 ≥3 的相合块（常见词 the/and 单个对上不算——2026-11-12 首跑因此裁错行，答案作废）；不够再认 ≥2 的块，
    但两锚在 tess 里的间距须与我们这边相当（残字可能被 tess 拆成 0–3 个词）。锚本身没对上的，往外让一词。"""
    sm = SequenceMatcher(None, ctx_toks, [x[0] for x in tw], autojunk=False)
    for need in (3, 2):
        m = {}
        for blk in sm.get_matching_blocks():
            if blk.size >= need:
                for k in range(blk.size):
                    m[blk.a + k] = blk.b + k
        for dl in (0, 1):
            for dr in (0, 1):
                a, b = il - dl, ir + dr
                if a in m and b in m:
                    gap_o, gap_t = b - a, m[b] - m[a]
                    if 0 < gap_t <= 14 and gap_o - 2 <= gap_t <= gap_o + 3:
                        return m[a], m[b]
    return None


def collect():
    pages, skip = {}, Counter()
    for vol in (1, 2, 3):
        vs, low, pos, leaves = vol_stream(vol)
        twc = {}
        pn = V.leaf_pages(vol)
        for lec in V.LECS[vol]:
            text = (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8')
            body = text.partition('\n---\n')[0]
            pgs = [int(x) for x in re.findall(r'<!-- PAGE (\d+) -->', body)]
            lo_pg, hi_pg = (min(pgs) - 1, max(pgs) + 1) if pgs else (0, 0)
            tags = [(m.start(), m.end()) for m in re.finditer(r'<!--.*?-->', body, re.S)]
            toks = [(m.start(), m.end(), m.group()) for m in TOK.finditer(body)
                    if not any(a <= m.start() < b for a, b in tags)]
            badi = [i for i, (s, e, w) in enumerate(toks) if bad(w) and not (w == '>' and body[s - 1] == '\n')
                    and not body[body.rfind('\n', 0, s) + 1:].startswith(('## ', '**LUKE'))]
            done = set()
            for i in badi:
                if i in done:
                    continue
                lo = hi = i
                while hi + 1 < len(toks) and (bad(toks[hi + 1][2]) or (hi + 2 < len(toks) and bad(toks[hi + 2][2])
                                                                       and hi + 2 - i <= 3)):
                    hi += 1
                done.update(range(lo, hi + 1))
                left = toks[max(0, lo - REACH):lo]
                right = toks[hi + 1:hi + 1 + REACH]
                if len(left) < 2 or len(right) < 2 or any(bad(w) for *_, w in left + right):
                    skip['锚不够'] += 1
                    continue
                s, e = left[-1][1], right[0][0]
                o = body[s:e]
                para = '\n\n' in o
                if para:
                    # 段首残字（`*^^ And`）：改问本段行首 → 右锚，转录取右锚所在段的段首起
                    ps = s + o.rfind('\n\n') + 2
                    while body.startswith('<!--', ps):
                        ps = body.find('-->', ps) + 3
                        ps += len(body[ps:]) - len(body[ps:].lstrip('\n'))
                    if body.startswith('> ', ps):
                        ps += 2
                    if '<!--' in body[ps:e] or '\n' in body[ps:e]:
                        skip['跨段'] += 1
                        continue
                elif '<!--' in o:
                    skip['跨页标记'] += 1
                    continue
                found = {}

                def in_lec(lf):
                    try:
                        return lo_pg <= int(pn.get(lf, -1)) <= hi_pg
                    except ValueError:
                        return False
                # 锚由长到短试（3/2/1 词），只认本讲页码范围里的命中——锚词本身读花时短锚也能定位
                for nl, nr in ((3, 3), (3, 2), (2, 3), (2, 2), (2, 1), (1, 2), (1, 1)):
                    L = letters(''.join(w for *_, w in left[-nl:]))
                    R = letters(''.join(w for *_, w in right[:nr]))
                    if len(L) < (8 if nl > 1 else 6) or len(R) < (5 if nr > 1 else 4):
                        continue
                    for m in re.finditer(re.escape(L), low):
                        h = m.start()
                        j = low.find(R, h + len(L), h + len(L) + 80 + len(R))
                        if j >= 0:
                            a0, b0 = pos[h + len(L) - 1] + 1, pos[j]
                            if in_lec(leaves[a0]):
                                found[vs[a0:b0]] = leaves[a0]
                    if found:
                        break
                if len(found) != 1:
                    skip['转录定位不到' if not found else '转录多处'] += 1
                    continue
                v, lf = found.popitem()
                if V.SENT in v:
                    skip['转录读不出'] += 1
                    continue
                tailp = para and not re.search('[A-Za-z]', re.sub(r'<!--.*?-->', '', o[o.find('\n\n'):])) \
                    and re.search(r'\S', o[:o.find('\n\n')])
                if tailp:
                    # 段末残字（经文段收引号读花 `inn.^\\*`）：截到本段末，转录取到它分段处
                    if '\n' not in v.lstrip(' '):
                        skip['段末·转录不分段'] += 1
                        continue
                    o = o[:o.find('\n\n')]
                    e = s + len(o)
                    v = v.strip(' ').split('\n')[0]
                    v = ' ' + v.lstrip() if o.startswith(' ') else v.lstrip()
                    para = False
                if para:
                    if '\n' in v.strip():
                        v = v[v.rstrip().rfind('\n') + 1:]
                    elif re.search('[A-Za-z]', re.sub(r'<!--.*?-->', '', body[s:ps])):
                        skip['跨段·转录不分段'] += 1
                        continue
                    # 我们在页首另起段、转录接着上页写：左锚到段首之间只有标记没有字，转录那截整段对应
                    s, o = ps, body[ps:e]
                v = re.sub(r'[ \t]*\n[ \t]*', ' ', v).replace('’', "'")
                # 两头口径对齐我们这截：左锚词末尾的标点、右锚词开头的标点（引号、星号）已在锚里，B 里去掉
                qn = lambda t: t.translate(str.maketrans('“”‘’', '""\'\''))
                ltail = re.search(r"[^A-Za-z]*$", left[-1][2]).group()
                rhead = re.match(r"[^A-Za-z]*", right[0][2]).group()
                vv = qn(v)
                if ltail and not para and vv.lstrip().startswith(qn(ltail)):
                    k = len(vv) - len(vv.lstrip())
                    v = v[:k] + v[k + len(ltail):]
                    vv = qn(v)
                if rhead and vv.rstrip().endswith(qn(rhead)):
                    k = len(vv.rstrip())
                    v = v[:k - len(rhead)] + v[k:]
                v = re.sub(r'\s+', ' ', v)
                if not o.strip() or re.search(r'-\s*$', v.strip() + ' ') and not o.strip().endswith('-') \
                        or v.strip().endswith('-'):
                    skip['空截/行末断词'] += 1
                    continue
                lo_, lv = letters(o), letters(v)
                if lv and len(lo_) > 3 and SequenceMatcher(None, lo_, lv, autojunk=False).ratio() < 0.4:
                    skip['字母不合'] += 1
                    continue
                if lf not in twc:
                    twc[lf] = I.tsv_words(vol, lf)
                tw = twc[lf]
                c0, c1 = max(0, lo - 15), min(len(toks), hi + 16)
                ctx_toks = [letters(w) for *_, w in toks[c0:c1]]
                best = find_box(tw, ctx_toks, lo - 1 - c0, hi + 1 - c0)
                if not best:
                    skip['定位不到行'] += 1
                    continue
                keys = {tw[best[0]][5], tw[best[1]][5]}
                line = [x for x in tw if x[5] in keys]
                box = [min(x[1] for x in line), min(x[2] for x in line),
                       max(x[1] + x[3] for x in line), max(x[2] + x[4] for x in line)]
                if box[3] - box[1] > 300:
                    skip['框太高'] += 1
                    continue
                lstart = left[-1][0] if not para else body.rfind('\n', 0, s) + 1
                q = {'kind': 'junk', 'lec': f'{lec:03d}', 's': s, 'e': e, 'i': 0,
                     'left': body[lstart:s], 'right': '' if tailp else body[e:right[0][1]], 'ours': o, 'vlm': v, 'box': box,
                     'ctx': re.sub(r'<!--.*?-->', '', body[max(0, s - 70):s] + '⟦' + o + '⟧' + body[e:e + 70]).replace('\n', ' ')}
                pages.setdefault((vol, lf), []).append(q)
    out = [{'vol': v, 'leaf': lf, 'qs': qs} for (v, lf), qs in sorted(pages.items())]
    J.WORK.mkdir(parents=True, exist_ok=True)
    J.CAND.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'题 {sum(len(p["qs"]) for p in out)}  页 {len(out)}  跳过 {dict(skip)} → {J.CAND}', file=sys.stderr)


def rules():
    """J.rules 出表后再过一道：改作里冒出的新词须是真词（第 17 讲 B 是 `un`、右锚 `per`，拼成 unper）。"""
    J.rules()
    lines = J.RULES.read_text(encoding='utf-8').splitlines()
    keep, drop = [lines[0]], []
    for ln in lines[1:]:
        lec, o, n = ln.split('\t')
        ow = set(re.findall(r"[A-Za-z']+", o))
        new = [w for w in re.findall(r"[A-Za-z']+", n) if w not in ow and not A._isword(w.strip("'").lower())]
        (drop if new else keep).append(ln if not new else (ln, new))
    J.RULES.write_text('\n'.join(keep) + '\n', encoding='utf-8')
    for ln, w in drop:
        print('挡：', ln.replace('\t', ' | ')[:120], w, file=sys.stderr)
    print(f'规则 {len(keep) - 1}（挡 {len(drop)}）', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--collect', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--rules', action='store_true')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    if a.collect:
        collect()
    elif a.run:
        J.run(a.sample, a.all)
    elif a.rules:
        rules()
    elif a.apply and J.RULES.exists():
        I.apply_multiline(J.RULES)


if __name__ == '__main__':
    main()
