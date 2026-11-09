#!/usr/bin/env python3
"""琼斯约翰二书、三书：第二证人 1636 印本（IA bim_…_jones-william-b-d_1636，719 叶）定位裁图。

    python3 scripts/jones_witness1636.py OUT_DIR 2john-013 3john-027 …

只用来复核 1635 胶片上判不定的推断（P:）与读不出（?）几组。定位/取叶照搬 jones_witness，换 ITEM 与目录；
1636 叶号 ≈ 印本页 + 5～7（前置叶比 1635 少），故在 +4～+10 里按 OCR 得分取最好的一叶。
紧图原生分辨率不缩放；另出整行（wrap）与旁注栏（margin）两版。卷首无页码几处见 MANUAL_LOC。
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jones_common as jc  # noqa: E402
import jones_witness as jw  # noqa: E402

jw.ITEM = 'bim_early-english-books-1475-1640_a-commentary-upon-the-ep_jones-william-b-d_1636'
jw.WIT = jc.BASE / 'witness1636'
jw.IMG = jw.WIT / 'img'
jw.OCR = jw.WIT / 'ocr'
MANUAL_LOC = {}


def locate(s):
    best = None
    for off in (5, 8):
        jw.LEAF_OFF = off
        for mode in ('', 'm') if s['stream'] == 'note' else ('',):
            r = jw.locate(s, mode)
            if r and (best is None or r[3] > best[3]):
                best = r
    return best


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    rep = {}
    for key in sys.argv[2:]:
        book, g = key.split('-')
        s = json.loads((jc.raw(book) / 'gap_sites.json').read_text(encoding='utf-8'))[int(g)]
        loc = MANUAL_LOC.get(key) or locate(s)
        if not loc:
            print(f'{key} 定位不到', file=sys.stderr)
            continue
        leaf, x, y = loc[:3]
        img = cv2.imread(str(jw.leaf_img(leaf)), cv2.IMREAD_GRAYSCALE)
        h, w = img.shape
        cv2.imwrite(str(out / f'{key}_tight.jpg'), img[max(0, y - 160):y + 260, max(0, x - 500):x + 1400])
        cv2.imwrite(str(out / f'{key}_margin.jpg'), img[max(0, y - 400):y + 400, :])
        rep[key] = dict(leaf=leaf, x=x, y=y, score=loc[3] if len(loc) > 3 else None, size=[w, h])
        print(key, rep[key], file=sys.stderr)
    (out / 'loc.json').write_text(json.dumps(rep, indent=0))


if __name__ == '__main__':
    main()
