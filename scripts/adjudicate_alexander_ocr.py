#!/usr/bin/env python3
"""第二证人判读：拿 1850 年三卷本给 1864 单卷本的残留可疑 token 定案。

`repair_alexander_ocr.py` 那三道闸（字形规则 / 判词典 / 语料自证）跑完，
账上还剩两千多个「存疑未动」。它们过不去的原因只有一个——**证据不足**：
规则造不出落进词典的候选，或者造出好几个而无从取舍。再怎么调规则也没用，
缺的不是规则而是**另一份原文**。

第三道闸原来是「候选必须在本书别处正确出现过」，这只是**词频**证据，说明
这个词书里有，不说明**这一处**就是它（feedback_ocr_adjudication_backfill：
按串找会改错位置）。这里把它换成**位置证据**：

    用可疑词前后的干净词做锚，在证人语料里找到同一段话，
    读出证人在**同一个位置**上印的是什么。

1850 三卷本是同一作者同一部书的早出版本，两版之间有修订，所以证人读数
**不能照单全收**，还要过两道：

  字形闸  证人读数必须和 OCR 串「长得像」（编辑距离占比 ≤ 1/3）。
          挡住的是两版之间真正的**改写**——1864 把某句重写了，证人给出
          一个完全不同的词，照抄就等于拿旧版覆盖新版，属于篡改底本。
  判词闸  证人读数本身得是真词，或在证人语料里出现 ≥3 次（放行 Adhonai、
          Sirion 这类专名与希伯来文音译——它们不在韦氏词表里，但反复出现，
          说明是书里确实有的写法，不是 OCR 噪点）。

两版读数一致的，记 `confirm`：这个 token 从「存疑」转成「已核实原样」，
以后不必再挖（project_calvin_en_footnote_audit 那种反复挖同一批残留的坑）。

用法：
    python3 scripts/adjudicate_alexander_ocr.py            # 只出报告，不改文件
    python3 scripts/adjudicate_alexander_ocr.py --apply    # 落盘
"""
import argparse
import pickle
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import alexander_lexicon
from alexander_lexicon import build, is_word
from repair_alexander_ocr import _apply_once as glyph_step

ROOT = Path(__file__).resolve().parent.parent
# 判读对象是**已发布的**那份，不是 alexander_raw/psalms/en_chapters/。
# 那个目录是 extract 的落点，任何一次重跑 extract 都会把它冲回未修复状态
# （2026-09-10 就被并行的另一条 isaiah 改造冲掉过一次）；已发布这份进了 git，
# 是站点实际服务的文本，也是唯一有历史可回溯的一份。
SRC = ROOT / 'alexander/psalms'
WITNESS = [ROOT / f'alexander_raw/psalms/src/pages{v}.pkl' for v in ('01', '02', '03')]
LOG = ROOT / 'logs/alexander_adjudicate.tsv'

TOKEN = re.compile(r"[A-Za-z][A-Za-z'’]*")

# 标签正则**不能**写成 `<[^>]+>`。正文里有 OCR 读出来的孤立 `<`（希伯来活字
# 残渣，诗篇 29 处），宽松写法会从那个 `<` 一路吃到几百词之后的下一个 `>`，
# 中间整段正文被当成标签跳过——判读器对它视而不见，而且毫无症状。
# 实测这一条曾让 2615 个 token 静默漏判。要求 `<` 后面紧跟字母且不再含尖括号。
TAG = re.compile(r'<!--.*?-->|</?[A-Za-z][^<>]*>')

# 锚的长度。3 个词在 35 万词的语料里已经足够罕见，短到 2 个就会撞上
# "of the" 这种到处都是的组合，读出来的是别处的字。
ANCHOR = 3

# 锚在目标词前后各多远的范围里滑动找。给到 6 是因为这本书的错常常连着两三个，
# 太窄了照样落在坏词上。
WINDOW = 6

# 锚命中超过这个数就当它太常见，读不准（"of the same" 在 35 万词里几十处）。
MAX_HITS = 8

# 证人读数与 OCR 串的最大编辑距离占比。超过这个就当成两版之间的改写，不采信。
MAX_DIST_RATIO = 1 / 3

# 序列相似度下限，见 verdict 里字形闸那一段。
SIM_FLOOR = 0.55

# 一个词被劈成两个 token 时，中间可能夹着的东西：一两个非字母数字的字符
# ——空格、残留的行末连字符，或 OCR 读出来的噪点（`af&rmation`、`hj^othesis`、
# `endu/reth`、`prept)sition`、`ac.ually`）。
SPLIT_SEP = re.compile(r'^[^0-9A-Za-z]{1,2}$')

# 拼词的相似度下限。比一般的 0.6 高：拼接本身已经是很强的假设，
# 再放宽就会把两个不相干的词硬凑在一起。
JOIN_SIM = 0.75

# 正字法闸。1864 是伦敦排的英式本，1850 是费城排的美式本，两版在
# -ise/-ize、waggon/wagon 这些地方**本来就不一样**。照证人改等于把底本的
# 拼写换成另一版的拼写，属于篡改（feedback_pdf_verify_before_change）。
# 词尾那组还要反过来用：`spirituaUsing` 是「U 读错 + 英式词尾」，
# 该修的只有 U，修完得还回 -ising，不能变成 -izing。
VARIANT_TAIL = [('isation', 'ization'), ('isations', 'izations'),
                ('ising', 'izing'), ('ised', 'ized'), ('ises', 'izes'),
                ('ise', 'ize'), ('iser', 'izer'), ('isers', 'izers')]
