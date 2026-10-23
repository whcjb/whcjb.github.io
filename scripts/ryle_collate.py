#!/usr/bin/env python3
"""莱尔马太：e-Sword 本逐段对齐 1857 扫描件 OCR（IA expositorythough01ryle），列出全部差异。

    python3 scripts/ryle_collate.py          → ryle_raw/matthew/collation_diffs.tsv（全部差异，带上下文）

只做「看」，不改字。改字由 ryle_apply（按 manual 表/成体系规则）做。
OCR 有噪声，所以差异里绝大多数是 OCR 错字；成体系的 e-Sword 改动（Savior、St.、出处格式）在这里按类计数。
"""
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'ryle_raw' / 'matthew'
OCR = RAW / 'src' / 'ia_1857' / 'expositorythough01ryle_djvu.txt'
SEC = RAW / 'esword_sections.json'
OUT = RAW / 'collation_diffs.tsv'

RUNHEAD = re.compile(r'^\s*(\d+\s+)?(EXPOSITORY\s+THOUGHTS\.?|MATTHEW,?\s+CHAP\.?.*?|PREFACE\.?.*)\s*(\d+)?\s*$')


HOCR = RAW / 'src' / 'ia_1857' / 'expositorythough01ryle_hocr.html'


def ocr_tokens():
    """hOCR → [(key, raw, (page, x0, y0, x1, y1))]。去页眉页码行，行末连字符拼回。page 从 0 起（同 PDF 页序）。"""
    import html as H
    src = HOCR.read_text(encoding='utf-8', errors='ignore')
    toks = []
    for pi, page in enumerate(re.split(r"<div class=.ocr_page", src)[1:]):
        for line in re.findall(r'<span class="ocr_line".*?</span>\s*</span>', page, re.S):
            ws = [(H.unescape(w), tuple(map(int, b.split()))) for b, w in
                  re.findall(r'class="ocrx_word"[^>]*title="bbox (\d+ \d+ \d+ \d+)[^"]*">([^<]*)', line)]
            text = ' '.join(w for w, _ in ws)
            if not ws or RUNHEAD.match(text) or re.fullmatch(r'\s*\d{1,3}\s*', text):
                continue
            for w, b in ws:
                toks.append([w.strip(), (pi,) + b])
    out = []
    i = 0
    while i < len(toks):
        w, b = toks[i]
        if re.search(r'[a-z]-$', w) and i + 1 < len(toks) and toks[i + 1][1][2] > b[2] + 5:
            w = w[:-1] + toks[i + 1][0]
            i += 1
        k = key(w)
        if k:
            out.append((k, w, b))
        i += 1
    return out


def key(w):
    return re.sub(r'[^a-z0-9]', '', w.lower())


def es_tokens(text):
    text = re.sub(r'⟨([^⟩]*)⟩', r' \1 ', text).replace('⟦fn⟧', ' ')
    text = text.replace('⟪', '').replace('⟫', '').replace('*', '').replace('—', ' — ')
    out = []
    for w in text.split():
        k = key(w)
        if k:
            out.append((k, w))
    return out


def locate(es, ocr_keys, start_hint):
    """在 OCR 里找本段开头：取前几个 6 词串依次试。"""
    for j in range(0, min(60, len(es) - 6), 3):
        sh = [e[0] for e in es[j:j + 6]]
        for i in range(start_hint, min(len(ocr_keys) - 6, start_hint + 12000)):
            if ocr_keys[i:i + 6] == sh:
                return max(start_hint, i - j - 5)
    return None


def classify(ka, kb, tag, ea):
    if ka in ('savior', 'saviors') and kb in ('saviour', 'saviours'):
        return 'savior'
    if tag == 'insert' and kb == 'st':
        return 'st'
    if re.search(r'_\d', ea):
        return 'ref'
    return 'other'


