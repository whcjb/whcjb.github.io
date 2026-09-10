#!/usr/bin/env python3
"""第二证人：拿 PDF 自带的 Internet Archive OCR 文本层校我们自己那一遍 tesseract。

为什么要两遍
------------
本书是 1831 年铅印扫描件，单靠一遍 OCR 修不动的错字满地都是——`ail?`（all）、
`T"`（T'）、`Ape`（Abel）、孤立的 `|` 与 `/`。挨个写规则改是猜；换个证人来对
才是判。PDF 里现成就有第二份 OCR：IA 扫描时留下的 `GlyphLessFont` 隐形文本层
（DIAGNOSIS.md §2）。两份都是 tesseract 出的，但**版本、预处理、页面切分都不同**，
错的地方基本不重叠，正好互为旁证。

判定规则（宁可不动，也不猜）
----------------------------
逐词对齐后只在两种情形下采信对方：

1. **孤立的 `|` / `/`**——本书里这两个字符从不合法出现。对方在同一位置
   有词就取对方的（`| omit` → `I omit`、`| Tim. ii.` → `1 Tim. ii.`），
   对方那里什么都没有就是扫描斑点，删掉（正文页里 81 处）。
2. **我方不是词、对方是词、且两者形近**——`ail`→`all`、`Ape`→`Abel`。
   我方是词就不动，哪怕对方也是词：两个都成立时没有理由偏信谁。
   另有三条守卫，都是被实测的错改逼出来的：
   · **不许变短**（长度比 ≥0.85）。我方把两个词读粘了时（`itis` / `greata` /
     `forall.` / `himin` / `wholeis`），对方那边是两个 token，对齐只取得到
     头一个，采信就等于**丢字**。
   · **对方不许带数字或怪符号**。`Morte`（拉丁文，英文词典里没有）差点被换成
     `3forte`；`lagius` → `las^ius`、`Chap.i.` → `Chap,\.` 同理。
   · **两边编辑距离 ≤2**。防止「形近」这条被长词拖着放行。

对齐不上（相似度 < 0.55）的行整行不动。实测正文页范围内 108 处孤立符号
全部判得出，零悬案。

用法（审计，不改文件）:
    python3 scripts/davenant_witness.py --vol 2 --pages 322-578
"""
import argparse
import collections
import json
import difflib
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
PDFS = {1: 'expositionofepis01dave.pdf', 2: 'expositionofepis02dave.pdf'}

DICT = set()
_dw = Path('/usr/share/dict/words')
if _dw.exists():
    DICT = {w.strip().lower() for w in _dw.read_text(errors='ignore').split()}

_docs, _cache = {}, {}
_BIGRAM, _UNI = None, None


def corpus():
    """→ (二元词频, 一元词频)，取自本书自己已提取的正文。

    两边**都是英文词**时（`ail` vs `all`、`be` vs `he`、`but` vs `hut`），
    谁对谁错没有先验——实测这类分歧 854 处，两个方向都大量存在。词典帮不上忙，
    但书自己的行文帮得上：`in all` 在全书出现几十次，`in ail` 一次也没有。
    用本书语料的二元词频当裁判，是拿同一部书的语言习惯判同一部书的错字，
    不引入外部假设。语料里当然也混着错字，但错字是稀疏的，压不过正确形式。
    """
    global _BIGRAM, _UNI
    if _BIGRAM is None:
        _BIGRAM, _UNI = collections.Counter(), collections.Counter()
        for name in ('davenant_colossians_structured.txt',
                     'davenant_colossians_appendix.txt'):
            f = RAW / name
            if not f.exists():
                continue
            txt = re.sub(r'<[^>]+>|\[[A-Z0-9_]+\]', ' ',
                         f.read_text(encoding='utf-8'))
            for line in txt.splitlines():
                ws = [_norm(w) for w in line.split()]
                ws = [w for w in ws if w]
                _UNI.update(ws)
                _BIGRAM.update(zip(ws, ws[1:]))
    return _BIGRAM, _UNI


