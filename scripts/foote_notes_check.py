#!/usr/bin/env python3
"""福特《路加福音讲义》注区看图：页脚注整页一题，我们 vs 整页转录的 [FN:] 行，一页图只看一次。

前面各层只管正文（`---` 之前），注区一直是第①层 OCR 原样（`Nttmb. XV. 32`、`Lev. zzUL 32`、`+ r^^rf/ffxc`）。
转录本（foote_raw/luke/vlm/）每页末尾逐条记 `[FN:*] Isa. xxi. 10.`，读法远比 OCR 干净——拿它当 B，看图定夺。

  题：某讲某页的全部 NOTE 条（同页、同讲、在注区里连续）与该页转录的 [FN:] 行不一致（比字母数字标点）。
  图：tess_grc 逐词框里与转录脚注词重合过半的行，合成一块裁原生分辨率；找不到就取页面下四分之一。
  落：只落答 B；转录带希腊字母的不落，列 notes_greek_pending.tsv 待用户核（单证人读希腊活字，须同意）；
      转录带 [?]、跨讲同页的不问。注号 `*` 写成 ♦（注区里 `*` 会被当斜体符；全书注区原有写法），余 † ‡ § ‖ ¶ 照转录。

    python3 scripts/foote_notes_check.py --collect
    python3 scripts/foote_notes_check.py --run --sample 5 | --run --all
    python3 scripts/foote_notes_check.py --rules       # → notes_fixes.tsv + notes_greek_pending.tsv
    python3 scripts/foote_notes_check.py --apply       # 链条最末（foote_junk_check.py --apply 之后）
"""
import argparse
import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_image_check as I  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402

RAW = A.RAW
WORK = RAW / 'imgcheck'
CAND = WORK / 'notes_candidates.json'
ANS = WORK / 'notes_answers'
RULES = RAW / 'notes_fixes.tsv'
GREEK = RAW / 'notes_greek_pending.tsv'
LOG = A.ROOT / 'logs' / 'foote_notes_check.tsv'
COST = A.ROOT / 'logs' / 'foote_notes_check_cost.tsv'

NOTE = re.compile(r'<!-- NOTE p\.(\S+) --> (.*)')
FNL = re.compile(r'^\[FN:([^\]]*)\]\s*(.*)$')
GRK = re.compile(r'[Ͱ-Ͽἀ-῿]')
SYM = {'*': '♦'}

SYSTEM = (
    'You are proof-reading the FOOTNOTES of a digitised 19th-century printed book against an image of the footnote area '
    'of one page (native scan resolution). For each numbered question you get two candidate transcriptions A and B of '
    'all footnotes on that page; " ¦ " separates one footnote from the next, and each footnote starts with its reference '
    'mark (♦ stands for the printed asterisk *). Decide which reading matches the print character for character: '
    'letters, digits, roman numerals, abbreviations, every punctuation mark. Asterisks *like this* around words only mark '
    'italics. Answer each question on its own line exactly as  #n: A   or  #n: B   or, if neither matches the print,  '
    '#n: = <the printed footnotes, same format>  . If it cannot be made out, answer  #n: ?  . Output only the answer lines.'
)


def vlm_notes(vol, leaf):
    f = V.VLM / f'v{vol}' / f'{leaf:04d}.txt'
    if not f.exists():
        return None
    out, started = [], False
    for ln in f.read_text(encoding='utf-8').splitlines():
        m = FNL.match(ln.strip())
        if m:
            started = True
            out.append([m.group(1).strip(), m.group(2).strip()])
        elif started and ln.strip() and not ln.startswith('[HEAD]'):
            out[-1][1] += ' ' + ln.strip()
    for x in out:   # 印张签名（`[SIG:VOL. III. 2 Q]`）不是脚注；转录的 en dash 全书作连字符
        x[1] = re.sub(r'\s*\[SIG:[^\]]*\]', '', x[1]).replace('–', '-').strip()
    return out


