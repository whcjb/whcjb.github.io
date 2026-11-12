#!/usr/bin/env python3
"""福特《路加福音讲义》页脚注卷进正文：正文里以 ♦ 起头的一截（抽取时页脚注没认出，接进了跨页的句子）。

`she ♦ Origen, Jerome, Theophylact, and the Syriac. was required` —— 句子被页脚注拦腰截断。
header_fixes.tsv 手修过 5 组；这里把其余（2026-11-12 普查正文 ♦ 30 处）程序化处理：

  定位：♦ 前一词作左锚，在整页转录里找该词、取其后 3 词作右锚，在我们 ♦ 之后找右锚——♦ 到右锚之间即卷入的注；
        转录对应页＝该卷各页 [FN:] 行里与卷入串字母最像的那页（相似度须过半）。
  题：A＝卷入串（我们的 OCR），B＝该页转录 [FN:] 行；一页图只看一次，裁注区。
  落：只落 B——正文删掉卷入串、并回句子；转录脚注按页序插进本讲注区（同 foote_notes_missing）。
      该页注区已有 NOTE 条的不落（两边会重复），列日志待看；含希腊/希伯来文的不落，列 notes_leak_greek.tsv。

    python3 scripts/foote_notes_leak.py --collect | --run --all | --rules | --apply
"""
import argparse
import csv
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_image_check as I  # noqa: E402
import foote_notes_check as N  # noqa: E402
import foote_notes_missing as M  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402

N.CAND = N.WORK / 'notes_leak_candidates.json'
N.ANS = N.WORK / 'notes_leak_answers'
N.RULES = N.RAW / 'notes_leak_fixes.tsv'
N.LOG = A.ROOT / 'logs' / 'foote_notes_leak.tsv'
N.COST = A.ROOT / 'logs' / 'foote_notes_leak_cost.tsv'
GREEK = N.RAW / 'notes_leak_greek.tsv'
HAND = N.RAW / 'hand_leak_fixes.tsv'   # 本脚本定位不到的（跨段、断词），人工看图核定，紧接着落
WORD = re.compile(r"[A-Za-z]+")


def vlm_body(vol, leaf):
    t = (V.VLM / f'v{vol}' / f'{leaf:04d}.txt').read_text(encoding='utf-8')
    t = re.split(r'\n\[FN:', t)[0]
    return '\n'.join(ln for ln in t.splitlines() if not ln.startswith('[HEAD]'))


