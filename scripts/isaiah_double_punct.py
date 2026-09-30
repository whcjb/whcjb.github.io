#!/usr/bin/env python3
"""连着两个标点的地方——`father..`、`instruments,.`、`Piscator)..`。

诗篇那边有 `psalms_double_punct.py` 管这一类，以赛亚一直没有，于是
`en_chapters` 里 16 处句号重出（`etc..`、`vs.. 10, 11`）从 OCR 阶段一路
带到了发布正文，十七道闸一个也看不见：判词典按空白分段找非词，`..`
两边都是好词，标点自己不构成一个段。

两处不同于诗篇，都是以赛亚自己的形态逼出来的：

**① 两个标点之间不许隔空白。** 以赛亚正文里有印面原有的省略号
`. . . . . .`（拉丁引文里省略整句，第 14、41 章共 6 处），诗篇的
`[*\\s]{0,3}` 会一路把它认成双标点，并掉其中一个点就把印面啃掉了。
实测真正的双标点没有一处中间隔空白，所以separator 收紧成只许 `*`（斜体标记）。

**② 一律要证人，不做「同一个标点重了就并掉」的无证据合并。**
诗篇可以这么干，以赛亚不行：满篇希伯来/希腊活字的 OCR 残渣里到处是
`fir-:;:::`、`t::r`、`re»:` 这种连着的冒号分号，它们不是标点读重了，
是那里根本不是标点。九份证人在同一位置读出的东西对不上，就自动出局。

安全闸与残留串那一路同一条：**只接受标点级的改动**。证人切片与我们这串
剥掉标点之后必须逐字相同，而且证人给出的那个标点必须**就是我们这两个
里的一个**，否则宁可留账——证人是另几家馆藏的独立扫描件，也会各自读崩。

用法：
    python3 scripts/isaiah_double_punct.py            # 只报告
    python3 scripts/isaiah_double_punct.py --apply    # 追加进 manual_fixes.tsv 并落盘
"""
import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_alexander_image as A
import alexander_lexicon as L
from adjudicate_alexander_isaiah import SECTION_VOL, WITNESSES

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/isaiah'
WSRC = ROOT / 'alexander_raw/isaiah/src'
FIXES = ROOT / 'alexander_raw/isaiah/manual_fixes.tsv'
OUT = ROOT / 'logs/alexander_isaiah_double_punct.tsv'

# 数字也算一个词：证人切片少一截数字照样能过字母闸，节号就那么丢了
# （诗篇那边踩过 6 处，全是经文出处）。
WORD = re.compile(r"[A-Za-z][A-Za-z'’]*|[0-9]+")
ANCHOR = 3          # 几个词做一个锚
REACH = 5           # 目标词前后各在几个词的窗口里找锚
MAX_HITS = 40       # 锚在证人语料里命中超过这个数就太泛，不用
TAIL = ',.;:!?)\'"'  # 词后面这些符号算这一串的一部分
MIN_VOTES = 2       # 至少两份证人给出同一读数
PUNCT = ',;:.'

# 两个标点之间只许隔斜体星号，**不许隔空白**（见模块开头 ①）。
# 前后都不许再挨着一个点：`Lord...` 命中之后并成 `Lord..`，把印面上的
# 省略号啃掉一个点。
CLUSTER = re.compile(r'(?<!\.)[,;:.]\*{0,3}[,;:.](?!\.)')
ROMAN = re.compile(r'^[ivxlcdm]+$', re.I)
LEX = L.build()
ABBREV = {a.lower() for a in A.ABBREV} | {'etc', 'ad', 'loc', 'ed', 'vo', 'fol'}


def is_abbrev(w):
    """这个词后面那个句点是**缩写的点**，不是句号。

    `Ps.` `&c.` `etc.` `sq.` 这些是现成的表；书里还有满地的临时缩写
    （`Henders.` `Soncin.` `Observ.` `Ew.`）——判据是「它不是一个英文词」：
    `places.` 里的 places 是词，那个点就是句号；`Soncin.` 不是词，是缩写。
    """
    t = w.lower()
    return (t in ABBREV or len(t) == 1 or ROMAN.match(t)
            or not L.is_word(w, LEX) or w[:1].isdigit())


def clean_side(w):
    """这一侧挨着的是正经英文，不是希伯来/希腊活字的 OCR 残渣。

    以赛亚正文里到处是 `fir-:;:::`、`t::r`、`spu:,`、`,:rsn` 这种——
    连着的冒号分号不是标点读重了，是那里根本不是标点。**并掉一个就是
    改坏印面**，所以两侧但凡有一侧不是词，一律不碰。
    """
    if not w:
        return False
    return (w[:1].isdigit() or L.is_word(w, LEX)
            or w.lower() in ABBREV or bool(ROMAN.match(w)))


