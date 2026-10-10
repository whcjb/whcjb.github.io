#!/usr/bin/env python3
"""约翰斯通《腓立比书讲疏》—— ABBYY 版面 × tesseract 字形 → en_chapters/。

    johnstone_raw/philippians/src/abbyy1875.xml.gz   版面结构 + 斜体
    johnstone_raw/philippians/src/ocr_eng/NNNN.txt   tesseract eng+grc 的字
            │  johnstone_common.transfer_page（按段对齐，区间搬斜体）
            ▼
    johnstone_raw/philippians/en_chapters/*.md

全书分段（见 PROVENANCE.md 的目录抄录）：
    preface · introduction · 1..30（讲章） · translation · notes-1..4 · polycarp

页码偏移不写死：ABBYY 的 XML 页数（520）和 jp2 的图数不一定相等，
扫描流程里多出来的大幅面页（8 张 3744×5616）就是差额的来源。按**印刷页码**
对，不按序号对 —— 两边各自从页眉里读出印刷页码，对不上就报错不硬跑。
"""
import argparse
import difflib
from collections import Counter
import collections
import gzip
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xml.etree.ElementTree as ET
import alexander_abbyy as A
import johnstone_common as J

ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, 'johnstone_raw', 'philippians')
XML_GZ = os.path.join(RAW, 'src', 'abbyy1875.xml.gz')
OCR_DIR = os.path.join(RAW, 'src', 'ocr_eng')
OUT_DIR = os.path.join(RAW, 'en_chapters')

# 30 篇讲题，抄自书前目录（leaf 0015/0016）。两套互不相干的 OCR
# ——IA 2010 年的 ABBYY 8.0 与本地 2026 年的 tesseract 5.5——在这份目录上
# 逐条一致，所以这不是「我编的标题表」，是底本自己给的。
LECTURES = [
    'Address and Salutation',
    'Pleasant Memories and Bright Hopes',
    'Prayer for Spiritual Discernment',
    'The Gospel in Rome',
    'Sufferings turning to Salvation',
    "The Saint's Life—Christ",
    "The Saint's Death—Gain",
    'A Strait betwixt Two',
    'Conversation becoming the Gospel',
    'Stedfastness for Christ',
    'Christian Concord',
    'The Great Example',
    'Working out our own Salvation',
    'Lights in the World',
    'Joy in Prospect of Martyrdom',
    'Mission of Timothy',
    'Mission of Epaphroditus',
    'Joy in the Lord',
    'Justification by Faith',
    "The Saint's Aspirations",
    'Pressing toward the Mark',
    'True Wisdom proved by Godliness',
    'Wise Choice of Examples',
    "The Saint's Citizenship and Hope",
    'Stedfastness in the Lord',
    'Brotherly-Kindness',
    'Prayerfulness and the Peace of God',
    'Summary of Duty',
    'Christian Contentment',
    'Christian Liberality and its Reward',
]

# 书末五节的「起头」在版面上长什么样，跟目录里的条目名**不是一回事**：
# 目录写「Notes on the Greek Text of Chapter II.」，正文那一页印的只有
# `CHAPTER II.` 五个字。拿目录名去找会找到页眉上去（实测 notes-2 切在了
# p.445 的页眉、notes-3 根本没找着）。所以这里记的是**印刷实样**。
TAIL = [
    ('translation', 'Revised Translation of the Epistle of Paul to the Philippians',
     'Revised Translation of the Epistle'),
    ('notes-1', 'Notes on the Greek Text. Chapter I.',
     'Notes on the Greek Text of Chapter I'),
    ('notes-2', 'Chapter II.', 'Notes on the Greek Text of Chapter II'),
    ('notes-3', 'Chapter III.', 'Notes on the Greek Text of Chapter III'),
    ('notes-4', 'Chapter IV.', 'Notes on the Greek Text of Chapter IV'),
    ('polycarp', 'Epistle of Polycarp to the Philippians',
     'Epistle of Polycarp to the Philippians'),
]


def load_xml():
    plain = os.path.join(RAW, 'src', 'abbyy1875.xml')
    if not os.path.exists(plain) or os.path.getmtime(plain) < os.path.getmtime(XML_GZ):
        with gzip.open(XML_GZ, 'rb') as fi, open(plain, 'wb') as fo:
            shutil.copyfileobj(fi, fo)
    return plain


def ocr_pages():
    """leaf 序号 → 行列表"""
    out = {}
    if not os.path.isdir(OCR_DIR):
        return out
    for name in sorted(os.listdir(OCR_DIR)):
        if not name.endswith('.txt'):
            continue
        leaf = int(os.path.splitext(name)[0])
        with open(os.path.join(OCR_DIR, name), encoding='utf-8') as f:
            out[leaf] = f.read().split('\n')
    return out


def drop_duplicate_leaves(ocr, window=5, thresh=0.55):
    """同一页被拍了两遍 → 丢掉糊的那一遍。

    这份扫描件里 p.230–231 各拍了两次：leaf 246/247 是好的，leaf 248/249 是
    补拍，**操作员的手压在正文右侧**，右边一截字被挡掉了（裁图确认过）。
    不查出来的话这两页正文会在产物里**重复出现一遍**，而且重复的那一遍是
    残的 —— `unaltered essenti , hatever varie` 就是它。

    判据：相邻 5 页内正文高度相似（归一化后前 1500 字相似度 >0.55）即判为
    重拍，保留**可识别词更多**的那一张。相邻页正常情况下相似度在 0.2 上下，
    0.55 这条线离得很远。
    """
    keys, order = {}, sorted(ocr)
    for leaf in order:
        t = re.sub(r'[^a-z]', '', '\n'.join(ocr[leaf]).lower())
        keys[leaf] = t
    drop = set()
    for i, a in enumerate(order):
        if a in drop or len(keys[a]) < 400:
            continue
        for b in order[i + 1:i + 1 + window]:
            if b in drop or len(keys[b]) < 400:
                continue
            r = difflib.SequenceMatcher(None, keys[a][:1500], keys[b][:1500],
                                        autojunk=False).ratio()
            if r > thresh:
                worse = a if len(keys[a]) < len(keys[b]) else b
                drop.add(worse)
                print(f'  重拍页：leaf {a:04d} ↔ {b:04d}（相似 {r:.2f}）→ '
                      f'丢 {worse:04d}', file=sys.stderr)
    return drop


def printed_number(lines):
    """从页眉读印刷页码。左页在行首，右页在行尾。读不出返回 None。"""
    for line in lines[:3]:
        t = line.strip()
        if not t:
            continue
        if 'hilippians' in t or re.match(r'^\W*(VER|Ver)', t):
            m = re.match(r'^\W*(\d{1,3})\b', t)
            if m:
                return int(m.group(1))
            m = re.search(r'\b(\d{1,3})\W*$', t)
            if m:
                return int(m.group(1))
        break
    return None


RE_FOLIO = re.compile(r'(?<![A-Za-z0-9])\d{1,3}(?![A-Za-z0-9])')


def has_folio(line):
    """行里有独立的 1–3 位页码？

    这一条是**页眉与节标题的唯一可靠分界**。页眉一律带页码
    （`40 Lectures on Philippians. [CH. I.`、`VER. 8.] …Hopes. 35`、
    `422 Revised Translation of the`），节标题页一律不带（`INTRODUCTION.`）。
    不卡这一条，`Introduction.` 这个形在全书出现 3 次被学成页眉，连带把
    p.1 那个真正的节标题一起剔掉 —— 整篇导论就并进前言里了（实测）。
    """
    return bool(RE_FOLIO.search(line))


def head_shape(line):
    """页眉的「形」：抹掉数字与非字母，剩下的骨架。

    `40 Lectures on Philippians. [CH. I.` 和 `46 Lectures on Philippians. [CH. I.`
    是同一个形；`VER. 8.] Pleasant Memories and Bright Hopes. 35` 与
    `VER. 9.] ...` 也是。正文第一行不会有第二页长成同一个形。
    """
    t = re.sub(r'\[.*$', '', line)
    t = re.sub(r'^\W*[Vv][Ee][Rr][Ss]?\W*\d*\W*\]?', '', t)
    t = re.sub(r'[^A-Za-z]', '', t).lower()
    return t


def head_candidates(lines, n=3):
    """页眉不一定是第 1 行。

    tesseract 常在页顶吐出一两个字的残渣（`ee` / `pit` / `Φ`），把真页眉挤到
    第 2 行。只看第 1 行的话，这些页就认不出所属讲章 —— 实测讲章 18 有 6 页
    因此被划进了讲章 19（它们中间还夹着双页，连带一起漂走）。
    所以在**头三个非空行**里找。
    """
    out = []
    for l in lines:
        t = l.strip()
        if not t:
            continue
        out.append(t)
        if len(out) >= n:
            break
    return out


def pick_head(lines):
    """头三行里挑出那一行页眉：带页码、够长的第一行。挑不出返回 ''。"""
    for t in head_candidates(lines):
        if has_folio(t) and len(t) >= 9:
            return t
    return next((l.strip() for l in lines if l.strip()), '')


def learn_heads(ocr, min_count=3, min_len=6):
    """页眉表让语料自证，不手写。

    手写判据只认得出见过的那几种写法 —— 第一版只写了
    `Lectures on Philippians` 和 `VER.`，结果 `Introduction. 3`、
    `Epistle of Polycarp. 481`、`The Epistle to the Philippians` 全漏进正文，
    还被当成节标题切出六个同名文件互相覆盖。

    改成：取每页第一行的「形」，全书统计，出现 ≥3 次的就是页眉。散文的第一行
    不会在 520 页里重复三次。
    """
    first = {leaf: pick_head(lines) for leaf, lines in ocr.items()}
    cnt = collections.Counter(head_shape(v) for v in first.values()
                              if has_folio(v))
    shapes = {s for s, c in cnt.items() if c >= min_count and len(s) >= min_len}
    return first, shapes


SECTION_TITLES = None            # main() 填；页眉判据要用


def looks_like_head_title(line):
    """页眉的另一支：**节标题 + 页码**。

    `422 Revised Translation of the` 这种，书里只在一页的页首出现过一次，
    频次闸（≥3 次）看不见它。但它有两个一起出现才成立的特征：
    文字跟某个节标题高度相似，而且带一个独立的 1–3 位页码。

    页码这一条不能省 —— 没有它，p.421 那个真正的节标题页
    （`REVISED TRANSLATION / OF THE EPISTLE.`）会被一起剔掉。
    """
    t = line.strip()
    if not t or len(t) > 70 or SECTION_TITLES is None:
        return False
    if not re.search(r'(?<![A-Za-z0-9])\d{1,3}(?![A-Za-z0-9])', t):
        return False
    k = re.sub(r'[^a-z]', '', t.lower())
    if len(k) < 10:
        return False
    return max(difflib.SequenceMatcher(None, k, s).ratio()
               for s in SECTION_TITLES) >= 0.75


