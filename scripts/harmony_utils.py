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
        if block.startswith('##') or block.startswith('<table') or block.startswith('<p'):
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


# 介词/冠词/连词等不可能结句的功能词
_FUNCTION_WORDS = {
    'a', 'an', 'the', 'of', 'to', 'in', 'for', 'and', 'or', 'nor',
    'but', 'with', 'by', 'at', 'from', 'into', 'through', 'upon', 'on',
    'that', 'which', 'who', 'whose', 'whom', 'as', 'its', 'his', 'her',
    'their', 'our', 'this', 'these', 'those', 'not',
}


def _ends_with_function_word(text):
    """True 表示块末尾是功能词（介词/冠词/连词），这类词绝对不能结句。"""
    t = re.sub(r'[\*_]+$', '', text.rstrip()).rstrip()
    last_word = re.split(r'\s+', t)[-1].strip('.,;:!?"\'")(').lower() if t else ''
    return last_word in _FUNCTION_WORDS


def _starts_new_quote(text):
    # opening curly/straight quote = standalone scripture paragraph, never merge
    return text[:1] in ('"', '\u201c', '\u2018')


_P_CENTER_RE = re.compile(r'^<p[^>]*>(.*?)</p>\s*$', re.DOTALL)

def _p_continuation_content(block):
    """若 block 是 <p> centered 且内容以小写字母开头（续行碎片），返回内容文本；否则返回 None。"""
    m = _P_CENTER_RE.match(block.strip())
    if not m:
        return None
    content = m.group(1).strip()
    t = re.sub(r'^\*+', '', content)
    if t and t[0].islower():
        return content
    return None


def merge_split_paragraphs(blocks):
    """合并跨 PDF block 断开的段落。
    两种合并信号：续行首字母小写，或当前块末尾是功能词（绝对不能结句）。"""
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
            if block.startswith('<p'):
                break
            # Footnote definitions must stay separate — they often end with a
            # function word (the original prose was wrapped) which would
            # otherwise trigger merging into the following body paragraph.
            if block.startswith('[^') or next_block.startswith('[^'):
                break
            # <p> centered 块若内容以小写开头，且前一块以字母或连字符结尾（行中断裂），
            # 才是续行碎片——剥掉标签合并。若前一块以标点结尾（如逗号），
            # 则 <p> 是新的居中元素（如 "zealous of good works,"），不合并。
            p_cont = _p_continuation_content(next_block)
            if p_cont is not None:
                block_end = block.rstrip()
                last_ch = block_end[-1] if block_end else ''
                if last_ch.isalpha() or last_ch == '-':
                    if last_ch == '-':
                        # Hyphenated word break: remove hyphen, join without space
                        block = block_end[:-1] + p_cont.lstrip()
                    else:
                        block = block_end + ' ' + p_cont.lstrip()
                    i += 1
                    continue
                # else: previous block ends with punctuation → <p> is new centered element
            if next_block.startswith('<p'):
                break
            # 续行首字母小写，或当前块末尾是功能词（不可能是句末）
            # 但如果下一块以开引号开头，是独立圣经引文段，不合并
            if (_continuation_start(next_block) or _ends_with_function_word(block)) \
                    and not _starts_new_quote(next_block):
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


# 提取阶段对多列章首经文用 <!--SCRIPTURE col=N of=M--> 标记每段所属列
_SCRIPTURE_COL_RE = re.compile(r'^<!--SCRIPTURE col=(\d+) of=(\d+)-->\s*\n?', re.DOTALL)


def _scripture_col_info(block):
    """若 block 是多列经文标记，返回 (col_idx, n_cols)；否则 None。"""
    m = _SCRIPTURE_COL_RE.match(block.strip())
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _is_scripture_block(block):
    """True if block is pure scripture text.

    1. 多列标记块（<!--SCRIPTURE col=N of=M-->）
    2. 经典格式：**N.** 起首且无任何斜体标记 (Calvin commentary 必含斜体引语)
    """
    stripped = block.strip()
    if _scripture_col_info(block) is not None:
        return True
    if not re.match(r'^\*\*\d+\.\*\*', stripped):
        return False
    no_verse_nums = re.sub(r'\*\*\d+\.\*\*', '', block)
    return '*' not in no_verse_nums


def _md_bold_to_html(text):
    """Convert **text** markers to <strong>text</strong> for use inside raw HTML."""
    text = _SCRIPTURE_COL_RE.sub('', text)
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)


