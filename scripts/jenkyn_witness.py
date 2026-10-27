#!/usr/bin/env python3
"""詹金《犹大书讲解》(EEBO-TCP A87554 + A87557) 缺字的证人判读。

    python3 scripts/jenkyn_witness.py gaps      # TCP → gap_sites.json（每处缺字词组 + 上下文 + 缺字元素编号）
    python3 scripts/jenkyn_witness.py build     # 证人 hOCR → witness/words_{key}.json
    python3 scripts/jenkyn_witness.py match     # 每处缺字在各证人里定位 → witness_locs.json
    python3 scripts/jenkyn_witness.py relocate  # 没定位到的在前后已定位缺字之间单侧再找
    python3 scripts/jenkyn_witness.py judge     # 证人读数 + TCP 残字 → 预填值（不落盘）
    python3 scripts/jenkyn_witness.py sheets --gids 1,2,3 --name x   # 判读图

证人
----
| 键 | IA item | 是什么 | 管哪部分 |
|---|---|---|---|
| r1865 | expositionuponep00jenk（Edinburgh: Nichol 1865，Sherman 校订） | 重排本，现代铅字 | 全书：定位 + 读词 |
| bim52 | bim_…_jenkyn-william_1652（EEBO 缩微胶片灰度扫描） | **与 TCP 第一部分同一版** | 第一部分：看图 |
| bim56 | bim_…_jenkyn-william_1656（IA 题作 First part，实为第二部分 1656 第二版） | 第二部分的再版 | 第二部分：看图（版次不同，只作旁证） |

1654 年第二部分初版（TCP A87557 的底本）网上没有扫描件。

比对、挑拼法、闸子的函数与 adams_witness.py 同口径（fold / fold2 / gap_regex …直接引用）。
**落盘规则（memory feedback_no_guess_inference_needs_approval）：只有看图核过、证人在同一位置明确读出的
才可落盘；凡推断一律列清单待用户同意。**

缺字编号 gid = 缺字词组在 TCP 文档顺序里的序号；每组记下所含缺字元素的编号 gns
（extract_jenkyn.load_roots 编的 gn），落盘时按 gns 在抽取产物里找位置，不靠串比对。
"""
import argparse
import collections
import html
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adams_witness import (fold, fold2, gap_regex, split_punct, fix_case, locate,  # noqa: E402
                           page_box, _download, UA)
from extract_jenkyn import load_roots, gap_text, TEI, ID_L, ID_R, PUNC, GAP_FOREIGN, GAP_SPAN, GAP_WORD  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'jenkyn_raw' / 'jude'
W = RAW / 'witness'
IMG = W / 'img'
ITEMS = {'r1865': 'expositionuponep00jenk',
         'bim52': 'bim_early-english-books-1641-1700_an-exposition-of-the-epi_jenkyn-william_1652',
         'bim56': 'bim_early-english-books-1641-1700_an-exposition-of-the-epi_jenkyn-william_1656'}
BIM = {1: 'bim52', 2: 'bim56'}
TOK = re.compile(r'•|〈◊〉|〈…〉|〈Greek〉|▪')
RE_ID = re.compile(f'{ID_L}(\\d+){ID_R}')


# ── 1. TCP → 缺字清单 ─────────────────────────────────────────────────
class Flat:
    """TEI 压平成词流：正文（main）与页边旁注（note，每条单独成段）。缺字记号前带编号。"""

    def __init__(self, part):
        self.part = part
        self.notes = []
        self.facs = None
        self.where = ''

    def text(self, e, out):
        out.append(e.text or '')
        for c in e:
            t = c.tag.replace(TEI, '')
            if t == 'gap':
                if c.get('reason') != 'duplicate':
                    s, _ = gap_text(c)
                    lead = s[:len(s) - len(s.lstrip())]
                    out.append(lead + f'{ID_L}{c.get("gn")}{ID_R}' + s.lstrip())
            elif t == 'g':
                ref = c.get('ref')
                if ref in ('char:EOLhyphen', 'char:EOLunhyphen'):
                    while out and out[-1].strip() == '' and '\n' in out[-1]:
                        out.pop()
                    if out and '\n' in out[-1]:
                        out[-1] = out[-1].rstrip()
                    out.append('\x00')
                elif ref == 'char:punc':
                    out.append(f'{ID_L}{c.get("gn")}{ID_R}{PUNC}')
                elif ref == 'char:V':
                    out.append('U')
                else:
                    out.append(c.text or '')
            elif t == 'note':
                sub = []
                self.text(c, sub)
                self.notes.append((self.facs, self.where, ''.join(sub)))
                out.append(' ')
            elif t == 'pb':
                self.facs = c.get('facs')
                out.append(f' \x01{self.facs}\x01 ')
            elif t in ('desc', 'milestone'):
                pass
            else:
                if t in ('p', 'head', 'item', 'l', 'q', 'bibl', 'epigraph', 'list', 'div', 'trailer'):
                    out.append(' ')
                if t == 'div' and c.get('type') in ('verse', 'verses'):
                    self.where = f"{self.part}:{c.get('n')}"
                    out.append(f' \x02{self.where}\x02 ')
                self.text(c, out)
                if t in ('p', 'head', 'item', 'l', 'list', 'div'):
                    out.append(' ')
            out.append(c.tail or '')


