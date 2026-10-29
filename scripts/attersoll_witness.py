#!/usr/bin/env python3
"""阿特索尔《腓利门书注释》(1612, EEBO-TCP A22481) 缺字的证人判读。骨架照搬 taylor_witness.py。

    python3 scripts/attersoll_witness.py gaps     # en_chapters → gap_sites.json（每组缺字 + 上下文）
    python3 scripts/attersoll_witness.py crops    # 每组缺字：取 1612 胶片对应叶 → 本地 OCR 定位 → 裁出所在行

证人
----
| 键 | IA item | 是什么 |
|---|---|---|
| bim | bim_…_attersoll-william_1612（IA40310712-04） | EEBO 缩微胶片（1265:10）的灰度扫描，**与 TCP 同一卷胶片** |
| e1633 | bim_…_william-attersoll_1633 | 1633 修订增补第二版：只作旁证 |

**落盘规则（memory feedback_no_guess_inference_needs_approval）：只有看图读出的才落；
按上下文/后出版次的推断写 P:xx，列清单待用户同意。** OCR 读数只用来定位，不作证据。
"""
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import attersoll_common as rc  # noqa: E402

ROOT = rc.ROOT
RAW = rc.RAW
W = RAW / 'witness'
NCTX = 8


# ── 1. 缺字清单 ──────────────────────────────────────────────────────
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
            margins = [(m.start(), m.end()) for m in re.finditer(r'<span class="at-margin[^"]*"[^>]*>.*?</span>', md, re.S)]
            blank = md
            for a, b in margins:
                blank = blank[:a] + ' ' * (b - a) + blank[b:]
            pbs = [(m.start(), int(m.group(1))) for m in re.finditer(r'<span class="at-pb"[^>]*data-facs="(\d+)"', md)]
            pns = [(m.start(), m.group(1)) for m in re.finditer(r'<span class="at-pb"[^>]*data-p="(\d+)"', md)]
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



# ── 2. 裁图：取叶 → 本地 OCR 定位 → 裁出缺字所在行 ───────────────────
ITEM = 'bim_early-english-books-1475-1640_a-commentarie-upon-the-e_attersoll-william_1612'
IMG, OCR, CROPS = W / 'img', W / 'ocr', W / 'crops'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'
RE_HW = re.compile(r"<span class='ocrx_word' id='[^']+' title='bbox (\d+) (\d+) (\d+) (\d+); x_wconf (\d+)'[^>]*>(.*?)</span>", re.S)


def fold(w):
    """比对口径：长 s 在 OCR 里成 f，所以 f 折成 s；u/v、i/j/y、双写、词尾 e 折平。"""
    w = re.sub(r'[^a-z]', '', w.lower().replace('ſ', 's'))
    w = w.replace('v', 'u').replace('j', 'i').replace('y', 'i').replace('f', 's')
    w = re.sub(r'(.)\1+', r'\1', w)
    w = w.replace('ie', 'i').replace('ei', 'i').replace('ee', 'e')
    if len(w) > 3 and w.endswith('e'):
        w = w[:-1]
    return w


def leaf_img(leaf):
    """整页图：IA 服务端缩到半宽（2548 宽，≈400 ppi）。叶号 = 访问页号（579 叶全部可访问）。"""
    import urllib.request
    IMG.mkdir(parents=True, exist_ok=True)
    f = IMG / f'bim_{leaf:04d}.jpg'
    if not f.exists():
        req = urllib.request.Request(f'https://archive.org/download/{ITEM}/page/n{leaf}_w2548.jpg',
                                     headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=300) as r:
            f.write_bytes(r.read())
    return f


def leaf_words(leaf):
    """本地 tesseract（eng，psm 3，中值滤波）→ [[词, x, y, w, h]]；只作定位。"""
    import html as H
    import subprocess
    import tempfile
    OCR.mkdir(parents=True, exist_ok=True)
    out = OCR / f'{leaf:04d}.json'
    if out.exists():
        return json.loads(out.read_text())
    import cv2
    img = cv2.medianBlur(cv2.imread(str(leaf_img(leaf)), cv2.IMREAD_GRAYSCALE), 3)
    with tempfile.TemporaryDirectory() as td:
        pth = Path(td) / 'p.png'
        cv2.imwrite(str(pth), img)
        subprocess.run(['tesseract', str(pth), str(Path(td) / 'o'), '-l', 'eng', '--psm', '3', 'hocr'],
                       check=True, capture_output=True)
        h = (Path(td) / 'o.hocr').read_text(encoding='utf-8')
    ws = []
    for m in RE_HW.finditer(h):
        t = H.unescape(re.sub(r'<[^>]+>', '', m.group(6))).strip()
        if t:
            x0, y0, x1, y1 = map(int, m.group(1, 2, 3, 4))
            ws.append([t, x0, y0, x1 - x0, y1 - y0])
    out.write_text(json.dumps(ws))
    return ws


