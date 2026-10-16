#!/usr/bin/env python3
"""他版证人：1841 年 T. Ward 重印本（Google Books PXRjAAAAcAAJ，大英图书馆藏本）
按位置判读 TCP 缺字（old-book-ocr 第 ② 层）。

    python3 scripts/hutcheson_witness.py fetch        # 逐页取页图 → witness_1841/img/
    python3 scripts/hutcheson_witness.py ocr          # 分栏 tesseract → witness_1841/ocr/*.tsv
    python3 scripts/hutcheson_witness.py build        # → witness_1841/words.json（全书词流）
    python3 scripts/hutcheson_witness.py match        # 每处缺字定位 + 读数 → witness_locs.json
    python3 scripts/hutcheson_witness.py sheets       # 判读图（TCP 上下文 + 1841 页图裁行）

1841 本**不是逐字翻印**：拼写现代化（beleevers → believers）、`&` 展开、经文出处
改罗马数字章号、偶有小标题（DOCTRINES.）。所以它只当证人，不当底本：
  1. 位置：缺字两侧 TCP 上下文在 1841 词流里按锚点对上（左右两侧都要对上）；
  2. 字形：1841 读数折算后与 TCP 残字逐字母相容（`b•t` 只能落 but/bet/bit…）；
  3. 拼写：落盘的是**1657 的写法**——候选从 TCP 残字 + 本书语料里生成，1841 读数
     只负责在候选里挑一个；整词缺口才直接用 1841 读数，并在证据里注明。
判读图逐条人工过目后才落 gap_decisions_witness.tsv。

页图（不入库，可重新下载）：Google Books 阅读器的签名页图接口
`books?id=…&pg=PAn&jscmd=click3` → `src`，PDF 下载会被人机验证拦住，页图接口不会。
"""
import argparse
import collections
import json
import re
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'hutcheson_raw' / 'john'
W = RAW / 'witness_1841'
IMG = W / 'img'
OCR = W / 'ocr'
GB = 'PXRjAAAAcAAJ'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')


