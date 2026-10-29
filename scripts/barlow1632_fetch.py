#!/usr/bin/env python3
"""巴洛 1632 年对开本（IA bim_…_barlow-john_1633，665 叶，800 ppi 胶片扫描）按叶取原图，存半尺寸灰度图（≈400 ppi）。

    python3 scripts/barlow1632_fetch.py 272-664

old-book-ocr §2.5：渲染取原生或 400 dpi，不上采样。原生一叶 ≈ 8900×13500，按 HTTP Range 从 *_jp2.zip 只取那一叶
（ia_rangezip.py），缩半存 witness/img/NNNN.jpg（磁盘紧，原图不落盘）。
"""
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ia_rangezip import RangeZip  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / 'barlow_raw' / '2timothy-1632' / 'witness' / 'img'
ITEM = 'bim_early-english-books-1475-1640_an-exposition-of-the-fis_barlow-john_1633'
_local = threading.local()


def one(leaf):
    out = IMG / f'{leaf:04d}.jpg'
    if out.exists():
        return 0
    if not hasattr(_local, 'z'):
        _local.z = RangeZip(ITEM, f'{ITEM}_jp2.zip')
    from PIL import Image
    im = _local.z.image(leaf).convert('L')
    im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    im.save(out, quality=90)
    return 1


def main():
    a, b = map(int, sys.argv[1].split('-'))
    IMG.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(14) as ex:
        for k, _ in enumerate(ex.map(one, range(a, b + 1))):
            if k % 10 == 0:
                print(f'{k}/{b - a + 1}', file=sys.stderr, flush=True)


if __name__ == '__main__':
    main()