def tokens(s):
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


def strip_ids(w):
    return RE_ID.sub('', w)


def gaps():
    roots = load_roots()
    sites, mains = [], []
    for part, root in enumerate(roots, 1):
        f = Flat(part)
        buf = []
        f.text(root.find(f'{TEI}text'), buf)
        main = tokens(''.join(buf))
        mains.append([(strip_ids(w), fa, wh) for w, fa, wh in main])

        def scan(toks, stream, nidx=None):
            k = 0
            while k < len(toks):
                if not TOK.search(toks[k][0]):
                    k += 1
                    continue
                j = k
                while j + 1 < len(toks) and TOK.search(toks[j + 1][0]):
                    j += 1
                words = [t[0] for t in toks[k:j + 1]]
                gns = [int(x) for w in words for x in RE_ID.findall(w)]
                sites.append({'part': part, 'stream': stream, 'note': nidx, 'i': k, 'j': j + 1,
                              'tcp': ' '.join(strip_ids(w) for w in words), 'gns': gns,
                              'facs': toks[k][1], 'where': toks[k][2],
                              'left': [strip_ids(t[0]) for t in toks[max(0, k - 10):k]],
                              'right': [strip_ids(t[0]) for t in toks[j + 1:j + 11]]})
                k = j + 1

        scan(main, 'main')
        for n, (facs, where, txt) in enumerate(f.notes):
            nt = [(w, facs, where) for w, _, _ in tokens(txt)]
            if any(TOK.search(w) for w, _, _ in nt):
                scan(nt, 'note', n)
    for g, s in enumerate(sites):
        s['gid'] = g
        s['kind'] = ('foreign' if GAP_FOREIGN in s['tcp'] else 'span' if GAP_SPAN in s['tcp']
                     else 'word' if GAP_WORD in s['tcp'] else 'letter' if '•' in s['tcp']
                     else 'punc')
    (RAW / 'gap_sites.json').write_text(json.dumps(sites, ensure_ascii=False, indent=0), encoding='utf-8')
    (RAW / 'tcp_main_tokens.json').write_text(json.dumps(mains, ensure_ascii=False), encoding='utf-8')
    c = collections.Counter((s['part'], s['stream'], s['kind']) for s in sites)
    ng = sum(len(s['gns']) for s in sites)
    print(f'缺字词组 {len(sites)}（含缺字元素 {ng}）：{dict(sorted(c.items()))}', file=sys.stderr)


# ── 2. 证人 hOCR → 词流 ──────────────────────────────────────────────
RE_PAGE = re.compile(r'<div class="ocr_page" id="page_(\d+)" title="[^"]*?bbox 0 0 (\d+) (\d+)')
RE_WORD = re.compile(r'<span class="ocrx_word" id="[^"]+" title="bbox (\d+) (\d+) (\d+) (\d+)[^"]*">([^<]*)</span>')


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


def wit_keys(site, keys):
    """这一处该查哪几份证人：1865 全书；胶片按部分。"""
    return [k for k in keys if k == 'r1865' or k == BIM[site['part']]]


def match(keys):
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    mains = json.loads((RAW / 'tcp_main_tokens.json').read_text(encoding='utf-8'))
    n1 = len(mains[0])
    ntot = n1 + len(mains[1])
    streams = {k: Stream(k) for k in keys}
    out = []
    last = {k: None for k in keys}
    for s in sites:
        rec = {k: v for k, v in s.items() if k not in ('i', 'j')}
        for k in wit_keys(s, keys):
            st = streams[k]
            near = None
            if s['stream'] == 'main':
                if last[k] is not None:
                    near = last[k]
                elif k == 'r1865':
                    near = int((s['i'] + (n1 if s['part'] == 2 else 0)) / ntot * len(st.ws))
                else:
                    near = int(s['i'] / len(mains[s['part'] - 1]) * len(st.ws))
            r = st.find(s['left'], s['right'], near) if near is not None else st.find(s['left'], s['right'])
            if r is None and near is not None:
                r = st.find(s['left'], s['right'])
            if r:
                i, j, sc = r
                rec[k] = {'read': ' '.join(w['t'] for w in st.ws[i:j]), 'score': sc, 'wi': i, 'wj': j,
                          **page_box(st.ws, i, j)}
                if s['stream'] == 'main':
                    last[k] = i
        out.append(rec)
    (RAW / 'witness_locs.json').write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    for k in keys:
        tot = sum(1 for r in out if k in wit_keys(r, keys))
        n = sum(k in r for r in out)
        print(f'{k}: 定位 {n}/{tot}', file=sys.stderr)