VARIANT_WORD = {
    'waggon': 'wagon', 'waggons': 'wagons', 'connexion': 'connection',
    'connexions': 'connections', 'shew': 'show', 'shews': 'shows',
    'shewn': 'shown', 'shewing': 'showing', 'inflexion': 'inflection',
    'inflexions': 'inflections', 'reflexion': 'reflection',
}


def canon(w):
    """把英美拼写差异抹平，用来判断两个读数是不是「同一个词的两种拼法」。"""
    x = w.lower()
    if x in VARIANT_WORD:
        return VARIANT_WORD[x]
    for br, am in VARIANT_TAIL:
        if x.endswith(br) and len(x) > len(br) + 1:
            return x[:-len(br)] + am
    return x


def keep_style(dst):
    """修完把英式词尾还回去：spirituaUsing → spiritualising（不是 -izing）。

    按**本书**的正字法办，不按证人的，也不看 OCR 串自己长什么样 ——
    `spirituaUsing` 的 U 就是读错的那个字母，拿它去判词尾判不出来。
    `size`/`prize` 不是这个后缀，用「-ize 前面至少还有三个字母」挡掉。
    """
    low = dst.lower()
    for am, br in BRITISH_TAIL:
        if low.endswith(am) and len(low) - len(am) >= 3:
            return dst[:-len(am)] + br
    return dst


def load_witness():
    """三卷证人 → 一条词流。斜体哨兵是私用区字符，按 Unicode 类别剔干净。"""
    words, chunks = [], []
    for path in WITNESS:
        for page in pickle.load(open(path, 'rb')):
            for par in page['pars']:
                t = ''.join(c for c in par['text'] if unicodedata.category(c) != 'Co')
                chunks.append(t)
    text = '\n'.join(chunks)
    return TOKEN.findall(text), text


def build_index(words):
    idx = defaultdict(list)
    low = [w.lower() for w in words]
    for i in range(len(low) - ANCHOR):
        idx[tuple(low[i:i + ANCHOR])].append(i)
    return idx, low


def edit_distance(a, b):
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def look_up(toks, i, idx, wlow, worig):
    """读出证人在 toks[i] 这个位置上印的词。

    锚不能固定取「前三个词」：这本书的错是成片的，锚里往往恰好也有一个词
    读崩了，一崩整个锚就失配——`nowitness` 那一大栏多半是这么来的，并不是
    证人真的没有这段话。改成在目标词**前后各六词**的窗口里滑动，凡是连续
    三个词能在证人语料里命中的都算一个锚，再按各自的位移反推目标词的位置。

    一个锚命中多处而读数不一致的作废；多个锚给出不同读数的也作废。
    宁可不判，不可判错——判错是静默的，不判只是留在账上。
    """
    n = len(toks)
    low = [t.lower() for t in toks]
    nxt = low[i + 1] if i + 1 < n else None
    prv = low[i - 1] if i > 0 else None

    def probe(order, confirm_at, confirm_word):
        """按给定顺序试锚，第一个给出唯一读数的就采用。

        confirm_* 是**另一侧的确认**：锚定位之后，证人在相邻位置上印的词
        也得对得上。少了这一道，锚偶然撞到语料别处就会读出隔壁的词
        （`Bpeak` 读成 represented、`Kighteousness` 读成 Jehovah 都是这样）。
        """
        for start in order:
            if start < 0 or start + ANCHOR > n or start <= i < start + ANCHOR:
                continue
            hits = idx.get(tuple(low[start:start + ANCHOR]))
            if not hits or len(hits) > MAX_HITS:
                continue
            delta = i - start
            cand = set()
            for p in hits:
                j = p + delta
                if not (0 <= j < len(wlow)):
                    continue
                if confirm_word is not None:
                    k = j + confirm_at
                    if not (0 <= k < len(wlow)) or wlow[k] != confirm_word:
                        continue
                cand.add(worig[j])
            if len(cand) == 1:
                return cand.pop()
        return None

    # 锚**由近及远**试：锚离目标越远，中间夹进一处增删的概率越大，位移一错
    # 就读出隔壁的词。但只认「紧挨着的三个词」又太脆——这本书的错成片出现，
    # 锚里往往也有坏词。所以滑动，且分三级：
    near_l = range(i - ANCHOR, i - ANCHOR - WINDOW - 1, -1)
    near_r = range(i + 1, i + 1 + WINDOW)
    #   一、左锚 + 右邻确认（两侧都对上，最可靠）
    r = probe(near_l, 1, nxt)
    if r is not None:
        return r
    #   二、右锚 + 左邻确认
    r = probe(near_r, -1, prv)
    if r is not None:
        return r
    #   三、左锚、不做确认。粘连处（SeeExod = See + Exod）证人比我们多一个
    #       token，右邻永远对不上，只有这一级能判出来；也最容易误判，垫底。
    return probe(near_l, 0, None)


