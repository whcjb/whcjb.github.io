import sys, json, pathlib, collections
sys.path.insert(0,'scripts')
import davenant_witness as W
W.corpus()
prop = collections.defaultdict(collections.Counter)
for vol in (1, 2):
    for ln in (pathlib.Path('davenant_raw/colossians')/f'vol{vol}_lines.jsonl').open(encoding='utf-8'):
        d = json.loads(ln)
        for l in d['lines']:
            _, log = W.fix_line(vol, d['page'], l['text'])
            for o, n, why in log:
                prop[why][(o, n)] += 1
for why in sorted(prop, key=lambda k: -sum(prop[k].values())):
    c = prop[why]
    print(f'\n═══ {why}：{sum(c.values())} 处 / {len(c)} 种 ═══')
    for (o, n), k in c.most_common(40):
        print(f'  {k:4}  {o!r:18} → {n!r}')
