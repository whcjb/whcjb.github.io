#!/usr/bin/env python3
"""约翰斯通《腓立比书讲疏》—— 拿 ABBYY 当第二证人修 tesseract 的错字。

这本书全网只有一份扫描件，没有第二份影像可以按位置比对。但**有两套互相
独立的 OCR**：IA 2010 年的 ABBYY FineReader 8.0，和本地 2026 年的
tesseract 5.5。两者的败法完全不同 —— ABBYY 栽在连字（tlie/l)y），
tesseract 栽在斜体字形（*religious* → veigious、*Lord* → Zord）。
一方读错的地方另一方多半是对的，这就是第二证人。

比对在**抽取时已经做过的那次字符级对齐**上进行，不另起炉灶。

三道闸，缺一条都会改坏（feedback_ocr_repair_three_gates）：

  ① 判词典   tesseract 这一侧必须**不是**词，ABBYY 那一侧必须**是**词。
             少了它会把 shews/connexion 这类 19 世纪拼法「改正」成现代拼法。
  ② 形近     相似度 ≥0.5，且 ABBYY 侧不得比 tesseract 侧短 2 个字以上。
             少了它 `Iam → I`、`Itis → It` 会直接吃掉一个词（实测两处）。
  ③ 语料自证 改出来的词必须在本书别处**正确出现过** ≥2 次。
             少了它 `Cesar → Caesar` 这类会过 —— 原书印的是 Cæsar，
             两边谁对要看影像，语料不认就不动。

改不动的一律原样留下并记账，交给影像精读，绝不猜。
"""
import argparse
import difflib
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alexander_abbyy as A
import johnstone_common as J
import extract_johnstone as E
from alexander_lexicon import build, is_word

ROOT = os.path.dirname(HERE)
TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9']*")
MIN_RATIO = 0.5
MIN_ATTEST = 2


# ── 逐句核过上下文的几条 ─────────────────────────────────────
#
# 第二证人给出的「长跳跃」候选（tesseract 把词截断、ABBYY 给出整词）不能
# 一概采信：ABBYY 自己也会截断。下面每一条都对着上下文逐句核过，
# 右边括号里是核的那句话。

VERIFIED = {
    # 两边都对得上，ABBYY 给的是整词
    'ept': 'except',          # how our spirits can act, «except» through a body
    'contradi': 'contradictory',  # would be directly «contradictory» of that made in
    'wor': 'world',           # God so loved the «world», that He gave His only-begotten Son
    'orfor': 'torpor',        # Men who are in a «torpor», through indolence
    'waction': 'unction',     # Ye have an «unction» from the Holy One（约壹 2:20）
    'sowd': 'soul',           # oneness of «soul», subjection of natural discordances
    'vange': 'range',         # Observe the «range» of proper subjects of prayer
    'pfu': 'helpful',         # His own teaching might be «helpful» to his brethren
    'hea': 'hearers',         # apt to beset both preachers and «hearers»
    'thil': 'things',         # To say the same «things» to their hearers（腓 3:1）
    'urt': 'heart',           # has mind and «heart» shielded thereby
    'spiritu': 'spiritually',  # are changed «spiritually» into the same image

    # 两个 OCR 都错，正解靠上下文定（第二证人在这里帮不上忙）
    'ove': 'love',            # Him who rests in His «love»（番 3:17）——ABBYY 给的 one 是错的
    'ves': 'lives',           # yet he «lives» spiritually through the loving contemplation
    'rst': 'first',           # just after that «first» verse had been written
    'GLAsGow': 'GLASGOW',     # 序末落款，原书排小型大写（leaf 0013 影像确认）
    'Zhe': 'The',             # 斜体 T 读成 Z；长度不够走不到字形回扫
    'Luodia': 'Euodia',       # 斜体 E 读成 L（p.349 影像确认）
    'icene': 'Nicene',        # *Ante-Nicene Christian Library*（leaf 0013 影像确认）
                              #   ——不是 1st：两边读的 ist/rst 都不对
}

