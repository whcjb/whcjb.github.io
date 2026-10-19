#!/usr/bin/env python3
"""以赛亚书剩余外文乱码 → tesseract 读数 + 视觉模型**印证**，两家全同才落。

闭集选词（isaiah_hebrew_closedset.py）只救得了马所拉文本里有的词。剩下的——迦勒底
意译（14:14「(SE35 b=)」= כל עמא）、拉比原话、七十士译本希腊文——原图印得清楚，
tesseract 也常常读对了，只是置信度够不上 80、或词不在 WLC 里，于是一直以乱码留着
（用户 2026-10-19：「相关的错误是否都解决了，不要只解决这一个」）。

old-book-ocr SKILL §3.2c「证人只许当印证，候选必须来自非生成式字流」：
    候选 = tesseract heb / grc 对裁图的读数（非生成式）
    证人 = 视觉模型看同一块裁图，只照抄印的字母
    落盘 = 两家在同一位置给出**同一串字母**才落 tesseract 的读数；证人的字不进产物
      希伯来/亚兰：辅音全同（只落辅音，同闭集口径）
      希腊：连重音、气号全同（NFC 比）
    证人说是拉丁字母 → 一律不动（这本身是防误伤的闸：英文残字不会被换成外文）

只处理**发布页上乱码还在**的块；一批 25 块图一次送（SKILL §2.6：送图是大头成本）。

用法：
    python3 scripts/isaiah_witness_vlm.py --pages 342-370     # 试一章
    python3 scripts/isaiah_witness_vlm.py                     # 全书
输出 alexander_raw/isaiah/hebrew_witness.tsv（apply 格式），证人原始回答存
alexander_raw/isaiah/witness_vlm.jsonl（一次性资产，重跑不再花钱）。
"""
import argparse
import base64
import json
import re
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
import isaiah_hebrew_ocr as H                       # noqa: E402
import isaiah_hebrew_closedset as C                 # noqa: E402
from alexander_lexicon import build                 # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'alexander_raw/isaiah/hebrew_witness.tsv'
CACHE = ROOT / 'alexander_raw/isaiah/witness_vlm.jsonl'
CROPS = ROOT / 'alexander_raw/isaiah/witness_crops'
BATCH = 25

SYSTEM = (
    'You are a transcription witness for a 19th-century printed book. Each image is a small crop '
    'of printed type. Copy exactly the characters printed in each image — do not translate, '
    'correct, complete, or guess.\n'
    'Rules:\n'
    '- Hebrew or Aramaic letters: write the Hebrew consonants in reading order (right to left as '
    'read), WITHOUT vowel points or accents. Keep spaces and maqaf (־) between words.\n'
    '- Greek: write the Greek letters with all accents and breathings exactly as printed.\n'
    '- Latin letters (English, Latin, German…): write them as printed.\n'
    '- Mixed scripts: write everything in the order printed.\n'
    '- Ignore parentheses, commas and other punctuation.\n'
    '- If you cannot read a character with certainty, write ? in its place. Never invent.\n'
    'Answer with one line per image: the image number, a tab, then the transcription. '
    'Nothing else.'
)

LATIN = re.compile(r'[A-Za-z]')
GREEK = re.compile(r'[Ͱ-Ͽἀ-῿]')


def greek_norm(s):
    s = unicodedata.normalize('NFC', s).replace('ς', 'σ').replace('ϑ', 'θ')
    return re.sub(r'[^Ͱ-Ͽἀ-῿]', '', s)


def ask(batch):
    """batch = [(id, png_bytes)] → {id: text}"""
    content = []
    for i, png in batch:
        content.append({'type': 'text', 'text': f'Image {i}:'})
        content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                                    'data': base64.b64encode(png).decode()}})
    content.append({'type': 'text', 'text': 'Transcribe each image.'})
    msg = {'type': 'user', 'message': {'role': 'user', 'content': content}}
    cmd = ['claude', '-p', '--safe-mode', '--mcp-config', '{"mcpServers":{}}',
           '--strict-mcp-config', '--disallowedTools', '*',
           '--input-format', 'stream-json', '--output-format', 'stream-json',
           '--verbose', '--system-prompt', SYSTEM]
    r = subprocess.run(cmd, input=json.dumps(msg) + '\n', capture_output=True, text=True, timeout=900)
    for line in r.stdout.splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get('type') == 'result':
            if o.get('is_error'):
                raise RuntimeError(str(o.get('result'))[:200])
            out = {}
            for ln in str(o.get('result') or '').splitlines():
                m = re.match(r'\s*(?:Image\s*)?(\d+)\s*[:\t]\s*(.*)$', ln)
                if m:
                    out[int(m.group(1))] = m.group(2).strip()
            return out, float(o.get('total_cost_usd') or 0)
    raise RuntimeError('no result: ' + r.stderr[-200:])