def _uni():
    return corpus()[1]


def subst_repair(tok):
    """→ 换字后的词，或 None。拿**本书自己的词汇表**回填字形混淆。

    第二证人有两处够不着：一是目标是专名（`Paul` 不在英文词典里，规则里
    「对方得是词典词」这条就把它挡了）；二是对方那一遍也读花了
    （`Sau!` 那行 IA 读成 `«Sa///`）。这两种都能靠书自己的词汇解决——
    `Pau/` 换 `/`→`l` 得到 `paul`，全书出现几百次；`Sau!` 换 `!`→`l` 得到
    `saul`，也是本书的常用专名。

    卡得很紧：原词必须是生僻词（≤2 次），换出来的必须是常见词（≥8 次），
    且**只有一种换法**能换出常见词——两种都成立就说明证据不唯一，不动。
    """
    bg, uni = corpus()
    base = _norm(tok)
    if len(base) < 3 or uni[base] > 2:
        return None
    out = set()
    for a, b in CHAR_SUBS:
        if a in tok and uni[_norm(tok.replace(a, b))] >= 8:
            out.add(tok.replace(a, b))
    return out.pop() if len(out) == 1 else None


APOS_RE = re.compile(r"^([A-Za-z]{2,})'([A-Za-z]{2,})$")
# 十七—十九世纪诗行里的省音写法。本书引诗不少，这几个词形是**原文**，
# 任何一条撇号规则都不许碰：`pow'rs` 补个 e 正好是 powers、`Ne'er` 补个 v
# 正好是 never，语料频次还都很高，不列出来就一定会被"改正"掉。
POETIC = {"ne'er", "e'er", "o'er", "pow'r", "pow'rs", "heav'n", "heav'ns",
          "ev'ry", "giv'n", "wond'rous", "s'ems", "th'", "op'ning"}


def _bookword(w):
    """词典或本书语料认得就算词。系统词典缺屈折形（called / nailed /
    ministered 一个都查不到），只靠 DICT 这一路，撇号规则形同虚设。"""
    b = _norm(w)
    return len(b) >= 2 and (b in DICT or _uni()[b] >= 8)


def apos_repair(tok, other, oseg):
    """撇号位上的两类 OCR 错：读掉的空格、读花的字母。

      · 撇号原是空格（`Which'are` / `by'the`）：两半都是词，且**第二证人
        在这一位断开了**，或本书语料里这个二元组本来就常见（≥5 次）而粘
        起来的词形本身生僻（≤2 次）
      · 撇号原是字母（`nai'ed` / `righ'eousness` / `fa'se`）：先认第二证人
        补出来的那个词（它比我多且只多一个字符、首尾都对得上）；两卷都读花
        时退到本书语料——只有**唯一**一个字母能填出本书常见词才动手

    诗行省音走 POETIC 白名单挡掉，不靠频次去猜。
    """
    m = APOS_RE.match(tok)
    if not m or tok.lower() in POETIC:
        return None
    a, b = m.group(1), m.group(2)
    base = _norm(tok)
    seg = [x for x in (oseg or []) if x]
    if _bookword(a) and _bookword(b):
        split_seen = (len(seg) == 2 and _norm(seg[0]) == _norm(a)
                      and _norm(seg[1]) == _norm(b)) or (
            isinstance(other, str) and _norm(other) == _norm(a))
        bg, uni = corpus()
        if split_seen or (uni[base] <= 2 and bg[(_norm(a), _norm(b))] >= 5):
            return f'{a} {b}'
    cands = []
    if isinstance(other, str):
        cands.append(other)
    if len(seg) == 2:
        cands.append(seg[0] + seg[1])
    for c in cands:
        o = _norm(c)
        if (len(o) == len(base) + 1 and o.startswith(_norm(a))
                and o.endswith(_norm(b)) and (o in DICT or _uni()[o] >= 2)):
            return c
    if _uni()[base] <= 2:
        fill = {a + ch + b for ch in 'abcdefghijklmnopqrstuvwxyz'
                if _uni()[_norm(a + ch + b)] >= 8}
        if len(fill) == 1:
            return fill.pop()
    return None


