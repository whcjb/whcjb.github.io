#!/usr/bin/env python3
"""卡里尔缺部 OCR：kraken ALTO → 逐页版面（页眉／页码／正文行／旁注／接字）→ caryl_raw/job_ocr/p<部>/pages.json

    /usr/bin/python3 scripts/caryl_ocr_assemble.py 4            # 只读已识别的叶
    /usr/bin/python3 scripts/caryl_ocr_assemble.py 4 --show 30  # 打印一叶的分类结果（核对用，不看图）

版面判据（第 4 部实测，坐标是缩放后的像素）：
- 正文栏左右界：宽行（≥ 页宽 40%）的行首、行尾各用 RANSAC 拟合一条直线（版心两缘可斜），旁注一侧用全部固定栏宽推，见 column_bounds。kraken 会把同一高度的旁注与正文连成一行
  （「bæc verba sunt am clean in thy sight…」），所以**按词**划：词起点在右栏界以外、或终点在左栏界以内的归旁注（词中心判据会漏短词，实测 ces、Ifa.）。
- 页眉：正文首行含 Chap./Exposition/Vers 之一；页码：页眉附近的纯数字短行。
- 接字（catchword）：末行、短（< 栏宽 25%）、靠右——是下一页首词的重复，丢。
- 分段：行首比栏左界缩进 ≥ 35px 起新段（原书段首缩一格）。
- 行末 `¬`（kraken 出的断词号）或 `-`：与下一行首词拼合。
"""
import argparse
import collections
import json
import re
import statistics
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'caryl_raw' / 'job_ocr'
TWO_COL = {82}          # 第 8 部底本：1676–77 对开本，双栏
RE_HEAD = re.compile(r'Chap|Expo|Vers|Verf|Book|Bok|JOB|IOB', re.I)


def load(p):
    r = ET.parse(p).getroot()
    ns = r.tag.split('}')[0] + '}'
    pg = r.find(f'.//{ns}Page')
    W, H = int(float(pg.get('WIDTH'))), int(float(pg.get('HEIGHT')))
    lines = []
    for tl in r.iter(ns + 'TextLine'):
        ws = [dict(t=s.get('CONTENT'), x=int(float(s.get('HPOS'))), w=int(float(s.get('WIDTH'))))
              for s in tl.iter(ns + 'String') if s.get('CONTENT')]
        if not ws:
            continue
        lines.append(dict(x=int(float(tl.get('HPOS'))), y=int(float(tl.get('VPOS'))),
                          w=int(float(tl.get('WIDTH'))), h=int(float(tl.get('HEIGHT'))), words=ws))
    lines.sort(key=lambda l: (l['y'], l['x']))
    return W, H, lines


def edge_line(pts, tol=12):
    """RANSAC：在 (y, x) 点里找最多点落在 ±tol 内的直线 x = a·y + b（版心左右缘可能是斜的——扫描透视变形，行本身仍水平；实测斜率到 0.033，上限放到 0.06）。
    → (a, b, 内点数)。正文行的行首／行尾共线，粘连了旁注的行乱跳，凑不成线——即使它们占多数。"""
    best = (0.0, statistics.median(x for _, x in pts) if pts else 0, 0)
    n = len(pts)
    for i in range(n):
        for j in range(i + 1, n):
            (ya, xa), (yb, xb) = pts[i], pts[j]
            if abs(yb - ya) < 200:
                continue
            a = (xb - xa) / (yb - ya)
            if abs(a) > 0.06:
                continue
            b = xa - a * ya
            k = sum(1 for y, x in pts if abs(a * y + b - x) <= tol)
            if k > best[2]:
                best = (a, b, k)
    return best


def edge_fits(lines, W):
    """宽行（≥ 页宽 40%）的行首、行尾各拟合一条直线 → ((a0, b0, k0), (a1, b1, k1))；宽行不足 6 条 → None。"""
    wide = [l for l in lines if l['w'] >= W * 0.4][:60]
    if len(wide) < 6:
        return None
    return (edge_line([(l['y'], l['words'][0]['x']) for l in wide]),
            edge_line([(l['y'], l['words'][-1]['x'] + l['words'][-1]['w']) for l in wide]))


