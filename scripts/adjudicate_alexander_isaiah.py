#!/usr/bin/env python3
"""以赛亚书的多证人判读：拿另外八份扫描件给已发布正文的可疑 token 定案。

思路照搬 `adjudicate_alexander_ocr.py`（诗篇那份，另一个会话所作），
纯工具函数直接从那里 import，不另写一套。不同的只有两点：

**证人是八份，不是一份。** 同一部 1846/47 年 Wiley and Putnam 版，
Internet Archive 上有多家馆藏各自扫的独立副本。它们的 OCR 错法互不相关，
所以可以**多数表决**——比诗篇只有一个 1850 三卷本硬得多。这里要求
至少两份证人给出同一个读数才算数，一份说了不算。

    卷一（第 1–39 章）  earlierprophecie00alex / 00alexrich / 01alex / 187600alex
    卷二（第 40–66 章） laterprophecieso184700alex / 00alex / 00alexrich / 02alex
                        laterprophecies00alexgoog

1865 年 Scribner 重排本（propheciesofisai01alex）**不当证人**：那是另一次
排版，行文有修订，读数不同时分不清是 OCR 错还是版本差异。

**两类都查，不只查非词。** 判词典查不出「错成另一个英文词」的那类
（`Jield`→`held`、`har`→`bar`），而那恰恰是最难自己发现的错字。所以除了
非词，还要报告「我们印的是词、但多数证人在同一位置印的是另一个词」的分歧。
后一类**只报告不落盘**——两版之间本来就可能有异文，得人看过才算。

用法：
    python3 scripts/adjudicate_alexander_isaiah.py            # 只出报告
    python3 scripts/adjudicate_alexander_isaiah.py --apply    # 落盘
"""
import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adjudicate_alexander_ocr import (ANCHOR, MAX_DIST_RATIO, build_index,
                                      edit_distance, glyph_reachable, look_up,
                                      restore_case)
from alexander_lexicon import build, is_word

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/isaiah'
WSRC = ROOT / 'alexander_raw/isaiah/src'
LOG = ROOT / 'logs/alexander_isaiah_adjudicate.tsv'

WITNESSES = {
    'v1': ['earlierprophecie00alex', 'earlierprophecie00alexrich',
           'earlierprophecie01alex', 'earlierprophecie187600alex'],
    'v2': ['laterprophecieso184700alex', 'laterprophecieso00alex',
           'laterprophecieso00alexrich', 'laterprophecieso02alex',
           'laterprophecies00alexgoog'],
}
# 章号 → 用哪一卷的证人。前置件按所属卷走。
SECTION_VOL = {'preface': 'v1', 'introduction': 'v1',
               'later-preface': 'v2', 'later-introduction': 'v2'}

# token 里要认带变音符的字母。只认 ASCII 的话，`Rosenmüller` 会被切成
# `Rosenm` + `ller` 两截，前半截当成残串「补全」，拼出 `Rosenmümuller`——
# 判读器反复跑到收敛，每一轮都再糟一点（踩过）。
TOKEN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’]*")
MIN_VOTES = 2           # 至少两份证人给出同一读数
FRONT = re.compile(r'^---.*?^---\n', re.S | re.M)
# 标签必须**长得像标签**（`<` 后面紧跟字母或 `/`），不能写成 `<[^>]+>`：
# 正文里有 OCR 读出来的孤立 `<`（希伯来活字残渣），宽松的写法会从那个 `<`
# 一路吃到几百词之后的某个 `>`，把整段正文当标签吞掉——诗篇没这个问题，
# 以赛亚书第 19 章一处就吞了 572 个 token。
# HTML 实体也要当成「不是正文词」切掉：publish 把野生 `<` 转义成 `&lt;`
# 之后，token 正则会把里头的 `lt` 当成一个词，凭空多出一批非词
SEGMENT = re.compile(r'(<!--.*?-->|</?[A-Za-z][^<>]*>|&(?:lt|gt|amp|quot|nbsp);)',
                     re.S)


