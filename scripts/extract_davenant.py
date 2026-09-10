#!/usr/bin/env python3
"""达文南特《歌罗西书注释》hOCR 行数据 → 结构化 raw。

输入  davenant_raw/colossians/vol{1,2}_lines.jsonl（scripts/ocr_davenant.py 产出，
      每行一页，含每个文本行的 bbox / x_size / text）
输出  davenant_raw/colossians/davenant_colossians_structured.txt

为什么走几何+字号而不是纯文本
------------------------------
第一版按空行猜段落、按「页面后 40%」找脚注区，vol1 p88 就翻车：脚注区起点
在 42% 处（Allport 那条编辑长注占了半页），阈值漏掉，脚注被当正文输出。
本书两样东西恰好都有可测的样式信号（vol1 p88 实测，见 DIAGNOSIS.md）：

    脚注   x_size 30–35   ┐ 双峰，谷底在 36
    正文   x_size 37–45   ┘
    段首行 x0 比续行大 ≈ 48 px（续行 ±5），400 dpi 下约合一个 em

⚠️ 不能用「页内字号中位数」做阈值：p88 有 26/44 行是脚注，中位数 34.65
落在脚注一侧。阈值按**卷**做全局校准（直方图找谷底）。

结构标签
--------
    [H1] CHAP. I          歌罗西书章（全书 4 个）
    [SECTION] Verses 3, 4.  节组标题，本书的经节锚点
    [SCRIPTURE] 3|…       该节组的经文，逐节一条（与 KJV 比对定边界）
    [BODY] …              注释正文
    [LEMMA] An Apostle    被注释的词句（原书斜体 + `]` 收尾）
    [FN] …                页脚脚注

用法:
    python3 scripts/extract_davenant.py --vol 1 --pages 86-170   # 试跑
    python3 scripts/extract_davenant.py                          # 全书
"""
import argparse
import collections
import difflib
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import davenant_witness as W                       # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'

# 注释正文页范围（0-based 扫描页号，含两端）。DIAGNOSIS.md §2：
# vol1 前 86 页是 Allport 的达文南特传；vol2 p320 起是另一部著作《论基督之死》。
# ⚠️ vol2 尾页是 317：318 是《论基督之死》的半标题页（"A DISSERTATION /
# ON THE / DEATH OF CHRIST"），写 318 会把它拼到 4 章末尾（实测 4.md 末段
# 出现 "FINIS. A DISSERTATION DEATH OF CHRIST,"）。
RANGES = {1: (86, 631), 2: (14, 317)}

# 页眉：`Ver. 2.  EPISTLE TO THE COLOSSIANS.  35` / `214  AN EXPOSITION
# OF ST. PAUL'S  Chap. iv.`
# ⚠️ 不要去卡左边的 `Ver. N.`——OCR 把它读成 Vers / Verne / Ven / Ver. M.
# 各种花样，写死了会漏（实测 419 个页眉漏掉 77 个，整行页眉被拼进正文中间）。
# 页眉中间那句全大写的书名反而稳，且只在页眉出现（正文写的是 this Epistle），
# 又只拿页首前几行来试，不会误伤正文。
HEAD_RES = [
    re.compile(r'[EKR]?P[Ii1l!|][SB5][TI1l][Ll][EF]\s+T[Oo0]\s+TH[EFRK]\s+C[Oo0][Ll]',
               re.I),
    re.compile(r'[Aa][Nn]\s+EXP[Oo0][Ss5][IiL1l]T[IiL1l][Oo0][Nn]\s+[Oo0]F\s+ST',
               re.I),
]
# 签名/页码等版面碎片：极短、或全大写卷次标记
JUNK_RE = re.compile(r'^\s*(?:[A-Z]\s?\d?|\d{1,4}|VOL[.,]?\s*[IVX0-9]+\.?\s*[A-Z]?\s?\d?'
                     r'|[a-z]\s?\d)\s*$')
# 页脚的书帖签名。JUNK_RE 认不全（`VOL. I. Mm` 的 Mm 是两个字母、
# `Vel. 1. NR` 的 VOL 被读成 Vel），漏掉的会当正文拼进段落中间（实测 14 处）。
# 两种形态，只对**页面末两行**试（有的页把 `VOL. I.` 和签名排成两行）：
#   a) 卷次标记打头：`VOL. I. Zz` / `vol. 1. F` / `VOLL, 11, DAS` / `VOL. II, Q2?`
#      —— OCR 把 VOL 读成 VOLL/VOL,/NOL，签名读成 pd/oc/rf/n1 各种，所以
#      卷次标记之后一律放行到 5 个字符
#   b) 光秃秃的签名：`B 2` / `F f 2` / `Zz` / `x 2` / `GN`
# 正文末行都带标点、且不以 VOL 起首（`Cor. viii. 9.` / `tive details.` /
# `Amen."`），不会命中。
def is_foot(t):
    t = t.strip()
    if len(t) > 20:
        return False
    if re.match(r'^[VvNn][Oo0Ee][LlIi1|,.]{1,2}[.,]?(\s|$)', t):
        return not re.search(r'[a-z]{3,}', t[3:])   # 卷次标记之后不许再有实词
    return bool(re.match(r'^[A-Za-z\[\]|]{1,2}\s?[A-Za-z]?\s?\d?$', t))