def column_bounds(fits, width):
    """→ (左界 y→x, 右界 y→x)。旁注一侧的行首／行尾被粘连行搅乱（第 4 部第 11 叶右侧旁注，行尾拟合只得 12 个内点，
    而且落在旁注外缘），所以取内点多的一侧作锚，另一侧 = 锚 ± 全部固定栏宽（同一版式，栏宽不变；斜变形两缘平行）。
    两侧都拟合得好且宽度与栏宽相差 ≤ 30px 时，两侧都用自己的。"""
    if not fits:
        return None
    (a0, b0, k0), (a1, b1, k1) = fits
    if k0 < 4 and k1 < 4:
        return None
    ym = 2000
    if k0 >= 8 and k1 >= 8 and abs((a1 * ym + b1) - (a0 * ym + b0) - width) <= 30:
        return (lambda y: a0 * y + b0), (lambda y: a1 * y + b1)
    if k0 >= k1:
        return (lambda y: a0 * y + b0), (lambda y: a0 * y + b0 + width)
    return (lambda y: a1 * y + b1 - width), (lambda y: a1 * y + b1)


def part_width(all_fits):
    """全部栏宽：两侧都有 ≥ 15 个内点、两缘平行（斜率差 < 0.01）的页，取宽度中位数。"""
    ws = [(a1 * 2000 + b1) - (a0 * 2000 + b0) for f in all_fits.values() if f
          for (a0, b0, k0), (a1, b1, k1) in [f] if k0 >= 15 and k1 >= 15 and abs(a0 - a1) < 0.01]
    return statistics.median(ws) if ws else None


def text(ws):
    return ' '.join(w['t'] for w in ws).strip()


def layout(W, H, lines, fits=None, width=None, detect_head=True):
    wide = [l for l in lines if l['w'] >= W * 0.4]
    if len(wide) < 5:
        return dict(kind='other', lines=[text(l['words']) for l in lines])
    # 栏界：见 column_bounds（行首、行尾各拟合直线，旁注一侧用固定栏宽推）。中位数、众数、页图投影都试过：
    # 旁注多的页粘连行过半，中位数／众数被拉到旁注外缘；版心左右缘又是斜的，投影里的栏缝被抹掉。
    cb = column_bounds(fits, width) if width else None
    if cb:
        fx0, fx1 = cb
    else:
        m0 = statistics.median(l['x'] for l in wide)
        m1 = statistics.median(l['x'] + l['w'] for l in wide)
        fx0, fx1 = (lambda y: m0), (lambda y: m1)
    ymid = statistics.median(l['y'] for l in wide)
    # 拟合出的栏界有几十 px 的偏差（第 4 部第 11 叶右界低估约 40px）：用两侧没粘旁注的整行实测行首、行尾再校一次
    d0 = [l['words'][0]['x'] - fx0(l['y']) for l in wide if abs(l['words'][0]['x'] - fx0(l['y'])) <= 60]
    d1 = [l['words'][-1]['x'] + l['words'][-1]['w'] - fx1(l['y']) for l in wide
          if abs(l['words'][-1]['x'] + l['words'][-1]['w'] - fx1(l['y'])) <= 60]
    s0 = statistics.median(d0) if len(d0) >= 5 else 0
    s1 = statistics.median(d1) if len(d1) >= 5 else 0
    gx0, gx1 = fx0, fx1
    fx0 = lambda y: gx0(y) + s0          # noqa: E731
    fx1 = lambda y: gx1(y) + s1          # noqa: E731
    x0, x1 = fx0(ymid), fx1(ymid)
    body, margin = [], []
    for l in lines:
        lx0, lx1 = fx0(l['y']), fx1(l['y'])
        ws = []
        for w in l['words']:
            # kraken 把跨栏缝的两截认成一个词（for-crius、immelo-ta）：越过右界且含连字符的，在连字符处劈开
            m = re.match(r'(.+?[-¬])(.+)$', w['t'])
            if m and w['x'] < lx1 - 15 < w['x'] + w['w'] - 20 and w['x'] + w['w'] > lx1 + 25:
                k = len(m.group(1)) / len(w['t'])
                ws += [dict(t=m.group(1), x=w['x'], w=int(w['w'] * k)),
                       dict(t=m.group(2), x=int(lx1 + 30), w=int(w['w'] * (1 - k)))]
            else:
                ws.append(w)
        l['words'] = ws
        # 起点越过右界／终点不到左界 = 旁注。原用「接近右界 15px」，行尾的 a、is 这类窄词起点离右界不到 15px，被划进旁注
        # （第 4 部印本第 181 页一页丢了 4 个）
        bw = [w for w in ws if w['x'] < lx1 - 2 and w['x'] + w['w'] > lx0 + 2]
        mw = [w for w in l['words'] if w not in bw]
        if mw:
            margin.append(dict(y=l['y'], side='L' if mw[0]['x'] < x0 else 'R', t=text(mw)))
        if bw:
            bx = bw[0]['x']
            body.append(dict(y=l['y'], x=bx, end=bw[-1]['x'] + bw[-1]['w'], t=text(bw), lx0=lx0, lx1=lx1))
    head, pageno, catch = None, None, None
    # 页眉：前两行里含页眉字样的；页码：页眉之前或同高的纯数字
    for k in range(min(3, len(body))):
        b = body[k]
        if re.fullmatch(r'[\dIl|]{1,4}\.?', b['t']):
            pageno = b['t']
            continue
        # 页眉须含 Chap／Exposition；只含 Job、Book、Vers 的行可能是正文（「…then Job saith here」）或段首出处行
        # （第 9 部第 383 叶「IOB 31. Verf. 9, 10, 11, 12.」曾被当页眉吞掉，连同它之前的行）。
        # 页眉断出来的单独一截「Vers.1.」只在本页第一行、且很短时才认。
        if detect_head and (re.search(r'Chap|Expo', b['t'], re.I) and len(b['t']) < 90 or
                            k == 0 and len(b['t']) <= 12 and re.match(r'V\w{2,4}', b['t'])):
            head = b['t']
            body = body[k + 1:]
            # 页眉右端的「Vers. 3.」有时断成下一行（第 4 部第 24 叶等）
            if body and re.fullmatch(r'V\w{2,4}[.,]?\s*[\dIlo]{1,3}\W{0,2}', body[0]['t']):
                head += ' ' + body[0]['t']
                body = body[1:]
            break
    pageno_m = [m for m in margin if re.fullmatch(r'\d{1,4}', m['t']) and m['y'] < H * 0.2]
    if pageno_m and not pageno:
        pageno = pageno_m[0]['t']
    margin = [m for m in margin if m not in pageno_m]
    body = [b for b in body if b['t'] != pageno]
    while body and len(re.sub(r'\W', '', body[-1]['t'])) <= 3 and re.search(r'\d|^[A-Z]+$', body[-1]['t']):
        body = body[:-1]                    # 页底书帖签名（「3」「C 3」「Aa」）
    if body:
        last = body[-1]
        if last['end'] - last['x'] < (x1 - x0) * 0.25 and last['x'] > x0 + (x1 - x0) * 0.5:
            catch = last['t']
            body = body[:-1]
    while body and len(re.sub(r'\W', '', body[-1]['t'])) <= 4 and re.search(r'\d|^[A-Z][a-z]?\s?[a-z]?\s?\d?$', body[-1]['t']):
        body = body[:-1]                    # 接字后面还有书帖签名（「A a 3」在接字「Is」之前一行）
    if body:                                # 正文首行之上的「旁注」是页眉断出来的残片（「4. 181」）
        margin = [m for m in margin if m['y'] >= body[0]['y'] - 10]
    for b in body:
        b['indent'] = b['x'] - b['lx0'] >= 35
        b['short'] = b['end'] < b['lx1'] - 80
    return dict(kind='text', x0=x0, x1=x1, head=head, pageno=pageno, catch=catch, body=body, margin=margin)


