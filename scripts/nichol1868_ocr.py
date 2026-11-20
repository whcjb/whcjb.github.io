#!/usr/bin/env python3
"""1868 年爱丁堡 Nichol《清教徒注释丛书》合订本（史密斯诗 1 / 皮尔森诗 27、84、85、87 / 古治诗 116）的 OCR 底层。

IA `davidsblessedman00smit`（Princeton 神学院藏本，452 幅，400dpi，2021×2762）。用法见各发布脚本；本模块只管：
  · parse()  ABBYY XML → 每页的块（双栏各一块）与段（带斜体哨兵、字号、缩进）
  · classify 页眉（页顶单行）／页边经节标记（窄块，如「Ver. 1.]」）／正文（7 号字）／编者脚注（6 号字）
  · tess()   第二证人：对每个正文块裁图跑 tesseract（psm 4，eng），按块缓存
  · repair() 第 ② 层：ABBYY 的非词，在 tesseract 同一位置（difflib 对齐、取最长块为锚）给出真词、且字形相近才换；
             其余照留并记入残字账（old-book-ocr skill：宁可不改）。

注意：IA 的 _hocr.html 是 ABBYY 结果的另一种导出（头部写 LuraDocument XML Exporter for ABBYY FineReader），
不是独立证人，不能拿来对证。
"""
import difflib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import alexander_lexicon as lexmod   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'nichol1868_raw'
SRC = Path.home() / 'Documents' / '论文' / 'nichol1868'
NS = '{http://www.abbyy.com/FineReader_xml/FineReader6-schema-v1.xml}'
IT_ON, IT_OFF = '', ''
IA = 'davidsblessedman00smit'
_LEX = None


def lex():
    global _LEX
    if _LEX is None:
        _LEX = lexmod.build()
    return _LEX


ARCHAIC = re.compile(r'^(.*?)(eth|est|edst|st)$', re.I)


def is_word(t):
    """判词典 + 古体动词词尾（useth、beginneth、goest：词根是真词即算）。"""
    if lexmod.is_word(t, lex()):
        return True
    m = ARCHAIC.match(t)
    if m and len(m.group(1)) >= 2:
        st = m.group(1)
        for c in (st, st + 'e', st[:-1] if len(st) > 3 and st[-1] == st[-2] else None,
                  st[:-1] + 'y' if st.endswith('i') else None):
            if c and lexmod.is_word(c, lex()):
                return True
    return False


def _line(line):
    out = []
    for f in line.iter(NS + 'formatting'):
        s = ''.join(c.text or '' for c in f.iter(NS + 'charParams'))
        if s:
            out.append(IT_ON + s + IT_OFF if f.get('italic') == 'true' else s)
    return ''.join(out)


def _join(lines):
    buf = ''
    for t in (x.strip() for x in lines):
        if not t:
            continue
        if not buf:
            buf = t
            continue
        tail = buf.rstrip(IT_OFF)
        if tail.endswith('-') and t.lstrip(IT_ON)[:1].islower():
            ma, mb = re.search(r'([A-Za-z]+)-$', tail), re.match(r'[a-z]+', t.lstrip(IT_ON))
            if ma and mb and dehyphen(re.match(r'(.+)-(.+)', ma.group(1) + '-' + mb.group(0))).count('-'):
                buf = tail + buf[len(tail):] + t           # 复合词：连字符留着
            else:
                buf = tail[:-1] + buf[len(tail):] + t      # 行尾断词：去连字符直接拼
        else:
            buf += ' ' + t
    return re.sub(IT_OFF + r'(\s*)' + IT_ON, r'\1', buf)


def parse(xml_path):
    """→ {页序(1 起): [block, …]}；block = {l,t,r,b, pars:[{text, fs, attrs, nlines}]}"""
    pages = {}
    idx = 0
    for _, el in ET.iterparse(xml_path, events=('end',)):
        if el.tag != NS + 'page':
            continue
        idx += 1
        blocks = []
        for b in el.iter(NS + 'block'):
            if b.get('blockType') != 'Text':
                continue
            blk = {k: int(b.get(k)) for k in ('l', 't', 'r', 'b')}
            blk['pars'] = []
            for par in b.iter(NS + 'par'):
                lines = list(par.iter(NS + 'line'))
                if not lines:
                    continue
                fss = [f.get('fs') for f in par.iter(NS + 'formatting') for _ in [0]]
                fs = max(set(fss), key=fss.count) if fss else None
                blk['pars'].append(dict(text=_join(_line(l) for l in lines), fs=float(fs) if fs else 0,
                                        attrs=dict(par.attrib), nlines=len(lines)))
            blocks.append(blk)
        pages[idx] = blocks
        el.clear()
    return pages


