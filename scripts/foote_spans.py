#!/usr/bin/env python3
"""福特《路加福音讲义》两条字流按**片段**挑读得对的那一条（skill old-book-ocr §3.2d 缩到片段级）。

扫描件局部受损时，ABBYY 会把长段里的一截读废（第 86 讲 p.637、第 128 讲 p.529/542、第 120 讲 p.418），
平摊到整段非词率只有 5–13%，按段判（foote_streams.py）看不见；一截里错词成片，逐词判读找不到锚也救不回。

做法：整段与 tesseract 同几页的词序列对齐，取长度 ≥3、位移一致的匹配块当锚；两个相邻锚之间那一截：

  我们这截 ≥2 个非词且占 ≥40%        —— 确实读废了
  tesseract 那截全是真词              —— 换过去的本身干净
  两截词数比 0.6–1.6、各 ≤ 25 词      —— 不许换成吞词／多词的那条
  这一截不跨段、无斜体标记、无脚注哨兵 —— tesseract 没有格式

两侧锚都要对上（这就是另一侧确认），锚撞车读出隔壁的话过不了位移一致这道。
落成 foote_raw/luke/span_swaps.tsv（讲次、左锚三词、原截、新截），`--apply` 每讲从后往前、须恰好命中一次。
链条位置：repair 之后、adjudicate 之前（两张证人表按换后的文本判）。

    python3 scripts/foote_spans.py            # 判 → 表 + logs/foote_spans.tsv
    python3 scripts/foote_spans.py --apply
"""
import argparse
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
RULES = RAW / 'span_swaps.tsv'
LOG = ROOT / 'logs' / 'foote_spans.tsv'
FN_MARK = ''
WORD = re.compile(r"[A-Za-z][A-Za-z'’]*")
PARA = re.compile(r'<!-- PAGE (\S*) -->\n(.*?)(?=\n\n|\Z)', re.S)
MAXW = 25


def inv_pages(vol):
    d = json.load(open(RAW / 'src' / f'{F.VOLS[vol]}_page_numbers.json'))
    return {str(x['pageNumber']): x['leafNum'] for x in d['pages'] if x.get('pageNumber')}


def tess_text(vol, leaf, n=4):
    parts = [(TESS / f'v{vol}' / f'{l:04d}.txt') for l in range(leaf, leaf + n)]
    t = '\n'.join(p.read_text(encoding='utf-8') for p in parts if p.exists())
    return re.sub(r'([A-Za-z])-\s*\n\s*([a-z])', r'\1\2', t)


def norm(s):
    s = re.sub(r"[‘’]", "'", s)
    s = re.sub(r'[“”]', '"', s)
    return re.sub(r'\s+', ' ', s).strip()


def real(w, lex):
    return all(is_word(x, lex) for x in re.split(r"['’]", w) if x)


def corpus_counts():
    from collections import Counter
    c = Counter()
    for f in SRC.glob('*.md'):
        c.update(w.lower() for w in WORD.findall(f.read_text(encoding='utf-8')))
    return c


