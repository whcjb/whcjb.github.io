#!/usr/bin/env python3
"""坎德利什《约翰一书讲解》：Monergism 录入本 PDF → candlish_raw/1john/units.json

    python3 scripts/extract_candlish.py

底本是 Monergism 电子书（William A. Anderson 2008 年 Libronix 录入本的再排版），一个文本块 = 一段。
版式（实测）：
  - 部分标题 Georgia-Bold 25pt；讲题 Georgia-Bold 21.2pt，「XII: TITLE…」跨几块；
  - 题记经文 x0≈92 的正体块；正文 x0≈77 的 15pt 正体块；
  - 跨页的段：上一页最后一块末行排满（x1 ≥ 515）即与下一页第一块相接（接缝留 JOIN 记号）。
行与行之间保留 '\n'，比对时要知道哪个词落在行尾（PDF 生成时行尾会被截字，见 align_candlish.py）。
"""
import json
import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'candlish_raw' / '1john'
PDF = RAW / 'src' / 'monergism' / 'candlish_1john.pdf'
OUT = RAW / 'units.json'

FULL_X1 = 515
# 跨页拼接点：PDF 上「上页末行排满 + 下页起新段」与「段落跨页」分不开，先拼上、留这个记号，
# 发布时用 e-Sword 本的段落起点判（publish_candlish_en.py resolve_joins）。
JOIN = '\n\u2063'
RE_LECT = re.compile(r'^([IVXL]+): (.*)$')


def blocks():
    doc = fitz.open(PDF)
    for pno, page in enumerate(doc):
        for b in page.get_text('dict')['blocks']:
            ls = b.get('lines', [])
            lines = [(''.join(s['text'] for s in l['spans']), l['bbox'][2]) for l in ls]
            lines = [(t, x1) for t, x1 in lines if t.strip()]
            if not lines:
                continue
            sp = ls[0]['spans'][0]
            yield dict(page=pno, x0=b['bbox'][0], bold='Bold' in sp['font'], size=round(sp['size'], 1),
                       lines=lines)


def kind(b):
    if b['bold']:
        if b['size'] >= 24:
            return 'part'
        if b['size'] >= 20:
            return 'head'
        return 'bold'
    if b['x0'] > 85:
        return 'epi'
    return 'para'


def main():
    bl = []
    for b in blocks():
        if b['page'] < 2:
            continue
        # 末页正文之后是 Monergism 的版权声明，从「-----」分隔线（其后 MONERGISM BOOKS）起不收
        if b['lines'][0][0].strip().startswith('-----'):
            break
        bl.append(b)
    items, prev = [], None
    pages = {}
    for b in bl:
        pages.setdefault(b['page'], []).append(b)
    for pno in sorted(pages):
        pb = pages[pno]
        for i, b in enumerate(pb):
            k = kind(b)
            text = '\n'.join(t.strip() for t, _ in b['lines'])
            first_on_page = i == 0
            if (prev and first_on_page and k in ('para', 'epi') and prev['kind'] == k
                    and prev['last_x1'] >= FULL_X1 and prev['ends_page']):
                prev['text'] += JOIN + text
                prev['pages'].append(pno)
                prev['last_x1'] = b['lines'][-1][1]
            else:
                prev = dict(kind=k, text=text, pages=[pno], last_x1=b['lines'][-1][1])
                items.append(prev)
            prev['ends_page'] = i == len(pb) - 1

    # 组装：front（目录 + 两篇序）→ part / lecture
    units, cur = [], None
    pending_part = []
    for it in items:
        k, t = it['kind'], it['text']
        if k == 'part':
            if cur and cur['type'] == 'lecture' and cur['paras']:
                cur = None
            if units and units[-1]['type'] == 'part' and units[-1]['open']:
                units[-1]['title'] += ' ' + t.replace('\n', ' ')
            else:
                units.append(dict(type='part', title=t.replace('\n', ' '), open=True))
            continue
        if units and units[-1]['type'] == 'part':
            units[-1]['open'] = False
        if k == 'head' or k == 'bold':
            line = t.replace('\n', ' ')
            m = RE_LECT.match(line)
            if m:
                cur = dict(type='lecture', num=m.group(1), title=m.group(2), epi=[], paras=[], pages=it['pages'])
                units.append(cur)
            elif cur and cur['type'] == 'lecture' and not cur['epi'] and not cur['paras']:
                cur['title'] += ' ' + line
            elif line in ('Table of Contents',) or line.startswith('PREFACE'):
                cur = dict(type='front', title=line, epi=[], paras=[], pages=it['pages'])
                units.append(cur)
            elif cur and cur['type'] == 'front' and cur['title'] == 'Table of Contents':
                cur['paras'].append(t)
            else:
                units.append(dict(type='misc', title=line, pages=it['pages']))
            continue
        if cur is None:
            units.append(dict(type='misc', title=t.replace('\n', ' '), pages=it['pages']))
            continue
        if k == 'epi' and not cur['paras'] and cur['type'] == 'lecture':
            cur['epi'].append(t)
        else:
            cur['paras'].append(t)
    for u in units:
        u.pop('open', None)
    OUT.write_text(json.dumps(units, ensure_ascii=False, indent=1), encoding='utf-8')
    lec = [u for u in units if u['type'] == 'lecture']
    print(f'units {len(units)}  lectures {len(lec)}  paras {sum(len(u.get("paras", [])) for u in units)}')
    for u in units:
        if u['type'] != 'lecture':
            print(' ', u['type'], u['title'][:80], len(u.get('paras', [])))


if __name__ == '__main__':
    main()
