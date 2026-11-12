#!/usr/bin/env python3
"""福特《路加福音讲义》正文残字·第 3 版看图（2026-11-12 用户令「处理」）。

前两轮残串看图（foote_junk_check.py）之后正文还剩约 420 处残字。抽看第 21 讲 p.306：主底本（第 2 版）这页
右栏行末被墨渍盖住（`Brethren▬`、`le▬`、`error o▬`、`multitud▬`），转录本那里也记 [?]——这份扫描读不出，
再看它的图也没用。第 1–66 讲另有第 3 版一份扫描（lecturesongospe01footgoog）：

  定位：残字两旁各取至多 4 个干净词（无残字、纯字母）作锚，左锚字母串在第 3 版 ABBYY 字母流里唯一命中、
        右锚紧随其后（中间至多 60 字母）——两锚之间就是第 3 版同位印的字（B）。
  闸：  B 每个词都是真词；B 与我们这截词数相同（挡两版之间的改写）；我们这截里能读的字母与 B 大体相合。
  题：  A＝我们这截，B＝第 3 版那截；图＝第 3 版那几行（ABBYY 行框，原生分辨率）。一页图只看一次。
  落：  只落答 B。

    python3 scripts/foote_junk_ed3.py --collect      # 链条位置：foote_notes_fill --apply 之后
    python3 scripts/foote_junk_ed3.py --run --sample 3 | --run --all
    python3 scripts/foote_junk_ed3.py --rules        # → junk_ed3_fixes.tsv
    python3 scripts/foote_junk_ed3.py --apply
"""
import argparse
import base64
import csv
import gzip
import io
import json
import random
import re
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import fitz
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_image_check as I  # noqa: E402
import foote_junk_check as J  # noqa: E402

RAW = A.RAW
WORK = RAW / 'imgcheck'
CAND = WORK / 'junk_ed3_candidates.json'
ANS = WORK / 'junk_ed3_answers'
ED3 = WORK / 'ed3_lines.json'
RULES = RAW / 'junk_ed3_fixes.tsv'
LOG = A.ROOT / 'logs' / 'foote_junk_ed3.tsv'
COST = A.ROOT / 'logs' / 'foote_junk_ed3_cost.tsv'
PDF = RAW / 'pdf' / 'vol1_ed3_lecturesongospe01footgoog.pdf'
NS = '{http://www.abbyy.com/FineReader_xml/FineReader6-schema-v1.xml}'
ORD = re.compile(r'\b\d+(st|nd|rd|th|d)\b')
CLEAN = re.compile(r"[A-Za-z][A-Za-z']*")
WORD = re.compile(r"[^\s]+")
REACH = 4
ROUND = 1


def use_round(n):
    """第 2 轮（链条末段，notes_leak2 之后）：锚放宽——锚词只须不带残符号（墨渍页附近的锚词本身也常读花），
    由长到短试 3/2/1 词。题、答、表另存 *_r2。"""
    global ROUND, CAND, ANS, RULES, LOG
    ROUND = n
    if n == 2:
        CAND = WORK / 'junk_ed3_candidates_r2.json'
        ANS = WORK / 'junk_ed3_answers_r2'
        RULES = RAW / 'junk_ed3_fixes_r2.tsv'
        LOG = A.ROOT / 'logs' / 'foote_junk_ed3_r2.tsv'

SYSTEM = (
    'You are proof-reading a digitised 19th-century printed book. Our copy of a passage is damaged (ink blots over '
    'line ends), so you are shown the SAME passage printed in another edition of the book: one or more line strips '
    '(native scan resolution). For each numbered question you get the passage in context and two candidate readings '
    'A and B of the disputed stretch. Decide which reading matches what is printed in the strips, character for '
    'character: letters, apostrophes, hyphens, and every punctuation mark. A word broken across two lines with a '
    'hyphen counts as the whole word. Asterisks *like this* only mark italics; ⁽ⁿ⁾ stands for a footnote mark. '
    'Answer each question on its own line exactly as  #n: A   or  #n: B   or, if neither matches the print,  '
    '#n: = <the printed text of the stretch>  . If it cannot be made out, answer  #n: ?  . Output only the answer lines.'
)


