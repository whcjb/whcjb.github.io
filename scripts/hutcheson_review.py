#!/usr/bin/env python3
"""判读图人工复核 → gap_review_1841.tsv（按 slug + ord 落，重跑 match 也不丢）。

    python3 scripts/hutcheson_review.py list [起 止]      # 编号 → slug/ord/TCP/自动判读
    python3 scripts/hutcheson_review.py add  '0=' '1=take' '7=?'

编号是判读图上的 `#n`（witness_locs.json 的下标）。值：
  =       采纳自动判读
  ?       看过，判不了（定位错 / 影像也糊）
  词      判读结果，只写缺字所在词的**词身**，前后标点由脚本按 TCP 原样补回；
          拼写按 1657（本书语料）——1841 的现代拼写不照搬
  !整串   原样替换整个 TCP 词（含标点；词身与标点都要改时用）
证据列自动记 `img 1841 <页>`。复核表的结论优先于 judge 的自动判读。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'hutcheson_raw' / 'john'
LOCS = RAW / 'witness_locs.json'
DEC = RAW / 'gap_decisions_witness.tsv'
REV = RAW / 'gap_review_1841.tsv'
P = '.,;:()?!\'"[]’‘'


def auto():
    d = {}
    if DEC.exists():
        for ln in DEC.read_text(encoding='utf-8').splitlines():
            if ln and not ln.startswith('#'):
                f = ln.split('\t')
                d[(f[0], int(f[1]))] = f[3]
    return d


def load_rev():
    rv = {}
    if REV.exists():
        for ln in REV.read_text(encoding='utf-8').splitlines():
            if ln and not ln.startswith('#'):
                f = ln.split('\t')
                rv[(f[0], int(f[1]))] = f
    return rv


def save_rev(rv):
    rows = sorted(rv.values(), key=lambda f: (f[0], int(f[1])))
    REV.write_text('# slug\tord\ttcp_word\t判读(?=看过判不了)\t证据\n'
                   + '\n'.join('\t'.join(f) for f in rows) + '\n', encoding='utf-8')


def wrap(tcp, body):
    lead = len(tcp) - len(tcp.lstrip(P))
    trail = len(tcp) - len(tcp.rstrip(P))
    return tcp[:lead] + body + (tcp[len(tcp) - trail:] if trail else '')


def main():
    locs = json.loads(LOCS.read_text(encoding='utf-8'))
    au = auto()
    rv = load_rev()
    if sys.argv[1] == 'list':
        a, b = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, len(locs))
        for n in range(a, min(b, len(locs))):
            r = locs[n]
            k = (r['slug'], r['ord'])
            print(n, r['slug'], r['ord'], r['tcp'], '→', au.get(k, '?'), '| 复核:', rv[k][3] if k in rv else '—')
        return
    for arg in sys.argv[2:]:
        n, v = arg.split('=', 1)
        r = locs[int(n)]
        k = (r['slug'], r['ord'])
        if v in ('=', ''):           # `N=` 与 `N==` 都是采纳自动判读（空值曾被误当成「判读为空」）
            fixed = au.get(k, '?')
            if fixed == '?':
                print(f'#{n} 没有自动判读可采纳', file=sys.stderr)
                continue
        elif v == '?':
            fixed = '?'
        elif v.startswith('!'):
            fixed = v[1:]
        else:
            fixed = wrap(r['tcp'], v)
        rv[k] = [r['slug'], str(r['ord']), r['tcp'], fixed, f"img 1841 {r.get('pid', '')}"]
    save_rev(rv)
    print(f'复核表 {len(rv)} 条（判出 {sum(f[3] != "?" for f in rv.values())}）', file=sys.stderr)


if __name__ == '__main__':
    main()
