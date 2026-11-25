#!/usr/bin/env python3
"""卡里尔缺部 OCR：抽章实读后的全书同类清理（old-book-ocr §4.5 第 4 步）。排在 caryl_ocr_manual.py 之后（人工改正表是照上下文纠错之后的文字记的，清理若排在前面会先改掉原串的一部分，改正表就对不上）。

    /usr/bin/python3 scripts/caryl_ocr_sweep.py              # 试跑：每条规则命中数与样例
    /usr/bin/python3 scripts/caryl_ocr_sweep.py --apply      # 落到各部 fixed/；改动记 caryl_raw/job_ocr/sweep.tsv

规则来自 2026-11-25 抽读第 9 部 31:7–8 一段（25 页，记错 235 条，平均每页约 12 处）。每条都只在纯文本上匹配，
不跨标签（旁注、页码锚点、存疑标记、经文框标签都不碰）：

  split   词中断开：相邻两截拼起来是本书 ≥ 5 次的词，且至少一截不是词，或后一截是常见后缀
          （direct ly、end lesse、out ward、unjust ly、oc asion）
  job     Job 读坏：Tob/fob/Sob/Jub/Iob/Jeb（含所有格 s）→ Job；小写 job 前面不是 a/the/his 时 → Job
  way     冠词、物主代词、形容词之后的 may/nay/var/mav → way（「the may」「good may」）；不碰 that/this/which may（情态动词）
  modal   人称代词之后的 mill/mil → will，mould → would，mas/vas → was，vere/mere → were
  saith   faith 前是人名（Job、David、God、Christ、the Lord…）或后是人名、he、the Lord → saith（长 s 读成 f）
  of      独立的 ef → of；er → or（两边都是英文词）
  tis     'Tis 开引号读错：「"Tis」「“ Tis」「“Tis」→「'Tis」
  isa     书卷缩写读坏：I/a. → Isa.，P/al. → Psal.，Plal. → Psal.
  ——第 2 轮（第 9 部 31:9–12，44 页）补：Tis 撇号读丢（ofx「ofit→of it」第 3 轮撤回：原书连排）、fin→sin、fh-→sh-、bis/bim→his/him、
          代词后 hill→will、mould not→would not、(I Cor.→(1 Cor.、(Ter.→(Jer.、(Hof.→(Hos.、(faith the text→(saith
  ——第 3 轮（第 6 部 21:30–31）补：mw（斜体 w 读成 m：主语后 mas/mere/mill/mould、the mise/mord、mbo/Nho/H'ho→who）、
          shall（sall/spall/spalt/sual）、(Per.→(Jer.、(Plal.→(Psal.、(Isa-→(Isa.、句首 Te→Ye、junk
  ——第 4 轮（第 4 部 11:4–6）补：pronI（l will→I will、Iam→I am、I'have→I have）、fs（fo/fay/fome/fuch→so/say/some/such）、
          ot→of、1Cor.→1 Cor.、«» 噪点、页顶页眉残片（Vers.〔节号旁注〕）
  ——第 5 轮（第 6 部 21:27–29）补：wh（W'hat/u'hat/n'hen→What/when）、jf（femes/facob/ferusalem→Jewes/Jacob/Jerusalem）、
          sob→Job、句中 Te→Ye、(Job. N.N)→(Joh. N.N)（按 KJV 引文比对）
  ——第 6 轮（第 4 部 11:15–16）补：Tou→You、Tea→Yea、句首 l→I、Ged/Gcd→God、osten→often、chap. I0.→10.、旁注插在词中（MARGIN_SPLIT）（整段乱码：书末花饰、横线、单成一段的签名）、段首「- 」「+ 」噪点（会被排成列表）
  head    漏进正文的页眉（「Chap. 31. An Exposition upon the Booke of JOB. Vers. 7.」）删掉
"""
import argparse
import collections
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import caryl_ocr_ctx as C  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'caryl_raw' / 'job_ocr'
PARTS = ('p4', 'p6', 'p82', 'p9')
UNI = C.UNI
SUFFIX = {'ly', 'lesse', 'nesse', 'ward', 'wards', 'ing', 'ed', 'ment', 'ness', 'ful', 'full', 'ous'}
NAMES = r'(?:Job|David|God|Christ|Moses|Paul|Peter|Solomon|Isaiah|Jeremiah|Elihu|Eliphaz|Bildad|Zophar|the Lord|the Prophet|the Apostle|he|she|they|hee)'
DETS = r'(?:the|a|good|his|my|their|our|your|her|its|narrow|right|wrong|same|thy|thine|mine|old|new|plaine|straight|evill|crooked)'