def relocate(keys):
    """第一轮没定位到的：在前后最近的已定位缺字之间（证人词流里的窗口）找，左右任一侧 4 词以上连续对上即可。"""
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    for k in keys:
        st = Stream(k)
        mains = [r for r in locs if r['stream'] == 'main' and k in wit_keys(r, keys)]
        found = 0
        for n, r in enumerate(mains):
            if k in r:
                continue
            lo = next((m[k]['wi'] for m in reversed(mains[:n]) if k in m), 0)
            hi = next((m[k]['wi'] for m in mains[n + 1:] if k in m), len(st.ws))
            if hi - lo > 20000 or hi < lo:
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
                    i = lo + m.a + (len(pat) - m.b) if side == 'L' else lo + m.a - m.b - 1
                    best = (side, max(0, i), m.size)
            if best:
                side, i, sz = best
                j = i + max(1, len(r['tcp'].split()))
                r[k] = {'read': ' '.join(w['t'] for w in st.ws[i:j]), 'score': round(sz / 6, 2),
                        'side': side, 'wi': i, 'wj': j, **page_box(st.ws, i, j)}
                found += 1
        print(f'{k}: 补定位 {found}', file=sys.stderr)
    (RAW / 'witness_locs.json').write_text(json.dumps(locs, ensure_ascii=False, indent=0), encoding='utf-8')


def leaf_map(locs, key, part):
    """TCP 影像号 facs → 胶片叶号：同一 facs 的正文缺字已在该胶片定位到的叶（众数）；没有的按前后插值。"""
    by = collections.defaultdict(collections.Counter)
    for r in locs:
        if r['part'] == part and r['stream'] == 'main' and key in r and r.get('facs'):
            by[int(r['facs'].split(':')[-1])][r[key]['leaf']] += 1
    known = sorted((f, c.most_common(1)[0][0]) for f, c in by.items())
    def est(f):
        if f in by:
            return [by[f].most_common(1)[0][0]]
        lo = max((x for x in known if x[0] < f), default=None)
        hi = min((x for x in known if x[0] > f), default=None)
        if lo and hi:
            a = lo[1] + (hi[1] - lo[1]) * (f - lo[0]) / (hi[0] - lo[0])
            return [int(a), int(a) + 1]
        return []
    return est


def locate_notes(keys):
    """旁注缺字：TCP 每条旁注是一小段，上下文短，三词组投票定位不上。按 facs 推出胶片叶号，
    在该叶及前后一叶里按字符模糊对齐左右各四词（同 adams locate_bim_by_page）。
    左右都没有字（整条旁注就是一处希腊文）的记 leafonly，判读时看整页页边。"""
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    for part, key in BIM.items():
        if key not in keys:
            continue
        st = Stream(key)
        byleaf = collections.defaultdict(list)
        for k, w in enumerate(st.ws):
            byleaf[w['leaf']].append(k)
        est = leaf_map(locs, key, part)
        found = only = 0
        for r in locs:
            if r['part'] != part or r['stream'] != 'note' or key in r or not r.get('facs'):
                continue
            leaves = est(int(r['facs'].split(':')[-1]))
            if not leaves:
                continue
            cand = [k for lf in range(min(leaves) - 1, max(leaves) + 2) for k in byleaf.get(lf, ())]
            L = ' '.join(fold(w) for w in r['left'][-4:] if not TOK.search(w))
            R = ' '.join(fold(w) for w in r['right'][:4] if not TOK.search(w))
            best = (0, None)
            for side, pat in (('L', L), ('R', R)):
                if len(pat) < 6:
                    continue
                m = len(pat.split())
                for i in range(len(cand) - m):
                    win = ' '.join(st.keys[c] for c in cand[i:i + m])
                    if abs(len(win) - len(pat)) > len(pat):
                        continue
                    sc = SequenceMatcher(None, win, pat, autojunk=False).ratio()
                    if sc > best[0]:
                        k = cand[i + m] if side == 'L' and i + m < len(cand) else cand[max(0, i - 1)]
                        best = (sc, k)
            if best[0] >= 0.6:
                k = best[1]
                r[key] = {'read': st.ws[k]['t'], 'score': round(best[0], 2), 'side': 'page', 'wi': k, 'wj': k + 1,
                          **page_box(st.ws, k, k + 1)}
                found += 1
            else:
                r.setdefault('leafonly', {})[key] = leaves
                only += 1
        print(f'{key}: 旁注按页定位 {found}，只知叶号 {only}', file=sys.stderr)
    (RAW / 'witness_locs.json').write_text(json.dumps(locs, ensure_ascii=False, indent=0), encoding='utf-8')


# ── 4. 自动预读（只当判读图上的预填值，不落盘）────────────────────────
DEC_W = RAW / 'gap_decisions_witness.tsv'
PUNCT = '.,;:!?()[]\'"‘’“”'


def corpus():
    mains = json.loads((RAW / 'tcp_main_tokens.json').read_text(encoding='utf-8'))
    freq = collections.Counter()
    for main in mains:
        for w, _, _ in main:
            if TOK.search(w):
                continue
            c = w.strip(PUNCT)
            if c:
                freq[c] += 1
    return freq


_REAL = None


