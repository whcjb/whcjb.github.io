"""花括号分析表体检：重建表里的每一块都要出现在产物里。

按页面影像手工重建的块（brace_blocks.json）是**替换**出来的，抽取那边一旦
对不上就 SystemExit；但产物这一侧也要看一眼——publish 若没认 [BRACE] 这个
tag，块会静默消失，抽取那边察觉不到。
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
tbl = json.loads((ROOT / 'davenant_raw/colossians/brace_blocks.json')
                 .read_text(encoding='utf-8'))
want = {k: v['html'] for k, v in tbl.items() if not k.startswith('_')}
txt = '\n'.join(p.read_text(encoding='utf-8')
                for p in sorted((ROOT / 'davenant/colossians').glob('*.md')))
bad = 0
for k, html in sorted(want.items()):
    head = html.split('\n')[1] if '\n' in html else html
    if head not in txt:
        print(f'  x {k} 没落到产物里：{head[:60]}')
        bad += 1
opens = len(re.findall(r'<div class="dv-brace">', txt))
print(f'  重建表 {len(want)} 块，产物里缺 {bad}；dv-brace 开 {opens} 个')
