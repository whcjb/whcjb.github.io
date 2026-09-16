#!/usr/bin/env python3
"""引号多出来 / 少一个的地方——按段落配对算账，再拿 1850 三卷本按位置判。

这一类前面几道闸一个也看不见：
  · `psalms_backlog.py` 按空白分段找非词，`"We` 里 `We` 是好词
  · `psalms_double_punct.py` 只管 `,;:.`，不管引号
  · 斜体自检只数 `*`
可它们是实打实的错，而且读者一眼就看得见。实读诗 134 时撞见的：
「the priests concluded. "We may then assume」——影像上那里根本没有引号。

来路是 1864 那副字模的 `W`：OCR 常把它左边那一竖连同前面的词距读成一个 `"`，
于是 `We / While / With / When / Why / Who` 前面凭空多出一个引号。
另有几处是连字被读成引号：`sufi"ers`=suffers、`fu"st`=first、`off"enders`=offenders。

判法与残留串、双标点同一套：拿 1850 三卷本按位置读出那一处的**原文切片连标点**，
**只接受引号级的改动**——两边剥掉引号之后必须逐字相同，否则一律不采信。
这样证人只能告诉我们「这里有没有引号」，不可能顺手改词。

段落里引号本来就可能跨段（他引一整段圣经），所以只查**段内配对不上**的段落。

用法：
    python3 scripts/psalms_quote_marks.py            # 只报告
    python3 scripts/psalms_quote_marks.py --apply
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_alexander_image as A
from psalms_residue_witness import (ANCHOR, MAX_HITS, REACH, TAIL, WORD,
                                    load_witness, slice_at)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
FIXES = ROOT / 'alexander_raw/psalms/manual_fixes.tsv'
OUT = ROOT / 'logs/alexander_psalms_quotes.tsv'
HEB = re.compile(r'[֐-׿Ͱ-Ͽἀ-῿]')
QUOTE = '"“”'


def core(s):
    """比对用的芯：剥掉引号和空白，其余逐字保留。"""
    return re.sub(r'[\s"“”]', '', s)


def scan():
    """段内引号配对不上的地方，逐个引号连同挨着它的那个词。"""
    out = []
    for sec in ['preface'] + [str(i) for i in range(1, 151)]:
        p = SRC / f'{sec}.md'
        if not p.exists():
            continue
        raw = p.read_text(encoding='utf-8')
        start = raw.find('<!-- PAGE ')
        if start < 0:
            continue
        masked = A._mask_markup(raw)
        toks = [(m.group(0), m.start(), m.end()) for m in WORD.finditer(masked)]
        body = masked[start:]
        # 段落边界按空行切，位置换算回整篇
        pos = start
        for para in body.split('\n\n'):
            if para.count('"') % 2:
                for m in re.finditer('"', para):
                    at = pos + m.start()
                    if HEB.search(masked[max(0, at - 8):at + 8]):
                        continue                    # 希伯来乱码里的引号另案
                    k = nearest(toks, at)
                    if k is None:
                        continue
                    out.append(dict(sec=sec, raw=raw, masked=masked, toks=toks,
                                    tok=k, at=at))
            pos += len(para) + 2
    return out


def nearest(toks, at):
    """挨着这个引号的词：优先右边（`"We`），没有就取左边（`off"` ）。"""
    for k, t in enumerate(toks):
        if t[1] >= at:
            if t[1] - at <= 1:
                return k
            return k - 1 if k else None
    return None


def span_of(raw, toks, k, at):
    """连着这个词和这个引号的一整串（含中间的引号与空白）。"""
    a, b = toks[k][1], toks[k][2]
    return raw[min(a, at):max(b, at + 1)]


def judge(it, wtext, wtoks, widx):
    toks, k = it['toks'], it['tok']
    low = [t[0].lower() for t in toks]
    reads = {}
    for start in list(range(k - REACH, k - ANCHOR + 1)) + list(range(k + 1, k + 1 + REACH)):
        if start < 0 or start + ANCHOR > len(toks):
            continue
        if not (start + ANCHOR <= k or start > k):
            continue
        hits = widx.get(tuple(low[start:start + ANCHOR]))
        if not hits or len(hits) > MAX_HITS:
            continue
        d = k - start
        cand = set()
        for p in hits:
            j = p + d
            if 0 <= j < len(wtoks):
                cand.add(wide_slice(wtext, wtoks, j))
        if len(cand) == 1:
            reads[start] = cand.pop()
    vals = set(reads.values())
    if not vals:
        return None, '证人语料里找不到这段话'
    if len(vals) > 1:
        return None, f'几个锚读数不一致：{sorted(vals)[:3]}'
    return vals.pop(), f'{len(reads)} 个锚一致'


def wide_slice(text, toks, j):
    """证人在这个词上印的原文，**两头**都把引号和紧贴的标点带上。"""
    a, b = toks[j][1], toks[j][2]
    while a > 0 and text[a - 1] in QUOTE + ' ':
        if text[a - 1] == ' ' and not (a > 1 and text[a - 2] in QUOTE):
            break
        a -= 1
    while b < len(text) and text[b] in TAIL + QUOTE:
        b += 1
    return text[a:b].strip()


def main(apply=False):
    wtext, wtoks, wlow, widx = load_witness()
    items = scan()
    print(f'段内引号配对不上的地方 {len(items)} 处')
    stat, rows, add = Counter(), [], []
    for it in items:
        span = span_of(it['raw'], it['toks'], it['tok'], it['at'])
        read, why = judge(it, wtext, wtoks, widx)
        if read is None:
            stat['证人给不出'] += 1
            rows.append((it['sec'], span, '', why))
            continue
        if core(read) != core(span):
            stat['芯对不上'] += 1
            rows.append((it['sec'], span, read, '剥掉引号后不一致，不采信'))
            continue
        # 只准动引号：把读数里的引号情况套到我们这一串上
        if read.count('"') == span.count('"'):
            stat['证人也这样'] += 1
            rows.append((it['sec'], span, read, '证人印的就是这样'))
            continue
        if read.count('"') > span.count('"'):
            stat['证人多一个引号'] += 1        # 我们少了——补引号风险大，留账
            rows.append((it['sec'], span, read, '证人比我们多引号，留给影像'))
            continue
        new = span.replace('"', '')
        if new != span.strip() and new.strip() != new:
            new = new.strip()
        new = re.sub(r'\s+', ' ', new).strip()
        stat['可删'] += 1
        rows.append((it['sec'], span, new, why))
        add.append((it, span, new))
    print('，'.join(f'{k} {v}' for k, v in stat.most_common()))
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open('w', encoding='utf-8') as fh:
        fh.write('篇\t我们\t改成\t说明\n')
        for r in rows:
            fh.write('\t'.join(r) + '\n')
    print(f'逐条 → {OUT}')
    if not apply:
        for it, span, new in add:
            print(f'  [{it["sec"]}] {span!r} → {new!r}')
        return
    n = skip = 0
    with FIXES.open('a', encoding='utf-8') as fh:
        for it, span, new in add:
            p = SRC / f'{it["sec"]}.md'
            t = p.read_text(encoding='utf-8')
            old, rep = span, new
            if t.count(old) != 1:
                head = it['raw'][max(0, min(it['toks'][it['tok']][1], it['at']) - 18):
                                 min(it['toks'][it['tok']][1], it['at'])]
                old, rep = head + old, head + rep
                if t.count(old) != 1:
                    skip += 1
                    continue
            fh.write(f'{it["sec"]}\t{old}\t{rep}\twitness1850: 引号级，证人按位置读出\n')
            p.write_text(t.replace(old, rep, 1), encoding='utf-8')
            n += 1
    print(f'落盘 {n} 处，定位不唯一跳过 {skip} 处')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    main(ap.parse_args().apply)