def rules():
    R = []
    # job
    R.append(('job', re.compile(r'\b(?:Tob|fob|Fob|Sob|sob|Jub|Iob|Jeb|Ieb|lob|Iub)([\'’]?s?)\b'), lambda m: 'Job' + m.group(1)))   # sob：第 5 轮
    R.append(('job', re.compile(r'(?<!\ba )(?<!\bthe )(?<!\bhis )\bjob(\'?s?)\b'), lambda m: 'Job' + m.group(1)))
    # way
    R.append(('way', re.compile(rf'(?<!nay to )(?<!yea to )\b({DETS}) (?:may|nay|var|mav)\b(?! be\b)'), lambda m: m.group(1) + ' way'))   # 「yea to their yea, and nay to their nay」不碰
    R.append(('way', re.compile(r'\b(out of (?:the|that|his|their|my) )(?:may|nay|man|var)\b'), lambda m: m.group(1) + 'way'))
    # modal
    R.append(('modal', re.compile(r'\b(I|we|wee|he|hee|they|ye|yee|you|thou|she|it|who|which) (mill|mil|mould|mas|vas|vere|mere)\b'),
              lambda m: m.group(1) + ' ' + {'mill': 'will', 'mil': 'will', 'mould': 'would', 'mas': 'was', 'vas': 'was',
                                            'vere': 'were', 'mere': 'were'}[m.group(2)]))
    # saith
    R.append(('saith', re.compile(rf'\b({NAMES}) faith\b'), lambda m: m.group(1) + ' saith'))
    R.append(('saith', re.compile(rf'([,;(] ?)faith (?={NAMES}\b)'), lambda m: m.group(1) + 'saith '))
    # of / or
    R.append(('of', re.compile(r'(?<=[a-z] )ef(?= [A-Za-z])'), lambda m: 'of'))   # 「wickednes ef Nabal」
    R.append(('of', re.compile(r'(?<=[a-z] )er(?= [a-z])'), lambda m: 'or'))
    # 'Tis
    R.append(('tis', re.compile(r'(?<=[.;:?!])["“”]\s?Tis\b'), lambda m: " 'Tis"))   # 「heaven." Tis」：句末后补回空格
    R.append(('tis', re.compile(r'["“”]\s?Tis\b'), lambda m: "'Tis"))
    # 书卷缩写
    R.append(('isa', re.compile(r'\bI/a\.'), lambda m: 'Isa.'))
    R.append(('isa', re.compile(r'\bP[/l]al\.'), lambda m: 'Psal.'))
    # —— 第 2 轮（2026-11-25，第 9 部 31:9–12 实读 44 页）补的几类
    # of 与后词粘连（ofit、ofthe）：第 3 轮看图证实原书本就连排（p.813「repayment ofit」），照录，不再拆（第 2 轮的 ofx 规则撤回）
    # 'Tis 撇号读丢：句中独立的 Tis / tis（排在上面 tis 规则之后，引号形的已归一）
    R.append(('tis', re.compile(r'(?<![’\'‘"“\w])Tis\b'), lambda m: "'Tis"))
    R.append(('tis', re.compile(r"(?<=\s)['’‘] (?=tis\b)"), lambda m: '’'))
    R.append(('tis', re.compile(r'((?:[,;:(]|\b(?:and|but|so|when|thus|as|yet|because|that|for|or|know|here|therefore)) )tis\b', re.I),
              lambda m: m.group(1) + "’tis"))           # 「wait tis my change come」是 till，不碰
    # 长 s 读成 f：fin/finne/finner…（本书这几部讲不到鱼鳍）；fhall/fhould/fhew… → sh-
    R.append(('fin', re.compile(r'\bfin(|ne|s|nes|full|fully|fulnesse|fullnesse|ner|ners|ning|ned)\b'), lambda m: 'sin' + m.group(1)))
    R.append(('fh', re.compile(r'\bfh(?=[a-z])'), lambda m: 'sh'))
    # bis/bim → his/him（「a five-fold bis」那一处另说，不碰）
    R.append(('bis', re.compile(r'(?<!fold )\bbis\b'), lambda m: 'his'))
    R.append(('bis', re.compile(r'\bbim\b'), lambda m: 'him'))
    # 人称代词、God 之后的 hill → will；mould not/be/have → would（「dust and mould of the Earth」不动）
    R.append(('modal', re.compile(r'\b(I|he|hee|we|wee|they|ye|yee|you|thou|it|who|God) hill\b'), lambda m: m.group(1) + ' will'))
    R.append(('modal', re.compile(r'\bmould(?= (?:not|be|have)\b)'), lambda m: 'would'))
    # 书卷：(I Cor. → (1 Cor.；(Ter. → (Jer.；(Hof. → (Hos.
    R.append(('isa', re.compile(r'\(I (?=(?:Cor|Tim|Sam|King|Kings|Chron|Pet|Joh|Thes|Thess)\.)'), lambda m: '(1 '))
    R.append(('isa', re.compile(r'\(Ter\.'), lambda m: '(Jer.'))
    R.append(('isa', re.compile(r'\(Hof\.'), lambda m: '(Hos.'))
    # (faith the text / the Evangelist / one … → (saith
    R.append(('saith', re.compile(r'\(faith (?=the |one )'), lambda m: '(saith '))
    # —— 第 3 轮（2026-11-26，第 6 部 21:30–31 实读 17 页）补的几类
    # m 读成 w 的前半（斜体 w 读成 m）：mas/mere/mill/mould 在主语之后（名词主语也算：age mas、God mill），
    # mise/mord 在冠词、物主代词之后；「same mould」「the mould of」名词不碰
    SUBJ = r'(?:[A-Z][a-z]+|I|we|wee|he|hee|she|they|ye|yee|you|thou|it|who|which|that|there|this|age|man|men|God|Lord|all|none|one)'
    R.append(('mw', re.compile(rf'(?<!\w)(?!(?:Every|Each|Any|No|A|The)\b)({SUBJ}) mas\b'), lambda m: m.group(1) + ' was'))   # 「Every mas」是 man
    R.append(('mw', re.compile(rf'\b({SUBJ}) mere\b(?! (?:man|men|nothing|words?|shew|creatures?|trifles?|forms?|formality)\b)'), lambda m: m.group(1) + ' were'))
    R.append(('mw', re.compile(rf'\b({SUBJ}) mill\b(?! (?:of|in|and)\b)'), lambda m: m.group(1) + ' will'))
    R.append(('mw', re.compile(rf'\b({SUBJ}) mould\b(?= (?:\w+ly )?[a-z]+(?:e|en|ed|eak|ome|ing)?\b)(?! (?:of|and|in)\b)'), lambda m: m.group(1) + ' would'))
    R.append(('mw', re.compile(r'\b(the|his|my|thy|our|your|their|her|a|no|any|this|that|by-) ?mord\b'),
              lambda m: m.group(1) + ('' if m.group(1).endswith('-') else ' ') + 'word'))
    R.append(('mw', re.compile(r'\b(the|a|no) mise\b'), lambda m: m.group(1) + ' wise'))     # 「my mise」是 my wife，不碰
    R.append(('mw', re.compile(r'\bmbo\b|\bMbo\b|\bNho\b|\bvvho\b|\b[HhnNw][\'’]ho\b'),
              lambda m: 'Who' if m.group(0)[0].isupper() and m.group(0)[0] not in 'Mm' else ('Who' if m.group(0) == 'Mbo' else 'who')))
    # 长 s 读坏的 shall：sall / spall / spalt / sual
    R.append(('shall', re.compile(r'\b(sall|spall|spalt|sual)\b'), lambda m: 'shall'))
    # 书卷：(Per. → (Jer.、(Plal. → (Psal.、(Isa- → (Isa.
    R.append(('isa', re.compile(r'\(Per\b'), lambda m: '(Jer'))
    R.append(('isa', re.compile(r'\(Plal\.'), lambda m: '(Psal.'))
    R.append(('isa', re.compile(r'\(sal\.(?=\s?\d)'), lambda m: '(Psal.'))      # 第 7 轮
    R.append(('isa', re.compile(r'\(Isa-'), lambda m: '(Isa.'))
    # 句首 Te → Ye（斜体 Y 读成 T）
    R.append(('te', re.compile(r'(?<=[.;:?!(] )Te (?=(?:have|are|shall|will|know|say|heard|should|may|did|do|see|be|were|that|cannot|must)\b)'), lambda m: 'Ye '))
    # shem → shew（「shem thes hom」）
    R.append(('mw', re.compile(r'\bshem\b'), lambda m: 'shew'))
    # —— 第 4 轮（第 4 部 11:4–6）：页边阴影读成的「«」「»」（本书英文正文不用书名号式引号）；页边阴影读成的段首「(」只逐条改
    R.append(('guil', re.compile(r'(?<=\w)[«»](?=\w)'), lambda m: ''))                     # 词中：a«b → ab
    R.append(('guil', re.compile(r' ?[«»] ?'), lambda m: ' '))                               # 其余：并成一个空格（行首行尾的空格由 sweep_md 收拾）
    # —— 第 4 轮（第 4 部 11:4–6 实读 36 页）补的几类
    # 代词 I 读成 l（「l will」「l have」）；粘连「Iam/Ihave/Iwill…」；撇号噪点「I'have」「l'am」
    R.append(('pronI', re.compile(r"\b[Il]['’](am|have|was|had)\b"), lambda m: 'I ' + m.group(1)))
    R.append(('pronI', re.compile(r'\bI(am|have|had|will|was|shall|would|know)\b'), lambda m: 'I ' + m.group(1)))
    R.append(('pronI', re.compile(r'(?<=[a-z,;:)] )l(?= (?:am|have|had|was|will|would|shall|should|can|could|do|did|know|say|said|bear|grant|passe|cannot|thought|see|must|may)\b)'),
              lambda m: 'I'))
    # 长 s 读成 f：fo/fay/fome/fuch（本书无此词；fee、fin 另有规则或是真词，不碰）
    R.append(('fs', re.compile(r'\b(fo|fay|fome|fuch|Fo|Fay|Fome|Fuch)\b'), lambda m: 's' + m.group(1)[1:] if m.group(1)[0] == 'f' else 'S' + m.group(1)[1:]))
    # of 读成 ot（后接限定词时）
    R.append(('of', re.compile(r'(?<=[a-z] )ot(?= (?:the|his|their|God|it|a|an|this|that|our|my|thy|your|her|them|him|all)\b)'), lambda m: 'of'))
    # 书卷数字后补空格：1Cor. → 1 Cor.
    R.append(('isa', re.compile(r'\b([12])(Cor|Joh|Tim|Sam|Pet|King|Kings|Thes|Thess|Chron)\.'), lambda m: m.group(1) + ' ' + m.group(2) + '.'))
    # —— 第 5 轮（第 6 部 21:27–29 实读 23 页）补的几类
    # 斜体 W 读成 W'／u'／n'／N'／Iv'（W'hat、u'hat、n'hen、Iv'here）
    def wh_any(m):
        lead, rest = m.group(1), m.group(2)
        if lead[0] == 'I' and len(lead) == 1 and rest in ('ope', 'id', 'old', 'ear', 'ave', 'ad', 'eard', 'ate'):
            return 'I h' + rest                                        # I'hope／I'hid／I'hold：I ＋ 词
        if len(rest) >= 2 and UNI.get('wh' + rest, 0) >= 3:
            up = lead[0] in 'WNIU' and not re.search(r'[a-z,;]\s$', m.string[max(0, m.start() - 2):m.start()])
            return ('W' if up else 'w') + 'h' + rest
        return m.group(0)
    R.append(('wh', re.compile(r"\b([uUwWnNI]v?)['’]h([a-z]+)\b"), wh_any))      # 第 6 轮复查：wherefore、wheremithall、wheat
    R.append(('wh', re.compile(r"\b([uUwWnNI]v?)['’](hat|here|hen|ho|hich|hom|hose|hy)\b"),
              lambda m: ('W' if m.group(1)[0] in 'WNIU' and not re.search(r'[a-z,;]\s$', m.string[max(0, m.start() - 2):m.start()]) else 'w')
              + m.group(2)))
    # 斜体 J 读成 f：femes/feremy/ferusalem/facob/foseph → J…；sob → Job（「sob」在本书不是词）
    R.append(('jf', re.compile(r'\b(femes|feremy|feremiah|feremie|ferusalem|facob|foseph|fosephs|fews|fewes)\b'),
              lambda m: 'J' + {'femes': 'ewes'}.get(m.group(1), m.group(1)[1:])))
    # 句中 Te → Ye（逗号、分号后）
    R.append(('te', re.compile(r'(?<=[,;:] )Te (?=(?:have|are|shall|will|know|say|heard|should|may|did|do|see|be|were|cannot|must)\b)'), lambda m: 'Ye '))
    # —— 第 6 轮（第 4 部 11:15–16 实读 21 页）补的几类
    R.append(('te', re.compile(r'\bTou (?=[a-z])(?!saith)'), lambda m: 'You '))
    R.append(('te', re.compile(r'\bTe (?=[a-z])'), lambda m: 'Ye '))   # 第 6 轮复查：「(Exod.19.6.) Te shall」「thus:⏎⏎Te ought」
    R.append(('te', re.compile(r'(?:(?<=[.;:,?!(] )|(?<=\n)|^)Tea\b'), lambda m: 'Yea'))
    R.append(('pronI', re.compile(r'(?<=[.;:?!] )l (?=[a-z])'), lambda m: 'I '))
    R.append(('god', re.compile(r'\b(Ged|Gcd)\b'), lambda m: 'God'))
    R.append(('fs', re.compile(r'\bosten\b'), lambda m: 'often'))
    R.append(('isa', re.compile(r'\b((?:chap|Chap|vers|ver|Isa|Psal)\.?\s?)I[Oo0]\.'), lambda m: m.group(1) + '10.'))
    # 复查补：代词 I 与后面的词粘连（Irejoyced、Igave）：I＋词 不是词、后半截是常见词才拆；anto → unto
    R.append(('pronI', re.compile(r'(?<![-\w])I([a-z]{3,})\b'),
              lambda m: 'I ' + m.group(1) if not UNI.get('i' + m.group(1), 0) and UNI.get(m.group(1), 0) >= 20 else m.group(0)))
    R.append(('of', re.compile(r'\banto\b'), lambda m: 'unto'))
    # —— 第 7 轮（第 9 部 31:19–21 实读 22 页）补：斜体 th／w 读坏
    R.append(('th', re.compile(r'\b(ihe|ibe|tbe|rhe)\b'), lambda m: 'the'))
    R.append(('th', re.compile(r'\b(ibat|tbat)\b'), lambda m: 'that'))
    R.append(('th', re.compile(r'\brhen\b'), lambda m: 'when'))
    R.append(('mw', re.compile(r'\b(my|thy|his|her|their|our|your|mine|thine|own|owne|one) (omne|onne|oune|omn)\b'), lambda m: m.group(1) + ' owne'))
    R.append(('mw', re.compile(r'\b(I|he|she|they|we|ye|who) sam\b'), lambda m: m.group(1) + ' saw'))
    R.append(('mw', re.compile(r'\b(for|of|in|no|their|his|our|my|killing|prevent their) mant\b'), lambda m: m.group(1) + ' want'))
    R.append(('fs', re.compile(r'\b((?:on|of) (?:my|his|their|our|your|the|that|this|other|every|one)) fide\b'), lambda m: m.group(1) + ' side'))
    R.append(('pronI', re.compile(r'(?<=[a-z] )l (?=(?:perceive|spake|come|found|known|knew|see|saw|thinke|think|said|sayd|will|would|shall|should|am|have|had|was|must|may|can|could|doe|did|answer|conceive|know|speake|beleeve|hope|pray)\b)'), lambda m: 'I '))
    # 漏进正文的页眉
    R.append(('head', re.compile(r'\bCha[pn][.,-]?\s?\d{1,2}\.?\s+An Ex\w*\s+u\w*\s+\w+\s+Boo?[sk]\w*\s+\S{1,3}\s?\S{0,3}\s+V\w{2,5}[.,]?\s?\d{0,2}\.?'),
              lambda m: ''))
    return R