DROPCAPS = []
VERSE = {}
WITNESS = {}
VERSE_LOG = []
DROPPED_ITALIC = []


def pars_attrs(par):
    """这一段有没有首行缩进。par 这里是**原始 dict**（带 attrs），
    不是已经拆出来的 text —— 调用方要把 dict 传进来。"""
    if isinstance(par, dict):
        return par.get('attrs', {}).get('startIndent')
    return None


def page_text(pars, lines, first_line, shapes, vflags=None):
    """一页 → markdown。先剔页眉，再合流。

    页眉只剔**本页第一行**那一处。整页逐行比对会把正文里碰巧同形的句子
    一起剔掉，而页眉在版面上只可能在页顶。
    """
    def is_head(s):
        s = s.strip()
        if not s:
            return False
        if s == first_line and has_folio(s) and (head_shape(s) in shapes
                                                 or looks_like_head_title(s)):
            return True
        return J.is_running_head(s)

    body, seen = [], 0
    for l in lines:
        if l.strip() and seen < 3:
            seen += 1
            if is_head(l):
                continue
        body.append(l)
    ocr = J.join_ocr_lines(body)

    keep, keep_v, keep0, dropped_head = [], [], None, False
    for pi, par in enumerate(pars):
        # ⚠️ pars 是**原始 par 字典**，不是 text 串：续行判据要读 attrs
        p = par['text'] if isinstance(par, dict) else par
        plain = J.strip_sentinels(p)[0].strip()
        if not dropped_head and plain:
            dropped_head = True
            head0 = plain.split('\n')[0]
            if is_head(head0) or (has_folio(head0) and head_shape(plain) in shapes):
                continue
        if keep0 is None and plain:
            keep0 = par
        keep.append(p)
        keep_v.append(vflags[pi] if vflags and pi < len(vflags) else None)
    if not keep or not ocr.strip():
        return '', False
    # ABBYY 的 startIndent：首行缩进＝新段落；没有缩进＝上一页的续行。
    # 全书 418 页里 399 页是续行——这正是按页拼接会切错的地方。
    cont = not pars_attrs(keep0)
    return (J.transfer_page(keep, ocr, DROPPED_ITALIC, DROPCAPS, keep_v),
            cont)


def _key(s):
    """标题比对用的归一：只留字母，小写。OCR 的 Zhe/Fustification/Flopes
    这类错字靠 difflib 的相似度兜，不靠规则一条条写。"""
    return re.sub(r'[^a-z]', '', s.lower())


BOOK_HEADS = ('lectures on philippians', 'lecturesonphilippians',
              'the epistle to the philippians', 'theepistletothephilippians')

ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7,
         'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12, 'XIII': 13,
         'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19,
         'XX': 20, 'XXI': 21, 'XXII': 22, 'XXIII': 23, 'XXIV': 24, 'XXV': 25,
         'XXVI': 26, 'XXVII': 27, 'XXVIII': 28, 'XXIX': 29, 'XXX': 30}
RE_ROMAN_LINE = re.compile(r'^\W{0,3}([IVXLivxl]{1,6})\W{0,4}$')


def opens_section(lines, sec):
    """这一页是不是 `sec` 这一节的开篇？

    **讲章不另起新页**。本书的排法是：上一讲在页中收尾，下一讲紧接着往下排，
    所以开篇页照样印着页眉（leaf 80 = p.64，页眉 `64 Lectures on Philippians.`，
    底下才是 `V.` 和 `SUFFERINGS TURNING TO SALVATION.`）。
    早先按「没页眉的那一页就是标题页」去认，30 篇里认错 16 篇 —— 开头全是
    上一讲的半句话。所以这里只认**正文里的讲题行**，不看页眉。

    认两样，中一样即可：
        单独一行的罗马数字，数值等于本讲序号（`V.`）
        一行讲题，跟目录对得上（数字与讲题挤在一行也认，`XII. THE GREAT EXAMPLE.`）
    """
    want = num = None
    if sec == 'introduction':
        want = _key('Introduction')
    elif sec == 'tail':
        # 书末部分的第一页印的是 `REVISED TRANSLATION / OF THE / ...`，
        # 没有页码，页眉判据看不见它，整页会留在第 30 讲里（实测）。
        want = _key('Revised Translation')
    elif sec and sec.isdigit() and 1 <= int(sec) <= len(LECTURES):
        want, num = _key(LECTURES[int(sec) - 1]), int(sec)
    if want is None:
        return False
    for t in head_candidates(lines, 10):
        m = RE_ROMAN_LINE.match(t)
        if m and num and ROMAN.get(m.group(1).upper().replace('L', 'I')) == num:
            return True
        if len(t) <= 80 and not has_folio(t) \
                and difflib.SequenceMatcher(None, want, _key(t)).ratio() >= 0.72:
            return True
    return False


def assign_leaves(ocr):
    """每一页属于哪一节。

    两道判据，顺序不能反：

    ① **这一页有没有本节的开篇**（正文里的罗马数字 / 讲题行）→ 是就换节。
       讲章不另起新页，开篇页上照样有页眉，所以不能靠「有没有页眉」认。

    ② 否则看**页眉**。单页（recto）页眉印的就是本讲讲题，全书重复几百次，
       错一两页无所谓；双页（verso）页眉印书名，跟当前节走。

    页眉这条冗余是整条链子里最稳的信号 —— 30 篇讲章的标题行 tesseract 只读
    出 12 篇干净的，而页眉有四百多处可以互相纠。
    """
    sec_keys = ([('introduction', _key('Introduction'))]
                + [(str(i + 1), _key(t)) for i, t in enumerate(LECTURES)])
    order = ['front', 'introduction'] + [str(i + 1) for i in range(len(LECTURES))] \
        + ['tail']
    pos = {s: i for i, s in enumerate(order)}

    mark = {}
    for leaf, lines in ocr.items():
        head = pick_head(lines)
        low = head.lower()
        if not has_folio(head):
            mark[leaf] = None
            continue
        if any(h in low or h in head_shape(head) for h in BOOK_HEADS):
            mark[leaf] = None
            continue
        if 'otes on the greek' in low or 'ppendix' in low or 'olycarp' in low \
                or 'evised translation' in low:
            mark[leaf] = 'tail'
            continue
        k = head_shape(head)
        best = max(((difflib.SequenceMatcher(None, k, t).ratio(), s)
                    for s, t in sec_keys), default=(0.0, None))
        mark[leaf] = best[1] if best[0] >= 0.72 else None

    # 书前（扉页/题献/序/目录）整段圈出来。目录那两页把 30 条讲题印得比正文
    # 标题还工整，放进来会让讲章 1 从 leaf 14 起、讲章 24 冒到 leaf 16 去。
    front_end = 0
    for leaf, lines in ocr.items():
        if leaf > 80:
            continue
        for t in head_candidates(lines, 4):
            if len(t) <= 40 and re.fullmatch(
                    r'\W*(?:\S{1,5}\s+)?(?:contents|preface)'
                    r'\s*\W*(?:\S{1,5})?\W*', t, re.I):
                front_end = max(front_end, leaf)

    out, idx = {}, 0
    for leaf in sorted(ocr):
        if leaf <= front_end:
            out[leaf] = 'front'
            continue
        if idx + 1 < len(order) and opens_section(ocr[leaf], order[idx + 1]):
            idx += 1
        else:
            m = mark[leaf]
            if m is not None and pos[m] > idx:     # 只许往前走，不许回头
                idx = pos[m]
        out[leaf] = order[idx]
    return out


def split_tail(paras, keys):
    """书末五节（修订译文 / 希腊文注 I–IV / 波利卡普）按**段落**切。

    这一段没法靠页眉：四章希腊文注共用同一个页眉 `Notes on the Greek Text`，
    章号只在正文里以 `CHAPTER II.` 这样一行单独排。页眉那条路在这里断了，
    只能回到标题行 —— 好在这几行 tesseract 读得干净。
    """
    marks, cursor = [], 0
    for slug, printed, title in TAIL:
        want = _key(printed)
        best, best_i, hit = 0.0, None, None
        for i in range(cursor, len(paras)):
            if len(keys[i]) > 2.2 * len(want) + 20 or has_folio(paras[i]):
                continue
            acc, cands = keys[i], [keys[i]]
            for j in (i + 1, i + 2):      # 起头可能排成连着的两三个短段
                if j >= len(paras) or len(keys[j]) > 46:
                    break
                acc += keys[j]
                cands.append(acc)
            r = max(difflib.SequenceMatcher(None, want, c).ratio() for c in cands)
            # `Chapter II.` 与 `Chapter III.` 的相似度是 0.947——光靠阈值分不开。
            # 真缺了一个（比如 CHAPTER II. 被别的判据吃掉），notes-2 就会匹配到
            # CHAPTER III.、notes-3 匹配到 CHAPTER IV.，notes-4 整节落空（实测）。
            # 所以凡是 `Chapter <罗马数字>` 这种探针，**章号必须一字不差**。
            mw = re.fullmatch(r'chapter([ivx]+)', want)
            if mw:
                mk = re.fullmatch(r'chapter([ivx]+)', keys[i])
                if not mk or mk.group(1) != mw.group(1):
                    continue
                hit = i
                break
            if r >= 0.90:
                hit = i
                break
            if r > best:
                best, best_i = r, i
        i = hit if hit is not None else (best_i if best >= 0.72 else None)
        if i is None:
            print(f'  ⚠️ 书末找不到起头：{slug}（最高 {best:.2f}）', file=sys.stderr)
            continue
        marks.append((i, slug, title))
        cursor = i + 1
    out = []
    for k, (i, slug, title) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(paras)
        out.append((slug, title, '\n\n'.join(paras[i:end])))
    return out


GARBAGE = []


def junk_score(par):
    """这一段里「像词的词」占多少。

    扫描件的空白页、书脊阴影、末尾的出版社书目，OCR 出来是
    `i dt | . v _ " ' . Ἢ φ ΕΝ 4 Ms a` 这样的碎点。判据不猜内容，只量形态：
    长度 ≥3 且纯字母的 token 占全部 token 的比例。正文随便哪一段都在 0.7 以上。
    """
    toks = par.split()
    if not toks:
        return 0.0
    good = sum(1 for t in toks
               if len(t.strip('.,;:!?()[]{}\'"‘’“”—-')) >= 3
               and t.strip('.,;:!?()[]{}\'"‘’“”—-').isalpha())
    return good / len(toks)


