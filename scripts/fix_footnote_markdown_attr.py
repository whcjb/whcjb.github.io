#!/usr/bin/env python3
"""给包着脚注引用的 <span>/<p> 补 markdown 属性，否则引用渲染成字面量。

kramdown 遇到块级/行内 HTML 默认按原样输出，里面的 `[^f21]` 不会变成上标脚注，
页面上直接露出 `[^f21]` 这几个字符。规矩是：`<p>` 要 `markdown="1"`，行内的
`<span>` 要 `markdown="span"`（见 reference_kramdown_markdown_attr）。

生成器与各发布脚本都已经在出口处补这个属性，本脚本扫历史产物的漏网之鱼。
只改开标签，正文一个字不动；闭合不完整的块不碰（拿不准边界，宁可不改）。

用法：
    python3 scripts/fix_footnote_markdown_attr.py [--apply] [目录…]
默认扫 calvin/ 下全部书卷。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPAN = re.compile(r'(<span\b[^>]*>)((?:(?!</span>).)*)</span>', re.S)
P = re.compile(r'(<p\b[^>]*>)((?:(?!</p>).)*)</p>', re.S)


def fix_text(text: str):
    n = 0

    def _one(m, attr, close):
        nonlocal n
        tag, inner = m.group(1), m.group(2)
        if 'markdown=' in tag or '[^' not in inner:
            return m.group(0)
        n += 1
        return f'{tag[:-1]} markdown="{attr}">{inner}{close}'

    text = SPAN.sub(lambda m: _one(m, 'span', '</span>'), text)
    text = P.sub(lambda m: _one(m, '1', '</p>'), text)
    return text, n


def main() -> int:
    apply = '--apply' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dirs = [Path(a) for a in args] or [ROOT / 'calvin']
    total, files = 0, 0
    for d in dirs:
        for p in sorted(d.glob('*/*.md') if d.name == 'calvin' else d.glob('*.md')):
            text = p.read_text(encoding='utf-8')
            new, n = fix_text(text)
            if not n:
                continue
            total += n
            files += 1
            print(f'  {p}: {n} 处')
            if apply:
                p.write_text(new, encoding='utf-8')
    print(f'[{"applied" if apply else "dry-run"}] {total} 处 / {files} 个文件')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