def page_leaf():
    d = json.loads((W / 'page_numbers.json').read_text())['pages']
    m = {}
    for p in d:
        if p['pageNumber'].isdigit():
            m.setdefault(int(p['pageNumber']), p['leafNum'])
    return m


def candidates(s, pl):
    if s['page'] and s['slug'] != 'contents-table':
        lf = pl.get(int(s['page']))
        if lf:
            return list(range(lf - 4, lf + 3))      # IA 页码猜测会偏两三叶
    if s['slug'] == 'contents-table':
        return list(range(528, 537))     # 书末内容索引（叶 552 起是胶片重拍的卷首）
    return list(range(2, 24))


def score(ws, s):
    """在词流里找缺字位置：左 4 词 + 右 4 词按位置比对，取得分最高处。返回 (分, 左端词号, 右端词号)。"""
    fw = [fold(w[0]) for w in ws]
    L = [fold(x) for x in s['left'][-8:] if fold(x)]
    R = [fold(x) for x in s['right'][:8] if fold(x)]
    gl = max(1, len(s['tcp'].split()))
    best = (0, None, None)
    for i in range(len(fw)):
        sc = 0
        for k, x in enumerate(reversed(L)):
            j = i - 1 - k
            if 0 <= j < len(fw) and fw[j] == x:
                sc += 1
        for k, x in enumerate(R):
            j = i + gl + k
            if 0 <= j < len(fw) and fw[j] == x:
                sc += 1
        if sc > best[0]:
            best = (sc, i, i + gl - 1)
    return best


def crops(gids=None):
    from PIL import Image, ImageDraw
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    pl = page_leaf()
    CROPS.mkdir(parents=True, exist_ok=True)
    locs = {}
    for s in sites:
        if gids and s['gid'] not in gids:
            continue
        best = (0, None, None, None)
        for lf in candidates(s, pl):
            ws = leaf_words(lf)
            sc, a, b = score(ws, s)
            if sc > best[0]:
                best = (sc, lf, a, b)
        if s['stream'] == 'note' and best[0] < 3:
            t = dict(s, left=s['mleft'], right=s['mright'], tcp='x')
            for lf in candidates(s, pl):
                sc, a, b = score(leaf_words(lf), t)
                if sc > best[0]:
                    best = (sc, lf, a, b)
        sc, lf, a, b = best
        if lf is None:
            print(f'#{s["gid"]} 未定位', file=sys.stderr)
            continue
        ws = leaf_words(lf)
        a = min(a, len(ws) - 1)
        b = min(max(a, b), len(ws) - 1)
        x, y, w, h = ws[a][1:]
        y1 = max(ws[a][2] + ws[a][4], ws[b][2] + ws[b][4])
        im = Image.open(leaf_img(lf)).convert('RGB')
        lh = 62
        Y0, Y1 = max(0, min(y, ws[b][2]) - lh * 2), min(im.height, y1 + lh * 2)
        c = im.crop((0, Y0, im.width, Y1))
        dr = ImageDraw.Draw(c)
        dr.rectangle([x - 8, y - Y0 - 6, ws[b][1] + ws[b][3] + 8, y1 - Y0 + 6], outline=(230, 120, 0), width=3)
        c.save(CROPS / f'{s["gid"]:04d}.jpg', quality=85)
        locs[s['gid']] = dict(leaf=lf, score=sc, ocr=' '.join(w[0] for w in ws[a:b + 1]))
    f = RAW / 'witness_locs.json'
    old = json.loads(f.read_text()) if f.exists() else {}
    old.update({str(k): v for k, v in locs.items()})
    f.write_text(json.dumps(old, ensure_ascii=False, indent=0))
    print(f'裁图 {len(locs)}', file=sys.stderr)


def sheets(gids, name, per=6):
    """每条：一行文字（编号、TCP 上下文）+ 原版裁图，per 条拼一张。"""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    sites = {s['gid']: s for s in json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))}
    locs = json.loads((RAW / 'witness_locs.json').read_text())
    sh = W / 'sheets'
    sh.mkdir(exist_ok=True)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 26)
    width, rows, k, n = 1600, [], 0, 0
    for g in gids:
        s = sites[g]
        head = Image.new('L', (width, 70), 255)
        dr = ImageDraw.Draw(head)
        lo = locs.get(str(g), {})
        dr.text((6, 2), f"#{g} {s['slug']} p.{s['page']} {'[旁注]' if s['stream'] == 'note' else ''} leaf {lo.get('leaf')} "
                        f"score {lo.get('score')} OCR: {lo.get('ocr', '')}"[:100], font=font, fill=70)
        dr.text((6, 36), (' '.join(s['left'][-5:]) + ' [[' + s['tcp'] + ']] ' + ' '.join(s['right'][:5]))[:100],
                font=font, fill=0)
        f = CROPS / f'{g:04d}.jpg'
        im = Image.open(f).convert('L') if f.exists() else Image.new('L', (width, 40), 220)
        im = im.resize((width, max(1, int(im.height * width / im.width))))
        rows += [np.array(head), np.array(im), np.full((8, width), 40, np.uint8)]
        n += 1
        if n % per == 0:
            Image.fromarray(np.vstack(rows)).save(sh / f'{name}_{k:03d}.jpg', quality=85)
            rows, k = [], k + 1
    if rows:
        Image.fromarray(np.vstack(rows)).save(sh / f'{name}_{k:03d}.jpg', quality=85)
        k += 1
    print(f'{n} 条 → {k} 张', file=sys.stderr)


