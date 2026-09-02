#!/usr/bin/env python3
"""给贺智注释章节注入 per-verse 锚点，供章顶 verse-nav 与 /verse-index/ 使用。

贺智的注释段起首是加粗节号，形态比 Calvin 杂（英文源本身就不统一，中译又各
自发挥）：

    **3.**            **1, 2.**       **3-5.**      **32 33.**
    **8、9节。**       **43, 44 节。**  **15、16两节。**  **33，34.**

每个节号 → 一个锚点 `<div class="commentary-anchor" id="<book>-<ch>-<v>"></div>`，
插在该段之前。合节头（**6, 7.**）为**每一节**各出一个锚点，都落在同一段：
第 6 节和第 7 节的注释就是这一段，胶囊点哪个都该到这里（skill 07 §4
「一个胶囊一节注释」）。

幂等：先剥掉已有锚点再重新注入，可反复跑。

用法:
    python3 scripts/add_hodge_verse_anchors.py                 # 全部 en+zh
    python3 scripts/add_hodge_verse_anchors.py --book 2corinthians
    python3 scripts/add_hodge_verse_anchors.py --check         # 只报告不写
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOKS = ['1corinthians', '2corinthians']

ANCHOR_RE = re.compile(r'^<div class="commentary-anchor" id="[^"]+"></div>\n', re.M)

# 加粗节号头：**<数字串>**，中间允许 , ， 、 - – 空格 作分隔，
# 尾部允许「节」「两节」和 . / 。。后面必须跟空格或 < （红色经文 span）。
HEAD_RE = re.compile(
    r'^\*\*\s*'
    r'(\d{1,3}(?:\s*[,，、]\s*\d{1,3}|\s*[-–]\s*\d{1,3}|\s+\d{1,3})*)'
    r'\s*(?:两)?\s*节?\s*[.。]?\s*'
    r'\*\*(?=[\s<])'
)


def parse_verses(spec: str):
    """'6, 7' → [6,7]；'3-5' → [3,4,5]；'32 33' → [32,33]。"""
    verses = []
    for part in re.split(r'[,，、]|\s+(?=\d)', spec):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r'(\d{1,3})\s*[-–]\s*(\d{1,3})', part)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            if lo <= hi and hi - lo <= 60:
                verses.extend(range(lo, hi + 1))
            else:                      # 反序或离谱跨度，只当两个孤立节号
                verses.extend([lo, hi])
        elif part.isdigit():
            verses.append(int(part))
    # 去重保序
    seen, out = set(), []
    for v in verses:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def process(path: Path, book: str, ch: str, write: bool):
    text = path.read_text(encoding='utf-8')
    text = ANCHOR_RE.sub('', text)              # 幂等：先剥旧锚点

    out, seen = [], {}
    n_anchor = 0
    for line in text.split('\n'):
        m = HEAD_RE.match(line)
        if m:
            for v in parse_verses(m.group(1)):
                seen[v] = seen.get(v, 0) + 1
                # 同一节再起一段（贺智偶有）→ 第二次起加 -2/-3 后缀，
                # verse-index 只取首次出现的裸 id。
                suffix = '' if seen[v] == 1 else f'-{seen[v]}'
                out.append(f'<div class="commentary-anchor" '
                           f'id="{book}-{ch}-{v}{suffix}"></div>')
                n_anchor += 1
        out.append(line)
    new = '\n'.join(out)

    if write and new != text:
        path.write_text(new, encoding='utf-8')
    return n_anchor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    books = [a.book] if a.book else BOOKS
    total = 0
    for book in books:
        for sub, label in (('', 'en'), ('zh', 'zh')):
            d = ROOT / 'hodge' / book / sub if sub else ROOT / 'hodge' / book
            if not d.is_dir():
                continue
            files = sorted(d.glob('[0-9]*.md'), key=lambda p: int(p.stem))
            if not files:
                continue
            n = sum(process(f, book, f.stem, not a.check) for f in files)
            total += n
            print(f'{book}/{label:2s}  {len(files):2d} 章  {n:4d} 锚点')
    print(f'合计 {total} 锚点' + ('（--check，未写入）' if a.check else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