# ── 段首结构标签 ────────────────────────────────────────────────────────
# 论文与注释里成对出现的 `OBJECTION 8.` / `REPLY 8.` / `ARGUMENT 4.` /
# `THESIS 4.` 原书排小型大写，OCR 认出二十几种写法：OsjEcTioN、Ossection、
# Oxssection、Onj;EcTION、Opsecrion、Repty、Repry、Rerrv、RreprrLv、
# AncuMENT、Arcument、Tuesis…… 这些是全书最显眼的错字，它们等同于小标题。
#
# 归一按**相似度 + 上下文**：必须落在段首、后面紧跟一个数字加句读
# （`OsjEcTioN 8.`），且与词表中某项的相似度 ≥0.58。上下文这一条是关键守卫，
# 没有它 `Observe,`（正文里 10 处）这类词也会被拖进来。
#
# ⚠️ 词表里**不放 TESTIMONY**：原书自己写的就是缩写 `Test. 1.`，
# 放进去会把 17 处正确的缩写改成 TESTIMONY。
LABELS = ('OBJECTION', 'REPLY', 'ARGUMENT', 'THESIS')
# 原书自己就用的缩写，一律不动（都核过扫描原页）：`Test. 1.`（Testimony，
# 17 处）、`Argum. 4.`（罗马正体，不是小型大写，vol1 p367 核过）、
# `Cap. 10, &c.` 等。不列进来的话 TEST→THESIS、ARGUM→ARGUMENT 会全改错。
LABEL_KEEP = {'TEST', 'ARGUM', 'CAP', 'CHAP', 'PART', 'VER', 'VERS', 'SECT',
              'OBS', 'NOTE', 'ART', 'LIB', 'QU', 'QUEST'}
# 相似度够不着、但按上下文能确认的几条（第三章是 OBJECTION n / REPLY n
# 严格交替，这三条都紧跟在对应的 OBJECTION 之后）
# `OSNJRCRIN` 与 OBJECTION 的相似度只有 0.22，任何阈值都够不着，按上下文
# 记名单：它排在 REPLY 16 之后、REPLY 17 之前，正文写的是「The last
# objection is derived from…」。
LABEL_ALIAS = {'REERVY': 'REPLY', 'RREPRV': 'REPLY', 'RERRV': 'REPLY',
               'OSNJRCRIN': 'OBJECTION'}
# 词里要容数字：OCR 会把字母读成数字（`Osnjrcri0N 17.` 里的 `0` 其实是 `O`），
# 字符类不放数字的话这一条连 LABEL_RE 都匹配不上，别名表再全也用不到。
LABEL_RE = re.compile(r"^([A-Za-z][A-Za-z0-9;,.'’]{2,13})\.?(\s+\d{1,2}\s*[.,])")


def fix_label(t):
    """→ (文本, 改了什么)。段首结构标签归一到原书的小型大写形态。"""
    m = LABEL_RE.match(t)
    if not m:
        return t, None
    key = re.sub(r'[^A-Za-z]', '', m.group(1)).upper()
    if not key or key in LABEL_KEEP:
        return t, None
    best = LABEL_ALIAS.get(key)
    if best is None:
        best = max(LABELS,
                   key=lambda L: difflib.SequenceMatcher(None, key, L).ratio())
        r = difflib.SequenceMatcher(None, key, best).ratio()
        # 相似度够不着时，再给一条「首字母相同 + 长度相近 + 本身不是英文词」
        # 的通道：`Osnjrcri0N 17.` 这种烂到 0.44 的，靠这三条仍能认回 OBJECTION。
        # 「不是英文词」是关键守卫——正文里 `Observe, 3.` 与 OBJECTION 的
        # 相似度也有 0.5，没有这条会被一起改掉。
        if r < 0.58 and not (r >= 0.45 and key[:1] == best[:1]
                             and abs(len(key) - len(best)) <= 3
                             and key.lower() not in DICT_WORDS):
            return t, None
    if m.group(1) == best:
        return t, None
    # key == best 也要改：第二证人常把 `OsjEcTioN` 校成 `Objection`，
    # 拼写对了但大小写不是原书的小型大写，同一章里会一半 OBJECTION、
    # 一半 Objection。一律归到全大写。
    return best + m.group(2) + t[m.end():], (m.group(1), best)


# ── 页脚书帖签名 ────────────────────────────────────────────────────────
# 每 8 页一条 `VOL. I. B` / `VOL. II. 2 N`，OCR 读得千奇百怪：`WEE. 17. Ge`、
# `Mem. 11. Z`、`V Oils, hls 2N`、`HE» 11. c`、`Vigili lus P`、`WOH Vrs 2L`。
# 按字形写规则追不上（is_foot 与 FOOT_EXTRA_RE 加起来仍漏 7 条，混在正文里
# 把句子劈成两半——`the fountain itself WEE. 17. Ge lies hid in Christ`）。
#
# 改按**版面比例**认：签名行「字少、却横跨很宽」——`VOL. II.` 顶在左边、
# 签名字母排在中间，中间是一大片空白。实测每字符宽度：
#     签名行   47–161 px/字（101 条全在 45 以上）
#     正常末行 16–37 px/字（`* Vide page 22.` 16、`THE END.` 37）
# 45 这道坎两边留着一倍余量。再加两条守卫挡真正的正文：
#   · 不含 ≥7 个字母的词（`cal England. :` 这样的正文末行会被挡掉）
#   · 不含任何系统词典里的实词（≥4 字母）
DICT_WORDS = set()
_dw = Path('/usr/share/dict/words')
if _dw.exists():
    DICT_WORDS = {w.strip().lower() for w in _dw.read_text(errors='ignore').split()
                  if len(w.strip()) >= 4}


def is_signature(l):
    """→ 该行是否页脚书帖签名。只对**每页最后一行**试。"""
    t = l['text'].strip()
    if not t or len(t) > 26:
        return False
    if (l['x1'] - l['x0']) / len(t) < 45:
        return False
    toks = re.findall(r'[A-Za-z]+', t)
    if any(len(w) >= 7 for w in toks):
        return False
    return not any(w.lower() in DICT_WORDS for w in toks if len(w) >= 4)


