#!/usr/bin/env python3
"""博纳尔《诗篇中的基督与教会》：从 Monergism PDF 的字形坐标重建希伯来文。

PDF 里希伯来文是按视觉位置逐字形排的，直接取文字会把元音点和字母拆开、顺序打乱
（例：`הָ ָָעש` 实为 עָשָׂה 一类）。这里按坐标重建：
  - 有宽度的点（元音、sin/shin 点）的框包住它所属字母的框 → 挂到框中心落在点框内、离点框中心最近的字母；
  - 零宽的点（dagesh/mappiq、holam 等）挂到字形流里紧跟其后的那个字母；
  - 字母按横坐标从右到左排，字间距 > GAP 处断词；
  - 挂不上的点记为 orphan，交人工看图。
供 extract_bonar.py 调用：hebrew_runs(page) → [(line_bbox, 原字形流文字, 重建文字, orphans)]。
"""
import unicodedata

GAP = 1.5


def is_heb(c):
    o = ord(c)
    return 0x0590 <= o <= 0x05FF or 0xFB1D <= o <= 0xFB4F


def is_mark(c):
    return unicodedata.category(c) == 'Mn'


def rebuild(chars):
    """chars: [(c, bbox)]，一行里连续的希伯来字形（流顺序）。→ (text, orphans)"""
    bases = [dict(c=unicodedata.normalize('NFKC', c), bb=bb, m=[], i=i)
             for i, (c, bb) in enumerate(chars) if not is_mark(c)]
    orphans = []
    for i, (c, bb) in enumerate(chars):
        if not is_mark(c):
            continue
        w = bb[2] - bb[0]
        tgt = None
        if w > 0.5:
            cand = [B for B in bases if bb[0] - 0.3 <= (B['bb'][0] + B['bb'][2]) / 2 <= bb[2] + 0.3]
            if cand:
                mc = (bb[0] + bb[2]) / 2
                tgt = min(cand, key=lambda B: abs((B['bb'][0] + B['bb'][2]) / 2 - mc))
        else:
            nxt = [B for B in bases if B['i'] > i]
            if nxt:
                tgt = nxt[0]
        if tgt is None:
            orphans.append(c)
        else:
            tgt['m'].append(c)
            if w > 0.5:      # 带点字母的字形框被压窄，点的框才是它的整个字宽
                tgt['bb'] = (min(tgt['bb'][0], bb[0]), tgt['bb'][1], max(tgt['bb'][2], bb[2]), tgt['bb'][3])
    bases.sort(key=lambda B: -(B['bb'][0] + B['bb'][2]) / 2)
    out, prev = '', None
    for B in bases:
        if prev is not None and prev['bb'][0] - B['bb'][2] > GAP:
            out += ' '
        out += unicodedata.normalize('NFC', B['c'] + ''.join(B['m']))
        prev = B
    return out, orphans


def hebrew_runs(page):
    """页 → 每行的希伯来片段。返回 [(line_no_in_page, start_char_idx, end_char_idx, rebuilt, orphans)] 以及行字形。"""
    res = []
    for b in page.get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            chars = [(c['c'], c['bbox']) for s in l['spans'] for c in s['chars']]
            i = 0
            while i < len(chars):
                if is_heb(chars[i][0]):
                    j = i
                    while j < len(chars) and (is_heb(chars[j][0]) or
                                              (chars[j][0] in ' ‎‏‪‫‬' and
                                               any(is_heb(c) for c, _ in chars[j:j + 3]))):
                        j += 1
                    seg = [(c, bb) for c, bb in chars[i:j] if is_heb(c)]
                    txt, orph = rebuild(seg)
                    res.append(dict(bbox=l['bbox'], raw=''.join(c for c, _ in chars[i:j]), text=txt, orphans=orph))
                    i = j
                else:
                    i += 1
    return res


if __name__ == '__main__':
    import sys
    import fitz
    from pathlib import Path
    pdf = Path(__file__).resolve().parent.parent / 'bonar_raw/psalms/src/monergism/bonar_psalms.pdf'
    d = fitz.open(pdf)
    n = no = 0
    for pno in (map(int, sys.argv[1:]) if len(sys.argv) > 1 else range(len(d))):
        for r in hebrew_runs(d[pno]):
            n += 1
            no += bool(r['orphans'])
            print(pno, r['text'], ('ORPHAN ' + ''.join(r['orphans'])) if r['orphans'] else '')
    print('runs', n, 'with orphans', no, file=sys.stderr)