def suspicious(prev_word, next_word, cluster):
    """这一处的双标点值不值得查。"""
    if not clean_side(prev_word) or not clean_side(next_word):
        return False
    flat = re.sub(r'[^,;:.]', '', cluster)
    if flat[0] == '.' and flat != '..':
        # `Ps. xcvii., but`、`&c.; the grass`、`q. d.: such are` 都是正经的：
        # 缩写的点 + 分句的标点。全书八十多处，前面那个词是缩写就放行。
        return not is_abbrev(prev_word)
    return True


def letters(s):
    return re.sub(r'[^A-Za-z0-9]', '', s).lower()


def load_witnesses():
    """{卷: [(名字, 原文, 词表, 锚索引), ...]}"""
    out = defaultdict(list)
    for vol, names in WITNESSES.items():
        for name in names:
            path = WSRC / f'{name}.txt'
            if not path.exists():
                print(f'⚠ 证人缺失，跳过: {name}')
                continue
            text = path.read_text(encoding='utf-8', errors='replace')
            toks = [(m.group(0), m.start(), m.end()) for m in WORD.finditer(text)]
            low = [t[0].lower() for t in toks]
            idx = defaultdict(list)
            for i in range(len(low) - ANCHOR):
                idx[tuple(low[i:i + ANCHOR])].append(i)
            out[vol].append((name, text, toks, idx))
    return out


def slice_at(text, toks, j):
    """证人在第 j 个词上印的原文，连同紧跟其后的标点。"""
    a, b = toks[j][1], toks[j][2]
    while b < len(text) and text[b] in TAIL:
        b += 1
    return text[a:b]


def read_one(low, k, wit):
    """一份证人在 toks[k] 这个位置上印的是什么（连标点）；给不出就 None。"""
    _, text, wtoks, widx = wit
    cand = set()
    for start in (list(range(k - REACH, k - ANCHOR + 1))
                  + list(range(k + 1, k + 1 + REACH))):
        if start < 0 or start + ANCHOR > len(low):
            continue
        if not (start + ANCHOR <= k or start > k):
            continue
        hits = widx.get(tuple(low[start:start + ANCHOR]))
        if not hits or len(hits) > MAX_HITS:
            continue
        d = k - start
        here = {slice_at(text, wtoks, p + d)
                for p in hits if 0 <= p + d < len(wtoks)}
        if len(here) == 1:
            cand |= here
    return cand.pop() if len(cand) == 1 else None


def poll(low, k, wits):
    """九份证人多数表决 → (读数, 票数, 参与数, 说明)"""
    votes = Counter()
    for w in wits:
        r = read_one(low, k, w)
        if r:
            votes[r] += 1
    if not votes:
        return None, 0, 0, '证人都给不出这一处'
    top, n = votes.most_common(1)[0]
    if len(votes) > 1 and votes.most_common(2)[1][1] == n:
        return None, 0, sum(votes.values()), f'证人平票：{sorted(votes)[:3]}'
    if n < MIN_VOTES:
        return None, n, sum(votes.values()), f'只有 {n} 份证人给出 {top!r}'
    return top, n, sum(votes.values()), f'{n}/{sum(votes.values())} 份证人读作 {top!r}'


def vol_of(sec):
    if sec in SECTION_VOL:
        return SECTION_VOL[sec]
    return 'v1' if sec.isdigit() and int(sec) <= 39 else 'v2'


def scan():
    """找出所有双标点，连同它前面那个词。"""
    out = []
    for p in sorted(SRC.glob('*.md')):
        sec = p.stem
        raw = p.read_text(encoding='utf-8')
        start = raw.find('<!-- PAGE ')
        if start < 0:
            start = 0
        masked = A._mask_markup(raw)
        toks = [(m.group(0), m.start(), m.end()) for m in WORD.finditer(masked)]
        low = [t[0].lower() for t in toks]
        ends = {t[2]: k for k, t in enumerate(toks)}
        for m in CLUSTER.finditer(masked, start):
            j = m.start()
            while j > 0 and j not in ends:
                if not masked[j - 1].isspace() and masked[j - 1] not in '*)]':
                    break
                j -= 1
            k = ends.get(j)
            if k is None:
                continue
            # 同一个词在标点后面又出现一遍（跨行重出），并掉标点只会留下重复的词
            after = masked[m.end():m.end() + len(toks[k][0]) + 2].strip()
            if after.lower().startswith(toks[k][0].lower()):
                continue
            nx = WORD.search(masked, m.end())
            if not suspicious(toks[k][0], nx.group(0) if nx else '', m.group(0)):
                continue
            out.append(dict(sec=sec, path=p, raw=raw, masked=masked, low=low,
                            tok=k, word=toks[k][0],
                            a=toks[k][1], b=m.end(),
                            span=raw[toks[k][1]:m.end()]))
    return out