# 书本身之外的东西：图书馆藏书票/借书卡、出版社书目广告、装订页编号。
# 这些不是约翰斯通写的，也不是 1875 年那本书的一部分。
NOT_THE_BOOK = re.compile(
    r'WORKS\s+PUBLISHED\s+BY|UNIVERSITY\s+OF\s+TORONTO|PLEASE\s+DO\s+NOT\s+REMOVE'
    r'|Digitized\s+by\s+the\s+Internet\s+Archive|ESTATE\s+OF\s+THE\s+LATE'
    r'|presented\s+to\s+(?:C|t)he\s+Library', re.I)


def trim_edges(paras, slug):
    """只掐**首尾**，而且只掐两类：书外之物，和纯碎点。

    中间一律不动 —— 版式溢出、残页这些 PDF 原文里有的东西不擅自删
    （feedback_preserve_pdf_artifacts）。

    阈值压到 0.35 是有教训的：先用 0.55 时，目录页那些
    `XXVI.—Brotherly-Kindness, . Ξ π΄ -` 被一条条当碎屑掐掉了 —— 目录是书的
    一部分，点线引导符让它「不像词」而已。宁可留一点噪声，不可删掉正文。

    掐掉的每一段都记进 logs/johnstone_merge.tsv，可回查。
    """
    # 碎点清理**只对全书的头尾两个文件**生效。讲章文件的头一段是罗马数字
    # （`I,`、`*V.*`）和全大写讲题，拿「像词的词占比」去量一律是 0 ——
    # 第一版就这样把 11 篇的篇号、第 6 篇的讲题整行掐掉了。
    edges_only = slug in ('preface', 'polycarp')

    def junk(p):
        t = p.strip()
        if not t:
            return True
        if t.startswith(FN_MARK):
            return False
        if NOT_THE_BOOK.search(t):
            return True
        return edges_only and junk_score(t) < 0.35

    lo, hi = 0, len(paras)
    while lo < hi and junk(paras[lo]):
        GARBAGE.append((slug, 'head', paras[lo][:120])); lo += 1
    while hi > lo and junk(paras[hi - 1]):
        GARBAGE.append((slug, 'tail', paras[hi - 1][:120])); hi -= 1

    # 出版社书目广告一旦开始就一直到书尾，整段连同后面全部切掉
    for k in range(lo, hi):
        if re.search(r'WORKS\s+PUBLISHED\s+BY', paras[k], re.I):
            for j in range(k, hi):
                GARBAGE.append((slug, 'ads', paras[j][:120]))
            hi = k
            break
    return paras[lo:hi]


# ── 书前杂页 ─────────────────────────────────────────────────
#
# 扫描件最前面十几页是：藏书票、IA 插页、书名页、书名页背面（图书馆编号 +
# 借书日期戳）、题献页、序、目录。其中两页根本不是「文字页」：
#   leaf 0008 是书名页**背面**，正面的字透过纸背印过来，OCR 拿它当正文读，
#            吐出 `“ἄνω, Ἢ κι ὦ “ a 144 , Ἵ ν he : 7 ᾿ Lae ot…` 这样 241 个
#            字符的纯乱码（裁图确认，见 PROVENANCE.md）
#   leaf 0007 是书名页，花体大字 + 大量字距，OCR 读成
#            `ON THE ΠΟΤΕ TO- THE PHILIPPIANS.` / `mee EPISTLE OF PAUL TO
#            Pris Fite i Pri Ans`
# 这两页不是「修一修就能用」，**照影像重新录入**才对 —— 下面两段是逐字
# 对着 leaf 0007 / 0009 的页图敲的，不是从 OCR 改出来的。
TITLE_PAGE = """LECTURES

EXEGETICAL AND PRACTICAL

ON

THE EPISTLE OF PAUL TO THE PHILIPPIANS

*WITH A REVISED TRANSLATION OF THE EPISTLE*

*AND NOTES ON THE GREEK TEXT*

BY THE

REV. ROBERT JOHNSTONE, LL.B.

GLASGOW

EDINBURGH

WILLIAM OLIPHANT AND CO.

1875"""

DEDICATION = """TO THE

UNITED PRESBYTERIAN CONGREGATION

OF

PARLIAMENTARY ROAD, GLASGOW,

*This Book is Inscribed,*

WITH MUCH AFFECTION,

BY

THEIR FRIEND AND MINISTER,

THE AUTHOR."""


# ⚠️ 段尾噪点**不做自动裁剪**（试过，撤了）。
#
# `…Greek Anthology. eee ee ee Se` 这类段尾残渣确实有十来处，但按「末尾连续
# 的短残片」去掐，会把脚注里的经文出处一起掐掉 —— 实测 49 处裁剪里有
# `Heb. iv. 12.`、`Rom. xii. 10; Eph. v. 21; 1 Pet. v. 5.`、`(Rom. xv. 15, 16).`
# 这些**正文**。书卷缩写与罗马数字天生就是「≤3 个字母、不在词典里」，
# 跟噪点在形态上分不开。
#
# 这十来处留着，交给通读时按影像处理。宁可留噪声，不可删正文
# （feedback_fix_table_makes_errors：修复表自己会制造错误）。

# 导论前面还有一张**半扉页**（leaf 0017），同样是花体大字 + 对页透印，
# OCR 读成 `ON THE eeror` / `LE TO THE PHILIPPIANS.` ——`EPISTLE` 被拆成
# `eeror`（那是透印）和 `LE`。照影像重录。
HALF_TITLE = """LECTURES

ON THE

EPISTLE TO THE PHILIPPIANS."""


def rebuild_intro(paras, log):
    """导论：丢掉糊掉的半扉页，换成重录的那三行。"""
    k = next((i for i, p in enumerate(paras[:6])
              if re.match(r'^\W*INTRODUCTION\b', p.strip('* '), re.I)), None)
    if k is None:
        return paras
    for p in paras[:k]:
        log.append(('introduction', 'half-title', p[:110]))
    return [HALF_TITLE] + paras[k:]


def rebuild_front(paras, log):
    """书前：重录的书名页 + 题献 + 序的正文。目录整段不要。

    目录那两页是双栏带点线引导的表格，OCR 把页码与条目拆得七零八落
    （`INTRODUCTION, 11` / `III.— Prayer for Spiritual Discernment, 1v`
    ——后面那个 `1v` 是罗马数字页码不是节号）。站内书卷首页本身就是目录，
    条目与经文出处都是对的，留着这份残表只会多一堆错。
    """
    # 锚点要「长**且干净**」。只看长度会落到书名页背面那段 241 字的透印乱码
    # 上（`“ἄνω, Ἢ κι ὦ “ a 144 …`），于是整张书名页又被当成正文留下来。
    body = next((i for i, p in enumerate(paras)
                 if len(p) > 200 and junk_score(p) >= 0.6), None)
    end = next((i for i, p in enumerate(paras)
                if re.match(r'^\W*CONTENTS\b', p, re.I)), len(paras))
    if body is None or body >= end:
        return paras
    for p in paras[:body] + paras[end:]:
        log.append(('front', 'front-matter', p[:110]))
    return [TITLE_PAGE, DEDICATION] + paras[body:end]


# 正文中段漏下的页眉。页眉只在页顶出现，但 OCR 常在它上面吐一两行残渣
# （`Ἵ ᾿ VER. 8.] *Summary of Duty.* 381 ον`），把它挤出「头三行」那个窗口，
# 于是整条留在正文里。这里做一次全局兜底：短行 + 带页码 + 跟某个节标题
# 高度相似 = 页眉。正文段落没有这么短，也不会整段长得像节标题。
RE_ROMAN_FOLIO = re.compile(r'(?<![A-Za-z])[ivxlIVXL]{2,7}(?![A-Za-z])')
GREEK_RE = re.compile(r'[Ͱ-Ͽἀ-῿]')


def inner_head_score(par, titles):
    t = re.sub(r'\s+', ' ', par.strip())
    # 书前几页的页码是**罗马数字**（`Vill Preface.` = VIII、`Preface. ix`），
    # 只认阿拉伯数字的话这两条页眉会一直留在序里。
    if len(t) > 86 or not (has_folio(t) or RE_ROMAN_FOLIO.search(t)):
        return 0.0
    k = _key(t)
    if len(k) < 8:
        return 0.0
    return max(difflib.SequenceMatcher(None, k, s).ratio() for s in titles)


# 扫描噪点段：整段没有一个像样的词。**不能只看 junk_score** ——
# 脚注里的经文出处（`1 Tim. v. 17.`、`Ps. xcviii. 8; Isa. lv. 12.`）、
# 全大写的讲题行（`VI. THE SAINT'S LIFE—CHRIST.`）、题记出处
# （`'To me to die is gain.'—PHIL. i. 21, 2nd clause.`）分数一样低，
# 删掉就是删正文。下面三条白名单把它们挡在外面。
RE_CITATION = re.compile(
    r'^[\s\d*\\]*(?:[1-3]\s*)?[A-Z][a-z]{1,4}\.?\s*[ivxlcIVXLC]+\.?\s*[\d,\s.;:–—-]*$')
RE_CAPS_LINE = re.compile(r'^[^a-z]{5,}$')
RE_EPIGRAPH_REF = re.compile(r'PHIL\.|—\s*PHIL', re.I)


RE_PIPE = re.compile(r'\s*\|+\s*')


def strip_pipes(par, log, slug=''):
    """竖线一律去掉。

    **这不是「看着像噪点」，是 kramdown 的语法字符**：一行里出现 `|`
    就被当成表格，整段连同邻段被框进 <table>，页面上看是一个带框的方块
    外加右侧一格孤零零的词（用户截图指出，全书 25 个页面中招）。

    这本书的正文里不存在真正的竖线——印面比对那一遍把它们逐个报成
    `| → 空`（页边划痕、栏线、折痕）。去掉而不是转义：转义只是让噪点
    原样显示出来，一样是错的。
    """
    if '|' not in par:
        return par
    log.append((slug, 'pipe', par[max(0, par.find('|') - 30):par.find('|') + 30]))
    return RE_PIPE.sub(' ', par).strip()


def is_scan_noise(par):
    t = par.strip().strip('*')
    if len(t) < 13 or t.startswith('#'):
        return False
    if junk_score(t) >= 0.3:
        return False
    if RE_CITATION.match(t) or RE_CAPS_LINE.match(t) or RE_EPIGRAPH_REF.search(t):
        return False
    return True


