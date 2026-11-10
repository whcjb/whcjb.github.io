#!/usr/bin/env python3
"""霍志恒《诗篇的末世论》中文页发布：vos_raw/psalter/zh_chapters/index.md → vos/psalter/zh/index.md

中文 raw 由 scripts/translate_vos.py 产出（正文段落 + 末尾 `[^n]: …` 脚注，排版标记已还原）。
这里只套页面外壳：front matter、底本说明、署名；不改译文。重跑逐字节不变。
英文页的「中文版 →」链接由 publish_vos_psalter.py 在中文页存在时自动加。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'vos_raw' / 'psalter'
SRC = RAW / 'zh_chapters' / 'index.md'
OUT = ROOT / 'vos' / 'psalter' / 'zh' / 'index.md'


def main():
    if not SRC.exists():
        sys.exit('还没有中文 raw：先跑 scripts/translate_vos.py')
    body = SRC.read_text(encoding='utf-8').strip()
    # 英文 raw 里的底本说明与署名是 keep 块，原样带过来了：换成中文
    body = re.sub(r'<div class="vs-source".*?</div>\s*', '', body, flags=re.S)
    body = re.sub(r'<p class="vs-sign">.*?</p>\s*', '', body, flags=re.S)
    paras, _, notes = body.partition('\n[^1]:')
    notes = '[^1]:' + notes if notes else ''
    date = json.loads((RAW / 'zh_meta.json').read_text(encoding='utf-8'))['index']
    n_corr = sum(1 for ln in (RAW / 'corrections.tsv').read_text(encoding='utf-8').splitlines()
                 if ln.strip() and not ln.startswith('#'))
    out = ['---',
           'layout: vos-essay',
           'zh: true',
           'title: "诗篇的末世论"',
           'subtitle: "Geerhardus Vos · 《普林斯顿神学评论》第 18 卷（1920 年 1 月）第 1–43 页"',
           'en_url: /vos/psalter/',
           'description: "霍志恒《诗篇的末世论》（Eschatology of the Psalter，1920）中译全文，附原注。"',
           f'date: {date}',
           '---',
           '',
           '<div class="vs-source" markdown="0">'
           '英文底本据 Ted Hildebrandt 录入本，与 1920 年《普林斯顿神学评论》原刊扫描逐词比对，'
           f'出入处看原刊页图读定，改正 {n_corr} 处（原书误植照录）；中译据校定后的英文本。'
           '灰色 <span class="vs-pbk">p.N</span> 为 1920 年原刊页码。'
           '</div>',
           '',
           paras.strip(),
           '',
           '<p class="vs-sign"><i>Princeton.</i><span>Geerhardus Vos.</span></p>',
           '']
    if notes:
        out += [notes.strip(), '']
    text = '\n'.join(out)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    old = OUT.read_text(encoding='utf-8') if OUT.exists() else None
    OUT.write_text(text, encoding='utf-8')
    refs = re.findall(r'\[\^(\d+)\](?!:)', paras)
    defs = re.findall(r'^\[\^(\d+)\]:', notes, flags=re.M)
    print(f'{"未变" if old == text else "已写"} {OUT.relative_to(ROOT)}  注号 {len(refs)}  注文 {len(defs)}')
    if [int(x) for x in refs] != [int(x) for x in defs]:
        sys.exit('⛔ 中文页注号与注文对不上')


if __name__ == '__main__':
    main()
