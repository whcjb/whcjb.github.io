#!/usr/bin/env python3
"""
owen_outline.py — 欧文导论/序言的「内容总纲」→ 锚点导航。

欧文每篇开头有一段总纲(把全篇各节 1. 2. ... N. 逐条列出)。本模块:
  1) 给正文中段首为递增整数 `N.` 的 <p> 加 id="sec-N";
  2) 把总纲段拆成链接 <a href="#sec-N">N. 文字</a>。
锚点(#sec-N)与语言无关, 中英两版共用同一套 → owen_build(英) / translate_owen(中) 都调 linkify。
"""
import re

def _split_outline(text):
    """'1. A。2. B。…40. Z。' -> [(1,'A'),(2,'B'),…] 取从 1 起的递增连续段; 少于3条返回 None"""
    marks = [(m.start(), m.end(), int(m.group(1))) for m in re.finditer(r'(\d{1,3})\.', text)]
    kept = []; expect = 1
    for s, e, n in marks:
        if n == expect:
            kept.append((s, e, n)); expect += 1
    if len(kept) < 3:
        return None
    items = []
    for i, (s, e, n) in enumerate(kept):
        seg_end = kept[i+1][0] if i+1 < len(kept) else len(text)
        item = text[e:seg_end].strip(' 。；;.,、—–-　')
        # 去掉条目尾部残留的连接词(英文 "; and" / 中文 ";及/;以及/和/与")
        item = re.sub(r'[;；,，、]?\s*(and|及|以及|和|与|與)\s*$', '', item, flags=re.I)
        item = item.strip(' 。；;.,、—–-　')
        items.append((n, item))
    return items

def _extract_from(text, expect):
    """从 text 里按递增(从 expect 起)抽编号条目 -> ([(n,item)...], 首个编号前的散文, 末编号)"""
    marks = [(m.start(), m.end(), int(m.group(1))) for m in re.finditer(r'(\d{1,3})\.', text)]
    kept = []
    e0 = expect
    for s, e, n in marks:
        if n == e0:
            kept.append((s, e, n)); e0 += 1
    if not kept:
        return [], text, expect - 1
    lead = text[:kept[0][0]].strip(' 。；;.,、—–-　')   # 首编号前的散文
    items = []
    for i, (s, e, n) in enumerate(kept):
        seg_end = kept[i+1][0] if i+1 < len(kept) else len(text)
        it = text[e:seg_end].strip(' 。；;.,、—–-　')
        it = re.sub(r'[;；,，、]?\s*(and|及|以及|和|与|與)\s*$', '', it, flags=re.I).strip(' 。；;.,、—–-　')
        items.append([n, it])
    return items, lead, kept[-1][2]

def linkify(body_lines):
    """首个「像总纲」的 <p> 起, 把后续延续编号的段一并并入纲目(跨段提要); 正文段首递增 N.→id=sec-N。"""
    out = list(body_lines)
    p_lines = [i for i, l in enumerate(out) if re.match(r'^<p>.*</p>\s*$', l.strip(), re.S)]
    # 1) 定位首个总纲段(段首 1. 且含 2. 3.)
    oi = None
    for i in p_lines:
        inner = re.match(r'^<p>(.*)</p>\s*$', out[i].strip(), re.S).group(1)
        if re.match(r'^\s*1\.', inner) and re.search(r'\b2\.', inner) and re.search(r'\b3\.', inner):
            oi = i; break
    arg_idx = set()
    all_items = []
    if oi is not None:
        inner = re.match(r'^<p>(.*)</p>\s*$', out[oi].strip(), re.S).group(1)
        items, _lead, last_n = _extract_from(inner, 1)
        all_items = items; arg_idx.add(oi)
        # 2) 向后并入延续编号的段(其首编号 == 上段末编号+1)
        for i in [x for x in p_lines if x > oi]:
            t = re.match(r'^<p>(.*)</p>\s*$', out[i].strip(), re.S).group(1)
            more, lead, last2 = _extract_from(t, last_n + 1)
            if not more:
                break                      # 不再延续 = 释义正文开始
            if lead and all_items:
                all_items[-1][1] = (all_items[-1][1] + '——' + lead).strip('——')
            all_items += more; arg_idx.add(i); last_n = last2
    # 3) 正文段首递增数字 → 锚点(排除所有提要段)
    last = 0
    for i, l in enumerate(out):
        if i in arg_idx:
            continue
        m = re.match(r'^<p>(\d{1,3})\.\s', l.strip())
        if m:
            n = int(m.group(1))
            if n > last:
                out[i] = l.replace('<p>', f'<p id="sec-{n}">', 1); last = n
    # 4) 合并成一个纲目导航; 其余提要段清空
    if all_items and len(all_items) >= 3:
        links = ''.join(f'<a class="owen-outline-item" href="#sec-{n}"><b>{n}.</b> {t}</a>'
                        for n, t in all_items)
        out[oi] = ('<details class="owen-outline" markdown="0">'
                   '<summary class="owen-outline-hd">本篇纲目 · Argument</summary>'
                   '<div class="owen-outline-body">' + links + '</div></details>')
        for i in arg_idx:
            if i != oi:
                out[i] = ''
    return out
