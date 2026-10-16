#!/usr/bin/env python3
"""gap_decisions.tsv（逐条影像判读记录）→ manual_fixes.tsv（按位落盘表）。

    python3 scripts/perkins_decisions.py

判读记录里：
  - 具体词  → 落盘
  - `=`     → 与同词前一处合并已判（同一个词里有两处缺字记号）
  - `?` / `?ED` / `?Z` → 未判（挂起：希腊文待放大 / 墨渍待他版 / 待放大），不落
tcp_word 一律从**抽取产物**按 perkins_common.gap_word 的口径取，与落盘时核位
的口径一致（切分口径两处必须一致）。判读时看的上下文去掉了斜体星号，若两种
口径取出的词不同，报出来人工看，不硬落。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perkins_common as pc  # noqa: E402

RAW = pc.RAW
DEC = RAW / 'gap_decisions.tsv'
LOCS = RAW / 'gap_locs.json'


def main():
    sites = {s['id']: s for s in json.loads(LOCS.read_text(encoding='utf-8'))}
    dec = {}
    for ln in DEC.read_text(encoding='utf-8').splitlines():
        if not ln.strip() or ln.startswith('#'):
            continue
        f = ln.split('\t')
        dec[int(f[0])] = (f[1], f[2] if len(f) > 2 else '')
    md_cache = {}
    rows, warn = [], []
    pend = {'?': 0, '?ED': 0, '?Z': 0, '=': 0}
    for i, (val, ev) in sorted(dec.items()):
        if val in pend:
            pend[val] += 1
            continue
        s = sites[i]
        slug = s['slug']
        md = md_cache.setdefault(slug, (pc.SRC / f'{slug}.md').read_text(encoding='utf-8'))
        ms = list(pc.TOK.finditer(md))
        m = ms[s['ord']]
        a, b = pc.gap_word(md, m)
        tcp = md[a:b]
        if tcp.replace('*', '') != s['word'].replace('*', ''):
            warn.append(f'#{i} {slug}: 判读口径 {s["word"]!r} ≠ 落盘口径 {tcp!r}')
            continue
        # 同词里若先出现的记号另有 ord，落盘表登记词里第一处记号的 ord
        first = next(k for k, mm in enumerate(ms) if a <= mm.start() < b)
        rows.append((slug, first, tcp, val, f'#{i} leaf {s["loc"]["leaf"] if s.get("loc") else "-"} {ev}'))
    out = ['# 帕金斯加拉太书缺字回填表（由 scripts/perkins_decisions.py 从 gap_decisions.tsv 生成，勿手改）',
           '# slug\tord\ttcp_word\tfixed\tevidence']
    seen = set()
    for r in rows:
        if (r[0], r[1]) in seen:
            warn.append(f'重复登记 {r[0]}#{r[1]}')
            continue
        seen.add((r[0], r[1]))
        out.append('\t'.join(map(str, r)))
    pc.FIXES.write_text('\n'.join(out) + '\n', encoding='utf-8')
    for w in warn:
        print('⚠️ ' + w, file=sys.stderr)
    print(f'落盘 {len(seen)} 条；挂起 {pend}', file=sys.stderr)


if __name__ == '__main__':
    main()