# 只能按**上下文**定位的人工条目：同一个词在别处是对的，不能全局替换。
# 每条都注明在哪一页的影像上核的。
MANUAL_CONTEXT = [
    # p.103（leaf 0119）：印面是 *never* to despond。读成 ever **把意思读反了**，
    # 而 ever 本身是真词、全书到处都是，任何全局判据都碰不得它。
    ('important, *ever* to despond', 'important, *never* to despond'),
    # p.407：OCR 把 lead 的 l 读成星号，印面比对把 lead 补回来了，
    # 但那个被转义的字面星号留在原地（归一化定位看不见它）。
    # p.407：OCR 把 lead 的 l 读成星号，于是这段斜体**只有开头没有结尾**。
    # 印面比对把 lead 补回来了，但那个字面星号与缺失的闭合标记它看不见
    # （归一化时星号被抹掉）。连同闭合一起补。
    ('‘*when I departed from Macedonia,’ \\*lead us',
     '‘*when I departed from Macedonia,*’ lead us'),

    # ── 印面比对报出来、但替换区间压着斜体标记的 11 条 ──
    # 自动回填一律跳过这种（删区间会连标记一起删），改为逐条手写，
    # 标记位置照原样保留。每条都是 OCR 把**斜体字母**读错：
    #   d→b  K→F  £→k  z→wh  A→th  22→in  d/→bl
    ('be ολίγον*» unto the Lord,*', 'be *Holiness unto the Lord,*'),
    ('‘ *Kor unto you', '‘ *For unto you'),
    ('‘ *deing like-minded,*', '‘ *being like-minded,*'),
    ('‘ *d/ameless and harmless', '‘ *blameless and harmless'),
    ('‘ *d/ameless’*', '‘ *blameless’*'),
    ('‘ *de of the same mind.', '‘ *be of the same mind.'),
    ('‘ *22: everything.*', '‘ *in everything.*'),
    ('‘ *£eep’*', '‘ *keep’*'),
    ('‘ *zwhatsoever things are pure.*', '‘ *whatsoever things are pure.*'),
    ('‘ *Ais’*', '‘ *this’*'),
    # 希腊文不打斜体（Porson 体本身就是斜的），所以这条连标记一起去掉
    ('*xairep* > & δ ἐγὼ ἔχων', 'καίπερ ἐγὼ ἔχων'),
]


# 第二证人提了但核下来是错的，明确拒掉，免得下次又被提出来。
NEVER = {
    ('ove', 'one'), ('ves', 'rest'), ('rst', 'ist'),
    ('iam', 'him'),   # 所在整页糊成一片，him 接不上下文，留给影像精读
}


def norm_tok(s):
    return s.replace('’', "'")


