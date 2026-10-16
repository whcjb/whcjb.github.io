#!/usr/bin/env python3
"""TCP 缺字 → 页面影像裁图（old-book-ocr §1 第 ③ 层：页面影像是最终证据）。

    python3 scripts/perkins_gapcrop.py locate        # 定位，写 gap_locs.json，报定位失败的
    python3 scripts/perkins_gapcrop.py sheets [--kind letter] [--per 10]
                                                     # 拼判读图 witness_1604/sheets/*.jpg

定位：拿缺字两侧各 ≤6 个词，在本地 tesseract 的词坐标里按**位置**对齐
（old-book-ocr §3.2 ①：拿最长匹配块当锚，不取首尾匹配块）。
字形折叠 f/ſ→s、v→u、j→i（tesseract eng 把长 s 读成 f；TCP 已把 ſ 录成 s），
两侧至少各对上 1 个词、合计 ≥3 个词才算定位成功；否则报出来手工处理，
不降低门槛硬凑——锚撞车会裁到隔壁那一行（§1 第 ② 层的失效区）。

判读图上每条：编号、TCP 原文（缺字处标【】）、本地 OCR 在同一位置读到的、裁图。
OCR 那一栏只当提示，判读一律以裁图为准。
"""
import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'perkins_raw' / 'galatians'
SRC = RAW / 'en_chapters'
W = RAW / 'witness_1604'
JP2 = W / 'jp2'
OCR = W / 'ocr'
SHEETS = W / 'sheets'
SITES = RAW / 'gap_sites.json'
LOCS = RAW / 'gap_locs.json'
ID = 'bim_early-english-books-1475-1640_a-commentarie-_perkins-william_1604'

TOK = re.compile(r'•+|〈◊〉|〈…〉|〈Greek〉|▪')
CTX = 6


def fold(w):
    w = w.lower().replace('ſ', 's').replace('f', 's').replace('v', 'u').replace('j', 'i')
    w = w.replace('̄', '')
    return re.sub(r'[^a-z]', '', w)


def load_ocr(leaf):
    p = OCR / f'{leaf:04d}.tsv'
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding='utf-8').splitlines()[1:]:
        f = ln.split('\t')
        if len(f) < 12 or f[0] != '5' or not f[11].strip():
            continue
        out.append({'t': f[11], 'x': int(f[6]), 'y': int(f[7]), 'w': int(f[8]),
                    'h': int(f[9]), 'line': (f[2], f[3], f[4]), 'k': fold(f[11])})
    return out


def site_contexts():
    """每处缺字在 md 里的上下文（旁注里的缺字只取旁注内的上下文）。"""
    sites = json.loads(SITES.read_text(encoding='utf-8'))
    by = {}
    for i, s in enumerate(sites):
        s['id'] = i
        by.setdefault(s['slug'], []).append(s)
    for slug, lst in by.items():
        md = (SRC / f'{slug}.md').read_text(encoding='utf-8')
        ms = list(TOK.finditer(md))
        assert len(ms) == len(lst), slug
        for o, (s, m) in enumerate(zip(lst, ms)):
            s['ord'] = o
            a, b = m.start(), m.end()
            o = md.rfind('<span class="pk-margin"', 0, a)
            in_note = o >= 0 and md.find('</span>', o) > a
            if in_note:
                lo = md.find('>', o) + 1
                hi = md.find('</span>', o)
            else:
                lo, hi = 0, len(md)
            left = md[lo:a]
            right = md[b:hi]
            if not in_note:
                left = re.sub(r'<span class="pk-margin"[^>]*>.*?</span>', ' ', left)
                right = re.sub(r'<span class="pk-margin"[^>]*>.*?</span>', ' ', right)
            left = re.sub(r'<[^>]+>', ' ', left).replace('*', '')
            right = re.sub(r'<[^>]+>', ' ', right).replace('*', '')
            # 缺字所在的那个词：贴着记号的左右残字
            lw = re.search(r'(\S*)$', left).group(1)
            rw = re.match(r'^(\S*)', right).group(1)
            s['word'] = lw + m.group(0) + rw
            s['left'] = left[:len(left) - len(lw)].split()[-CTX:]
            s['right'] = right[len(rw):].split()[:CTX]
            s['in_note'] = in_note
            if in_note:
                # 旁注挂靠处前后的正文：旁注排在它旁边的页边，拿正文定行
                o_end = md.find('</span>', o) + len('</span>')
                bl = re.sub(r'<span class="pk-margin"[^>]*>.*?</span>', ' ', md[max(0, o - 400):o])
                br = re.sub(r'<span class="pk-margin"[^>]*>.*?</span>', ' ', md[o_end:o_end + 400])
                bl = re.sub(r'<[^>]+>', ' ', bl).replace('*', '').split()[-8:]
                br = re.sub(r'<[^>]+>', ' ', br).replace('*', '').split()[:8]
                s['anchor'] = bl + br
            s['tcp'] = (' '.join(s['left']) + ' 【' + s['word'] + '】 ' + ' '.join(s['right'])).strip()
    return sites