def glyph_reachable(tok, reading, depth=2):
    """从 OCR 串出发，按 1864 那套「误读 → 正确」的字形规则，能不能走到证人读数。

    这是一道**方向性**的证据，判词闸解决不了的那种局面全靠它：证人读数是
    Antilibanus / Alleghanies / majestaticus 这类专名与拉丁词，词典里查不到，
    证人语料里也只出现这一次，判词闸只能把它当噪点否掉，可它明明是对的。

    字形规则是单向的（`h → li`、`U → ll`、`fi → ff`——左边是误读，右边是
    正确形态）。从我们这串走得到证人那串，就说明**错在我们这边**，证人给的
    是它没读崩的样子。走不到，就是两版各读各的，或者证人自己读崩了
    （`Bathsheba → Bathshcba` 需要 e→c，规则表里没有，正好挡住）。
    """
    a, b = tok.lower(), reading.lower()
    seen, frontier = {a}, {a}
    for _ in range(depth):
        nxt = set()
        for x in frontier:
            for y in glyph_step(x):
                if y == b:
                    return True
                if y not in seen:
                    seen.add(y)
                    nxt.add(y)
        frontier = nxt
    return False


def hyphen_or_space(a, b, wtext):
    """这个复合词在证人正文里是带连字符还是分写的？按多数定。

    连字符那一侧要容忍换行：证人自己也会在同一个位置断行，
    印出来是 `well-\nwatered`。
    """
    h = len(re.findall(rf'\b{re.escape(a)}-\s*{re.escape(b)}\b', wtext, re.I))
    s = len(re.findall(rf'\b{re.escape(a)}\s+{re.escape(b)}\b', wtext, re.I))
    if h == 0 and s == 0:
        return '?'          # 两种都没见过，留给人判
    return '-' if h > s else ' '


