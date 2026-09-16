#!/usr/bin/env python3
"""把双语经文表单元格里的 markdown 记号转成 HTML，否则页面上原样显示。

kramdown 不解析 `<td>` 里的 markdown（`markdown="1"` 只作用到块级元素这一层），
所以单元格里残留的 `*vel*`、`**平安**`、`[^f15]` 会被原样吐到页面上——读者看到
的是一串星号和方括号。生成器 `structured_to_md.py` 塞 td 之前本来就会转
（`_md_to_html_inline`），这批是转换没覆盖到的漏网之鱼，全库 226 格。

转换与生成器一致：
    **X**   → <strong>X</strong>
    *X*     → <em>X</em>
    [^fN]   → <sup id="fnref:N"><a href="#fn:N" class="footnote">N</a></sup>

脚注还要让 kramdown 生成底部定义：框里那行隐藏的 `{:.scripture-fnref-stub}`
负责这件事，转换后把新出现的码补进去（已有就不动）。

用法：
    python3 scripts/fix_td_markdown.py [--apply]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOX = re.compile(r'<div class="scripture-box[^"]*"[^>]*>.*?\n</div>', re.S)
CELL = re.compile(r'(<td class="scripture-(?:en|la)">)(.*?)(</td>)', re.S)
FN = re.compile(r'\[\^([A-Za-z]{0,3}\d+[A-Za-z]?)\]')
STUB = re.compile(r'^(.*)\n\{:\.scripture-fnref-stub\}$', re.M)


def convert(cell: str):
    """返回 (新内容, 本格出现的脚注码)。"""
    codes = []

    def fn(m):
        codes.append(m.group(1))
        return (f'<sup id="fnref:{m.group(1)}">'
                f'<a href="#fn:{m.group(1)}" class="footnote">{m.group(1)}</a></sup>')

    out = FN.sub(fn, cell)
    out = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', out, flags=re.S)
    out = re.sub(r'(?<![*\w])\*([^*\n]+?)\*(?![*\w])', r'<em>\1</em>', out)
    return out, codes


def fix_box(box: str):
    codes_all = []
    changed = [False]

    def one(m):
        inner = m.group(2)
        if not re.search(r'\*|\[\^', inner):
            return m.group(0)
        new, codes = convert(inner)
        if new == inner:
            return m.group(0)
        changed[0] = True
        codes_all.extend(codes)
        return m.group(1) + new + m.group(3)

    box = CELL.sub(one, box)
    if not changed[0]:
        return box, 0
    if codes_all:
        stub = STUB.search(box)
        if stub:
            have = set(FN.findall(stub.group(1)))
            add = [c for c in dict.fromkeys(codes_all) if c not in have]
            if add:
                line = stub.group(1).rstrip() + ' ' + ' '.join(f'[^{c}]' for c in add)
                box = box[:stub.start(1)] + line + box[stub.end(1):]
        else:
            # 没有 stub 行就补一行（隐藏，只为让 kramdown 生成底部定义）
            tail = box.rindex('</div>')
            stub_line = ' '.join(f'[^{c}]' for c in dict.fromkeys(codes_all))
            box = box[:tail] + f'{stub_line}\n{{:.scripture-fnref-stub}}\n\n' + box[tail:]
    return box, 1


def main() -> int:
    apply = '--apply' in sys.argv
    total = 0
    for p in sorted(ROOT.glob('calvin/*/*.md')):
        text = p.read_text(encoding='utf-8')
        if 'scripture-la' not in text and 'scripture-en"' not in text:
            continue
        out, last, n = [], 0, 0
        for m in BOX.finditer(text):
            new_box, k = fix_box(m.group(0))
            if k:
                out.append(text[last:m.start()] + new_box)
                last = m.end()
                n += 1
        if not n:
            continue
        total += n
        print(f'  {p}: {n} 个框的单元格转了 markdown')
        if apply:
            p.write_text(''.join(out) + text[last:], encoding='utf-8')
    print(f'[{"applied" if apply else "dry-run"}] {total} 个框')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
