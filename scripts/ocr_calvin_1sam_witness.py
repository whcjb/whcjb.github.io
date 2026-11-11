#!/usr/bin/env python3
"""加尔文《撒母耳记上讲章》拉丁文本：tesseract 第二证人。

    python3 scripts/ocr_calvin_1sam_witness.py [--jobs 4]

底本 PDF（日内瓦大学开放档案的 CO 29 / 30 扫描件）自带一层 OCR 文字（含斜体），那是主文本；
这里用 tesseract `script/Latin`（实测比 `lat` 少一大批 c→e 误读）对同一份页图另读一遍，只当证人：两家分歧处才进判读，证人的字不直接落盘。

页图取 PDF 内嵌的原生图（2500×3150，300 dpi 黑白），不重采样（old-book-ocr §2.5）。
按文字层的栏界把页图切成左右两栏分别读（--psm 6），避免跨栏串行。
产物：calvin_sermons_raw/1samuel/witness_tess.jsonl，一行一栏 {vol, page, col, text}；已有的页跳过，可断点续跑。
"""
import argparse
import io
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import fitz
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_calvin_1sam import SINGLE_COL, gutter_chars  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'calvin_sermons_raw' / '1samuel'
OUT = RAW / 'witness_tess.jsonl'
VOLS = {'29': (RAW / 'src' / 'co29.pdf', 131, 384), '30': (RAW / 'src' / 'co30.pdf', 15, 417)}   # 1 起的 PDF 页码，含首尾


def col_split(page):
    """文字层里两栏的分界（页面坐标），与抽取脚本同一个判据（extract_calvin_1sam.gutter_chars）。"""
    lines = [l for b in page.get_text('rawdict')['blocks'] for l in b.get('lines', [])]
    return gutter_chars(lines, page.rect.width) if lines else page.rect.width / 2


def work(args):
    vol, pno = args
    pdf, _, _ = VOLS[vol]
    d = fitz.open(pdf)
    page = d[pno - 1]
    imgs = page.get_images(full=True)
    if not imgs:
        return []
    xref = imgs[0][0]
    pix = d.extract_image(xref)
    im = Image.open(io.BytesIO(pix['image'])).convert('L')
    sx = im.width / page.rect.width
    cut = int(col_split(page) * sx)
    out = []
    boxes = [(0, 0, im.width, im.height)] if (vol, pno) in SINGLE_COL else [(0, 0, cut, im.height), (cut, 0, im.width, im.height)]
    for ci, box in enumerate(boxes, 1):
        crop = im.crop(box)
        buf = io.BytesIO()
        crop.save(buf, format='PNG')
        r = subprocess.run(['tesseract', 'stdin', 'stdout', '-l', 'script/Latin', '--psm', '6'],
                           input=buf.getvalue(), capture_output=True)
        out.append({'vol': vol, 'page': pno, 'col': ci, 'text': r.stdout.decode('utf-8', 'replace')})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', type=int, default=4)
    a = ap.parse_args()
    done = set()
    if OUT.exists():
        for ln in OUT.read_text(encoding='utf-8').splitlines():
            r = json.loads(ln)
            done.add((r['vol'], r['page']))
    todo = [(v, p) for v, (_, a0, a1) in VOLS.items() for p in range(a0, a1 + 1) if (v, p) not in done]
    print(f'待读 {len(todo)} 页', flush=True)
    with ProcessPoolExecutor(a.jobs) as ex, OUT.open('a', encoding='utf-8') as f:
        for i, res in enumerate(ex.map(work, todo, chunksize=2), 1):
            for r in res:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
            f.flush()
            if i % 25 == 0:
                print(f'{i}/{len(todo)}', flush=True)
    print('完成')


if __name__ == '__main__':
    main()