def _scripture_box(header, text):
    """Render scripture block(s) as a bordered box matching the PDF layout.

    `text` 可以是：
    - 字符串：单段经文，渲染为单 <p>
    - 字符串列表：
      * 都没有列标记 → 多段单栏经文，依次渲染为独立 <p>
      * 含列标记 <!--SCRIPTURE col=N of=M--> → 共观福音平行多栏，渲染为
        <table class="scripture-table"> N 栏并列，列头取自 header 按 `;` 拆分

    Header e.g. 'LUKE 1:1-4; MATTHEW 3:1' → 'Luke 1:1-4; Matthew 3:1'。
    """
    display = ' '.join(w.capitalize() if w.isalpha() else w for w in header.split())
    paras = text if isinstance(text, list) else [text]

    col_infos = [_scripture_col_info(p) for p in paras]
    if any(ci is not None for ci in col_infos):
        # 多栏渲染：按 col 聚合
        n_cols = next(ci[1] for ci in col_infos if ci is not None)
        col_paras = [[] for _ in range(n_cols)]
        for p, ci in zip(paras, col_infos):
            if ci is None:
                continue   # 罕见：单栏块混在多栏组里，先丢弃
            col_paras[ci[0]].append(_md_bold_to_html(p))

        # 列标题来自 header 按 `;` 拆分
        col_titles_raw = [s.strip() for s in header.split(';')]
        col_titles = [
            ' '.join(w.capitalize() if w.isalpha() else w for w in t.split())
            for t in col_titles_raw
        ]
        # 若列数对不上，用占位
        while len(col_titles) < n_cols:
            col_titles.append(f'Column {len(col_titles)+1}')

        thead = ''.join(f'<th>{ct}</th>' for ct in col_titles[:n_cols])
        tds = []
        for col_idx in range(n_cols):
            # 跨页的同栏续接段在 PDF 中原本是一段连续经文，合并为单个 <p>
            # 避免渲染出段间空隙。续接处末尾若是字母/连字符则按断词处理。
            parts = col_paras[col_idx]
            joined = parts[0] if parts else ''
            for nxt in parts[1:]:
                tail = joined.rstrip()
                last = tail[-1:] if tail else ''
                if last == '-':           # 断字续接，去连字符
                    joined = tail[:-1] + nxt.lstrip()
                else:
                    joined = tail + ' ' + nxt.lstrip()
            tds.append(f'<td><p>{joined}</p></td>')
        return (
            '<div class="scripture-box scripture-box--multi">\n'
            f'<p class="scripture-ref">{display}</p>\n'
            '<table class="scripture-table">\n'
            f'<thead><tr>{thead}</tr></thead>\n'
            f'<tbody><tr>{"".join(tds)}</tr></tbody>\n'
            '</table>\n'
            '</div>'
        )

    body_html = '\n'.join(f'<p>{_md_bold_to_html(p)}</p>' for p in paras)
    return (
        '<div class="scripture-box">\n'
        f'<p class="scripture-ref">{display}</p>\n'
        f'{body_html}\n'
        '</div>'
    )


def process_section_blocks(header, body):
    """将一个节（header + body）的 body 拆块并运行完整处理管道。
    返回处理后的 block 列表（不含 header block）。

    第一段若为纯经文（无斜体），渲染为 PDF 原文的有边框方框；
    后续段落为注释，走完整处理管道。"""
    raw_blocks = re.split(r'\n{2,}', body)
    blocks = [b.strip() for b in raw_blocks if b.strip()]

    if not blocks:
        return []

    result = []

    # 收集章首经文 block 群作为一个 scripture-box。包含：
    # - **N.** 起首的纯经文段
    # - <!--SCRIPTURE col=N of=M--> 多列标记段
    # - <p style="text-align:center"> 居中段（PDF 在经文内的居中行如 Mark 1:13 短句）
    # - 不以 **N.** 起首但无斜体的续接段（跨页/跨列时常见）
    # 停在第一个带「斜体引语」或 **Book N:M.** 注释起首标记的 block。
    def _is_commentary(block):
        s = block.strip()
        if re.match(r'^\*\*[A-Z][a-z]+ \d+:\d+', s):
            return True   # **Matthew 4:5.** 等 Calvin 注释逐节标记
        # 去掉 **bold** 后若仍有 *italic*，说明是注释里的经文引语
        no_bold = re.sub(r'\*\*[^*]+\*\*', '', block)
        if re.search(r'\*[^*\n]+\*', no_bold):
            return True
        return False

    comm_start = 0
    has_scripture = False
    while comm_start < len(blocks):
        b = blocks[comm_start]
        if _is_commentary(b):
            break
        if _is_scripture_block(b) or b.strip().startswith('<p style=') or has_scripture:
            has_scripture = has_scripture or _is_scripture_block(b)
            comm_start += 1
        else:
            break
    if has_scripture:
        result.append(_scripture_box(header, blocks[:comm_start]))
    else:
        comm_start = 0

    # Commentary blocks through full pipeline
    if blocks[comm_start:]:
        comm_all = [f'## {header}'] + blocks[comm_start:]
        comm_all = split_rich_by_verse(comm_all)
        comm_all = join_orphan_verse_numbers(comm_all)
        comm_all = merge_split_paragraphs(comm_all)
        comm_all = expand_verse_refs(comm_all)
        if comm_all and comm_all[0].startswith('## '):
            comm_all = comm_all[1:]
        result.extend(comm_all)

    return result