def kind(blk):
    """runhead：页顶（t<260）；margin：窄块（页边经节标记等）；text：正文栏。"""
    w = blk['r'] - blk['l']
    if blk['t'] < 260 and blk['b'] < 300:
        return 'runhead'
    if w < 420:
        return 'margin'
    return 'text'


# ── 第二证人 ──
def image(idx):
    # ABBYY 第 idx 页 = 扫描第 idx-1 叶；IA 可访问影像剔掉了第 0–2 叶（scandata.xml 标 Delete），所以 n = idx-4
    f = SRC / 'img' / f'n{idx - 4:04d}.jpg'
    if not f.exists() or f.stat().st_size < 10000:
        f.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(5):
            r = subprocess.run(['curl', '-sL', '--http1.1', '-m', '120', '-o', str(f),
                                f'https://archive.org/download/{IA}/page/n{idx - 4}.jpg'])
            if r.returncode == 0 and f.exists() and f.stat().st_size > 10000:
                break
    return f


def tess(idx, bi, blk):
    """正文块裁图 → tesseract 词序列（缓存 WORK/tess/<页>_<块>.txt）。"""
    out = WORK / 'tess' / f'{idx:04d}_{bi}.txt'
    if out.exists():
        return out.read_text(encoding='utf-8')
    out.parent.mkdir(parents=True, exist_ok=True)
    crop = WORK / 'tess' / 'crop.png'
    px, py = 40, 10          # 左右多留：ABBYY 块右界常压在末字母上，留 8px 时 tesseract 每行丢尾字母
    geo = f'{blk["r"] - blk["l"] + 2 * px}x{blk["b"] - blk["t"] + 2 * py}+{max(0, blk["l"] - px)}+{max(0, blk["t"] - py)}'
    subprocess.run(['magick', str(image(idx)), '-crop', geo, '+repage', '-colorspace', 'Gray', str(crop)], check=True)
    r = subprocess.run(['tesseract', str(crop), '-', '--psm', '4', '-l', 'eng'], capture_output=True, text=True)
    txt = r.stdout
    out.write_text(txt, encoding='utf-8')
    return txt


# ── 第 ② 层 ──
WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*[A-Za-z]|[A-Za-z]")


def norm(w):
    return re.sub(r"[^a-z]", '', w.lower())


def repair(text, witness, ledger):
    """ABBYY 段落 text（带斜体哨兵）里的非词 → witness（tesseract 同块全文）同位置的真词。"""
    witness = re.sub(r'-\s*\n\s*(?=[a-z])', '', witness)      # tesseract 行尾断词拼回
    a_tokens = list(WORD.finditer(text.replace(IT_ON, ' ').replace(IT_OFF, ' ')))
    a = [norm(m.group()) for m in a_tokens]
    w_tokens = WORD.findall(witness)
    b = [norm(x) for x in w_tokens]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    rep = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != 'replace' or (i2 - i1) != (j2 - j1) or i2 - i1 > 3:
            continue
        for k in range(i2 - i1):
            orig = a_tokens[i1 + k].group()
            cand = w_tokens[j1 + k]
            if is_word(orig) or not is_word(cand):
                continue
            if difflib.SequenceMatcher(None, orig.lower(), cand.lower()).ratio() < 0.6:
                continue
            # 大小写跟 ABBYY 走（首字母大写的保持）
            if orig[:1].isupper() and cand[:1].islower():
                cand = cand[:1].upper() + cand[1:]
            rep[i1 + k] = cand
    if not rep:
        return text, 0
    # 按 a_tokens 位置在原 text（含哨兵）上替换：哨兵不占 WORD，位置换算用同长度替换串
    plain = text.replace(IT_ON, ' ').replace(IT_OFF, ' ')
    assert len(plain) == len(text)
    out, last = [], 0
    for k in sorted(rep):
        m = a_tokens[k]
        out.append(text[last:m.start()])
        out.append(rep[k])
        ledger.append((m.group(), rep[k]))
        last = m.end()
    out.append(text[last:])
    return ''.join(out), len(rep)


# ── 第 ① 层：字形规则（ABBYY 在这套 1868 年铅字上的系统误读，抽样量出来的） ──
# 只留抽样核过、方向单一的几种；c↔e、l↔i、E→R 之类会把真内容改坏（试跑：soids→solds、com→coin、liut→hut），不收。
GLYPH = [('li', 'h'), ('li', 'b'), ('U', 'll'), ('U', 'li'), ('Hf', 'lif'), ('hf', 'lif'), ('Hv', 'liv'), ('hv', 'liv'), ('Hk', 'lik'),
         ('hk', 'lik'), ('Ht', 'lit'), ('ht', 'lit'), ('m', 'in'), ('i-', 'r'), ('i\'', 'r'), ('j\'', 'y'),
         ('vn', 'wi'), ('v', 'w'), ('tli', 'th'), ('cli', 'ch'), ('wli', 'wh'), ('ji', 'p'), ('jl', 'p'), ('ii', 'u')]
