#!/usr/bin/env python3
"""雷登《彼得前书》缺字的证人判读（old-book-ocr 第 ②③ 层）。

    python3 scripts/leighton_witness.py build    # 四份 hOCR → witness/words_{r1864,orig}.json
    python3 scripts/leighton_witness.py match    # 每处缺字：1864 本定位读出 + 原版同页定位 → witness_locs.json
    python3 scripts/leighton_witness.py sheets [--only todo|all]   # 判读图：TCP 上下文 + 原版裁图 + 1864 裁图

证人
----
| 键 | IA item | 是什么 | 用途 |
|---|---|---|---|
| orig | comment00leig（卷一 1693 York）、pract00leig（卷二 1694 London） | **与 TCP 同一版**的实物扫描（非缩微胶片） | 最终依据：裁图看原书这一处印的是什么 |
| r1864 | 1864practicalcom01/02leiguoft（Philadelphia: Presbyterian Board） | 重排本，现代字体 | OCR 干净，用来定位与读出候选词 |

原版的 IA OCR 很糟（长 s 读成 f：`thofc`、`arc`），只拿来在页内找位置，**读法以看图为准**。
1864 本是重排本，拼法现代化（Iesus→Jesus、then→than），读出的词只当候选，落盘写 1693/94 的写法。

**落盘规则（2026-10-16 用户定）：只有看图核过、证人在同一位置明确读出的才可落盘；
凡推断（本书用词、上下文）一律列清单待用户同意。** 判读结论由 leighton_review.py 录入
gap_review_witness.tsv，证据列写 `img orig …` / `img r1864 …`。

页图不入库（witness/ 在 .gitignore），按需从 IA 单页接口取：
`https://archive.org/download/<item>/page/n<leaf>.jpg`（leaf 从 0 起，与 hOCR 的 page_NNNNNN 对应）。
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
import leighton_common as lc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'leighton_raw' / '1peter'
W = RAW / 'witness'
IMG = W / 'img'
ITEMS = {'orig': [('comment00leig', 1), ('pract00leig', 2)],
         'r1864': [('1864practicalcom01leiguoft', 1), ('1864practicalcom02leiguoft', 2)]}
TOK = lc.TOK
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'


def fold(w):
    """比对口径：两侧同一个函数。长 s 在原版 OCR 里成 f，所以 f 折成 s；u/v、i/j/y、双写、词尾 e 折平。"""
    w = re.sub(r'[^a-z]', '', w.lower().replace('ſ', 's'))
    w = w.replace('v', 'u').replace('j', 'i').replace('y', 'i').replace('f', 's')
    w = re.sub(r'(.)\1+', r'\1', w)
    w = w.replace('ie', 'i').replace('ei', 'i').replace('ee', 'e')
    if len(w) > 3 and w.endswith('e'):
        w = w[:-1]
    return w


RE_PAGE = re.compile(r'<div class="ocr_page" id="page_(\d+)" title="bbox 0 0 (\d+) (\d+)')
RE_WORD = re.compile(r'<span class="ocrx_word" id="[^"]+" title="bbox (\d+) (\d+) (\d+) (\d+)[^"]*">([^<]*)</span>')


def build():
    for key, items in ITEMS.items():
        words = []
        for item, vol in items:
            text = (W / f'{item}.hocr.html').read_text(encoding='utf-8', errors='replace')
            starts = [(m.start(), int(m.group(1)), int(m.group(2)), int(m.group(3)))
                      for m in RE_PAGE.finditer(text)] + [(len(text), 0, 0, 0)]
            for i in range(len(starts) - 1):
                s, leaf, pw, ph = starts[i]
                chunk = text[s:starts[i + 1][0]]
                for m in RE_WORD.finditer(chunk):
                    t = html.unescape(m.group(5)).strip()
                    if not t:
                        continue
                    x0, y0, x1, y1 = map(int, m.group(1, 2, 3, 4))
                    # 行末断词 `excel-` + `lency` → 一个词
                    if words and words[-1]['t'].endswith('-') and len(words[-1]['t']) > 2 \
                            and t[:1].islower() and words[-1]['item'] == item:
                        words[-1]['t'] = words[-1]['t'][:-1] + t
                        words[-1]['k'] = fold(words[-1]['t'])
                        continue
                    words.append({'t': t, 'k': fold(t), 'item': item, 'vol': vol, 'leaf': leaf,
                                  'pw': pw, 'ph': ph, 'x': x0, 'y': y0, 'w': x1 - x0, 'h': y1 - y0})
        (W / f'words_{key}.json').write_text(json.dumps(words), encoding='utf-8')
        print(f'{key}: {len(words)} 词', file=sys.stderr)


class Stream:
    def __init__(self, key):
        self.key = key
        self.ws = json.loads((W / f'words_{key}.json').read_text())
        self.keys = [w['k'] for w in self.ws]
        self.tri = collections.defaultdict(list)
        for k in range(len(self.keys) - 2):
            self.tri[(self.keys[k], self.keys[k + 1], self.keys[k + 2])].append(k)

    def find(self, left, right, vol):
        """两侧三词组投票定位（同 hutcheson_witness.Stream.find），只在同一卷里找。"""
        L = [fold(w) for w in left if not TOK.search(w) and fold(w)]
        R = [fold(w) for w in right if not TOK.search(w) and fold(w)]
        votes = collections.Counter()
        for t in range(len(L) - 2):
            for k in self.tri.get(tuple(L[t:t + 3]), ())[:60]:
                if self.ws[k]['vol'] == vol:
                    votes[(k + len(L) - t) // 4] += 1
        for t in range(len(R) - 2):
            for k in self.tri.get(tuple(R[t:t + 3]), ())[:60]:
                if self.ws[k]['vol'] == vol:
                    votes[(k - t - 1) // 4] += 1
        best = None
        for bucket, v in votes.most_common(4):
            if v < 2:
                break
            c = bucket * 4
            r = locate(self.keys, L, R, max(0, c - 16), min(len(self.ws), c + 20))
            if r and (not best or r[2] > best[2]):
                best = r
        return best


def locate(keys, L, R, lo, hi):
    """左块紧贴缺字左边、右块紧贴右边，中间隔 0–6 词。→ (i, j, 覆盖率)"""
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
    if not (0 <= j - i <= 6):
        return None
    cov = min(sum(b.size for b in lb) / len(L), sum(b.size for b in rb) / len(R))
    return i, j, round(cov, 2)


def context(md, a, b, n=8):
    left = re.sub(r'<[^>]+>', ' ', md[:a]).replace('*', ' ').split()[-n:]
    right = re.sub(r'<[^>]+>', ' ', md[b:b + 600]).replace('*', ' ').split()[:n]
    return left, right


def page_box(ws, i, j):
    g = ws[min(i, len(ws) - 1)]
    span = [x for x in range(max(0, i - 3), min(len(ws), j + 3)) if ws[x]['leaf'] == g['leaf']
            and ws[x]['item'] == g['item']]
    return {'item': g['item'], 'leaf': g['leaf'], 'pw': g['pw'], 'gx': g['x'], 'gy': g['y'],
            'box': [min(ws[x]['x'] for x in span), min(ws[x]['y'] for x in span),
                    max(ws[x]['x'] + ws[x]['w'] for x in span), max(ws[x]['y'] + ws[x]['h'] for x in span)]}


def match():
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    vol_of = {}
    for s in sites:
        vol_of.setdefault(s['slug'], s['vol'])
    streams = {k: Stream(k) for k in ITEMS}
    rows = [l.rstrip('\n').split('\t') for l in (RAW / 'gap_decisions.tsv').read_text(encoding='utf-8').splitlines()
            if l and not l.startswith('#')]
    out = []
    mds = {}
    for slug, ordi, word, auto, ev in rows:
        md = mds.setdefault(slug, (lc.SRC / f'{slug}.md').read_text(encoding='utf-8'))
        m = list(TOK.finditer(md))[int(ordi)]
        a, b = lc.gap_word(md, m)
        left, right = context(md, a, b)
        vol = vol_of.get(slug, 1 if slug in ('1', '2', 'title1', 'reader1', 'errata1') else 2)
        rec = {'slug': slug, 'ord': int(ordi), 'tcp': word, 'corpus': auto, 'corpus_ev': ev,
               'left': left, 'right': right, 'vol': vol}
        for k, st in streams.items():
            r = st.find(left, right, vol)
            if r:
                i, j, sc = r
                rec[k] = {'read': ' '.join(w['t'] for w in st.ws[i:j]), 'score': sc, **page_box(st.ws, i, j)}
        out.append(rec)
    (RAW / 'witness_locs.json').write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    c = collections.Counter(('r1864' in r, 'orig' in r) for r in out)
    print(f'缺字词 {len(out)}；定位（1864, 原版）: {dict(c)}', file=sys.stderr)


_ACCESS = {}


def access_index(item, leaf):
    """hOCR 的页序号 = 全部扫描叶（含色卡、空白等不对外显示的叶）；IA 单页接口 page/n{N}
    的 N 只数对外显示的叶。按 <item>_scandata.xml 的 addToAccessFormats 换算——不换算会
    裁到别的页上（2026-10-16 第一版判读图整批裁错，就是这个原因）。"""
    if item not in _ACCESS:
        s = (W / f'{item}_scandata.xml').read_text(encoding='utf-8', errors='replace')
        pages = re.findall(r'<page leafNum="(\d+)">(.*?)</page>', s, re.S)
        acc = [int(n) for n, b in pages if re.search(r'<addToAccessFormats>true', b)]
        _ACCESS[item] = {leaf: i for i, leaf in enumerate(acc)}
    return _ACCESS[item][leaf]


def page_img(item, leaf):
    IMG.mkdir(parents=True, exist_ok=True)
    f = IMG / f'{item}_{leaf:04d}.jpg'          # 文件名用 hOCR 叶号，下载时换算成 page/n
    if not f.exists():
        n = access_index(item, leaf)
        req = urllib.request.Request(f'https://archive.org/download/{item}/page/n{n}.jpg',
                                     headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            f.write_bytes(r.read())
    return f


WIDE = False


def crop(loc, width=1400):
    import cv2
    im = cv2.imread(str(page_img(loc['item'], loc['leaf'])), cv2.IMREAD_GRAYSCALE)
    sc = im.shape[1] / loc['pw'] if loc['pw'] else 1.0
    gy = int(loc['gy'] * sc)
    x0, _, x1, _ = [int(v * sc) for v in loc['box']]
    # 只裁缺字那一行上下各一行左右（原版行高约 70–100px），一张判读图放 8 条；
    # rest 模式放宽到上下各约 4 行，并在缺字词位置画框（页边旁注也一并裁进来）
    lh = max(60, int(loc['box'][3] * sc - loc['box'][1] * sc) // 2 + 60)
    if WIDE:
        lh = 330
        import cv2 as _cv
        im = _cv.cvtColor(im, _cv.COLOR_GRAY2BGR)
        gx = int(loc['gx'] * sc)
        _cv.rectangle(im, (max(0, gx - 30), gy - 15), (gx + 260, gy + 95), (0, 0, 255), 4)
    c = im[max(0, gy - lh):min(im.shape[0], gy + lh + 40), :]
    if c.ndim == 3:      # 画框后转回灰度（框成深灰粗线），与判读图其余条带同通道
        c = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)
    return cv2.resize(c, (width, int(c.shape[0] * width / c.shape[1])))


def sheets(only):
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    reviewed, resolved = set(), set()
    rv = RAW / 'gap_review_witness.tsv'
    if rv.exists():
        for ln in rv.read_text(encoding='utf-8').splitlines():
            if ln and not ln.startswith('#'):
                f = ln.split('\t')
                reviewed.add((f[0], int(f[1])))
                if f[3] != '?':
                    resolved.add((f[0], int(f[1])))
    global WIDE
    WIDE = (only == 'rest')
    sh = W / 'sheets'
    sh.mkdir(exist_ok=True)
    for f in sh.glob(f'{only}_*.jpg'):
        f.unlink()
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 22)
    width = 1400
    rows, n_items, k = [], 0, 0
    for n, rec in enumerate(locs):
        if only == 'todo' and (rec['slug'], rec['ord']) in reviewed:
            continue
        if only == 'rest' and (rec['slug'], rec['ord']) in resolved:
            continue
        if 'orig' not in rec and 'r1864' not in rec:
            continue
        head = Image.new('L', (width, 64), 255)
        dr = ImageDraw.Draw(head)
        ctx = ' '.join(rec['left'][-7:]) + ' [[' + rec['tcp'] + ']] ' + ' '.join(rec['right'][:7])
        dr.text((6, 4), f"#{n} {rec['slug']}  {ctx}"[:140], font=font, fill=0)
        r64 = rec.get('r1864', {}).get('read', '—')
        dr.text((6, 34), f"预填 → {rec.get('auto', '?')}    1864: {r64}    语料: {rec['corpus']}    （上：1693/94 原版；下：1864）"[:140], font=font, fill=90)
        rows.append(np.array(head))
        for key in ('orig', 'r1864'):
            if key in rec:
                try:
                    rows.append(crop(rec[key], width))
                except Exception as e:      # noqa: BLE001
                    print(f'  #{n} {key} 取图失败 {e}', file=sys.stderr)
                rows.append(np.full((4, width), 200, np.uint8))
        rows.append(np.full((10, width), 90, np.uint8))
        n_items += 1
        if n_items % (3 if WIDE else 8) == 0:
            cv2.imwrite(str(sh / f'{only}_{k:03d}.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 80])
            rows, k = [], k + 1
    if rows:
        cv2.imwrite(str(sh / f'{only}_{k:03d}.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 80])
        k += 1
    print(f'{n_items} 条 → {k} 张 {sh}', file=sys.stderr)


# ── 自动预读（只当判读图上的预填值，不落盘）──────────────────────────────
DEC_W = RAW / 'gap_decisions_witness.tsv'


def judge():
    """1864 读数 + TCP 残字 → 预填读法。复用 hutcheson_witness.judge_one（同一套字形相容、
    罗马数字换算、整词拼写回映规则），语料换成本书的。结果只是判读图上的预填值。"""
    import hutcheson_witness as hw
    forms = collections.defaultdict(collections.Counter)
    freq = collections.Counter()
    for f in lc.SRC.glob('*.md'):
        for t in re.sub(r'<[^>]+>', ' ', f.read_text(encoding='utf-8')).replace('*', ' ').split():
            core = t.strip('.,;:()?!\'"[]’‘')
            if TOK.search(t) or not re.fullmatch(r'[A-Za-z]+', core):
                continue
            forms[hw.fold(core)][core] += 1
            freq[core.lower()] += 1
    lex = collections.defaultdict(set)
    for w in Path('/usr/share/dict/web2').read_text().split():
        if w.islower():
            lex[len(w)].add(w)
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    rows, tally = [], collections.Counter()
    for rec in locs:
        r64 = rec.get('r1864')
        hrec = {'tcp': rec['tcp']}
        if r64:
            hrec.update(wit=r64['read'], score=r64['score'])
        fixed, ev = hw.judge_one(hrec, forms, freq, lex)
        ev = ev.replace('w1841', 'r1864')
        tally['预填' if fixed != '?' else '无预填'] += 1
        rec['auto'] = fixed
        rows.append((rec['slug'], rec['ord'], rec['tcp'], fixed, ev))
    DEC_W.write_text('# 1864 读数 + 残字的自动预读，只是判读图预填值，不落盘\n'
                     + '\n'.join('\t'.join(map(str, r)) for r in rows) + '\n', encoding='utf-8')
    (RAW / 'witness_locs.json').write_text(json.dumps(locs, ensure_ascii=False, indent=0), encoding='utf-8')
    print('  '.join(f'{k} {v}' for k, v in tally.items()), file=sys.stderr)


def relocate():
    """第二轮：未判出的（复核为 ? 或未出图），按同篇前后已定位缺字夹出页码范围（±2 叶），
    在两份证人各自词流里按「左文 + 右文」相似度找最佳落点；单侧兜底。写回 witness_locs.json
    （记 relocated=True，原读数不覆盖已有的高分定位）。判读图照样逐条看图定夺。"""
    locs = json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))
    done = set()
    rv = RAW / 'gap_review_witness.tsv'
    for ln in rv.read_text(encoding='utf-8').splitlines():
        if ln and not ln.startswith('#'):
            f = ln.split('\t')
            if f[3] != '?':
                done.add((f[0], int(f[1])))
    n_new = 0
    for key in ITEMS:
        st = Stream(key)
        by_slug = collections.defaultdict(list)
        for r in locs:
            if key in r and r[key]['score'] >= 0.5:
                by_slug[r['slug']].append((r['ord'], r[key]['item'], r[key]['leaf']))
        for r in locs:
            if (r['slug'], r['ord']) in done:
                continue
            kn = sorted(by_slug.get(r['slug'], []))
            b = [x for x in kn if x[0] < r['ord']]
            a = [x for x in kn if x[0] > r['ord']]
            ref = (b[-1] if b else None) or (a[0] if a else None)
            if not ref:
                continue
            item = ref[1]
            lo = (b[-1][2] if b else a[0][2]) - 2
            hi = (a[0][2] if a else b[-1][2]) + 2
            if hi - lo > 14:
                continue
            idx = [k for k, w in enumerate(st.ws) if w['item'] == item and lo <= w['leaf'] <= hi]
            if not idx:
                continue
            L = [fold(w) for w in r['left'] if not TOK.search(w) and fold(w)]
            R = [fold(w) for w in r['right'] if not TOK.search(w) and fold(w)]
            best = None
            for k in idx:
                for gap in (0, 1, 2, 3):
                    sl = SequenceMatcher(None, st.keys[k:k + len(L)], L, autojunk=False).ratio() if L else 0
                    sr = SequenceMatcher(None, st.keys[k + len(L) + gap:k + len(L) + gap + len(R)], R,
                                         autojunk=False).ratio() if R else 0
                    sc = max(min(sl, sr), 0.85 * max(sl, sr))
                    if not best or sc > best[0]:
                        best = (sc, k + len(L), k + len(L) + gap)
            if best and best[0] >= 0.45:
                old = r.get(key)
                if old and old['score'] >= best[0]:
                    continue
                sc, i, j = best
                r[key] = {'read': ' '.join(w['t'] for w in st.ws[i:j]), 'score': round(sc, 2),
                          'relocated': True, **page_box(st.ws, i, j)}
                n_new += 1
    (RAW / 'witness_locs.json').write_text(json.dumps(locs, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'第二轮定位 {n_new} 处', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build', 'match', 'judge', 'sheets', 'relocate'])
    ap.add_argument('--only', default='todo', choices=['todo', 'all', 'rest'])
    a = ap.parse_args()
    if a.cmd == 'sheets':
        return sheets(a.only)
    {'build': build, 'match': match, 'judge': judge, 'relocate': relocate}[a.cmd]()


if __name__ == '__main__':
    main()
