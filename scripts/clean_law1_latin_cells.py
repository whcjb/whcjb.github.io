#!/usr/bin/env python3
"""清理摩西五经合参卷一(harmony-law-1 中英两版)双语经文表拉丁列里混入的
错乱英文注释垃圾(AGES 双列 PDF 合并 artifact)。

每个受污染的拉丁格形如: <td><p>N. [拉丁经文]. [错乱英文注释垃圾]...</p></td>
拉丁经文是单句(内部只有逗号/冒号, 无句点), 故截断点=第 2 个句点(第 1 个是节号
"N." 的点), 保留到该点, 删掉其后英文垃圾。

判定"含英文垃圾": 拉丁格文本里 ≥3 个英文虚词(the/that/which/they/from/...)。
DRY=True 只预览不写入。
"""
import re
import sys
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
CHAPTERS = [21, 22, 23, 24, 27]
STOP = re.compile(r'\b(the|that|which|they|from|Himself|people|would|because|He|His|for|but|since|only|here|and|to)\b')
# 拉丁格: <td><p>N. ... </p></td>  (右列, 以节号+拉丁开头)
# .*? 兜住英文垃圾里内嵌的 <19B972> 等 AGES 码 / 标签; 非贪婪到首个 </p></td>
CELL = re.compile(r'(<td><p>)(\d+\.\s+)(.*?)(</p></td>)')

DRY = '--apply' not in sys.argv


def clean_cell_text(latin_and_junk):
    """输入 'Latin sentence. english junk...' → 返回 'Latin sentence.' """
    # 找第 1 个句点(拉丁终止), 其后应是空格+英文
    m = re.search(r'\.\s', latin_and_junk)
    if not m:
        return None
    keep = latin_and_junk[:m.start() + 1]  # 含该句点
    rest = latin_and_junk[m.end():]
    # 保险: rest 确实是英文垃圾(含虚词)才截断
    if len(STOP.findall(rest)) < 2:
        return None
    return keep


def process(path):
    text = path.read_text(encoding='utf-8')
    changes = []

    def repl(m):
        pre, num, body, post = m.groups()
        if len(STOP.findall(body)) < 3:
            return m.group(0)  # 无英文垃圾
        cleaned = clean_cell_text(body)
        if not cleaned:
            return m.group(0)
        changes.append((num.strip(), body[:60], cleaned, body[len(cleaned):][:50]))
        return f'{pre}{num}{cleaned}{post}'

    new = CELL.sub(repl, text)
    if changes and not DRY:
        path.write_text(new, encoding='utf-8')
    return changes


def main():
    print('模式:', 'DRY-RUN(预览)' if DRY else 'APPLY(写入)')
    total = 0
    for ver in ('', '-en'):
        for ch in CHAPTERS:
            p = ROOT / 'calvin' / f'harmony-law-1{ver}' / f'{ch}.md'
            if not p.exists():
                continue
            ch_changes = process(p)
            for num, before, cleaned, removed in ch_changes:
                total += 1
                print(f'\n── {p.relative_to(ROOT)}  节{num} ──')
                print(f'  保留: {cleaned}')
                print(f'  删除: …{removed}…')
    print(f'\n共 {total} 处 (中英合计)')


if __name__ == '__main__':
    main()
