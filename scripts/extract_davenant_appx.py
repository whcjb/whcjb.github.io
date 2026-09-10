#!/usr/bin/env python3
"""达文南特卷二后半（注释正文之外的部分）hOCR 行数据 → 结构化 raw。

卷二 622 页里，歌罗西书注释正文只到扫描页 317（书页 308）。其后是四块
**独立文献**，此前一概没有发布（见 DIAGNOSIS.md §2 的「日后另立」）：

    322–324  TO THE KIND READER            1683 年 12mo 版的致读者（Allport 译）
    326–567  A DISSERTATION ON THE DEATH OF CHRIST   序 + 七章，书页 313–558
    570–578  ON THE GALLICAN CONTROVERSY   达文南特论法国改革宗之争，书页 561–569
    580–610  General Index 等六种索引 + ERRATA

本脚本只管前三块（连续散文）。索引是双栏，OCR 行把左右两栏拼成了一行
（`CovNocirs continued. Hospinian ... . «» 540`），必须先按栏切图重跑，
走 scripts/ocr_davenant_cols.py + extract_davenant_index.py。

与 extract_davenant.py 的关系
-----------------------------
几何判据（脚注区、段首缩进、连字合并）整套复用，只换三处：

1. **页眉正则**。原来的两条只认 `EPISTLE TO THE COLOSSIANS` /
   `AN EXPOSITION OF ST. PAUL'S`，本段的页眉是
   `A DISSERTATION ON THE DEATH OF CHRIST` 与 `Chap. i. ON THE ORIGIN…`，
   一条都不命中——实测整行页眉拼进正文中间（`…did not suffer
   Chap.i. ON THE ORIGIN OF THE CONTROVERSY. IT is truly…`）。
2. **脚注区上界放宽**。原规则要求注区起点在页面 25% 以下。Allport 的
   传记体长注在本段能占到**四分之三页**（p329 实测：正文 7 行，注 38 行，
   注区起点在 15%），被这条守卫挡掉，整条注拼进正文。放宽到 12%，
   同时补一条独立守卫：注区字号中位数必须 < 正文区的 0.9 倍
   （p329 是 43/54 = 0.79）。字号与行距是两个不相干的信号，一起卡不会误伤。
3. **缩进阈值逐页算**。本段几个部分的字号差得远——致读者与法国之争是
   大字（x_size≈64），论文正文是小字（≈55）。按整段算一个阈值，大字页的
   段首认得出、小字页认不出（0.55×64=35 > 小字页实际缩进 30）。
   改成按页取该页字号中位数的 0.55 倍，与倾斜无关。

用法:
    python3 scripts/extract_davenant_appx.py --pages 326-352   # 试跑
    python3 scripts/extract_davenant_appx.py                   # 全部
"""
import argparse
import collections
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_davenant as E          # noqa: E402  几何判据整套复用
import davenant_witness as W          # noqa: E402  第二证人（IA OCR 层）

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
VOL = 2

# ── 三块散文的扫描页范围（0-based，含两端）──────────────────────────────
# 边界都按实测定：321/325/569 是空白页或扫描斑点页，318/320/326/570 是
# 半标题与标题页（内容重复，正文里另行处理）。
PIECES = [
    {'id': 'preface',   'lo': 322, 'hi': 324, 'kind': 'plain',
     'title': 'To the Kind Reader'},
    {'id': 'diss',      'lo': 326, 'hi': 567, 'kind': 'chaptered',
     'title': 'A Dissertation on the Death of Christ'},
    {'id': 'gallican',  'lo': 570, 'hi': 578, 'kind': 'plain',
     'title': 'On the Gallican Controversy'},
]