def real_word(w):
    """1865 读数可不可信：1865 全书出现 ≥2 次、或系统词典有，才算真词（OCR 乱码多半只出现一次）。"""
    global _REAL
    if _REAL is None:
        c = collections.Counter(re.sub(r"[^a-z']", '', x['t'].lower())
                                for x in json.loads((W / 'words_r1865.json').read_text()))
        try:
            d = {ln.strip().lower() for ln in open('/usr/share/dict/words')}
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
    """缺字词 tok 与证人同位词 w → 原书拼法的读法（或 None）。同 adams_witness.pick。"""
    lead, core, trail = split_punct(tok)
    rx = None if core in (GAP_WORD, '') else gap_regex(core)
    wc = w.strip(PUNCT + '▪')
    fw = fold2(wc)
    if not fw or not real_word(wc):
        return None, False
    forms = [f for f in byfold.get(fw, ()) if rx is None or rx.match(f)]
    if forms:
        def nrm(x):
            return x.lower().replace('v', 'u').replace('j', 'i')
        top = max(freq.get(f, 0) for f in forms)
        exact = [f for f in forms if nrm(f) == nrm(wc) and freq.get(f, 0) >= 0.15 * top]
        best = max(exact or forms, key=lambda f: freq.get(f, 0))
        corpus_form = True
    elif rx is None or rx.match(wc):
        best, corpus_form = wc, False
    else:
        return None, False
    best = fix_case(best, core, wc)
    if PUNC in trail:
        trail = trail.replace(PUNC, re.search(r'[.,;:!?]?$', w.rstrip('”’"\'')).group(0))
    return lead + best + trail, corpus_form


def judge():
    freq = corpus()
    byfold = collections.defaultdict(collections.Counter)
    for w, n in freq.items():
        byfold[fold2(w)][w] += n
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    tiers = collections.Counter()
    lines = ['# gid\ttcp\t预填\t档\t依据\tr1865\tbim']
    for rec in locs:
        bk = BIM[rec['part']]
        r65 = rec.get('r1865', {}).get('read', '')
        rbm = rec.get(bk, {}).get('read', '')
        if rec['kind'] in ('foreign', 'span'):
            rec['auto'], rec['tier'] = None, 'X'
            tiers['X:' + rec['kind']] += 1
            lines.append(f"{rec['gid']}\t{rec['tcp']}\t\tX\t{rec['kind']}\t{r65}\t{rbm}")
            continue
        toks = [t for t in rec['tcp'].split() if t.strip(PUNCT + '▪')]
        w65 = [w for w in r65.split() if w.strip(PUNCT)]
        wbm = [w for w in rbm.split() if w.strip(PUNCT)]
        auto, tier, ev = None, 'C', ''
        nb_ok = False
        if 'r1865' in rec and rec['r1865'].get('nb'):
            tl = rec['left'][-1] if rec['left'] else ''
            tr = rec['right'][0] if rec['right'] else ''
            pl, nr = rec['r1865']['nb']

            def same(a, b):
                fa, fb = fold2(a.strip(PUNCT)), fold2(b.strip(PUNCT))
                return (not fa and not fb) or (fa and fb and fa == fb)
            nb_ok = (same(tl, pl) or TOK.search(tl)) and (same(tr, nr) or TOK.search(tr))
        if rec['kind'] == 'punc':
            # 认不清的标点：1865 的标点是 Sherman 按现代习惯改过的，不作证据，一律看原版胶片
            pass
        elif 'r1865' in rec and len(w65) == len(toks) and nb_ok:
            outs, allcorp, bimok = [], True, len(wbm) == len(toks)
            for t, w, wb in zip(toks, w65, wbm if bimok else w65):
                if not TOK.search(t):
                    if fold2(t) != fold2(w) and fold2(t) and fold2(w):
                        outs = None
                        break
                    outs.append(t)
                    continue
                r, corp = pick(t, w, freq, byfold)
                if r is None:
                    outs = None
                    break
                outs.append(r)
                allcorp &= corp
                if bimok and fold(wb.strip(PUNCT)) != fold(r.strip(PUNCT + '()[]')):
                    bimok = False
            if outs:
                last = outs[-1]
                m = re.search(r'([.?!])["”’]?$', w65[-1]) if w65 else None
                if m and TOK.search(toks[-1]) and not re.search(r'[.,;:!?)]$', last) \
                        and rec['right'] and rec['right'][0][:1].isupper():
                    outs[-1] = last + m.group(1)
                auto = ' '.join(outs)
                tier = ('A' if bimok else 'B') if allcorp else 'B?'
                ev = 'r1865' + ('+bim' if bimok else '') + ('' if allcorp else ' 非语料词形')
        rec['auto'], rec['tier'] = auto, tier
        tiers[tier] += 1
        lines.append(f"{rec['gid']}\t{rec['tcp']}\t{auto or ''}\t{tier}\t{ev}\t{r65}\t{rbm}")
    (RAW / 'witness_locs.json').write_text(json.dumps(locs, ensure_ascii=False, indent=0), encoding='utf-8')
    DEC_W.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'预填档位：{dict(tiers)}', file=sys.stderr)


# ── 5. 判读图 ────────────────────────────────────────────────────────
CROPS = W / 'crops'
_ACCESS = {}


