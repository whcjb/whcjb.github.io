#!/usr/bin/env python3
"""博纳尔《诗篇中的基督与教会》：Monergism 录入本 PDF → bonar_raw/psalms/units.json

    python3 scripts/extract_bonar.py

底本是 Monergism Books 电子本（2020），一个文本块 = 一段。版式（实测）：
  - 标题 Georgia-Bold 21.2pt：PREFACE / PSALM N（可带 * 脚注号）/ SONGS OF DEGREES；
  - 正文 Georgia 15pt，x0≈77；希伯来文 ArialMT / NotoSansHebrew，希腊文 Roboto；
  - 原书每篇开头印整篇经文，录入本只留节号范围「1–10 HITHERTO…」；原书斜体、页边小标题录入本都没有；
  - 跨页的段：上页末块末行排满（x1 ≥ FULL_X1）即可能与下页首块相接，接缝留 JOIN 记号，发布时用 1859 初版判；
  - 第 449 页「-----」之后是 Monergism 版权声明与目录，不收。
希伯来文按字形坐标重建（scripts/bonar_hebrew.py），重建结果再经 hebrew_fixes.tsv 看图校正。
"""
import json
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bonar_hebrew as H  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'bonar_raw' / 'psalms'
PDF = RAW / 'src' / 'monergism' / 'bonar_psalms.pdf'
OUT = RAW / 'units.json'
HEB_OUT = RAW / 'work' / 'hebrew_runs.json'

FULL_X1 = 515
JOIN = '\n⁣'
HEB_OPEN, HEB_CLOSE = '⟪', '⟫'      # 希伯来片段的界标，发布时换成 <span lang="he">
RE_PSALM = re.compile(r'^PSALM (\d+)\s*([*†]?)$')


def line_text(l, pno, heb_log):
    """一行 → 文字；希伯来片段换成坐标重建的结果，并记入 heb_log。"""
    chars = [(c['c'], c['bbox']) for s in l['spans'] for c in s['chars']]
    out, i = [], 0
    while i < len(chars):
        c = chars[i][0]
        if H.is_heb(c):
            j = i
            while j < len(chars) and (H.is_heb(chars[j][0]) or
                                      (chars[j][0] in ' ‎‏‪‫‬' and
                                       any(H.is_heb(x) for x, _ in chars[j:j + 3]))):
                j += 1
            seg = [(x, bb) for x, bb in chars[i:j] if H.is_heb(x)]
            txt, orph = H.rebuild(seg)
            hid = len(heb_log)
            heb_log.append(dict(id=hid, page=pno, bbox=[round(v, 1) for v in l['bbox']],
                                x0=round(min(bb[0] for _, bb in seg), 1), x1=round(max(bb[2] for _, bb in seg), 1),
                                raw=''.join(x for x, _ in seg), text=txt, orphans=''.join(orph)))
            out.append(f'{HEB_OPEN}{hid}{HEB_CLOSE}')
            i = j
        else:
            if c not in '‎‏‪‫‬':
                out.append(c)
            i += 1
    t = ''.join(out)
    return re.sub(r' {2,}', ' ', t).strip()


def head_is_title(b):
    """第 2 页顶上的书名、著者两块（PREFACE 之前）。"""
    return b['page'] == 2 and ' '.join(t for t, _ in b['lines']) in (
        'Christ and His Church', 'in the Book of Psalms', 'by Andrew Bonar')


def blocks(heb_log):
    doc = fitz.open(PDF)
    for pno, page in enumerate(doc):
        for b in page.get_text('rawdict')['blocks']:
            ls = [l for l in b.get('lines', []) if ''.join(c['c'] for s in l['spans'] for c in s['chars']).strip()]
            if not ls:
                continue
            sp = ls[0]['spans'][0]
            lines = [(line_text(l, pno, heb_log), l['bbox'][2]) for l in ls]
            yield dict(page=pno, x0=b['bbox'][0], bold='Bold' in sp['font'], size=round(sp['size'], 1),
                       lines=lines)


def main():
    heb_log = []
    bl = []
    for b in blocks(heb_log):
        if b['page'] < 2:
            continue
        if b['lines'][0][0].startswith('-----'):
            break
        bl.append(b)
    for i, b in enumerate(bl):
        b['last_on_page'] = i + 1 == len(bl) or bl[i + 1]['page'] != b['page']
        b['first_on_page'] = i == 0 or bl[i - 1]['page'] != b['page']
    units, cur, prev = [], None, None
    for b in bl:
        if b['bold'] and cur is None and head_is_title(b):
            continue
        if b['bold'] and b['size'] >= 20:
            head = ' '.join(t for t, _ in b['lines'])
            m = RE_PSALM.match(head)
            if m:
                cur = dict(type='psalm', num=int(m.group(1)), mark=m.group(2), paras=[])
            elif head == 'PREFACE':
                cur = dict(type='preface', title='Preface', paras=[])
            elif head == 'SONGS OF DEGREES':
                cur = dict(type='section', title='Songs of Degrees', paras=[])
            else:
                raise SystemExit(f'未知标题：p{b["page"]} {head!r}')
            units.append(cur)
            prev = None
            continue
        text = '\n'.join(t for t, _ in b['lines'])
        if prev and prev['last_on_page'] and b['first_on_page'] and prev['lines'][-1][1] >= FULL_X1:
            cur['paras'][-1] += JOIN + text
        else:
            cur['paras'].append(text)
        prev = b
    OUT.write_text(json.dumps(units, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    HEB_OUT.write_text(json.dumps(heb_log, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    ps = [u['num'] for u in units if u['type'] == 'psalm']
    print(f'单元 {len(units)}（诗篇 {len(ps)}，缺 {sorted(set(range(1, 151)) - set(ps))}）；'
          f'段 {sum(len(u["paras"]) for u in units)}；接缝 {sum(p.count(JOIN) for u in units for p in u["paras"])}；'
          f'希伯来片段 {len(heb_log)}（有孤点 {sum(1 for h in heb_log if h["orphans"])}）', file=sys.stderr)


if __name__ == '__main__':
    main()
