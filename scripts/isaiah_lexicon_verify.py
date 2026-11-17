#!/usr/bin/env python3
"""isaiah_lexicon_detector 候选的裁图复核：用**该语言自己的模型**读印面。

isaiah_garble_verify 用英文模型复读，英文模型把拉丁错字照样读成同一个错字，于是一律
判 latin 放过（第 38 轮第 34 章 perpendiculuni / fovei / verrath 就是这么漏的）。
这里换成：
  拉丁类候选 → tesseract lat（德文 deu、法文 fra、意文 ita），模型自带该语言词典，
              印的是 perpendiculum 就倾向读出 perpendiculum；
  希伯来候选 → tesseract heb，比读数离「正文的词」近还是离「附近经文那个差一个字母的词」近。

判定（只出清单，不改正文；落盘前逐条看图）：
  拉丁类：读数（去标点、小写）== 正文 → asis（原书即如此），剔掉；否则 CHECK，附读数。
  希伯来：读数辅音与建议词的相似度 > 与正文词的相似度 → CHECK；否则 asis。
  定位不到 → nofind（不上图，单列）。

用法：
    python3 scripts/isaiah_lexicon_detector.py > $S/lex.tsv
    python3 scripts/isaiah_lexicon_verify.py $S/lex.tsv $S/lexv        # → $S/lexv/verified.tsv + 裁图
    python3 scripts/isaiah_garble_sheets.py $S/lexv                    # CHECK 条拼图（sheets 认 CHECK）
"""
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from isaiah_garble_verify import DPI, OFFSET, PAD, PDF, build_index, locate, ocr   # noqa: E402

LANG = {'lat': 'lat', 'deu': 'deu', 'fra': 'fra', 'ita': 'ita'}


def letters(s):
    return re.sub(r'[^a-zà-ÿß]', '', s.lower())


def heb(s):
    return re.sub(r'[^א-ת]', '', s)


def main(cand_path, out_dir):
    out_dir = Path(out_dir)
    (out_dir / 'crops').mkdir(parents=True, exist_ok=True)
    cache = Path(out_dir).parent
    idx = {v: build_index(v, cache / f'xml_{v}.pkl') for v in ('v1', 'v2')}
    docs = {v: fitz.open(PDF[v]) for v in ('v1', 'v2')}
    jobs, nofind = [], []
    for n, line in enumerate(open(cand_path, encoding='utf-8')):
        if line.startswith('#'):
            continue
        ch, page, ln, tok, kind, prev, nxt, ctx = line.rstrip('\n').split('\t')
        if not page.isdigit():
            nofind.append((ch, page, tok, kind, ctx))
            continue
        vol = 'v1' if int(ch) <= 39 else 'v2'
        scan = int(page) + OFFSET[vol]
        hit = None
        for sp in (scan, scan + 1, scan + 2, scan + 3, scan - 1):
            if sp not in idx[vol]:
                continue
            w, h, lines = idx[vol][sp]
            t, score = locate(lines, prev, tok, nxt)
            if t and (hit is None or score > hit[0]):
                hit = (score, sp, w, h, t)
        if not hit:
            nofind.append((ch, page, tok, kind, ctx))
            continue
        score, sp, w, h, ((xtxt, (l, t, r, b)), pv, nx) = hit
        pg = docs[vol][sp - 1]
        sx, sy = pg.rect.width / w, pg.rect.height / h
        png = out_dir / 'crops' / f'{n:05d}_{ch}_{page}.png'
        pg.get_pixmap(dpi=DPI, clip=fitz.Rect((l - PAD) * sx, (t - PAD) * sy, (r + PAD) * sx,
                                              (b + PAD) * sy)).save(png)
        cl, cr = l, r
        for _, (bl, bt, br, bb) in (pv, nx):
            if bt < b and bb > t:
                cl, cr = min(cl, bl), max(cr, br)
        cpng = out_dir / 'crops' / f'{n:05d}_{ch}_{page}_ctx.png'
        pg.get_pixmap(dpi=250, clip=fitz.Rect((cl - 30) * sx, (t - 12) * sy, (cr + 30) * sx,
                                              (b + 12) * sy)).save(cpng)
        jobs.append(dict(ch=ch, page=page, tok=tok, kind=kind, ctx=ctx, xml=xtxt, png=str(png),
                         cpng=str(cpng)))

    def judge(j):
        k = j['kind']
        if k.startswith('heb'):
            j['read'], j['conf'] = ocr(j['png'], 'heb')
            sugg = k.split(':', 1)[1].split('/') if ':' in k else []
            rd, tk = heb(j['read']), heb(j['tok'])
            s_tok = SequenceMatcher(None, rd, tk).ratio()
            s_sug = max((SequenceMatcher(None, rd, heb(s)).ratio() for s in sugg), default=0)
            # heb 模型读小裁图基本读不出（回测 עפו 读成「7」），读数只作参考，希伯来条目一律上图
            j['verdict'] = 'CHECK'
            j['hint'] = 'sug' if s_sug > s_tok else ''
        else:
            lang = LANG.get(k.split('-')[0], 'lat')
            j['read'], j['conf'] = ocr(j['png'], lang)
            j['verdict'] = 'asis' if letters(j['read']) == letters(j['tok']) else 'CHECK'
        return j

    with ThreadPoolExecutor(8) as pool:
        res = list(pool.map(judge, jobs))
    with open(out_dir / 'verified.tsv', 'w', encoding='utf-8') as f:
        # 列与 isaiah_garble_verify 对齐（sheets 读 0 判定、1 章、2 页、3 词、9 裁图、10 上下文）
        f.write('verdict\tch\tpage\ttok\tkind\tread\t-\t-\txml\tpng\tctx\n')
        for j in res:
            f.write('\t'.join([j['verdict'], j['ch'], j['page'], j['tok'], j['kind'],
                               f"{j['read']}|{j['conf']:.0f}", '', '', j['xml'], j['cpng'], j['ctx']]) + '\n')
    with open(out_dir / 'nofind.tsv', 'w', encoding='utf-8') as f:
        for r in nofind:
            f.write('\t'.join(r) + '\n')
    import collections
    c = collections.Counter((j['verdict'], j['kind'][:3]) for j in res)
    print(dict(c), 'nofind', len(nofind), file=sys.stderr)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
