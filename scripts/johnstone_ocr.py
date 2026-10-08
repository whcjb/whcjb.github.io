#!/usr/bin/env python3
"""约翰斯通《腓立比书讲疏》—— 扫描原图重 OCR。

IA 自带的 OCR 是 ABBYY FineReader 8.0（2007），希腊文一个字符都没出来，
而这本书的副标题就是「附希腊文经文注释」。原图是 1995×3342（约 400 dpi），
够重跑，所以不迁就旧产物，直接从 jp2 重来。

每页跑**两遍**：
  eng+grc  —— 正文用这一遍。字准好，希腊文大部分也对。
  grc      —— 只为希腊文。eng+grc 会把一个词里最前面的希腊词当拉丁字母读
              （`γίνεσθε` → `yivseds`），grc-only 这一遍读得对；英文在这一遍
              里是乱码，所以只能当「希腊文证人」，不能整页替换。

两遍的产物都落盘，合流交给 extract_johnstone.py。OCR 很慢（单页约 8 秒），
落盘后重跑合流不必再 OCR。
"""
import argparse
import os
import subprocess
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'johnstone_raw', 'philippians')
PASSES = {'eng': 'eng+grc', 'grc': 'grc'}


def unpack(zip_path, img_dir):
    """jp2.zip → img_dir/NNNN.jp2（只解一次；已解过就跳过）"""
    os.makedirs(img_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        names = sorted(n for n in z.namelist() if n.lower().endswith('.jp2'))
        for n in names:
            # 包内名形如 lecturesexegeti00john_jp2/..._0056.jp2
            leaf = os.path.splitext(os.path.basename(n))[0].rsplit('_', 1)[-1]
            dst = os.path.join(img_dir, leaf + '.jp2')
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                continue
            with z.open(n) as src, open(dst, 'wb') as out:
                out.write(src.read())
    return sorted(f for f in os.listdir(img_dir) if f.endswith('.jp2'))


def ocr_one(args):
    img_dir, out_dir, name, lang = args
    leaf = os.path.splitext(name)[0]
    base = os.path.join(out_dir, leaf)
    if os.path.exists(base + '.txt') and os.path.getsize(base + '.txt') > 0:
        return leaf, 'cached'
    # tesseract 读不了 jp2，先转 png。opj_decompress 比 ImageMagick 稳。
    png = base + '.png'
    r = subprocess.run(['opj_decompress', '-i', os.path.join(img_dir, name),
                        '-o', png], capture_output=True)
    if r.returncode != 0 or not os.path.exists(png):
        return leaf, 'decode-fail'
    try:
        subprocess.run(['tesseract', png, base, '-l', lang, '--psm', '3'],
                       capture_output=True, check=True)
    finally:
        os.unlink(png)
    return leaf, 'ok'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zip', required=True, help='lecturesexegeti00john_jp2.zip')
    ap.add_argument('--pass', dest='which', choices=list(PASSES), default='eng')
    ap.add_argument('--jobs', type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument('--limit', type=int, default=0, help='只跑前 N 页（试水用）')
    a = ap.parse_args()

    img_dir = os.path.join(RAW, 'src', 'images')
    out_dir = os.path.join(RAW, 'src', 'ocr_' + a.which)
    os.makedirs(out_dir, exist_ok=True)
    names = unpack(a.zip, img_dir)
    if a.limit:
        names = names[:a.limit]
    print(f'{len(names)} pages → {out_dir} (lang={PASSES[a.which]}, jobs={a.jobs})',
          file=sys.stderr)

    tasks = [(img_dir, out_dir, n, PASSES[a.which]) for n in names]
    done = fail = 0
    with ProcessPoolExecutor(a.jobs) as ex:
        for leaf, status in ex.map(ocr_one, tasks):
            done += 1
            if status == 'decode-fail':
                fail += 1
                print(f'  !! {leaf} {status}', file=sys.stderr)
            if done % 25 == 0:
                print(f'  {done}/{len(names)}', file=sys.stderr)
    print(f'done {done}, decode-fail {fail}', file=sys.stderr)


if __name__ == '__main__':
    main()
