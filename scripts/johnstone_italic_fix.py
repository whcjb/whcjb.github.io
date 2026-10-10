#!/usr/bin/env python3
"""斜体边界：拿第三证人把多标/少标的那一两个词修回去。

**为什么敢信证人**：抽样回影像定夺过两处，印面都是只有一个词是斜体
（`‘ *Sanctify* them through`、`was of *pure* Jewish blood`），而我们各多标
了一个词。这跟实现机制也对得上 —— `_par_italic` 的「外侧卡」在左锚点没对上
时会往前多吃一个词。两方独立读同一张图，证人在**范围**上比我们准。

**闸**：只处理「一侧是另一侧的前缀或后缀、且只差 1–2 个词」的分歧。
词序不同、差三个词以上的一律不碰——那多半是对位本身错了。
输出是**逐字面的替换**（星号位置要动，不能走归一化那条路）。

    python3 scripts/johnstone_italic_fix.py            # 试跑
    python3 scripts/johnstone_italic_fix.py --write
"""
import argparse
import difflib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alexander_abbyy as A
import extract_johnstone as E
import johnstone_page_proofread as P
import johnstone_vlm_diff as V

ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'en_chapters')
TBL = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'manual_italic.tsv')
VLM = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'src', 'vlm')
RUN = re.compile(r'\*([^*]{1,200})\*')


def words(s):
    return [w.strip("'’‘").lower() for w in V.WORD.findall(s)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    ab = A.parse_pages(E.load_xml())
    ocr = E.ocr_pages()
    for lf in E.drop_duplicate_leaves(ocr):
        del ocr[lf]
    first, shapes = E.learn_heads(ocr)
    whole = P.published()
    w_words, w_pos = [], []
    for m in P.WORD.finditer(whole):
        w_words.append(m.group(0)); w_pos.append((m.start(), m.end()))

    texts = {f: open(os.path.join(SRC, f), encoding='utf-8').read()
             for f in os.listdir(SRC) if f.endswith('.md')}
    rows, skip = [], 0
    for fn in sorted(int(f[:-4]) for f in os.listdir(VLM) if f.endswith('.txt')):
        vt = V.clean_vlm(open(os.path.join(VLM, f'{fn:04d}.txt'),
                              encoding='utf-8').read())
        raw = E.page_text([p['text'] for p in ab[fn]['pars']], ocr[fn],
                          first.get(fn, ''), shapes)
        ours = P.slice_for(raw, whole, w_words, w_pos)
        if not ours:
            continue
        ours = P.strip_markup(ours)
        oi = [(m.group(0), words(m.group(1))) for m in RUN.finditer(ours)]
        vi = [words(m.group(1)) for m in RUN.finditer(vt)]
        sm = difflib.SequenceMatcher(
            None, [' '.join(x[1]) for x in oi], [' '.join(x) for x in vi],
            autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != 'replace' or (i2 - i1) != 1 or (j2 - j1) != 1:
                continue
            lit, ow = oi[i1]
            vw = vi[j1]
            if not ow or not vw or ow == vw:
                continue
            # 只认「前缀 / 后缀」关系，且差 1–2 个词
            # 两个方向都要认。早先只写了「我们多标」一向，
            # 「我们少标」（`christ jesus` vs `in christ jesus`）整类漏掉。
            if len(ow) > len(vw) and ow[len(ow) - len(vw):] == vw:
                drop, side = len(ow) - len(vw), 'head'
            elif len(ow) > len(vw) and ow[:len(vw)] == vw:
                drop, side = len(ow) - len(vw), 'tail'
            elif len(vw) > len(ow) and vw[len(vw) - len(ow):] == ow:
                drop, side = len(vw) - len(ow), 'grow-head'
            elif len(vw) > len(ow) and vw[:len(ow)] == ow:
                drop, side = len(vw) - len(ow), 'grow-tail'
            else:
                skip += 1; continue
            if drop > 2:
                skip += 1; continue
            if side.startswith('grow'):
                # 往外扩：把紧邻的 drop 个词圈进来。只有当这些词确实就在
                # 字面两侧、且与证人给的词一致时才动。
                at = ours.find(lit)
                if at < 0:
                    skip += 1; continue
                if side == 'grow-head':
                    pre = ours[:at]
                    mm = list(V.WORD.finditer(pre))
                    if len(mm) < drop:
                        skip += 1; continue
                    if [m.group(0).strip("'’‘").lower() for m in mm[-drop:]] \
                            != vw[:drop]:
                        skip += 1; continue
                    start = mm[-drop].start()
                    old = ours[start:at + len(lit)]
                    new = '*' + ours[start:at].rstrip() + ' ' + lit[1:]
                else:
                    post = ours[at + len(lit):]
                    mm = list(V.WORD.finditer(post))
                    if len(mm) < drop:
                        skip += 1; continue
                    if [m.group(0).strip("'’‘").lower() for m in mm[:drop]] \
                            != vw[-drop:]:
                        skip += 1; continue
                    end = at + len(lit) + mm[drop - 1].end()
                    old = ours[at:end]
                    new = lit[:-1] + ours[at + len(lit):end] + '*'
                if sum(t.count(old) for t in texts.values()) != 1:
                    skip += 1; continue
                hits = [f for f, t in texts.items() if t.count(old) == 1]
                rows.append((hits[0], str(fn), old, new))
                continue
            inner = lit[1:-1]
            ws = list(V.WORD.finditer(inner))
            if len(ws) < drop + 1:
                skip += 1; continue
            if side == 'head':
                cut = ws[drop].start()
                new = inner[:cut] + '*' + inner[cut:] + '*'
            else:
                cut = ws[len(ws) - drop].start()
                new = '*' + inner[:cut].rstrip() + '*' + inner[cut - (len(inner[:cut]) - len(inner[:cut].rstrip())):]
            hits = [f for f, t in texts.items() if t.count(lit) == 1]
            if sum(t.count(lit) for t in texts.values()) != 1:
                skip += 1; continue
            rows.append((hits[0], str(fn), lit, new))

    print(f'可修 {len(rows)} 处，跳过 {skip} 处')
    for r in rows[:14]:
        print(f'  {r[0]:13s} leaf {r[1]:>4s}  {r[2][:52]}\n  {"":13s}           → {r[3][:52]}')
    if a.write:
        with open(TBL, 'w', encoding='utf-8') as fh:
            fh.write('# 斜体边界修正（第三证人）。每行：文件\tleaf\t原样\t改后\n')
            fh.write('# **逐字面替换**，星号位置要动，不能走归一化那条路。\n')
            for r in rows:
                fh.write('\t'.join(r) + '\n')
        print(f'→ {TBL}')


if __name__ == '__main__':
    main()
