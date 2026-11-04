#!/usr/bin/env python3
"""佩特《马可福音注释》(1661, EEBO-TCP A54583) 缺字清单。gaps 一步照搬 dickson_witness.py。

    python3 scripts/petter_witness.py gaps      # en_chapters → gap_sites.json（每组缺字 + 上下文）
    python3 scripts/petter_witness.py anchors   # 原书页码 → IA 叶号锚点 page_leaf.json；need_leaves.json
    python3 scripts/petter_bim_ocr.py           # need_leaves 各叶本地 OCR（只定位用）
    python3 scripts/petter_witness.py build     # → witness/words_bim.json
    python3 scripts/petter_witness.py match     # → witness_locs.json
    python3 scripts/petter_witness.py sheets [--gids a-b] [--name x]   # 判读图

证人
----
| 键 | IA item | 是什么 |
|---|---|---|
| bim | bim_early-english-books-1641-1700_a-learned-pious-and-pra_petter-george_1661（IA40310611-51，915 叶，800 ppi） | EEBO 缩微胶片灰度扫描，**与 TCP 同一卷胶片**（同样止于 p.884）；只此一份 |

**落盘规则（memory feedback_no_guess_inference_needs_approval）：只有看图读出的才落；
推断写 P:xx，列清单待用户同意。**
"""
import argparse
import collections
import html
import json
import re
import sys
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import petter_common as rc  # noqa: E402

ROOT = rc.ROOT
RAW = rc.RAW
W = RAW / 'witness'
IMG = W / 'img'
ITEMS = {'bim': 'bim_early-english-books-1641-1700_a-learned-pious-and-pra_petter-george_1661'}
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'
TOK = rc.TOK
NCTX = 8


def fold(w):
    """比对口径：两侧同一个函数。长 s 在原版 OCR 里成 f，所以 f 折成 s；u/v、i/j/y、双写、词尾 e 折平。"""
    w = re.sub(r'[^a-z]', '', w.lower().replace('ſ', 's'))
    w = w.replace('v', 'u').replace('j', 'i').replace('y', 'i').replace('f', 's')
    w = re.sub(r'(.)\1+', r'\1', w)
    w = w.replace('ie', 'i').replace('ei', 'i').replace('ee', 'e')
    if len(w) > 3 and w.endswith('e'):
        w = w[:-1]
    return w


def gaps():
    sites = []
    main_total = 0
    od = rc.order()
    prev_tail = []
    facs = None
    pnum = None
    for slug in od['order']:
        if True:
            md = rc.read_src(slug)
            margins = [(m.start(), m.end()) for m in re.finditer(r'<span class="pt-margin"[^>]*>.*?</span>', md, re.S)]
            blank = md
            for a, b in margins:
                blank = blank[:a] + ' ' * (b - a) + blank[b:]
            pbs = [(m.start(), int(m.group(1))) for m in re.finditer(r'<span class="pt-pb"[^>]*data-facs="(\d+)"', md)]
            pns = [(m.start(), m.group(1)) for m in re.finditer(r'<span class="pt-pb"[^>]*data-p="(\d+)"', md)]
            for a, b, s, isnote in rc.gap_groups(md):
                f = next((x for p, x in reversed(pbs) if p < a), facs)
                pn = next((x for p, x in reversed(pns) if p < a), pnum)
                extra = {}
                if isnote:
                    na, nb = next((x, y) for x, y in margins if x <= a < y)
                    left = rc.flat_words(md[na:a])
                    right = rc.flat_words(md[b:nb])
                    stream = 'note'
                    # 旁注挂在正文的哪一处：正文上下文，旁注自己定位不到时用它找行
                    extra = {'mleft': (prev_tail + rc.flat_words(blank[:na]))[-NCTX:],
                             'mright': rc.flat_words(blank[nb:])[:NCTX]}
                else:
                    left = prev_tail + rc.flat_words(blank[:a])
                    right = rc.flat_words(blank[b:])
                    stream = 'main'
                sites.append({'gid': len(sites), 'slug': slug, 'stream': stream,
                              'tcp': s, 'left': left[-NCTX:], 'right': right[:NCTX], 'facs': f, 'page': pn,
                              'i': main_total + len(rc.flat_words(blank[:a])), **extra})
            if pbs:
                facs = pbs[-1][1]
            if pns:
                pnum = pns[-1][1]
            w = rc.flat_words(blank)
            prev_tail = w[-NCTX:]
            main_total += len(w)
    (RAW / 'gap_sites.json').write_text(json.dumps(sites, ensure_ascii=False, indent=0), encoding='utf-8')
    (RAW / 'main_words.json').write_text(json.dumps(main_total), encoding='utf-8')
    c = collections.Counter(s['stream'] for s in sites)
    print(f'缺字组 {len(sites)}  {dict(c)}', file=sys.stderr)


