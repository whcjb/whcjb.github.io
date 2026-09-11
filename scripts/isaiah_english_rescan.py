#!/usr/bin/env python3
"""给剩下那批待判串**再找一个证人**：拿 tesseract 重扫同一块活字。

判读走到这一步，剩下的按证据分三档：证人还有话说 / 证人对不上（锚撞车）/
压根没证据。后两档一直被记成「只能翻影像」——但翻影像做的事，无非是用另一
双眼睛重认这几个字母。tesseract 就是另一双眼睛，而且它认的是**同一份 PDF
原图**，不是别家扫描件，不存在锚撞车的问题。

与九份 IA 证人的区别正在这里：那些证人是各自独立扫描、独立 OCR 的，所以
位置要靠前后文锚去对，锚一撞就给出风马牛不相及的读数（`Carchemish → some`）。
这里的裁图坐标直接来自 ABBYY XML 的 charParams，**位置是精确的**，读出来
是什么就是这个词。

用生成式模型做 OCR 是明令禁止的（会「改词意」），这里用的是 tesseract。

接受条件（三条都要满足）：
  · 读数与 ABBYY 那串不同，且置信度 ≥ 80
  · 读数是词典里的词——重扫也可能读崩，读崩的结果通常还是非词
  · 与原串足够像（相似度 ≥ 0.5）——差太远说明裁歪了或本来就不是拉丁活字

用法：
    python3 scripts/isaiah_english_rescan.py              # 扫，出 TSV
    python3 scripts/isaiah_english_rescan.py --apply      # 落回已发布正文
"""
import argparse
import csv
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_lexicon import build, is_word
from isaiah_hebrew_ocr import BODY, PDF, XML, NS, DPI, PAD, line_tokens, ocr

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / 'alexander/isaiah'
BACKLOG = ROOT / 'logs/alexander_isaiah_backlog.tsv'
OUT = ROOT / 'alexander_raw/isaiah/english_rescan.tsv'
LOG = ROOT / 'logs/alexander_isaiah_rescan_applied.tsv'

MIN_CONF = 80
MIN_SIM = 0.5