def load_witnesses():
    """{卷: [(名字, 索引, 小写词表, 原词表), ...]}"""
    out = defaultdict(list)
    for vol, names in WITNESSES.items():
        for name in names:
            path = WSRC / f'{name}.txt'
            if not path.exists():
                print(f'⚠ 证人缺失，跳过: {name}')
                continue
            words = TOKEN.findall(path.read_text(encoding='utf-8', errors='replace'))
            idx, low = build_index(words)
            out[vol].append((name, idx, low, words))
    return out


def look_up_strict(toks, i, idx, wlow, worig):
    """两侧各三词都对上才算命中。

    `look_up` 只校验右侧**一个**词，四词上下文对常见句式并不够：
    第 34 章的 `by the gratuitous ⟨assertion⟩ that` 就撞上了书里别处的
    `by the gratuitous assumption that`，四份证人「一致」给出 assumption，
    照办就把原文的 assertion 改错了（翻页面影像才发现）。
    真词那一路本来就是在改**看起来没毛病的词**，锚必须更硬。
    """
    left = [t.lower() for t in toks[max(0, i - ANCHOR):i]]
    right = [t.lower() for t in toks[i + 1:i + 1 + ANCHOR]]
    if len(left) < ANCHOR or len(right) < ANCHOR:
        return None
    readings = []
    for p in idx.get(tuple(left), ()):
        j = p + ANCHOR
        if j >= len(wlow):
            continue
        if wlow[j + 1:j + 1 + ANCHOR] != right:
            continue
        readings.append(worig[j])
    uniq = {r.lower() for r in readings}
    return readings[0] if len(uniq) == 1 else None


def poll(toks, i, witnesses, strict=False):
    """各证人在 toks[i] 这个位置上分别印的是什么 → (多数读数, 票数, 参与数)"""
    votes = Counter()
    probe = look_up_strict if strict else look_up
    for _, idx, low, orig in witnesses:
        r = probe(toks, i, idx, low, orig)
        if r:
            votes[r.lower()] += 1
    if not votes:
        return None, 0, 0
    top, n = votes.most_common(1)[0]
    # 有分歧时必须**唯一**领先，否则作废：宁可不判，不可判错
    if len(votes) > 1 and votes.most_common(2)[1][1] == n:
        return None, 0, sum(votes.values())
    return top, n, sum(votes.values())


def segments(raw):
    """原文 → [(是否正文, 片段)]。

    判读与落盘**必须共用这一份切分**。分头各切一次，只要有一处不一致，
    token 序号就整体错位，替换会落到别的词上（第 9 章曾把 prosperity 换成
    隔壁拉丁引文里的 commiscebit）。
    """
    m = FRONT.match(raw)
    rest = raw[m.end():] if m else raw
    return [(not p.startswith(('<', '&')), p) for p in SEGMENT.split(rest) if p]


def body_tokens(raw):
    out = []
    for is_text, seg in segments(raw):
        if is_text:
            out.extend(TOKEN.findall(seg))
    return out


