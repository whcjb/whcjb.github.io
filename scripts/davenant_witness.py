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


def reset_corpus():
    """清掉语料缓存。提取器迭代到不动点时每一遍都要重新读自己的新产物。"""
    global _BIGRAM, _UNI, _INFL
    _BIGRAM = _UNI = None
    _INFL = None


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
DIGIT_GLYPH = {'0': 'oO', '1': 'ilt', '2': 'iz', '3': 'e', '4': 'at',
               '5': 'sb', '6': 'b', '7': 'ti', '8': 'b', '9': 'gq'}
DIGIT_IN_WORD = re.compile(r'^([a-z]{0,4})([0-9])([a-z]{1,4})([.,;:!?]?)$')


# `1` 被读成 `l` 的三种残形。段首那一种提取器已有 ENUM_L 管，但编号不总在
# 段首——`Observe l. The time…`、`…may be deduced. l. That…`、`John i. l.`
# 都在句中（全书 22 处）。另有两种：`T` 被读成 `'l'`（`'l'o` / `'l'he`，3 处），
# 以及夹在两个词之间的孤立 `l`（扫描斑点，5 处：`he teaches l us`）。
ELL_ENUM = re.compile(r'^\]?l\.$')
ELL_T = re.compile(r"^'l'(?=[A-Za-z])")


def ell_repair(w, prev, nxt, other, other3):
    """→ 改后的 token / '' （删掉）/ None（不动）。"""
    if ELL_T.match(w):
        return 'T' + w[3:]                # `'l'o` → `To`，这个形状不会是别的
    ws = [c for c in (other, other3) if isinstance(c, str)]
    if ELL_ENUM.match(w) and nxt[:1].isupper():
        # 编号位：要有证人读作 `1.` 才改，不靠上下文猜
        if any(re.fullmatch(r'\]?1\.', c) for c in ws):
            return '1.'
        return None
    if w == 'l' and prev and nxt and _wordish(prev) and _wordish(nxt):
        # 夹在两个词之间的孤立 `l`：两个证人那里都没有它，就是扫描斑点
        if ws and not any(_norm(c) == 'l' or c in ('1', 'l') for c in ws):
            return ''
    return None


def digit_repair(tok):
    """→ 换字后的词，或 None。原词在本书生僻（≤2 次），换出来的常见（≥8 次），
    且**只有一种换法**能换出常见词。三条同时成立才动手。"""
    m = DIGIT_IN_WORD.match(tok)
    if not m:
        return None
    # 序数与版本格式是原文就该有的：`3d`（第三）、`4to`（四开）、`8vo`（八开）、
    # `2dly`、`9th`。不列出来，`3d` 会被换成 `ed`（实测）。
    if re.fullmatch(r'\d+(?:st|nd|rd|d|th|to|vo|mo|dly|ly)\.?', tok):
        return None
    a, d, b, punct = m.groups()
    # 这里**不能**照 subst_repair 那样先卡「原词生僻」：_uni 的键是去掉
    # 非字母后的形状，`1s` 归一成 `s`，而单字母 `s` 在本书里到处都是
    # （缩写、书名），门槛当场把每一个待修的词都挡掉（实测一处都改不动）。
    # 含数字的词形本来就不是英文词，守卫交给下面「唯一 + 常见」两条。
    # 候选还得是**干净的词**：词典词或罗马数字。只看本书频次不行——语料里
    # 混着同类错字（`ts` / `lt` 这些形状自己就出现十几次），`1s` 的候选里
    # `is` 和 `ts` 双双过线，唯一性判据当场失效，一个也改不成。
    # ⚠️ 唯一性要按**归一化词形**算，不是按字符串算。`0` 的换法表里 o 和 O
    # 都在，`0f` 于是生出 `of` 与 `Of` 两个"不同"候选，唯一性判据当场失效，
    # 这个词一直没被修（实测）。
    out = {}
    for c in DIGIT_GLYPH.get(d, ''):
        cand = a + c + b
        n = _norm(cand)
        if _uni()[n] >= 8 and (n in DICT or re.fullmatch(r'[ivxlcm]+', n)):
            out.setdefault(n, cand)
    return list(out.values())[0] + punct if len(out) == 1 else None


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


# ── 第三证人：600 dpi + 中值滤波 + --psm 4 重扫（scripts/ocr_davenant_w3.py）─
# 前两份都是 tesseract 出的，重叠的那部分错两两相校无解——`have xot seen my
# face, Kc.` 就是标本：我们读 `xot` / `Kc.`，IA 读 `iiot` / `&,c.`。
# 换一套预处理与参数再读一遍，重叠面才断得开。
_w3 = {}
_w3tok = {}


