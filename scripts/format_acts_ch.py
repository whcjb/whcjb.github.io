#!/usr/bin/env python3
"""
格式化 calvin/acts/N.md
将翻译文本转换为 HTML 标记格式，与 1thessalonians 章节风格一致。

用法：
    python3 scripts/format_acts_ch.py 1          # 格式化第1章
    python3 scripts/format_acts_ch.py 1 2 3      # 格式化多章
"""
import re, sys
from pathlib import Path

ACTS_DIR = Path('/Users/yanpeifa/Documents/whcjb.github.io/calvin/acts')
TOTAL_CHAPTERS = 28

# ── 正则 ─────────────────────────────────────────────────────────────
SCRIPTURE_HDR_RE = re.compile(r'^使徒行传\s*\d+[:：]\d+')
TITLE_RE         = re.compile(r'^(使徒行传注释|第[一二三四五六七八九十百\d]+章|使徒行传注释.*)$')
FOOTNOTE_SEP_RE  = re.compile(r'^-{2,}$')
FOOTNOTE_CONT_RE = re.compile(
    r'^(?:[¹²³⁴⁵⁶⁷⁸⁹⁰]+\s|<sup>\d+</sup>|\d{1,3}\s+[「"（<])'
)
# 多节号经文（段落中含2个或以上"数字+中文"节号）
MULTI_VERSE_RE   = re.compile(r'(?:^|\s)\d{1,2}\s+[\u4e00-\u9fff]')

def strip_bold(s: str) -> str:
    return re.sub(r'^\*+|\*+$', '', s).strip()

def is_scripture_header(p: str) -> bool:
    return bool(SCRIPTURE_HDR_RE.match(strip_bold(p)))

def is_verse_block(p: str) -> bool:
    """段落包含2个以上节号，且不是加粗段落 → 判定为经文块"""
    if p.startswith('*'):
        return False
    return len(MULTI_VERSE_RE.findall(p)) >= 2

def is_footnote_content(p: str) -> bool:
    return bool(FOOTNOTE_CONT_RE.match(p.strip()))


def format_chapter(ch_num: int):
    src_file = ACTS_DIR / f'{ch_num}.md'
    if not src_file.exists():
        print(f'[跳过] {src_file} 不存在')
        return

    src = src_file.read_text(encoding='utf-8')

    # 1. 修正 front matter
    src = re.sub(r'(total_chapters:\s*)\d+', rf'\g<1>{TOTAL_CHAPTERS}', src)

    # 2. 分离 front matter
    fm_end = src.index('---\n', 3) + 4
    fm = src[:fm_end]
    body = src[fm_end:]

    # 3. 预处理：让 --- 脚注分隔线始终独占一段
    body = re.sub(r'^(-{2,})\n(?=[^\n])', r'\1\n\n', body, flags=re.MULTILINE)

    # 4. 分段
    paras = [p.strip() for p in re.split(r'\n{2,}', body.strip()) if p.strip()]

    # 5. 逐段转换
    out = []
    i = 0

    # 跳过冗余标题段
    while i < len(paras) and TITLE_RE.match(paras[i]):
        i += 1

    while i < len(paras):
        p = paras[i]; i += 1

        # ── (A) 脚注分隔线 ────────────────────────────────────────
        if FOOTNOTE_SEP_RE.match(p):
            fn_lines = []
            while i < len(paras):
                nxt = paras[i]
                if FOOTNOTE_SEP_RE.match(nxt):
                    i += 1; continue
                if is_footnote_content(nxt):
                    fn_lines.append(nxt); i += 1
                else:
                    break
            if fn_lines:
                out.append('<div class="calvin-footnotes">')
                for fl in fn_lines:
                    out.append(f'<p class="fn">{fl}</p>')
                out.append('</div>')
            continue

        # ── (B) 经文段落标题（使徒行传 X:Y-Z）────────────────────
        if is_scripture_header(p):
            header_text = strip_bold(p)
            out.append(f'\n**{header_text}**\n')
            # 消费下一段作为经文正文
            if i < len(paras):
                verse = re.sub(r'^\*+|\*+$', '', paras[i]).strip()
                out.append('<div class="calvin-verse">')
                out.append(f'<p>{verse}</p>')
                out.append('</div>')
                i += 1
            continue

        # ── (C) 独立加粗标题（整段 = **heading**）──────────────────
        m_only = re.match(r'^\*\*(.+)\*\*\s*$', p)
        if m_only:
            out.append(f'\n<h3 class="reading-subheading">{m_only.group(1).strip()}</h3>\n')
            continue

        # ── (D) 段落以加粗标题开头（**heading** 正文...）──────────
        # 限制标题长度 ≤ 60 字，避免误判整段加粗
        m_lead = re.match(r'^\*\*(.{1,60}?)\*\*\s*[。，、：？！；]?\s*(.+)', p, re.DOTALL)
        if m_lead:
            heading = m_lead.group(1).strip()
            rest    = m_lead.group(2).strip()
            # 标题后的标点归入 h3 尾部，rest 从非标点字开始
            out.append(f'\n<h3 class="reading-subheading">{heading}</h3>\n')
            if rest:
                out.append(f'<p>{rest}</p>')
            continue

        # ── (E) 多节号经文块（无标题的独立经文段，如 9-11 节）──────
        if is_verse_block(p):
            out.append('<div class="calvin-verse">')
            out.append(f'<p>{p}</p>')
            out.append('</div>')
            continue

        # ── (F) 普通段落 ────────────────────────────────────────────
        out.append(f'<p>{p}</p>')

    # 6. 组装
    result = fm + '\n' + '\n\n'.join(out) + '\n'
    src_file.write_text(result, encoding='utf-8')
    print(f'第{ch_num}章格式化完成  ({len(result)} 字符)')


if __name__ == '__main__':
    chapters = [int(x) for x in sys.argv[1:]] if sys.argv[1:] else [1]
    for ch in chapters:
        format_chapter(ch)