# 扫描斑点被读成孤立一行（`-` / `|` / `]` / `¢`）。它挡在页眉前面时，
# 剥页眉的循环会以为已经剥完（实测 8 个页眉因此整行拼进正文）。
SPECK_RE = re.compile(r'^\s*[^\w\s]{1,3}\s*$|^\s*\w\s*$')
# 节号既有阿拉伯数字（`Verses 3, 4.`）也有罗马数字（`Vers. I.`，vol2 p223；
# 那是原书的排法，不是 OCR 错，600 dpi 对照过 p223，别去"改正"成 1）。
# ⚠️ 数字里混进字形近似的字母：`17` 被读成 `I7`（vol1 p562）。只写
# `\d+|[IVXLivxl]{1,6}` 时，`Verses 16, I7.` 只能吃到 `16,`，标题落成
# `Verses 16,`，`I7.` 掉进经文块开头。混合式必须**含至少一个数字**才认，
# 否则 `Verses is,` 这类正文也会被当节号标题。
_NUMTOK = r'(?:[Il0OS\]\[|]*\d[\dIl0OS\]\[|]*|[IVXLivxl]{1,6})'
# 标题尾巴的 `&c.`（`Vers. 2, &c.`，vol2 p233）要一起吃掉：不吃的话它成了
# 经文池的第一段，另一个 `&c.` 又落成孤立正文段（实测两处都错）。
SECTION_RE = re.compile(r'^\s*Vers?e?s?\.?\s*'
                        r'(' + _NUMTOK + r'(?:\s*[,&]\s*' + _NUMTOK + r')*)'
                        r'\s*[.,;](?:\s*&\s*c\.)?')
_ROMAN = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7,
          'viii': 8, 'ix': 9, 'x': 10, 'xi': 11, 'xii': 12, 'xiii': 13,
          'xiv': 14, 'xv': 15, 'xvi': 16, 'xvii': 17, 'xviii': 18,
          'xix': 19, 'xx': 20, 'xxi': 21, 'xxii': 22, 'xxiii': 23,
          'xxiv': 24, 'xxv': 25, 'xxvi': 26, 'xxvii': 27, 'xxviii': 28,
          'xxix': 29}


# 数字位上的字形回填：`I`/`l` 是 1，`O` 是 0，`S` 是 5。只在**已经确定是
# 数字串**（含至少一个阿拉伯数字）时才用，纯字母串仍按罗马数字解。
# 本书这套字体的 `1` 是「平顶衬线 + 竖杆 + 底座」，OCR 除了读成 `l` / `I`，
# 还常读成 `]`（`Verse ]7.` = Verse 17.、`Verse 2].` = Verse 21.，vol1 p574
# 与 p606，600 dpi 核过）。少了 `]` 这一路，那两节的标题和经文块整个丢掉，
# 落成两段普通正文。
_DIGIT_FIX = str.maketrans({'I': '1', 'l': '1', ']': '1', '[': '1', '|': '1',
                            'O': '0', 'o': '0', 'S': '5'})


def parse_nums(s):
    out = []
    for tok in re.findall(_NUMTOK, s):
        if any(c.isdigit() for c in tok):
            out.append(int(tok.translate(_DIGIT_FIX)))
        elif tok.lower() in _ROMAN:
            out.append(_ROMAN[tok.lower()])
    return out


def render_section(raw, nums):
    """把标题里的号码区按 nums 改写，**只动需要动的那个 token**。

    不做归一：原书这几个词自己就不统一（`Ver.` / `Verse` / `Verses` /
    `Vers.` / `Vers` 都有，p255 那个 `Vers 4.` 确实没有点），标点也照留
    （`Vers. 2, &c.` 的逗号）。尤其是罗马数字的节号——vol2 p223 原书印的
    就是 `CHAP. IV.—Vers. I.`，600 dpi 看过，写成 `Vers. 1.` 反倒是改错。
    只有两种情形才落笔：数字位混进了字母（`I7`→`17`），以及节号被 OCR
    读错、由 KJV 重扫救回（`Vers. 18.`→`Vers. 13.`）。
    """
    m = SECTION_RE.match(raw)
    if not m or not nums:
        return raw.strip()
    toks = list(re.finditer(_NUMTOK, m.group(1)))
    if len(toks) != len(nums):
        return raw.strip()
    base = m.start(1)
    out, pos = [], 0
    for t, v in zip(toks, nums):
        keep = t.group(0) if (not any(c.isdigit() for c in t.group(0))
                              and _ROMAN.get(t.group(0).lower()) == v) \
            else str(v)
        out.append(raw[pos:base + t.start()])
        out.append(keep)
        pos = base + t.end()
    out.append(raw[pos:])
    return ''.join(out).strip()


# `CHAP. IV.—Vers. I.`：章标题与节号常挤在同一行，中间可能是破折号
# （vol2 p223 实测；只允许 `.`/`,` 时这一章整个漏掉）。
CHAP_RE = re.compile(r'^\s*CHAP[.,;]?\s*([IVX]{1,4})\s*[.,;：—–-]*\s*')
# 被注释词句的收尾方括号，OCR 常把 `]` 读成 `|` 或 `)`（实测 47 处 lemma
# 因此漏检，占全书 357 条的 13%）。放开这两种变体，用三道守卫挡假阳：
#   · 前缀里不许有 `(`——`explains (as I have said) the cause` 这类插入语
#   · 括号后必须是空格 + 大写/引号——`in ) good works` 这种排版斑点排除
#   · 前缀长度 ≤140 字符、≤20 词（调用处）
# ⚠️ 收尾方括号后面那个「大写字母」不能只认 ASCII。希腊文回填之后，
# 被注释的词句后面跟的常常是希腊大写（`XuuPiRacbevrav.] Συμβιβάξω is to knit`），
# 只写 `[A-Z]` 时这一条 lemma 认不出来，整段塌成普通正文（实测 3 条）。
LEMMA_RE = re.compile(
    r'^([^\]\)\|\n]{1,140}?)\s*[.,]?\s*[\]\)\|]\s+'
    r'(?=[A-Z“"(\u0386-\u03ab\u1f08-\u1fff])')
# 段首缩进阈值由 calibrate() 按卷算（两卷像素尺度不同），此处仅作兜底


