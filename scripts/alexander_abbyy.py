#!/usr/bin/env python3
"""解析 Internet Archive 的 ABBYY FineReader XML（J. A. Alexander《诗篇注释》）。

为什么不直接用 _djvu.txt：那份纯文本把**斜体丢干净了**。Alexander 全书靠
斜体区分「他自己对希伯来文的译文」与「解说」——丢了斜体，读者无法分辨哪句
是经文哪句是注释，等于毁掉这本书的体例。ABBYY XML 里每个 <formatting> 带
italic 属性，是唯一能还原这一层的来源。

XML 结构（自外向内）：
    page → block[blockType=Text] → par → line → formatting → charParams

par 的属性就是段落信号，不用自己按几何猜（principles §0.3 的例外：这里
ABBYY 已经把版面判读做完了，直接用它的结论比重新推断可靠）：
    startIndent  首行缩进 → **新段落**
    （无 startIndent 且是块内第一段）→ 上一页 / 上一段的**续行**
    leftIndent 很大 + 单行 → 居中的标题或页眉
"""
import re
import xml.etree.ElementTree as ET

NS = '{http://www.abbyy.com/FineReader_xml/FineReader6-schema-v1.xml}'

# 斜体哨兵：用私用区字符，正文绝不会出现，避免与真正的 * 打架
IT_ON, IT_OFF = '', ''
# 行末断词的接缝标记。这里**不能直接把连字符删掉**：真的复合词
# （well-watered、burnt-offering、twenty-second）也会正好断在连字符上，
# 删了就再也分不出「断词」与「复合词」。留个标记，等 cleanup 阶段拿全书
# 的复合词表来定夺（另一个会话在诗篇里查出 8 处被拼成 wellwatered）。
HYPH = '\ue003'
# 行与行之间的接缝。ABBYY 有时把行末的连字符整个吞掉（`ac-` + `quirements`
# 读成 `ac` + `quirements`），拼成段落之后与句中的正常空格再也分不开。
# 留个哨兵，让 cleanup 阶段知道「这个空格原本是行末」——断词只可能发生在
# 这里，判据限定在接缝上就不会误伤句中真正的两个词（`in deed`、`for ever`）。
BREAK = '\ue004'


def _line_text(line):
    """一行 → 文本，斜体段用哨兵包起来"""
    out = []
    for fmt in line.iter(NS + 'formatting'):
        txt = ''.join(cp.text or '' for cp in fmt.iter(NS + 'charParams'))
        if not txt:
            continue
        if fmt.get('italic') == 'true':
            out.append(IT_ON + txt + IT_OFF)
        else:
            out.append(txt)
    return ''.join(out)


def _join_lines(lines, drop_line=None):
    """行拼段：行尾连字符按「下一行首字母小写」判断是否为断词。

    「Anglo-Saxon」这类真连字符后面接大写，保留；「compres-sion」接小写，
    合并。19 世纪排印里断词处一律小写续接，这条足够。

    接小写的那一支**不直接删连字符**，改插 HYPH 标记：well-watered 这类
    本来就带连字符的复合词也会断在连字符上，删与不删要看全书别处怎么写，
    那是 cleanup 阶段的事（alexander_common.resolve_hyphens）。
    """
    lines = list(lines)
    multiline = len(lines) > 1
    buf = ''
    for raw in lines:
        t = raw.strip()
        if not t:
            continue
        # 页眉有时不是独立的 par，而是**夹在一段里的一行**（页顶那一行被
        # ABBYY 归进了跨页的同一段）。段级过滤看不见它，只能在这里按行剔。
        # 剔在拼行之前，跨页断词才接得上（`correspond-` + 页眉行 + `ing to`）。
        #
        # ⚠️ 只对**多行段**生效。章题本身就是个单行段（`CHAPTER I.`），
        # 同一套判据会把它一并剔掉，39 章一个都找不到（踩过）。
        if multiline and drop_line is not None \
                and drop_line(t.replace(IT_ON, '').replace(IT_OFF, '')):
            continue
        if not buf:
            buf = t
            continue
        # 哨兵可能夹在连字符和行尾之间，判断时先剥掉
        tail = buf.rstrip(IT_OFF)
        nxt = t.lstrip(IT_ON)
        if tail.endswith('-') and nxt[:1].islower():
            buf = tail[:-1] + HYPH + (IT_OFF if buf.endswith(IT_OFF) else '') + t
        else:
            buf = buf + BREAK + t
    return buf


def parse_pages(xml_path, drop_line=None):
    """流式解析整卷 → [{'index': 1-based, 'pars': [par, ...]}, ...]

    par = {'text': str, 'nlines': int, 'attrs': dict, 'block_top': int}
    """
    pages = []
    ctx = ET.iterparse(xml_path, events=('end',))
    idx = 0
    for _, el in ctx:
        if el.tag != NS + 'page':
            continue
        idx += 1
        pars = []
        for blk in el.iter(NS + 'block'):
            if blk.get('blockType') != 'Text':
                continue
            btop = int(blk.get('t') or 0)
            for par in blk.iter(NS + 'par'):
                lines = list(par.iter(NS + 'line'))
                if not lines:
                    continue
                pars.append({
                    'text': _join_lines((_line_text(l) for l in lines), drop_line),
                    'nlines': len(lines),
                    'attrs': dict(par.attrib),
                    'block_top': btop,
                })
        pages.append({'index': idx, 'pars': pars})
        el.clear()
    return pages


# ── 页眉 / 页脚 ────────────────────────────────────────────────
# verso: "2 PSALM I."  recto: "PSALM I. 3"  变体含 OCR 噪声（I J / 1 / IJ）
_RUNHEAD = re.compile(
    r'^\s*(?:\d{1,3}\s+)?PSALMS?\s*[IVXLCDMlJ0-9]{0,12}\s*[.,:;]?\s*(?:\d{1,3})?\s*$',
    re.I)
# 卷次署名行 "VOL, I 1" / "VOL. II. 5*" —— 装订用的书帖标记，不是正文
_SIGNATURE = re.compile(r'^\s*VOL[.,]?\s*[IVX]+\s*[.,]?\s*\d*\**\s*$', re.I)


def is_running_head(par, page_pars):
    """页眉/页脚 = 单行 + 命中模式 + 位于页首或页尾"""
    if par['nlines'] != 1:
        return False
    t = par['text'].strip()
    if _SIGNATURE.match(t):
        return True
    if not _RUNHEAD.match(t):
        return False
    # 章标题（"PSALM I." 单独居中、无页码）不能误删：页眉一定带页码，
    # 章标题不带。这是两者唯一稳定的区别。
    return bool(re.search(r'\d', t))
