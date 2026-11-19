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
            buf = tail[:-1] + buf[len(tail):] + t          # 行尾断词：去连字符直接拼
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
         'knovvn': 'known', 'thanksgidng': 'thanksgiving'}


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


def glyph_repair(text, ledger):
    text = symbol_repair(text, ledger)
    text = rejoin(text, ledger)
    def sub(m):
        t = m.group()
        if is_word_h(t) or len(t) < 2:
            return t
        f = glyph_fix(t)
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
        a, b = _printed(idx - 1), _printed(idx + 1)
        v = a + 1 if a is not None else (b - 1 if b is not None else None)
    return v


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
