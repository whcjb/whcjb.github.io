#!/usr/bin/env python3
"""给律法合参(harmony-law-1/2/3/4)每个注释头 `**书卷 章:节。**` 前插入隐形
`<a class="verse-anchor" id="{slug}-{ch}-{v}"></a>` 锚点, 供经文索引精确跳转
(与对观福音合参 harmony-1/2/3 同构)。

幂等: 若该 id 已存在(scripture-anchor 精确命中 或 已插过的 verse-anchor)则跳过,
避免重复 id。范围 scripture-anchor(如 exodus-21-7-11)不算精确命中, 仍会为 21:7 插锚。
"""
import re
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
SLUG = {'创世记': 'genesis', '出埃及记': 'exodus', '利未记': 'leviticus',
        '民数记': 'numbers', '申命记': 'deuteronomy'}
# 尾部句号可选: law-1 注释头为 **书 章:节**(无句号), law-2/3/4 为 **书 章:节。**
HEAD_RE = re.compile(r'^(\*\*([一-鿿]+) (\d+):(\d+)[。.]?\*\*)', re.M)


def process(path):
    text = path.read_text(encoding='utf-8')
    existing = set(re.findall(r'\bid="([a-z]+-\d+-\d+)"', text))  # 精确逐节 id
    added = 0

    def repl(m):
        nonlocal added
        head, bk, ch, v = m.group(1), m.group(2), m.group(3), m.group(4)
        slug = SLUG.get(bk)
        if not slug:
            return head
        anchor_id = f'{slug}-{ch}-{v}'
        if anchor_id in existing:
            return head  # 已有精确锚点, 不重复
        existing.add(anchor_id)
        added += 1
        return f'<a class="verse-anchor" id="{anchor_id}"></a>\n\n{head}'

    new = HEAD_RE.sub(repl, text)
    if added:
        path.write_text(new, encoding='utf-8')
    return added


def main():
    total = 0
    for vol in (1, 2, 3, 4):
        vol_dir = ROOT / 'calvin' / f'harmony-law-{vol}'
        for path in sorted(vol_dir.glob('[0-9]*.md')):
            n = process(path)
            total += n
            if n:
                print(f'  {path.relative_to(ROOT)}: +{n}')
    print(f'\n共插入 {total} 个 verse-anchor')


if __name__ == '__main__':
    main()
