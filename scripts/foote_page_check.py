#!/usr/bin/env python3
"""福特《路加福音讲义》余下残字·一页一图（2026-11-12 用户令「继续，一个图用多次」）。

前面各层按题型分开问，同一页可能被看好几次图。这层把一页上剩下的残字（正文、注区一起）编成一题组，整页原图
（原生分辨率，竖切三条）只送一次，每处答 `= 印面这截` 或 `?`。

模型读的是印面，但它是生成式的，不单独作数——落盘须有第二个独立来源相合（任一）：
  T 转录同位读法（整卷转录字母流按两旁各 2 词定位）字字相同；
  S tess_grc（另一 OCR 引擎读同一扫描）同位词的字母相同；
  P 字母与我们这截删去残符号后相同，只是残符号换成了标点/引号（模型只补了印面上的标点）。
三闸都不过的不落，列 page_check_pending.tsv 待用户核。注号（印面 * † ‡）一律答 ⁽ⁿ⁾，个数须与我们这截相同；
斜体星号照我们的（模型不判斜体），改后本段星号须成偶数。

    python3 scripts/foote_page_check.py --collect      # 链条位置：foote_notes_entry --apply 之后
    python3 scripts/foote_page_check.py --run --sample 2 | --run --all
    python3 scripts/foote_page_check.py --rules        # → page_check_fixes.tsv + page_check_pending.tsv
    python3 scripts/foote_page_check.py --apply
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
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import fitz
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_image_check as I  # noqa: E402
import foote_junk_check as J  # noqa: E402
import foote_line_check as LC  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402

RAW = A.RAW
WORK = RAW / 'imgcheck'
CAND = WORK / 'page_check_candidates.json'
ANS = WORK / 'page_check_answers'
RULES = RAW / 'page_check_fixes.tsv'
PEND = RAW / 'page_check_pending.tsv'
LOG = A.ROOT / 'logs' / 'foote_page_check.tsv'
COST = A.ROOT / 'logs' / 'foote_page_check_cost.tsv'
ORD = re.compile(r'\b\d+(st|nd|rd|th|d)\b')
TOK = re.compile(r'\S+')
FNS = '⁽ⁿ⁾'
JUNKC = re.compile(r'[\^<>•■«»|~{}]')

SYSTEM = (
    'You are proof-reading a digitised 19th-century printed book against the image of ONE printed page (cut into two horizontal strips, top half and bottom half). Our digital text of this page has damaged spots. For each '
    'numbered question you get the spot inside ⟦ ⟧ with some context before and after; the context may itself contain '
    'OCR errors, use it only to find the place. The spot may be in the main text or in the footnotes at the foot of the '
    'page. Write exactly what is PRINTED for the stretch inside ⟦ ⟧: letters, digits, apostrophes, hyphens, dashes, '
    'commas, full stops, colons, semicolons, quotation marks (write them as straight " and \'). Greek or Hebrew: write it '
    'in Greek or Hebrew letters as printed. Do not write italics markers. Write a footnote reference mark (* † ‡ § ‖ ¶ '
    'printed small after a word) as ⁽ⁿ⁾. Do not correct the print: if the print has a misprint, copy the misprint. '
    'If the stretch inside ⟦ ⟧ is only noise in the scan (a speck, a blot) with nothing printed there, answer  #n: =  '
    '(nothing after the equals sign). Answer each question on its own line exactly as  #n: = <printed text>  or, if '
    'that place cannot be read with certainty,  #n: ?  . Output only the answer lines.'
)


def bad(w):
    return bool(J.BAD.search(ORD.sub('', w)))


def clusters(text, lo_, hi_):
    """text[lo_:hi_] 里的残字截：[(起, 止, 左锚词列, 右锚词列)]。"""
    tags = [(m.start(), m.end()) for m in re.finditer(r'<!--.*?-->', text, re.S)]
    toks = [(m.start(), m.end(), m.group()) for m in TOK.finditer(text, lo_, hi_)
            if not any(a <= m.start() < b for a, b in tags)]
    out, i = [], 0
    while i < len(toks):
        w = toks[i][2]
        line = text[text.rfind('\n', 0, toks[i][0]) + 1:]
        if not bad(w) or (w == '>' and text[toks[i][0] - 1] == '\n') or line.startswith(('## ', '**LUKE')):
            i += 1
            continue
        lo = hi = i
        while hi + 1 < len(toks) and (bad(toks[hi + 1][2]) or (hi + 2 < len(toks) and bad(toks[hi + 2][2])
                                                               and hi + 2 - lo <= 3)):
            hi += 1
        i = hi + 1
        s, e = toks[lo][0], toks[hi][1]
        if '<!--' in text[s:e] or '\n\n' in text[s:e]:
            continue
        out.append((s, e, [x[2] for x in toks[max(0, lo - 4):lo]], [x[2] for x in toks[hi + 1:hi + 5]],
                    [LC.letters(x[2]) for x in toks[max(0, lo - 8):min(len(toks), hi + 9)]], lo - max(0, lo - 8),
                    hi - max(0, lo - 8)))
    return out


def tess_span(tw, ctx, il, ir):
    """我们截前后词与 tess 逐词对齐（相合块 ≥2），截两旁锚词都对上时取 tess 在两锚之间的词。"""
    sm = SequenceMatcher(None, ctx, [x[0] for x in tw], autojunk=False)
    m = {}
    for b in sm.get_matching_blocks():
        if b.size >= 2:
            for k in range(b.size):
                m[b.a + k] = b.b + k
    a, b = il - 1, ir + 1
    if a in m and b in m and 0 < m[b] - m[a] <= 8:
        return ''.join(x[0] for x in tw[m[a] + 1:m[b]])
    return None


def locate_y(tw, lws, rws):
    """左锚两词或右锚两词在 tess 逐词里连续唯一出现 → 该行纵坐标；否则 None。"""
    ws = [x[0] for x in tw]
    for pair in (lws, rws):
        pair = [w for w in pair if w]
        if len(pair) < 2:
            continue
        hits = [k for k in range(len(ws) - 1) if ws[k] == pair[0] and ws[k + 1] == pair[1]]
        if len(hits) == 1:
            return tw[hits[0]][2]
    return None


def collect():
    pages = defaultdict(list)
    skip = Counter()
    for vol in (1, 2, 3):
        pn = V.leaf_pages(vol)
        leaf_of = {}
        for lf, pg in sorted(pn.items()):
            leaf_of.setdefault(str(pg), lf)
        vs, low, pos, leaves = LC.vol_stream(vol)
        for lec in V.LECS[vol]:
            text = (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8')
            nb = text.find('\n---\n')
            nb = len(text) if nb < 0 else nb
            pgs = [int(x) for x in re.findall(r'<!-- PAGE (\d+) -->', text[:nb])]
            lo_pg, hi_pg = (min(pgs) - 1, max(pgs) + 1) if pgs else (0, 0)
            for s, e, lw, rw, ctx, il, ir in clusters(text, 0, len(text)):
                if s < nb:
                    pm = list(re.finditer(r'<!-- PAGE (\d+) -->', text[:s]))
                    pg = pm[-1].group(1) if pm else None
                    where = 'body'
                else:
                    ls = text.rfind('\n', 0, s) + 1
                    m = re.match(r'<!-- NOTE p\.(\d+)', text[ls:])
                    pg = m.group(1) if m else None
                    where = 'note'
                if pg is None or pg not in leaf_of:
                    skip['无页'] += 1
                    continue
                lf = leaf_of[pg]
                # T：转录同位（两旁各 2 词字母串，限本讲页码范围内的叶）
                tB = None
                L, R = LC.letters(''.join(lw[-2:])), LC.letters(''.join(rw[:2]))
                if where == 'body' and len(L) >= 6 and len(R) >= 4:
                    found = set()
                    for mm in re.finditer(re.escape(L), low):
                        h = mm.start()
                        j = low.find(R, h + len(L), h + len(L) + 80 + len(R))
                        if j >= 0:
                            a0 = pos[h + len(L) - 1] + 1
                            try:
                                ok = lo_pg <= int(pn.get(leaves[a0], -1)) <= hi_pg
                            except ValueError:
                                ok = False
                            if ok:
                                found.add(vs[a0:pos[j]])
                    if len(found) == 1:
                        tB = found.pop()
                        if V.SENT in tB:
                            tB = None
                # S：tess 同位
                tw = I.tsv_words(vol, lf)
                sB = tess_span(tw, ctx, il, ir)
                y = locate_y(tw, [LC.letters(w) for w in lw[-2:]], [LC.letters(w) for w in rw[:2]])
                c0 = text.rfind('\n', 0, s) + 1
                before = re.sub(r'<!--.*?-->', '', text[max(c0, s - 90):s])
                after = text[e:e + 90].split('\n')[0]
                pages[(vol, lf)].append({'lec': f'{lec:03d}', 'page': pg, 'where': where, 's': s, 'e': e,
                                         'ours': text[s:e], 'tB': tB, 'sB': sB, 'y': y,
                                         'ctx': (before + '⟦' + text[s:e] + '⟧' + after).replace(A.FN_MARK, FNS)})
    out = [{'vol': v, 'leaf': lf, 'qs': qs} for (v, lf), qs in sorted(pages.items())]
    WORK.mkdir(parents=True, exist_ok=True)
    CAND.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    n = sum(len(p['qs']) for p in out)
    print(f'题 {n}  页 {len(out)}  有转录同位 {sum(1 for p in out for q in p["qs"] if q["tB"] is not None)}  '
          f'有tess同位 {sum(1 for p in out for q in p["qs"] if q["sB"])}  跳过 {dict(skip)} → {CAND}', file=sys.stderr)


def page_strips(vol, leaf, n=2):
    doc = fitz.open(RAW / 'pdf' / I.PDF[vol])
    im = Image.open(io.BytesIO(doc.extract_image(doc[leaf].get_images(full=True)[0][0])['image'])).convert('L')
    h = im.height
    out = []
    for k in range(n):
        y0, y1 = max(0, k * h // n - 40), min(h, (k + 1) * h // n + 40)   # 相邻条重叠 40px，行不被切断
        buf = io.BytesIO()
        c = im.crop((0, y0, im.width, y1))
        k_ = 1568 / max(c.size)                     # 预先缩到模型实际处理的尺寸（长边 1568），省 token
        if k_ < 1:
            c = c.resize((round(c.width * k_), round(c.height * k_)), Image.LANCZOS)
        c.save(buf, 'PNG')
        out.append(buf.getvalue())
    return out


def band_image(vol, leaf, ys):
    """各处所在行上下各约 3 行的横条，按页序竖拼成一张（重叠的并起来）。"""
    doc = fitz.open(RAW / 'pdf' / I.PDF[vol])
    im = Image.open(io.BytesIO(doc.extract_image(doc[leaf].get_images(full=True)[0][0])['image'])).convert('L')
    spans = []
    for y in sorted(ys):
        a, b = max(0, y - 220), min(im.height, y + 260)
        if spans and a <= spans[-1][1]:
            spans[-1][1] = b
        else:
            spans.append([a, b])
    parts = [im.crop((0, a, im.width, b)) for a, b in spans]
    h = sum(p.height for p in parts) + 12 * (len(parts) - 1)
    out = Image.new('L', (im.width, h), 255)
    yy = 0
    for p in parts:
        out.paste(p, (0, yy))
        yy += p.height
        if yy < h:
            out.paste(0, (0, yy + 4, im.width, yy + 8))   # 条间黑线
            yy += 12
    k_ = 1568 / max(out.size)
    if k_ < 1:
        out = out.resize((round(out.width * k_), round(out.height * k_)), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, 'PNG')
    return buf.getvalue()


def seam_image(vol, leaf):
    """本页页尾四分之一 + 下一页页首四分之一竖拼（残字在下页页首、锚词在本页页尾的，第 1 轮整页图上找不到）。"""
    doc = fitz.open(RAW / 'pdf' / I.PDF[vol])
    ims = [Image.open(io.BytesIO(doc.extract_image(doc[k].get_images(full=True)[0][0])['image'])).convert('L')
           for k in (leaf, leaf + 1)]
    a = ims[0].crop((0, ims[0].height * 3 // 4, ims[0].width, ims[0].height))
    b = ims[1].crop((0, 0, ims[1].width, ims[1].height // 4))
    out = Image.new('L', (max(a.width, b.width), a.height + b.height + 12), 255)
    out.paste(a, (0, 0))
    out.paste(0, (0, a.height + 4, out.width, a.height + 8))
    out.paste(b, (0, a.height + 12))
    k_ = 1568 / max(out.size)
    if k_ < 1:
        out = out.resize((round(out.width * k_), round(out.height * k_)), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, 'PNG')
    return buf.getvalue()


SEAM = False


def ask(vol, leaf, qs):
    content = []
    if SEAM:
        content.append({'type': 'text', 'text': 'Foot of one page (above the black rule) and the head of the NEXT page '
                                                '(below it); the spot may be at the very top of the next page:'})
        content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                                    'data': base64.b64encode(seam_image(vol, leaf)).decode()}})
    ys = [q.get('y') for q in qs]
    if not SEAM and all(y is not None for y in ys) and sum(1 for _ in set(ys)) <= 3:
        imgs = [band_image(vol, leaf, ys)]
        content.append({'type': 'text', 'text': 'The relevant lines of the page (several bands of the same page, '
                                                'separated by black rules):'})
        content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                                    'data': base64.b64encode(imgs[0]).decode()}})
    for k, png in enumerate(page_strips(vol, leaf) if len(content) == 0 and not SEAM else [], 1):
        content.append({'type': 'text', 'text': f'Strip {k} of 2:'})
        content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                                    'data': base64.b64encode(png).decode()}})
    content.append({'type': 'text', 'text': '\n'.join(
        f'#{n}: ({"footnote" if q["where"] == "note" else "main text"}) «{q["ctx"]}»' for n, q in enumerate(qs, 1))})
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


def qkey(q):
    return (q['lec'], q['ours'], q['ctx'])


def answered():
    got = {}
    for f in sorted(ANS.glob('*.json')) + (sorted((WORK / 'page_check_answers_seam').glob('*.json'))
                                           if ANS.name == 'page_check_answers' else []):
        d = json.loads(f.read_text(encoding='utf-8'))
        for n, q in enumerate(d['qs'], 1):
            got[qkey(q)] = d['ans'].get(str(n), '')
    return got


def run(sample, all_):
    pages = json.loads(CAND.read_text(encoding='utf-8'))
    got = answered()
    todo = [dict(p, qs=[q for q in p['qs'] if qkey(q) not in got]) for p in pages]
    todo = [p for p in todo if p['qs']]
    if not all_:
        random.seed(20261112)
        todo = random.sample(todo, min(sample or 2, len(todo)))
    total, fails = 0.0, 0
    ANS.mkdir(parents=True, exist_ok=True)
    with open(COST, 'a', encoding='utf-8') as fh:
        for n, p in enumerate(todo, 1):
            try:
                res, cost = ask(p['vol'], p['leaf'], p['qs'])
            except Exception as e:                     # noqa: BLE001
                fails += 1
                print(f"v{p['vol']} {p['leaf']:4d} 失败 {e}", file=sys.stderr, flush=True)
                if 'limit' in str(e).lower():
                    sys.exit(42)
                if fails >= 5:
                    sys.exit(3)
                continue
            fails = 0
            total += cost
            ans = {int(m.group(1)): m.group(2) for m in re.finditer(r'^\s*#(\d+):\s*(.*?)\s*$', res, re.M)}
            f = ANS / f"v{p['vol']}_{p['leaf']:04d}.json"
            k = 1
            while f.exists():
                k += 1
                f = ANS / f"v{p['vol']}_{p['leaf']:04d}_{k}.json"
            f.write_text(json.dumps({'raw': res, 'ans': ans, 'qs': p['qs']}, ensure_ascii=False), encoding='utf-8')
            fh.write(f"{p['vol']}\t{p['leaf']}\t{len(p['qs'])}\t{len(ans)}\t{cost:.4f}\n")
            fh.flush()
            print(f"v{p['vol']} {p['leaf']:4d} 问 {len(p['qs']):2d} 答 {len(ans):2d}  ${cost:.4f}  累计 ${total:.2f}  "
                  f"({n}/{len(todo)})", file=sys.stderr, flush=True)


def norm(t):
    return re.sub(r'\s+', ' ', t.translate(str.maketrans('“”‘’', '""\'\''))).strip()


_SR = None


def second_read_has(vol, leaf, x):
    """x 的希腊词是否都在同页看图第二读（foote_greek_read，不给提示照印面读）里出现（比去重音字母）。"""
    global _SR
    if _SR is None:
        import foote_greek_notes as GN
        import foote_greek_read as G
        _SR = ({k: {G.bare(w) for r in v for w in r.split()} for k, v in GN.second_reads().items()}, G)
    sr, G = _SR
    words = re.findall(r'[Ͱ-Ͽἀ-῿]+', x)
    pool = sr[0].get((vol, leaf), set()) if False else _SR[0].get((vol, leaf), set())
    return bool(words) and all(G.bare(w) in pool for w in words)


def vlm_wild_has(vol, leaf, x):
    """x 的每个希腊词都能在同页转录（正文与 [FN:] 行）里找到相合的词：转录读出的字母相同、[?] 处任意 0–3 字母。"""
    import foote_greek_read as G
    import foote_notes_fill as NF
    f = V.VLM / f'v{vol}' / f'{leaf:04d}.txt'
    if not f.exists():
        return False
    toks = [t.strip('.,;:—"\'()*') for t in f.read_text(encoding='utf-8').split()]
    toks = [t for t in toks if re.search(r'[Ͱ-Ͽἀ-῿]', t)]
    words = re.findall(r'[Ͱ-Ͽἀ-῿᾿῾ʼ\']+', x)
    if not words:
        return False
    for w in words:
        bw = G.bare(w)
        if not any((NF.wild(t).match(bw) if '[?]' in t else G.bare(t) == bw) for t in toks):
            return False
    return True


def gate(q, x):
    """模型读法 x 过哪道闸：'T' / 'S' / 'P' / 'G' / ''。"""
    lx = LC.letters(x)
    if re.search(r'[Ͱ-Ͽἀ-῿]', x) and not re.search(r'[A-Za-z]', x) and second_read_has(q['vol'], q['leaf'], x):
        return 'G'                                  # 希腊文：与同页第二读（另一次照印面读）字母相同
    if re.search(r'[Ͱ-Ͽἀ-῿]', x) and vlm_wild_has(q['vol'], q['leaf'], x):
        return 'W'                                  # 希腊文：与同页转录（[?] 作通配）相合
    if q['tB'] is not None and re.sub(r'[\s*]', '', norm(q['tB'])) == re.sub(r'[\s*]', '', norm(x).replace(FNS, P_FN)):
        return 'T'
    if q['tB'] is not None and LC.letters(q['tB']) == lx and lx:
        return 'T'
    if q['sB'] and q['sB'] == lx and lx:
        return 'S'
    o = JUNKC.sub('', q['ours'].replace(A.FN_MARK, ''))
    if LC.letters(o) == lx and re.findall(r'\d', o) == re.findall(r'\d', x):   # 只补标点：字母、数字都不许动（`29(>.`→`296.` 不放）
        return 'P'
    return ''


P_FN = ''


def rebuild(q, x):
    """模型读法 → 改作：注号 ⁽ⁿ⁾ → 哨兵；斜体星号照我们这截两头；两头空白照我们。"""
    o = q['ours']
    core = norm(x).replace(FNS, A.FN_MARK)
    lead = re.match(r'\s*\**', o).group()
    tail = re.search(r'\**\s*$', o).group()
    core = core.strip('*')
    inner = o.strip().strip('*')
    # 我们这截中间的斜体星号（`*rejoiced*—`）模型不判：中间有星号的不自动落
    if '*' in inner:
        return None
    return lead + core + tail


def rules():
    pages = json.loads(CAND.read_text(encoding='utf-8'))
    got = answered()
    rows, out, pend = [], [], []
    texts = {}
    for p in pages:
        for q in p['qs']:
            q = dict(q, vol=p['vol'], leaf=p['leaf'])
            a = got.get(qkey(q))
            if a is None:
                rows.append(('unasked', q['lec'], q['page'], q['ours'], '', ''))
                continue
            if not a.startswith('='):
                rows.append(('?', q['lec'], q['page'], q['ours'], a, ''))
                continue
            x = a[1:].strip()
            g = gate(q, x) if x else ('P' if not LC.letters(JUNKC.sub('', q['ours'])) else '')
            new = rebuild(q, x) if x else ''
            why = ''
            t0 = (A.SRC / f"{q['lec']}.md").read_text(encoding='utf-8')
            if re.search(r'[*†‡§‖¶]', x):
                g, why = '', '注号读成字面符号'          # 模型把注号写成 * ‡（应作 ⁽ⁿ⁾），落进正文会当斜体符
            elif new and new.rstrip().endswith('-'):
                # 行末断词：接后一词成真词才落（`mean- ing`→meaning），否则不落
                m2 = re.match(r'\s+([a-z]+)', t0[q['e']:])
                m1 = re.search(r'([A-Za-z]+)-\s*$', new)
                if m1 and m2 and A._isword((m1.group(1) + m2.group(1)).lower()):
                    new = new.rstrip()[:-1] + m2.group(1)
                    q = dict(q, e=q['e'] + len(m2.group(0)))
                else:
                    g, why = '', '断词接不成'
            if new is None:
                g, why = '', '中间斜体'
            elif x and new.count(A.FN_MARK) != q['ours'].count(A.FN_MARK):
                g, why = '', '注号个数'
            t = texts.setdefault(q['lec'], (A.SRC / f"{q['lec']}.md").read_text(encoding='utf-8'))
            if g:
                pa = t.rfind('\n\n', 0, q['s'])
                pb = t.find('\n\n', q['e'])
                para = t[pa + 2 if pa >= 0 else 0:q['s']] + new + t[q['e']:pb if pb >= 0 else len(t)]
                if len(re.findall(r'(?<!\\)\*', re.sub(r'<!--.*?-->', '', para))) % 2 and \
                        len(re.findall(r'(?<!\\)\*', re.sub(r'<!--.*?-->', '', t[pa + 2 if pa >= 0 else 0:pb if pb >= 0 else len(t)]))) % 2 == 0:
                    g, why = '', '斜体成单'
            rows.append((g or 'pending', q['lec'], q['page'], q['ours'], x, why or f"T={q['tB']!r} S={q['sB']!r}"))
            if not g:
                pend.append((q['lec'], q['page'], q['where'], q['ours'], x, why, q['ctx']))
                continue
            # 开引号：本书写作 `"*And`（引号在前、斜体星在后、后面不空格）
            m3 = re.fullmatch(r'(\s*)\*"\s*', new) or re.fullmatch(r'(\s*)\*"(?=\S)(.*)', new)
            if new.strip() in ('*"', '"', '"*') and re.match(r' [A-Za-z]', t[q['e']:q['e'] + 2]):
                new = new.replace('*"', '"*')
                q = dict(q, e=q['e'] + 1)
            elif re.match(r'\s*\*"[A-Za-z]', new):
                new = new.replace('*"', '"*', 1)
            # 原串带两旁的词，逐词放宽到唯一
            ls, re_ = q['s'], q['e']
            old = t[ls:re_]
            for _ in range(8):
                if t.count(old) == 1:
                    break
                ls = max(t.rfind(' ', 0, max(0, ls - 1)) + 1, t.rfind('\n', 0, max(0, ls - 1)) + 1)
                re_ = min(x_ for x_ in (t.find(' ', re_ + 1), t.find('\n', re_ + 1), len(t)) if x_ >= 0)
                old = t[ls:re_]
            if t.count(old) != 1:
                rows[-1] = ('X-not-unique',) + rows[-1][1:]
                continue
            nw = t[ls:q['s']] + new + t[q['e']:re_]
            if not nw.strip() and not old.strip():
                continue
            nw = re.sub(r' +\n', '\n', re.sub(r'(?<=\S)  +', ' ', nw))
            if nw == old:
                continue
            out.append((q['lec'], old, nw))
    with open(LOG, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['verdict', 'lecture', 'page', 'ours', 'read', 'note'])
        w.writerows(rows)
    RULES.write_text('# lecture\t原串\t改作 —— foote_page_check.py 生成（一页一图，模型读法另有转录/tess/只补标点之一相合）；\\n 表换行\n'
                     + ''.join('\t'.join(x.replace('\n', '\\n') for x in r) + '\n' for r in out), encoding='utf-8')
    with open(PEND, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['lecture', 'page', 'where', 'ours', 'model_read', 'why', 'ctx'])
        w.writerows(pend)
    print(dict(Counter(r[0] for r in rows)), f'规则 {len(out)} → {RULES}；待核 {len(pend)} → {PEND}', file=sys.stderr)


def use_seam():
    """第 2 轮（页缝）：第 1 轮答 ? 的各处，改送本页页尾＋下页页首。答案另存 page_check_answers_seam/。"""
    global SEAM, ANS, CAND
    got = answered()
    pages = json.loads(CAND.read_text(encoding='utf-8'))
    keep = [dict(p, qs=[q for q in p['qs'] if got.get(qkey(q), '').strip() == '?']) for p in pages]
    keep = [p for p in keep if p['qs']]
    SEAM = True
    ANS = WORK / 'page_check_answers_seam'
    CAND = WORK / 'page_check_candidates_seam.json'
    CAND.write_text(json.dumps(keep, ensure_ascii=False, indent=0), encoding='utf-8')
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--collect', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--rules', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--seam', action='store_true')
    a = ap.parse_args()
    if a.collect:
        collect()
    elif a.run and a.seam:
        use_seam()
        run(a.sample, a.all)
    elif a.run:
        run(a.sample, a.all)
    elif a.rules:
        rules()
    elif a.apply and RULES.exists():
        I.apply_multiline(RULES)


if __name__ == '__main__':
    main()