def w3_lines(vol, page):
    if vol not in _w3:
        f = RAW / f'vol{vol}_w3.jsonl'
        _w3[vol] = {}
        if f.exists():
            for ln in f.open(encoding='utf-8'):
                r = json.loads(ln)
                _w3[vol][r['page']] = [re.sub(r'\s+', ' ', x).strip()
                                       for x in r['text'].splitlines() if x.strip()]
    return _w3[vol].get(page, [])


def w3_tokens(vol, page):
    key = (vol, page)
    if key not in _w3tok:
        _w3tok[key] = ' '.join(w3_lines(vol, page)).split()
    return _w3tok[key]


def _match(cands, toks, pt):
    """best_match 的公用体：先按行找最像的，退不到就在整页 token 串里截。"""
    if not cands:
        return None
    key = ' '.join(_norm(w) for w in toks)
    best = max(cands, key=lambda c: difflib.SequenceMatcher(
        None, key, ' '.join(_norm(w) for w in c.split())).ratio())
    r = difflib.SequenceMatcher(None, key, ' '.join(
        _norm(w) for w in best.split())).ratio()
    if r >= 0.55:
        return best.split()
    sm = difflib.SequenceMatcher(None, [_norm(w) for w in toks],
                                 [_norm(w) for w in pt], autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size]
    if not blocks or sum(b.size for b in blocks) < len(toks) * 0.6:
        return None
    lo = max(0, blocks[0].b - blocks[0].a)
    hi = min(len(pt), blocks[-1].b + blocks[-1].size + (len(toks) - blocks[-1].a))
    return pt[lo:hi]


def best_match3(vol, page, toks):
    return _match(w3_lines(vol, page), toks, w3_tokens(vol, page))


# ── 希腊文那一路（scripts/ocr_davenant_grc.py）────────────────────────────────
# 原书的希腊活字，主 OCR 用 eng+lat 读出来是拉丁乱码
# （`Tw wpoceuxn wpooxaprspeire` = Τῇ προσευχῇ προσκαρτερεῖτε），
# IA 那层同样是英文模型，两个证人一起花，三方相校救不了。
# 单跑一遍 `grc+eng` 取希腊字母那部分；英文照旧用主 OCR 的结果——
# grc 进主 OCR 会把小型大写页眉 `Ver. 3.` 读成 `Ρεν, 8.`（实测）。
GREEK_RE = re.compile(r'[\u0370-\u03ff\u1f00-\u1fff]')
_grc = {}
_grctok = {}
_grc2 = {}


def _load_grc(store, suffix, vol):
    if vol not in store:
        f = RAW / f'vol{vol}_grc{suffix}.jsonl'
        store[vol] = {}
        if f.exists():
            for ln in f.open(encoding='utf-8'):
                r = json.loads(ln)
                store[vol][r['page']] = [re.sub(r'\s+', ' ', x).strip()
                                         for x in r['text'].splitlines() if x.strip()]
    return store[vol]


def grc_lines(vol, page):
    return _load_grc(_grc, '', vol).get(page, [])


def grc_confirm(vol, page):
    """→ 佐证那一遍（另一套预处理与切分）在该页读出的希腊词集合。

    单遍的希腊读数不可靠：抽查 13 条，4 条与原书不符——`ἀντε` 原书是
    `ἀυτȣ`、`ἀγώνας` 原书是 `ἀγωνα`、`Ραμ` 那一行压根没有希腊文。印错的
    希腊文比留着拉丁乱码更坏：乱码一眼看得出是没读出来，错字看着像真的。
    所以改成**两遍一致才采信**，不一致的退回原样。
    """
    out = set()
    for l in _load_grc(_grc2, '2', vol).get(page, []):
        for w in l.split():
            core = re.sub(r'[^\u0370-\u03ff\u1f00-\u1fff]', '', w)
            if len(core) >= 2:
                out.add(core)
    return out


def grc_tokens(vol, page):
    key = (vol, page)
    if key not in _grctok:
        _grctok[key] = ' '.join(grc_lines(vol, page)).split()
    return _grctok[key]


def best_match_grc(vol, page, toks):
    return _match(grc_lines(vol, page), toks, grc_tokens(vol, page))


def _greekish(s):
    """希腊字母占到一半以上的 token 才算希腊词——grc 模型读英文时也会
    零星吐出一两个希腊字母，只判「含希腊字母」会把英文词一起换掉。"""
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and sum(1 for c in letters if GREEK_RE.match(c)) >= \
        max(2, len(letters) * 0.5)


