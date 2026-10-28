#!/usr/bin/env python3
"""按页判读：缺字多、OCR 定位差时（巴洛 1625 胶片），把缺字按所在叶归组，每叶切上下两半出图，
同页的缺字一起对着整页读。

    python3 scripts/tcp_pages.py barlow --gids 0-60 [--name p]
    → witness/sheets/<name>_<叶>_{a,b}.jpg 与 <name>.txt（每叶的缺字清单与上下文）
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tcp_native import parse_gids  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('book')
    ap.add_argument('--gids', required=True)
    ap.add_argument('--name', default='p')
    a = ap.parse_args()
    raw = ROOT / f'{a.book}_raw' / '2timothy'
    W = raw / 'witness'
    locs = {r['gid']: r for r in json.loads((raw / 'witness_locs.json').read_text(encoding='utf-8'))}
    by = {}
    for g in parse_gids(a.gids):
        r = locs[g]
        if 'bim' in r:
            by.setdefault(r['bim']['leaf'], []).append(g)
    sh = W / 'sheets'
    for f in sh.glob(f'{a.name}_*.jpg'):
        f.unlink()
    lines = []
    for leaf in sorted(by):
        im = Image.open(W / 'img' / f'bim_{leaf:04d}.jpg').convert('L')
        h = im.height
        im.crop((0, 0, im.width, h * 55 // 100)).save(sh / f'{a.name}_{leaf:04d}_a.jpg', quality=88)
        im.crop((0, h * 45 // 100, im.width, h)).save(sh / f'{a.name}_{leaf:04d}_b.jpg', quality=88)
        lines.append(f'== 叶 {leaf}')
        for g in by[leaf]:
            r = locs[g]
            pos = r['bim'].get('gy', 0) / max(1, r['bim'].get('ph', 1))
            lines.append(f'#{g} {r["slug"]} {"[旁注]" if r["stream"] == "note" else ""} y≈{pos:.2f}  '
                         + ' '.join(r['left'][-6:]) + ' [[' + r['tcp'] + ']] ' + ' '.join(r['right'][:6]))
    (sh / f'{a.name}.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
