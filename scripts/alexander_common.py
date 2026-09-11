#!/usr/bin/env python3
"""亚历山大各书抽取器的公共部分（诗篇、以赛亚书……）。

两本书的**版式规矩是同一套**——同一位作者、同一家排印传统：
章题居中单行、页眉带页码、段首缩进、他自己的译文用斜体嵌在解说里。
不同的只是几个正则（页眉长什么样、章题怎么写、节号怎么起头）和页码范围。
所以把「怎么合段、怎么修斜体、怎么推页码」抽到这里，各书的抽取器只声明
自己的那几个正则。

⚠️ 改这里会同时影响所有书。诗篇的产物已经核过（逐篇字符数比对，150 篇
合计差 2 字符），改完必须重跑并确认产物不变。
"""
import re

from alexander_abbyy import HYPH, IT_ON, IT_OFF

# 字面星号（OCR 自带、非斜体标记）的待判哨兵，由 repair 阶段裁决
LIT_STAR = '\ue002'


def bare(t):
    return t.replace(IT_ON, '').replace(IT_OFF, '').replace(HYPH, '')


COMPOUND = re.compile(r'(?<![A-Za-z])([a-z]{2,})-([a-z]{2,})(?![A-Za-z])')


def collect_compounds(pages):
    """全书**行内**出现过的连字符复合词。

    行内的连字符不可能是断词（断词只出现在行末），所以这一份就是「原书
    确实这样连写」的证据表。行末断词处到底该不该留连字符，全靠它定夺。
    """
    out = set()
    for pg in pages:
        for par in pg['pars']:
            t = par['text']
            for m in COMPOUND.finditer(t.replace(IT_ON, '').replace(IT_OFF, '')):
                if HYPH in m.group(0):
                    continue
                out.add(m.group(1) + '-' + m.group(2))
    return out


def resolve_hyphens(t, compounds):
    """接缝标记 → 连字符或空。

    `well-watered` / `burnt-offering` / `twenty-second` 这类原书本来就带
    连字符的复合词，正好断在连字符上时不能把连字符吃掉（另一个会话在诗篇
    里查出 8 处被拼成 `wellwatered`）。凭据是同一部书别处**行内**怎么写。
    """
    def repl(m):
        a, b = m.group(1), m.group(2)
        return f'{a}-{b}' if f'{a.lower()}-{b.lower()}' in compounds else a + b
    t = re.sub(r'([A-Za-z]+)' + HYPH + r'([a-z]+)', repl, t)
    return t.replace(HYPH, '')


# ── 文本清理 ─────────────────────────────────────────────────

def normalize_italics(t):
    """哨兵 → markdown `*…*`，并修好 ABBYY 切碎的斜体段边界。

    三类必修（不修的后果见 principles §0.5：kramdown 会把星号原样吐出来）：
      1. 空白落在标记内侧 —— `«the man! »` → `«the man!» `
      2. 同一句斜体被切成相邻两段 —— `«How completely» «happy»` → `«How completely happy»`
      3. 空段 `«»`

    **三条必须一起迭代到不动点，不能各跑一遍。** 合并会造出新的内侧空白：
    `«1»« »mutual` 里第二段是个「斜体空格」，第 1 条把它挪成 `«1» «»mutual`，
    第 2 条合并成 `«1 »mutual`——IT_OFF 内侧又贴上了空白，而第 1 条已经跑完了。
    落到页面上就是 `*1 *mutual`，kramdown 不认这种强调，于是那个星号一路开着，
    直到远处另一个星号才闭合：以赛亚书出过 1728 字连成一段斜体的，全书 236 段，
    诗篇 21 段。
    """
    prev = None
    while prev != t:
        prev = t
        # 1. 边界空白外移
        t = re.sub(IT_ON + r'(\s+)', r'\1' + IT_ON, t)
        t = re.sub(r'(\s+)' + IT_OFF, IT_OFF + r'\1', t)
        # 2. 相邻斜体段合并（中间只有空白）
        t = re.sub(IT_OFF + r'(\s*)' + IT_ON, r'\1', t)
        # 3. 空段
        t = re.sub(IT_ON + r'\s*' + IT_OFF, '', t)
    # 收尾标点：ABBYY 常把结束引号/逗号漏在斜体外，无从判断，保持原状
    return t.replace(IT_ON, '*').replace(IT_OFF, '*')


