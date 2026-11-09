#!/usr/bin/env python3
"""福特《路加福音讲义》第 ③ 层：拿整页转录（第三证人）按位置判读残字（skill old-book-ocr §2.6 / §1）。

三份字流在同一页上逐词对齐：
  我们    en_chapters（ABBYY 抽取 + 前几层修复）
  tess    tesseract 重扫（非生成式）
  vlm     视觉模型整页转录（foote_transcribe.py，生成式，**只当证人**）

判决（一对一对齐上的每个分歧词）：
  agree3      我们不是真词；tess 与 vlm 同位读出同一真词          → 候选落（两家独立一致，其一非生成式）
  realword3   我们是真词（判词典看不见的真词错字 hook←book）；tess 与 vlm 同位一致、与我们不同、字形相近 → 候选落
  vlm_only    我们不是真词；只有 vlm 给出真词（tess 读崩/对不上）   → 不落，留裁原图看
  其余（vlm 与 tess 都同我们、或 vlm 与我们都是真词而 tess 同我们）不动——vlm 读错的就在这里被挡下

产物：logs/foote_vlm.tsv（全部分歧，备查）；`--rules` 时把 agree3 / realword3 写成 foote_raw/luke/vlm_fixes.tsv
（格式同 witness_fixes：讲次、前三词锚、原样、改作），**写出后须逐条看过**再接链条（adjudicate --apply 在 symbols 之后落）。

    python3 scripts/foote_vlm_adjudicate.py            # 只统计 + 日志
    python3 scripts/foote_vlm_adjudicate.py --rules    # 另写规则表
"""
import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
from alexander_lexicon import build, is_word  # noqa: E402
from repair_alexander_ocr import foote_kjv_words  # noqa: E402

ROOT = A.ROOT
RAW = A.RAW
VLM = RAW / 'vlm'
TESS = RAW / 'tess'
IDS = {1: 'lecturesongospe03footgoog', 2: 'lecturesongospe02footgoog', 3: 'lecturesongospe00footgoog'}
LECS = {1: range(1, 41), 2: range(41, 91), 3: range(91, 138)}
LOG = ROOT / 'logs' / 'foote_vlm.tsv'
RULES = RAW / 'vlm_fixes.tsv'
TOKEN = A.TOKEN
PAGE = re.compile(r'<!-- PAGE ([^>]*?) ?-->')


def leaf_pages(vol):
    d = json.loads((RAW / 'src' / f'{IDS[vol]}_page_numbers.json').read_text())
    return {x['leafNum']: x['pageNumber'] for x in d['pages']}


def page_segments(vol):
    """印刷页 → [(讲次, 起, 止)]，只取正文（`---` 注区之前）。讲首在第一个 PAGE 标记之前的部分属于上一页。"""
    segs = defaultdict(list)
    cur = None
    for lec in LECS[vol]:
        text = (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8')
        body_end = text.find('\n---\n')
        body_end = len(text) if body_end < 0 else body_end
        pos = 0
        for m in PAGE.finditer(text, 0, body_end):
            if cur is not None and m.start() > pos:
                segs[cur].append((lec, pos, m.start()))
            pg = m.group(1).strip()
            cur = pg if pg else (str(int(cur) + 1) if cur and cur.isdigit() else cur)
            pos = m.end()
        if cur is not None:
            segs[cur].append((lec, pos, body_end))
    return segs


def clean_vlm(t):
    lines = [ln for ln in t.splitlines() if not ln.startswith('[HEAD]')]
    body = []
    for ln in lines:
        if re.match(r'\s*\[FN:', ln):
            break                      # 注文在页末，正文到此为止
        body.append(ln)
    s = '\n'.join(body)
    s = re.sub(r'\[FN:[^\]]*\]|\[SIG:[^\]]*\]', ' ', s)
    s = s.replace('[?]', '  ').replace('*', '')
    return s


SENT = '\ue000'
VWORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’]*|" + SENT)
OKP = set(' \t\n,.;:!?\'"’”‘“)]—-*<\\')     # 词后可以紧跟的正常字符；其余非字母＝残渣
LEAD = set(' \t\n*"“‘\'—->')                 # 词前可以紧挨的；否则这个词是残片（Sa^tan 的 tan）
PUNCT = set(',.;:!?')
QUOTE = set('"“‘\'([')


def vtoks(s):
    return [(m.start(), m.end(), m.group(0)) for m in VWORD.finditer(s)]