def full_page(key, leaf):
    """IA 单页接口 page/n{N} 的 N 只数对外显示的叶，按 scandata 换算。整页缓存在 witness/img/。"""
    item = ITEMS[key]
    if item not in _ACCESS:
        sd = (W / f'{item}_scandata.xml').read_text(encoding='utf-8', errors='replace')
        pages = re.findall(r'<page leafNum="(\d+)">(.*?)</page>', sd, re.S)
        acc = [int(n) for n, b in pages if re.search(r'<addToAccessFormats>true', b)]
        _ACCESS[item] = {lf: i for i, lf in enumerate(acc)} if acc else None
    IMG.mkdir(parents=True, exist_ok=True)
    f = IMG / f'{key}_{leaf:04d}.jpg'
    if not f.exists():
        n = _ACCESS[item][leaf] if _ACCESS[item] else leaf
        suf = '_w2400' if key.startswith('bim') else '_w1500'
        import time
        for t in range(5):
            try:
                _download(f'https://archive.org/download/{item}/page/n{n}{suf}.jpg', f)
                break
            except Exception:       # noqa: BLE001
                if t == 4:
                    raise
                time.sleep(5 * (t + 1))
    return f


def crop_file(gid, key, loc, rows=1.0):
    """缺字词所在行，上下各约半行到一行，左右约七个字高。"""
    CROPS.mkdir(parents=True, exist_ok=True)
    f = CROPS / f'{gid:05d}_{key}.jpg'
    if f.exists():
        return f
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    h = max(14, loc.get('gh', 40))
    gx0, gx1 = loc['gx'], max(loc.get('gx1', loc['gx']), loc['gx'] + h)
    X0 = max(0, gx0 - h * 12)
    X1 = min(loc['pw'], gx1 + h * 12)
    Y0 = max(0, loc['gy'] - int(h * 2.4 * rows))     # 上下各约两行：定位词偶尔落在邻行
    Y1 = loc["gy"] + int(h * 4.6 * rows)
    im = Image.open(full_page(key, loc['leaf'])).convert('L')
    sc = im.width / loc['pw'] if loc['pw'] else 1.0
    c = im.crop((int(X0 * sc), int(Y0 * sc), int(X1 * sc), int(Y1 * sc)))
    c = c.resize((700, max(1, int(c.height * 700 / c.width))))
    c.save(f, quality=85)
    return f


def fetch(gids, workers=6):
    from concurrent.futures import ThreadPoolExecutor
    locs = {r['gid']: r for r in json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))}
    pages = sorted({(k, locs[g][k]['leaf']) for g in gids for k in ITEMS if k in locs[g]})
    bad = []

    def one(j):
        try:
            full_page(*j)
        except Exception as e:      # noqa: BLE001
            bad.append((j, str(e)[:60]))
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, pages))
    jobs = [(g, k, locs[g][k]) for g in gids for k in ITEMS if k in locs[g]]
    for j in jobs:
        try:
            crop_file(*j)
        except Exception as e:      # noqa: BLE001
            bad.append((j[:2], str(e)[:60]))
    print(f'整页 {len(pages)}，裁图 {len(jobs)}，失败 {len(bad)}', bad[:5], file=sys.stderr)


def sheets(gids, name, per=8):
    """每条：两行文字（编号、TCP 上下文、预填、1865 读数）+ 一行图 [原版胶片 | 1865]，各 700 宽。"""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    locs = {r['gid']: r for r in json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))}
    fetch(gids)
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
            return im.resize((half, max(1, int(im.height * half / im.width))))
        im = Image.new('L', (half, 50), 235)
        ImageDraw.Draw(im).text((6, 14), f'（{key} 未定位）', font=font, fill=120)
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
        dr.text((6, 2), f"#{g} p{rec['part']}  {ctx}"[:140], font=font, fill=0)
        dr.text((6, 29), f"预填 → {rec.get('auto') or '?'}   [{rec.get('tier')}]    1865: "
                         f"{rec.get('r1865', {}).get('read', '—')}    胶片OCR: {rec.get(BIM[rec['part']], {}).get('read', '—')}"[:150],
                font=font, fill=70)
        if 'r1865' in rec or BIM[rec['part']] not in rec:
            a_, b_ = strip(g, BIM[rec['part']]), strip(g, 'r1865')
            hh = max(a_.height, b_.height)
            row = Image.new('L', (width, hh), 255)
            row.paste(a_, (0, 0))
            row.paste(b_, (half + 4, 0))
        else:       # 只有胶片（旁注：1865 本删了）：裁图原尺寸 700 宽，放左半，右半留白
            row = Image.new('L', (width, strip(g, BIM[rec['part']]).height), 255)
            row.paste(strip(g, BIM[rec['part']]), (0, 0))
        rows += [np.array(head), np.array(row), np.full((8, width), 50, np.uint8)]
        n_items += 1
        if n_items % per == 0:
            flush()
    flush()
    print(f'{n_items} 条 → {k} 张 {sh}/{name}_*.jpg', file=sys.stderr)