# ── 被碎屑劈开的段落 ────────────────────────────────────────
#
# 页脚的印张标记（`B` `M` `2A`…，装订用的，不是正文）和扫描噪点（`_` `~`
# `χ` `΄`）会**夹在一段话中间自成一段**，把一句话劈成两半：
#     …his light waxing ⟨_⟩ brighter and brighter until…
#     …to which ⟨$s⟩ the poor are exposed…
# 结果页面上一句话断成两段，中间还杵着一个孤零零的符号。
#
# 处理分四档，**没有一档会丢字**：
#   ① 印张标记（\d?[A-Z]）→ 丢掉。它不是正文。
#   ② 不含拉丁字母的碎屑 → 丢掉。
#   ③ 碎屑里有两个以上真词 → 那是正文（`come quickly.’`、`of ὅστις.`），
#      原样并进去。
#   ④ 其余字母碎片（`tru` `p` `we`）→ **保留字母**并进去。宁可留一个怪词，
#      不可凭猜删字母。
# 前一段若已经以句末标点收尾，说明两段本来就该分开，只丢碎屑不合并。
RE_SIGNATURE = re.compile(r'^\W*\d?[A-Z]\.?\W*$')
RE_SENT_END = re.compile(r"[.!?][’'\"”)\]*]*$")
RE_CITE_PAR = re.compile(r"^[\s\d'*\\]*(?:[1-3]\s*)?[A-Z][A-Za-z]{1,9}[.,]")


def mend_split_paragraphs(paras, lex_check, slug, log):
    out = []
    i = 0
    while i < len(paras):
        p = paras[i]
        prev_ok = bool(out) and len(out[-1]) >= 40
        nxt = paras[i + 1] if i + 1 < len(paras) else ''
        if (prev_ok and len(p) <= 15 and len(nxt) >= 40
                and not p.startswith('#')
                and not p.startswith(FN_MARK)
                and not nxt.startswith(FN_MARK)
                and not out[-1].startswith(FN_MARK)
                and not RE_CITE_PAR.match(p)
                # 全大写的短段是**节标题**（`CHAPTER II.`、`APPENDIX.`），
                # 不是碎屑。被当碎屑并掉的话，书末那一节就再也找不到起头
                # ——notes-2 整节因此落空（实测）。
                and not re.fullmatch(r'[^a-z]{3,}', p.strip())
                and not re.match(r'^\W*[IVXL]{1,6}[.,]?\W*$', p)):
            letters = re.sub(r"[^A-Za-z']", ' ', p).split()
            real = [w for w in letters if len(w) > 1 and lex_check(w)]
            if RE_SIGNATURE.match(p) or not letters:
                keep = ''                                   # ①②
            elif len(real) >= 2:
                keep = p                                    # ③
            else:
                keep = ' '.join(letters)                    # ④
            if RE_SENT_END.search(out[-1].rstrip('*')):
                log.append((slug, 'speck', p[:60]))
                if keep:
                    out.append(keep)
                i += 1
                continue
            merged = out[-1] + (' ' + keep if keep else '') + ' ' + nxt
            log.append((slug, 'mend', f'…{out[-1][-34:]} ⟨{p}⟩ {nxt[:34]}…'))
            out[-1] = merged
            i += 2
            continue
        out.append(p)
        i += 1
    return out


LEX_CHECK = None          # main() 填：判一个 token 是不是真词


# ── 跨页续段 ────────────────────────────────────────────────
#
# 一段话写到页底没完、翻页接着写，是书里最常见的情形。我按页出段落、
# 页间直接空行拼接，于是**每一个这样的地方都被切成两段**——全书 307 处，
# 页面上读起来就是一句话从中间断开：
#     …cursory reader cannot fail to observe them. This genuine human
#     （空行）
#     element in the Word of God, appealing as it does to…
#
# ABBYY 本来就给了信号（alexander_abbyy 的文档里写着）：
#     startIndent 首行缩进 → 新段落
#     无 startIndent 且是页内第一段 → 上一页的续行
# 这里两条判据一起用，必须**同时**成立才合并：
#   ① 上一段结尾没有句末标点
#   ② 本页第一段以小写起头（或引号后接小写）
# 只有 ① 会把「段末正好没标点」的真段落错并；只有 ② 会把「新段落碰巧
# 小写起头」错并。两条一起，宁可少并几处。
RE_PARA_END = re.compile(r"[.!?:;][’'\"”)\]*…]*$")
RE_CONT_HEAD = re.compile(r'^\**[‘’\'"“]?[a-z]')


RE_ALLCAPS_ANCHOR = re.compile(r'^[^a-z]{3,}$')


def is_continuation(prev_par, next_par):
    if not prev_par or not next_par:
        return False
    # 全大写短段是**节标题**（`CHAPTER II.`、`APPENDIX.`），任何合并都不许
    # 碰它——并掉的话那一节就再也找不到起头（notes-2 整节落空，实测两次：
    # 一次被碎屑合并吃掉，一次被跨页合并吃掉）。
    if RE_ALLCAPS_ANCHOR.match(next_par.strip()):
        return False
    if prev_par.startswith(FN_MARK) or next_par.startswith(FN_MARK):
        return False
    if len(prev_par) < 40 or len(next_par) < 40:
        return False
    if prev_par.lstrip().startswith('#'):
        return False
    if RE_PARA_END.search(prev_par.rstrip('*\\ ')):
        return False
    return bool(RE_CONT_HEAD.match(next_par))


# ── 脚注 ────────────────────────────────────────────────────
#
# 脚注印在**页脚**，所以按页序读出来就落在该页正文之后；而那段正文往往
# 还要接到下一页去。结果脚注横插在一句话中间，页面上是这样：
#     …most fully used his opportunities of obtaining general as well as
#     biblical knowledge, 1
#     （脚注：According to a precept ascribed by early writers to our Lord…）
#     in whom true Christian wisdom, contemplating all the knowledge…
# 句子被劈开，脚注又混在正文里（用户截图指出）。
#
# 识别靠**整页转录里的 `[FN:n]` 标注**。拿生成式模型出「版面标签」是
# SKILL.md §2.6 明确允许的一档——标签错了看得见，文字错了才看不见；
# 这里只用它判「这一段是不是脚注」，一个字都不从它那边抄。
# 转录目录不在时自动退回原行为，不让链条依赖它。
VLM_DIR = os.path.join(RAW, 'src', 'vlm')
# 脚注段带着这个前缀在流水线里走完全程，最后才摘到本节末尾。
# 一开始是判出来就 `continue` 丢掉的——那不是「挪位置」，是**删正文**，
# 60 条脚注一条都没落盘（提交信息里却写着已移到 .jh-notes）。
FN_MARK = '\x01'
RE_FN_LINE = re.compile(r'^\s*\[FN:(\d+)\]\s*(.+)$')


def load_footnotes():
    out = {}
    if not os.path.isdir(VLM_DIR):
        return out
    for f in os.listdir(VLM_DIR):
        if not f.endswith('.txt'):
            continue
        fns, short, refs, sig = [], [], [], None
        lines = open(os.path.join(VLM_DIR, f), encoding='utf-8').read().split('\n')
        k = next((i for i, l in enumerate(lines) if RE_FN_LINE.match(l)), None)
        # 脚注一旦起头就一直排到页底：**第一条 `[FN:` 之后的全部文字**都是
        # 页脚内容。原书的脚注常跨好几段（引文 + 希腊诗行 + 下接的英文），
        # 证人只给头一行打标签，只认标签就会把后面几段留在正文里，读起来
        # 缺了引子（用户截图 p.102）。这里取的是**边界**，文字仍用自己的。
        foot_pool = Counter(w.lower() for w in
                            re.findall(r"[A-Za-z]{2,}", '\n'.join(lines[k:]))) \
            if k is not None else Counter()
        for line in lines:
            m = RE_FN_LINE.match(line)
            if m and len(m.group(2).strip()) >= 8:
                ws = [w.lower() for w in re.findall(r"[A-Za-z']+", m.group(2))]
                # 四个词以上才够词序列对齐用；短的（`Chrysostom.`、
                # `Acts ii. 24.`）留**字面**，走另一条判据。
                # 号码一路带着走，正文记号与脚注靠它配对。
                (fns if len(ws) >= 4 else short).append(
                    (m.group(1), ws if len(ws) >= 4 else m.group(2).strip()))
                continue
            ms = re.search(r'\[SIG:(\S{1,3}?)\]', line)
            if ms:
                sig = ms.group(1)
            for mk in re.finditer(r'\[FN:(\d+)\]', line):
                ctx = re.findall(r"[A-Za-z']+", line[:mk.start()])[-8:]
                if len(ctx) >= 4:
                    refs.append((mk.group(1), [w.lower() for w in ctx]))
        if fns or short or refs or sig:
            out[int(f[:-4])] = (fns, short, refs, sig, foot_pool)
    return out


GREEK_LOOKALIKE = str.maketrans(
    'ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ', 'ABEZHIKMNOPTYX')


def drop_signature(text, sig, log, sec):
    """抹掉页底的**书帖签名**（`A`、`B`、`C`……）。

    印刷装订用的记号，不是正文。它落在页底，跨页续句一合并就横在句子
    中间：`…would not be` ⟨D⟩ `to hinder the growth of the church.`
    （用户截图）。全书 31 页有，证人标成 `[SIG:x]`——拿的是版面标签，
    删哪个字仍看页底那一小截本身。

    不能拿硬正则去套，尾巴有三种变体，一刀切只认得出一半：
        `…the older English the C` ⟨c⟩   小写
        `…both in the Old Testa- ` ⟨Ζ⟩   希腊字形的 Zeta
        `…result would not be ’` ⟨D⟩     前面还粘着一个假引号
    所以按**归一化后的末尾词**判：大小写不敏感、希腊同形字折回拉丁。
    """
    if not sig:
        return text
    body = text.rstrip()
    m = re.search(r'(\S+)\s*$', body)
    if not m:
        return text
    tok = m.group(1).strip('.,;:')
    if len(tok) > 2 or tok.translate(GREEK_LOOKALIKE).upper() != sig.upper():
        return text
    cut = body[:m.start(1)]
    # 签名那一行自己的噪声（假引号）紧贴着它，一起抹
    cut2 = re.sub(r"[\s‘’\'\"]{1,3}$", '', cut)
    log.append((sec, 'signature', tok + (' +' + cut[len(cut2):].strip()
                                         if cut2 != cut else '')))
    return cut2.rstrip()


