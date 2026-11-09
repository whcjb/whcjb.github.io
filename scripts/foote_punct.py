#!/usr/bin/env python3
"""福特《路加福音讲义》第 ③ 层·标点：逐「缝」判读（两词之间的标点、引号）。

第 45 讲逐字对图（PROVENANCE「抽查第 45 讲」）查出的 B/C/D/E/I/L 几类都在词缝里：
  开引号读成 `^^ '^ ''`、逗号读成 `^`、经文引语里逗号读成句号（`said. Send`）、收引号前的句点丢失（`done"*`）、
  段首多一个引号、逗号丢失（`individuals and`）。
词级判读（foote_vlm_adjudicate）只比词，这些看不见。

做法：同一页三条字流（我们 / tesseract / 整页转录）逐词对齐；**缝两侧的词三家都同位相等**时，比较缝里的标点：
  我们的缝（去空白、去斜体星号）≠ 转录的缝 == tesseract 的缝      → 候选：按转录改我们的标点，星号与 HTML 原位保留
其余（两家不一致、缝里有注号 / 读不出 / 页缝 / 数字字母）一律不动。转录只当证人：它与非生成式的 tesseract 一致才落。

    python3 scripts/foote_punct.py            # 统计 + logs/foote_punct.tsv
    python3 scripts/foote_punct.py --rules    # 另写 foote_raw/luke/punct_fixes.tsv（逐类看过再接链条）
    python3 scripts/foote_punct.py --apply    # 按表落（链条上排在 adjudicate --apply --vlm 之后）
"""
import argparse
import csv
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402

RAW = A.RAW
LOG = A.ROOT / 'logs' / 'foote_punct.tsv'
RULES = RAW / 'punct_fixes.tsv'
# 看图否决：两家一致但原图读不准或与印面不符的缝（讲次、锚、右词），生成时跳过
REJECT_F = RAW / 'punct_reject.tsv'
REJECT = {tuple(ln.split('\t')[:3]) for ln in (REJECT_F.read_text(encoding='utf-8').splitlines()
                                                if REJECT_F.exists() else []) if ln and not ln.startswith('#')}
TOKEN = A.TOKEN
FN = ''
OK = set(',.;:!?"\'()—-[]')                 # 允许落进产物的标点
NORM = str.maketrans({'“': '"', '”': '"', '‘': "'", '’': "'", '–': '-'})


def clean_vlm(t):
    """同 V.clean_vlm，但注号留成哨兵（缝里有注号的不判），读不出的 [?] 也留哨兵。"""
    lines = [ln for ln in t.splitlines() if not ln.startswith('[HEAD]')]
    body = []
    for ln in lines:
        if re.match(r'\s*\[FN:', ln):
            break
        body.append(ln)
    s = '\n'.join(body)
    s = re.sub(r'\[FN:[^\]]*\]', FN, s)
    s = re.sub(r'\[SIG:[^\]]*\]', ' ', s)
    s = s.replace('[?]', ' ' + V.SENT + ' ')
    return s


def core(g):
    """缝的比较口径：去空白、去斜体星号、引号直化、`--` 当破折号；转义星号 `\\*` 算一个字面字符。"""
    g = g.replace('\\*', ESC).translate(NORM).replace('--', '—')
    return re.sub(r'[\s*]', '', g)


ESC = '\ue002'                               # 转义星号 `\*`（字面星号＝读错的引号）当一个核心字符


def rebuild(gap, target):
    """把 gap 的核心字符改成 target，星号与空白原位保留。只动标点。"""
    gap = gap.replace('\\*', ESC)
    out = _rebuild(gap, target).replace(ESC, '\\*')
    if not re.search(r'\s', out):
        out = out + ' ' if out.strip('*') == out else out   # 删光了也得留一个空格，免得两词粘连
        if not re.search(r'\s', out):
            out = out.replace('*', '* ', 1) if out.startswith('*') is False else out + ' '
    return out