# 词当中混进阿拉伯数字：`1s`→is、`2n`→in、`7s`→is、`2t`→it（全书四种
# 数字都出现过，`1` 最多）。这是 `l.`→`1.` 那条的反向——那一条修的是编号位
# 上的字母，这一条修的是字母位上的数字，两边都得管。
# 换法按字形出，不是随便试 26 个字母：`1s` 若允许全字母替换，`as`/`is`/`us`
# 在本书里都常见，唯一性判据当场失效。
DIGIT_GLYPH = {'0': 'oO', '1': 'ilt', '2': 'iz', '3': 'e', '4': 'a',
               '5': 's', '6': 'b', '7': 'ti', '8': 'b', '9': 'gq'}
DIGIT_IN_WORD = re.compile(r'^([a-z]{0,4})([0-9])([a-z]{1,4})([.,;:!?]?)$')


def digit_repair(tok):
    """→ 换字后的词，或 None。原词在本书生僻（≤2 次），换出来的常见（≥8 次），
    且**只有一种换法**能换出常见词。三条同时成立才动手。"""
    m = DIGIT_IN_WORD.match(tok)
    if not m:
        return None
    a, d, b, punct = m.groups()
    # 这里**不能**照 subst_repair 那样先卡「原词生僻」：_uni 的键是去掉
    # 非字母后的形状，`1s` 归一成 `s`，而单字母 `s` 在本书里到处都是
    # （缩写、书名），门槛当场把每一个待修的词都挡掉（实测一处都改不动）。
    # 含数字的词形本来就不是英文词，守卫交给下面「唯一 + 常见」两条。
    # 候选还得是**干净的词**：词典词或罗马数字。只看本书频次不行——语料里
    # 混着同类错字（`ts` / `lt` 这些形状自己就出现十几次），`1s` 的候选里
    # `is` 和 `ts` 双双过线，唯一性判据当场失效，一个也改不成。
    out = {a + c + b for c in DIGIT_GLYPH.get(d, '')
           if _uni()[_norm(a + c + b)] >= 8
           and (_norm(a + c + b) in DICT
                or re.fullmatch(r'[ivxlcm]+', _norm(a + c + b)))}
    return out.pop() + punct if len(out) == 1 else None


# ── 数字位上的 `l` ────────────────────────────────────────────────────────────
# `1` 这个字形在本书的字体里是「衬线底座 + 竖杆 + 旗」，OCR 有两种读法错：
#   · 整个读成小写 `l`（`l.` → `1.`，段首编号那条已经在提取器里处理）
#   · **多读出一个字形**：`1.` 读成 `1l.`、`31.` 读成 `3l.`
# 后一种没法只看形状判：`1l` 既可能是原书的 `1`（底座被多读了一遍），
# 也可能是原书真的 `11`（vol2 p47 那条 600 dpi 看得很清楚，就是 11）。
# 所以一律要证据：先问第二证人，第二证人那一行缺失或读花时，查
# numeral_votes.json——那张表由 `--build-numerals` 把该行按 8 倍重新 OCR
# 一遍建出来（同一张扫描图放大重扫，是本项目一贯的「第三证人」做法）。
NUMERAL_RE = re.compile(r'^([\dl]{1,4})([.,;:]?)$')
NUM_TABLE = RAW / 'numeral_votes.json'
_NUMS = None


def numeral_votes():
    global _NUMS
    if _NUMS is None:
        _NUMS = (json.loads(NUM_TABLE.read_text(encoding='utf-8'))
                 if NUM_TABLE.exists() else {})
    return _NUMS