def verdict(tok, reading, lex, wvocab, bvocab, wtext, nxt, wbigram, nxt_raw=''):
    """证人读数 → 判决。"""
    # 手工表排在最前面：它们本来就是**证人也判不了**才手工核定的，
    # 排在「证人没读数」后面等于永远轮不到（Itsis / upbefore / Ezekel 都这么丢过）。
    if tok.lower() in HANDS_OFF:
        return 'handsoff', reading or ''
    if tok.lower() in MANUAL:
        return 'manual', MANUAL[tok.lower()]
    if reading is None:
        return 'nowitness', ''
    if reading.lower() == tok.lower():
        return 'confirm', reading
    # 读数不能是单个字母（a / I / O 三个真词除外）。把一个 token 缩成一个
    # 字母几乎不可能是对的，多半是证人在希伯来活字那一片自己读崩了
    # ——`Sb`（希伯来残渣）就这么被改成了 `b`。
    if len(reading) == 1 and reading.lower() not in ('a', 'i', 'o'):
        return 'badwitness', reading
    # 正字法闸：只是英式／美式拼法之差，不是错
    if canon(tok) == canon(reading):
        return 'variant', reading
    reading = keep_style(reading)
    # 粘连：证人读数是 OCR 串的前缀，剩下的一截也成词 —— 两个词被挤成了
    # 一个。直接换成证人读数会**吞掉后一个词**（revilingsto → revilings，
    # to 就没了），必须拆开还原。
    #
    # 拆开填什么，分三种，不能一律填空格：
    #   连字符  well-watered / twenty-second / burnt-offering 这类复合词，
    #           断在行末，抽取阶段那条「行末连字符 + 下行小写 = 断词」的
    #           规则把连字符吃掉了，拼成 wellwatered。填空格等于把原书的
    #           连字符改成空格，仍然不是底本的样子。到证人正文里数一下
    #           `a-b` 和 `a b` 各出现多少次，按多数还原。
    #   空格    thehouse / SeeExod / totheir，OCR 单纯把空格读丢了。
    #   撇号    applied'to / men'seek，空格位置上落了个多余的撇。
    # 两截都得是**真词**且各自 ≥2 个字母，否则只是证人自己读崩了
    # （Adhonai → Adhon ai、natiom → natio m 都是这么来的）。
    if tok.lower().startswith(reading.lower()):
        rest = tok[len(reading):]
        quote = rest[:1] in ("'", '\u2019')
        core = rest.lstrip("'\u2019")
        if len(reading) >= 2 and len(core) >= 2 and is_word(reading, lex) and is_word(core, lex):
            if quote:
                return 'splitq', reading + ' ' + core
            sep = hyphen_or_space(reading, core, wtext)
            if sep == '?':      # 证人正文里两种写法都没出现过，不猜
                return 'unknownsep', reading + '|' + core
            return ('hyphen' if sep == '-' else 'split'), reading + sep + core
    # 粘连的另一半：证人读数**不是**前缀，但 OCR 串尾巴上多挂着一个虚词
    # （`Mejoicein` = Rejoice + in，`appUcationof` = application + of）。
    # 只换成证人读数会把那个虚词吞掉，得先摘下来再拼回去。
    for tail in GLUE_TAIL:
        # 串必须比证人读数长出至少一个虚词那么多，且摘掉虚词后**几乎就是**
        # 证人读数（差一个字母以内）。放宽任何一条都会把 `circimilocution`
        # 这类结尾恰好撞上虚词的整词错拆成两半。
        if tok.lower().endswith(tail) and len(tok) > len(tail) + 2:
            head = tok[:-len(tail)]
            # 摘掉虚词后必须**更像**证人读数，不然只是词尾碰巧撞上虚词
            # （circimilocution 结尾是 "on"，摘掉反而离 circumlocution 更远）。
            # 「像」不能只按编辑距离算：`appUcation → application` 是一个
            # U 顶了 li 两个字母，编辑距离是 2，可它恰恰是本书最典型的那类错，
            # 所以字形规则走得通也算像。
            if ((edit_distance(head.lower(), reading.lower()) <= 1
                    or glyph_reachable(head, reading))
                    and edit_distance(head.lower(), reading.lower())
                        < edit_distance(tok.lower(), reading.lower())
                    and not (tail in PREP and nxt in PREP)
                    and (reading.lower(), tail) in wbigram):
                return 'split', reading + ' ' + tok[-len(tail):]

    # 一个词被空格劈成了两个 token：`Egy t` = Egypt、`com are` = compare、
    # `confes Bion` = confession、`clauf e` = clause。只换前半截会留下一截
    # 孤立的残字（`Egypt t`），必须把两个 token 一起换掉。
    # 只往「证人拼成一个词」的方向合并，且那个词必须是真词或本书别处
    # 正确用过——否则会反过来把我们**本来正确的两个词**按证人自己的连写
    # 错误并掉（`salvum fac` 差点被并成 salvumfac）。
    # 四道约束，缺一条就会把「前一个词的碎片」和后一个词硬凑在一起
    # （`eady` + `manifested` → manifested，把 eady 吞掉；正确做法是让
    # 前面那个 `alr` 去和 `eady` 拼成 already，那条路本来就走得通）：
    #   两截都要 ≥2 个字母      —— 挡住 `Mai. i`（Mal. i. 是书卷缩写，不是断词）
    #   读数不能等于其中一截    —— 等于就说明另一截被吞了
    #   拼起来的长度要和读数相当 —— 差 2 个字母以内
    if (nxt_raw and len(reading) > len(tok) and len(tok) >= 2 and len(nxt_raw) >= 2
            and reading.lower() not in (tok.lower(), nxt_raw.lower())
            and abs(len(tok) + len(nxt_raw) - len(reading)) <= 2
            # 拼起来必须比单独这一截**更接近**读数。否则本来只是这个词自己
            # 掉了个字母（`rospered` → prospered），硬拼上后一个就把它吞了。
            and edit_distance((tok + nxt_raw).lower(), reading.lower())
                < edit_distance(tok.lower(), reading.lower())
            and (is_word(reading, lex) or bvocab[reading.lower()] >= 1)):
        joined = (tok + nxt_raw).lower()
        # 证人正文里若印着带连字符的写法，那就是书里**本来就有的复合词**
        # （co-extensive / co-relative），不是被行末断词劈开的，不能并。
        hyphenated = re.search(rf'\b{re.escape(tok)}-\s*{re.escape(nxt_raw)}\b',
                               wtext, re.I)
        if not hyphenated and (edit_distance(joined, reading.lower()) <= 1
                               or glyph_reachable(tok + nxt_raw, reading)
                               or SequenceMatcher(None, joined,
                                                  reading.lower()).ratio() >= JOIN_SIM):
            return 'joinnext', reading

    # 词头粘连：证人读数是 OCR 串的**后缀**，前面那截是个虚词。
    for head in GLUE_HEAD:
        if (tok.lower().startswith(head) and tok.lower().endswith(reading.lower())
                and len(tok) == len(head) + len(reading)
                and (head, reading.lower()) in wbigram):
            return 'split', tok[:len(head)] + ' ' + reading

    # 字形闸：两版之间的改写读数长得完全不像，挡在这里。
    # 但「长得像」不能只用编辑距离量：连字被读成单个字形时，一个 U 顶掉
    # li／ll 两个字母，`faUs → falls` 的编辑距离是 2、占串长的一半，
    # 照距离算要被当成改写否掉——而它恰恰是这本扫描件最典型的错。
    # 字形规则走得通，本身就证明了「同一个词被读崩」，比距离硬。
    # 「长得像」有三种量法，任一成立即可：编辑距离占比、字形规则可达、
    # 序列相似度。前两种都偏严——连字被读成单个字形时一个 U 顶掉两个字母，
    # 距离占比立刻超标；而规则表也穷举不完 `Imows→knows`、`lilie→like`、
    # `xmder→under`、`knoio→know` 这些多字母同时崩掉的读法。
    # 实测相似度在 0.6 处分得很干净：≥0.6 的几乎全对，≤0.4 的几乎全是
    # 锚落错位置读出的隔壁词。0.5 那一档鱼龙混杂，宁可漏判不误判。
    if (edit_distance(tok.lower(), reading.lower()) > max(1, len(tok) * MAX_DIST_RATIO)
            and not glyph_reachable(tok, reading)
            and SequenceMatcher(None, tok.lower(), reading.lower()).ratio() < SIM_FLOOR):
        return 'divergent', reading
    # 判词闸：真词，或证人语料里反复出现的专名 / 音译，
    # 或者字形上「我们这串是它读崩的产物」——见 glyph_reachable
    if not (is_word(reading, lex) or wvocab[reading.lower()] >= 3
            or glyph_reachable(tok, reading)):
        return 'badwitness', reading
    # 语料自证闸：短读数还要求本书别处**正确地**用过。
    # 位置证据再强也架不住证人自己那一处读崩：`di nne majesty`（divine 被
    # 拆成两半）证人读成 `ine`，位置对得严丝合缝，可 `ine` 在本书里从来
    # 不是一个词，韦氏词表却收了它，判词闸拦不住。
    # 只卡 ≤4 字母：长词是不是真词一望而知，再要求词频旁证就会把
    # `panegyric`/`hearkening` 这种**全书只出现这一次**的正确修复全否掉
    # （PROVENANCE 记过这个坑），得不偿失。
    if len(reading) <= 4 and bvocab[reading.lower()] < 1 and wvocab[reading.lower()] < 3:
        return 'unattested', reading
    return 'fix', reading