CORPUS = None
# 三个字母以内的高频误读，逐个看过影像才收（短词走规则太容易撞上别的真词）
SHORT = {'aU': 'all', 'AU': 'All', 'wiU': 'will', 'heU': 'hell', 'Ufe': 'life', 'Hfe': 'life', 'hfe': 'life',
         'hve': 'live', 'Hve': 'Live', 'sm': 'sin', 'tliy': 'thy', 'liis': 'his', 'liim': 'him', 'Ul': 'ill', 'wUl': 'will', 'vUl': 'will', 'wiU': 'will',
         'mth': 'with', 'mtli': 'with', 'vnih': 'with', 'hke': 'like', 'Hke': 'Like', 'tiU': 'till', 'tUl': 'till',
         'AMien': 'When', 'AMiat': 'What', 'Eev': 'Rev', 'Dadd': 'David', 'Uve': 'live', 'kmd': 'kind',
         'knovvn': 'known', 'thanksgidng': 'thanksgiving', 'mih': 'with', 'vrA': 'will',
         'Rey': 'Rev', 'Ley': 'Lev', 'Ses': 'Sec'}
# tesseract 在这套铅字上的系统误读（合流后才露出来）：v → y、c → e
GLYPH += [('y', 'v'), ('Y', 'V')]


def roman_fix(tok):
    """读坏的罗马数字（经文出处）：y→v、e→c、I/L→l，归一后是合法罗马数字才认（Ixy→lxv、exliv→cxliv、xliy→xliv）。"""
    if len(tok) < 2 or not re.fullmatch(r'[IlLivxcye]+', tok) or not re.search(r'[ye]|^[IL]', tok):
        return None
    u = tok.replace('y', 'v').replace('e', 'c')
    u = re.sub(r'^[IL]', 'l', u) if u[1:] == u[1:].lower() else u
    if u.lower() != u:
        return None
    return u if lexmod.ROMAN.fullmatch(u) else None


def split_fix(tok):
    """两词粘连（othersthat、froma、shallI）：拆开后两边都是真词、且这个二元组在清教徒语料里出现过 ≥2 次，取唯一最优。"""
    if len(tok) < 5 or not tok.isalpha():
        return None
    d = bigrams()['bi']
    best = []
    for i in range(1, len(tok)):
        a, b = tok[:i], tok[i:]
        if not ((len(a) >= 2 or a in ('a', 'I', 'A', 'O')) and (len(b) >= 2 or b in ('a', 'I'))):
            continue
        if not (is_word(a) and is_word(b)):
            continue
        c = d.get(f'{a.lower()} {b.lower()}', 0)
        if c >= 2:
            best.append((c, a, b))
    best.sort(reverse=True)
    if not best or (len(best) > 1 and best[1][0] * 3 > best[0][0]):
        return None
    return best[0][1] + ' ' + best[0][2]


CLOSED = set('''a an the and or but nor if as at by for from in into of on to unto upon with without within when what which who whom whose
where while that this these those than then thou thee thy thine he him his she her it its we us our ye you your they them their
i me my is are was were be been am hath have had doth do did shall should will would may might can could must not no so'''.split())


def dehyphen(m):
    """行尾断词拼回。拼成的是真词就拼；拼成非词而两半都是真词时：带连字符的写法在本书或清教徒语料里出现过（self-love、
    burnt-offerings）就留连字符；没出现过、且有一半是虚词，是 tesseract 在行尾凭空读出的「-」（when-\nthou），拆成两个词。"""
    a, b = m.group(1), m.group(2)
    if is_word_h(a + b) or not (is_word(a) and is_word(b)):
        return a + b
    h = (a + '-' + b).lower()
    if bigrams()['uni'].get(h, 0) or corpus()[h]:
        return a + '-' + b
    if a.lower() in CLOSED or b.lower() in CLOSED:
        return a + ' ' + b
    return a + '-' + b


def corpus():
    """全书（ABBYY 正文）词频，候选要在书里别处真出现过（语料自证）。"""
    global CORPUS
    if CORPUS is None:
        import collections
        CORPUS = collections.Counter()
        for blocks in load().values():
            for b in blocks:
                for p in b['pars']:
                    CORPUS.update(w.lower() for w in WORD.findall(p['text'].replace(IT_ON, ' ').replace(IT_OFF, ' ')))
    return CORPUS


