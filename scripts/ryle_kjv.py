#!/usr/bin/env python3
"""莱尔马太经文框：1769 钦定本（ebible eng-kjv2006，\\add 斜体）逐词对齐 1857 扫描件 OCR，
拼写以 1857 为准（只取成族的拼写差异），其余取钦定本（OCR 噪声）。

    python3 scripts/ryle_kjv.py            → ryle_raw/matthew/kjv_diffs.tsv（全部差异，供看图）
    python3 scripts/ryle_kjv.py --build    → ryle_raw/matthew/kjv_1857.json  {"c:v": "text with *italic*"}
"""
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ryle_collate as C  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'ryle_raw' / 'matthew'
USFM = RAW / 'src' / 'kjv' / '70-MATeng-kjv2006.usfm'
OUT = RAW / 'kjv_1857.json'
DIFFS = RAW / 'kjv_diffs.tsv'


def kjv_words():
    """→ [(c, v, word, italic)]，word 带标点。"""
    out = []
    c = v = 0
    for line in USFM.read_text(encoding='utf-8').split('\n'):
        m = re.match(r'\\c (\d+)', line)
        if m:
            c = int(m.group(1))
            continue
        m = re.match(r'\\v (\d+) (.*)', line)
        if not m:
            continue
        v, body = int(m.group(1)), m.group(2)
        body = re.sub(r'\\\+?w ([^|\\]*)\|[^\\]*\\\+?w\*', r'\1', body)
        body = body.replace('¶', '')
        body = re.sub(r'\\\+?add ([^\\]*)\\\+?add\*', lambda x: ' '.join('⁅' + w + '⁆' for w in x.group(1).split()), body)
        body = re.sub(r'\\\+?[a-z]+\*?', '', body)
        for w in body.split():
            it = w.startswith('⁅')
            out.append((c, v, w.replace('⁅', '').replace('⁆', ''), it))
    return out


def box_tokens():
    """hOCR 里小字号（x_size ≤ 55，正文是 69）的行＝经文框与页底脚注；页眉一并是小字，去掉。"""
    import html as H
    src = C.HOCR.read_text(encoding='utf-8', errors='ignore')
    toks = []
    for pi, page in enumerate(re.split(r"<div class=.ocr_page", src)[1:]):
        for m in re.finditer(r'<span class="ocr_line"[^>]*title="([^"]*)"(.*?)</span>\s*</span>', page, re.S):
            xs = re.search(r'x_size (\d+)', m.group(1))
            if not xs or int(xs.group(1)) > 55:
                continue
            ws = [(H.unescape(w).strip(), tuple(map(int, b.split()))) for b, w in
                  re.findall(r'class="ocrx_word"[^>]*title="bbox (\d+ \d+ \d+ \d+)[^"]*">([^<]*)', m.group(2))]
            if not ws or C.RUNHEAD.match(' '.join(w for w, _ in ws)):
                continue
            for w, b in ws:
                toks.append([w, (pi,) + b])
    out = []
    i = 0
    while i < len(toks):
        w, b = toks[i]
        if re.search(r'[a-z]-$', w) and i + 1 < len(toks):
            w = w[:-1] + toks[i + 1][0]
            i += 1
        if C.key(w):
            out.append((C.key(w), w, b))
        i += 1
    return out


if __name__ == '__main__' and '--build' not in sys.argv:
    K = kjv_words()
    O = box_tokens()
    sm = difflib.SequenceMatcher(None, [C.key(w[2]) for w in K], [o[0] for o in O], autojunk=False)
    pairs = Counter()
    rows = []
    for tag, a1, a2, b1, b2 in sm.get_opcodes():
        if tag == 'replace' and a2 - a1 == b2 - b1 and a2 - a1 <= 3:
            for i, j in zip(range(a1, a2), range(b1, b2)):
                pairs[(C.key(K[i][2]), O[j][0])] += 1
                rows.append((f'{K[i][0]}:{K[i][1]}', 'rep', str(i), K[i][2], O[j][1], ' '.join(map(str, O[j][2]))))
        elif tag in ('insert', 'delete') and max(a2 - a1, b2 - b1) <= 3:
            j = min(b1, len(O) - 1)
            i = min(a1, len(K) - 1)
            rows.append((f'{K[i][0]}:{K[i][1]}', 'ins' if tag == 'insert' else 'del', str(a1),
                         ' '.join(w[2] for w in K[a1:a2]), ' '.join(o[1] for o in O[b1:b2]), ' '.join(map(str, O[j][2]))))
    matched = sum(b.size for b in sm.get_matching_blocks())
    print(f'钦定本 {len(K)} 词，对上 {matched}')
    with DIFFS.open('w', encoding='utf-8') as f:
        f.write('cv\top\tk_idx\tkjv\tocr1857\tpage_bbox\n')
        for r in rows:
            f.write('\t'.join(r) + '\n')
    for k, n in pairs.most_common(120):
        print(n, k)