def ed3_lines():
    """第 3 版 ABBYY → [(leaf, [l,t,r,b] 按页图像素, 行文本)]，缓存。"""
    if ED3.exists():
        return json.loads(ED3.read_text(encoding='utf-8'))
    doc = fitz.open(PDF)
    out, leaf = [], 0
    with gzip.open(RAW / 'src' / f'{A.WITNESS_ID}_abbyy.gz') as f:
        for _, el in ET.iterparse(f):
            if el.tag != NS + 'page':
                continue
            img = doc.extract_image(doc[leaf].get_images(full=True)[0][0])
            k = img['width'] / int(el.get('width'))
            for ln in el.iter(NS + 'line'):
                t = ''.join(c.text or '' for c in ln.iter(NS + 'charParams'))
                t = ''.join(c for c in t if unicodedata.category(c) != 'Co')
                if t.strip():
                    out.append((leaf, [round(int(ln.get(x)) * k) for x in 'ltrb'], t))
            leaf += 1
            el.clear()
    WORK.mkdir(parents=True, exist_ok=True)
    ED3.write_text(json.dumps(out), encoding='utf-8')
    return out


def stream(lines):
    """行拼成全文（行间 \\n）；字母流 low 与字母→全文位置 pos；全文位置→行号 lno。"""
    text, lno = [], []
    for i, (_, _, t) in enumerate(lines):
        text.append(t + '\n')
        lno += [i] * (len(t) + 1)
    text = ''.join(text)
    pos = [i for i, c in enumerate(text) if c.isalpha()]
    low = ''.join(text[i].lower() for i in pos)
    return text, low, pos, lno


def letters(t):
    return re.sub(r'[^a-z]', '', t.lower())


def junk_spans(text):
    """正文里残字所在的截：[(左锚起, 截起, 截止, 右锚止)]，相邻残字并成一截。"""
    body = text.partition('\n---\n')[0]
    words = [(m.start(), m.end(), m.group()) for m in WORD.finditer(body)]
    tags = [(m.start(), m.end()) for m in re.finditer(r'<!--.*?-->', body, re.S)]
    intag = lambda p: any(a <= p < b for a, b in tags)
    def clean(w):                                  # 锚词：纯字母、真词（`mean--^ ing` 的 ing 不能当锚）
        c = w.strip('.,;:!?"()*—\'')
        return CLEAN.fullmatch(c) and not J.BAD.search(w) and A._isword(c.strip("'"))
    bad = [i for i, (s, e, w) in enumerate(words)
           if not intag(s) and J.BAD.search(ORD.sub('', w)) and not (w == '>' and body[s - 1] == '\n')]
    spans, i = [], 0
    while i < len(bad):
        lo = hi = bad[i]
        while i + 1 < len(bad) and bad[i + 1] - hi <= 2:
            i += 1
            hi = bad[i]
        i += 1
        # 截两边各扩到最近的干净词为止（干净词不进截）
        while lo > 0 and not clean(words[lo - 1][2]):
            lo -= 1
        while hi + 1 < len(words) and not clean(words[hi + 1][2]):
            hi += 1
        left = words[max(0, lo - REACH):lo]
        right = words[hi + 1:hi + 1 + REACH]
        if len(left) < 2 or len(right) < 2 or not all(clean(w) for *_, w in left + right):
            continue
        if any(intag(s) for s, *_ in left + right) or '\n\n' in body[left[0][0]:right[-1][1]]:
            continue
        spans.append((left[0][0], left[-1][1], right[0][0], right[-1][1]))
    return spans


