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
import collections
import difflib
import gzip
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
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
DROPPED_ITALIC = []


def page_text(pars, lines, first_line, shapes):
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

    keep, dropped_head = [], False
    for p in pars:
        plain = J.strip_sentinels(p)[0].strip()
        if not dropped_head and plain:
            dropped_head = True
            head0 = plain.split('\n')[0]
            if is_head(head0) or (has_folio(head0) and head_shape(plain) in shapes):
                continue
        keep.append(p)
    if not keep or not ocr.strip():
        return ''
    return J.transfer_page(keep, ocr, DROPPED_ITALIC, DROPCAPS)


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
            if r >= 0.90:          # 够准就取**最早**的 —— CHAPTER II./III./IV.
                hit = i            # 彼此相似度 0.94，取「最像」会切错章
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


def is_scan_noise(par):
    t = par.strip().strip('*')
    if len(t) < 13 or t.startswith('#'):
        return False
    if junk_score(t) >= 0.3:
        return False
    if RE_CITATION.match(t) or RE_CAPS_LINE.match(t) or RE_EPIGRAPH_REF.search(t):
        return False
    return True


def split_sections(pages, leaf_sec):
    """[(leaf, markdown)] → [(slug, 标题, 正文)]"""
    titles = dict([('front', 'Preface'), ('introduction', 'Introduction')]
                  + [(str(i + 1), t) for i, t in enumerate(LECTURES)])
    buckets, order = {}, []
    for leaf, text in pages:
        sec = leaf_sec.get(leaf, 'front')
        if sec not in buckets:
            buckets[sec] = []
            order.append(sec)
        for p in text.split('\n\n'):
            if p.strip():
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
            if inner_head_score(p, head_titles) >= 0.65:
                GARBAGE.append((slug, 'inner-head', p[:110])); continue
            if is_scan_noise(p):
                GARBAGE.append((slug, 'scan-noise', p[:110])); continue
            keep.append(p)
        swept.append((slug, title, '\n\n'.join(keep)))
    return swept


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
        txt = page_text([p['text'] for p in ab[leaf]['pars']], ocr[leaf],
                        first.get(leaf, ''), shapes)
        if a.dump_page and leaf == a.dump_page:
            print(txt)
            return
        pages.append((leaf, txt))

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
