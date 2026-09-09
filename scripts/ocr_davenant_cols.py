#!/usr/bin/env python3
"""达文南特卷二末尾双栏索引页的按栏 OCR。

为什么要单独一遍
----------------
卷二 p580-595（General Index）、p599-601（传略索引）、p602-603（注中人事索引）
是**双栏密排**。整页丢给 tesseract（scripts/ocr_davenant.py 的 --psm 6）
会把左右两栏当成同一行读，产物是这样的：

    CovNocirs continued. Hospinian ... . «» 540
    Nice cited ote, 177 Hostiensis (Henry deSusa) 15 .

左栏的「尼西亚会议…177」和右栏的「Hostiensis…15」被拼成一句，条目和页码
全部错配，无法用。行的 bbox 也横跨两栏（x0=202 x1=1544），事后按坐标切不开
——分栏必须在**成像阶段**做。

做法：渲图 → 按墨迹的竖直投影找栏间白槽 → 切成左右两张图分别 OCR →
右栏的 bbox 加回横向偏移，仍按一份 jsonl 输出，下游（extract_davenant_index.py）
不必知道这一步的存在。

白槽的找法：只在页宽中段 35%–65% 里找**最长的一段近乎无墨的列**。写死
中点会切坏——两栏不等宽，且扫描件整体有平移（实测槽心在 0.46–0.53 之间浮动）。

用法:
    python3 scripts/ocr_davenant_cols.py --pages 580-595
    python3 scripts/ocr_davenant_cols.py --pages 599-603 --check   # 只报槽位不 OCR
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import fitz
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ocr_davenant import parse_hocr                       # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
LINES = {json.loads(l)['page']: json.loads(l)['lines']
         for l in (RAW / 'vol2_lines.jsonl').open(encoding='utf-8')}
PDF = RAW / 'expositionofepis02dave.pdf'
DPI = 400
INK = 160          # 灰度低于此值算墨（400 dpi 灰度图上，纸底 ~230、字 ~60）


# ── 哪几页是双栏、页顶有几行是整幅标题 ────────────────────────────────────
# 0-based 扫描页号 → 页顶整幅（横跨两栏）的行数。逐页看过原图定的：
#   580      General Index 的标题页：GENERAL INDEX / OF / SUBJECTS IN THE
#            EXPOSITION.  三行，其下才起双栏条目
#   581-595  正文页，页顶只有一行页眉（`572 GENERAL INDEX.`）
#   599      传略索引的标题页：INDEX / TO / THE BIOGRAPHICAL SKETCHES / OF /
#            FATHERS, HERESIARCHS, SCHOOLMEN, &c. / APPENDED BY THE
#            TRANSLATOR. / 「斜体名字只见于《论基督之死》」那条说明  共七行
#   600-601  传略索引正文页，一行页眉
#   602      注中人事索引的标题页：INDEX / OF / SUBJECTS AND WORKS /
#            INCIDENTALLY GLANCED AT / IN THE NOTES.  五行
#   603      注中人事索引正文页，一行页眉
#
# 为什么写死而不自动判：试过三种自动判据，都被扫描噪声顶翻——
#   · 「谷底/中位数」：p599 上半页整幅标题的笔画压在页宽中段，比值 0.202，
#     整页被判成单栏。
#   · 「自上而下找第一个左右都有墨、槽内无墨的文字行」：槽心挪 25 px 就换答案
#     （p581 从 y=313 跳到 y=1979）。
#   · 「槽内贯通白带占页高的比例」：条目的引点线一挨近槽就把白带截断，
#     p580/581/583/584/585 等实测比例掉到 0.14–0.49，与单栏页混在一起。
# 这是一部页数固定的书，24 页逐页核过一遍比养一个赢不了噪声的判据可靠。
TWO_COL = {580: 3, 599: 7, 600: 1, 601: 1, 602: 5, 603: 1}
TWO_COL.update({p: 1 for p in range(581, 596)})

# 槽心的人工覆盖（400 dpi 渲图上的横坐标）。
# 传略索引每半页其实是个四栏小表：姓名 | 卷一页码 | 竖线 | 卷二页码，
# 竖线左边那道空隙比真正的栏间槽**更白**（p599 实测：竖线左侧 830-852 一格
# 墨都没有，真正的栏间槽 920-962 因扫描底灰每列还有 4-6 个像素）。
# 自动找槽取的是最白的那道，于是从表内切开——左半页的「卷二页码」被划到了
# 右半页，Abelard/Alvarez 一类条目页码全丢，右栏则平白多出 435/453 这些
# 孤零零的数字（实测）。p600/p601 的槽自动找是对的，只有 p599 要按住。
CUT_OVERRIDE = {599: 941}

# 传略索引这三页每半页是个小表：姓名 … | 卷一页码 │ 卷二页码。
# 中间那道竖线是版面上唯一区分「这个页码属于哪一卷」的东西——不按它再切一刀，
# 两栏数字会混成一串，`Abelard … 435` 到底是卷一 435 还是卷二 435 无从判断，
# 发出去就是错的。竖线两侧没有任何字跨过，按它切绝对安全（不像「姓名/卷一」
# 之间只有引点线相隔，`Parisiensis (William Bp.` 这种长名会伸进数字栏）。
TABLE_PAGES = {599, 600, 601}


def find_rule(arr, x0, x1, y_from):
    """→ 半页之内那道竖线的 x。取墨量最强的一列。

    搜索范围掐掉半页的右端 8%：块间那道**双竖线**比表内单竖线更粗更黑，
    不掐掉就会选中它，切出来的「卷二」区是空的（p601 实测选到 x=990，
    真正的表内竖线在 850）。
    """
    ink = (arr[y_from:] < INK).sum(axis=0)
    lo = x0 + int((x1 - x0) * 0.55)
    hi = x1 - int((x1 - x0) * 0.08)
    return int(np.argmax(ink[lo:hi])) + lo


def find_gutter(arr, y_from=0):
    """→ 槽心 x。按 9 px 盒滤波抹平墨迹的竖直投影，取页宽中段的最小值位置。

    ⚠️ 只在 y_from 以下量。整幅标题的笔画压在页宽中段，会把真正的槽埋掉
    （p599 实测）。也不能把槽心写死在页宽一半：两栏不等宽、扫描件整体有
    平移，实测槽心在 0.44–0.55 之间浮动。
    """
    ink = (arr[y_from:] < INK).sum(axis=0).astype(float)
    sm = np.convolve(ink, np.ones(9) / 9, mode='same')
    w = arr.shape[1]
    lo, hi = int(w * 0.35), int(w * 0.65)
    return int(np.argmin(sm[lo:hi])) + lo


def head_bottom(idx, n_head):
    """→ 页顶前 n_head 行（整幅标题/页眉）的下界 y，取自整页 OCR 的行 bbox。

    直接量像素也能定，但 vol2_lines.jsonl 与这里同是 400 dpi 渲图，
    行 bbox 现成且稳，不必再造一套。
    """
    if not n_head:
        return 0
    lines = sorted(LINES.get(idx, []), key=lambda r: r['y0'])[:n_head]
    return (max(l['y1'] for l in lines) + 12) if lines else 0


def ocr_img(png, lang='eng+lat'):
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, 'o')
        r = subprocess.run(['tesseract', png, out, '-l', lang, '--psm', '6', 'hocr'],
                           capture_output=True)
        if r.returncode != 0:
            return []
        return parse_hocr(open(out + '.hocr', encoding='utf-8').read())


def ocr_page(idx):
    doc = fitz.open(str(PDF))
    pix = doc[idx].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
    doc.close()
    img = Image.frombytes('L', (pix.width, pix.height), pix.samples)
    arr = np.asarray(img)
    ys = head_bottom(idx, TWO_COL[idx])
    cut = CUT_OVERRIDE.get(idx) or find_gutter(arr, y_from=ys)
    rows = []
    with tempfile.TemporaryDirectory() as td:
        regions = [('H', 0, 0, img.width, ys)] if ys > 0 else []
        if idx in TABLE_PAGES:
            rl = find_rule(arr, 0, cut, ys)
            rr = find_rule(arr, cut, img.width, ys)
            regions += [('L', 0, ys, rl, img.height),
                        ('L2', rl, ys, cut, img.height),
                        ('R', cut, ys, rr, img.height),
                        ('R2', rr, ys, img.width, img.height)]
        else:
            regions += [('L', 0, ys, cut, img.height),
                        ('R', cut, ys, img.width, img.height)]
        for side, x0, y0, x1, y1 in regions:
            if y1 - y0 < 20:
                continue
            f = os.path.join(td, f'{side}.png')
            img.crop((x0, y0, x1, y1)).save(f)
            for r in ocr_img(f):
                r['x0'] += x0; r['x1'] += x0
                r['y0'] += y0; r['y1'] += y0
                r['col'] = side
                rows.append(r)
    # 先整幅标题，再左栏读到底，再右栏——原书的阅读顺序
    order = {'H': 0, 'L': 1, 'L2': 1.5, 'R': 2, 'R2': 2.5}
    rows.sort(key=lambda r: (order[r['col']], r['y0']))
    return idx, cut, ys, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', required=True, help='如 580-595（0-based，含两端）')
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--check', action='store_true', help='只报白槽位置，不 OCR')
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.pages.split('-'))
    idxs = [i for i in range(lo, hi + 1) if i in TWO_COL]
    skipped = [i for i in range(lo, hi + 1) if i not in TWO_COL]
    if skipped:
        print(f'  跳过单栏页 {skipped[0]}-{skipped[-1]}（{len(skipped)} 页，'
              f'整页 OCR 已够用，走 vol2_lines.jsonl）')
    if not idxs:
        print('该区间内没有双栏页')
        return 0

    if a.check:
        doc = fitz.open(str(PDF))
        for i in idxs:
            pix = doc[i].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
            arr = np.asarray(Image.frombytes('L', (pix.width, pix.height),
                                             pix.samples))
            ys = head_bottom(i, TWO_COL[i])
            auto = find_gutter(arr, y_from=ys)
            cut = CUT_OVERRIDE.get(i) or auto
            mark = f'（人工覆盖，自动值 {auto}）' if i in CUT_OVERRIDE else ''
            print(f'  p{i}  槽心 {cut} ({cut/arr.shape[1]:.3f})  '
                  f'整幅头 {TWO_COL[i]} 行 → y={ys}{mark}')
        return 0

    print(f'▶ 双栏 OCR  {len(idxs)} 页  workers={a.workers}', flush=True)
    res = {}
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for k, (idx, cut, ys, rows) in enumerate(ex.map(ocr_page, idxs), 1):
            res[idx] = rows
            print(f'  [{k}/{len(idxs)}] p{idx}  槽 {cut}  整幅头 {ys}px  '
                  f'{len(rows)} 行', flush=True)
    out = RAW / f'vol2_cols_{lo}_{hi}.jsonl'
    with out.open('w', encoding='utf-8') as fh:
        for i in idxs:
            fh.write(json.dumps({'page': i, 'lines': res[i]},
                                ensure_ascii=False) + '\n')
    print(f'✓ 写出 {out.name}  {out.stat().st_size:,} 字节  '
          f'{sum(len(v) for v in res.values())} 行')
    return 0


if __name__ == '__main__':
    sys.exit(main())