def collect_pairs():
    """重走一遍抽取时的对齐，把「同一位置的两个词」收集起来。"""
    ab = A.parse_pages(E.load_xml())
    ocr = E.ocr_pages()
    for leaf in E.drop_duplicate_leaves(ocr):
        del ocr[leaf]
    first, shapes = E.learn_heads(ocr)
    E.SECTION_TITLES = [E._key(t) for t in (
        ['Introduction'] + E.LECTURES + [t for _, _p, t in E.TAIL]
        + ['Lectures on Philippians', 'The Epistle to the Philippians',
           'Contents', 'Preface', 'Appendix'])]

    pairs = Counter()
    for leaf in sorted(ocr):
        if leaf >= len(ab):
            break
        # 页眉必须先剔。不剔的话 `[CH. II.` 这类页眉残片会配出
        # `IL → ii`、`cu → ch` 这种假对（实测 10 组以上）。
        txt = E.page_text([p['text'] for p in ab[leaf]['pars']], ocr[leaf],
                          first.get(leaf, ''), shapes)
        if not txt.strip():
            continue
        keep, seen = [], False
        for par in ab[leaf]['pars']:
            plain = J.strip_sentinels(par['text'])[0].strip()
            if not seen and plain:
                seen = True
                head0 = plain.split('\n')[0]
                if E.has_folio(head0) and E.head_shape(plain) in shapes:
                    continue
            keep.append(par['text'])
        a_all = ''.join(J.strip_sentinels(t)[0] for t in keep)
        b_all = txt.replace('*', '')
        if not a_all.strip() or not b_all.strip():
            continue
        sm = difflib.SequenceMatcher(None, J._norm(a_all), J._norm(b_all),
                                     autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                continue
            while i1 > 0 and a_all[i1 - 1].isalpha():
                i1 -= 1
            while i2 < len(a_all) and a_all[i2 - 1:i2].isalpha():
                i2 += 1
            while j1 > 0 and b_all[j1 - 1].isalpha():
                j1 -= 1
            while j2 < len(b_all) and b_all[j2 - 1:j2].isalpha():
                j2 += 1
            if i2 - i1 > 40 or j2 - j1 > 40:
                continue
            aw = TOKEN.findall(norm_tok(a_all[i1:i2]))
            bw = TOKEN.findall(norm_tok(b_all[j1:j2]))
            if len(aw) == 1 and len(bw) == 1:
                pairs[(bw[0], aw[0])] += 1
    return pairs


HYPHENATED = re.compile(r'\b([A-Za-z]{2,})-([a-z]{2,})\b')


def corpus_vocab(lex, texts):
    """全书里**本来就正确**的词表。改出来的词必须在这张表里出现过。

    连字符复合词（self-seeking）整体记一条，拆词判据要拿它当凭据。
    """
    v = Counter()
    for t in texts:
        clean = norm_tok(re.sub(r'[Ͱ-Ͽἀ-῿]+', ' ', t))
        for w in TOKEN.findall(clean):
            if is_word(w, lex):
                v[w.lower()] += 1
        for m in HYPHENATED.finditer(clean):
            v[m.group(0).lower()] += 1
    return v


def decide(pairs, lex, vocab):
    """三道闸，出一张 {错 → 对} 的表。"""
    best, rejected = {}, []
    by_src = {}
    for (b, a), c in pairs.items():
        by_src.setdefault(b, []).append((c, a))
    for b, cands in by_src.items():
        cands.sort(reverse=True)
        c, a = cands[0]
        why = None
        if is_word(b, lex) and not (
                vocab.get(b.lower(), 0) <= 1 and vocab.get(a.lower(), 0) >= 5
                and difflib.SequenceMatcher(None, b.lower(), a.lower()).ratio() >= 0.8):
            # 真词错误（`edders`＝web2 收的一个僻词，实为 elders）规则抓不到，
            # 判词典自己先把它当成合法词放行了。唯一的凭据是**语料**：
            # 错的那个形全书只出现一两次，对的那个出现几十次，而且形很近。
            why = '① tesseract 侧本来就是词'
        elif not is_word(a, lex):
            why = '① ABBYY 侧也不是词'
        elif b.lower() == a.lower():
            why = '两边一样'
        elif difflib.SequenceMatcher(None, b.lower(), a.lower()).ratio() < MIN_RATIO:
            why = '② 形差太远'
        elif len(a) < len(b):
            # ABBYY 比 tesseract 短 = 多半是 tesseract 把两个词粘住了，
            # 而 ABBYY 只给出前一个。照搬会**吃掉一个词**：
            #   witha → with（丢了 a）   ButI → But（丢了 I）
            #   chooseI → choose        Iam → I
            # 这类要补的是空格不是替换，交给另一道判据，这里一律不动。
            why = '② ABBYY 侧更短，多半是粘词只给了前半'
        elif (b, a) in NEVER:
            why = '④ 核过上下文，这条是错的'
        elif len(a) > len(b) + 2 and b not in VERIFIED:
            why = '④ ABBYY 侧长出一截（tesseract 截词），未逐句核过不采信'
        elif vocab.get(a.lower(), 0) < MIN_ATTEST:
            why = f'③ 全书只正确出现 {vocab.get(a.lower(), 0)} 次'
        if why:
            rejected.append((b, a, c, why))
        else:
            best[b] = (a, c)
    return best, rejected


# ── 两类版面伤 ───────────────────────────────────────────────

# 行末断词的连字符还在，但**两半中间插进了垃圾**（页边噪点、斜体残星、
# 破折号），抽取阶段的「行尾连字符 + 下一行首字母小写」判据因此配不上：
#     direc- ‘tion      posi- — tion      appear- _ ance      com- _pleteness
# 判据里的「中间必须有东西」不能省 —— 没它会把 co-operate、pre-incarnate
# 这类**原书本来就带连字符**的复合词一起拼掉。
# 中间那截垃圾里**不许包含 `*` 和 `\`**：那是 markdown 的斜体标记，
# 吃掉一个就让整段的标记错位，kramdown 会把后面的星号原样打印出来
# （实测 `re- * garding` 吞掉一个斜体开关，30.md 的星号从此成了奇数）。
HYPH_GAP = re.compile(
    r'\b([A-Za-z]{2,})-(?:[ \t]*[^\s A-Za-z*\\][^\sA-Za-z*\\]{0,3}[ \t]*|[ \t]+)([a-z]{2,})\b')


def rejoin_hyphen_gap(text, lex, vocab, log):
    def repl(m):
        x, y = m.group(1), m.group(2)
        j = x + y
        if is_word(x, lex) and is_word(y, lex):
            return m.group(0)          # 两半都是词，没证据说该拼
        if not is_word(j, lex):
            return m.group(0)
        # 整词在本书别处正确出现过，或左半根本不是词（unobtru- / notwith-）
        if vocab.get(j.lower(), 0) >= 1 or not is_word(x, lex):
            log.append((m.group(0), j))
            return j
        return m.group(0)
    return HYPH_GAP.sub(repl, text)


def split_glued(text, lex, vocab, bigrams, log):
    """该有空格却粘住了：`Itis` → `It is`、`tothe` → `to the`。

    切法不能取「第一个两半都成词的位置」—— `aman` 会切成 `am an`，
    而正解是 `a man`；`Lightfoot` 会切成 `Light foot`，而它根本不该切。

    判据交给语料：枚举所有切法，取**这一对词在本书里真正相邻出现**最多的
    那一种，且至少 3 次；同时粘着的那个形在本书出现 ≥2 次就不动
    （Lightfoot 出现 39 次、meantime 3 次 —— 那是真词，不是粘词）。
    """
    def repl(m):
        w = m.group(0)
        # 长度下限 3 不是 4：`ina`（in a）正好是 3 个字母，卡 4 就永远改不掉
        # ——p.103 的 `labouring ina field` 实读才发现（4 处）。
        if len(w) < 3 or is_word(norm_tok(w), lex):
            return w
        # 只有**粘着的那个形本身是个真词**才放过（Lightfoot 39 次、meantime 3 次）。
        # 早先只看「出现 ≥2 次」，于是 `ina`（4 次，不是词）也被放过，
        # p.103 的 `labouring ina field` 一直没改掉（实读查出）。
        if is_word(norm_tok(w), lex) and vocab.get(w.lower(), 0) >= 2:
            return w
        best, bc = None, 0
        for i in range(1, len(w)):
            x, y = w[:i], w[i:]
            if not (is_word(x, lex) and is_word(y, lex)):
                continue
            c = bigrams.get((x.lower(), y.lower()), 0)
            if c > bc:
                # 原书可能本来就是**带连字符的复合词**（self-seeking），
                # 拆成两个词是另一种错。看全书哪一种写法更多。
                sep = '-' if vocab.get(f'{x.lower()}-{y.lower()}', 0) >= c else ' '
                best, bc = x + sep + y, c
        if best and bc >= 3:
            log.append((w, best))
            return best
        return w
    return TOKEN.sub(repl, text)


# 旧式数字（old-style figures）被当成字母读。这本书正文里的序数全用旧式
# 数字排，字形与小写字母极像：1→r、0→o、9→g 或 o、2→z。
#     the roth and 11th verses      the gth verse      the znd chapter
# 每一条都由上下文定死（见下），不是凭字形猜：
#   gth / oth = 9th —— 「与第 9 节那一祈求同列」正是腓 1:9；
#                      「第 9 节的 ταῦτα」正是腓 4:9「这些事你们要去行」；
#                      波利卡普「第 9 段」提到伊格那丢之死，也对得上。
#   znd = 2nd   —— 「启示录第 2 章写给那教会」「第 2 节提到的那两个妇人」。
ORDINAL_FIG = {'gth': '9th', 'oth': '9th', 'znd': '2nd'}

# `roth` 不能一概而论：它既出现在「the roth and 11th verses」（=10th），
# 也出现在「the 18th and roth」（=19th）。所以不按字形改，按**邻居**改 ——
# 一个范围里另一个序数是干净的，就用它 ±1 把这个推出来。
ORD_PAIR = re.compile(
    r'\bthe\s+(\d{1,3})(?:st|nd|rd|th)\s+and\s+([a-z]{2,4})\b'
    r'|\bthe\s+([a-z]{2,4})\s+and\s+(\d{1,3})(?:st|nd|rd|th)\b')
GARBLED_ORD = re.compile(r'^[a-z]{1,2}(?:th|nd|rd|st)$')


def suffix(n):
    if 10 <= n % 100 <= 20:
        return 'th'
    return {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')


def fix_ordinals(text, log):
    def pair(m):
        if m.group(1):
            num, bad, after = int(m.group(1)), m.group(2), True
        else:
            bad, num, after = m.group(3), int(m.group(4)), False
        if not GARBLED_ORD.match(bad):
            return m.group(0)
        n = num + 1 if after else num - 1
        if n < 1:
            return m.group(0)
        good = f'{n}{suffix(n)}'
        log.append((bad, good))
        return m.group(0).replace(bad, good)

    text = ORD_PAIR.sub(pair, text)

    def single(m):
        w = m.group(0)
        fix = ORDINAL_FIG.get(w)
        if not fix:
            return w
        log.append((w, fix))
        return fix
    return re.sub(r'\b(?:' + '|'.join(ORDINAL_FIG) + r')\b', single, text)


# 合字 æ / œ。原书用的是真合字，两套 OCR 都拆不出来，各自吐出一堆变体：
#   Cæsar     → Cesar / Czsar / Ceesar / Czesar / Casar
#   Prætorian → Praetorian / Pretorian / Preetorian / Przetorian
#   prætorium → pretorium / fretorium
# **已对页面影像确认**（leaf 0437 的「they that are of Cæsar's household」、
# leaf 0068 的「of the Prætorian soldiers」），不是靠猜。
# 这一类正是第③道闸（语料自证）挡下 ABBYY 的 `Cesar → Caesar` 的地方 ——
# 两个证人都错时，只有影像说了算。
LIGATURE = [
    (r'\bC[aeozx]{1,3}sar\b', 'Cæsar'),
    (r'\bC[aeozx]{1,3}sarea\b', 'Cæsarea'),
    (r'\b[Pp]r[aeozx]{1,3}torian\b', 'Prætorian'),
    (r'\b[pf]r[aeozx]{1,3}torium\b', 'prætorium'),
]


def fix_ligatures(text, log):
    for pat, good in LIGATURE:
        def repl(m, good=good):
            w = m.group(0)
            out = good if w[:1].isupper() or good[:1].islower() else good
            if w != out:
                log.append((w, out))
            return out
        text = re.sub(pat, repl, text)
    return text


# ── 第四道：从已确认的修正里**学**字形混淆，再回扫全书 ────────
#
# 到这一步，第二证人已经确认了两百多条修正。把每条拿 difflib 对齐，就能把
# tesseract 在这份扫描件上的字形混淆**统计出来**，不必凭直觉写规则：
#     f→p 17 次   z→i 13 次   d→b 11 次   z→n 8 次   m→n 7 次
#     v→r 5 次    A→h 3 次    w→u 3 次    Z→l/T/p 各 2 次
# 再拿这张表去扫剩下的非词。闸子四道，少一道都会改坏（实测）：
#   ① 判词典：原词不是词、改出来的是词
#   ② 语料自证：改出来的词在本书正确出现过 ≥3 次
#   ③ **只许一次替换，且原词 ≥5 个字母**
#      —— 少了这条，`pre`→`pro`（11 处！）、`cer`→`cor`、`com`→`con`、
#         `ence`→`once` 全会过。它们是连字符前缀和断词碎片，不是错字。
#   ④ **连字符旁边的 token 一律不碰**：`pre-eminence` 的 `pre` 被切成独立
#      token，看着像非词，其实是正文。
#
# 斜杠另算一支。词里出现 `/` 在英文里不可能是对的（`e/ders`、`radical/`、
# `know/edge`、`a/ways` —— 斜体的 l 被读成斜杠，或多吐一个斜杠）。
# 只试「删掉」和「换成 l/t/i」，结果必须 ≥3 个字母、且全书出现过 ≥3 次
# （不卡长度的话 `A/y` 会变成 `Ay`，而它其实是 `My`）。
SLASH_TRY = ['', 'l', 't', 'i']

# 字形回扫自动给出的解不对、但人核得出来的，写死在这里。
# 这两条都是**原词只剩两三个字母**，自动解没有足够信息。
GLYPH_FIX = {
    'd/e': 'Me',    # `a word of wondering praise: ‘*Me*—who was a persecutor,
                    #  a blasphemer, and injurious’`（ABBYY 读作 `^Me—`，
                    #  且提前 1:13 原文如此）。自动解给的是 die，错。
                    #  第二证人那一遍本来认得出，被「ABBYY 侧不得更短」挡了。
    'se/': 'self',  # `a firm *se/(-restraint`＝self-restraint。自动解给 set，错。
}
MIN_SUB = 2          # 一条字形混淆至少在确认表里出现过几次
MIN_LEN = 5          # 原词至少几个字母才允许按字形改
MIN_VOCAB = 3        # 改出来的词在本书至少正确出现过几次


def learn_confusions(table):
    """{错→对} → [(错字形, 对字形)]，按 difflib 对齐统计。"""
    cnt = Counter()
    for a, (b, _n) in table.items():
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                None, a, b, autojunk=False).get_opcodes():
            if tag == 'replace' and i2 - i1 <= 2 and j2 - j1 <= 2:
                cnt[(a[i1:i2], b[j1:j2])] += 1
            elif tag == 'delete' and i2 - i1 <= 1:
                cnt[(a[i1:i2], '')] += 1
    return [(x, y) for (x, y), c in cnt.items() if c >= MIN_SUB and x]


def glyph_sweep(text, lex, vocab, rules, log):
    def once(w):
        out = set()
        for x, y in rules:
            i = 0
            while True:
                i = w.find(x, i)
                if i < 0:
                    break
                out.add(w[:i] + y + w[i + len(x):])
                i += 1
        return out

    def repl(m):
        w = m.group(0)
        lo, hi = m.start(), m.end()
        if (lo and text[lo - 1] == '-') or (hi < len(text) and text[hi] == '-'):
            return w                      # ④ 连字符旁边的碎片不碰
        if is_word(norm_tok(w), lex):
            return w
        if w in GLYPH_FIX:
            log.append((w, GLYPH_FIX[w]))
            return GLYPH_FIX[w]
        if '/' in w:
            # 斜杠词常常**还带着另一个字形错**（`d/ameless` 要先把斜杠还原成
            # l，再把 d 还原成 b 才成 blameless）。所以允许「斜杠一步 +
            # 学来的混淆一步」，闸子不变。
            # 词里出现斜杠在英文里不可能是对的，所以这一支不卡「全书出现
            # ≥3 次」那条硬线（`radical` 全书只出现 2 次，卡死就修不掉），
            # 改成**取语料里出现最多的那个解，且要甩开第二名一倍**。
            step1 = {w.replace('/', y) for y in SLASH_TRY}
            cand = [v for v in step1
                    if len(re.sub(r"[^A-Za-z]", '', v)) >= 3 and is_word(v, lex)]
            if not cand:
                cand = [v2 for v in step1 for v2 in once(v)
                        if len(re.sub(r"[^A-Za-z]", '', v2)) >= 4 and is_word(v2, lex)]
            ranked = sorted(cand, key=lambda v: -vocab.get(v.lower(), 0))
            good = set()
            if ranked and vocab.get(ranked[0].lower(), 0) >= 1:
                second = vocab.get(ranked[1].lower(), 0) if len(ranked) > 1 else 0
                if vocab.get(ranked[0].lower(), 0) >= max(1, 2 * second):
                    good = {ranked[0]}
        elif len(re.sub(r"[^A-Za-z]", '', w)) >= MIN_LEN:
            good = {v for v in once(w)
                    if is_word(v, lex) and vocab.get(v.lower(), 0) >= MIN_VOCAB}
        else:
            return w
        if len(good) != 1:
            return w
        fix = good.pop()
        log.append((w, fix))
        return fix
    return GLYPH_TOKEN.sub(repl, text)


# 斜杠也可能在**词首**（`/eads`＝leads、`/ast`＝last），所以 token 允许以
# 斜杠开头 —— 只认字母开头的话这一支整类都扫不到（实测漏 8 处）。
GLYPH_TOKEN = re.compile(r"/?[A-Za-z][A-Za-z0-9'/]*")


# ── 斜体大写 I ───────────────────────────────────────────────
#
# **这一类是实读印面才查出来的，所有检测器都看不见**：原书斜体的大写 I
# 字形带衬线、略带弧度，tesseract 读成 `7` / `J` / `Z` / `77`。
#     `*J may rejoice in the day of Christ, that 7 have not run in vain*`
#     `‘ Z *beseech Euodia,*—*and 77 beseech Syntyche.*`
#     `*‘but 7 desire fruit that may abound to your account*`
# 它们全是**合法 token**（数字、大写字母），非词率、星号奇偶、页眉判据
# 一条都报不出来。只有把页面影像和正文摆到一起逐句看才看得见
# （feedback_page_image_is_final_authority）。
#
# 判据：token 独立成词（两边都是空白或引号/星号），后面紧跟一个小写词，
# 而且前面不是经文出处里的数字（`2 Thess. i. 4-7` 的那个 7 要留着）。
RE_ITALIC_I = re.compile(
    r"(?:(?<=^)|(?<=[\s‘’“”\"\*—–\(\[:;,]))(?P<tok>Z|J|7{1,2}|TJ)"
    r"(?P<post>\*?\s+\*?)(?P<next>[a-z]{2,})", re.M)
RE_CITATION_LEAD = re.compile(r'[0-9ivxlcIVXLC]\s*[.\-–,]\s*$|\d\s*$')


def fix_italic_i(text, log):
    def repl(m):
        lead = text[max(0, m.start() - 16):m.start('tok')]
        if RE_CITATION_LEAD.search(lead):
            return m.group(0)
        log.append((m.group('tok'), 'I'))
        return 'I' + m.group('post') + m.group('next')
    return RE_ITALIC_I.sub(repl, text)


def count_bigrams(texts):
    big = Counter()
    for t in texts:
        ws = [w.lower() for w in TOKEN.findall(norm_tok(t))]
        for i in range(len(ws) - 1):
            big[(ws[i], ws[i + 1])] += 1
    return big


# ── 印面比对落下来的人工条目 ──────────────────────────────
#
# manual_fixes.tsv 每行：文件 \t leaf \t 我们的 \t 印面的（都已归一化）。
# 归一化抹掉了引号样式、破折号样式和**斜体标记**，所以回填时
# **只能把真正不同的那几个片段塞回去，不能整段替换** ——
# 整段替换会把 `*…*` 一起抹掉，等于拿修正去毁斜体。
#
# 做法：原文归一化时记下「归一化下标 → 原文下标」的对照表，
# 在归一化串上定位、算差异，再按对照表把差异片段映射回原文下标，
# 从后往前 splice。星号落在两个映射点之间，原样留着。
FIX_TBL = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'manual_fixes.tsv')
# 「修订译文」那一节的边码单独一张表：它不是「改错字」，是**补回被当噪点
# 清掉的节号**，来源也不同（单独问影像左侧页边那一列），分开放便于复核。
FIX_TBL_EXTRA = os.path.join(ROOT, 'johnstone_raw', 'philippians',
                             'manual_fixes_extra.tsv')
