#!/usr/bin/env python3
"""已发布正文的廉价体检。改完正文顺手跑一遍，别等人翻出来。

三项，都是踩过的：

  星号奇偶   斜体 `*…*` 必须成对。文本级替换很容易多插或少插一个星号，
             kramdown 那边不会报错，只会把半截星号原样吐在页面上。
             （诗篇线上线时有 3 篇不配对，其中一篇正是自动规则多插的。）
  页眉残渣   页眉混进正文，按完整形态搜是搜不全的——页眉本身也会被 OCR
             读崩。诗篇线查过 `Psalm N:N` 的完整形态，漏了读成 `Psakn`
             的那种。这里按**字形归一**后的形态搜。
  HTML 配对  `<span>` 一类标签少一个闭合，整页版式就塌了。

    python3 scripts/isaiah_sanity.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / 'alexander/isaiah'
FRONT = re.compile(r'^---.*?^---\n', re.S | re.M)
TAG = re.compile(r'</?([A-Za-z][A-Za-z0-9]*)\b[^<>]*?(/?)>')

# 页眉原文是 "ISAIAH, CHAP. XIV." / "CHAPTER XXXIX."；OCR 读崩之后
# 字母会互相串（I↔l↔1、A↔4、H↔ll、S↔5、C↔0↔O），所以先把易混字形
# 归一再搜，不按字面。
SQUASH = str.maketrans('01458|', 'OIASBI')


def runhead_like(s):
    t = re.sub(r'[^A-Za-z0-9|]', '', s).upper().translate(SQUASH)
    return bool(re.search(r'(ISAIAH|ISAIAII)CHAP|CHAPTER[IVXLC]{1,9}$', t))


def main():
    bad = 0
    for path in sorted(PUB.glob('*.md')):
        raw = path.read_text(encoding='utf-8')
        body = FRONT.sub('', raw)

        # 一、星号奇偶。转义过的 `\*` 是字面星号，不参与配对
        n = len(re.findall(r'(?<!\\)\*', body))
        if n % 2:
            print(f'{path.name}: 星号 {n} 个，不配对')
            bad += 1

        # 二、页眉残渣。正文里任何一段连续大写串像页眉都算
        for m in re.finditer(r'[A-Z][A-Z0-9 .,|]{10,}', body):
            if runhead_like(m.group()):
                print(f'{path.name}: 疑似页眉混入 → {m.group()[:48]!r}')
                bad += 1

        # 三、HTML 标签配对
        depth = {}
        for m in TAG.finditer(body):
            if m.group(2):
                continue
            depth[m.group(1)] = depth.get(m.group(1), 0) + (
                -1 if m.group(0).startswith('</') else 1)
        for tag, d in depth.items():
            if d:
                print(f'{path.name}: <{tag}> 未配对，差 {d}')
                bad += 1
    print('体检通过，没发现问题' if not bad else f'共 {bad} 处要看')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