def pending():
    """待判的那三档 → {串}"""
    out = set()
    with open(BACKLOG, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
            if (r.get('bucket') or '').startswith('待判'):
                out.add(r['token'])
    return out


def judge(job):
    """**不设闸**，读到什么记什么。

    扫一遍要跑十几分钟，闸门却要反复调；把判断挪到落盘那一步，一份扫描
    结果就能试很多组阈值，不必为了改个数字重扫一遍。
    """
    png, garbage = job['png'], job['garbage']
    # psm 8 = 单个词，psm 7 = 单行；裁图跨度不定，两个都试取更自信的
    best = max((ocr(png, 'eng', psm) for psm in ('8', '7')), key=lambda x: x[1])
    Path(png).unlink(missing_ok=True)
    reading, conf = best[0].strip(' .,:;'), best[1]
    if not reading or reading == garbage:
        return None
    return (job['vol'], job['scan_page'], job['before'], garbage, job['after'],
            reading, round(conf))


def scan():
    want = pending()
    print(f'待判串 {len(want)} 个')
    rows = []
    for vol in ('v1', 'v2'):
        lo, hi = BODY[vol]
        doc = fitz.open(PDF[vol])
        idx = 0
        for _, el in ET.iterparse(XML[vol], events=('end',)):
            if el.tag != NS + 'page':
                continue
            idx += 1
            if not (lo <= idx <= hi):
                el.clear()
                continue
            pw, ph = int(el.get('width')), int(el.get('height'))
            page = doc[idx - 1]
            sx, sy = page.rect.width / pw, page.rect.height / ph
            jobs = []
            for line in el.iter(NS + 'line'):
                toks = line_tokens(line)
                for i, (txt, box) in enumerate(toks):
                    if txt.strip(".,;:!?()[]'\"") not in want:
                        continue
                    clip = fitz.Rect((box[0] - PAD) * sx, (box[1] - PAD) * sy,
                                     (box[2] + PAD) * sx, (box[3] + PAD) * sy)
                    if clip.width <= 0 or clip.height <= 0:
                        continue
                    with tempfile.NamedTemporaryFile(suffix='.png',
                                                     delete=False) as fh:
                        png = fh.name
                    page.get_pixmap(dpi=DPI, clip=clip).save(png)
                    clean = lambda x: re.sub(r'[\t\r\n]+', ' ', x).strip()
                    jobs.append(dict(
                        png=png, vol=vol, scan_page=idx, garbage=clean(txt),
                        before=clean(' '.join(t for t, _ in toks[max(0, i - 4):i])),
                        after=clean(' '.join(t for t, _ in toks[i + 1:i + 3]))))
            el.clear()
            if jobs:
                with ThreadPoolExecutor(8) as pool:
                    rows.extend(r for r in pool.map(judge, jobs) if r)
        doc.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('vol\tscan_page\tbefore\tgarbage\tafter\treading\tconf\n')
        for r in rows:
            f.write('\t'.join(str(x) for x in r) + '\n')
    print(f'重扫读出 {len(rows)} 条 → {OUT}')


def norm(text):
    out, idx, prev_space = [], [], True
    for i, ch in enumerate(text):
        if ch.isalnum():
            out.append(ch)
            idx.append(i)
            prev_space = False
        elif not prev_space:
            out.append(' ')
            idx.append(i)
            prev_space = True
    return ''.join(out), idx


def witness_readings():
    """判读日志里每个串对应的证人读数 → {串: {读数}}"""
    out = {}
    path = ROOT / 'logs/alexander_isaiah_adjudicate.tsv'
    if not path.exists():
        return out
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
            w = (r.get('witness') or '').strip().lower()
            if w:
                out.setdefault((r.get('ours') or '').strip(), set()).add(w)
    return out


def accept(r, lex, wit):
    """这条重扫读数收不收。两条并行的路，各有各的证据：

    一、**读数是词典里的词**。重扫也会读崩，但读崩的结果通常还是非词；
        读出来是个词，而且与原串还像（相似度 ≥0.5），基本就是原串读错了。
        这条要 ≥80 的置信度。

    二、**读数与 IA 证人给的一模一样**。这时是两个来源各自独立认出同一串
        字母——一个认的是本 PDF 原图，一个认的是别家扫描件——比词典那条
        路证据还硬，所以词典不认（拉丁文、德文、专名）也收，置信度放到 70。
    """
    reading, garbage, conf = r['reading'], r['garbage'], int(r['conf'])
    # 只差标点的不算改。重扫经常把词尾的逗号句点吞掉（`Bauer, → Bauer`），
    # 那是「这个词本来就没读错」的佐证，落下去反倒把标点删了。
    # 空格要留着比：`oflooking → of looking` 只差一个空格，那正是要改的东西
    letters = lambda x: ' '.join(
        re.sub(r'[^0-9A-Za-zÀ-ÖØ-öø-ÿ ]', '', x).lower().split())
    if letters(reading) == letters(garbage):
        return False
    if SequenceMatcher(None, reading.lower(), garbage.lower()).ratio() < MIN_SIM:
        return False
    core = lambda x: x.strip(".,;:!?()[]'\"")
    if core(reading).lower() in wit.get(core(garbage), ()) and conf >= 70:
        return True
    # 读数可能是两个词——`oflooking → of looking` 这类粘连，重扫会拆开。
    # 每一截都得是词，不能有一截是残串。
    parts = [core(w) for w in reading.split()]
    return (conf >= MIN_CONF and all(parts)
            and all(is_word(w, lex) for w in parts))


def apply_it():
    """按前后文锚唯一定位后落回。定位不唯一就不落——同一串在不同地方
    未必来自同一个词，这一点与希伯来那条线同理。"""
    lex, wit = build(), witness_readings()
    rows = [r for r in csv.DictReader(open(OUT, encoding='utf-8'), delimiter='\t',
                                      quoting=csv.QUOTE_NONE)
            if accept(r, lex, wit)]
    chapters = {p.stem: p.read_text(encoding='utf-8') for p in PUB.glob('*.md')}
    keys = {k: norm(v) for k, v in chapters.items()}
    edits, log, stat = {k: [] for k in chapters}, [], {'applied': 0,
                                                      'notfound': 0,
                                                      'ambiguous': 0}
    for r in rows:
        anchor, _ = norm(f"{r['before']} {r['garbage']} {r['after']}")
        garb, _ = norm(r['garbage'])
        if not garb or not anchor:
            continue
        hits = []
        for name, (flat, _) in keys.items():
            start = 0
            while True:
                p = flat.find(anchor, start)
                if p < 0:
                    break
                hits.append((name, p))
                start = p + 1
        if not hits:
            stat['notfound'] += 1
            log.append((r['garbage'], r['reading'], r['conf'], 'notfound'))
            continue
        if len(hits) > 1:
            stat['ambiguous'] += 1
            log.append((r['garbage'], r['reading'], r['conf'], 'ambiguous'))
            continue
        name, p = hits[0]
        flat, idx = keys[name]
        g = flat.find(garb, p)
        if g < 0 or g > p + len(anchor):
            stat['notfound'] += 1
            log.append((r['garbage'], r['reading'], r['conf'], 'notfound'))
            continue
        # 重扫常把词尾标点吞掉（`Statms, → Statius`）。原串带着的首尾标点
        # 要还回去，不然落一次盘就少一个逗号。
        rep = r['reading']
        lead = re.match(r'^[^0-9A-Za-zÀ-ÖØ-öø-ÿ]*', r['garbage']).group()
        tail = re.search(r'[^0-9A-Za-zÀ-ÖØ-öø-ÿ]*$', r['garbage']).group()
        if lead and not rep.startswith(lead):
            rep = lead + rep
        if tail and not rep.endswith(tail):
            rep = rep + tail
        edits[name].append((idx[g], idx[g + len(garb) - 1] + 1, rep))
        stat['applied'] += 1
        log.append((r['garbage'], r['reading'], r['conf'], 'applied'))
    for name, es in edits.items():
        if not es:
            continue
        text = chapters[name]
        for a, b, rep in sorted(es, reverse=True):
            text = text[:a] + rep + text[b:]
        (PUB / f'{name}.md').write_text(text, encoding='utf-8')
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('garbage\treading\tconf\tstatus\n')
        for row in log:
            f.write('\t'.join(str(x) for x in row) + '\n')
    print('重扫落盘:', stat, '→', LOG)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    if a.apply:
        apply_it()
    else:
        scan()
