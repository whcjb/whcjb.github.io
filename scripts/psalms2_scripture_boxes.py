#!/usr/bin/env python3
"""给 psalms-2-en 补上经文框，对齐卷一（也对齐 PDF 原貌）。

PDF 里每段经文都排在一个蓝色双线边框、米黄底的框里，框头是暗红的 AGES 代码
`<19C801>` 加粗体 `PSALM 128:1-3`。卷一的 `.scripture-box` 正是还原这个；
卷二出自更早一代的转换器，只留下一行 `## <19C801>PSALM 128:1-3` 加一段裸经文，
框、锚点、框头三样都没有。

本脚本把卷二的形态改写成卷一的结构：

    ## <19C801>PSALM 128:1-3          <h2 class="scripture-anchor" id="psalm-128-1-3" …>
    **1.** Blessed is …          →    <div class="scripture-box" markdown="1">
                                        <p class="scripture-ref">…</p>
                                        <strong>1.</strong> Blessed is …
                                      </div>

只动这两处结构，经文文字一字不改。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EN = ROOT / 'calvin/psalms-2-en'
ZH = ROOT / 'calvin_raw/psalms-2/zh_chapters'      # 中译 raw 同样要转（不重译）
# 诗篇 119 的 AGES 码是 7 位（<19B9105>），不是统一的 6 位
# AGES 码并非纯十六进制，诗篇 136 出现 <191K10> 这样带 K 的
# 英文写 PSALM，中译写 诗篇；卷名同步取出来放进框头
HEAD = re.compile(r'^## <([0-9A-Z]{6,8})>(PSALM|诗篇)\s*(\d+):([\d,\-—]+)\s*$', re.M)


def convert(text):
    out, n = [], 0
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        m = HEAD.match(lines[i])
        if not m:
            out.append(lines[i]); i += 1
            continue
        code, book, psalm, verses = m.groups()
        # 紧跟其后的第一段非空文本就是经文本体
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        body = []
        while j < len(lines) and lines[j].strip():
            body.append(lines[j]); j += 1
        if not body:
            out.append(lines[i]); i += 1
            continue
        vid = verses.replace('—', '-').replace(',', '-')
        out += [
            f'<h2 class="scripture-anchor" id="psalm-{psalm}-{vid}" '
            f'data-ref="PSALM {psalm}:{verses}" style="display:none">'
            f'{book} {psalm}:{verses}</h2>',
            '',
            '<div class="scripture-box" markdown="1">',
            f'<p class="scripture-ref"><span class="ages-code">&lt;{code}&gt;</span>'
            f'<span class="book-name">{"诗篇" if book == "诗篇" else "Psalm"}</span> '
            f'<span class="verse-range">{psalm}:{verses}</span></p>',
            '',
        ] + body + ['', '</div>']
        n += 1
        i = j
    return '\n'.join(out), n


if __name__ == '__main__':
    dry = '--dry-run' in sys.argv
    total = files = 0
    targets = list(EN.glob('*.md')) + (list(ZH.glob('*.md')) if ZH.exists() else [])
    for p in sorted(targets):
        t = p.read_text(encoding='utf-8')
        new, n = convert(t)
        if n:
            total += n; files += 1
            if not dry:
                p.chmod(0o644)
                p.write_text(new, encoding='utf-8')
                if 'zh_chapters' in str(p):
                    p.chmod(0o444)
    print(f'{"将转换" if dry else "已转换"} {total} 处经文框，涉及 {files} 个文件')
