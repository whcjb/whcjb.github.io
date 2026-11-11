#!/usr/bin/env python3
"""福特《路加福音讲义》希腊／希伯来文：看图独立转录（第二读），与整页转录（第一读）对照，出待核清单。

第④层评估过：tess grc 读带重音希腊活字全错，不落；整页转录里的希腊文是模型单读，且常带 [?]。
按规矩希腊引文须看图、且单证人读法要用户同意。这里：
  · 每页（整页转录里有希腊/希伯来字母、或脚注带 [?] 的页）裁图——正文有希腊文的送整页，只脚注有的裁注区——
    **不给任何提示**，让模型把页上每段希腊/希伯来文照印面转录，连同紧挨前后的一个词作锚；
  · 锚在我们文本（该页所属各讲正文＋注区）里找，夹在两锚之间的就是我们的残串；
  · 与整页转录同位的读法比：去重音后一致＝两读一致（推荐），否则只列出；
  · 全部写 greek_pending.tsv 交用户核；**本脚本不落盘**，用户同意的条目另抄入 greek_fixes.tsv 才进链条。

    python3 scripts/foote_greek_read.py --collect
    python3 scripts/foote_greek_read.py --run --sample 3 | --run --all
    python3 scripts/foote_greek_read.py --report       # → foote_raw/luke/greek_pending.tsv
    python3 scripts/foote_greek_read.py --apply        # greek_fixes.tsv（用户同意过的）落盘，链条最末
"""
import argparse
import base64
import csv
import io
import json
import random
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import fitz
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_image_check as I  # noqa: E402
import foote_notes_check as N  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402

RAW = A.RAW
WORK = RAW / 'imgcheck'
CAND = WORK / 'greek_pages.json'
ANS = WORK / 'greek_answers'
PENDING = RAW / 'greek_pending.tsv'
FIXES = RAW / 'greek_fixes.tsv'
COST = A.ROOT / 'logs' / 'foote_greek_read_cost.tsv'
GH = re.compile(r'[Ͱ-Ͽἀ-῿֐-׿]')

SYSTEM = (
    'You transcribe Greek and Hebrew from images of a printed 19th-century English book. '
    'Find EVERY passage printed in Greek or Hebrew type in the image (single words included). For each, output one line:\n'
    '#k: <the word printed immediately before it> ⟦<the passage exactly as printed>⟧ <the word printed immediately after it>\n'
    'Rules: transcribe in Unicode exactly as printed, letter for letter — keep the breathings, accents, iota subscripts, '
    'final sigma and punctuation that are printed; do NOT add accents that are not printed, do NOT correct or normalise '
    'the text, do NOT complete it from memory of the source. Where a letter cannot be made out write [?]. '
    'The before/after words are the neighbouring printed words (English, Latin, a reference mark like * † ‡, '
    'or a number) copied exactly; write ^ if the passage begins a line of a footnote with nothing before it, '
    'and $ if nothing follows. If there is no Greek or Hebrew at all, output: NONE'
)


