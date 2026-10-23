#!/usr/bin/env python3
"""莱尔马太：e-Sword 本与 1857 扫描件 OCR 有实词出入的地方，裁原书行图拼成对照图，逐处看图判读。

    python3 scripts/ryle_review.py            # 生成 ryle_raw/matthew/review/sheet_NN.png + review.tsv（判读表，verdict 待填）

候选（来自 collation_diffs.tsv 的 other 类）：
  rr  两边都是真词却不同（e-Sword 改词、引经改字、或 OCR 恰好错成另一个真词如 be/he）
  ins 1857 有、e-Sword 没有的真词
  del e-Sword 有、1857 没有的词
OCR 一边是非词（tlie、wiU）的不进候选：那是 OCR 错，e-Sword 对。
判读表已有 verdict 的行保留，重跑只补新行。verdict：es＝e-Sword 对；1857＝照原书改；文字写在 reading 栏。
"""
import csv
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ryle_common import GLOBAL_SPELLING

GS = {k.replace("'", ''): v for k, v in GLOBAL_SPELLING.items()}

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'ryle_raw' / 'matthew'
DIFF = RAW / 'collation_diffs.tsv'
JP2 = RAW / 'src' / 'ia_1857' / 'expositorythough01ryle_jp2'
OUTD = RAW / 'review'
TSV = RAW / 'review.tsv'
PER_SHEET = 10
MODAL = {'to', 'may', 'might', 'must', 'shall', 'will', 'would', 'can', 'cannot', 'could', 'should', 'not',
         'never', 'also', 'ever', 'always', 'all', 'only', 'then', 'now', 'cannot', 'shalt', 'wilt'}

EXTRA_WORDS = {'saviour', 'fulfil', 'fulfilment', 'fulness', 'marvellous', 'offence', 'defence', 'pretence',
               'traveller', 'shew', 'shews', 'shewed', 'labour', 'honour', 'neighbour', 'connexion',
               'unmistakeable', 'worshipped', 'travelling', 'sceptical', 'wilful', 'intrench', 'hath', 'doth',
               'unto', 'thee', 'thy', 'thou', 'ye', 'shalt', 'saith', 'cometh', 'goeth', 'hast', 'art', 'wilt',
               'didst', 'canst', 'spake', 'sepulchre', 'christ', 'jesus', 'god', 'lord'}


def words():
    """「真词」＝在莱尔正文（e-Sword 全书）或马太钦定本里出现过的词，再加原书拼写族。
    不用系统词典：它收了 lis、kome、mari、ho 这类生僻词，OCR 错字一撞就成「真词」。"""
    import json
    d = json.loads((RAW / 'esword_sections.json').read_text(encoding='utf-8'))
    text = ' '.join(p for s in d['sections'] for p in s['paras'] + s['notes'])
    usfm = (RAW / 'src' / 'kjv' / '70-MATeng-kjv2006.usfm').read_text(encoding='utf-8')
    usfm = re.sub(r'\\[a-z0-9]+\*?|\|strong="[^"]*"', ' ', usfm)
    vocab = {k(w) for w in (text + ' ' + usfm).split() if k(w)} | EXTRA_WORDS
    # 系统词典里 5 个字母以上的词也算：justness 这类原书用词在别处没出现，但 OCR 不会凭空拼出长词
    return vocab | {x.strip().lower() for x in open('/usr/share/dict/words') if len(x.strip()) >= 5}


def k(w):
    return re.sub(r'[^a-z]', '', w.lower())


def realwords(s, W):
    ws = [k(w) for w in s.split() if k(w)]
    return bool(ws) and all((w in W and len(w) > 1) or w in ('a', 'i', 'o') for w in ws)


def candidates():
    W = words()
    out = []
    for x in csv.DictReader(DIFF.open(encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
        if x['cat'] != 'other':
            continue
        e, o = x['esword'], x['ocr1857']
        if x['op'] == 'replace' and realwords(o, W) and realwords(e, W):
            if k(e) in GS and GS[k(e)].replace("'", '') == k(o):   # 整族回改的拼写，不必看图
                continue
            # be/he：前一词是情态动词或 to，只能是 be（OCR 把 b 认成 h）
            prev = x['context'].split('⟦')[0].split()[-1:] or ['']
            if k(e) == 'be' and k(o) == 'he' and k(prev[0]) in MODAL:
                continue
            c = 'rr'
        elif x['op'] == 'insert' and realwords(o, W):
            c = 'ins'
        elif x['op'] == 'delete' and realwords(e, W):
            c = 'del'
        else:
            continue
        out.append(dict(kind=c, **x))
    return out


_PAGE = {}


def crop(pb):
    pg, x0, y0, x1, y1 = map(int, pb.split())
    if pg not in _PAGE:
        _PAGE.clear()
        _PAGE[pg] = Image.open(JP2 / f'expositorythough01ryle_{pg:04d}.jp2').convert('L')
    im = _PAGE[pg]
    W, H = im.size
    top, bot = max(0, y0 - 75), min(H, y1 + 75)
    # 横向取整行：正文版心大约 x 100–1800
    return im.crop((max(0, min(x0 - 900, 90)), top, min(W, max(x1 + 900, 1820)), bot))


def main():
    OUTD.mkdir(exist_ok=True)
    old = {}
    if TSV.exists():
        for r in csv.DictReader(TSV.open(encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
            old[r['sec'] + '|' + r['context'] + '|' + r['esword'] + '|' + r['ocr1857']] = r
    cs = candidates()
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 30)
    except OSError:
        font = ImageFont.load_default()
    rows = []
    for n, c in enumerate(cs, 1):
        key = c['sec'] + '|' + c['context'] + '|' + c['esword'] + '|' + c['ocr1857']
        r = old.get(key, {})
        rows.append(dict(id=str(n), sec=c['sec'], kind=c['kind'], es_idx=c['es_idx'], esword=c['esword'],
                         ocr1857=c['ocr1857'], page_bbox=c['page_bbox'], context=c['context'],
                         verdict=r.get('verdict', ''), reading=r.get('reading', ''), note=r.get('note', '')))
    for s in range(0, len(rows), PER_SHEET):
        batch = rows[s:s + PER_SHEET]
        tiles = []
        for r in batch:
            im = crop(r['page_bbox'])
            im = im.resize((im.width * 2 // 3, im.height * 2 // 3))
            lab = Image.new('L', (im.width, 44), 255)
            ImageDraw.Draw(lab).text((6, 6), f"#{r['id']} {r['sec']} [{r['kind']}]  e-Sword: {r['esword']!r}   "
                                             f"OCR: {r['ocr1857']!r}", fill=0, font=font)
            tiles += [lab, im]
        Wd = max(t.width for t in tiles)
        sheet = Image.new('L', (Wd, sum(t.height for t in tiles) + 8 * len(tiles)), 255)
        y = 0
        for t in tiles:
            sheet.paste(t, (0, y))
            y += t.height + 8
        sheet.save(OUTD / f'sheet_{s // PER_SHEET + 1:02d}.png')
    with TSV.open('w', encoding='utf-8') as f:
        cols = ['id', 'sec', 'kind', 'es_idx', 'esword', 'ocr1857', 'page_bbox', 'context', 'verdict', 'reading',
                'note']
        f.write('\t'.join(cols) + '\n')
        for r in rows:
            f.write('\t'.join(r[c].replace('\t', ' ') for c in cols) + '\n')
    print(f'{len(rows)} 处候选，{(len(rows) + PER_SHEET - 1) // PER_SHEET} 张对照图 → {OUTD}')


if __name__ == '__main__':
    main()