# ── fetch ────────────────────────────────────────────────────────────
def _get(url, cookie=None):
    req = urllib.request.Request(url, headers={'User-Agent': UA, **({'Cookie': cookie} if cookie else {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.headers


def fetch():
    IMG.mkdir(parents=True, exist_ok=True)
    body, hd = _get(f'https://books.google.com/books?id={GB}&pg=PA10&jscmd=click3&vq=')
    cookie = '; '.join(c.split(';')[0] for c in hd.get_all('Set-Cookie') or [])
    pids = []
    for p in json.loads(body)['page']:
        if p['pid'] not in pids:
            pids.append(p['pid'])
    (W / 'pids.json').write_text(json.dumps(pids), encoding='utf-8')
    todo = [p for p in pids if not (IMG / f'{p}.jpg').exists()]
    print(f'{len(pids)} 页，待取 {len(todo)}', file=sys.stderr)
    miss = []
    srcs = {}           # 每次页表请求会顺带给出前后几页的签名地址，全部攒下来用
    for pid in todo:
        if (IMG / f'{pid}.jpg').exists():
            continue
        if pid not in srcs:
            for _ in range(3):
                try:
                    d = json.loads(_get(f'https://books.google.com/books?id={GB}&pg={pid}&jscmd=click3&vq=', cookie)[0])
                    for p in d['page']:
                        if p.get('src'):
                            srcs[p['pid']] = p['src']
                    break
                except Exception as e:              # noqa: BLE001
                    print(f'  {pid} 页表失败 {e}', file=sys.stderr)
                    time.sleep(5)
        src = srcs.get(pid)
        if not src:
            miss.append(pid)
            continue
        try:
            data, hd = _get(src + '&w=1800', cookie)
        except Exception as e:                      # noqa: BLE001
            print(f'  {pid} 页图失败 {e}', file=sys.stderr)
            miss.append(pid)
            continue
        if not hd.get('Content-Type', '').startswith('image/jpeg'):
            miss.append(pid)            # 占位图（png「image not available」）
            continue
        (IMG / f'{pid}.jpg').write_bytes(data)
        time.sleep(0.3)
    print(f'取不到 {len(miss)}：{miss}', file=sys.stderr)


# ── ocr ──────────────────────────────────────────────────────────────
def _split_cols(im):
    """双栏：在页宽 40%–60% 之间找竖向最白的一列当栏缝。"""
    import numpy as np
    h, w = im.shape
    band = im[int(h * .12):int(h * .92), int(w * .40):int(w * .60)]
    dark = (band < 140).sum(axis=0)
    k = int(np.argmin(np.convolve(dark, np.ones(9), 'same')))
    x = int(w * .40) + k
    return [(0, x), (x, w)]


def _ocr_one(pid):
    """两套 OCR，只用来定位（读数以页图为准）：
      A  原图 --psm 4                 → <pid>.tsv
      B  放大 2 倍 + Otsu --psm 6      → <pid>.b.tsv（坐标折回原图）
    页图是 Google 的原生上限 1548×2500，正文字高约 23px；两套在不同行上读崩
    （PA24 `whereby he purchaseth…` 一行 A 套全乱、B 套完好），合用定位率高得多。"""
    import cv2
    im = cv2.imread(str(IMG / f'{pid}.jpg'), cv2.IMREAD_GRAYSCALE)
    cols = _split_cols(im)
    for suf, prep, psm, sc in (('', lambda c: c, '4', 1),
                               ('.b', lambda c: cv2.threshold(cv2.resize(c, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC),
                                                              0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1], '6', 2)):
        out = OCR / f'{pid}{suf}.tsv'
        if out.exists() and out.stat().st_size:
            continue
        rows = []
        for ci, (x0, x1) in enumerate(cols):
            png = OCR / f'{pid}{suf}_{ci}.png'
            cv2.imwrite(str(png), prep(im[:, x0:x1]))
            r = subprocess.run(['tesseract', str(png), 'stdout', '-l', 'eng', '--psm', psm, 'tsv'],
                               capture_output=True)
            png.unlink()
            if r.returncode:
                return pid, 'ERR ' + r.stderr.decode('utf-8', 'replace')[-200:]
            for ln in r.stdout.decode('utf-8', 'replace').splitlines()[1:]:
                f = ln.split('\t')
                if len(f) == 12 and f[0] == '5' and f[11].strip():
                    rows.append([ci, f[2], f[3], f[4], f[5], int(f[6]) // sc + x0, int(f[7]) // sc,
                                 int(f[8]) // sc, int(f[9]) // sc, f[10], f[11]])
        out.write_text('\n'.join('\t'.join(map(str, r)) for r in rows) + '\n', encoding='utf-8')
    return pid, 'ok'


def ocr():
    OCR.mkdir(parents=True, exist_ok=True)
    pids = json.loads((W / 'pids.json').read_text())
    pids = [p for p in pids if (IMG / f'{p}.jpg').exists()]
    bad = 0
    with ProcessPoolExecutor(8) as ex:
        for pid, st in ex.map(_ocr_one, pids):
            if st.startswith('ERR'):
                bad += 1
                print(pid, st, file=sys.stderr)
    print(f'{len(pids)} 页，失败 {bad}', file=sys.stderr)


# ── build ────────────────────────────────────────────────────────────
def fold(w):
    """比对口径：小写、只留字母、1657↔1841 拼写差异折平（u/v、i/j/y、双写、词尾 e）。
    TCP 与 1841 两侧必须用同一个函数（切分口径两处必须一致）。"""
    w = re.sub(r'[^a-z]', '', w.lower().replace('ſ', 's'))
    w = w.replace('v', 'u').replace('j', 'i').replace('y', 'i')
    w = re.sub(r'(.)\1+', r'\1', w)
    w = w.replace('ie', 'i').replace('ei', 'i').replace('ee', 'e')
    if len(w) > 3 and w.endswith('e'):
        w = w[:-1]
    return w


def build():
    for suf in ('', '.b'):
        _build(suf)


def _build(suf):
    pids = json.loads((W / 'pids.json').read_text())
    words = []
    for pid in pids:
        f = OCR / f'{pid}{suf}.tsv'
        if not f.exists():
            continue
        rows = [ln.split('\t') for ln in f.read_text(encoding='utf-8').splitlines() if ln]
        # 阅读顺序：栏 → 块 → 段 → 行 → 词（tesseract 已按栏内顺序给出）
        for r in rows:
            t = r[10]
            # 页眉（`10 EXPOSITION OF` / `JOHN` / 页码）在版框之上：y < 页高 6.5%
            if int(r[6]) < 160:
                continue
            w = {'t': t, 'k': fold(t), 'pid': pid, 'x': int(r[5]), 'y': int(r[6]),
                 'w': int(r[7]), 'h': int(r[8]), 'c': r[0]}
            # 行末断词 `excel-` + `lency` → 拼成一个词（坐标取前半）
            if words and words[-1]['t'].endswith('-') and len(words[-1]['t']) > 2 and t[:1].islower():
                p = words[-1]
                p['t'] = p['t'][:-1] + t
                p['k'] = fold(p['t'])
                continue
            words.append(w)
    (W / f'words{suf}.json').write_text(json.dumps(words), encoding='utf-8')
    print(f'words{suf}: {len(words)} 词', file=sys.stderr)


# ── match ────────────────────────────────────────────────────────────
TOK = re.compile(r'•+|〈◊〉|〈…〉|〈Greek〉|▪')


def tcp_context(md, a, b, n=8):
    """缺字词前后各 n 个词（剥 HTML、星号；同一段落内的缺字记号原样留着）。"""
    left = re.sub(r'<[^>]+>', ' ', md[:a]).replace('*', ' ').split()[-n:]
    right = re.sub(r'<[^>]+>', ' ', md[b:b + 600]).replace('*', ' ').split()[:n]
    return left, right


def locate(ws, keys, left, right, lo, hi):
    """在 ws[lo:hi] 里找 left 的末尾与 right 的开头：两侧各取最长匹配块，要求
    左块紧贴缺字左边、右块紧贴缺字右边，两块之间隔 1–6 个词。返回 (i, j, 分)：
    1841 里缺字对应的词区间 [i, j)。"""
    L = [fold(w) for w in left if not TOK.search(w) and fold(w)]
    R = [fold(w) for w in right if not TOK.search(w) and fold(w)]
    if len(L) < 3 or len(R) < 3:
        return None
    seg = keys[lo:hi]
    best = None
    sm = SequenceMatcher(None, seg, L + ['\x00'] + R, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size]
    lb = [b for b in blocks if b.b < len(L)]
    rb = [b for b in blocks if b.b > len(L)]
    if not lb or not rb:
        return None
    # 左侧：最靠右、且覆盖到 L 末尾附近的块；右侧：最靠左、覆盖 R 开头附近的块
    l = max(lb, key=lambda b: (b.b + b.size, b.size))
    r = min(rb, key=lambda b: (b.b, -b.size))
    lcov = sum(b.size for b in lb) / len(L)
    rcov = sum(b.size for b in rb) / len(R)
    i = lo + l.a + l.size + (len(L) - (l.b + l.size))     # L 末尾之后
    j = lo + r.a - (r.b - len(L) - 1)                       # R 开头
    if not (0 <= j - i <= 6):
        return None
    return i, j, round(min(lcov, rcov), 2)


def compatible(tcp_core, wit):
    """1841 读数与 TCP 残字逐字母相容：残字里已知的字母在对应位置上要对得上。
    折算口径只做大小写与 u/v、i/j 互换——字母数必须一样（双写差异另行判）。"""
    if len(tcp_core) != len(wit):
        return False
    for c, d in zip(tcp_core.lower(), wit.lower()):
        if c == '•':
            continue
        if c == d or {c, d} in ({'u', 'v'}, {'i', 'j'}, {'i', 'y'}):
            continue
        return False
    return True


class Stream:
    """一套 OCR 的词流 + 三词组索引。"""

    def __init__(self, suf):
        self.name = suf or 'A'
        self.ws = json.loads((W / f'words{suf}.json').read_text())
        self.keys = [w['k'] for w in self.ws]
        self.tri = collections.defaultdict(list)
        for k in range(len(self.keys) - 2):
            self.tri[(self.keys[k], self.keys[k + 1], self.keys[k + 2])].append(k)

    def find(self, left, right):
        """投票定位：两侧每个三词组都去索引里查，各自推算缺字落点（左侧：组尾之后；
        右侧：组头之前一词）。单个读坏的词只废掉含它的那几组，不让整处定位失败
        （`and by` 被读成 `and b` 的教训）。"""
        L = [fold(w) for w in left if not TOK.search(w) and fold(w)]
        R = [fold(w) for w in right if not TOK.search(w) and fold(w)]
        votes = collections.Counter()
        for t in range(len(L) - 2):
            for k in self.tri.get(tuple(L[t:t + 3]), ())[:50]:
                votes[(k + len(L) - t) // 4] += 1
        for t in range(len(R) - 2):
            for k in self.tri.get(tuple(R[t:t + 3]), ())[:50]:
                votes[(k - t - 1) // 4] += 1
        res = None
        for bucket, v in votes.most_common(4):
            if v < 2:
                break
            c = bucket * 4
            r = locate(self.ws, self.keys, left, right, max(0, c - 16), min(len(self.ws), c + 20))
            if r and (not res or r[2] > res[2]):
                res = r
        return res


def match():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import hutcheson_common as hc
    streams = [Stream(''), Stream('.b')]
    rows = [l.rstrip('\n').split('\t') for l in (RAW / 'gap_decisions.tsv').read_text(encoding='utf-8').splitlines()
            if l and not l.startswith('#')]
    todo = [r for r in rows if r[3] == '?']
    mds = {}
    out = []
    for slug, ordi, word, _, ev in todo:
        # 序号按抽取原稿算（gap_decisions 的口径），不能读已落修正的文本
        md = mds.setdefault(slug, (hc.SRC / f'{slug}.md').read_text(encoding='utf-8'))
        m = list(hc.TOK.finditer(md))[int(ordi)]
        a, b = hc.gap_word(md, m)
        left, right = tcp_context(md, a, b)
        rec = {'slug': slug, 'ord': int(ordi), 'tcp': word, 'left': left, 'right': right}
        best = None
        for st in streams:
            r = st.find(left, right)
            if r and (not best or r[2] > best[1][2]):
                best = (st, r)
        if best:
            st, (i, j, sc) = best
            ws = st.ws
            span = range(max(0, i - 3), min(len(ws), j + 3))
            same = [x for x in span if ws[x]['pid'] == ws[min(i, len(ws) - 1)]['pid']]
            g = ws[min(i, len(ws) - 1)]
            rec.update(gy=g['y'], gx=g['x'])          # 缺字处那个词的坐标（裁图以它为中心）
            rec.update(wit=' '.join(w['t'] for w in ws[i:j]), score=sc, stream=st.name,
                       pid=ws[min(i, len(ws) - 1)]['pid'],
                       box=[min(ws[x]['x'] for x in same), min(ws[x]['y'] for x in same),
                            max(ws[x]['x'] + ws[x]['w'] for x in same), max(ws[x]['y'] + ws[x]['h'] for x in same)])
        out.append(rec)
    (RAW / 'witness_locs.json').write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    hit = [r for r in out if 'wit' in r]
    print(f'待判 {len(todo)}，定位到 {len(hit)}（A {sum(r.get("stream") == "A" for r in hit)} / '
          f'B {sum(r.get("stream") == ".b" for r in hit)}）', file=sys.stderr)


# ── judge ────────────────────────────────────────────────────────────
DEC = RAW / 'gap_decisions_witness.tsv'
ROMAN = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100}


def roman(s):
    s = s.lower()
    if not s or not re.fullmatch(r'[ivxlc]+', s):
        return None
    n = 0
    for k, ch in enumerate(s):
        v = ROMAN[ch]
        n += -v if k + 1 < len(s) and ROMAN[s[k + 1]] > v else v
    return n


def corpus_forms():
    """本书语料：fold → 最常见的 1657 写法（整词缺口的拼写回映）；以及词频。"""
    import collections
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import hutcheson_common as hc
    forms = collections.defaultdict(collections.Counter)
    freq = collections.Counter()
    for f in hc.SRC.glob('*.md'):
        for t in re.sub(r'<[^>]+>', ' ', f.read_text(encoding='utf-8')).replace('*', ' ').split():
            core = t.strip('.,;:()?!\'"[]’‘')
            if TOK.search(t) or not re.fullmatch(r'[A-Za-z]+', core):
                continue
            forms[fold(core)][core] += 1
            freq[core.lower()] += 1
    return forms, freq


def judge_one(rec, forms, freq, lex):
    """→ (fixed 或 '?', 证据)。只输出能自动定的；其余 '?' 交判读图。"""
    tcp = rec['tcp']
    wit = rec.get('wit')
    if wit is None:
        return '?', 'w1841:未定位'
    lead = len(tcp) - len(tcp.lstrip('.,;:()?!\'"[]’‘'))
    trail = len(tcp) - len(tcp.rstrip('.,;:()?!\'"[]’‘'))
    core = tcp[lead:len(tcp) - trail] if trail else tcp[lead:]
    pre, post = tcp[:lead], (tcp[len(tcp) - trail:] if trail else '')
    wtoks = wit.split()
    wcore = [w.strip('.,;:()?!\'"[]“”’‘') for w in wtoks]
    if rec['score'] < 0.5:
        return '?', f'w1841:锚点覆盖低 {rec["score"]}'
    # 词里缺字母
    if re.fullmatch(r'[A-Za-z•]+', core) and '•' in core:
        if len(wcore) != 1 or not wcore[0]:
            return '?', f'w1841:读数非单词 {wit!r}'
        w = wcore[0]
        rx = re.compile('^' + ''.join('.' if c == '•' else re.escape(c.lower()) for c in core) + '$')
        cands = [c for c in freq if rx.match(c) and fold(c) == fold(w)]
        if len(cands) == 1:
            pick = cands[0]
            ev = f'w1841:{w}→语料{pick}×{freq[pick]}'
        elif not cands and compatible(core, w) and (w.lower() in lex.get(len(w), ()) or freq[w.lower()]):
            pick = w.lower()
            ev = f'w1841:{w}（逐字母相容）'
        else:
            return '?', f'w1841:读数 {w!r} 与残字 {core!r} 不相容或候选多' + (f' {cands}' if cands else '')
        out = ''.join(pick[i] if c == '•' else c for i, c in enumerate(core))
        return pre + out + post, ev
    # 经文出处里的数字：`1•.10` ← 1841 `x. 10` / `xiv. 10`
    if re.fullmatch(r'[\d•.,]+', core) and '•' in core:
        nums = []
        for w in wcore:
            for part in re.split(r'[.,]', w):
                if part.isdigit():
                    nums.append(part)
                elif roman(part):
                    nums.append(str(roman(part)))
        segs = [s for s in re.split(r'[.,]', core) if s]
        if len(nums) >= len(segs):
            for off in range(len(nums) - len(segs) + 1):
                cand = nums[off:off + len(segs)]
                if all(len(c) == len(s) and all(x == '•' or x == y for x, y in zip(s, c)) for s, c in zip(segs, cand)):
                    it = iter(cand)
                    res = re.sub(r'[\d•]+', lambda m: next(it), core)
                    return pre + res + post, f'w1841:{wit}（罗马数字换算）'
        return '?', f'w1841:数字对不上 {wit!r}'
    # 整词 / 一截缺口：取 1841 读数，拼写按本书语料回映
    if core in ('〈◊〉', '〈…〉') or re.fullmatch(r'[A-Za-z]*〈[◊…]〉[A-Za-z]*', core):
        if not wtoks or len(wtoks) > (1 if '◊' in core else 6):
            return '?', f'w1841:读数长度不合 {wit!r}'
        mapped = []
        for t in wtoks:
            # 1841 读数自带的标点不要：TCP 词前后的标点由 pre/post 原样补回，否则成 `it;;`
            c = t.strip('.,;:()?!\'"[]“”’‘')
            f = forms.get(fold(c))
            mapped.append(f.most_common(1)[0][0] if f else c)
        return pre + ' '.join(mapped) + post, f'w1841:{wit}（整词，拼写按本书语料回映）'
    return '?', f'w1841:类型待人工（{core!r} ← {wit!r}）'


def judge():
    import collections
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    forms, freq = corpus_forms()
    lex = collections.defaultdict(set)
    web2 = Path('/usr/share/dict/web2')
    if web2.exists():
        for w in web2.read_text().split():
            if w.islower():
                lex[len(w)].add(w)
    rows, tally = [], collections.Counter()
    for rec in locs:
        fixed, ev = judge_one(rec, forms, freq, lex)
        tally['落' if fixed != '?' else ev.split(' ')[0].split('（')[0]] += 1
        rows.append((rec['slug'], rec['ord'], rec['tcp'], fixed, ev))
    DEC.write_text('# slug\tord\ttcp_word\t判读(?=不判)\t证据（hutcheson_witness.py judge；人工复核改这里）\n'
                   + '\n'.join('\t'.join(map(str, r)) for r in rows) + '\n', encoding='utf-8')
    print('  '.join(f'{k} {v}' for k, v in tally.most_common()), file=sys.stderr)


def sheets(only=None):
    """判读图：每条一行标题（序号 · TCP 上下文 [[缺字]] · 自动判读）+ 1841 页图裁出的那几行。
    only：'auto' 只出已自动落的（抽查用），'pending' 只出 '?' 的，None 全出。"""
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    dec = {}
    if DEC.exists():
        for ln in DEC.read_text(encoding='utf-8').splitlines():
            if ln and not ln.startswith('#'):
                f = ln.split('\t')
                dec[(f[0], int(f[1]))] = (f[3], f[4])
    reviewed = set()
    rv = RAW / 'gap_review_1841.tsv'
    if rv.exists():
        for ln in rv.read_text(encoding='utf-8').splitlines():
            if ln and not ln.startswith('#'):
                f = ln.split('\t')
                reviewed.add((f[0], int(f[1])))
    sh = W / 'sheets'
    sh.mkdir(exist_ok=True)
    for f in sh.glob(f'{only or "all"}_*.jpg'):
        f.unlink()
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 22)
    width = 1500
    items = []
    for n, rec in enumerate(locs):
        d = dec.get((rec['slug'], rec['ord']), ('?', ''))
        if only == 'auto' and d[0] == '?':
            continue
        if only == 'pending' and d[0] != '?':
            continue
        if 'box' not in rec:          # 未定位的没有裁图可看
            continue
        if only == 'todo' and (rec['slug'], rec['ord']) in reviewed:
            continue
        if only == 'todo' and rec.get('score', 0) < 0.5:   # 锚点覆盖低的十有八九是错位
            continue
        items.append((n, rec, d))
    rows, idx = [], []
    for n, rec, d in items:
        head = Image.new('L', (width, 64), 255)
        dr = ImageDraw.Draw(head)
        ctx = ' '.join(rec['left'][-6:]) + ' [[' + rec['tcp'] + ']] ' + ' '.join(rec['right'][:6])
        dr.text((6, 4), f"#{n} {rec['slug']}  {ctx}"[:150], font=font, fill=0)
        dr.text((6, 34), f"→ {d[0]}    {d[1]}"[:150], font=font, fill=90)
        rows.append(np.array(head))
        if 'box' in rec and (IMG / f"{rec['pid']}.jpg").exists():
            im = cv2.imread(str(IMG / f"{rec['pid']}.jpg"), cv2.IMREAD_GRAYSCALE)
            x0, y0, x1, y1 = rec['box']
            cx = (x0 + x1) // 2
            # 按真实栏缝切（按页面中线切会把右栏行首的词头切掉：`vine.` 只剩 `e.`）
            (a0, a1), (b0, b1) = _split_cols(im)
            c0, c1 = (0, a1 + 12) if cx < a1 else (max(0, b0 - 12), im.shape[1])
            # 锚点框可能跨栏、跨段（#333 框高 4000px，缩下来看不清）：框太高就以缺字词为中心裁
            if y1 - y0 > 260 and 'gy' in rec:
                y0, y1 = rec['gy'] - 90, rec['gy'] + 120
                cx = rec['gx']
                c0, c1 = (0, a1 + 12) if cx < a1 else (max(0, b0 - 12), im.shape[1])
            crop = im[max(0, y0 - 45):min(im.shape[0], y1 + 45), c0:c1]
            crop = cv2.resize(crop, (width, int(crop.shape[0] * width / crop.shape[1])))
            rows.append(crop)
        else:
            rows.append(np.full((20, width), 200, np.uint8))
        rows.append(np.full((8, width), 120, np.uint8))
        idx.append(n)
    page, h, k = [], 0, 0
    for r in rows:
        page.append(r)
        h += r.shape[0]
        if h > 2600 and r.shape[0] == 8:
            cv2.imwrite(str(sh / f'{only or "all"}_{k:03d}.jpg'), np.vstack(page), [cv2.IMWRITE_JPEG_QUALITY, 80])
            page, h, k = [], 0, k + 1
    if page:
        cv2.imwrite(str(sh / f'{only or "all"}_{k:03d}.jpg'), np.vstack(page), [cv2.IMWRITE_JPEG_QUALITY, 80])
        k += 1
    print(f'{len(items)} 条 → {k} 张 {sh}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['fetch', 'ocr', 'build', 'match', 'judge', 'sheets'])
    ap.add_argument('--only', choices=['auto', 'pending', 'todo'])
    a = ap.parse_args()
    if a.cmd == 'sheets':
        return sheets(a.only)
    {'fetch': fetch, 'ocr': ocr, 'build': build, 'match': match, 'judge': judge}[a.cmd]()


if __name__ == '__main__':
    main()
