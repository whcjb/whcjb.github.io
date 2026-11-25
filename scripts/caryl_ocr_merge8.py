#!/usr/bin/env python3
"""卡里尔第 8 部（27–29 章）：两份底本按原书页码逐页择优（old-book-ocr §3.2d）。

    /usr/bin/python3 scripts/caryl_ocr_merge8.py            # 试跑：页码对齐、各取多少页
    /usr/bin/python3 scripts/caryl_ocr_merge8.py --apply    # p8/pages.json ← 合成；原胶片版留 p8/pages_film.json；
                                                            # 没选中的那份拼成对照文本 witness/w8_hocr_searchtext.txt.gz

两份：p8 = 1670 EEBO 胶片（800 ppi，自第 160 叶起大段发暗透印）；p81 = Packer 藏本纸本（300 ppi）。
页码：两份都主要是「叶序 − 5」，但纸本夹着缺叶／多叶（偏移 −4、−6、+1 各有几十页），不能全书一个偏移。
逐页定：读出的页码与前一可信页的差 = 叶序差（±0）才采信，其余按两侧可信页插补；插补不出的不参与择优。
择优：同一印本页两份都有时取正文非词率低的（词表见 caryl_ocr_fix）；只有一份的取那份。
两份都缺的页插一行说明（cy-gap）。
对照文本：没选中的那份，按页码顺序拼起来——两边都是 kraken 识别的，比 IA 的 tesseract 层（非词率 15.6%）好得多。
"""
import argparse
import gzip
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import caryl_ocr_fix as fx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'caryl_raw' / 'job_ocr'


def assign_pages(P):
    leaves = sorted(k for k, v in P.items() if v['kind'] == 'text')
    read = {}
    for i, lf in enumerate(leaves):
        pn = P[lf].get('pageno')
        if pn and re.fullmatch(r'\d{1,4}', pn):
            read[i] = int(pn)
    # 可信：与前后各一个读数的「页码差 = 叶序差」至少一侧成立
    ks = sorted(read)
    good = {}
    for j, i in enumerate(ks):
        ok = False
        for k in (ks[j - 1] if j else None, ks[j + 1] if j + 1 < len(ks) else None):
            if k is not None and read[k] - read[i] == k - i:
                ok = True
        if ok:
            good[i] = read[i]
    out = {}
    gk = sorted(good)
    for i, lf in enumerate(leaves):
        if i in good:
            out[lf] = good[i]
            continue
        lo = max((k for k in gk if k < i), default=None)
        hi = min((k for k in gk if k > i), default=None)
        if lo is not None and hi is not None and good[hi] - good[lo] == hi - lo:
            out[lf] = good[lo] + (i - lo)
        elif lo is not None and hi is None and i - lo <= 3:
            out[lf] = good[lo] + (i - lo)
        elif hi is not None and lo is None and hi - i <= 3:
            out[lf] = good[hi] - (hi - i)
    return out


def nonword(pg):
    ws = [w.lower() for b in pg.get('body', []) for w in re.findall(r'[A-Za-z]{3,}', b['t'])]
    return (sum(1 for w in ws if not fx.LEX.get(w)) / len(ws), len(ws)) if len(ws) >= 30 else (1.0, len(ws))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    d8, d81 = BASE / 'p8', BASE / 'p81'
    src8 = d8 / 'pages_film.json' if (d8 / 'pages_film.json').exists() else d8 / 'pages.json'
    A = json.loads(src8.read_text(encoding='utf-8'))
    B = json.loads((d81 / 'pages.json').read_text(encoding='utf-8'))
    pa, pb = assign_pages(A), assign_pages(B)
    bya = {n: lf for lf, n in pa.items()}
    byb = {n: lf for lf, n in pb.items()}
    pages = sorted(n for n in set(bya) | set(byb) if n >= 1)
    merged, wit, pick = {}, [], {'film': 0, 'paper': 0}
    # 前置页（没定出页码的胶片前几叶：扉页、致读者）照搬胶片版
    first = min(pages)
    for lf in sorted(A):
        if A[lf]['kind'] != 'text' or lf not in pa:
            if not merged or int(lf) < int(bya[first]):
                merged[f'0{lf}'] = A[lf]
    have = set(pages)
    for n in range(min(pages), max(pages) + 1):
        if n not in have:                   # 两份都缺：插一行说明，不让上下文悄悄接上
            merged[f'1{n:04d}'] = dict(kind='text', head=None, pageno=str(n), catch=None, x0=0, x1=0, margin=[],
                                       body=[dict(y=0, x=0, end=0, lx0=0, lx1=0, indent=True, short=True,
                                                  t=f'<span class="cy-gap">[Page {n} is missing from both scans. '
                                                    f'此页两份扫描都缺，待补。]</span>')])
            continue
    for n in pages:
        ca = A[bya[n]] if n in bya else None
        cb = B[byb[n]] if n in byb else None
        ra = nonword(ca)[0] if ca else 9
        rb = nonword(cb)[0] if cb else 9
        if ra <= rb:
            chosen, other, k = dict(ca), cb, 'film'
        else:
            chosen, other, k = dict(cb), ca, 'paper'
        chosen['pageno'] = str(n)
        chosen['src'] = k
        merged[f'1{n:04d}'] = chosen
        pick[k] += 1
        if other:
            wit.append(' '.join(b['t'] for b in other.get('body', [])))
    print(f'胶片定出页码 {len(pa)} 叶，纸本 {len(pb)} 叶；合计印本页 {len(pages)}（{min(pages)}–{max(pages)}）；'
          f'取胶片 {pick["film"]}、取纸本 {pick["paper"]}；对照文本 {len(wit)} 页', file=sys.stderr)
    miss = [n for n in range(min(pages), max(pages) + 1) if n not in set(pages)]
    print(f'两份都缺的印本页 {len(miss)}：{miss[:30]}', file=sys.stderr)
    if a.apply:
        if not (d8 / 'pages_film.json').exists():
            shutil.copy(d8 / 'pages.json', d8 / 'pages_film.json')
        (d8 / 'pages.json').write_text(json.dumps(merged, ensure_ascii=False) + '\n', encoding='utf-8')
        with gzip.open(BASE / 'witness' / 'w8_hocr_searchtext.txt.gz', 'wt', encoding='utf-8') as f:
            f.write('\n'.join(wit))


if __name__ == '__main__':
    main()