RULES = rules()
RE_SPLIT = re.compile(r'\b([A-Za-z]{1,10}) ([a-z]{1,7})\b')


def split_fix(m):
    a, b = m.group(1), m.group(2)
    w = (a + b).lower()
    if UNI.get(w, 0) < 5:
        return None
    if UNI.get(a.lower(), 0) >= 20 and UNI.get(b, 0) >= 20 and b not in SUFFIX:
        return None                          # 两截都是常见词（in deed、a way…）：不合
    if b in ('full', 'ful') and re.search(r'\b(?:a|an|the|his|her|my|thy|our|your|their)\s$', m.string[:m.start()], re.I) \
            and m.string[m.end():m.end() + 3] == ' of':
        return None                          # 「a mind full of Anguish」是名词＋形容词，不是 mindfull（「art mind ful of him」照合）
    if a.lower() in ('a', 'an', 'the', 'i', 'o') and b not in SUFFIX:
        return None                          # 冠词、代词＋后词：「a wry thought」不并成 awry
    if b in SUFFIX or not UNI.get(a.lower(), 0) or not UNI.get(b, 0):
        return a + b
    return None


def sweep_text(pt, log, where):
    """纯文本段落上跑规则；返回新文本。"""
    def sub_split(m):
        r = split_fix(m)
        if r:
            log.append(('split', where, m.group(0), r))
            return r
        return m.group(0)
    for _ in range(3):                       # 匹配会互相吃掉：「and resol ved」先被「and resol」占了，「resol ved」轮不到——迭代到不动点
        new = RE_SPLIT.sub(sub_split, pt)
        if new == pt:
            break
        pt = new
    for name, rx, fn in RULES:
        def rep(m, name=name, fn=fn):
            new = fn(m)
            if new != m.group(0):
                log.append((name, where, m.group(0), new))
            return new
        pt = rx.sub(rep, pt)
    return pt


