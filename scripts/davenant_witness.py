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


def _norm(s):
    return re.sub(r'[^a-z]', '', s.lower())


def _isword(w):
    b = _norm(w)
    return len(b) >= 2 and b in DICT


def fix_line(vol, page, text):
    """→ (改后的文本, [(原, 新, 理由), …])。判不了就原样返回。"""
    toks = text.split()
    if len(toks) < 2:
        return text, []
    # ⚠️ 这里**不能**因为「每个词都在词典里」就早退。词频裁判要处理的正是
    # 「两边都是词」的情形——`Does not free-will one cause effect in ail?`
    # 整行八个词全在词典里，早退一挡，`ail` → `all` 永远轮不到判（实测）。
    cands = ia_lines(vol, page)
    if not cands:
        return text, []
    key = re.sub(r'[^a-z ]', '', text.lower())
    best = max(cands, key=lambda c: difflib.SequenceMatcher(
        None, key, re.sub(r'[^a-z ]', '', c.lower())).ratio())
    if difflib.SequenceMatcher(None, key, re.sub(
            r'[^a-z ]', '', best.lower())).ratio() < 0.55:
        # 对不上行（多半是两边都读花的希腊文音译）时，别的都不动，
        # 但孤立的 `|` `/` 照删——这两个字符在本书里从不合法出现，
        # 不需要第二证人也能断定是扫描斑点。
        if not any(SPECK.match(t) for t in toks):
            return text, []
        keep = [t for t in toks if not SPECK.match(t)]
        return ' '.join(keep), [(t, '', '斑点') for t in toks if SPECK.match(t)]

    theirs = best.split()
    sm = difflib.SequenceMatcher(None, [_norm(w) for w in toks],
                                 [_norm(w) for w in theirs])
    ops = sm.get_opcodes()
    out, log = list(toks), []
    for i, w in enumerate(toks):
        # 对方在这一位是什么
        other = '~'                       # '~' = 对方那里空着
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
            break
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', type=int, required=True, choices=(1, 2))
    ap.add_argument('--pages', required=True, help='如 322-578')
    ap.add_argument('--limit', type=int, default=60)
    a = ap.parse_args()
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