def _download(url, dest):
    if dest.exists() and dest.stat().st_size > 0:
        return
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    tmp = dest.with_suffix('.part')
    with urllib.request.urlopen(req, timeout=600) as r, open(tmp, 'wb') as fo:
        while (b := r.read(1 << 20)):
            fo.write(b)
    tmp.rename(dest)


def build():
    """词流取本地重跑的 OCR（dickson_bim_ocr.py → witness/ocr/NNNN.json），按叶序拼接。
    IA 自带 hOCR 漏词太多，只留 scandata（叶号换算）。"""
    W.mkdir(parents=True, exist_ok=True)
    item = ITEMS['bim']
    _download(f'https://archive.org/download/{item}/{item}_scandata.xml', W / f'{item}_scandata.xml')
    words = []
    for f in sorted((W / 'ocr').glob('*.json')):
        leaf = int(f.stem)
        d = json.loads(f.read_text())
        for t, x, y, w, h, c in d['words']:
            if words and words[-1]['leaf'] == leaf and words[-1]['t'].endswith('-') \
                    and len(words[-1]['t']) > 2 and t[:1].islower():
                words[-1]['t'] = words[-1]['t'][:-1] + t
                words[-1]['k'] = fold(words[-1]['t'])
                continue
            words.append({'t': t, 'k': fold(t), 'leaf': leaf, 'pw': d['w'], 'ph': d['h'],
                          'x': x, 'y': y, 'w': w, 'h': h})
    (W / 'words_bim.json').write_text(json.dumps(words), encoding='utf-8')
    print(f'bim: {len(words)} 词', file=sys.stderr)


