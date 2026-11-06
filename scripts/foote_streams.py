#!/usr/bin/env python3
"""福特《路加福音讲义》两条字流按段挑读得对的那一条（skill old-book-ocr §3.2d）。

正文的字一向取 ABBYY 一条流；可扫描件局部受损时，ABBYY 会在某几段上整段读废
（第 128 讲 p.529、第 86 讲 p.637 一段几乎每个词都是乱码），逐词判读救不回来——锚都找不到。
tesseract 重扫（foote_tesseract.py）同一处往往是干净的。页级判据看不见它（整页非词率被正常段拉平），
所以**按段**比：

  ABBYY 段非词率 − tesseract 段非词率 ≥ 0.20
  tesseract 段非词率 ≤ 0.05（换过去的本身得干净）
  tesseract 段词数 ≥ ABBYY 段的 0.8（不许换成吞了词的那条）
  段内无脚注标号、无斜体（tesseract 没有格式，换了会丢）

定位：印刷页码 → IA 页码表反查扫描页序 → 取该页起三页的 tesseract 文本，按词序列对齐，
取最长匹配块当锚（skill §3.2 ①），由首尾匹配块推出 tesseract 里同一段话的起止。
换过来的文字顺手归一：直引号、行内多空格、行末断词接上。

判决落成 foote_raw/luke/stream_swaps.tsv（讲次、原段 md5、新文），`--apply` 按 md5 换，
排在 repair 之后、adjudicate 之前（两张证人表要按换流后的文本判）。

    python3 scripts/foote_streams.py            # 判 → 表 + logs/foote_streams.tsv
    python3 scripts/foote_streams.py --apply
"""
import argparse
import hashlib
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_foote as F  # noqa: E402
from alexander_lexicon import build, is_word  # noqa: E402
from repair_alexander_ocr import foote_kjv_words  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'foote_raw' / 'luke'
SRC = RAW / 'en_chapters'
TESS = RAW / 'tess'
RULES = RAW / 'stream_swaps.tsv'
LOG = ROOT / 'logs' / 'foote_streams.tsv'
FN_MARK = ''
WORD = re.compile(r"[A-Za-z][A-Za-z'’]*")
PARA = re.compile(r'(<!-- PAGE (\S*) -->\n)(.*?)(?=\n\n|\Z)', re.S)