def grc_pass(toks, greek, confirm=None):
    """整段替换希腊文。→ (新 token 串, [(原, 新, 理由)])

    两条路，都不去猜块内的一一对应：

    · **块内两边 token 数相同**：一对一是可靠的，只换其中确实是希腊词的那些
      （`'Tw wpoceuxn wpooxaprspeire.]` 对面是 `Tu apocevxn τπροσκαρτερεῖτε)`，
      只有第三个是希腊词，就只换第三个）
    · **token 数不同**：整块一起换，且要求对方**每一个**都是希腊词。逐词凑
      会错位——实测 `uel meds ToUs` 被凑成 `πρὸς τούς αλλους` 的错位版。

    ⚠️ 这一趟必须排在英文那几条规则**之后**。grc 模型读英文页时也会吐希腊
    字母：`xot`（原词 not）对面读出来是 `κοΐ`，先跑希腊文就把一个英文错字
    变成了希腊词（实测）。放在后面，`xot` 已经被三方词频裁判改回 `not`，
    是本书的词，这里就不会再碰它。
    """
    if not greek:
        return toks, []
    ok = confirm if confirm is not None else set()

    def backed(g):
        """这个希腊读数在佐证那一遍里有没有出现（允许 ≥0.8 的形近）。"""
        core = re.sub(r'[^\u0370-\u03ff\u1f00-\u1fff]', '', g)
        if len(core) < 2:
            return False
        return core in ok or any(
            difflib.SequenceMatcher(None, core, c).ratio() >= 0.8 for c in ok)
    ops = difflib.SequenceMatcher(None, [_norm(w) for w in toks],
                                  [_norm(w) for w in greek]).get_opcodes()
    out, log = [], []
    for tag, a1, a2, b1, b2 in ops:
        mine, theirs = toks[a1:a2], greek[b1:b2]
        if tag != 'replace' or not mine or not theirs:
            out.extend(mine)
            continue
        if len(mine) == len(theirs):
            for w, g in zip(mine, theirs):
                if (not _bookword(w) and _letters(w) >= 2 and _greekish(g)
                        and max(_letters(w), _letters(g)) >= 4 and backed(g)):
                    got = _keep_punct(w, w, g)
                    out.append(got)
                    log.append((w, got, '希腊文'))
                else:
                    out.append(w)
            continue
        if all(_letters(w) >= 2 and not _bookword(w) for w in mine) \
                and any(_letters(w) >= 3 for w in mine) \
                and all(_greekish(x) and backed(x) for x in theirs):
            got = _keep_punct(mine[0], mine[-1], *theirs)
            if got:
                out.append(got)
                log.append((' '.join(mine), got, '希腊文'))
                continue
        out.extend(mine)
    return out, log


def _keep_punct(first, last, *greek):
    """标点以**我方**为准，且只留结构性的那几个。

    `»páros` 的 `»` 是读花的字形不是标点；lemma 的收尾 `]` 被 grc 读成
    `)`，照抄过去 LEMMA_RE 就认不出这一条被注释的词句（实测）。
    """
    # 只留希腊字母、附加符号与词内的省字符。grc 那一遍偶尔把括号读进词里
    # （`πιϑανολογια.)]Ὶ`），只剥两端剥不掉词当中的那几个，落到产物里就成了
    # `ev πιϑανολογια.)]Ὶ.]`，LEMMA_RE 前缀里含 `]` 直接认不出，整条 lemma
    # 塌成正文（实测 1 条）。希腊词里本来就不该有拉丁字母和括号。
    core = re.sub(r'[^\u0370-\u03ff\u1f00-\u1fff\u0300-\u036f\s'
                  r'\u2019\u1fbd\u1ffe\'`]', '', ' '.join(greek))
    core = re.sub(r'\s+', ' ', core).strip()
    if not core:
        return ''
    # 标点按**黑名单**筛，不用白名单：白名单一收紧就把 lemma 的收尾
    # `|`（`]` 的 OCR 变体）和脚注符 `*` 一起丢了，那一条 lemma 整个塌成
    # 正文（实测 3 条）。真正要去掉的只有读花的字形那几个。
    junk = '\u00bb\u00ab\u00a2\u00a7~^\\`'
    head = ''.join(c for c in re.match(r'^\W*', first, re.U).group(0)
                   if c not in junk)
    tail = ''.join(c for c in re.search(r'\W*$', last, re.U).group(0)
                   if c not in junk)
    return head + core + tail


def _letters(s):
    return sum(1 for c in s if c.isalpha())


def _greekish(s):
    """希腊字母占到一半以上的 token 才算希腊词——grc 模型读英文时也会
    零星吐出一两个希腊字母，只判「含希腊字母」会把英文词一起换掉。"""
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and sum(1 for c in letters if GREEK_RE.match(c)) >= \
        max(2, len(letters) * 0.5)


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
    """→ [(我方词形, "词1 词2")]，供 build_split_table 统计用。

    两个证人都问：第三证人（600 dpi 重扫）与 IA 那一层的断词位置不同，
    只问一个会漏（`whichis` / `faithfulin` / `atall` / `givethanks`
    在 IA 那边也粘着，第三证人才排成两个 token）。
    """
    toks = text.split()
    if len(toks) < 2:
        return []
    out = []
    for cand in (best_match(vol, page, toks), best_match3(vol, page, toks)):
        if cand is None:
            continue
        sm = difflib.SequenceMatcher(None, [_norm(w) for w in toks],
                                     [_norm(w) for w in cand])
        out += [(toks[i], two) for i, two in _pairs(toks, cand, sm.get_opcodes())]
    return out


