#!/usr/bin/env python3
"""福特《路加福音讲义》第 ② 层：第二证人按位置判读（skill old-book-ocr §1 第 ② 层）。

证人＝第 3 版两卷本卷一（IA lecturesongospe01footgoog，Lect. I–LXVI），覆盖本书第 1–66 讲。
第 67–137 讲没有第二份扫描，本脚本不碰，留给第 ③ 层看图。

判读对象是第 ① 层之后 en_chapters/ 里仍不是真词的 token。做法照诗篇那套
（adjudicate_alexander_ocr.look_up）：可疑词前后各六词窗口里滑动取三词锚，在证人词流里
定位，读出证人在**同一位置**印的是什么，并要求另一侧相邻词也对得上。

两版之间作者可能有修订，所以读数要过闸才落：
  字形闸  读数与 OCR 串编辑距离占比 ≤ 1/3，或从 OCR 串按字形规则走得到读数
          ——挡住两版之间真正的改写（拿第 3 版覆盖第 2 版＝篡改底本）
  判词闸  读数是真词（含钦定本路加词形），或在证人里出现 ≥ 3 次
  形状闸  读数不得是单个字母；不得只差大小写（那是 confirm）
两版一致的记 confirm（已核实原样，以后不必再挖）。

判决落成规则表 foote_raw/luke/witness_fixes.tsv（讲次、前三词锚、原样、改作），
`--apply` 按表落到 en_chapters/：每条须恰好命中一次，否则报错。publish 之前跑，
重跑 extract→repair 之后再跑一次即可全量恢复（skill §3 硬约束 1）。

    python3 scripts/adjudicate_foote_ocr.py [--witness ed3|tess]          # 判读 → 写规则表 + logs
    python3 scripts/adjudicate_foote_ocr.py --apply [--witness ed3|tess]  # 按规则表落盘（默认 ed3 → tess 按序）

注意：tess 的判读要在 ed3 落盘**之后**跑（它判的是 ed3 修完还剩的残字），规则锚也是那时的文本。
"""
import argparse
import itertools
import csv
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_foote as F  # noqa: E402
from adjudicate_alexander_ocr import build_index, edit_distance, glyph_reachable, look_up  # noqa: E402
from alexander_lexicon import build, is_word  # noqa: E402
from repair_alexander_ocr import foote_kjv_words  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'foote_raw' / 'luke'
SRC = RAW / 'en_chapters'
WITNESS_ID = 'lecturesongospe01footgoog'
# 两个证人，按序落：
#   ed3   第 3 版卷一 ABBYY，Lect. 1–66（另一份印本）
#   tess  第 2 版本身的 tesseract 重扫（foote_tesseract.py），全书——同一份扫描、换一个引擎
#         （skill §3.2c：第二条非生成式字流）。Lect. 67–137 只有它。
WITNESSES = {
    'ed3': dict(lectures=range(1, 67), rules=RAW / 'witness_fixes.tsv',
                log=ROOT / 'logs' / 'foote_adjudicate.tsv'),
    'tess': dict(lectures=range(1, 138), rules=RAW / 'witness_fixes_tess.tsv',
                 log=ROOT / 'logs' / 'foote_adjudicate_tess.tsv'),
}
TESS = RAW / 'tess'
TOKEN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’]*")
TAG = re.compile(r'<!--.*?-->')
MAX_DIST_RATIO = 1 / 3


def load_tess(vol):
    """tesseract 重扫一卷 → 词流。行末断词（`desig-` + `nate`）先接上，否则与我们的切分对不齐。"""
    pages = sorted((TESS / f'v{vol}').glob('*.txt'))
    text = '\n'.join(p.read_text(encoding='utf-8') for p in pages)
    text = re.sub(r'([A-Za-z])-\s*\n\s*([a-z])', r'\1\2', text)
    return TOKEN.findall(text), text


def load_witness():
    F.VOLS[9] = WITNESS_ID
    pages = F.load_pages(9)
    chunks = []
    for pg in pages:
        for par in pg['pars']:
            chunks.append(''.join(c for c in par['text'] if unicodedata.category(c) != 'Co'))
    text = '\n'.join(chunks)
    return TOKEN.findall(text), text