def judge():
    kjv = foote_kjv_words()
    lex = build() | kjv
    vocab = corpus_counts()
    inv = {v: inv_pages(v) for v in (1, 2, 3)}
    rules, log = [], []
    stat = dict(swap=0, cleanboth=0, tessdirty=0, ratio=0, marked=0)
    for n in range(1, 138):
        vol = next(v for v in (1, 2, 3) if F.FIRST_LECT[v] <= n <= F.LAST_LECT[v])
        body = (SRC / f'{n:03d}.md').read_text(encoding='utf-8').partition('\n---\n')[0]
        for m in PARA.finditer(body):
            page, para = m.group(1), m.group(2)
            ot = list(WORD.finditer(para))
            if len(ot) < 8 or sum(1 for x in ot if not real(x.group(0), lex)) < 2:
                continue
            leaf = inv[vol].get(page)
            if leaf is None:
                continue
            tt = tess_text(vol, leaf)
            tm = list(WORD.finditer(tt))
            ow = [x.group(0).lower() for x in ot]
            tw = [x.group(0).lower() for x in tm]
            blocks = [b for b in SequenceMatcher(None, ow, tw, autojunk=False).get_matching_blocks() if b.size >= 3]
            for b1, b2 in zip(blocks, blocks[1:]):
                a0, a1 = b1.a + b1.size, b2.a
                t0, t1 = b1.b + b1.size, b2.b
                if a1 <= a0 or t1 <= t0 or a1 - a0 > MAXW or t1 - t0 > MAXW:
                    continue
                # 位移一致：两锚之间的错位不得太大（锚撞车）
                if abs((b2.b - b2.a) - (b1.b - b1.a)) > 6:
                    continue
                ours = ow[a0:a1]
                bad = sum(1 for k in range(a0, a1) if not real(ot[k].group(0), lex))
                if bad < 2 or bad / len(ours) < 0.4:
                    stat['cleanboth'] += 1
                    continue
                if any(not real(tm[k].group(0), lex) for k in range(t0, t1)):
                    stat['tessdirty'] += 1
                    log.append((f'{n:03d}', para[ot[a0].start():ot[a1 - 1].end()], tt[tm[t0].start():tm[t1 - 1].end()], 'tessdirty'))
                    continue
                if not (0.6 <= (t1 - t0) / (a1 - a0) <= 1.6):
                    stat['ratio'] += 1
                    continue
                old = para[ot[a0].start():ot[a1 - 1].end()]
                if '\n' in old or FN_MARK in old or re.search(r'(?<!\\)\*', old):
                    stat['marked'] += 1
                    continue
                raw_t = tt[tm[t0].start():tm[t1 - 1].end()]
                tws = [tm[k].group(0).lower() for k in range(t0, t1)]
                # 闸（220 处抽查后加）：
                #   页眉混入（`… LUKE IV`）／我们本来对的词不许被换掉（It→I）／数字不许丢（xxiiL 7→xxiii）／
                #   tesseract 给的词须是本书常见词或钦定本词（theer 是生僻真词）
                why = None
                if re.search(r'\b(LUKE|LECTURE)\b', raw_t) and not re.search(r'\b(LUKE|LECTURE)\b', old):
                    why = 'runhead'
                elif any(real(ot[k].group(0), lex) and len(ot[k].group(0)) >= 2 and ow[k] not in tws for k in range(a0, a1)):
                    why = 'realword'
                elif sorted(re.findall(r'\d+', old)) != sorted(re.findall(r'\d+', raw_t)):
                    why = 'digits'
                elif any(vocab[w] < 2 and w not in kjv for w in tws):
                    why = 'rareword'
                elif any(len(w) == 1 and w not in ('a', 'i', 'o') for w in tws):
                    why = 'single'            # 单字母多是脚注 † 读成 f/t（fea^ts → feasts;"f）
                elif len(tws) < sum(1 for k in range(a0, a1) if len(ow[k]) >= 3):
                    why = 'dropword'          # measore, in the penrerted → measure, in the（吞了 perverted）
                elif SequenceMatcher(None, re.sub('[^a-z]', '', ' '.join(ours)),
                                     re.sub('[^a-z]', '', ' '.join(tws))).ratio() < 0.5:
                    why = 'unlike'
                if why:
                    stat[why] = stat.get(why, 0) + 1
                    log.append((f'{n:03d}', old, raw_t, why))
                    continue
                new = norm(raw_t)
                anchor = ' '.join(x.group(0) for x in ot[max(0, a0 - 3):a0])
                rules.append((f'{n:03d}', anchor, old, new))
                log.append((f'{n:03d}', old, new, 'swap'))
                stat['swap'] += 1
    with open(RULES, 'w', encoding='utf-8') as f:
        f.write('# lecture\tanchor(左三词)\told\tnew —— foote_spans.py 生成；每讲从后往前落\n')
        for r in rules:
            f.write('\t'.join(r) + '\n')
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('lecture\tours\ttess\tkind\n')
        for r in log:
            f.write('\t'.join(x.replace('\t', ' ').replace('\n', ' ') for x in r) + '\n')
    print('片段换流：', stat, file=sys.stderr)


def apply():
    by = {}
    for ln in RULES.read_text(encoding='utf-8').splitlines():
        if ln.strip() and not ln.startswith('#'):
            lec, anchor, old, new = ln.split('\t')
            by.setdefault(lec, []).append((anchor, old, new))
    done = already = 0
    bad = []
    for lec, rs in by.items():
        path = SRC / f'{lec}.md'
        text = path.read_text(encoding='utf-8')
        for anchor, old, new in reversed(rs):
            # 锚词之间原文可能夹着符号（`synagogue^ when`），锚按词拼成宽松式
            apat = r'[^A-Za-z]{1,12}'.join(re.escape(w) for w in anchor.split())
            pat = apat + r'([^A-Za-z]{1,12})' + re.escape(old) if anchor else re.escape(old)
            hits = list(re.finditer(pat, text))
            if len(hits) == 1:
                h = hits[0]
                s = h.end() - len(old)
                text = text[:s] + new + text[h.end():]
                done += 1
            elif not hits and re.search((apat + r'[^A-Za-z]{1,12}' if anchor else '') + re.escape(new), text):
                already += 1
            else:
                bad.append((lec, anchor, old[:30], len(hits)))
        path.write_text(text, encoding='utf-8')
    print(f'片段换流落盘 {done}；已落过 {already}；定位失败 {len(bad)} {bad[:4]}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    apply() if a.apply else judge()


if __name__ == '__main__':
    main()
