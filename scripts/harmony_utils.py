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
    """True 表示块末尾是功能词（介词/冠词/连词），这类词绝对不能结句。

    扩展规则：若末词无句末标点（. ! ?）且倒数第二个词是功能词（如 and/or/of），
    则末词大概率只是名词短语的起首（如"the Old and **New**"），下一块多半
    是其延续（"Testaments"），同样视为不能结句。
    """
    t = re.sub(r'[\*_]+$', '', text.rstrip()).rstrip()
    if not t:
        return False
    words = re.split(r'\s+', t)
    last_word = words[-1].strip('.,;:!?"\'")(').lower()
    if last_word in _FUNCTION_WORDS:
        return True
    # 末词大写且无句末标点 + 倒数第二词是 function word → 名词短语中段断行
    last_raw = words[-1].rstrip(',;:')  # 容忍尾随次级标点
    ends_with_terminal_punct = last_raw.endswith(('.', '!', '?'))
    if not ends_with_terminal_punct and len(words) >= 2 and last_word:
        prev_word = words[-2].strip('.,;:!?"\'")(').lower()
        if prev_word in _FUNCTION_WORDS:
            return True
    return False


def _ends_mid_sentence(text):
    """True 表示块末尾是中句标点（逗号/分号/冒号/连字符等），后必有续接。
    剥掉尾部脚注引用 `[^N]`、粗/斜体标记后再判断。"""
    t = text.rstrip()
    # 剥脚注引用 [^N]
    t = re.sub(r'\[\^\d+\]\s*$', '', t).rstrip()
    # 剥粗/斜体收尾
    t = re.sub(r'[\*_]+$', '', t).rstrip()
    return bool(t) and t[-1] in ',;:-—'


def _starts_new_quote(text):
    # opening curly/straight quote = standalone scripture paragraph, never merge
    return text[:1] in ('"', '\u201c', '\u2018')


_P_CENTER_RE = re.compile(r'^<p[^>]*>(.*?)</p>\s*$', re.DOTALL)

