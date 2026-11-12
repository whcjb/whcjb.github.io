#!/usr/bin/env python3
"""福特《路加福音讲义》注区看图·转录带 [?] 的页（2026-11-12 用户令「处理」）。

foote_notes_check 不问转录带 [?] 的页（96 页，残字 235）。这些 [?] 几乎都在希腊字母上（转录不敢定的重音、元音）。
看图第二读（foote_greek_read.py，不给提示、照印面读）读了同页的希腊文：转录里读出的字母与第二读逐字相同、
[?] 处 0–3 个字母由第二读给出——两次独立读法除 [?] 外一致，[?] 取第二读。一页的 [?] 全能这样补上才出题。
其余希腊字形照 foote_greek_notes 的办法取第二读写法（找不到的去锐钝音）。

  题：A＝我们该页注区，B＝补好的转录。一页图只看一次（问法、裁图同 foote_notes_check）。
  落：只落答 B（希腊文 2026-11-12 已得同意「放进书里」）。

    python3 scripts/foote_notes_fill.py --collect     # 链条位置：foote_greek_notes --apply 之后
    python3 scripts/foote_notes_fill.py --run --sample 3 | --run --all
    python3 scripts/foote_notes_fill.py --rules       # → notes_fill_fixes.tsv
    python3 scripts/foote_notes_fill.py --apply
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_greek_notes as GN  # noqa: E402
import foote_greek_read as G  # noqa: E402
import foote_image_check as I  # noqa: E402
import foote_notes_check as N  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402

N.CAND = N.WORK / 'notes_fill_candidates.json'
N.ANS = N.WORK / 'notes_fill_answers'
N.RULES = N.RAW / 'notes_fill_fixes.tsv'
N.GREEK = N.WORK / 'notes_fill_greek_unused.tsv'      # 本层希腊文照落，不另列
N.LOG = A.ROOT / 'logs' / 'foote_notes_fill.tsv'
N.COST = A.ROOT / 'logs' / 'foote_notes_fill_cost.tsv'
TOK = re.compile(r'\S*\[\?\]\S*')
EDGE = '.,;:—"\'()*'
GSEG = re.compile(r'(?:[Ͱ-Ͽἀ-῿᾿῾ʼʽ]|\[\?\])+')


def wild(tok):
    return re.compile('^' + '.{0,3}'.join(re.escape(G.bare(p)) for p in tok.split('[?]')) + '$')


def fill_note(t, words, stat):
    """t 里每个带 [?] 的词换成第二读里唯一相合的词；有一个补不上返回 None。"""
    toks = t.split(' ')
    for i, tok in enumerate(toks):
        if '[?]' not in tok:
            continue
        m = GSEG.search(tok)                       # 只换词里的希腊字母段（`παλ[?]μᾳ—*Pindar*,` 里的 παλ[?]μᾳ）
        if not m:
            stat['非希腊[?]'] += 1
            return None
        core = m.group()
        if not G.bare(core.replace('[?]', '')) and len(core) <= 3:
            stat['光[?]'] += 1
            return None
        w = wild(core)
        hits = [j for j, x in enumerate(words) if w.match(G.bare(x.strip(EDGE)))]
        if len({words[j].strip(EDGE) for j in hits}) > 1:
            # 多个相合：按前后邻词（不带 [?]、字母相同）挑
            def ctx(j):
                n = 0
                if i > 0 and j > 0 and '[?]' not in toks[i - 1] and G.bare(toks[i - 1]) == G.bare(words[j - 1]):
                    n += 1
                if i + 1 < len(toks) and j + 1 < len(words) and '[?]' not in toks[i + 1] \
                        and G.bare(toks[i + 1]) == G.bare(words[j + 1]):
                    n += 1
                return n
            best = max(map(ctx, hits))
            hits = [j for j in hits if ctx(j) == best] if best else []
        if len({words[j].strip(EDGE) for j in hits}) != 1:
            stat['补不上'] += 1
            return None
        x = re.sub(r'(?<=\w)-(?=\w)', '', words[hits[0]].strip(EDGE))
        toks[i] = tok[:m.start()] + x + tok[m.end():]
        if '[?]' in toks[i]:
            stat['一词两段[?]'] += 1
            return None
        stat['补上'] += 1
    return ' '.join(toks)


def collect():
    sr = GN.second_reads()
    pages, skip, stat = [], Counter(), Counter()
    for vol in (1, 2, 3):
        pn = V.leaf_pages(vol)
        leaf_of = {}
        for lf, pg in sorted(pn.items()):
            leaf_of.setdefault(pg, lf)
        owner, blocks = defaultdict(set), {}
        for lec in V.LECS[vol]:
            _, bl = N.note_blocks(lec)
            for pg, b in bl.items():
                owner[pg].add(lec)
                blocks[(lec, pg)] = b
        for (lec, pg), (s, e, ts) in blocks.items():
            lf = leaf_of.get(pg)
            vn = N.vlm_notes(vol, lf) if lf is not None else None
            if len(owner[pg]) > 1 or not vn or not any('[?]' in t for _, t in vn):
                continue
            reads = sr.get((vol, lf), [])
            words = [w for x in reads if '[?]' not in x for w in x.split()]
            filled = []
            for sym, t in vn:
                f = fill_note(t, words, stat) if '[?]' in t else t
                if f is None:
                    break
                filled.append((sym, GN.greekify(f, reads, stat).replace('ȣ', 'ου')))   # 印本 ου 连写字，全书写 ου
            if len(filled) != len(vn):
                skip['补不全'] += 1
                continue
            o, v = N.show_ours(ts), N.show_vlm(filled)
            if N.key(o) == N.key(v):
                skip['已一致'] += 1
                continue
            if (SequenceMatcher(None, N.key(o), N.key(v), autojunk=False).ratio() < 0.5
                    or len(N.key(v)) < 0.8 * len(N.key(o))):
                skip['两边对不上'] += 1
                continue
            bx = N.box_for(vol, lf, vn)
            if not bx:
                skip['定位不到'] += 1
                continue
            pages.append({'vol': vol, 'leaf': lf, 'qs': [{
                'kind': 'notes', 'lec': f'{lec:03d}', 'page': pg, 's': s, 'e': e, 'ours': o, 'vlm': v,
                'vn': filled, 'greek': False, 'box': bx, 'ctx': f'footnotes of p. {pg}'}]})
    N.WORK.mkdir(parents=True, exist_ok=True)
    N.CAND.write_text(json.dumps(pages, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'题 {len(pages)}  跳过 {dict(skip)}  {dict(stat)} → {N.CAND}', file=sys.stderr)


# 看图答 other 的 8 页，2026-11-12 逐页裁原生分辨率注区读定：(讲, 页) → 改作里要换的 (原, 新)，空表＝照 B 落。
# 005 印 Θεȣ（＝Θεου，第二读补成 Θεω 错）；037 印 ἐστι—.；056 印 συστασι ἡμων αὐταρκη；065 εὑρησετε 后只一个 .—；
# 091 两处都只一个 ·；105 印 ληνος : 、120 印 Κιδρων（模型的 ; 与 Κεδρων 不对，照 B）；015 裁图落在页眉，不落。
HAND = {
    ('005', '70'): [('Θεω', 'Θεου')],
    ('037', '526'): [('ἐστι——.', 'ἐστι—.')],
    ('056', '235'): [('συστασει ἡμων αὐταρκης', 'συστασι ἡμων αὐταρκη')],
    ('065', '365'): [('εὑρησετε.—.—', 'εὑρησετε.—')],
    ('091', '5'): [('ὑμων···', 'ὑμων·'), ('Ἐντος··', 'Ἐντος·')],
    ('105', '198'): [],
    ('120', '416'): [],
}


def rules():
    got = N.answered()
    pages = json.loads(N.CAND.read_text(encoding='utf-8'))
    for p in pages:
        q = p['qs'][0]
        subs = HAND.get((q['lec'], str(q['page'])))
        if subs is None:
            continue
        for a, b in subs:
            if not any(a in t for _, t in q['vn']):
                raise SystemExit(f"HAND {q['lec']} p.{q['page']}: 找不到 {a}")
            q['vn'] = [(s, t.replace(a, b)) for s, t in q['vn']]
        q['vlm'] = N.show_vlm(q['vn'])
        got[N.qkey(q)] = 'B'
    N.answered = lambda: got
    N.CAND = N.WORK / 'notes_fill_candidates_hand.json'   # 原题表不动，二跑仍从原题起
    N.CAND.write_text(json.dumps(pages, ensure_ascii=False, indent=0), encoding='utf-8')
    N.rules()


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