def numeral_repair(vol, page, tok, other):
    m = NUMERAL_RE.match(tok)
    if not m or 'l' not in m.group(1) or m.group(1) == 'l':
        return None
    mine = m.group(1).replace('l', '1')
    ok = {mine, mine[:-1]} - {''}         # `1l` → 11 或 1，两种都可能
    got = None
    if isinstance(other, str):
        o = re.match(r'^(\d{1,4})[.,;:]?$', other)
        if o and o.group(1) in ok:
            got = o.group(1)
    if got is None:
        got = numeral_votes().get(f'{vol}|{page}|{tok}')
        if got not in ok:
            got = None
    if got is None and len(mine) > 1 and mine[0] != '1':
        # `3l` / `4l` 这种没有歧义：`3` 的字形不会被多读出一个 l，
        # 那个 l 只能是紧跟其后的数字 1（`Matt. vi. 3l.` 原书是 31.，
        # 600 dpi 核过）
        got = mine
    return got + m.group(2) if got else None


def judge(prev, nxt, mine, other):
    """→ 采信对方吗。看 (前词,候选) 与 (候选,后词) 两个二元组的词频差。

    要求赢家至少 4 倍于输家、且自己出现 ≥5 次；否则维持原样（不猜）。
    """
    bg, uni = corpus()
    a, b = _norm(mine), _norm(other)
    sa = bg[(prev, a)] + bg[(a, nxt)]
    sb = bg[(prev, b)] + bg[(b, nxt)]
    if sb >= 5 and sb >= sa * 4:
        return True
    return False
# 孤立的 | 或 /（两侧是空白或行首行尾）
SPECK = re.compile(r'^[|/]$')
# OCR 在这本书上的字形混淆：斜体 l 读成 / ! | 1，重音符是扫描脏点。
# 只在「换完之后正好是本书里的常见词、且原词是生僻词」时才换（见 subst_repair）。
CHAR_SUBS = (('/', 'l'), ('!', 'l'), ('|', 'l'), ('1', 'l'), ('í', 'i'),
             ('à', 'a'), ('á', 'a'), ('â', 'a'), ('é', 'e'), ('è', 'e'),
             ('ê', 'e'), ('ó', 'o'), ('ò', 'o'), ('ú', 'u'), ('ï', 'i'),
             ('¢', 'c'), ('§', 's'))
# 圣经书卷缩写里带卷次的那几种，`1 Tim.` / `2 Cor.` 的卷次常被读成 `|`
BIBLE_BOOK = re.compile(
    r'^(Tim|Cor|Thess|Pet|John|Kings|Sam|Chron|Macc|Esdr)[.,]', re.I)


def ia_lines(vol, page):
    key = (vol, page)
    if key not in _cache:
        if vol not in _docs:
            _docs[vol] = fitz.open(str(RAW / PDFS[vol]))
        txt = _docs[vol][page].get_text()
        _cache[key] = [re.sub(r'\s+', ' ', l).strip()
                       for l in txt.splitlines() if l.strip()]
    return _cache[key]


_ptoks = {}


def page_tokens(vol, page):
    """→ 整页 IA 文本的 token 串（带缓存）。"""
    key = (vol, page)
    if key not in _ptoks:
        _ptoks[key] = ' '.join(ia_lines(vol, page)).split()
    return _ptoks[key]


def best_match(vol, page, toks):
    """→ 与我方这一行对齐的对方 token 串。

    先按行找最相似的一行；找不到（相似度 <0.55）就退到**整页**对齐——
    两遍 OCR 的换行位置常常不一样，同一句在对方那边可能跨了两行
    （`…to the faith of Christ, as a` / `memorial of so great a conquest.`），
    按行比永远比不上（实测相似度只有 0.47），整页比就没这个问题。
    """
    cands = ia_lines(vol, page)
    if not cands:
        return None
    key = ' '.join(_norm(w) for w in toks)
    best = max(cands, key=lambda c: difflib.SequenceMatcher(
        None, key, ' '.join(_norm(w) for w in c.split())).ratio())
    r = difflib.SequenceMatcher(None, key, ' '.join(
        _norm(w) for w in best.split())).ratio()
    if r >= 0.55:
        return best.split()
    # 整页兜底：在整页 token 串里截出与本行最贴合的一段
    pt = page_tokens(vol, page)
    sm = difflib.SequenceMatcher(None, [_norm(w) for w in toks],
                                 [_norm(w) for w in pt], autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size]
    if not blocks or sum(b.size for b in blocks) < len(toks) * 0.6:
        return None
    lo = max(0, blocks[0].b - (blocks[0].a))
    hi = min(len(pt), blocks[-1].b + blocks[-1].size + (len(toks) - blocks[-1].a))
    return pt[lo:hi]


