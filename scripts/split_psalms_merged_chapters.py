#!/usr/bin/env python3
"""把被并进前一篇的诗篇拆回自己的文件。

缺陷来源：分章时若某篇缺少可识别的章起始锚点，整篇会被并入前一篇的文件，
于是前一篇文件里出现两个 title-block-h1，而本篇文件只剩 front matter。
psalms-2 受影响两处：ch110 吞了 111，ch145 吞了 146（psalms-1 干净）。

英文 calvin/psalms-2-en/ 与中文 raw calvin_raw/psalms-2/zh_chapters/ 结构一一对应
（翻译保留了全部 HTML 锚点与脚注定义），所以两边做同一个切分，中文不需要重翻。

切分规则（对齐未受影响章节的既有约定，见 ch109/ch112）：
    文件 = front matter + 章标题 + 正文 + 本篇脚注定义 + 下一篇的 h2 终止锚点
- 切点取第二个 title-block-h1；
- 脚注定义按「引用出现在哪一篇」重新分配；
- 夹在两组定义之间的 `id="psalm-<N2>"` 锚点正是前一篇的终止锚点；
- 原文件末尾的终止锚点归后一篇。

用法:
    python3 scripts/split_psalms_merged_chapters.py --dry-run
    python3 scripts/split_psalms_merged_chapters.py
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (卷, 被吞的篇号) —— 被吞篇的内容现在躺在 N-1 的文件里
CASES = [('psalms-2', 110, 111), ('psalms-2', 145, 146)]

TITLE_RE = re.compile(r'<p class="title-block-h1".*?</p>', re.S)
DEF_RE = re.compile(r'^\[\^([A-Za-z0-9]+)\]:.*?(?=\n\[\^|\Z)', re.S | re.M)
ANCHOR_RE = re.compile(
    r'<h2 class="scripture-anchor" id="psalm-(\d+)" data-ref="PSALM \d+"[^>]*>.*?</h2>', re.S)
FM_RE = re.compile(r'\A---\n.*?\n---\n', re.S)


def split_file(path2_stub, text, n1, n2):
    """返回 (前一篇新正文, 后一篇新正文)，均不含 front matter。"""
    fm = FM_RE.match(text)
    if not fm:
        raise SystemExit(f'{path2_stub}: 找不到 front matter')
    body = text[fm.end():]

    titles = list(TITLE_RE.finditer(body))
    if len(titles) != 2:
        raise SystemExit(f'期望 2 个 title-block-h1，实得 {len(titles)}')
    cut = titles[1].start()

    # 终止锚点：夹在中间的 psalm-<n2> 归前篇，文件末尾那个归后篇
    mid_anchor, tail_anchor = None, None
    for m in ANCHOR_RE.finditer(body):
        if int(m.group(1)) == n2 and m.start() > cut:
            mid_anchor = m
        elif int(m.group(1)) > n2:
            tail_anchor = m

    part1, part2 = body[:cut], body[cut:]

    # 脚注定义按引用归属重新分配
    defs = {m.group(1): m.group(0).strip() for m in DEF_RE.finditer(body)}

    def drop_anchors(part, offset, drops):
        out, last = [], 0
        for m in ANCHOR_RE.finditer(part):
            if (m.start() + offset) in drops:
                out.append(part[last:m.start()])
                last = m.end()
        out.append(part[last:])
        return ''.join(out)

    drops = {m.start() for m in (mid_anchor, tail_anchor) if m}
    part1 = drop_anchors(DEF_RE.sub('', part1), 0, drops)
    part2 = drop_anchors(DEF_RE.sub('', part2), cut, drops)

    refs1 = set(re.findall(r'\[\^([A-Za-z0-9]+)\](?!:)', part1))
    refs2 = set(re.findall(r'\[\^([A-Za-z0-9]+)\](?!:)', part2))
    orphan = set(defs) - refs1 - refs2
    if orphan:
        print(f'  ⚠ 定义无对应引用，暂归前篇: {sorted(orphan)}')
        refs1 |= orphan
    both = refs1 & refs2
    if both:
        print(f'  ⚠ 两篇都引用，定义复制到两边: {sorted(both)}')

    def assemble(part, refs, terminator):
        part = part.rstrip() + '\n'
        block = '\n\n'.join(defs[c] for c in defs if c in refs)
        if block:
            part += '\n' + block + '\n'
        if terminator:
            part = part.rstrip('\n') + ' ' + terminator.group(0) + '\n'
        return part

    return assemble(part1, refs1, mid_anchor), assemble(part2, refs2, tail_anchor)


def verify(path, n):
    t = path.read_text()
    errs = []
    titles = [re.sub('<[^>]+>', '', m.group(0)).strip() for m in TITLE_RE.finditer(t)]
    if len(titles) != 1:
        errs.append(f'title-block-h1 有 {len(titles)} 个: {titles}')
    nums = re.findall(r'(?:PSALM|诗篇) (\d+)', ' '.join(titles))
    if nums and int(nums[0]) != n:
        errs.append(f'标题篇号 {nums[0]} ≠ {n}')
    defs = set(re.findall(r'^\[\^([A-Za-z0-9]+)\]:', t, re.M))
    refs = set(re.findall(r'\[\^([A-Za-z0-9]+)\](?!:)', t))
    if refs - defs:
        errs.append(f'脚注缺定义: {sorted(refs - defs)}')
    if defs - refs:
        errs.append(f'脚注定义无引用: {sorted(defs - refs)}')
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    for book, n1, n2 in CASES:
        for kind, d in (('EN', ROOT / f'calvin/{book}-en'),
                        ('ZH', ROOT / f'calvin_raw/{book}/zh_chapters')):
            f1, f2 = d / f'{n1}.md', d / f'{n2}.md'
            if not f1.exists():
                print(f'{kind} {f1} 不存在，跳过'); continue
            if not f2.exists():
                print(f'{kind} {f2} 不存在（尚未翻译），跳过'); continue
            t1, t2 = f1.read_text(), f2.read_text()
            if len(TITLE_RE.findall(t1)) != 2:
                print(f'{kind} ch{n1}: 已是单篇，跳过'); continue
            print(f'--- {kind} ch{n1} → ch{n1} + ch{n2} ---')
            body1, body2 = split_file(f1, t1, n1, n2)
            fm1 = FM_RE.match(t1).group(0)
            fm2 = FM_RE.match(t2).group(0)
            if a.dry_run:
                print(f'  ch{n1}: {len(fm1) + len(body1)} chars, '
                      f'ch{n2}: {len(fm2) + len(body2)} chars')
                continue
            for p in (f1, f2):
                p.chmod(0o644)
            f1.write_text(fm1 + body1)
            f2.write_text(fm2 + body2)
            for p, n in ((f1, n1), (f2, n2)):
                errs = verify(p, n)
                print(f'  {p.name}: {"OK" if not errs else "; ".join(errs)}')
                if kind == 'ZH':
                    p.chmod(0o444)


if __name__ == '__main__':
    main()
