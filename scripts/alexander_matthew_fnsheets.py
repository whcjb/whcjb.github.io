#!/usr/bin/env python3
"""亚历山大《马太福音释义》脚注转录用图：每页裁出页脚注区（连同上面几行正文，看得见注号）。

    python3 scripts/alexander_matthew_fnsheets.py 26 28 30      # 指定页（ABBYY 页序号，1 起）
    python3 scripts/alexander_matthew_fnsheets.py --all         # work/fn_pages.json 里的全部页
    → alexander_raw/matthew/work/fnsheets/p<页>.jpg  与  p<页>.txt（OCR 草稿，只作对照）

原图取 IA 的 <编号>_jp2.zip 里第 <页序号-1> 张（与 crop_alexander_acts.py 同）。ABBYY 坐标系与 jp2 不一致，
按页高比例换算，上下各放宽一截。
"""
import io
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_alexander_matthew as X  # noqa: E402

IDENT = X.VOLS[0]
OUT = X.WORK / 'fnsheets'
PAGE_H = 3431                     # 主扫描本 ABBYY 页高


def fetch(page):
    f = X.WORK / 'pages' / f'{page:04d}.png'
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        url = f'https://archive.org/download/{IDENT}/{IDENT}_jp2.zip/{IDENT}_jp2%2F{IDENT}_{page - 1:04d}.jp2'
        Image.open(io.BytesIO(urllib.request.urlopen(url, timeout=180).read())).convert('L').save(f)
    return Image.open(f)


def main():
    pages = json.loads((X.WORK / 'fn_pages.json').read_text())['pages'] if sys.argv[1:] == ['--all'] \
        else [int(x) for x in sys.argv[1:]]
    d = dict(X.load_abbyy(IDENT))
    OUT.mkdir(parents=True, exist_ok=True)
    for pg in pages:
        pars = d[pg]
        small = [p['top'] for p in pars if p['small'] and p['top']]
        im = fetch(pg)
        W, H = im.size
        top = (min(small) / PAGE_H if small else 0.62) - 0.10
        crop = im.crop((0, int(max(top, 0) * H), W, H))
        if crop.width > 1500:
            crop = crop.resize((1500, int(crop.height * 1500 / crop.width)))
        crop.save(OUT / f'p{pg}.jpg', quality=85)
        txt = [' '.join(w for w, _ in p['words']) for p in pars if p['small']]
        (OUT / f'p{pg}.txt').write_text('\n'.join(txt) + '\n', encoding='utf-8')
        print(OUT / f'p{pg}.jpg', W, H)


if __name__ == '__main__':
    main()
