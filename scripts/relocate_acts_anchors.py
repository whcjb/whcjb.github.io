#!/usr/bin/env python3
"""把 calvin/acts/*.md 里 scripture-anchor 上的 id 从经文块前面挪到经文块后面，
让 verse-index 胶囊点击后直接落在注释段，而不是经文块。

原结构（id 在 h2 上 → 跳转落在经文块之前）：
    <h2 class="scripture-anchor" id="acts-1-1-2" data-ref="ACTS 1:1-2">...</h2>
    <div class="scripture-box" markdown="1">
      <p>...经文...</p>
    </div>

    <注释段...>

改后（id 移到经文块后的 commentary-anchor，跳转直接落在注释）：
    <h2 class="scripture-anchor" data-ref="ACTS 1:1-2">...</h2>
    <div class="scripture-box" markdown="1">
      <p>...经文...</p>
    </div>
    <span class="commentary-anchor" id="acts-1-1-2"></span>

    <注释段...>

特例：若某 h2 后面没有 scripture-box（注释段直接紧随 h2），则 commentary-anchor
紧贴 h2 之后，保证点击跳转仍落在注释开头。

用法：python3 scripts/relocate_acts_anchors.py
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
SRC_DIR = ROOT / 'calvin' / 'acts'

# 行级匹配：仅匹配 h2 scripture-anchor 上带 id="acts-..." 的；
# 其它带 id="f..." 的（ages footnote 锚点）不动。
H2_RE = re.compile(
    r'^(<h2 class="scripture-anchor")\s+id="(acts-[0-9-]+)"(.*?)>(.*)$'
)


def relocate_in_text(text: str) -> tuple[str, int]:
    lines = text.split('\n')
    out: list[str] = []
    n_moved = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        m = H2_RE.match(line)
        if not m:
            out.append(line)
            i += 1
            continue

        pre, aid, post_attrs, h2_tail = m.groups()
        new_h2 = f'{pre}{post_attrs}>{h2_tail}'
        anchor_line = f'<div class="commentary-anchor" id="{aid}"></div>'

        # 向后看：跳过空行，看下一行是否为 <div class="scripture-box"
        j = i + 1
        while j < len(lines) and lines[j].strip() == '':
            j += 1

        if j < len(lines) and lines[j].lstrip().startswith('<div class="scripture-box"'):
            # 找到这个 scripture-box 的 </div> 闭合
            k = j + 1
            depth = 1  # 已开一个 div
            while k < len(lines) and depth > 0:
                # 简化：只看 <div / </div ；md 里 markdown="1" 模式不含 nested div
                opens = lines[k].count('<div')
                closes = lines[k].count('</div>')
                depth += opens - closes
                if depth == 0:
                    break
                k += 1
            if k >= len(lines):
                # 没找到闭合，保留原样
                out.append(line)
                i += 1
                continue
            # 写入：new_h2 + 中间所有行（含 scripture-box 整块） + commentary-anchor
            out.append(new_h2)
            out.extend(lines[i + 1:k + 1])
            out.append(anchor_line)
            n_moved += 1
            i = k + 1
        else:
            # 紧随 h2 的不是 scripture-box → commentary-anchor 紧贴 h2 之后
            out.append(new_h2)
            out.append(anchor_line)
            n_moved += 1
            i += 1

    return '\n'.join(out), n_moved


def main():
    total = 0
    for path in sorted(SRC_DIR.glob('*.md')):
        if not path.stem.isdigit():
            continue
        text = path.read_text(encoding='utf-8')
        new_text, n = relocate_in_text(text)
        if n and new_text != text:
            path.write_text(new_text, encoding='utf-8')
            print(f'  {path.name}: {n} anchors relocated')
            total += n
    print(f'\n✓ 合计 {total} 个 anchor 已迁移到注释段开头')


if __name__ == '__main__':
    main()
