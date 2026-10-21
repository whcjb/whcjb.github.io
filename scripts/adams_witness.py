#!/usr/bin/env python3
"""亚当斯《彼得后书注释》(1633, EEBO-TCP A00665) 缺字的证人判读。

    python3 scripts/adams_witness.py gaps     # TCP → gap_sites.json（每处缺字词 + 上下文）
    python3 scripts/adams_witness.py build    # 证人 hOCR → witness/words_{key}.json
    python3 scripts/adams_witness.py match    # 每处缺字在各证人里定位 → witness_locs.json
    python3 scripts/adams_witness.py judge    # 证人读数 + TCP 残字 → 预填值（不落盘）
    python3 scripts/adams_witness.py sheets [--only todo|all]   # 判读图

证人
----
| 键 | IA item | 是什么 | 用途 |
|---|---|---|---|
| r1862 | expositionuponse00adam（Edinburgh: Nichol 1862，Sherman 修订） | 重排本，现代字体 | OCR 干净，定位 + 读出候选词 |
| r1848 | anexpositionupo00shergoog（London: Bohn 1848，Sherman 修订，哈佛藏本） | 同一修订本的另一印 | 1862 读不出/改写时的后备 |
| bim | bim_early-english-books-…_adams-thomas_1632（EEBO 缩微胶片的灰度扫描） | **与 TCP 同一版** | 看图：原版这一处印的是什么 |

Sherman 本拼写现代化（ſonne→son、then→than），读出的词只当候选，落盘写 1633 的写法。
**落盘规则（用户定，见 memory feedback_no_guess_inference_needs_approval）：只有看图核过、
证人在同一位置明确读出的才可落盘；凡推断（本书用词、上下文）一律列清单待用户同意。**

缺字编号 = TCP 文档顺序里第几个缺字词（gid），TCP 原件不变则编号稳定，判读表按 gid 落。
"""
import argparse
import collections
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'adams_raw' / '2peter'
SRC = RAW / 'src' / 'A00665.xml'
W = RAW / 'witness'
IMG = W / 'img'
TEI = '{http://www.tei-c.org/ns/1.0}'
ITEMS = {'r1862': 'expositionuponse00adam',
         'r1848': 'anexpositionupo00shergoog',
         'bim': 'bim_early-english-books-1475-1640_a-commentary-upon-the-se_adams-thomas_1632'}
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'

GAP_LETTER, GAP_WORD, GAP_SPAN, GAP_FOREIGN, PUNC = '•', '〈◊〉', '〈…〉', '〈Greek〉', '▪'
TOK = re.compile(r'•|〈◊〉|〈…〉|〈Greek〉|▪')


def fold(w):
    """比对口径：两侧同一个函数。长 s 在原版 OCR 里成 f，所以 f 折成 s；u/v、i/j/y、双写、词尾 e 折平。"""
    w = re.sub(r'[^a-z]', '', w.lower().replace('ſ', 's'))
    w = w.replace('v', 'u').replace('j', 'i').replace('y', 'i').replace('f', 's')
    w = re.sub(r'(.)\1+', r'\1', w)
    w = w.replace('ie', 'i').replace('ei', 'i').replace('ee', 'e')
    if len(w) > 3 and w.endswith('e'):
        w = w[:-1]
    return w


# ── 1. TCP → 缺字清单 ─────────────────────────────────────────────────
class Flat:
    """TEI 压平成两条词流：正文（main）与页边旁注（note，每条旁注单独成段）。
    斜体只记不出星号（判读只要文字）；行末断词拼合；ſ→s；duplicate 页丢。"""

    def __init__(self):
        self.main = []          # [str] 片段
        self.notes = []         # [(facs, text)]
        self.facs = None
        self.where = ''         # 最近的 div 头（章、节）

    def text(self, e, out):
        out.append(e.text or '')
        for c in e:
            t = c.tag.replace(TEI, '')
            if t == 'gap':
                r, ext = c.get('reason', ''), c.get('extent', '') or ''
                if r == 'duplicate':
                    pass
                elif r == 'foreign':
                    out.append(GAP_FOREIGN)
                elif (m := re.match(r'(\d+) letters?', ext)):
                    out.append(GAP_LETTER * int(m.group(1)))
                elif (m := re.match(r'(\d+) words?', ext)):
                    out.append(' ' + ' '.join([GAP_WORD] * int(m.group(1))) + ' ')
                elif re.match(r'\d+ (span|line|page)s?', ext):
                    out.append(' ' + GAP_SPAN + ' ')
                else:
                    raise ValueError(c.attrib)
            elif t == 'g':
                ref = c.get('ref')
                if ref in ('char:EOLhyphen', 'char:EOLunhyphen'):
                    while out and out[-1].strip() == '' and '\n' in out[-1]:
                        out.pop()
                    if out and '\n' in out[-1]:
                        out[-1] = out[-1].rstrip()
                    out.append('\x00')          # 拼合点：后面的排版空白要吃掉
                elif ref == 'char:punc':
                    out.append(PUNC)
                elif ref == 'char:V':
                    out.append('U')
                else:                           # cmbAbbrStroke / abque：照录 g 的文字
                    out.append(c.text or '')
            elif t == 'note':
                sub = []
                self.text(c, sub)
                self.notes.append((self.facs, self.where, ''.join(sub)))
                out.append(' ')
            elif t == 'pb':
                self.facs = c.get('facs')
                out.append(f' \x01{self.facs}\x01 ')
            elif t == 'desc':
                pass
            else:
                if t in ('p', 'head', 'item', 'l', 'q', 'bibl', 'epigraph', 'list', 'div', 'trailer'):
                    out.append(' ')
                if t == 'div' and c.get('type') in ('chapter', 'verse', 'part'):
                    self.where = f"{c.get('type')}:{c.get('n')}"
                    out.append(f' \x02{self.where}\x02 ')
                self.text(c, out)
                if t in ('p', 'head', 'item', 'l', 'list', 'div'):
                    out.append(' ')
            out.append(c.tail or '')