def still_garbage(j):
    """发布页上这块乱码还在吗（已被闭集 / 开集 / 人工换掉的就不再送）"""
    loc = C.locate(j)
    if not loc:
        return True          # 定位不到的也送：证人判定之后 apply 自己再按锚找
    text, _ = C._FLAT[loc[0]]
    return C.norm_loc(j['garbage']) in text


def collect(page_range):
    lex = build()
    jobs = []
    for vol in ('v1', 'v2'):
        doc = fitz.open(H.PDF[vol])
        idx = 0
        for _, el in ET.iterparse(H.XML[vol], events=('end',)):
            if el.tag != H.NS + 'page':
                continue
            idx += 1
            if not (page_range[vol][0] <= idx <= page_range[vol][1]):
                el.clear()
                continue
            pw, ph = int(el.get('width')), int(el.get('height'))
            page = doc[idx - 1]
            sx, sy = page.rect.width / pw, page.rect.height / ph
            prev_hyphen, prev_tail = False, ''
            for line in el.iter(H.NS + 'line'):
                toks = H.line_tokens(line)
                skip = set()
                line_hyphen = bool(toks) and toks[-1][0].rstrip('\'"').endswith('-')
                if line_hyphen:
                    skip.add(len(toks) - 1)
                if prev_hyphen and toks:
                    skip.add(0)
                prev_hyphen = line_hyphen
                run = []
                for k, (txt, box) in enumerate(toks + [(None, None)]):
                    if txt is not None and run and not any(c.isalnum() for c in txt):
                        run.append((txt, box))
                        continue
                    if (txt is not None and k not in skip and H.looks_residue(txt, lex)
                            and not C.english(txt, lex) and len(run) < 4):
                        run.append((txt, box))
                        continue
                    if run:
                        j = H.crop(run, toks, page, sx, sy, vol, idx)
                        if j:
                            j['chapters'] = list(range(1, 67))
                            j['ctx'] = (prev_tail + ' ' + j['before']).strip()
                            jobs.append(j)
                        run = []
                prev_tail = ' '.join(t for t, _ in toks[-4:])
            el.clear()
        doc.close()
    return jobs


