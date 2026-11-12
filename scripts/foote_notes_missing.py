#!/usr/bin/env python3
"""福特《路加福音讲义》注区看图·整页丢失的脚注：转录记了 [FN:] 行、我们全卷没有该页任何 NOTE 条的页。

2026-11-12 普查：有脚注的 915 页里 136 页（228 条）在我们文本里整页没有注（抽取时丢的，如第 1 讲
`Nicephorus (Callistus) is the first who mentions it…`）。foote_notes_check 只核已有的 NOTE 块，问不到这些。

  题：该页注区，A＝tess 在注区那几行的逐词读法（第二份读法，只作对照），B＝转录 [FN:] 行。一页图只看一次。
  落：只落答 B，按页序插进该讲注区（没有注区的讲新开 `---`）；注号 `*` 写 ♦，余照转录。
  不问：转录带 [?]、该页跨两讲（归属不明）、注文已在本讲正文里（卷进正文的另行处理）、定位不到注区行。
  希腊/希伯来文的页不问，列 notes_missing_greek.tsv 待用户同意。

    python3 scripts/foote_notes_missing.py --collect
    python3 scripts/foote_notes_missing.py --run --sample 3 | --run --all
    python3 scripts/foote_notes_missing.py --rules      # → notes_missing_fixes.tsv
    python3 scripts/foote_notes_missing.py --apply      # 链条：notes_check 之后
"""
import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_image_check as I  # noqa: E402
import foote_notes_check as N  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402

N.CAND = N.WORK / 'notes_missing_candidates.json'
N.ANS = N.WORK / 'notes_missing_answers'
N.RULES = N.RAW / 'notes_missing_fixes.tsv'
N.LOG = A.ROOT / 'logs' / 'foote_notes_missing.tsv'
N.COST = A.ROOT / 'logs' / 'foote_notes_missing_cost.tsv'
GREEK = N.RAW / 'notes_missing_greek.tsv'
NOTE = re.compile(r'<!-- NOTE p\.(\S+) -->')


def letters(t):
    return re.sub(r'[^a-z]', '', t.lower())


