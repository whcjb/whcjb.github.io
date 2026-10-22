#!/usr/bin/env python3
"""打印缺字组在抽取产物里的原始 markdown 前后文（看斜体星号落在哪）。  python3 scripts/rollock_show.py 122 108 ..."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rollock_common as rc  # noqa: E402

sites = json.loads((rc.RAW / 'gap_sites.json').read_text(encoding='utf-8'))
by = {}
for s in sites:
    by.setdefault((s['book'], s['slug']), []).append(s['gid'])
for g in map(int, sys.argv[1:]):
    s = sites[g]
    md = rc.read_src(s['book'], s['slug'])
    k = by[(s['book'], s['slug'])].index(g)
    a, b, t, _ = rc.gap_groups(md)[k]
    ctx = md[max(0, a - 110):a] + '⟪' + t + '⟫' + md[b:b + 90]
    print(g, re.sub(r'<span class="rl-pb"[^>]*></span>', '¶', ctx).replace('\n', '⏎'))
