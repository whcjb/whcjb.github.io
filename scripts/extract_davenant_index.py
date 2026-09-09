#!/usr/bin/env python3
"""达文南特卷二末尾六种索引 + ERRATA → 结构化 raw。

输入  davenant_raw/colossians/vol2_cols_580_603.jsonl（双栏页，按栏 OCR）
      davenant_raw/colossians/vol2_lines.jsonl       （单栏页，整页 OCR）
输出  davenant_raw/colossians/davenant_colossians_index.txt

条目怎么分行
------------
索引不是散文，不能按「缩进的那行是段首」来分——版式正好相反：**条目顶格，
回行缩进**（悬挂缩进）。而且不止两级：

    General Index / 传略索引 / 注中人事索引 / 问题索引   两级：条目、回行
    经文索引                 三级：书卷+节、同卷下一节、回行
    论文目录                 三级：章、章内小节、回行
    ERRATA                   三级：`Page N` 起首、同段下一处、回行

各级的绝对缩进量逐块不同（字号不同、扫描件平移不同），写死像素值必错。
改法分两趟：先把每行归类（标题 / 说明 / 小标题 / 栏头 / 字母分隔 / 条目），
再只拿**条目行**的 x0 做聚类——x0 先减去该页该栏自己的左边界以消掉平移与
歪斜，然后按「两侧都够密的最大间隙」切成至多三簇，簇序即缩进级别。

⚠️ 聚类必须排除非条目行。第一版把标题页整幅标题、栏头一起丢进去聚，
居中排的标题行 x0 能偏出 500 px，最大间隙全落在这些离群值上，切点算到
277/422（真正的界在 35 附近），于是整块索引每一行都成了独立条目、
回行一条也没并（实测 2560 条，实际约 1400 条）。

用法: python3 scripts/extract_davenant_index.py
"""
import collections
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_davenant as E                       # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
COLS = RAW / 'vol2_cols_580_603.jsonl'
WHOLE = RAW / 'vol2_lines.jsonl'

# 0-based 扫描页号。cols=True 的走按栏 OCR 那份数据。
# head = 该块开头要丢掉的整幅标题行数（逐页核过原图；标题另由 title/sub 给出）。
PIECES = [
    {'id': 'index-general', 'lo': 580, 'hi': 595, 'cols': True, 'head': 3,
     'title': 'General Index', 'sub': 'of Subjects in the Exposition'},
    {'id': 'index-questions', 'lo': 596, 'hi': 597, 'cols': False, 'head': 3,
     'title': 'Index of Questions',
     'sub': 'incidentally and briefly determined in the work'},
    {'id': 'contents-dissertation', 'lo': 598, 'hi': 598, 'cols': False,
     'head': 3, 'title': 'Contents of the Dissertation',
     'sub': 'on the extent of the death of Christ'},
    {'id': 'index-biographical', 'lo': 599, 'hi': 601, 'cols': True, 'head': 6,
     'title': 'Index to the Biographical Sketches',
     'sub': 'of Fathers, Heresiarchs, Schoolmen, &c., appended by the Translator',
     'leaders': True},
    {'id': 'index-notes', 'lo': 602, 'hi': 603, 'cols': True, 'head': 5,
     'title': 'Index of Subjects and Works',
     'sub': 'incidentally glanced at in the Notes'},
    {'id': 'index-scripture', 'lo': 604, 'hi': 609, 'cols': False, 'head': 4,
     'title': 'Index of Passages of Scripture', 'sub': 'explained by the way'},
    {'id': 'errata', 'lo': 610, 'hi': 610, 'cols': False, 'head': 1,
     'title': 'Errata', 'sub': ''},
]