def split_columns(lines, W, H):
    """对开本双栏：宽行（≥ 页宽 25%）的行首聚成左右两团，取两团之间最大的间隙作分界；页顶横跨两栏的页眉单独取出。
    → (页顶行, 左栏行, 右栏行)；分不出两团 → None。"""
    # 页顶：页高 10% 以内、像页眉（CHAP./Exposition）或纯数字（页码）的行；按固定比例切会把正文首行也切进来
    top = [l for l in lines if l['y'] < H * 0.1 and (RE_HEAD.search(text(l['words'])) or
                                                      re.fullmatch(r'\d{1,4}', text(l['words']).strip()))]
    rest = [l for l in lines if l not in top]
    xs = sorted(l['words'][0]['x'] for l in rest if l['w'] >= W * 0.25)
    if len(xs) < 10:
        return None
    gaps = [(xs[i + 1] - xs[i], i) for i in range(len(xs) - 1) if W * 0.25 < xs[i + 1] < W * 0.75]
    if not gaps:
        return None
    g, i = max(gaps)
    if g < W * 0.15:
        return None
    cut = (xs[i] + xs[i + 1]) / 2
    left = [l for l in rest if l['words'][0]['x'] < cut]       # 按行首归栏：左栏行宽，按中心点会越过分界
    right = [l for l in rest if l['words'][0]['x'] >= cut]
    return top, left, right