# 证人一致、但自动闸放不过去的真词错字：逐条读过上下文才收进来。
# 「自动闸放不过去」多半是因为两边都是常用词（frequency 比过不了 20 倍），
# 或者错串跨了 token 边界（`growl li`、`unreason able`）。
# 每条都带足上下文，避免误伤同一个词的其他出现。
MANUAL_TEXT = [
    # —— 人名被读成常见词 ——
    ('Rosenmuller and August!', 'Rosenmuller and Augusti'),
    ('But Miller (in his Onomasticon)', 'But Hiller (in his Onomasticon)'),   # Onomasticon Sacrum 的作者是 Hiller
    ("Holler's attempt to set aside", "Moller's attempt to set aside"),
    # —— 经文译文里的错字（这些是 Alexander 自己的译文，错了最刺眼）——
    ('*Fitted* cannot mean', '*Filled* cannot mean'),                          # 赛 2:6
    ('thou shah', 'thou shalt'),
    ('the rebuke of Jive shall ye flee', 'the rebuke of five shall ye flee'),  # 赛 30:17
    ("and pooh* (or *lakes\')", "and pools* (or *lakes\')"),                   # 赛 42:15
    ('am leaching thee to profit', 'am teaching thee to profit'),              # 赛 48:17
    ('smiling a man', 'smiting a man'),                                        # 赛 66:3
    ('*Gush was the brother of Mizraim', '*Cush was the brother of Mizraim'),
    ('Gush was the brother of Mizraim', 'Cush was the brother of Mizraim'),
    ('remnant of the home of Israel', 'remnant of the house of Israel'),       # 赛 46:3
    ('Joah, Asaphs son', "Joah, Asaph's son"),
    # —— 解说里的错字 ——
    ('opportunity of rinding a mythology', 'opportunity of finding a mythology'),
    ('the growl li of plants', 'the growth of plants'),
    ('dry and innutritions food', 'dry and innutritious food'),
    ('to the by-slanders', 'to the by-standers'),
    ('properly a stickler or wet-nurse', 'properly a suckler or wet-nurse'),
    ('if you phase*', 'if you please*'),
    ('these interpreter? suppose', 'these interpreters suppose'),
    ('mean? salvation', 'means salvation'),
    ('and appeals to understand the clause', 'and appears to understand the clause'),
    ('scorn and haired for a time', 'scorn and hatred for a time'),
    ('assertion might he made', 'assertion might be made'),
    ('by refuting the offered attestation', 'by refusing the offered attestation'),
    ('the deputation of their people by Tiglath-pileser',
     'the deportation of their people by Tiglath-pileser'),
    ("comparing them to swarm's of noxious", 'comparing them to swarms of noxious'),
    ('he was a renegade or apostate Jew', 'he was a renegado or apostate Jew'),
    ('not more unreason able than', 'not more unreasonable than'),
    ('by its render ing the suffix', 'by its rendering the suffix'),
    ('the analogy of others like ifc.', 'the analogy of others like it.'),
    ('fumantes pulvere compos', 'fumantes pulvere campos'),
    # 底本这一处**整词漏印**（翻页处，OCR 连字都没读出来），四份证人一致
    # 作 cited。判读器是逐 token 比对，看不见「少了一个词」，只能人工补。
    ('the only case which has been to establish',
     'the only case which has been cited to establish'),                    # Virgil, Aen. 那句是 campos
]


# 正则版的人工核定。放在**判读之后**，不放进 repair：一旦正文里出现 ü，
# 判读器的 token 正则（只认 ASCII 字母）就会把 `Rosenmüller` 切成
# `Rosenm` + `ller`，前半截被当成残串「补全」，拼出 `Rosenmümuller`（踩过）。
MANUAL_RE = [
    # 德文变音符：页面上印的是 ü，OCR 读成 ii/ti/ij/rnt 等等。翻过书页影像
    # 核实（书页 405 的 Rosenmüller 清清楚楚带两点），还原属于复现原文。
    (re.compile(r'\bRosen[a-zA-ZüöäÜÖÄ]{1,8}ll?er\b'), 'Rosenmüller'),
    (re.compile(r'\bFiirst\b'), 'Fürst'),
    (re.compile(r'\bR[iu]ckert\b'), 'Rückert'),
    (re.compile(r'\biiber\b'), 'über'),
    (re.compile(r'\bStiitze\b'), 'Stütze'),
    (re.compile(r'\bgefliigelter\b'), 'geflügelter'),
    # 人名拼错，证人与页面一致
    (re.compile(r'\bVilringa\b'), 'Vitringa'),
    (re.compile(r'\bShalmeneser\b'), 'Shalmaneser'),
]


def load_manual_file():
    """逐条核过的人工改正，放在数据文件里而不是脚本里。

    条目会长到几十上百条，塞在脚本里既难读也难 review；而且它是**数据**
    （每条都带依据），不是逻辑。左列必须带足上下文，保证全书唯一。
    """
    path = ROOT / 'alexander_raw/isaiah/manual_fixes.tsv'
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) >= 2 and parts[0] != 'before':
            out.append((parts[0], parts[1]))
    return out