RE_PB = re.compile(r'<span class="cy-pb"[^>]*></span>')
KJV_DIR = ROOT / 'foote_raw' / 'luke' / 'src' / 'kjv'


def kjv_book(fn):
    vs, ch = {}, 0
    for ln in (KJV_DIR / fn).read_text(encoding='utf-8').splitlines():
        m = re.match(r'\\c (\d+)', ln)
        if m:
            ch = int(m.group(1))
        m = re.match(r'\\v (\d+) (.*)', ln)
        if m:
            t = re.sub(r'\\\+?w ([^|]*)\|[^\\]*\\\+?w\*', r'\1', m.group(2))
            vs[(ch, int(m.group(1)))] = set(w.lower() for w in re.findall(r'[A-Za-z]{3,}', re.sub(r'\\\+?\w+\*?', '', t)))
    return vs


KJV_JOB, KJV_JHN = kjv_book('19-JOBeng-kjv2006.usfm'), kjv_book('73-JHNeng-kjv2006.usfm')


def job_or_john(m):
    """「(Job. 14. 19.) Because I live…」：斜体 Joh 读成 Job。拿紧跟的引文去比 KJV 约伯记与约翰福音那一节，
    约翰那边重合明显更多才改（约伯记真引文、或两边都对不上的，不动）。"""
    ch, v = int(m.group(2)), int(m.group(3))
    follow = set(w.lower() for w in re.findall(r'[A-Za-z]{3,}', m.string[m.end():m.end() + 120])[:12])
    if len(follow) < 4:
        return None
    sj = len(follow & KJV_JOB.get((ch, v), set()))
    sn = len(follow & KJV_JHN.get((ch, v), set()))
    return 'Joh' if sn >= 3 and sn >= 2 * sj + 2 else None