# 字母分隔（`A.` / `D.` / `IL.`）：原书排在栏中央，x0 落在回行那一簇里，
# 不先认出来会被当成上一条的回行并进去。
LETTER_RE = re.compile(r'^\s*[A-Z]{1,3}\s*[.,;:]?\s*$')
# 栏头：`Vol. I.| II.` / `Text |Note` / `PAGE.` / `VOL. PAGE.` / `CHAP. PAGE.`
CAPTION_RE = re.compile(
    r'^\s*(?:[A-Z]\.\s*)?Vol[.,]\s*[Il1]|^\s*Text\s*[|I]?\s*Note'
    r'|^\s*(?:CHAP\.?\s*|VOL[.,]?\s*)?PAGE[.,]?\s*$', re.I)
# 块内小标题：`IN THE EXPOSITION OF CHAPTER I.`（问题索引按注释章分节）、
# `IN VOL. I.`（ERRATA 分卷）。整行大写且不含小写实词。
SUBHEAD_RE = re.compile(r'^\s*IN\s+(?:THE\s+EXPOSITION|VOL)', re.I)
# 译者说明：原书用方括号或 ☞ 引出，说明这份索引是 Allport 增补的
NOTE_RE = re.compile(r'^\s*[\[(]|^\s*\S{0,3}\s*Those names printed', re.I)
# 页脚书帖签名的第二种式样：`V Oils, hls 2N` 是 `VOL. II. 2 N` 被 OCR 读花，
# `is_foot` 与 FOOT_EXTRA_RE 都认不出（首字母只有一个 V，中间还夹了逗号）。
# 收得很紧——必须以「数字 + 单个大写字母」收尾——全库只命中这一条与索引里的
# `VOL. 11. 2 Q`；`Verse 17.` / `verse.` 这类不会误伤（实测三份 raw 全扫过）。
SIGNATURE_RE = re.compile(
    r'^[VvNn]\W{0,2}[Oo0Ee]\w{0,3}\W{0,3}\w{0,4}\W{0,3}\s*\d\s?[A-Z]$')
HEAD_RES = [
    re.compile(r'GENERAL\s+[Il1]NDEX', re.I),
    re.compile(r'[Il1]NDEX\s+(?:TO|OF)\s+(?:B[Il1]OGRAPH|QUEST[Il1]ONS|'
               r'SUBJECTS|PASSAGES)', re.I),
    re.compile(r'[Il1]NDEX\s+OF\s+SUBJECTS\s+[Il1]N\s+T[HIU]', re.I),
    re.compile(r'EXPLA[Il1]NED\s+[Il1]N\s+THE\s+EXPOS[Il1]T[Il1]ON', re.I),
]


# 引点线（`Abelard  ...  ...  435` 里那两串点）在 OCR 下碎成 `oo oca` /
# `coo oco` / `000 000` / `e. —` 这类垃圾词。只在**传略索引**里收拾它：
# 那一块的条目是「专名 + 页码」，没有散文，误吃真词的风险按版式就排除了。
# 其余几块的条目是句子（`Whether our love is God himself …`），同样的规则
# 会把 was / man / one 这类小写实词当成引点吃掉，一律不动。
LEADER_TOK = re.compile(r"^[a-z.,;:_|\"'\-—–=~*()]{1,4}$")
LEADER_KEEP = {'de', 'of', 'le', 'la', 'du', 'van', 'von', 'di', 'da', 'el'}


def strip_leaders(t):
    """把「行尾 / 末位数字之前」那一串引点垃圾收成一个 …。

    只收**贴着行尾或贴着末位数字**的那一串——`Altissiodorensis, alias
    William Bp. of Auxerre 68` 里的 `of` 后面跟着大写的 Auxerre，串就断了，
    不会被吃。`Alphonsus de Castro` 同理。
    """
    toks = t.split()
    i = len(toks)
    # 末位是页码就从它前面往回收；`000` 这种全零的不是页码，是引点被读成了零
    if i and re.match(r'^\d', toks[-1]) and not re.fullmatch(r'0+', toks[-1]):
        i -= 1
    j = i
    while j > 1 and (LEADER_TOK.match(toks[j - 1])
                     and toks[j - 1].strip('.,;:') not in LEADER_KEEP
                     or re.fullmatch(r'0+', toks[j - 1])):
        j -= 1
    if j == i:
        return t
    # 第一串引点常被 OCR 粘在名字尾巴上（`Ambrose...` / `Aquinas...`）
    head = toks[:j]
    if head:
        head[-1] = re.sub(r'\.{2,}$', '', head[-1])
    return ' '.join(head + ['…'] + toks[i:])


