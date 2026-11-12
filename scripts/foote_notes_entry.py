#!/usr/bin/env python3
"""福特《路加福音讲义》注区逐条看图（2026-11-12 用户令「继续处理」）。

注区前几层都是整页一题（foote_notes_check / notes_fill）：一页里只要有一条对不上——转录那条带 [?]、我们首条是上页注的
续文（转录只记本页起头的注）、或整页答 A/other——整页就不落。剩下的注区残字约 258 处多在这些页上。

这层拆成逐条：该页我们的 NOTE 条与转录 [FN:] 条按序配对（我们比转录多出的首条视为上页续文，不配）；每对字不同、
且我们这条带残字的出一题：A＝我们这条，B＝转录这条（希腊字形照 foote_greek_notes 取第二读），转录带 [?] 的不问。
图：该页注区（同 notes_check 的裁法）。一页图只看一次。只落答 B，整行换掉（注号写法照 notes_check：* 作 ♦）。

    python3 scripts/foote_notes_entry.py --collect     # 链条位置：foote_line_check --apply --round 2 之后
    python3 scripts/foote_notes_entry.py --run --all
    python3 scripts/foote_notes_entry.py --rules       # → notes_entry_fixes.tsv
    python3 scripts/foote_notes_entry.py --apply
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
import foote_greek_notes as GN  # noqa: E402
import foote_image_check as I  # noqa: E402
import foote_junk_check as J  # noqa: E402
import foote_notes_check as N  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402

N.CAND = N.WORK / 'notes_entry_candidates.json'
N.ANS = N.WORK / 'notes_entry_answers'
N.RULES = N.RAW / 'notes_entry_fixes.tsv'
N.LOG = A.ROOT / 'logs' / 'foote_notes_entry.tsv'
N.COST = A.ROOT / 'logs' / 'foote_notes_entry_cost.tsv'
ORD = re.compile(r'\b\d+(st|nd|rd|th|d)\b')
LINE = re.compile(r'<!-- NOTE p\.(\S+) --> (.*)')

N.SYSTEM = N.SYSTEM.replace('two candidate transcriptions A and B of all footnotes on that page; " ¦ " separates one '
                            'footnote from the next, and each footnote starts with its reference mark',
                            'two candidate transcriptions A and B of ONE footnote on that page (the strip shows the whole '
                            'footnote area; find that footnote in it); the footnote starts with its reference mark')


def bad(t):
    return bool(J.BAD.search(ORD.sub('', t)))


def collect():
    sr = GN.second_reads()
    pages, skip, stat = [], Counter(), Counter()
    for vol in (1, 2, 3):
        pn = V.leaf_pages(vol)
        leaf_of = {}
        for lf, pg in sorted(pn.items()):
            leaf_of.setdefault(str(pg), lf)
        owner = defaultdict(set)
        blocks = {}
        for lec in V.LECS[vol]:
            text, bl = N.note_blocks(lec)
            for pg, b in bl.items():
                owner[pg].add(lec)
                blocks[(lec, pg)] = (text, b)
        for (lec, pg), (text, (s, e, ts)) in blocks.items():
            if len(owner[pg]) > 1 or pg not in leaf_of:
                continue
            lf = leaf_of[pg]
            vn = N.vlm_notes(vol, lf)
            if not vn:
                continue
            ours = [m for m in LINE.finditer(text, s, e)]
            if len(ours) == len(vn) + 1:
                ours = ours[1:]                     # 首条是上页注的续文，转录不记
            if len(ours) != len(vn):
                skip['条数不合'] += 1
                continue
            qs = []
            allm = [m for m in LINE.finditer(text, s, e)]
            for m, (sym, vt) in zip(ours, vn):
                o = m.group(2)
                k = [x.start() for x in allm].index(m.start())
                prev = allm[k - 1] if k else None
                if not bad(o):
                    continue
                if '[?]' in vt:
                    skip['转录读不出'] += 1
                    continue
                v = f"{N.SYM.get(sym, sym)} {GN.greekify(vt, sr.get((vol, lf), []), stat)}".replace('ȣ', 'ου')
                if N.key(o) == N.key(v):
                    continue
                ko, kv = re.sub(r'[^a-z0-9]', '', o.lower()), re.sub(r'[^a-z0-9]', '', vt.lower())
                grk = bool(re.search(r'[Ͱ-Ͽἀ-῿]', vt))
                r = SequenceMatcher(None, ko, kv, autojunk=False).ratio()
                lr = len(N.key(v)) / max(1, len(N.key(o)))
                if not (r >= 0.35 or (grk and 0.6 < lr < 1.6)) or lr < 0.7:
                    skip['配对不像'] += 1           # 条序错开、或我们把两条并成一行（Chateaubriand. t Richardson.）
                    continue
                # 同一条注被拆成两行：前一行是读花的希腊文开头（`*X Ourt ratv…`），这一行不以注号起头、是后半截，
                # 转录这条又以希腊文起头——两行一起换成转录这条（第 51、92 讲）
                merge = ''
                first = re.sub(r'[*\\]', '', o.split(' ', 1)[0])
                symlike = len(first) <= 2 and not A._isword(re.sub(r'[^a-z]', '', first.lower()) or 'zz')
                if prev is not None and bad(prev.group(2)) and not symlike \
                        and not re.match(r'\s*[♦†‡§‖¶•]', prev.group(2)) \
                        and re.match(r'\W*[Ͱ-Ͽἀ-῿]', vt) and not re.match(r'\s*[♦†‡§‖¶•]', o):
                    merge = prev.group(0) + '\n\n'
                qs.append({'kind': 'notes', 'lec': f'{lec:03d}', 'page': pg, 's': m.start(2), 'e': m.end(2), 'merge': merge,
                           'ours': o.replace(A.FN_MARK, ''), 'raw': o, 'vlm': v, 'vn': [[sym, vt]], 'greek': False,
                           'ctx': f'one footnote of p. {pg}'})
            if not qs:
                continue
            box = N.box_for(vol, lf, vn)
            if not box:
                skip['定位不到'] += 1
                continue
            for q in qs:
                q['box'] = box
            pages.append({'vol': vol, 'leaf': lf, 'qs': qs})
    N.WORK.mkdir(parents=True, exist_ok=True)
    N.CAND.write_text(json.dumps(pages, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'题 {sum(len(p["qs"]) for p in pages)}  页 {len(pages)}  跳过 {dict(skip)} → {N.CAND}', file=sys.stderr)


def rules():
    pages = json.loads(N.CAND.read_text(encoding='utf-8'))
    got = N.answered()
    rows, out = [], []
    for p in pages:
        for q in p['qs']:
            a = got.get(N.qkey(q))
            v = 'unasked' if a is None else N.verdict(q, a)
            rows.append((v, q['lec'], q['page'], q['ours'], q['vlm'], a or ''))
            if v != 'B':
                continue
            o = q.get('merge', '') + f"<!-- NOTE p.{q['page']} --> {q['raw']}"
            n = f"<!-- NOTE p.{q['page']} --> {q['vlm']}" + A.FN_MARK * q['raw'].count(A.FN_MARK)
            t = (A.SRC / f"{q['lec']}.md").read_text(encoding='utf-8')
            if t.count(o) != 1:
                rows[-1] = ('X-not-unique',) + rows[-1][1:]
                continue
            out.append((q['lec'], o, n))
    with open(N.LOG, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['verdict', 'lecture', 'page', 'ours', 'vlm', 'answer'])
        w.writerows(rows)
    N.RULES.write_text('# lecture\t原串\t改作 —— foote_notes_entry.py 生成（注区逐条看图答 B＝转录）；\\n 表换行\n'
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