def place_fn_refs(text, refs, log, sec, leaf):
    """把脚注号插回**引用处**，位置取自证人的 `[FN:n]` 标注。

    先前是拿「页缝上的裸数字」猜的，猜反了：证人里 `[FN:1]` 标在
    `spiritual traffickers.` 后面，而页末那个 `1` 是脚注**自己的编号**印在
    页脚，于是上标插到了下一句的 `biblical knowledge,` 上（用户截图）。
    标记位置是版面事实，看得见对错；正文一个字仍不从证人那边抄。
    """
    for num, ctx in refs:
        words = [(m.group(0).lower(), m.start(), m.end())
                 for m in RE_WORD_OFF.finditer(text)]
        tw = [w for w, _a, _b in words]
        sm = difflib.SequenceMatcher(None, ctx, tw, autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size]
        if not blocks:
            continue
        cov = sum(b.size for b in blocks) / len(ctx)
        end = blocks[-1].b + blocks[-1].size
        if cov < 0.75 or end > len(words):
            continue
        at = words[end - 1][2]
        while at < len(text) and text[at] in '.,;:!?’\'"”)]*\\':
            at += 1
        # 上标数字本身也被 OCR 读错了，就留在插入点上：
        #   `of the Lord.’!` 的 `!` 是 ¹，`the abyss.’?` 的 `?` 是 ²，
        #   `for His.’\*` 的 `\*` 是 ¹。影像核过（0056 页 `traffickers.¹`）。
        # 记号的权威位置已经由证人给出，这里把读错的那一个字符抹掉。
        # 只抹**绝不会出现在句末的**那几个：`.`、`,`、`’` 一律不动。
        head = text[:at]
        m3 = re.search(r'(?:\\\*|[!?^_|}])$', head)
        if m3:
            head = head[:m3.start()]
            log.append((sec, 'fn-mark-glyph', m3.group(0)))
        # 引号形的误读**不抹**。`traffickers.¹` 影像上确实没有引号，可
        # 同样形态的 `them for His.’¹`（p.143）影像上那个引号是真的——
        # 两边 OCR 都给了 `’`，分不开。我写过一道「本段引号落单就抹」的
        # 自证闸，27 处里就把 p.143 这个真引号删了。证据不够就留着：
        # 宁可留噪声，不可删正文（feedback_preserve_pdf_artifacts）。
        tail = text[at:]
        m4 = re.match(r'[\s]*(?:\\\*|[!?^_|}])(?=[\s]|$)', tail)
        if m4:
            tail = tail[m4.end():]
            log.append((sec, 'fn-mark-glyph', m4.group(0).strip()))
        text = (head + f'<sup class="jh-fn" data-fn="{leaf}-{num}">'
                + num + '</sup>' + tail)
        log.append((sec, 'fn-ref', ' '.join(ctx[-4:]) + ' ⟨' + num + '⟩'))
    return text


RE_WORD_OFF = re.compile(r"[A-Za-z']+")
RE_TAG = re.compile(r'<[^>]+>')


def _plain_words(s, n=2):
    """量词频前先剥 HTML 标签。

    诗块包了 `<span class="jh-verse">`，`span`/`class`/`verse`/`br` 都会
    被当成正文词，「这一段的词是不是全来自页脚」立刻失真——p.102 的
    Animula 四行因此没被收进脚注（体检从 117 退回 116）。
    """
    return [w.lower() for w in re.findall(r'[A-Za-z]{%d,}' % n, RE_TAG.sub(' ', s))]
TWO_LETTER = set('am an as at be by do go he if in is it me my no of on or '
                 'so to up us we ye oh ah lo ox ye'.split())

# 页缝上的裸数字。原书印成上标脚注号（`…biblical knowledge,¹`），OCR 落成
# 正文里一个孤零零的数字——用户问「这里的 1 是干啥的」就是它。
# 同一个位置也会落页码和书帖签名（`B 2`），两者长得一样，只能靠**那一页
# 有没有脚注**分：号码不超过该页脚注条数的才是脚注号，其余是残渣。
RE_FN_REF = re.compile(r"(?<=[a-z’'\"])([,.;:]?)\s+([1-9])(?=\s+[a-z‘“]|\s*$)")


def strip_seam_digits(text, log, sec):
    def sub(m):
        log.append((sec, 'seam-digit', m.group(0).strip()))
        return m.group(1)
    return RE_FN_REF.sub(sub, text)


RE_DUP_REF = re.compile(r'(</sup>)([\s,.;:’\'"]*)([1-9])(?![0-9])'
                        r'(?=[\s,.;:’\'"]|$)')


def _dedup_fn_ref(text, log, sec):
    """上标旁边那个重复的裸数字。

    脚注自己的编号印在页脚，OCR 把它读在页缝上，跟我们按证人插进去的
    上标挨在一起，页面上就出现两个 1（用户截图）：
        `…or a Cicero.`⟦1⟧` 1`
    `strip_seam_digits` 的后瞻只认「后面跟小写拉丁词」，这处后面是希腊文
    另起一段，够不着。插完上标之后再按**紧贴上标**这个位置清一次。
    """
    def sub(m):
        log.append((sec, 'dup-fn-ref', m.group(3)))
        return m.group(1) + m.group(2)
    return RE_DUP_REF.sub(sub, text)


def _one_par(s):
    """切出来的脚注压成**一段**。

    切口可能跨段落分隔（`1\n\nHenry Ward Beecher.`）。带着空行存进去，
    后面按空行重新切段时就裂成两段，前半截带着哨兵、后半截不带——那条
    脚注于是原样留在正文里，体检还报「已摘出」（实测 p.77）。
    """
    return re.sub(r'\s+', ' ', s).strip()


def excise_footnotes(text, fns, short, foot_pool, log, sec):
    """把脚注从这一页的正文里切出来，按**词序列对齐**定位。

    上一版只认「整段就是一条脚注」。可 ABBYY 常把短脚注直接并进正文段里，
    于是句子被从中间劈开，判据一条也看不见：
        …where combined ⟨' See, for example, 1 Thess. v. 23 and Heb. iv. 12.⟩
          action is desired…
    按段落量永远捞不到这种，必须能在段内定位到**一段连续的词**。

    两边 OCR 不一样，所以不按字面比，按词序列求最长公共块（difflib），
    覆盖率六成以上且跨度不比脚注本身长太多才算——跨度那一条是防它把
    零散的公共词连成一大片，把正文一起切走。
    """
    if not fns and not short:
        return text, []
    got = []
    # 一两个词的短脚注（`Chrysostom.`、`Acts ii. 24.`）：词序列对齐在两个
    # 词上不可靠，会在全页找到一堆巧合。改用两条一起卡——
    #   ① 字面模糊匹配（词之间允许 OCR 噪声）
    #   ② 前面必须紧跟**记号残痕**：孤立的数字或误读符号
    # 这两条单用都不够，合起来才认得出 `…as ‘a  1 *Pro Rab.* 5. servant’…`
    # 这种把句子从中间劈开的短脚注。
    for num, lit in short:
        lw = re.findall(r"[A-Za-z']+", lit)
        if not lw:
            continue
        # 两种进场方式：
        #   ① 前面有记号残痕（`…as ‘a  1 *Pro Rab.* 5. servant’…`）
        #   ② 记号在 OCR 里整个丢了，只剩脚注本身横在两句之间
        #      （`…requirements of the passage.  Henry Ward Beecher.  In their…`）
        # ② 单靠字面很容易误伤——`Dr. Eadie` 正文里本来也提到——所以它只在
        # **本页脚注列表里有这条**时才走，页级这层限定就是它的凭据。
        pat = re.compile(r'(?:(?<=\s)[\d!?|^_*\\,;:.‘’\'"\-]{1,4}\s*'
                         r'|(?<=[.!?’\'"]) )\s*'
                         + r'\W{0,6}'.join(re.escape(w) for w in lw)
                         # 引文的数字尾巴（`Acts ii.` 后面的 `24.`）不在词表
                         # 里，不一起吃掉就会留在正文中间。限长 8 个字符，
                         # 免得越过下一条脚注的记号。
                         + r'[\s.,;:)\]’\'"*\\]{0,4}[\s\d.,;:&–-]{0,8}', re.I)
        m = pat.search(text)
        if not m or m.start() == 0:
            continue
        # 切口把**记号**也带进来了，它不是脚注正文的一部分：
        #   `11 Tim. v. 17.` 其实是记号 `1` + 脚注 `1 Tim. v. 17.`
        # 号码是已知的，照它剥；剥不掉就剥掉开头那串非字母数字的残符。
        cut = _one_par(m.group(0))
        if cut.startswith(num):
            cut = cut[len(num):].lstrip()
        else:
            # 星号和反斜杠不能剥：剥掉 `*Pro Rab.* 5.` 的开头那只星号，
            # 这条脚注就只剩一只闭合星号，整篇的斜体奇偶立刻报错。
            cut = re.sub(r"^[^0-9A-Za-z‘“*\\]+", '', cut).lstrip()
        got.append((num, cut))
        log.append((sec, 'footnote-short',
                    '⟨' + lit[:46] + '⟩ ← 切出 ⟨' + m.group(0).strip()[:46] + '⟩'))
        text = (text[:m.start()].rstrip() + ' ' + text[m.end():].lstrip()).strip()
    # 先按**段**搬：页脚那一串短脚注常被 OCR 并成一段
    #   `Literally, ‘endured to go.’ ? Acts ii. 24. 31 Pet. i. & 4 Eph. ii.
    #    8, 9. ©: Pet. i. 13. 6 1 Pet. iii. 9. 7 Matt. vii. 1. 8 These two…`
    # 逐条按词序列切只会把其中一条摘走，剩下的留在正文（p.500 实测）。
    # 判据：这一段的词几乎全来自本页脚注（按重数算，七成五以上）。
    pool = Counter(w for _n, fw in fns for w in fw)
    rest = []
    for par in text.split('\n\n'):
        pwords = _plain_words(par)
        if len(pwords) >= 3:
            have = Counter(pwords)
            cov = sum(min(c, pool.get(w, 0)) for w, c in have.items()) / len(pwords)
            if cov >= 0.75:
                # 这一整段对应哪一条脚注：取覆盖率最高的那条的号码
                best, bn = 0.0, None
                for n, fw in fns:
                    c = sum(min(have.get(w, 0), 1) for w in set(fw)) / len(set(fw))
                    if c > best:
                        best, bn = c, n
                got.append((bn, _one_par(par)))
                log.append((sec, 'footnote', par.strip()[:90]))
                continue
        rest.append(par)
    text = '\n\n'.join(rest)
    for num, fw in fns:
        words = [(m.group(0).lower(), m.start(), m.end())
                 for m in RE_WORD_OFF.finditer(text)]
        if len(words) < 3:
            break
        tw = [w for w, _a, _b in words]
        sm = difflib.SequenceMatcher(None, fw, tw, autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size]
        if not blocks:
            continue
        # **拿最长块当锚，只收锚点附近的块**。直接取首尾块会被页首的
        # `a`/`the`/`to` 这类虚词带偏：首块落在正文开头，跨度一下子涨到
        # 几百词，跨度判据就把真脚注否掉了（p.23 那条 32 词的脚注整段
        # 留在正文里，就是这么丢的）。
        span = len(fw) * 1.6 + 4
        anchor = max(blocks, key=lambda b: b.size).b
        near = [b for b in blocks if abs(b.b - anchor) <= span]
        cov = sum(b.size for b in near) / len(fw)
        lo = min(b.b for b in near)
        hi = max(b.b + b.size for b in near)
        if cov < 0.6 or (hi - lo) > span:
            continue
        a, b = words[lo][1], words[hi - 1][2]
        # 左右各吃掉紧贴的标点与引号；脚注号（`, 1` 里的裸数字）留在正文，
        # 由 publish 转上标 —— 它是**正文里的引用记号**，不是脚注的一部分。
        while b < len(text) and text[b] in '.,;:)]’\'"”*\\ ':
            b += 1
        # 脚注尾巴上的页码/节号（`Heb. iv. 12.` 的 `12.`）：词序列对齐只认
        # 字母，数字落在对齐之外会留在正文里（`where combined ' 12. action`）。
        # 只吃数字和标点，且最多 12 个字符，不许越过下一个词。
        m2 = re.match(r'[\s\d.,;:)\]’\'"”-]{1,12}(?=\s|$)', text[b:])
        if m2:
            b += m2.end()
        while a > 0 and text[a - 1] in '‘\'"“([*\\':
            a -= 1
        got.append((num, _one_par(text[a:b])))
        log.append((sec, 'footnote', text[a:b].strip()[:90]))
        text = (text[:a].rstrip() + ' ' + text[b:].lstrip()).strip()
        text = _wipe_rule(text, a, log, sec)
    # 横线印在**页底**，OCR 常把它读在整页末尾，离切口很远
    # （`…biblical knowledge, 1 Ss *YS Se and*`，实测）。页底位置同样确定，
    # 再从末尾扫一次。只对有脚注的页做——没脚注的页底不该有横线。
    text = _wipe_rule(text, len(text), log, sec)

    # 跨段的脚注：前面按条切走了头一段，后面的续段（希腊诗行、下接的
    # 英文）还留在正文里。从**页末往回**收，词几乎全来自页脚就接到上一条
    # 脚注后面——接而不是另起一条，不然一条脚注会被编成好几个号。
    if foot_pool and got:
        pars = text.split('\n\n')
        tail = []
        while pars:
            # 希腊诗行按拉丁词去量永远对不上（`Τίς οἶδεν…` 在页脚词表里
            # 是希腊字母，OCR 出来的 `Tis`/`tors` 两边都不认）。整段以希腊
            # 文为主的，直接算续段——第一行诗就是这么被挡在外面的。
            greek = len(re.findall(r'[Ͱ-Ͽἀ-῿]', pars[-1]))
            latin = len(re.findall(r'[A-Za-z]', RE_TAG.sub(' ', pars[-1])))
            pw = _plain_words(pars[-1])
            if tail and greek >= 3 and greek >= latin:
                tail.insert(0, pars.pop())
                continue
            if len(pw) < 2:
                # 希腊诗行里一个拉丁词都没有，照收，但只在它上面还有
                # 页脚内容时才算数（下面的 `tail` 非空判据兜住）
                if not tail:
                    break
                tail.insert(0, pars.pop())
                continue
            have = Counter(pw)
            cov = sum(min(c, foot_pool.get(w, 0)) for w, c in have.items()) / len(pw)
            if cov < 0.7:
                break
            tail.insert(0, pars.pop())
        if tail:
            num, head = got[-1]
            got[-1] = (num, head + '<br>'
                       + '<br>'.join(_one_par(t) for t in tail))
            for t in tail:
                log.append((sec, 'footnote-cont', _one_par(t)[:70]))
            text = '\n\n'.join(pars)
    return text, got


