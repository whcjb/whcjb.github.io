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
    'icene': 'Nicene',        # *Ante-Nicene Christian Library*（leaf 0013 影像确认）
                              #   ——不是 1st：两边读的 ist/rst 都不对
}

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
        if is_word(b, lex):
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
        if len(w) < 4 or is_word(norm_tok(w), lex):
            return w
        if vocab.get(w.lower(), 0) >= 2:
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


def count_bigrams(texts):
    big = Counter()
    for t in texts:
        ws = [w.lower() for w in TOKEN.findall(norm_tok(t))]
        for i in range(len(ws) - 1):
            big[(ws[i], ws[i + 1])] += 1
    return big


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
    gap_log, glue_log, ord_log, lig_log = [], [], [], []
    for f, t in texts.items():
        new = apply_witness(t)
        new = rejoin_hyphen_gap(new, lex, vocab, gap_log)
        new = split_glued(new, lex, vocab, bigrams, glue_log)
        new = fix_ordinals(new, ord_log)
        new = fix_ligatures(new, lig_log)
        if a.apply and new != t:
            open(os.path.join(src, f), 'w', encoding='utf-8').write(new)

    print(f'连字符夹垃圾 {len(gap_log)} 处，粘词 {len(glue_log)} 处，'
          f'旧式数字序数 {len(ord_log)} 处，æ 合字 {len(lig_log)} 处',
          file=sys.stderr)
    for was, now in gap_log + glue_log + ord_log + lig_log:
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
        for b, c_a, c, why in sorted(rejected, key=lambda r: -r[2]):
            fh.write(f'reject\t{b}\t{c_a}\t{c}\t{why}\n')
    print(f'{"落盘" if a.apply else "试跑"}：命中 {sum(hits.values())} 处 → {log}',
          file=sys.stderr)
    for b, (c_a, _c) in sorted(table.items(), key=lambda kv: -hits[kv[0]])[:40]:
        print(f'  {hits.get(b, 0):3d}  {b:20s} → {c_a}', file=sys.stderr)


if __name__ == '__main__':
    main()
