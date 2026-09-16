#!/usr/bin/env python3
"""删掉没有对应开标签的 `</p>`（多出现在文末脚注定义里）。

耶利米书上下卷、耶利米哀歌等卷的脚注定义中间夹着一个孤立的 `</p>`：

    [^fC57]: *加塔克*与*劳斯*即持此说；他们引证 列王纪下 24:12 与</p>耶利米书 22:26。

浏览器会就地把段落关掉，后半句跑到段外；有时后面还跟着一个 `<p …>` 把定义的
下半截另起一段，脚注在页面上就断成两截。

两种处理，都保持开闭标签数平衡：
  · 孤立 `</p>` 后面紧跟 `<p …>` → 两个一起去掉，前后文接成一句（定义本来就是
    一句话被拦腰截断的）；
  · 否则 → 只删这个 `</p>`。

判定方式是从头扫一遍计数，只在「深度要变成负数」的那个 `</p>` 上动手，不碰任何
配对正常的标签。

用法：
    python3 scripts/fix_stray_close_p.py [--apply]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG = re.compile(r'<p\b[^>]*>|</p>')
JOIN = re.compile(r'</p>\s*\n\n<p\b[^>]*>')


def fix_text(text: str):
    hits = []
    while True:
        depth = 0
        stray = None
        for m in TAG.finditer(text):
            if m.group(0).startswith('<p'):
                depth += 1
            else:
                depth -= 1
                if depth < 0:
                    stray = m
                    break
        if stray is None:
            return text, hits
        before = re.sub(r'(?:</[a-zA-Z][^>]*>)+$', '', text[:stray.start()].rstrip())
        # 只有「上半句没写完」才接回去；已经用句号收尾的，说明下一个 <p> 本来
        # 就是另起一段（耶利米书 3 那处上半是经文引块、下半是另一条按语）
        mid_sentence = bool(before) and before[-1] not in '.?!。！？」』”)'
        jm = JOIN.match(text, stray.start()) if mid_sentence else None
        if jm:
            hits.append(('接回上一句', text[max(0, stray.start() - 28):stray.start()]))
            text = text[:stray.start()] + ' ' + text[jm.end():]
        else:
            hits.append(('删掉孤立 </p>', text[max(0, stray.start() - 28):stray.start()]))
            text = text[:stray.start()] + text[stray.end():]


def main() -> int:
    apply = '--apply' in sys.argv
    total = 0
    for p in sorted(ROOT.glob('calvin/*/*.md')):
        text = p.read_text(encoding='utf-8')
        if text.count('</p>') == len(re.findall(r'<p\b', text)):
            continue
        new, hits = fix_text(text)
        if not hits:
            continue
        total += len(hits)
        for how, ctx in hits:
            print(f'  {p}: {how}（…{ctx[-24:]}）')
        if apply:
            p.write_text(new, encoding='utf-8')
    print(f'[{"applied" if apply else "dry-run"}] {total} 处')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
