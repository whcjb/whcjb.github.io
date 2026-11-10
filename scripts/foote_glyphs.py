#!/usr/bin/env python3
"""福特《路加福音讲义》第 ③ 层·字形类：撇号丢失（G）、æ/œ 连写丢失（J）、跨行断词没接上（K）。

第 45 讲逐字对图查出、词级判读（foote_vlm_adjudicate）看不见的三类：
  G `Master s` —— 我们把 `'s` 的撇号丢了，拆成两个词；词级对齐 2 对 1，对不上。
  J `Caesar`   —— 印面是 æ 连写，ABBYY 拆成 ae；tesseract 也读不出 æ（全书 0 个），只有转录读得出。
  K `be- -lieveth` / `follow- ing` —— 行末连字符断词没接上，两半成了两个词。

    python3 scripts/foote_glyphs.py            # 统计 + logs/foote_glyphs.tsv（干跑，不动产物）
    python3 scripts/foote_glyphs.py --rules    # 另写 foote_raw/luke/glyph_fixes.tsv
    python3 scripts/foote_glyphs.py --apply    # 按表落（链条上排在 foote_punct.py --apply 之后）

K 不靠证人：断词多在页缝（转录本页止于 `de-`、下页起于 `fence`），三条字流都对不上。按全书语料定连不连：
  整词是真词、全书他处出现过、连字符形 0 次           → 并成一词（`follow- ing`→`following`）
  连字符形全书他处出现过、整词 0 次、两截都是真词      → 留连字符去空格（`self- righteous`→`self-righteous`）
  其余（两截有残字 `uni- Tcrsally`、破折号读成连字符 `against- God`、两样都没见过 `simple- hearted`）→ 不动，
  记 logs/foote_glyphs.tsv 的 K? 行待看。
"""
import argparse
import csv
import glob
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_punct as P  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402

