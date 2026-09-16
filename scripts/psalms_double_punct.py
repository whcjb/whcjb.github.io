#!/usr/bin/env python3
"""连着两个标点的地方——`arm,,`、`Solomon,;at`、`A Psalm,. By David`。

这类错 `psalms_backlog.py` 一个也看不见：它按「空白分段」找非词，而
`,,` 两边都是好词，标点自己不构成一个段。可它们是**实打实的错**，
而且读者一眼就看得见。来路有两处：
  · ABBYY 把一个逗号读成两个（页面上的脏点恰好落在逗号旁边）
  · 判读落盘时读数尾巴上带了标点，而正文里那个标点本来就在 —— 这一类是
    我们自己造的（以赛亚那条线也踩过：「重扫把读数两端的标点还回去」）

判法与残留串同一套：拿 1850 三卷本按位置读出那一处的原文切片，
**只接受标点级的改动**（剥掉标点后逐字相同），否则不动。

`.,` 特别处理：`Ps. xcvii., but` 这种是正经的（缩写的点 + 分句的逗号），
全书八十多处。只有前面那个词**不是**罗马数字、也不是书里通行缩写时，
才当成可疑——`Absalom., his son`、`had., been withdrawn` 就是这么捞出来的。

用法：
    python3 scripts/psalms_double_punct.py            # 只报告
    python3 scripts/psalms_double_punct.py --apply
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_alexander_image as A
from psalms_residue_witness import (ANCHOR, MAX_HITS, REACH, WORD, letters,
                                    load_witness, slice_at)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
FIXES = ROOT / 'alexander_raw/psalms/manual_fixes.tsv'
OUT = ROOT / 'logs/alexander_psalms_double_punct.tsv'

# 两个标点之间只允许隔空白或斜体星号。**不能把右括号也算进来**：
# `(cxx.-cxxxiv,), all bearing` 里那两个逗号一个在括号内一个在括号外，
# 各有各的活儿，不是「同一个标点重了两次」——并掉哪个都是错的。
CLUSTER = re.compile(r'[,;:.][*\s]{0,3}[,;:.]')
ROMAN = re.compile(r'^[ivxlcdm]+$', re.I)


def suspicious(prev_word, cluster):
    """这一处的双标点值不值得查。"""
    flat = re.sub(r'[^,;:.]', '', cluster)
    if flat in (',,', ';;', '::', ',;', ';,', ',.', ';.', ':,'):
        return True
    if flat == '.,':
        # `Ps. xcvii., but`、`&c., in our language`、`i. e., of its wilful
        # continuance` 都是正经的：缩写的点 + 分句的逗号。单字母的词一律
        # 当缩写看——`i.` `e.` `c.` `v.` 全书就这几个。
        return not (ROMAN.match(prev_word) or prev_word in A.ABBREV
                    or len(prev_word) == 1
                    or prev_word.lower() in {'c', 'viz', 'ib'})
    return False


def scan():
    """找出所有可疑的双标点，连同它前面那个词。"""
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
        ends = {t[2]: k for k, t in enumerate(toks)}
        for m in CLUSTER.finditer(masked, start):
            # 紧挨着这个标点簇的前一个词
            k = None
            j = m.start()
            while j > 0 and j not in ends:
                if not masked[j - 1].isspace() and masked[j - 1] not in '*)]':
                    break
                j -= 1
            k = ends.get(j)
            if k is None:
                continue
            if not suspicious(toks[k][0], m.group(0)):
                continue
            # 同一个词在标点后面又出现一遍（`The common;;common version`）——
            # 那是**跨行重出**，不是标点重了，并掉标点只会留下重复的词
            after = masked[m.end():m.end() + len(toks[k][0]) + 2].strip()
            if after.lower().startswith(toks[k][0].lower()):
                continue
            out.append(dict(sec=sec, raw=raw, masked=masked, tok=k, toks=toks,
                            a=toks[k][1], b=m.end(),
                            span=raw[toks[k][1]:m.end()]))
    return out


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
        cand = {slice_at(wtext, wtoks, p + d, p + d)
                for p in hits if 0 <= p + d < len(wtoks)}
        if len(cand) == 1:
            reads[start] = cand.pop()
    vals = set(reads.values())
    if not vals:
        return None, '证人语料里找不到这段话'
    if len(vals) > 1:
        return None, f'几个锚读数不一致：{sorted(vals)[:3]}'
    return vals.pop(), f'{len(reads)} 个锚一致'


PUNCT = ',;:.'


def collapse(span, tok, read, nxt=''):
    """定出这一处该留哪个标点。**只准删标点**，不准加、不准换、不准碰排版符号。

    两条路：
      · 两个标点一模一样（`,,` `;;`）——印刷上不存在连着两个逗号，
        直接并成一个，不用问证人
      · 两个不一样（`,.` `;,`）——问证人留哪个。证人给出的那个必须
        **就是我们这两个里的一个**，否则宁可留着让影像去判：
        证人是 1850 那一版，标点本来就可能与 1864 不同

    返回 (新串, 说明) 或 (None, 留账原因)。
    """
    tail = span[len(tok):]
    marks = [i for i, c in enumerate(tail) if c in PUNCT]
    if len(marks) < 2:
        return None, '没有两个标点'
    chars = [tail[i] for i in marks]
    if len(set(chars)) == 1:
        keep = marks[:1]
        why = f'同一个标点重了 {len(marks)} 次，并成一个'
    else:
        if read is None:
            return None, '证人给不出，两个标点又不一样'
        wit = ''.join(c for c in read[len(tok):] if c in PUNCT)
        if len(wit) != 1 or wit not in chars:
            return None, f'证人读数 {read!r} 不在我们这两个标点之内'
        keep = [marks[chars.index(wit)]]
        why = f'证人留的是 {wit!r}'
    out = tok + ''.join(c for i, c in enumerate(tail)
                        if c not in PUNCT or i in keep)
    # 被删掉的那个标点如果本来兼着词距的活儿（`him,.in` `Solomon,;at`），
    # 删完得把空格补回来，否则两个词黏在一起
    if nxt[:1].isalnum() and not out.endswith((' ', '*')):
        out += ' '
    return (None, '与原串相同') if out == span else (out, why)


def main(apply=False):
    wtext, wtoks, wlow, widx = load_witness()
    items = scan()
    print(f'可疑双标点 {len(items)} 处')
    stat, add, rows = Counter(), [], []
    for it in items:
        read, why = judge(it, wtext, wtoks, widx)
        if read is not None and letters(read) != letters(it['toks'][it['tok']][0]):
            read, why = None, '证人读数字母对不上'
        nxt = it['raw'][it['b']:it['b'] + 1]
        out, note = collapse(it['span'], it['toks'][it['tok']][0], read, nxt)
        if out is None:
            stat['留账'] += 1
            rows.append((it['sec'], it['span'], read or '', note))
            continue
        stat['可改'] += 1
        rows.append((it['sec'], it['span'], out, note))
        add.append((it, out))
    print('，'.join(f'{k} {v}' for k, v in stat.most_common()))
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open('w', encoding='utf-8') as fh:
        fh.write('篇\t我们\t改成\t说明\n')
        for r in rows:
            fh.write('\t'.join(r) + '\n')
    print(f'逐条 → {OUT}')
    if not apply:
        for it, out in add:
            print(f'  [{it["sec"]}] {it["span"]!r} → {out!r}')
        return
    n = skip = 0
    with FIXES.open('a', encoding='utf-8') as fh:
        for it, out in add:
            p = SRC / f'{it["sec"]}.md'
            t = p.read_text(encoding='utf-8')
            old, new = it['span'], out
            if t.count(old) != 1:
                head = it['raw'][max(0, it['a'] - 18):it['a']]
                old, new = head + old, head + new
                if t.count(old) != 1:
                    skip += 1
                    continue
            fh.write(f'{it["sec"]}\t{old}\t{new}\twitness1850: 双标点并一个\n')
            p.write_text(t.replace(old, new, 1), encoding='utf-8')
            n += 1
    print(f'落盘 {n} 处，定位不唯一跳过 {skip} 处')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    main(ap.parse_args().apply)