def spans_r2(text):
    """第 2 轮的截：残字两旁各至多 3 个不带残符号的词（不求真词），返回 (左锚词列, 截起, 截止, 右锚词列)。"""
    body = text.partition('\n---\n')[0]
    tags = [(m.start(), m.end()) for m in re.finditer(r'<!--.*?-->', body, re.S)]
    toks = [(m.start(), m.end(), m.group()) for m in WORD.finditer(body) if not any(a <= m.start() < b for a, b in tags)]
    bad = lambda w: bool(J.BAD.search(ORD.sub('', w)))
    out, i = [], 0
    while i < len(toks):
        if not bad(toks[i][2]) or (toks[i][2] == '>' and body[toks[i][0] - 1] == '\n'):
            i += 1
            continue
        lo = hi = i
        while hi + 1 < len(toks) and bad(toks[hi + 1][2]):
            hi += 1
        i = hi + 1
        left, right = toks[max(0, lo - 3):lo], toks[hi + 1:hi + 4]
        if not left or not right or any(bad(w) for *_, w in left + right):
            continue
        s, e = left[-1][1], right[0][0]
        if '\n\n' in body[s:e] or '<!--' in body[s:e]:
            continue
        out.append(([w for *_, w in left], s, e, [w for *_, w in right]))
    return out


def collect():
    if ROUND == 2:
        return collect_r2()
    lines = ed3_lines()
    etext, low, pos, lno = stream(lines)
    pages, skip = {}, Counter()
    for lec in range(1, 67):
        text = (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8')
        for a0, s, e, b1 in junk_spans(text):
            L, R = letters(text[a0:s]), letters(text[e:b1])
            if len(L) < 10 or len(R) < 6:
                skip['锚太短'] += 1
                continue
            hits = [m.start() for m in re.finditer(re.escape(L), low)]
            found = []
            for h in hits:
                j = low.find(R, h + len(L), h + len(L) + 60 + len(R))
                if j >= 0:
                    found.append((h, j))
            if len(found) != 1:
                skip['第3版定位不到' if not found else '第3版多处'] += 1
                continue
            h, j = found[0]
            cs, ce = pos[h + len(L) - 1] + 1, pos[j]          # 左锚末字母之后 → 右锚首字母之前
            raw = etext[cs:ce]
            b = re.sub(r'(?<=[a-z])-\n(?=[a-z])', '', raw).replace('\n', ' ')
            o = text[s:e]
            # 截两端的空白、引号照我们的样子：只比中间
            ow, bw = o.split(), b.split()
            if not bw or J.BAD.search(ORD.sub('', b)) or any(not A._isword(x.strip("'")) for x in re.findall(r"[A-Za-z']+", b)):
                skip['第3版也残'] += 1
                continue
            if re.search(r'-\W*$', o.strip()):
                skip['行末断词'] += 1                  # `the mean--^ ing`：右锚 ing 是断词后半，换了会成 `mean ing`
                continue
            if len(ow) != len(bw):
                skip['词数不同'] += 1
                continue
            lo_, lb = letters(o), letters(b)
            if lo_ and SequenceMatcher(None, lo_, lb, autojunk=False).ratio() < 0.5:
                skip['字母不合'] += 1
                continue
            if letters(o) == lb and not J.BAD.search(o):
                continue
            core = b.strip()
            if o.strip().startswith('*') and o.strip().endswith('*'):
                core = '*' + core + '*'            # 斜体照我们的
            core += A.FN_MARK * o.count(A.FN_MARK)  # 注号哨兵留着（第 3 版的注号字符是私用区，已滤掉）
            new = o[:len(o) - len(o.lstrip())] + core + o[len(o.rstrip()):]
            l0, l1 = lno[cs], lno[max(cs, ce - 1)]
            leaf = lines[l0][0]
            if lines[l1][0] != leaf:
                skip['跨页'] += 1
                continue
            box = [min(lines[k][1][0] for k in range(l0, l1 + 1)), lines[l0][1][1],
                   max(lines[k][1][2] for k in range(l0, l1 + 1)), lines[l1][1][3]]
            ctx = (text[max(0, s - 70):s] + '⟦' + o + '⟧' + text[e:e + 70]).replace('\n', ' ')
            pages.setdefault(leaf, []).append({'lec': f'{lec:03d}', 's': s, 'e': e, 'ours': o, 'vlm': new,
                                               'box': box, 'ctx': re.sub(r'<!--.*?-->', '', ctx)})
    out = [{'leaf': k, 'qs': v} for k, v in sorted(pages.items())]
    WORK.mkdir(parents=True, exist_ok=True)
    CAND.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'题 {sum(len(p["qs"]) for p in out)}  页 {len(out)}  跳过 {dict(skip)} → {CAND}', file=sys.stderr)