def _p_continuation_content(block):
    """若 block 是 <p> centered 且像「上段引文的续接」，返回内容文本；否则 None。

    续接特征（任一即可）：
    1. 内容以小写字母开头（被 PDF 跨行截断的句子续接）；
    2. 内容含 `)` 闭合括号但不以 `(` 开头——典型如
       `Galatians 3:10;)` 是上段 `(Deuteronomy 27:26;` 的尾巴。
    """
    m = _P_CENTER_RE.match(block.strip())
    if not m:
        return None
    content = m.group(1).strip()
    t = re.sub(r'^\*+', '', content)
    if not t:
        return None
    if t[0].islower():
        return content
    # 引文尾巴：含右括号但不以左括号起首（Calvin 标准居中引文皆以 `(` 起首）
    if ')' in t and not t.startswith('('):
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
                # 引文尾巴（含 `)` 不以 `(` 起首）：只要 prev 不是真正完成
                # 的句子（不以 . ! ? 收尾），就合并——典型 prev 以 `;`/`,`
                # 等中段标点结尾，p_cont 是上段引文的闭合
                is_citation_tail = ')' in p_cont and not p_cont.lstrip('*').startswith('(')
                prev_complete = last_ch in '.!?'
                if last_ch.isalpha() or last_ch == '-':
                    if last_ch == '-':
                        # Hyphenated word break: remove hyphen, join without space
                        block = block_end[:-1] + p_cont.lstrip()
                    else:
                        block = block_end + ' ' + p_cont.lstrip()
                    i += 1
                    continue
                if is_citation_tail and not prev_complete:
                    block = block_end + ' ' + p_cont.lstrip()
                    i += 1
                    continue
                # else: previous block ends with punctuation → <p> is new centered element
            if next_block.startswith('<p'):
                break
            # 续行首字母小写、当前块末尾是功能词、或当前块末尾是中句标点
            # （`,`/`;`/`:`/`-` 等，常见跨页断行）。下一块以开引号开头则是独立
            # 圣经引文段，不合并。
            if (_continuation_start(next_block)
                    or _ends_with_function_word(block)
                    or _ends_mid_sentence(block)) \
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
    2. 经典格式：**N.** 起首且无 *italic* 斜体标记 (Calvin commentary 必含斜体引语)

    判定斜体存在性时必须先剥离 **bold** 段，否则 PDF 偶有的 `**,**`/`**.**`
    等 bold 标点会被误判为斜体（其中的 `*` 是 bold 标记不是 italic）。
    例：Matt 6:5–8 raw 中 `**7.**But praying**,** use not...` 含 bold 逗号，
    早期版本因 `'*' in no_verse_nums` 直接返回 False，整段被当成注释。
    """
    stripped = block.strip()
    if _scripture_col_info(block) is not None:
        return True
    if not re.match(r'^\*\*\d+\.\*\*', stripped):
        return False
    no_verse_nums = re.sub(r'\*\*\d+\.\*\*', '', block)
    no_bold = re.sub(r'\*\*[^*]*\*\*', '', no_verse_nums)
    return '*' not in no_bold


def _fnref_to_html(text):
    """Convert Kramdown [^N] refs to <sup><a> HTML for use inside raw HTML.

    Kramdown GFM 不处理 HTML 块内的 Markdown（`markdown="1"` 属性也不
    生效），所以 scripture-box 内必须手工转 `[^N]` 为 `<sup>`。配套
    需在发布最后做 strip_footnote_defs() 收集所有 `[^N]: text` 定义，
    转成 `<li id="fn:N">` 并替换 Kramdown 自动生成的 footnotes 区域，
    否则定义会因为没有 Markdown ref 而被 Kramdown 当作孤儿丢弃。"""
    return re.sub(
        r'\[\^(\d+)\]',
        r'<sup id="fnref:\1"><a href="#fn:\1" class="footnote">\1</a></sup>',
        text,
    )


def _md_bold_to_html(text):
    """Convert **text** markers to <strong>text</strong> for use inside raw HTML.
    同时把 [^N] 转为 <sup>（详见 _fnref_to_html docstring）。"""
    text = _SCRIPTURE_COL_RE.sub('', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return _fnref_to_html(text)


_FN_REF_RE = re.compile(r'\[\^(\d+)\]')


def _collect_fn_refs(paras):
    """从多段经文里收集所有 [^N] 编号（在转 HTML 之前）。"""
    refs = []
    for p in paras:
        if isinstance(p, list):
            for sub in p:
                refs.extend(_FN_REF_RE.findall(sub))
        else:
            refs.extend(_FN_REF_RE.findall(p))
    # 保序去重
    seen, out = set(), []
    for n in refs:
        if n not in seen:
            seen.add(n); out.append(n)
    return out


def _fn_stub(refs):
    """生成隐藏的 Markdown 引用占位，使 Kramdown 仍能为这些 [^N] 生成
    <li id="fn:N"> 定义条目，让 scripture-box 内的 <sup> 跳转有效。"""
    if not refs:
        return ''
    refs_md = ' '.join(f'[^{n}]' for n in refs)
    return f'\n\n{refs_md}\n{{:.scripture-fnref-stub}}\n'


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
    fn_stub = _fn_stub(_collect_fn_refs(paras))

    col_infos = [_scripture_col_info(p) for p in paras]
    if any(ci is not None for ci in col_infos):
        # 多栏渲染：按 col 聚合
        n_cols = next(ci[1] for ci in col_infos if ci is not None)
        col_paras = [[] for _ in range(n_cols)]
        for p, ci in zip(paras, col_infos):
            if ci is None:
                continue   # 罕见：单栏块混在多栏组里，先丢弃
            col_paras[ci[0]].append(_md_bold_to_html(p))

        # 列标题来自 header，但要按**卷名分组**，把无卷名前缀的引用并入
        # 上一个卷（如「MARK 9:49-50; 4:21」→ 一个 Mark 列；
        # 「LUKE 14:34-35; 8:16; 11:33」→ 一个 Luke 列）。
        parts = [s.strip() for s in header.split(';')]
        col_titles_raw = []
        for p in parts:
            if re.match(r'^[A-Z][A-Za-z]*\b', p):
                col_titles_raw.append(p)
            elif col_titles_raw:
                col_titles_raw[-1] += '; ' + p
            else:
                col_titles_raw.append(p)
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
            + fn_stub
        )

    def _wrap_p(p):
        s = p.strip()
        # 已经是 <p ...>...</p> 块（如居中 <p style=...>）就不再包一层
        if s.startswith('<p') and s.endswith('</p>'):
            return _md_bold_to_html(s)
        return f'<p>{_md_bold_to_html(p)}</p>'
    body_html = '\n'.join(_wrap_p(p) for p in paras)
    return (
        '<div class="scripture-box">\n'
        f'<p class="scripture-ref">{display}</p>\n'
        f'{body_html}\n'
        '</div>'
        + fn_stub
    )


def process_section_blocks(header, body):
    """将一个节（header + body）的 body 拆块并运行完整处理管道。
    返回处理后的 block 列表（不含 header block）。

    第一段若为纯经文（无斜体），渲染为 PDF 原文的有边框方框；
    后续段落为注释，走完整处理管道。"""
    # PyMuPDF 同 style 的相邻 span 偶尔会被切成两段，导致 block_to_markdown
    # 产出 `**Matthew 5:42****.**` 这种 abut-bold 模式（kramdown 渲染为两个
    # 相邻 <strong>，verse-nav 正则匹配的是 "Book Ch:N." 整体，分成两个 strong
    # 后第一个只剩 "Matthew 5:42" 不带 `.` 故无法识别）。
    # 解决：在 body 进入 pipeline 前合并所有同 style 的 abutting 标记。
    # `****` 为四个连续星号——只可能由 `**A**` 紧贴 `**B**` 产生（合法 markdown
    # 中三星号 `***` 用于 bold-italic，但 raw 中 `***` 之后必有内容字符，
    # 不会形成纯 4 星序列；实测无误判）
    body = body.replace('****', '')
    # 引文 italic 只包到引号字符的情况——见 calvin_extract._fix_split_italic_quotes
    body = re.sub(
        r'\*(["“”\'‘’])\*([^*]+?)\*([,.;:!?]*["“”\'‘’])\*',
        r'*\1\2\3*', body,
    )
    body = re.sub(
        r'\*(["“”\'‘’])\*([^*]+?["“”])',
        r'*\1\2*', body,
    )
    raw_blocks = re.split(r'\n{2,}', body)
    blocks = [b.strip() for b in raw_blocks if b.strip()]

    if not blocks:
        return []

    result = []

    # 收集章首经文 block 群作为一个 scripture-box。允许的 block：
    # - **N.** 起首的纯经文段（_is_scripture_block 包含此情况）
    # - <!--SCRIPTURE col=N of=M--> 多列标记段（_is_scripture_block 包含此情况）
    # - <p style="text-align:center"> 居中段（章首经文里的居中行如 Mark 1:13 短句）
    # 一旦遇到第一个非上述类型的 block 就停——注释段不可混入经文盒子，
    # 即便首句没有斜体或 **Book Ch:N.** 标记（这是 Luke 2:1-7 等节常见情况）。
    comm_start = 0
    has_scripture = False
    while comm_start < len(blocks):
        b = blocks[comm_start]
        if _is_scripture_block(b):
            has_scripture = True
            comm_start += 1
        elif b.strip().startswith('<p style='):
            comm_start += 1   # 不算 scripture，但允许跟随
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