def _norm(s):
    return re.sub(r'[^a-z]', '', s.lower())


def _isword(w):
    b = _norm(w)
    return len(b) >= 2 and b in DICT


def _pairs(toks, theirs, ops):
    """→ [(下标, "词1 词2")]，我方一个 token 对上对方两个的那些位置。"""
    out = []
    for tag, a1, a2, b1, b2 in ops:
        if tag != 'replace' or a2 - a1 != 1 or b2 - b1 != 2:
            continue
        w0, p1, p2 = toks[a1], theirs[b1], theirs[b1 + 1]
        mine_, two = _norm(w0), _norm(p1) + _norm(p2)
        # 四条守卫，都是被实测的错改逼出来的：
        # · 带连字号或破折号的不动——`loving-kindness` 会被切成
        #   `loving- kindness`，`Trent.—He` 更是把 `.—` 一起吃掉。
        # · 带脚注符的不动——`because*of` 里那个 `*` 是脚注引用，切完就没了。
        # · 不许变短：对方自己读花时会短一截（`infused` → `i) fused`）。
        # · 两半都得是词（词典词或本书里出现 ≥8 次）——挡住把词尾当独立词切
        #   的那种（`feareth` → `fear eth`）。
        # 撇号同理：`Father's` 会被切成 `Father s`
        if re.search(r"[-—*+'’]", w0):
            continue
        # 长度下限 3：`asa`(as a) / `isa`(is a) / `wasa` 这类最常见的粘连
        # 只有三四个字母，卡到 4 就把它们全漏了（实测）。
        if len(mine_) < 3 or len(two) < len(mine_):
            continue
        if difflib.SequenceMatcher(None, mine_, two).ratio() < 0.85:
            continue
        _, uni = corpus()
        if not all(_isword(x) or uni[_norm(x)] >= 8 for x in (p1, p2)):
            continue
        # 拆开只许加空格，不许多出别的字符：对方那边有时把标点也读花了
        # （`God,.in` → `God,- in` 凭空多个连字符，`1nless` → `In less`
        # 把 `1` 换成了 `I`——真正的原词是 Unless）。
        if set((p1 + p2).replace(' ', '')) - set(w0.replace(' ', '')):
            continue
        out.append((a1, p1 + ' ' + p2))
    return out


def _split_props(vol, page, text):
    """→ [(我方词形, "词1 词2")]，供 build_split_table 统计用。"""
    toks = text.split()
    if len(toks) < 2:
        return []
    theirs = best_match(vol, page, toks)
    if theirs is None:
        return []
    sm = difflib.SequenceMatcher(None, [_norm(w) for w in toks],
                                 [_norm(w) for w in theirs])
    return [(toks[i], two) for i, two in _pairs(toks, theirs, sm.get_opcodes())]


