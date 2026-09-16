#!/usr/bin/env python3
"""残留串里的**标点级**错——拿 1850 三卷本按位置读出来。

复扫剩下的 165 处，一多半长这样：`declare^`、`Jehovah^`、`w^ord`、`the^pollution`、
`Deut.^xxv`。词本身是对的，崩掉的是词旁边那个符号：`^` 底下压着的是逗号、
句号，或者根本什么都没有（只是纸上的一个脏点）。

这类错 `adjudicate_alexander_ocr.py` 一辈子也碰不到——它的 TOKEN 正则只认字母，
`declare^` 在它眼里就是个好词 `declare`。而影像判读一处一裁图，76 处要裁 76 张。
第二证人是现成的，而且免费：同一段话 1850 三卷本也印了一遍，把那一处的
**原文切片连标点**读出来就行。

安全闸只有一条，但足够硬：**只接受标点级的改动**。证人切片与我们这串
剥掉所有非字母字符之后必须逐字相同，否则一律不采信。这样证人既能告诉我们
`^` 底下是逗号还是句号，又不可能顺手把词改掉——它读崩的地方（这本书的两份
OCR 常在同一处一起崩）会因为字母对不上而自动出局。

锚：目标串前后各取若干词做 3-gram，命中处必须给出一致的切片；
左右两侧都试，任何一侧给出唯一且一致的读数就采信，两侧都给且不一致则作废。

用法：
    python3 scripts/psalms_residue_witness.py             # 只报告
    python3 scripts/psalms_residue_witness.py --apply     # 追加进 manual_fixes.tsv 并落盘
"""
import argparse
import pickle
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_alexander_image as A
import alexander_lexicon as L

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
WITNESS = [ROOT / f'alexander_raw/psalms/src/pages{v}.pkl' for v in ('01', '02', '03')]
FIXES = ROOT / 'alexander_raw/psalms/manual_fixes.tsv'
PRINTED = ROOT / 'alexander_raw/psalms/printed_as_is.txt'
OUT = ROOT / 'logs/alexander_psalms_residue_witness.tsv'

# 数字也要算一个词：`xvii.28.` 里的 28 不算词的话，证人切片只覆盖 xvii，
# 拿它去换整串就把「28」悄悄删掉了（试跑时 6 处这样，全是经文出处的节号）。
WORD = re.compile(r"[A-Za-z][A-Za-z'’]*|[0-9]+")
ANCHOR = 3          # 几个词做一个锚
REACH = 5           # 目标串前后各在几个词的窗口里找锚
MAX_HITS = 40       # 锚在证人语料里命中超过这个数就太泛，不用
TAIL = ',.;:!?)\'"'  # 词后面这些符号算这一串的一部分


def letters(s):
    """比对用的芯：字母**和数字**，标点全剥掉。

    只比字母是不够的——证人切片少一截数字照样能过闸，节号就这么丢了。
    """
    return re.sub(r'[^A-Za-z0-9]', '', s).lower()


def load_witness():
    chunks = []
    for path in WITNESS:
        for page in pickle.load(open(path, 'rb')):
            for par in page['pars']:
                chunks.append(''.join(c for c in par['text']
                                      if unicodedata.category(c) != 'Co'))
    text = '\n'.join(chunks)
    toks = [(m.group(0), m.start(), m.end()) for m in WORD.finditer(text)]
    low = [t[0].lower() for t in toks]
    idx = defaultdict(list)
    for i in range(len(low) - ANCHOR):
        idx[tuple(low[i:i + ANCHOR])].append(i)
    return text, toks, low, idx


def slice_at(text, toks, j0, j1):
    """证人在 [j0, j1] 这几个词上印的原文，连同紧跟其后的标点。"""
    a, b = toks[j0][1], toks[j1][2]
    while b < len(text) and text[b] in TAIL:
        b += 1
    return text[a:b]


def edition_risk(span, read):
    """这一处的分歧会不会是**两版排印不同**，而不是我们读崩了。

    证人是 1850 三卷本，1864 单卷本是作者自己改过的版子，标点不一定一样。
    只有「我们这串里明摆着有个 OCR 噪点」时，证人的读数才算是在告诉我们
    那个噪点底下印的是什么；换成两版可能本来就不同的地方，就不能听它的：

      · 串里带 `-`：1864 的引语用单引号，OCR 一半读成 `'`、一半读成 `-`
        （诗 118 同一句里两种都出现过），而 1850 那版根本不加引号。
        听证人的就会把真的引号删掉。
      · 读数里凭空多出引号：同理，反过来。
    """
    if '-' in span:
        return '带连字符/破折号，可能是 1864 的引号'
    if set(read) - set(span) & set('\'"\u2018\u2019\u201c\u201d'):
        return '读数里多出引号'
    return ''


def read_spans(vocab, asis):
    """重扫一遍正文，拿到每处残留串的**位置**（backlog 那张表只有上下文）。"""
    items = []
    for sec in ['preface'] + [str(i) for i in range(1, 151)]:
        p = SRC / f'{sec}.md'
        if not p.exists():
            continue
        raw = p.read_text(encoding='utf-8')
        start = raw.find('<!-- PAGE ')
        if start < 0:
            continue
        masked = A._mask_markup(raw)
        for m in A.SPAN.finditer(masked, start):
            bad, core = A._suspect(m.group(0), vocab)
            if not bad or core in asis or not letters(core):
                continue
            items.append(dict(sec=sec, raw=raw, masked=masked, span=m.group(0),
                              core=core, a=m.start(), b=m.end()))
    return items