# ── 3. 定位 ──────────────────────────────────────────────────────────
class Stream:
    def __init__(self):
        self.ws = json.loads((W / 'words_bim.json').read_text())
        self.keys = [w['k'] for w in self.ws]
        self.tri = collections.defaultdict(list)
        for k in range(len(self.keys) - 2):
            self.tri[(self.keys[k], self.keys[k + 1], self.keys[k + 2])].append(k)
        self.by_leaf = collections.defaultdict(list)
        for k, w in enumerate(self.ws):
            self.by_leaf[w['leaf']].append(k)
        self.bi = collections.defaultdict(list)
        for k in range(len(self.keys) - 1):
            self.bi[(self.keys[k], self.keys[k + 1])].append(k)

    def find(self, left, right, near=None, span=40000, n=3):
        """两侧 n 词组投票定位；near=期望位置，只在其附近找。"""
        L = [fold(w) for w in left if not TOK.search(w) and fold(w)]
        R = [fold(w) for w in right if not TOK.search(w) and fold(w)]
        idx = self.tri if n == 3 else self.bi
        votes = collections.Counter()
        for t in range(len(L) - n + 1):
            for k in idx.get(tuple(L[t:t + n]), ())[:80]:
                if near is None or abs(k - near) < span:
                    votes[(k + len(L) - t) // 4] += 1
        for t in range(len(R) - n + 1):
            for k in idx.get(tuple(R[t:t + n]), ())[:80]:
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
    i = min(i, len(ws) - 1)
    g = ws[i]
    e = ws[max(i, min(j, len(ws)) - 1)]
    return {'i': i, 'j': j, 'leaf': g['leaf'], 'pw': g['pw'], 'ph': g['ph'], 'gx': g['x'], 'gy': g['y'], 'gh': g['h'],
            'gx1': e['x'] + e['w'] if e['leaf'] == g['leaf'] and abs(e['y'] - g['y']) < g['h'] else g['x'] + g['w']}


def leaves_of(s):
    """缺字所在原书页 → IA 叶号（前后各看两叶）。TCP 一帧是一个对开、IA 一叶一页，但两边的偏移会漂
    （前半 2f−2/2f−3，后半漂到 2f−10/2f−11，中间夹重拍），不能套公式：按原书页码在 page_leaf.json 的锚点
    （两边页首文字逐字对上的页）之间线性插值。没有页码的（书名页、序）退回按帧号 2f−3。"""
    anc = _anchors()
    p = s.get('page') if isinstance(s, dict) else None
    if p is None or not anc:
        f = s['facs'] if isinstance(s, dict) else s
        c = 2 * int(f) - 3 if f else 0
    else:
        p = int(p)
        lo = max((a for a in anc if a[0] <= p), default=None)
        hi = min((a for a in anc if a[0] >= p), default=None)
        if lo is None:                       # 第一个锚点之前 / 最后一个之后：一页一叶往外推
            c = hi[1] - (hi[0] - p)
        elif hi is None:
            c = lo[1] + (p - lo[0])
        else:
            c = lo[1] if hi[0] == lo[0] else round(lo[1] + (p - lo[0]) * (hi[1] - lo[1]) / (hi[0] - lo[0]))
    return [c + d for d in (-2, -1, 0, 1, 2, 3)]


_ANC = []


def _anchors():
    if not _ANC and (W / 'page_leaf.json').exists():
        _ANC.extend(sorted(tuple(x) for x in json.loads((W / 'page_leaf.json').read_text())))
    return _ANC


def anchors():
    """原书页码 → IA 叶号锚点：每个 TCP 页首（pt-pb 带页码）后取 12 个干净词折叠成串，在 IA 自带 hOCR 搜索
    文本里找唯一出现，落在哪叶就是哪叶；再去掉偏移与前后锚点中位数差 > 2 的离群点（重拍、误配）。"""
    import gzip
    item = ITEMS['bim']
    for suf in ('hocr_searchtext.txt.gz', 'hocr_pageindex.json.gz', 'scandata.xml'):
        _download(f'https://archive.org/download/{item}/{item}_{suf}', W / f'{item}_{suf}')
    txt = gzip.open(W / f'{item}_hocr_searchtext.txt.gz', 'rt', encoding='utf-8').read()
    idx = json.load(gzip.open(W / f'{item}_hocr_pageindex.json.gz', 'rt'))

    def f2(x):
        return re.sub(r'[^a-z]', '', x.lower().replace('ſ', 's').replace('v', 'u').replace('j', 'i').replace('f', 's'))
    parts, owner = [], []
    for pi, (a, b, *_) in enumerate(idx):
        t = f2(txt[a:b])
        parts.append(t)
        owner += [pi] * len(t)
    ft = ''.join(parts)
    res = []
    for slug in rc.order()['order']:
        md = rc.read_src(slug)
        for m in re.finditer(r'<span class="pt-pb" id="p(\d+)" data-p="\d+" data-facs="\d+"[^>]*></span>', md):
            after = re.sub(r'<[^>]+>|\*', '', md[m.end():m.end() + 600])
            key = f2(' '.join([w for w in after.split() if not TOK.search(w)][:12]))[:40]
            if len(key) < 25:
                continue
            k = ft.find(key)
            if k >= 0 and ft.find(key, k + 1) < 0:
                res.append((int(m.group(1)), owner[k]))
    res.sort()
    keep = []
    for i, (p, lf) in enumerate(res):
        offs = sorted(l2 - p2 for p2, l2 in res[max(0, i - 4):i + 5])
        if abs((lf - p) - offs[len(offs) // 2]) <= 2:
            keep.append([p, lf])
    (W / 'page_leaf.json').write_text(json.dumps(keep) + '\n', encoding='utf-8')
    print(f'锚点 {len(keep)}/{len(res)}', file=sys.stderr)


def need_leaves():
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    lv = sorted({lf for s in sites for lf in leaves_of(s) if 0 <= lf < 915})
    (W / 'need_leaves.json').write_text(json.dumps(lv) + '\n', encoding='utf-8')
    print(f'需 OCR 的叶 {len(lv)}', file=sys.stderr)


def _eq(a, b):
    if a == b:
        return 1.0
    if len(a) < 3 or len(b) < 3:
        return 0.0
    r = SequenceMatcher(None, a, b).ratio()
    return r if r >= 0.75 else 0.0


def page_find(st, s, need=3.0):
    """只在缺字所在那一对开的几叶里找。每个候选位置 p（缺字之后第一个词的下标，缺字占 k 词）：
    左上下文从 p-k-1 往回、右上下文从 p 往后逐词比（字形折叠后相等或相似度≥0.75），
    连续对上的词数之和为分；不连续就停（容许中间夹一个 OCR 碎词）。"""
    L = [fold(w) for w in s['left'] if not TOK.search(w) and fold(w)][-7:]
    R = [fold(w) for w in s['right'] if not TOK.search(w) and fold(w)][:7]
    keys = st.keys
    best = None
    for leaf in leaves_of(s):
        idx = st.by_leaf.get(leaf)
        if not idx:
            continue
        lo, hi = idx[0], idx[-1] + 1
        for gi in range(lo, hi + 1):            # gi = 缺字词组起点
            for k in range(0, 5):               # 缺字在证人里占 k 个词
                sl, q, skip = 0.0, gi - 1, 0
                for w in reversed(L):
                    while q >= lo and skip <= 1:
                        e = _eq(keys[q], w)
                        if e:
                            sl += e; q -= 1; break
                        q -= 1; skip += 1
                    else:
                        break
                sr, q, skip = 0.0, gi + k, 0
                for w in R:
                    while q < hi and skip <= 1:
                        e = _eq(keys[q], w)
                        if e:
                            sr += e; q += 1; break
                        q += 1; skip += 1
                    else:
                        break
                sc = sl + sr - 0.1 * k
                if sl > .5 and sr > .5 and (not best or sc > best[0]):
                    best = (sc, gi, gi + k)
    if not best or best[0] < need:
        return None
    return best[1], max(best[2], best[1] + 1), round(best[0] / 14, 2)


def char_find(st, s, ctx=28, tol=0.34):
    """字符级定位：tesseract 常把排得紧的词粘成一个（`therefore,whatneeds`），按词比对就断。
    把这一对开几叶的 OCR 词折叠后无空格拼成一串，左右上下文各取末/首 ctx 个字符，
    edlib 半全局编辑距离找位置（容错 tol），左块结束与右块开始之间就是缺字。"""
    import edlib
    leaves = [lf for lf in leaves_of(s) if st.by_leaf.get(lf)]
    if not leaves:
        return None
    idx = [k for lf in leaves for k in st.by_leaf[lf]]
    P, cmap = [], []
    for k in idx:
        P.append(st.keys[k]); cmap += [k] * len(st.keys[k])
    P = ''.join(P)
    # 上下文在别的缺字处截断：跨过缺字拼起来，证人那边夹着一个词，编辑距离就超了
    lw, rw = list(s['left']), list(s['right'])
    while any(TOK.search(w) for w in lw):
        lw = lw[next(i for i in range(len(lw) - 1, -1, -1) if TOK.search(lw[i])) + 1:]
    rw = rw[:next((i for i, w in enumerate(rw) if TOK.search(w)), len(rw))]
    Ls = ''.join(fold(w) for w in lw)[-ctx:]
    Rs = ''.join(fold(w) for w in rw)[:ctx]
    if len(Ls) < 6 or len(Rs) < 6:
        return None
    gl = len(fold(re.sub(r'[•〈〉◊…▪]', 'x', s['tcp']))) + 4
    la = edlib.align(Ls, P, mode='HW', task='locations', k=int(len(Ls) * tol))
    ra = edlib.align(Rs, P, mode='HW', task='locations', k=int(len(Rs) * tol))
    if la['editDistance'] < 0 or ra['editDistance'] < 0:
        return None
    best = None
    for _, le in la['locations']:
        for rs, _ in ra['locations']:
            d = rs - le - 1
            if -2 <= d <= gl + 12 and (not best or d < best[2]):
                best = (le, rs, d)
    if not best:
        return None
    le, rs, _ = best
    i = cmap[min(le + 1, len(cmap) - 1)] if le + 1 < len(cmap) else cmap[-1]
    if le + 1 < len(cmap) and cmap[le] == cmap[le + 1]:
        i = cmap[le]                 # 缺字与左邻粘在同一个 OCR 词里
    j = cmap[rs] if rs < len(cmap) else cmap[-1] + 1
    if rs > 0 and cmap[rs - 1] == cmap[rs]:
        j = cmap[rs] + 1             # 与右邻粘连
    j = max(j, i + 1)
    sc = (len(Ls) - la['editDistance']) + (len(Rs) - ra['editDistance'])
    return i, j, round(sc / (len(Ls) + len(Rs)), 2)


def match():
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    nmain = json.loads((RAW / 'main_words.json').read_text())
    st = Stream()
    out = []
    last = None
    for s in sites:
        rec = {k: v for k, v in s.items() if k != 'i'}
        lo, hi = None, None
        r = None
        if s.get('facs') or s.get('page'):
            lv = leaves_of(s)
            ks = [k for leaf in lv for k in st.by_leaf.get(leaf, [])]
            if ks:
                lo, hi = min(ks), max(ks) + 1
                r = char_find(st, s)
                if r is None:
                    r = char_find(st, s, ctx=18, tol=0.4)
                    if r:
                        rec['loose'] = True
                if r is None:
                    r = page_find(st, s, need=2.5 if s['stream'] == 'note' else 3.5)
                if r is None and s['stream'] == 'note':
                    r = char_find(st, {**s, 'left': s['mleft'], 'right': s['mright'], 'tcp': ''}) or \
                        page_find(st, {**s, 'left': s['mleft'], 'right': s['mright']}, need=3.5)
                    if r:
                        rec['anchor'] = True
        if r:
            i, j, sc = r
            rec['bim'] = {'read': ' '.join(w['t'] for w in st.ws[i:j]), 'score': sc, **page_box(st.ws, i, j)}
            if s['stream'] == 'main':
                last = i
        out.append(rec)
    estimate(out, sites, st)
    (RAW / 'witness_locs.json').write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    c = collections.Counter((r['stream'], 'bim' in r) for r in out)
    print(f'定位 {sum("bim" in r for r in out)}/{len(out)}  {dict(c)}', file=sys.stderr)


def estimate(locs, sites, st):
    """没定位到的正文缺字（多是透印、污损处，OCR 读成乱码）：取前后最近的已定位缺字，按 TCP 词序在两者
    之间按比例插值出**证人词流下标**（跨页也自然落对），取该词的叶与纵坐标，标 est；判读图出高裁图。"""
    pos = {s['gid']: s['i'] for s in sites}
    mains = [r for r in locs if r['stream'] == 'main']
    n_est = 0
    for n, r in enumerate(mains):
        if 'bim' in r:
            continue
        a = next((m for m in reversed(mains[:n]) if 'bim' in m and not m['bim'].get('est')), None)
        b = next((m for m in mains[n + 1:] if 'bim' in m and not m['bim'].get('est')), None)
        lv = leaves_of(r)
        if a and b and pos[b['gid']] > pos[a['gid']] and b['bim']['i'] > a['bim']['i'] \
                and b['bim']['i'] - a['bim']['i'] < 3 * (pos[b['gid']] - pos[a['gid']]) + 200:
            t = (pos[r['gid']] - pos[a['gid']]) / (pos[b['gid']] - pos[a['gid']])
            k = int(a['bim']['i'] + t * (b['bim']['i'] - a['bim']['i']))
        else:
            m = a if a and (not b or pos[r['gid']] - pos[a['gid']] <= pos[b['gid']] - pos[r['gid']]) else b
            if not m:
                continue
            k = m['bim']['i'] + (pos[r['gid']] - pos[m['gid']])
        k = max(0, min(len(st.ws) - 1, k))
        if st.ws[k]['leaf'] not in lv:
            ks = [x for lf in lv for x in st.by_leaf.get(lf, [])]
            if not ks:
                continue
            k = min(ks, key=lambda x: abs(x - k))
        w = st.ws[k]
        r['bim'] = {'read': '', 'score': 0, 'est': True, 'i': k, 'j': k + 1, 'leaf': w['leaf'], 'pw': w['pw'],
                    'ph': w['ph'], 'gx': w['x'], 'gy': w['y'], 'gh': max(w['h'], 30), 'gx1': w['x'] + w['w']}
        n_est += 1
    print(f'插值估位 {n_est}', file=sys.stderr)


# ── 4. 判读图 ────────────────────────────────────────────────────────
CROPS = W / 'crops'
_ACCESS = {}


def page_url(leaf, width=None):
    """IA 单页接口 page/n{N} 的 N 只数对外显示的叶，按 scandata 的 addToAccessFormats 换算
    （leighton 踩过：不换算会裁到别页）。"""
    item = ITEMS['bim']
    if item not in _ACCESS:
        sd = (W / f'{item}_scandata.xml').read_text(encoding='utf-8', errors='replace')
        pages = re.findall(r'<page leafNum="(\d+)">(.*?)</page>', sd, re.S)
        acc = [int(n) for n, b in pages if re.search(r'<addToAccessFormats>true', b)]
        _ACCESS[item] = {lf: i for i, lf in enumerate(acc)}
    return f'https://archive.org/download/{item}/page/n{_ACCESS[item][leaf]}' + (f'_w{width}' if width else '') + '.jpg'


def full_page(leaf):
    """裁图用的整页：dickson_bim_ocr.py 存的半尺寸图（≈400 ppi）。"""
    f = IMG / f'bim_{leaf:04d}.jpg'
    if not f.exists():
        import petter_bim_ocr
        petter_bim_ocr.one(leaf)
    return f


def crop_file(gid, loc, wide=False):
    """缺字所在行连同上下各两行，横向取正文整栏宽（定位偶尔差一行或落在行首/行尾），
    定位到的词画一个淡框作提示。wide=上下各四行。"""
    CROPS.mkdir(parents=True, exist_ok=True)
    f = CROPS / f'{gid:04d}{"w" if wide else ""}.jpg'
    if f.exists():
        return f
    from PIL import Image, ImageDraw
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(full_page(loc['leaf'])).convert('L')
    sc = im.width / loc['pw'] if loc['pw'] else 1.0
    lines = _lines(loc['leaf'])
    h = max(20, loc.get('gh', 40))
    gx0, gx1 = loc['gx'], max(loc.get('gx1', loc['gx']), loc['gx'] + h)
    est = loc.get('est') or rec_anchor.get(gid)
    n = 5 if (wide or est) else (2 if rec_anchor.get(gid) else 1)   # 正文缺字只取上下各一行，一张判读图多放几条
    lh = int(h * 1.45)
    Y0, Y1 = max(0, loc['gy'] - lh * n - h // 3), min(loc['ph'], loc['gy'] + h + lh * n + h // 3)
    X0, X1 = lines.get('x0', 0), lines.get('x1', loc['pw'])
    X0, X1 = min(X0, gx0 - h), max(X1, gx1 + h)
    X0, X1 = max(0, X0 - h), min(loc['pw'], X1 + h)
    if rec_anchor.get(gid) or rec_note.get(gid):   # 旁注：横向取整页，连页边一起
        X0, X1 = 0, loc['pw']
    c = im.crop((int(X0 * sc), int(Y0 * sc), int(X1 * sc), int(Y1 * sc))).convert('RGB')
    dr = ImageDraw.Draw(c)
    bx = [(gx0 - X0 - 6) * sc, (loc['gy'] - Y0 - 6) * sc, (gx1 - X0 + 6) * sc, (loc['gy'] + h - Y0 + 8) * sc]
    if not est:
        dr.rectangle(bx, outline=(230, 120, 0), width=3)
    out_w = 1150
    if c.width > out_w:
        c = c.resize((out_w, max(1, int(c.height * out_w / c.width))))
    c.save(f, quality=86)
    return f


_LINES = {}
rec_anchor = {}
rec_note = {}


def _lines(leaf):
    """本叶正文的左右边界（词 x 的 3% / 97% 分位），裁图横向取这一段。"""
    if leaf not in _LINES:
        d = json.loads((W / 'ocr' / f'{leaf:04d}.json').read_text())
        xs = sorted(w[1] for w in d['words'] if len(w[0]) > 2)
        xe = sorted(w[1] + w[3] for w in d['words'] if len(w[0]) > 2)
        _LINES[leaf] = {'x0': xs[int(len(xs) * .03)], 'x1': xe[int(len(xe) * .97)]} if xs else {}
    return _LINES[leaf]


def fetch(gids, wide=False, workers=6):
    from concurrent.futures import ThreadPoolExecutor
    locs = {r['gid']: r for r in json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))}
    jobs = [(g, locs[g]['bim']) for g in gids if 'bim' in locs[g]]
    rec_anchor.update({g: True for g in gids if locs[g].get('anchor')})
    rec_note.update({g: True for g in gids if locs[g]['stream'] == 'note'})
    bad = []

    def one(j):
        try:
            crop_file(*j, wide=wide)
        except Exception as e:      # noqa: BLE001
            bad.append((j[0], str(e)[:80]))
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, jobs))
    print(f'裁图 {len(jobs) - len(bad)}/{len(jobs)}', bad[:5], file=sys.stderr)