def note_blocks(lec):
    """本讲注区 → {页: (起, 止, [条文])}；同页条须连续，否则不收。"""
    text = (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8')
    base = text.find('\n---\n')
    if base < 0:
        return text, {}
    ent = [(m.start(), m.end(), m.group(1), m.group(2)) for m in NOTE.finditer(text, base)]
    blocks, bad = {}, set()
    for k, (s, e, pg, t) in enumerate(ent):
        if pg in blocks:
            if ent[k - 1][2] != pg:
                bad.add(pg)
            b = blocks[pg]
            blocks[pg] = (b[0], e, b[2] + [t])
        else:
            blocks[pg] = (s, e, [t])
    return text, {p: b for p, b in blocks.items() if p not in bad}


def show_ours(ts):
    return ' ¦ '.join(t.strip() for t in ts).replace(A.FN_MARK, '')


def show_vlm(vn):
    return ' ¦ '.join(f"{SYM.get(s, s)} {t}" for s, t in vn)


def key(t):
    t = t.replace('♦', '*').replace('’', "'").replace('“', '"').replace('”', '"')
    return re.sub(r'[\s*¦]', '', t).lower()


def box_for(vol, leaf, vn):
    words = set(w.lower() for _, t in vn for w in re.findall(r'[A-Za-z]{2,}', t))
    tw = I.tsv_words(vol, leaf)
    lines = defaultdict(list)
    for x in tw:
        lines[x[5]].append(x)
    hit = [ln for ln in lines.values()
           if len(ln) and sum(x[0] in words for x in ln) >= max(1, len(ln) // 2)]
    # 只取页底那一簇（自下而上、行距 < 150px 连着的）：正文里的常见词（see、on、luke）也会凑上
    hit.sort(key=lambda ln: -min(x[2] for x in ln))
    keep = hit[:1]
    for ln in hit[1:]:
        if min(x[2] for x in keep[-1]) - max(x[2] + x[4] for x in ln) > 150:
            break
        keep.append(ln)
    hit = keep
    ys = [y for ln in hit for x in ln for y in (x[2], x[2] + x[4])]
    if not ys:
        return None
    y0, y1 = min(ys), max(ys)
    xs = [v for ln in hit for x in ln for v in (x[1], x[1] + x[3])]
    return [min(xs), y0, max(xs), y1]


def collect():
    pages, skip, ngreek = [], Counter(), 0
    for vol in (1, 2, 3):
        pn = V.leaf_pages(vol)
        leaf_of = {}
        for lf, pg in sorted(pn.items()):
            leaf_of.setdefault(pg, lf)
        owner = defaultdict(set)
        blocks = {}
        for lec in V.LECS[vol]:
            text, bl = note_blocks(lec)
            for pg, b in bl.items():
                owner[pg].add(lec)
                blocks[(lec, pg)] = b
        for (lec, pg), (s, e, ts) in blocks.items():
            if len(owner[pg]) > 1:
                skip['跨讲同页'] += 1
                continue
            lf = leaf_of.get(pg)
            vn = vlm_notes(vol, lf) if lf is not None else None
            if not vn:
                skip['无转录脚注'] += 1
                continue
            if any('[?]' in t for _, t in vn):
                skip['转录读不出'] += 1
                continue
            o, v = show_ours(ts), show_vlm(vn)
            if key(o) == key(v):
                continue
            # 转录只记本页起头的注，接续上页的那截没有 [FN:]——对不上的不问（落 B 会删掉我们的字）
            if (SequenceMatcher(None, key(o), key(v), autojunk=False).ratio() < 0.5
                    or len(key(v)) < 0.8 * len(key(o))):
                skip['两边对不上'] += 1
                continue
            bx = box_for(vol, lf, vn)
            if not bx:
                skip['定位不到'] += 1
                continue
            g = bool(GRK.search(v))
            ngreek += g
            pages.append({'vol': vol, 'leaf': lf, 'qs': [{
                'kind': 'notes', 'lec': f'{lec:03d}', 'page': pg, 's': s, 'e': e, 'ours': o, 'vlm': v,
                'vn': vn, 'greek': g, 'box': bx, 'ctx': f'footnotes of p. {pg}'}]})
    WORK.mkdir(parents=True, exist_ok=True)
    CAND.write_text(json.dumps(pages, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'注区题 {len(pages)}（含希腊 {ngreek}）跳过 {dict(skip)} → {CAND}', file=sys.stderr)


def show(q):
    return q['ours'], q['vlm']


def qkey(q):
    return (q['lec'], q['page'], q['ours'], q['vlm'])


def answered():
    got = {}
    for f in sorted(ANS.glob('v*/*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        for n, q in enumerate(d['qs'], 1):
            a = d['ans'].get(str(n), '')
            if q.get('swap') and a in ('A', 'B'):
                a = 'B' if a == 'A' else 'A'
            got[qkey(q)] = a
    return got


def run(sample, all_):
    pages = json.loads(CAND.read_text(encoding='utf-8'))
    got = answered()
    todo = []
    for p in pages:
        qs = [q for q in p['qs'] if qkey(q) not in got]
        rnd = random.Random(f"notes-{p['vol']}-{p['leaf']}")
        for q in qs:
            q['swap'] = rnd.random() < 0.5
        if qs:
            todo.append(dict(p, qs=qs))
    if not all_:
        random.seed(20261111)
        todo = random.sample(todo, min(sample or 5, len(todo)))
    total, fails = 0.0, 0
    old_sys, old_show = I.SYSTEM, I.show
    I.SYSTEM, I.show = SYSTEM, show
    with open(COST, 'a', encoding='utf-8') as fh:
        for n, p in enumerate(todo, 1):
            try:
                res, cost = I.ask(p['vol'], p['leaf'], p['qs'])
            except Exception as e:                     # noqa: BLE001
                fails += 1
                print(f"v{p['vol']} {p['leaf']:4d} 失败 {e}", file=sys.stderr, flush=True)
                if 'limit' in str(e).lower():
                    print('⛔ 额度用尽，中止', file=sys.stderr, flush=True)
                    sys.exit(42)
                if fails >= 5:
                    print('⛔ 连续失败过多，中止', file=sys.stderr, flush=True)
                    sys.exit(3)
                continue
            fails = 0
            total += cost
            ans = {int(m.group(1)): m.group(2) for m in re.finditer(r'^\s*#(\d+):\s*(.*?)\s*$', res, re.M)}
            d = ANS / f"v{p['vol']}"
            d.mkdir(parents=True, exist_ok=True)
            k = 1
            while (d / f"{p['leaf']:04d}_{k}.json").exists():
                k += 1
            (d / f"{p['leaf']:04d}_{k}.json").write_text(
                json.dumps({'raw': res, 'ans': ans, 'qs': p['qs']}, ensure_ascii=False), encoding='utf-8')
            fh.write(f"{p['vol']}\t{p['leaf']}\t{len(p['qs'])}\t{len(ans)}\t{cost:.4f}\n")
            fh.flush()
            print(f"v{p['vol']} {p['leaf']:4d} 问 {len(p['qs']):2d} 答 {len(ans):2d}  ${cost:.4f}  累计 ${total:.2f}  "
                  f"({n}/{len(todo)})", file=sys.stderr, flush=True)
    I.SYSTEM, I.show = old_sys, old_show


def verdict(q, a):
    if a in ('A', 'B'):
        return a
    if not a.startswith('='):
        return 'other'
    x = key(a[1:])
    return 'B' if x == key(q['vlm']) else 'A' if x == key(q['ours']) else 'other'


def rules():
    pages = json.loads(CAND.read_text(encoding='utf-8'))
    got = answered()
    rows, out, greek = [], [], []
    for p in pages:
        for q in p['qs']:
            a = got.get(qkey(q))
            text = (A.SRC / f"{q['lec']}.md").read_text(encoding='utf-8')
            old = text[q['s']:q['e']]
            if a is None:
                rows.append(('unasked', q['lec'], q['page'], q['ours'], q['vlm'], ''))
                continue
            if show_ours([m.group(2) for m in NOTE.finditer(old)]) != q['ours']:
                rows.append(('stale', q['lec'], q['page'], q['ours'], q['vlm'], a))
                continue
            v = verdict(q, a)
            if v == 'B' and q['greek']:
                v = 'B-greek'
                greek.append((q['lec'], q['page'], p['vol'], p['leaf'], q['ours'], q['vlm']))
            rows.append((v, q['lec'], q['page'], q['ours'], q['vlm'], a))
            if v != 'B':
                continue
            # 原注区里夹的注号哨兵（极少）随条保留在首条末
            fnm = old.count(A.FN_MARK)
            new = '\n\n'.join(f"<!-- NOTE p.{q['page']} --> {SYM.get(s, s)} {t}".rstrip() for s, t in q['vn']) + A.FN_MARK * fnm
            if text.count(old) != 1:
                rows.append(('X', q['lec'], q['page'], q['ours'], q['vlm'], 'not-unique'))
                continue
            out.append((q['lec'], old, new))
    with open(LOG, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['verdict', 'lecture', 'page', 'ours', 'vlm', 'answer'])
        w.writerows(rows)
    RULES.write_text('# lecture\t原串\t改作 —— foote_notes_check.py 生成（注区整页看图答 B＝转录）；\\n 表换行\n'
                     + ''.join('\t'.join(x.replace('\n', '\\n') for x in r) + '\n' for r in out), encoding='utf-8')
    with open(GREEK, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['lecture', 'page', 'vol', 'leaf', 'ours', 'vlm(看图答B，含希腊文，待用户同意)'])
        w.writerows(greek)
    print(dict(Counter(r[0] for r in rows)), f'规则 {len(out)} → {RULES}；希腊待核 {len(greek)} → {GREEK}',
          file=sys.stderr)


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
        run(a.sample, a.all)
    elif a.rules:
        rules()
    elif a.apply and RULES.exists():
        I.apply_multiline(RULES)


if __name__ == '__main__':
    main()
