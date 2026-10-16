#!/usr/bin/env python3
"""他版证人：1607 / 1617 重排本（IA EEBO 缩微）按位置判读 1604 缺字。

    python3 scripts/perkins_otheredition.py build            # 两版 hOCR → leaves.json
    python3 scripts/perkins_otheredition.py match --ids 1,2  # 按上下文定位 → other_locs.json
    python3 scripts/perkins_otheredition.py sheets           # 下载对应页图、拼判读图

为什么要他版（old-book-ocr §1 第 ② 层 + PROVENANCE.md）：1604 那份缩微胶片上
有成片墨渍、页边旁注糊成一团——TCP 录入员就是对着这同一套影像判不出的，
再看一遍同一张图不会多出信息。1607、1617 是同一文本的重排本（不同排版、
不同的缩微拍摄），在同一句话的位置上给出独立读数。

两版之间可能有改写，所以他版读数只当**候选**：
  1. 位置：缺字两侧 TCP 上下文在他版 OCR 里按锚点投票对上（左右都要有票）；
  2. 字形：他版读数与 TCP 残字逐字母相容；
  3. 影像：裁他版影像，人工判读定夺（判读图上并排给出）。
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perkins_gapcrop as gc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'perkins_raw' / 'galatians'
EDS = {
    '1607': 'bim_early-english-books-1475-1640_a-commentarie-on-the-fiv_perkins-william_1607',
    '1617': 'bim_early-english-books-1475-1640_a-commentarie-or-exposit_perkins-william_1617',
}
OUT = RAW / 'other_locs.json'
RE_PAGE = re.compile(r'<div class="ocr_page" id="page_(\d+)"')
RE_WORD = re.compile(r'<span class="ocrx_word" id="[^"]+" title="bbox (\d+) (\d+) (\d+) (\d+);[^"]*">([^<]*)</span>')
RE_LINE = re.compile(r'<span class="ocr_line" id="([^"]+)"')


def wdir(ed):
    return RAW / f'witness_{ed}'


def build():
    for ed in EDS:
        text = (wdir(ed) / 'hocr.html').read_text(encoding='utf-8')
        starts = [m.start() for m in RE_PAGE.finditer(text)] + [len(text)]
        leaves = []
        for i in range(len(starts) - 1):
            chunk = text[starts[i]:starts[i + 1]]
            words = []
            line = None
            pos = 0
            for m in re.finditer(r'<span class="ocr_line" id="([^"]+)"|' + RE_WORD.pattern, chunk):
                if m.group(1):
                    line = m.group(1)
                    continue
                x0, y0, x1, y1, w = m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)
                w = html.unescape(w)
                words.append({'t': w, 'k': gc.fold(w), 'x': int(x0), 'y': int(y0),
                              'w': int(x1) - int(x0), 'h': int(y1) - int(y0), 'line': line})
            leaves.append(words)
        (wdir(ed) / 'leaves.json').write_text(json.dumps(leaves), encoding='utf-8')
        print(f'{ed}: {len(leaves)} 叶 {sum(map(len, leaves))} 词', file=sys.stderr)


_leaves = {}


def leaves(ed):
    if ed not in _leaves:
        _leaves[ed] = json.loads((wdir(ed) / 'leaves.json').read_text(encoding='utf-8'))
    return _leaves[ed]


from difflib import SequenceMatcher


def hits(ws, k):
    """k 在本叶 OCR 里的位置：3–4 字母要逐字相同；5 字母以上相似度 ≥0.75
    （他版 OCR 也读花：`Symbolic`/`Fheologia`）。"""
    out = []
    for j, w in enumerate(ws):
        x = w['k']
        if not x:
            continue
        if len(k) < 5:
            if x == k:
                out.append(j)
        elif abs(len(x) - len(k)) <= 3 and x[0] in (k[0], 's', 'f') and \
                SequenceMatcher(None, k, x).ratio() >= 0.75:
            out.append(j)
    return out


def vote(ws, L, R):
    """同 perkins_gapcrop.locate 的锚点投票（模糊比词）；返回 (分, 左锚, 右锚)。"""
    lv, rv = {}, {}
    for t, k in enumerate(L):
        if len(k) >= 3:
            for j in hits(ws, k):
                lv.setdefault(j + (len(L) - t), set()).add(j)
    for t, k in enumerate(R):
        if len(k) >= 3:
            for j in hits(ws, k):
                rv.setdefault(j - t, set()).add(j)
    best = None
    for g in set(lv) | {h - k for h in rv for k in range(5)}:
        ls = set().union(*[lv.get(g + d, set()) for d in (-1, 0, 1)])
        rs = set().union(*[rv.get(g + k, set()) for k in range(6)])
        if not ls or not rs:
            continue
        lj, rj = max(ls), min(rs)
        if rj <= lj or rj - lj > 8:
            continue
        sc = len(ls) + len(rs)
        if best is None or sc > best[0]:
            best = (sc, lj, rj)
    return best


def match(ids):
    sites = {s['id']: s for s in json.loads(gc.LOCS.read_text(encoding='utf-8'))}
    res = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
    for i in ids:
        s = sites[i]
        note = bool(s.get('in_note') and s.get('anchor'))
        if note:
            # 旁注：拿挂靠处正文定位（旁注在他版里排在同一处的页边），裁页边栏
            A = s['anchor']
            h = len(A) // 2
            L = [gc.fold(w) for w in A[:h]]
            R = [gc.fold(w) for w in A[h:]]
        else:
            L = [gc.fold(w) for w in s['left'][-12:]]
            R = [gc.fold(w) for w in s['right'][:12]]
        frac = int(s['facs']) * 2 / 755
        out = {}
        for ed in EDS:
            lv = leaves(ed)
            c = int(frac * len(lv))
            best = None
            for leaf in range(max(0, c - 30), min(len(lv), c + 30)):
                b = vote(lv[leaf], L, R)
                if b and (best is None or b[0] > best[0]):
                    best = (b[0], leaf, b[1], b[2])
            if not best or best[0] < MIN_SCORE:
                continue
            sc, leaf, lj, rj = best
            ws = lv[leaf]
            if note:
                # 页已由正文锚点定下；旁注在页上的位置用**旁注自己的词**找
                # （只用正文行的 y 去猜，左右栏、上下行都常错——ed_009~012 几乎全空）
                nw = [gc.fold(w) for w in s['left'] + s['right'] if len(gc.fold(w)) >= 4]
                bestn = None
                for lf in (leaf - 1, leaf, leaf + 1):
                    if not (0 <= lf < len(lv)):
                        continue
                    pts = [lv[lf][j] for k in nw for j in hits(lv[lf], k)]
                    if len(pts) >= max(1, min(2, len(nw))) and (bestn is None or len(pts) > len(bestn[1])):
                        bestn = (lf, pts)
                if not bestn:
                    continue
                lf, pts = bestn
                ys = sorted(w['y'] for w in pts)
                xs = sorted(w['x'] for w in pts)
                cy, cx = ys[len(ys) // 2], xs[len(xs) // 2]
                out[ed] = {'leaf': lf, 'score': sc + len(pts), 'mid': f'(note words {len(pts)})',
                           'box': [cx - 500, cy - 260, cx + 700, cy + 420], 'native': True}
            else:
                mid = ws[lj + 1:rj]
                span = ws[max(0, lj - 3):rj + 4]
                out[ed] = {'leaf': leaf, 'score': sc, 'mid': ' '.join(w['t'] for w in mid),
                           'box': [min(w['x'] for w in span), min(w['y'] for w in span),
                                   max(w['x'] + w['w'] for w in span), max(w['y'] + w['h'] for w in span)]}
        res[str(i)] = out
        print(f"#{i} {s['tcp'][:70]!r} → " + '  '.join(f"{ed}:{v['mid']!r}(L{v['leaf']},{v['score']})"
                                                       for ed, v in out.items()), file=sys.stderr)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=0) + '\n', encoding='utf-8')


def fetch(ed, leaf):
    ID = EDS[ed]
    d = wdir(ed) / 'jp2'
    d.mkdir(exist_ok=True)
    p = d / f'{leaf:04d}.jp2'
    if not p.exists() or p.stat().st_size < 1000:
        import subprocess
        subprocess.run(['curl', '-sL', '--retry', '3', '-o', str(p),
                        f'https://archive.org/download/{ID}/{ID}_jp2.zip/{ID}_jp2%2F{ID}_{leaf:04d}.jp2'],
                       check=True)
    return p


ONLY = set()
# 实测 3–4 分的匹配大半落到别段（ed_004 五条错四条），收紧到 5
MIN_SCORE = 5


def sheets(ids, per=4, width=1500):
    """同一处影像（同版同叶、框重叠）上的几处缺字合成一条，免得一张图看几遍。"""
    sites = {s['id']: s for s in json.loads(gc.LOCS.read_text(encoding='utf-8'))}
    res = json.loads(OUT.read_text(encoding='utf-8'))
    for f in gc.SHEETS.glob('ed_*.jpg'):
        f.unlink()
    groups = []
    for i in ids:
        r = res.get(str(i))
        if not r:
            continue
        ed0 = sorted(r)[0]
        key = (ed0, r[ed0]['leaf'], r[ed0]['box'][1] // 250)
        if groups and groups[-1][0] == key:
            groups[-1][1].append(i)
        else:
            groups.append((key, [i]))
    n = 0
    for k in range(0, len(groups), per):
        rows = []
        for key, gid in groups[k:k + per]:
            for i in gid:
                s = sites[i]
                head = np.full((34, width), 255, np.uint8)
                cv2.putText(head, f"#{i} {s['kind']} {'NOTE ' if s['in_note'] else ''}{gc.ascii_safe(s['tcp'])[:115]}",
                            (6, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.68, 0, 2)
                rows.append(head)
            cand = res[str(gid[0])]
            # 只出分最高的那一版：同一处两版都看是重复劳动
            top = max(cand, key=lambda e: cand[e]['score'])
            for ed, v in cand.items():
                if ed != top or (ONLY and ed not in ONLY):
                    continue
                im = cv2.imread(str(fetch(ed, v['leaf'])), cv2.IMREAD_GRAYSCALE)
                H, W = im.shape
                x0, y0, x1, y1 = v['box']
                pad = 0 if v.get('native') else 40
                c = im[max(0, y0 - pad):min(H, y1 + pad), max(0, x0 - pad):min(W, x1 + pad)]
                if c.size == 0:
                    continue
                sc = min(1.0, width / c.shape[1])
                c = cv2.resize(c, (int(c.shape[1] * sc), int(c.shape[0] * sc)), interpolation=cv2.INTER_AREA)
                if c.shape[1] < width:
                    c = np.hstack([c, np.full((c.shape[0], width - c.shape[1]), 255, np.uint8)])
                lab = np.full((26, width), 255, np.uint8)
                cv2.putText(lab, f"{ed} leaf {v['leaf']}  ocr: {gc.ascii_safe(v['mid'])[:90]}", (6, 19),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, 90, 1)
                rows += [lab, c]
            rows.append(np.full((14, width), 160, np.uint8))
        cv2.imwrite(str(gc.SHEETS / f'ed_{k // per:03d}.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
        n += 1
    print(f'{sum(len(g) for _, g in groups)} 条 / {len(groups)} 处影像 → {n} 张他版判读图', file=sys.stderr)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build', 'match', 'sheets'])
    ap.add_argument('--ids', default='')
    ap.add_argument('--per', type=int, default=4)
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    ids = [int(x) for x in a.ids.split(',') if x]
    ONLY = set(x for x in a.only.split(',') if x)
    if a.cmd == 'build':
        build()
    elif a.cmd == 'match':
        match(ids)
    else:
        sheets(ids, a.per)