def body_tokens(text):
    """正文（含经文段、注区）→ [(start, end, token)]，跳过 PAGE/NOTE 注释。"""
    out = []
    pos = 0
    for m in TAG.finditer(text + '<!---->'):
        seg = text[pos:m.start()]
        for t in TOKEN.finditer(seg):
            out.append((pos + t.start(), pos + t.end(), t.group(0)))
        pos = m.end()
    return out


FN_MARK = '\ue010'
# 我们这侧本来就对、证人读错的（逐条看过）：Gallio 迦流（徒 18）证人读 Gallic；Csesar 是 Cæsar 读成，证人读 Cesar
KEEP = {'gallio', 'csesar', 'snfler'}
# tesseract 证人那一轮逐条看过、不放行的（改成别的真词 hready→bread、oftn→oven、fowlsf→fouls、
# zxiv→XXII、Grsece→Grace(=Græce)；碎片 ssion/Tersation；证人也崩 TnE→Tue、tnan→quan；
# 脚注 † 判断可疑 thet/mef/farf；候选不唯一 ahoot(shoot/about)、rhen(they/When)、yent）→ 留看图
TESS_HOLD = {'ahoot', 'cau', 'baie', 'eejeed', 'ephafu', 'feneral', 'fii', 'fint', 'fibuces', 'fowlsf',
             'freni', 'gmve', 'hatht', 'hereai', 'hready', 'iofe', 'ivn', 'maity', 'miine', 'ners', 'ofr',
             'oftn', 'oit', 'ooils', 'redrew', 'rhen', 'ruinse', 'ssion', 'suae', 'tersation', 'tmngs', 'tnan',
             'tne', 'tteo', 'uest', 'yim', 'yent', 'zxiv', 'thet', 'mef', 'farf', 'eaor', 'grsece'}
# 等长两处替换里拿不准的（Thsi 可 This 可 They；fiul 可 full 可 fail …）
SHAPE2_HOLD = {'thsi', 'eist', 'fiul', 'merc', 'noine', 'orcu', 'inme', 'wtot'}


def verdict(tok, reading, lex, wvocab, prev_w, next_w):
    """→ (kind, 改作)。kind == 'fix' 才落。全书试跑 1058 种改法逐条看过后定的闸。"""
    if reading is None:
        return 'nowitness', ''
    if reading.lower() == tok.lower():
        return 'confirm', reading
    if tok.lower() in KEEP:
        return 'reject:keep', ''
    reading = reading.rstrip("'’") or reading
    t, r = tok.lower(), reading.lower()
    if len(reading) == 1 and r not in ('a', 'i', 'o'):
        return 'reject:single', ''
    # 词尾 y/j＝逗号读错（Christy / saidy / Gody）：改成「词＋逗号」，删掉就丢了逗号
    if len(t) == len(r) + 1 and t.startswith(r) and t[-1] in 'yj' and is_word(reading, lex):
        return 'fix', reading + ','
    # 词尾 t/f＝脚注标号 † 读错（Jesusf / Bethlehemt）：保留成脚注哨兵
    if len(t) == len(r) + 1 and t.startswith(r) and t[-1] in 'tf' and is_word(reading, lex):
        return 'fix', reading + FN_MARK
    # 一头丢字（ofAbia→Abia、Sth→th）：证人与我们切分不同或读出隔壁，丢的可能是真字
    if t != r and t.endswith(r) and len(t) > len(r):
        return 'reject:dropfront', ''
    if t != r and t.startswith(r) and len(t) > len(r):
        return 'reject:dropback', ''
    # 截断（Gosp→Gospel）／前缺（ith→with）：缺的那截若正是相邻 token，就是被拆开的词，单改一处会叠字
    if r.startswith(t) and r[len(t):] == (next_w or '').lower():
        return 'reject:split', ''
    if r.endswith(t) and r[:len(r) - len(t)] == (prev_w or '').lower():
        return 'reject:split', ''
    if r.startswith(t) and len(r) - len(t) >= 2:
        return 'reject:truncated', ''
    # 我们只多一个尾字（generationl）：去掉尾字就是真词，证人读出别的词（feneration）多半是证人错。
    # 只对长词（去尾 ≥ 6 字母）：短串去尾碰巧成词太常见（hini→hin、whai→wha），会挡掉正确的修正
    # 只是最后一个字母读错（privilegei→privileges、beliere→believe、divinel→divinely）：
    # 与证人共享整个词干，不算这一类
    # 只差中间一个字母的（beliere→believe、serrant→servant）也不算：编辑距离 1 是普通误读
    if len(t) - 1 >= 6 and is_word(tok[:-1], lex) and r != t[:-1] and not r.startswith(t[:-1]) \
            and edit_distance(t, r) > 1:
        return 'reject:tailnoise', ''
    d = edit_distance(t, r)
    shape = d / max(len(t), len(r)) <= MAX_DIST_RATIO or glyph_reachable(tok, reading)
    # 等长、两处替换、读数是真词（coidd→could、qmet→quiet、muen→much）：69 条逐条看过，
    # 拿不准的 8 条（SHAPE2_HOLD）留给看图
    if not shape and len(t) == len(r) >= 4 and d == 2 and is_word(reading, lex) and t not in SHAPE2_HOLD:
        shape = True
    if not shape:
        return 'reject:shape', ''
    # 证人自己读崩：从证人读数按字形规则走得到我们的串（Satuminus→Saturninus）
    if glyph_reachable(reading, tok):
        return 'reject:witnessbroken', ''
    # 判词闸：读数必须是真词（判词典＋钦定本路加词形）。不开「证人里出现 ≥3 次」的后门——
    # 第 3 版的 OCR 也有同样的成套错（imderstood / oflf / sufier / IsraeV / Markf 都出现多次）
    if not is_word(reading, lex):
        return 'reject:word', ''
    return 'fix', reading