def collapse(span, tok, read, nxt=''):
    """定出这一处该留哪个标点。**只准删标点**，不准加、不准换、不准碰排版符号。

    返回 (新串, 说明) 或 (None, 留账原因)。
    """
    tail = span[len(tok):]
    marks = [i for i, c in enumerate(tail) if c in PUNCT]
    if len(marks) < 2:
        return None, '没有两个标点'
    chars = [tail[i] for i in marks]
    wit = ''.join(c for c in read[len(tok):] if c in PUNCT)
    if len(wit) > 1:
        return None, f'证人读数 {read!r} 自己也是双标点'
    if len(wit) == 0:
        return None, f'证人读数 {read!r} 这里一个标点也没有'
    if wit not in chars:
        return None, f'证人读数 {read!r} 不在我们这两个标点之内'
    keep = [marks[chars.index(wit)]]
    out = tok + ''.join(c for i, c in enumerate(tail)
                        if c not in PUNCT or i in keep)
    # 被删掉的那个标点如果本来兼着词距的活儿（`him,.in`），删完得把空格补回来
    if nxt[:1].isalnum() and not out.endswith((' ', '*')):
        out += ' '
    return (None, '与原串相同') if out == span else (out, f'证人留的是 {wit!r}')


def unique_anchor(book, raw, a, b):
    """把左边界往前挪，直到这一串在**全书**正文里只出现一次。

    修复表没有章号这一列，是按字面串在全书上替换的；`isaiah_fixes_lint.py`
    的第二条判据也是按全书数命中次数。只在本章里唯一是不够的。
    """
    for pad in (0, 18, 40, 80):
        head = raw[max(0, a - pad):a]
        if book.count(head + raw[a:b]) == 1:
            return head, raw[a:b]
    return None, None


def main(apply=False):
    wits = load_witnesses()
    items = scan()
    print(f'双标点 {len(items)} 处')
    stat, add, rows = Counter(), [], []
    for it in items:
        read, n, tot, why = poll(it['low'], it['tok'], wits[vol_of(it['sec'])])
        if read is not None and letters(read) != letters(it['word']):
            read, why = None, f'证人读数 {read!r} 字母对不上 {it["word"]!r}'
        if read is None:
            stat['留账'] += 1
            rows.append((it['sec'], it['span'], '', why))
            continue
        nxt = it['raw'][it['b']:it['b'] + 1]
        out, note = collapse(it['span'], it['word'], read, nxt)
        if out is None:
            stat['留账'] += 1
            rows.append((it['sec'], it['span'], '', f'{why}；{note}'))
            continue
        stat['可改'] += 1
        rows.append((it['sec'], it['span'], out, f'{why}；{note}'))
        add.append((it, out))
    print('，'.join(f'{k} {v}' for k, v in stat.most_common()))
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open('w', encoding='utf-8') as fh:
        fh.write('章\t我们\t改成\t说明\n')
        for r in rows:
            fh.write('\t'.join(x.replace('\n', ' ') for x in r) + '\n')
    print(f'逐条 → {OUT}')
    if not apply:
        for it, out in add:
            print(f'  [{it["sec"]}] {it["span"]!r} → {out!r}')
        return
    n = skip = 0
    lines = []
    book = ''.join(p.read_text(encoding='utf-8') for p in sorted(SRC.glob('*.md')))
    for it, out in add:
        span, b = it['span'], it['b']
        # 补回来的词距若落在串尾，把后面那个词也收进来：TSV 里行尾的空格
        # 靠不住（编辑器、git 的 whitespace 钩子都可能把它抹掉），而
        # `Egypt,.and` → `Egypt, and` 少了那个空格就是两个词黏在一起。
        if out.endswith(' '):
            m = WORD.search(it['raw'], b)
            if m and m.start() == b:
                span, out, b = span + m.group(0), out + m.group(0), m.end()
        head, tail = unique_anchor(book, it['raw'], it['a'], b)
        if head is None:
            skip += 1
            continue
        old, new = head + tail, head + out
        text = it['path'].read_text(encoding='utf-8')
        if text.count(old) != 1:
            skip += 1
            continue
        lines.append(f'{old}\t{new}\tdblpunct: 证人按位置读出这一处只有一个标点')
        it['path'].write_text(text.replace(old, new, 1), encoding='utf-8')
        n += 1
    if lines:
        # 追加前先确认表是以换行收尾的：少这一步，第一条新规则会与最后一行
        # 粘成一行，两条规则**一起失效**，而且修复表自检看不出来
        # （粘出来的那行 parts[0]/parts[1] 照样解析得出，只是后半截没了）。
        cur = FIXES.read_text(encoding='utf-8')
        with FIXES.open('a', encoding='utf-8') as fh:
            if cur and not cur.endswith('\n'):
                fh.write('\n')
            fh.write('\n'.join(lines) + '\n')
    print(f'落盘 {n} 处，定位不唯一跳过 {skip} 处')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    main(ap.parse_args().apply)