def collect():
    pages, skip, greek = [], Counter(), []
    for vol in (1, 2, 3):
        pn = V.leaf_pages(vol)
        fns = {lf: N.vlm_notes(vol, lf) for lf in pn}
        fns = {lf: vn for lf, vn in fns.items() if vn}
        for lec in V.LECS[vol]:
            text = (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8')
            body = text.partition('\n---\n')[0]
            for m in re.finditer('♦', body):
                pre = WORD.findall(body[max(0, m.start() - 80):m.start()])
                if len(pre) < 3:
                    skip['无左锚'] += 1
                    continue
                tail = body[m.start():m.start() + 600]
                # 转录页：脚注字母与卷入串开头最像
                best, bl = 0, None
                left3 = r'\W+'.join(pre[-3:])
                for lf, vn in fns.items():
                    nl = M.letters(' '.join(t for _, t in vn))
                    if len(nl) < 6:                        # 纯希腊的注没有拉丁字母，空串比谁都「像」
                        continue
                    if not re.search(left3, vlm_body(vol, lf)):   # 短注（`Matt. xxii. 23.`）别页也有：先要左锚在本页正文
                        continue
                    r = SequenceMatcher(None, nl, M.letters(tail)[:len(nl)], autojunk=False).ratio()
                    if r > best:
                        best, bl = r, lf
                if best < 0.5:
                    skip['找不到转录页'] += 1
                    continue
                vn = fns[bl]
                # 右锚：转录正文里左锚三词之后的 3 词（可能在下一页开头）
                vb = vlm_body(vol, bl) + ' ' + (vlm_body(vol, bl + 1) if (V.VLM / f'v{vol}' / f'{bl + 1:04d}.txt').exists() else '')
                vm = re.search(left3 + r'\W+((?:[A-Za-z]+\W+){2}[A-Za-z]+)', vb)
                if not vm:
                    skip['转录无左锚'] += 1
                    continue
                rw = WORD.findall(vm.group(1))
                rm = re.search(r'\s*(?:["“\'‘(*]\s?)?' + r'\W+'.join(rw), body[m.start():m.start() + 800])
                if not rm:
                    skip['我们无右锚'] += 1
                    continue
                s = m.start()
                while s > 0 and body[s - 1] in ' \n':
                    s -= 1
                e = m.start() + rm.start()
                leak = text[s:e]
                v = N.show_vlm(vn)
                pg = str(pn[bl])
                if any('[?]' in t for _, t in vn):
                    skip['转录读不出'] += 1
                    continue
                if N.GRK.search(v):
                    greek.append((f'{lec:03d}', pg, vol, bl, leak, v))
                    continue
                bx = N.box_for(vol, bl, vn)
                if not bx:
                    skip['定位不到'] += 1
                    continue
                pages.append({'vol': vol, 'leaf': bl, 'qs': [{
                    'kind': 'notes-leak', 'lec': f'{lec:03d}', 'page': pg, 's': s, 'e': e,
                    'ours': leak.strip().replace(A.FN_MARK, ''), 'vlm': v, 'vn': vn, 'greek': False, 'box': bx,
                    'ctx': f'footnotes of p. {pg}', 'join': text[max(0, s - 40):s] + ' ⟦…⟧' + text[e:e + 40]}]})
    N.WORK.mkdir(parents=True, exist_ok=True)
    N.CAND.write_text(json.dumps(pages, ensure_ascii=False, indent=0), encoding='utf-8')
    with open(GREEK, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['lecture', 'page', 'vol', 'leaf', 'leak(正文里卷入的串)', 'vlm(转录，含希腊/希伯来文，未问未落，待用户同意)'])
        w.writerows(greek)
    print(f'卷入题 {len(pages)}  希腊另列 {len(greek)}  跳过 {dict(skip)} → {N.CAND}', file=sys.stderr)


def rules():
    pages = json.loads(N.CAND.read_text(encoding='utf-8'))
    got = N.answered()
    rows, out, texts = [], [], {}
    for p in pages:
        q = p['qs'][0]
        a = got.get(N.qkey(q))
        v = 'unasked' if a is None else N.verdict(q, a)
        if v == 'A' and N.key(q['ours']) == N.key(q['vlm']):
            v = 'B'                                        # 卷入串与转录一字不差（`♦ See Whitby.`）：两读一致
        text = texts.setdefault(q['lec'], (A.SRC / f"{q['lec']}.md").read_text(encoding='utf-8'))
        orig = (A.SRC / f"{q['lec']}.md").read_text(encoding='utf-8')   # 题目位置按收题时的原文
        leak = orig[q['s']:q['e']]
        has = q['page'] in M.NOTE.findall(text)            # 该页注已由 foote_notes_missing 补进注区：只删正文这截
        rows.append((v + ('·只删正文' if has else ''), q['lec'], q['page'], q['ours'], q['vlm'], a or ''))
        if v != 'B':
            continue
        # 删卷入串（连同它前面的空白；后面右锚前的空白保留一个），注号哨兵随串保留在原位
        ctx_l = orig[max(0, q['s'] - 30):q['s']]
        old = ctx_l + leak
        new = ctx_l + A.FN_MARK * leak.count(A.FN_MARK)
        h = re.search(r'([a-z])-[;^]*$', ctx_l)
        if h and re.match(r'\s+[a-z]', orig[q['e']:]):
            # 行末断词被卷入串隔开（`alie- ♦ … nated`）：并回整词
            ws = re.match(r'\s+', orig[q['e']:]).group()
            old = ctx_l + leak + ws
            new = ctx_l[:h.start() + 1] + A.FN_MARK * leak.count(A.FN_MARK)
        if text.count(old) != 1:
            rows.append(('X', q['lec'], q['page'], old[:60], '', 'not-unique'))
            continue
        text = text.replace(old, new)
        out.append((q['lec'], old, new))
        if not has:
            ent = '\n\n'.join(f"<!-- NOTE p.{q['page']} --> {N.SYM.get(s, s)} {t}".rstrip() for s, t in q['vn'])
            o2, n2 = M.insert_row(text, q['page'], ent)
            if text.count(o2) != 1:
                rows.append(('X', q['lec'], q['page'], o2[:60], '', 'note-anchor-not-unique'))
            else:
                text = text.replace(o2, n2)
                out.append((q['lec'], o2, n2))
        texts[q['lec']] = text
    with open(N.LOG, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['verdict', 'lecture', 'page', 'leak', 'vlm', 'answer'])
        w.writerows(rows)
    N.RULES.write_text('# lecture\t原串\t改作 —— foote_notes_leak.py 生成（卷进正文的页脚注：删出正文、转录脚注插回注区，看图答 B）；\\n 表换行\n'
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
    elif a.apply:
        for t in (N.RULES, HAND):
            if t.exists():
                I.apply_multiline(t)


if __name__ == '__main__':
    main()