def fix_line(vol, page, text):
    """→ (改后的文本, [(原, 新, 理由), …])。判不了就原样返回。"""
    toks = text.split()
    if len(toks) < 2:
        return text, []
    # ⚠️ 这里**不能**因为「每个词都在词典里」就早退。词频裁判要处理的正是
    # 「两边都是词」的情形——`Does not free-will one cause effect in ail?`
    # 整行八个词全在词典里，早退一挡，`ail` → `all` 永远轮不到判（实测）。
    theirs = best_match(vol, page, toks)
    if theirs is None:
        # 对不上行（多半是两边都读花的希腊文音译）时，别的都不动，
        # 但孤立的 `|` `/` 照删——这两个字符在本书里从不合法出现，
        # 不需要第二证人也能断定是扫描斑点。
        if not any(SPECK.match(t) for t in toks):
            return text, []
        keep = [t for t in toks if not SPECK.match(t)]
        return ' '.join(keep), [(t, '', '斑点') for t in toks if SPECK.match(t)]

    sm = difflib.SequenceMatcher(None, [_norm(w) for w in toks],
                                 [_norm(w) for w in theirs])
    ops = sm.get_opcodes()
    pair2 = dict(_pairs(toks, theirs, ops))
    out, log = list(toks), []
    for i, w in enumerate(toks):
        # 对方在这一位是什么
        other, oseg = '~', None           # '~' = 对方那里空着
        for tag, a1, a2, b1, b2 in ops:
            if not (a1 <= i < a2):
                continue
            if tag == 'equal':
                other = theirs[b1 + (i - a1)]
            elif tag == 'delete':
                other = None
            elif tag == 'replace':
                seg, off = theirs[b1:b2], i - a1
                other = seg[off] if off < len(seg) else None
                # 我这一个 token 对上对方一整段时，整段也留下来：
                # `righ'eousness` 对面是 `right` + `eousness` 两个 token，
                # 只看 seg[0] 什么也判不出，拼起来才看得见那个 `t`
                if a2 - a1 == 1:
                    oseg = list(seg)
            break
        # 我方把两个词读粘了：对方那边把它排成**两个** token，直接采信。
        # 这是证据不是猜——`asa memorial` 对面是 `as a memorial`。
        # 不靠「能拆成两个词典词」那种判据：`becometh` / `sumus` / `Johnson`
        # 一样能拆，实测 287 种候选里过半是这种误判。
        fix = (apos_repair(w, other, oseg) or digit_repair(w)
               or numeral_repair(vol, page, w, other))
        if fix:
            out[i] = fix
            log.append((w, fix, '撇号'))
            continue
        if not SPECK.match(w) and i in pair2 and w in splits():
            out[i] = pair2[i]
            log.append((w, pair2[i], '对方拆作两词'))
            continue
        if SPECK.match(w):
            nxt = toks[i + 1] if i + 1 < len(toks) else ''
            if isinstance(other, str) and other != '~' and len(other) <= 4 \
                    and not SPECK.match(other):
                out[i] = other
                log.append((w, other, '第二证人'))
            elif BIBLE_BOOK.match(nxt):
                # 对方那边对不齐（多半整行是希腊文音译，两边都读花了），
                # 但后面紧跟着圣经书卷缩写时，这个 `|` 只能是数字 1
                # （`| Tim. ii.` = 1 Tim. ii.），删掉就把卷次吃了。
                out[i] = '1'
                log.append((w, '1', '书卷序数'))
            else:
                # 其余一律当斑点删：`|` `/` 在本书里从不合法出现，
                # 这一条不需要第二证人也能断定。
                out[i] = None
                log.append((w, '', '斑点'))
            continue
        # 语料回填先试：这条只在「原词生僻 + 只有一种换法能换出本书常见词」
        # 时才动手，条件比后面几条都硬，放前面不会抢别人的活。
        # ⚠️ 必须放在依赖 `other` 的判断之前——`Sau!` 那行对方读成 `«Sa///`，
        # 而 `_isword('«Sa///')` 归一成 `sa` 竟命中词典，于是流程被带进
        # 「两边都是词」的岔路，回填一直没机会执行（实测）。
        # 门槛用「本书里是不是生僻」，不用「在不在词典里」：`pau` / `asa`
        # 这类三字母串在系统词典里居然都有，用词典当门槛会把它们放过去。
        if _uni()[_norm(w)] <= 2:
            fix = subst_repair(w)
            if fix:
                out[i] = fix
                log.append((w, fix, '语料回填'))
                continue
        if other in (None, '~') or not isinstance(other, str):
            continue
        if _isword(w) and _isword(other):
            # 两边都是词：交给本书语料的二元词频裁判（见 judge）
            a, b = _norm(w), _norm(other)
            # 同样不许变短：`Fora`(For a) 被判成 `For` 就把 "a" 吃掉了
            if (len(b) >= len(a) and abs(len(a) - len(b)) <= 1
                    and sum(1 for x in difflib.ndiff(a, b) if x[0] != ' ') <= 2
                    and not re.search(r'[\d^\\~`]', other)
                    and judge(_norm(toks[i - 1]) if i else '',
                              _norm(toks[i + 1]) if i + 1 < len(toks) else '',
                              w, other)):
                out[i] = other
                log.append((w, other, '词频裁判'))
            continue
        if _isword(w) or not _isword(other):
            continue
        a, b = _norm(w), _norm(other)
        if len(a) < 3 or len(b) < len(a) * 0.85:
            continue                      # 变短 = 我方粘词、对方只对上半截
        if re.search(r'[\d^\\~`]', other):
            continue                      # 对方自己就是乱码
        if difflib.SequenceMatcher(None, a, b).ratio() < 0.55:
            continue
        if sum(1 for _ in difflib.ndiff(a, b) if _[0] != ' ') > 4:
            continue                      # 编辑距离 >2
        out[i] = other
        log.append((w, other, '第二证人'))
    if not log:
        return text, []
    return ' '.join(x for x in out if x is not None), log