def collect_r2():
    lines = ed3_lines()
    etext, low, pos, lno = stream(lines)
    pages, skip = {}, Counter()
    for lec in range(1, 67):
        text = (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8')
        for lw, s, e, rw in spans_r2(text):
            found = set()
            for nl, nr in ((3, 3), (3, 2), (2, 3), (2, 2), (2, 1), (1, 2), (1, 1)):
                if nl > len(lw) or nr > len(rw):
                    continue
                L, R = letters(''.join(lw[-nl:])), letters(''.join(rw[:nr]))
                if len(L) < 7 or len(R) < 4:
                    continue
                for m in re.finditer(re.escape(L), low):
                    h = m.start()
                    j = low.find(R, h + len(L), h + len(L) + 40 + len(R))
                    if j >= 0:
                        found.add((pos[h + len(L) - 1] + 1, pos[j]))
                if found:
                    break
            if len(found) != 1:
                skip['第3版定位不到' if not found else '第3版多处'] += 1
                continue
            cs, ce = found.pop()
            b = re.sub(r'(?<=[a-z])-\n(?=[a-z])', '', etext[cs:ce]).replace('\n', ' ')
            # 左锚词末标点、右锚词首标点已在锚里：B 两头去掉
            lt = re.search(r"[^A-Za-z]*$", lw[-1]).group()
            rh = re.match(r"[^A-Za-z]*", rw[0]).group()
            if lt and b.lstrip().startswith(lt):
                k = len(b) - len(b.lstrip())
                b = b[:k] + b[k + len(lt):]
            if rh and b.rstrip().endswith(rh):
                k = len(b.rstrip())
                b = b[:k - len(rh)] + b[k:]
            o = text[s:e]
            if not b.strip() or J.BAD.search(ORD.sub('', b)) or any(
                    not A._isword(x.strip("'").lower()) for x in re.findall(r"[A-Za-z']+", b)):
                skip['第3版也残'] += 1
                continue
            if abs(len(o.split()) - len(b.split())) > 1:
                skip['词数不同'] += 1
                continue
            if re.search(r'-\W*$', o.strip()) or re.fullmatch(r'\s*[b-hj-z]\s*', b):
                skip['行末断词'] += 1                  # `mean--^ ing`、`multitud -^ of`（补出孤立的 e）
                continue
            if any(b.count(c) > o.count(c) for c in '"\''):
                skip['引号'] += 1                      # 两版引号排法可能不同，第 3 版的引号不搬
                continue
            lo_, lb = letters(o), letters(b)
            if lo_ and SequenceMatcher(None, lo_, lb, autojunk=False).ratio() < 0.4:
                skip['字母不合'] += 1
                continue
            core = re.sub(r'\s+', ' ', b.strip())
            core = re.sub(r'^"\s+(?=[A-Za-z])', '"', core)   # ABBYY 在开引号后多读一个空格
            if o.strip().startswith('*') and o.strip().endswith('*') and len(o.strip()) > 1:
                core = '*' + core + '*'
            core += A.FN_MARK * o.count(A.FN_MARK)
            new = o[:len(o) - len(o.lstrip())] + core + o[len(o.rstrip()):]
            l0, l1 = lno[cs], lno[max(cs, ce - 1)]
            leaf = lines[l0][0]
            if lines[l1][0] != leaf:
                skip['跨页'] += 1
                continue
            box = [min(lines[k][1][0] for k in range(l0, l1 + 1)), lines[l0][1][1],
                   max(lines[k][1][2] for k in range(l0, l1 + 1)), lines[l1][1][3]]
            ctx = (text[max(0, s - 70):s] + '⟦' + o + '⟧' + text[e:e + 70]).replace('\n', ' ')
            pages.setdefault(leaf, []).append({'lec': f'{lec:03d}', 's': s, 'e': e, 'ours': o, 'vlm': new,
                                               'box': box, 'ctx': re.sub(r'<!--.*?-->', '', ctx)})
    out = [{'leaf': k, 'qs': v} for k, v in sorted(pages.items())]
    CAND.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'第2轮 题 {sum(len(p["qs"]) for p in out)}  页 {len(out)}  跳过 {dict(skip)} → {CAND}', file=sys.stderr)


