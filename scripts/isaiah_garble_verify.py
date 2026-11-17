#!/usr/bin/env python3
"""给 isaiah_garble_detector 的候选做**本地二次确认**：裁原图那一个词，三台引擎对读。

检测器只看文字，判不了「fit / tab / inn / into」这种恰好是英文词的乱码，也分不清
没变音的德文和希伯来残渣。这里沿用 isaiah_hebrew_ocr.py 的证据链：

  已发布正文里的候选（带前后各两个词）
    → 在 IA 的 ABBYY XML 同一扫描页里按前后词找到那个词的外接框
    → PDF 按 600dpi 裁出来
    → tesseract eng / heb / grc 各读一遍，取置信度
    → heb 或 grc 明显高于 eng 的，判为「外文活字被读成拉丁」，附上读数与裁图路径

只出清单，不改正文；读数只是提示，落盘前逐条看图（[[feedback_image_proof_before_apply]]）。

用法：
    python3 scripts/isaiah_garble_detector.py --broad > $S/cand.tsv
    python3 scripts/isaiah_garble_verify.py $S/cand.tsv $S/verify   # 出 $S/verify/verified.tsv 与裁图
"""
import gzip
import pickle
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander_raw/isaiah/src'
NS = '{http://www.abbyy.com/FineReader_xml/FineReader6-schema-v1.xml}'
XML = {'v1': SRC / 'v1.xml', 'v2': SRC / 'v2.xml'}
PDF = {'v1': Path.home() / 'Documents/论文/alexander/propheciesisaiah01alexuoft.pdf',
       'v2': Path.home() / 'Documents/论文/alexander/propheciesisaiah02alexuoft.pdf'}
OFFSET = {'v1': 78, 'v2': 46}          # 书页 + OFFSET = 扫描页（PDF 页序号，从 1 起）
PAD, DPI = 8, 600


def build_index(vol, cache):
    """扫描页 → [行[(词, 框)]]，外加页面像素尺寸。XML 四五百兆，只解析一次存 pickle。"""
    if cache.exists():
        return pickle.load(open(cache, 'rb'))
    idx, n = {}, 0
    for _, el in ET.iterparse(XML[vol], events=('end',)):
        if el.tag != NS + 'page':
            continue
        n += 1
        lines = []
        for line in el.iter(NS + 'line'):
            toks, cur = [], []
            for c in line.iter(NS + 'charParams'):
                ch = c.text or ''
                if ch.strip():
                    cur.append((ch, int(c.get('l')), int(c.get('t')), int(c.get('r')), int(c.get('b'))))
                elif cur:
                    toks.append(cur)
                    cur = []
            if cur:
                toks.append(cur)
            lines.append([(''.join(x[0] for x in g), (min(x[1] for x in g), min(x[2] for x in g),
                                                       max(x[3] for x in g), max(x[4] for x in g)))
                          for g in toks])
        idx[n] = (int(el.get('width')), int(el.get('height')), lines)
        el.clear()
    pickle.dump(idx, open(cache, 'wb'))
    return idx


def norm(w):
    return re.sub(r'[^0-9a-z]', '', w.lower())


def locate(lines, prev, tok, nxt):
    """在扫描页的词序列里找「前词 候选 后词」最像的位置 → 框。前后词各占大头，候选本身是乱码只算一点。"""
    flat = [t for ln in lines for t in ln]
    best, bi = 0.0, None
    for i in range(1, len(flat) - 1):
        s = (SequenceMatcher(None, norm(flat[i - 1][0]), norm(prev)).ratio() * 2
             + SequenceMatcher(None, norm(flat[i + 1][0]), norm(nxt)).ratio() * 2
             + SequenceMatcher(None, norm(flat[i][0]), norm(tok)).ratio())
        if s > best:
            best, bi = s, i
    if bi is None or best < 3.0:
        return None, best
    return (flat[bi], flat[bi - 1], flat[bi + 1]), best