def collect():
    pages = []
    for vol in (1, 2, 3):
        pn = V.leaf_pages(vol)
        for f in sorted((V.VLM / f'v{vol}').glob('*.txt')):
            leaf = int(f.stem)
            t = f.read_text(encoding='utf-8')
            body, _, notes = t.partition('\n[FN:')
            gb, gn = bool(GH.search(body)), bool(GH.search(notes))
            qn = '[?]' in notes
            if not (gb or gn or qn):
                continue
            vn = N.vlm_notes(vol, leaf) or []
            box = None if gb else N.box_for(vol, leaf, vn)
            pages.append({'vol': vol, 'leaf': leaf, 'page': pn.get(leaf, ''), 'full': gb or box is None,
                          'box': box, 'vlm_greek': [m.group(0) for m in re.finditer(
                              r'[Ͱ-Ͽἀ-῿֐-׿][^\n¦]*?(?=[A-Za-z*"“]{2}|$|\n)', t)]})
    WORK.mkdir(parents=True, exist_ok=True)
    CAND.write_text(json.dumps(pages, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'页 {len(pages)}（整页 {sum(p["full"] for p in pages)}）→ {CAND}', file=sys.stderr)


def image(p):
    doc = fitz.open(RAW / 'pdf' / I.PDF[p['vol']])
    im = Image.open(io.BytesIO(doc.extract_image(doc[p['leaf']].get_images(full=True)[0][0])['image'])).convert('L')
    if not p['full']:
        x0, y0, x1, y1 = p['box']
        im = im.crop((0, max(0, y0 - 40), im.width, min(im.height, max(y1 + 40, int(im.height * 0.96)))))
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return buf.getvalue()


def ask(p):
    content = [{'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                            'data': base64.b64encode(image(p)).decode()}},
               {'type': 'text', 'text': 'Transcribe every Greek or Hebrew passage in this image as instructed.'}]
    msg = {'type': 'user', 'message': {'role': 'user', 'content': content}}
    cmd = ['claude', '-p', '--safe-mode', '--strict-mcp-config', '--disallowedTools', '*',
           '--input-format', 'stream-json', '--output-format', 'stream-json', '--verbose', '--system-prompt', SYSTEM]
    r = subprocess.run(cmd, input=json.dumps(msg) + '\n', capture_output=True, text=True, timeout=900)
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


def run(sample, all_):
    pages = json.loads(CAND.read_text(encoding='utf-8'))
    todo = [p for p in pages if not (ANS / f"v{p['vol']}" / f"{p['leaf']:04d}.json").exists()]
    if not all_:
        random.seed(20261111)
        todo = random.sample(todo, min(sample or 3, len(todo)))
    total, fails = 0.0, 0
    with open(COST, 'a', encoding='utf-8') as fh:
        for n, p in enumerate(todo, 1):
            try:
                res, cost = ask(p)
            except Exception as e:                     # noqa: BLE001
                fails += 1
                print(f"v{p['vol']} {p['leaf']:4d} 失败 {e}", file=sys.stderr, flush=True)
                if 'limit' in str(e).lower():
                    print('⛔ 额度用尽，中止', file=sys.stderr, flush=True)
                    sys.exit(42)
                if fails >= 5:
                    print('⛔ 连续失败过多，中止', file=sys.stderr, flush=True)
                    sys.exit(3)
                continue
            fails = 0
            total += cost
            d = ANS / f"v{p['vol']}"
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{p['leaf']:04d}.json").write_text(json.dumps({'raw': res, 'page': p}, ensure_ascii=False),
                                                     encoding='utf-8')
            fh.write(f"{p['vol']}\t{p['leaf']}\t{cost:.4f}\n")
            fh.flush()
            print(f"v{p['vol']} {p['leaf']:4d}  ${cost:.4f}  累计 ${total:.2f}  ({n}/{len(todo)})", file=sys.stderr, flush=True)


def bare(t):
    t = unicodedata.normalize('NFD', t)
    t = ''.join(c for c in t if not unicodedata.combining(c)).replace('ς', 'σ').lower()
    return re.sub(r'[^Ͱ-Ͽ֐-׿]', '', t)


MARKS = '♦•*†‡§‖¶+'


def regions(vol, page):
    """该页在我们文本里的区域：[(讲, 起, 止, 'note'|'body')]——注区里 p.页 的各条、正文里 PAGE 页 标记起的各段。"""
    out = []
    for lec in V.LECS[vol]:
        t = (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8')
        for m in re.finditer(r'<!-- NOTE p\.' + re.escape(page) + r' --> (.*)', t):
            out.append((lec, m.start(1), m.end(1), 'note'))
        for m in re.finditer(r'<!-- PAGE ' + re.escape(page) + r' -->\n(.*)', t):
            out.append((lec, m.start(1), m.end(1), 'body'))
    return out


def garbled(mid):
    """希腊活字读花的样子：须带 OCR 残符（`^ « » < > \\ / | %`、字母夹数字），且英文词不过四成；拉丁文引句不算。"""
    if GH.search(mid):
        return True
    if not re.search(r'[\^«»<>%\\/|]|\d[A-Za-z]|[A-Za-z]\d|[A-Za-z][(][A-Za-z]', mid):
        return False
    ws = re.findall(r"[A-Za-z]{2,}", mid)
    return not ws or sum(1 for w in ws if not A._isword(w)) / len(ws) >= 0.6


def locate(vol, page, lw, gk, rw):
    """两锚之间、长度与希腊文相当、多半是残字的一段。锚是注号/行首/行尾时按条首、注号位、条尾算。返回 [(讲, 起, 止)]。"""
    la = re.sub(r'[^A-Za-z0-9]', '', lw)
    ra = re.sub(r'[^A-Za-z0-9]', '', rw)
    n = len(gk)
    hits = []
    for lec, s0, e0, kind in regions(vol, page):
        t = (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8')
        seg = t[s0:e0]
        if la:
            starts = [m.end() for m in re.finditer(re.escape(la), seg)]
        else:   # 注号或行首：条首、以及各注号位之后
            starts = [0] + [m.end() for m in re.finditer(r'(?:^|\s)[' + re.escape(MARKS) + r'tf]\*?\s', seg)]
        for st in starts:
            if ra:
                ends = [m.start() for m in re.finditer(re.escape(ra), seg[st:st + 3 * n + 40])]
            else:
                ends = [len(seg[st:st + 3 * n + 40].rstrip())]
            for en in ends:
                mid = seg[st:st + en]
                core = mid.strip(' ,.;:"\'*')
                if not (0.4 * n <= len(core) <= 1.6 * n + 8) or '<!--' in mid:
                    continue
                if garbled(core):
                    hits.append((lec, s0 + st, s0 + st + en))
                    break
    return hits


def report():
    rows, stat = [], Counter()
    for f in sorted(ANS.glob('v*/*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        p = d['page']
        vg = ' '.join(p['vlm_greek'])
        for m in re.finditer(r'^#\d+:\s*(.*?)\s*⟦(.*?)⟧\s*(.*?)\s*$', d['raw'], re.M):
            lw, gk, rw = m.group(1), m.group(2).strip(), m.group(3)
            if not GH.search(gk):
                continue
            agree = bool(bare(gk)) and bare(gk) in bare(vg)
            hits = locate(p['vol'], p['page'], lw if lw not in ('^',) else '', gk, rw if rw not in ('$',) else '')
            uniq = len(hits) == 1
            stat['两读一致' if agree else '两读不一'] += 1
            stat['定位唯一' if uniq else '定位不到' if not hits else '定位多处'] += 1
            lec, s, e = hits[0] if uniq else ('', 0, 0)
            ours = (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8')[s:e] if uniq else ''
            rows.append(('推荐' if agree and uniq else '待看' if uniq else '定位不到' if not hits else '多处',
                         f'{lec:03d}' if uniq else '', p['vol'], p['leaf'], p['page'], lw, ours, gk, rw,
                         '一致' if agree else '不一', s, e))
    with open(PENDING, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['建议', 'lecture', 'vol', 'leaf', 'page', '前锚', '我们现在', '看图读(第二读)', '后锚',
                    '与整页转录(去重音)', 's', 'e'])
        w.writerows(rows)
    print(dict(stat), f'→ {PENDING}（{len(rows)} 条）', file=sys.stderr)


def proposal(ours, gk):
    """我们那段 → 改作：两头标点空白留着，中间残串（连同包着它的斜体星号）换成希腊文；注号留在末尾。
    星号（非转义）个数为奇的不收（会拆散斜体）。返回 None 表示不收。"""
    if len(re.findall(r'(?<!\\)\*', ours)) % 2:
        return None
    lead = re.match(r'^[\s,.;:()"“”\'—-]*', ours).group(0)
    trail = re.search(r'[\s"“”\'()—-]*$', ours[len(lead):]).group(0)
    if lead.strip() and lead[-1] not in ' ("“\'':
        lead += ' '
    return lead + gk + A.FN_MARK * ours.count(A.FN_MARK) + trail


def propose():
    """greek_pending.tsv 的「推荐」→ greek_proposed.tsv（用户同意后整份或逐条抄进 greek_fixes.tsv）。"""
    rows = list(csv.reader(open(PENDING, encoding='utf-8'), delimiter='\t'))[1:]
    out, skip = [], 0
    for r in rows:
        if r[0] != '推荐' or GH.search(r[6]):
            continue
        new = proposal(r[6], r[7])
        if new is None:
            skip += 1
            continue
        out.append((r[1], r[6], new))
    path = RAW / 'greek_proposed.tsv'
    path.write_text('# lecture\t原串\t改作 —— foote_greek_read.py 生成：看图第二读与整页转录去重音一致、定位唯一；待用户同意\n'
                    + ''.join('\t'.join(x.replace('\n', '\\n') for x in r) + '\n' for r in out), encoding='utf-8')
    print(f'提议 {len(out)} 条（星号奇数不收 {skip}）→ {path}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--collect', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    if a.collect:
        collect()
    elif a.run:
        run(a.sample, a.all)
    elif a.report:
        report()
        propose()
    elif a.apply and FIXES.exists():
        I.apply_multiline(FIXES)


if __name__ == '__main__':
    main()