def sheets_notes(gids, name, per=12):
    """旁注判读图：只有胶片可看，两条并排（左右各 700 宽），每条上方两行小字（编号、TCP 上下文）。"""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    locs = {r['gid']: r for r in json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))}
    fetch(gids)
    sh = W / 'sheets'
    sh.mkdir(exist_ok=True)
    for f in sh.glob(f'{name}_*.jpg'):
        f.unlink()
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 17)
    half = 700

    def cell(g):
        rec = locs[g]
        head = Image.new('L', (half, 46), 255)
        dr = ImageDraw.Draw(head)
        dr.text((4, 2), f"#{g} p{rec['part']} " + ' '.join(rec['left'][-4:]) + ' [[' + rec['tcp'] + ']]', font=font, fill=0)
        dr.text((4, 23), ' '.join(rec['right'][:6])[:70], font=font, fill=90)
        f = CROPS / f'{g:05d}_{BIM[rec["part"]]}.jpg'
        im = Image.open(f).convert('L') if f.exists() else Image.new('L', (half, 40), 235)
        im = im.resize((half, max(1, int(im.height * half / im.width))))
        return np.vstack([np.array(head), np.array(im)])
    k = 0
    for i in range(0, len(gids), per):
        chunk = gids[i:i + per]
        rows = []
        for j in range(0, len(chunk), 2):
            a = cell(chunk[j])
            b = cell(chunk[j + 1]) if j + 1 < len(chunk) else np.full((10, half), 255, np.uint8)
            h = max(a.shape[0], b.shape[0])
            pad = lambda x: np.vstack([x, np.full((h - x.shape[0], half), 255, np.uint8)])
            rows.append(np.hstack([pad(a), np.full((h, 4), 50, np.uint8), pad(b)]))
            rows.append(np.full((6, half * 2 + 4), 50, np.uint8))
        Image.fromarray(np.vstack(rows)).save(sh / f'{name}_{k:03d}.jpg', quality=82)
        k += 1
    print(f'{len(gids)} 条 → {k} 张 {sh}/{name}_*.jpg', file=sys.stderr)


def margin_sheets(name='mg', only=None):
    """旁注逐叶判读图（2026-10-27）：旁注上下文短，按词定位常裁偏；改为一叶一张——
    裁出外侧页边栏（上下两半并排），图上方列出这一叶待判的旁注缺字（编号 + TCP 上下文）。
    页边在哪一侧：有定位的取定位词所在一侧，否则数胶片 OCR 词落在左右外侧 22% 里的多少。"""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    Image.MAX_IMAGE_PIXELS = None
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    done = {}
    f = RAW / 'gap_review.tsv'
    if f.exists():
        for ln in f.read_text(encoding='utf-8').splitlines():
            if ln[:1].isdigit():
                done[int(ln.split('\t')[0])] = ln.split('\t')[1]
    words = {k: collections.defaultdict(list) for k in BIM.values()}
    for k in BIM.values():
        for w in json.loads((W / f'words_{k}.json').read_text()):
            words[k][w['leaf']].append(w)
    groups = collections.defaultdict(list)
    for r in locs:
        if r['stream'] != 'note' or done.get(r['gid'], '?') != '?':
            continue
        if only and r['gid'] not in only:
            continue
        k = BIM[r['part']]
        if k in r:
            lf = r[k]['leaf']
            side = ('L' if r[k]['gx'] < r[k]['pw'] / 2 else 'R') if r[k].get('score', 0) >= 0.8 else None
        else:
            continue        # 只知 facs 估叶的不出（估叶常差一两叶，见 relocate_notes）
        groups[(k, lf)].append((r, side))
    sh = W / 'sheets'
    for x in sh.glob(f'{name}_*.jpg'):
        x.unlink()
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 26)
    n = 0
    for (k, lf), items in sorted(groups.items()):
        sides = [s for _, s in items if s]
        ws = words[k][lf]
        pw = ws[0]['pw'] if ws else 1
        # 单页扫描：奇数叶页边在左、偶数叶在右（高分定位统计 bim52 58:6、bim56 135:18）；
        # 同叶有高分定位的以定位为准（重拍页会打乱奇偶）
        side = collections.Counter(sides).most_common(1)[0][0] if sides else ('L' if lf % 2 else 'R')
        try:
            im = Image.open(full_page(k, lf)).convert('L')
        except Exception as e:      # noqa: BLE001
            print('取图失败', k, lf, e, file=sys.stderr)
            continue
        # 左右两侧的页边栏都裁（判侧常错：定位词可能落在正文里），各约 30% 页宽、上下两半，四条并排
        tw = 460
        strips = []
        for x0, x1 in ((0, int(im.width * 0.30)), (int(im.width * 0.70), im.width)):
            col = im.crop((x0, 0, x1, im.height))
            h = col.height // 2 + 60
            for c in (col.crop((0, 0, col.width, h)), col.crop((0, col.height - h, col.width, col.height))):
                strips.append(np.array(c.resize((tw, int(c.height * tw / c.width)))))
        hh = max(x.shape[0] for x in strips)
        parts = []
        for x in strips:
            if x.shape[0] < hh:
                x = np.vstack([x, np.full((hh - x.shape[0], tw), 255, np.uint8)])
            parts += [x, np.full((hh, 5), 40, np.uint8)]
        body = np.hstack(parts)
        head = Image.new('L', (body.shape[1], 34 * len(items) + 40), 255)
        dr = ImageDraw.Draw(head)
        dr.text((6, 4), f'{k} leaf {lf}   左页边 上|下   右页边 上|下', font=font, fill=0)
        for i, (r, _) in enumerate(items):
            ctx = ' '.join(r['left'][-4:]) + ' [[' + r['tcp'] + ']] ' + ' '.join(r['right'][:4])
            dr.text((6, 38 + 34 * i), f"#{r['gid']}  {ctx}"[:110], font=font, fill=60)
        Image.fromarray(np.vstack([np.array(head), body])).save(sh / f'{name}_{n:03d}.jpg', quality=80)
        n += 1
    print(f'{sum(len(v) for v in groups.values())} 条 → {n} 张 {sh}/{name}_*.jpg', file=sys.stderr)