def glyph_fix(tok):
    """非词 → 按 GLYPH 做一到两处替换，真词候选唯一时返回，否则 None。"""
    if tok in SHORT:
        return SHORT[tok]
    if re.fullmatch(r'I[xvicl]+', tok) and lexmod.ROMAN.match('l' + tok[1:]):   # Ixxxi → lxxxi（l 读成 I）
        return 'l' + tok[1:]
    if is_word(tok) or len(tok) < 4:
        return None
    cands, seen = set(), {tok}
    frontier = [tok]
    for _ in range(2):
        nxt = []
        for t in frontier:
            for a, b in GLYPH:
                i = t.find(a)
                while i >= 0:
                    u = t[:i] + b + t[i + len(a):]
                    if u not in seen:
                        seen.add(u)
                        nxt.append(u)
                        if is_word(u) and corpus()[u.lower()] >= 2:
                            cands.add(u)
                    i = t.find(a, i + 1)
        if cands:
            break
        frontier = nxt
    low = {c.lower() for c in cands}
    return cands.pop() if len(low) == 1 else None


def is_word_h(t):
    """带连字符的复合词：各段都是真词即算真词（door-keeper、free-will）。"""
    if is_word(t):
        return True
    parts = [x for x in re.split(r'[-’\']', t) if x]
    return len(parts) > 1 and all(is_word(x) for x in parts)


# 符号形误读（试跑补文里成批出现，抽样核过上下文）：只在字母中间／词首这类位置生效
SYMBOL = [(re.compile(r"\^+\\'"), 'w'),                                # ^\'ill → will
          (re.compile(r"\^+v(?=[a-zA-Z])"), 'w'),                          # ^vicked → wicked、^vUl → wUl
          (re.compile(r"\^+V(?=[a-z])"), 'W'),
          (re.compile(r"\^+(?=[a-zA-Z])"), ''),                            # ^without → without
          (re.compile(r"(?<=[A-Za-z])\\'?-?(?=[a-z])"), 'v'),              # Da\'id、Sa\-iour、gi\'ing
          (re.compile(r"(?<![A-Za-z])[ji]\)(?=[a-z])"), 'p'),               # j)uttest
          (re.compile(r"(?<=[a-z])[ji]\)(?=[a-z])"), 'p'),                  # prosj)er
          (re.compile(r"(?<=[a-z])l>(?=[a-z])"), 'b'),                     # troul>le
          (re.compile(r"(?<![A-Za-z])\(j(?=[a-z]{3})"), 'g')]                # (jreat → great                      # troul>le


def symbol_repair(text, ledger):
    for rx, rep in SYMBOL:
        def sub(m, rep=rep):
            ledger.append((m.group(), rep))
            return rep
        text = rx.sub(sub, text)
    # 剥掉 ^ 之后留下的 v 开头非词：vicked → wicked（候选必须是真词）
    def vw(m):
        t = m.group()
        u = 'w' + t[1:] if t[0] == 'v' else 'W' + t[1:]
        if not is_word(t) and is_word(u):
            ledger.append((t, u))
            return u
        return t
    return re.sub(r"(?<![A-Za-z])[vV][a-z]+", vw, text)


def rejoin(text, ledger):
    """栏末断词丢了连字符：「evi dence」「occa sion」→ 拼起来是真词、且至少一段不是真词才拼（逐词扫，不用重叠正则）。"""
    out, pos = [], 0
    toks = list(re.finditer(r"[A-Za-z]+", text))
    k = 0
    while k < len(toks):
        m = toks[k]
        if k + 1 < len(toks):
            m2 = toks[k + 1]
            a, b, gap = m.group(), m2.group(), text[m.end():m2.start()]
            if re.fullmatch(r"\s+", gap) and b[:1].islower() and len(a) >= 2 and len(b) >= 2 \
                    and (not is_word(a) or not is_word(b)) and is_word(a + b) and len(a + b) >= 5:
                out.append(text[pos:m.start()])
                out.append(a + b)
                ledger.append((a + gap + b, a + b))
                pos = m2.end()
                k += 2
                continue
        k += 1
    out.append(text[pos:])
    return "".join(out)


def hyphen_fix(t):
    """行中的 a-b：两半都是罗马数字 → 拼（cxxx-vii）；带连字符的写法在语料里没见过、且有一半是虚词 → 拆成两词
    （he-was、out-of：tesseract 把字间污点读成「-」）；某一半是非词 → 那一半走字形规则（loying-kindness）。"""
    if t.count('-') != 1:
        return None
    a, b = t.split('-')
    if not a or not b:
        return None
    if lexmod.ROMAN.fullmatch(a + b) and ROMAN_TOK.match(a) and ROMAN_TOK.match(b):
        return a + b
    if bigrams()['uni'].get(t.lower(), 0) or corpus()[t.lower()] >= 2:
        return None
    if is_word(a) and is_word(b) and ({a.lower(), b.lower()} & (CLOSED - {'a', 'by'})):
        return a + ' ' + b
    fa = a if is_word(a) else glyph_fix(a)
    fb = b if is_word(b) else glyph_fix(b)
    if fa and fb and (fa, fb) != (a, b):
        return fa + '-' + fb
    return None


