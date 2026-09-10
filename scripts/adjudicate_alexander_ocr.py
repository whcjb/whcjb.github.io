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

# 锚的长度。3 个词在 35 万词的语料里已经足够罕见，短到 2 个就会撞上
# "of the" 这种到处都是的组合，读出来的是别处的字。
ANCHOR = 3

# 证人读数与 OCR 串的最大编辑距离占比。超过这个就当成两版之间的改写，不采信。
MAX_DIST_RATIO = 1 / 3

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

    三种锚各试一遍，先左后右：左锚三词命中后要求右邻也对上，右锚反之。
    这一条是防「锚碰巧撞上别处」——单边对上很容易，两边同时对上极难。
    命中多处而读数不一致的，一律作废：宁可不判，不可判错。
    """
    def probe(anchor_words, offset, check_at, check_word):
        key = tuple(anchor_words)
        out = []
        for p in idx.get(key, ()):
            j = p + offset
            if not (0 <= j < len(wlow)):
                continue
            k = p + check_at
            if check_word is not None:
                if not (0 <= k < len(wlow)) or wlow[k] != check_word:
                    continue
            out.append(worig[j])
        return out

    left = [t.lower() for t in toks[max(0, i - ANCHOR):i]]
    right = [t.lower() for t in toks[i + 1:i + 1 + ANCHOR]]

    readings = []
    if len(left) == ANCHOR:
        nxt = right[0] if right else None
        readings = probe(left, ANCHOR, ANCHOR + 1, nxt)
    if not readings and len(right) == ANCHOR:
        prv = left[-1] if left else None
        readings = probe(right, -1, -2, prv)
    if not readings and len(left) == ANCHOR:
        readings = probe(left, ANCHOR, 0, None)

    uniq = {r.lower() for r in readings}
    if len(uniq) != 1:
        return None
    return readings[0]


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


def verdict(tok, reading, lex, wvocab, bvocab, wtext, nxt, wbigram):
    """证人读数 → 判决。"""
    if reading is None:
        return 'nowitness', ''
    if reading.lower() == tok.lower():
        return 'confirm', reading
    if tok.lower() in HANDS_OFF:
        return 'handsoff', reading
    if tok.lower() in MANUAL:
        return 'manual', MANUAL[tok.lower()]
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

    # 字形闸：两版之间的改写读数长得完全不像，挡在这里
    if edit_distance(tok.lower(), reading.lower()) > max(1, len(tok) * MAX_DIST_RATIO):
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
             'we', 'or', 'and', 'the', 'for', 'that', 'not', 'but', 'with']

# 拆出来的虚词后面**又是**一个介词，说明拆错了：`Salein of Gen. xiv` 的
# 真值是 `Salem of`，硬拆成 `Salem in` 会读出 "Salem in of Gen. xiv"。
PREP = {'of', 'in', 'to', 'for', 'with', 'on', 'at', 'as', 'by', 'from'}

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
        text = re.sub(r'<!--.*?-->|<[^>]+>', '', text)
        for w in TOKEN.findall(text):
            if is_word(w, lex):
                vocab[w.lower()] += 1
    return vocab


def chapter_tokens(text):
    """正文 token 流（含在原文里的 span/offset），注释与 HTML 标签内的不算。"""
    spans = []
    fm = re.match(r'---\n.*?\n---\n', text, re.S)      # front matter 不是正文
    if fm:
        spans.append(fm.span())
    for m in re.finditer(r'<!--.*?-->|<[^>]+>', text):
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
            kind, r = verdict(w, reading, lex, wvocab, bvocab, wtext, nxt, wbigram)
            # 改完和左右邻居撞成叠词，多半是把节号 / 缩写当成了词
            if kind == 'fix':
                nb = [t[0].lower() for t in toks[max(0, i - 1):i + 2] if t[0] != w]
                if r.lower() in nb:
                    kind = 'dupe' 
            stat[kind] += 1
            ctx = ' '.join(words[max(0, i - 4):i + 5])
            rows.append((path.stem, w, r, kind, ctx))
            if kind in ('fix', 'split', 'splitq', 'hyphen', 'manual'):
                edits.append((a, b, restore_case(w, r)))
        if args.apply and (edits or any(a in text for a, _ in MANUAL_TEXT)
                            or (path.stem == 'preface' and PREFACE_CUT in text)):
            for a, b, new in reversed(edits):
                text = text[:a] + new + text[b:]
            for a, b in MANUAL_TEXT:
                text = text.replace(a, b)
            if path.stem == 'preface' and PREFACE_CUT in text:
                text = text[:text.index(PREFACE_CUT)].rstrip() + '\n' 
            path.write_text(text, encoding='utf-8')

    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('chapter\tfrom\twitness\tverdict\tcontext\n')
        for r in rows:
            f.write('\t'.join(r) + '\n')
    print('判决:', dict(stat))
    print('日志:', LOG)


if __name__ == '__main__':
    main()