def restore_case(src, dst):
    """首字母被规则动过就不还原大写（Uterally 的 U 是 li 连字，不是词首大写）。"""
    if src[:1].lower() == dst[:1].lower():
        if src.isupper() and len(src) > 1:
            return dst.upper()
        if src[:1].isupper():
            return dst[:1].upper() + dst[1:]
    return dst


# 逐条核过上下文、确认证人错而底本对的。加进来必须写明为什么。
# 证人只读出半截、或读崩了，但真值由上下文与钦定本可确指的。逐条核过。
MANUAL = {
    # Ps. cv. 17 "he was sold for a servant"；证人只读出 sold，
    # 尾巴上的 jor 是 for（f 读成 j），按证人会拼成 "sold or"
    'soldjor': 'sold for',
    'dxoellfor': 'dwell for',      # "dwell for evermore"，w 读成 xo
    # 「摘掉词尾虚词」那条规则在这里失灵：证人正文里碰巧有 "subject it"
    # 这个搭配，bigram 闸放行了，可这一处是 "the subject or contents"，
    # 尾巴上的 it 是 subject 自己读崩的，不是另一个词
    'subjetit': 'subject',
    # 下面四个是证人正文里连字符 / 空格两种写法都没出现过的粘连，
    # 靠上下文与钦定本定的
    'itsis': 'It is',              # "It is of this mortal sin, and not of…"
    'upbefore': 'up before',       # "let me cheer up, before I go hence"
    'ezekel': 'Ezekiel',           # "only here and in Ezekiel xl."
    'contemporarycomposition': 'contemporary composition',
    # Ps. 105:29 "He turned their waters to blood and killed their fish"。
    # 两版在同一处都读崩了（1864 作 Uood，1850 作 Mood），位置判读于是
    # 拿一份崩的去改另一份崩的。blood 在本书别处出现 43 次，钦定本亦同。
    'uood': 'blood',
}

HANDS_OFF = {
    'oves',      # "Gen. xii. *oves et boves*" 是拉丁文，证人把 v 读成 r
    'quousque',  # "Domine, quousque" 拉丁文本来就是一个词，证人拆成了 quo usque
    'lusus',     # "lusus verborum"，同上，证人拆成 lus us
    # 下面几个都在**希伯来文音译或节号**的位置上。证人在同一处也读崩了，
    # 只是崩得不一样，位置证据于是给出一个同样无意义的读数。两份 OCR
    # 都读不出来的地方，只能等第三份底本，不能拿其中一份去改另一份。
    'jy',        # "The adjective jy means afflicted" —— 希伯来词，证人读成 iy
    'ki',        # "the particle of entreaty Ki" —— 同上，证人读成 i
    'nr',        # "the simple Hebrew phrase nr D"
    'ht',        # "the pronoun Ht, this is our God"
    'nne',       # "the di nne majesty" —— divine 被拆成两半，证人读成 ine
    'ig',        # "Ezekiel x. IG" —— 是节号 16，不是词
    'idn',       # "derived from IDn, love" —— 希伯来文音译，证人读成 ion
    'tojhee',    # "to thee"，t 读成 j 又粘上了 to；证人只读出 thee，照抄会吞掉 to
    'shalll',    # "shall I, must I go" 挤成了 `shalll,mmt I go`，见 MANUAL_TEXT
    'mmt',       # 同上
    'kj',        # 希伯来文的祈使小品词，两份 OCR 各读各的
    'haman',     # Esther vii. 10 的哈曼，我们是对的；证人读成 Hainan
    # 下面四个证人只读出半截，token 级替换会吞掉后一个词，
    # 交给 MANUAL_TEXT 整句改（不挡住这里，token 修复会先把串改掉，
    # MANUAL_TEXT 就再也匹配不上——自检报的那四条失效就是这么来的）
    'egy', "irutes'm", 'andtve', 'godvml',
    'anji',      # "the inside of anji hing" = anything，见 MANUAL_TEXT
    # 以下都在希伯来活字的位置上，两份 OCR 各崩各的，证人读数同样无意义
    'xy',        # "derived from in and Xy" / "see and ear i Xy and INly'"
    'tl',        # "repetition of the verb Tl" —— 证人作 TV / ifih
    'il',        # "because D il nations had now begun"
    'iif',       # "that iif and i are treated" —— 讨论希伯来字母
    'je',        # "his prayer shall Je Jbr sin" —— 该是 be，证人也读成了 he
}

# 本书是伦敦排的英式本：-ised 210 : -ized 8，-ising 107 : -izing 2。
# 证人（费城美式本）给的 -ize 词尾一律还回 -ise，不然修一个错字顺手把
# 底本的正字法改成了另一版的。
BRITISH_TAIL = [('ization', 'isation'), ('izations', 'isations'),
                ('izing', 'ising'), ('ized', 'ised'), ('izes', 'ises'),
                ('izer', 'iser'), ('ize', 'ise')]

# 粘连词尾只认这些虚词。放开成「任何真词」会把 expositicai 这类**本来就
# 该整体替换**的串误判成粘连，硬拆出一个不存在的词。
GLUE_TAIL = ['of', 'in', 'to', 'is', 'as', 'be', 'on', 'at', 'it', 'he',
             'we', 'or', 'and', 'the', 'for', 'that', 'not', 'but', 'with',
             'them', 'him', 'her', 'us', 'me', 'my', 'thee', 'thou', 'thy',
             'will', 'shall', 'are', 'was', 'his']