def md5(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()[:16]


def inv_pages(vol):
    d = json.load(open(RAW / 'src' / f'{F.VOLS[vol]}_page_numbers.json'))
    return {str(x['pageNumber']): x['leafNum'] for x in d['pages'] if x.get('pageNumber')}


def tess_pages(vol, leaf, n=3):
    parts = []
    for l in range(leaf, leaf + n):
        p = TESS / f'v{vol}' / f'{l:04d}.txt'
        if p.exists():
            parts.append(p.read_text(encoding='utf-8'))
    t = '\n'.join(parts)
    t = re.sub(r'([A-Za-z])-\s*\n\s*([a-z])', r'\1\2', t)
    return t


def nonword(words, lex):
    ws = [w for w in words if len(w) >= 2]
    if not ws:
        return 1.0
    return sum(1 for w in ws if not all(is_word(x, lex) for x in re.split(r"['’]", w) if x)) / len(ws)


def norm_text(s):
    s = re.sub(r"[‘’]", "'", s)
    s = re.sub(r'[“”]', '"', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def judge():
    lex = build() | foote_kjv_words()
    inv = {v: inv_pages(v) for v in (1, 2, 3)}
    rules, log = [], []
    stat = dict(swap=0, nolocate=0, keep=0, marked=0)
    for n in range(1, 138):
        vol = next(v for v in (1, 2, 3) if F.FIRST_LECT[v] <= n <= F.LAST_LECT[v])
        body = (SRC / f'{n:03d}.md').read_text(encoding='utf-8').partition('\n---\n')[0]
        for m in PARA.finditer(body):
            page, para = m.group(2), m.group(3)
            pw = WORD.findall(para)
            if len(pw) < 12:
                continue
            nw_a = nonword(pw, lex)
            if nw_a < 0.20:
                continue
            if FN_MARK in para or re.search(r'(?<!\\)\*', para):
                stat['marked'] += 1
                log.append((f'{n:03d}', page, f'{nw_a:.2f}', '', 'marked'))
                continue
            leaf = inv[vol].get(page)
            if leaf is None:
                stat['nolocate'] += 1
                continue
            tt = tess_pages(vol, leaf)
            tm = list(WORD.finditer(tt))
            tw = [x.group(0).lower() for x in tm]
            sm = SequenceMatcher(None, [w.lower() for w in pw], tw, autojunk=False)
            blocks = [b for b in sm.get_matching_blocks() if b.size]
            if not blocks:
                stat['nolocate'] += 1
                continue
            big = max(blocks, key=lambda b: b.size)
            if big.size < 3:
                stat['nolocate'] += 1
                log.append((f'{n:03d}', page, f'{nw_a:.2f}', '', 'nolocate'))
                continue
            # 只收锚附近、位移一致的块（防止 of/the 之类撞到别处）
            off = big.b - big.a
            near = [b for b in blocks if abs((b.b - b.a) - off) <= 6]
            first, last = near[0], near[-1]
            t0 = max(0, first.b - first.a)
            t1 = min(len(tm), last.b + last.size + (len(pw) - (last.a + last.size)))
            if t1 <= t0:
                stat['nolocate'] += 1
                continue
            seg = tt[tm[t0].start():tm[t1 - 1].end()]
            sw = WORD.findall(seg)
            nw_b = nonword(sw, lex)
            ok = nw_a - nw_b >= 0.20 and nw_b <= 0.05 and len(sw) >= 0.8 * len(pw)
            log.append((f'{n:03d}', page, f'{nw_a:.2f}', f'{nw_b:.2f}', 'swap' if ok else 'keep'))
            if not ok:
                stat['keep'] += 1
                continue
            # 段尾标点：tesseract 段止于最后一个词，补回它后面紧跟的标点
            tail = re.match(r'[^\sA-Za-z]{0,3}', tt[tm[t1 - 1].end():]).group(0)
            new = norm_text(seg + tail)
            rules.append((f'{n:03d}', md5(para), new))
            stat['swap'] += 1
    with open(RULES, 'w', encoding='utf-8') as f:
        f.write('# lecture\tmd5(原段)\t新文(tesseract) —— foote_streams.py 生成\n')
        for r in rules:
            f.write('\t'.join(r) + '\n')
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('lecture\tpage\tnw_abbyy\tnw_tess\tkind\n')
        for r in log:
            f.write('\t'.join(r) + '\n')
    print('按段换流：', stat, file=sys.stderr)


def apply():
    by = {}
    for ln in RULES.read_text(encoding='utf-8').splitlines():
        if ln.strip() and not ln.startswith('#'):
            lec, h, new = ln.split('\t')
            by.setdefault(lec, {})[h] = new
    done = already = 0
    for lec, mp in by.items():
        path = SRC / f'{lec}.md'
        text = path.read_text(encoding='utf-8')
        body, sep, notes = text.partition('\n---\n')
        news = set(mp.values())

        def rep(m):
            nonlocal done, already
            h = md5(m.group(3))
            if h in mp:
                done += 1
                return m.group(1) + mp[h]
            if m.group(3) in news:
                already += 1
            return m.group(0)
        body = PARA.sub(rep, body)
        path.write_text(body + sep + notes, encoding='utf-8')
    total = sum(len(v) for v in by.values())
    print(f'换流落盘 {done}；已落过 {already}；共 {total}', file=sys.stderr)
    if done + already != total:
        raise SystemExit('有换流规则没找到原段（上游改过？）')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    apply() if a.apply else judge()


if __name__ == '__main__':
    main()