def _wipe_rule(text, at, log, sec):
    """抹掉切口上的**脚注横线残渣**（`biblical knowledge, 1 Ss *YS Se and*`）。

    三条收口，每一条都是试出来的：

    ① **只在讲章里做，书末注疏整节跳过。** 希腊文注里 `§ 63. I. 2. 1`、
       `24. 31 & 4` 这类是真引文，长得跟残渣一模一样；我分不出来，就不碰
       （17 处候选里 12 处在那儿，全是误伤）。
    ② **按词删，不按区间删。** 上一版整段切，把 `and` 一起吃了——那是
       下一句的真词，残渣只有 `Ss YS Se`。
    ③ **专名和断词前半截要护。** `Cicero.?`、`com-` 不在词典里，第一版当
       残渣删掉了。但护「首字母大写」会连 `Ss` 一起护住，所以还要求它
       **有元音**——OCR 碎块基本没有。

    改动含 markdown 标记，星号个数必须对得上，否则是修复表自己制造斜体
    断裂（feedback_fix_table_makes_errors）。
    """
    if sec == 'tail' or LEX_CHECK is None:
        return text
    toks = [(m.group(0), m.start(), m.end()) for m in re.finditer(r'\S+', text)]
    if not toks:
        return text

    def real(t):
        w = re.sub(r"[^A-Za-z']", '', t)
        if len(w) < 2:
            return False
        if t.rstrip('*\\').endswith('-'):
            return True
        # 要三个字母以上：`Cicero` 护得住，`Se`/`Ss` 这种 OCR 碎块护不住
        # （只要两个字母时，读烂的页眉 `Ss *YS Se` 整串都被当成专名）。
        if w[0].isupper() and len(w) >= 3 and re.search(r'[aeiouyAEIOUY]', w):
            return True
        # 两个字母的不查词典：`se`、`ss`、`ye` 这类在词表里查得到，于是读烂
        # 的页眉碎块 `Se` 被当真词留在正文里。两字母真词就那么几十个，列死。
        if len(w) <= 2:
            return w.lower() in TWO_LETTER
        return LEX_CHECK(w.lower())

    k = next((i for i, (_t, _a, b) in enumerate(toks) if b > at), len(toks))
    lo = hi = k
    while hi < len(toks) and not real(toks[hi][0]) and hi - k < 8:
        hi += 1
    while lo > 0 and not real(toks[lo - 1][0]) and k - lo < 8:
        lo -= 1
    # 残渣常半截压在斜体区里；把整个区并进来，不然只切一半留下单只星号。
    # **必须有上界**：没上界时它会一路找到下一个星号，把中间整句正文
    # 一起划进待删区间（`*| the carth ; and that every tongue should…`，
    # 实测删掉了一整句）。最多再吃三个词，吃不平就整次放弃。
    grow = 0
    while (hi < len(toks) and grow < 3
           and len(re.findall(r'(?<!\\)\*',
                              text[toks[lo][1]:toks[hi - 1][2]])) % 2):
        hi += 1
        grow += 1
    if hi - lo < 2:
        return text
    la, hb = toks[lo][1], toks[hi - 1][2]
    run = text[la:hb]
    if len(re.findall(r'(?<!\\)\*', run)) % 2:
        return text
    noise = [t for t, _a, _b in toks[lo:hi] if not real(t)
             and not re.fullmatch(r"[\d.,;:'’]+", t)]
    if len(noise) < 2:
        return text
    kept = ' '.join(t.replace('*', '') for t, _a, _b in toks[lo:hi]
                    if t not in noise)
    log.append((sec, 'fn-rule', run[:70] + ' → ' + kept[:30]))
    return (text[:la].rstrip() + (' ' + kept if kept else '')
            + ' ' + text[hb:].lstrip()).strip()


def looks_like_footnote(par, fns):
    """这一段是不是该页的某条脚注。

    按**词集合重合度**判，不按字面——两边的 OCR 不一样。
    脚注一侧的实词有六成以上出现在这一段里，且两边长度相仿，就算。
    """
    # 太短的不碰：书末几节的切分锚点就是 `CHAPTER IV.` 这样的短行，
    # 词集合重合度很容易把它判成脚注，整节会因此找不到起头（实测 notes-4）。
    if len(par.strip()) < 40:
        return False
    pw = set(w.lower() for w in re.findall(r"[A-Za-z']{3,}", par))
    if not pw:
        return False
    for fw in fns:
        if not fw:
            continue
        hit = len(fw & pw) / len(fw)
        if hit >= 0.6 and len(pw) <= len(fw) * 2.5 + 6:
            return True
    return False