def _at(ops, theirs, i):
    """→ (对方在第 i 位的 token, 我这一个 token 对上的对方整段)。"""
    for tag, a1, a2, b1, b2 in ops:
        if not (a1 <= i < a2):
            continue
        if tag == 'equal':
            return theirs[b1 + (i - a1)], None
        if tag == 'delete':
            return None, None
        if tag == 'replace':
            seg, off = theirs[b1:b2], i - a1
            return (seg[off] if off < len(seg) else None,
                    list(seg) if a2 - a1 == 1 else None)
        break
    return '~', None


def _norm2(s):
    """归一但**保留数字**。索引与引经处的 token 本来就是数字与字母混排
    （`2i` 该是 `21`），按 _norm 归一后只剩一个 `i`，任何形近判据都失效。"""
    return re.sub(r'[^a-z0-9]', '', s.lower())


def _plausible(w, cand, digits=False):
    """两个 token 之间的形近守卫，几条证人规则共用。"""
    f = _norm2 if digits else _norm
    a, b = f(w), f(cand)
    if len(a) < 2 or len(b) < 2 or len(b) < len(a) * 0.85:
        return False                      # 变短 = 我方粘词、对方只对上半截
    if not digits and re.search(r'[\d^\\~`]', cand):
        return False                      # 对方自己就是乱码
    d = sum(1 for _ in difflib.ndiff(a, b) if _[0] != ' ')
    if len(a) <= 3 and len(b) <= 3:
        return d <= 2                     # 短 token 用编辑距离，比率没意义
    if difflib.SequenceMatcher(None, a, b).ratio() < 0.55:
        return False
    return d <= 4


def consensus(w, other, other3):
    """两个证人读到一处、且与我方不同 → 采信。排在确定性规则**之前**。

    `XXII. 2i,`（经文索引，原书 21）就是被顺序坑的：digit_repair 先手，
    按「换出来是罗马数字就采信」把 `2i` 改成了 `ii`；而第三证人与 grc 那
    两遍都明明白白读作 `21`。有证人说话时，不该让字形规则去猜。
    """
    cands = [c for c in (other, other3) if isinstance(c, str) and c != '~']
    if len(cands) != 2 or _norm2(cands[0]) != _norm2(cands[1]):
        return None
    got = cands[0]
    if _norm2(got) == _norm2(w):
        return None
    # 我方是不是词**不作为**否决理由：两个独立的 OCR 都读成另一个词时，
    # outlier 是我们。歌 3:8 的 `out of your south` 就是这样——`south` 是
    # 正经英文词，词典判据一挡就永远修不成 `mouth`（三个证人都读 mouth）。
    # 换成「我方这个形在本书里常见（>2 次）才不动」，19 世纪拼法
    # （shews / connexion / amongst）不会被碰：证人读到的也是它们本身。
    if _uni()[_norm(w)] > 2:
        return None
    if not (_bookword(got) or re.fullmatch(r'[\d.,;:]+', got)):
        return None
    if not _plausible(w, got, digits=True):
        return None
    tail = re.search(r'[.,;:!?]*$', w).group(0)
    if tail and not re.search(r'[.,;:!?]$', got):
        got += tail
    return got


# `&c.` 是本书最常见的缩写（正文里 243 处），`&` 这个字形 OCR 读得五花八门：
# `Kc.` `Sc.` `Xc.` `NC.`。它归一成字母只剩一个 `c`，长度守卫与词典判据
# 全都够不着，得单列一条。判据是证人：对方读出 `&c.` 的形状就采信。
ETC_MINE = re.compile(r'^[A-Za-z&][ce][.,]?$')
ETC_THEIRS = re.compile(r'^&\W?[ce][.,]?$')


def etc_repair(w, other, other3):
    if not ETC_MINE.match(w) or w.startswith('&'):
        return None
    if any(isinstance(c, str) and ETC_THEIRS.match(c) for c in (other, other3)):
        return '&c' + (w[-1] if w[-1] in '.,' else '.')
    return None


_INFL = None


