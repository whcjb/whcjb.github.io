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
# 注释家 → 书卷。司布真马太福音的节号头形态（`**11, 12.**` / `**4-6.**`）
# 与贺智林前后完全同型，HEAD_RE 直接可用，所以共用本脚本，只把目录参数化。
AUTHOR_BOOKS = {
    'hodge':    ['1corinthians', '2corinthians', 'romans', 'ephesians'],
    'spurgeon': ['matthew'],
}
BOOKS = AUTHOR_BOOKS['hodge']

ANCHOR_RE = re.compile(r'^<div class="commentary-anchor" id="[^"]+"></div>\n', re.M)

# 加粗节号头：**<数字串>**，中间允许 , ， 、 - – 空格 作分隔，
# 尾部允许「节」「两节」和 . / 。。后面必须跟空格或 < （红色经文 span）。
HEAD_RE = re.compile(
    r'^\*\*\s*'
    r'(\d{1,3}(?:\s*[,，、]\s*\d{1,3}|\s*[-–]\s*\d{1,3}|\s+\d{1,3})*)'
    r'\s*(?:两)?\s*节?\s*[.。]?\s*'
    r'\*\*(?=[\s<])'
)


# 罗马书的节号头不是加粗数字，而是小型大写的 `VERSE 1.` / `VERSES 6, 7.` /
# `VERSES 12-21.`（AGES 排版把 V 与 ERSE 分成两个 span，collapse_spaced_caps
# 合并后就是这个形态）。全书 377 个头：VERSE N. 333 / VERSES N, N. 24 /
# VERSES N-N. 17 / VERSES N-N, AND N-N. 1 / VERSES N, N, N. 1 / VERSE: N. 1，
# 另有 2 个无号的裸 `VERSE.`（无从定位，跳过）。
HEAD_VERSE_RE = re.compile(
    r'^VERSES?\s*[:.]?\s*'
    r'(\d{1,3}(?:\s*(?:[,，、]|[-–]|\s+AND\s+)\s*\d{1,3})*)'
    r'\s*[.。]?\s*(?=[\s<])'
)


# 以弗所书的节号头是第三种形态：`V. 4.` / `Vs. 26. 27.` / `VS. 20, 21.`，
# 既不是加粗数字（林前后）也不是小型大写 VERSE（罗马书）。全书 141 处，
# 语料里单数前缀 `V.` **一次都没有**带多个节号（复合一律写成 `Vs.`/`VS.`），
# 所以单数只取一个数字——放开成列表会把正文里 `V. 4. 1. In its primary
# sense…` 这种「节号 + 列举项」连读成两节。
# 数字位允许字母 l：AGES 数字化把 1 印成小写 L 是本书的老毛病（章头 `CHAPTER Vl`
# 是同一种），以弗所书 6:1 的节号头就是 `V. l.`。全书只此 1 处，其余三本一处
# 没有（那三本唯一的非数字是 `V. The`，字符类挡掉了）。
HEAD_V_ONE_RE = re.compile(r'^V\.\s*([\dl]{1,3})\s*\.?\s*(?=[\s<])')
HEAD_V_MULTI_RE = re.compile(
    r'^V[sS]\.\s*(\d{1,3}(?:\s*[.,]\s*\d{1,3})*)\s*\.?\s*(?=[\s<])')


# 中文页的节号头：`第 1 节` / `第1节`（空格可有可无），复合写法
# `第 1、2 节` / `第 1-2 节` 一并认。英文页是 `V. 1.`，翻译时按中文习惯改写成
# 这个形态，所以中文页不能靠继承英文页的锚点——发布链条只要在「重发英文页」
# 与「补锚点」之间翻译了某一章，那一章的中文页就一个锚点都没有
# （以弗所书 ch4 只继承到 1 个、ch6 2 个，就是这么来的）。
HEAD_CN_RE = re.compile(
    r'^第\s*(\d{1,3}(?:\s*[、,，]\s*\d{1,3}|\s*[-–至]\s*\d{1,3})*)\s*节')


def parse_verses(spec: str):
    """'6, 7' → [6,7]；'3-5' → [3,4,5]；'32 33' → [32,33]。"""
    verses = []
    for part in re.split(r'[,，、]|\s+AND\s+|\s+(?=\d)', spec):
        part = part.strip().strip('.')
        if part and re.fullmatch(r'[\dl]+', part):
            part = part.replace('l', '1')      # 见 HEAD_V_ONE_RE 上方注释
        if not part:
            continue
        m = re.fullmatch(r'(\d{1,3})\s*[-–至]\s*(\d{1,3})', part)
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
        m = (HEAD_RE.match(line) or HEAD_VERSE_RE.match(line)
             or HEAD_V_MULTI_RE.match(line) or HEAD_V_ONE_RE.match(line)
             or HEAD_CN_RE.match(line))
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
    ap.add_argument('--author', default='hodge', choices=sorted(AUTHOR_BOOKS))
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    books = [a.book] if a.book else AUTHOR_BOOKS[a.author]
    total = 0
    for book in books:
        for sub, label in (('', 'en'), ('zh', 'zh')):
            d = ROOT / a.author / book / sub if sub else ROOT / a.author / book
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