def split_sections(pages, leaf_sec):
    """[(leaf, markdown)] → [(slug, 标题, 正文)]"""
    titles = dict([('front', 'Preface'), ('introduction', 'Introduction')]
                  + [(str(i + 1), t) for i, t in enumerate(LECTURES)])
    footnotes = load_footnotes()
    buckets, order = {}, []
    for leaf, text, cont in pages:
        sec = leaf_sec.get(leaf, 'front')
        if sec not in buckets:
            buckets[sec] = []
            order.append(sec)
        # 页眉读烂了就粘在页顶，`learn_heads` 的页眉形认不出来，还会把
        # 下一句的首词一起裹进去（`Ss *YS Se and*` —— `and` 是正文）。
        # 只对**续页**做：讲章起头那页的页顶是篇号和全大写讲题，按
        # 「像不像词」去量一律是 0，会被整行掐掉（trim_edges 栽过这个跟头）。
        if cont:
            text = _wipe_rule(text, 0, GARBAGE, sec)
        if leaf in footnotes:
            fns, short, refs, sig, foot_pool = footnotes[leaf]
            text = drop_signature(text, sig, GARBAGE, sec)
            text, got = excise_footnotes(text, fns, short, foot_pool,
                                         GARBAGE, sec)
            for num, g in got:
                buckets[sec].append(f'{FN_MARK}{leaf}-{num}\x1f{g}')
            # 页缝上的裸数字全是残渣：脚注自己的编号印在页脚，页码和书帖
            # 签名也落在同一位置。真正的引用记号由证人的标注定位。
            text = strip_seam_digits(text, GARBAGE, sec)
            text = place_fn_refs(text, refs, GARBAGE, sec, leaf)
            text = _dedup_fn_ref(text, GARBAGE, sec)
        first = True
        for p in text.split('\n\n'):
            if not p.strip():
                continue
            # 页内第一段若是上一页的续行，接回去，不另起一段。
            # 不接的话全书 307 处段落被从句子中间切开（用户截图指出）。
            # startIndent 当主判据（全书 418 页里 399 页是续行），
            # 文本判据当**否决权**：上一段已经以句末标点收尾、且这一段大写
            # 起头，那就是新段落，ABBYY 漏了缩进也不并。
            # 要接回去的是最后一段**正文**，不是最后一段。脚注印在页脚、
            # 按页序排在该页正文之后，可那页的正文还要接到下一页去——
            # 拿 buckets[-1] 当落点，跨页的那半句就会卡在脚注后面接不上
            # （`…biblical knowledge, 1` 后面永远少半句，实测）。
            tgt = next((k for k in range(len(buckets[sec]) - 1, -1, -1)
                        if not buckets[sec][k].startswith(FN_MARK)), None)
            merge = (is_continuation(buckets[sec][tgt], p.strip())
                     if tgt is not None else False)
            if (first and cont and tgt is not None and not merge
                    and not RE_ALLCAPS_ANCHOR.match(p.strip())
                    and not p.startswith(FN_MARK)):
                prev = buckets[sec][tgt]
                if not (RE_PARA_END.search(prev.rstrip('*\\ '))
                        and re.match(r'^\**[‘’\'"“]?[A-Z]', p.strip())):
                    merge = True
            if first and tgt is not None and merge:
                GARBAGE.append((sec, 'merge-page',
                                buckets[sec][tgt][-46:] + ' ⟂ ' + p.strip()[:46]))
                buckets[sec][tgt] = buckets[sec][tgt].rstrip() + ' ' + p.strip()
                first = False
                continue
            # 脚注抽出正文流，攒到本节末尾。抽走之后上下两段才接得上。
            first = False
            buckets[sec].append(p)

    head_titles = [_key(t) for t in (
        ['Introduction', 'Lectures on Philippians', 'Contents', 'Preface',
         'The Epistle to the Philippians', 'Notes on the Greek Text',
         'Appendix', 'Epistle of Polycarp', 'Revised Translation of the Epistle']
        + LECTURES)]
    out = []
    for sec in order:
        paras = buckets[sec]
        if sec == 'front':
            paras = rebuild_front(paras, GARBAGE)
        if sec == 'introduction':
            paras = rebuild_intro(paras, GARBAGE)
        if sec == 'tail':
            for slug, title, body in split_tail(
                    paras, [_key(p.strip().strip('*')) for p in paras]):
                out.append((slug, title,
                            '\n\n'.join(trim_edges(body.split('\n\n'), slug))))
        else:
            slug = 'preface' if sec == 'front' else sec
            out.append((slug, titles.get(sec, sec),
                        '\n\n'.join(trim_edges(paras, slug))))

    # 兜底清扫放在**分节之后**：书末那几节的标题页本身就长得像页眉
    # （`EPISTLE OF PAUL TO THE PHILIPPIANS. _ LS) 3» 4`，相似度 0.81），
    # 分节前扫会把切分锚点一起扫掉——实测「修订译文」整节因此找不到起头。
    swept = []
    for slug, title, body in out:
        keep = []
        for p in body.split('\n\n'):
            if not p.strip():
                continue
            if p.startswith(FN_MARK):
                keep.append(FN_MARK + strip_pipes(p[1:], GARBAGE, slug)); continue
            if inner_head_score(p, head_titles) >= 0.65:
                GARBAGE.append((slug, 'inner-head', p[:110])); continue
            if is_scan_noise(p):
                GARBAGE.append((slug, 'scan-noise', p[:110])); continue
            keep.append(strip_pipes(p, GARBAGE, slug))
        keep = mend_split_paragraphs(keep, LEX_CHECK, slug, GARBAGE)
        # 页**内**也会被切开：ABBYY 把引号起头当成新段，残留页眉夹在段中
        # 把一段劈成两段。同一条判据（上段无句末标点 + 下段小写起头）全局
        # 再扫一遍，把它们接回去。
        merged = []
        for p in keep:
            t = next((k for k in range(len(merged) - 1, -1, -1)
                      if not merged[k].startswith(FN_MARK)), None)
            if t is not None and is_continuation(merged[t], p.strip()):
                GARBAGE.append((slug, 'merge-inner',
                                merged[t][-40:] + ' ⟂ ' + p.strip()[:40]))
                merged[t] = merged[t].rstrip() + ' ' + p.strip()
            else:
                merged.append(p)
        keep = merged
        body = [x for x in keep if not x.startswith(FN_MARK)]
        notes = []
        for x in keep:
            if x.startswith(FN_MARK):
                k, _, t = x[1:].partition('\x1f')
                notes.append((k, t.strip()))
        if notes:
            body.append(_render_notes(body, notes))
        swept.append((slug, title, '\n\n'.join(body)))
    return swept


RE_SUP_KEY = re.compile(r'<sup class="jh-fn" data-fn="([^"]+)">\d+</sup>')
RE_DROPCAP = re.compile(r'(?<![A-Za-z])([A-Z]{2,5})(?= [a-z])')


def mend_dropcaps(md, pars, log):
    """下沉首字被 tesseract 吞掉，从 ABBYY 补——**按页**补，不按段首补。

    `johnstone_common.restore_dropcap` 只看每段开头。可 ABBYY 常把题记和
    正文并成一段（讲章开篇那页就是），下沉首字于是落在段中间，判据够不着：
        产物  `…—PHIL. i. 3-8.` ⟦HIS⟧ first paragraph, or, more exactly…
        ABBYY `…—PHIL. i. 3-8.` ⟦THIS⟧ first paragraph^ or, more exactly…
    对位要**按词**，不能按字面：同一处两边的标点常常不一样（这例里 ABBYY
    把逗号读成了 `^`），字面 find 一次都对不上。

    只在 ABBYY 的写法**以 OCR 这串结尾且更长**时才补（`THIS` 以 `HIS`
    结尾）——补回去的永远只是开头掉的那几个字母，不改词。
    """
    ab = ' '.join(J.strip_sentinels(p['text'])[0] for p in pars)
    aw = [(m.group(0), m.start()) for m in re.finditer(r'\S+', ab)]
    alow = [w.lower().strip('.,;:^’\'"*\\()[]') for w, _ in aw]
    out, last = [], 0
    for m in RE_DROPCAP.finditer(md):
        cap = m.group(1)
        nxt = re.findall(r"[A-Za-z']+", md[m.end():m.end() + 70])[:5]
        if len(nxt) < 4:
            continue
        nxt = [w.lower() for w in nxt]
        sm = difflib.SequenceMatcher(None, nxt, alow, autojunk=False)
        blk = sm.find_longest_match(0, len(nxt), 0, len(alow))
        if blk.size < 3 or blk.a != 0 or blk.b == 0:
            continue
        prev = aw[blk.b - 1][0].strip('.,;:^’\'"*\\()[]')
        if prev == cap or not prev.endswith(cap) or not prev.isupper():
            continue
        out.append(md[last:m.start()] + prev)
        last = m.end()
        log.append((cap, prev))
    md = ''.join(out) + md[last:] if out else md

    # 第二种败法：下沉首字没被吞掉，而是**糊成一团乱码**
    #   ABBYY `WITH the free discursiveness of a familiar letter…`
    #   产物  `Ἶ Ww" H the free discursiveness of a familiar letter…`
    # 上面那条判据要求开头是干净的全大写词，认不出这种。这里改从段首的
    # 小写词往回找：拿后面四个小写词去 ABBYY 对位置，取它前面那个全大写
    # 词，换掉段首那一小截乱码。只换 ≤16 个字符的一小截，换不准就不换。
    pars_out = []
    for par in md.split('\n\n'):
        m = re.match(r'^(.{1,16}?)((?:[a-z’\']+\s+){4})', par)
        # 「段首这一小截是不是乱码」要按**乱码字符**判，不能按「有标点」判：
        # 第一版拿 `[^A-Za-z\s]` 当判据，把正常的 `The mss.` 也当乱码，
        # 换成了 ABBYY 的 `MSS`，`The` 就这么没了。
        if m and re.search(r'[^\x00-\x7f|"^~_*\\]|[|"^~_*\\]', m.group(1)):
            nxt = [w.lower() for w in re.findall(r"[A-Za-z']+", m.group(2))][:4]
            sm = difflib.SequenceMatcher(None, nxt, alow, autojunk=False)
            blk = sm.find_longest_match(0, len(nxt), 0, len(alow))
            if blk.size >= 3 and blk.a == 0 and blk.b > 0:
                prev = aw[blk.b - 1][0].strip('.,;:^’\'"*\\()[]')
                if prev.isupper() and 2 <= len(prev) <= 8 and prev.isalpha():
                    log.append((m.group(1).strip(), prev))
                    par = prev + ' ' + par[m.end(1):].lstrip()
        pars_out.append(par)
    return '\n\n'.join(pars_out)


def _render_notes(body, notes):
    """脚注编号 + 正文记号与脚注互相跳转。

    原书每页从 1 起编，一篇讲章横跨十几页，号码会重复好几轮；网页上一篇
    就是一页，所以**按篇重编**。配对不能靠出现次序——有的记号在 OCR 里
    整个丢了，次序一错后面全错——靠的是 `{页}-{页内号}` 这把键。
    正文里没找到记号的脚注仍然排进来，接在后面，只是没有回跳箭头。
    """
    have = {k for k, _t in notes}
    seq, n = {}, 0
    for p in body:
        for m in RE_SUP_KEY.finditer(p):
            if m.group(1) in have and m.group(1) not in seq:
                n += 1
                seq[m.group(1)] = n
    for k, _t in notes:
        if k not in seq:
            n += 1
            seq[k] = n

    def renum(p):
        return RE_SUP_KEY.sub(
            lambda m: (f'<sup class="jh-fn" id="fnref-{seq[m.group(1)]}">'
                       f'<a href="#fn-{seq[m.group(1)]}">{seq[m.group(1)]}</a>'
                       f'</sup>') if m.group(1) in seq else m.group(0), p)

    for i, p in enumerate(body):
        body[i] = renum(p)
    rows = []
    for k, t in sorted(notes, key=lambda kt: seq[kt[0]]):
        num = seq[k]
        back = (f'<a class="jh-back" href="#fnref-{num}">{num}</a>'
                if any(f'id="fnref-{num}"' in p for p in body)
                else f'<span class="jh-back">{num}</span>')
        # 号码与正文之间**不留空格**：这一段是两端对齐的，空格会被拉开，
        # 号码跟正文之间裂出老远（用户截图）。间距交给 CSS 的 margin。
        rows.append(f'<p class="jh-note" id="fn-{num}" markdown="span">'
                    f'{back}{t}</p>')
    return '<div class="jh-notes">\n' + '\n'.join(rows) + '\n</div>'


