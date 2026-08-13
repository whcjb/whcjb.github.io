#!/usr/bin/env python3
"""用 PDF 内部链接重建「正文标记 → 附录定义」的权威映射。

此前一直按编号查表（正文 fcN → 附录 ftcN），但 AGES 附录的编号并不可靠：
诗篇 81 一段整体错位一格、ftc378 是 ftc578 的数字误识、ftc407/408 顺序还是反的。
按编号对就会把注挂错地方，而"引用数 = 定义数"这类校验完全查不出来。

PDF 里每个脚注上标都是可点击的内部链接，指向定义所在的**页**（不到具体条目）。
把它和页内顺序结合起来就能定死：

    某页上的 k 个标记（按阅读顺序） ↔ 目标页上的 k 条定义（按版面顺序）

条目数比标记少 1 时，说明该页首条定义是从上一页续下来的，前置补上。

用法:
    python3 scripts/psalms_footnote_links.py --vol 2            # 输出映射并与现状比对
    python3 scripts/psalms_footnote_links.py --vol 2 --write    # 写入 footnote_links.json
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
PDF = {'1': 'CAL_PSA1.pdf', '2': 'CAL_PSA2.pdf'}
MARK = re.compile(r'\s*(f[a-z]\d+[A-Za-z]?)\s*[.,;:!?\'"’”]*\s*')
ENTRY = re.compile(r'\s*([Ff][Tt][a-z]\d+[A-Za-z]?)\b')


def appendix_start(doc):
    for i in range(len(doc) - 1, 0, -1):
        if re.search(r'^\s*FOOTNOTES\s*$', doc[i].get_text(), re.M):
            return i
    return len(doc)


def scan(doc, fn_start):
    """→ (正文标记 [(page,y,x,code,rect)], 附录条目 [(page,y,code)])"""
    body, app = [], []
    for i, page in enumerate(doc):
        for b in page.get_text('dict')['blocks']:
            if b['type']:
                continue
            for line in b['lines']:
                for s in line['spans']:
                    if i < fn_start:
                        m = MARK.fullmatch(s['text'])
                        # 卷二部分 marker 不带 superscript flag，只能靠小字号识别
                        if m and (s['flags'] & 1 or s['size'] < 9.5):
                            body.append((i, round(s['bbox'][1]), round(s['bbox'][0]),
                                         m.group(1), s['bbox']))
                    else:
                        m = ENTRY.match(s['text'])
                        if m:
                            app.append((i, round(s['bbox'][1]), m.group(1)))
    body.sort(key=lambda r: (r[0], r[1], r[2]))
    app.sort(key=lambda r: (r[0], r[1]))
    return body, app


def marker_targets(doc, body):
    """标记 → 链接目标页（按 bbox 命中链接矩形）"""
    links = defaultdict(list)
    for i in range(len(doc)):
        for l in doc[i].get_links():
            if l.get('kind') == 1 and 'page' in l:
                links[i].append((l['from'], l['page']))
    out = {}
    for pno, y, x, code, rect in body:
        r = fitz.Rect(rect)
        for lr, tgt in links.get(pno, []):
            if lr.intersects(r):
                out[(pno, y, x, code)] = tgt
                break
    return out


def build(vol):
    doc = fitz.open(f'/Users/yanpeifa/Documents/论文/calvin/{PDF[vol]}')
    fn_start = appendix_start(doc)
    body, app = scan(doc, fn_start)
    tgt = marker_targets(doc, body)

    by_page = defaultdict(list)          # 目标页 → 该页上的定义条目（版面序）
    for pno, y, code in app:
        by_page[pno].append(code)
    order = [c for _, _, c in app]
    idx = {c: i for i, c in enumerate(order)}

    groups = defaultdict(list)           # 目标页 → 指向它的标记（阅读序）
    for pno, y, x, code, rect in body:
        t = tgt.get((pno, y, x, code))
        if t is not None:
            groups[t].append(code)

    mapping, unsure = {}, []
    for page, marks in groups.items():
        entries = by_page.get(page, [])
        # 标记比条目多 1 → 首条是上一页续下来的，前置补上
        if len(marks) == len(entries) + 1 and entries and idx.get(entries[0], 0) > 0:
            entries = [order[idx[entries[0]] - 1]] + entries
        if len(marks) == len(entries):
            mapping.update(dict(zip(marks, entries)))
        else:
            unsure.append((page, marks, entries))
    return mapping, unsure, len(body), len(app)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', default='2')
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args()

    mapping, unsure, nb, na = build(args.vol)
    print(f'卷{args.vol}: 正文标记 {nb} | 附录条目 {na} | 链接确定映射 {len(mapping)} 条'
          f' | 页内数量对不上 {len(unsure)} 页')
    same = [k for k, v in mapping.items() if v == 'ft' + k[1:]]
    diff = {k: v for k, v in mapping.items() if v != 'ft' + k[1:]}
    print(f'  与"按编号直接对应"一致 {len(same)} 条，不一致 {len(diff)} 条')
    for k, v in list(diff.items())[:10]:
        print(f'    {k} → {v}（按编号会挂 ft{k[1:]}）')
    if args.write:
        p = ROOT / f'calvin_raw/psalms-{args.vol}/footnote_links.json'
        p.write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding='utf-8')
        print('已写入', p.relative_to(ROOT))
