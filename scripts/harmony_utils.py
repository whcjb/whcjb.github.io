#!/usr/bin/env python3
"""
harmony_utils.py — 共观福音三卷共用的处理工具

供 matthew/publish.py、matthew1/publish.py、harmony3/publish.py 导入使用。
"""
import re

# 匹配行内节号标记（裸数字格式或完整书卷格式）
# 例：**16.**  或  **Luke 10:16.**
_VERSE_MARKER = re.compile(
    r'(?<=\S)\s+(\*\*(?:[A-Z][a-z]+ \d+:\d+|\d+)\.\*\*)'
)


def split_rich_by_verse(blocks):
    """把同一 block 内多个节号标记分割为独立段落。
    覆盖裸数字（**16.**）和完整格式（**Luke 10:16.**）两种。"""
    result = []
    for block in blocks:
        if block.startswith('##') or block.startswith('<table'):
            result.append(block)
            continue
        parts = _VERSE_MARKER.split(block)
        if len(parts) <= 1:
            result.append(block)
            continue
        result.append(parts[0].strip())
        i = 1
        while i < len(parts) - 1:
            result.append((parts[i] + ' ' + parts[i + 1].lstrip()).strip())
            i += 2
    return [b for b in result if b.strip()]


def join_orphan_verse_numbers(blocks):
    """把孤立的 **N.** 单行与下一段合并。"""
    result = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        if re.match(r'^\*\*\d+\.\*\*$', block.strip()):
            if i + 1 < len(blocks) and not blocks[i + 1].startswith('##'):
                result.append(block.strip() + ' ' + blocks[i + 1].lstrip())
                i += 2
                continue
        result.append(block)
        i += 1
    return result


def _continuation_start(text):
    """True 表示块的第一个实际字母是小写（跳过前导 * 标记）。"""
    t = re.sub(r'^\*+', '', text.lstrip())
    return bool(t) and t[0].islower()


def merge_split_paragraphs(blocks):
    """合并跨 PDF block 断开的段落（续行以小写字母开头）。"""
    merged = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        while i + 1 < len(blocks):
            next_block = blocks[i + 1]
            if block.startswith('##') or next_block.startswith('##'):
                break
            if block.startswith('<table') or next_block.startswith('<table'):
                break
            if _continuation_start(next_block):
                block = block.rstrip() + ' ' + next_block.lstrip()
                i += 1
            else:
                break
        merged.append(block)
        i += 1
    return merged


def expand_verse_refs(blocks):
    """把裸 **N.** 展开为 **Book Ch:N.**，从当前 ## 节头追踪书卷和章号。
    仅用于共观福音——单书注释无需调用。"""
    result = []
    current_book = None
    current_ch = None
    for block in blocks:
        if block.startswith('## '):
            m = re.match(r'^## (MATTHEW|MARK|LUKE|JOHN) (\d+):', block)
            if m:
                current_book = m.group(1).capitalize()
                current_ch = int(m.group(2))
            result.append(block)
        elif block.startswith('<table') or not current_book:
            result.append(block)
        else:
            new_block = re.sub(
                r'^\*\*(\d+)\.\*\*',
                lambda mo: f'**{current_book} {current_ch}:{mo.group(1)}.**',
                block
            )
            result.append(new_block)
    return result


def process_section_blocks(header, body):
    """将一个节（header + body）的 body 拆块并运行完整处理管道。
    返回处理后的 block 列表（不含 header block）。"""
    raw_blocks = re.split(r'\n{2,}', body)
    blocks = [b.strip() for b in raw_blocks if b.strip()]
    all_blocks = [f'## {header}'] + blocks
    all_blocks = split_rich_by_verse(all_blocks)
    all_blocks = join_orphan_verse_numbers(all_blocks)
    all_blocks = merge_split_paragraphs(all_blocks)
    all_blocks = expand_verse_refs(all_blocks)
    if all_blocks and all_blocks[0].startswith('## '):
        all_blocks = all_blocks[1:]
    return all_blocks