FIX_QUOTE = str.maketrans({'‘': "'", '’': "'", '“': '"', '”': '"',
                           '′': "'", '—': '-', '–': '-'})


def norm_map(text):
    """归一化 + 下标对照表。"""
    out, idx = [], []
    prev_space = False
    for i, ch in enumerate(text):
        c = ch.translate(FIX_QUOTE)
        if c in '*\\':
            continue
        if c.isspace():
            if prev_space or not out:
                continue
            out.append(' '); idx.append(i); prev_space = True
            continue
        prev_space = False
        out.append(c); idx.append(i)
    return ''.join(out), idx


def load_fixes():
    out = {}
    for tbl in (FIX_TBL, FIX_TBL_EXTRA,
                os.path.join(ROOT, 'johnstone_raw', 'philippians',
                             'manual_fixes_vlm.tsv')):
        if not os.path.exists(tbl):
            continue
        for line in open(tbl, encoding='utf-8'):
            if line.startswith('#'):
                continue
            p = line.rstrip('\n').split('\t')
            if len(p) >= 4:
                out.setdefault(p[0], []).append((p[2], p[3], p[1]))
    return out


def apply_fixes(text, items, log):
    flat, idx = norm_map(text)
    edits = []
    for before, after, leaf in items:
        at = flat.find(before)
        if at < 0 or flat.find(before, at + 1) >= 0:
            log.append((f'leaf {leaf} 落不下', before[:52]))
            continue
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                None, before, after, autojunk=False).get_opcodes():
            if tag == 'equal':
                continue
            lo = idx[at + i1] if at + i1 < len(idx) else len(text)
            hi = (idx[at + i2 - 1] + 1) if i2 > i1 else lo
            edits.append((lo, hi, after[j1:j2], before[i1:i2], leaf))
    edits.sort(key=lambda e: -e[0])
    done, last = [], len(text) + 1
    for lo, hi, rep, was, leaf in edits:
        if hi > last:                 # 片段重叠，跳过后到的那个
            log.append((f'leaf {leaf} 片段重叠', was[:40])); continue
        # ⚠️ 替换区间里夹着斜体标记就**整条跳过**。
        # 归一化时星号被抹掉了，它落在两个映射点「之间」，
        # 一旦被圈进 [lo,hi) 就会跟着被删 —— 实测 12 个文件的星号因此成了
        # 奇数，整段斜体错位。宁可少改一处，不可毁掉标记
        # （feedback_fix_table_makes_errors）。
        if '*' in text[lo:hi] or '\\' in text[lo:hi]:
            log.append((f'leaf {leaf} 区间含斜体标记，跳过', was[:40])); continue
        text = text[:lo] + rep + text[hi:]
        last = lo
        done.append((was, rep))
    return text, done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='落盘；不给就是试跑')
    a = ap.parse_args()

    lex = build()
    src = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'en_chapters')
    files = sorted(f for f in os.listdir(src) if f.endswith('.md'))
    texts = {f: open(os.path.join(src, f), encoding='utf-8').read() for f in files}
    vocab = corpus_vocab(lex, texts.values())

    pairs = collect_pairs()
    table, rejected = decide(pairs, lex, vocab)
    for wrong, right in VERIFIED.items():   # 核过的直接进表，不走闸
        table[wrong] = (right, 0)
    print(f'对齐词对 {len(pairs)} 组 → 采纳 {len(table)} 条，驳回 {len(rejected)} 条',
          file=sys.stderr)

    log = os.path.join(ROOT, 'logs', 'johnstone_repair.tsv')
    hits = Counter()

    def apply_witness(t):
        def repl(m):
            w = m.group(0)
            fix = table.get(norm_tok(w))
            if not fix:
                return w
            hits[w] += 1
            return fix[0]
        return TOKEN.sub(repl, t)

    # ⚠️ 所有修复**串在同一个字符串上跑，最后只写一次盘**。
    # 早先是「第二证人那一遍写一次，版面伤那一遍从 texts 原文再写一次」，
    # 后者把前者的改动整个盖掉了 —— 表里明明有 `zs → is` 命中 19 处，
    # 产物里 zs 却原样还在 17 处。只有连跑两次 --apply 才看起来是对的。
    bigrams = count_bigrams(texts.values())
    rules = learn_confusions(table)
    gap_log, glue_log, ord_log, lig_log, glyph_log = [], [], [], [], []
    ital_i_log, manual_log, fix_log, fix_fail = [], [], [], []
    FIXES = load_fixes()
    for f, t in texts.items():
        new = apply_witness(t)
        new = rejoin_hyphen_gap(new, lex, vocab, gap_log)
        new = split_glued(new, lex, vocab, bigrams, glue_log)
        new = fix_ordinals(new, ord_log)
        new = fix_ligatures(new, lig_log)
        new = glyph_sweep(new, lex, vocab, rules, glyph_log)
        new = fix_italic_i(new, ital_i_log)
        if f in FIXES:
            new, applied = apply_fixes(new, FIXES[f], fix_fail)
            fix_log.extend(applied)
        for before, after in MANUAL_CONTEXT:
            if before in new:
                new = new.replace(before, after)
                manual_log.append((before[:46], after[:46]))
        if a.apply and new != t:
            open(os.path.join(src, f), 'w', encoding='utf-8').write(new)

    print(f'连字符夹垃圾 {len(gap_log)} 处，粘词 {len(glue_log)} 处，'
          f'旧式数字序数 {len(ord_log)} 处，æ 合字 {len(lig_log)} 处，'
          f'字形回扫 {len(glyph_log)} 处（{len(rules)} 条学来的混淆），'
          f'斜体大写 I {len(ital_i_log)} 处，按上下文的人工条目 {len(manual_log)} 处，'
          f'印面比对条目 {len(fix_log)} 处（落不下 {len(fix_fail)} 条）',
          file=sys.stderr)
    for was, now in gap_log + glue_log + ord_log + lig_log + glyph_log + ital_i_log + manual_log + fix_log:
        print(f'    {was!r} → {now}', file=sys.stderr)

    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, 'w', encoding='utf-8') as fh:
        fh.write('verdict\tfrom\tto\tpairs\thits\n')
        for b, (c_a, c) in sorted(table.items(), key=lambda kv: -hits[kv[0]]):
            fh.write(f'fix\t{b}\t{c_a}\t{c}\t{hits.get(b, 0)}\n')
        for was, now in gap_log:
            fh.write(f'hyphen-gap\t{was}\t{now}\t\t\n')
        for was, now in glue_log:
            fh.write(f'glued\t{was}\t{now}\t\t\n')
        for was, now in ord_log:
            fh.write(f'ordinal\t{was}\t{now}\t\t\n')
        for was, now in lig_log:
            fh.write(f'ligature\t{was}\t{now}\t\t\n')
        for was, now in glyph_log:
            fh.write(f'glyph\t{was}\t{now}\t\t\n')
        for was, now in ital_i_log:
            fh.write(f'italic-I\t{was}\t{now}\t\t\n')
        for b, c_a, c, why in sorted(rejected, key=lambda r: -r[2]):
            fh.write(f'reject\t{b}\t{c_a}\t{c}\t{why}\n')
    print(f'{"落盘" if a.apply else "试跑"}：命中 {sum(hits.values())} 处 → {log}',
          file=sys.stderr)
    for b, (c_a, _c) in sorted(table.items(), key=lambda kv: -hits[kv[0]])[:40]:
        print(f'  {hits.get(b, 0):3d}  {b:20s} → {c_a}', file=sys.stderr)


if __name__ == '__main__':
    main()
