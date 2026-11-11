#!/usr/bin/env python3
"""加尔文《撒母耳记上讲章》拉丁文本：第 ③ 层·看图判读（两份 OCR + 词表都判不了的 residue）。

用户 2026-11-11 定：**一页图只看一次**——这一页上所有待判词一起判，不许一处看一次、也不许同一页再送第二遍。

做法：
  --collect  repair_log.tsv 里 residue 的词 → 在 PDF 文字层的逐词框里定位（同栏、同词形、第 n 次出现）→
             candidates.json（按页）。行末断词（文字层是 `impie-`，判读时已并成整词）连同下一行的词头一起框上。
  --run      每页一次调用：把待判词所在各行按带状裁成若干条（PDF 内嵌原图，原生分辨率不放大），每个待判词画红框、
             标号；问题里给出我们目前的读法，答「#n: 印面上的词」或「#n: ?」。答案存 imgcheck/answers/。
             串行一路；额度用尽退出码 42，已答的页跳过。
  --rules    答案 → image_fixes.tsv（键：卷、页、栏、原词、该栏第几处同形 residue）。守卫：答 ? 不落；
             答案须是字母词，且与我们的读法或证人读法相近（相似度 ≥ 0.5），否则记 held 待人看。
  落盘：repair_calvin_1sam.Repairer 在判出 residue 时查 image_fixes.tsv，命中即用印面读法（action=image）。
"""
import argparse
import base64
import collections
import csv
import difflib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_calvin_1sam import SINGLE_COL, VOLS, gutter_chars  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'calvin_sermons_raw' / '1samuel'
WORK = RAW / 'imgcheck'
CAND = WORK / 'candidates.json'
ANS = WORK / 'answers'
RULES = RAW / 'image_fixes.tsv'
WHOLE = RAW / 'image_whole_fixes.tsv'
CONFIRMED = RAW / 'image_confirmed.tsv'   # 看图确认印面即如此（含原书印错），照录、不再算待判     # 整串替换（希腊词等），extract 在判读前落到行文字上
COST = ROOT / 'logs' / 'calvin_1sam_image_check_cost.tsv'
PDF = {v: p for v, p, _, _ in VOLS}
CLEAN = lambda w: re.sub(r"[^A-Za-zÀ-ÿ0-9']", '', w)

SYSTEM = (
    'You are proof-reading a 19th-century printed Latin book (Calvin, Homiliae in I. librum Samuelis, Calvini Opera '
    '1885–86) against images of its printed lines. Each image is a strip of the scan at native resolution; some words '
    'in it are framed by thin red boxes labelled with a number. A word broken at the end of a line with a hyphen has '
    'both of its parts framed with the same number. For each number, read what is actually printed inside the box(es) '
    'and write that one word exactly as printed: Latin spelling as it stands (i for j, u/v as printed, ae not æ), '
    'keep capitals, keep a diaeresis if printed (Israël), no accents unless printed, no punctuation. For a hyphen-broken '
    'word write the whole word joined, without the hyphen. Do not correct the print: if the printer misspelt a word, '
    'write the misprint. The OCR reading given with each number is often wrong; do not trust it. If the print inside a '
    'box cannot be made out, answer ?. Some boxes hold a Greek word (the OCR shows it as garbage such as l&tlo&Qt]oxtlaiç): '
    'write it in Greek letters with accents and breathings exactly as printed. A box may also hold two words printed '
    'apart that the OCR ran together; then write them with a space. '
    'Answer each number on its own line exactly as  #n: word   and output nothing else.'
)


def page_words(vol, pno):
    d = fitz.open(PDF[vol])
    pg = d[pno - 1]
    lines = [l for b in pg.get_text('rawdict')['blocks'] for l in b.get('lines', [])]
    split = pg.rect.width + 1 if (vol, pno) in SINGLE_COL else gutter_chars(lines, pg.rect.width)
    out = []
    for x0, y0, x1, y1, w, b, ln, wn in pg.get_text('words'):
        side = 1 if (x0 + x1) / 2 < split else 2
        out.append(dict(box=(x0, y0, x1, y1), w=w, side=side, key=(b, ln), y=y0))
    out.sort(key=lambda r: (r['side'], round(r['y'] / 3), r['box'][0]))
    return out, pg.rect.width


