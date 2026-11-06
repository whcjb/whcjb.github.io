#!/usr/bin/env python3
"""琼斯约翰二书、三书：缺字组清单 + 1635 胶片影像定位裁图（判读用）。

    python3 scripts/jones_witness.py gaps            # en_chapters → <book>/gap_sites.json
    python3 scripts/jones_witness.py crops           # 取叶 + 本地 OCR 定位 + 裁图（witness/，不入库）
    python3 scripts/jones_witness.py sheets          # 裁图拼成判读页 witness/sheets/*.jpg

骨架照搬 attersoll_witness.py。底本 TCP A04619 与 IA 胶片
`bim_…_jones-william-b-d_1635` 是同一册（剑桥大学图书馆藏本，扉页有馆藏章）。
IA 叶号 ≈ 印本页 + 9（page_numbers.json 只给了零星几页；定位时前后各放宽一叶，按 OCR 得分取）。
本地 tesseract（eng，psm 3，中值滤波）只作定位，**它读出的字不落盘**；判读一律看裁图。
"""
import collections
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jones_common as jc  # noqa: E402

ITEM = 'bim_early-english-books-1475-1640_a-commentary-upon-the-ep_jones-william-b-d_1635'
WIT = jc.BASE / 'witness'
IMG = WIT / 'img'
OCR = WIT / 'ocr'
CROP = WIT / 'crops'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'
NCTX = 12
LEAF_OFF = 9
RE_HW = re.compile(r"<span class='ocrx_word' id='[^']+' title='bbox (\d+) (\d+) (\d+) (\d+); x_wconf (\d+)'[^>]*>(.*?)</span>", re.S)


def gaps():
    for book in jc.BOOKS:
        sites = []
        od = jc.order(book)
        prev_tail, pnum = [], None
        for slug in od['order']:
            md = jc.read_src(book, slug)
            margins = [(m.start(), m.end()) for m in re.finditer(r'<span class="jw-margin[^"]*"[^>]*>.*?</span>', md, re.S)]
            blank = md
            for a, b in margins:
                blank = blank[:a] + ' ' * (b - a) + blank[b:]
            pns = [(m.start(), m.group(1)) for m in re.finditer(r'<span class="jw-pb"[^>]*data-p="(\d+)"', md)]
            if slug == 'title':
                pnum = None
            for a, b, s, isnote in jc.gap_groups(md):
                pn = next((x for p, x in reversed(pns) if p < a), pnum)
                extra = {}
                if isnote:
                    na, nb = next((x, y) for x, y in margins if x <= a < y)
                    left, right, stream = jc.flat_words(md[na:a]), jc.flat_words(md[b:nb]), 'note'
                    # 旁注挂在正文哪一处：自身上下文太短定位不到时，拿正文上下文找行，裁整行宽（含页边）
                    extra = {'mleft': (prev_tail + jc.flat_words(blank[:na]))[-NCTX:],
                             'mright': jc.flat_words(blank[nb:])[:NCTX]}
                else:
                    left = prev_tail + jc.flat_words(blank[:a])
                    right, stream = jc.flat_words(blank[b:]), 'main'
                sites.append({'gid': len(sites), 'slug': slug, 'stream': stream, 'tcp': s,
                              'left': left[-NCTX:], 'right': right[:NCTX], 'page': pn, **extra})
            if pns:
                pnum = pns[-1][1]
            prev_tail = jc.flat_words(blank)[-NCTX:]
        (jc.raw(book) / 'gap_sites.json').write_text(json.dumps(sites, ensure_ascii=False, indent=0), encoding='utf-8')
        c = collections.Counter('greek' if s['tcp'].strip('*') == '〈Greek〉' else 'other' for s in sites)
        print(f'{book}: 缺字组 {len(sites)} {dict(c)}', file=sys.stderr)


def fold(w):
    w = re.sub(r'[^a-z]', '', w.lower().replace('ſ', 's'))
    w = w.replace('v', 'u').replace('j', 'i').replace('y', 'i').replace('f', 's')
    w = re.sub(r'(.)\1+', r'\1', w)
    if len(w) > 3 and w.endswith('e'):
        w = w[:-1]
    return w