MARGIN_SPLIT = [
    ('p4/11-15', 'ret', 'neweth', 'reneweth'),       # p.135 影像
]
MARGIN_BODY = [
    ('p4/11-4', 'God', 'is', 'invincible'),          # p.38 影像
    ('p6/21-27', 'God', 'or', '(as'),
    ('p6/21-27', 'draw', 'it', 'out.'),              # p.787 影像
    ('p6/21-27', 'if', 'all', 'that'),               # p.795 影像
    ('p6/21-27', 'Benefactors,', 'or', 'Gratious'),  # p.795 影像              # p.785 影像
]


def sig_letters(t):
    """签名串 → 字母：剥掉尾巴上的页序数字（Ffff3、LII12 的 2），其余 1／I 读法折成 l（Lllll 读成 LI11I）。"""
    t = re.sub(r'\s?[2-9]$', '', t.strip())
    t = re.sub(r'(?<=[A-Za-z])[1Il]|(?<=[1Il ])1', 'l', t)
    return re.sub(r'[^A-Za-z]', '', t)


def is_sig(letters):
    """书帖签名（Ddd、Nnnn、Ccce、KKXK、SES、H h'hh）：2–5 个字母、大写起头、同一字母占六成以上、不是词。"""
    if len(letters) >= 3 and len(set(letters.lower())) == 1 and len(letters) <= 5:
        return True                          # 「t t t」：全小写也算
    if not (2 <= len(letters) <= 5) or not letters[0].isupper():
        return False
    if UNI.get(letters.lower(), 0):
        return False
    return letters.lower().count(letters[0].lower()) / len(letters) >= 0.6