def sheets(gids, name, per=10, wide=False):
    """每条：一行文字（编号、TCP 上下文）+ 原版裁图。"""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    locs = {r['gid']: r for r in json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))}
    fetch(gids, wide=wide)
    sh = W / 'sheets'
    sh.mkdir(exist_ok=True)
    for f in sh.glob(f'{name}_*.jpg'):
        f.unlink()
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 22)
    width = 1150
    rows, n_items, k = [], 0, 0

    def flush():
        nonlocal rows, k
        if rows:
            Image.fromarray(np.vstack(rows)).save(sh / f'{name}_{k:03d}.jpg', quality=85)
            rows, k = [], k + 1
    for g in gids:
        rec = locs[g]
        head = Image.new('L', (width, 58), 255)
        dr = ImageDraw.Draw(head)
        dr.text((6, 2), f"#{g} {rec['slug']} {'[旁注]' if rec['stream'] == 'note' else ''}  "
                        f"{'【估位·按上下文找】' if rec.get('bim', {}).get('est') else '【旁注·看页边】' if rec.get('anchor') else 'OCR: ' + rec.get('bim', {}).get('read', '—')}"[:90], font=font, fill=70)
        ctx = ' '.join(rec['left'][-5:]) + ' [[' + rec['tcp'] + ']] ' + ' '.join(rec['right'][:5])
        dr.text((6, 30), ctx[:95], font=font, fill=0)
        f = CROPS / f'{g:04d}{"w" if wide else ""}.jpg'
        if 'bim' in rec and f.exists():
            im = Image.open(f).convert('L')
            if im.width != width:
                im = im.resize((width, max(1, int(im.height * width / im.width))))
        else:
            im = Image.new('L', (width, 50), 235)
            ImageDraw.Draw(im).text((6, 12), '（未定位）', font=font, fill=120)
        rows += [np.array(head), np.array(im), np.full((6, width), 40, np.uint8)]
        n_items += 1
        if n_items % per == 0:
            flush()
    flush()
    print(f'{n_items} 条 → {k} 张 {sh}/{name}_*.jpg', file=sys.stderr)


