#!/usr/bin/env python3
"""亚历山大《马太福音释义》脚注转录工作单：每页列出 OCR 读到的注文草稿，和正文里疑似注号的位置
（换算成录入本上下文，供 footnotes.tsv 的「挂点」一栏用）。

    python3 scripts/alexander_matthew_fnplan.py 26 27 28     # 指定页
    python3 scripts/alexander_matthew_fnplan.py --all > work/fnplan.txt

疑似注号：OCR 正文词里带 * † ‡ §，或句末标点后粘着 t f X + %（† ‡ 常这样读坏）。只是线索，
逐条对着原图（alexander_matthew_fnsheets.py 出的图、或 crop_alexander_matthew.py 裁行）定。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_alexander_matthew as X  # noqa: E402

SUSPECT = re.compile(r'[*†‡§]|[.,;:)\]?!][\'"’”]?[tfX+%•]{1,2}[\'"’”.,;:)]*$')


def main():
    pages = json.loads((X.WORK / 'fn_pages.json').read_text())['pages'] if sys.argv[1:] == ['--all'] \
        else [int(x) for x in sys.argv[1:]]
    secs = X.load_pa()
    mtoks = [(si, pi, w) for si, s in enumerate(secs) for pi, p in enumerate(s['paras']) for w in p.split(' ')]
    body, heads, notes = X.ocr_stream()
    mi = [i for i, t in enumerate(mtoks) if X.key(t[2])]
    oi = [i for i, t in enumerate(body) if X.key(t[0])]
    pairs, _ = X.align([X.key(mtoks[i][2]) for i in mi], [X.key(body[i][0]) for i in oi])
    o2m = {oi[b]: mi[a] for a, b in pairs.items()}
    want = set(pages)
    for pg in pages:
        print(f'=== p{pg}')
        for n in [n for n in notes if n['page'] == pg]:
            print(f'  注 {n["text"][:220]}')
        for o, t in enumerate(body):
            if t[3] != pg or not SUSPECT.search(t[0]):
                continue
            j = next((x for x in range(o, max(o - 60, -1), -1) if x in o2m), None)
            if j is None:
                print(f'  号 {t[0]!r}  （对不上录入本）')
                continue
            m = o2m[j]
            ctx = ' '.join(x[2] for x in mtoks[max(m - 5, 0):m + 1])
            ch = secs[mtoks[m][0]].get('ch', '-')
            print(f'  号 {t[0]!r}  ch{ch}  …{ctx}')
    del want


if __name__ == '__main__':
    main()