def fix_pagebreaks(md, log, where):
    """页码锚点前：剥掉漏进正文的书帖签名；锚点前是空行、上段没收尾、锚点后小写起头的，并回一段
    （「…He will E e e ⟂ watch dayly」「…the sent-U u u ⟂ forth-light」「…our bodyes afB bb ⟂ ter the resurrection」）。"""
    out, last = [], 0
    for m in RE_PB.finditer(md):
        seg = md[last:m.start()]
        k = len(seg)
        while k and seg[k - 1].isspace():
            k -= 1
        body, gap = seg[:k], seg[k:]
        if not body or (body.endswith('>') and not re.search(r'<span class="cy-ocr"[^>]*>[^<]*</span>$', body)):
            out.append(seg + m.group(0))
            last = m.end()
            continue
        glued = False
        # 末尾往回剥最多 4 个短 token（纯字母／数字，或 cy-ocr 包着的），找像签名的最短后缀
        toks, cut, bb = [], [], body
        while len(toks) < 6:
            mt = re.search(r'(\s?)(<span class="cy-ocr"[^>]*>([^<]{1,6})</span>|[A-Za-z’\'\d]{1,6})$', bb)
            if not mt:
                break
            toks.insert(0, mt.group(3) if mt.group(3) is not None else mt.group(2))
            cut.insert(0, mt.start())
            bb = bb[:mt.start()]
            if not mt.group(1):
                break
        for i in range(len(toks)):
            t0 = toks[i]
            pre = re.match(r'([a-z]+)([A-Z].*)$', t0)                       # 「afB bb」：签名粘在半个词后面
            letters = sig_letters(' '.join([pre.group(2) if pre else t0] + toks[i + 1:]))
            if is_sig(letters) and (i > 0 or pre or cut[0] == 0 or body[cut[0]].isspace() or not body[cut[0] - 1].isalpha()):
                start = cut[i]
                keep = ''
                if pre:                      # 留下前半截（连存疑标记一起去掉：签名剥掉后它就是半个正常词）
                    start = cut[i] + (1 if body[cut[i]].isspace() else 0)
                    keep = pre.group(1)
                    glued = True
                log.append(('sig', where, re.sub(r'<[^>]+>', '', body[start:]).strip(), keep))
                body = body[:start].rstrip(' ') + (' ' if keep and body[cut[i]].isspace() else '') + keep
                break
        after = md[m.end():m.end() + 1]
        if '\n\n' in gap and re.search(r'[a-z,;-]$', body) and re.match(r'[a-z]', after) and not body.rstrip().endswith('>'):
            log.append(('pbjoin', where, body[-20:] + '⏎⏎', after))
            gap = '' if glued or body.endswith('-') else ' '
        elif glued:
            gap = '' if '\n\n' not in gap else gap
        out.append(body + gap + m.group(0))
        last = m.end()
    out.append(md[last:])
    return ''.join(out)