def caret_fix(garbage, witness):
    """拉丁字母串里夹的 ^：候选全从 ABBYY 原串枚举——删掉、换空格、换成任一字母——
    与证人读的字母（不计大小写、标点）一致的才用；都不一致返回 None（交给链条末尾清扫）。
    直接删会造出新错：`same^dogs`→samedogs、`sp^fcific`→spfcific（^ 占的是 e）。"""
    if '?' in witness:                     # 证人自己没读清
        return None
    key = lambda x: re.sub(r'[^a-z ]', '', x.lower().replace('æ', 'ae')).split()
    want = key(witness)
    cands = [garbage.replace('^', ''), garbage.replace('^', ' ')]
    if garbage.count('^') == 1:
        cands += [garbage.replace('^', ch) for ch in 'abcdefghijklmnopqrstuvwxyz']
    for c in cands:
        if key(c) == want and not re.search(r'[<>{}|~\\]', c):
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', help='v1 扫描页范围（试跑）')
    ap.add_argument('--jobs', type=int, default=4)
    a = ap.parse_args()
    if a.pages:
        lo, hi = map(int, a.pages.split('-'))
        pr = {'v1': (lo, hi), 'v2': (0, -1)}
    else:
        pr = {'v1': H.BODY['v1'], 'v2': H.BODY['v2']}

    # 结果表是**累积**的：所有候选块都出结果（证人回答走缓存）；「乱码还在发布页上」只决定送不送
    # 新证人。曾经只给「还在」的块出结果，上一轮已落好的 1101 处下一轮不再进表，重跑链条又退回乱码
    jobs = collect(pr)
    for j in jobs:
        j['live'] = still_garbage(j)
    print(f'候选块 {len(jobs)}，其中乱码仍在发布页上 {sum(j["live"] for j in jobs)}', flush=True)

    # tesseract 两套读数（候选，非生成式）
    def tess(j):
        heb, ch = H.ocr(j['png'], 'heb')
        if len(H.HEBREW.findall(heb)) < 2:
            heb, ch = H.ocr(j['png'], 'heb', '8')
        grc, cg = H.ocr(j['png'], 'grc')
        j.update(heb=heb, heb_conf=ch, grc=grc, grc_conf=cg)
        return j
    with ThreadPoolExecutor(8) as pool:
        jobs = list(pool.map(tess, jobs))

    # 免费预筛：tesseract 自己都读不出外文的块不送（第 14 章试跑 284 块里 222 块证人说是
    # 拉丁字母——人名、拉丁文、英文残字——送了白花钱）
    def foreign(j):
        # 带 ^ 的一律送：原书不印 ^，它一出现就是活字残渣（用户 2026-10-19「把全书所有的 ^ 都解决了」）
        if '^' in j['garbage']:
            return True
        nh, ng = len(H.HEBREW.findall(j['heb'])), len(GREEK.findall(j['grc']))
        return nh >= 2 or (ng >= 3 and j['grc_conf'] >= 50)
    n0 = len(jobs)
    jobs = [j for j in jobs if foreign(j)]
    print(f'预筛：{n0} → {len(jobs)} 块（tesseract 读得出外文字母的）', flush=True)

    # 证人：先查缓存（键 = 页 + 前文 + 乱码），没有的才送
    cache = {}
    if CACHE.exists():
        for ln in CACHE.read_text(encoding='utf-8').splitlines():
            o = json.loads(ln)
            cache[o['key']] = o['vlm']
    key = lambda j: f"{j['vol']}|{j['scan_page']}|{j['before']}|{j['garbage']}"
    todo = [j for j in jobs if key(j) not in cache and j['live']]
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    print(f'送证人 {len(todo)} 块，{len(batches)} 批', flush=True)
    cost = 0.0

    def send(b):
        res, c = ask([(n + 1, Path(j['png']).read_bytes()) for n, j in enumerate(b)])
        return [(j, res.get(n + 1, '')) for n, j in enumerate(b)], c
    with ThreadPoolExecutor(a.jobs) as pool, CACHE.open('a', encoding='utf-8') as fh:
        for pairs, c in pool.map(send, batches):
            cost += c
            for j, v in pairs:
                cache[key(j)] = v
                fh.write(json.dumps({'key': key(j), 'vlm': v}, ensure_ascii=False) + '\n')
    print(f'证人费用 ${cost:.2f}', flush=True)

    rows, stat = [], {'块': len(jobs), '希伯来全同': 0, '希腊全同': 0, '证人说拉丁': 0, '对不上': 0}
    for j in jobs:
        v = cache.get(key(j), '')
        Path(j['png']).unlink(missing_ok=True)
        if not v:
            stat['未问过'] = stat.get('未问过', 0) + 1
            continue
        if False:
            stat['对不上'] += 1
            continue
        if LATIN.search(v):
            stat['证人说拉丁'] += 1
            if '^' in j['garbage'] and not re.search(r'[\u05D0-\u05EA\u0370-\u03FF\u1F00-\u1FFF]', v):
                # 拉丁字母印的（专名、拉丁词）只是夹了 ^：删 ^，字母照 ABBYY 原样，证人的字不进产物
                fixed = caret_fix(j['garbage'], v)
                if fixed is not None:
                    rows.append((j['vol'], j['scan_page'], j['before'], j['garbage'], j['after'],
                                 'caret', fixed, 91, v, '', 0))
            continue
        hv, ht = C.cons(v), C.cons(j['heb'])
        if '?' not in v and len(hv) >= 2 and hv == ht and not GREEK.search(v) and not LATIN.search(j['heb']) \
                and C.shape_ok(j['garbage'], j['heb']):
            stat['希伯来全同'] += 1
            reading = re.sub(r'[^א-ת־ ]', '', re.sub(r'\s+', ' ', j['heb'])).strip()
            rows.append((j['vol'], j['scan_page'], j['before'], j['garbage'], j['after'],
                         'heb-wit', reading, 92, v, j['heb'], round(j['heb_conf'])))
            continue
        gv, gt = greek_norm(v), greek_norm(j['grc'])
        if '?' not in v and len(gv) >= 2 and gv == gt and not re.search(r'[א-ת]', v):
            stat['希腊全同'] += 1
            reading = unicodedata.normalize('NFC', re.sub(r'[|\s]+', ' ', j['grc'])).strip(' .,;:')
            rows.append((j['vol'], j['scan_page'], j['before'], j['garbage'], j['after'],
                         'grc-wit', reading, 92, v, j['grc'], round(j['grc_conf'])))
            continue
        # 两家读不一致：字救不回来，但证人看得出是哪种文字——标出来，不留乱码
        if re.search(r'[\u05D0-\u05EA]', v):
            stat['标 Heb'] = stat.get('标 Heb', 0) + 1
            rows.append((j['vol'], j['scan_page'], j['before'], j['garbage'], j['after'],
                         'mark', '[Heb.]', 91, v, j['heb'], round(j['heb_conf'])))
            continue
        if GREEK.search(v):
            stat['标 Gk'] = stat.get('标 Gk', 0) + 1
            rows.append((j['vol'], j['scan_page'], j['before'], j['garbage'], j['after'],
                         'mark', '[Gk.]', 91, v, j['grc'], round(j['grc_conf'])))
            continue
        stat['对不上'] += 1
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('vol\tscan_page\tbefore\tgarbage\tafter\tscript\treading\tconf\twitness\ttesseract\ttess_conf\n')
        for r in rows:
            f.write('\t'.join(str(x).replace('\t', ' ') for x in r) + '\n')
    print(stat, '→', OUT)


if __name__ == '__main__':
    main()