def diffs(es, sid, O, sm, a_off=0, rows=None, cat=None, blocks=None):
    """把一次对齐的 opcodes 摊成差异行；es 侧超过 40 词没对上的整块记进 blocks 留给局部重对。"""
    for tag, a1, a2, b1, b2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        if a2 - a1 > 40 or b2 - b1 > 40:      # 经文框（只在 OCR 侧）、挪到页底的脚注等整块
            cat['block'] += 1
            if a2 - a1 > 40 and blocks is not None:
                blocks.append((a_off + a1, a_off + a2, b1))
            continue
        ea = ' '.join(e[1] for e in es[a1:a2])
        ob = ' '.join(w[1] for w in O[b1:b2])
        ka = ''.join(e[0] for e in es[a1:a2])
        kb = ''.join(w[0] for w in O[b1:b2])
        if ka == kb:
            continue
        c = classify(ka, kb, tag, ea)
        cat[c] += 1
        ctx = ' '.join(e[1] for e in es[max(0, a1 - 6):a1]) + ' ⟦' + ea + '⟧ ' + ' '.join(e[1] for e in es[a2:a2 + 6])
        bb = O[b1][2] if b1 < len(O) else O[-1][2]
        ia = a_off + a1
        rows.append((sid[min(ia, len(sid) - 1)], c, tag, ea, ob, ' '.join(map(str, bb)), str(ia), ctx))


def main():
    d = json.loads(SEC.read_text(encoding='utf-8'))
    O = ocr_tokens()
    es, sid = [], []
    for s in d['sections']:
        notes = iter(s['notes'])
        # 脚注就地插在 ⟦fn⟧ 处：1857 原书脚注排在该页页底，紧跟标记所在那几行之后
        text = re.sub('⟦fn⟧', lambda m: ' ' + next(notes) + ' ', '\n'.join(s['paras']))
        for e in es_tokens(text):
            es.append(e)
            sid.append(f'{s["ch"]}:{s["v1"]}')
    sm = difflib.SequenceMatcher(None, [e[0] for e in es], [w[0] for w in O], autojunk=False)
    rows, blocks, cat = [], [], Counter()
    diffs(es, sid, O, sm, 0, rows, cat, blocks)
    # 第二遍：整块没对上的（脚注挪到了页底/下一页），在前后几页里局部重对
    for a1, a2, b1 in blocks:
        pg = O[min(b1, len(O) - 1)][2][0]
        sub = [w for w in O if pg - 2 <= w[2][0] <= pg + 3]
        seg = es[a1:a2]
        sm2 = difflib.SequenceMatcher(None, [e[0] for e in seg], [w[0] for w in sub], autojunk=False)
        got = sum(b.size for b in sm2.get_matching_blocks())
        if got < 0.6 * len(seg):
            print(f'  ⚠️ {sid[a1]} 有 {len(seg)} 词在 1857 本 p.{pg - 2}–{pg + 3} 找不到：',
                  ' '.join(e[1] for e in seg[:16]), file=sys.stderr)
            continue
        # 只取 seg 首尾之间对上的那一段 OCR，避免把整页别的文字算成差异
        mb = [b for b in sm2.get_matching_blocks() if b.size]
        lo, hi = mb[0].b, mb[-1].b + mb[-1].size
        sub = sub[lo:hi]
        sm2 = difflib.SequenceMatcher(None, [e[0] for e in seg], [w[0] for w in sub], autojunk=False)
        diffs(seg, sid, sub, sm2, a1, rows, cat, None)
    rows.sort(key=lambda r: int(r[6]) if r[6].isdigit() else 0)
    with OUT.open('w', encoding='utf-8') as f:
        f.write('sec\tcat\top\tesword\tocr1857\tpage_bbox\tes_idx\tcontext\n')
        for r in rows:
            f.write('\t'.join(x.replace('\t', ' ') for x in r) + '\n')
    print(dict(cat), '→', OUT)


if __name__ == '__main__':
    main()