def align_map(a, b):
    """a 的下标 → b 的同位下标（只取等长替换块与相等块）。"""
    out = {}
    sm = SequenceMatcher(None, [x.lower() for x in a], [x.lower() for x in b], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal' or (op == 'replace' and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                out[i1 + k] = j1 + k
    return out


def trail(s, e):
    """词后紧跟的标点（到空白为止，只收 ,.;:!?）。"""
    k = e
    while k < len(s) and s[k] in PUNCT:
        k += 1
    return s[e:k]


def make_rule(text, a, b, o, v, vs, va, vb, ts, tb0, tb, nxt):
    """守卫：返回 (原串, 改作) 或 (None, 原因)。原串＝我们的词＋紧粘的残渣。"""
    if len(o) >= len(v) + 3 and (o.lower().startswith(v.lower()) or o.lower().endswith(v.lower())
                                 or SequenceMatcher(None, o.lower(), v.lower()).ratio() < 0.5):
        return None, 'merge_suspect'                   # Avulhe → he：我们这个串里还粘着别的词
    i = a
    while i > 0 and text[i - 1] not in LEAD and not text[i - 1].isalpha() and not text[i - 1].isspace():
        i -= 1                                         # 词前紧粘的残渣（«uid、6ase、^^AU）
    if i > 0 and text[i - 1] not in LEAD:
        return None, 'frag_left'                       # 残渣前还粘着字母：残片（Sa^tan 的 tan）
    lead = text[i:a]
    if va > 0 and (vs[va - 1].isdigit() or vs[va - 1].isalpha()):
        return None, 'v_frag'                          # 证人那边是 1st 的 st
    if nxt and len(v) > len(o) and v.lower() == (o + nxt).lower():
        return None, 'frag_right'                      # glori fy → glorify：要并词，不在这里做
    if o[-1:] in "'’" and v[-1:] not in "'’":
        return None, 'apos'                            # of' → of：撇号是不是真引号，看图
    j = b
    while j < len(text) and text[j] not in OKP and not text[j].isalpha():
        j += 1
    junk = text[b:j]
    if junk and j < len(text) and text[j].isalpha():
        return None, 'junk_join'                       # God^s / Chrisf9people：残渣连着下一个词
    vt, tt = trail(vs, vb), trail(ts, tb) if ts is not None else ''
    if lead:
        vq = vs[va - 1] if va > 0 and vs[va - 1] in QUOTE else ''
        tq = ts[tb0 - 1] if ts is not None and tb0 > 0 and ts[tb0 - 1] in QUOTE else ''
        if vq != tq and not (vq and tq):
            return None, 'lead_disagree'               # 残渣是不是开引号，两家说法不一
        if junk or (o.lower()[:-1] == v.lower() and o[-1:].lower() in 'yjs'):
            return None, 'lead_and_tail'               # 两头都有残渣，看图
        q = {'“': '"', '‘': "'"}.get(vq, vq)        # 本书一律直引号
        if i > 0 and text[i - 1] in QUOTE:
            q = ''                                     # 引号已在残渣前面（"/or → "for），不再补
        return (lead + o, q + v), ''
    if junk:
        if vt[:1] != tt[:1]:
            return None, 'punct_disagree'              # 残渣是不是标点，两家说法不一
        return (o + junk, v + vt[:1]), ''
    if len(o) == len(v) + 1 and o.lower().endswith(v.lower()) and va > 0 and vs[va - 1] in "'‘":
        return (o, "'" + v), ''                        # 诗行省音 'gainst 的撇号读成了 A
    agree_p = vt[:1] and vt[:1] == tt[:1] and text[b:b + 1] not in PUNCT
    if o.lower()[:-1] == v.lower():
        # 多出的词尾是标点读错（deaths to → death, to；himP → him?）：两家都要在这里有同一个标点
        if agree_p:
            return (o, v + vt[:1]), ''
        if o[-1:].lower() in 'yjs':
            return None, 'tail_nopunct'
        return (o, v), ''
    if agree_p and o[-1:].lower() in 'yjs':
        return (o, v + vt[:1]), ''                     # tiSy → us,
    return (o, v), ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rules', action='store_true')
    a = ap.parse_args()
    lex = build() | foote_kjv_words()
    W = lambda w: is_word(w, lex) or is_word(w.replace('’', "'"), lex)
    stat, skip = Counter(), Counter()
    rows, rules, pend = [], [], []
    for vol in (1, 2, 3):
        if not (VLM / f'v{vol}').exists():
            continue
        pn = leaf_pages(vol)
        segs = page_segments(vol)
        texts = {lec: (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8') for lec in LECS[vol]}
        # 锚按整讲的词序取（与 adjudicate.apply 同口径），不按本页——页首的词前三词在上一页
        ltoks = {lec: A.body_tokens(t) for lec, t in texts.items()}
        lidx = {lec: {ta: k for k, (ta, _, _) in enumerate(tk)} for lec, tk in ltoks.items()}
        for f in sorted((VLM / f'v{vol}').glob('*.txt')):
            leaf = int(f.stem)
            pg = pn.get(leaf, '')
            if pg not in segs:
                stat['页对不上'] += 1
                continue
            ours = []
            for lec, s, e in segs[pg]:
                for (ts_, te_, t) in A.body_tokens(texts[lec][s:e]):
                    ours.append((lec, s + ts_, s + te_, t))
            ow = [t for *_, t in ours]
            vs = clean_vlm(f.read_text(encoding='utf-8'))
            vt = vtoks(vs)
            tf = TESS / f'v{vol}' / f'{leaf:04d}.txt'
            tsx = tf.read_text(encoding='utf-8') if tf.exists() else ''
            tt = [(m.start(), m.end(), m.group(0)) for m in TOKEN.finditer(tsx)]
            vm = align_map(ow, [x[2] for x in vt])
            tm = align_map(ow, [x[2] for x in tt])
            stat['页'] += 1
            for i, (lec, s, e, o) in enumerate(ours):
                vi = vm.get(i)
                if vi is None:
                    continue
                va, vb, v = vt[vi]
                if v == SENT:
                    continue
                v = v.replace('’', "'")                # 本书一律直撇号，证人的弯撇号不算分歧
                if v.lower() == o.lower().replace('’', "'"):
                    continue
                ti = tm.get(i)
                t = tt[ti][2] if ti is not None else None
                if 'æ' in v.lower() or 'œ' in v.lower():
                    continue                   # 只差 æ/œ 连写（Caesar/Cæsar），不动
                ow_ok, vw_ok = W(o), W(v)
                if t and t.lower() == v.lower() and not ow_ok:
                    kind = 'agree3'            # 两家一致即可，判词典不认的人名也收（Satuminus→Saturninus）
                elif not vw_ok:
                    kind = 'vlm_nonword'
                elif t and t.lower() == v.lower():
                    if not ow_ok:
                        kind = 'agree3'
                    elif SequenceMatcher(None, o.lower(), v.lower()).ratio() >= 0.5:
                        kind = 'realword3'
                    else:
                        kind = 'realword3_far'
                elif not ow_ok:
                    kind = 'vlm_only'
                else:
                    kind = 'keep'          # 我们是真词、tess 不支持 vlm → vlm 多半读错，不动
                stat[kind] += 1
                k = lidx[lec][s]
                lw = [t for *_, t in ltoks[lec]]
                for na in range(3, 9):                 # 本讲里同词同三词锚的有好几处时，锚往前加长到唯一
                    anchor = ' '.join(lw[max(0, k - na):k])
                    if sum(1 for j in range(len(lw)) if lw[j] == o and ' '.join(lw[max(0, j - na):j]) == anchor) == 1:
                        break
                text = texts[lec]
                ctx = text[max(0, s - 50):e + 40].replace('\n', ' ')
                note = ''
                if kind == 'agree3' and not vw_ok and not v[:1].isupper():
                    kind = 'agree3_nonword'        # 两家读出同一个非词（nbt）：不落
                    stat['agree3'] -= 1
                    stat[kind] += 1
                if kind in ('agree3', 'realword3'):
                    nxt = ours[i + 1][3] if i + 1 < len(ours) and ours[i + 1][0] == lec else ''
                    r, why = make_rule(text, s, e, o, v, vs, va, vb,
                                       tsx if ti is not None else None, tt[ti][0] if ti is not None else 0,
                                       tt[ti][1] if ti is not None else 0, nxt)
                    if r:                              # 同锚同改的多条＝本讲里同形的几处，apply 按条数一起落
                        rules.append((f'{lec:03d}', anchor, r[0], r[1]))
                    else:
                        skip[why] += 1
                        note = why
                        pend.append((f'{lec:03d}', vol, leaf, pg, anchor, o, v, why, ctx))
                rows.append((f'{lec:03d}', vol, leaf, pg, anchor, o, v, t or '', kind, note, ctx))
    with open(LOG, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['lecture', 'vol', 'leaf', 'page', 'anchor', 'ours', 'vlm', 'tess', 'kind', 'skip', 'ctx'])
        w.writerows(rows)
    print(dict(stat), file=sys.stderr)
    print('守卫挡下', dict(skip), file=sys.stderr)
    if a.rules:
        RULES.write_text('# lecture\tanchor(前三词)\tfrom(词＋紧粘残渣)\tto —— foote_vlm_adjudicate.py 生成（agree3/realword3），须逐条看过\n'
                         + ''.join('\t'.join(r) + '\n' for r in rules), encoding='utf-8')
        print(f'规则 {len(rules)} 条 → {RULES}', file=sys.stderr)


if __name__ == '__main__':
    main()