def locate(s, ctx=8):
    """锚点投票（old-book-ocr §3.2 ①：拿匹配块当锚，不要求从缺字处起连续对上）。

    TCP 两侧各取 ctx 个词；每个 ≥3 字母、在本叶 OCR 里能**逐字（折叠后）**
    找到的词，按它与缺字的相对位置推出一个「缺字在 OCR 词流里的下标」投一票。
    票数最多的下标 ±1 内的票合计 ≥3、且两侧（有上下文的那侧）都至少有一票，才算定位成功。
    一个 OCR 错字只少一票，不会让整串对齐断掉。"""
    L = [fold(w) for w in s['left'][-ctx:]]
    R = [fold(w) for w in s['right'][:ctx]]
    best = None
    F = int(s['facs'])
    for leaf in (2 * F - 3, 2 * F - 2):
        words = load_ocr(leaf)
        if not words:
            continue
        index = {}
        for j, w in enumerate(words):
            index.setdefault(w['k'], []).append(j)
        # 左票：g = 缺字之后第一个 OCR 词的下标（精确推得）；
        # 右票：h = 右侧上下文首词的下标 = g + k（k = 缺字词占了几个 OCR 词，0~4 未知）
        lv, rv = {}, {}
        for t, k in enumerate(L):
            if len(k) < 3:
                continue
            for j in index.get(k, []):
                lv.setdefault(j + (len(L) - t), set()).add(j)
        for t, k in enumerate(R):
            if len(k) < 3:
                continue
            for j in index.get(k, []):
                rv.setdefault(j - t, set()).add(j)
        need_l = any(len(k) >= 3 for k in L)
        need_r = any(len(k) >= 3 for k in R)
        cands = set(lv) | {h - k for h in rv for k in range(0, 5)}
        for g in cands:
            ls = set().union(*[lv.get(g + d, set()) for d in (-1, 0, 1)])
            rs = set().union(*[rv.get(g + k, set()) for k in range(0, 6)])
            if (need_l and not ls) or (need_r and not rs):
                continue
            score = len(ls) + len(rs)
            if best is None or score > best[0]:
                lj = max(ls) if ls else None
                rj = min(rs) if rs else None
                best = (score, leaf, lj, rj, len(ls), len(rs))
    if not best or best[0] < 3:
        return None
    score, leaf, lj, rj, nl, nr = best
    words = load_ocr(leaf)
    lo = lj if lj is not None else max(0, rj - 3)
    hi = rj if rj is not None else min(len(words) - 1, lj + 3)
    if hi < lo or hi - lo > 14:          # 左右锚相距太远 = 撞车，不认
        return None
    # 裁图范围：两锚各再往外带 3 个词，但只取两锚所在的行（跨行缺字两行都要）
    lines = {words[lo]['line'], words[hi]['line']}
    span = [w for w in words[max(0, lo - 3):hi + 4] if w['line'] in lines] or words[lo:hi + 1]
    # 左右锚不在同一行时（缺字落在行尾/行首），两行都要
    mid = words[lo + 1:hi] if lj is not None and rj is not None else []
    return {'leaf': leaf, 'score': score, 'nl': nl, 'nr': nr,
            'ocr_mid': ' '.join(w['t'] for w in mid),
            'box': [min(w['x'] for w in span), min(w['y'] for w in span),
                    max(w['x'] + w['w'] for w in span), max(w['y'] + w['h'] for w in span)],
            'mid_box': ([min(w['x'] for w in mid), min(w['y'] for w in mid),
                         max(w['x'] + w['w'] for w in mid), max(w['y'] + w['h'] for w in mid)]
                        if mid else None)}