LOG = A.ROOT / 'logs' / 'foote_glyphs.tsv'
RULES = A.RAW / 'glyph_fixes.tsv'
BREAK = re.compile(r"\b([A-Za-z]+)-[ \t]+-?([A-Za-z]+)\b")
LIG = str.maketrans({'æ': 'ae', 'Æ': 'Ae', 'œ': 'oe', 'Œ': 'Oe'})
APOS = str.maketrans({'’': "'"})
# 转录侧连 œ 一起认（VWORD 不含 œ，U+0153 在 Latin Extended-A）
VW = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿŒœ][A-Za-zÀ-ÖØ-öø-ÿŒœ'’]*|" + V.SENT)


def italic_mask(s, toks):
    """每个词是否在斜体里：从段首（空行）起数未转义星号的奇偶。"""
    out = []
    for a, _b, _w in toks:
        p = s.rfind('\n\n', 0, a)
        out.append(len(re.findall(r'(?<!\\)\*', s[max(p, 0):a])) % 2 == 1)
    return out


RUN = re.compile(r'(?<![\\*])\*(?=\S)([^*\n]+?)(?<=\S)(?<!\\)\*(?!\*)')


def unique_span(text, s, e, rep):
    """把 text[s:e]→rep 写成本讲唯一的整串规则：两头按词往外扩，直到原串在本讲只出现一次。"""
    a, b = s, e
    for _ in range(12):
        if text.count(text[a:b]) == 1:
            return text[a:b], text[a:s] + rep + text[e:b]
        a2 = text.rfind(' ', 0, max(a - 1, 0))
        b2 = text.find(' ', b + 1)
        a = 0 if a2 < 0 else a2
        b = len(text) if b2 < 0 else b2
        if '\n' in text[a:b] or '<' in text[a:b]:
            break
    return None


def judge():
    """G / J / H：逐页三条字流对齐。返回 (rows, edits)；edits＝[(讲, 起, 止, 改作, 类)]。"""
    rows, edits = [], []
    for vol, leaf, texts, ours, vs, _vt, ts, tt in P.page_pairs():
        vt = [(m.start(), m.end(), m.group(0)) for m in VW.finditer(vs)]
        ow = [t for *_, t in ours]
        vm = V.align_map(ow, [x[2].translate(LIG).translate(APOS) for x in vt])
        tm = V.align_map(ow, [x[2].translate(APOS) for x in tt])
        vit = italic_mask(vs, vt)
        for i, (lec, s, e, o) in enumerate(ours):
            text = texts[lec]
            ctx = text[max(0, s - 40):e + 40].replace('\n', ' ')
            # J：æ/œ —— 转录同位词去连写后与我们相同、且转录确有连写（tesseract 全书读不出 æ，只作参照；
            # 看图 3 处含 tesseract 读成平写 Caesar(s) 的两处，印面都是连写）
            if i in vm:
                v = vt[vm[i]][2]
                if v != v.translate(LIG) and v.translate(LIG).translate(APOS) == o:
                    rows.append(('J', f'{lec:03d}', vol, leaf, o, v, tt[tm[i]][2] if i in tm else '', ctx))
                    edits.append((lec, s, e, v.translate(APOS), 'J'))
            if i + 1 >= len(ours) or ours[i + 1][0] != lec:
                continue
            _l2, s2, e2, o2 = ours[i + 1]
            gap = text[e:s2]
            pv, nv = vm.get(i - 1), vm.get(i + 2)
            if gap != ' ' or o2 not in ('s', 't') or pv is None or nv is None or nv - pv != 2:
                continue
            v = vt[pv + 1][2].translate(APOS)
            pt, nt = tm.get(i - 1), tm.get(i + 2)
            tw = ''.join(x[2] for x in tt[pt + 1:nt]).translate(APOS) if pt is not None and nt is not None else ''
            # G：`X s` ← 转录 `X's`，且 tesseract 同位也读出 `X's`
            if v == o + "'" + o2:
                ok = tw == v
                rows.append(('G' if ok else 'G?', f'{lec:03d}', vol, leaf, o + gap + o2, v, tw, ctx))
                if ok:
                    edits.append((lec, s, e2, v, 'G'))
        # H：我们整段斜体（`*…*`），其中每个词都与转录同位、转录里一个也不是斜体 → 去掉这对星号
        idx = {(lec, s): i for i, (lec, s, _e, _o) in enumerate(ours)}
        for lec in {x[0] for x in ours}:
            text = texts[lec]
            lo = min(s for l_, s, *_ in ours if l_ == lec)
            hi = max(e for l_, _s, e, _o in ours if l_ == lec)
            for m in RUN.finditer(text, lo, hi):
                ins = [idx[(lec, s)] for (l_, s, e, _o) in ours if l_ == lec and m.start() < s < m.end()]
                if not ins or '<' in m.group(0):
                    continue
                if any(i not in vm for i in ins):
                    continue
                flags = [vit[vm[i]] for i in ins]
                if any(flags):
                    if not all(flags):
                        rows.append(('H?', f'{lec:03d}', vol, leaf, m.group(0), '', '',
                                     text[max(0, m.start() - 40):m.end() + 40].replace('\n', ' ')))
                    continue
                rows.append(('H', f'{lec:03d}', vol, leaf, m.group(0), m.group(1),
                             ' '.join(vt[vm[i]][2] for i in ins),
                             text[max(0, m.start() - 40):m.end() + 40].replace('\n', ' ')))
                edits.append((lec, m.start(), m.end(), m.group(1), 'H'))
    return rows, edits


def judge_breaks():
    """K：逐讲找 `A- B`，按全书语料定并词 / 留连字符 / 不动。返回 (rules, rows)。"""
    texts = {Path(f).stem: Path(f).read_text(encoding='utf-8') for f in sorted(glob.glob(str(A.SRC / '*.md')))}
    allt = ''.join(texts.values())
    cnt = lambda w: len(re.findall(r'(?<![A-Za-z-])' + re.escape(w) + r'(?![A-Za-z-])', allt, re.I))
    rules, rows = [], []
    for lec, text in texts.items():
        for m in BREAK.finditer(text):
            a, b = m.groups()
            old = m.group(0)
            joined, hyph = cnt(a + b), cnt(a + '-' + b)
            if A._isword(a + b) and joined and not hyph:
                new, cls = a + b, 'K'
            elif hyph and not joined and A._isword(a) and A._isword(b):
                new, cls = a + '-' + b, 'K-'
            else:
                rows.append(('K?', lec, '', '', old, f'joined={joined} hyph={hyph}', '',
                             text[max(0, m.start() - 40):m.end() + 40].replace('\n', ' ')))
                continue
            if text.count(old) != 1:
                rows.append(('K?', lec, '', '', old, new, 'not-unique', ''))
                continue
            rules.append((lec, old, new))
            rows.append((cls, lec, '', '', old, new, f'joined={joined} hyph={hyph}',
                         text[max(0, m.start() - 40):m.end() + 40].replace('\n', ' ')))
    return rules, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rules', action='store_true')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    if a.apply:
        A.apply_spans(RULES)
        return
    rows, edits = judge()
    krules, krows = judge_breaks()
    rows += krows
    # G/J/H 的落点按讲从后往前转成整串规则（同讲多处时各自扩到唯一；扩不到唯一的记 X 行不落）
    texts = {}
    grules = []
    edits = list({(x[0], x[1]): x for x in edits}.values())   # 跳过的页借上一页那截：同一落点只留一条
    for lec, s, e, rep, cls in sorted(edits, key=lambda x: (x[0], -x[1])):
        text = texts.setdefault(lec, (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8'))
        r = unique_span(text, s, e, rep)
        if not r:
            rows.append(('X' + cls, f'{lec:03d}', '', '', text[s:e], rep, 'not-unique', ''))
            continue
        grules.append((f'{lec:03d}', r[0], r[1]))
        texts[lec] = text[:s] + rep + text[e:]
    krules = grules + krules              # 不排序：同讲 G/J/H 按从后往前生成、须照此顺序落（后一条的唯一性依赖前一条已改）
    stat = Counter(r[0] for r in rows)
    with open(LOG, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['cls', 'lecture', 'vol', 'leaf', 'ours', 'vlm', 'tess', 'ctx'])
        w.writerows(rows)
    print(dict(stat), file=sys.stderr)
    if a.rules:
        # 与旧表合并：在已落过的产物上重跑判不出已改的那些，不能因此把旧规则丢掉
        old = [tuple(ln.split('\t')) for ln in (RULES.read_text(encoding='utf-8').splitlines()
                                                 if RULES.exists() else []) if ln and not ln.startswith('#')]
        # 旧条的原串已被上游改掉（020 `*\\ij*`，改字层把 \\ij 改成 by 了）、改作也不在的，丢掉
        def _alive(r):
            t = (A.SRC / f'{r[0]}.md').read_text(encoding='utf-8')
            return t.count(r[1]) == 1 or r[2] in t
        old = [r for r in old if _alive(r)]
        seen = {(r[0], r[1]) for r in old}
        krules = (old + [r for r in krules if (r[0], r[1]) not in seen
                               and not any(o[0] == r[0] and o[2] == r[1] for o in old)])
        RULES.write_text('# lecture\t原串(逐字)\t改作 —— foote_glyphs.py 生成（G 撇号 / J 连写 / H 多余斜体 / K 断词）\n'
                         + ''.join('\t'.join(r) + '\n' for r in krules), encoding='utf-8')
        print(f'规则 {len(krules)} 条 → {RULES}', file=sys.stderr)


if __name__ == '__main__':
    main()
