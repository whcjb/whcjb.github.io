#!/usr/bin/env python3
"""把误插进经文表单元格里的 commentary-anchor 挪到框外。

注释锚点（`<div class="commentary-anchor" id="…"></div>`）本来应该紧跟在经文框
`</div>` 之后，注释正文之前。有些章的锚点被插进了表格最后一格里，还带出一个多余
的 `</p>`：

    <td class="scripture-la">…quiete.</p>
    <div class="commentary-anchor" id="hosea-11-4"></div></td>

浏览器能容错渲染，但锚点落在框**内**——点经文导航跳过去会停在框上而不是注释
开头；`</p>` 也是孤立的闭标签。全库 100 余格。

修法：把单元格里的锚点整块取出来，连同紧挨它前面那个多余的 `</p>` 一起删掉，
再按通例放到该框 `</div>` 的后面。锚点的 id 一字不改。

用法：
    python3 scripts/fix_anchor_in_cell.py [--apply]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOX = re.compile(r'<div class="scripture-box[^"]*"[^>]*>.*?\n</div>', re.S)
CELL = re.compile(r'(<td class="scripture-(?:en|la)">)(.*?)(</td>)', re.S)
# 锚点有两种写法，第二种是坏的：闭标签写成了 </p>（habakkuk/hosea/joel 共 10 处）
ANCHOR = re.compile(r'\s*(?:</p>\s*)?(<div class="commentary-anchor"[^>]*>)\s*(?:</div>|</p>)\s*', re.S)


def fix_box(box: str):
    found = []

    def one(m):
        inner = m.group(2)
        if 'commentary-anchor' not in inner:
            return m.group(0)
        def grab(am):
            found.append(am.group(1) + '</div>')      # 统一补成合法的闭标签
            return ''
        return m.group(1) + ANCHOR.sub(grab, inner).rstrip() + m.group(3)

    new = CELL.sub(one, box)
    if not found:
        return box, []
    return new + '\n' + '\n'.join(found), found


# 坏锚点（`<div …></p>`）当初没闭合，后面往往跟着一个多出来的 `</div>` 替它收尾。
# 现在锚点自己闭合了，那个多余的就得去掉，否则框外凭空多一层 </div>
# （habakkuk/hosea/joel 共 10 处，开闭数会差 10）。
SURPLUS = re.compile(r'(<div class="commentary-anchor"[^>]*></div>)\n\n</div>')


def drop_surplus_div(text: str):
    return SURPLUS.subn(r'\1', text)


# 更狠的一种：锚点注入把整个框头都替换掉了——`<div class="scripture-box">` 与
# `<table><tbody><tr><td class="scripture-en">` 全没了，只剩一个孤零零的
# `<p class="scripture-ref">` 加一段 `<p>` 正文，后面直接接 `</td><td …>`：
#
#     <p class="scripture-ref">…</p>
#     <p style="margin-left:2em;" markdown="1"><strong>3.</strong> 中文</p>
#     <div class="commentary-anchor" id="amos-3-3-8"></p></td><td class="scripture-la">…
#
# 页面上这一框整个塌掉（裸的 </td>、表格没有开标签）。阿摩司书 3、以西结书 16
# 各一处。把框头补回来，锚点照例移到框后。
BROKEN_HEAD = re.compile(
    r'(<p class="scripture-ref">[^\n]*</p>)\n\n'
    r'<p style="[^"]*" markdown="1">([^\n]*?)</p>\n'
    r'(<div class="commentary-anchor"[^>]*>)</p></td>')
BOX_TAIL = '</tbody>\n</table>\n\n</div>'


def fix_broken_head(text: str):
    """补回被毁掉的框头，并把锚点放到这个框自己的 </div> 后面。

    正则按行锚定（不用 DOTALL）：`.*?` 跨行会从上一个框的 scripture-ref 开始匹，
    结果把开标签插到上一个框头上、锚点插到上一个框尾——试过一次，两处都错位。
    """
    n = 0
    while True:
        m = BROKEN_HEAD.search(text)
        if not m:
            break
        head = ('<div class="scripture-box scripture-box--bilingual" markdown="1">\n'
                + m.group(1) + '\n\n<table class="scripture-bilingual">\n<tbody>\n'
                + '<tr><td class="scripture-en">' + m.group(2) + '</td>')
        anchor = m.group(3) + '</div>'
        text = text[:m.start()] + head + text[m.end():]
        tail = text.find(BOX_TAIL, m.start())      # 本框自己的收尾
        if tail >= 0:
            cut = tail + len(BOX_TAIL)
            text = text[:cut] + '\n' + anchor + text[cut:]
        n += 1
    return text, n


def main() -> int:
    apply = '--apply' in sys.argv
    total = 0
    for p in sorted(ROOT.glob('calvin/*/*.md')):
        text = p.read_text(encoding='utf-8')
        if 'commentary-anchor' not in text:
            continue
        text, broken = fix_broken_head(text)
        if broken:
            total += broken
            print(f'  {p}: 补回 {broken} 个被锚点注入毁掉的框头')
            if apply:
                p.write_text(text, encoding='utf-8')
        text, dropped = drop_surplus_div(text)
        if dropped:
            print(f'  {p}: 去掉 {dropped} 个多余的 </div>（坏锚点留下的）')
            if apply:
                p.write_text(text, encoding='utf-8')
        out, last, n = [], 0, 0
        for m in BOX.finditer(text):
            new_box, found = fix_box(m.group(0))
            if not found:
                continue
            out.append(text[last:m.start()] + new_box)
            last = m.end()
            n += len(found)
        if not n:
            continue
        total += n
        print(f'  {p}: 挪出 {n} 个锚点')
        if apply:
            p.write_text(''.join(out) + text[last:], encoding='utf-8')
    print(f'[{"applied" if apply else "dry-run"}] {total} 个锚点')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