def collect():
    rows = [r for r in csv.DictReader(open(RAW / 'repair_log.tsv', encoding='utf-8'), delimiter='\t')
            if 'residue' in r['action']]
    bypage = collections.OrderedDict()
    for r in rows:
        bypage.setdefault((r['vol'], int(r['page'])), []).append(r)
    pages, miss = [], 0
    for (vol, pno), rs in bypage.items():
        words, pw = page_words(vol, pno)
        seen = collections.Counter()
        qs = []
        for r in rs:
            col = int(r['col'])
            k = (col, r['primary'])
            n = seen[k]
            seen[k] += 1
            target = CLEAN(r['primary'])
            hits = []
            colw = [w for w in words if w['side'] == col]
            for i, w in enumerate(colw):
                cw = CLEAN(w['w'])
                if CLEAN(w['w'].rstrip('-¬')) == target or cw == target:
                    hits.append([w])
                elif w['w'].rstrip().endswith(('-', '¬')) and cw and target.startswith(CLEAN(w['w'].rstrip('-¬'))) \
                        and len(CLEAN(w['w'].rstrip('-¬'))) < len(target):
                    nxt = colw[i + 1] if i + 1 < len(colw) else None
                    rest = target[len(CLEAN(w['w'].rstrip('-¬'))):]
                    if nxt and CLEAN(nxt['w']).startswith(rest):
                        hits.append([w, nxt])
                    else:
                        hits.append([w])
            if n >= len(hits):
                # 文字层里整串读烂的（希腊词 `l&tlo&Qt]oxtlaiç`、词中夹符号 `exb-ibiturum,`）：判读时被拆成几截，
                # 按「整串」问一次，答案整串替换（whole）；同一串的几截只问一次
                cont = [w for w in colw if target and target in CLEAN(w['w']) and CLEAN(w['w']) != target
                        and re.search(r"[A-Za-zÀ-ÿ][^A-Za-zÀ-ÿ\s']+[A-Za-zÀ-ÿ]", w['w'])]   # 只配内部夹符号的脏串
                if cont:
                    w = cont[min(n - len(hits), len(cont) - 1)] if len(hits) <= n else cont[0]
                    if not any(q.get('raw') == w['w'] for q in qs):
                        qs.append(dict(kind='whole', col=col, raw=w['w'], ours=w['w'], witness='', boxes=[w['box']]))
                    continue
                miss += 1
                continue
            h = hits[n]
            qs.append(dict(col=col, primary=r['primary'], occ=n, ours=r['result'], witness=r['witness'],
                           boxes=[x['box'] for x in h]))
        if qs:
            pages.append(dict(vol=vol, page=pno, qs=qs))
    # 已问过的页不再改题（一页只看一次）：保留当时的题目
    for p in pages:
        f = ANS / f"{p['vol']}_{p['page']:03d}.json"
        if f.exists():
            p['qs'] = json.loads(f.read_text(encoding='utf-8'))['qs']
    WORK.mkdir(parents=True, exist_ok=True)
    CAND.write_text(json.dumps(pages, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'待判 {sum(len(p["qs"]) for p in pages)} 处 / {len(pages)} 页；文字层里定位不到 {miss} 处')


def strips(vol, pno, qs):
    """待判词所在行按带状裁条（每条高 ≤ 420px、宽为本栏），红框标号。返回 [png]。"""
    d = fitz.open(PDF[vol])
    pg = d[pno - 1]
    im = Image.open(io.BytesIO(d.extract_image(pg.get_images(full=True)[0][0])['image'])).convert('RGB')
    s = im.width / pg.rect.width
    lines = [l for b in pg.get_text('rawdict')['blocks'] for l in b.get('lines', [])]
    split = (pg.rect.width + 1 if (vol, pno) in SINGLE_COL else gutter_chars(lines, pg.rect.width)) * s
    draw = ImageDraw.Draw(im)
    spans = []                          # (col, y0, y1)
    for n, q in enumerate(qs, 1):
        for (x0, y0, x1, y1) in q['boxes']:
            X0, Y0, X1, Y1 = x0 * s - 3, y0 * s - 3, x1 * s + 3, y1 * s + 3
            draw.rectangle([X0, Y0, X1, Y1], outline=(220, 0, 0), width=2)
            draw.text((X0, Y0 - 13), str(n), fill=(220, 0, 0))
            spans.append((q['col'], Y0 - 16, Y1 + 6))
    out = []
    for col in (1, 2):
        ys = sorted((a, b) for c, a, b in spans if c == col)
        bands = []
        for a, b in ys:
            if bands and a <= bands[-1][1] + 40 and b - bands[-1][0] <= 420:
                bands[-1][1] = max(bands[-1][1], b)
            else:
                bands.append([a, b])
        x0, x1 = (0, split + 6) if col == 1 else (split - 6, im.width)
        if (vol, pno) in SINGLE_COL:
            x0, x1 = 0, im.width
        for a, b in bands:
            buf = io.BytesIO()
            im.crop((int(x0), int(max(0, a)), int(x1), int(min(im.height, b)))).save(buf, 'PNG')
            out.append(buf.getvalue())
    return out


def ask(vol, pno, qs):
    content = []
    for k, png in enumerate(strips(vol, pno, qs), 1):
        content.append({'type': 'text', 'text': f'Strip {k}:'})
        content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                                    'data': base64.b64encode(png).decode()}})
    content.append({'type': 'text', 'text': '\n'.join(f'#{n}: OCR read «{q["ours"]}»' for n, q in enumerate(qs, 1))})
    msg = {'type': 'user', 'message': {'role': 'user', 'content': content}}
    cmd = ['claude', '-p', '--safe-mode', '--strict-mcp-config', '--disallowedTools', '*',
           '--input-format', 'stream-json', '--output-format', 'stream-json', '--verbose', '--system-prompt', SYSTEM]
    r = subprocess.run(cmd, input=json.dumps(msg) + '\n', capture_output=True, text=True, timeout=1200)
    for line in r.stdout.splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get('type') == 'result':
            if o.get('is_error'):
                raise RuntimeError(str(o.get('result'))[:200])
            return str(o.get('result') or ''), float(o.get('total_cost_usd') or 0)
    raise RuntimeError('no result: ' + r.stderr[-200:])