def glyph_repair(text, ledger):
    text = symbol_repair(text, ledger)
    text = rejoin(text, ledger)
    def sub(m):
        t = m.group()
        if '-' in t:
            f = hyphen_fix(t)
            if f:
                ledger.append((t, f))
                return f
        if is_word_h(t) or len(t) < 2:
            return t
        f = glyph_fix(t) or roman_fix(t) or split_fix(t)
        if f:
            ledger.append((t, f))
            return f
        return t
    return WORD.sub(sub, text)


def disagree(text, witness):
    """两条流都给出真词、但字母不同的位置（真词互换：com/corn、wand/wind）→ [(abbyy, tesseract)]，留给看图判定。"""
    witness = re.sub(r'-\s*\n\s*(?=[a-z])', '', witness)
    a = WORD.findall(text.replace(IT_ON, ' ').replace(IT_OFF, ' '))
    b = WORD.findall(witness)
    sm = difflib.SequenceMatcher(None, [norm(x) for x in a], [norm(x) for x in b], autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'replace' and i2 - i1 == j2 - j1 and i2 - i1 <= 2:
            for k in range(i2 - i1):
                x, y = a[i1 + k], b[j1 + k]
                if is_word_h(x) and is_word_h(y) and norm(x) != norm(y) \
                        and difflib.SequenceMatcher(None, x.lower(), y.lower()).ratio() >= 0.6:
                    out.append((x, y, ' '.join(a[max(0, i1 - 4):i1 + 5])))
    return out


def nonwords(text):
    toks = WORD.findall(text.replace(IT_ON, ' ').replace(IT_OFF, ' '))
    return [t for t in toks if len(t) > 1 and not is_word_h(t)], len(toks)


def printed_page(idx):
    """印本页码；本页页眉读不出时按前后页推（前页 +1 / 后页 −1），卷首不编页的返回 None。"""
    v = _printed(idx)
    if v is None:
        for d in (1, 2, 3):                      # 前后各看三页；前后都读得出、且推得一致才用
            a, b = _printed(idx - d), _printed(idx + d)
            ca, cb = (a + d if a is not None else None), (b - d if b is not None else None)
            if ca is not None or cb is not None:
                v = ca if cb is None or ca == cb or ca is not None and d == 1 else cb
                break
    return v if v and v > 0 else None


def _printed(idx):
    """页眉里的印本页码（页顶小块里的纯数字）；取不到返回 None。"""
    for b in load()[idx]:
        if kind(b) == 'runhead':
            for p in b['pars']:
                t = p['text'].replace(IT_ON, '').replace(IT_OFF, '').strip()
                if re.fullmatch(r'\d{1,3}', t):
                    return int(t)
    return None


def load(path=None):
    cache = WORK / 'abbyy_pages.json'
    if cache.exists():
        return {int(k): v for k, v in json.loads(cache.read_text(encoding='utf-8')).items()}
    pages = parse(str(path or (SRC / 'abbyy.xml')))
    WORK.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(pages, ensure_ascii=False), encoding='utf-8')
    return pages


# ── 合流：字取 tesseract，斜体／分段取 ABBYY（old-book-ocr §3.2d） ──
# 这套扫描上 tesseract 明显更准（原始非词率：皮尔森 1.09% vs ABBYY 3.02%，古治 3.14% vs 5.39%；ABBYY 把
# Return 读成 Eduni、O 读成 0、this 读成 tills）。但 tesseract 有自己的系统错：罗马数字常丢一个 i（Dan. iii → ii）、
# v → y（vow → yow）、c → e（crieth → erieth）。所以按块整体对齐后逐词定夺：
#   · 一边真词一边非词 → 取真词；罗马数字 → 取 ABBYY；
#   · 两边都是真词而读法不同 → judge 回调（古治有 TCP 投票）→ 二元词频（非 OCR 来源的清教徒英文语料）→ 默认 tesseract；
#   · ABBYY 有而 tesseract 没有的词（tesseract 吞词）→ 是真词就补回；tesseract 多出的词 → 在段内、是真词才留。
# 段的边界、斜体范围一律跟 ABBYY 走：ABBYY 的词映射到 tesseract 的词，斜体词连成段再包哨兵。
ROMAN_TOK = re.compile(r'^[ivxlcIVXLC]+$')
BIGRAM = None
FUNC = {'a', 'i', 'o', 'an', 'as', 'at', 'be', 'by', 'do', 'he', 'if', 'in', 'is', 'it', 'me', 'my', 'no', 'of', 'on',
        'or', 'so', 'to', 'up', 'us', 'we', 'ye'}