def tokens(s):
    """片段 → [(词, facs, where)]；\x00 处把后面的空白吃掉（行末断词拼合）。"""
    s = re.sub(r'\x00\s*', '', s).replace('ſ', 's')
    out, facs, where = [], None, ''
    for w in s.split():
        if w.startswith('\x01'):
            facs = w.strip('\x01')
            continue
        if w.startswith('\x02'):
            where = w.strip('\x02')
            continue
        out.append((w, facs, where))
    return out


def gaps():
    root = ET.parse(SRC).getroot()
    f = Flat()
    buf = []
    f.text(root.find(f'{TEI}text'), buf)
    main = tokens(''.join(buf))
    sites = []

    def scan(toks, stream, nidx=None):
        k = 0
        while k < len(toks):
            if not TOK.search(toks[k][0]):
                k += 1
                continue
            j = k
            while j + 1 < len(toks) and TOK.search(toks[j + 1][0]):   # 相邻缺字词并成一处
                j += 1
            words = [t[0] for t in toks[k:j + 1]]
            sites.append({'stream': stream, 'note': nidx, 'i': k, 'j': j + 1,
                          'tcp': ' '.join(words), 'facs': toks[k][1], 'where': toks[k][2],
                          'left': [t[0] for t in toks[max(0, k - 10):k]],
                          'right': [t[0] for t in toks[j + 1:j + 11]]})
            k = j + 1

    scan(main, 'main')
    for n, (facs, where, txt) in enumerate(f.notes):
        nt = [(w, facs, where) for w, _, _ in tokens(txt)]
        if any(TOK.search(w) for w, _, _ in nt):
            scan(nt, 'note', n)
    for g, s in enumerate(sites):
        s['gid'] = g
        s['kind'] = ('foreign' if GAP_FOREIGN in s['tcp'] else 'span' if GAP_SPAN in s['tcp']
                     else 'word' if GAP_WORD in s['tcp'] else 'punc' if s['tcp'].strip(PUNC + '.,;:') == ''
                     else 'letter')
    (RAW / 'gap_sites.json').write_text(json.dumps(sites, ensure_ascii=False, indent=0), encoding='utf-8')
    (RAW / 'tcp_main_tokens.json').write_text(json.dumps(main, ensure_ascii=False), encoding='utf-8')
    c = collections.Counter((s['stream'], s['kind']) for s in sites)
    print(f'正文 {len(main)} 词；旁注 {len(f.notes)} 条；缺字词 {len(sites)}：{dict(c)}', file=sys.stderr)


# ── 2. 证人 hOCR → 词流 ──────────────────────────────────────────────
RE_PAGE = re.compile(r'<div class="ocr_page" id="page_(\d+)" title="[^"]*?bbox 0 0 (\d+) (\d+)')
RE_WORD = re.compile(r'<span class="ocrx_word" id="[^"]+" title="bbox (\d+) (\d+) (\d+) (\d+)[^"]*">([^<]*)</span>')


def _download(url, dest):
    if dest.exists() and dest.stat().st_size > 0:
        return
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    tmp = dest.with_suffix('.part')
    with urllib.request.urlopen(req, timeout=600) as r, open(tmp, 'wb') as fo:
        while (b := r.read(1 << 20)):
            fo.write(b)
    tmp.rename(dest)