def inflected():
    """DICT 的屈折形补集：系统词典（web2）是词头表，`winds` / `fills` /
    `lists` / `terrors` / `pays` / `paved` / `Tithes` / `fishes` 一个都不收。

    不补这一层，词频裁判会把这些**本来就对**的词"改正"掉——实测 56 处里
    有 13 处是这么错的：`winds and storms`→minds、`he fills up`→wills、
    `entered the lists`→lusts、`terrors of death`→errors、`paved the way`→saved、
    `Tithes of new broken-up lands`→Titles。它们在本书里都只出现一两次，
    「生僻」那道闸拦不住，只能靠词形本身认出来。
    """
    global _INFL
    if _INFL is None:
        _INFL = set()
        # 不规则动词形词典一个都不收，而它们正是这条规则最容易改坏的
        # （memory 里 `heard → beard` 那一条同类）：`overcame` 被改成
        # overcome、`bore`/`smote`/`clave` 一类同理。
        _INFL |= set("""
            was were been am is are being had has having did does done
            said made went gone came overcame became begun began sang sung
            sat stood spoke spoken broke broken chose chosen drove driven
            ate eaten fell fallen forgot forgotten froze frozen gave given
            grew grown knew known rose risen ran run saw seen shook shaken
            sank sunk stole stolen swore sworn took taken threw thrown
            wore worn wrote written bore borne bound bought brought built
            burnt caught clave cleft crept dealt dug dwelt fed felt fought
            found fled flung got held hung hurt kept knelt laid led left
            lent lost meant met paid put read rent said sent shed shone
            shot slept slid slung smote spent spun spread sprang sprung
            stood stuck stung struck strove striven sought sold sown swept
            swum swung taught told thought thrust trod trodden understood
            upheld wept won wound wrought slain slew lain lay bidden bade
            begotten begat forsook forsaken hewn shorn smitten stricken
            """.split())
        for w in DICT:
            if len(w) < 3:
                continue
            _INFL |= {w + 's', w + 'es', w + 'ed', w + 'd', w + 'ing',
                      w + 'er', w + 'est'}
            if w.endswith('y'):
                _INFL |= {w[:-1] + 'ies', w[:-1] + 'ied'}
            if w.endswith('e'):
                _INFL |= {w[:-1] + 'ing', w + 'd'}
    return _INFL


# 圣经书卷缩写：本书引经处处都是 `Mich. iv. 3` `Kom. vi. 12` 这种写法。
# 它们不在词典也不在语料常用词里，词频裁判会拿它们当错字改——实测把
# `Mich.`（弥迦书）改成了 `Much.`。这是 memory 里 `Joh → Job` 那一条的
# 同类，列表挡住，不靠上下文猜。
BIBLE_ABBR = {
    'gen', 'exod', 'exo', 'lev', 'num', 'deut', 'josh', 'judg', 'ruth',
    'sam', 'kings', 'chron', 'ezra', 'neh', 'esth', 'job', 'ps', 'psal',
    'psalm', 'prov', 'eccl', 'eccles', 'cant', 'isa', 'jer', 'lam', 'ezek',
    'dan', 'hos', 'joel', 'amos', 'obad', 'jon', 'mic', 'mich', 'nah',
    'hab', 'zeph', 'hag', 'zech', 'zach', 'mal', 'matt', 'mat', 'mark',
    'luke', 'luk', 'john', 'joh', 'acts', 'rom', 'cor', 'gal', 'ephes',
    'eph', 'phil', 'philip', 'col', 'coloss', 'thess', 'tim', 'tit',
    'philem', 'heb', 'jam', 'jac', 'pet', 'jude', 'rev', 'apoc',
    'wisd', 'ecclus', 'macc', 'tob', 'judith', 'baruch', 'esdr',
}


# 拉丁虚词：本书引拉丁成段成句，这些词在英文词典里一个都没有、在本书语料里
# 又未必过得了 8 次的门槛，正好落进词频裁判的射程——`propter`（引 Vulgate）
# 就被判成了 proper。与其把整行判成引文（门槛一松就误伤同行的真错字），
# 不如把这张表列出来：它是死数据，不是启发式。
LATIN_STOP = set("""
    propter quia quod enim autem ergo sed etiam tamen ideo nisi sicut unde
    inter apud ante post super sine cum per pro sub ad ex non nec vel aut
    atque itaque igitur quidem quoque tantum semper numquam nunquam ubi
    quando qui quae cuius cui quem quam quo qua quibus hoc haec hic hunc
    huius illa ille illud illum ipse ipsa ipsum idem eadem idest scilicet
    videlicet nempe utique ita sic tam quam magis minus valde omnis omnes
    omnia nihil nemo aliquis alius alia aliud multi multa pauci totus
    solus solum tantummodo verum vero nam namque siquidem quatenus
    prout secundum iuxta juxta erga contra circa infra intra ultra citra
    est sunt esse fuit fuerunt erat erant sit sint fieri factum
    dei deo deum domini domino dominum christi christo christum
    homo homines hominis hominum anima animae corpus corporis
    fides fidei gratia gratiae peccatum peccati lex legis
""".split())