def load(path):
    return {json.loads(l)['page']: json.loads(l)['lines']
            for l in Path(path).open(encoding='utf-8')}


def breaks(vals, unit):
    """→ 至多两个切点，把归一化 x0 切成至多三簇。按「两侧都够密的最大间隙」找。

    「两侧都够密」这条守卫不能省：索引里总有零星几行排到很右边（页码孤行、
    表格式的双栏数字），单看间隙大小，最大的那几个全在这些离群值旁边。
    要求切点两侧各占至少 8%，间隙才作数。

    也试过按 `round((x0-margin)/em)` 直接算级别——不行：各块的级差不是整数倍
    em（经文索引是 +110 / +321 px，em 才 27），硬除会把三级压成两级。
    """
    xs = sorted(vals)
    n = len(xs)
    if n < 12:
        return []
    cand = []
    for i in range(n - 1):
        if min(i + 1, n - i - 1) < n * 0.08:
            continue
        g = xs[i + 1] - xs[i]
        if g > unit * 0.8:
            cand.append((g, xs[i] + g / 2))
    cand.sort(reverse=True)
    cuts = []
    for g, c in cand:
        if all(abs(c - k) > unit for k in cuts):
            cuts.append(c)
        if len(cuts) == 2:
            break
    return sorted(cuts)


def hanging_starts(xs, em):
    """→ 每行是否新条目（悬挂缩进：条目顶格、回行缩进）。局部基线。

    双栏索引不能用「全块一个切点」分条目与回行：条目行的 x0 在一栏之内
    就能漂 45 px（p582 左栏 110→157），与一个 em 的缩进量同量级，两簇在
    直方图上首尾相接，没有间隙可切（实测 index-general 一个切点都找不到，
    整块 1810 行全成了独立条目）。

    ⚠️ 基线要跟着**条目行**走，不能跟着回行走。先写成「回行占多数，拿最近
    几行的 x0 中位数当回行基线，比它靠左的是条目」，在 General Index 上对
    （条目只占 20%），到传略索引就垮了——那份索引一条一行、回行不到 5%，
    基线取不到回行，几乎每一行都被判成回行并进上一条（实测整栏并成一条
    `Abelard oo oca Abbot, Robert … Albert coo oco 148 …`）。
    改成反过来：基线 = 最近几个**条目**的 x0 中位数，比它右缩一个 em 以上的
    才算回行。条目是版面的锚（顶格那一列），两种密度下都成立；基线随倾斜漂，
    与整栏的绝对位置无关。起手值取该栏 x0 的 10 分位——条目再少也在左端。
    """
    import collections as _c
    if not xs:
        return []
    ordered = sorted(xs)
    seed = ordered[max(0, int(len(ordered) * 0.10) - 1)]
    recent, out = _c.deque(maxlen=6), []
    for x in xs:
        base = statistics.median(recent) if len(recent) >= 3 else seed
        start = x <= base + em * 0.8
        out.append(start)
        if start:
            recent.append(x)
    return out


def strip_head(lines):
    n = 0
    for _ in range(2):
        if not lines:
            break
        t = lines[0]['text']
        if any(r.search(t) for r in HEAD_RES):
            lines.pop(0); n += 1; continue
        if E.JUNK_RE.match(t) or E.SPECK_RE.match(t):
            lines.pop(0); continue
        break
    return lines, n


