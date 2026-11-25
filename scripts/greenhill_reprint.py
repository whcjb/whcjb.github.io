#!/usr/bin/env python3
"""格林希尔《以西结书释义》推断条（判读表 P:）对第二证人：Nichol 1863 爱丁堡重排本。

    python3 scripts/greenhill_reprint.py build     # djvu.xml → witness/nichol1863/words.json
    python3 scripts/greenhill_reprint.py match     # P: 各条 → witness/nichol1863/locs.json
    python3 scripts/greenhill_reprint.py sheets    # 判读图 witness/nichol1863/sheets/p_*.jpg

证人：IA anexpositionofth00greeuoft（Toronto 藏本，Sherman 编，xv+859 页）。
重排本、现代拼法、旁注多改脚注或删去——只证「是哪个词」，不证原书拼法。
与 EEBO 胶片不是同一实物：墨团、透印不会两本同处。
"""
import collections
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import greenhill_common as rc  # noqa: E402
from greenhill_witness import fold, locate, UA  # noqa: E402

ITEM = 'anexpositionofth00greeuoft'
W = rc.RAW / 'witness' / 'nichol1863'
TOK = rc.TOK


def build():
    """djvu.xml：OBJECT 顺序即 page/n{N} 的 N。词坐标 coords="x0,y1,x1,y0"。"""
    src = (W / 'djvu.xml').read_text(encoding='utf-8', errors='replace')
    words = []
    for n, m in enumerate(re.finditer(r'<OBJECT [^>]*width="(\d+)" height="(\d+)">(.*?)</OBJECT>', src, re.S)):
        pw, ph = int(m.group(1)), int(m.group(2))
        for line in re.finditer(r'<LINE>(.*?)</LINE>', m.group(3), re.S):
            for x0, y1, x1, y0, t in re.findall(r'<WORD coords="(\d+),(\d+),(\d+),(\d+)[^>]*>([^<]*)</WORD>', line.group(1)):
                x0, y0, x1, y1, t = int(x0), int(y0), int(x1), int(y1), t.strip()
                if words and words[-1]['n'] == n and words[-1]['t'].endswith('-') and t[:1].islower():
                    words[-1]['t'] = words[-1]['t'][:-1] + t       # 行末连字号接回
                    words[-1]['k'] = fold(words[-1]['t'])
                    continue
                words.append({'t': t, 'k': fold(t), 'n': n, 'pw': pw, 'ph': ph,
                              'x': x0, 'y': y0, 'w': x1 - x0, 'h': y1 - y0})
    (W / 'words.json').write_text(json.dumps(words), encoding='utf-8')
    print(f'{len(words)} 词', file=sys.stderr)


def p_rows():
    out = []
    for line in (rc.RAW / 'gap_review.tsv').read_text(encoding='utf-8').splitlines():
        f = line.split('\t')
        if len(f) > 1 and not line.startswith('#') and f[1].startswith('P:'):
            out.append((int(f[0]), f[1][2:], f[3] if len(f) > 3 else ''))
    return out