def _wordish(w):
    """比 _bookword 再宽一档：加上词典词的屈折形与拉丁虚词。只给词频裁判用。"""
    b = _norm(w)
    return (_bookword(w) or b in LATIN_STOP
            or (len(b) >= 3 and b in inflected()))


def _inflection(a, b):
    """两个词形只差在**末尾**（`frees`/`freed`、`attains`/`attain`）时判 True。

    这不是 OCR 错，是单复数与时态的差别——词典缺屈折形，`attains` 查不到、
    被当成"不是词"，词频裁判就把它改成 `attain`。实测这一路一口气把
    frees→freed、overcomes→overcome、Scholastics→Scholastic、Saviour's→Saviour
    等三十来处改坏。OCR 的错是**字形替换**，位置随机；末位单独一处不同的，
    宁可不动。
    """
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return a[:-1] == b[:-1]           # 只差最后一个字母
    lo, hi = (a, b) if len(a) < len(b) else (b, a)
    return hi[:-1] == lo                  # 末尾多/少一个字母


def foreign_line(toks):
    """这一行是不是拉丁/希腊引文。

    本书引拉丁成段成句（`which is propter retributionem, and ad-`），
    拉丁词在英文词典里一个都查不到、在本书语料里也稀疏，正好落进词频裁判的
    射程，`propter` 就被改成了 proper（实测）。判据：同一行里另有 ≥2 个
    ≥4 字母的非英文词，就当引文行，整行不做裁判。
    """
    n = sum(1 for t in toks
            if len(_norm(t)) >= 4 and not _wordish(t) and not _uni()[_norm(t)] >= 8)
    return n >= 3