def bigrams():
    """Owen、Manton、Matthew Henry 英文版（AGES／CCEL 排版本，非 OCR）的词频与二元词频，缓存 WORK/bigrams.json。"""
    global BIGRAM
    if BIGRAM is not None:
        return BIGRAM
    cache = WORK / 'bigrams.json'
    if cache.exists():
        d = json.loads(cache.read_text(encoding='utf-8'))
    else:
        import collections
        uni, bi = collections.Counter(), collections.Counter()
        for top in ('owen', 'manton', 'mhenry'):
            for f in (ROOT / top).rglob('*.md'):
                if '/zh/' in str(f):
                    continue
                for para in re.split(r'\n\s*\n', f.read_text(encoding='utf-8', errors='ignore')):
                    ws = [w.lower() for w in WORD.findall(re.sub(r'<[^>]+>', ' ', para))]
                    uni.update(ws)
                    bi.update(f'{x} {y}' for x, y in zip(ws, ws[1:]))
        d = dict(uni={k: v for k, v in uni.items() if v >= 2}, bi={k: v for k, v in bi.items() if v >= 2})
        cache.write_text(json.dumps(d), encoding='utf-8')
    BIGRAM = d
    return d


def lm_pick(a, t, left, right):
    """两个真词二选一：比 (左词, 候选)、(候选, 右词) 的二元词频；分不出来返回 None。"""
    d = bigrams()
    def score(w):
        w = w.lower()
        s = d['bi'].get(f'{left.lower()} {w}', 0) + d['bi'].get(f'{w} {right.lower()}', 0)
        return s
    sa, st = score(a), score(t)
    if sa == st:
        ua, ut = d['uni'].get(a.lower(), 0), d['uni'].get(t.lower(), 0)
        if max(ua, ut) >= 20 and min(ua, ut) * 50 < max(ua, ut):     # 一边是罕用词（tins/tills 对 this）
            return a if ua > ut else t
        return None
    if max(sa, st) >= 3 and min(sa, st) * 3 <= max(sa, st):
        return a if sa > st else t
    return None


def _okword(w):
    return (len(w) >= 2 or w.lower() in FUNC) and is_word_h(w)


