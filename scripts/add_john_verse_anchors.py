#!/usr/bin/env python3
"""为 calvin/john/N.md 每个 `**约翰福音 N:V。**` marker 段前插入 verse-anchor
H2，作为 verse-index 胶囊的跳转目标。

参照 romans 同款格式：

    <h2 class="verse-anchor" id="john-N-V" data-ref="约翰福音 N:V">约翰福音 N:V</h2>

    **约翰福音 N:V。** *phrase。* commentary...

CSS (calvin-en.html `.calvin-en-content h2.verse-anchor`) 已将 h2 隐藏 +
scroll-margin-top:80px，跳转后注释段贴在 navbar 下面。

同一 verse 多段评论时（已经过 dedupe，第二段及之后没有 marker 前缀），
只对第一次出现插 anchor。

idempotent: 重跑跳过已存在 anchor。
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
DIR = ROOT / 'calvin' / 'john'

MARKER_RE = re.compile(r'^\*\*约翰福音 (\d+):(\d+)。\*\*')
ANCHOR_RE = re.compile(r'^<h2 class="verse-anchor" id="john-(\d+)-(\d+)"')


def process(path: Path) -> int:
    ch_file = int(path.stem)
    text = path.read_text(encoding='utf-8')
    lines = text.split('\n')
    out = []
    seen = set()
    # 先扫一遍已有 anchor 占用
    for ln in lines:
        m = ANCHOR_RE.match(ln)
        if m:
            seen.add((int(m.group(1)), int(m.group(2))))
    n_added = 0
    for i, ln in enumerate(lines):
        m = MARKER_RE.match(ln)
        if m:
            ch, v = int(m.group(1)), int(m.group(2))
            if ch == ch_file and (ch, v) not in seen:
                anchor = (
                    f'<h2 class="verse-anchor" id="john-{ch}-{v}" '
                    f'data-ref="约翰福音 {ch}:{v}">约翰福音 {ch}:{v}</h2>'
                )
                out.append(anchor)
                out.append('')
                seen.add((ch, v))
                n_added += 1
        out.append(ln)
    if n_added:
        new_text = '\n'.join(out)
        # 折叠任何 3+ 连续空行 → 2
        new_text = re.sub(r'\n{3,}', '\n\n', new_text)
        path.write_text(new_text, encoding='utf-8')
    return n_added


def main():
    total = 0
    for f in sorted(DIR.glob('*.md')):
        if not f.stem.isdigit():
            continue
        n = process(f)
        if n:
            print(f'  {f.name}: added {n} verse-anchors')
            total += n
    print(f'\nTotal: {total}')


if __name__ == '__main__':
    main()