def fix_literal_asterisks(t):
    """OCR 文本里**自带**的 `*` 字符——必须在哨兵转成 `*` 之前处理掉。

    不处理的后果：这些字面星号与斜体标记混在一起，段落里的 `*` 个数变成奇数，
    kramdown 的强调配对整段错位——从那一点起，该斜体的变正体、该正体的变斜体
    （诗篇 107 v.4 整段后半全反了）。

    对着扫描页看过，它们的来源只有三类：
      `*'` / `**`  开引号 `"` 被读错（19 世纪的双撇号排版）
      `*.` + `e.`  `i. e.` 的 `i` 被读成 `*`
      其余          希伯来文活字读崩后的残渣（`7J*1`、`*T*DrT`）
    前两类有确定的正解，直接还原。第三类不在这里定夺：换成私用区哨兵
    交给 repair 阶段，那里有判词典和语料自证，能分辨 `fi*om`（是 `from`）
    与 `(*nS)`（希伯来活字残渣，无解）。
    """
    t = re.sub(r"\*\*|\*'|'\*", '"', t)
    t = re.sub(r'\*(\.\s*' + IT_ON + r'?\s*e\.)', r'i\1', t)
    return t.replace('*', LIT_STAR)


def fix_ocr_brackets(t):
    """`{Oh)` / `[felicities` —— 左圆括号被读成花/方括号。

    只在「左括号变体 … 右圆括号」这种配对成立时才改，避免动到真正的方括号。
    """
    return re.sub(r'[\[{](?=[^\[\]{}()]*\))', '(', t)


def cleanup(t, compounds=frozenset()):
    t = resolve_hyphens(t, compounds)
    t = fix_literal_asterisks(t)
    t = normalize_italics(t)
    t = fix_ocr_brackets(t)
    t = re.sub(r'[ \t]{2,}', ' ', t)
    t = re.sub(r'\s+([,.;:!?])', r'\1', t)
    return t.strip()


# ── 页码 ─────────────────────────────────────────────────────

PAGENO = re.compile(r'^\s*(\d{1,3})\b|\b(\d{1,3})\s*$')


def as_matcher(runhead):
    """页眉判据既可以是编译好的正则，也可以是自定义谓词。

    以赛亚书的页眉 OCR 出来有 `I N T R O D U 0 T I O N.` 这种**字母被逐个
    拆开**的形态，正则写不完；那本书传的是一个先剥非字母、再做字形归一的
    函数。诗篇仍传正则，两种都要能用。
    """
    if callable(runhead):
        return runhead
    return lambda b: bool(runhead.match(b))


def printed_page_numbers(pages, body_range, runhead, first_page=None):
    """扫描页序号 → 书页页码（页眉上印的那个数）。

    `<!-- PAGE n -->` 标的若是扫描页序号，别人拿任何一本实体书或另一份扫描件
    都对不上——IA 同一 item 的 ABBYY XML 与 PDF 页数本身就能差好几页。
    页眉上印的页码才是跨版本通用的坐标。

    正文第一页通常**没有页眉**（章题占了页顶），推不出页码，所以由调用方用
    `first_page` 给出起点；不给就留 None。

    页码从页眉里取；页眉缺失或数字被 OCR 读崩的，按前一页 +1 推。
    只采信「比上一页恰好大 1」的读数，其余一律当误识——页码本来就是连号的，
    这条约束比任何 OCR 置信度都可靠。
    """
    lo, hi = body_range
    match = as_matcher(runhead)
    out, last = {}, None
    first = True
    for pg in pages:
        if not (lo <= pg['index'] <= hi):
            continue
        num = None
        for par in pg['pars'][:2]:
            b = bare(par['text']).strip()
            if par['nlines'] == 1 and match(b):
                m = PAGENO.search(b)
                if m:
                    cand = int(m.group(1) or m.group(2))
                    if last is None or cand == last + 1:
                        num = cand
                break
        if num is None:
            if last is not None:
                num = last + 1
            elif first:
                num = first_page
        out[pg['index']] = num
        last = num
        first = False
    return out