def calibrate(pages):
    """按卷校准 (脚注字号上限, 段首缩进阈值)。**尺度无关**。

    ⚠️ 两卷的绝对像素尺寸不同：扫描件逐卷页面物理尺寸不一样（vol1 约
    266×452 pt、vol2 约 326×564 pt），而渲图用的是固定 400 dpi，于是
    vol2 的字号整体是 vol1 的 1.27 倍：

        vol1  脚注峰 34   正文峰 44   谷底 36
        vol2  脚注峰 49   正文峰 56   谷底 51

    第一版把峰值搜索区间写死成 [24,37] / [37,52]，vol2 直接失效——
    低峰落在 34 处只有 4 行，守卫触发退回 36.0，而 36 在 vol2 是正文
    以下的空区，于是整卷「含脚注页 0」（实测）。
    改法：正文峰 = 全局众数；脚注峰 = 其下方的次峰（计数 ≥ 正文峰 5%、
    间隔 ≥ 4）；阈值取两峰之间的谷底。缩进阈值按正文峰字号取 0.55 倍。
    """
    h = collections.Counter(int(l['size']) for p in pages for l in p['lines'])
    if not h:
        return 36.0, 25
    body = max(h, key=lambda s: h[s])
    indent = max(12, int(round(body * 0.55)))
    # 一维 Otsu：取使类间方差最大的阈值。
    # 曾用「正文峰下方的次峰」找脚注峰，但正文簇本身很宽（vol1 是 37–46
    # 且内部有多个局部峰），次峰搜到 38 这个**正文**字号，阈值 41.5 把
    # 大量正文判成脚注（实测 vol1 含脚注页 173 → 248）。Otsu 不依赖峰形。
    ks = sorted(h)
    tot = sum(h.values())
    best, best_var = None, -1.0
    for t in ks[:-1]:
        w0 = sum(h[k] for k in ks if k <= t)
        w1 = tot - w0
        if w0 == 0 or w1 == 0:
            continue
        m0 = sum(k * h[k] for k in ks if k <= t) / w0
        m1 = sum(k * h[k] for k in ks if k > t) / w1
        var = w0 * w1 * (m0 - m1) ** 2
        if var > best_var:
            best, best_var = t, var
    if best is None:
        return float(body) - 4.5, indent
    return float(best) + 0.5, indent


def page_body_x0(lines):
    """本页正文行的 x0 众数（5px 桶）。扫描件逐页有偏移/歪斜，必须逐页取。"""
    if not lines:
        return 0
    c = collections.Counter(round(l['x0'] / 5) * 5 for l in lines)
    return c.most_common(1)[0][0]


def para_starts(lines, x0, indent_min):
    """→ 每行是否段首。基线取**最近几行续行**的中位数，不是整页众数。

    扫描件是歪的：vol1 p130 实测 x0 从页顶 80 漂到页尾 112（+32px），
    比缩进阈值 24 还大，整页众数一挡，页尾的续行全被判成段首——那一页
    末四行被切成四个独立段落，连字符还留在行尾（`is not re-` / `vealed in
    the word,`）。全书这样被切碎的段落 188 处。
    局部基线跟着倾斜一起漂，判的是「相对左邻行凸出一个 em」，与整页倾斜无关。
    """
    recent = collections.deque(maxlen=5)
    out = []
    for l in lines:
        base = statistics.median(recent) if len(recent) >= 3 else x0
        start = l['x0'] - base > indent_min
        out.append(start)
        if not start:                     # 只有续行进基线，段首行本就凸出
            recent.append(l['x0'])
    return out


FN_MARK = re.compile(r'^\s*(\*|\+|†|‡|[ftJI])\s+(?=[A-Z(“"\d])')