# ── 页眉 ────────────────────────────────────────────────────────────────
# 只对页首前几行试。OCR 把这几句读得很花：`4 DISSERTATION` / `^ DISSERTATION`
# / `<A DISSERTATION` / `ON TIE DEATH` / `DEATH OT CHRIST` / `Chap.1.` /
# `Chip. vi.` / `Chap. ui.`，所以一律只卡中间那个稳定的词根。
HEAD_RES = [
    re.compile(r'D[Il1|]S[SB5]ERTAT[Il1|]ON\s+ON\s+T[HIU]E\s+DEA', re.I),
    re.compile(r'^\s*[^A-Za-z]{0,3}Ch[a@ni][pn][.,;]?\s*[ivxlIVXL]{1,5}\s*[.,;]', re.I),
    re.compile(r'CONTROVERSY\s+AMONG\s+TH[EF]\s+FRENCH', re.I),
    re.compile(r'OP[Il1]N[Il1]ON\s+OF\s+B[Il1]SHOP\s+DAVENANT', re.I),
    re.compile(r'GALL[Il1]CAN\s+CONTROVERSY', re.I),
]
# 章首页重复排的半标题（`A DISSERTATION / ON THE / DEATH OF CHRIST.`）。
# 只在页首 6 行内、居中（x0 > 250）时才剥，正文里同样的字不会误伤。
HALF_TITLE_RE = re.compile(
    r"^[^A-Za-z]{0,3}(A\s+DISSERTATION|ON\s+THE|DEATH\s+OF\s+CHRIST)[.,;'\s]*$", re.I)
CHAP_RE = re.compile(r'^\s*CHAP(?:TER)?[.,;]?\s*([IVXil]{1,5})\s*[.,;:]?\s*$', re.I)
_ROMAN = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7}
ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII'}
# 页脚书帖签名的补充式样。E.is_foot 认不出 `Mem. 11. Z`（`VOL. II. Z` 被
# OCR 读成 Mem/11），漏掉的会当正文单独成段（实测 p348 末尾）。
# 页脚书帖签名的第二种式样：`V Oils, hls 2N` 是 `VOL. II. 2 N` 被 OCR 读花，
# `is_foot` 与 FOOT_EXTRA_RE 都认不出（首字母只有一个 V，中间还夹了逗号）。
# 收得很紧——必须以「数字 + 单个大写字母」收尾——全库只命中这一条与索引里的
# `VOL. 11. 2 Q`；`Verse 17.` / `verse.` 这类不会误伤（实测三份 raw 全扫过）。
SIGNATURE_RE = re.compile(
    r'^[VvNn]\W{0,2}[Oo0Ee]\w{0,3}\W{0,3}\w{0,4}\W{0,3}\s*\d\s?[A-Z]$')
FOOT_EXTRA_RE = re.compile(r'^[A-Za-z]{2,4}[.,]?\s*[Il1V]{1,3}[.,]?\s*[A-Za-z]{1,3}\s?\d?$')
# 章标题（CHAP. N 下面那一两行全大写小字）与卷末的 `END OF THE DISSERTATION.`
END_RE = re.compile(r'^\s*(END OF THE DISSERTATION|FINIS)[.,]?\s*$', re.I)
# 法国之争把达文南特要辩的三条命题排成 `PART I.` / `PART II.` / `PART III.`
# 三个居中小标题。p573/p577 那两条自己成行，p575 那条后面紧跟正文同一段
# （版面上是标题下方接排），不切开三条会长得不一样。
PART_RE = re.compile(r'^\s*PART\s+([IVX]{1,4}|Il|ll)\s*[.,;:]\s*')


def clean_heading(t):
    """标题行的版面碎片。只清三类**确定是扫描噪声**的东西，不改词：

    · 孤立的 `|` `/`：扫描斑点被当成一个字（`| KIND READER.*`、
      `ILLUSTRATED, / AND CONFIRMED`）。
    · 全大写词头上粘的数字：装饰性大写首字母被读成数字
      （`4THE GRACIOUS AND SAVING WILL` —— 原书这里是一个花体 T）。
    · 行末的句读。

    正文里同样的字符一律不动（见 feedback：PDF 版式碎片不做启发式删除），
    这里只对标题动手，是因为标题会印在页面大标题上，一个 `|` 很显眼。
    """
    t = re.sub(r'(?:^|\s)[|/](?=\s|$)', ' ', t)
    t = re.sub(r'\b\d(?=[A-Z]{3,})', '', t)
    return re.sub(r'\s{2,}', ' ', t).strip(' .,;:')