def trio_repair(w, prev, nxt, other, other3, edge=False):
    """两份新旧证人都读花时的第三条路。

    · **两个证人读到一处**（我方不是词、他俩是同一个词）：直接采信。
      `tlie`→the、`stauds`→stands、`sius.`→sins. 都是这么来的。
    · **三方各异**（`xot` / `iiot` / `iot`）：把三种读法各挪一个字母，
      凑出本书的常见词做候选，再交给二元词频裁判——`have not seen` 在
      本书里几十次，`have got/hot/lot seen` 一次也没有。裁判要求赢家
      至少 4 倍于输家，判不出就不动。
    """
    # ⚠️ 门槛必须是 _bookword 而不是 _isword。系统词典（web2）是词头表，
    # 复数与屈折形几乎都不收——`words` / `has` / `Apostles` / `sins` 查不到，
    # 一律被判成「不是词」，于是词频裁判把它们改成了 works / was / Apostle /
    # sons（实测这一条一口气改了 3425 处，全书最常见的词全被改坏）。
    # 再加一道「本书生僻（≤2 次）」：真错字是稀疏的，常用词轮不到这条规则。
    # 前一个 token 是孤零零一个字母时，这一个多半是**被切开的词的后半**
    # （`with the y ke of bondage` 里的 `ke` 是 yoke 的后半），裁判会把它
    # 判成 `be`，越改越错。
    if len(prev) == 1:
        return None
    # 断词的半截（`princi-` / `ples`）天生不是词、天生生僻，两道门槛都拦不住，
    # 词频裁判就把 `hea-`→`sea-`、`ples`→`plea`、`rity`→`city` 一路改了下去
    # （实测 251 处里过半是这个）。断词由后面的 dehyph 拼回，这里不碰：
    # 尾半截看 `-` 结尾，头半截看是不是**行首**那一个。
    # ⚠️ 行尾**不能**一并排除——用户圈出来的 `have xot` 里，`xot` 正好是
    # 行末最后一个 token，一刀切就把这个标本本身漏掉了。
    bg, uni = corpus()
    if edge or w.endswith('-'):
        return None
    # 通篇乱码的 token（多半是希腊文被 eng 模型读花：`9é£ao9e,`）不进这条。
    # 归一化会把非字母全丢掉，剩下的三两个字母跟任何短词都"形近"，
    # 于是 `9é£ao9e,` 被判成 `are,`（实测）。字母占比不到七成就不碰。
    if len(_norm(w)) < 0.7 * len(w.strip('.,;:!?()[]"\u2018\u2019\u201c\u201d')):
        return None
    # 门槛压到 2 太紧：`zn`（in）这类错字形状全书出现 4 次，永远修不成。
    # 但抬到 7 又太松，实测放进来 `propter`→proper（拉丁词）、`Jas.`→Was.、
    # `Chr.`→Cor.、`(Hor.`→(for. 四处错改。取 4，并把缩写另立一条挡住。
    if _wordish(w) or not re.search(r'[A-Za-z]', w) or uni[_norm(w)] > 4:
        return None
    # 缩写不碰：`Jas.`（雅各书）、`Chr.`（历代志）、`Hor.`（贺拉斯）、
    # `Hom.`（讲道篇）都是「大写开头 + ≤4 字母 + 句点」，词典里没有、本书里
    # 又稀疏，正好落进这条规则的射程。有证人背书的那几条（`Kom.`→Rom.）
    # 走的是「两证人一致」，不受这里影响。
    if re.fullmatch(r'[A-Z][A-Za-z]{0,3}\.', w.strip('([\u201c\u2018\'"')):
        return None
    if w.endswith('.') and _norm(w) in BIBLE_ABBR:
        return None
    # 带撇号或连字符的 token 不进这条：`ome's` / `PAUI's` 的正解是 `one's`
    # / `PAUL'S`，`haud-writing` 的正解是 `hand-writing`，而候选池是按
    # 纯字母生成的，凑出来的只能是 `ones` / `Pauls` / `handwriting`——
    # 把一个错换成另一个错。撇号那一路另有 apos_repair。
    if "'" in w or '\u2019' in w or '-' in w.strip('-'):
        return None
    cands = [c for c in (other, other3) if isinstance(c, str) and c != '~']
    if len(cands) == 2 and _norm(cands[0]) == _norm(cands[1]) \
            and _bookword(cands[0]) and _norm(cands[0]) != _norm(w) \
            and _plausible(w, cands[0]):
        # 尾标点以**我方**为准：对方那一遍常把行末的冒号句号漏掉，
        # 照抄过来就把 `augels:` 改成了 `angels`，标点没了（实测）
        tail = re.search(r'[.,;:!?]*$', w).group(0)
        got = cands[0]
        if tail and not re.search(r'[.,;:!?]$', got):
            got += tail
        return got, '两证人一致'
    pool = set()
    for src in [w] + cands:
        b = _norm(src)
        if not 2 <= len(b) <= 14:
            continue
        for k in range(len(b)):
            for ch in 'abcdefghijklmnopqrstuvwxyz':
                pool.add(b[:k] + ch + b[k + 1:])          # 换一个字母
            pool.add(b[:k] + b[k + 1:])                   # 删一个字母
    # 词典缺屈折形，只认 DICT 会把 `Scriptnres.` 这种复数错字堵死；
    # 放一条「本书里出现 ≥20 次」的通道补上，屈折翻转另有 _inflection 拦。
    pool = {c for c in pool
            if (c in DICT or c in inflected() or uni[c] >= 20) and uni[c] >= 8
            and _plausible(w, c) and not _inflection(_norm(w), c)}
    pool.discard(_norm(w))
    if not pool:
        return None
    scored = sorted(((bg[(prev, c)] + bg[(c, nxt)], c) for c in pool),
                    reverse=True)
    if len(scored) == 1 or (scored[0][0] >= 8
                            and scored[0][0] >= max(4 * scored[1][0], 8)):
        best = scored[0]
        if best[0] >= 8:
            # 大小写与尾标点照原样带回
            head = re.match(r'^\W*', w).group(0)
            tail = re.search(r'\W*$', w).group(0)
            cand = best[1].capitalize() if w[:1].isupper() else best[1]
            return head + cand + tail, '三方各异·词频裁判'
    return None


# 确定性规则（字形回填，不依赖行对齐）与证人规则（依赖行对齐）在索引里
# 风险完全不同：前者只在词内部换字形，后者会因为对齐滑到隔壁条目而整词换掉。
DETERMINISTIC = {'词内数字', '数字位字形', '撇号', '&c.', '希腊文'}


def _strict_ok(old, new, why=''):
    """索引那一路的收窄闸：只放行「同一个词内部的字形错」。

    索引的版面对不上行——两栏、点线引导、条目短——证人的行对齐会滑到
    **隔壁条目**上去，于是整词被换掉：`Abelard …435` 被换成 `Bernard …435`、
    页码 `304`→`354`、`66, 67`→`67, 67`（实测）。正文里这种滑动会被上下文
    兜住，索引里没有上下文可兜。所以这里只认三条都成立的改动：
    首字母不变、长度差 ≤1、且不是纯数字的 token。
    """
    if why in DETERMINISTIC:
        # 字形回填照放（`1s`→is、`7n`→in），只有一条例外：换出来是**纯罗马
        # 数字**的不要。索引里数字与罗马数字混排，`XXII. 2i,`（原书 21）
        # 会被按「换出来是罗马数字就采信」改成 `ii`（实测）。
        return not re.fullmatch(r'[ivxlcdm]+', _norm2(new))
    if ' ' in new:
        # 拆词照放（`in usein`→`in use in`、`asa`→`as a`、`toa`→`to a`），
        # 但**罗马数字不拆**——`XXVIII.` 被拆成 `XXV III.`（实测），一拆就废。
        if re.fullmatch(r'[ivxlcdm]+', _norm2(old)):
            return False
        return all(_bookword(x) or x.strip('.,;:') in ('a', 'I')
                   for x in new.split())
    a, b = _norm2(old), _norm2(new)
    if not a or not b or a[0] != b[0] or abs(len(a) - len(b)) > 1:
        return False
    # 纯数字之间不许互改（页码 `304`→`354`、`66`→`67` 都是行对齐滑到隔壁
    # 条目上去的）；但 `2i`→`21` 这种「字母位上本该是数字」要放行。
    return not (a.isdigit() and b.isdigit())