def cmd_locate():
    sites = site_contexts()
    ok = fail = 0
    for s in sites:
        loc = locate(s)
        s['loc'] = loc
        if loc:
            ok += 1
        else:
            fail += 1
    LOCS.write_text(json.dumps(sites, ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
    print(f'定位成功 {ok}，失败 {fail}', file=sys.stderr)
    for s in sites:
        if not s['loc']:
            print(f"  #{s['id']} {s['slug']} p{s['page']} facs{s['facs']} {s['kind']}: {s['tcp'][:100]}",
                  file=sys.stderr)


_img_cache = {}


def page_img(leaf):
    if leaf not in _img_cache:
        _img_cache.clear()
        _img_cache[leaf] = cv2.imread(str(JP2 / f'{ID}_{leaf:04d}.jp2'), cv2.IMREAD_GRAYSCALE)
    return _img_cache[leaf]


def crop(s, pad_x=60, pad_y=40):
    loc = s['loc']
    im = page_img(loc['leaf'])
    x0, y0, x1, y1 = loc['box']
    H, Wd = im.shape
    c = im[max(0, y0 - pad_y):min(H, y1 + pad_y), max(0, x0 - pad_x):min(Wd, x1 + pad_x)].copy()
    if loc['mid_box']:   # 缺字处画一道下划线（不遮字）
        mx0, my0, mx1, my1 = loc['mid_box']
        ox, oy = max(0, x0 - pad_x), max(0, y0 - pad_y)
        cv2.line(c, (mx0 - ox, my1 - oy + 12), (mx1 - ox, my1 - oy + 12), 0, 4)
    return c


def ascii_safe(t):
    t = t.replace('•', '#').replace('〈◊〉', '<WORD>').replace('〈…〉', '<SPAN>') \
         .replace('〈Greek〉', '<GREEK>').replace('▪', '<P>').replace('【', '[[').replace('】', ']]')
    t = t.replace('̄', '~').replace('&', '&')
    return ''.join(ch if ord(ch) < 128 else '?' for ch in t)


def cmd_sheets(kind, per, width=1500):
    sites = json.loads(LOCS.read_text(encoding='utf-8'))
    todo = [s for s in sites if s['loc'] and (kind == 'all' or s['kind'] == kind)]
    SHEETS.mkdir(exist_ok=True)
    for f in SHEETS.glob(f'{kind}_*.jpg'):
        f.unlink()
    n = 0
    for b in range(0, len(todo), per):
        rows = []
        for s in todo[b:b + per]:
            c = crop(s)
            scale = min(1.0, width / c.shape[1])
            c = cv2.resize(c, (int(c.shape[1] * scale), int(c.shape[0] * scale)),
                           interpolation=cv2.INTER_AREA)
            canvas = np.full((c.shape[0] + 70, width), 255, np.uint8)
            canvas[70:, :c.shape[1]] = c
            cv2.putText(canvas, f"#{s['id']} {s['kind']}  {ascii_safe(s['tcp'])[:118]}", (6, 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, 0, 2)
            cv2.putText(canvas, f"ocr: {ascii_safe(s['loc']['ocr_mid'])[:80]}   (leaf {s['loc']['leaf']})",
                        (6, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.65, 90, 1)
            rows.append(canvas)
            rows.append(np.full((14, width), 160, np.uint8))
        sheet = np.vstack(rows)
        path = SHEETS / f'{kind}_{b // per:03d}.jpg'
        cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
        n += 1
    print(f'{len(todo)} 条 → {n} 张判读图（{SHEETS}）', file=sys.stderr)


# ---------------------------------------------------------------------------
# 行段裁图：定位失败（旁注里上下文太短）或判读时发现裁错行的，改用 TCP 的版心
# 行号定位。<milestone n="5|10|…"> 是原书版心右侧印的行号（影像上看得见），
# 缺字落在「最近一个行号 L」之后、L+5 之前；裁出 L-1 … L+6 共约 8 行的整幅宽
# （旁注在页边，必须带上页边）。判读时拿 TCP 上下文对着这一段找。

_page_words = None


def page_words():
    """篇:印本页 → 该页 TCP 全部词（折叠后）。前置篇无页码，按 TCP 图号 facs 归页。"""
    global _page_words
    if _page_words is None:
        _page_words = {}
        rx = re.compile(r'<span class="pk-pb" id="p([^"]+)" data-p="[^"]+" data-facs="(\d+)"></span>')
        for f in SRC.glob('*.md'):
            md = f.read_text(encoding='utf-8')
            parts = rx.split(md)
            keys = [(f.stem, None)] + [(f.stem, parts[i]) for i in range(1, len(parts), 3)]
            texts = [parts[0]] + [parts[i + 2] for i in range(1, len(parts), 3)]
            for k, t in zip(keys, texts):
                t = re.sub(r'<[^>]+>', ' ', t).replace('*', '')
                _page_words.setdefault(k, set()).update(fold(w) for w in t.split() if len(fold(w)) >= 4)
    return _page_words


def pick_leaf(s):
    """对开图的两叶里哪一叶是这一页：拿**整页** TCP 词与两叶 OCR 词比重合数。
    只拿缺字两侧上下文去比会选错（实测 #39/#69/#73 三条全错到对页）。"""
    F = int(s['facs'])
    want = page_words().get((s['slug'], s['page']), set())
    best = None
    for leaf in (2 * F - 3, 2 * F - 2):
        n = len(want & {w['k'] for w in load_ocr(leaf)})
        if best is None or n > best[0]:
            best = (n, leaf)
    return best[1]


def body_lines(leaf):
    """本叶正文行（按 y 排序）：词数 ≥3 的 OCR 行，取每行 y 中心。"""
    lines = {}
    for w in load_ocr(leaf):
        lines.setdefault(w['line'], []).append(w)
    out = []
    for ws in lines.values():
        if len(ws) < 3:
            continue
        y0 = min(w['y'] for w in ws)
        y1 = max(w['y'] + w['h'] for w in ws)
        x0 = min(w['x'] for w in ws)
        x1 = max(w['x'] + w['w'] for w in ws)
        out.append((y0, y1, x0, x1))
    out.sort()
    # 合并 y 重叠的（tesseract 常把一行的版心与页边旁注拆成两条「行」）
    merged = []
    for ln in out:
        if merged and ln[0] < (merged[-1][0] + merged[-1][1]) / 2:
            p = merged[-1]
            merged[-1] = (min(p[0], ln[0]), max(p[1], ln[1]), min(p[2], ln[2]), max(p[3], ln[3]))
        else:
            merged.append(ln)
    return merged


def ocr_lines(leaf):
    """本叶 OCR 行：[(折叠后的字母串, 框)]，按 y 排。"""
    lines = {}
    for w in load_ocr(leaf):
        lines.setdefault(w['line'], []).append(w)
    out = []
    for ws in lines.values():
        box = [min(w['x'] for w in ws), min(w['y'] for w in ws),
               max(w['x'] + w['w'] for w in ws), max(w['y'] + w['h'] for w in ws)]
        out.append((''.join(w['k'] for w in ws), box))
    out.sort(key=lambda t: t[1][1])
    return out


def band(s):
    """行级模糊匹配：缺字上下文（字母串）与每条 OCR 行比，取「这一行有多少落在上下文里」
    最高的那行。逐词精确对位失败的（旁注、OCR 读花的行）大多能这样找回。"""
    leaf = pick_leaf(s)
    if s.get('anchor'):
        ctx = ''.join(fold(w) for w in s['anchor'])
    else:
        ctx = ''.join(fold(w) for w in s['left'] + [s['word']] + s['right'])
    best = None
    for lt, box in ocr_lines(leaf):
        if len(lt) < 8:
            continue
        sm = SequenceMatcher(None, lt, ctx, autojunk=False)
        hit = sum(b.size for b in sm.get_matching_blocks() if b.size >= 3)
        score = hit / len(lt)
        if best is None or score > best[0]:
            best = (score, box)
    if not best or best[0] < 0.45:
        return None
    x0, y0, x1, y1 = best[1]
    h = y1 - y0
    if s.get('in_note'):
        # 旁注：只裁页边那一栏 + 正文贴边的一截，**原生分辨率**（缩小后小号字读不出）
        lines = [b for lt, b in ocr_lines(leaf) if len(lt) > 40]
        bl = sorted(b[0] for b in lines)[len(lines) // 2] if lines else 600
        br = sorted(b[2] for b in lines)[len(lines) // 2] if lines else 3400
        W = page_img(leaf).shape[1]
        left_w, right_w = bl, W - br
        xa, xb = (max(0, bl - 900), bl + 350) if left_w > right_w else (br - 350, min(W, br + 900))
        return {'leaf': leaf, 'box': [xa, y0 - int(3.5 * h), xb, y1 + int(3.5 * h)], 'mid_box': None,
                'ocr_mid': f'line-match {best[0]:.2f} margin', 'score': 0, 'nl': 0, 'nr': 0, 'native': True}
    return {'leaf': leaf, 'box': [0, y0 - int(1.6 * h), 10 ** 6, y1 + int(1.6 * h)], 'mid_box': None,
            'ocr_mid': f'line-match {best[0]:.2f}', 'score': 0, 'nl': 0, 'nr': 0}


def cmd_band_sheets(ids, per=3, width=1500):
    sites = {s['id']: s for s in json.loads(LOCS.read_text(encoding='utf-8'))}
    SHEETS.mkdir(exist_ok=True)
    for f in SHEETS.glob('band_*.jpg'):
        f.unlink()
    todo = []
    for i in ids:
        s = sites[i]
        b = band(s)
        if b:
            s['band'] = b
            todo.append(s)
        else:
            print(f'  #{i} 行级也对不上', file=sys.stderr)
    for k in range(0, len(todo), per):
        rows = []
        for s in todo[k:k + per]:
            b = s['band']
            im = page_img(b['leaf'])
            H, Wd = im.shape
            x0, y0, x1, y1 = b['box']
            c = im[max(0, y0):min(H, y1), max(0, x0):min(Wd, x1)]
            scale = min(1.0, width / c.shape[1]) if b.get('native') else width / c.shape[1]
            c = cv2.resize(c, (int(c.shape[1] * scale), int(c.shape[0] * scale)), interpolation=cv2.INTER_AREA)
            if c.shape[1] < width:
                c = np.hstack([c, np.full((c.shape[0], width - c.shape[1]), 255, np.uint8)])
            head = np.full((70, width), 255, np.uint8)
            cv2.putText(head, f"#{s['id']} {s['kind']} {'NOTE ' if s['in_note'] else ''} {ascii_safe(s['tcp'])[:110]}",
                        (6, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.72, 0, 2)
            cv2.putText(head, f"leaf {b['leaf']}  tcp-line~{s.get('line')}  {b['ocr_mid']}", (6, 58),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, 90, 1)
            rows += [head, c, np.full((14, width), 160, np.uint8)]
        cv2.imwrite(str(SHEETS / f'band_{k // per:03d}.jpg'), np.vstack(rows),
                    [cv2.IMWRITE_JPEG_QUALITY, 82])
    print(f'{len(todo)} 条 → {(len(todo) + per - 1) // per} 张行段图', file=sys.stderr)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['locate', 'sheets', 'band'])
    ap.add_argument('--ids', default='')
    ap.add_argument('--kind', default='letter')
    ap.add_argument('--per', type=int, default=10)
    a = ap.parse_args()
    if a.cmd == 'locate':
        cmd_locate()
    elif a.cmd == 'band':
        cmd_band_sheets([int(x) for x in a.ids.split(',') if x], a.per)
    else:
        cmd_sheets(a.kind, a.per)