def ocr(png, lang):
    r = subprocess.run(['tesseract', png, 'stdout', '-l', lang, '--psm', '7', 'tsv'],
                       capture_output=True, text=True)
    words, confs = [], []
    for line in r.stdout.splitlines()[1:]:
        f = line.split('\t')
        if len(f) >= 12 and f[11].strip():
            try:
                c = float(f[10])
            except ValueError:
                continue
            if c >= 0:
                words.append(f[11])
                confs.append(c)
    return ' '.join(words), (sum(confs) / len(confs) if confs else 0.0)


def main(cand_path, out_dir):
    out_dir = Path(out_dir)
    (out_dir / 'crops').mkdir(parents=True, exist_ok=True)
    idx = {v: build_index(v, out_dir / f'xml_{v}.pkl') for v in ('v1', 'v2')}
    docs = {v: fitz.open(PDF[v]) for v in ('v1', 'v2')}
    jobs = []
    for n, line in enumerate(open(cand_path, encoding='utf-8')):
        if line.startswith('#'):
            continue
        ch, page, ln, tok, kind, prev, nxt, ctx = line.rstrip('\n').split('\t')
        if not page.isdigit():
            continue
        vol = 'v1' if int(ch) <= 39 else 'v2'
        scan = int(page) + OFFSET[vol]
        # 页码标记标的是段落起点所在页；词可能落在后一两页，三页都试
        hit = None
        for sp in (scan, scan + 1, scan + 2, scan - 1):
            if sp not in idx[vol]:
                continue
            w, h, lines = idx[vol][sp]
            t, score = locate(lines, prev, tok, nxt)
            if t and (hit is None or score > hit[0]):
                hit = (score, sp, w, h, t)
        if not hit:
            continue
        score, sp, w, h, ((xtxt, (l, t, r, b)), pv, nx) = hit
        pg = docs[vol][sp - 1]
        sx, sy = pg.rect.width / w, pg.rect.height / h
        png = out_dir / 'crops' / f'{n:05d}_{ch}_{page}.png'
        pg.get_pixmap(dpi=DPI, clip=fitz.Rect((l - PAD) * sx, (t - PAD) * sy, (r + PAD) * sx,
                                              (b + PAD) * sy)).save(png)
        # 看图用的带上下文窄条：同一行上的前后词一起框进来
        cl, cr = l, r
        for _, (bl, bt, br, bb) in (pv, nx):
            if bt < b and bb > t:
                cl, cr = min(cl, bl), max(cr, br)
        cpng = out_dir / 'crops' / f'{n:05d}_{ch}_{page}_ctx.png'
        pg.get_pixmap(dpi=250, clip=fitz.Rect((cl - 30) * sx, (t - 12) * sy, (cr + 30) * sx,
                                              (b + 12) * sy)).save(cpng)
        jobs.append(dict(n=n, ch=ch, page=page, sp=sp, tok=tok, kind=kind, ctx=ctx, xml=xtxt,
                         png=str(png), cpng=str(cpng), score=round(score, 2)))

    def judge(j):
        for lang in ('eng', 'heb', 'grc'):
            j[lang] = ocr(j['png'], lang)
        return j

    with ThreadPoolExecutor(8) as pool:
        res = list(pool.map(judge, jobs))
    with open(out_dir / 'verified.tsv', 'w', encoding='utf-8') as f:
        f.write('verdict\tch\tpage\ttok\tkind\teng\theb\tgrc\txml\tpng\tctx\n')
        for j in res:
            e, hb, g = j['eng'][1], j['heb'][1], j['grc'][1]
            same = norm(j['eng'][0]) == norm(j['tok']) and e >= 50
            if same:
                v = 'latin'          # 英文模型把原词原样读出来了：印的就是拉丁字母
            elif hb >= 70 and hb > e + 15:
                v = 'HEB'
            elif g >= 70 and g > e + 15:
                v = 'GRC'
            elif e < 60:
                v = 'unclear'
            else:
                v = 'latin'
            f.write('\t'.join([v, j['ch'], j['page'], j['tok'], j['kind'],
                               f"{j['eng'][0]}|{e:.0f}", f"{j['heb'][0]}|{hb:.0f}", f"{j['grc'][0]}|{g:.0f}",
                               j['xml'], j['cpng'], j['ctx']]) + '\n')
    import collections
    print(collections.Counter(l.split('\t')[0] for l in open(out_dir / 'verified.tsv')), file=sys.stderr)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