def merge_vol2(main, side):
    """把「卷二页码」那一栏按行高对齐并回主栏。传略索引专用。

    传略索引每半页是个小表：姓名 … │ 卷一页码 ┃ 卷二页码。
    ocr_davenant_cols.py 已按中间那道竖线把两侧分开 OCR（col 标 L / L2），
    这里按 y 把 L2 的数字配回 L 的同一行——竖线两侧是同一行排版，
    y 中心差不超过半个行高。配不上的数字（该行主栏是空行）原样丢弃前先记账。
    """
    lost = 0
    for s2 in side:
        c2 = (s2['y0'] + s2['y1']) / 2
        best = min(main, key=lambda m: abs((m['y0'] + m['y1']) / 2 - c2),
                   default=None)
        if best is None or abs((best['y0'] + best['y1']) / 2 - c2) > \
                (best['y1'] - best['y0']):
            lost += 1
            continue
        best['vol2'] = (best.get('vol2', '') + ' ' + s2['text']).strip()
    return lost


def page_groups(pc, pages):
    """→ [(page, col, [lines])]，双栏页按栏拆，单栏页整页一组。"""
    for p in range(pc['lo'], pc['hi'] + 1):
        ls = pages.get(p, [])
        if not ls:
            continue
        if pc['cols']:
            # 按栏 OCR 的数据已带 col 标记（H 整幅头 / L 左栏 / R 右栏，
            # 传略索引另有 L2 / R2 = 竖线右边的「卷二页码」栏）
            for col in ('H', 'L', 'R'):
                g = [l for l in ls if l.get('col') == col]
                side = [l for l in ls if l.get('col') == col + '2']
                if side:
                    merge_vol2(g, side)
                if g:
                    yield p, col, g
        else:
            yield p, '-', sorted(ls, key=lambda r: r['y0'])


def classify(pc, pages):
    """第一趟：逐行归类。→ [(page, col, line, kind)]，kind ∈ 下列之一。

        head     整幅标题 / 页眉，丢
        note     译者说明，原样保留
        subhead  块内小标题
        caption  栏头
        letter   字母分隔
        entry    条目行（只有这一类进第二趟的 x0 聚类）
    """
    rows, dropped, open_note = [], 0, False
    for p, col, g in page_groups(pc, pages):
        g = list(g)
        # 双栏块的页眉与整幅标题都在 H 带里，栏内（L/R）一行都不用剥。
        # 原来对每一组都跑 strip_head，它那条「顺手丢掉版面碎片」的规则把
        # 栏首单个大写的字母分隔当碎片吃了（p582 的 `C`），额度也数不准，
        # 反过来把总索引的第一条 `Abel, Christ the head of…` 当标题丢掉。
        if col == 'H':
            g, _ = strip_head(g)
            for l in g:
                t = E.clean(l['text'])
                if t and NOTE_RE.match(t):
                    rows.append((p, col, l, t, 'note'))   # 译者说明留下
            continue
        if not pc['cols']:
            g, nh = strip_head(g)
        base = min((l['x0'] for l in g), default=0)
        span = max((l['x1'] for l in g), default=0) - base
        for l in g:
            t = E.clean(l['text'])
            if not t:
                continue
            # ⚠️ 居中的短行先认字母分隔，再走垃圾过滤。JUNK_RE 里
            # `[A-Z]\s?\d?` 与 `\d{1,4}` 两条正好把单个大写的分隔行
            # （`C`）和被读成数字的分隔行（`T` → `186`）当版面碎片丢掉，
            # 总索引因此少了 C、T 两段（实测）。
            centred = bool(span) and (l['x0'] - base) / span > 0.30
            if not (centred and len(t) <= 6):
                if E.JUNK_RE.match(t) or E.SPECK_RE.match(t):
                    continue
                if len(t) <= 18 and SIGNATURE_RE.match(t):   # 页脚书帖签名
                    continue
            # ⚠️ 整幅标题只在**该块的第一页**上丢。原来只数「已丢几行」，
            # 而 strip_head 会先替你剥掉一部分标题行（`GENERAL INDEX` 命中
            # 页眉正则），计数没数够，剩下的额度就落到后面几页的正文头上
            # ——第 582 页的字母分隔 `C` 因此被当标题丢掉了（实测）。
            if not pc['cols'] and p == pc['lo'] and dropped < pc['head']:
                dropped += 1
                rows.append((p, col, l, t, 'head'))
                continue
            if NOTE_RE.match(t) or open_note:
                kind = 'note'
                # 译者说明是整段方括号，跨好几行（经文索引那条占四行）。
                # 只认起首那一行的话，后三行会当成索引条目排进去，读者看到的
                # 第一条是半句话（`ture, not noted in the Original Index…`）。
                open_note = not re.search(r'[\]）)]\s*$', t)
                # 原书用一只印刷用的「☞」引出译者说明，OCR 读成 `Q3"` / `(G5`
                t = re.sub(r'^[^A-Za-z(\[]*[A-Za-z0-9]{0,3}["\']?\s+(?=[A-Z(\[])',
                           '', t)
            elif SUBHEAD_RE.match(t):
                kind = 'subhead'
            elif CAPTION_RE.match(t):
                kind = 'caption'
            elif LETTER_RE.match(t) or (centred and len(t) <= 6):
                # 字母分隔在原书排在栏中央。只认字形（`^[A-Z]{1,3}\.?$`）会漏掉
                # 一大半——OCR 把 `N` 读成 `IN`、`V` 读成 `IE`、`T` 读成 `186`、
                # `Y` 读成 `We`、`P`/`S` 读成小写（实测 26 个分隔只认出 19 个，
                # 漏掉的 5 个当条目印出来，其中 `s.` 是个近乎空的条目）。
                # 居中是版面性质，不吃 OCR 认错字的影响：全块只有分隔行的
                # 居中度 >0.30，条目与回行都在 0.00–0.25。
                kind = 'letter'
            else:
                kind = 'entry'
                if pc.get('leaders'):
                    t = strip_leaders(t)
            rows.append((p, col, l, t, kind))
    return rows