# 拆出来的虚词后面**又是**一个介词，说明拆错了：`Salein of Gen. xiv` 的
# 真值是 `Salem of`，硬拆成 `Salem in` 会读出 "Salem in of Gen. xiv"。
PREP = {'of', 'in', 'to', 'for', 'with', 'on', 'at', 'as', 'by', 'from'}

# 粘连也会发生在**词头**：`Andbrought` = And + brought，`uponMahalath` =
# upon + Mahalath。只换成证人读数会把前一个词吞掉，和词尾那种一样。
GLUE_HEAD = ['and', 'upon', 'of', 'in', 'to', 'the', 'from', 'with', 'on',
             'for', 'as', 'is', 'be', 'that', 'not', 'but', 'see', 'compare']

# token 判读够不着的那一类，全部对着 1850 三卷本逐字核过：
#   · **真词错**——`fall`/`Done`/`and` 本身是英文词，判词闸根本不会把它们
#     当可疑 token，位置判读也就永远轮不到它们；
#   · **标点与非字母符号**——`&`、`~`、`(Ps,` 落在 token 正则之外；
#   · **一词被读成两个 token**——得两个一起换。
# 写成整句而不是单词，是因为这些词在别处都是对的，只有这一处错。
MANUAL_TEXT = [
    # 著者序（对照 psalmstranslated01alex 逐词校）
    ('more ha& been directly drawn', 'more has been directly drawn'),
    ('a prayer, &c.i sometimes', 'a prayer, &c.; sometimes'),
    ('The first book (Ps, i.-xli.)', 'The first book (Ps. i.-xli.)'),
    ('one by Moses (Ps. xc), and several', 'one by Moses (Ps. xc.), and several'),
    ('culminating point and fall development', 'culminating point and full development'),
    ('promise was in fall possession', 'promise was in full possession'),
    ('weakened rather~than enhanced', 'weakened rather than enhanced'),
    ('which might be fally treated', 'which might be fully treated'),
    # 正文
    ('" and to Done more than my neighbours,"', '" and to none more than my neighbours,"'),
    ('as it is c6mmonly translated, *and of the living,*',
     'as it is commonly translated, *land of the living,*'),
    ('as it is commonly translated, *and of the living,*',
     'as it is commonly translated, *land of the living,*'),
    # 上一句里 *then* 本身就在同一句的前半截以正确形态出现（"equivalent to
    # *then* or *still* after a conditional clause"），自证充分
    ('*theji* they shall remain', '*then* they shall remain'),
    # "Lips of *rejoicings*" 被读成 "rejoicinr s"，尾巴上的 s 单独成了 token
    ('rejoicinr s', 'rejoicings'),
    # 证人作 "he himself, and not a delegated"；我们这边 himself 被劈成
    # `hi` + `iiself` 两个 token，只改后半截会剩个孤立的 hi
    ('he hi iiself', 'he himself'),
    # 词被连字符甩掉最后一两个字母，token 判读只能看见前半截
    ('denotes failui-e to discharge', 'denotes failure to discharge'),
    ('mere ordinai-y men', 'mere ordinary men'),
    # 证人作 "shall I, must I go"（Ps. 43:2）；I 被吞、must 读成 mmt，
    # 挤成了一个 `shalll,mmt`
    ('*shalll,mmt I go', '*shall I, must I go'),
    # 词被杂散符号劈开，token 判读只看得见半截，只能整句改
    ('*Lips of rejoicinr^s*', '*Lips of rejoicings*'),
    ('seems to confii-m the', 'seems to confirm the'),
    ('though 6}Tionymous, is not', 'though 6}synonymous, is not'),
    ('more emphaticallyy^sf', 'more emphatically^sf'),
    # 词被 OCR 噪点劈开，中间夹的不是空格也不是连字符，joinnext 够不着
    ('smiter of) Egy2)t, i. e.*', 'smiter of) Egypt, i. e.*'),
    ('the Egj-ptians', 'the Egyptians'),
    ('and com];>are Isa', 'and compare Isa'),
    ('*inside* of anji-hing', '*inside* of anything'),
    # 证人只读出半截，照抄会吞掉后一个词
    ('*Irutes\'m* general', '*brutes* in general'),
    ('horses, andtve in the name', 'horses, and we in the name'),
    ('*GodvMl send his mercy', '*God will send his mercy'),

    # 游离的连字符。token 正则在连字符处断开，两截又各自是真词，
    # 判读器根本看不见它们；可这一横印在页面上就是个错。
    # 逐处到证人正文里核过，17 处**全都没有**这一横：
    #   "does not make the day, with its attendant toils, perpetual"
    #   "he shall not fear, until he look upon his foes"  …
    # 另两处是行末断词的连字符没去掉（following / construction）。
    ('day, -ndth its attendant', 'day, with its attendant'),   # -ndth 即 with
    ('shall not fear, -until he look', 'shall not fear, until he look'),
    ('the last clause -is, *to keep', 'the last clause is, *to keep'),
    ('When the -vileness (or vilest)', 'When the vileness (or vilest)'),
    ('and despised of the -people.*', 'and despised of the people.*'),
    ('now rejoices. As -he believed', 'now rejoices. As he believed'),
    ('always have occasion -so to do', 'always have occasion so to do'),
    ('depravity to the -wicked (one)', 'depravity to the wicked (one)'),
    ('one of poetical -composition, as Virgil', 'one of poetical composition, as Virgil'),
    ('usually that of the -writer.', 'usually that of the writer.'),
    ('*food to the -people, to the wild', '*food to the people, to the wild'),
    ('xxxiv. 7, 8) -to denote the act', 'xxxiv. 7, 8) to denote the act'),
    ('*(when he writeth -up the people)*', '*(when he writeth up the people)*'),
    ('a heart of -wisdom," with allusion', 'a heart of wisdom," with allusion'),
    ('is the centre of the -psalm, and', 'is the centre of the psalm, and'),
    ('admits of this constr-uction:', 'admits of this construction:'),
]

