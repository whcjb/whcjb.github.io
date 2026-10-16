#!/usr/bin/env python3
"""TCP 录入错候选：低频词换一个形近字母 → 书中常见词（old-book-ocr 第 ① 层：语料自证）。

    python3 scripts/perkins_confusion.py            # 列出候选 → perkins_raw/galatians/confusion_cands.json

只列候选，不改字。落盘须逐条对 1604 影像（第 ③ 层）——印本自身的排印错（`religon`）
也会被列出来，那是原书原样，不改。
混淆对取录入员读 1604 罗马体最常混的：ſ/f（双向：f 录成 s 也有，通读第 1 章发现 `insringe`）、c/e、n/u、m/rn、i/l、h/b、t/r。
"""
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perkins_common as pc  # noqa: E402

PAIRS = [('f', 's'), ('s', 'f'), ('c', 'e'), ('e', 'c'), ('n', 'u'), ('u', 'n'), ('rn', 'm'), ('m', 'rn'),
         ('l', 'i'), ('i', 'l'), ('b', 'h'), ('h', 'b'), ('t', 'r'), ('r', 't'), ('o', 'e'), ('e', 'o')]


def main():
    docs = {f.stem: pc.load(f.stem) for f in pc.SRC.glob('*.md')}
    plain = {}
    c = collections.Counter()
    for k, md in docs.items():
        t = re.sub(r'<span class="pk-margin".*?</span>', ' ', md)
        t = re.sub(r'<[^>]+>', ' ', t).replace('*', ' ')
        plain[k] = t
        c.update(w.lower() for w in re.findall(r'[A-Za-z]+', t))
    out = []
    for k, t in plain.items():
        for m in re.finditer(r'[A-Za-z]+', t):
            w = m.group(0)
            lw = w.lower()
            if c[lw] > 1 or len(lw) < 4:
                continue
            best = None
            for a, b in PAIRS:
                for i in range(len(lw)):
                    if lw.startswith(a, i):
                        v = lw[:i] + b + lw[i + len(a):]
                        if c[v] >= 3 and (best is None or c[v] > best[1]):
                            best = (v, c[v])
            if best:
                L = t[:m.start()].split()[-8:]
                R = t[m.end():].split()[:8]
                out.append({'slug': k, 'w': w, 'to': best[0], 'n': best[1], 'left': L, 'right': R})
    (pc.RAW / 'confusion_cands.json').write_text(json.dumps(out, ensure_ascii=False, indent=0) + '\n',
                                                 encoding='utf-8')
    print(f'{len(out)} 个候选', file=sys.stderr)
    for o in out:
        print(f"{o['slug']:10s} {o['w']:16s} → {o['to']:16s} ({o['n']})  …{' '.join(o['left'][-4:])} [{o['w']}] {' '.join(o['right'][:4])}")


if __name__ == '__main__':
    main()