def build(keys):
    W.mkdir(parents=True, exist_ok=True)
    for key in keys:
        item = ITEMS[key]
        for suf in ('_hocr.html', '_scandata.xml'):
            _download(f'https://archive.org/download/{item}/{item}{suf}', W / f'{item}{suf}')
        text = (W / f'{item}_hocr.html').read_text(encoding='utf-8', errors='replace')
        starts = [(m.start(), int(m.group(1)), int(m.group(2)), int(m.group(3)))
                  for m in RE_PAGE.finditer(text)] + [(len(text), 0, 0, 0)]
        words = []
        for i in range(len(starts) - 1):
            s, leaf, pw, ph = starts[i]
            for m in RE_WORD.finditer(text, s, starts[i + 1][0]):
                t = html.unescape(m.group(5)).strip()
                if not t:
                    continue
                x0, y0, x1, y1 = map(int, m.group(1, 2, 3, 4))
                if words and words[-1]['t'].endswith('-') and len(words[-1]['t']) > 2 \
                        and t[:1].islower():
                    words[-1]['t'] = words[-1]['t'][:-1] + t
                    words[-1]['k'] = fold(words[-1]['t'])
                    continue
                words.append({'t': t, 'k': fold(t), 'leaf': leaf, 'pw': pw, 'ph': ph,
                              'x': x0, 'y': y0, 'w': x1 - x0, 'h': y1 - y0})
        (W / f'words_{key}.json').write_text(json.dumps(words), encoding='utf-8')
        print(f'{key}: {len(words)} 词', file=sys.stderr)