def layout2(W, H, lines, fitsL, fitsR, width):
    """双栏一页：两栏各自 layout，再先左后右拼；页顶行里认页眉、页码。"""
    top, left, right = split_columns(lines, W, H)
    L = layout(W / 2, H, left, fits=fitsL, width=width, detect_head=False)   # 栏宽约半页；页眉整页已取
    R = layout(W / 2, H, right, fits=fitsR, width=width, detect_head=False)
    if L['kind'] != 'text' or R['kind'] != 'text':
        return layout(W, H, lines)
    toptext = ' '.join(text(l['words']) for l in top)
    head = toptext if RE_HEAD.search(toptext) else (L['head'] or R['head'])
    nums = [int(x) for x in re.findall(r'(?:^|\s)(\d{1,4})(?=\s|$)', toptext)]
    big = [x for x in nums if x >= 100]          # 栏间行号（10、20、30…）也落在页顶，栏号是三位数
    pageno = str(min(big)) if big else (L['pageno'] or R['pageno'])   # 两栏各有号（331、332），取左栏的小号
    if pageno and pageno.isdigit() and int(pageno) % 2 == 0:
        pageno = str(int(pageno) - 1)            # 左栏号恒为奇数；读到偶数 = 只读到右栏号（左栏号在暗边上没读出）
    # 对开本两栏之间的栏缝印行号（每 10 行一个：20、30…），落进旁注，去掉
    margin = [m for m in L['margin'] + R['margin'] if not re.fullmatch(r'[\dIlO]{1,3}', m['t'].strip())]
    return dict(kind='text', x0=L['x0'], x1=R['x1'], head=head, pageno=pageno, catch=R['catch'],
                body=L['body'] + R['body'], margin=margin, cols=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('part', type=int)
    ap.add_argument('--show', type=int)
    a = ap.parse_args()
    d = BASE / f'p{a.part}'
    loaded = {}
    for p in sorted((d / 'alto').glob('*.xml')):
        try:
            loaded[p.stem] = load(p)
        except ET.ParseError:            # kraken 还在写的半截文件
            print(f'跳过未写完的 {p.name}', file=sys.stderr)
    if a.part in TWO_COL:
        cols = {k: split_columns(v[2], v[0], v[1]) for k, v in loaded.items()}
        fitsL = {k: edge_fits(c[1], loaded[k][0] / 2) if c else None for k, c in cols.items()}
        fitsR = {k: edge_fits(c[2], loaded[k][0] / 2) if c else None for k, c in cols.items()}
        width = part_width({**{k + 'L': f for k, f in fitsL.items()}, **{k + 'R': f for k, f in fitsR.items()}})
        print(f'第 {a.part} 部（双栏）栏宽 {width:.0f}px', file=sys.stderr)
        pages = {k: (layout2(*loaded[k], fitsL[k], fitsR[k], width) if cols[k] else layout(*loaded[k]))
                 for k in loaded}
        if a.show is not None:
            L = pages[f'{a.show:04d}']
            print(json.dumps({k: v for k, v in L.items() if k != 'body'}, ensure_ascii=False, indent=1)[:1500])
            for b in L.get('body', []):
                print(('¶ ' if b['indent'] else '  ') + b['t'])
            return
        (d / 'pages.json').write_text(json.dumps(pages, ensure_ascii=False) + '\n', encoding='utf-8')
        k2 = [v for v in pages.values() if v['kind'] == 'text']
        print(f'第 {a.part} 部：{len(pages)} 叶，正文页 {len(k2)}（双栏 {sum(1 for v in k2 if v.get("cols") == 2)}），'
              f'有页眉 {sum(1 for v in k2 if v["head"])}，有页码 {sum(1 for v in k2 if v["pageno"])}', file=sys.stderr)
        return
    fits = {k: edge_fits(v[2], v[0]) for k, v in loaded.items()}
    width = part_width(fits)
    print(f'第 {a.part} 部全部栏宽 {width:.0f}px（按 {sum(1 for f in fits.values() if f)} 页拟合）', file=sys.stderr)
    if a.show is not None:
        k = f'{a.show:04d}'
        L = layout(*loaded[k], fits=fits[k], width=width)
        print(json.dumps({k: v for k, v in L.items() if k != 'body'}, ensure_ascii=False, indent=1))
        for b in L.get('body', []):
            print(('¶ ' if b['indent'] else '  ') + b['t'])
        return
    pages = {k: layout(*v, fits=fits[k], width=width) for k, v in loaded.items()}
    (d / 'pages.json').write_text(json.dumps(pages, ensure_ascii=False) + '\n', encoding='utf-8')
    k = [v for v in pages.values() if v['kind'] == 'text']
    print(f'第 {a.part} 部：{len(pages)} 叶，正文页 {len(k)}，有页眉 {sum(1 for v in k if v["head"])}，'
          f'有页码 {sum(1 for v in k if v["pageno"])}，有接字 {sum(1 for v in k if v["catch"])}，'
          f'旁注 {sum(len(v["margin"]) for v in k)} 行', file=sys.stderr)


if __name__ == '__main__':
    main()