def run(sample):
    pages = json.loads(CAND.read_text(encoding='utf-8'))
    todo = [p for p in pages if not (ANS / f"{p['vol']}_{p['page']:03d}.json").exists()]
    if sample:
        todo = todo[:sample]
    ANS.mkdir(parents=True, exist_ok=True)
    total, fails = 0.0, 0
    with open(COST, 'a', encoding='utf-8') as fh:
        for i, p in enumerate(todo, 1):
            try:
                res, cost = ask(p['vol'], p['page'], p['qs'])
            except Exception as e:                     # noqa: BLE001
                fails += 1
                print(f"{p['vol']} {p['page']} 失败 {e}", file=sys.stderr, flush=True)
                if 'limit' in str(e).lower():
                    print('⛔ 额度用尽，中止', file=sys.stderr, flush=True)
                    sys.exit(42)
                if fails >= 5:
                    sys.exit(3)
                continue
            fails = 0
            total += cost
            ans = {int(m.group(1)): m.group(2).strip() for m in re.finditer(r'^\s*#(\d+):\s*(.*?)\s*$', res, re.M)}
            (ANS / f"{p['vol']}_{p['page']:03d}.json").write_text(
                json.dumps({'raw': res, 'ans': ans, 'qs': p['qs']}, ensure_ascii=False), encoding='utf-8')
            fh.write(f"{p['vol']}\t{p['page']}\t{len(p['qs'])}\t{len(ans)}\t{cost:.4f}\n")
            fh.flush()
            print(f"{p['vol']} p{p['page']:3d} 问 {len(p['qs']):3d} 答 {len(ans):3d} ${cost:.4f} 累计 ${total:.2f} "
                  f"({i}/{len(todo)})", flush=True)


