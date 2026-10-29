#!/usr/bin/env python3
"""亚历山大《使徒行传注释》判读用裁图：在原图上找含指定串的行，连上下各一行裁出。

用法：python3 scripts/crop_alexander_acts.py <IA 编号> <页序号> <搜索串> [<搜索串> ...]
      搜索串按 tesseract 在原图上读出的行文字找（不分大小写）
      → alexander_raw/acts/work/crops/<编号>_<页>_<词>.png

页序号即 ABBYY 的第几页（1 起），原图取 IA 的 <编号>_jp2.zip 里第 <页序号-1> 张。
"""
import subprocess
import io
import re
import sys
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander_raw' / 'acts' / 'src'
OUT = ROOT / 'alexander_raw' / 'acts' / 'work' / 'crops'


def tess_lines(png):
    """tesseract 行框：ABBYY 的坐标系与 IA 发布的 jp2 不一致（宽高比都不同），只能在图上重新定位。"""
    tsv = subprocess.run(['tesseract', str(png), '-', '--psm', '4', 'tsv'], capture_output=True, text=True).stdout
    lines = {}
    for row in tsv.splitlines()[1:]:
        f = row.split('\t')
        if len(f) < 12 or not f[11].strip():
            continue
        k = (f[2], f[3], f[4])
        l, t, w, h = map(int, f[6:10])
        x = lines.setdefault(k, [[], l, t, l + w, t + h])
        x[0].append(f[11]); x[1] = min(x[1], l); x[2] = min(x[2], t); x[3] = max(x[3], l + w); x[4] = max(x[4], t + h)
    return sorted(([' '.join(v[0])] + v[1:] for v in lines.values()), key=lambda r: r[2])


def main():
    ident, page, words = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f'{ident}_{page}.png'
    if not png.exists():
        url = (f'https://archive.org/download/{ident}/{ident}_jp2.zip/{ident}_jp2%2F{ident}_{page - 1:04d}.jp2')
        Image.open(io.BytesIO(urllib.request.urlopen(url, timeout=180).read())).convert('L').save(png)
    im = Image.open(png)
    lines = tess_lines(png)
    for w in words:
        hits = [i for i, l in enumerate(lines) if w.lower() in l[0].lower()]
        if not hits:
            print(f'{w}: tesseract 本页没读到', file=sys.stderr)
            continue
        for k, i in enumerate(hits):
            a, b = max(i - 1, 0), min(i + 1, len(lines) - 1)
            t = min(l[2] for l in lines[a:b + 1]); bt = max(l[4] for l in lines[a:b + 1])
            name = re.sub(r'\W', '_', w)
            p = OUT / f'{ident}_{page}_{name}_{k}.png'
            im.crop((0, max(t - 6, 0), im.size[0], bt + 6)).save(p)
            print(p)


if __name__ == '__main__':
    main()