def relocate(gids):
    """估位裁错的：在缺字所在几叶里按「行」找。OCR 词按纵坐标聚成行，每行（连同下一行）折叠成串，
    与缺字左右上下文（各 6 词）比相似度，取最好的一行重写 witness_locs 里的位置（去掉 est，标 reloc）。"""
    import difflib
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    by = {r['gid']: r for r in locs}
    n = 0
    for g in gids:
        r = by[g]
        lw = [w for w in r['left'][-6:] if not TOK.search(w)]
        rw = [w for w in r['right'][:6] if not TOK.search(w)]
        key_l, key_r = ''.join(fold(w) for w in lw), ''.join(fold(w) for w in rw)
        best = None
        for lf in leaves_of(r):
            f = W / 'ocr' / f'{lf:04d}.json'
            if not f.exists():
                continue
            d = json.loads(f.read_text())
            ws = sorted(d['words'], key=lambda w: (w[2], w[1]))
            lines = []
            for w in ws:
                if lines and abs(lines[-1][-1][2] - w[2]) < max(12, w[4] * .6):
                    lines[-1].append(w)
                else:
                    lines.append([w])
            for k, ln in enumerate(lines):
                ln = sorted(ln, key=lambda w: w[1])
                nxt = sorted(lines[k + 1], key=lambda w: w[1]) if k + 1 < len(lines) else []
                txt = ''.join(fold(w[0]) for w in ln + nxt)
                sl = difflib.SequenceMatcher(None, key_l, txt, autojunk=False).find_longest_match(0, len(key_l), 0, len(txt))
                sr = difflib.SequenceMatcher(None, key_r, txt, autojunk=False).find_longest_match(0, len(key_r), 0, len(txt))
                sc = sl.size + sr.size + (5 if sl.b < sr.b else 0)
                if not best or sc > best[0]:
                    pick = ln if sl.b < len(''.join(fold(w[0]) for w in ln)) else (nxt or ln)
                    best = (sc, lf, d, pick)
        if not best or best[0] < 10:
            continue
        sc, lf, d, ln = best
        x0 = min(w[1] for w in ln)
        x1 = max(w[1] + w[3] for w in ln)
        y = min(w[2] for w in ln)
        h = max(w[4] for w in ln)
        r['bim'] = {'read': ' '.join(w[0] for w in ln), 'score': sc, 'reloc': True, 'i': 0, 'j': 0, 'leaf': lf,
                    'pw': d['w'], 'ph': d['h'], 'gx': x0, 'gy': y, 'gh': h, 'gx1': x1}
        n += 1
        for suf in ('', 'w'):
            c = W / 'crops' / f'{g:04d}{suf}.jpg'
            if c.exists():
                c.unlink()
    (RAW / 'witness_locs.json').write_text(json.dumps(locs, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'重定位 {n}/{len(gids)}', file=sys.stderr)


def parse_gids(s, total):
    if not s:
        return list(range(total))
    out = []
    for part in s.split(','):
        if '-' in part:
            a, b = map(int, part.split('-'))
            out += list(range(a, b + 1))
        else:
            out.append(int(part))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['gaps', 'anchors', 'build', 'match', 'sheets', 'relocate'])
    ap.add_argument('--gids')
    ap.add_argument('--name', default='s')
    ap.add_argument('--per', type=int, default=10)
    ap.add_argument('--wide', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'gaps':
        gaps()
    elif a.cmd == 'anchors':
        W.mkdir(parents=True, exist_ok=True)
        anchors()
        need_leaves()
    elif a.cmd == 'build':
        build()
    elif a.cmd == 'match':
        match()
    elif a.cmd == 'relocate':
        relocate(parse_gids(a.gids, 0))
    else:
        n = len(json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8')))
        sheets(parse_gids(a.gids, n), a.name, a.per, a.wide)


if __name__ == '__main__':
    main()