def is_junk(t):
    """整段乱码（书末花饰、横线、页底签名单成一段）：一个真词也没有，且同一字符连写 5 个以上、像书帖签名、
    大写占七成以上（≥ 5 个字母）、或字母数字混杂而没有小写词。「Ohierve」「Ianswer」「vocamus」这类真内容挡在外面。"""
    ws = re.findall(r'[A-Za-z]+', t)
    if any(len(w) >= 3 and UNI.get(w.lower(), 0) for w in ws):
        return False
    L = re.sub(r'[^A-Za-zΑ-ωἀ-ῼ]', '', t)
    if not L:
        return False
    if re.search(r'(.)\1{4,}', t) or is_sig(sig_letters(t)):
        return True
    if len(L) >= 5 and sum(c.isupper() for c in L) / len(L) >= 0.7:
        return True
    if re.search(r'\d', t) and not re.search(r'\b[a-z]{3,}\b', t) and len(L) >= 2:
        return True
    return bool(re.search(r'\*\s', t)) and len(t) < 12


def drop_junk(md, log, where):
    out = []
    for para in md.split('\n\n'):
        if para.strip() and 'cy-margin' not in para and not re.search(r'<(?!/?span)[a-z]', para) and '{:' not in para:
            t = re.sub(r'<[^>]+>', '', para).strip()
            if t and len(t) <= 60 and is_junk(t):
                log.append(('junk', where, t, ''))
                keep = ''.join(RE_PB.findall(para))
                if keep:
                    out.append(keep)
                continue
        out.append(para)
    return '\n\n'.join(out)


def sweep_md(md, log, where):
    """只改标签之间的纯文本片段（不跨标签），旁注 span 整个跳过。"""
    md = drop_junk(md, log, where)
    # 看图确认、旁注插在一个正文词中间（「ret [旁注] neweth」）：并成一词、旁注挪到词后
    for w0, a, b, whole in MARGIN_SPLIT:
        if w0 == where:
            ocr = r'(?:<span class="cy-ocr"[^>]*>)?'
            rx = re.compile(rf'{ocr}\b{re.escape(a)}(?:</span>)? (<span class="cy-margin">[^<]*</span>)\s*{ocr}{re.escape(b)}\b(?:</span>)?')
            if rx.search(md):
                log.append(('mword', where, f'{a} [..] {b}', whole))
                md = rx.sub(lambda m: f'{whole} {m.group(1)}', md, 1)
    # 看图确认、被划进旁注的正文小词（人工表跨不了标签，在这里放回）：(段, 前词, 旁注词, 后词)
    for w0, a, w, b in MARGIN_BODY:
        if w0 == where:
            rx = re.compile(rf'(\b{re.escape(a)}) <span class="cy-margin">{re.escape(w)}</span> ({re.escape(b)})')
            if rx.search(md):
                log.append(('mword', where, f'{a} [{w}] {b}', f'{a} {w} {b}'))
                md = rx.sub(lambda m: f'{m.group(1)} {w} {m.group(2)}', md, 1)
    # 页顶漏进正文的页眉残片：页码锚点后「Vers. / verss.」紧跟一个只有数字的旁注（页眉节号被划进旁注）、
    # 或「An 〔页码〕 Exposition upon the Book of」（真正的逐节小标题节号都在行内，不受影响）
    def unhead(m):
        log.append(('head', where, re.sub(r'<[^>]+>', ' ', m.group(2)).strip(), ''))
        return m.group(1)
    md = re.sub(r'(<span class="cy-pb"[^>]*></span>)((?:[VvU]er[sfſ]+e?\.?\s*<span class="cy-margin">\s*\d{1,2}\.?\s*</span>'
                r'|An\s*<span class="cy-margin">\s*\d{2,4}\s*</span>\s*Exposition upon the Book of)\s*)', unhead, md)
    # 段首噪点「- 」「+ 」「• 」：markdown 会排成项目列表（第 6 部 21-30「- First, Some wicked men…」）
    def unlist(m):
        log.append(('list', where, m.group(2) + ' ', ''))
        return m.group(1)
    md = re.sub(r'((?:^|\n\n)(?:<span class="cy-pb"[^>]*></span>)?)([-–+•]) (?=[A-Za-z(])', unlist, md)
    for _ in range(3):                       # 长签名（「H h h h h」）一遍只剥得掉后几截：迭代到不动点
        new = fix_pagebreaks(md, log, where)
        if new == md:
            break
        md = new
    def jhn(m):
        r = job_or_john(m)
        if r:
            log.append(('joh', where, m.group(0), m.group(0).replace(m.group(1), r, 1)))
            return m.group(0).replace(m.group(1), r, 1)
        return m.group(0)
    md = re.sub(r'\((Job|Tob|fob|Iob)\.\s?(\d{1,2})\.\s?(\d{1,2})', jhn, md)
    def pjoin(m):
        log.append(('pjoin', where, m.group(1)[-20:] + '⏎⏎', m.group(2)[:15]))
        return m.group(1) + ' ' + m.group(2)
    # 上段须以字母或断词号收尾（不收「Observe,」「;」：下段是论点句，只是首字母读成了小写）、且不短于 50 字符
    for _ in range(10):                      # 连着劈成三四段的，一遍并不完
        new = re.sub(r'(?m)^((?!<(?!span class="cy-ocr")|[{#])(?=.{50,}).*[a-z-])\n\n((?:<span class="cy-ocr"[^>]*>)?[a-z][^\n]*)$', pjoin, md)
        if new == md:
            break
        md = new
    out, last = [], 0
    # 段界：旁注、页码锚点、缺页说明、其余标签；存疑标记 cy-ocr 不算段界（第 6 轮：「punispment</span> ef the」「(<span>Plal</span>. 139」
    # 以前被标记切开，规则够不着）——段内透过存疑标记匹配，改动碰到的标记连同标记一起去掉（与人工表同一口径）
    for m in re.finditer(r'<span class="cy-margin">.*?</span>|<span class="cy-pb"[^>]*></span>|<span class="cy-gap">.*?</span>'
                         r'|<(?!span class="cy-ocr")(?!/span>)[^>]+>|\{:[^}]*\}', md, re.S):
        out.append(sweep_seg(md[last:m.start()], log, where))
        out.append(m.group(0))
        last = m.end()
    out.append(sweep_seg(md[last:], log, where))
    return re.sub(r' {2,}', ' ', ''.join(out))


