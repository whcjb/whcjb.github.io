#!/usr/bin/env python3
"""判读到底改了哪些词：拿已发布正文与修复后的 raw 逐词比对。

判读器每跑一轮都会覆盖自己的日志，而它要跑三四轮才收敛——最后一轮的日志
是空的，累计改了什么反而查不到。这个脚本直接比对两端产物，得到的是**最终
生效**的全部改动，比任何一轮的日志都完整。

    python3 scripts/isaiah_applied_diff.py
"""
import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'alexander_raw/isaiah/en_chapters'
PUB = ROOT / 'alexander/isaiah'
OUT = ROOT / 'logs/alexander_isaiah_applied.tsv'

FRONT = re.compile(r'^---.*?^---\n', re.S | re.M)
SEGMENT = re.compile(r'(<!--.*?-->|</?[A-Za-z][^<>]*>)', re.S)


def words(text):
    text = FRONT.sub('', text)
    return [w for seg in SEGMENT.split(text) if not seg.startswith('<')
            for w in seg.split()]


def main():
    rows = []
    for raw_path in sorted(RAW.glob('*.md')):
        pub_path = PUB / raw_path.name
        if not pub_path.exists():
            continue
        a = words(raw_path.read_text(encoding='utf-8'))
        b = words(pub_path.read_text(encoding='utf-8'))
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                None, a, b, autojunk=False).get_opcodes():
            if tag == 'equal':
                continue
            rows.append((raw_path.stem, ' '.join(a[i1:i2]), ' '.join(b[j1:j2])))
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('chapter\tbefore\tafter\n')
        for r in rows:
            f.write('\t'.join(r) + '\n')
    print(f'判读最终生效的改动 {len(rows)} 处 → {OUT}')


if __name__ == '__main__':
    main()