def judge(wname):
    cfg = WITNESSES[wname]
    lex = build() | foote_kjv_words()
    streams = {}
    if wname == 'ed3':
        w, _ = load_witness()
        streams = {v: w for v in (1, 2)}
    else:
        for v in (1, 2, 3):
            streams[v] = load_tess(v)[0]
    built = {}
    rules, log, stat = [], [], Counter()
    for n in cfg['lectures']:
        vol = next(v for v in (1, 2, 3) if F.FIRST_LECT[v] <= n <= F.LAST_LECT[v])
        if vol not in built:
            idx, wlow = build_index(streams[vol])
            built[vol] = (idx, wlow, streams[vol], Counter(wlow))
        idx, wlow, wwords, wvocab = built[vol]
        path = SRC / f'{n:03d}.md'
        text = path.read_text(encoding='utf-8')
        toks = body_tokens(text)
        words = [t for _, _, t in toks]
        for i, (a, b, tok) in enumerate(toks):
            parts = [x for x in re.split(r"['’]", tok) if x]
            if len(tok) < 3 or all(is_word(x, lex) for x in parts) or is_word(tok, lex):
                continue
            reading = look_up(words, i, idx, wlow, wwords)
            v, to = verdict(tok, reading, lex, wvocab, words[i - 1] if i else '',
                            words[i + 1] if i + 1 < len(words) else '')
            # 'tne' 只挡大写混写的 TnE（→Tue 证人崩）；小写 tne→the 是对的
            if v == 'fix' and wname == 'tess' and tok.lower() in TESS_HOLD and tok != 'tne':
                v = 'reject:hold'
            stat[v] += 1
            log.append((f'{n:03d}', tok, reading or '', v))
            if v == 'fix':
                anchor = ' '.join(words[max(0, i - 3):i])
                rules.append((f'{n:03d}', anchor, tok, to))
    RULES, LOG = cfg['rules'], cfg['log']
    with open(RULES, 'w', encoding='utf-8') as f:
        f.write('# lecture\tanchor(前三词)\tfrom\tto —— adjudicate_foote_ocr.py 生成；手改须同步说明\n')
        for r in rules:
            f.write('\t'.join(r) + '\n')
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('lecture\tfrom\treading\tkind\n')
        for r in log:
            f.write('\t'.join(r) + '\n')
    stat['confirm'] = stat.get('confirm', 0)
    print(f'[{wname}] 判读：', dict(stat), f'→ 规则 {len(rules)} 条 {RULES.name}', file=sys.stderr)


