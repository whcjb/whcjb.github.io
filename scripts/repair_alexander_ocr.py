#!/usr/bin/env python3
"""规则 + 判词典的 OCR 修复。只碰「不是真词」的 token。

这份扫描件的错误高度成套，几乎全是**连字与相似字形**被拆错：
    li → U / H / h        appUed  Hterally  hke
    ll → U                aU  wiU
    ff → fi / flf         efiect  scoflfers
    rn ↔ m                modem(modern)  scomers(scorners)
    w  → iv / vn / ui     ivith  vnth  uill
    r  → i'               fii'st  wi'iters
所以修复方式不是逐条硬编码，而是给出这套字形替换规则，穷举 1–2 次替换的候选，
**只接受落进词典的结果**。落不进去的一律原样保留并记账，交给第二证人比对
（adjudicate_alexander_ocr.py）——绝不猜。

真词错误（modem/bom 这种「改错了仍是英文词」）规则抓不到，走 REAL_WORD_FIX，
每一条都必须在 1850 三卷本上核对过才准加。
"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_lexicon import build, is_word

ROOT = Path(__file__).resolve().parent.parent

LIT_STAR = ''      # extract 留下的「字面星号待判」哨兵

RULES = [
    # 连字 li 被拆成单个字形 —— 本扫描件最大的一类错
    ('u', 'li'), ('h', 'li'), ('li', 'h'), ('tli', 'th'), ('tl', 'th'),
    # 双 l 读成 U：aU → all
    ('u', 'll'),
    # ff / fl 连字
    ('fi', 'ff'), ('fi', 'fl'), ('flf', 'ff'), ("fi'", 'ff'),
    # rn ↔ m 互串
    ('rn', 'm'), ('m', 'rn'), ('rri', 'm'), ('hn', 'lm'),
    # w 被拆成两个字母
    ('iv', 'w'), ('vn', 'w'), ('ui', 'w'), ('tv', 'w'), ('vv', 'w'),
    ('xv', 'w'), ('xo', 'w'), ('lo', 'w'), ('to', 'w'),
    # r 被读成 i 加撇
    ("i'", 'r'), ('fir', 'fr'), ('fi\"', 'ff'),
    # 字母被读成数字：19 世纪铅字的 n/e/o/l 常被读成 7i / 6 / 0 / 1
    ('7i', 'n'), ('7z', 'n'), ('7l', 'n'), ('7', 'n'), ('2i', 'u'),
    ('6', 'e'), ('6', 'o'), ('0', 'o'), ('1', 'l'), ('1', 'i'), ('5', 's'),
    ('8', 'b'), ('9', 'g'), ('4', 'a'),
    # 字面星号：多半是 `r`（fi*om→from、ai*e→are、figui*e→figure），
    # 也可能纯属噪点。两种都试，落不进词典就不动。
    ('i' + LIT_STAR, 'r'), (LIT_STAR, 'r'), (LIT_STAR, ''), (LIT_STAR, 'c'),
    # wi / wn / un 整组串位
    ('vn', 'wi'), ('un', 'wi'), ('vm', 'wn'), ('im', 'un'), ('nn', 'rm'),
    ('h', 'b'), ('ji', 'h'), ('vp', 'up'), ('j', 'f'),
]

# 只在词首生效的规则。词首的 w 常被整个读成一个 u/v/n（"will" → "uill"），
# 但把这条放进通用规则会去动 sound/under 这类词的中段，风险不对等。
HEAD_RULES = [('u', 'w'), ('v', 'w'), ('n', 'w'), ('U', 'W')]

# 规则抓不到的真词错误。每条都对着 1850 三卷本核过。
PSALMS_REAL_WORD = {
    'modem': 'modern',
    'bom': 'born',
    'tum': 'turn',
    'tums': 'turns',
    'bums': 'burns',
    'moming': 'morning',
    'evemng': 'evening',
    'nnder': 'under',
    'arid': 'and',        # 只在孤立出现时替换，见 _fix_arid
}

# 语料自证闸（见 corpus_vocab）会连带否掉一批**确实正确**的低频修复——
# 目标词全书只出现这一次，自然没有旁证。逐条看过上下文确认后放行。
PSALMS_MANUAL = {
    'hmbs': 'limbs', 'htigious': 'litigious', 'anghcan': 'Anglican',
    'accompuces': 'accomplices', 'accompushes': 'accomplishes',
    'ampufies': 'amplifies', 'bubbhng': 'bubbling', 'demohshed': 'demolished',
    "difi'erently": 'differently', 'draiver': 'drawer', 'duphcity': 'duplicity',
    "efi'orts": 'efforts', 'eflforts': 'efforts', 'elupses': 'ellipses',
    'fehcitation': 'felicitation', 'ghmpse': 'glimpse', 'hbations': 'libations',
    'homebom': 'homeborn', 'howhng': 'howling', 'hver': 'liver',
    'immobiuty': 'immobility', "imploi'ing": 'imploring',
    'inexphcable': 'inexplicable', 'instabiuty': 'instability',
    'ivrest': 'wrest', 'morauty': 'morality', 'overpotvered': 'overpowered',
    'pohtic': 'politic', 'pohtically': 'politically', 'pubucity': 'publicity',
    'reneivest': 'renewest', 'saivest': 'sawest', 'scomers': 'scorners',
    'simphfied': 'simplified', 'supercihous': 'supercilious',
    'totauty': 'totality', 'unukeness': 'unlikeness',
    # 词首 w 整个被读丢，语料自证也救不回来的几例
    # 证人（1850）在同一处作 learned，且这是斜体译文——Ps. 2:10 的
    # 「你们要受管教」，紧接着才是 be admonished。"be warned, be admonished"
    # 语义重复，"be learned, be admonished" 才是管教与警戒两面。
    'uarued': 'learned', 'vath': 'with', 'vrith': 'with', 'tuill': 'will',
    'tuatchers': 'watchers', 'knouest': 'knowest', 'suul': 'soul',
    'unkss': 'unless', 'humue': 'humble', "i'he": 'The', 'suftered': 'suffered',
    'oji': 'on',         # "literally *on thee, on (account of) thee*"
    'devoui': 'devour', 'soid': 'soul', 'aheady': 'already', 'grod': 'God',
    'wtiter': 'writer', 'tjie': 'The', 'rahah': 'Rahab', 'afibrded': 'afforded',
    'fonn': 'form', 'noim': 'noun',
    # ↓ 第二证人复核 repair 全量改动时抓出来的：字形规则把这些残串改成了
    #   **另一个真词**，判词闸和后面的判读器于是全都看不见了。放进这张表
    #   （它排在规则之前）从源头掐掉。每条都对着 1850 三卷本按位置核过。
    'ojf': 'of',           # "garments of holiness"（Lev. xvi. 4），规则作 off
    'uood': 'blood',       # Ps. 105:29 "turned their waters to blood"，规则作 wood
    'turong': 'wrong',     # "do not practise wrong"，规则作 throng
    'thom': 'them',        # "The *and* between them"，规则作 thorn
    'bome': 'some',        # "as some interpreters suppose"，规则作 Borne
    'nore': 'more',        # "gladness more than"，规则作 wore
    # w 形翻案那条要求 w 拼法在书里出现 ≥5 次且是 iv 拼法的 3 倍，
    # 这三个够不着。各自的旁证：
    'ivinning': 'winning',  # 后面紧跟着自证的注解 "(i. e. when he wins)"
    'ivhoso': 'whoso',      # 证人作 whoso；钦定本 Ps. 50:23 "Whoso offereth praise"
    'ivays': 'ways',        # "*His ways are firm*"，Ps. 10:5

    # ↓ 两份 OCR 在**同一处**都读崩了，拿一份崩的改另一份崩的没有意义
    #   （PDF 的文本层也是同一份 ABBYY OCR，同样不算第三方）。
    #   这一批是渲染 1864 扫描件的**页面影像**逐处看出来的，
    #   scripts/crop_alexander_page.py 按书页页码 + 页眉标定的偏移裁图。
    'icine': 'wine',              # "their corn and their wine abounded" (Ps. 4)
    'luisely': 'wisely',          # "acting wisely towards the poor" (Ps. 41)
    'hecatise': 'because',        # "I do not depart, because thou guidest me" (119)
    'hreaketh': 'breaketh',       # "My soul breaketh with longing" (119)
    'hestouments': 'bestowments', # "all his bestowments upon me" (116)
    'yerh': 'verb',               # "The twofold use of the verb find" (116)
    'histoiy': 'history',         # "found also in the history, Gen. l. 7" (105)
    'forgeffulness': 'forgetfulness',   # "the land of forgetfulness" (88)
    "u'onders": 'wonders',        # "the words of thy wonders" (145)
    'icarnesf': 'warnest',        # "Happy the man whom thou warnest, Jah" (94)
    'shadoio': 'shadow',          # "the mountains (with) its shadow" (80)
    'huiterings': 'butterings',   # "Smooth are the butterings of his mouth" (55)
    'oreh': 'Oreb',               # "like Oreb and like Zeeb" (83)
    'natiom': 'nations',          # "Hear this, all the nations" (49)
    'throun': 'Thrown',           # "Thrown down among the rocks" (141)
    'afihiction': 'affliction',   # "bound in affliction and iron" (107)
    'sufterings': 'sufferings',   # "relieve the sufferings of his creatures" (114)
    "sufl'erings": 'sufferings',  # 同上一类，ff 连字读成 fl（107）
    # 拉丁文与专名，词典查不到，判词闸只能当噪点否掉，也靠影像定
    'tnajestaticus': 'majestaticus',   # "pluralis majestaticus" (11)
    'salvvcmfac': 'salvum fac',        # "Domine salvum fac regem" (20)，本是两个词
    'contriium': 'contritum',          # "the Latin contritum" (51)
    'personce': 'person\u00e6',         # "enallage personæ" (52)，原书是 æ 合字
    'trofundis': 'Profundis',          # "De Profundis, Miserere…" (57)
    'sohnnitates': 'solennitates',     # "Jer. solennitates" (74)
    'idumsea': 'Idum\u00e6a',           # "Idumæa and Arabia Petræa" (75)，同为 æ
    'petraea': 'Petr\u00e6a',           # 同上一句，原书亦是 æ 合字
    # 证人在这里读成 fames，是错的；影像上印的是 flames
    # "The word translated *flames* occurs above in Ps. lxxvi. 4 (3)" (78)
    'yzames': 'flames',
    'halleujah': 'Hallelujah',    # "corresponding to the *Hallelujah* at the beginning"
    'xu': 'xli',                  # "Ps. xx. 3 (2), xli. 4 (3), xciv."——罗马数字里 li 读成 U
    'xh': 'xli',                  # "Ps. ii. 10, xiv. 2, xli. 2 (1)"——同上，li 读成 H
    'aud': 'and',                 # 全书仅一处，"…to Jehovah, and thou didst take away"
    'pretection': 'protection',   # "a place of honour but of protection"
    'appucationof': 'application of',   # 粘连，证人在这一处读崩，按上下文定
    'difibrent': 'different',           # 证人在这一处也读崩了，按上下文定
    'amd': 'and',                       # 证人这一处读成 aTid，也是残串
    'wiejced': 'wicked',                # "the face of the wicked"，证人读成 tricked
    # 罗马数字：l 被读成 k；证人给的 Ixix/Ixxi 首字母又是大写 I，两头都不能直接用
    'kix': 'lxix', 'kxi': 'lxxi', 'kvi': 'lxvi',
    # 'Ji' 被读成 'l'/'h' 之后仍是英文词，规则挡不住，逐个核过上下文：
    'jire': 'fire',      # "as wax is melted before fire"
    'jiock': 'flock',    # "The sheep (or flock) of thy pasture"
    'tjion': 'Thou',     # "Thou wilt not hear"
    # 一个 token 里叠了两三处误识，字形规则一步两步都够不着，逐条核过：
    'iviiiys': 'wings', 'ivllh': 'with', 'iviih': 'with', 'theji': 'then',
    'ivalhing': 'walking', 'ftdl': 'full', 'woas': 'works',
    'certaiuty': 'certainty', 'certaiu': 'certain', 'miessential': 'unessential',
    'distinguised': 'distinguished', 'expositicai': 'exposition', 'tbe': 'the',
    'recuitence': 'recurrence', 'kabbins': 'Rabbins', 'pxirpose': 'purpose',
    'fibrst': 'first',
}

# token 正则切不开的错：词中混进数字、或两词被粘在一起
PSALMS_PRE = [
    (r'\bs7nokes\b', 'smokes'),
    (r'\bthatver\b', 'that ver'),
    (r'\b(on|in|above|below)Ps\.', r'\1 Ps.'),
    (r'my soul lire\b', 'my soul live'),
    # `y` 被读成 `^'`：t^'pes → types
    (r"\^'", 'y'),
    (r"v,'hom", 'whom'),   # "to set whom for princes"（Isa. liii. 10 引文）
    (r'\bThon wilt\b', 'Thou wilt'),
    # `Jie` 在两处的真值不同（一处 the、一处 be），只能带上下文改
    (r'represents Jie king', 'represents the king'),
    # `be` 被读成 `he`，改完仍是真词，规则与判词闸都拦不住，只能带上下文改
    (r'\*To he wise\*', '*To be wise*'),
    # 同一个 obhgation，ch20 是 oblation（两种祭物），ch40 是 obligation
    # （incumbent obligation），只能按上下文分开
    (r'two species of obhgation', 'two species of oblation'),
    # 空格位置上落了个 `^`。全书 642 个 `^` 几乎都是希伯来活字读崩的残渣，
    # 不能一概换成空格，只改这一处两侧都成词的。
    (r'by taking, as\^the central', 'by taking, as the central'),
    (r'though there he hut a handful', 'though there be but a handful'),
    # ff 连字读成 fi，中间还落了个引号：ofi"ering
    (r'ofi"ering', 'offering'),
    (r'\bthi\)igs\b', 'things'),
    (r'the Psalms op David', 'the Psalms of David'),
    # 最后一条漏网页眉：这一处没带页码，且被并进了正文段落中间
    (r'my\* no \*Psalm 22:15,16 heart', 'my* no *heart'),
]

# ── 以赛亚书 ────────────────────────────────────────────────
# 每一条都对着扫描页或第二证人核过，不核不加。
ISAIAH_MANUAL = {}
ISAIAH_REAL_WORD = {
    'modem': 'modern', 'bom': 'born', 'tum': 'turn', 'moming': 'morning',
}
ISAIAH_PRE = [
    # 卷一第 1 章开头的小型大写被整块读崩（书页 1，全书唯一一处章首误识）。
    # 走 PRE_FIX 而不是 MANUAL：串里有 `£`，token 正则切不出完整的词。
    (r'THE fteJ£n of this chapter', 'THE design of this chapter'),
    # 斜体大写 I 被读成斜杠：`V. 3. / Jehovah (am) keeping her`。
    # 只改**独立成词**的斜杠，不动 and/or 之间的分隔符或分数。
    (r'(?<=[\s*(])/(?=[\s,.;:)])', 'I'),
    (r'\b(on|in|above|below)Ps\.', r'\1 Ps.'),
    # 词尾字母被读成括号：`genera]`(general) `unit}'`(unity)。
    # token 正则切不出这种串，只能在文本层改。
    (r'\bgenera\]', 'general'),
    # 词中间冒出一个句点，把词劈成两截（`A.nd` = And）。判读器只看得见后半截
    # 那个 token，改完会拼成 `A.and` 这种更糟的东西，所以必须在它之前修掉。
    (r'\bA\.nd\b', 'And'),
    (r'\bA\.nnahme\b', 'Annahme'),
    (r'\bof a\.child born\b', 'of a child born'),
    (r"\bone's\.self\b", "one's self"),
    (r'\bnot yet J\.ave called\b', 'not yet have called'),
    (r'\bcontrary to u\.sa\^e\b', 'contrary to usage'),
    # 德文变音符：页面上印的是 ü，OCR 一律读成 ii。翻过书页影像核实
    # （书页 405 的 Rosenmüller 清清楚楚带两点），还原属于「复现原文」，
    # 不是改写。只收反复出现、能确认的几个人名与常用词。
    (r'\bRosenmiiller\b', 'Rosenmüller'),
    (r'\bFiirst\b', 'Fürst'),
    (r'\bRiickert\b', 'Rückert'),
    (r'\biiber\b', 'über'),
    (r'\bStiitze\b', 'Stütze'),
    (r'\bgefliigelter\b', 'geflügelter'),
    # 人名拼错，证人与页面一致
    (r'\bVilringa\b', 'Vitringa'),
    (r'\bShalmeneser\b', 'Shalmaneser'),
    (r"\bunit\}'", 'unity'),
]

BOOKS = {
    # short_len：多短的 token 才需要把语料门槛从「出现过」抬到 20 次。
    # 诗篇必须是 3。抬到 4 会连带杀掉四字母的 li→U/h 整类——faUs/waUs/
    # sohd/ahke/Uved/Uves/cxhi/rohe，正是这本扫描件最大的一类错，而它们的
    # 目标词在书里只出现 4–11 次，过不了 20 的门槛。反过来，要挡的
    # coun→colin、unum→linum 词频本来就是 0，「出现过」这一条已经够了。
    'psalms': dict(src=ROOT / 'alexander_raw/psalms/en_chapters',
                   log=ROOT / 'logs/alexander_ocr_repair.tsv',
                   manual=PSALMS_MANUAL, real=PSALMS_REAL_WORD, pre=PSALMS_PRE,
                   short_len=3),
    'isaiah': dict(src=ROOT / 'alexander_raw/isaiah/en_chapters',
                   log=ROOT / 'logs/alexander_isaiah_ocr_repair.tsv',
                   manual=ISAIAH_MANUAL, real=ISAIAH_REAL_WORD, pre=ISAIAH_PRE,
                   short_len=4),
}

# 私用区哨兵必须靠拼接进正则：写在 r"..." 里 `\ue002` 不会被解释成那个字符，
# 而是反斜杠+u+e+0+0+2 六个字面字符，字符类里根本不含哨兵，token 会在哨兵处断开
# ——`fi<哨兵>om` 被切成 `fi` 和 `om`，所有针对哨兵的规则全部落空（踩过）。
# 词内允许数字：`Upo7z`(Upon) `judgme7it`(judgment) `th6`(the) 这类把字母读成
# 数字的错，不把数字纳入 token 就永远切不出完整的词，规则一条也用不上。
# 必须以字母开头（`1846`、`23` 这类纯数字不是词），但**可以以数字结尾**
# ——`th6` 就是 `the`，不许结尾带数字的话只切出 `th`，规则一条也用不上。
TOKEN = re.compile('[A-Za-z' + LIT_STAR + "][A-Za-z0-9" + LIT_STAR + "'’]*")


def _apply_once(w):
    out = set()
    for a, b in HEAD_RULES:
        if w.startswith(a):
            out.add(b + w[len(a):])
    for a, b in RULES:
        start = 0
        while True:
            i = w.find(a, start)
            if i < 0:
                break
            out.add(w[:i] + b + w[i + len(a):])
            start = i + 1
    return out


def candidates(w, lex, depth=2):
    # 收解用 is_word 而不是 `in lex`：罗马数字（xlix、lxxviii）不在词表里，
    # 用 `in lex` 收不到，`xHx → xlix` 这类citation 里的错永远修不掉。
    seen = {w}
    frontier = {w}
    good = []
    for _ in range(depth):
        nxt = set()
        for x in frontier:
            for y in _apply_once(x):
                if y in seen:
                    continue
                seen.add(y)
                nxt.add(y)
                if is_word(y, lex):
                    good.append(y)
        if good:
            return good           # 就近取解：一步能修好就不做两步
        frontier = nxt
    return good


# 韦氏词表收了、但在这本书里绝不可能是真词的两字母残片：
# `aU`(all) `iU`(ill) 这类被判成词就再也修不掉。
NOT_WORDS = {'au', 'ai', 'oi', 'iu', 'ia', 'ae', 'ea', 'oe', 'ui'}


W_PREFIXES = ('iv', 'tv', 'vn', 'ui', 'vv', 'xo', 'lo', 'to')


def _w_misread(low, vocab):
    for pre in W_PREFIXES:
        if low.startswith(pre) and len(low) > len(pre):
            alt = 'w' + low[len(pre):]
            if vocab.get(alt, 0) >= 5 and vocab.get(alt, 0) > vocab.get(low, 0) * 3:
                return alt
    return None


def restore_case(src, dst):
    """只在首字母**没被规则动过**时才还原大写。

    反例：`Uterally` 的大写 U 是 `li` 连字被误读的产物，不是词首大写。
    照搬大小写会得到 `Literally`，把一个 OCR 错误换成另一个。
    """
    if src[:1].lower() == dst[:1].lower():
        if src.isupper() and len(src) > 1:
            return dst.upper()
        if src[:1].isupper():
            return dst[:1].upper() + dst[1:]
    return dst


def corpus_vocab(lex, src):
    """全书里**本来就正确**的词表。修复候选必须在这张表里出现过。

    这是最后一道闸：规则 + 词典能把 `hang` 改成 `liang`、`lieth` 改成 `heth`
    ——两个目标词都在韦氏词表里，词典拦不住。但它们在这本书里一次都没正确
    出现过，而 `literally`/`applied`/`with` 出现过几十次。「候选必须是本书
    确实用过的词」把这类换错一网打尽。"""
    vocab = Counter()
    for path in sorted(src.glob('*.md')):
        text = re.sub(r'<!--.*?-->', '', path.read_text(encoding='utf-8'))
        for w in TOKEN.findall(text):
            if is_word(w, lex):
                vocab[w.lower()] += 1
    return vocab


# 断词处的连字符 OCR 时有时无：`incon-` 有，`charac`（接下一行 `ter`）没有。
# 有连字符的在抽取阶段就接好了，没有的只能靠词典在这里补。
# 后半用**前瞻**而不是捕获：正则替换是不重叠扫描的，若把后半也吃掉，
# `the con struction` 会先配成 (the, con)（两边都是词，不动）然后从
# `struction` 之后接着扫，`con struction` 这一对**永远轮不到**（踩过）。
SPLIT_WORD = re.compile(r'\b([A-Za-z]{2,})[ ](?=([a-z]{2,})\b)')


def rejoin_split_words(text, lex, vocab):
    """把行末断词漏掉连字符造成的 `charac ter` 拼回 `character`。

    只在**至少一半不是词**时才拼：两半都是词的（`to be`、`may be`、
    19 世纪本来就分写的 `any thing`）一律不动——那里没有任何证据说明
    原书是一个词，拼起来就是篡改。
    """
    def repl(m):
        a, b = m.group(1), m.group(2)
        if is_word(a, lex) and is_word(b, lex):
            return m.group(0)
        j = a + b
        # 拼出来的词还必须**在本书别处正确出现过**：只靠词典会把
        # `to co-operate` 拼成 `toco`（toco 恰好也在韦氏词表里）。
        if is_word(j, lex) and vocab.get(j.lower(), 0) >= 1:
            return a          # 只吃掉空格，后半留在原处等下一轮配对
        return m.group(0)
    return SPLIT_WORD.sub(repl, text)


def join_across_star(text, lex):
    """`com* posed` / `cir* umjacent`：星号噪点顺带把一个词劈成两半。

    只有**拼回去正好是个词**时才合并，否则原样不动——不能因为「看着像断词」
    就把两个词粘起来。
    """
    def repl(m):
        joined = m.group(1) + m.group(2)
        if is_word(joined, lex):
            return joined
        if is_word(m.group(1) + 'c' + m.group(2), lex):   # 星号本身是个 c
            return m.group(1) + 'c' + m.group(2)
        return m.group(0)
    return re.sub(r'([A-Za-z]{2,})' + LIT_STAR + r'\s+([A-Za-z]{2,})', repl, text)


def settle_stars(text, lex):
    """规则救不回来的字面星号，按它在句子里的位置收尾。

    看过全部残留后归纳出的四种情形：
      `generation* The idea`   句号被读成星号 → 还原句号（后接大写）
      `for thy* mercy`         纯噪点          → 删掉（后接小写或数字）
      `of*domestic`            噪点顺带吞了空格 → 还原空格（两侧都成词）
      `(*nS)` `7J*1`           希伯来活字残渣   → 转义 `\*` 原样保留

    最后一种不删：那是页面上确实印着、OCR 读不出来的希伯来文，
    抹掉等于假装原书没有这段（feedback_preserve_pdf_artifacts）。
    """
    def between(m):
        a, b = m.group(1), m.group(2)
        if is_word(a, lex) and is_word(b, lex):
            return a + ' ' + b
        return m.group(0)
    text = re.sub(r'([A-Za-z]{2,})' + LIT_STAR + r'([A-Za-z]{2,})', between, text)
    text = re.sub(r'(?<=[a-z])' + LIT_STAR + r'(\s+)(?=[A-Z])', r'.\1', text)
    text = re.sub(r'(?<=[.,;:])' + LIT_STAR + r'(?=\d)', ' ', text)
    text = re.sub(r'(?<=[A-Za-z.,;:)—–\"\'])' + LIT_STAR + r'(?=\s)', '', text)
    text = re.sub(r'(?<=\s)' + LIT_STAR + r'(?=\s)', '', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.replace(LIT_STAR, r'\*')


def main(book='psalms'):
    cfg = BOOKS[book]
    src, logfile = cfg['src'], cfg['log']
    manual_fix, real_word_fix, pre_fix = cfg['manual'], cfg['real'], cfg['pre']
    lex = build()
    vocab = corpus_vocab(lex, src)
    log = []
    stat = Counter()
    for path in sorted(src.glob('*.md')):
        text = path.read_text(encoding='utf-8')

        def repl(m):
            w = m.group(0)
            low = w.lower()
            if low in manual_fix:
                stat['manual'] += 1
                log.append((path.stem, w, manual_fix[low], 'manual'))
                return restore_case(w, manual_fix[low])
            if low in real_word_fix:
                stat['realword'] += 1
                log.append((path.stem, w, real_word_fix[low], 'realword'))
                return restore_case(w, real_word_fix[low])
            # 罗马数字里的 l 被读成 I：Ixxviii → lxxviii。
            # 这一条必须**排在 is_word 之前**：is_word 把任何由 ivxlcdm 组成
            # 的串都当罗马数字放行，而 I 恰好也在这个集合里（大小写不敏感），
            # 于是 Ixxviii 被判成「合法罗马数字」，永远轮不到修（踩过）。
            if re.fullmatch(r'I[xvi]{1,7}', w):
                stat['roman'] += 1
                log.append((path.stem, w, 'l' + w[1:], 'roman'))
                return 'l' + w[1:]
            # 词首的 w 被拆成 iv/tv/vn/ui/vv/to/lo/xo 之后，**碰巧还是个
            # 词典词**（ivas 由 iva+s 派生、ivill 曾被当罗马数字），判词典
            # 拦不住。这里用语料证据翻案：w 形在本书出现 5 次以上、且是该
            # 拼法的三倍以上，才改。
            if low in NOT_WORDS:
                cands = [c for c in candidates(low, lex) if vocab.get(c, 0) >= 20]
                if len(set(cands)) == 1:
                    stat['rule'] += 1
                    log.append((path.stem, w, cands[0], 'rule'))
                    return restore_case(w, cands[0])
            alt = _w_misread(low, vocab)
            if alt:
                stat['wform'] += 1
                log.append((path.stem, w, alt, 'wform'))
                return restore_case(w, alt)
            if is_word(w, lex):
                return w
            if len(low) < 3:          # oi / co / ia 这类两字母残片，规则一碰就错
                stat['tooshort'] += 1
                log.append((path.stem, w, '', 'tooshort'))
                return w
            # 三字母的 token 证据太薄：一次替换就能变成好几个真词
            # （thg→thig、oui→ow、Joh→Job）。对它们把语料自证的门槛从
            # 「出现过」抬到「出现过 20 次以上」，只放行 like/life/lips
            # 这类全书高频词。
            # 四字母以下证据太薄：coun→colin、unum→unurn、har→bar 都是
            # 这么来的。语料门槛从「出现过」抬到「出现过 20 次以上」。
            floor = 20 if len(low) <= cfg.get('short_len', 3) else 1
            cands = [c for c in candidates(low, lex) if vocab.get(c, 0) >= floor]
            if len(set(cands)) == 1:
                fixed = restore_case(w, cands[0])
                stat['rule'] += 1
                log.append((path.stem, w, fixed, 'rule'))
                return fixed
            if cands:
                stat['ambiguous'] += 1
                log.append((path.stem, w, '|'.join(sorted(set(cands))[:5]), 'ambiguous'))
                return w
            stat['unresolved'] += 1
            log.append((path.stem, w, '', 'unresolved'))
            return w

        for pat, rep in pre_fix:
            text = re.sub(pat, rep, text)
        text = rejoin_split_words(text, lex, vocab)
        text = join_across_star(text, lex)
        # 注释行（<!-- PAGE n -->）不参与
        parts = re.split(r'(<!--.*?-->)', text)
        parts = [p if p.startswith('<!--') else TOKEN.sub(repl, p) for p in parts]
        text = ''.join(parts)
        # 规则跑完再过一遍：字形规则自己会**造出**新的真词错误
        # （'Uve' → 'lire'），只有在它后面才拦得住。
        for pat, rep in pre_fix:
            text = re.sub(pat, rep, text)
        text = settle_stars(text, lex)
        path.write_text(text, encoding='utf-8')

    logfile.parent.mkdir(exist_ok=True)
    with open(logfile, 'w', encoding='utf-8') as f:
        f.write('chapter\tfrom\tto\tkind\n')
        for row in log:
            f.write('\t'.join(row) + '\n')
    print('修复统计:', dict(stat))
    print('日志:', logfile)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'psalms')