def sim(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def short(a, ours):
    """答案比我们的读法少了两成以上的字母：多半只读了框里的一截（momentiest→momenti、necesse.fuitillis→fuit illis）
    或框对错了词（Helcanae→Heli）。不落，挂起。"""
    la = len(re.sub(r'[^A-Za-zÀ-ÿ]', '', a))
    lo = len(re.sub(r'[^A-Za-zÀ-ÿ]', '', ours))
    return lo and la < 0.8 * lo


def long(a, ours):
    """答案比我们的读法长出四成以上：我们这处多半只是断词的半截（vasset→sublevasset、infen→infensissimi），
    整词替进去另半截还在，会重复。不落，挂起。粘连拆开（答案带空格、字母数相当）不算。"""
    la = len(re.sub(r'[^A-Za-zÀ-ÿ]', '', a))
    lo = len(re.sub(r'[^A-Za-zÀ-ÿ]', '', ours))
    return lo and la > 1.4 * lo


def rules():
    out, held, whole, conf, stat = [], [], [], [], collections.Counter()
    for f in sorted(ANS.glob('*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        vol, page = f.stem.split('_')
        for n, q in enumerate(d['qs'], 1):
            a = str(d['ans'].get(str(n), d['ans'].get(n, ''))).strip()
            a = a.strip('«»"\'.,;:')
            if q.get('kind') == 'whole':
                if not a or a == '?' or a == q['raw']:
                    continue
                greek = re.search(r'[\u0370-\u03ff\u1f00-\u1fff]', a)
                if not greek and (short(a, q['raw']) or long(a, q['raw'])):
                    held.append((vol, page, q, a, 'short/long'))
                    stat['held'] += 1
                    continue
                whole.append((vol, int(page), q['col'], q['raw'], a))
                stat['whole'] += 1
                continue
            if not a or a == '?':
                stat['unreadable'] += 1
                continue
            if not re.fullmatch(r"[A-Za-zëïÉ']+( [A-Za-zëïÉ']+){0,3}", a):        # 粘连的词印面是分开的（ei duae uxores）
                held.append((vol, page, q, a, 'not-a-word'))
                stat['held'] += 1
                continue
            if a == q['ours']:
                stat['confirmed'] += 1               # 印面就是这样（含原书印错），照录
                conf.append((vol, int(page), q['col'], q['primary'], q['occ']))
                continue
            if short(a, q['ours']) or long(a, q['ours']):
                held.append((vol, page, q, a, 'short/long'))
                stat['held'] += 1
                continue
            if max(sim(a, q['ours']), sim(a, q['witness'] or '')) < 0.5:
                held.append((vol, page, q, a, 'far'))
                stat['held'] += 1
                continue
            out.append((vol, int(page), q['col'], q['primary'], q['occ'], a))
            stat['fix'] += 1
    with open(RULES, 'w', encoding='utf-8') as fh:
        fh.write('vol\tpage\tcol\tprimary\tocc\tprinted\n')
        for r in out:
            fh.write('\t'.join(map(str, r)) + '\n')
    with open(CONFIRMED, 'w', encoding='utf-8') as fh:
        fh.write('vol\tpage\tcol\tprimary\tocc\n')
        for r in conf:
            fh.write('\t'.join(map(str, r)) + '\n')
    with open(WHOLE, 'w', encoding='utf-8') as fh:
        fh.write('vol\tpage\tcol\traw\tprinted\n')
        for r in whole:
            fh.write('\t'.join(map(str, r)) + '\n')
    with open(WORK / 'held.tsv', 'w', encoding='utf-8') as fh:
        fh.write('vol\tpage\tcol\tours\twitness\tanswer\twhy\n')
        for vol, page, q, a, why in held:
            fh.write(f"{vol}\t{page}\t{q['col']}\t{q['ours']}\t{q['witness']}\t{a}\t{why}\n")
    print(dict(stat))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--collect', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--rules', action='store_true')
    a = ap.parse_args()
    if a.collect:
        collect()
    if a.run:
        run(a.sample)
    if a.rules:
        rules()