# 人工核定表（不是某个证人自动判出来的）：逐条看过才进，--apply 时排在两证人表之后落
MANUAL = RAW / 'manual_fixes.tsv'


# 人工核定的整串替换（断词并回 `sepa^ rates`→`separates` 这类，跨两个 token，按词规则表落不了）：
# lecture \t 原串（逐字）\t 改作。原串须在本讲恰好出现一次；已是改作且原串不在＝已落过
MANUAL_SPANS = RAW / 'manual_spans.tsv'

# 第 ③ 层：整页转录（第三证人）与 tesseract 同位一致的改字（foote_vlm_adjudicate.py 生成、逐组看过）。
# 锚取自 symbols 之后的文本，所以链条上排在 foote_symbols.py --apply 之后：adjudicate --apply --vlm
VLM_RULES = RAW / 'vlm_fixes.tsv'


def apply_spans(path):
    done, already, bad = 0, 0, []
    by = {}
    for ln in path.read_text(encoding='utf-8').splitlines():
        if ln.strip() and not ln.startswith('#'):
            lec, old, new = ln.split('\t')
            by.setdefault(lec, []).append((old, new))
    for lec, rs in by.items():
        f = SRC / f'{lec}.md'
        text = f.read_text(encoding='utf-8')
        for old, new in rs:
            n = text.count(old)
            if n == 1:
                text = text.replace(old, new)
                done += 1
            elif n == 0 and new in text:
                already += 1
            else:
                bad.append((lec, old, n))
        f.write_text(text, encoding='utf-8')
    print(f'整串落盘 {done} 条；已落过 {already}；定位失败 {len(bad)} {bad[:5]}', file=sys.stderr)
    if bad:
        raise SystemExit(1)


def _all_rules():
    out = {}
    for cfg in list(WITNESSES.values()) + [dict(rules=MANUAL)]:
        if not cfg['rules'].exists():
            continue
        for ln in cfg['rules'].read_text(encoding='utf-8').splitlines():
            if ln.strip() and not ln.startswith('#'):
                lec, anchor, old, new = ln.split('\t')
                out.setdefault(lec, []).append((anchor, old, new))
    return out


ALLMAP = {}
SPANMAP = {}   # lecture → [(原串的词序列, 改作的词序列)]，供「已落过」判断换算锚


def _load_spanmap():
    if MANUAL_SPANS.exists():
        for ln in MANUAL_SPANS.read_text(encoding='utf-8').splitlines():
            if ln.strip() and not ln.startswith('#'):
                lec, old, new = ln.split('\t')
                SPANMAP.setdefault(lec, []).append((' '.join(TOKEN.findall(old)), ' '.join(TOKEN.findall(new))))