def fix_line(vol, page, text, strict=False):
    """→ (改后的文本, [(原, 新, 理由), …])。判不了就原样返回。

    strict=True 时只放行同词内部的字形错，见 _strict_ok（索引专用）。"""
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
        # ⚠️ 对不上行**不等于**什么都不能做。digit_repair / numeral_repair
        # 这几条不依赖对方，靠的是字形表加本书语料；早退一挡，`1s` `5e` `1i`
        # 这些在对不上的行里一处也修不成（索引那一路整段整段对不上，实测
        # 残留十来处）。只把依赖对方的那几条跳过。
        out, log = [], []
        for w in toks:
            f = digit_repair(w) or numeral_repair(vol, page, w, None)
            if f and (not strict or _strict_ok(w, f, '词内数字')):
                out.append(f)
                log.append((w, f, '词内数字'))
            elif SPECK.match(w):
                log.append((w, '', '斑点'))
            else:
                out.append(w)
        toks, glog = grc_pass(out, best_match_grc(vol, page, out))
        log += glog
        return (' '.join(toks), log) if log else (text, [])

    sm = difflib.SequenceMatcher(None, [_norm(w) for w in toks],
                                 [_norm(w) for w in theirs])
    ops = sm.get_opcodes()
    pair2 = dict(_pairs(toks, theirs, ops))
    third = best_match3(vol, page, toks)
    ops3 = difflib.SequenceMatcher(
        None, [_norm(w) for w in toks],
        [_norm(w) for w in third]).get_opcodes() if third else None
    out, log = list(toks), []
    for i, w in enumerate(toks):
        other, oseg = _at(ops, theirs, i)
        other3 = _at(ops3, third, i)[0] if ops3 else None
        # 我方把两个词读粘了：对方那边把它排成**两个** token，直接采信。
        # 这是证据不是猜——`asa memorial` 对面是 `as a memorial`。
        # 不靠「能拆成两个词典词」那种判据：`becometh` / `sumus` / `Johnson`
        # 一样能拆，实测 287 种候选里过半是这种误判。
        for _why, _fix in (('l→1', ell_repair(
                               w, toks[i - 1] if i else '',
                               toks[i + 1] if i + 1 < len(toks) else '',
                               other, other3)),
                           ('两证人一致', consensus(w, other, other3)),
                           ('撇号', apos_repair(w, other, oseg)),
                           ('词内数字', digit_repair(w)),
                           ('数字位字形', numeral_repair(vol, page, w, other)),
                           ('&c.', etc_repair(w, other, other3))):
            if _fix is not None and _fix != w:
                out[i] = _fix or None     # '' = 删掉这个 token（斑点）
                log.append((w, _fix, _why))
                break
        else:
            _fix = None
        if _fix is not None and _fix != w:
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
            trio = trio_repair(w, _norm(toks[i - 1]) if i else '',
                               _norm(toks[i + 1]) if i + 1 < len(toks) else '',
                               other, other3,
                               edge=(i == 0 or foreign_line(toks)))
            if trio:
                out[i], why = trio
                log.append((w, out[i], why))
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
    if strict:
        log2 = []
        for i, (o, n) in enumerate(zip(toks, out)):
            if n is None or n == o:
                continue
            why = next((w for oo, nn, w in log if oo == o and nn == n), '')
            if _strict_ok(o, n, why):
                log2.append((o, n, why))
                continue
            # 被证人规则挡下来的，再给确定性规则一次机会：同一处改动常常
            # 两条规则都能给出（`1s`→is 既是「两证人一致」也是「词内数字」），
            # 证人那一路在索引里不可靠，字形那一路可靠。
            alt = digit_repair(o) or numeral_repair(vol, page, o, None)
            if alt and _strict_ok(o, alt, '词内数字'):
                out[i] = alt
                log2.append((o, alt, '词内数字'))
            else:
                out[i] = o
        log = log2
    kept = [x for x in out if x is not None]
    out, glog = grc_pass(kept, best_match_grc(vol, page, kept),
                         grc_confirm(vol, page))
    log += glog
    if not log:
        return text, []
    return ' '.join(out), log


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