# 著者序末尾那段 NOTE TO THE READER 和罗马数字换算表，是 Kregel 1991 年
# 影印时新加的编者按（"most of us today"），版权在世；PROVENANCE 已定
# Kregel 新增内容一律不取（p12–13 的 FOREWORD 同此）。两栏表在 OCR 里
# 还塌成了一行，本来也不可读。1864 版的序到 "reward of his exertions." 为止。
PREFACE_CUT = 'NOTE TO THE READER'


def book_vocab(lex):
    """1864 本书里**本来就正确**的词表 —— 语料自证闸的依据。"""
    vocab = Counter()
    for path in sorted(SRC.glob('*.md')):
        text = re.sub(r'---\n.*?\n---\n', '', path.read_text(encoding='utf-8'), count=1, flags=re.S)
        text = TAG.sub('', text)
        for w in TOKEN.findall(text):
            if is_word(w, lex):
                vocab[w.lower()] += 1
    return vocab


# token 两侧算「干净边界」的字符。左右不对称：`(` 只能在左，`)` 只能在右。
CLEAN_L = set(' \t\n([{"\'*\u201c\u2018\u2014\u2013')
CLEAN_R = set(' \t\n)]}.,;:!?"\'*\u201d\u2019\u2014\u2013')


WORDISH = re.compile(r"[A-Za-z][A-Za-z'\u2019]*")


def _hyphen_ok(text, pos, lex, back):
    """连字符两侧：另一半是真词就算正常复合词，否则是被劈开的半截。

    `short-Uved` 的 `short` 是真词 → 这是 short-lived 断在行末，后半截该修；
    `gi-atitude` 的 `gi` 不是词 → 整个串是 gratitude 被杂散连字符劈开，别碰。
    """
    if back:
        m = None
        for m in WORDISH.finditer(text[max(0, pos - 30):pos]):
            pass
        other = m.group(0) if m and m.end() == pos - max(0, pos - 30) else ''
    else:
        m = WORDISH.match(text, pos)
        other = m.group(0) if m else ''
    # 另一半必须至少两个字母：`failui-e` 的 `e`、`ordinai-y` 的 `y` 是被
    # 连字符甩出来的单个字母，不是复合词的一半。放它们过去，前半截就会被
    # 修成 failure / ordinary，留下 `failure-e` 这种更坏的结果。
    return len(other) >= 2 and is_word(other, lex)


def clean_bounded(text, a, b, lex):
    """这个 token 是不是一个**完整的词**，而不是被杂散标点劈开的半截。

    `gi-atitude` 会被 token 正则切成 `gi` 和 `atitude`，后半截拿去判读就成了
    `gratitude`，落盘写出 `gi-gratitude`——比原来更坏。`^octrine`、`2)rospered`、
    `hi)iiself`、`v/hich`、`ma,nifestation` 全是这么来的。
    左边紧挨着 `-` `)` `/` `,` `^` 这类字符（而不是空格或开引号）就说明
    它只是半个词，不判。
    """
    # 只有**符号的另一侧还是字母或数字**才算碎片——那说明一个词被这个符号
    # 劈成了两半（`gi-atitude` `ma,nifestation` `2)rospered`）。若符号外面是
    # 空格，那只是词旁边落了个杂散符号（` &ee` ` ^octrine` `this^ `），
    # 词本身是完整的，照修不误。
    def joined(k, step):
        j = k + step
        return 0 <= j < len(text) and (text[j].isalnum() or text[j] == "'")

    ok_l = a == 0 or text[a - 1] in CLEAN_L or not joined(a - 1, -1)
    ok_r = b >= len(text) or text[b] in CLEAN_R or not joined(b, 1)
    # 连字符另说：两侧都是真词就是正常复合词，该修
    if not ok_l and text[a - 1] == '-':
        ok_l = _hyphen_ok(text, a - 1, lex, True)
    if not ok_r and text[b] == '-':
        ok_r = _hyphen_ok(text, b + 1, lex, False)
    return ok_l and ok_r