def apply(RULES):
    """按规则表落盘。每讲内**从后往前**落：规则的锚是判读时的前三词，前一条改掉的词
    可能正是后一条的锚，顺着落会定位失败（实测 22 条）。幂等判断时锚也按本讲修正表换算。"""
    by = {}
    for ln in RULES.read_text(encoding='utf-8').splitlines():
        if not ln.strip() or ln.startswith('#'):
            continue
        lec, anchor, old, new = ln.split('\t')
        by.setdefault(lec, []).append((anchor, old, new))
    done, already, bad, alr = 0, 0, [], []
    for lec, rs in by.items():
        path = SRC / f'{lec}.md'
        text = path.read_text(encoding='utf-8')
        # 同锚同改的 n 条：本讲里恰有 n 处同形时一起落（判读逐页出的，每处一条）
        mult = {r: rs.count(r) for r in rs}
        rs = list(dict.fromkeys(rs))
        # 锚换算用**所有**证人表的修正（ed3 的锚里可能有词后来被 tess 那一轮改掉）
        fixmap = {o: re.sub(r'^[^A-Za-z]+|[^A-Za-z\'’]+$', '', n) for _, o, n in ALLMAP.get(lec, [])}
        for anchor, old, new in reversed(rs):
            toks = body_tokens(text)
            words = [t for _, _, t in toks]
            # 原串可带词前/词后紧粘的残渣（vlm_fixes：«uid → and、mean« → means）；词规则表的原串就是词本身
            m = TOKEN.search(old)
            off, otok = (m.start(), m.group(0)) if m else (0, old)
            na = max(3, len(anchor.split()))          # 锚一般三词；同形多处时生成器会加长
            hits = [k for k, (ta, _, t) in enumerate(toks)
                    if t == otok and text[ta - off:ta - off + len(old)] == old
                    and ' '.join(words[max(0, k - na):k]) == anchor]
            if len(hits) == mult[(anchor, old, new)]:
                for h in reversed(hits):
                    a = toks[h][0] - off
                    text = text[:a] + new + text[a + len(old):]
                    done += 1
                continue
            # 换算后可能多出词（人工表拆词 hornof→horn of），只取最后三个词，与判读时的三词锚同口径
            # 修正表按词全讲统一换算会误伤锚里本来就对的同形词（he→be 一讲里有对有错），
            # 所以每个锚词「换／不换」两种都试（最多 2^na 个候选）
            cands = set()
            for combo in itertools.product(*[{w, fixmap.get(w, w)} for w in anchor.split()]):
                a2 = ' '.join(combo)
                for so, sn in SPANMAP.get(lec, []):      # 人工整串表并回的断词（Abra ham→Abraham）
                    a2 = a2.replace(so, sn)
                cands.add(' '.join(a2.split()[-na:]))
            # 改作按词序列比（人工表拆词的改作是两个词：hornof → horn of）
            new_t = TOKEN.findall(new)
            # 撇号当空格比：判读时 centurion^s 是两个词，symbols 之后成了 centurion's 一个词
            norm = lambda x: ' '.join(re.sub(r"['’]", ' ', x).split())
            st = lambda ws: [w.rstrip("'’") for w in ws]     # 改作后面紧跟的收引号会被 TOKEN 并进词里（me'）
            if new_t and any(st(words[k:k + len(new_t)]) == st(new_t)
                             and (' '.join(words[max(0, k - na):k]) == anchor
                                  or any(norm(' '.join(words[max(0, k - na - 1):k])).endswith(norm(c)) for c in cands))
                             for k in range(len(words))):
                already += 1
                alr.append((lec, anchor, old, len(hits)))
                continue
            bad.append((lec, anchor, old, len(hits)))
        path.write_text(text, encoding='utf-8')
    print(f'落盘 {done} 条；已落过 {already}；定位失败 {len(bad)} {bad[:5]}', file=sys.stderr)
    if done and alr:
        print(f'  （同一轮里既有落盘又有「已落过」，核一下：{alr[:8]}）', file=sys.stderr)
    if bad:
        raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--witness', choices=list(WITNESSES), help='只跑一个证人（默认按序全跑）')
    ap.add_argument('--vlm', action='store_true', help='只落第 ③ 层 vlm_fixes.tsv（symbols 之后）')
    a = ap.parse_args()
    ALLMAP.update(_all_rules())
    _load_spanmap()
    # 「已落过」判断要把锚里被第 ③ 层改过的词也换算进去（锚 teach ils to → teach us to）；
    # 在终态上重跑 ② 层各表时同样要换算，否则 ③ 改过的锚词让 ② 的规则认不出自己
    if VLM_RULES.exists():
        for ln in VLM_RULES.read_text(encoding='utf-8').splitlines():
            if ln.strip() and not ln.startswith('#'):
                lec, anchor, old, new = ln.split('\t')
                m = TOKEN.search(old)
                ALLMAP.setdefault(lec, []).append((anchor, m.group(0) if m else old, new))
    if a.vlm:
        if a.apply:
            apply(VLM_RULES)
        return
    for w in ([a.witness] if a.witness else list(WITNESSES)):
        if a.apply:
            if WITNESSES[w]['rules'].exists():
                apply(WITNESSES[w]['rules'])
        else:
            judge(w)
    if a.apply and not a.witness and MANUAL.exists():
        apply(MANUAL)
    if a.apply and not a.witness and MANUAL_SPANS.exists():
        apply_spans(MANUAL_SPANS)


if __name__ == '__main__':
    main()