def strips(leaf, qs):
    doc = fitz.open(PDF)
    im = Image.open(io.BytesIO(doc.extract_image(doc[leaf].get_images(full=True)[0][0])['image'])).convert('L')
    groups = []
    for n, q in enumerate(qs, 1):
        x0, y0, x1, y1 = q['box']
        for g in groups:
            if not (y1 < g[1] or y0 > g[3]):
                g[:4] = [min(g[0], x0), min(g[1], y0), max(g[2], x1), max(g[3], y1)]
                g[4].append(n)
                break
        else:
            groups.append([x0, y0, x1, y1, [n]])
    out = []
    for x0, y0, x1, y1, ns in sorted(groups, key=lambda g: g[1]):
        buf = io.BytesIO()
        im.crop((max(0, x0 - 40), max(0, y0 - 20), min(im.width, x1 + 40), min(im.height, y1 + 20))).save(buf, 'PNG')
        out.append((buf.getvalue(), ns))
    return out


def ask(leaf, qs):
    content = []
    for k, (png, ns) in enumerate(strips(leaf, qs), 1):
        content.append({'type': 'text', 'text': f'Strip {k} (questions {", ".join("#%d" % n for n in ns)}):'})
        content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                                    'data': base64.b64encode(png).decode()}})
    lines = []
    for n, q in enumerate(qs, 1):
        a, b = q['ours'], q['vlm']
        if q.get('swap'):
            a, b = b, a
        lines.append(f'#{n}: context «{q["ctx"].replace(A.FN_MARK, "⁽ⁿ⁾")}»\n    A = «{a.replace(A.FN_MARK, "⁽ⁿ⁾")}»'
                     f'\n    B = «{b.replace(A.FN_MARK, "⁽ⁿ⁾")}»')
    content.append({'type': 'text', 'text': '\n'.join(lines)})
    old = I.SYSTEM
    I.SYSTEM = SYSTEM
    try:
        msg = {'type': 'user', 'message': {'role': 'user', 'content': content}}
        cmd = ['claude', '-p', '--safe-mode', '--strict-mcp-config', '--disallowedTools', '*',
               '--input-format', 'stream-json', '--output-format', 'stream-json', '--verbose', '--system-prompt', SYSTEM]
        r = subprocess.run(cmd, input=json.dumps(msg) + '\n', capture_output=True, text=True, timeout=900)
    finally:
        I.SYSTEM = old
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


def qkey(q):
    return (q['lec'], q['ours'], q['vlm'], q['ctx'])


