#!/usr/bin/env python3
"""在 calvin/acts/*.md 注释段里的 `**N.**` 段落之前插入 per-verse 锚点
`<div class="commentary-anchor" id="acts-CH-N"></div>`，让 verse-index 胶囊
能精确跳到该节的注释段（而不是只能跳到经节范围的开头）。

输入：calvin/acts/N.md
输出：原地写入，每个注释段起首 `**V.**` 前加 per-verse 锚点
跳过：scripture-box 内的 `**N.**`（那是经文本身）

特殊情况：
- 同一节 V 在注释中多次出现 → 第二次起 id 加后缀 `acts-CH-V-2`、`-3` 等，
  verse-index 仍指向第一次出现的位置
- 注释段段首形如 `**14.** <span ...>` 或 `**14.** 直接接中文`，两种都要识别

用法：python3 scripts/add_acts_verse_anchors.py
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
SRC_DIR = ROOT / 'calvin' / 'acts'

# 段首 verse marker：`**N.**` 后跟空格或 <
VERSE_MARK_RE = re.compile(r'^\*\*(\d{1,3})\.\*\*[\s<]')


def add_verse_anchors(text: str, ch: int) -> tuple[str, int, int]:
    """Return (new_text, n_anchors_added, n_dup_skipped).

    思路：在 scripture-box 外，凡是行首匹配 `**N.**` 的都是注释段起首
    （scripture-box 内用的是 <strong>N.</strong> HTML，不会被 VERSE_MARK_RE 命中），
    在它之前插入 <div class="commentary-anchor" id="acts-CH-N"></div>。
    不依赖 prev_blank，因为 <!-- PAGE NN --> 会破坏空行规律。
    """
    lines = text.split('\n')
    out: list[str] = []
    in_scripture_box = False
    seen: dict[int, int] = {}   # verse -> occurrence count
    n_added = 0
    n_dup = 0

    for raw in lines:
        stripped = raw.strip()

        # 跟踪 scripture-box 进出
        if stripped.startswith('<div class="scripture-box"'):
            in_scripture_box = True
            out.append(raw)
            continue
        if in_scripture_box:
            if stripped == '</div>':
                in_scripture_box = False
            out.append(raw)
            continue

        m = VERSE_MARK_RE.match(raw)
        if m:
            v = int(m.group(1))
            seen[v] = seen.get(v, 0) + 1
            if seen[v] == 1:
                aid = f'acts-{ch}-{v}'
                out.append(f'<div class="commentary-anchor" id="{aid}"></div>')
                n_added += 1
            else:
                # 重复节号：用后缀 id，不被 verse-index 引用
                aid = f'acts-{ch}-{v}-{seen[v]}'
                out.append(f'<div class="commentary-anchor" id="{aid}"></div>')
                n_dup += 1
            out.append(raw)
            continue

        out.append(raw)

    return '\n'.join(out), n_added, n_dup


def main():
    total_added = 0
    total_dup = 0
    for path in sorted(SRC_DIR.glob('*.md')):
        if not path.stem.isdigit():
            continue
        ch = int(path.stem)
        text = path.read_text(encoding='utf-8')
        # 跳过已添加 per-verse 锚点的文件（避免重复跑造成嵌套）
        if re.search(rf'commentary-anchor" id="acts-{ch}-\d+"(?:></div>)', text):
            existing = len(re.findall(
                rf'commentary-anchor" id="acts-{ch}-\d+(?:-\d+)?"', text))
            print(f'  {path.name}: 已有 {existing} 个 per-verse anchor，跳过')
            continue
        new_text, n, d = add_verse_anchors(text, ch)
        if n:
            path.write_text(new_text, encoding='utf-8')
            print(f'  {path.name}: +{n} per-verse anchor (dup {d})')
            total_added += n
            total_dup += d
    print(f'\n✓ 合计添加 {total_added} 个 per-verse 锚点，跳过 {total_dup} 个重复节')


if __name__ == '__main__':
    main()