# ── 3. 旁证：1633 修订增补第二版（IA 自带 djvu.xml 词坐标定位，裁图看原图）────────
ITEM33 = 'bim_early-english-books-1475-1640_a-commentarie-upon-the-e_william-attersoll_1633'
_E33 = {}


def e1633_words():
    """djvu.xml → 全书词流 [(词, 叶, x0, y0, x1, y1)]，叶 = 访问页序（OBJECT 序）。"""
    if 'w' not in _E33:
        import html as H
        x = (W / 'e1633_djvu.xml').read_text(encoding='utf-8', errors='replace')
        out = []
        for leaf, obj in enumerate(re.findall(r'<OBJECT.*?</OBJECT>', x, re.S)):
            for m in re.finditer(r'<WORD coords="(\d+),(\d+),(\d+),(\d+)[^"]*"[^>]*>([^<]*)</WORD>', obj):
                x0, y1, x1, y0 = map(int, m.group(1, 2, 3, 4))
                out.append((H.unescape(m.group(5)), leaf, x0, y0, x1, y1))
        _E33['w'] = out
        _E33['f'] = [fold(w[0]) for w in out]
    return _E33['w'], _E33['f']


def e1633_locate(s, leaves=None):
    ws, fw = e1633_words()
    L = [fold(x) for x in s['left'][-8:] if fold(x)]
    R = [fold(x) for x in s['right'][:8] if fold(x)]
    best = (0, None)
    idx = collections.defaultdict(list)
    if 'idx' not in _E33:
        for i, f in enumerate(fw):
            idx[f].append(i)
        _E33['idx'] = idx
    idx = _E33['idx']
    cand = set()
    for k, x in enumerate(reversed(L)):
        cand |= {i + 1 + k for i in idx.get(x, [])}
    for k, x in enumerate(R):
        cand |= {i - 1 - k for i in idx.get(x, [])}
    if leaves is not None:
        cand = {i for i in cand if 0 <= i < len(ws) and ws[i][1] in leaves}
    for i in cand:
        sc = sum(1 for k, x in enumerate(reversed(L)) if 0 <= i - 1 - k < len(fw) and fw[i - 1 - k] == x)
        for gl in (1, 2):
            sc2 = sc + sum(1 for k, x in enumerate(R) if 0 <= i + gl + k < len(fw) and fw[i + gl + k] == x)
            if sc2 > best[0]:
                best = (sc2, i)
    return best


def e1633_hints():
    """各组在 1633 版的可信叶号（得分 ≥ 9），给得分低的组按前后组估叶。"""
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    ws, _ = e1633_words()
    good = {}
    for s in sites:
        sc, i = e1633_locate(s)
        if i is not None and sc >= 9:
            good[s['gid']] = ws[i][1]
    return good


def e1633_best(s, good):
    sc, i = e1633_locate(s)
    if i is not None and sc >= 9:
        return sc, i
    near = [good[g] for g in sorted(good, key=lambda g: abs(g - s['gid']))[:2]]
    if near:
        lv = set(range(min(near) - 2, max(near) + 3))
        sc2, i2 = e1633_locate(s, lv)
        if i2 is not None and sc2 > sc - 1:
            return sc2, i2
    return sc, i


def e1633_img(leaf):
    """半宽图（4378 宽）；djvu.xml 坐标按原图（8756 宽），用时放大一倍对齐。"""
    import urllib.request
    IMG.mkdir(parents=True, exist_ok=True)
    f = IMG / f'e1633_{leaf:04d}.jpg'
    if not f.exists():
        req = urllib.request.Request(f'https://archive.org/download/{ITEM33}/page/n{leaf}_w4378.jpg',
                                     headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=300) as r:
            f.write_bytes(r.read())
    return f


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['gaps', 'crops', 'sheets'])
    ap.add_argument('--gids')
    ap.add_argument('--name', default='s')
    ap.add_argument('--per', type=int, default=6)
    a = ap.parse_args()
    sel = None
    if a.gids:
        sel = []
        for part in a.gids.split(','):
            x, _, y = part.partition('-')
            sel += list(range(int(x), int(y or x) + 1))
    if a.cmd == 'gaps':
        gaps()
    elif a.cmd == 'crops':
        crops(set(sel) if sel else None)
    else:
        n = len(json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8')))
        sheets(sel or list(range(n)), a.name, a.per)