def merge_block(pars, witness, judge=None, ledger=None):
    """pars：ABBYY 一个正文块的各段（带斜体哨兵）；witness：同块 tesseract 全文 → 合流后的各段文本（带斜体哨兵）。
    对不上的段（与 tesseract 等同的词不到四成）照 ABBYY 原样返回，由下游 repair 处理。"""
    ledger = ledger if ledger is not None else []
    W = re.sub(r"([A-Za-z]+)-[ \t]*\n[ \t]*([a-z][a-z]*)", dehyphen, witness)   # 行尾断词拼回（空行保留，切段用）
    T = list(WORD.finditer(W))
    TW = [m.group() if is_word(m.group()) else (roman_fix(m.group()) or m.group()) for m in T]   # exvi → cxvi
    A = []                                                        # (段号, 词, 是否斜体, 段内 start, end)
    for pi, text in enumerate(pars):
        it = False
        plain = []
        for ch in text:
            if ch == IT_ON:
                it = True
                plain.append(' ')
            elif ch == IT_OFF:
                it = False
                plain.append(' ')
            else:
                plain.append(ch)
        plain = ''.join(plain)
        flags = []
        st = False
        for ch in text:
            if ch == IT_ON:
                st = True
            elif ch == IT_OFF:
                st = False
            flags.append(st)
        ms = list(WORD.finditer(plain))
        for k, m in enumerate(ms):
            nxt = ms[k + 1].start() if k + 1 < len(ms) else m.end()
            A.append((pi, m.group(), flags[m.start()], m.start(), m.end(), re.sub(r'\s+', ' ', plain[m.end():nxt]) or ' '))
    if not A or not T:
        return list(pars)
    sm = difflib.SequenceMatcher(None, [norm(x[1]) for x in A], [norm(x) for x in TW], autojunk=False)
    ops = sm.get_opcodes()
    # 每个 ABBYY 词 → 输出词表里的 (词, 斜体, 来源 T 下标或 None)
    seq = {pi: [] for pi in range(len(pars))}                     # 段号 → [(word, italic, tidx, pre, post)]
    eq = {pi: 0 for pi in range(len(pars))}
    tot = {pi: 0 for pi in range(len(pars))}
    for x in A:
        tot[x[0]] += 1

    def ctx(i, d):
        k = i + d
        return A[k][1] if 0 <= k < len(A) else ''

    for oi, (tag, i1, i2, j1, j2) in enumerate(ops):
        if tag == 'equal':
            for k in range(i2 - i1):
                pi = A[i1 + k][0]
                eq[pi] += 1
                seq[pi].append((TW[j1 + k], A[i1 + k][2], j1 + k, None, i1 + k))
        elif tag == 'replace':
            if i2 - i1 == j2 - j1:
                for k in range(i2 - i1):
                    a, t = A[i1 + k][1], TW[j1 + k]
                    pi = A[i1 + k][0]
                    if ROMAN_TOK.match(a) and ROMAN_TOK.match(t):
                        # 罗马数字：TCP 等证人先判；判不了取 ABBYY（tesseract 常丢一个 i，抽样 ABBYY 对的多）
                        w = judge(a, t, [x[1] for x in A[max(0, i1 + k - 3):i1 + k]], [x[1] for x in A[i1 + k + 1:i1 + k + 4]]) \
                            if judge else None
                        w = w or a
                        # ABBYY 的数字前紧贴污点符号（vi 读成 \i、^i）：它丢了一个字母，tesseract 的更长读法是对的
                        prev = A[i1 + k - 1][5] if i1 + k > 0 else ''
                        if w == a and len(t) > len(a) and t.endswith(a) and re.search(r'[\\^`~|]\s*$', prev):
                            w = t
                    elif _okword(t) and not _okword(a):
                        w = t
                    elif _okword(a) and not _okword(t):
                        w = a
                    elif _okword(a) and _okword(t):
                        w = None
                        if judge:
                            w = judge(a, t, [x[1] for x in A[max(0, i1 + k - 3):i1 + k]], [x[1] for x in A[i1 + k + 1:i1 + k + 4]])
                        if w is None:
                            w = lm_pick(a, t, ctx(i1 + k, -1), ctx(i1 + k, 1)) or t
                        if w != t:
                            ledger.append(('keepA', a, t))
                    else:
                        w = t
                    seq[pi].append((w, A[i1 + k][2], j1 + k, None, i1 + k))
            else:
                ta = [TW[j] for j in range(j1, j2)]
                aa = [A[i][1] for i in range(i1, i2)]
                pis = [A[i][0] for i in range(i1, i2)]
                usea = all(_okword(x) for x in aa) and not all(_okword(x) for x in ta)
                if not usea and len(aa) > len(ta) and all(_okword(x) for x in aa) \
                        and norm(''.join(aa)) == norm(''.join(ta)):
                    # 只差空格／连字符（tesseract 把字间污点读成「-」：he-was、a-man）：带连字符的写法没在语料里见过就取 ABBYY
                    usea = not any('-' in x and (bigrams()['uni'].get(x.lower(), 0) or corpus()[x.lower()]) for x in ta)
                if usea or len(set(pis)) > 1:                     # 跨段的不等长替换：保守，取 ABBYY
                    for i in range(i1, i2):
                        seq[A[i][0]].append((A[i][1], A[i][2], None, A[i][5], i))
                else:
                    itf = sum(A[i][2] for i in range(i1, i2)) * 2 >= (i2 - i1)
                    for j in range(j1, j2):
                        seq[pis[0]].append((TW[j], itf, j, None, None))
        elif tag == 'delete':                                     # tesseract 吞词：真词补回
            for i in range(i1, i2):
                a = A[i][1]
                if _okword(a) or len(a) >= 4:
                    seq[A[i][0]].append((a, A[i][2], None, A[i][5], i))
                    ledger.append(('fillA', a, ''))
        elif tag == 'insert':                                     # tesseract 多出的词：两侧同段、全是真词才留
            if 0 < i1 < len(A) and A[i1 - 1][0] == A[i1][0] and j2 - j1 <= 4 \
                    and all(_okword(T[j].group()) and (len(T[j].group()) >= 2 or T[j].group() in 'OAI')
                            for j in range(j1, j2)):
                pi = A[i1][0]
                itf = A[i1 - 1][2] and A[i1][2]
                for j in range(j1, j2):
                    seq[pi].append((TW[j], itf, j, None, None))
                    ledger.append(('insT', TW[j], ''))
    out = []
    for pi, text in enumerate(pars):
        items = seq[pi]
        if not items or tot[pi] == 0 or eq[pi] < 0.4 * tot[pi]:
            out.append(text)
            continue
        out.append(_build(items, W, T, text, [x[5] for x in A], bool(NUMSTART.match(text.replace(IT_ON, ''))),
                          pi + 1 < len(pars) and bool(NUMSTART.match(pars[pi + 1].replace(IT_ON, '')))))
    return out