def chapter_tokens(text):
    """正文 token 流（含在原文里的 span/offset），注释与 HTML 标签内的不算。"""
    spans = []
    fm = re.match(r'---\n.*?\n---\n', text, re.S)      # front matter 不是正文
    if fm:
        spans.append(fm.span())
    for m in TAG.finditer(text):
        spans.append(m.span())
    def masked(pos):
        return any(a <= pos < b for a, b in spans)
    out = []
    for m in TOKEN.finditer(text):
        if not masked(m.start()):
            out.append((m.group(0), m.start(), m.end()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--only', help='只跑某几篇，逗号分隔')
    args = ap.parse_args()

    # 判词典的补充词表加载不到会**静默降级**：is_word 把一大批本来正确的
    # 19 世纪拼法与专名当成可疑 token，判读器于是凭空多出几百条「修复」。
    # 这种失败没有任何症状，只有对着日志逐条看才发现，必须让它直接停下。
    if not alexander_lexicon.EXTRA.exists():
        sys.exit(f'补充词表缺失：{alexander_lexicon.EXTRA}\n'
                 '判词闸会失准，判读结果不可用。先确认 alexander_lexicon.EXTRA 的路径。')

    lex = build()
    bvocab = book_vocab(lex)
    worig, wtext = load_witness()
    idx, wlow = build_index(worig)
    wvocab = Counter(wlow)
    # 拆词的旁证：拆出来的这两个词，证人正文里得真的**相邻出现过**。
    # `hearkeit` 摘掉尾巴恰好是 hearken，可 "hearken it" 这个说法书里没有，
    # 它其实是一个词读崩了，不是两个词粘在一起。
    wbigram = set(zip(wlow, wlow[1:]))
    print(f'证人词流 {len(worig)} 词，{len(idx)} 个 {ANCHOR}-gram 锚', file=sys.stderr)

    files = sorted(SRC.glob('*.md'), key=lambda p: (p.stem != 'preface', p.stem))
    files = [f for f in files if f.name != 'index.html']
    if args.only:
        keep = set(args.only.split(','))
        files = [f for f in files if f.stem in keep]

    stat = Counter()
    rows = []
    # MANUAL_TEXT 是按整句匹配的，上游一改（重新 extract、repair 换规则），
    # 匹配不上就**静默不生效**——跟判词典缺失同一类无症状失败。
    # 记下每条命中过几次，一条都没命中的最后报出来。
    hit = Counter()
    for path in files:
        text = path.read_text(encoding='utf-8')
        toks = chapter_tokens(text)
        words = [t[0] for t in toks]
        edits = []
        for i, (w, a, b) in enumerate(toks):
            if is_word(w, lex):
                continue
            reading = look_up(words, i, idx, wlow, worig)
            nxt = words[i + 1].lower() if i + 1 < len(words) else ''
            # 被劈开的同一个词，中间只可能隔一个空格或一个残留的行末连字符
            # （`confes- Bion` = confession，`conti-ast` = contrast）。
            nxt_raw = ''
            if i + 1 < len(toks) and SPLIT_SEP.match(text[b:toks[i + 1][1]] or ' '):
                nxt_raw = toks[i + 1][0]
            kind, r = verdict(w, reading, lex, wvocab, bvocab, wtext, nxt,
                              wbigram, nxt_raw)
            # 碎片判定放在判决**之后**：被杂散符号劈开的半截，只要能跟
            # 邻居拼回一个整词（joinnext），那就不是碎片而是可修的错。
            if kind != 'joinnext' and not clean_bounded(text, a, b, lex):
                kind, r = 'fragment', ''
            if kind == 'joinnext':
                b = toks[i + 1][2]          # 替换范围延伸到下一个 token 末尾
                w = text[a:b]
            # 改完和左右邻居撞成叠词，多半是把节号 / 缩写当成了词
            if kind == 'fix':
                nb = [t[0].lower() for t in toks[max(0, i - 1):i + 2] if t[0] != w]
                if r.lower() in nb:
                    kind = 'dupe' 
            stat[kind] += 1
            ctx = ' '.join(words[max(0, i - 4):i + 5])
            rows.append((path.stem, w, r, kind, ctx))
            if kind in ('fix', 'split', 'splitq', 'hyphen', 'manual', 'joinnext'):
                edits.append((a, b, restore_case(w, r), w))
        if args.apply and (edits or any(a in text for a, _ in MANUAL_TEXT)
                            or (path.stem == 'preface' and PREFACE_CUT in text)):
            for a, b, new, was in reversed(edits):
                # 偏移核对：落盘时这一段必须仍是判读时看到的那个 token。
                # 错位是**静默**的，不核对根本发现不了（另一条线上就因为
                # 判读与落盘用了两份切分，把 prosperity 换成了隔壁拉丁引文里的词）。
                if text[a:b] != was:
                    sys.exit(f'{path.name} 偏移错位：位置 {a} 应为 {was!r}，实为 {text[a:b]!r}')
                text = text[:a] + new + text[b:]
            for a, b in MANUAL_TEXT:
                if a in text:
                    hit[a] += text.count(a)
                    text = text.replace(a, b)
            if path.stem == 'preface' and PREFACE_CUT in text:
                text = text[:text.index(PREFACE_CUT)].rstrip() + '\n' 
            path.write_text(text, encoding='utf-8')

    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('chapter\tfrom\twitness\tverdict\tcontext\n')
        for r in rows:
            f.write('\t'.join(r) + '\n')
    # 「没命中」有两种：本来就已经修好了（幂等重跑的常态），和上游文本
    # 变了导致规则失效（真故障）。靠**修复后的形态在不在**来区分：
    # 两种形态都找不到，才是真的失效了。
    stale = []
    for a, b in MANUAL_TEXT:
        if hit[a]:
            continue
        if not any(b in f.read_text(encoding='utf-8') for f in files):
            stale.append(a)
    if stale:
        print(f'!! MANUAL_TEXT 有 {len(stale)} 条失效了（原文与修复后的形态都找不到）:')
        for a in stale:
            print('   ', repr(a))
    else:
        print(f'MANUAL_TEXT {len(MANUAL_TEXT)} 条：命中 {sum(1 for a, _ in MANUAL_TEXT if hit[a])}，'
              f'其余已是修复后的形态')
    print('判决:', dict(stat))
    print('日志:', LOG)


if __name__ == '__main__':
    main()