MANUAL_FILE = load_manual_file()


def apply_manual(raw):
    n = 0
    for a, b in MANUAL_TEXT + MANUAL_FILE:
        if a in raw:
            n += raw.count(a)
            raw = raw.replace(a, b)
    for pat, rep in MANUAL_RE:
        raw, k = pat.subn(rep, raw)
        n += k
    return raw, n


def base_vocab():
    """已发布正文自己的词频。判「真词错字」时要用。"""
    c = Counter()
    for path in SRC.glob('*.md'):
        for w in body_tokens(path.read_text(encoding='utf-8')):
            c[w.lower()] += 1
    return c


def main(apply_it):
    lex = build()
    wit = load_witnesses()
    bvocab = base_vocab()
    for vol in ('v1', 'v2'):
        print(f'{vol} 证人 {len(wit[vol])} 份')

    rows = []
    stat = Counter()
    for path in sorted(SRC.glob('*.md')):
        stem = path.stem
        vol = SECTION_VOL.get(stem)
        if vol is None:
            if not stem.isdigit():
                continue
            vol = 'v1' if int(stem) <= 39 else 'v2'
        raw = path.read_text(encoding='utf-8')
        toks = body_tokens(raw)
        fixes = {}
        for i, tok in enumerate(toks):
            ours_is_word = is_word(tok, lex)
            reading, votes, total = poll(toks, i, wit[vol], strict=ours_is_word)
            if not reading or votes < MIN_VOTES:
                stat['无证据' if not ours_is_word else 'ok'] += 1
                continue
            if reading == tok.lower():
                stat['证人一致' if not ours_is_word else 'ok'] += 1
                if not ours_is_word:
                    rows.append((stem, tok, tok, votes, total, 'confirm'))
                continue

            # —— 读数不同 ——
            dist = edit_distance(tok.lower(), reading)
            close = dist <= max(1, round(len(reading) * MAX_DIST_RATIO))
            # 目标掉到一两个字母的，一律不信：那是希伯来活字残渣
            # （`bx`→`b`、`ic`→`c`），证人那边也是残渣，只是残得不一样。
            # 等长的两字母词（`ol`→`of`、`le`→`be`、`yc`→`ye`）另当别论。
            if len(reading) < 3 and not (len(reading) == len(tok)
                                         and is_word(reading, lex)):
                close = False
            if not ours_is_word:
                # —— 撇号当空格，repair 阶段不敢拆的那一批 ——
                # repair 里只能靠「两半都是词」判断，为了不碰希伯来残渣
                # （`ni'aa`）只好用长度兜底，`of'the` 这类真空格因此被挡下。
                # 这里有**位置证据**：证人在同一位置读出的就是前半截。
                # `of'the` 的证人读数是 `of`，`ni'aa` 的证人读数不会是 `ni`，
                # 所以残渣自动落不进来，不必用长度换安全。
                # （做法来自诗篇线的 splitq。）
                if tok.lower().startswith(reading):
                    rest = tok[len(reading):]
                    core = rest.lstrip("'’")
                    if (rest[:1] in ("'", "’") and len(reading) >= 2
                            and len(core) >= 2 and is_word(reading, lex)
                            and is_word(core, lex)):
                        fixed = restore_case(tok, reading) + ' ' + core
                        fixes[i] = (tok, fixed)
                        rows.append((stem, tok, fixed, votes, total, 'splitq'))
                        stat['撇号拆词'] += 1
                        continue
                # 我们这串不是词：证人读数得是词（或字形上从我们这串走得到）
                ok = (is_word(reading, lex) or glyph_reachable(tok, reading)) and close
                # 两字母的残串多半是**被标点劈开的半个词**（`A.nd` 里的 `nd`）。
                # 照证人补全会拼成 `A.and` 这种更糟的东西。等长的（`ol`→`of`）
                # 不在此列——那是整词误读，不是断片。
                if len(tok) < 3 and len(tok) != len(reading):
                    ok = False
                # 缩水守卫：证人读数比我们这串短三个字母以上，多半是它只读出
                # 了半个词（`waterbrooks` 只读到 `brooks`），照办等于吞词。
                # 距离闸按**读数长度**算阈值，短读数的阈值也小，挡得住大部分，
                # 但挡不住 `explanations'of`→`explanations` 这种（另一个会话
                # 在诗篇上抓到 6 处）。这一条专防它。
                if len(tok) - len(reading) >= 3:
                    ok = False
                if ok:
                    fixes[i] = (tok, restore_case(tok, reading))
                    rows.append((stem, tok, reading, votes, total, 'fix'))
                    stat['改'] += 1
                else:
                    rows.append((stem, tok, reading, votes, total, 'reject'))
                    stat['证据不足'] += 1
            else:
                # 我们这串是词，证人却印着另一个词——判词典看不见的那类错字
                # （`thai`/`tha`/`stilt`/`hut` 都是真词，却明显是 that/the/
                # still/but 读崩的）。两版之间也确实可能有异文，所以只在
                # **证据压倒性**时才落盘：
                #   全体证人一致（不是多数，是一致），且至少三份；
                #   证人读数在本书里比我们这串常见 20 倍以上。
                # 后一条挡住 mere/more、his/this、those/these 这种两边都常用
                # 的对子——那种分不清是错字还是异文，留给人看。
                if not (is_word(reading, lex) and close):
                    pass
                elif (votes == total >= 3 and len(tok) >= 3
                      and bvocab.get(reading, 0) >= 20 * max(bvocab.get(tok.lower(), 0), 1)):
                    fixes[i] = (tok, restore_case(tok, reading))
                    rows.append((stem, tok, reading, votes, total, 'realword-fix'))
                    stat['真词改'] += 1
                else:
                    rows.append((stem, tok, reading, votes, total, 'realword?'))
                    stat['真词分歧待看'] += 1

        if apply_it:
            new = apply_fixes(raw, fixes) if fixes else raw
            new, nm = apply_manual(new)
            stat['人工核定'] += nm
            if new != raw:
                path.write_text(new, encoding='utf-8')

    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('chapter\tours\twitness\tvotes\tpolled\tverdict\n')
        for r in rows:
            f.write('\t'.join(str(x) for x in r) + '\n')
    print('判读统计:', dict(stat))
    print('日志:', LOG)
    if not apply_it:
        print('（这是报告模式，没有落盘。要落盘加 --apply）')


