#!/usr/bin/env python3
"""福特《路加福音讲义》卷进正文的页脚注·第二轮（2026-11-12 用户令「把错误都处理」）。

foote_notes_leak 只认 ♦ 起头的卷入串；注号读成 `•` `f` `t` `+` `*X*` `J`、或干脆没有注号的（`could either Numb, xxxiv. 11;
Josh. xii. 3. f I>€ Bello, iu. 10. see or hear him`）都漏了。这层反过来找：拿转录本每页的注条（[FN:] 行）去本讲正文里找。

  认定（三道闸）：该页全部注条在正文里按序挨着出现（条间至多隔一个注号残串）；转录本该页正文里没有这串（是注不是正文，
        挡住 `Matt. xxiii. 34` 撞 `Matt. xxiii. 3` 这类）；卷入串整段在一段之内，或整段自成段落（段前的 PAGE 标记一并去）。
  落：  正文删去卷入串（段内的接回一个空格）；该页注区还没有注的，补进注区——注文看图（A＝我们卷入的 OCR 串、
        B＝转录各条）答 B 用转录，否则把我们的 OCR 串原样挪进注区（不丢字、不推断）。

    python3 scripts/foote_notes_leak2.py --collect     # 链条位置：foote_line_check --apply 之后
    python3 scripts/foote_notes_leak2.py --run --all
    python3 scripts/foote_notes_leak2.py --rules       # → notes_leak2_fixes.tsv
    python3 scripts/foote_notes_leak2.py --apply
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
import foote_notes_missing as M  # noqa: E402
import foote_punct as P  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402

N.CAND = N.WORK / 'notes_leak2_candidates.json'
N.ANS = N.WORK / 'notes_leak2_answers'
N.RULES = N.RAW / 'notes_leak2_fixes.tsv'
N.LOG = A.ROOT / 'logs' / 'foote_notes_leak2.tsv'
N.COST = A.ROOT / 'logs' / 'foote_notes_leak2_cost.tsv'


def key(t):
    return re.sub(r'[^a-z0-9]', '', t.lower())


def kstream(s):
    pos = [i for i, c in enumerate(s) if c.isascii() and c.isalnum()]
    return ''.join(s[i].lower() for i in pos), pos


def locate(bk, vn):
    """全部注条按序在 bk 里挨着出现 → (首条起, 末条止) 字母流下标；不成返回 None。"""
    ks = [key(t) for _, t in vn]
    if any(len(k) < 5 for k in ks):
        return None
    for m in re.finditer(re.escape(ks[0][:14]), bk):
        start = cur = m.start()
        ok = True
        for n, k in enumerate(ks):
            if n:
                p = bk.find(k[:14], cur, cur + 14)          # 条间至多隔一个注号残串（f / t / x / 数字）
                if p < 0:
                    ok = False
                    break
                cur = p
            tail = k[-6:]
            q = bk.find(tail, cur + len(k) - 10, cur + len(k) + 10)
            if q < 0:
                ok = False
                break
            cur = q + len(tail)
        if ok:
            return start, cur
    return None


def collect():
    out, skip = [], Counter()
    for vol in (1, 2, 3):
        pn = V.leaf_pages(vol)
        leaf_of = {}
        for lf, pg in sorted(pn.items()):
            leaf_of.setdefault(str(pg), lf)
        for lec in V.LECS[vol]:
            text = (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8')
            body = text.partition('\n---\n')[0]
            bk, bpos = kstream(body)
            for pg in sorted(set(re.findall(r'<!-- PAGE (\d+) -->', body)), key=int):
                lf = leaf_of.get(pg)
                vn = N.vlm_notes(vol, lf) if lf is not None else None
                if not vn or any('[?]' in t for _, t in vn):
                    continue
                if sum(len(key(t)) for _, t in vn) < 10:
                    continue                              # 太短（Henry、Dr Guyse）易撞正文里本有的词
                loc = locate(bk, vn)
                if not loc:
                    continue
                vb = ''.join(key(P.clean_vlm((V.VLM / f'v{vol}' / f'{x:04d}.txt').read_text(encoding='utf-8')))
                             for x in (lf - 1, lf, lf + 1) if (V.VLM / f'v{vol}' / f'{x:04d}.txt').exists())
                if key(vn[0][1])[:14] in vb:
                    skip['转录正文也有'] += 1
                    continue
                s, e = bpos[loc[0]], bpos[loc[1] - 1] + 1
                while e < len(body) and body[e] in '.,;:)*"\'':
                    e += 1
                if e < len(body) and body[e].isalnum():
                    skip['后接字母数字'] += 1                # `Matt. xxiii. 3` 撞正文的 `Matt. xxiii. 34`
                    continue
                # 往前吃注号残串：前一个空白分隔的短串（≤5 字符、不是真词，或单字母 f/t/J/X）
                k = s
                while k > 0 and body[k - 1] == ' ':
                    k -= 1
                w0 = body.rfind(' ', 0, k) + 1
                w0 = max(w0, body.rfind('\n', 0, k) + 1)
                tok = body[w0:k]
                if tok and len(tok) <= 5 and (tok.strip('*\\') in ('f', 't', 'J', 'X', '+', '•', '♦', '*', '-j-', '^')
                                              or not A._isword(re.sub(r'[^A-Za-z]', '', tok).lower() or 'zzzz')):
                    s = w0
                block = body[s:e]
                if '\n\n' in block:
                    skip['跨段'] += 1
                    continue
                ls = body.rfind('\n', 0, s) + 1
                le = body.find('\n', e)
                le = len(body) if le < 0 else le
                whole = not body[ls:s].strip() and not body[e:le].strip()
                if whole:
                    # 自成一段：连段前紧贴的 PAGE 标记行一起去
                    a = ls
                    m = re.search(r'(\n\n<!-- PAGE \S* -->\n)$', body[:ls])
                    if m:
                        a = ls - len(m.group(1)) + 2
                    old_s, old_e = a, min(le + 2, len(body)) if body[le:le + 2] == '\n\n' else le
                    if not body[old_e:].strip():
                        old_s = len(body[:old_s].rstrip('\n'))   # 正文最末一段：连前面的空行一起去
                    new = ''
                else:
                    old_s, old_e = s, e
                    while old_s > 0 and body[old_s - 1] == ' ':
                        old_s -= 1
                    while old_e < len(body) and body[old_e] == ' ':
                        old_e += 1
                    new = ' '
                    if body[old_s - 1:old_s] == '\n':
                        new = ''                          # 行首：不留前导空格
                    m1 = re.search(r'([A-Za-z]+)-$', body[:old_s])
                    m2 = re.match(r'[a-z]+', body[old_e:])
                    if m1 and m2 and A._isword((m1.group(1) + m2.group()).lower()):
                        old_s -= 1                        # 断词中间夹着卷入串：`express- ⟦注⟧ ing` → expressing
                        new = ''
                has = pg in M.NOTE.findall(text)
                out.append({'vol': vol, 'leaf': lf, 'qs': [{
                    'kind': 'notes-leak2', 'lec': f'{lec:03d}', 'page': pg, 'old_s': old_s, 'old_e': old_e, 'new': new,
                    'has': has, 'ours': re.sub(r'\s+', ' ', re.sub(r'<!--.*?-->', ' ', block)).strip(),
                    'vlm': N.show_vlm(vn), 'vn': vn, 'greek': False, 'box': N.box_for(vol, lf, vn),
                    'ctx': f'footnotes of p. {pg}'}]})
                skip['有注已在注区' if has else '待补注'] += 1
    N.WORK.mkdir(parents=True, exist_ok=True)
    N.CAND.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'卷入 {len(out)}  {dict(skip)} → {N.CAND}', file=sys.stderr)


def rules():
    pages = json.loads(N.CAND.read_text(encoding='utf-8'))
    got = N.answered()
    texts, rows, out = {}, [], []
    # 同讲多处：从后往前删，偏移不乱；每处以原串＋两旁各 30 字求唯一
    qs = sorted((p['qs'][0] for p in pages), key=lambda q: (q['lec'], -q['old_s']))
    orig = {}
    for q in qs:
        t = texts.setdefault(q['lec'], (A.SRC / f"{q['lec']}.md").read_text(encoding='utf-8'))
        o0 = orig.setdefault(q['lec'], t)
        a, b = max(0, q['old_s'] - 30), min(len(o0), q['old_e'] + 30)
        old = o0[a:b]
        new = o0[a:q['old_s']] + q['new'] + o0[q['old_e']:b]
        if t.count(old) != 1:
            rows.append(('X-not-unique', q['lec'], q['page'], q['ours'], ''))
            continue
        t = t.replace(old, new)
        out.append((q['lec'], old, new))
        v = 'has'
        if not q['has']:
            a_ = got.get(N.qkey(q)) if q['box'] else None
            v = N.verdict(q, a_) if a_ else 'unasked'
            if v == 'B':
                ent = '\n\n'.join(f"<!-- NOTE p.{q['page']} --> {N.SYM.get(s, s)} {x}".rstrip() for s, x in q['vn'])
            else:
                ent = f"<!-- NOTE p.{q['page']} --> {q['ours']}"
            o2, n2 = M.insert_row(t, q['page'], ent)
            if t.count(o2) != 1:
                rows.append(('X-insert', q['lec'], q['page'], q['ours'], ''))
                continue
            t = t.replace(o2, n2)
            out.append((q['lec'], o2, n2))
        texts[q['lec']] = t
        rows.append((v, q['lec'], q['page'], q['ours'], q['vlm']))
    with open(N.LOG, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['verdict', 'lecture', 'page', 'ours', 'vlm'])
        w.writerows(rows)
    N.RULES.write_text('# lecture\t原串\t改作 —— foote_notes_leak2.py 生成（卷进正文的页脚注删出、该页无注的补进注区）；\\n 表换行\n'
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
        pages = json.loads(N.CAND.read_text(encoding='utf-8'))
        ask = [p for p in pages if not p['qs'][0]['has'] and p['qs'][0]['box']]
        N.CAND.with_suffix('.ask.json').write_text(json.dumps(ask, ensure_ascii=False), encoding='utf-8')
        cand, N.CAND = N.CAND, N.CAND.with_suffix('.ask.json')
        N.run(a.sample, a.all)
        N.CAND = cand
    elif a.rules:
        rules()
    elif a.apply and N.RULES.exists():
        I.apply_multiline(N.RULES)


if __name__ == '__main__':
    main()