RE_OCR_SPAN = re.compile(r'<span class="cy-ocr"[^>]*>([^<]*)</span>')


def sweep_seg(seg, log, where):
    if '<span class="cy-ocr"' not in seg:
        return sweep_text(seg, log, where)
    plain = RE_OCR_SPAN.sub(lambda m: m.group(1), seg)
    lg = []
    new = sweep_text(plain, lg, where)
    if new == plain:
        return seg
    log.extend(lg)
    # 存疑标记在纯文本里的位置
    spans, off, pos = [], 0, 0
    for m in RE_OCR_SPAN.finditer(seg):
        a = m.start() - off
        spans.append((a, a + len(m.group(1)), m.group(0)[:m.start(1) - m.start()]))
        off += len(m.group(0)) - len(m.group(1))
    sm = difflib.SequenceMatcher(None, plain, new, autojunk=False)
    ops = sm.get_opcodes()
    changed = [(i1, i2) for op, i1, i2, j1, j2 in ops if op != 'equal']
    keep = [sp for sp in spans if not any(i1 <= sp[1] and sp[0] <= i2 for i1, i2 in changed)]
    # 留下的标记都落在未改动的区段里：按位置映射到新文本后重新包上
    res, k = [], 0
    pmap = {}
    for op, i1, i2, j1, j2 in ops:
        if op == 'equal':
            for t in range(i2 - i1 + 1):
                pmap[i1 + t] = j1 + t
    marks = []
    for a, b, opener in keep:
        if a in pmap and b in pmap:
            marks.append((pmap[a], pmap[b], opener))
    for a, b, opener in sorted(marks):
        res.append(new[k:a]); res.append(opener + new[a:b] + '</span>'); k = b
    res.append(new[k:])
    return ''.join(res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--show', default='')
    a = ap.parse_args()
    log, outs = [], {}
    for p in PARTS:
        for f in sorted((BASE / p / 'fixed').glob('*.md')):
            outs[f] = sweep_md(f.read_text(encoding='utf-8'), log, f'{p}/{f.stem}')
    c = collections.Counter(x[0] for x in log)
    print('全书同类清理：' + '，'.join(f'{k} {v}' for k, v in c.most_common()), file=sys.stderr)
    for k in c:
        xs = [x for x in log if x[0] == k]
        step = max(1, len(xs) // 12)
        print(f'  [{k}] ' + ' | '.join(f'{x[2]}→{x[3]}' for x in xs[::step][:12]), file=sys.stderr)
    if a.show:
        for x in log:
            if x[0] == a.show:
                print('\t'.join(x))
    if a.apply:
        for f, md in outs.items():
            f.write_text(md, encoding='utf-8')
        (BASE / 'sweep.tsv').write_text(''.join('\t'.join(x) + '\n' for x in log), encoding='utf-8')


if __name__ == '__main__':
    main()