def answered():
    got = {}
    for f in sorted(ANS.glob('*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        for n, q in enumerate(d['qs'], 1):
            a = d['ans'].get(str(n), '')
            if q.get('swap') and a in ('A', 'B'):
                a = 'B' if a == 'A' else 'A'
            got[qkey(q)] = a
    return got


def run(sample, all_):
    pages = json.loads(CAND.read_text(encoding='utf-8'))
    got = answered()
    todo = []
    for p in pages:
        qs = [q for q in p['qs'] if qkey(q) not in got]
        rnd = random.Random(f"ed3-{p['leaf']}")
        for q in qs:
            q['swap'] = rnd.random() < 0.5
        if qs:
            todo.append(dict(p, qs=qs))
    if not all_:
        random.seed(20261112)
        todo = random.sample(todo, min(sample or 3, len(todo)))
    total, fails = 0.0, 0
    ANS.mkdir(parents=True, exist_ok=True)
    with open(COST, 'a', encoding='utf-8') as fh:
        for n, p in enumerate(todo, 1):
            try:
                res, cost = ask(p['leaf'], p['qs'])
            except Exception as e:                     # noqa: BLE001
                fails += 1
                print(f"{p['leaf']:4d} 失败 {e}", file=sys.stderr, flush=True)
                if 'limit' in str(e).lower():
                    sys.exit(42)
                if fails >= 5:
                    sys.exit(3)
                continue
            fails = 0
            total += cost
            ans = {int(m.group(1)): m.group(2) for m in re.finditer(r'^\s*#(\d+):\s*(.*?)\s*$', res, re.M)}
            k = 1
            while (ANS / f"{p['leaf']:04d}_{k}.json").exists():
                k += 1
            (ANS / f"{p['leaf']:04d}_{k}.json").write_text(
                json.dumps({'raw': res, 'ans': ans, 'qs': p['qs']}, ensure_ascii=False), encoding='utf-8')
            fh.write(f"{p['leaf']}\t{len(p['qs'])}\t{len(ans)}\t{cost:.4f}\n")
            fh.flush()
            print(f"{p['leaf']:4d} 问 {len(p['qs']):2d} 答 {len(ans):2d}  ${cost:.4f}  累计 ${total:.2f}  "
                  f"({n}/{len(todo)})", file=sys.stderr, flush=True)


def verdict(q, a):
    if a in ('A', 'B'):
        return a
    if not a.startswith('='):
        return 'other'
    f = lambda t: re.sub(r"[^A-Za-z0-9']", '', t.replace('’', "'"))
    x = f(a[1:])
    return 'B' if x == f(q['vlm']) else 'A' if x == f(q['ours']) else 'other'


def rules():
    pages = json.loads(CAND.read_text(encoding='utf-8'))
    got = answered()
    rows, out, texts = [], [], {}
    for p in pages:
        for q in p['qs']:
            a = got.get(qkey(q))
            v = 'unasked' if a is None else verdict(q, a)
            rows.append((v, q['lec'], p['leaf'], q['ours'], q['vlm'], a or '', q['ctx']))
            if v != 'B':
                continue
            text = texts.setdefault(q['lec'], (A.SRC / f"{q['lec']}.md").read_text(encoding='utf-8'))
            # 原串带两旁的词，逐词放宽到唯一（同讲两处 `other^` 只差上下文）
            ls, re_ = q['s'], q['e']
            for _ in range(8):
                ls = text.rfind(' ', 0, max(0, ls - 1)) + 1
                re_ = text.find(' ', re_ + 1)
                old = text[ls:re_]
                if text.count(old) == 1:
                    break
            new = text[ls:q['s']] + q['vlm'] + text[q['e']:re_]
            if text.count(old) != 1:
                rows[-1] = ('X-not-unique',) + rows[-1][1:]
                continue
            out.append((q['lec'], old, new))
    with open(LOG, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['verdict', 'lecture', 'ed3leaf', 'ours', 'ed3', 'answer', 'ctx'])
        w.writerows(rows)
    RULES.write_text('# lecture\t原串\t改作 —— foote_junk_ed3.py 生成（正文残字，第 3 版同位读出、看第 3 版图答 B）；\\n 表换行\n'
                     + ''.join('\t'.join(x.replace('\n', '\\n') for x in r) + '\n' for r in out), encoding='utf-8')
    print(dict(Counter(r[0] for r in rows)), f'规则 {len(out)} → {RULES}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--collect', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--rules', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--round', type=int, default=1)
    a = ap.parse_args()
    use_round(a.round)
    if a.collect:
        collect()
    elif a.run:
        run(a.sample, a.all)
    elif a.rules:
        rules()
    elif a.apply and RULES.exists():
        I.apply_multiline(RULES)


if __name__ == '__main__':
    main()