SPLIT_TABLE = RAW / 'split_votes.json'
_SPLITS = None


def splits():
    """→ {我方词形: '两个词'}，全书投票的结果。

    单看一行不足以判「这是不是粘连词」：`everywhere` / `becometh` 也能被
    对方拆成两半。改看**全书**——对同一个词形，IA 若在大多数出处都排成两个词，
    那就是我方把它读粘了；只在个别行拆开的，多半是对方那一行读花了。
    门槛：至少出现 2 次、且 ≥60% 的出处对方都拆；只出现 1 次的另需该词不在
    英文词典里。表建一次存盘（davenant_raw/colossians/split_votes.json），
    提取时直接读，不必每次重扫两卷。
    """
    global _SPLITS
    if _SPLITS is None:
        _SPLITS = (json.loads(SPLIT_TABLE.read_text(encoding='utf-8'))
                   if SPLIT_TABLE.exists() else {})
    return _SPLITS


def build_split_table():
    """扫两卷，统计每个词形被对方拆开的比例，写出 split_votes.json。"""
    seen = collections.Counter()
    split = collections.Counter()
    prop = {}
    for vol in (1, 2):
        for ln in (RAW / f'vol{vol}_lines.jsonl').open(encoding='utf-8'):
            d = json.loads(ln)
            for l in d['lines']:
                for tok, two in _split_props(vol, d['page'], l['text']):
                    split[tok] += 1
                    prop.setdefault(tok, two)
            for l in d['lines']:
                for t in l['text'].split():
                    seen[t] += 1
    table = {}
    for tok, n in split.items():
        tot = seen[tok] or n
        if n >= 2 and n / tot >= 0.6:
            table[tok] = prop[tok]
        elif n == 1 and tot == 1 and not _isword(tok):
            table[tok] = prop[tok]
    SPLIT_TABLE.write_text(json.dumps(table, ensure_ascii=False, indent=0),
                           encoding='utf-8')
    print(f'✓ {SPLIT_TABLE.name}  {len(table)} 个词形')
    return table


