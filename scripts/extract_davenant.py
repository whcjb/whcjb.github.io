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
# ⚠️ vol2 首页是 12，不是 14（2026-09-21 修）。p10 是卷二扉页、p11 是印工
# 落款，p12 才是正文第一页（印本 p.3）——上面印着第三章的章题
# `EXPOSITION / OF / THE THIRD CHAPTER.`，接着是两页总论（本章旨趣、
# 两重劝勉的分段）。写 14 就把这两页整段丢掉：发布出来第三章从
# `Verses 1, 2.` 直接开讲，一、二、四章都有的章题与开篇总论独独第三章没有。
RANGES = {1: (86, 631), 2: (12, 317)}

# 页眉：`Ver. 2.  EPISTLE TO THE COLOSSIANS.  35` / `214  AN EXPOSITION
# OF ST. PAUL'S  Chap. iv.`
# ⚠️ 不要去卡左边的 `Ver. N.`——OCR 把它读成 Vers / Verne / Ven / Ver. M.
# 各种花样，写死了会漏（实测 419 个页眉漏掉 77 个，整行页眉被拼进正文中间）。
# 页眉中间那句全大写的书名反而稳，且只在页眉出现（正文写的是 this Epistle），
# 又只拿页首前几行来试，不会误伤正文。
HEAD_RES = [
    # `TO THE` 的 H 被读成 I 或 II：`EPISTLE TO TIE COLOSSIANS. 385`、
    # `EPISTLE TO TIIE COLOSSIANS. 101`。写死 TH 漏掉 4 行页眉，它们整行拼进
    # 了正文（v1p468/474、v2p110、v2p302；v2p302 那行还把 `Vers. 13.` 留在
    # 段首，读者看到的是「Vers. 13. when occasion offers…」）。
    # 全书试跑：放宽后新命中正好这 4 行，都在第 0 行，没有误伤。
    re.compile(r'[EKR]?P[Ii1l!|][SB5][TI1l][Ll][EF]\s+T[Oo0]\s+T[HIiLl1]{1,2}[EFRK]'
               r'\s+C[Oo0][Ll]', re.I),
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
# 编号位同样要容字形变体与序数后缀：原书的 `ARGUMENT 1st.` 被读成
# `ARGUMENT lst.`、`OBJECTION 11.` 被读成 `OpsectTion 1].`，编号里带了
# `l` / `]`，只认纯数字这两条 lemma 连 LABEL_RE 都匹配不上，标签归一与
# 后面的编号连续性检查全落空（实测 ARGUMENT 少一条、OBJECTION 少一条）。
# 行首也容三两个非字母：`. ARGUMENT 2.` 那个点是扫描斑点。
LABEL_RE = re.compile(
    r"^[^A-Za-z]{0,3}([A-Za-z][A-Za-z0-9;,.'’]{2,13})\.?"
    r"(\s+[\dlI\]\[|]{1,3}(?:st|nd|rd|th)?\s*[.,])")


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
    # ⚠️ 不能在「标签词已经对了」时就早退：编号位可能还是花的
    # （`ARGUMENT lst.` 的 `lst` 是 `1st`），行首也可能挂着扫描斑点
    # （`. ARGUMENT 2.`）。一律重排一遍，真没变才返回 None。
    # key == best 也要改：第二证人常把 `OsjEcTioN` 校成 `Objection`，
    # 拼写对了但大小写不是原书的小型大写，同一章里会一半 OBJECTION、
    # 一半 Objection。一律归到全大写。
    num = m.group(2).translate(_DIGIT_FIX)
    out = best + num + t[m.end():]
    return (out, (m.group(1), best)) if out != t else (t, None)


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


# 行首的孤立斑点会把 x0 往左拽，段首缩进判据跟着失灵：vol2 p461 的
# `. ARGUMENT 2.` 行首多一个点，x0 从 305 变成 240，比上一行还靠左，
# 于是被判成续行、整条 ARGUMENT 并进了上一段（编号连续性闸抓到的）。
# 斑点只认这几个在本书里从不合法出现在行首的字符。
# `!` 与 `_` 是 2026-09-21 补的：`! The first, comprehended…`（v2p13）
# `_and the impostures…`（v2p12）——左边距上的斑点，`_` 还常常直接贴着词，
# 所以单列一条不要求后面有空格。全书试跑只多认 12 行，逐条看过全是斑点。
HEAD_SPECK = re.compile(r"^\s*[.,;:'\u2019\u201c\u201d|/*+~^`\-!]{1,2}\s+(?=[A-Za-z])"
                        r"|^\s*_+\s*(?=[A-Za-z])")

# 行末右边距上的孤立斑点（见 build_paragraphs 里的调用处）
TAIL_SPECK = re.compile(r'[a-z] [-.]$')


def unspeck(l):
    """→ (去掉行首斑点的文本, 修正后的 x0)。按字符数比例把 x0 推回去。

    ⚠️ 剥掉的前缀记进 `l['speck']`：`*` `+` 也在斑点字符表里，而脚注行
    行首那个 `*` 是**脚注符**，不是斑点。unspeck 在 split_page 之前跑，
    marks 被提前剥掉，注区判据里的 FN_MARK 就看不见它了
    （v1p155 的 `* Vide p. 20, 21.` 因此整条留在正文里）。
    把前缀留着，需要认脚注符的地方用 `had_fn_mark()` 复原来看。
    """
    t = l['text']
    m = HEAD_SPECK.match(t)
    if not m:
        return t, l['x0']
    l['speck'] = m.group(0)
    cut = m.end()
    x0 = l['x0'] + int((l['x1'] - l['x0']) * cut / max(len(t), 1))
    return t[cut:], x0


def line_offsets(lines, x0, indent_min):
    """→ 每行的左缩进量（相对**最近几行续行**的基线），段首判据与缩进块判据共用。

    扫描件是歪的：vol1 p130 实测 x0 从页顶 80 漂到页尾 112（+32px），
    比缩进阈值 24 还大，整页众数一挡，页尾的续行全被判成段首——那一页
    末四行被切成四个独立段落，连字符还留在行尾（`is not re-` / `vealed in
    the word,`）。全书这样被切碎的段落 188 处。
    局部基线跟着倾斜一起漂，量的是「相对左邻行凸出多少」，与整页倾斜无关。
    """
    recent = collections.deque(maxlen=5)
    out = []
    for l in lines:
        base = statistics.median(recent) if len(recent) >= 3 else x0
        d = l['x0'] - base
        out.append(d)
        if d <= indent_min:               # 只有续行进基线，段首行本就凸出
            recent.append(l['x0'])
    return out


def para_starts(lines, x0, indent_min):
    """→ 每行是否段首（凸出超过一个 em）。"""
    return [d > indent_min for d in line_offsets(lines, x0, indent_min)]


def indent_scale(ds, indent_min):
    """→ (本页段首缩进, 右移块门槛, 孤身一行的门槛)。两个版式判据共用。"""
    near = [d for d in ds if indent_min < d <= 2.5 * indent_min]
    para = statistics.median(near) if len(near) >= 3 else 1.8 * indent_min
    return para, max(2.2 * indent_min, 1.5 * para), max(3.0 * indent_min,
                                                        2.0 * para)


def _all_caps(t):
    L = [c for c in t if c.isalpha()]
    return bool(L) and all(c.isupper() for c in L)


def outline_items(lines, ds, indent_min):
    """→ 每行是否「原书整体右移排的一条」：分析表的支、清单的一行、引诗的一句。

    原书在一句领起语（`The principal divisions of this Chapter are three:`）
    之后，把各支整体右移一大格排成一块，行距还是行距。抽取器按「缩进＝段首」
    读，每一支都成了独立段落，发布出来是十几个孤零零的短段（v2p232 实测，
    用户报的就是这一页）。花括号表那几处是按影像手工重建的
    （brace_blocks.json），但**没画括号、只靠缩进**的这一类全书还有几十处，
    手工表罩不住，只能按几何量。

    判据分两档，因为两类错判的代价不一样：
      · 连续 ≥2 行、左边界互相对齐（±25px）→ 门槛 max(2.2·em, 1.5·本页段首缩进)
        取得低，v1p319 那张「1.–6.」的分析表只比段首深 45px，高了就漏。
      · 孤身一行 → 门槛抬到 max(3·em, 2·本页段首缩进)，且要求它与本页已认定的
        某一条左边界对齐、上一行以 `,` `:` `;` 收尾。
        不加这两条，居中的小标题（v2p284 `Observations.`、v1p126
        `From the Scriptures.`）会被当成缩进条；抬门槛是因为页面歪斜会让
        普通段首量到 116px（v2p136 `From the Author God…` 实测，对照影像
        它就排在正常段首缩进上）。
    全大写的行一律不算：`EXPOSITION` / `THE FOURTH CHAPTER.` 是居中章题。
    宁可漏判（退回现状，一条一段）也不错判——错判会把居中标题拽进缩进块。
    """
    para, deep_run, deep_one = indent_scale(ds, indent_min)
    cand = [d > deep_run and not _all_caps(l['text'])
            for l, d in zip(lines, ds)]
    acc = [False] * len(lines)
    # ⚠️ 一段连续的候选行里可能**混着右对齐的出处行**（`Duncan's Boethius,
    # 1789.` x0=798，紧挨着四行 x0≈270 的译诗）。早先要求「整段行行对齐」，
    # 这一行不齐就把整段作废，v1p166/v1p285 两处引诗因此一条一段。
    # 改成按左边界切小段：每段内部对齐（±25px），≥2 行的小段才认。
    # 出处行自己落单，不成段，仍旧是普通段落——这是想要的。
    i = 0
    while i < len(lines):
        if not cand[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(lines) and cand[j + 1]:
            j += 1
        g = i
        while g <= j:
            h = g
            while h + 1 <= j and abs(lines[h + 1]['x0'] - lines[g]['x0']) <= 25:
                h += 1
            if h > g:
                for k in range(g, h + 1):
                    acc[k] = True
            g = h + 1
        i = j + 1
    aligned = [lines[k]['x0'] for k in range(len(lines)) if acc[k]]
    for k in range(len(lines)):
        if acc[k] or not cand[k] or ds[k] <= deep_one or not aligned:
            continue
        prev = lines[k - 1]['text'].rstrip() if k else ''
        if any(abs(lines[k]['x0'] - x) <= 25 for x in aligned) and \
                prev.endswith((',', ':', ';')):
            acc[k] = True
    return acc


SENT_TAIL = ('.', '!', '?', ':', ';', ',', '"', '”', '’', ')')

# 19 世纪排长引文时每行行首重复的那个开引号。OCR 读成什么样都有：
# `“` / `"` / `**` / `''` / `,,` / 反引号（v1p262 实测 `** `）。
# 单个 `*` **不在**表里——那是脚注符。
QUOTE_SPECK = re.compile(r'^(“|”|"|\*\*|\'\'|,,|``)$')


def text_right(lines):
    """正文的右边界：x1 **上半的中位数**，不是最大值。

    最大值会被个别过界的行拉走（v1p418 实测 max 1447、真正的右边界 1311），
    居中判据按它算出来的左右边距差 175 px，门槛 156 差一点就是过不去——
    章题 `EXPOSITION / OF` 与 `DOGMATICAL OBSERVATIONS.` 这几行因此漏判。
    """
    xs = sorted(l['x1'] for l in lines)
    return statistics.median(xs[len(xs) // 2:]) if xs else 0


def centered_heads(lines, ds, starts, marks, left, right, indent_min):
    """→ 每行的版式角色：'head'（居中小标题）/ 'attrib'（右对齐的出处行）/ ''。

    达文南特的应用段前面常印一行居中的小鉴题——`Instructions.`
    `Corollaries.` `Observations.` `Hence let us observe,`，章题
    `EXPOSITION / OF / THE FOURTH CHAPTER.` 与章末 `FINIS.` 也是居中的。
    抽取器只认缩进，这些行成了普通正文段落：短短一段顶在段首缩进位，
    和它引出的那几条挤在一起，读者看不出它是标题（全书 30 余处）。

    判据是**左右边距对称**（页面几何），不是字面清单——写死
    `Instructions|Corollaries|…` 只能罩住数得出来的那几个词：
      · 左右两侧各留出 >12% 版心宽，且两侧之差 ≤12% 版心宽
      · 行长 ≤75% 版心宽（居中标题都短）
      · 上一行以句末标点收尾，或上一行本身就是居中标题（章题是连着三行）
      · 下一行是新段首，或上一行是居中标题（章题末行 `THE FOURTH
        CHAPTER.` 底下那行是不缩进的正文，只看下一行会漏掉它）
      · 至少有一个 ≥2 字母的词（挡掉 `1 2` 这种页面碎片）
    右移块（outline_items 已认定的条目）优先：拉丁引诗、分析表的支本来就
    短、也可能左右对称，但它们是块里的一条，不是标题。
    """
    W = max(right - left, 1)
    _para, deep_run, _one = indent_scale(ds, indent_min)

    def sym(l):
        """纯几何的「居中」：左右边距都留够、两侧之差小、行不长。"""
        lg, rg = l['x0'] - left, right - l['x1']
        return (lg > 0.12 * W and rg > 0.12 * W and abs(lg - rg) <= 0.12 * W
                and l['x1'] - l['x0'] <= 0.75 * W)

    out = [''] * len(lines)
    for i, l in enumerate(lines):
        lg, rg = l['x0'] - left, right - l['x1']
        w = l['x1'] - l['x0']
        if not any(len(x) >= 2 and x.isalpha()
                   for x in re.findall(r'[A-Za-z]+', l['text'])):
            continue
        prev_cen = i > 0 and out[i - 1] == 'head'
        # 上一行行末的脚注符不算内容（`…rewards of vighteousness.*`），
        # 剥掉再看它是不是以句末标点收尾。
        prev = lines[i - 1]['text'].rstrip().rstrip('*+†‡ ') if i else ''
        if not (i == 0 or prev_cen or prev.endswith(SENT_TAIL)):
            continue
        if not (i + 1 >= len(lines) or starts[i + 1] or prev_cen):
            continue
        # 下一行是**右移**的 → 这一行是一块缩进引文的头一行，不是居中标题
        # （v2p146 的 `……What is the duty of Physicians,` 领起三行右移的
        # 耶柔米引文，左右边距恰好对称，只看几何会当成标题）。
        # 只卡居中那一档：右对齐的出处行后面接着另一块引诗是常事
        # （v1p357 的 `ZEneid. x.` 底下就是英译）。
        # 下一行若自己也是居中的（章题连着三行 `EXPOSITION / OF /
        # THE FOURTH CHAPTER.`，第二行比第一行还靠右），不算「领起缩进块」。
        next_deep = (i + 1 < len(lines) and ds[i + 1] > deep_run
                     and not prev_cen and not sym(lines[i + 1]))
        if not marks[i] and not next_deep and sym(l):
            out[i] = 'head'
        # 右对齐的出处行：引诗、引文之后单排一行的作者/篇名
        # （`Prudent.` / `Duncan's Boethius, 1789.` / `Hor. Epist. lib. 1.
        # Ep. 16.` / `Prudent. in Psychom.`，全书 4 处）。它贴着右边界、
        # 左边留出一大片白，和居中标题是同一类「原书版式」，只是靠右。
        # 行长卡到 45% 版心：再长的多半是被页边斑点把 x1 拽到右边界的
        # 普通行（v2p254 的 `Corollaries. )` 实测 53%）。
        # 右边距放到 15%：短的出处行并不顶到右边界（`In Hamart.` 实测离
        # 边界 149 px、`ZEneid. x.` 136 px，版心 1160 左右）。
        elif lg > 0.35 * W and rg < 0.15 * W and w <= 0.45 * W:
            out[i] = 'attrib'
    return out


# 「第 N 条」的行首编号：`1.` `l.` `].` `1,`——OCR 把 `1` 读成 `l` `]` `|`
# 是常态（产物里 `l. They are to be blamed…` 就是原书的 `1.`）。
ENUM_LEAD = re.compile(r'^\s*[\dlI\]\[|]{1,3}\s*[.,;:)]\s')

# 手工认定的小标题：按「卷|扫描页号」定位，值是该页要认成标题的**整行原文**。
# 只收几何判据够不着、又对着影像逐处核过的那几处。
MANUAL_HEADS = {
    # v1p126：`…Now let us proceed to` 一句直接跑进标题行里（原书就是这么
    # 排的，600 dpi 影像核过），所以「上一行以句末标点收尾」这条不成立；
    # 底下跟的又不是「1. 2. 3.」的条目而是一段散文，`indent_heads` 的两道
    # 主判据都够不着。它比段首缩进多缩 45 px、单独占一行、后面紧跟着居中的
    # `From the Scriptures.`——与它是同一层的小标题，只是原书一个居中一个缩排。
    (1, 126): ['The arguments of the Papists.'],
}


def indent_heads(lines, ds, starts, marks, heads, right, indent_min, key):
    """→ 在 `heads` 上补「缩排（而非居中）的小鉴题」，标成 `'rubric'`。

    ⚠️ 角色是 `'rubric'` 不是 `'head'`：原书这一档**不居中**，只比段首多缩
    一格（v2p61 `Corollaries.`、v1p126 `The arguments of the Papists.`，
    400 dpi 影像核过）。早先一并出成 `[HEAD]`→`dv-synopsis`（居中），
    页面上把缩排排成了居中，是偏离原书的——用户截图指出来的就是这个。
    发布侧 `[RUBRIC]`→`.dv-rubric`（左缩进，不居中）。


    `centered_heads` 按**左右边距对称**认标题，罩住的是原书居中排的那 43 处。
    但同一个元素原书还有另一种排法：**不居中，只比段首多缩一格**——
    `Corollaries.` `Instructions.` `Observations.` `Hence learn,`
    `From the Author God, the peace of God.` 这些词两种排法都出现过
    （v2p157 的 `Instructions.` 缩排、v2p284 的居中）。缩排那一批全书 29 处，
    原先一律是普通正文段落：页面上读者看到的是一个孤零零的短段，和它领起的
    「1. 2. 3.」挤在一起，看不出是标题。

    判据仍然是几何，不是词表（写死 `Instructions|Corollaries` 只能罩住数得出
    来的那几个）：
      · 缩进 > 1.35 × 本页段首缩进（`ds` 已按行剥过行首斑点）
      · 行短：右边留白 ≥15% 版心，**或**字符数 ≤ 本页中位数的一半
        （两个都要是因为 x1 会被页边斑点拽到右边界——v2p138 的
        `Instructions;` 实测右余 2%，只看几何量不出来）
      · 上一行以句末标点收尾（或它本身是标题、或它是本页第一行）
      · 下一行是段首、**且是「1.」这样的条目**（`ENUM_LEAD`）
      · 上下两行都不是右移行
    最后这两条是要害。去掉「下一行是条目」，进来的全是**经文块的末行**——
    经文整块缩排，末行短、上一行以逗号收尾，几何上与缩排标题一模一样
    （v1p313 的 `dwell.`、v2p168 的 `against them.`、v1p412 的
    `which worketh in me mightily.`）。把经文末行认成标题，后面 KJV 对齐
    那一步就再也拼不回整块经文。实测：不卡这一条 34 处里 5 处是经文末行，
    卡上之后 29 处**逐条对影像核过**，无一例外都是小鉴题。
    """
    para, deep_run, _one = indent_scale(ds, indent_min)
    T = para * 1.35
    W = max(right - min((l['x0'] for l in lines), default=0), 1)
    med = statistics.median([len(l['text']) for l in lines]) if lines else 0
    manual = set(MANUAL_HEADS.get(key, ()))
    for i, l in enumerate(lines):
        if heads[i] or marks[i]:
            continue
        if l['text'].strip() in manual:
            heads[i] = 'rubric'
            continue
        if _all_caps(l['text']) or ds[i] <= T:
            continue
        if SECTION_RE.match(l['text']) or CHAP_RE.match(l['text']):
            continue
        if not (right - l['x1'] >= 0.15 * W or len(l['text']) <= 0.5 * med):
            continue
        if not any(len(x) >= 2 and x.isalpha()
                   for x in re.findall(r'[A-Za-z]+', l['text'])):
            continue
        if i + 1 >= len(lines) or not starts[i + 1] or ds[i + 1] > T:
            continue
        if not ENUM_LEAD.match(lines[i + 1]['text']):
            continue
        if i and (ds[i - 1] > T or marks[i - 1]):
            continue
        prev = lines[i - 1]['text'].rstrip().rstrip('*+\u2020\u2021 ') if i else ''
        if not (i == 0 or heads[i - 1] in ('head', 'rubric')
                or prev.endswith(SENT_TAIL)):
            continue
        heads[i] = 'rubric'
    return heads


FN_MARK = re.compile(r'^\s*(\*|\+|†|‡|[ftJI])\s+(?=[A-Z(“"\d])')


def _fn_zone_by_size(L, fn_max, lead, gaps):
    """按字号找脚注区起点，找不到返回 None。四条守卫全成立才给答案。

    ⚠️ 前后试了四版，前三版都会误判，记在这里免得再走一遍：
      ① 页内最大字号落差（相对比较）→ 新判出 169 页，真正漏判的只有 15 页。
         正文页上那个「最大落差点」不过是逐行噪声，随便落在哪都能配上一段
         行距偏紧的尾巴。
      ② 「从页尾往回吃所有 size < fn_max 的行」→ 正文里偶有几行字号掉到界下
         （p255 的 38/37），一路回溯把正文吃进注区。
      ③ 「头尾中位数满足 up ≥ fn_max > dn，取最早的 k」→ 那个不等式在一整段
         k 上都成立，取最早的就切进了正文中间（p96 切在 `they made use of;`）。
    根子都在「偏晚的切点挡不住」：切点偏早会被中位数判据自然否掉——尾段混进
    正文行就把尾段中位数拉过界；偏晚却不会，头段混进几行脚注，中位数仍在界上。
    所以必须另加一道**局部**判据，就是下面的 ①。
    """
    for k in range(max(3, len(L) // 6), len(L) - 3):
        # ① 局部跃变：切点前一行在界上，后面**连续三行**在界下。
        #    连续三行是为了挡短行——`arms.` `selves.` 这类行本身短，
        #    测得的 size 也小，只看一行会被当成注区起点。
        if L[k - 1]['size'] < fn_max or any(
                L[k + j]['size'] >= fn_max for j in range(3)):
            continue
        # ② 整体也分得开：头段中位数在界上、尾段在界下
        up = statistics.median([x['size'] for x in L[:k]])
        dn = statistics.median([x['size'] for x in L[k:]])
        if not (up >= fn_max > dn):
            continue
        # ③ 区内行距明显比正文紧（脚注是小字号小行距）
        zg = [L[i + 1]['y0'] - L[i]['y0'] for i in range(k, len(L) - 1)]
        if not zg or statistics.median(zg) >= lead * 0.9:
            continue
        # ④ 断口看得见（比正文行距大 15% 以上）
        if gaps[k - 1] < lead * 1.15:
            continue
        return k
    return None


# 章末标记：`END OF THE FIRST CHAPTER.` / `THE END OF THE SECOND CHAPTER.`
# / `FINIS.`。OCR 把 CHAPTER 读成 CITAPTER/CHAPTEB 之类，所以尾巴放宽。
CHAP_END_RE = re.compile(r'^\s*((THE\s+)?END\s+OF\s+THE\s+\w+\s+C\w{5,7}\.?'
                         r'|FINIS\s*\.?)\s*$', re.I)


def had_fn_mark(l):
    """这一行原本是不是以脚注符起首（把 unspeck 剥掉的前缀接回去再看）。"""
    return bool(FN_MARK.match(l.get('speck', '') + l['text']))


def _fn_zone_tail(L, fn_max, gap_ratio=1.6, size_ratio=0.92, min_run=8):
    """整页大半是编者长注的页面：按「页尾一整段小字」找注区起点，找不到返回 None。

    判据全是**页内比值**，不依赖本页的参考行距（那把尺子在这种页面上本身
    就被压短了，见调用处的注释）：
      · 页尾连续 ≥min_run 行字号在界下——长注一定连到页脚；
      · 切口 ≥ gap_ratio × 注区内部行距，或注区首行带脚注符；
      · 注区中位字号 ≤ size_ratio × 上半中位字号。
    切点在「小字起点」前后两行里取断口最大的那一个：正文末行常是短行，
    量得的字号偏小，会把起点往前拽一两行（v1p197 的
    `its fervid devotion, to pray and desire.` 是标本）。
    """
    # 极短的行（`282.)` 5 个字符实测量到 54.7，比正文还大）字号量不准，
    # 扫尾段时跳过不算界——不然注区末尾一个 `282.)` 就把整段 39 行注顶回
    # 正文（附卷 v2p468 实测）。
    k0 = len(L)
    while k0 > 0 and (L[k0 - 1]['size'] < fn_max
                      or len(L[k0 - 1]['text'].strip()) <= 8):
        k0 -= 1
    if len(L) - k0 < min_run or k0 < 2:
        return None
    cand = [k for k in (k0, k0 + 1, k0 + 2) if 2 <= k <= len(L) - min_run]
    if not cand:
        return None
    k = max(cand, key=lambda i: L[i]['y0'] - L[i - 1]['y0'])
    zg = [L[i + 1]['y0'] - L[i]['y0'] for i in range(k, len(L) - 1)]
    if len(zg) < 3:
        return None
    if L[k]['y0'] - L[k - 1]['y0'] < gap_ratio * statistics.median(zg) \
            and not FN_MARK.match(L[k]['text']):
        return None
    if statistics.median([x['size'] for x in L[k:]]) > size_ratio * \
            statistics.median([x['size'] for x in L[:k]]):
        return None
    return k


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

    # 空隙判据够不着的那一档：注区**首行是上一页脚注的接续**，行首没有
    # 脚注符（守卫二不过），而那道空隙又恰好差一点点没到 1.5 倍
    # （p99 实测 79 px vs 门槛 79.5）。这两条一失效，整条编者长注就整段
    # 落进正文，还被一行一段地拆开——全书 15 页、478 行（p99 的尼西亚会议
    # 引文是最长的一条）。
    #
    # 补的是**页内**字号落差。文件开头说过字号做全局阈值不可靠（逐行噪声
    # 大、两卷尺度还不同），但同一页内「正文中位数 vs 注区中位数」是可靠的
    # ——两卷都是 44→34 / 54→43 这种量级。仍旧要两个信号同时成立：
    # 字号落到 0.85 以下，**且**注区行距明显比正文紧。
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
        # ⚠️ 短行的 x_size 量不准（`* Vide p. 20, 21.` 实测 46，反而在界上），
        # 所以**带脚注符**的那一行不再卡字号——空隙 1.7 倍 + 行首脚注符
        # 已经足够硬。只放在这一道里：把 FN_MARK 全线复原会改掉主判据挑的
        # 切点，实测 v1p104/p376 的注区反被缩小 8 行和 3 行。
        for i in range(len(gaps) - 1, len(gaps) * 55 // 100 - 1, -1):
            if gaps[i] < lead * 1.7:
                continue
            zone = L[i + 1:]
            if len(zone) <= 2 and (all(x['size'] < fn_max for x in zone)
                                   or had_fn_mark(zone[0])):
                best = i + 1
            break
    if best is None:
        # 兜底一·c：**带脚注符**的短注，上方那道空隙没到 1.7 倍。原书排注时
        # 页面排得满，注与正文之间只多留半行（v1p293 实测 76 px vs 正文行距
        # 54、v1p557 71 px、v2p49 105 vs 67），1.7 倍的门槛够不着，整条注
        # 留在正文里成了两三段莫名其妙的短段。
        # 门槛降到 1.25 倍，但要求三条同时成立：行首有脚注符（unspeck 剥掉的
        # 前缀接回来看）、该段到页尾**每一行**字号都在界下、且不超过 6 行。
        # 全书只命中这 3 页。
        for i in range(len(gaps) - 1, len(gaps) * 55 // 100 - 1, -1):
            zone = L[i + 1:]
            if len(zone) > 6:
                break
            if gaps[i] >= lead * 1.25 and had_fn_mark(zone[0]) and \
                    all(x['size'] < fn_max for x in zone):
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
    # 兜底三：按**字号**认注区。上面每一道都要求「注区顶上有一道可见空隙」
    # 或「注区顶上有脚注符」；两者同时失效的情形是——注区首行是**上一页脚注
    # 的接续**（没有脚注符），而那道空隙又恰好差一点点没到门槛
    # （p99 实测 79 px vs 1.5×53=79.5）。两条一起失效，整条编者长注就整段
    # 落进正文，还被一行一段地拆开。全书 15 页、478 行。
    #
    # 用的是 calibrate 算出来的 fn_max——一个按卷校准、尺度无关的绝对字号界
    # （vol1 40.5 / vol2 51.5）。这个参数一直传进来却从没被用过。
    if best is None or len(L) - best < 4:
        alt = _fn_zone_by_size(L, fn_max, lead, gaps)
        if alt is not None and (best is None or alt < best):
            # 「已判出但只切了几行」也要覆盖：p99 现有规则只认出末尾 2 行，
            # 另外 30 行注文还留在正文里。全书 64 个「注区 <4 行」的页面里，
            # 这条判据只对 p99 提出覆盖，其余一律 None——不会乱动。
            best = alt
    # 兜底四：整页大半是编者长注的页面。上面每一道都拿本页的参考行距 lead
    # 当尺子，而 lead 取的是页顶前 8 行——这种页面页顶只剩三五行正文，那
    # 8 个间隙里混着注区的紧行距，尺子本身就被压短了（p262 实测 45 vs 真正
    # 的正文行距 54），「区内行距明显比正文紧」于是永远不成立。整条长注
    # 留在正文里，还被一行一段地拆开，带着原书每行行首重复的 `“`
    # （v1p99/197/255/256/262/268/366/370/620/621、v2p222 共 11 页 ~340 行）。
    #
    # 这一道换成**卷级**的正文行距（VOL_LEAD，只取字号在界上的相邻行对算，
    # 与页面构成无关），判据是「页尾一整段小字 + 区内行距紧 + 切口看得见」：
    #   · 页尾连续 ≥8 行字号在界下（长注一定连到页脚）
    #   · 区内行距 < 0.9 × 卷级正文行距
    #   · 切口 ≥ 1.3 × 卷级正文行距，或注区首行带脚注符
    # 切点在「小字起点」前后两行里取断口最大的那一个——正文末行常是短行，
    # 量得的字号偏小，会把切点往前拽一两行（v1p197 的
    # `its fervid devotion, to pray and desire.` 实测）。
    # 拿全书试跑：这一道认出 147 页，其中 136 页与现有产物**完全一致**，
    # 另外 11 页就是上面那批漏判；11 处切点逐页对照 600 dpi 影像核过。
    alt = _fn_zone_tail(L, fn_max)
    if alt is not None and (best is None or alt < best):
        best = alt
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
    # 章末标记（`END OF THE FIRST CHAPTER.` / `FINIS.`）印在页脚上方、字号
    # 与脚注一样小，会被一并划进注区，发布出来成了一条莫名其妙的脚注
    # （全书 3 处：v1p417 / v1p630 / v2p222）。它是居中的章末标记，不是注，
    # 划回正文交给居中标题那一路。
    while len(L) > best and CHAP_END_RE.match(clean(L[-1]['text'])):
        tail = L.pop()
        L.insert(best, tail)
        best += 1
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


# 夹在两个小写词之间的孤立标点是扫描斑点（`be ye . reconciled to God`、
# `which we readily ] confess`）。davenant_witness.stray_repair 已在**行内**
# 处理，但斑点常落在**行尾**——拼成段落之后才看得见（行内 40 处，段落层 109
# 处）。所以这里再扫一遍。逐条看过 97 处，没有一处是原书的真标点：英文排版
# 里不会出现「小写词 + 空格 + 孤立句点 + 空格 + 小写词」。
# 前一个字符也可能是脚注符（`Durandus* . also writes`）——那时词尾不是字母，
# 只认 `[a-z]` 会把这一处漏掉。
# `,` 也算：`the knowledge of the things to be believed, and of , those to be
# done`（9 处）。但 `;` 与 `:` **不算**——原书排的就是「空格 + 分号」
# （19 世纪英式行文，全书 1736 处分号、334 处冒号都是这个样子），
# 把它们当斑点会把整本书的标点删光。
STRAY_MID = re.compile(r'(?<=[a-z,;*\u2020\u2021]) [.\]\[,] (?=[a-z])')


# 断词中间夹了斑点：`personally un- . known` / `per- . son`。连字与续行之间
# 多一个孤立句点，dehyph 已经把两半接起来了，斑点留在中缝（实测 26 处）。
# 中缝里的斑点不只是句点：`doc-: trine` `princi-, palities` `de- , lightful`
# `rea- ] son` 都有（全书 27 处），连字与续行之间夹什么标点的都有。
HYPHEN_STRAY = re.compile(r'([a-z])-\s*[.,;:\]\[]\s*([a-z])')


# 断词的后一半跑到了下一个 token 上，中缝只剩一个空格（`ef- fect`）。
# 连字符后面**紧跟空格**这个形状本身就是换行断词的痕迹——原书排的复合词
# （`well-known`）连字符后不带空格。再卡一道「接起来必须是词」。
HYPHEN_SPLIT = re.compile(r'\b([a-z]{2,})-\s+([a-z]{2,})\b')

# 书眉。左页 `250 AN EXPOSITION OF ST. PAUL'S — Chap. iv.`、
# 右页 `EPISTLE TO THE COLOSSIANS. 293`。绝大多数在行层就被剥掉了，
# 漏网的是 `ST.` 被读成 `$T` `8T` `5T` `8ST` 那些——版面在段落中缝断页，
# 书眉就嵌进了句子里（实测 19 处）。剥掉正好把句子接回去。
HEADER_L = re.compile(
    r'\s*\d{1,3}\s+AN\s+EXPOSITION\s+[A-Z]{2}\s+[\$0-9A-Z]{0,2}T\.?\s*'
    r"PAUL['\u2019]?[Ss]?\s*(?:[—–-]\s*)?(?:<em>)?\s*Chap\.?\s*(?:</em>)?"
    r'\s*[ivwxl]+\.?\s*')
HEADER_L2 = re.compile(
    r"\s*\d{1,3}\s+AN\s+EXPOSITION\s+[A-Z]{2}\s+[\$0-9A-Z]{0,2}T\.?\s*"
    r"PAUL['\u2019]?[Ss]?\s*(?:[—–-]\s*)?")
HEADER_R = re.compile(
    r'\s*EPISTLE\s+TO\s+T[HI][EI]\s+COLOSSIANS\.?\s*\d{1,3}\s*',
    re.IGNORECASE)
# 印张标记（`VOL. II. U 2` 读成 `Vise Iie u 2`）
SIGNATURE = re.compile(r'\s*Vise\s+Iie\s+u\s+2\s*')


def strip_header(t):
    for rx in (HEADER_L, HEADER_L2, HEADER_R, SIGNATURE):
        t = rx.sub(' ', t)
    return t


def _rejoin(m):
    from davenant_witness import attested
    return m.group(1) + m.group(2) if attested(m.group(1) + m.group(2)) \
        else m.group(0)


# 换行的连字符被读成了句点：`Chris. tian` `them. selves` `de. serving`。
# 与 HYPHEN_SPLIT 是同一件事，只是断的那一笔读成了别的字符。
DOT_SPLIT = re.compile(r'\b([A-Za-z]{2,})\. ([a-z]{2,})\b')
# 后半是这些的时候，前半是**人名/书名缩写**，不是断词——
# `says August. in Ps. cxviii.` 是「奥古斯丁，在诗篇……」，
# 合成 `Augustin Ps.` 就把引文出处吃掉了（实测）。
DOT_SPLIT_CITE = {'in', 'ad', 'de', 'contr', 'cont', 'adv', 'advers', 'lib',
                  'cap', 'ep', 'epist', 'serm', 'hom', 'tom', 'tract', 'qu',
                  'quest', 'art', 'sup', 'super', 'on', 'upon', 'apud', 'ex'}


def _dotjoin(m):
    from davenant_witness import attested, corpus, DOT_ABBR, BIBLE_ABBR
    a, b = m.group(1), m.group(2)
    if a.lower() in DOT_ABBR or a.lower() in BIBLE_ABBR or b in DOT_SPLIT_CITE:
        return m.group(0)
    j = a + b
    if not attested(j):
        return m.group(0)
    # 两半各自都是词、拼起来在本书里又一次都没出现过 → 多半是两句话，别接
    # （`VI. and` `IV. in` `may. be` 全靠这一条挡住）
    _, uni = corpus()
    if attested(a) and attested(b) and uni[j.lower()] == 0:
        return m.group(0)
    return j


def drop_stray(t):
    t = HYPHEN_STRAY.sub(r'\1\2', t)
    t = HYPHEN_SPLIT.sub(_rejoin, t)
    t = DOT_SPLIT.sub(_dotjoin, t)
    t = strip_header(t)
    return STRAY_MID.sub(' ', t)


def build_paragraphs(vol, lo, hi, fn_max, indent_min):
    """→ ([(文本, 页码, 是否缩进条)], footnotes, stats)"""
    paras, fns, stats = [], [], collections.Counter()
    cur, cur_pages = '', set()          # 段落跨了哪几页——脚注配对要按页对齐
    cur_kind = ''                       # '' / 'item'（右移块的一条）/ 'head'（居中小标题）
    last_kind = ''                      # 上一页最后一行的角色——版式块可能正好断在页末
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
        # 行首斑点先剥掉并把 x0 推回去，否则段首判据整行失灵（见 unspeck）
        for l in lines:
            t2, x2 = unspeck(l)
            if t2 != l['text']:
                l['text'], l['x0'] = t2, x2
        # 行**末**右边距上的孤立斑点：`…but to the Son, and to -` / `…such
        # readers as are .`，下一行接着往下排，产物里就成了句中的 ` - `／` . `
        # （`the argument of this - Chapter` 是用户看到的那一处）。
        # 英文排版里不会出现「小写词 + 空格 + 孤立短横／句点」收行——真正的
        # 破折号不带前空格，真正的句号也不会以空格与前一个词隔开。
        # 全书 `-` 31 处、`.` 80 处，`-` 的 31 处与 `.` 里下一行大写起首的
        # 4 处**逐条读过**，无一例外都是斑点（`and to - the Holy Spirit`、
        # `says . Bernard`）；`.` 的其余各处下一行都是小写起首，真句号不可能
        # 后接小写。所以这里不再卡下一行。
        for k in range(len(lines) - 1):
            if TAIL_SPECK.search(lines[k]['text'].rstrip()):
                lines[k]['text'] = lines[k]['text'].rstrip()[:-1].rstrip()
        body, fn = split_page(lines, fn_max)
        if fn:
            stats['fn_pages'] += 1
            fns.append((p, fn))
        x0 = page_body_x0(body)
        ds = line_offsets(body, x0, indent_min)
        starts = [d > indent_min for d in ds]
        # 行首斑点把段首缩进吃掉了。`unspeck` 按**字符数比例**把 x0 推回去，
        # 而斑点与首词之间那一大片空白被 OCR 收成了一个空格，比例算不出来，
        # 推不够（v2p13 `! The first, comprehended…` 实测推到 ds=25、门槛 31，
        # 差 6 px；页面上它与底下的 `1.` 左边界齐平，是实打实的段首）。
        # 只捞这一档：本行剥过斑点 + ds 落在半个门槛到门槛之间 + 首字母大写
        # + 上一行以**句点**收尾。全书两处（v1p460 `Hence we may lay it down,`、
        # v2p13 那一行），都对着 400 dpi 影像核过。
        # ⚠️ 上一行放宽到 `:` `;` 收尾会多进来 v2p25——那是「…two things:
        # How we are dead ; and, How much…」的续行，不是段首。
        for k in range(1, len(body)):
            if starts[k] or not body[k].get('speck'):
                continue
            if not (0.5 * indent_min <= ds[k] < indent_min):
                continue
            if not body[k]['text'][:1].isupper():
                continue
            if body[k - 1]['text'].rstrip().endswith('.'):
                starts[k] = True
        marks = outline_items(body, ds, indent_min)
        right = text_right(body)
        heads = centered_heads(body, ds, starts, marks, x0, right, indent_min)
        # 同一个小鉴题，原书还有「不居中、只比段首多缩一格」的排法（29 处）
        heads = indent_heads(body, ds, starts, marks, heads, right,
                             indent_min, (vol, p))
        # 右移的块（引诗／经文／分析表）之后，正文接着往下排是**不缩进**的：
        # v2p298 两行引诗右移，接着 `But now among the many operations…` 顶格
        # 续排。只看缩进会把它读成引诗那一行的续行，整段散文黏在诗句后面。
        # 全书触发 2 处，另一处 v1p86（`THERE are four parts…` 接在经文末行
        # 之后）本来就被经文对齐那一步切开了，这里只是把它提到行一级。
        # 居中标题底下的正文同样**不缩进**（章题 `THE FOURTH CHAPTER.` 底下
        # 的 `I premise a few things…` 顶格起，还带大写首字），章题因此被
        # 拼进第一段：页面上是三行居中的章题，产物里是
        # `THE FOURTH CHAPTER. I premise a few things…` 一整段。
        for k in range(1, len(body)):
            if (marks[k - 1] or heads[k - 1] in ('head', 'rubric')) \
                    and not marks[k] \
                    and not starts[k] and body[k]['text'][:1].isupper():
                starts[k] = True
        kinds = [h if h else ('item' if m else '')
                 for h, m in zip(heads, marks)]
        # 版式块断在页末时，下一页第一行的正文同样顶格续排，页内那条判据
        # 看不见跨页的上一行（v1p357 的引诗末行在页末，`So Christ himself
        # exclaims…` 落到下一页页顶，整段散文因此黏在诗句后面）。
        if body and last_kind in ('item', 'head', 'rubric') and not marks[0] \
                and not starts[0] and body[0]['text'][:1].isupper():
            starts[0] = True
        last_kind = kinds[-1] if kinds else ''
        for l, is_start, kind in zip(body, starts, kinds):
            # 第二证人：拿 PDF 自带的 IA OCR 层校我们这一遍（见
            # scripts/davenant_witness.py）。两遍都是 tesseract，但版本、
            # 预处理、切页都不同，错处基本不重叠。只在「我方非词、对方是词、
            # 形近且不变短」时采信，孤立的 `|` `/` 另按斑点规则处理。
            raw = fix_enum_head(l['text']) if is_start else l['text']
            txt = clean(W.fix_line(vol, p, raw)[0])
            if not txt:
                continue
            if is_start and cur:
                paras.append((cur, sorted(cur_pages), cur_kind))
                cur, cur_pages, cur_kind = txt, {p}, kind
            elif cur:
                cur = dehyph(cur, txt)
                cur_pages.add(p)
                if cur_kind in ('head', 'rubric', 'attrib'):  # 吃进续行→不算
                    cur_kind = ''
            else:
                cur, cur_pages, cur_kind = txt, {p}, kind
        stats['pages'] += 1
        stats['lines'] += n0
    if cur:
        paras.append((cur, sorted(cur_pages), cur_kind))
    # 段落级再过一遍人工核定表：跨行断词的词（`distin-` + `euished`）
    # 只有在 dehyph 之后才成形，行级那一道看不到它。
    paras = [(W.para_fix(vol, pg, W.manual_para(vol, pg, drop_stray(t))), pg, k)
             for t, pg, k in paras]
    return paras, fns, stats


# 连续的 `[ITEM]`（原书右移排的一条）并成一个 `[OUTLINE]` 块，条与条之间
# 用 `\n` 转义分隔——与 `[BRACE]` 的落盘约定一致。发布那边一条一行渲染，
# 行距是行距，不再是十几个孤零零的短段（v2p232）。
PGMARK_RE = re.compile(r'^<!--v(\d+)p(\d+)(?:-(\d+))?-->')


ORD_N = {'FIRST': 1, 'SECOND': 2, 'THIRD': 3, 'FOURTH': 4}
CHAP_TITLE_RE = re.compile(r'^\[HEAD\](?: <!--[^>]*-->)?\s*THE\s+(\w+)\s+C\w{5,7}\.?\s*$')
H1_RE = re.compile(r'^\[H1\] CHAP\. ([IVX]+)\s*$')


def lift_chapter_head(lines):
    """把 `[H1] CHAP. N` 提到本章**章题**那一组之前。

    原书每章开头是三行居中的章题（`EXPOSITION / OF / THE SECOND CHAPTER.`），
    其后是几页总论（本章旨趣、四点分段、`OF THE EXORDIUM.`…），再往下才是
    `Verse 1.`。而 `[H1]` 是按正文里那行 `CHAP. II.` 认的——它印在第一节释经
    那一页上，于是章题连同四页总论（v1p418-421）全落进了上一章：发布出来
    第一章页尾挂着第二章的章题与开篇（实测）。

    判据：`[H1] CHAP. N` 往回扫，**不跨过 [SECTION]/[SCRIPTURE]/[H1]**，
    遇到本章的 `THE <序数> CHAPTER.` 居中题就把 H1 移到该题那一组之前
    （连着的 `EXPOSITION` / `OF` 两行一起算作一组）。
    第三、四章不受影响：它们的 H1 本来就紧挨着自己的第一个节组，往回扫先
    撞上 [SECTION]（第四章的章题排在 4:1 释经之后，属于章内容的一部分）。
    """
    out = list(lines)
    for i, ln in enumerate(out):
        m = H1_RE.match(ln)
        if not m:
            continue
        want = {v: k for k, v in ROMAN.items()}.get(m.group(1)) if 'ROMAN' in globals() \
            else None
        want = want or {'I': 1, 'II': 2, 'III': 3, 'IV': 4}.get(m.group(1))
        j = i - 1
        hit = None
        while j >= 0:
            t = out[j]
            if t.startswith(('[SECTION]', '[SCRIPTURE]', '[H1]')):
                break
            mt = CHAP_TITLE_RE.match(t)
            if mt and ORD_N.get(mt.group(1).upper()) == want:
                hit = j
                break
            j -= 1
        if hit is None:
            continue
        # 往前把同一组的 `EXPOSITION` / `OF` 收进来，但**不要越过章末标记**
        # ——`END OF THE FIRST CHAPTER.` 属于上一章，紧挨着下一章的章题。
        k = hit
        while k - 1 >= 0 and out[k - 1].startswith('[HEAD]') and \
                not CHAP_END_RE.match(re.sub(r'^\[HEAD\](?: <!--[^>]*-->)?', '',
                                             out[k - 1]).strip()):
            k -= 1
        out.insert(k, out.pop(i))
    return out


def merge_outline(lines):
    out, buf = [], []

    def flush():
        if not buf:
            return
        vols, pgs, texts = set(), [], []
        for body in buf:
            m = PGMARK_RE.match(body)
            if m:
                vols.add(int(m.group(1)))
                pgs += [int(m.group(2)), int(m.group(3) or m.group(2))]
                body = body[m.end():]
            texts.append(body)
        pg = ''
        if len(vols) == 1 and pgs:
            lo, hi = min(pgs), max(pgs)
            pg = f'<!--v{vols.pop()}p{lo}-->' if lo == hi \
                else f'<!--v{vols.pop()}p{lo}-{hi}-->'
        out.append('[OUTLINE] ' + pg + '\\n'.join(texts))
        buf.clear()

    for ln in lines:
        if ln.startswith('[ITEM] '):
            buf.append(ln[len('[ITEM] '):])
            continue
        flush()
        out.append(ln)
    flush()
    return out


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


def kjv_repair(scr, chap, nums, kjv, vol, pages):
    """经文块拿 KJV 再校一遍。→ (改后的经文, [(原, 新), …])

    本书的经文引的就是 KJV，所以在**经文块之内**，KJV 是一个独立于三遍 OCR
    的证人。逐词对齐后按两条采信：

      · 我方这个词不是词（`fot` / `chidren` / `salutcth` / `covelousness`）
        → 直接用 KJV 的
      · 我方是正经英文词，但三遍 OCR 的页面里**一次都没出现过**它，而 KJV
        那个词出现了 → 也用 KJV 的。歌 3:8 的 `out of your south` 就是这样：
        `south` 是词，词典判据一挡就永远修不成 `mouth`，可三个证人读的都是
        mouth，页面上根本没有 south。

    反过来，`amongst` / `unblamable` / `acknowledgment` / `unto` 这些与 KJV
    不同的读法**不动**——那是 1831 年译本自己的拼法，证人们读到的也是它们，
    照 KJV 改就是篡改底本。
    """
    exp = ' '.join(kjv.get(f'{chap}:{v}', '') for v in nums).strip()
    if not exp:
        return scr, []
    mine, theirs = scr.split(), exp.split()
    a = [W._norm(x) for x in mine]
    b = [W._norm(x) for x in theirs]
    seen = None
    fixes = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag != 'replace' or (i2 - i1) > 2 or (j2 - j1) != 1:
            continue
        cand = re.sub(r'[^A-Za-z]', '', theirs[j1])
        got = ''.join(a[i1:i2])
        if not cand or not got or got == W._norm(cand):
            continue
        lim = 6 if i2 - i1 > 1 else 4     # 并词（断词没接上）放宽一档
        if sum(1 for _ in difflib.ndiff(got, cand.lower()) if _[0] != ' ') > lim:
            continue                      # 编辑距离超了不认
        # 判词性只认词典与屈折形，**不看本书频次**：`ts` 是 OCR 常见的错字
        # 形状（全书 36 次），按频次判它就成了"词"，歌 3:25 的 `ts` 永远修不成
        # `is`。经文块里有 KJV 当参照，用严一点的词表反而更稳。
        if any(W._norm(x) in W.DICT or W._norm(x) in W.inflected()
               for x in mine[i1:i2]):
            if seen is None:
                # ⚠️ 证人那边的行也是断词的。`perfect` 在三遍 OCR 里都排成
                # `per-` + `fect` 两行，不先接回去就查不到，`per- Sect` 这处
                # 永远修不成（实测）。按提取器同一套 dehyph 接。
                seen = set()
                for pg in pages:
                    for fn in (W.ia_lines, W.w3_lines, W.grc_lines):
                        joined = ''
                        for l in (fn(vol, pg) or []):
                            joined = dehyph(joined, l) if joined else l
                        seen |= {W._norm(t) for t in joined.split()}
            if got in seen or W._norm(cand) not in seen:
                continue                  # 版本拼法之别，不是 OCR 错
        head = re.match(r'^\W*', mine[i1]).group(0)
        tail = re.search(r'\W*$', mine[i2 - 1]).group(0)
        new = head + (cand.capitalize() if mine[i1][:1].isupper() else cand) + tail
        fixes.append((' '.join(mine[i1:i2]), new))
        mine[i1:i2] = [new]
        a[i1:i2] = [W._norm(new)]
    return ' '.join(mine), fixes


# ── 花括号分析表：按页面影像手工重建 ────────────────────────────────────────
# 原书用一个大括号把一个标签分成三支排版。OCR 按**基线**读，于是右栏每一支
# 被拆成一行一段，左栏那行标签还被切进右栏文字中间
# （v2p246：`What is to besought? 4 culty; To speak the mystery`）。
# 几何上是能认的（正文左边界 226，右栏 798-897），但全书这一类落在四章正文里
# 只有 4 处，为它写一个几何解析器不划算也不稳。按 600 dpi 页面影像逐张手工
# 重建，落进 brace_blocks.json，与 manual_votes 一样**按位置**定位。
BRACE_TBL = RAW / 'brace_blocks.json'
_brace = None


def brace_blocks():
    global _brace
    if _brace is None:
        _brace = ({k: v for k, v in
                   json.loads(BRACE_TBL.read_text(encoding='utf-8')).items()
                   if not k.startswith('_')} if BRACE_TBL.exists() else {})
    return _brace


def apply_brace(vol, paras, lo=None, hi=None):
    """把表里记着的连续段落换成重建好的块。

    ⚠️ 对不上就**报错**，不静默跳过。这条线上栽过的坑是「规则一改，按整串
    匹配的人工表就静默失效」——157 条票只落实 90 条，是事后才查出来的。
    """
    tbl = {k.split('|')[1]: v for k, v in brace_blocks().items()
           if k.split('|')[0] == str(vol)}
    # 试跑（--pages）只建一小段，表里别页的条目当然对不上——只核范围内的。
    if lo is not None:
        tbl = {k: v for k, v in tbl.items() if lo <= int(k) <= hi}
    if not tbl:
        return paras, 0
    hit = 0
    for page, rec in sorted(tbl.items(), key=lambda kv: int(kv[0])):
        want = rec['match']
        for i in range(len(paras) - len(want) + 1):
            if [paras[i + k][0] for k in range(len(want))] != want:
                continue
            if str(int(page)) not in [str(x) for x in paras[i][1]]:
                continue
            pages = sorted({x for k in range(len(want)) for x in paras[i + k][1]})
            paras[i:i + len(want)] = [(BRACE_MARK + rec['html'], pages, '')]
            hit += 1
            break
        else:
            raise SystemExit(
                f'✗ brace_blocks v{vol}p{page}：对不上产物，表该重建了\n'
                f'  表里第一段： {want[0]!r}')
    return paras, hit


BRACE_MARK = '\x00BRACE\x00'

# 经文块切出来的尾巴：`&c.` / `c.`（`&` 被 OCR 吃掉）/ 孤立的标点
SCR_TAIL_RE = re.compile(r'(&\s*)?c\.?|[,;:.]')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', type=int, choices=(1, 2))
    ap.add_argument('--pages', help='如 86-170，需配 --vol')
    a = ap.parse_args()
    kjv = json.loads((RAW / 'kjv_colossians.json').read_text(encoding='utf-8'))

    plan = ([(a.vol, *(int(x) for x in a.pages.split('-')))] if a.pages
            else [(v, *RANGES[v]) for v in ([a.vol] if a.vol else (1, 2))])

    # ── 迭代到不动点 ──────────────────────────────────────────────
    # 词频裁判读的语料（corpus）就是这个脚本自己的产物：跑一遍语料变一次，
    # 下一遍的判断就可能翻过来。实测两次重跑之间来回摆——`epinion→opinion`
    # 这一轮落上、下一轮又没落，`in` 反被判成 `im`。所以这里自己迭代：
    # 重建 → 落盘 → 清掉语料缓存 → 再建，直到产物不再变（最多 4 遍）。
    # 不这么做，产物就不是确定的，同一份输入两次跑出两个结果。

    def build():
        out, total = [], collections.Counter()
        for vol, lo, hi in plan:
            pages = [r for r in load(vol) if RANGES[vol][0] <= r['page'] <= RANGES[vol][1]]
            fn_max, indent_min = calibrate(pages)
            paras, fns, st = build_paragraphs(vol, lo, hi, fn_max, indent_min)
            paras, n_brace = apply_brace(vol, paras, lo, hi)
            st['brace'] = n_brace
            total.update(st)
            print(f'  vol{vol}: 页 {lo}-{hi}  脚注字号上限 {fn_max} 缩进阈值 {indent_min}  '
                  f'段落 {len(paras)}  含脚注页 {st["fn_pages"]}  剥页眉 {st["head"]}  '
                  f'花括号表 {st["brace"]}')

            seen_chap, cur_chap, pend = False, None, None
            i = 0
            while i < len(paras):
                para, ppages, kind = paras[i]
                i += 1
                if para.startswith(BRACE_MARK):
                    pg = (f'<!--v{vol}p{ppages[0]}-->' if len(ppages) == 1
                          else f'<!--v{vol}p{ppages[0]}-{ppages[-1]}-->') if ppages else ''
                    out.append('[BRACE] ' + pg
                               + para[len(BRACE_MARK):].replace('\n', '\\n'))
                    continue
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
                        scr, kfix = kjv_repair(scr, cur_chap, used, kjv, vol, ppages)
                        for o, n in kfix:
                            print(f'  [KJV 校经] {cur_chap}:{used} {o!r} → {n!r}',
                                  flush=True)
                            total['kjv_fix'] += 1
                        # 引文尾巴的 `&c.` 跟着经文走。它跟 KJV 对不上，贪心增长
                        # 到它这一段相似度只会掉，于是被留在外面成了孤零零一段
                        # `&c.`（vol2 p233 实测，页面上就印着 "…with thanksgiving,
                        # &c."）。经文收尾后紧跟的独立 `&c.` 段直接并回去。
                        # 引文尾巴的 `&c.` 跟着经文走。KJV 里没有这两个字，
                        # split_scripture 的切点落在它前面，于是它被当成正文
                        # 甩出来，页面上多一段孤零零的 `&c.`（vol2 p233 实测，
                        # 原书印的是 "…with thanksgiving, &c."）。
                        # `&` 掉了只剩 `c.`、或只剩一个逗号分号的，同样是经文的
                        # 尾巴，不是段落（v1p195 的 `c.`、v1p295 的 `,`、
                        # v2p306 的 `;` 实测，页面上就是三段孤零零的标点）。
                        if rest and SCR_TAIL_RE.fullmatch(rest.strip()):
                            scr, rest = scr.rstrip() + ' ' + rest.strip(), ''
                        elif not rest and i < len(paras) and \
                                SCR_TAIL_RE.fullmatch(paras[i][0].strip()):
                            scr = scr.rstrip() + ' ' + paras[i][0].strip()
                            i += 1
                        # 原书的经文栏里常常连着印**下一节的开头**（`Vers. 9.`
                        # 底下把第 10 节两行一并排进去、`Vers. 10.` 底下压着
                        # `Where there is neither Greek, &c.`）。贪心增长按本节
                        # 的 KJV 比相似度，多出来的那几行只会把相似度拉低，于是
                        # 被甩成正文段落——页面上就是经文框底下挂着两段没头没尾
                        # 的经文（v2p84 / v2p93 实测，全书 2 处）。
                        # 这里按**下一节**的 KJV 前缀再贪心收一次，像了才收，
                        # 收进来的节号一并记进块头。
                        while cur_chap and i < len(paras):
                            nv = used[-1] + 1
                            key = f'{cur_chap}:{nv}'
                            if key not in kjv:
                                break
                            pool2, j2, pick = [], i, None
                            while len(pool2) < 4 and j2 < len(paras) and not (
                                    CHAP_RE.match(paras[j2][0])
                                    or SECTION_RE.match(paras[j2][0])):
                                pool2.append(paras[j2][0]); j2 += 1
                                c2 = _join(pool2)
                                if len(c2) < 12:
                                    continue
                                r2 = sim(c2, kjv[key][:len(c2) + 10])
                                if pick is None or r2 > pick[1]:
                                    pick = (c2, r2, len(pool2))
                            if pick is None or pick[1] < 0.8:
                                break
                            print(f'  [经文续节] {cur_chap}:{used} + {nv} '
                                  f'（相似度 {pick[1]:.3f}）', flush=True)
                            scr = scr.rstrip() + ' ' + pick[0].strip()
                            used = used + [nv]
                            i += pick[2]
                            total['scr_next'] += 1
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
                        r'^(AN EXPOSITION|OF THE|EPISTLE OF ST\..*'
                        r'|COLOSSIANS\.?)\s*$', para):
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
                        paras.insert(i, (rest, ppages, ''))
                    else:
                        pend = [1, 2] if cur_chap else None
                        if rest:
                            paras.insert(i, (rest, ppages, ''))
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
                        paras.insert(i, (rest, ppages, ''))
                    continue
                m = LEMMA_RE.match(para)
                if m and 0 < len(m.group(1).split()) <= 20 and '(' not in m.group(1):
                    out.append(f'[LEMMA] {pg}{m.group(1).strip()}')
                    total['lemma'] += 1
                    rest = clean(para[m.end():])
                    if rest:
                        out.append(f'[BODY] {fix_label(rest)[0]}')
                    continue
                tag = {'item': 'ITEM', 'head': 'HEAD', 'rubric': 'RUBRIC',
                       'attrib': 'ATTRIB'}.get(kind, 'BODY')
                out.append(f'[{tag}] {pg}{fix_label(para)[0]}')

            for p, fn in fns:
                x0 = page_body_x0(fn)
                cur = ''
                for l, is_start in zip(fn, para_starts(fn, x0, indent_min)):
                    t = clean(W.fix_line(vol, p, l['text'])[0])
                    # 原书排长引文时**每一行行首都重复一个开引号**（19 世纪
                    # 惯例）：`“ proceeds from the disposition, so natural…`。
                    # 这些行的文字整体缩了一格、引号顶在左边，按缩进读每一行
                    # 都是段首，一条注被切成十几条，引号还一个个留在正文里
                    # （v1p262/268 的尼西亚会议长注是标本）。
                    # 判据是引号账：只有当前累积的注里还有**没闭合**的开引号时，
                    # 才把行首这个引号当续行标记剥掉。
                    # ⚠️ 行首那个引号多半已经被 unspeck 当斑点剥掉了（`“` 在
                    # 斑点字符表里），而且 OCR 把它读成 `**` / `''` / `"` 各种
                    # 花样（v1p262 实测 `** `）。所以看的是**剥掉的那个前缀**，
                    # 并且按「注区里只有脚注符才起新条」定：前缀是引号一类的
                    # 就一律算续行——真要起一条新注，行首是 `*` / `†`，
                    # 单个符号不在这张表里。
                    if QUOTE_SPECK.match(l.get('speck', '').strip()) or \
                            QUOTE_SPECK.match(t[:2].strip()):
                        if QUOTE_SPECK.match(t[:2].strip()):
                            t = t[2:].lstrip() if t[:2].strip() in ('**', "''", '``', ',,') \
                                else t[1:].lstrip()
                        is_start = False
                    # 脚注符本身就是分条的界标，不能只看缩进：同页两条短注常常
                    # 首行缩进一模一样（vol1 p151 两条都是 x0=214），只看缩进会把
                    # 第二条当续行并进第一条，页面上就出现 `\* That is, indefinite…
                    # + That is, formed…` 两条注挤成一条（实测 7 处）。
                    if (is_start or FN_MARK.match(t)) and cur:
                        out.append(f'[FN] <!--v{vol}p{p}--> {drop_stray(cur)}')
                        cur = t
                    elif cur:
                        cur = dehyph(cur, t)
                    else:
                        cur = t
                if cur:
                    out.append(f'[FN] <!--v{vol}p{p}--> {drop_stray(cur)}')

        # 落盘前统一再清一遍孤立标点。段落那一层已经清过，但经文块、节号
        # 余段等几条路径是在 build_paragraphs 之外拼出来的，绕过了那一道
        # （`philosophy and vain . deceit` 就漏在经文块里）。这里是所有
        # 落盘路径的必经之处。
        return lift_chapter_head(merge_outline(
            [drop_stray(x) for x in out])), total

    prev = None
    for _round in range(4):
        out, total = build()
        joined = "\n".join(out)
        if joined == prev:
            break
        prev = joined
        dst0 = RAW / ('davenant_colossians_structured.txt' if not a.pages
                      else 'sample_structured.txt')
        dst0.write_text(joined + '\n', encoding='utf-8')
        W.reset_corpus()
    else:
        print('  ⚠ 四遍仍未收敛，取最后一遍', flush=True)

    dst = RAW / ('davenant_colossians_structured.txt' if not a.pages
                 else 'sample_structured.txt')
    dst.write_text('\n'.join(out) + '\n', encoding='utf-8')
    print(f'[ok] → {dst.name}  {dst.stat().st_size:,} 字节  {len(out)} 行')
    n_out = sum(1 for x in out if x.startswith('[OUTLINE] '))
    n_row = sum(x.count('\\n') + 1 for x in out if x.startswith('[OUTLINE] '))
    print(f'  缩进块 {n_out}（共 {n_row} 条）')
    print(f'  CHAP {total["chap"]} · 节组 {total["sec"]} · 经文块 {total["scr"]}'
          f'（对不上 {total["scr_fail"]}）· lemma {total["lemma"]} · '
          f'共 {total["pages"]} 页 {total["lines"]} 行')
    return 0


if __name__ == '__main__':
    sys.exit(main())