# ── 3. 定位 ──────────────────────────────────────────────────────────
class Stream:
    def __init__(self, key):
        self.key = key
        self.ws = json.loads((W / f'words_{key}.json').read_text())
        self.keys = [w['k'] for w in self.ws]
        self.tri = collections.defaultdict(list)
        for k in range(len(self.keys) - 2):
            self.tri[(self.keys[k], self.keys[k + 1], self.keys[k + 2])].append(k)

    def find(self, left, right, near=None, span=60000):
        """两侧三词组投票定位；near=期望位置（按全书比例/前一处定位推出），只在其附近找。"""
        L = [fold(w) for w in left if not TOK.search(w) and fold(w)]
        R = [fold(w) for w in right if not TOK.search(w) and fold(w)]
        votes = collections.Counter()
        for t in range(len(L) - 2):
            for k in self.tri.get(tuple(L[t:t + 3]), ())[:80]:
                if near is None or abs(k - near) < span:
                    votes[(k + len(L) - t) // 4] += 1
        for t in range(len(R) - 2):
            for k in self.tri.get(tuple(R[t:t + 3]), ())[:80]:
                if near is None or abs(k - near) < span:
                    votes[(k - t - 1) // 4] += 1
        best = None
        for bucket, v in votes.most_common(4):
            if v < 2:
                break
            c = bucket * 4
            r = locate(self.keys, L, R, max(0, c - 18), min(len(self.ws), c + 22))
            if r and (not best or r[2] > best[2]):
                best = r
        return best


def locate(keys, L, R, lo, hi):
    """左块紧贴缺字左边、右块紧贴右边，中间隔 0–8 词。→ (i, j, 覆盖率)"""
    if len(L) < 2 or len(R) < 2:
        return None
    seg = keys[lo:hi]
    sm = SequenceMatcher(None, seg, L + ['\x00'] + R, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size]
    lb = [b for b in blocks if b.b < len(L)]
    rb = [b for b in blocks if b.b > len(L)]
    if not lb or not rb:
        return None
    l = max(lb, key=lambda b: (b.b + b.size, b.size))
    r = min(rb, key=lambda b: (b.b, -b.size))
    i = lo + l.a + l.size + (len(L) - (l.b + l.size))
    j = lo + r.a - (r.b - len(L) - 1)
    if not (0 <= j - i <= 8):
        return None
    cov = min(sum(b.size for b in lb) / len(L), sum(b.size for b in rb) / len(R))
    return i, j, round(cov, 2)


def page_box(ws, i, j):
    g = ws[min(i, len(ws) - 1)]
    span = [x for x in range(max(0, i - 3), min(len(ws), j + 3)) if ws[x]['leaf'] == g['leaf']]
    e = ws[max(i, min(j, len(ws)) - 1)]
    nb = [ws[i - 1]['t'] if i > 0 else '', ws[j]['t'] if j < len(ws) else '']
    return {'nb': nb, 'leaf': g['leaf'], 'pw': g['pw'], 'gx': g['x'], 'gy': g['y'], 'gh': g['h'],
            'gx1': e['x'] + e['w'] if e['leaf'] == g['leaf'] and abs(e['y'] - g['y']) < g['h'] else g['x'] + g['w'],
            'box': [min(ws[x]['x'] for x in span), min(ws[x]['y'] for x in span),
                    max(ws[x]['x'] + ws[x]['w'] for x in span), max(ws[x]['y'] + ws[x]['h'] for x in span)]}


def match(keys):
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    nmain = len(json.loads((RAW / 'tcp_main_tokens.json').read_text(encoding='utf-8')))
    streams = {k: Stream(k) for k in keys}
    old = {}
    f = RAW / 'witness_locs.json'
    if f.exists():
        old = {r['gid']: r for r in json.loads(f.read_text(encoding='utf-8'))}
    out = []
    last = {k: None for k in keys}
    for s in sites:
        rec = old.get(s['gid'], {k: v for k, v in s.items() if k not in ('i', 'j')})
        for k, st in streams.items():
            # 期望位置：正文按前一处成功定位往后推；旁注没有可靠的顺序位置，全书找
            near = None
            if s['stream'] == 'main':
                near = last[k] if last[k] is not None else int(s['i'] / nmain * len(st.ws))
            r = st.find(s['left'], s['right'], near) if near is not None else st.find(s['left'], s['right'])
            if r is None and near is not None:
                r = st.find(s['left'], s['right'])
            if r:
                i, j, sc = r
                rec[k] = {'read': ' '.join(w['t'] for w in st.ws[i:j]), 'score': sc, **page_box(st.ws, i, j)}
                if s['stream'] == 'main':
                    last[k] = i
            else:
                rec.pop(k, None)
        out.append(rec)
    f.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    for k in keys:
        n = sum(k in r for r in out)
        print(f'{k}: 定位 {n}/{len(out)}', file=sys.stderr)


def relocate(keys):
    """第一轮没定位到的：在前后最近的已定位缺字之间（证人词流里的一个窗口）找，
    左右任一侧 4 词以上连续对上即可（单侧定位，判读图上标出）。"""
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    for k in keys:
        st = Stream(k)
        # 用 leaf+gy 反查词流下标太慢；直接对已定位记录重算一遍 find 拿下标
        pos = {}
        for r in locs:
            if k in r and r['stream'] == 'main':
                f = st.find(r['left'], r['right'])
                if f:
                    pos[r['gid']] = f[0]
        mains = [r for r in locs if r['stream'] == 'main']
        found = 0
        for n, r in enumerate(mains):
            if k in r:
                continue
            lo = next((pos[m['gid']] for m in reversed(mains[:n]) if m['gid'] in pos), 0)
            hi = next((pos[m['gid']] for m in mains[n + 1:] if m['gid'] in pos), len(st.ws))
            if hi - lo > 20000:
                continue
            L = [fold(w) for w in r['left'] if not TOK.search(w) and fold(w)][-6:]
            R = [fold(w) for w in r['right'] if not TOK.search(w) and fold(w)][:6]
            seg = st.keys[lo:hi + 1]
            best = None
            for side, pat in (('L', L), ('R', R)):
                if len(pat) < 4:
                    continue
                sm = SequenceMatcher(None, seg, pat, autojunk=False)
                m = sm.find_longest_match(0, len(seg), 0, len(pat))
                if m.size >= 4 and (not best or m.size > best[2]):
                    if side == 'L':
                        i = lo + m.a + (len(pat) - m.b)
                    else:
                        i = lo + m.a - m.b - 1
                    best = (side, max(0, i), m.size)
            if best:
                side, i, sz = best
                j = i + max(1, len(r['tcp'].split()))
                r[k] = {'read': ' '.join(w['t'] for w in st.ws[i:j]), 'score': round(sz / 6, 2),
                        'side': side, **page_box(st.ws, i, j)}
                found += 1
        print(f'{k}: 补定位 {found}', file=sys.stderr)
    (RAW / 'witness_locs.json').write_text(json.dumps(locs, ensure_ascii=False, indent=0), encoding='utf-8')


# ── 4. 自动预读（只当判读图上的预填值，不落盘）────────────────────────
DEC_W = RAW / 'gap_decisions_witness.tsv'
PUNCT = '.,;:!?()[]\'"‘’“”'


def corpus():
    """本书（TCP 正文）的词形频次：落盘写 1633 的拼法，证人读数只负责在这里挑一个。"""
    main = json.loads((RAW / 'tcp_main_tokens.json').read_text(encoding='utf-8'))
    freq = collections.Counter()
    for w, _, _ in main:
        if TOK.search(w):
            continue
        c = w.strip(PUNCT)
        if c:
            freq[c] += 1
    byfold = collections.defaultdict(collections.Counter)
    for w, n in freq.items():
        byfold[fold(w)][w] += n
    return freq, byfold


def fold2(w):
    """判读比对用（TCP 语料 ↔ 1862 现代铅字，两边都是干净文字）：只放宽古今**拼法**差异——
    长 s、u/v、i/j、双写、词尾 e、-es/-s（sinne/sin、remaines/remains、hee/he）。
    不折 f→s（fift≠fist）、不折 y→i 与 ie→i（yet≠it、eye≠ye≠I、yes≠is）。"""
    w = re.sub(r'[^a-z]', '', w.lower().replace('ſ', 's'))
    w = w.replace('v', 'u').replace('j', 'i')
    if len(w) > 3:                                  # 词中 y≈i（mercy/mercie、bodyes/bodies），短词不动（yet/eye）
        w = w[0] + w[1:].replace('y', 'i')
    w = re.sub(r'([^o])\1+', r'\1', w)             # 双写折平，oo 不折（good≠god、too≠to）
    if len(w) > 2 and w.endswith('e'):
        w = w[:-1]
    w = re.sub(r'ie$', 'i', w)
    w = re.sub(r'(es|ies)$', lambda m: 's' if m.group(0) == 'es' else 'is', w)
    return w


def gap_regex(core):
    """TCP 的 extent（几个字母）是录入员的估计，不精确：n 个 • 放宽到 max(1,n-1)…n+1 个字母。"""
    out = []
    for m in re.finditer(r'•+|▪+|[^•▪]+', core):
        g = m.group(0)
        if g[0] == GAP_LETTER:
            n = len(g)
            out.append(f'[A-Za-z]{{{max(1, n - 1)},{n + 1}}}')
        elif g[0] == PUNC:
            out.append(r'[.,;:!?]?')
        else:
            out.append(re.escape(g))
    return re.compile('^' + ''.join(out) + '$', re.I)


def split_punct(tok):
    lead = re.match(r'^[(\[‘“]*', tok).group(0)
    trail = re.search(r'[.,;:!?)\]’”▪]*$', tok[len(lead):]).group(0)
    core = tok[len(lead):len(tok) - len(trail)] if trail else tok[len(lead):]
    return lead, core, trail


def fix_case(form, core, wit):
    """大小写：TCP 残字有字母就照它（全大写词如 CHRIST 整词大写）；首字母正好缺，取 1862 该词首字母的大小写。"""
    known = [c for c in core if c.isalpha()]
    if known and all(c.isupper() for c in known) and len(known) > 1:
        return form.upper()
    if core and core[0].isalpha():
        return (core[0] + form[1:]) if form[:1].lower() == core[0].lower() else form
    if wit and wit[:1].isupper():
        return form[:1].upper() + form[1:]
    if wit and wit[:1].islower():
        return form[:1].lower() + form[1:]
    return form


_REAL = None


def real_word(w):
    """1862 读数可不可信：OCR 乱码（had→Jiad）多半全书只出现一次、词典里也没有。
    1862 全书出现 ≥2 次、或系统词典有（含去掉常见词尾），才算真词。"""
    global _REAL
    if _REAL is None:
        c = collections.Counter(re.sub(r"[^a-z']", '', x['t'].lower())
                                for x in json.loads((W / 'words_r1862.json').read_text()))
        try:
            d = {l.strip().lower() for l in open('/usr/share/dict/words')}
        except OSError:
            d = set()
        _REAL = (c, d)
    c, d = _REAL
    k = re.sub(r"[^a-z']", '', w.lower())
    if c[k] >= 2:
        return True
    base = re.sub(r"('s|s'|s)$", '', k)
    return any(x in d for x in (k, base, re.sub(r'(es|ed|ing|eth|est|ly)$', '', k)))


def pick(tok, w, freq, byfold):
    """缺字词 tok 与证人同位词 w → 1633 拼法的读法（或 None）。"""
    lead, core, trail = split_punct(tok)
    rx = None if core in (GAP_WORD, '') else gap_regex(core)
    wc = w.strip(PUNCT + '▪')
    fw = fold2(wc)
    if not fw or not real_word(wc):
        return None, False
    forms = [f for f in byfold.get(fw, ()) if rx is None or rx.match(f)]
    if forms:
        # 候选都与证人同形（fold2 口径），挑哪一种拼法：缺口里的原拼法 1862 推不出（要看 1633 原图），
        # 规则只管别把不同的词混了。用本书自己的频次判断「是两个词还是一个词的两种拼法」：
        # 与 1862 逐字同形的写法在本书里也常见（≥ 同类最高频的 15%；本印本 sin 680/sinne 1729、been 210/beene 681 两种都常用，缺口里的拼法只有原图读得清才定得了）→ Adams 两种都用，
        # 是不同的词（the/thee、to/too、of/off、her/here、if/is）→ 取逐字同形；
        # 否则是拼法差异（sin/sinne、been/beene、own/owne）→ 取本书最常用的拼法。
        # TCP 的缺字数是录入员估计，不作依据。
        def norm(x):
            return x.lower().replace('v', 'u').replace('j', 'i')
        top = max(freq.get(f, 0) for f in forms)
        exact = [f for f in forms if norm(f) == norm(wc)
                 and freq.get(f, 0) >= 0.15 * top]
        best = max(exact or forms, key=lambda f: freq.get(f, 0))
        corpus_form = True
    elif rx is None or rx.match(wc):
        best, corpus_form = wc, False      # 语料里没有：证人原词（专名、罕用词），拼写待看图
    else:
        return None, False
    best = fix_case(best, core, wc)
    if PUNC in trail:                       # 认不清的标点：取证人该词后的标点
        trail = trail.replace(PUNC, re.search(r'[.,;:!?]?$', w.rstrip('”’"\'')).group(0))
    return lead + best + trail, corpus_form


def judge():
    freq, _ = corpus()
    byfold = collections.defaultdict(collections.Counter)
    for w, n in freq.items():
        byfold[fold2(w)][w] += n
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    tiers = collections.Counter()
    lines = ['# gid\ttcp\t预填\t档\t依据\tr1862\tbim']
    for rec in locs:
        r62 = rec.get('r1862', {}).get('read', '')
        rbm = rec.get('bim', {}).get('read', '')
        if rec['kind'] in ('foreign', 'span'):
            rec['auto'], rec['tier'] = None, 'X'
            tiers['X:' + rec['kind']] += 1
            lines.append(f"{rec['gid']}\t{rec['tcp']}\t\tX\t{rec['kind']}\t{r62}\t{rbm}")
            continue
        toks = [t for t in rec['tcp'].split() if t.strip(PUNCT + '▪')]
        w62 = [w for w in r62.split() if w.strip(PUNCT)]
        wbm = [w for w in rbm.split() if w.strip(PUNCT)]
        auto, tier, ev = None, 'C', ''
        # 邻词闸：缺字紧邻的前后各一词，1862 同位也得对得上；对不上＝1862 在此改写或把拉丁译成英文
        # （#4155 `Gloriam t•• videre` → 1862 `even to see`，预填 to 是译文的词）
        nb_ok = False
        if 'r1862' in rec and rec['r1862'].get('nb'):
            tl = rec['left'][-1] if rec['left'] else ''
            tr = rec['right'][0] if rec['right'] else ''
            pl, nr = rec['r1862']['nb']
            def same(a, b):
                fa, fb = fold2(a.strip(PUNCT)), fold2(b.strip(PUNCT))
                return (not fa and not fb) or (fa and fb and fa == fb)
            nb_ok = (same(tl, pl) or TOK.search(tl)) and (same(tr, nr) or TOK.search(tr))
        if 'r1862' in rec and len(w62) == len(toks) and nb_ok:
            outs, allcorp, bimok = [], True, len(wbm) == len(toks)
            for t, w, wb in zip(toks, w62, wbm if bimok else w62):
                if not TOK.search(t):
                    if fold2(t) != fold2(w) and fold2(t) and fold2(w):
                        outs = None          # 夹在中间的已知词对不上 → 1862 此处改写过
                        break
                    outs.append(t)
                    continue
                r, corp = pick(t, w, freq, byfold)
                if r is None:
                    outs = None
                    break
                outs.append(r)
                allcorp &= corp
                if bimok and fold2(wb.strip(PUNCT)) != fold2(r.strip(PUNCT + '()[]')):
                    bimok = False
            if outs:
                # 缺口吞了句末标点（#5484 notice 〈◊〉 But → of.）：TCP 该词无标点、1862 同位词带 . ? !、
                # 下一词大写开头 → 补上 1862 的标点
                last = outs[-1]
                m = re.search(r'([.?!])["”’]?$', w62[-1]) if w62 else None
                if m and TOK.search(toks[-1]) and not re.search(r'[.,;:!?)]$', last) \
                        and rec['right'] and rec['right'][0][:1].isupper():
                    outs[-1] = last + m.group(1)
                auto = ' '.join(outs)
                tier = ('A' if bimok else 'B') if allcorp else 'B?'
                ev = 'r1862' + ('+bim' if bimok else '') + ('' if allcorp else ' 非语料词形')
        rec['auto'], rec['tier'] = auto, tier
        rec.pop('cand', None)
        if auto is None and w62:
            # C 档候选：不过闸，逐词按位置（词数不合就整段）挑，读不出的保留 1862 原词；只供判读图显示
            cs = []
            for n, t in enumerate(toks):
                if not TOK.search(t):
                    cs.append(t)
                    continue
                w = w62[n] if len(w62) == len(toks) else ' '.join(w62)
                lead, core, trail = split_punct(t)
                forms = [f for f in byfold.get(fold2(w.strip(PUNCT)), ()) ]
                cs.append(lead + (max(forms, key=lambda f: freq.get(f, 0)) if forms else w.strip(PUNCT)) + trail.replace(PUNC, ''))
            rec['cand'] = ' '.join(cs)
        tiers[tier] += 1
        lines.append(f"{rec['gid']}\t{rec['tcp']}\t{auto or ''}\t{tier}\t{ev}\t{r62}\t{rbm}")
    (RAW / 'witness_locs.json').write_text(json.dumps(locs, ensure_ascii=False, indent=0), encoding='utf-8')
    DEC_W.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'预填档位：{dict(tiers)}', file=sys.stderr)


# ── 5. 判读图 ────────────────────────────────────────────────────────
CROPS = W / 'crops2'
CACHED_ONLY = False      # 判读图只用已下载的整页（下载在后台跑时）


def iiif(key, leaf, x, y, w, h, width):
    """IA 的 IIIF 图像服务按扫描叶号（= hOCR page 序号）直接裁区域，不用下整页。"""
    item = ITEMS[key]
    u = (f'https://iiif.archive.org/image/iiif/3/{item}%2F{item}_jp2.zip%2F{item}_jp2%2F'
         f'{item}_{leaf:04d}.jp2/{x},{y},{w},{h}/{width},/0/default.jpg')
    import time
    for t in range(6):
        try:
            req = urllib.request.Request(u, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception:           # noqa: BLE001  504/超时：退避重试
            if t == 5:
                raise
            time.sleep(3 * (t + 1))


def crop_file(gid, key, loc):
    """缺字词所在行，上下各约一行，左右各留余白；文件缓存在 witness/crops/。"""
    CROPS.mkdir(parents=True, exist_ok=True)
    f = CROPS / f'{gid:05d}_{key}.jpg'
    if f.exists():
        return f
    # 只裁缺字词那一行：左右各约 6 个字高（≈前后两三个词），上下各留半行，看得到上下行的边
    h = max(20, loc.get('gh', 60))
    gx0, gx1 = loc['gx'], max(loc.get('gx1', loc['gx']), loc['gx'] + h)
    X0 = max(0, gx0 - h * 7)
    X1 = min(loc['pw'], gx1 + h * 7)
    Y0 = max(0, loc['gy'] - int(h * 0.9))
    Y1 = loc['gy'] + int(h * 1.9)
    # IIIF 区域裁图在持续负载下极慢（≈15 张/分、频繁 504），改为整页下载（bim 取半尺寸）后本地裁
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    if CACHED_ONLY and not (IMG / f'{key}_{loc["leaf"]:04d}.jpg').exists():
        return None
    im = Image.open(full_page(key, loc['leaf'])).convert('L')
    sc = im.width / loc['pw'] if loc['pw'] else 1.0
    c = im.crop((int(X0 * sc), int(Y0 * sc), int(X1 * sc), int(Y1 * sc)))
    c = c.resize((700, max(1, int(c.height * 700 / c.width))))
    c.save(f, quality=85)
    return f


_ACCESS = {}


def full_page(key, leaf):
    """IA 单页接口 page/n{N} 的 N 只数对外显示的叶，按 scandata 的 addToAccessFormats 换算
    （leighton 踩过：不换算会裁到别页）。整页缓存在 witness/img/。"""
    item = ITEMS[key]
    if item not in _ACCESS:
        sd = (W / f'{item}_scandata.xml').read_text(encoding='utf-8', errors='replace')
        pages = re.findall(r'<page leafNum="(\d+)">(.*?)</page>', sd, re.S)
        acc = [int(n) for n, b in pages if re.search(r'<addToAccessFormats>true', b)]
        _ACCESS[item] = {lf: i for i, lf in enumerate(acc)}
    IMG.mkdir(parents=True, exist_ok=True)
    f = IMG / f'{key}_{leaf:04d}.jpg'
    if not f.exists():
        suf = '_w3720' if key == 'bim' else '_w1500'   # bim 原图 7440 宽取半；1862 现代字体 1500 宽足够（带宽受限，按页大小取舍）
        for t in range(5):
            try:
                _download(f'https://archive.org/download/{item}/page/n{_ACCESS[item][leaf]}{suf}.jpg', f)
                break
            except Exception:       # noqa: BLE001
                if t == 4:
                    raise
                import time
                time.sleep(5 * (t + 1))
    return f


def fetch_pages(gids, keys=('r1862', 'bim'), workers=8):
    from concurrent.futures import ThreadPoolExecutor
    locs = {r['gid']: r for r in json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))}
    need = [(k, lf) for k in keys for lf in sorted({locs[g][k]['leaf'] for g in gids if k in locs[g]})]   # 先 1862 后 bim
    bad = []

    def one(j):
        try:
            full_page(*j)
        except Exception as e:      # noqa: BLE001
            bad.append((j, str(e)[:60]))
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, need))
    print(f'整页 {len(need) - len(bad)}/{len(need)}', bad[:5], file=sys.stderr)


