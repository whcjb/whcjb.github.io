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
        items.append((n, item))
    return items

def linkify(body_lines):
    """body_lines: <p>/<h2>/其它 行列表。首个「像总纲」的 <p> → 导航; 正文段首递增 N. → id=sec-N。"""
    out = list(body_lines)
    # 1) 定位总纲段 = 第一个 <p>, 且段首 1. 且含 2. 3.
    oi = None; oinner = None
    for i, l in enumerate(out):
        m = re.match(r'^<p>(.*)</p>\s*$', l.strip(), re.S)
        if m:
            inner = m.group(1)
            if re.match(r'^\s*1\.', inner) and re.search(r'\b2\.', inner) and re.search(r'\b3\.', inner):
                oi, oinner = i, inner
            break   # 只看第一个 <p>
    # 2) 正文段首递增数字 → 锚点
    last = 0
    for i, l in enumerate(out):
        if i == oi:
            continue
        m = re.match(r'^<p>(\d{1,3})\.\s', l.strip())
        if m:
            n = int(m.group(1))
            if n > last:
                out[i] = l.replace('<p>', f'<p id="sec-{n}">', 1)
                last = n
    # 3) 总纲 → 链接导航
    if oi is not None:
        items = _split_outline(oinner)
        if items:
            links = ''.join(
                f'<a class="owen-outline-item" href="#sec-{n}"><b>{n}.</b> {t}</a>'
                for n, t in items)
            out[oi] = ('<details class="owen-outline" markdown="0">'
                       '<summary class="owen-outline-hd">本篇纲目 · Argument</summary>'
                       '<div class="owen-outline-body">' + links + '</div></details>')
    return out