def pick_letters(rows):
    """→ 该保留为字母分隔的行号集合。

    候选是版面上居中的短行，字母取**紧随其后那条条目的首字母**（索引按字母排，
    这是从数据里读出来的，不是照抄 OCR——`N` 被读成 `IN`、`V` 读成 `IE`、
    `T` 读成 `186`、`Y` 读成 `We`，照字形 26 个只认得出 19 个）。

    再取「字母严格递增」的**最长子序列**，其余降回条目。为什么不逐个比
    「必须大于上一个」：只要有一个候选的字母推错并且偏大，它后面的全会被顶掉
    ——传略索引实测就是这样，18 个分隔只剩 BCVW 四个。最长递增子序列容得下
    个别错值，不会让一个错的带塌一片。
    """
    cand = []
    for i, (p, col, l, t, kind) in enumerate(rows):
        if kind != 'letter':
            continue
        # ⚠️ 取**第一条**，不要取前三条的众数：众数会被紧跟其后的次级条目
        # 带偏（总索引 E 段的后三条首字母是 E/I/I，众数给出 I，直接错一格）。
        nxt = next((x[3][:1].upper() for x in rows[i + 1:i + 8]
                    if x[4] == 'entry' and x[3][:1].isalpha()), '')
        if nxt:
            cand.append((i, nxt))
    # 最长严格递增子序列（候选不多，O(n²) 足够）
    best = [1] * len(cand)
    prev = [-1] * len(cand)
    for j in range(len(cand)):
        for k in range(j):
            if cand[k][1] < cand[j][1] and best[k] + 1 > best[j]:
                best[j], prev[j] = best[k] + 1, k
    keep, j = {}, (best.index(max(best)) if cand else -1)
    while j >= 0:
        keep[cand[j][0]] = cand[j][1]
        j = prev[j]
    return keep