def margin_sheets2(name='mf'):
    """旁注按对开判读图：TCP facs 是缩微胶片的一个对开（左页 + 右页）。叶号取同一 facs 的正文缺字定位
    （三词组投票，可靠）或前后插值，配成 (奇数叶, 奇数叶+1)＝(左页, 右页)；
    裁左页的左页边、右页的右页边（各约四分之一页宽，上下两半），四条并排。"""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    Image.MAX_IMAGE_PIXELS = None
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    done = {}
    for ln in (RAW / 'gap_review.tsv').read_text(encoding='utf-8').splitlines():
        if ln[:1].isdigit():
            done[int(ln.split('\t')[0])] = ln.split('\t')[1]
    groups = collections.defaultdict(list)
    ests = {p: leaf_map(locs, BIM[p], p) for p in BIM}
    for r in locs:
        if r['stream'] != 'note' or done.get(r['gid'], '?') != '?' or not r.get('facs'):
            continue
        groups[(r['part'], int(r['facs'].split(':')[-1]))].append(r)
    sh = W / 'sheets'
    for x in sh.glob(f'{name}_*.jpg'):
        x.unlink()
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 24)
    n = 0
    for (part, facs), items in sorted(groups.items()):
        k = BIM[part]
        lv = ests[part](facs)
        if not lv:
            continue
        lf = min(lv)
        pair = (lf, lf + 1) if lf % 2 else (lf - 1, lf)
        strips = []
        for leaf, side in zip(pair, ('L', 'R')):
            try:
                im = Image.open(full_page(k, leaf)).convert('L')
            except Exception:       # noqa: BLE001
                continue
            x0, x1 = (0, int(im.width * 0.27)) if side == 'L' else (int(im.width * 0.73), im.width)
            col = im.crop((x0, 0, x1, im.height))
            h = col.height // 2 + 60
            for c in (col.crop((0, 0, col.width, h)), col.crop((0, col.height - h, col.width, col.height))):
                strips.append(c.resize((470, int(c.height * 470 / c.width))))
        if not strips:
            continue
        hh = max(x.height for x in strips)
        body = np.hstack([np.vstack([np.array(x), np.full((hh - x.height, 470), 255, np.uint8)]) if x.height < hh
                          else np.array(x) for x in strips for _ in (0,)] if False else
                         sum(([np.vstack([np.array(x), np.full((hh - x.height, 470), 255, np.uint8)]),
                               np.full((hh, 5), 40, np.uint8)] for x in strips), []))
        head = Image.new('L', (body.shape[1], 30 * len(items) + 36), 255)
        dr = ImageDraw.Draw(head)
        dr.text((6, 4), f'{k} facs {facs} 叶 {pair[0]}(左页边 上|下) {pair[1]}(右页边 上|下)', font=font, fill=0)
        for i, r in enumerate(items):
            ctx = ' '.join(r['left'][-4:]) + ' [[' + r['tcp'] + ']] ' + ' '.join(r['right'][:4])
            dr.text((6, 34 + 30 * i), f"#{r['gid']}  {ctx}"[:120], font=font, fill=60)
        Image.fromarray(np.vstack([np.array(head), body])).save(sh / f'{name}_{n:03d}.jpg', quality=80)
        n += 1
    print(f'{sum(len(v) for v in groups.values())} 条 → {n} 张 {sh}/{name}_*.jpg', file=sys.stderr)


def relocate_notes(keys=('bim52', 'bim56'), span=3, thr=0.72):
    """未判的旁注缺字重新定叶（margin_sheets 用）：在 facs 估出的叶号前后 span 叶里，
    拿缺口前后各五词（拼成一串，按字符）与胶片 OCR 词流的同长窗口比，取最高分；
    左右两侧都有字的取两侧之和。分数过 thr 的改写该证人的定位（只改叶号与坐标）。"""
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    done = {}
    for ln in (RAW / 'gap_review.tsv').read_text(encoding='utf-8').splitlines():
        if ln[:1].isdigit():
            done[int(ln.split('\t')[0])] = ln.split('\t')[1]
    for part, key in BIM.items():
        if key not in keys:
            continue
        st = Stream(key)
        byleaf = collections.defaultdict(list)
        for k, w in enumerate(st.ws):
            byleaf[w['leaf']].append(k)
        est = leaf_map(locs, key, part)
        moved = kept = miss = 0
        for r in locs:
            if r['part'] != part or r['stream'] != 'note' or done.get(r['gid'], '?') != '?' or not r.get('facs'):
                continue
            lv = est(int(r['facs'].split(':')[-1]))
            if not lv:
                miss += 1
                continue
            cand = [k for lf in range(min(lv) - span, max(lv) + span + 1) for k in byleaf.get(lf, ())]
            L = ' '.join(fold(w) for w in r['left'][-5:] if not TOK.search(w) and fold(w))
            R = ' '.join(fold(w) for w in r['right'][:5] if not TOK.search(w) and fold(w))
            best = (0, None)
            for side, pat in (('L', L), ('R', R)):
                if len(pat) < 8:
                    continue
                m = len(pat.split())
                for i in range(len(cand) - m):
                    win = ' '.join(st.keys[c] for c in cand[i:i + m])
                    if abs(len(win) - len(pat)) > len(pat) * 0.6:
                        continue
                    sc = SequenceMatcher(None, win, pat, autojunk=False).ratio()
                    if sc > best[0]:
                        best = (sc, cand[min(len(cand) - 1, i + m)] if side == 'L' else cand[max(0, i - 1)])
            if best[0] >= thr:
                k = best[1]
                old = r.get(key, {}).get('leaf')
                r[key] = {'read': st.ws[k]['t'], 'score': round(best[0], 2), 'side': 'note2', 'wi': k, 'wj': k + 1,
                          **page_box(st.ws, k, k + 1)}
                r.pop('leafonly', None)
                moved += old != st.ws[k]['leaf']
                kept += old == st.ws[k]['leaf']
            else:
                miss += 1
        print(f'{key}: 旁注重定叶 改 {moved} / 原叶 {kept} / 找不到 {miss}', file=sys.stderr)
    (RAW / 'witness_locs.json').write_text(json.dumps(locs, ensure_ascii=False, indent=0), encoding='utf-8')