# ── 生成 1857 经文框 ─────────────────────────────────────────────
# 看图核过的替换（钦定本键, 1857 键）。按位：只在对齐上、OCR 恰为该词处换。
ACCEPT = {('publick', 'public'), ('axe', 'ax'), ('cloke', 'cloak'), ('neighbour', 'neighbor'),
          ('labourers', 'laborers'), ('labour', 'labor'), ('honour', 'honor'), ('hungred', 'hungered'),
          ('lunatick', 'lunatic'), ('woe', 'wo'), ('further', 'farther'),
          ('ye', 'you'), ('at', 'in'), ('oft', 'often'), ('saith', 'said'), ('that', 'which')}
# 成族、1857 经文框里英式写法对齐上 0 次的：未对上的位置也一并换
FAMILY = {'publick': 'public', 'lunatick': 'lunatic', 'cloke': 'cloak', 'neighbour': 'neighbor',
          'labourers': 'laborers', 'labourer': 'laborer', 'labour': 'labor', 'honour': 'honor', 'woe': 'wo'}
ONE_OFF = {'ye', 'at', 'oft', 'saith', 'that', 'hungred', 'further'}   # 只认对齐那一处


def build():
    K = kjv_words()
    O = box_tokens()
    sm = difflib.SequenceMatcher(None, [C.key(w[2]) for w in K], [o[0] for o in O], autojunk=False)
    words = [w[2] for w in K]
    eq = Counter()
    for b in sm.get_matching_blocks():
        for i in range(b.a, b.a + b.size):
            eq[C.key(K[i][2])] += 1
    changed = []
    for tag, a1, a2, b1, b2 in sm.get_opcodes():
        if tag == 'replace' and a2 - a1 == b2 - b1:
            for i, j in zip(range(a1, a2), range(b1, b2)):
                kk, ok = C.key(K[i][2]), O[j][0]
                if (kk, ok) in ACCEPT:
                    new = re.sub(r'[A-Za-z]+', lambda m: (ok[:1].upper() + ok[1:]) if m.group(0)[:1].isupper() else ok,
                                 words[i], count=1)
                    changed.append((f'{K[i][0]}:{K[i][1]}', words[i], new))
                    words[i] = new
    for i, w in enumerate(words):
        kk = C.key(w)
        if kk in FAMILY and eq[kk] == 0:
            new = re.sub(r'[A-Za-z]+', lambda m: (FAMILY[kk][:1].upper() + FAMILY[kk][1:])
                         if m.group(0)[:1].isupper() else FAMILY[kk], w, count=1)
            changed.append((f'{K[i][0]}:{K[i][1]}', w, new))
            words[i] = new
    for kk in FAMILY:
        if eq[kk]:
            print(f'⚠️ {kk} 在 1857 经文框里也有对上原样的 {eq[kk]} 处，未整族换')
    verses = {}
    for (c, v, _, it), w in zip(K, words):
        verses.setdefault(f'{c}:{v}', []).append(f'*{w}*' if it else w)
    out = {}
    for cv, ws in verses.items():
        s = ' '.join(ws)
        s = re.sub(r'\*\s+\*', ' ', s)          # 相邻斜体词并成一段
        s = re.sub(r'\*([^*]*?)([,.;:?!]+)\*', r'*\1*\2', s)   # 斜体不含句末标点
        out[cv] = s
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'{len(out)} 节，改 {len(changed)} 处 → {OUT}')
    for r in changed:
        print('  ', *r)


if __name__ == '__main__' and '--build' in sys.argv:
    build()