def apply_fixes(raw, fixes):
    """按 token 序号落回原文，只动正文里第 n 个 token，不碰 front matter/标签。

    切分走 segments()，与判读时**同一份**；再加一道逐个核对（见下），
    两层保险。front matter 与标签里也有英文单词（layout: alexander-chapter、
    class="ax-vnum"），数错一位后面就全歪。
    """
    m = FRONT.match(raw)
    head = m.group(0) if m else ''
    parts = segments(raw)
    n = 0
    for k, (is_text, seg) in enumerate(parts):
        if not is_text:
            continue
        out, last = [], 0
        for mt in TOKEN.finditer(seg):
            if n in fixes:
                want, repl = fixes[n]
                # 落盘前先核对：这里数到的第 n 个 token 是不是判读时看到的那个。
                # body_of 与这里必须用**同一套**切分口径，一旦偏一个位置，
                # 后面所有替换都会落到别的词上（ch9 曾把 prosperity 换成
                # 一句拉丁引文里的 commiscebit）。对不上就宁可不改。
                if seg[mt.start():mt.end()] != want:
                    raise SystemExit(
                        f'token 对不上：第 {n} 个应是 {want!r}，实际是 '
                        f'{seg[mt.start():mt.end()]!r}')
                out.append(seg[last:mt.start()])
                out.append(repl)
                last = mt.end()
            n += 1
        if out:
            out.append(seg[last:])
            parts[k] = (True, ''.join(out))
    return head + ''.join(seg for _, seg in parts)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    main(ap.parse_args().apply)