def _split_gap(gap, num):
    """两段之间的 tesseract 间隙 → (上段段尾, 下段段首)。有空行就在空行处切；否则下段段首只认开引号／括号，
    ABBYY 的下段以序号起头时（num）再认「12.」这样的序号——不然经文出处末尾的节号会被分给下一段。"""
    m = re.search(r'\n[ \t]*\n', gap)
    if m:
        tail, lead = gap[:m.start()], gap[m.end():]
    else:
        m = re.search(r'(' + (r'(?:\(?\d+\.\)?\s*)?' if num else '') + r'[‘“\'"(\[]*)\s*$', gap)
        tail, lead = gap[:m.start(1)], m.group(1)
    tail = re.sub(r'\s+', ' ', tail).strip()
    lead = re.sub(r'\s+', ' ', lead).strip()
    if re.search(r'[A-Za-z]', tail) or len(tail) > 12:
        tail = ''
    if not re.fullmatch(r'(?:\(?\d+\.\)?)?\s*[‘“\'"(\[]*', lead):
        lead = ''
    return tail, lead


NUMSTART = re.compile(r'^\W*[\dLlI]{1,3}[.,]\)?\s')


def _build(items, W, T, abbyy, asep_all, num, nxtnum):
    """词表 → 段落文本。词间分隔取 tesseract（两个相邻词都来自 tesseract 时），否则补一个空格；
    段首、段尾的标点（序号、引号、末尾的节号与句点）从 tesseract 的段间间隙里切（_split_gap）。"""
    parts = []
    plainA = abbyy.replace(IT_ON, '').replace(IT_OFF, '')
    if items[0][2] is not None:
        j = items[0][2]
        _, lead = _split_gap(W[T[j - 1].end() if j > 0 else 0:T[j].start()], num)
        lead = lead + (' ' if re.search(r'\.\)?$', lead) else '')
    else:
        m = re.match(r'^[^A-Za-z]*', plainA)
        lead = m.group(0).strip() + (' ' if m.group(0).strip() else '')
    parts.append((lead, False))
    for k, (w, it, j, asep, ai) in enumerate(items):
        parts.append((w, it))
        if k + 1 < len(items):
            nj, nai = items[k + 1][2], items[k + 1][4]
            if j is not None and nj is not None and nj == j + 1:
                sep = W[T[j].end():T[nj].start()]
                # 经文出处的节号 tesseract 丢了（Luke i. but），ABBYY 同位置有（Luke i. 6 ; but）：取 ABBYY 的分隔
                # （只认罗马数字之后：ABBYY 会把这套字体的问号读成 1，church? → church 1）
                if ai is not None and nai == ai + 1 and ROMAN_TOK.match(w) and re.fullmatch(r'\.?\s*', sep) \
                        and re.fullmatch(r'\.\s*\d+[\s\d,;:&–-]*', asep_all[ai]):
                    sep = asep_all[ai]
            elif j is not None and nj is not None and nj > j + 1:
                sep = W[T[j].end():T[j + 1].start()]
            elif asep is not None:                                # 取自 ABBYY 的词：分隔也取 ABBYY 的（数字、标点）
                sep = asep
            else:
                sep = ' '
            sep = re.sub(r'\s+', ' ', sep) or ' '
            parts.append((sep, 'sep'))
    j = items[-1][2]
    if j is not None:
        tail, _ = _split_gap(W[T[j].end():T[j + 1].start() if j + 1 < len(T) else len(W)], nxtnum)
    else:
        m = re.search(r'[^A-Za-z]*$', plainA)
        tail = m.group(0).strip() if m else ''
    # 斜体：相邻斜体词连成一段，中间的分隔符算在段内
    s = parts[0][0]
    body = parts[1:]
    out = []
    k = 0
    while k < len(body):
        w, it = body[k]
        if it == 'sep':
            out.append(w)
            k += 1
            continue
        if it:
            run = [w]
            k2 = k + 1
            while k2 + 1 < len(body) and body[k2][1] == 'sep' and body[k2 + 1][1] is True:
                run += [body[k2][0], body[k2 + 1][0]]
                k2 += 2
            out.append(IT_ON + ''.join(run) + IT_OFF)
            k = k2
        else:
            out.append(w)
            k += 1
    t = s + ''.join(out) + tail
    t = re.sub(r'([‘“])\s+', r'\1', t)                         # 开引号后的空白
    t = re.sub(r'(?<=[,.;:])!(?=\s|$)', '', t)                  # 脚注号读成 !：psalm,!
    return t
