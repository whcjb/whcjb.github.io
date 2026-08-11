#!/usr/bin/env python3
"""修复 calvin/psalms-1-en/ 的章节边界错位。

两处缺陷（均以 calvin_raw/psalms-1/calvin_psalms-1.md 为准）：

1. ch69/ch70 边界偏后一格：诗篇 70 的章标题 h2 + 加尔文题解 + 题词行被留在
   69.md 末尾，70.md 因此只剩经文框。章边界应当落在
   `<h2 ... id="psalm-N" data-ref="PSALM N">` 这一行，而不是第一个带节号的
   anchor。

2. ch71 没有终止：71.md 从诗篇 71 一路吞到卷末（诗篇 78），而 72–78 各自
   已有正确的独立文件。71.md 应在诗篇 72 的章标题行处截断。

只动这三个文件，不重跑整卷 publish（其余 76 章由更早的一代流程产出，
重跑会覆盖已校准内容）。front matter 的 date 一律保留原值。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EN = ROOT / 'calvin/psalms-1-en'

CHAP_HEAD_RE = r'<h2 class="scripture-anchor" id="psalm-{n}" data-ref="PSALM {n}"[^>]*>PSALM {n}</h2>'


def split_fm(text):
    """-> (front_matter_including_delimiters, body)"""
    m = re.match(r'(---\n.*?\n---\n)(.*)$', text, re.S)
    if not m:
        sys.exit('front matter 解析失败')
    return m.group(1), m.group(2)


def fix_69_70():
    p69, p70 = EN / '69.md', EN / '70.md'
    fm69, b69 = split_fm(p69.read_text(encoding='utf-8'))
    fm70, b70 = split_fm(p70.read_text(encoding='utf-8'))

    m = re.search(CHAP_HEAD_RE.format(n=70), b69)
    if not m:
        print('  69.md 已无诗篇 70 章标题，跳过')
        return False
    moved = b69[m.start():].rstrip() + '\n'
    new69 = b69[:m.start()].rstrip() + '\n'

    # 70.md 正文应以被移入的块开头，其后接原有内容（第一个带节号 anchor 起）
    if moved.split('\n')[0] in b70:
        print('  70.md 已含该块，跳过')
        return False
    new70 = '\n' + moved.strip() + '\n\n' + b70.strip() + '\n'

    p69.write_text(fm69 + new69, encoding='utf-8')
    p70.write_text(fm70 + new70, encoding='utf-8')
    print(f'  69.md: 移出 {len(moved)} 字节 → 70.md（{len(b70)} → {len(new70)}）')
    return True


def fix_71():
    p71 = EN / '71.md'
    fm71, b71 = split_fm(p71.read_text(encoding='utf-8'))
    m = re.search(CHAP_HEAD_RE.format(n=72), b71)
    if not m:
        print('  71.md 已无诗篇 72 章标题，跳过')
        return False

    cut = b71[m.start():]
    # 安全校验：被切掉的内容必须已经存在于 72–78 各章中
    published = ''.join((EN / f'{n}.md').read_text(encoding='utf-8') for n in range(72, 79))
    probes = [cut[i:i + 120] for i in range(200, len(cut) - 200, max(1, (len(cut) - 400) // 8))][:8]
    missing = [p for p in probes if p not in published]
    if missing:
        sys.exit(f'中止：被切掉的内容有 {len(missing)}/{len(probes)} 段在 72–78 中找不到，'
                 f'不能确认无损失。样例：{missing[0][:80]!r}')

    new71 = b71[:m.start()].rstrip() + '\n'
    # 补 next_section（原本缺失，因为它曾是"最后一章"）
    if 'next_section' not in fm71:
        fm71 = fm71.replace('---\n', '', 1)
        fm71 = '---\n' + fm71.rstrip('-\n') + '\nnext_section: 72\nnext_label: "Chapter 72"\n---\n'
    p71.write_text(fm71 + new71, encoding='utf-8')
    print(f'  71.md: {len(b71)} → {len(new71)} 字节（切掉 {len(cut)}，'
          f'{len(probes)} 段抽样全部在 72–78 中找到）')
    return True


if __name__ == '__main__':
    print('修复 ch69/ch70 边界：')
    fix_69_70()
    print('修复 ch71 截断：')
    fix_71()