def leaf_img(leaf):
    IMG.mkdir(parents=True, exist_ok=True)
    f = IMG / f'bim_{leaf:04d}.jpg'
    if not f.exists() or f.stat().st_size < 10000:
        req = urllib.request.Request(f'https://archive.org/download/{ITEM}/page/n{leaf}.jpg', headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=300) as r:
            f.write_bytes(r.read())
    return f


def leaf_words(leaf):
    import html as H
    import cv2
    OCR.mkdir(parents=True, exist_ok=True)
    out = OCR / f'{leaf:04d}.json'
    if out.exists():
        return json.loads(out.read_text())
    img = cv2.imread(str(leaf_img(leaf)), cv2.IMREAD_GRAYSCALE)
    h, w = img.shape
    if w > 3000:                       # 原生 ≈5300 宽；tesseract 只作定位，缩半够用
        img = cv2.resize(img, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
        k = 2
    else:
        k = 1
    img = cv2.medianBlur(img, 3)
    with tempfile.TemporaryDirectory() as td:
        pth = Path(td) / 'p.png'
        cv2.imwrite(str(pth), img)
        subprocess.run(['tesseract', str(pth), str(Path(td) / 'o'), '-l', 'eng', '--psm', '3', 'hocr'],
                       check=True, capture_output=True)
        hc = (Path(td) / 'o.hocr').read_text(encoding='utf-8')
    ws = []
    for m in RE_HW.finditer(hc):
        t = H.unescape(re.sub(r'<[^>]+>', '', m.group(6))).strip()
        if t:
            x0, y0, x1, y1 = (int(v) * k for v in m.group(1, 2, 3, 4))
            ws.append([t, x0, y0, x1 - x0, y1 - y0])
    out.write_text(json.dumps(ws))
    return ws


def locate(s, mode=''):
    """在候选叶上按左右上下文找缺字位置：返回 (叶, x, y, 得分)。mode='m' 用旁注挂靠处的正文上下文。"""
    page = int(s['page']) if s.get('page') else None
    if page is None:
        return None
    left, right = (s['mleft'], s['mright']) if mode == 'm' else (s['left'], s['right'])
    L = [fold(x) for x in left[-6:] if fold(x)]
    R = [fold(x) for x in right[:6] if fold(x)]
    best = None
    for leaf in (page + LEAF_OFF, page + LEAF_OFF - 1, page + LEAF_OFF + 1, page + LEAF_OFF + 1 + 1):
        ws = leaf_words(leaf)
        fw = [fold(w[0]) for w in ws]
        for i in range(len(ws)):
            sc_l = sum(1 for k, x in enumerate(reversed(L)) if i - 1 - k >= 0 and fw[i - 1 - k] == x)
            # 缺字可能占 0–3 个 OCR 词；右侧从 i+j 起对
            for j in range(0, 4):
                sc_r = sum(1 for k, x in enumerate(R) if i + j + k < len(fw) and fw[i + j + k] == x)
                sc = sc_l + sc_r
                if sc >= 3 and (best is None or sc > best[3]):
                    a = ws[i - 1] if i else ws[i]
                    best = (leaf, a[1] + a[3], a[2] + a[4] // 2, sc)
    return best


def crops(only=None):
    import cv2
    CROP.mkdir(parents=True, exist_ok=True)
    rep = {}
    for book in jc.BOOKS:
        sites = json.loads((jc.raw(book) / 'gap_sites.json').read_text(encoding='utf-8'))
        for s in sites:
            key = f'{book}-{s["gid"]:03d}'
            if only and key not in only:
                continue
            loc = locate(s)
            wide = False
            if not loc and s['stream'] == 'note':
                loc = locate(s, 'm')
                wide = True
            if not loc:
                rep[key] = None
                print(f'  {key} 定位不到 p.{s.get("page")} {" ".join(s["left"][-4:])} ⟨{s["tcp"]}⟩', file=sys.stderr)
                continue
            leaf, x, y, sc = loc
            img = cv2.imread(str(leaf_img(leaf)), cv2.IMREAD_GRAYSCALE)
            h, w = img.shape
            lh = 95                                  # 原生分辨率下一行约 95 px
            if wide:                                 # 旁注：整行宽，上下多放几行（旁注常比挂靠处高低错开）
                y0, y1, x0, x1 = max(0, y - lh * 4), min(h, y + lh * 4), 0, w
            else:
                y0, y1 = max(0, y - int(lh * 1.6)), min(h, y + int(lh * 1.6))
                x0, x1 = max(0, x - 1300), min(w, x + 1500)
            cv2.imwrite(str(CROP / f'{key}.jpg'), img[y0:y1, x0:x1])
            rep[key] = dict(leaf=leaf, x=x, y=y, score=sc)
    (WIT / 'crops.json').write_text(json.dumps(rep, indent=0))
    ok = sum(1 for v in rep.values() if v)
    print(f'裁图 {ok}/{len(rep)}', file=sys.stderr)


def sheets(per=6):
    """裁图拼成判读页：每页 per 张，左上角标组号；缩到 1800 宽（看字仍够），一页影像只送一次。"""
    import cv2
    import numpy as np
    out = WIT / 'sheets'
    out.mkdir(parents=True, exist_ok=True)
    keys = sorted(p.stem for p in CROP.glob('*.jpg'))
    for n in range(0, len(keys), per):
        rows = []
        for k in keys[n:n + per]:
            im = cv2.imread(str(CROP / f'{k}.jpg'), cv2.IMREAD_GRAYSCALE)
            im = cv2.resize(im, (1800, int(im.shape[0] * 1800 / im.shape[1])), interpolation=cv2.INTER_AREA)
            bar = np.full((44, 1800), 255, np.uint8)
            cv2.putText(bar, k, (8, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.1, 0, 2)
            rows += [bar, im, np.full((8, 1800), 0, np.uint8)]
        cv2.imwrite(str(out / f'sheet_{n // per:02d}.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f'{(len(keys) + per - 1) // per} 张判读页 → {out}', file=sys.stderr)


def tight(per=8, W=1100):
    """紧图：定位点左 200、右 900、上下各约一行，原生分辨率不缩放；拼成判读页 witness/tight/。
    希腊小字缩放后认不清（2026-11-06 实测），判读一律看这一版。卷首卷末无页码的几处见 MANUAL_LOC。"""
    import cv2
    import numpy as np
    out = WIT / 'tight'
    out.mkdir(parents=True, exist_ok=True)
    tiles = []
    for book in jc.BOOKS:
        sites = json.loads((jc.raw(book) / 'gap_sites.json').read_text(encoding='utf-8'))
        for s in sites:
            key = f'{book}-{s["gid"]:03d}'
            if book == '3john' and s['slug'] in SHARED:
                continue                      # 两卷共用的卷首卷末只判一次（2john）
            if key in MANUAL_LOC:
                leaf, x, y = MANUAL_LOC[key]
            else:
                loc = locate(s) or (locate(s, 'm') if s['stream'] == 'note' else None)
                if not loc:
                    print(f'  {key} 定位不到', file=sys.stderr)
                    continue
                leaf, x, y = loc[:3]
            img = cv2.imread(str(leaf_img(leaf)), cv2.IMREAD_GRAYSCALE)
            h, w = img.shape
            x0 = max(0, x - 200)
            t = img[max(0, y - 110):min(h, y + 90), x0:x0 + W]
            if t.shape[1] < W:
                t = np.hstack([t, np.full((t.shape[0], W - t.shape[1]), 255, np.uint8)])
            tiles.append((key, t))
    for n in range(0, len(tiles), per):
        rows = []
        for k, t in tiles[n:n + per]:
            bar = np.full((34, W), 255, np.uint8)
            cv2.putText(bar, k, (6, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
            rows += [bar, t, np.full((6, W), 0, np.uint8)]
        cv2.imwrite(str(out / f't_{n // per:02d}.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f'{len(tiles)} 条 → {(len(tiles) + per - 1) // per} 张', file=sys.stderr)


SHARED = {'title', 'dedication', 'to-the-reader', 'errata'}
# 无页码（卷首）或定位不准的几处：(叶, x, y)，看整页图定的点（缺字左邻词的右端、行中线）
MANUAL_LOC = {}


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'gaps':
        gaps()
    elif cmd == 'crops':
        crops(set(sys.argv[2:]) or None)
    elif cmd == 'sheets':
        sheets()
    elif cmd == 'tight':
        tight()
    else:
        print(__doc__)
