#!/usr/bin/env python3
"""古治《圣徒的祭：诗篇 116 篇注释》→ gouge/psalm116/（英文版），底本 1868 年 Nichol 重印本 OCR。

    python3 scripts/publish_gouge_psalm116.py

为什么不用 TCP：EEBO-TCP A01981 是一份错配的录入本——正文前半录的是 J. Gough 的剧本《The Strange Discovery》(1640)，
古治这本只录了后半（前 80 余页即第 1–39 小节缺失，此外 8 处各缺 2–4 页，书末也缺）。拼起来会有十来处 1632／1868 两种拼法来回切换，
所以整本用 1868 年 Nichol 本（IA davidsblessedman00smit，影像第 297–442 页；用户 2026-11-19 认可），TCP 覆盖的那六成拿来当第三证人。

清理（nichol1868_ocr.py + 本脚本）：
  ① ABBYY 段落 → ② tesseract 按位置对证 → ①' 符号形／字形规则 →
  ③ 真词互换（两条流都是真词但读法不同，如 tilings/things、laud/land）：TCP 在同一位置（左右各 3 词定位）与哪一边一致就取哪一边；
     TCP 未覆盖或两边都不一致的照 ABBYY 留着，记入 gouge_raw/psalm116/disagree_left.tsv。
  ④ 看图判读表 gouge_raw/psalm116/fixes.tsv（原串须全书唯一）。
结构：「Ver. N.」段起一节经文、一页；其前的总论（第 1–3 小节）一页；「Sec. N.」段首的斜体是小节标题，单成 h4。
编者／原书旁注（6 号字）收在各页末「Notes」。页边经节标记、页眉不收；合订本页码以 p.N 锚点标在页内。
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nichol1868_ocr as n          # noqa: E402
import publish_tcp_psalm as tp      # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'gouge_raw' / 'psalm116'
TEI = '{http://www.tei-c.org/ns/1.0}'
P = 'gg'
BODY = (304, 442)
FRONT = [('dedication', 'The Epistle Dedicatory', '献辞', 299, 301),
         ('to-blackfriars', 'To my Beloved Parishioners of Blackfriars', '致黑衣修士区堂众', 302, 303)]
CFG = dict(tcp='—', author='gouge', book='psalm116', P=P, c0='#3d1d5a', c1='#592b82', psalm=116,
           short='Gouge on Psalm 116', hero='Psalm 116', year='1868',
           title_en="The Saints' Sacrifice: A Commentary on Psalm CXVI",
           tagline="William Gouge · The Saints' Sacrifice",
           edition='First published London 1632 · text of the Edinburgh reprint, James Nichol, 1868')


def sk(w):
    w = n.norm(w).replace('v', 'u').replace('j', 'i').replace('y', 'i')
    w = re.sub(r'(.)\1', r'\1', w)
    return w[:-1] if w.endswith('e') and len(w) > 3 else w


def tcp_index():
    """TCP 古治部分（跳过剧本的 act/scene/prologue）→ sk 词序列与 3-gram 索引。"""
    r = ET.parse(RAW / 'src' / 'A01981.xml').getroot()
    words = []
    for d in r.iter(TEI + 'div'):
        if d.get('type') == 'section':
            words += [sk(x) for x in n.WORD.findall(''.join(d.itertext()).replace('ſ', 's'))]
    idx = {}
    for i in range(len(words) - 2):
        idx.setdefault(tuple(words[i:i + 3]), []).append(i)
    return words, idx


def tcp_vote(left, right, words, idx):
    """左 3 词、右 3 词都在 TCP 里相邻出现（中间恰 1 词）→ 返回中间那个词（sk 形），否则 None。"""
    for i in idx.get(tuple(left), []):
        if tuple(words[i + 4:i + 7]) == tuple(right):
            return words[i + 3]
    return None


def judge_tcp(tcp, left_log):
    """合流时两条流都是真词而读法不同：TCP 在同一位置（左右各 3 词定位）与哪一边一致就取哪一边；定不了返回 None
    （交给二元词频），并记入 disagree_left.tsv。"""
    words, idx = tcp

    def judge(a, t, left, right):
        if not words or len(left) < 3 or len(right) < 3:
            left_log.append((a, t, ' '.join(left + ['[' + a + ']'] + right)))
            return None
        v = tcp_vote([sk(x) for x in left], [sk(x) for x in right], words, idx)
        if v is not None and v == sk(t) and v != sk(a):
            return t
        if v is not None and v == sk(a) and v != sk(t):
            return a
        left_log.append((a, t, ' '.join(left + ['[' + a + ']'] + right)))
        return None
    return judge


def clean(text, wit):
    """合流之后：ABBYY 原样留下的段（对不上 tesseract）再走第 ② 层；然后字形规则。"""
    led = []
    t, _ = n.repair(text, wit, led)
    return n.glyph_repair(t, led)


def balance(t):
    """斜体哨兵配平：没开就关的关标记、到末尾没关的开标记，一律删。"""
    out, op = [], None
    for ch in t:
        if ch == n.IT_ON:
            if op is not None:
                continue
            op = len(out)
        elif ch == n.IT_OFF:
            if op is None:
                continue
            op = None
        out.append(ch)
    if op is not None:
        del out[op]
    return ''.join(out)


def heb(m):
    """(T13rT,)、(pn)、(p2{)：合订本在英文后括注希伯来原词，拉丁引擎读成乱码；判据：括号内不是真词／经节号／罗马数字。"""
    inner = m.group(1).replace(n.IT_ON, '').replace(n.IT_OFF, '').strip(' ,;')
    if not inner or re.fullmatch(r'(?:s[eo][ec]t?\.?|ver\.?|chap\.?)?\s*[\divxlcIVXLC.,:;&\s-]+', inner) or re.fullmatch(r'[A-Za-z]+', inner) and n.is_word(inner):
        return m.group(0)
    toks = re.findall(r'[A-Za-z]+', inner)
    if toks and all(n.is_word(x) for x in toks) and not re.search(r'[\d{}\[\]^]', inner):
        return m.group(0)
    return f'(<span class="{P}-gap" title="Hebrew in the 1868 edition, not read by OCR（原书此处是希伯来文，OCR 读不出）">〈Hebrew〉</span>)'


def dash_space(m):
    a, b = m.group(1), m.group(2)
    if n.is_word_h(a + b):
        return a + b
    if n.is_word(a) and n.is_word(b):
        return a + ' ' + b
    return a + b


ABBR = set('''sec ser serm cap lib ver hom art lect tract par part chap treat gen exod lev num deut josh judg sam kings chron
ezra neh esth job ps prov eccl eccles cant isa jer lam ezek dan hos joel amos obad mic nah hab zeph hag zech mal mat matt
mark luke john acts rom cor gal eph phil col thess tim tit heb james pet jude rev p pp ep epist cont q'''.split())


def fn_ref(m):
    w = m.group(1)
    core = re.sub(r'[^A-Za-z]', '', w).lower()
    if core in ABBR:
        return m.group(0)
    if not re.search(r'[.,;:?!’*]$', w) and core not in ('and', 'performing', 'he'):
        return m.group(0)
    return w


BOOKS = ('Gen|Exod|Lev|Num|Deut|Josh|Judg|Sam|Kings|Chron|Neh|Esth|Job|Ps|Prov|Eccles|Cant|Isa|Jer|Lam|Ezek|Dan|Hos|Joel|'
         'Amos|Mic|Micah|Hab|Zeph|Hag|Zech|Mal|Mat|Mark|Luke|John|Acts|Rom|Cor|Gal|Eph|Phil|Col|Thess|Tim|Tit|Heb|James|'
         'Pet|Jude|Rev|Jonah|Joshua|Judges|Ruth|Ezra|Esther|Hosea|Nahum|Obadiah|Daniel|Exek|Ezek|Titus|Philem')
ABBR_BOOKS = ('Pet|Cor|Gen|Exod|Lev|Num|Deut|Sam|Chron|Ps|Prov|Isa|Jer|Ezek|Dan|Hos|Zech|Mal|Mat|Rom|Gal|Eph|Phil|Col|'
              'Thess|Tim|Tit|Heb|Rev|Neh|Esth|Eccles|Cant|Lam|Hab|Zeph|Hag|Judg|Josh')
# ABBYY 把带 w／v 的宽字母常用词误判成斜体（看图核过 *will*、*own*、*with* 多处）；古治讨论词本身时的斜体是真的
FALSE_IT = 'with|will|wilt|own|evil|wise|type|types|view|in|by|be|so|make|down|yet|thy|they|is|we|all|his|and|over|us|a|write|power|eye'
GLOSS = re.compile(r'(?:particle|word|words|signifieth|signify|plural|singular|term|phrase|translated|noun|verb|pronoun|'
                   r'preposition|adverb|conjunction|copulative|note|notes|emphasis|expressed)\W{0,4}(?:\w+\W{1,3}){0,2}$', re.I)


def false_italic(m):
    pre = m.string[max(0, m.start() - 40):m.start()]
    return m.group(0) if GLOSS.search(pre) else m.group(1)


def roman_l(m):
    u = m.group(0).replace('l', 'i')
    return u if n.lexmod.ROMAN.fullmatch(u) and (m.group(0) == 'vill' or not n.is_word(m.group(0))) else m.group(0)


def md(t):
    """哨兵层面处理斜体（分得清开／关）：合并相邻斜体段、删 OCR 文本里原有的 *（脚注号或噪点），最后才转 markdown。"""
    t = t.replace('*', '')
    t = re.sub(r'[ \u00a0]{2,}', ' ', t)                                         # 先并空格，免得后面的规则因双空格落空
    t = re.sub(r'\s*■\s*', ' ', t)                                    # 污点：先删，免得斜体开头留空白
    t = re.sub(r'\\yi\[', 'will', t)                                  # 诗 85 斜体乱码（影像核：will）
    t = re.sub(r'(?<=[A-Za-z\]\[])\\+(?=\s|' + n.IT_OFF + r'|$)', '', t)   # 词尾孤立反斜杠（vrA\）会转义后面的星号
    t = re.sub(r'\(([^()]{1,12})\)', heb, t)                            # 括号里的希伯来文乱码 → 〈Hebrew〉（在斜体转换之前）
    t = balance(t)
    t = re.sub(n.IT_OFF + r'(\s*)' + n.IT_ON, r'\1', t)
    t = re.sub(n.IT_ON + r'(\s*)' + n.IT_OFF, r'\1', t)               # 空斜体段
    t = re.sub(n.IT_ON + r'(\s*)', r'\1' + n.IT_ON, t)                 # 开标记后的空白挪到外面
    t = re.sub(r'(\s*)' + n.IT_OFF, n.IT_OFF + r'\1', t)               # 关标记前的空白挪到外面
    t = t.replace(n.IT_ON, '*').replace(n.IT_OFF, '*')
    t = re.sub(r'\s*■\s*', ' ', t)
    t = re.sub(r'(?<=[A-Za-z.,;:\'’])[\^}]+(?=[\s,.;:\'’)*]|$)', '', t)     # 脚注号残渣：third^ branch、deliverances}
    t = re.sub(r'(?m)^(\d+)\. ', r'\1\\. ', t)          # 行首序号别被 kramdown 当列表
    t = t.replace('|', '')
    t = re.sub(r'\b([A-Za-z]+)- +([a-z]+)\b', dash_space, t)          # 断词连字符后多了空格：occa- sion
    t = re.sub(r'(?:(?<=[\s>])|^)[A-Za-z]2(?=\s|<|$)', '', t)                     # 书帖签名（Q2、R2）混进正文
    t = re.sub(r'\b([ivxlc]+)1(?=\.\s*\d)', r'\1', t)                    # 经文出处：xi1. 35 → xi. 35（这个 1 是多出来的）
    t = re.sub(r'\b([ivxlc]+)\.\.\s*(?=\d)', r'\1. ', t)                # xxv..8
    t = re.sub(r'(\d),(?=[A-Za-z‘])', r'\1, ', t)                        # 42,and
    # 粘在句末的脚注号：love.2 By、them*.2 As、God.1（段尾）、and1 also；前一个词是缩写（sec.5.、经卷名）不动
    t = re.sub(r'\b([A-Za-z][a-z]+[.,;:?!’]?\*?[.,;:?!’]?)[1-9](?=[\s_<]|\.\s|$)', fn_ref, t)
    t = re.sub(r'(?<=[.?!’*])_(?=\s|$)', '', t)
    t = re.sub(r'(?<=[a-z])\.\.(?=\s[A-Z])', '.', t)                       # 删了脚注号后的 rest.. We
    t = re.sub(r'&(?:e|o|¢|\*[ec]\*|\*Sec\*)?\.', '&c.', t)                 # &c. 读成 &e.／&o.／&.／&*Sec*.
    t = re.sub(r'&(\*?)(?:e¢|[ec¢o]?)(\*?)(?=[.,:;—])',                       # 带斜体标记的：&*c.—Cyp、&e,
               lambda m: '&c' + ('*' if len(m.group(1) + m.group(2)) == 1 else ''), t)
    t = re.sub(r'\b(' + BOOKS + r')\. ([ivxlc]+): (?=\d)', r'\1. \2. ', t)       # Mal. iii: 14
    t = re.sub(r'\*A US\*\.', '*Ans*.', t)
    t = re.sub(r'\*Am\*\. ?1,', '*Ans*. 1.', t)
    t = re.sub(r'\*?\b(?:Alls|Alts|Alt|Atis|Aiis|A\)is|A lis|yins|Aus)\*?\.', '*Ans*.', t)               # Ans. 读成 Alls.／Alts.
    t = re.sub(r'\bL(?=[xvi]+\b)', 'l', t)                                  # 经文出处罗马数字首字母 l 读成 L：Ps. Lxxxix.
    t = re.sub(r'(?<=\d)(?:-|[-—] )(?=\d)', '–', t)                          # 起讫节号：17-19、28- 35 → 17–19
    t = re.sub(r'(?<![*\w])\*([ivxlc]+)\*(?=\.)', r'\1', t)                   # 经文出处里假斜体的罗马数字：Num. *xv*. 30
    t = re.sub(r'(?<![*\w])\*(' + BOOKS + r')\*(?=\. [ivxlc]+\.)', r'\1', t)          # 经卷名假斜体：*Mal*. i. 1
    t = re.sub(r'\b(' + BOOKS + r'), (?=[ivxlcIL][ivxlc]*\.)', r'\1. ', t)            # 经卷名后的点读成逗号：Num, xvi.
    t = re.sub(r'\b([ivxlc]+)\.(?=\d)', r'\1. ', t)                          # Rom. v.12 → v. 12
    t = re.sub(r'\b(' + BOOKS + r')(\.?) ([ivxlc]+), (?=\d)', r'\1\2 \3. ', t)   # 1 Cor. iii, 16 → iii. 16；Acts xxi, 13
    t = re.sub(r'(\*Use\* \d),', r'\1.', t)
    t = re.sub(r'^\*I\*\. (?=[A-Z])', '1\\. ', t)
    t = re.sub(r'^\*(I{1,3}|IV|V|VI{1,3}|IX|X)\*\. (?=[A-Z])', r'\1. ', t)          # 段首罗马序号误成斜体：*IV*. The                                # 段首序号 1 读成斜体 I
    t = re.sub(r'^IL\. (?=\*|[A-Z])', 'II. ', t)
    t = re.sub(r'^(?:Ill|in|IIT|IIl)\. (?=\*|[A-Z])', 'III. ', t)
    t = re.sub(r'^VY\. (?=\*|[A-Z])', 'V. ', t)
    t = re.sub(r'\bmerey\b', 'mercy', t)
    t = re.sub(r'\bhaying\b', 'having', t)
    t = re.sub(r'\bca(y)ill', 'cavill', t)
    t = re.sub(r'\bmerit is\b', 'meritis', t)
    t = re.sub(r'(?<=\w)\+(?=\s)', '', t)                                        # 脚注号读成 +：restless+
    t = re.sub(r'\bp[oc]+enitent', 'pœnitent', t)                                           # 段首罗马序号 II 读成 IL
    t = re.sub(r'(?<=[a-z])® (?=[a-z])', ' ', t)                                      # 脚注号读成 ®
    t = re.sub(r'(?<=[A-Za-z]) ?([;:])[1-9](?= [a-z])', r'\1', t)                    # 粘在分号后的脚注号：God ;1 if
    t = re.sub(r'(?<=[.?!’]) ”(?=\s|$)', '', t)                                      # 句末多出的孤立闭引号
    t = re.sub(r'(?<=[a-z])~(?=[a-z])', ' ', t)                                       # 字间 ~：inclining~his
    t = re.sub(r'\b[ZL]nar\.', 'Enar.', t)
    t = re.sub(r'\*Avug\.', '*Aug.', t)
    t = re.sub(r'\bin Oral\. (?=de )', 'in Orat. ', t)
    t = re.sub(r'\b(lib|cap|ver|sec|treat|part|serm|hom)\.?, (?=[ivxlc\d]+\b)', r'\1. ', t)   # treat, ii. → treat. ii.
    t = re.sub(r'\bObit, (?=Theod)', 'Obit. ', t)
    t = re.sub(r'\bsees\. (?=\d)', 'secs. ', t)
    t = re.sub(r'\b([Ss]ec), (?=\d)', r'\1. ', t)                                     # See sec, 2.
    t = re.sub(r'(?<=the ‘Guide to go to God,’ )see\. (?=\d)', 'sec. ', t)
    t = re.sub(r'\baffect us\b', 'affectus', t)
    t = re.sub(r'\btune\b(?= me\b)', 'tunc', t)
    t = re.sub(r'\bSeriptur', 'Scriptur', t)
    t = re.sub(r'(?<=[a-z ,])lib, (?=[ivxlc]+\.)', 'lib. ', t)                      # lib, viii. → lib. viii.
    t = re.sub(r'(\*(?:Object|Obj|Quest|Ans)\*),(?= \d)', r'\1.', t)
    t = re.sub(r'(?<=[,’] )&c,(?=\s|$)', '&c.', t)
    t = re.sub(r'(?<=[a-z]{3})\.(?=(?:the|is|and|of|to|in|that|way|was)\b)', ' ', t)   # notwithstanding.the、anger.is
    t = re.sub(r'\b(Ps|Psal)\. e(?=[xlvi]*\.)', r'\1. c', t)                 # Ps. ex. → cx.
    t = re.sub(r' _ ?', ' ', t)                                                 # 页面污点读成 _（and _plentifully）
    t = re.sub(r'\b([Hh])orn\.(?=,?\s*\d)', r'\1om.', t)                       # 讲道集 hom. 读成 horn.
    t = re.sub(r'(?<=[A-Za-z])\\"(?=[a-z])', 'v', t)                              # Da\"id
    t = re.sub(r'\b(?!(?:What|what|alas|Alas|O|Oh|Lo|Ah|how|How|Behold)!)([A-Za-z]{2,})! (?=[a-z])', r'\1 ', t)   # 脚注号读成 !：some! refer
    t = re.sub(r'\bLey\.(?= [ivxlc]+\.)', 'Lev.', t)
    t = re.sub(r'(?<=[a-z]) \*[Ii]\*(?=[’\'\s]|$)', '?', t)                   # 问号读成斜体 I：with God *I* It
    t = re.sub(r'\b[ivxc]*[iv]l[il]*(?=\.)', roman_l, t)                        # 罗马数字里 i 读成 l：vill. → viii.
    t = re.sub(r'\b(?:wy|yv|y)\.(?= \d)', 'v.', t)                                 # 罗马数字 v. 读成 wy.／y.（抽查全是 v.）
    t = re.sub(r'\bLe(?=x[xvi]*\.)', 'lx', t)                                  # Lexxvii. → lxxxvii.
    t = re.sub(r'^Use (?=\d)', '*Use* ', t)
    t = re.sub(r'\*Us\*\??(?= \d)', '*Use*', t)
    t = re.sub(r'\bDa(?:y|)id\b', 'David', t)
    t = re.sub(r'(?<= )-(?=[a-z])', '', t)                                      # 词前孤立短横：where -he will
    t = re.sub(r'(?<=[a-z]) - (?=[a-z])', ' ', t)                                  # 词间孤立短横（污点）：debtors - unto
    t = re.sub(r'\b(again|mo|fir|thi|wa)\.(st|s)\b', r'\1\2', t)                    # 词中多一个句点：again.st、fir.st
    t = re.sub(r'\bas\.are\b', 'as are', t)
    t = re.sub(r'(?<=[a-z]{4})@(?= )', 'd', t)
    t = re.sub(r'(?<=[a-z;,]) ° (?=[a-z])', ' ', t)                               # 字间脚注号残渣：disquietness ° of                                       # d 读成 @：measure@
    t = re.sub(r'’/—', '’—', t)
    t = re.sub(r'(?<=[a-z])~(?=\s|$)', '', t)
    t = re.sub(r'(?<=[a-z]) [~’}] (?=[a-zA-Z])', ' ', t)                              # 字间污点：saving ~ knowledge、the ’ holy、inward } disposition
    t = re.sub(r'(?<=[a-z]) : (?=[A-Z][a-z]+ [a-z])', ' ', t) if False else t
    t = re.sub(r'(?<=[a-z])\.(?=[A-Z][a-z])', '. ', t)
    t = re.sub(r'(?<=[a-z]{3})\. (?=when\b|where\b|which\b)', ' ', t) if False else t                             # 句点后缺空格
    t = re.sub(r'\bTam\b', 'I am', t)                                          # I am 粘成 Tam
    # 拉丁引文里的 æ 连字、c 读成 e：que → quæ、hune → hunc（只收不会与英文撞车的独立词）
    for a, b in (('que', 'quæ'), ('hune', 'hunc'), ('Hine', 'Hinc'), ('hee', 'hæc'), ('Heec', 'Hæc'), ('heec', 'hæc'),
                 ('Hee', 'Hæc'), ('heee', 'hæc'), ('justitiz', 'justitiæ'), ('justitie', 'justitiæ'), ('mew', 'meæ'), ('miserie', 'miseriæ'), ('haec', 'hæc'), ('erederem', 'crederem'), ('hunce', 'hunc'), ('sie', 'sic'), ('egrotum', 'ægrotum'), ('quse', 'quæ'), ('queedam', 'quædam'), ('Hierosolyme', 'Hierosolymæ')):
        t = re.sub(r'\b' + a + r'\b', b, t)
    t = re.sub(r'\bTwill\b', 'I will', t)
    t = re.sub(r'(?<=‘)IT(?= [a-z])', 'I', t)                                       # ‘IT will → ‘I will
    t = re.sub(r'(?<=[a-z]{3} )wp(?= (?:the|to|his|her|their|my|thy|our|your|a)\b)', 'up', t)   # up 读成 wp
    t = re.sub(r'\b([Tt])(?:ills|ins)\b(?= (?:serves|is|was|we|he|they|world|life|doth|must|psalm|verse|point|is))', r'\1his', t)
    t = re.sub(r'\bIcing', 'king', t)                                            # k 读成 Ic
    t = re.sub(r"(?:' )?«(?=[A-Z])", '‘', t)                                     # 开引号读成 «
    t = re.sub(r'(?<=[a-z] )«(?=[a-z])', '', t)                                  # 字间污点读成 «
    t = re.sub(r'(?<=[a-z])\. \.(?=\s|$)', '.', t)
    t = re.sub(r'(?<=\d)\.,$', '.', t)
    t = re.sub(r'(?<=\d\.) \?$', '', t)                                             # 段末节号后孤立问号                                          # 段末 20.,
    t = re.sub(r'\b(xx|xxi|xxii|xxiii|iii|ii|vi|vii|viii|ix|xi|xii|xiii)(?=,(?: where| and|\s*$))', r'\1.', t)   # 2 Kings xxii, → xxii.
    t = re.sub(r'(?<=[a-z])"(?=[a-z])', '', t)                                   # off"ered
    t = re.sub(r'\bb(?=x[xvi]*\.)', 'l', t)                                    # 罗马数字 l 读成 b：bxxiii.
    t = re.sub(r'\b([Ilxvc][xvic]*)L([xv])(?=[.,])', lambda m: m.group(1).replace('I', 'l') + 'i' + m.group(2), t)   # IxxxLx → lxxxix
    t = re.sub(r'\bI(?=[xvi]+\.)', 'l', t)                                     # Isa. Iv. 7 → lv.（核过 Isa. 55:7、60:3、Ps. 51:6）
    t = re.sub(r'\bXXX(?=[xvi]+\.)', 'xxx', t)
    t = re.sub(r'\b(' + BOOKS + r')[.,] in\. (?=\d)', r'\1. iii. ', t)          # Mal. in. 14 → iii.
    t = re.sub(r'\b(' + BOOKS + r')[.,] X(?=[xvi]*\. \d)', r'\1. lx', t)          # Ps. Xx. 6 → lxx.（l 丢了、x 大写）
    t = re.sub(r'([ivxlc]+\. \d+),(?=\d)', r'\1, ', t)                          # 68,74 → 68, 74
    t = re.sub(r'\bPs\. 1\. (?=\d)', 'Ps. l. ', t)                              # 诗 50 篇：l 读成 1（诗 1 篇写作 Ps. i.）
    t = re.sub(r'\b(Kings|Sam|Chron|Cor|Pet|Thes|Tim|John|Rom|Gal|Eph|Phil|Col|Heb|Gen|Exod|Isa|Jer|Mat|Luke|Acts|Rev)\.? 1\. (?=\d)',
               lambda m: m.group(1) + ('. ' if m.group(1) not in ('Kings', 'John', 'Luke', 'Acts') else ' ') + 'i. ', t)   # Rom. 1. 29 → i. 29
    t = re.sub(r'\bPs\. hai\.', 'Ps. lxiii.', t)
    t = re.sub(r'\bloying', 'loving', t)
    t = re.sub(r'\b([Mm])oy(est|eth|ed|ing)\b', r'\1ov\2', t)                   # tesseract v→y：moyest
    t = re.sub(r'\b(' + ABBR_BOOKS + r') (?=[ivxlc]+\. ?\d)', r'\1. ', t)          # 缩写经卷名后缺点：1 Pet ii. 5
    t = re.sub(r'(?<![*\w])\*(' + FALSE_IT + r')\*(?![*\w])', false_italic, t)
    t = re.sub(r'(?<![\d.,:;] )(?<![\d])\b0(?= (?:my|Lord|God|thou|ye|that|how|the|what|Israel|Jerusalem|man|LORD)\b)', 'O', t)   # 呼格 O 读成 0
    return re.sub(r' {2,}', ' ', t).strip()


def assemble(lo, hi, tcp, left_log):
    """lo–hi 页 → 段落流 [{'kind': body/note/head/verse, 'text', 'page'}]，跨栏跨页续段已并。"""
    pages = n.load()
    out = []
    for i in range(lo, hi + 1):
        pp = n.printed_page(i)
        first_on_page = True
        for bi, b in enumerate(pages[i]):
            if n.kind(b) != 'text':
                continue
            wit = n.tess(i, bi, b)
            merged = n.merge_block([p['text'] for p in b['pars']], wit, judge=judge_tcp(tcp, left_log))
            for j, p in enumerate(b['pars']):
                t = clean(merged[j], wit)
                t = re.sub('^Ver\\. ' + n.IT_ON + r'li\. ', 'Ver. 14. ' + n.IT_ON, t)   # p.91 节号读进了斜体（影像核：14）
                plain = t.replace(n.IT_ON, '').replace(n.IT_OFF, '').strip()
                if not plain:
                    continue
                if p['fs'] and p['fs'] < 6.5 and not sec_match(t):          # 小节标题偶尔被判成小字号
                    out.append(dict(kind='note', text=t, page=pp))
                    continue
                if p['fs'] >= 9:                                  # 卷首大字（书名等）
                    out.append(dict(kind='big', text=t, page=pp))
                    continue
                new = 'startIndent' in p['attrs'] or (re.match(r'Ver[.,]?\s*[\dIl]', plain) or sec_match(t))
                anchor = f'<span class="{P}-pb" id="p{pp}" data-p="{pp}"></span>' if (first_on_page and pp) else ''
                first_on_page = False if anchor or not first_on_page else first_on_page
                prev = next((x for x in reversed(out) if x['kind'] == 'body'), None)
                if not new and j == 0 and prev is not None:       # 栏首／页首无首行缩进 → 上一段的续行
                    pt = prev['text']
                    if pt.rstrip(n.IT_OFF).endswith('-') and plain[:1].islower():
                        prev['text'] = pt.rstrip(n.IT_OFF)[:-1] + pt[len(pt.rstrip(n.IT_OFF)):] + anchor + t
                    else:
                        prev['text'] = pt + ' ' + anchor + t
                    continue
                out.append(dict(kind='body', text=anchor + t, page=pp))
    return out


BOUNDS = [(9, '1', '1–2'), (19, '3', '3'), (23, '4', '4'), (29, '5', '5'), (38, '6', '6'), (44, '7', '7'), (51, '8', '8'),
          (57, '9', '9'), (68, '10', '10–11'), (78, '12', '12–13'), (91, '14', '14'), (100, '15', '15'), (105, '16', '16'),
          (114, '17', '17'), (122, '18', '18'), (124, '19', '19')]
# 小节标题：tesseract 常把 Sec. 读成 See.／Sect.，号可能读坏（III ← 111）或丢掉；标题一律以「Of」起头，Of 有时不在斜体里
SEC = re.compile(r'^(S[eo][ec]t?[.,]?\s*[\dIlSGO]*[.,]?\s*)(Of\s+)?' + n.IT_ON + r'(.*?)' + n.IT_OFF + r'\s*(.*)$', re.S)


def sec_match(t):
    m = SEC.match(t)
    if not m or not (m.group(2) or re.match(r'\s*Of\b', m.group(3))):
        return None
    return m
VER = re.compile(r'^(?:<span[^>]*></span>)?(Ver[.,]?\s*[\dILl]+(?:,\s*\d+)*[.,]?\s*)' + n.IT_ON + r'(.*?)' + n.IT_OFF + r'\s*(.*)$', re.S)


def render(stream):
    """段落流 → markdown；小节标题 h4、经文框、页末注。"""
    body, notes = [], []
    for x in stream:
        t = x['text']
        if x['kind'] == 'note':
            notes.append(md(t))
            continue
        if x['kind'] == 'big':
            if len(re.sub(r'\W', '', t)) <= 2:                    # 书帖签名（页底单字母）被判成大字号
                continue
            body.append(f'<p class="{P}-quote">{md(t)}</p>')
            continue
        anchor = ''
        m0 = re.match(r'^(<span class="[^"]+-pb"[^>]*></span>)', t)
        if m0:
            anchor, t = m0.group(1), t[m0.end():]
        m = sec_match(t)
        if m and re.fullmatch(r'[.,;:]\s*', m.group(4)):         # 斜体后只剩句末标点：并进标题，别单成一段
            t = t[:m.start(4)].rstrip()
            m = sec_match(t)
        if m:
            num = re.sub(r'\D', '', re.sub(r'^S[eo][ec]t?[.,]?', '', m.group(1)).replace('l', '1').replace('I', '1')
                         .replace('S', '5').replace('G', '6').replace('O', '0')) or '?'
            body.append(f'#### {anchor}<span class="{P}-sec">Sec. {num}.</span> '
                        f'{md(n.IT_ON + (m.group(2) or "") + m.group(3) + n.IT_OFF)}')
            if m.group(4).strip():
                body.append(md(m.group(4)))
            continue
        m = VER.match(t)
        if m:
            tail = m.group(3) if re.fullmatch(r'[.,;:!?]\s*', m.group(3)) else ''
            body.append(f'<div class="{P}-text" markdown="1">\n\n{anchor}**{md(m.group(1)).strip()}** '
                        f'{md(n.IT_ON + m.group(2) + n.IT_OFF)}{tail.strip()}\n\n</div>')
            if m.group(3).strip() and not tail:
                body.append(md(m.group(3)))
            continue
        body.append(anchor + md(t))
    # 段落被按行切开（栏底、跨栏）：上段无句末标点、下段小写起头 → 接上（old-book-ocr §3.1，两条件都要）
    merged = []
    for b in body:
        b = re.sub(r'^\. (?=[A-Z])', '', b)
        if merged and not merged[-1].startswith(('<', '#', '**')) and not b.startswith(('<', '#', '**', '*Use*')) \
                and (re.search(r'[A-Za-z,]$', merged[-1]) and re.match(r'[a-z]', b)
                     or merged[-1].endswith(',') and re.match(r'[‘a-z]', b)):
            merged[-1] += ' ' + b
        else:
            merged.append(b)
    merged = [re.sub(r'(?<=\d),$', '.', b) if not b.startswith(('<', '#')) else b for b in merged]   # 段末节号后的逗号是句号
    merged = [re.sub(r'^\. (?=[A-Z])', '', b) for b in merged]                                      # 段首孤立句点（标题后的污点）
    merged = [re.sub(r'(?<=[.?’]) (?:[:;,]|“7)$', '', b) for b in merged]                                  # 段末句号后的孤立冒号（污点）
    out = '\n\n'.join(merged)
    # 同一行里排着几条短注（‘… sec. 20. 2 See … 3 Lege …’）：按脚注号拆开
    split = []
    for b in notes:
        split += re.split(r'(?<=[.)*]) +[2-9] +(?=See |Sec\.|Lege |Of |[A-Z][a-z]+ [a-z])', b)
    notes = split
    joined = []
    for b in [x for x in notes if x.strip() and not re.fullmatch(r'\s*[A-Z]\s*', x)]:   # 书帖签名（X、U 2）                                              # 跨页的脚注：上条无句末标点、下条小写起头 → 接上
        if joined and re.search(r'[A-Za-z,;]$', joined[-1]) and re.match(r'[a-z]', b):
            joined[-1] += ' ' + b
        else:
            joined.append(b)
    notes = joined
    if notes:
        out += f'\n\n<div class="{P}-notes" markdown="1">\n\n<p class="{P}-notes-h">Notes</p>\n\n' + \
               '\n\n'.join(notes) + '\n\n</div>'
    return out


def renumber(U):
    """小节号是连续的（1–128）：读坏的号（? 或与前后不接），前一个是 k−1、后一个是 k+1 时改成 k。"""
    rx = re.compile(r'(gg-sec">Sec\. )([^.<]*)(\.</span>)')
    seq = [(ui, m) for ui, u in enumerate(U) for m in rx.finditer(u['md'])]
    nums = [int(m.group(2)) if m.group(2).isdigit() else None for _, m in seq]
    fix = {}
    for k in range(len(nums)):
        prev = nums[k - 1] if k else 0
        nxt = nums[k + 1] if k + 1 < len(nums) else None
        if nums[k] != (prev or 0) + 1 and prev is not None and nxt == prev + 2:
            fix[k] = prev + 1
            nums[k] = prev + 1
    for k in sorted(fix, reverse=True):
        ui, m = seq[k]
        md_ = U[ui]['md']
        U[ui]['md'] = md_[:m.start(2)] + str(fix[k]) + md_[m.end(2):]
        print(f'  小节号 {m.group(2)!r} → {fix[k]}')
    missing = sorted(set(range(1, 129)) - set(nums))
    if missing:
        print('⚠️ 缺小节号：', missing)


GAP = {'@H': ('Hebrew', '希伯来文'), '@G': ('Greek', '希腊文')}


def gap(kind):
    en, zh = GAP[kind]
    return (f'<span class="{P}-gap" title="{en} in the 1868 edition, not read by OCR（原书此处是{zh}，OCR 读不出）">'
            f'〈{en}〉</span>')


def apply_fixes(text, f=None):
    """看图判读表：每行「原串<TAB>改成」，原串须在本页唯一；改成里的 @H／@G 展开成希伯来文／希腊文缺口；\\n 是换行。"""
    f = f or RAW / 'fixes.tsv'
    if not f.exists():
        return text
    notes = []
    for line in f.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        old, new = (x.replace('\\n', '\n') for x in line.split('\t'))
        key = (str(f), old)
        FIXHITS.setdefault(key, 0)
        old = re.sub(r'@[HG]', lambda m: gap(m.group()), old)       # 原串里的 @H/@G 指已有的缺字块
        c = text.count(old)
        if c > 1:
            FIXHITS[key] += 100                                     # 不唯一：报警
            continue
        if c == 1:
            if new.startswith('@NOTE '):                            # 混进正文的栏底脚注：摘出，挪到页末 Notes
                note, _, keep = new[6:].partition(' @@ ')              # 「@NOTE 注文 @@ 原处留下的文字」
                text = text.replace(old, keep or ('\n\n' if old.startswith('\n\n') and old.endswith('\n\n') else ''))
                notes.append(note)
            else:
                text = text.replace(old, re.sub(r'@[HG]', lambda m: gap(m.group()), new))
            FIXHITS[key] += 1
    if notes:
        block = '\n\n'.join(notes)
        if f'<p class="{P}-notes-h">Notes</p>' in text:
            text = re.sub(r'\n*</div>\s*$', '\n\n' + block + '\n\n</div>', text.rstrip(), count=1)
        else:
            text = text.rstrip() + f'\n\n<div class="{P}-notes" markdown="1">\n\n<p class="{P}-notes-h">Notes</p>\n\n' \
                   + block + '\n\n</div>'
    return text


def fix_report():
    for (f, old), c in FIXHITS.items():
        if c != 1:
            print(f'⚠️ 判读表条目命中 {c if c < 100 else "多"} 次：{Path(f).parent.name} {old!r}')


FIXHITS = {}


def main():
    tcp = tcp_index()
    left_log = []
    stream = assemble(BODY[0], BODY[1], tcp, left_log)
    # 按分界表切页（印本页码, OCR 读出的节号, 页标签）：古治第 2 节讲在第 1 节下、第 13 节讲在第 12 节下，第 10–11 节合讲；
    # 第 17 节开头先把 17–19 节一并引出，第 18、19 节在第 122、124 页才各自展开；第 11、16、19 节中途重引半节经文当小标题。
    # 表外的「Ver.」段一律只当小标题（经文框），不起新页。
    units, cur, verse, todo = [], [], 'intro', list(BOUNDS)
    for x in stream:
        plain = re.sub(r'<[^>]+>', '', x['text']).replace(n.IT_ON, '').replace(n.IT_OFF, '').strip()
        m = re.match(r'Ver[.,]?\s*(\S+?)[.,\s]', plain) if x['kind'] == 'body' else None
        if m and todo and x['page'] == todo[0][0] and m.group(1).strip('.') == todo[0][1]:
            if cur:
                units.append((verse, cur))
            cur, verse = [], todo.pop(0)[2]
        cur.append(x)
    units.append((verse, cur))
    assert not todo, todo
    fronts = []
    for slug, en, zh, a, b in FRONT:
        fronts.append(dict(slug=slug, title=en, zh=zh, md=apply_fixes(render(assemble(a, b, tcp, left_log)))))
    U = []
    for verse, xs in units:
        pg = [x['page'] for x in xs if x['page']]
        U.append(dict(verse=verse, part=None, pages=(min(pg), max(pg)) if pg else None, contents=[],
                      md=apply_fixes(render(xs)), slug='introduction' if verse == 'intro' else f'v{verse.replace("–", "-")}',
                      name='Introduction' if verse == 'intro' else None))
    fix_report()
    renumber(U)
    vs = [u['verse'] for u in U]
    print('经节页：', vs)
    (RAW / 'disagree_left.tsv').write_text('\n'.join('\t'.join(x) for x in left_log) + '\n', encoding='utf-8')
    tot = bad = 0
    for u in U:
        b, c = n.nonwords(re.sub(r'<[^>]+>', ' ', u['md']))
        tot += c
        bad += len(b)
    print(f'正文 {tot} 词，残余非词 {bad}（{bad / tot:.2%}）；未决的真词互换 {len(left_log)} 处')
    c = dict(CFG, about_en=ABOUT_EN, about_zh=ABOUT_ZH, omitted_en='', omitted_zh='', about_full=True)
    tp.write_layouts('gouge-psalm116', c, force='--layouts' in sys.argv)
    tp.publish('gouge-psalm116', c, fronts, U, [], {}, ROOT / 'gouge' / 'psalm116', '/gouge/psalm116/', RAW)


ABOUT_EN = ("Gouge, for forty-five years minister of St Anne's, Blackfriars, published this commentary on Psalm 116 in 1632 "
            "and dedicated it to Robert, Lord Rich, Earl of Warwick, and to his parishioners. The text given here is that of "
            "the Edinburgh reprint of 1868 (Nichol's Series of Commentaries), read by OCR from the Princeton copy "
            "(Internet Archive davidsblessedman00smit) and checked against a second, independent OCR, against the 1632 "
            "edition where its keyed transcription survives (EEBO-TCP A01981, which lacks about a third of the book), "
            "and against the page images. The opening sections on the whole psalm and each verse are one page; "
            "Gouge's 128 numbered sections are given as headings, and the notes at the foot of the 1868 pages are "
            "collected at the end of each page. The page numbers of the 1868 edition are marked in the text. Hebrew words, "
            "which OCR cannot read, are marked in red. OCR errors still remain, chiefly in the italic passages (verse "
            "texts and section headings); they are being corrected against the page images.")
ABOUT_ZH = ("古治在伦敦黑衣修士区圣安妮堂牧会四十五年，1632 年出版这部诗篇 116 篇注释，献给沃里克伯爵罗伯特·里奇勋爵及本堂会众。"
            "本站正文据 1868 年爱丁堡 Nichol《清教徒注释丛书》重印本，用普林斯顿藏本的扫描件（IA davidsblessedman00smit）OCR 识读，"
            "并与另一份独立 OCR、1632 年原版的录入本（EEBO-TCP A01981，缺全书约三分之一）及页面影像对照校过。"
            "开头论全篇的几节一页，每节经文一页；古治全书编号的 128 小节作小标题，1868 年版页脚的注收在各页之末；文中标出 1868 年版页码。"
            "希伯来文 OCR 读不出，以红字标出。目前仍有 OCR 错误，主要在斜体段落（经文与小节标题），正在对照页面影像逐页校正。")

if __name__ == '__main__':
    main()