def _rebuild(gap, target):
    g = gap.translate(NORM)
    idx = [i for i, ch in enumerate(g) if not ch.isspace() and ch != '*']
    src = ''.join(g[i] for i in idx)
    out = list(gap)
    sm = SequenceMatcher(None, src, target, autojunk=False)
    edits = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            continue
        # 只删核心字符本身（中间夹着的星号、空白原位不动），新字符插在第一个被删字符的位置
        for k in idx[i1:i2]:
            edits.append((k, k + 1, ''))
        if j1 < j2:
            if i1 < i2:
                at = idx[i1]
            elif i1 > 0:
                at = idx[i1 - 1] + 1
            elif idx:
                at = idx[0]
            else:
                ins = target[j1:j2]
                at = (gap.rfind(' ') + 1 if '*' in gap else len(gap) - len(gap.lstrip(' '))) \
                    if ins[:1] in '"\'(' else 0
            edits.append((at, at, target[j1:j2]))
    for pos, end, rep in sorted(edits, key=lambda e: (e[0], e[1] - e[0]), reverse=True):
        out[pos:end] = list(rep)
    s = ''.join(out)
    # 开引号后不留「星号前的空白」之类的怪样：只收拾 `" ` + 词 的既有样式，不额外改空白
    return s


def page_pairs():
    """逐页给出 (讲, 我们的词列表, 我们文本, 转录串, 转录词, tess 串, tess 词)。"""
    for vol in (1, 2, 3):
        if not (V.VLM / f'v{vol}').exists():
            continue
        pn = V.leaf_pages(vol)
        segs = V.page_segments(vol)
        texts = {lec: (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8') for lec in V.LECS[vol]}
        for f in sorted((V.VLM / f'v{vol}').glob('*.txt')):
            leaf = int(f.stem)
            pg = pn.get(leaf, '')
            if pg not in segs:
                continue
            ours = []
            for lec, s, e in segs[pg]:
                for (ts_, te_, t) in A.body_tokens(texts[lec][s:e]):
                    ours.append((lec, s + ts_, s + te_, t))
            vs = clean_vlm(f.read_text(encoding='utf-8'))
            vt = [(m.start(), m.end(), m.group(0)) for m in V.VWORD.finditer(vs)]
            tf = V.TESS / f'v{vol}' / f'{leaf:04d}.txt'
            ts = tf.read_text(encoding='utf-8') if tf.exists() else ''
            tt = [(m.start(), m.end(), m.group(0)) for m in TOKEN.finditer(ts)]
            yield vol, leaf, texts, ours, vs, vt, ts, tt


def judge():
    stat = Counter()
    rows, rules = [], []
    for vol, leaf, texts, ours, vs, vt, ts, tt in page_pairs():
        ow = [t for *_, t in ours]
        vm = V.align_map(ow, [x[2] for x in vt])
        tm = V.align_map(ow, [x[2] for x in tt])
        eqv = lambda i: i in vm and vt[vm[i]][2].lower() == ow[i].lower()
        eqt = lambda i: i in tm and tt[tm[i]][2].lower() == ow[i].lower()
        ltoks = {}
        for i in range(len(ours) - 1):
            lec, s, e, o = ours[i]
            lec2, s2, e2, o2 = ours[i + 1]
            if lec2 != lec or not (eqv(i) and eqv(i + 1) and eqt(i) and eqt(i + 1)):
                continue
            if vm[i + 1] != vm[i] + 1 or tm[i + 1] != tm[i] + 1:
                continue                           # 证人在这道缝里多出 / 少了词
            text = texts[lec]
            gap = text[e:s2]
            vg = vs[vt[vm[i]][1]:vt[vm[i + 1]][0]]
            tg = ts[tt[tm[i]][1]:tt[tm[i + 1]][0]]
            if '<' in gap or '\n\n' in gap or FN in vg or V.SENT in vg or re.search(r'[A-Za-z0-9]', gap + vg):
                continue                           # 页缝 / 段缝 / 注号 / 读不出 / 缝里有字
            oc, vc, tc = core(gap), core(vg), core(tg)
            if oc == vc:
                continue
            stat['分歧'] += 1
            if vc != tc:
                stat['两家不一'] += 1
                continue
            if not set(vc) <= OK:
                stat['目标含怪字符'] += 1
                continue
            if re.search(r'[†‡§♦•]', gap):
                stat['我们缝里有注号'] += 1
                continue
            g2 = gap.replace('\\*', ESC)
            cp = [k for k, ch in enumerate(g2) if not ch.isspace() and ch != '*']
            if cp and '*' in g2[cp[0]:cp[-1]]:
                stat['星号夹在标点中间'] += 1      # 斜体边界落在哪个标点前后，看不出来：不动
                continue
            new = rebuild(gap, vc)
            if core(new) != vc:
                stat['重建失败'] += 1
                continue
            stat['候选'] += 1
            if lec not in ltoks:
                ltoks[lec] = A.body_tokens(text)
            lw = [t for *_, t in ltoks[lec]]
            k = next(j for j, (ta, _, _) in enumerate(ltoks[lec]) if ta == s)
            for na in range(3, 10):                # 本讲里同锚同右词的缝有几处时，锚往前加长到唯一
                anchor = ' '.join(lw[max(0, k - na + 1):k + 1])
                if sum(1 for j in range(len(lw) - 1) if lw[j + 1] == o2
                       and ' '.join(lw[max(0, j - na + 1):j + 1]) == anchor) == 1:
                    break
            if (f'{lec:03d}', anchor, o2) in REJECT:
                stat['看图否决'] += 1
                continue
            rows.append((f'{lec:03d}', vol, leaf, anchor, gap, new, o2, oc, vc, text[max(0, s - 40):e2 + 30].replace('\n', ' ')))
            rules.append((f'{lec:03d}', anchor, gap, new, o2))
    return stat, rows, rules


def apply():
    """落表：锚＝缝左三词（含左词），缝须逐字等于原缝、右词须等于记录的右词；本讲恰好一处。"""
    by = {}
    for ln in RULES.read_text(encoding='utf-8').splitlines():
        if ln.strip() and not ln.startswith('#'):
            lec, anchor, old, new, right = ln.split('\t')
            by.setdefault(lec, []).append((anchor, old.replace('\\n', '\n'), new.replace('\\n', '\n'), right))
    done = already = 0
    bad = []
    for lec, rs in by.items():
        path = A.SRC / f'{lec}.md'
        text = path.read_text(encoding='utf-8')
        for anchor, old, new, right in reversed(rs):
            toks = A.body_tokens(text)
            words = [t for *_, t in toks]
            n = len(anchor.split())
            hits, olds = [], []
            for k in range(n - 1, len(toks) - 1):
                if ' '.join(words[k - n + 1:k + 1]) != anchor or words[k + 1] != right:
                    continue
                g = text[toks[k][1]:toks[k + 1][0]]
                (hits if g == old else olds if g == new else []).append(k)
            if len(hits) == 1:
                k = hits[0]
                text = text[:toks[k][1]] + new + text[toks[k + 1][0]:]
                done += 1
            elif not hits and olds:
                already += 1
            else:
                bad.append((lec, anchor, old, len(hits)))
        path.write_text(text, encoding='utf-8')
    print(f'标点落盘 {done}；已落过 {already}；定位失败 {len(bad)} {bad[:5]}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rules', action='store_true')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    if a.apply:
        apply()
        return
    stat, rows, rules = judge()
    with open(LOG, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['lecture', 'vol', 'leaf', 'anchor', 'gap', 'new', 'right', 'ours', 'witness', 'ctx'])
        w.writerows(rows)
    print(dict(stat), file=sys.stderr)
    if a.rules:
        RULES.write_text('# lecture\tanchor(缝左三词)\told(缝)\tnew\tright(缝右词) —— foote_punct.py 生成，须逐类看过\n'
                         + ''.join('\t'.join(x.replace('\n', '\\n') for x in r) + '\n' for r in rules),
                         encoding='utf-8')
        print(f'规则 {len(rules)} 条 → {RULES}', file=sys.stderr)


if __name__ == '__main__':
    main()
