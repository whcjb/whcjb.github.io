#!/usr/bin/env python3
"""列出还没判读的缺字组（gap_review.tsv 里没有、或判为 ? 的），供 rollock_witness.py sheets --gids 用。

    python3 scripts/rollock_todo.py [--q] [--from N] [--n K]    # --q 含已判 ? 的
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rollock_common as rc  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--q', action='store_true')
ap.add_argument('--from', dest='start', type=int, default=0)
ap.add_argument('--n', type=int, default=40)
ap.add_argument('--kind', choices=['hit', 'est', 'any'], default='any')
a = ap.parse_args()
done = {}
for f in rc._tsv('gap_review.tsv'):
    done[int(f[0])] = f[1]
locs = json.loads((rc.RAW / 'witness_locs.json').read_text(encoding='utf-8'))
out = []
for r in locs:
    g = r['gid']
    if g < a.start or (g in done and not (a.q and done[g] == '?')):
        continue
    b = r.get('bim')
    kind = 'none' if not b else 'est' if (b.get('est') or r.get('anchor')) else 'hit'
    if a.kind != 'any' and kind != a.kind:
        continue
    out.append(g)
    if len(out) >= a.n:
        break
print(','.join(map(str, out)))
