#!/usr/bin/env python3
"""规则 + 判词典的 OCR 修复。只碰「不是真词」的 token。

这份扫描件的错误高度成套，几乎全是**连字与相似字形**被拆错：
    li → U / H / h        appUed  Hterally  hke
    ll → U                aU  wiU
    ff → fi / flf         efiect  scoflfers
    rn ↔ m                modem(modern)  scomers(scorners)
    w  → iv / vn / ui     ivith  vnth  uill
    r  → i'               fii'st  wi'iters
所以修复方式不是逐条硬编码，而是给出这套字形替换规则，穷举 1–2 次替换的候选，
**只接受落进词典的结果**。落不进去的一律原样保留并记账，交给第二证人比对
（adjudicate_alexander_ocr.py）——绝不猜。

真词错误（modem/bom 这种「改错了仍是英文词」）规则抓不到，走 REAL_WORD_FIX，
每一条都必须在 1850 三卷本上核对过才准加。
"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_lexicon import build, is_word

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander_raw/psalms/en_chapters'
LOG = ROOT / 'logs/alexander_ocr_repair.tsv'

LIT_STAR = ''      # extract 留下的「字面星号待判」哨兵

RULES = [
    # 连字 li 被拆成单个字形 —— 本扫描件最大的一类错
    ('u', 'li'), ('h', 'li'), ('li', 'h'), ('tli', 'th'), ('tl', 'th'),
    # 双 l 读成 U：aU → all
    ('u', 'll'),
    # ff / fl 连字
    ('fi', 'ff'), ('fi', 'fl'), ('flf', 'ff'), ("fi'", 'ff'),
    # rn ↔ m 互串
    ('rn', 'm'), ('m', 'rn'), ('rri', 'm'), ('hn', 'lm'),
    # w 被拆成两个字母
    ('iv', 'w'), ('vn', 'w'), ('ui', 'w'), ('tv', 'w'), ('vv', 'w'),
    ('xv', 'w'), ('xo', 'w'), ('lo', 'w'), ('to', 'w'),
    # r 被读成 i 加撇
    ("i'", 'r'), ('fir', 'fr'), ('fi\"', 'ff'),
    # 字面星号：多半是 `r`（fi*om→from、ai*e→are、figui*e→figure），
    # 也可能纯属噪点。两种都试，落不进词典就不动。
    ('i' + LIT_STAR, 'r'), (LIT_STAR, 'r'), (LIT_STAR, ''), (LIT_STAR, 'c'),
    # wi / wn / un 整组串位
    ('vn', 'wi'), ('un', 'wi'), ('vm', 'wn'), ('im', 'un'), ('nn', 'rm'),
    ('h', 'b'), ('ji', 'h'), ('vp', 'up'),
]

# 只在词首生效的规则。词首的 w 常被整个读成一个 u/v/n（"will" → "uill"），
# 但把这条放进通用规则会去动 sound/under 这类词的中段，风险不对等。
HEAD_RULES = [('u', 'w'), ('v', 'w'), ('n', 'w'), ('U', 'W')]

# 规则抓不到的真词错误。每条都对着 1850 三卷本核过。
REAL_WORD_FIX = {
    'modem': 'modern',
    'bom': 'born',
    'tum': 'turn',
    'tums': 'turns',
    'bums': 'burns',
    'moming': 'morning',
    'evemng': 'evening',
    'nnder': 'under',
    'arid': 'and',        # 只在孤立出现时替换，见 _fix_arid
}

# 语料自证闸（见 corpus_vocab）会连带否掉一批**确实正确**的低频修复——
# 目标词全书只出现这一次，自然没有旁证。逐条看过上下文确认后放行。
MANUAL_FIX = {
    'hmbs': 'limbs', 'htigious': 'litigious', 'anghcan': 'Anglican',
    'accompuces': 'accomplices', 'accompushes': 'accomplishes',
    'ampufies': 'amplifies', 'bubbhng': 'bubbling', 'demohshed': 'demolished',
    "difi'erently": 'differently', 'draiver': 'drawer', 'duphcity': 'duplicity',
    "efi'orts": 'efforts', 'eflforts': 'efforts', 'elupses': 'ellipses',
    'fehcitation': 'felicitation', 'ghmpse': 'glimpse', 'hbations': 'libations',
    'homebom': 'homeborn', 'howhng': 'howling', 'hver': 'liver',
    'immobiuty': 'immobility', "imploi'ing": 'imploring',
    'inexphcable': 'inexplicable', 'instabiuty': 'instability',
    'ivrest': 'wrest', 'morauty': 'morality', 'overpotvered': 'overpowered',
    'pohtic': 'politic', 'pohtically': 'politically', 'pubucity': 'publicity',
    'reneivest': 'renewest', 'saivest': 'sawest', 'scomers': 'scorners',
    'simphfied': 'simplified', 'supercihous': 'supercilious',
    'totauty': 'totality', 'unukeness': 'unlikeness',
    # 词首 w 整个被读丢，语料自证也救不回来的几例
    'uarued': 'warned', 'vath': 'with', 'vrith': 'with', 'tuill': 'will',
    'tuatchers': 'watchers', 'knouest': 'knowest', 'suul': 'soul',
    'unkss': 'unless', 'humue': 'humble', "i'he": 'The', 'suftered': 'suffered',
    'oji': 'on',         # "literally *on thee, on (account of) thee*"
    'devoui': 'devour', 'soid': 'soul', 'aheady': 'already', 'grod': 'God',
    'wtiter': 'writer', 'tjie': 'The', 'rahah': 'Rahab', 'afibrded': 'afforded',
    'fonn': 'form', 'noim': 'noun',
    # 'Ji' 被读成 'l'/'h' 之后仍是英文词，规则挡不住，逐个核过上下文：
    'jire': 'fire',      # "as wax is melted before fire"
    'jiock': 'flock',    # "The sheep (or flock) of thy pasture"
    'tjion': 'Thou',     # "Thou wilt not hear"
}

# token 正则切不开的错：词中混进数字、或两词被粘在一起
PRE_FIX = [
    (r'\bs7nokes\b', 'smokes'),
    (r'\bthatver\b', 'that ver'),
    (r'\b(on|in|above|below)Ps\.', r'\1 Ps.'),
    (r'my soul lire\b', 'my soul live'),
    # `y` 被读成 `^'`：t^'pes → types
    (r"\^'", 'y'),
    (r"v,'hom", 'whom'),   # "to set whom for princes"（Isa. liii. 10 引文）
    (r'\bThon wilt\b', 'Thou wilt'),
    # 最后一条漏网页眉：这一处没带页码，且被并进了正文段落中间
    (r'my\* no \*Psalm 22:15,16 heart', 'my* no *heart'),
]

# 私用区哨兵必须靠拼接进正则：写在 r"..." 里 `\ue002` 不会被解释成那个字符，
# 而是反斜杠+u+e+0+0+2 六个字面字符，字符类里根本不含哨兵，token 会在哨兵处断开
# ——`fi<哨兵>om` 被切成 `fi` 和 `om`，所有针对哨兵的规则全部落空（踩过）。
TOKEN = re.compile('[A-Za-z' + LIT_STAR + '][A-Za-z' + LIT_STAR + "'’]*")


def _apply_once(w):
    out = set()
    for a, b in HEAD_RULES:
        if w.startswith(a):
            out.add(b + w[len(a):])
    for a, b in RULES:
        start = 0
        while True:
            i = w.find(a, start)
            if i < 0:
                break
            out.add(w[:i] + b + w[i + len(a):])
            start = i + 1
    return out


def candidates(w, lex, depth=2):
    # 收解用 is_word 而不是 `in lex`：罗马数字（xlix、lxxviii）不在词表里，
    # 用 `in lex` 收不到，`xHx → xlix` 这类citation 里的错永远修不掉。
    seen = {w}
    frontier = {w}
    good = []
    for _ in range(depth):
        nxt = set()
        for x in frontier:
            for y in _apply_once(x):
                if y in seen:
                    continue
                seen.add(y)
                nxt.add(y)
                if is_word(y, lex):
                    good.append(y)
        if good:
            return good           # 就近取解：一步能修好就不做两步
        frontier = nxt
    return good


def restore_case(src, dst):
    """只在首字母**没被规则动过**时才还原大写。

    反例：`Uterally` 的大写 U 是 `li` 连字被误读的产物，不是词首大写。
    照搬大小写会得到 `Literally`，把一个 OCR 错误换成另一个。
    """
    if src[:1].lower() == dst[:1].lower():
        if src.isupper() and len(src) > 1:
            return dst.upper()
        if src[:1].isupper():
            return dst[:1].upper() + dst[1:]
    return dst


def corpus_vocab(lex):
    """全书里**本来就正确**的词表。修复候选必须在这张表里出现过。

    这是最后一道闸：规则 + 词典能把 `hang` 改成 `liang`、`lieth` 改成 `heth`
    ——两个目标词都在韦氏词表里，词典拦不住。但它们在这本书里一次都没正确
    出现过，而 `literally`/`applied`/`with` 出现过几十次。「候选必须是本书
    确实用过的词」把这类换错一网打尽。"""
    vocab = Counter()
    for path in sorted(SRC.glob('*.md')):
        text = re.sub(r'<!--.*?-->', '', path.read_text(encoding='utf-8'))
        for w in TOKEN.findall(text):
            if is_word(w, lex):
                vocab[w.lower()] += 1
    return vocab


def join_across_star(text, lex):
    """`com* posed` / `cir* umjacent`：星号噪点顺带把一个词劈成两半。

    只有**拼回去正好是个词**时才合并，否则原样不动——不能因为「看着像断词」
    就把两个词粘起来。
    """
    def repl(m):
        joined = m.group(1) + m.group(2)
        if is_word(joined, lex):
            return joined
        if is_word(m.group(1) + 'c' + m.group(2), lex):   # 星号本身是个 c
            return m.group(1) + 'c' + m.group(2)
        return m.group(0)
    return re.sub(r'([A-Za-z]{2,})' + LIT_STAR + r'\s+([A-Za-z]{2,})', repl, text)


def settle_stars(text, lex):
    """规则救不回来的字面星号，按它在句子里的位置收尾。

    看过全部残留后归纳出的四种情形：
      `generation* The idea`   句号被读成星号 → 还原句号（后接大写）
      `for thy* mercy`         纯噪点          → 删掉（后接小写或数字）
      `of*domestic`            噪点顺带吞了空格 → 还原空格（两侧都成词）
      `(*nS)` `7J*1`           希伯来活字残渣   → 转义 `\*` 原样保留

    最后一种不删：那是页面上确实印着、OCR 读不出来的希伯来文，
    抹掉等于假装原书没有这段（feedback_preserve_pdf_artifacts）。
    """
    def between(m):
        a, b = m.group(1), m.group(2)
        if is_word(a, lex) and is_word(b, lex):
            return a + ' ' + b
        return m.group(0)
    text = re.sub(r'([A-Za-z]{2,})' + LIT_STAR + r'([A-Za-z]{2,})', between, text)
    text = re.sub(r'(?<=[a-z])' + LIT_STAR + r'(\s+)(?=[A-Z])', r'.\1', text)
    text = re.sub(r'(?<=[.,;:])' + LIT_STAR + r'(?=\d)', ' ', text)
    text = re.sub(r'(?<=[A-Za-z.,;:)—–\"\'])' + LIT_STAR + r'(?=\s)', '', text)
    text = re.sub(r'(?<=\s)' + LIT_STAR + r'(?=\s)', '', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.replace(LIT_STAR, r'\*')


def main():
    lex = build()
    vocab = corpus_vocab(lex)
    log = []
    stat = Counter()
    for path in sorted(SRC.glob('*.md')):
        text = path.read_text(encoding='utf-8')

        def repl(m):
            w = m.group(0)
            low = w.lower()
            if low in MANUAL_FIX:
                stat['manual'] += 1
                log.append((path.stem, w, MANUAL_FIX[low], 'manual'))
                return restore_case(w, MANUAL_FIX[low])
            if low in REAL_WORD_FIX:
                stat['realword'] += 1
                log.append((path.stem, w, REAL_WORD_FIX[low], 'realword'))
                return restore_case(w, REAL_WORD_FIX[low])
            # 罗马数字里的 l 被读成 I：Ixxviii → lxxviii。
            # 这一条必须**排在 is_word 之前**：is_word 把任何由 ivxlcdm 组成
            # 的串都当罗马数字放行，而 I 恰好也在这个集合里（大小写不敏感），
            # 于是 Ixxviii 被判成「合法罗马数字」，永远轮不到修（踩过）。
            if re.fullmatch(r'I[xvi]{1,7}', w):
                stat['roman'] += 1
                log.append((path.stem, w, 'l' + w[1:], 'roman'))
                return 'l' + w[1:]
            if is_word(w, lex):
                return w
            if len(low) < 3:          # oi / co / ia 这类两字母残片，规则一碰就错
                stat['tooshort'] += 1
                log.append((path.stem, w, '', 'tooshort'))
                return w
            # 三字母的 token 证据太薄：一次替换就能变成好几个真词
            # （thg→thig、oui→ow、Joh→Job）。对它们把语料自证的门槛从
            # 「出现过」抬到「出现过 20 次以上」，只放行 like/life/lips
            # 这类全书高频词。
            floor = 20 if len(low) == 3 else 1
            cands = [c for c in candidates(low, lex) if vocab.get(c, 0) >= floor]
            if len(set(cands)) == 1:
                fixed = restore_case(w, cands[0])
                stat['rule'] += 1
                log.append((path.stem, w, fixed, 'rule'))
                return fixed
            if cands:
                stat['ambiguous'] += 1
                log.append((path.stem, w, '|'.join(sorted(set(cands))[:5]), 'ambiguous'))
                return w
            stat['unresolved'] += 1
            log.append((path.stem, w, '', 'unresolved'))
            return w

        for pat, rep in PRE_FIX:
            text = re.sub(pat, rep, text)
        text = join_across_star(text, lex)
        # 注释行（<!-- PAGE n -->）不参与
        parts = re.split(r'(<!--.*?-->)', text)
        parts = [p if p.startswith('<!--') else TOKEN.sub(repl, p) for p in parts]
        text = ''.join(parts)
        # 规则跑完再过一遍：字形规则自己会**造出**新的真词错误
        # （'Uve' → 'lire'），只有在它后面才拦得住。
        for pat, rep in PRE_FIX:
            text = re.sub(pat, rep, text)
        text = settle_stars(text, lex)
        path.write_text(text, encoding='utf-8')

    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('chapter\tfrom\tto\tkind\n')
        for row in log:
            f.write('\t'.join(row) + '\n')
    print('修复统计:', dict(stat))
    print('日志:', LOG)


if __name__ == '__main__':
    main()