def judge(it, wtext, wtoks, wlow, widx):
    """证人在这一处印的是什么。返回 (读数, 理由)。"""
    masked = it['masked']
    toks = [(m.group(0), m.start(), m.end()) for m in WORD.finditer(masked)]
    low = [t[0].lower() for t in toks]
    inside = [k for k, t in enumerate(toks) if t[1] >= it['a'] and t[2] <= it['b']]
    if not inside:
        return None, '串里没有完整的词'
    i0, i1 = inside[0], inside[-1]
    reads = {}
    for start in list(range(i0 - REACH, i0 - ANCHOR + 1)) + list(range(i1 + 1, i1 + 1 + REACH)):
        if start < 0 or start + ANCHOR > len(toks):
            continue
        if not (start + ANCHOR <= i0 or start > i1):      # 锚不能压在目标串上
            continue
        hits = widx.get(tuple(low[start:start + ANCHOR]))
        if not hits or len(hits) > MAX_HITS:
            continue
        d0, d1 = i0 - start, i1 - start
        cand = set()
        for p in hits:
            j0, j1 = p + d0, p + d1
            if 0 <= j0 <= j1 < len(wtoks):
                cand.add(slice_at(wtext, wtoks, j0, j1))
        if len(cand) == 1:
            reads[start] = cand.pop()
    if not reads:
        return None, '证人语料里找不到这段话'
    vals = set(reads.values())
    if len(vals) > 1:
        return None, f'几个锚读数不一致：{sorted(vals)[:3]}'
    return vals.pop(), f'{len(reads)} 个锚一致'


def main(apply=False):
    vocab = L.build()
    asis = set()
    if PRINTED.exists():
        for line in PRINTED.open(encoding='utf-8'):
            asis.update(line.split('#')[0].split())
    wtext, wtoks, wlow, widx = load_witness()
    print(f'证人词流 {len(wtoks)} 词')
    items = read_spans(vocab, asis)
    print(f'残留 {len(items)} 处')

    stat = Counter()
    rows = []
    for it in items:
        read, why = judge(it, wtext, wtoks, wlow, widx)
        # 边界归一：我们这串的**后面**如果已经跟着标点，证人切片尾巴上那个
        # 标点就不能再要——`xliii.4` 后面本来就是逗号，照抄证人的 `xliii. 4.`
        # 会写出 `xliii. 4.,`。同理 `saidst` 后面已经有逗号，证人的 `saidst,`
        # 剥完尾巴就与我们相同，根本不用改。这类双标点是**静默**的，
        # 落盘之前不归一，事后只能靠眼睛一处处捡。
        if read:
            nxt = it['raw'][it['b']] if it['b'] < len(it['raw']) else ''
            if nxt in ',.;:!?)':
                read = read.rstrip(TAIL)
        if read is None:
            stat['证人给不出'] += 1
            rows.append((it['sec'], it['span'], '', why))
            continue
        # 安全闸：只准动标点。字母对不上 → 两边有一边读崩了，不采信。
        if letters(read) != letters(it['span']):
            stat['字母对不上'] += 1
            rows.append((it['sec'], it['span'], read, '字母对不上，不采信'))
            continue
        if read == it['span']:
            stat['与我们相同'] += 1
            rows.append((it['sec'], it['span'], read, '证人印的就是这样'))
            continue
        hold = edition_risk(it['span'], read)
        if hold:
            stat['留给影像'] += 1
            rows.append((it['sec'], it['span'], read, f'留给影像：{hold}'))
            continue
        stat['可改'] += 1
        rows.append((it['sec'], it['span'], read, why))
    print('，'.join(f'{k} {v}' for k, v in stat.most_common()))

    OUT.parent.mkdir(exist_ok=True)
    with OUT.open('w', encoding='utf-8') as fh:
        fh.write('篇\t我们\t证人\t说明\n')
        for r in rows:
            fh.write('\t'.join(r) + '\n')
    print(f'逐条 → {OUT}')
    if not apply:
        return

    # 落盘：按篇定位，要求 old 在该篇唯一（不唯一就加前文锚）
    fixed = skipped = 0
    add = []
    for it, (sec, span, read, why) in zip(items, rows):
        if not read or read == span or letters(read) != letters(span):
            continue
        if not why.endswith('个锚一致'):        # 留给影像的那批不落盘
            continue
        t = (SRC / f'{sec}.md').read_text(encoding='utf-8')
        old, new = span, read
        if t.count(old) != 1:
            head = it['raw'][max(0, it['a'] - 16):it['a']]
            old, new = head + span, head + read
            if t.count(old) != 1:
                skipped += 1
                continue
        add.append((sec, old, new))
    with FIXES.open('a', encoding='utf-8') as fh:
        for sec, old, new in add:
            fh.write(f'{sec}\t{old}\t{new}\twitness1850: 标点级，证人按位置读出\n')
    for sec, old, new in add:
        p = SRC / f'{sec}.md'
        p.write_text(p.read_text(encoding='utf-8').replace(old, new, 1), encoding='utf-8')
        fixed += 1
    print(f'落盘 {fixed} 处，定位不唯一跳过 {skipped} 处')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    main(ap.parse_args().apply)
