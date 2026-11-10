#!/usr/bin/env python3
"""Vos 文章斜体体检：在原刊页图上逐词量字形倾斜角，与发布稿的 *斜体* 标记比对。

扫描 OCR 不带字体信息，录入本漏标/多标的斜体靠文字比对查不出来。这里对 djvu.xml 每个词的框
做错切搜索：把字形按 -26°…+6° 逐度错切，取竖直投影方差最大的角度（竖笔对齐最好）。
正体竖笔直立，最佳角≈0；斜体实测落在 -8° 以下（本函数的符号约定下）。v/w/y 等斜笔字母多的词
会被误判，判定时排除含这些字母的短词。初版只搜到 +6°，真斜体全卡在边界上（实测）。

产物：vos_raw/psalter/italic_audit.tsv —— 两边不一致的连续词组（页码、发布稿上下文、扫描判定、平均倾角）。
只输出疑点，不改稿；疑点须看图读定后落 corrections.tsv。
"""
import difflib
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'vos_raw' / 'psalter'
SRC = RAW / 'src'


def slant(img):
    a = np.asarray(img, dtype=np.float32)
    ink = (a < a.mean() - 0.35 * a.std()).astype(np.float32)
    h, w = ink.shape
    if h < 12 or w < 12 or ink.sum() < 40:
        return None
    ys = np.arange(h) - h / 2
    best, best_v = 0, -1
    for deg in range(-26, 27):
        t = np.tan(np.radians(deg))
        cols = np.zeros(w + 2 * h, dtype=np.float32)
        for y in range(h):
            row = ink[y]
            if not row.any():
                continue
            off = int(round(h + ys[y] * t))          # 上方的行往左挪（deg<0 把右倾拉直）
            cols[off:off + w] += row
        v = cols.var()
        if v > best_v:
            best_v, best = v, deg
    return -best                                     # 右倾为正


def scan_words():
    x = (SRC / 'ptr_djvu.xml').read_text(encoding='utf-8')
    out = []
    for o in re.findall(r'<OBJECT[^>]*>.*?</OBJECT>', x, flags=re.S):
        leaf = int(re.search(r'_(\d{4})\.djvu', o).group(1))
        p = leaf - 2
        if not 1 <= p <= 43:
            continue
        img = Image.open(SRC / 'jp2' / f'{leaf:04d}.jp2').convert('L')
        for c, t in re.findall(r'<WORD coords="([^"]+)"[^>]*>([^<]*)</WORD>', o):
            l, b, r, tp = map(int, c.split(',')[:4])
            word = t.strip()
            if not re.search(r'[A-Za-z]{2,}', word):
                continue
            s = slant(img.crop((l, tp, r, b)))
            out.append({'p': p, 'w': word, 's': s})
    return out


def pub_tokens():
    md = (ROOT / 'vos' / 'psalter' / 'index.md').read_text(encoding='utf-8').split('---', 2)[2]
    md = re.sub(r'<div class="vs-source".*?</div>', '', md, flags=re.S)
    md = re.sub(r'<[^>]+>', '', md)
    md = re.sub(r'\[\^\d+\](?!:)', ' ', md)
    body, _, notes = md.partition('\n[^1]:')
    return _toks(body, 0) + _toks(notes, len(body)), md


def _toks(md, base):
    toks = []
    for m in re.finditer(r'\*[^*\n]+\*|[^*\s]+', md):
        seg = m.group()
        it = seg.startswith('*') and seg.endswith('*') and len(seg) > 2
        for w in re.findall(r"[A-Za-zÀ-ÿ']+", seg.strip('*')):
            if len(w) >= 2:
                toks.append({'w': w, 'it': it, 'ctx': base + m.start(), 'part': 'n' if base else 'b'})
    return toks


def norm(w):
    return re.sub(r'[^a-z]', '', w.lower())


def main():
    cache = RAW / 'italic_slant.json'
    if cache.exists():
        sw = json.loads(cache.read_text())
    else:
        sw = scan_words()
        cache.write_text(json.dumps(sw))
    toks, md = pub_tokens()
    B = [norm(re.sub(r'[^A-Za-zÀ-ÿ]', '', s['w'])) for s in sw]
    pairs = []
    for part in ('b', 'n'):                      # 正文、脚注分开对齐：发布稿脚注集中在文末，扫描本在各页页脚
        sub = [t for t in toks if t['part'] == part]
        sm = difflib.SequenceMatcher(None, [norm(t['w']) for t in sub], B, autojunk=False)
        for blk in sm.get_matching_blocks():
            if blk.size < 3:
                continue
            for k in range(blk.size):
                pairs.append((sub[blk.a + k], sw[blk.b + k]))
    vals = [s['s'] for _, s in pairs if s['s'] is not None]
    print(f'对齐 {len(pairs)}/{len(toks)} 词；倾角中位 {np.median(vals):.1f}°')
    # 连续不一致的词组
    rows, run = [], []
    def flush():
        if len(run) >= 1:
            ss = [s['s'] for _, s in run if s['s'] is not None]
            if ss:
                avg = sum(ss) / len(ss)
                pub_it = run[0][0]['it']
                # 单词长度 ≤3 的孤立词倾角不稳，要求组里至少一个 ≥4 字母词
                if any(len(t['w']) >= 4 for t, _ in run) and ((avg <= -9 and not pub_it) or (avg >= -3 and pub_it)):
                    c = run[0][0]['ctx']
                    rows.append((run[0][1]['p'], 'scan=italic pub=roman' if not pub_it else 'scan=roman pub=italic',
                                 f'{avg:.1f}', ' '.join(t['w'] for t, _ in run),
                                 md[max(0, c - 50):c + 60].replace('\n', ' ')))
    for t, s in pairs:
        if s['s'] is not None and not t['it'] and len(t['w']) <= 5 and re.search(r'[vwyVWYkxz]', t['w']):
            flush(); run = []; continue           # 斜笔字母多的短词倾角不可信
        italic_scan = s['s'] is not None and s['s'] <= -7
        if italic_scan != t['it']:
            run.append((t, s))
        else:
            flush(); run = []
    flush()
    with (RAW / 'italic_audit.tsv').open('w', encoding='utf-8') as f:
        f.write('# page\tkind\tavg_slant\twords\tcontext\n')
        for r in rows:
            f.write('\t'.join(map(str, r)) + '\n')
    print(f'疑点 {len(rows)} 组 → vos_raw/psalter/italic_audit.tsv')


if __name__ == '__main__':
    main()