def fetch_crops(gids, keys=('bim', 'r1862'), workers=5):
    from concurrent.futures import ThreadPoolExecutor
    locs = {r['gid']: r for r in json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))}
    jobs = [(g, k, locs[g][k]) for g in gids for k in keys if k in locs[g]]
    bad = []

    def one(j):
        try:
            crop_file(*j)
        except Exception as e:      # noqa: BLE001
            bad.append((j[0], j[1], str(e)[:80]))
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, jobs))
    print(f'裁图 {len(jobs) - len(bad)}/{len(jobs)}', file=sys.stderr)
    for b in bad[:10]:
        print('  取图失败', b, file=sys.stderr)


def sheets(gids, name, per=12):
    """每条：一行文字（编号、TCP 上下文、预填、1862 读数）+ 一行图 [1633 原版 bim | 1862]，各 700 宽。"""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    locs = {r['gid']: r for r in json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))}
    fetch_crops(gids)
    sh = W / 'sheets'
    sh.mkdir(exist_ok=True)
    for f in sh.glob(f'{name}_*.jpg'):
        f.unlink()
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 21)
    width, half = 1404, 700
    rows, n_items, k = [], 0, 0

    def strip(g, key):
        f = CROPS / f'{g:05d}_{key}.jpg'
        if key in locs[g] and f.exists():
            im = Image.open(f).convert('L')
            im = im.resize((half, max(1, int(im.height * half / im.width))))
            return im
        im = Image.new('L', (half, 60), 235)
        ImageDraw.Draw(im).text((6, 18), f'（{key} 未定位/取图失败）', font=font, fill=120)
        return im

    def flush():
        nonlocal rows, k
        if rows:
            Image.fromarray(np.vstack(rows)).save(sh / f'{name}_{k:03d}.jpg', quality=82)
            rows, k = [], k + 1
    for g in gids:
        rec = locs[g]
        head = Image.new('L', (width, 56), 255)
        dr = ImageDraw.Draw(head)
        ctx = ' '.join(rec['left'][-6:]) + ' [[' + rec['tcp'] + ']] ' + ' '.join(rec['right'][:5])
        dr.text((6, 2), f"#{g}  {ctx}"[:140], font=font, fill=0)
        pre = rec.get('auto') or (('候选 ' + rec['cand']) if rec.get('cand') else '?')
        dr.text((6, 29), f"预填 → {pre}   [{rec.get('tier')}]    1862: {rec.get('r1862', {}).get('read', '—')}"[:140],
                font=font, fill=70)
        a_, b_ = strip(g, 'bim'), strip(g, 'r1862')
        hh = max(a_.height, b_.height)
        row = Image.new('L', (width, hh), 255)
        row.paste(a_, (0, 0))
        row.paste(b_, (half + 4, 0))
        rows += [np.array(head), np.array(row), np.full((8, width), 50, np.uint8)]
        n_items += 1
        if n_items % per == 0:
            flush()
    flush()
    # 判读图上显示的预填值另存：记判读时按图上核过的值落，不受之后规则重跑影响
    side = sh / 'shown_prefill.json'
    shown = json.loads(side.read_text()) if side.exists() else {}
    shown.update({str(g): locs[g].get('auto') or locs[g].get('cand') for g in gids})
    side.write_text(json.dumps(shown, ensure_ascii=False))
    print(f'{n_items} 条 → {k} 张 {sh}/{name}_*.jpg', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['gaps', 'build', 'match', 'relocate', 'judge', 'sheets'])
    ap.add_argument('--keys', default='r1862,bim')
    ap.add_argument('--gids', default='')
    ap.add_argument('--name', default='todo')
    a = ap.parse_args()
    keys = a.keys.split(',')
    if a.cmd == 'sheets':
        global CACHED_ONLY
        CACHED_ONLY = True
        gids = [int(x) for x in a.gids.split(',') if x]
        return sheets(gids, a.name)
    {'gaps': gaps, 'build': lambda: build(keys), 'match': lambda: match(keys), 'relocate': lambda: relocate(keys), 'judge': judge}[a.cmd]()


if __name__ == '__main__':
    main()