def verse_pars(xml_path):
    """按 ABBYY 的**行坐标**标出哪些段是诗，顺带记下每段的行。

    原书把引用的诗排成缩进的一行一句（用户截图 p.102 的 Animula 四行）。
    我们按段出文字，四行并成一段流水句子，诗的样子就没了。ABBYY 给了行
    的左边界，判据一眼可见：正文行 l≈164，诗行 l≈571…710。拿整页正文行的
    **众数左边界**当基线，缩进超过页宽 12% 的算诗行；不拿固定像素，页与
    页的版心会差几格。

    **按段标，不在文字里找位置**。先前两版都是拿 ABBYY 的行文本去我们的
    文字里模糊定位，可 ABBYY 那份 OCR 更糊（`Animula vagula` 它读成
    `Animiila vagiila`），一个词都对不上，整块就丢了。而段落本来就是
    一一对应的——`transfer_page` 已经按段切好了——顺着这层对应走，
    一次模糊匹配都不用做。
    """
    out = {}
    ctx = ET.iterparse(xml_path, events=('end',))
    idx = -1
    for _, el in ctx:
        if el.tag != A.NS + 'page':
            continue
        idx += 1
        width = int(el.get('width') or 0)
        pars, lefts = [], []
        for blk in el.iter(A.NS + 'block'):
            if blk.get('blockType') != 'Text':
                continue
            for par in blk.iter(A.NS + 'par'):
                lines = list(par.iter(A.NS + 'line'))
                if not lines:
                    continue
                pars.append([(int(l.get('l') or 0), A._line_text(l))
                             for l in lines])
                lefts += [int(l.get('l') or 0) for l in lines]
        el.clear()
        if not lefts or not width:
            continue
        base = collections.Counter(lefts).most_common(1)[0][0]
        cut = base + width * 0.12
        flags = []
        for lines in pars:
            # 只数**够长的行**。脚注的首行也是缩进的，不加这条就会把
            # `Compare Heb. iii. 1.` 连同页底那个书帖签名 `T` 一起当成
            # 两行诗（实测 p.307）。诗是整句整句排的，行不会只有一两个字。
            real = [(l, t) for l, t in lines if len(t.strip()) > 8]
            ind = sum(1 for l, _t in real if l > cut)
            body_n = len([1 for _l2, t2 in lines if len(t2.strip()) > 2])
            ok = (len(real) >= 2 and len(real) == body_n
                  and ind >= len(real) * 0.8)
            flags.append([t for _l, t in real] if ok else None)
        if any(flags):
            out[idx] = flags
    return out


RE_STAR_QUOTE = re.compile(r'(^|\n\n)\\\*(\s+)(?=[A-Z])')


def mend_open_quote(md, log, sec):
    """段首那只落单的星号其实是**开引号**。

    ABBYY 把 `‘` 读成了 `*`（影像 leaf 0127 `‘ Only let your conversation…`
    核过），落盘时又转义成 `\\*` 免得被当斜体，页面上就显示成一个星号
    （用户截图）。只改段首这一处，且要求**本段里有闭引号**——没有配对
    就说不准，宁可留着。
    """
    out, last = [], 0
    for m in RE_STAR_QUOTE.finditer(md):
        end = md.find('\n\n', m.end())
        par = md[m.end():end if end > 0 else len(md)]
        if '’' not in par and "'" not in par:
            continue
        out.append(md[last:m.start()] + m.group(1) + '‘' + m.group(2))
        last = m.end()
        log.append((sec, 'star-open-quote', par[:46]))
    return ''.join(out) + md[last:] if out else md


# 白名单体检捞出来的全部游离符号。黑名单判据天生看不见单个游离符号，
# 必须反过来列**允许出现的字符**、其余一律报——两轮各捞出一批。
# `§` 不收：`Winer, *Gram.* § 20. 2` 里它是真的节号。
STRAY = '—–¢©»®°£¥«¶†‡µſ~=>+{}|^_`@#$%¥·•'
RE_STRAY = re.compile(r'(?<=\s)[' + STRAY + r']+(?=\s)')


def drop_stray(md, wit, log, sec):
    """独立成词的噪点与破折号，**按位置向证人取证**后才删。

    `confident, © and restful`、`Him,—how — impressive`（用户两次截图）
    都是扫描噪点被读成了字符。语料自证只能说明它可疑——全书紧贴前词的
    破折号 1737 个、两侧带空格的 182 个（9.5%），比例低不等于每一个都错。

    所以逐个取证：拿前后各四个词去证人那份转录里定位，证人在**同一位置**
    没有这个符号才删。定不了位就留着——证据不够不动手。

    `§` 不在清理之列：`Winer, *Gram.* § 20. 2` 里它是真的节号。
    """
    if not wit:
        return md
    ww = [w.lower() for w in re.findall(r"[A-Za-z]{2,}", wit)]
    out, last = [], 0
    for m in RE_STRAY.finditer(md):
        pre = [w.lower() for w in re.findall(r"[A-Za-z]{2,}", md[:m.start()])][-4:]
        post = [w.lower() for w in re.findall(r"[A-Za-z]{2,}", md[m.end():])][:4]
        if len(pre) < 3 or len(post) < 3:
            continue
        seq = pre + post
        sm = difflib.SequenceMatcher(None, seq, ww, autojunk=False)
        blk = sm.find_longest_match(0, len(seq), 0, len(ww))
        if blk.size < len(seq) - 1 or blk.a != 0:
            continue
        # 证人里这两个词之间有没有同样的符号
        a = blk.b + len(pre)
        gap = _wit_gap(wit, ww, blk.b, len(pre))
        if any(c in gap for c in STRAY):
            continue
        out.append(md[last:m.start()].rstrip() + ' ')
        last = m.end() + 1
        log.append((sec, 'stray', m.group(0) + ' ⟨' + ' '.join(pre[-2:])
                    + ' ⟂ ' + ' '.join(post[:2]) + '⟩'))
    return ''.join(out) + md[last:] if out else md


def _wit_gap(wit, ww, b, npre):
    """证人文本里第 b+npre-1 个词与第 b+npre 个词之间的那一小截。"""
    offs = [(m.start(), m.end()) for m in re.finditer(r"[A-Za-z]{2,}", wit)]
    i = b + npre
    if i <= 0 or i >= len(offs):
        return ''
    return wit[offs[i - 1][1]:offs[i][0]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0, help='只处理前 N 页（试水）')
    ap.add_argument('--dump-page', type=int, default=0, help='只打一页，调判据用')
    a = ap.parse_args()

    xml = load_xml()
    ab = A.parse_pages(xml)
    ocr = ocr_pages()
    if not ocr:
        sys.exit('没有 OCR 产物，先跑 scripts/johnstone_ocr.py')
    print(f'ABBYY {len(ab)} 页 / OCR {len(ocr)} 页', file=sys.stderr)

    if len(ab) != len(ocr):
        print(f'⚠️ 页数不等（ABBYY {len(ab)} vs OCR {len(ocr)}）—— '
              f'按序号对会整体错位，先把差额查清楚', file=sys.stderr)

    global SECTION_TITLES
    SECTION_TITLES = [_key(t) for t in (
        ['Introduction'] + LECTURES + [t for _, _p, t in TAIL]
        + ['Lectures on Philippians', 'The Epistle to the Philippians',
           'Contents', 'Preface', 'Appendix'])]
    for leaf in drop_duplicate_leaves(ocr):
        del ocr[leaf]
    global LEX_CHECK
    try:
        from alexander_lexicon import build as _build, is_word as _isw
        _lex = _build()
        LEX_CHECK = lambda w: _isw(w, _lex)
    except Exception:
        LEX_CHECK = lambda w: len(w) > 3
    global WITNESS
    WITNESS = {}
    if os.path.isdir(VLM_DIR):
        for _f in os.listdir(VLM_DIR):
            if _f.endswith('.txt'):
                WITNESS[int(_f[:-4])] = open(
                    os.path.join(VLM_DIR, _f), encoding='utf-8').read()
    global VERSE
    VERSE = verse_pars(load_xml())
    print(f'诗段（按 ABBYY 行坐标）'
          f'{sum(sum(1 for x in v if x) for v in VERSE.values())} 段',
          file=sys.stderr)
    first, shapes = learn_heads(ocr)
    print(f'页眉形 {len(shapes)} 种（语料自证，≥3 次）', file=sys.stderr)

    leaves = sorted(ocr)
    pages = []
    for n, leaf in enumerate(leaves):
        if a.limit and n >= a.limit:
            break
        # **按 leaf 号取 ABBYY 页，不按在列表里的位序**。
        # 重拍页被丢掉之后位序就跟 leaf 号错开了，用位序会让后面 270 页的
        # 版面与斜体整体漂移两页（实测斜体丢弃从 59 处暴涨到 607 处）。
        if leaf >= len(ab):
            break
        txt, cont = page_text(ab[leaf]['pars'], ocr[leaf],
                              first.get(leaf, ''), shapes,
                              VERSE.get(leaf))
        txt = mend_dropcaps(txt, ab[leaf]['pars'], DROPCAPS)
        txt = mend_open_quote(txt, GARBAGE, '')
        txt = drop_stray(txt, WITNESS.get(leaf, ''), GARBAGE, str(leaf))
        if a.dump_page and leaf == a.dump_page:
            print(txt)
            return
        pages.append((leaf, txt, cont))

    os.makedirs(OUT_DIR, exist_ok=True)
    sections = split_sections(pages, assign_leaves(ocr))

    # 行末断词的裁决放在**全书拼完之后**：复合词表要拿整本书的行内写法当凭据，
    # 一页一页做的时候还看不全。
    compounds = J.learn_compounds(b for _, _, b in sections)
    seams = []
    sections = [(s, t, J.resolve_hyphens(b, compounds, seams))
                for s, t, b in sections]
    kept = sum(1 for _, _, k in seams if k)
    print(f'行末断词 {len(seams)} 处：拼合 {len(seams) - kept}，'
          f'保留连字符 {kept}（复合词表 {len(compounds)} 条）', file=sys.stderr)
    for slug, title, body in sections:
        with open(os.path.join(OUT_DIR, slug + '.md'), 'w', encoding='utf-8') as f:
            f.write('# ' + title + '\n\n' + body + '\n')
    log = os.path.join(ROOT, 'logs', 'johnstone_merge.tsv')
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, 'w', encoding='utf-8') as f:
        f.write('kind\tfrom\tto\n')
        for was, now in DROPCAPS:
            f.write(f'dropcap\t{was}\t{now}\n')
        for run in DROPPED_ITALIC:
            f.write(f'italic-dropped\t{run}\t\n')
        for was, now, keep in seams:
            f.write(f'seam-{"keep" if keep else "join"}\t{was}\t{now}\n')
        for slug, where, txt in GARBAGE:
            f.write(f'drop/{where}\t{slug}\t{txt}\n')
    print(f'下沉首字补回 {len(DROPCAPS)} 处，斜体区间对不上丢弃 '
          f'{len(DROPPED_ITALIC)} 处 → {log}', file=sys.stderr)
    print(f'{len(sections)} 节 → {OUT_DIR}', file=sys.stderr)
    for slug, title, body in sections:
        print(f'  {slug:14s} {len(body):7d}  {title[:46]}', file=sys.stderr)


if __name__ == '__main__':
    main()