def check_page_sequence(pmap):
    """页码推完自查：应当严格 +1。返回断点列表（空 = 正常）。"""
    seq = [pmap[i] for i in sorted(pmap) if pmap[i] is not None]
    return [(a, b) for a, b in zip(seq, seq[1:]) if b != a + 1]


# ── 分段 ─────────────────────────────────────────────────────

# 段尾出现这些字符 = 句子没说完。连字符尤其硬——以 `-` 收尾的段落必然是
# 断词断在了段落边界上（`…of the sen-` ⏎ `tence follows…`），本书 15 处。
LOWER_END = set('abcdefghijklmnopqrstuvwxyz,-')


def merge(chunk, verse_start, pmap=None):
    """[(page, par)] → [[page, text]]；无 startIndent 的段是上一段的跨页续行。

    ABBYY 的 par 属性已经把版面判读做完了，直接用它的结论比重新按几何推断
    可靠（principles §0.3 的例外）。唯一的补充信号是节号——每节解说都另起
    一段，OCR 偶尔会漏掉 startIndent，用节号兜底。
    """
    paras = []
    for page, par in chunk:
        t = par['text'].strip()
        if not t:
            continue
        # 页码没被 ABBYY 单独切成一段，而是粘在了续行的开头
        # （`circum-` ⏎ `26 locution used…`）。并段时它就掉进句子中间了。
        # 判据很硬：这个数字必须**正好等于本页的书页页码**。
        if pmap and pmap.get(page) is not None:
            t = re.sub(r'^\s*%d\s+(?=[a-z(])' % pmap[page], '', t)
        new = 'startIndent' in par['attrs'] or bool(verse_start.match(bare(t)))
        # ABBYY 偶尔给跨页续段也标上 startIndent（页顶那一行的左边距被页眉
        # 顶歪），于是一句话被劈成两段，读者看到句子中间空一行。
        # **上一段以小写字母或逗号收尾就说明句子没说完**——句子总以句号收尾，
        # 半句话后面不会另起一段。这里不看下一段首字母是大是小：续行常常正好
        # 接一个专名（`…decoration, and` ⏎ `Hendewerk to the military…`）。
        # 内容信号压过几何信号（以赛亚书 76 处）。节号段不受影响。
        # 以数字开头的段永远不是句子中段的续行——节号写法不止一种
        # （`3 (2).` 和 `3 (2.)` 都有，后者句点在括号里，verse_start 认不出），
        # 只挡 verse_start 会漏。诗篇 84 就是这么被并掉一整节的。
        if new and paras and not verse_start.match(bare(t)) and not bare(t)[:1].isdigit():
            if bare(paras[-1][1]).rstrip()[-1:] in LOWER_END:
                new = False
        if new or not paras:
            paras.append([page, t])
        else:
            prev = paras[-1][1]
            tail = prev.rstrip(IT_OFF)
            if tail.endswith('-') and bare(t)[:1].islower():
                paras[-1][1] = tail[:-1] + HYPH + \
                    (IT_OFF if prev.endswith(IT_OFF) else '') + t
            else:
                paras[-1][1] = prev + ' ' + t
    return paras


def slice_pars(by_index, pg0, pi0, pg1, pi1, runhead):
    """取 (页 pg0 的第 pi0 段之后) 到 (页 pg1 的第 pi1 段之前) 的所有正文段。"""
    match = as_matcher(runhead)
    out = []
    for idx in range(pg0, pg1 + 1):
        pg = by_index.get(idx)
        if not pg:
            continue
        for i, par in enumerate(pg['pars']):
            if idx == pg0 and i <= pi0:
                continue
            if idx == pg1 and i >= pi1:
                continue
            if par['nlines'] == 1 and match(bare(par['text']).strip()):
                continue
            out.append((idx, par))
    return out