def split_page(lines, fn_max):
    """→ (body_lines, fn_lines)，按**行距**分脚注区。

    为什么不用字号：tesseract 的 x_size 逐行噪声很大，同一页正文能从 37
    跳到 46（vol2 是 48–58）。按它做全局阈值两卷都翻车——vol1 阈值被
    正文簇内部的局部峰带到 40.5/41.5，vol2 把 p14 一整页普通正文
    （x_size 48–51）判成脚注（实测「89 页有脚注」全是假阳性）。

    行距稳得多，且是尺度无关的比值：
        vol1  正文 53–54 px   脚注 42–45 px   注区上方空隙 104 px
    参考行距取**页顶**前若干行——像 p88 那样整页大半是脚注的，全页中位数
    已经落在脚注一侧（45），拿它当参考就分不出来了。

    三个信号互为守卫：行距偏小 + 位于页尾连续一段 + 该段必须含脚注符
    （`*` / `†` / `‡`，OCR 常读成 `+` `f` `t` `J` `I`）。缺一不判，
    宁可漏也不把正文吞进脚注。
    """
    L = list(lines)
    if len(L) < 8:
        return L, []
    gaps = [L[i + 1]['y0'] - L[i]['y0'] for i in range(len(L) - 1)]
    top = [g for g in gaps[:8] if g > 0]
    if not top:
        return L, []
    lead = statistics.median(top)

    # 注区上方有一道**明显大**的空隙（p88：104 px vs 正文行距 54）。
    # ⚠️ 不能「自底向上吃所有行距偏小的行」——两条脚注之间的间隙
    # （p88 是 59 px）比注内行距大，会把注区截断，只吃到最后一条
    # （实测 p88 前两条漏进正文）。所以找的是那道大空隙，取**最靠上**的一道。
    best = None
    for i, g in enumerate(gaps):
        # 下限放到 1/4：Allport 的编辑长注能占到 2/3 页，注区起点最高
        # 出现在 31% 处（vol1 p92 实测，用 1/3 会被这条守卫挡掉）。
        if i < len(gaps) // 4:
            continue
        if g < lead * 1.5:
            continue
        zone = L[i + 1:]
        if not zone or not any(FN_MARK.match(x['text']) for x in zone[:3]):
            continue
        zg = [zone[k + 1]['y0'] - zone[k]['y0'] for k in range(len(zone) - 1)]
        if zg and statistics.median(zg) >= lead * 0.92:
            continue                      # 区内行距不小 → 不是脚注
        best = i + 1
        break
    if best is None:
        # 兜底一：跨页的长注，续页顶上没有脚注符可认（Allport 的传记体长注
        # 常连着三四页）。实测 29 页因此把注文拼进正文。没有脚注符时改用
        # 更硬的几何门槛：上方空隙 ≥1.5 倍行距、注区行距 <0.88 倍、且注区
        # 落在页面后 45%——单靠这三条同时成立，正文内部不会出现。
        for i, g in enumerate(gaps):
            if i < len(gaps) // 4:          # 与主规则同一条下限：注区最高到 31%
                continue
            if g < lead * 1.5:
                continue
            zone = L[i + 1:]
            zg = [zone[k + 1]['y0'] - zone[k]['y0'] for k in range(len(zone) - 1)]
            if len(zone) >= 2 and zg and statistics.median(zg) < lead * 0.88:
                best = i + 1
                break
    if best is None:
        # 兜底一·b：只有一两行的短注（`* Egregias rationes—conclusives !`）。
        # 一行的注没有「区内行距」可比，只能靠上方那道空隙 + 字号：
        # vol1 p130 实测空隙 121px（正文行距 54）、字号 38（谷底 40.5）。
        for i in range(len(gaps) - 1, len(gaps) * 55 // 100 - 1, -1):
            if gaps[i] < lead * 1.7:
                continue
            zone = L[i + 1:]
            if len(zone) <= 2 and all(x['size'] < fn_max for x in zone):
                best = i + 1
            break
    if best is None:
        # 兜底二：有些页注区上方**没有**额外空隙（vol1 p95/p99 实测，
        # 该行上方空隙 50/47 vs 正文行距 53.5/53）。此时只认「脚注符起首
        # + 其后到页尾行距确实偏小」，位置限定在页面后 55% 以内。
        for i in range(len(L) * 45 // 100, len(L)):
            if not FN_MARK.match(L[i]['text']):
                continue
            zone = L[i:]
            zg = [zone[k + 1]['y0'] - zone[k]['y0'] for k in range(len(zone) - 1)]
            if len(zone) >= 2 and zg and statistics.median(zg) < lead * 0.95:
                best = i
                break
    if best is None:
        return [x for x in L if not JUNK_RE.match(x['text'])], []
    # 注区上提：整页几乎全是注的页面（长注跨了三四页），上面那道
    # 「注区起点不得高于页面 1/4」的守卫会把切点压得太低，切点以上还留着
    # 带脚注符、且字号与注区一样小的行——它们本来就是注，却混在正文里
    # （vol2 p86 的 `\* This refers to the use of Hellebore…` 与
    # `+ Cassian, to whom…`，页面上成了两段莫名其妙的正文）。
    # 条件卡得很紧：必须带脚注符、且字号不高于注区中位数的 1.05 倍。
    # 全书只命中 2 页（vol1 p181 / vol2 p86），不会动到正常版面。
    zone = L[best:]
    if zone:
        fs = statistics.median([x['size'] for x in zone])
        for i, x in enumerate(L[:best]):
            if FN_MARK.match(x['text']) and x['size'] <= fs * 1.05:
                best = i
                break
    fns = [x for x in L[best:] if not JUNK_RE.match(x['text'])]
    body = [x for x in L[:best] if not JUNK_RE.match(x['text'])]
    return body, fns


# 斜体的 `l` 被 tesseract 读成 `/`（`on/y` / `himse/f` / `Last/y` / `A/though`）。
# 这是本书 italic 字体上的系统性误读，两卷共 53 处。敢一律改回 `l` 的依据：
# `/` 在本书里**从不合法地出现在词中间**——全部 53 处逐条看过，替换后
# 42 条直接过系统词典，验不过的 8 条也都是对的，只是词典没收
# （fulfil / neglecting / self-existence / tehillim「诗篇」的希伯来音译…），
# 唯一一条 `wappni/a` 是被读花的希腊词，改不改都是乱码。
# ⚠️ 只管「后面跟小写」的：`of the/Deputies` 那处是漏了空格，不是 `l`，不动。
# 行末那一种要单列：跨页断词时行尾是 `A/-`（`Al-` + 下页 `though`），
# `/` 后面跟的是连字符不是小写字母，只写前一条会漏掉（实测 p496 的 `A/though`）。
OCR_SLASH_L = re.compile(r'(?<=[A-Za-z])/(?=[a-z]|-\s*$)')


# 左引号 `“` 被读成 `**`（全书 278 处，每一处后面都跟着收引号 `”` 或 `"`：
# `\*\* Townsend's Accusations,”` / `\*\* We," exclaims Justin Martyr`）。
# `**` 在本书里没有别的用处——脚注符是 `*` `†` `‡`（vol1 p88 裁图核过），
# 不存在 `**` 当第二个脚注符的排法。
OCR_OPEN_QUOTE = re.compile(r'\*\*')
# 单独成词的 `à` / `á` / `â` 是冠词 a 上落了个扫描点（全书 16 处，逐条看过
# 上下文：`à common practice` / `à created quality` / 拉丁 `à fortiori`、
# `à causa exemplari`，无一例外）。重音字母出现在词**中间**的是希腊文与拉丁文
# 的音译，一概不动。
OCR_ACCENT_A = re.compile(r'(?<![A-Za-zÀ-ÿ])[àáâ](?![A-Za-zÀ-ÿ])')
# `«` 就杂得多：多数落在被读花的希腊文音译里（`«0 diov`、`Ev «no disce`），
# 还有断词处的斑点（`tem- « pet`）。只收「脚注符或句读之后、其后是大写字母」
# 这一种形状——那是引号无疑（`\* « Sapientia carnis."`、`Author. *« Some`）。
OCR_GUILLEMET = re.compile(r'(?<=[*,.;:] )«\s*(?=[A-Z])|(?<=\*)\s?«\s*(?=[A-Z])')


# 行首孤立的 `+` 后面跟小写字母 = 扫描斑点，不是脚注符——脚注符后面一定是
# 大写字母或引号（`+ The well-known letter`）。斑点那种夹在断词中间
# （`…and ap-` / `+ proves the things…`），并进段落就成了 `ap- + proves`。
OCR_PLUS_SPECK = re.compile(r'^\s*\+\s+(?=[a-z])')
# 行**尾**孤立的 `+` 是右页边的斑点（`…so that the one knows and ap- +`）。
# 脚注符只出现在行首，行尾不可能是它；并段时它会卡进断词中间（`ap- + proves`）。
OCR_PLUS_TAIL = re.compile(r'\s\+\s*$')


# 段首编号的两种误读：数字 1 被读成小写 l（90 处），编号后的句点被读成
# 逗号（38 处）。两者都核过扫描原页（vol1 p434 的 `1.` 与 `2.`，600 dpi
# 放大看得很清楚：`1` 带衬线底座与旗，`2` 后面那点坐在基线上是句点不是逗号）。
# 危害不止是难看：
#   · 编号不成 `\d+\.` 的样子，enum_lead 认不出来，整段就没有 .dv-enum 样式，
#     同一组编号里第 1、2 条与第 3 条长得不一样；
#   · `l.` 会把第二证人的对齐顶歪——`1.` 归一后是空串，`l.` 归一后是 `l`，
#     于是 `l. Itis` 与对方的 `1. It is` 变成 2→3 的替换，粘连词配不上
#     （`Itis` 明明在采信表里却没被拆，实测）。
# 所以这一步必须排在 fix_line 之前。
ENUM_L = re.compile(r'^[l\]\[|I]\.(\s+)(?=[A-Z])')
ENUM_COMMA = re.compile(r'^(\d{1,2}),(\s+)(?=[A-Z])')


def fix_enum_head(t):
    t = ENUM_L.sub(r'1.\1', t)
    return ENUM_COMMA.sub(r'\1.\2', t)


def clean(t):
    """行内噪声：孤立标点、`/`→`l`、`**`→`“`、行首斑点 `+`。"""
    t = OCR_PLUS_SPECK.sub('', t)
    t = OCR_PLUS_TAIL.sub('', t)
    t = OCR_SLASH_L.sub('l', t)
    t = OCR_OPEN_QUOTE.sub('\u201c', t)
    t = OCR_ACCENT_A.sub('a', t)
    t = OCR_GUILLEMET.sub('\u201c', t)
    # 左边距的孤立标点。后面跟脚注符时也要剥——`; + The well-known letter`
    # 里那个 `;` 是斑点，不剥掉 FN_MARK 就认不出这是新的一条注。
    return re.sub(r'^\s*[.\-—·,;:]\s+(?=[a-zA-Z*+†‡])', '', t).strip()


def dehyph(a, b):
    """行末连字合并。`-` 后接大写视为破折号，不并。"""
    if a.endswith('-') and b[:1].islower():
        return a[:-1] + b
    return a + ' ' + b


def build_paragraphs(vol, lo, hi, fn_max, indent_min):
    """→ ([(kind, text)], footnotes, stats)  kind ∈ {para}"""
    paras, fns, stats = [], [], collections.Counter()
    cur, cur_pages = '', set()          # 段落跨了哪几页——脚注配对要按页对齐
    for rec in load(vol):
        p = rec['page']
        if not (lo <= p <= hi):
            continue
        lines = sorted(rec['lines'], key=lambda r: r['y0'])
        n0 = len(lines)
        for _ in range(3):                    # 剥页眉（页码/扫描斑点有时单独成行在前）
            if lines and any(r.search(lines[0]['text']) for r in HEAD_RES):
                lines.pop(0)
                stats['head'] += 1
                continue
            if lines and (JUNK_RE.match(lines[0]['text'])
                          or SPECK_RE.match(lines[0]['text'])):
                lines.pop(0)
                continue
            break
        for _ in range(2):                    # 剥页脚签名
            if lines and (is_foot(lines[-1]['text']) or is_signature(lines[-1])):
                lines.pop()
                stats['foot'] += 1
                continue
            break
        body, fn = split_page(lines, fn_max)
        if fn:
            stats['fn_pages'] += 1
            fns.append((p, fn))
        x0 = page_body_x0(body)
        starts = para_starts(body, x0, indent_min)
        for l, is_start in zip(body, starts):
            # 第二证人：拿 PDF 自带的 IA OCR 层校我们这一遍（见
            # scripts/davenant_witness.py）。两遍都是 tesseract，但版本、
            # 预处理、切页都不同，错处基本不重叠。只在「我方非词、对方是词、
            # 形近且不变短」时采信，孤立的 `|` `/` 另按斑点规则处理。
            raw = fix_enum_head(l['text']) if is_start else l['text']
            txt = clean(W.fix_line(vol, p, raw)[0])
            if not txt:
                continue
            if is_start and cur:
                paras.append((cur, sorted(cur_pages)))
                cur, cur_pages = txt, {p}
            elif cur:
                cur = dehyph(cur, txt)
                cur_pages.add(p)
            else:
                cur, cur_pages = txt, {p}
        stats['pages'] += 1
        stats['lines'] += n0
    if cur:
        paras.append((cur, sorted(cur_pages)))
    return paras, fns, stats


def load(vol):
    for ln in (RAW / f'vol{vol}_lines.jsonl').open(encoding='utf-8'):
        yield json.loads(ln)


def norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z ]', '', s.lower())).strip()


def sim(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def norm_map(s):
    """→ (归一化串, 归一化位置 → 原串位置)。只留小写字母与空格。"""
    out, idx = [], []
    for i, ch in enumerate(s):
        c = ch.lower()
        if c.isalpha() and c.isascii():
            out.append(c); idx.append(i)
        elif c.isspace() and out and out[-1] != ' ':
            out.append(' '); idx.append(i)
    idx.append(len(s))
    return ''.join(out), idx


def split_scripture(cand, chap, nums, kjv):
    """把「经文 + 可能紧跟的注释」切开。

    边界不靠启发式：节组标题已给出节号，拿 KJV 该几节的原文做序列对齐，
    找到「对齐到 KJV 末尾」的那个位置切开。这一步同时产出相似度，
    就是本卷「经文忠于底本」的检查（Gate T 在本卷不适用，见 DIAGNOSIS.md §3）。
    """
    exp = ' '.join(kjv.get(f'{chap}:{v}', '') for v in nums).strip()
    if not exp or not cand:
        return cand, '', 0.0
    en, _ = norm_map(exp)
    cn, cidx = norm_map(cand)
    sm = difflib.SequenceMatcher(None, en, cn, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size >= 8]
    if not blocks:
        return cand, '', 0.0
    last = max(blocks, key=lambda b: b.a + b.size)
    cut = cidx[min(last.b + last.size, len(cidx) - 1)]
    scr, rest = cand[:cut].strip(), cand[cut:].strip()
    ratio = difflib.SequenceMatcher(None, en, norm_map(scr)[0]).ratio()
    return scr, rest, round(ratio, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', type=int, choices=(1, 2))
    ap.add_argument('--pages', help='如 86-170，需配 --vol')
    a = ap.parse_args()
    kjv = json.loads((RAW / 'kjv_colossians.json').read_text(encoding='utf-8'))

    plan = ([(a.vol, *(int(x) for x in a.pages.split('-')))] if a.pages
            else [(v, *RANGES[v]) for v in ([a.vol] if a.vol else (1, 2))])

    out, total = [], collections.Counter()
    for vol, lo, hi in plan:
        pages = [r for r in load(vol) if RANGES[vol][0] <= r['page'] <= RANGES[vol][1]]
        fn_max, indent_min = calibrate(pages)
        paras, fns, st = build_paragraphs(vol, lo, hi, fn_max, indent_min)
        total.update(st)
        print(f'  vol{vol}: 页 {lo}-{hi}  脚注字号上限 {fn_max} 缩进阈值 {indent_min}  '
              f'段落 {len(paras)}  含脚注页 {st["fn_pages"]}  剥页眉 {st["head"]}')

        seen_chap, cur_chap, pend = False, None, None
        i = 0
        while i < len(paras):
            para, ppages = paras[i]
            i += 1
            # 段落的页码跨度：脚注按页配对要用（publish_davenant_en.py）
            # ⚠️ 必须带卷号。两卷的扫描页号区间重叠（vol1 86-631、
            # vol2 14-317），发布脚本按页号配脚注，只写 pN 会让 3/4 章去抢
            # 1/2 章的注（实测 144 条注落在共用桶里，6 条实际配串了卷）。
            pg = (f'<!--v{vol}p{ppages[0]}-->' if len(ppages) == 1
                  else f'<!--v{vol}p{ppages[0]}-{ppages[-1]}-->') if ppages else ''
            # 前一条标记（章首或节组）声明了要吃经文 → 先做 KJV 对齐
            if pend is not None:
                # 经文常被悬挂缩进切成好几段（歌 1:1-2 就是 5 段），
                # 所以往后**按相似度贪心增长**，取相似度最高的那个长度。
                # 曾把上限写死 4 段，第 5 段（含 `Father and the Lord Jesus
                # Christ`）被排除，经文尾巴被切进正文（实测）。
                nums = pend
                pool = [para]
                j = i
                while len(pool) < 10 and j < len(paras) and \
                        not (CHAP_RE.match(paras[j][0])
                             or SECTION_RE.match(paras[j][0])):
                    pool.append(paras[j][0]); j += 1
                # ⚠️ 段间用 dehyph 接，不能 ' '.join。经文是悬挂缩进，
                # 每一行都被判成段首，行末连字没走过 dehyph——直接拼就留下
                # `spiri- tual` / `be- ginning` 这种断词（实测 19 个经文块）。
                def _join(segs):
                    out = ''
                    for seg in segs:
                        out = dehyph(out, seg) if out else seg
                    return out

                def _best_for(vs):
                    b = None
                    for k in range(1, len(pool) + 1):
                        c = _join(pool[:k])
                        sc, rs, rr = split_scripture(c, cur_chap, vs, kjv)
                        if b is None or rr > b[3] + 1e-9:
                            b = (c, sc, rs, rr, k)
                    return b

                best, used, partial_ok = _best_for(nums), nums, False
                # 对不上时先别急着退回正文。全书 90 个节组里对不上的 3 个，
                # 拿 600 dpi 原页看过，是**两种不同的**毛病：
                #   · 节号被 OCR 读错：vol2 p119 原书 `Vers. 13.` 读成 18、
                #     p132 原书 `Verse 15.` 读成 16 → 按全章逐节重扫救回，
                #     命中 ≥0.9 才认，标题里的号码连带改正
                #   · 原书只引了半节：vol1 p339 `Verse 22.` 底下只印
                #     "Now hath he reconciled … through death."（0.458）
                #     → 本节仍是全章最像的，按半引接受，不许改号
                if best[3] < 0.55 and cur_chap:
                    alt = [(_best_for([v]), [v]) for v in range(1, 30)
                           if f'{cur_chap}:{v}' in kjv and [v] != nums]
                    hi = [x for x in alt if x[0][3] >= 0.9]
                    if hi:
                        b2, vs = max(hi, key=lambda x: x[0][3])
                        print(f'  [节号回填] {cur_chap}:{nums} → {vs} '
                              f'（相似度 {b2[3]}）', flush=True)
                        best, used = b2, vs
                        total['sec_fix'] += 1
                        for t in range(len(out) - 1, -1, -1):
                            if out[t].startswith('[SECTION] '):
                                mm = re.match(r'(\[SECTION\] (?:<!--[^>]*-->)?)(.*)$',
                                              out[t], re.S)
                                out[t] = mm.group(1) + render_section(mm.group(2), vs)
                                break
                    elif best[3] >= 0.40 and best[3] >= max(
                            (x[0][3] for x in alt), default=0):
                        print(f'  [半引接受] {cur_chap}:{nums} '
                              f'（相似度 {best[3]}）', flush=True)
                        total['scr_partial'] += 1
                        partial_ok = True
                cand, scr, rest, r, take = best
                i += take - 1
                if r >= 0.55 or partial_ok:
                    # 引文尾巴的 `&c.` 跟着经文走。它跟 KJV 对不上，贪心增长
                    # 到它这一段相似度只会掉，于是被留在外面成了孤零零一段
                    # `&c.`（vol2 p233 实测，页面上就印着 "…with thanksgiving,
                    # &c."）。经文收尾后紧跟的独立 `&c.` 段直接并回去。
                    # 引文尾巴的 `&c.` 跟着经文走。KJV 里没有这两个字，
                    # split_scripture 的切点落在它前面，于是它被当成正文
                    # 甩出来，页面上多一段孤零零的 `&c.`（vol2 p233 实测，
                    # 原书印的是 "…with thanksgiving, &c."）。
                    if rest and re.fullmatch(r'&\s*c\.?', rest.strip()):
                        scr, rest = scr.rstrip() + ' ' + rest.strip(), ''
                    elif not rest and i < len(paras) and \
                            re.fullmatch(r'&\s*c\.?', paras[i][0].strip()):
                        scr = scr.rstrip() + ' ' + paras[i][0].strip()
                        i += 1
                    out.append(f'[SCRIPTURE] {pg}{cur_chap}:'
                               f'{",".join(map(str, used))}|{r}| {scr}')
                    total['scr'] += 1
                    total['scr_sim'] += r
                    if rest:
                        out.append(f'[BODY] {pg}{rest}')
                else:                     # 对不上就原样留正文，不硬切
                    total['scr_fail'] += 1
                    out.append(f'[BODY] {pg}{cand}')
                pend = None
                continue
            m = CHAP_RE.match(para)
            if not seen_chap and not m and re.match(
                    r'^(AN EXPOSITION|OF THE|EPISTLE OF ST|COLOSSIANS\.?)\s*$', para):
                out.append(f'[TITLE] {para}')       # 卷首书名块，发布时不进正文
                continue
            if m:
                seen_chap = True
                cur_chap = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}.get(m.group(1))
                out.append(f'[H1] CHAP. {m.group(1)}')
                total['chap'] += 1
                # 章首直接接经文，没有 `Verses 1, 2.` 标题
                rest = clean(para[m.end():])
                # 同段后面若紧跟节号标题（`CHAP. IV.—Vers. I.`），
                # 退回队列交给 SECTION 分支，不要当成章首的 1,2 节
                if rest and SECTION_RE.match(rest):
                    pend = None
                    paras.insert(i, (rest, ppages))
                else:
                    pend = [1, 2] if cur_chap else None
                    if rest:
                        paras.insert(i, (rest, ppages))
                continue
            m = SECTION_RE.match(para)
            if m:
                nums = parse_nums(m.group(1))
                out.append(f'[SECTION] {pg}{render_section(m.group(0), nums)}')
                total['sec'] += 1
                rest = clean(para[m.end():])
                # ⚠️ 这里**不能**就着本段单独切经文。经文本身常被悬挂缩进
                # 拆成好几段，只拿第一段去对齐，相似度 0.60 也过了 0.55 的
                # 门槛，经文就只剩头一行——歌 3:25「But he that doeth wrong,
                # shall receive for the」到此为止，剩下三行掉进正文当独立段
                # （实测 86 个经文块里 11 个这样被腰斩）。一律退回队列交给
                # pend 分支，那里会按相似度贪心增长段数。
                pend = nums
                if rest:
                    paras.insert(i, (rest, ppages))
                continue
            m = LEMMA_RE.match(para)
            if m and 0 < len(m.group(1).split()) <= 20 and '(' not in m.group(1):
                out.append(f'[LEMMA] {pg}{m.group(1).strip()}')
                total['lemma'] += 1
                rest = clean(para[m.end():])
                if rest:
                    out.append(f'[BODY] {fix_label(rest)[0]}')
                continue
            out.append(f'[BODY] {pg}{fix_label(para)[0]}')

        for p, fn in fns:
            x0 = page_body_x0(fn)
            cur = ''
            for l, is_start in zip(fn, para_starts(fn, x0, indent_min)):
                t = clean(W.fix_line(vol, p, l['text'])[0])
                # 脚注符本身就是分条的界标，不能只看缩进：同页两条短注常常
                # 首行缩进一模一样（vol1 p151 两条都是 x0=214），只看缩进会把
                # 第二条当续行并进第一条，页面上就出现 `\* That is, indefinite…
                # + That is, formed…` 两条注挤成一条（实测 7 处）。
                if (is_start or FN_MARK.match(t)) and cur:
                    out.append(f'[FN] <!--v{vol}p{p}--> {cur}')
                    cur = t
                elif cur:
                    cur = dehyph(cur, t)
                else:
                    cur = t
            if cur:
                out.append(f'[FN] <!--v{vol}p{p}--> {cur}')

    dst = RAW / ('davenant_colossians_structured.txt' if not a.pages
                 else 'sample_structured.txt')
    dst.write_text('\n'.join(out) + '\n', encoding='utf-8')
    print(f'[ok] → {dst.name}  {dst.stat().st_size:,} 字节  {len(out)} 行')
    print(f'  CHAP {total["chap"]} · 节组 {total["sec"]} · 经文块 {total["scr"]}'
          f'（对不上 {total["scr_fail"]}）· lemma {total["lemma"]} · '
          f'共 {total["pages"]} 页 {total["lines"]} 行')
    return 0


if __name__ == '__main__':
    sys.exit(main())
