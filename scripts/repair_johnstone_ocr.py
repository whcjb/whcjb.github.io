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


def corpus_vocab(lex, texts):
    """全书里**本来就正确**的词表。改出来的词必须在这张表里出现过。"""
    v = Counter()
    for t in texts:
        for w in TOKEN.findall(norm_tok(re.sub(r'[Ͱ-Ͽἀ-῿]+', ' ', t))):
            if is_word(w, lex):
                v[w.lower()] += 1
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
    if a.apply:
        for f, t in texts.items():
            def repl(m):
                w = m.group(0)
                fix = table.get(norm_tok(w))
                if not fix:
                    return w
                hits[w] += 1
                return fix[0]
            new = TOKEN.sub(repl, t)
            if new != t:
                open(os.path.join(src, f), 'w', encoding='utf-8').write(new)
    else:
        for f, t in texts.items():
            for w in TOKEN.findall(t):
                if norm_tok(w) in table:
                    hits[w] += 1

    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, 'w', encoding='utf-8') as fh:
        fh.write('verdict\tfrom\tto\tpairs\thits\n')
        for b, (c_a, c) in sorted(table.items(), key=lambda kv: -hits[kv[0]]):
            fh.write(f'fix\t{b}\t{c_a}\t{c}\t{hits.get(b, 0)}\n')
        for b, c_a, c, why in sorted(rejected, key=lambda r: -r[2]):
            fh.write(f'reject\t{b}\t{c_a}\t{c}\t{why}\n')
    print(f'{"落盘" if a.apply else "试跑"}：命中 {sum(hits.values())} 处 → {log}',
          file=sys.stderr)
    for b, (c_a, _c) in sorted(table.items(), key=lambda kv: -hits[kv[0]])[:40]:
        print(f'  {hits.get(b, 0):3d}  {b:20s} → {c_a}', file=sys.stderr)


if __name__ == '__main__':
    main()