def match():
    """两侧各取 3 词组、2 词组投票；重排本改过字，覆盖率门槛放低到 0.4，判读看图定。
    定不到的：按 gid 前后已定位条在词流中的位置插值，只给估位。"""
    ws = json.loads((W / 'words.json').read_text())
    keys = [w['k'] for w in ws]
    idx = {n: collections.defaultdict(list) for n in (2, 3)}
    for n in (2, 3):
        for k in range(len(keys) - n + 1):
            idx[n][tuple(keys[k:k + n])].append(k)
    sites = {s['gid']: s for s in json.loads((rc.RAW / 'gap_sites.json').read_text(encoding='utf-8'))}
    gids_all = sorted(sites)
    locs = {}
    for gid, guess, note in p_rows():
        s = sites[gid]
        L = [fold(w) for w in s['left'] if not TOK.search(w) and fold(w)]
        R = [fold(w) for w in s['right'] if not TOK.search(w) and fold(w)]
        best = None
        for n in (3, 2):
            votes = collections.Counter()
            for t in range(len(L) - n + 1):
                for k in idx[n].get(tuple(L[t:t + n]), ())[:60]:
                    votes[(k + len(L) - t) // 4] += 1
            for t in range(len(R) - n + 1):
                for k in idx[n].get(tuple(R[t:t + n]), ())[:60]:
                    votes[(k - t - 1) // 4] += 1
            for bucket, v in votes.most_common(5):
                if v < 2:
                    break
                c = bucket * 4
                r = locate(keys, L, R, max(0, c - 20), min(len(ws), c + 24))
                if r and r[2] >= 0.4 and (not best or r[2] > best[2]):
                    best = r
                if not r and v >= 3 and not best:     # 两侧一边对上一边改写了：取票最多处作估位
                    best = (c, c, 0.0)
            if best and best[2] >= 0.4:
                break
        locs[gid] = {'gid': gid, 'guess': guess, 'stream': s['stream'],
                     'i': best[0], 'j': best[1], 'cov': best[2]} if best else {'gid': gid, 'guess': guess, 'stream': s['stream']}
    # 估位插值：用全书相邻已定位条（不限 P:）——这里只有 P: 条，按 gid 次序取前后已定位者
    done = sorted((g, r['i']) for g, r in locs.items() if 'i' in r and r['cov'] >= 0.4)
    for g, r in locs.items():
        if 'i' in r and r['cov'] >= 0.4:
            continue
        before = [x for x in done if x[0] < g]
        after = [x for x in done if x[0] > g]
        if before and after:
            (g0, i0), (g1, i1) = before[-1], after[0]
            if i1 > i0 and i1 - i0 < 60000:
                r['est'] = int(i0 + (i1 - i0) * (gids_all.index(g) - gids_all.index(g0)) /
                               max(1, gids_all.index(g1) - gids_all.index(g0)))
    for r in locs.values():
        k = r.get('i', r.get('est'))
        if k is not None:
            k = min(k, len(ws) - 1)
            r['n'] = ws[k]['n']
            r['read'] = ' '.join(w['t'] for w in ws[r['i']:r['j']]) if 'i' in r and r['cov'] >= 0.4 else ''
    (W / 'locs.json').write_text(json.dumps(list(locs.values()), ensure_ascii=False, indent=0), encoding='utf-8')
    c = collections.Counter('定位' if r.get('cov', 0) >= 0.4 else '估位' if 'n' in r else '无' for r in locs.values())
    print(dict(c), file=sys.stderr)


def page_img(n):
    f = W / 'img' / f'n{n:04d}.jpg'
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(f'https://archive.org/download/{ITEM}/page/n{n}.jpg', headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=300) as r:
            f.write_bytes(r.read())
    return f


def crop(r, ws):
    """定位条：所在行上下各三行、该栏全宽，框出缺字位置；估位条/旁注：取整页。"""
    from PIL import Image, ImageDraw
    n = r['n']
    im = Image.open(page_img(n)).convert('RGB')
    pg = [w for w in ws if w['n'] == n]
    pw = pg[0]['pw'] if pg else im.width
    sc = im.width / pw
    if r.get('cov', 0) >= 0.4 and r['stream'] == 'main':
        a = ws[min(r['i'], len(ws) - 1)]
        b = ws[max(r['i'], r['j'] - 1)] if r['j'] > r['i'] else a
        h = max(a['h'], 30)
        mid = pw / 2
        col = (0, mid) if a['x'] + a['w'] / 2 < mid else (mid, pw)
        # 单栏页：词横跨中线就取全宽
        if any(w['x'] < mid - 50 and w['x'] + w['w'] > mid + 50 for w in pg):
            col = (0, pw)
        X0, X1 = max(0, col[0] - 20), min(pw, col[1] + 20)
        Y0, Y1 = max(0, a['y'] - h * 6), min(r_ph(pg, im, sc), a['y'] + h * 7)
        c = im.crop((int(X0 * sc), int(Y0 * sc), int(X1 * sc), int(Y1 * sc)))
        dr = ImageDraw.Draw(c)
        x0 = a['x'] - X0 - 8
        x1 = (b['x'] + b['w'] if abs(b['y'] - a['y']) < h else a['x'] + max(a['w'], h)) - X0 + 8
        if r['j'] == r['i']:          # 重排本此处无字：在左邻词末尾画竖线
            p = ws[r['i'] - 1]
            x0 = x1 = p['x'] + p['w'] - X0 + 6
        dr.rectangle([x0 * sc, (a['y'] - Y0 - 8) * sc, x1 * sc, (a['y'] + h - Y0 + 8) * sc], outline=(230, 120, 0), width=4)
    else:
        c = im
    return c


def r_ph(pg, im, sc):
    return pg[0]['ph'] if pg else im.height / sc


def sheets(per_h=2050, width=1150):
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    ws = json.loads((W / 'words.json').read_text())
    locs = sorted(json.loads((W / 'locs.json').read_text(encoding='utf-8')), key=lambda r: r['gid'])
    sites = {s['gid']: s for s in json.loads((rc.RAW / 'gap_sites.json').read_text(encoding='utf-8'))}
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 22)
    sh = W / 'sheets'
    sh.mkdir(exist_ok=True)
    for f in sh.glob('*.jpg'):
        f.unlink()
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(page_img, sorted({r['n'] for r in locs if 'n' in r})))
    rows, k, tot = [], 0, 0

    def flush():
        nonlocal rows, k
        if rows:
            Image.fromarray(np.vstack(rows)).save(sh / f'p_{k:03d}.jpg', quality=85)
            rows, k = [], k + 1
    for kind in ('loc', 'page'):
        for r in locs:
            located = r.get('cov', 0) >= 0.4 and r['stream'] == 'main'
            if (kind == 'loc') != located or 'n' not in r:
                continue
            s = sites[r['gid']]
            head = Image.new('L', (width, 58), 255)
            dr = ImageDraw.Draw(head)
            tag = '' if located else ('【旁注·整页找】' if r['stream'] == 'note' else '【估位·整页找】')
            dr.text((6, 2), f"#{r['gid']}  推断 P:{r['guess']}  n{r['n']} {tag}"[:90], font=font, fill=70)
            dr.text((6, 30), (' '.join(s['left'][-5:]) + ' [[' + s['tcp'] + ']] ' + ' '.join(s['right'][:5]))[:95], font=font, fill=0)
            c = crop(r, ws).convert('L')
            c = c.resize((width, max(1, int(c.height * width / c.width))))
            if not located and c.height > per_h - 70:
                c = c.resize((int(c.width * (per_h - 70) / c.height), per_h - 70))
                pad = Image.new('L', (width, c.height), 255)
                pad.paste(c, (0, 0))
                c = pad
            if rows and sum(x.shape[0] for x in rows) + 58 + c.height > per_h:
                flush()
            rows += [np.array(head), np.array(c), np.full((6, width), 40, np.uint8)]
            tot += 1
        flush()
    print(f'{tot} 条 → {k} 张 {sh}/p_*.jpg', file=sys.stderr)


if __name__ == '__main__':
    {'build': build, 'match': match, 'sheets': sheets}[sys.argv[1]]()
