"""按位置核定表的自检：管线到底问到了哪些 (卷,页,词)。

手工表是按整串匹配的，上游一改就**静默失效**（old-book-ocr §3.3）。
这个脚本不去猜 token 长什么样，直接 spy 住 manual_repair，记录管线实际
问过的每一个键，再拿票据去比——命中、页号错、从没问过，分三档报出来。

⚠️ 盲区：本脚本只遍历正文那份源（vol*_lines.jsonl）。索引走的是分栏源
vol2_cols_*.jsonl，附卷的段落级查表（manual_para）也不在这里体现——
这两路的票在本脚本里会被误报成「页号错」或「从没问过」。
实测教训：`2|588|hy`→`by` 本来是对的，按本脚本的报告撤票之后，
索引里的 `badly observed by the Papists` 就被改坏成了 `hy`。
撤票前务必先确认该票属于哪一路。
"""
import sys, json, pathlib, collections
sys.path.insert(0, 'scripts')
import davenant_witness as W
W.corpus()
seen = collections.defaultdict(set)
orig = W.manual_repair
def spy(vol, page, w, nxt=None):
    s = seen[(vol, page)]
    s.add(w); s.add(w.rstrip('.,;:!?'))
    if nxt:                       # 带后词限定的票（`change.>taking`）也要记
        s.add(f'{w}>{nxt}'); s.add(f"{w.rstrip('.,;:!?')}>{nxt}")
    return orig(vol, page, w, nxt)
W.manual_repair = spy
for vol in (1, 2):
    for ln in (pathlib.Path('davenant_raw/colossians')/f'vol{vol}_lines.jsonl').open(encoding='utf-8'):
        d = json.loads(ln)
        for l in d['lines']:
            W.fix_line(vol, d['page'], l['text'])
W.manual_repair = orig
votes = {k: v for k, v in json.load(open('davenant_raw/colossians/manual_votes.json')).items()
         if not k.startswith('_')}
hit, moved, never = [], [], []
for k, v in votes.items():
    p = k.split('|', 2)
    if len(p) != 3 or not p[0].isdigit() or not p[1].isdigit():
        continue
    vol, pg, w = int(p[0]), int(p[1]), p[2]
    if w in seen[(vol, pg)]:
        hit.append(k); continue
    where = sorted(pp for (vv, pp), s in seen.items() if vv == vol and w in s)
    (moved if where else never).append((k, v, where))
print(f'命中 {len(hit)} · 页号错 {len(moved)} · 从没问过 {len(never)}\n')
print('── 页号错 ──')
out = {}
for k, v, wh in moved:
    print(f'  {k:26} → {v!r:18} 实际页 {wh[:4]}')
    out[k] = wh
json.dump(out, open('/tmp/vote_move.json', 'w'))
print('\n── 从没问过 ──')
for k, v, _ in never:
    print(f'  {k:26} → {v!r}')