def build_numeral_table():
    """第三证人：把含歧义数字的行按 8 倍重新 OCR，写 numeral_votes.json。

    只处理第二证人给不出答案的那些位置（IA 那一行缺失、或读成别的形状）。
    8 倍重扫认得出「一个字形还是两个」——`cap. 1l.` 重扫成 `cap. |.`（一个），
    `cap. 1l,` 重扫成 `cap. 11,`（两个）。做完存盘，提取时直接查表。
    """
    import subprocess
    import tempfile
    from PIL import Image
    pdfs = {1: 'expositionofepis01dave.pdf', 2: 'expositionofepis02dave.pdf'}
    table = {}
    for vol in (1, 2):
        doc = fitz.open(str(RAW / pdfs[vol]))
        for ln in (RAW / f'vol{vol}_lines.jsonl').open(encoding='utf-8'):
            d = json.loads(ln)
            for l in d['lines']:
                toks = [t for t in l['text'].split()
                        if NUMERAL_RE.match(t) and 'l' in NUMERAL_RE.match(t).group(1)
                        and NUMERAL_RE.match(t).group(1) != 'l']
                if not toks:
                    continue
                page = doc[d['page']]
                sc = (8 * 72) / 400          # hOCR 坐标是 400 dpi 出的
                pix = page.get_pixmap(matrix=fitz.Matrix(8, 8))
                im = Image.frombytes('RGB', (pix.width, pix.height),
                                     pix.samples).convert('L')
                box = (max(0, int(l['x0'] * sc) - 10), max(0, int(l['y0'] * sc) - 8),
                       min(im.size[0], int(l['x1'] * sc) + 10),
                       min(im.size[1], int(l['y1'] * sc) + 8))
                with tempfile.NamedTemporaryFile(suffix='.png') as fh:
                    im.crop(box).save(fh.name)
                    txt = subprocess.run(
                        ['tesseract', fh.name, 'stdout', '--psm', '7', '-l', 'eng'],
                        capture_output=True, text=True).stdout
                for t in toks:
                    mine = NUMERAL_RE.match(t).group(1).replace('l', '1')
                    key = f'{vol}|{d["page"]}|{t}'
                    # 重扫里那一位读出来**几个字形**——`1` `l` `I` `|` `]`
                    # 都算一个。⚠️ 不能用 `\b` 收边：`1]` 后面接的是句点，
                    # `]` 本身不是词字符，`\b` 匹配不上，两字形的那一条永远
                    # 落空，`iv. 11.` 会被判成 `1`（实测）。
                    G = r'[1lI|\]]'
                    NB = r'(?<![\w|\]])'
                    NA = r'(?![\w|\]])'
                    if mine[0] != '1':
                        if re.search(NB + re.escape(mine[0]) + G + NA, txt):
                            table[key] = mine
                        continue
                    if re.search(NB + G + G + NA, txt):
                        table[key] = mine if len(mine) > 1 else mine
                    elif re.search(NB + G + NA, txt):
                        table[key] = mine[:-1] or mine
                    print(f'  v{vol}p{d["page"]} {t!r} → {table.get(key)!r}'
                          f'   重扫: {" ".join(txt.split())[:78]}', flush=True)
    NUM_TABLE.write_text(json.dumps(table, ensure_ascii=False, indent=0),
                         encoding='utf-8')
    print(f'✓ {NUM_TABLE.name}  {len(table)} 处')
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', type=int, default=1, choices=(1, 2))
    ap.add_argument('--pages', default='86-631', help='如 322-578')
    ap.add_argument('--limit', type=int, default=60)
    ap.add_argument('--build-splits', action='store_true',
                    help='扫两卷统计粘连词，写 split_votes.json')
    ap.add_argument('--build-numerals', action='store_true',
                    help='含歧义数字的行按 8 倍重扫，写 numeral_votes.json')
    a = ap.parse_args()
    if a.build_splits:
        build_split_table()
        return 0
    if a.build_numerals:
        build_numeral_table()
        return 0
    lo, hi = (int(x) for x in a.pages.split('-'))
    import json
    tally = collections.Counter()
    shown = 0
    for ln in (RAW / f'vol{a.vol}_lines.jsonl').open(encoding='utf-8'):
        d = json.loads(ln)
        if not lo <= d['page'] <= hi:
            continue
        for l in d['lines']:
            _, log = fix_line(a.vol, d['page'], l['text'])
            for old, new, why in log:
                tally[why] += 1
                if shown < a.limit:
                    shown += 1
                    print(f"  p{d['page']:<4} {why}  {old!r} → {new!r}")
    print('汇总', dict(tally), '合计', sum(tally.values()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