def main():
    src_cols, src_whole = load(COLS), load(WHOLE)
    out, stats = [], collections.Counter()

    for pc in PIECES:
        rows = classify(pc, src_cols if pc['cols'] else src_whole)

        # 第二趟：只拿条目行聚类。基线按 (页, 栏) 各算各的，消掉平移与歪斜。
        base, unit = {}, []
        for p, col, l, t, kind in rows:
            if kind != 'entry':
                continue
            k = (p, col)
            base[k] = min(base.get(k, l['x0']), l['x0'])
        for k in base:
            sz = [l['size'] for p, col, l, t, kd in rows
                  if kd == 'entry' and (p, col) == k]
            if sz:
                unit.append(statistics.median(sz) * 0.55)
        em = statistics.median(unit) if unit else 24
        # 双栏块走局部基线（只分两级），单栏块走全局切点（可分三级）。
        # 分开的理由：双栏页一栏之内的倾斜量与缩进量同量级，全局切点切不开；
        # 单栏块（论文目录、经文索引、ERRATA）确实有三级缩进，而它们页少、
        # 倾斜小，全局切点反而干净。
        if pc['cols']:
            cuts, deepest = None, 1
            starts = {}
            for k in base:
                xs = [l['x0'] for p, col, l, t, kd in rows
                      if kd == 'entry' and (p, col) == k]
                starts[k] = dict(zip(range(len(xs)), hanging_starts(xs, em)))
            seen = collections.Counter()
        else:
            norm = [l['x0'] - base[(p, col)] for p, col, l, t, kd in rows
                    if kd == 'entry']
            cuts = breaks(norm, em)
            deepest = max(len(cuts), 1)

        out.append(f"[SEC] {pc['id']}|{pc['title']}|{pc['sub']}")
        cur, cur_p, cur_v2 = '', None, []

        def flush():
            nonlocal cur, cur_p, cur_v2
            if cur:
                # `¦` 之后是原书竖线右边那一栏（卷二页码），发布时另排一列
                v2 = ' '.join(cur_v2).strip()
                out.append(f'[E] <!--v2p{cur_p}-->{cur}' + (f'¦{v2}' if v2 else ''))
                stats['entry'] += 1
            cur, cur_p, cur_v2 = '', None, []

        letters = pick_letters(rows)
        prev_key = None
        for ri, (p, col, l, t, kind) in enumerate(rows):
            if kind == 'head':
                stats['head'] += 1
                continue
            if (p, col) != prev_key:
                flush()          # 条目不跨页/跨栏续行，页眉两边的条目不能粘
                prev_key = (p, col)
            if kind == 'letter':
                if ri in letters:
                    flush()
                    out.append(f'[LETTER] {letters[ri]}')
                    stats['letter'] += 1
                    continue
                kind = 'entry'           # 落选 → 当条目走下去，内容不丢
            if kind in ('note', 'subhead', 'caption'):
                flush()
                tag = {'note': 'NOTE', 'subhead': 'SUBHEAD',
                       'caption': 'CAPTION'}[kind]
                out.append(f'[{tag}] {t}')
                stats[kind] += 1
                continue
            if cuts is None:
                i = seen[(p, col)]
                seen[(p, col)] += 1
                lv = 0 if starts[(p, col)].get(i) else 1
            else:
                lv = sum(1 for c in cuts if l['x0'] - base[(p, col)] > c)
            if lv >= deepest and cur:
                cur = E.dehyph(cur, t)
                if l.get('vol2'):
                    cur_v2.append(l['vol2'])
                continue
            flush()
            cur, cur_p = ('  ' * lv) + t, p
            if l.get('vol2'):
                cur_v2.append(l['vol2'])
        flush()
        print(f"  {pc['id']:<22} 页 {pc['lo']}-{pc['hi']}  em≈{em:.0f}  "
              + ('局部基线（两级）' if cuts is None
                 else f"级别切点 {[round(c) for c in cuts]}"))

    dst = RAW / 'davenant_colossians_index.txt'
    dst.write_text('\n'.join(out) + '\n', encoding='utf-8')
    print(f'[ok] → {dst.name}  {dst.stat().st_size:,} 字节  {len(out)} 行')
    print(f'  条目 {stats["entry"]} · 字母 {stats["letter"]} · '
          f'小标题 {stats["subhead"]} · 栏头 {stats["caption"]} · '
          f'说明 {stats["note"]} · 剥标题 {stats["head"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
