#!/usr/bin/env python3
"""福特《路加福音讲义》第 ③ 层·看图定夺：单证人的残留（只有整页转录读得不同）按页一次看图全部判完。

前面各层只收「转录与 tesseract 两家同位一致」的；剩下的是 tesseract 与我们读错得一样（`hy` `hut` `Master s`）、
或 tesseract 没读出的——只有转录一个证人，按规矩须看图。用户 2026-11-10 定：**一页图只看一次**，这页上所有待判处
一起判，不许一处看一次。

做法：链条终态上逐页三条字流对齐（同 foote_punct.page_pairs，已 trim），收两类待判：
  词：我们与转录同位不同（至少一侧邻词三家相等，防错位）
  缝：两侧词与转录相等、缝里标点不同（转录与 tesseract 不一致的、或被前面守卫挡下的）
每处在 tess_grc 逐词框里找到所在行，裁 PDF 内嵌原图（原生分辨率，不放大）整行条；一页的所有条＋问题一次送去，
每问给 A（我们）/ B（转录）两读，答 A、B 或照印面写。**只在答 B（＝转录）时落**：转录与看图两次读印面一致；
答 A 不动，答别的记下待看。

    python3 scripts/foote_image_check.py --collect          # 收待判 → foote_raw/luke/imgcheck/candidates.json
    python3 scripts/foote_image_check.py --run --sample 5   # 抽几页试
    python3 scripts/foote_image_check.py --run --all        # 一路串行；额度用尽退出码 42，已判的页跳过
    python3 scripts/foote_image_check.py --rules            # 答案 → image_fixes.tsv（整串、本讲唯一）
    python3 scripts/foote_image_check.py --apply            # 链条最末（foote_glyphs.py --apply 之后）
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
import foote_glyphs as G  # noqa: E402
import foote_punct as P  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402

RAW = A.RAW
WORK = RAW / 'imgcheck'
CAND = WORK / 'candidates.json'
ANS = WORK / 'answers'
# 第二轮（11-10 补上页首那截覆盖后重收候选）：问过的按内容认答案，只问新的；第二轮答案连题目一起存
CAND1 = WORK / 'candidates_r1.json'
ANS2 = WORK / 'answers2'
RULES = RAW / 'image_fixes.tsv'
LOG = A.ROOT / 'logs' / 'foote_image_check.tsv'
COST = A.ROOT / 'logs' / 'foote_image_check_cost.tsv'
PDF = {1: 'vol1_ed2_lecturesongospe03footgoog.pdf', 2: 'vol2_ed2_lecturesongospe02footgoog.pdf',
       3: 'vol3_ed2_lecturesongospe00footgoog.pdf'}
NORMW = lambda w: w.translate(G.LIG).replace('’', "'").lower()


def tsv_words(vol, leaf):
    f = RAW / 'tess_grc' / f'v{vol}' / f'{leaf:04d}.tsv'
    out = []
    if not f.exists():
        return out
    for r in list(csv.reader(open(f, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))[1:]:
        if len(r) >= 12 and r[0] == '5' and r[11].strip():
            w = re.sub(r'[^A-Za-zÀ-ÿ]', '', r[11]).lower()
            if w:
                out.append((w, int(r[6]), int(r[7]), int(r[8]), int(r[9]), (r[2], r[3], r[4])))
    return out


def collect():
    V.EDGE = False
    pages = []
    nword = ngap = nspan = nloc = 0
    for vol, leaf, texts, ours, vs, _vt, ts, tt in P.page_pairs():
        vt = [(m.start(), m.end(), m.group(0)) for m in G.VW.finditer(vs)]
        ow = [t for *_, t in ours]
        vw = [NORMW(x[2]) for x in vt]
        vm = V.align_map(ow, vw)
        eq = lambda i: i in vm and vw[vm[i]] == NORMW(ow[i])
        qs = []
        for i, (lec, s, e, o) in enumerate(ours):
            if i not in vm or eq(i):
                continue
            v = vt[vm[i]][2]
            if v == V.SENT or not (eq(i - 1) or eq(i + 1)):
                continue
            # 跨页断词：转录这页只有 `de`/`fence`，我们是整词 `defence`——不是错
            if len(v) < len(o) and (NORMW(o).startswith(NORMW(v)) or NORMW(o).endswith(NORMW(v))):
                continue
            if i > 0 and ours[i - 1][0] == lec and texts[lec][ours[i - 1][2]:s].count('<'):
                pass
            qs.append({'kind': 'word', 'lec': lec, 's': s, 'e': e, 'i': i, 'ours': o, 'vlm': v.replace('’', "'")})
            nword += 1
        for i in range(len(ours) - 1):
            lec, s, e, o = ours[i]
            lec2, s2, e2, o2 = ours[i + 1]
            if lec2 != lec or not (eq(i) and eq(i + 1)) or vm[i + 1] != vm[i] + 1:
                continue
            gap = texts[lec][e:s2]
            vg = vs[vt[vm[i]][1]:vt[vm[i + 1]][0]]
            if '<' in gap or '\n\n' in gap or P.FN in vg or V.SENT in vg or re.search(r'[A-Za-z0-9]', gap + vg):
                continue
            oc, vc = P.core(gap), P.core(vg)
            if oc == vc or not set(vc) <= P.OK:
                continue
            qs.append({'kind': 'gap', 'lec': lec, 's': e, 'e': s2, 'i': i, 'ours': gap, 'vlm': vc,
                       'left': o, 'right': o2, 'oc': oc.replace(P.ESC, '*'),
                       'og': re.sub(r'\s+', ' ', gap.replace('*', '')), 'vg': re.sub(r'\s+', ' ', vg.replace('*', '')).translate(P.NORM)})
            ngap += 1
        # 跨: 词数对不上的一小截（`Master s`↔`Master's`、`hoi/t`↔`how`、`tons`↔`to us`），两头各一词相同
        sm = SequenceMatcher(None, [NORMW(x) for x in ow], vw, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if (op != 'replace' or not (1 <= i2 - i1 <= 3 and 1 <= j2 - j1 <= 3) or i2 - i1 == j2 - j1
                    or i1 == 0 or i2 >= len(ow) or NORMW(ow[i1 - 1]) != vw[j1 - 1] or NORMW(ow[i2]) != vw[j2]):
                continue
            lec, s0 = ours[i1][0], ours[i1][1]
            e0 = ours[i2 - 1][2]
            if any(ours[k][0] != lec for k in range(i1, i2)) or any(x[2] == V.SENT for x in vt[j1:j2]):
                continue
            o = texts[lec][s0:e0]
            v = re.sub(r'\s+', ' ', vs[vt[j1][0]:vt[j2 - 1][1]].replace('’', "'"))
            if re.search(r'[*<\n]', o) or not re.fullmatch(r"[A-Za-zæœÆŒ' ,;:.\-]+", v):
                continue
            qs.append({'kind': 'span', 'lec': lec, 's': s0, 'e': e0, 'i': i1, 'ours': o, 'vlm': v})
            nspan += 1
        if not qs:
            continue
        # 行定位：我们的词 ↔ tess_grc 逐词框
        tw = tsv_words(vol, leaf)
        tm = {}
        sm = SequenceMatcher(None, [NORMW(x) for x in ow], [x[0] for x in tw], autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'equal' or (op == 'replace' and i2 - i1 == j2 - j1):
                for k in range(i2 - i1):
                    tm[i1 + k] = j1 + k
        for q in qs:
            idx = [q['i']] + ([q['i'] + 1] if q['kind'] == 'gap' else [])
            boxes = []
            for k in idx:
                j = next((tm[k + d] for d in (0, -1, 1, -2, 2) if k + d in tm), None)
                if j is not None:
                    key = tw[j][5]
                    line = [x for x in tw if x[5] == key]
                    boxes.append((min(x[1] for x in line), min(x[2] for x in line),
                                  max(x[1] + x[3] for x in line), max(x[2] + x[4] for x in line)))
            if boxes:
                q['box'] = [min(b[0] for b in boxes), min(b[1] for b in boxes),
                            max(b[2] for b in boxes), max(b[3] for b in boxes)]
                nloc += 1
            text = texts[q['lec']]
            q['ctx'] = (text[max(0, q['s'] - 60):q['s']] + '⟦' + text[q['s']:q['e']] + '⟧'
                        + text[q['e']:q['e'] + 60]).replace('\n', ' ')
            q['lec'] = f"{q['lec']:03d}"
        pages.append({'vol': vol, 'leaf': leaf, 'qs': [q for q in qs if 'box' in q]})
    pages = [p for p in pages if p['qs']]
    WORK.mkdir(parents=True, exist_ok=True)
    CAND.write_text(json.dumps(pages, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'词 {nword}  缝 {ngap}  跨 {nspan}  定位到行 {nloc}  页 {len(pages)}  → {CAND}', file=sys.stderr)


def strips(vol, leaf, qs):
    """一页裁成若干行条：同一行（或相交）的问题合用一条。返回 [(png, [问题号])]。"""
    doc = fitz.open(RAW / 'pdf' / PDF[vol])
    im = Image.open(io.BytesIO(doc.extract_image(doc[leaf].get_images(full=True)[0][0])['image'])).convert('L')
    groups = []
    for n, q in enumerate(qs, 1):
        x0, y0, x1, y1 = q['box']
        for g in groups:
            if not (y1 < g['y0'] or y0 > g['y1']):
                g['y0'], g['y1'] = min(g['y0'], y0), max(g['y1'], y1)
                g['x0'], g['x1'] = min(g['x0'], x0), max(g['x1'], x1)
                g['ns'].append(n)
                break
        else:
            groups.append({'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1, 'ns': [n]})
    out = []
    for g in sorted(groups, key=lambda g: g['y0']):
        box = (max(0, g['x0'] - 60), max(0, g['y0'] - 28), min(im.width, g['x1'] + 60), min(im.height, g['y1'] + 28))
        buf = io.BytesIO()
        im.crop(box).save(buf, 'PNG')
        out.append((buf.getvalue(), g['ns']))
    return out


SYSTEM = (
    'You are proof-reading a digitised 19th-century printed book against images of its printed lines. '
    'For each numbered question you get a line strip (native scan resolution) and a disputed spot shown inside ⟦ ⟧ '
    'in its context, with two candidate readings A and B. Look at the strip and decide what is actually printed '
    'at that spot, character for character: letters, apostrophes, ligatures (æ œ), hyphens, and every punctuation '
    'mark (comma vs full stop, colon vs semicolon, opening/closing quotation marks). Italics do not matter. '
    'Answer each question on its own line exactly as  #n: A   or  #n: B   or, if neither matches the print,  '
    '#n: = <the printed text of the spot>  . If the spot cannot be made out, answer  #n: ?  . '
    'Output only the answer lines.'
)


def show(q):
    if q['kind'] in ('word', 'span'):
        return q['ours'], q['vlm']
    # 按各自原样的空白显示（开引号在空白后、收引号在空白前；只给核心字符会把 `The “piece` 显示成 `The" piece`）
    return q['left'] + q['og'] + q['right'], q['left'] + q['vg'] + q['right']


def verdict(q, a):
    """答案 → A / B / other。`= 照印面` 的答案去空白、弯引号直化后与 A 或 B 相同，按 A / B 算；词只比字母和撇号。"""
    if a in ('A', 'B'):
        return a
    if not a.startswith('='):
        return 'other'
    x = a[1:].strip()
    if q['kind'] in ('word', 'span'):
        f = lambda t: re.sub(r"[^A-Za-z0-9æœÆŒ']", '', t.replace('’', "'"))   # 数字也比（`= XVI. 1` ≠ `XVI`）
    else:
        f = lambda t: re.sub(r'\s', '', t.translate(P.NORM))
    sa, sb = show(q)
    return 'B' if f(x) == f(sb) else 'A' if f(x) == f(sa) else 'other'


_CORPUS = None


def _corpus_has(w):
    global _CORPUS
    if _CORPUS is None:
        _CORPUS = Counter(re.findall(r"[A-Za-z]+", ''.join(f.read_text(encoding='utf-8')
                                                          for f in sorted(A.SRC.glob('*.md')))))
    return _CORPUS[w] >= 2          # 自己那处是残字不算；别处至少再见一次（取 ≥2 防候选本身已被改过）


_ALL = None


def _hyph_seen(w):
    global _ALL
    if _ALL is None:
        _ALL = ''.join(f.read_text(encoding='utf-8') for f in sorted(A.SRC.glob('*.md')))
    return len(re.findall(r'(?<![A-Za-z-])' + re.escape(w) + r'(?![A-Za-z-])', _ALL, re.I)) > 1


def hold(q, a):
    """B 答案里不落的两类（全书 2045 个 B 逐类看过）：模型会照着转录本的错字答 B。
      词：转录同位词不是真词（`evidences`→`evidenees`、`Then`→`Theu`，44 处里绝大多数是转录错）——
          除非答案是模型自己写出的 `= …`、或转录带 æ/œ（Peræa、Æneas）、或我们这边本是残字而转录带撇号（toss'd）。
      空：把我们的逗号/无标点改成句末点、而右边紧接小写词（`deny himself. and take up his cross`）——罗马数字除外（Isa. vii）。"""
    if q['kind'] == 'span':
        # 连字符复合词（`stumbling-stone`↔`stumblingstone`）连不连归 K 层按全书语料定，这里不改
        m = re.fullmatch(r"([A-Za-z]+)-\s*([A-Za-z]+)", q['ours'])
        if m and A._isword(m.group(1)) and A._isword(m.group(2)) and '-' not in q['vlm']:
            # 同 K 层：并成的词全书别处见过、连字符形一次没有（`govern-ment`、`ex-amine`）才放
            return not (_corpus_has(m.group(1) + m.group(2)) and not _hyph_seen(m.group(1) + '-' + m.group(2)))
        return not a.startswith('=') and not all(A._isword(w.strip("'")) or re.search('[æœÆŒ]', w)
                                                 for w in re.findall(r"[A-Za-zæœÆŒ']+", q['vlm']))
    if q['kind'] == 'word':
        v = q['vlm']
        if A._isword(v.strip("'")) or a.startswith('=') or re.search('[æœÆŒ]', v):
            return False
        if A._isword(q['ours'].strip("'")):
            return True
        # 我们本是残字：转录带撇号（toss'd）、或转录那词全书别处出现过（hefell→befell、Floras→Florus）就落
        return not ("'" in v.strip("'") or _corpus_has(v))
    core = lambda t: re.sub(r'[\s"\'*“”‘’]', '', t)
    right = re.sub(r'^[\s"\'*“”‘’(]+', '', q['right'])
    return (re.search(r'[.?!]$', core(q['vg'])) is not None and not re.search(r'[.?!]$', core(q['og']))
            and right[:1].islower() and not re.match(r'[ivxlc]+\b', right))


def ask(vol, leaf, qs):
    content = []
    for k, (png, ns) in enumerate(strips(vol, leaf, qs), 1):
        content.append({'type': 'text', 'text': f'Strip {k} (questions {", ".join("#%d" % n for n in ns)}):'})
        content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                                    'data': base64.b64encode(png).decode()}})
    lines = []
    for n, q in enumerate(qs, 1):
        a, b = show(q)
        if q.get('swap'):
            a, b = b, a
        lines.append(f'#{n}: context «{q["ctx"]}»\n    A = «{a}»\n    B = «{b}»')
    content.append({'type': 'text', 'text': '\n'.join(lines)})
    msg = {'type': 'user', 'message': {'role': 'user', 'content': content}}
    cmd = ['claude', '-p', '--safe-mode', '--strict-mcp-config', '--disallowedTools', '*',
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
            return str(o.get('result') or ''), float(o.get('total_cost_usd') or 0)
    raise RuntimeError('no result: ' + r.stderr[-200:])


def qkey(q):
    return (q['lec'], q['kind'], q['ours'], q['vlm'], q['ctx'])


def answered():
    """问过的题 → 答案：第一轮（candidates_r1.json 的题号对 answers/）＋第二轮（answers2/ 自带题目）。"""
    got = {}
    for p in json.loads(CAND1.read_text(encoding='utf-8')) if CAND1.exists() else []:
        f = ANS / f"v{p['vol']}" / f"{p['leaf']:04d}.json"
        if f.exists():
            ans = json.loads(f.read_text(encoding='utf-8'))['ans']
            for n, q in enumerate(p['qs'], 1):
                got.setdefault(qkey(q), ans.get(str(n), ''))
    for f in sorted(ANS2.glob('v*/*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        for n, q in enumerate(d['qs'], 1):
            a = d['ans'].get(str(n), '')
            if q.get('swap') and a in ('A', 'B'):
                a = 'B' if a == 'A' else 'A'       # 问时 A/B 对调过（第一轮 B 恒为转录、模型偏答 B）
            got[qkey(q)] = a
    return got


def run(sample, all_):
    pages = json.loads(CAND.read_text(encoding='utf-8'))
    got = answered()
    todo = []
    for p in pages:
        qs = [q for q in p['qs'] if qkey(q) not in got]
        rnd = random.Random(f"{p['vol']}-{p['leaf']}")
        for q in qs:
            q['swap'] = rnd.random() < 0.5
        if qs:
            todo.append(dict(p, qs=qs))
    if not all_:
        random.seed(20261110)
        todo = random.sample(todo, min(sample or 5, len(todo)))
    total, fails = 0.0, 0
    with open(COST, 'a', encoding='utf-8') as fh:
        for n, p in enumerate(todo, 1):
            try:
                res, cost = ask(p['vol'], p['leaf'], p['qs'])
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
            ans = {}
            for m in re.finditer(r'^\s*#(\d+):\s*(.*?)\s*$', res, re.M):
                ans[int(m.group(1))] = m.group(2)
            d = ANS2 / f"v{p['vol']}"
            d.mkdir(parents=True, exist_ok=True)
            k = 1
            while (d / f"{p['leaf']:04d}_{k}.json").exists():
                k += 1
            (d / f"{p['leaf']:04d}_{k}.json").write_text(
                json.dumps({'raw': res, 'ans': ans, 'qs': p['qs']}, ensure_ascii=False), encoding='utf-8')
            fh.write(f"{p['vol']}\t{p['leaf']}\t{len(p['qs'])}\t{len(ans)}\t{cost:.4f}\n")
            fh.flush()
            print(f"v{p['vol']} {p['leaf']:4d} 问 {len(p['qs']):2d} 答 {len(ans):2d}  ${cost:.4f}  累计 ${total:.2f}  "
                  f"({n}/{len(todo)})", file=sys.stderr, flush=True)


FNM = '\ue010'
_SRC = {}


def src_text(lec):
    if lec not in _SRC:
        _SRC[lec] = (A.SRC / f'{lec}.md').read_text(encoding='utf-8')
    return _SRC[lec]


def _span(text, s, e, rep):
    """G.unique_span，再加一条：原串不得是改作的一截（`tout`→`stout`、`Jew`→`Jews`），否则第二遍又落一次；往两头各扩一词再试。"""
    for _ in range(6):
        r = G.unique_span(text, s, e, rep)
        if not r or r[0] not in r[1]:
            return r
        a = max(text.rfind(' ', 0, max(s - 1, 0)), 0)
        b = text.find(' ', e + 1)
        b = len(text) if b < 0 else b
        if '\n' in text[a:b]:
            return None
        rep, s, e = text[a:s] + rep + text[e:b], a, b
    return None


def rules():
    pages = json.loads(CAND.read_text(encoding='utf-8'))
    got = answered()
    edits, rows = [], []
    for p in pages:
        for q in p['qs']:
            a = got.get(qkey(q))
            if a is None:
                rows.append(('unasked', q['lec'], p['vol'], p['leaf'], q['kind'], q['ours'], q['vlm'], '', q['ctx']))
                continue
            if src_text(q['lec'])[q['s']:q['e']] != q['ours']:
                # 候选是在别的底本状态上收的（位置错了会落成切过词的串）：重跑 --collect
                rows.append(('stale', q['lec'], p['vol'], p['leaf'], q['kind'], q['ours'], q['vlm'], a, q['ctx']))
                continue
            v = verdict(q, a)
            if v == 'B' and hold(q, a):
                v = 'B-hold'
            rows.append((v, q['lec'], p['vol'], p['leaf'], q['kind'], q['ours'], q['vlm'], a, q['ctx']))
            if v != 'B':
                continue
            if q['kind'] in ('word', 'span'):
                edits.append((q['lec'], q['s'], q['e'], q['vlm']))
            else:
                new = P.rebuild(q['ours'], q['vlm'])
                # 开斜体星号后多一个空白（`The * piece`）：补的开引号要在星号前、星号紧贴下一词（`The "*piece`）
                new = re.sub(r'\*\s+(["\'])$', r'\1*', new)
                edits.append((q['lec'], q['s'], q['e'], new))
    # 注号 U+E010 只在夹在字母中间时（`com\ue010 munion`，行末连字符读花）随残字去掉；
    # 词间的注号（`Luke\ue010* As`）问题里没显示、答案与转录都不管它——留着，放在改好的收尾标点之后
    fixed = []
    for lec, s, e, rep in edits:
        o = src_text(lec)[s:e]
        k = o.count(FNM) - rep.count(FNM) - len(re.findall(r'[A-Za-z]' + FNM + r'[\s.|^]*[A-Za-z]', o))
        if k > 0:
            m = None if o[:1].isalpha() else re.match(r'^\s*[.,;:!?)\]—"\'”’]*', rep)
            at = m.end() if m else len(rep.rstrip())
            rep = rep[:at] + FNM * k + rep[at:]
        fixed.append((lec, s, e, rep))
    edits = fixed
    # 相邻的落点（空 ` *''^` 紧挨着词 `ha`）先并成一处：各自扩成唯一串会互相罩住，第二遍就不再是不动点
    src = {}
    merged = []
    for lec, s, e, rep in sorted(set(edits)):
        text = src.setdefault(lec, (A.SRC / f'{lec}.md').read_text(encoding='utf-8'))
        if merged and merged[-1][0] == lec and s <= merged[-1][2] + 40 and '\n' not in text[merged[-1][2]:s]:
            pl, ps, pe, pr = merged[-1]
            if s < pe:
                continue
            merged[-1] = (lec, ps, e, pr + text[pe:s] + rep)
        else:
            merged.append((lec, s, e, rep))
    texts, out = {}, []
    for lec, s, e, rep in sorted(merged, key=lambda x: (x[0], -x[1])):
        text = texts.setdefault(lec, src[lec])
        r = _span(text, s, e, rep)
        if r:
            out.append((lec, r[0], r[1]))
            texts[lec] = text[:s] + rep + text[e:]
    # 模拟连落两遍：第二遍还能落上（原串又出现）或两头都找不到的，不收
    def _pass(tx, rs):
        moved = []
        for i, (lec, o, n) in enumerate(rs):
            c = tx[lec].count(o)
            if c == 1:
                tx[lec] = tx[lec].replace(o, n)
                moved.append(i)
            elif not (c == 0 and n in tx[lec]):
                moved.append(i)
        return moved
    tx = dict(src)
    _pass(tx, out)
    badi = set(_pass(tx, out))
    for i in sorted(badi):
        rows.append(('X', out[i][0], '', '', 'span', out[i][1], out[i][2], 'not-idempotent', ''))
    out = [r for i, r in enumerate(out) if i not in badi]
    with open(LOG, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['verdict', 'lecture', 'vol', 'leaf', 'kind', 'ours', 'vlm', 'answer', 'ctx'])
        w.writerows(rows)
    RULES.write_text('# lecture\t原串(逐字)\t改作 —— foote_image_check.py 生成（看图答 B＝转录）\n'
                     + ''.join('\t'.join(r).replace('\n', '\\n') + '\n' for r in out), encoding='utf-8')
    from collections import Counter
    print(dict(Counter(r[0] for r in rows)), f'规则 {len(out)} → {RULES}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--collect', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--rules', action='store_true')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    if a.collect:
        collect()
    elif a.run:
        run(a.sample, a.all)
    elif a.rules:
        rules()
    elif a.apply:
        A.apply_spans(RULES)


if __name__ == '__main__':
    main()