def write_chapter(path, header, chunk, verse_start, pmap=None,
                  compounds=frozenset()):
    """一章 → 一个 md 文件，返回段落数。"""
    paras = merge(chunk, verse_start, pmap)
    lines = [header, '']
    cur = None
    for page, t in paras:
        if page != cur:
            shown = (pmap or {}).get(page) or page
            lines.append(f'<!-- PAGE {shown} -->')
            cur = page
        txt = cleanup(t, compounds)
        if txt:
            lines.append(txt)
            lines.append('')
    path.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
    return len(paras)


# ── 章题定位 ─────────────────────────────────────────────────

_ROMAN_VALS = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'),
               (90, 'XC'), (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'),
               (5, 'V'), (4, 'IV'), (1, 'I')]

# OCR 常见混淆：把整行压成只剩罗马数字骨架再比
_SKEL = str.maketrans({'1': 'I', 'l': 'I', '|': 'I', 'J': 'I', 'j': 'I',
                       'i': 'I', '!': 'I', 'v': 'V', 'U': 'V', 'u': 'V',
                       'Y': 'V', 'x': 'X', 'K': 'X', 'c': 'C', 'O': 'C',
                       '0': 'C', 'e': 'C', 'E': 'C', 's': 'S'})


def roman(n):
    out = ''
    for v, s in _ROMAN_VALS:
        while n >= v:
            out += s
            n -= v
    return out


def skeleton(t):
    t = re.sub(r'[^A-Za-z0-9|!]', '', bare(t)).upper()
    return t.translate(_SKEL)


def _head_matches(s, target):
    """章题骨架 s 是否就是 target。

    两条规矩，缺一不可：
      **不能用前缀匹配**——XII 是 XIII 的前缀，以赛亚书卷一第 12 章会因此
      定位到第 13 章的标题上，往后 27 章全部找不到。所以尾巴里不许再出现
      罗马字母。
      **要容一个字符的误识**——`CHAPTER XI.` 被读成 `CHAPTER XL`（`I.` 粘成
      `L`），以赛亚书第 11 章就是这么丢的。只在**长度相同**时容一次替换：
      长度一变，XI 与 XII 这类相邻章号就会互相串号。
    """
    if s.startswith(target) and not re.search(r'[IVXLCDM]', s[len(target):]) \
            and len(s) <= len(target) + 3:
        return True
    if len(s) == len(target):
        return sum(a != b for a, b in zip(s, target)) == 1
    return False


def find_roman_heads(pages, start_index, lo, hi, prefix='CHAPTER', runhead=None):
    """按**顺序预期**找罗马数字章题，而不是硬套正则。

    章题里的罗马数字被 OCR 读崩的花样太多（`LiV`、`CXLIII` 粘成一坨、
    `PSALMCXLIII.`），逐个写正则永远漏。章是连号的，所以每次只找「下一章」
    这一个目标，把候选行压成骨架比对——诗篇 150 篇一次全中。

    → {章号: (页序号, 段序号)}
    """
    # 页眉必须先剔掉：以赛亚书卷二的页眉就是 `CHAPTER XL. 3`，与章题只差一个
    # 页码，不排除就会把「章从这里开始」定位到页顶的页眉上，把上一章的尾巴
    # 并进下一章。
    match = as_matcher(runhead) if runhead is not None else (lambda b: False)
    heads = {}
    exp = lo
    for pg in pages:
        if pg['index'] < start_index:
            continue
        for i, par in enumerate(pg['pars']):
            if par['nlines'] > 2:
                continue
            if par['nlines'] == 1 and match(bare(par['text']).strip()):
                continue
            s = skeleton(par['text'])
            if len(s) > 26:
                continue
            target = skeleton(prefix) + skeleton(roman(exp))
            if not _head_matches(s, target):
                continue
            if True:
                heads[exp] = (pg['index'], i)
                exp += 1
                if exp > hi:
                    return heads
    return heads