def tess_notes(vol, leaf, box):
    """tess_grc 逐词框落在 box 里的词，按行拼回（A 读法）。"""
    f = N.RAW / 'tess_grc' / f'v{vol}' / f'{leaf:04d}.tsv'
    lines = {}
    for r in list(csv.reader(open(f, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))[1:]:
        if len(r) >= 12 and r[0] == '5' and r[11].strip():
            x, y = int(r[6]), int(r[7])
            if box[0] - 5 <= x <= box[2] and box[1] - 5 <= y <= box[3]:
                lines.setdefault((r[2], r[3], r[4]), []).append(r[11])
    return ' ¦ '.join(' '.join(w) for w in lines.values())


def collect():
    pages, skip, greek = [], Counter(), []
    for vol in (1, 2, 3):
        pn = V.leaf_pages(vol)
        segs = V.page_segments(vol)
        have = set()
        texts = {}
        for lec in V.LECS[vol]:
            texts[lec] = (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8')
            have |= set(NOTE.findall(texts[lec]))
        for lf, pg in sorted(pn.items()):
            vn = N.vlm_notes(vol, lf)
            if not vn or str(pg) in have:
                continue
            lecs = sorted({s[0] for s in segs.get(pg, [])})
            if len(lecs) != 1:
                skip['跨讲/无归属'] += 1
                continue
            lec = lecs[0]
            v = N.show_vlm(vn)
            if any('[?]' in t for _, t in vn):
                skip['转录读不出'] += 1
                continue
            body = letters(texts[lec].partition('\n---\n')[0])
            if all(len(letters(t)) >= 12 and letters(t)[:25] in body for _, t in vn):
                skip['已在正文'] += 1
                continue
            if N.GRK.search(v):
                greek.append((f'{lec:03d}', pg, vol, lf, v))
                continue
            bx = N.box_for(vol, lf, vn)
            if not bx:
                skip['定位不到'] += 1
                continue
            pages.append({'vol': vol, 'leaf': lf, 'qs': [{
                'kind': 'notes-missing', 'lec': f'{lec:03d}', 'page': str(pg), 'ours': tess_notes(vol, lf, bx) or '(nothing)',
                'vlm': v, 'vn': vn, 'greek': False, 'box': bx, 'ctx': f'footnotes of p. {pg}'}]})
    N.WORK.mkdir(parents=True, exist_ok=True)
    N.CAND.write_text(json.dumps(pages, ensure_ascii=False, indent=0), encoding='utf-8')
    with open(GREEK, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['lecture', 'page', 'vol', 'leaf', 'vlm(转录，含希腊/希伯来文，未问未落，待用户同意)'])
        w.writerows(greek)
    print(f'整页缺注题 {len(pages)}  希腊另列 {len(greek)}  跳过 {dict(skip)} → {N.CAND}', file=sys.stderr)


def pg_num(p):
    m = re.match(r'\d+', p)
    return int(m.group()) if m else 0


def insert_row(text, pg, block):
    """注条插进注区的（原串, 改作）：接在页码 ≤ pg 的最后一条之后；没有就接在 `---` 之后；没有注区就文末新开。
    一律「接在前一条之后」：同一处连插几页时，后插的接在先插的后面，各条改作都还在文中——二跑认得出已落过。"""
    body, sep, notes = text.partition('\n---\n')
    if not sep:
        old = text.rstrip('\n')[-60:]
        return old, old + '\n\n---\n\n' + block
    ents = [(m.start(), m.group(1)) for m in re.finditer(r'<!-- NOTE p\.(\S+) -->', notes)]
    prev = [s for s, p in ents if pg_num(p) <= pg_num(pg)]
    if prev:
        s = prev[-1]
        e = notes.find('\n', s)
        line = notes[s:e if e >= 0 else len(notes)]
        return line, line + '\n\n' + block
    return '\n---\n\n', '\n---\n\n' + block + '\n\n'


def rules():
    pages = json.loads(N.CAND.read_text(encoding='utf-8'))
    got = N.answered()
    rows, add = [], {}
    for p in pages:
        q = p['qs'][0]
        a = got.get(N.qkey(q))
        v = 'unasked' if a is None else N.verdict(q, a)
        rows.append((v, q['lec'], q['page'], q['ours'], q['vlm'], a or ''))
        if v == 'B':
            ent = '\n\n'.join(f"<!-- NOTE p.{q['page']} --> {N.SYM.get(s, s)} {t}".rstrip() for s, t in q['vn'])
            add.setdefault(q['lec'], []).append((q['page'], ent))
    out = []
    for lec, items in sorted(add.items()):
        text = (A.SRC / f'{lec}.md').read_text(encoding='utf-8')
        for pg, block in sorted(items, key=lambda x: pg_num(x[0])):
            old, new = insert_row(text, pg, block)
            if text.count(old) != 1:
                rows.append(('X', lec, pg, old[:60], block[:60], 'not-unique'))
                continue
            text = text.replace(old, new)
            out.append((lec, old, new))
    with open(N.LOG, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['verdict', 'lecture', 'page', 'tess', 'vlm', 'answer'])
        w.writerows(rows)
    N.RULES.write_text('# lecture\t原串\t改作 —— foote_notes_missing.py 生成（整页丢失的脚注，看图答 B＝转录，插入）；\\n 表换行\n'
                       + ''.join('\t'.join(x.replace('\n', '\\n') for x in r) + '\n' for r in out), encoding='utf-8')
    print(dict(Counter(r[0] for r in rows)), f'规则 {len(out)} → {N.RULES}', file=sys.stderr)


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
        N.run(a.sample, a.all)
    elif a.rules:
        rules()
    elif a.apply and N.RULES.exists():
        I.apply_multiline(N.RULES)


if __name__ == '__main__':
    main()
