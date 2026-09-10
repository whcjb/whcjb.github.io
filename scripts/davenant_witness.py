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
        # 我方把两个词读粘了：对方那边把它排成**两个** token，直接采信。
        # 这是证据不是猜——`asa memorial` 对面是 `as a memorial`。
        # 不靠「能拆成两个词典词」那种判据：`becometh` / `sumus` / `Johnson`
        # 一样能拆，实测 287 种候选里过半是这种误判。
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', type=int, default=1, choices=(1, 2))
    ap.add_argument('--pages', default='86-631', help='如 322-578')
    ap.add_argument('--limit', type=int, default=60)
    ap.add_argument('--build-splits', action='store_true',
                    help='扫两卷统计粘连词，写 split_votes.json')
    a = ap.parse_args()
    if a.build_splits:
        build_split_table()
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
