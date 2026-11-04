#!/usr/bin/env python3
"""亚历山大《马太福音释义》脚注草稿：三份扫描本的 OCR 注文逐词投票。

主扫描本（gospelaccordingt00alex）的每条注，找另两份里最像的那条（前 80 字相似度 > 0.7），
三份逐词对齐，同位词取多数（三份各不相同时取主扫描本，记为分歧）。草稿只用来**对着原图核**，
不直接发布：注文最终以原图为准（memory feedback_page_image_is_final_authority）。

    python3 scripts/alexander_matthew_fndraft.py   → alexander_raw/matthew/work/footnotes_vote.tsv
    列：页 / 页内第几条 / 注号 / 投票稿 / 分歧词数 / 有无非 ASCII 或疑似希腊文残渣
"""
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_alexander_matthew as X  # noqa: E402


def notes_of(vol):
    X.VOLS = [vol]
    return X.ocr_stream()[2]


def vote(base, others):
    bw = base.split()
    cols = [[w] for w in bw]
    for o in others:
        ow = o.split()
        sm = SequenceMatcher(None, bw, ow, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal' or (tag == 'replace' and i2 - i1 == j2 - j1):
                for k in range(i2 - i1):
                    cols[i1 + k].append(ow[j1 + k])
    out, dis = [], 0
    for c in cols:
        w, n = Counter(c).most_common(1)[0]
        if n * 2 <= len(c) and len(c) > 1:
            w = c[0]
            dis += 1
        elif w != c[0]:
            dis += 1
        out.append(w)
    return ' '.join(out), dis


def main():
    vols = X.ITALIC_WITNESSES
    main_notes = notes_of(vols[0])
    others = {v: notes_of(v) for v in vols[1:]}
    rows, seen = [], Counter()
    for n in main_notes:
        seen[n['page']] += 1
        alts = []
        for v, ns in others.items():
            best = max(ns, key=lambda x: SequenceMatcher(None, n['text'][:80], x['text'][:80]).ratio())
            if SequenceMatcher(None, n['text'][:80], best['text'][:80]).ratio() > 0.7:
                alts.append(best['text'])
        txt, dis = vote(n['text'], alts)
        m = X.FOOTNOTE.match(txt)
        mark = (m.group(0).strip() if m else '')
        body = txt[m.end():] if m else txt
        odd = 'Y' if re.search(r'[^\x00-\x7f]|[{}^\\|]', body) else ''
        rows.append(f'{n["page"]}\t{seen[n["page"]]}\t{mark}\t{body}\t{dis}/{len(alts) + 1}\t{odd}')
    out = X.WORK / 'footnotes_vote.tsv'
    out.write_text('# 页\t页内第几条\t注号(OCR)\t投票稿\t分歧词/证人数\t疑似外文残渣\n' + '\n'.join(rows) + '\n',
                   encoding='utf-8')
    print(f'{len(rows)} 条 → {out}', file=sys.stderr)


if __name__ == '__main__':
    main()