def is_caps(t):
    """整行是否全大写（容 OCR 噪声）。章标题、`PART II.` 这类靠它认。"""
    a = [c for c in t if c.isalpha()]
    return len(a) >= 3 and sum(c.isupper() for c in a) / len(a) >= 0.8


def strip_head(lines, at_chapter_start):
    """剥页眉 + 章首重复半标题。→ (剩余行, 剥掉几行)"""
    n = 0
    for _ in range(3):
        if not lines:
            break
        t = lines[0]['text']
        if any(r.search(t) for r in HEAD_RES):
            lines.pop(0); n += 1; continue
        if E.JUNK_RE.match(t) or E.SPECK_RE.match(t):
            lines.pop(0); continue
        break
    if at_chapter_start:
        for _ in range(4):
            if lines and HALF_TITLE_RE.match(lines[0]['text']) and lines[0]['x0'] > 250:
                lines.pop(0); n += 1
                continue
            break
    return lines, n


def split_page(L):
    """→ (body_lines, fn_lines)。E.split_page 的放宽版，见模块 docstring §2。

    保留原版的三个互为守卫的信号（注区上方一道明显大的空隙、注区内行距偏小、
    区内首行须有脚注符），改动三处：

    1. 注区上界 25% → 12%。Allport 的传记体长注在本段能占到四分之三页
       （p329 实测：正文 7 行、注 38 行，注区起点在 15%），原来那条守卫
       直接把它挡掉，整条注拼进正文。
    2. **参考行距与参考字号都取「候选切点以上那一段」**，不再取页顶前 8 行
       或整页中位数。两处旧写法各有死角：
       · 整页中位数——本段长注占大半页时，中位数已落在注一侧，等于自己跟
         自己比，条件永远不成立（p328/329/330/340-348 实测全漏）。
       · 页顶前 8 行——法国之争首页顶上是六行标题块，行距 121-275，
         算出的参考行距 121.5 把真正的注区空隙 131 顶掉了（p570 实测）。
       取候选切点以上那一段则两种页面都对：它天然就是「正文的行距/字号」。
    3. 多一条字号守卫（注区字号 < 正文区的 0.9 倍）。行距与字号互不相干，
       一起卡不会误伤。

    """
    if len(L) < 8:
        return L, []
    gaps = [L[i + 1]['y0'] - L[i]['y0'] for i in range(len(L) - 1)]
    fallback = [g for g in gaps[:8] if g > 0]
    if not fallback:
        return L, []
    lo = max(2, len(gaps) * 12 // 100)

    def head_stats(head):
        """→ (行距, 字号)，都取候选切点以上那一段的中位数。"""
        hg = [g for g in (head[k + 1]['y0'] - head[k]['y0']
                          for k in range(len(head) - 1)) if g > 0]
        lead = statistics.median(hg) if len(hg) >= 3 else statistics.median(fallback)
        return lead, statistics.median([x['size'] for x in head])

    def ok_zone(head, zone, gap, need_mark):
        if len(zone) < 2 or len(head) < 4:
            return False
        # 脚注符前面常粘着一个扫描斑点（`: * GnEVINCHOVIUS`），放两个字符的余量
        marked = any(E.FN_MARK.match(x['text'])
                     or re.match(r'^\W{1,2}\s*[*+†‡]\s', x['text'])
                     for x in zone[:3])
        if need_mark and not marked:
            return False
        lead, hs = head_stats(head)
        if gap < lead * 1.5:
            return False
        # 空隙**过大**同样不是脚注。没有脚注符时全部证据只有几何，就得要求
        # 几何落在常态区间里：全书 50 个注区的分隔空隙都在 1.5–2.4 倍行距之间，
        # 唯独法国之争 p572 是 4.72 倍——那里根本不是注，是版面从大字正文切到
        # 小字引文（`THE JUDGMENT OF BISHOP DAVENANT`，达文南特原件的引录）。
        # 光看「空隙大 + 字号小」两条，这一整页引文都被吞进了一条脚注（实测）。
        if not marked and gap > lead * 3:
            return False
        zg = [zone[k + 1]['y0'] - zone[k]['y0'] for k in range(len(zone) - 1)]
        if not zg or statistics.median(zg) >= lead * 0.92:
            return False
        # 字号守卫。有脚注符时 0.9 就够——符本身已经是铁证；**没有符**时全部
        # 证据只剩几何，收紧到 0.85：全书 17 个无符注区（跨页续注）的字号比都
        # ≤0.800，而法国之争 p572 那处版面换字号是 0.873——那里根本不是注，是
        # 大字引言切到小字排的达文南特原件引录（`THE JUDGMENT OF BISHOP
        # DAVENANT`，而且这一小字一路排到 p578）。0.9 会把整页引文吞成一条脚注。
        ratio = 0.9 if marked else 0.85
        return statistics.median([x['size'] for x in zone]) < hs * ratio

    best = None
    for need_mark in (True, False):
        for i, g in enumerate(gaps):
            if i < lo:
                continue
            if ok_zone(L[:i + 1], L[i + 1:], g, need_mark):
                best = i + 1
                break
        if best is not None:
            break
    if best is None:
        # 兜底：只有一两行的短注（`* Leontius, Bishop of Arles, according to
        # Du Pin.` / `* Vide Vol. I. page 237, Note.`）。一行的注没有「区内
        # 行距」可比，主规则不触发，整条会当正文单独成段（实测 p340/p348）。
        # 改看另外两个信号：上方那道空隙略大于正常行距，且该行字号明显小于
        # 正文。p348 是空隙 90 / 行距 67（1.34 倍）、字号 43 / 55（0.78 倍）；
        # 正文段落之间在本书不加额外行距，1.3 倍这道坎正文内部不会出现。
        for i in range(len(gaps) - 1, max(len(gaps) * 60 // 100, 3) - 1, -1):
            zone = L[i + 1:]
            if len(zone) > 2 or len(L[:i + 1]) < 4:
                continue
            lead, hs = head_stats(L[:i + 1])
            if gaps[i] < lead * 1.3:
                break
            if all(x['size'] < hs * 0.85 for x in zone):
                best = i + 1
            break
    if best is None:
        return [x for x in L if not E.JUNK_RE.match(x['text'])], []
    return ([x for x in L[:best] if not E.JUNK_RE.match(x['text'])],
            [x for x in L[best:] if not E.JUNK_RE.match(x['text'])])


def para_starts(lines, indent_min):
    """→ 每行是否段首。与 E.para_starts 只差**基线的起手值**。

    E 版用整页 x0 众数起手。本段的页面从页顶到页尾能斜 45 px（p393 实测
    225 → 182），众数落在页尾一侧（185），页顶那几行相对它凸出 40 px >
    缩进阈值 31，全被判成段首；而段首行按规则不进基线，基线就一直卡在
    185 解不开——直到第 9 行 x0 掉到 215 才恢复，页顶 8 行被切成 8 个独立
    段落（p393 / p425 实测，正文中间凭空多出七处断段）。

    改用**前 5 行 x0 的中位数**起手：一页最多一两个段首，前 5 行的中位数
    必然取到续行，且与页面倾斜同侧。往后仍按「相对最近 5 行续行的中位数
    凸出一个 em」判，与整页倾斜无关。
    """
    if not lines:
        return []
    seed = statistics.median([l['x0'] for l in lines[:5]])
    recent = collections.deque(maxlen=5)
    out = []
    for l in lines:
        base = statistics.median(recent) if len(recent) >= 3 else seed
        start = l['x0'] - base > indent_min
        out.append(start)
        if not start:
            recent.append(l['x0'])
    return out


def shape(body):
    """→ 每行的版式角色 list，取值 '' / 'verse' / 'cite'。**全靠几何**。

    原书用缩进区分三种东西，OCR 层没有字形信息但**坐标是准的**：

        正文        x0 = 左边界，段首多缩一个 em（相对宽度约 0.04）
        引诗        x0 比左边界多缩 0.08–0.13 个版心宽，且右边参差不齐
        出处行      x0 落在版心右半（0.5 以上），如 `Cap. 10, &c.` / `Cap. 13.`

    不做这一步的代价是实打实的错，不只是难看：出处行 `Cap. 10, &c.` 单独一行
    右对齐，按正文合并规则会被接到**下一段的开头**，读者看到的是
    `Cap. 10, &c. Yet the same Prosper says…`（实测 p338/p339 两处）。

    引诗按**行组**判而不是逐行判：法国之争里三条 PART 的引录也是整块缩进的，
    但那是散文——它右边是齐的（右余 ≈ 0.01），引诗右边参差（0.08–0.77）。
    一行一行看会把引录的末行（短行）也当成诗；成组看，组内多数行参差才算诗。
    """
    if len(body) < 6:
        return [''] * len(body)
    left = statistics.median([l['x0'] for l in body])
    right = statistics.median([l['x1'] for l in body])
    w = right - left
    if w <= 0:
        return [''] * len(body)
    rel = [(l['x0'] - left) / w for l in body]
    rag = [(right - l['x1']) / w for l in body]
    out = ['cite' if rel[i] > 0.5 else '' for i in range(len(body))]
    ind = [0.08 < rel[i] <= 0.5 and not is_caps(body[i]['text'])
           for i in range(len(body))]
    i = 0
    while i < len(body):
        if not ind[i]:
            i += 1
            continue
        j = i
        while j < len(body) and ind[j]:
            j += 1
        run = range(i, j)
        if j - i >= 2 and sum(rag[k] >= 0.05 for k in run) >= (j - i) * 0.6:
            for k in run:
                out[k] = 'verse'
        i = j
    return out


def page_indent(lines):
    """本页的段首缩进阈值 = 该页字号中位数 × 0.55。见模块 docstring §3。"""
    if not lines:
        return 30
    return max(12, int(round(statistics.median([l['size'] for l in lines]) * 0.55)))


def run_piece(pc, pages, out, stats):
    chap_starts = set()
    if pc['kind'] == 'chaptered':
        for p in range(pc['lo'], pc['hi'] + 1):
            for l in pages.get(p, []):
                if CHAP_RE.match(l['text']) and l['x0'] > 350:
                    chap_starts.add(p)

    out.append(f"[SEC] {pc['id']}|{pc['title']}")
    cur, cur_pages = '', set()
    pend_title = []                    # CHAP 之后待收的全大写标题行
    fns = []

    def flush():
        nonlocal cur, cur_pages
        if cur:
            pg = (f'<!--v{VOL}p{min(cur_pages)}-->' if len(cur_pages) == 1
                  else f'<!--v{VOL}p{min(cur_pages)}-{max(cur_pages)}-->')
            out.append(f'[BODY] {pg}{E.fix_label(cur)[0]}')
            stats['para'] += 1
        cur, cur_pages = '', set()

    for p in range(pc['lo'], pc['hi'] + 1):
        lines = sorted(pages.get(p, []), key=lambda r: r['y0'])
        if not lines:
            continue
        lines, nh = strip_head(lines, p in chap_starts)
        stats['head'] += nh
        for _ in range(2):
            t_last = lines[-1]['text'].strip()
            if lines and (E.is_foot(t_last) or FOOT_EXTRA_RE.match(t_last)
                          or E.is_signature(lines[-1])
                          or (len(t_last) <= 18 and SIGNATURE_RE.match(t_last))):
                lines.pop(); stats['foot'] += 1
                continue
            break
        if not lines:
            continue
        body, fn = split_page(lines)
        if fn:
            fns.append((p, fn))
            stats['fn_pages'] += 1
        indent = page_indent(body)
        roles = shape(body)
        for l, is_start, role in zip(body, para_starts(body, indent), roles):
            raw = E.fix_enum_head(l['text']) if is_start else l['text']
            t = E.clean(W.fix_line(VOL, p, raw)[0])
            if not t:
                continue
            if role in ('verse', 'cite') and not pend_title:
                flush()
                out.append(f'[{role.upper()}] <!--v{VOL}p{p}-->{t}')
                stats[role] += 1
                continue
            m = CHAP_RE.match(t)
            if m and l['x0'] > 350:
                flush()
                n = _ROMAN.get(m.group(1).lower().replace('l', 'i'))
                # 标签从解析出的序号回写，不用 OCR 原串：`CHAPTER II` 常被
                # 读成 `CHAPTER IL`，原样输出会印在页面标题上。
                out.append(f'[H1] {n or m.group(1)}|'
                           f'CHAPTER {ROMAN.get(n, m.group(1).upper())}')
                stats['chap'] += 1
                pend_title = []
                continue
            if pend_title is not None and is_caps(t) and l['x0'] > 150 and not cur:
                # CHAP 之后的全大写行是章标题，可能排成两三行
                pend_title.append(t.rstrip('.,'))
                continue
            if pend_title:
                out.append('[H2] ' + clean_heading(' '.join(pend_title)))
                pend_title = []
            m = PART_RE.match(t)
            if m:
                flush()
                out.append(f'[H3] PART {m.group(1).upper().replace("L", "I")}.')
                rest = E.clean(t[m.end():])
                if rest:
                    cur, cur_pages = rest, {p}
                continue
            if END_RE.match(t):
                flush()
                out.append(f'[END] {t}')
                continue
            if is_start:
                flush()
                cur, cur_pages = t, {p}
            elif cur:
                cur = E.dehyph(cur, t)
                cur_pages.add(p)
            else:
                cur, cur_pages = t, {p}
        stats['pages'] += 1
    if pend_title:
        out.append('[H2] ' + clean_heading(' '.join(pend_title)))
    flush()

    for p, fn in fns:
        indent = page_indent(fn)
        cur_fn = ''
        for l, is_start in zip(fn, para_starts(fn, indent)):
            raw = E.fix_enum_head(l['text']) if is_start else l['text']
            t = E.clean(W.fix_line(VOL, p, raw)[0])
            if not t:
                continue
            if (is_start or E.FN_MARK.match(t)) and cur_fn:
                out.append(f'[FN] <!--v{VOL}p{p}--> {cur_fn}')
                stats['fn'] += 1
                cur_fn = t
            elif cur_fn:
                cur_fn = E.dehyph(cur_fn, t)
            else:
                cur_fn = t
        if cur_fn:
            out.append(f'[FN] <!--v{VOL}p{p}--> {cur_fn}')
            stats['fn'] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', help='如 326-352，只跑落在该区间内的部分')
    a = ap.parse_args()
    pages = {r['page']: r['lines'] for r in E.load(VOL)}

    plan = PIECES
    if a.pages:
        lo, hi = (int(x) for x in a.pages.split('-'))
        plan = [dict(pc, lo=max(pc['lo'], lo), hi=min(pc['hi'], hi))
                for pc in PIECES if pc['lo'] <= hi and pc['hi'] >= lo]

    out, stats = [], collections.Counter()
    for pc in plan:
        run_piece(pc, pages, out, stats)

    dst = RAW / ('davenant_colossians_appendix.txt' if not a.pages
                 else 'appendix_sample.txt')
    dst.write_text('\n'.join(out) + '\n', encoding='utf-8')
    print(f'[ok] → {dst.name}  {dst.stat().st_size:,} 字节  {len(out)} 行')
    print(f'  章 {stats["chap"]} · 段落 {stats["para"]} · 引诗 {stats["verse"]}'
          f' · 出处行 {stats["cite"]} · 脚注 {stats["fn"]}'
          f'（{stats["fn_pages"]} 页）· 剥页眉 {stats["head"]} · '
          f'剥页脚 {stats["foot"]} · 共 {stats["pages"]} 页')
    return 0


if __name__ == '__main__':
    sys.exit(main())