def note_block_sheets(name='nb', per=8):
    """旁注块判读图：以定位词为中心，宽约 30 字高、高约 16 行，两条并排。旁注一行只几个词，
    定位词常落在旁注块的某一行，块够大才能把整条旁注收进来。"""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    Image.MAX_IMAGE_PIXELS = None
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    done = {}
    for ln in (RAW / 'gap_review.tsv').read_text(encoding='utf-8').splitlines():
        if ln[:1].isdigit():
            done[int(ln.split('\t')[0])] = ln.split('\t')[1]
    items = [r for r in locs if r['stream'] == 'note' and done.get(r['gid'], '?') == '?' and BIM[r['part']] in r]
    sh = W / 'sheets'
    for x in sh.glob(f'{name}_*.jpg'):
        x.unlink()
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 17)
    half = 700

    def cell(r):
        k = BIM[r['part']]
        loc = r[k]
        h = max(20, loc.get('gh', 40))
        X0, X1 = max(0, loc['gx'] - h * 14), min(loc['pw'], loc['gx'] + h * 16)
        Y0, Y1 = max(0, loc['gy'] - h * 9), loc['gy'] + h * 9
        im = Image.open(full_page(k, loc['leaf'])).convert('L')
        sc = im.width / loc['pw']
        c = im.crop((int(X0 * sc), int(Y0 * sc), int(X1 * sc), int(Y1 * sc)))
        c = c.resize((half, max(1, int(c.height * half / c.width))))
        head = Image.new('L', (half, 46), 255)
        dr = ImageDraw.Draw(head)
        dr.text((4, 2), f"#{r['gid']} " + ' '.join(r['left'][-4:]) + ' [[' + r['tcp'] + ']]', font=font, fill=0)
        dr.text((4, 23), ' '.join(r['right'][:6])[:70], font=font, fill=90)
        return np.vstack([np.array(head), np.array(c)])
    k = 0
    for i in range(0, len(items), per):
        rows = []
        chunk = items[i:i + per]
        for j in range(0, len(chunk), 2):
            a = cell(chunk[j])
            b = cell(chunk[j + 1]) if j + 1 < len(chunk) else np.full((10, half), 255, np.uint8)
            hh = max(a.shape[0], b.shape[0])
            pad = lambda x: np.vstack([x, np.full((hh - x.shape[0], half), 255, np.uint8)])
            rows += [np.hstack([pad(a), np.full((hh, 4), 40, np.uint8), pad(b)]), np.full((6, half * 2 + 4), 40, np.uint8)]
        Image.fromarray(np.vstack(rows)).save(sh / f'{name}_{k:03d}.jpg', quality=82)
        k += 1
    print(f'{len(items)} 条 → {k} 张 {sh}/{name}_*.jpg', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['gaps', 'build', 'match', 'relocate', 'notes', 'judge', 'sheets', 'nsheets', 'margins', 'margins2', 'renotes', 'nblocks'])
    ap.add_argument('--keys', default='r1865,bim52,bim56')
    ap.add_argument('--gids', default='')
    ap.add_argument('--name', default='todo')
    a = ap.parse_args()
    keys = a.keys.split(',')
    if a.cmd == 'nblocks':
        return note_block_sheets(a.name)
    if a.cmd == 'renotes':
        return relocate_notes()
    if a.cmd == 'margins2':
        return margin_sheets2(a.name)
    if a.cmd == 'margins':
        return margin_sheets(a.name)
    if a.cmd == 'nsheets':
        return sheets_notes([int(x) for x in a.gids.split(',') if x], a.name)
    if a.cmd == 'sheets':
        return sheets([int(x) for x in a.gids.split(',') if x], a.name)
    {'gaps': gaps, 'build': lambda: build(keys), 'match': lambda: match(keys),
     'relocate': lambda: relocate(keys), 'notes': lambda: locate_notes(keys), 'judge': judge}[a.cmd]()


if __name__ == '__main__':
    main()
