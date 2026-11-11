#!/usr/bin/env python3
"""加尔文《撒母耳记上讲章》拉丁文本抽取：CO 29 / 30 扫描件的文字层 → calvin_sermons_raw/1samuel/units.json

    python3 scripts/extract_calvin_1sam.py

底本：Calvini Opera（Corpus Reformatorum 57–58）第 29 卷（1885）第 131–384 页、第 30 卷（1886）第 15–417 页，
日内瓦大学开放档案 unige:650 的 PDF（bf_433x_57.pdf / bf_433x_58.pdf）。PDF 自带 OCR 文字层，字体分正体/斜体，
本脚本以它为主文本；第二证人（tesseract）的比对另由 repair 步骤做，这里只做版面还原。

版面：每页两栏；页顶是栏码（全集按栏编号，左右各一）+ 栏眉；页底有书帖签名（「16」「41*」）与「Calvini opera. Vol. XXIX.」；
编者脚注字号 9.0，以 *) 或 •) 起头，排在页底。讲章以 13.9 号字「HOMILIA …」起头，下接居中的「CAP. …」，
再接斜体的所讲经文（节号正体），然后才是缩进起段的正文。

产物与约伯记/申命记讲章同构（publish_calvin_sermons.py 直接吃）：
  front: [Prolegomena]，sermons: [{num, chapter, chapter2, head, md, cols}]，gaps: {}，merged: {}
正文 markdown：斜体 *…*，栏码锚点 <span class="cs-pb" id="cNNN" data-p="NNN"></span>，经文框 <div class="cs-text">，
编者脚注 → 正文 <sup class="cs-edn">*</sup> + 篇末 .cs-ednote。
"""
import collections
import difflib
import json
import re
import statistics
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repair_calvin_1sam import WORD, Repairer  # noqa: E402

NO_REPAIR = '--raw' in sys.argv
REPAIR_STATS = {}
REP = None
STAR_LOG = []

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'calvin_sermons_raw' / '1samuel'
SINGLE_COL = {('29', 131), ('29', 132)}       # 全集编者导言通栏排
VOL_START = {'29': 237, '30': 5}
VOLS = [('29', RAW / 'src' / 'co29.pdf', 131, 382), ('30', RAW / 'src' / 'co30.pdf', 15, 417)]

ROMAN = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
ORD = {'PRIMA': 1, 'SECUNDA': 2, 'TERTIA': 3, 'QUARTA': 4, 'QUINTA': 5, 'SEXTA': 6, 'SEPTIMA': 7,
       'OCTAVA': 8, 'NONA': 9, 'DECIMA': 10}


def roman(s):
    s = s.upper().replace('O', 'C').replace('Y', 'V').replace('G', 'C').replace('Í', 'I').replace('L', 'L')
    s = re.sub(r'[^IVXLC]', '', s)
    if not s:
        return None
    v = 0
    for i, ch in enumerate(s):
        n = ROMAN[ch]
        v += -n if i + 1 < len(s) and ROMAN[s[i + 1]] > n else n
    return v


# ───────────────────────── 版面：一页 → 行 ─────────────────────────

def page_rows(page, single=False):
    """一页的行：[{col, y, x0, x1, size, segs:[(text, italic)], text}]，同栏同基线的碎片合成一行。"""
    lines = [l for b in page.get_text('rawdict')['blocks'] for l in b.get('lines', [])]
    if not lines:
        return [], None
    split = page.rect.width + 1 if single else gutter_chars(lines, page.rect.width)   # 导言两页通栏
    # 文字层偶有一「行」横跨两栏（左右两栏的字被连成一行）：按字符中心在栏界处切开
    segs = []
    for l in lines:
        pieces = {}
        for sp in l['spans']:
            for ch in sp['chars']:
                cx = (ch['bbox'][0] + ch['bbox'][2]) / 2
                if ch['c'] in 'I|/' and abs(cx - split) < 4:      # 栏间竖线读成的 I / |
                    continue
                side = 1 if cx < split else 2
                pc = pieces.setdefault(side, dict(spans=[], box=None))
                if ch['c'].strip():                       # 行框只按可见字符算（行首空格会把右栏行拉过栏界）
                    bx = pc['box'] or list(ch['bbox'])
                    bx[0], bx[1] = min(bx[0], ch['bbox'][0]), min(bx[1], ch['bbox'][1])
                    bx[2], bx[3] = max(bx[2], ch['bbox'][2]), max(bx[3], ch['bbox'][3])
                    pc['box'] = bx
                if pc['spans'] and pc['spans'][-1]['font'] == sp['font'] and pc['spans'][-1]['size'] == sp['size']:
                    pc['spans'][-1]['text'] += ch['c']
                else:
                    pc['spans'].append(dict(text=ch['c'], font=sp['font'], size=sp['size']))
        for side, pc in sorted(pieces.items()):
            sp = [x for x in pc['spans'] if x['text']]
            if sp and pc['box'] and ''.join(x['text'] for x in sp).strip():
                segs.append(dict(bbox=tuple(pc['box']), spans=sp, side=side))
    # 仍横跨栏界的（字符框不可信的几行），文字里夹着栏间竖线读成的「 I 」「 / 」：在那里切开
    fixed = []
    for sg in segs:
        x0, y0, x1, y1 = sg['bbox']
        txt = ''.join(x['text'] for x in sg['spans'])
        m = None
        if x0 < split - 20 and x1 > split + 20:
            ms = list(re.finditer(r' [I/|] ', txt))
            if ms:
                m = min(ms, key=lambda q: abs(q.start() - len(txt) / 2))
        if not m:
            fixed.append(sg)
            continue
        left, right, pos = [], [], 0
        for sp in sg['spans']:
            a, b = pos, pos + len(sp['text'])
            if b <= m.start():
                left.append(sp)
            elif a >= m.end():
                right.append(sp)
            else:
                if m.start() > a:
                    left.append(dict(sp, text=sp['text'][:m.start() - a]))
                if b > m.end():
                    right.append(dict(sp, text=sp['text'][m.end() - a:]))
            pos = b
        fixed.append(dict(bbox=(x0, y0, split - 2, y1), spans=left, side=1))
        fixed.append(dict(bbox=(split + 2, y0, x1, y1), spans=right, side=2))
    segs = fixed
    rows = []
    for s in sorted(segs, key=lambda s: (s['bbox'][1], s['bbox'][0])):
        x0, y0, x1, y1 = s['bbox']
        col = s['side']
        for r in rows:
            sz = max(sp['size'] for sp in s['spans'])
            if r['col'] == col and abs(r['y'] - y0) < 3 and abs(r['sz0'] - sz) < 1.5:
                r['parts'].append(s)
                r['x1'] = max(r['x1'], x1)
                r['x0'] = min(r['x0'], x0)
                break
        else:
            rows.append(dict(col=col, y=y0, x0=x0, x1=x1, parts=[s], sz0=max(sp['size'] for sp in s['spans'])))
    for r in rows:
        r['parts'].sort(key=lambda s: s['bbox'][0])
        sg = []
        for i, p in enumerate(r['parts']):
            for j, sp in enumerate(p['spans']):
                t = sp['text']
                if i > 0 and j == 0 and sg and not sg[-1][0].endswith(' ') and not t.startswith(' '):
                    t = ' ' + t
                sg.append((t, 'Italic' in sp['font'], sp['size']))
        r['segs'] = [(t, it) for t, it, _ in sg]
        r['size'] = max(sz for t, _, sz in sg if t.strip()) if any(t.strip() for t, _, _ in sg) else 0
        r['minsize'] = min(sz for t, _, sz in sg if t.strip()) if any(t.strip() for t, _, _ in sg) else 0
        r['text'] = ''.join(t for t, _ in r['segs']).strip()
        del r['parts']
    rows.sort(key=lambda r: (r['col'], r['y']))
    return rows, split


def gutter(boxes, w):
    """栏间空当：页面中部跨过它的行最少的那条竖线（右栏行首有时在页宽一半以左，不能拿 w/2 硬切）。"""
    best = []
    for x in range(int(w * 0.40), int(w * 0.60)):
        n = sum(1 for x0, y0, x1, y1 in boxes if x0 < x - 1 and x1 > x + 1)
        best.append((n, x))
    m = min(n for n, _ in best)
    xs = [x for n, x in best if n == m]
    return (xs[0] + xs[-1]) / 2 if xs[-1] - xs[0] < 60 else xs[len(xs) // 2]


CAP_RE = re.compile(r'^\s*[CGO][AÁ][PRB]\.?\s*([IVXLCOY1l ]{1,10})\.?\s*$', re.I)
def gutter_chars(lines, w):
    """栏界：页面中部可见字符覆盖最少的那段空当的中点（比按行框算稳：行框会被行首空格、跨栏误连的行撑过栏界）。"""
    cov = collections.Counter()
    for l in lines:
        for sp in l['spans']:
            for ch in sp['chars']:
                if ch['c'].strip():
                    for x in range(int(ch['bbox'][0]), int(ch['bbox'][2]) + 1):
                        cov[x] += 1
    lo, hi = int(w * 0.40), int(w * 0.60)
    m = min(cov[x] for x in range(lo, hi))
    runs, cur = [], []
    for x in range(lo, hi):
        if cov[x] <= m + 1:
            cur.append(x)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    best = max(runs, key=len)
    return (best[0] + best[-1]) / 2


HEAD_RE = re.compile(r'HOMI|SAMUEL|LIB\.|CAP', re.I)


def classify_page(rows):
    """切出栏眉、页脚、编者脚注；返回 (栏码[左,右], 正文行, 脚注行)。"""
    if not rows:
        return [None, None], [], []
    # 页顶噪点（如第 30 卷 404 页栏眉上方一个孤立的「4」）：短碎片且离下一行十几点以上的，不算页顶
    srt = sorted(rows, key=lambda r: r['y'])
    while len(srt) > 1 and len(srt[0]['text']) <= 3 and srt[1]['y'] - srt[0]['y'] > 10 and srt[0]['y'] < 60:
        srt = srt[1:]
    noise = {id(r) for r in rows} - {id(r) for r in srt}
    rows = srt
    top = min(r['y'] for r in rows)
    cols = [None, None]
    body, notes = [], []
    head_y = None
    toprows = [r for r in rows if r['y'] < top + 5]
    # 栏眉：「255 HOMILIA II. 256」，HOMILIA 常读花（HOM / HOHIL / HUMILIA / flOMILIA），以栏码数字打头或收尾即认
    if toprows and top < 75 and any(HEAD_RE.search(r['text']) or re.match(r'^\W{0,2}\d{1,3}\b', r['text'])
                                    or re.search(r'\b\d{1,3}\W{0,2}$', r['text']) for r in toprows):
        head_y = top
        nums = []
        for r in sorted(toprows, key=lambda r: r['x0']):
            nums += [int(n) for n in re.findall(r'\b(\d{1,3})\b', r['text'])]
        if len(nums) >= 2:
            cols = [nums[0], nums[-1]]        # 只有一个数读得出时不猜左右，交给顺序校验
    for r in rows:
        if head_y is not None and r['y'] < head_y + 5:
            continue
        t = r['text']
        if re.match(r'^\s*C\w{2,6}\s*opera\W{0,3}\s*Vo', t, re.I):          # 页脚「Calvini opera. Vol. XXIX.」（读花作 Cahmi 等）
            continue
        if r['y'] > 640 and re.fullmatch(r'[\d\s*\.]{1,6}', t):          # 书帖签名「16」「41*」
            continue
        if r['minsize'] and r['size'] <= 9.2 and r['y'] > 560:
            notes.append(r)
            continue
        body.append(r)
    return cols, body, notes


# ───────────────────────── 行 → 讲章 ─────────────────────────

def esc(t):
    return t.replace('*', '&#42;').replace('|', '&#124;')        # 「|」是原书书名的换行记号，不能让 kramdown 当表格


def render(tokens):
    """[(text, italic) | ('\x00A', n)] → markdown；斜体合并，星号转义，锚点照放。"""
    out = []
    cur_it = False
    buf = []

    def flush():
        nonlocal buf
        s = ''.join(buf)
        buf = []
        if not s:
            return
        if cur_it and s.strip():
            lead = s[:len(s) - len(s.lstrip())]
            trail = s[len(s.rstrip()):]
            out.append(f'{lead}*{s.strip()}*{trail}')
        else:
            out.append(s)

    for t, it in tokens:
        if t == '\x00A':
            flush()
            out.append(f'<span class="cs-pb" id="c{it}" data-p="{it}"></span>')
            continue
        if t == '\x00N':
            flush()
            out.append('<sup class="cs-edn">*)</sup>')
            continue
        t = esc(t)
        if it != cur_it and t.strip():
            flush()
            cur_it = it
        buf.append(t)
    flush()
    s = ''.join(out)
    s = re.sub(r'\*\s*\*', ' ', s) if False else s
    s = re.sub(r'[ \t]+', ' ', s)
    return s.strip()


def join_rows(rows):
    """一段内的行 → token 序列：行末连字符接下一行（下一行小写起头才接），否则补一个空格。"""
    toks = []
    for i, r in enumerate(rows):
        if r.get('anchor') is not None:
            toks.append(('\x00A', r['anchor']))
        segs = list(r['segs'])
        # 编者脚注记号 *) / •) → 记号 token
        ns = []
        for t, it in segs:
            parts = re.split(r'\s*[*•]\s*\)', t)
            for k, p in enumerate(parts):
                if k:
                    ns.append(('\x00N', False))
                ns.append((p, it))
        segs = ns
        nxt = rows[i + 1] if i + 1 < len(rows) else None
        last = segs[-1][0].rstrip() if segs else ''
        hyph = last.endswith('-') and nxt is not None and re.match(r'^[a-zàâäéèêëïîôöüùû]', nxt['text'] or '')
        if hyph:
            t, it = segs[-1]
            segs[-1] = (t.rstrip()[:-1], it)
            toks += segs
        else:
            toks += segs
            toks.append((' ', segs[-1][1] if segs else False))
    return toks


def is_italic_row(r):
    n = sum(len(t.strip()) for t, _ in r['segs'])
    i = sum(len(t.strip()) for t, it in r['segs'] if it)
    return n and i / n > 0.5


def main():
    stream = []          # 全书正文行（已带栏码锚点），外加脚注
    notes_by_anchor = []
    last_col = None
    dup_pages, col_gaps, col_misread = [], [], []
    for vol, pdf, a, b in VOLS:
        d = fitz.open(pdf)
        last_col = VOL_START[vol] - 1     # 两卷各自编栏：第 29 卷导言起于第 237 栏，第 30 卷首篇起于第 5 栏
        recent = []
        for pno in range(a, b + 1):
            rows, split = page_rows(d[pno - 1], single=(vol, pno) in SINGLE_COL)
            cols, body, notes = classify_page(rows)
            # 扫描件有整页重扫（第 30 卷 PDF 244–271 页是 463–466 栏两页轮流重复 14 遍）：跟最近几页比正文开头去重
            sig = re.sub(r'\W', '', ''.join(r['text'] for r in body[:8]))[:160]
            L, R = cols
            back = L is not None and R is not None and L == R - 1 and last_col - 8 < L <= last_col   # 页眉栏码倒退＝重扫
            if back or (sig and any(difflib.SequenceMatcher(None, sig, o).ratio() > 0.8 for o in recent)):
                dup_pages.append((vol, pno))
                continue
            recent = (recent + [sig])[-8:]
            # 栏码：页眉左右两个数字常被读错（635←535、890←390），以「上一页 + 1」为准，左右两数一致指向别处才算真跳号
            exp = last_col + 1
            L, R = cols
            if L is None or exp in (L, (R or 0) - 1):
                c0 = exp
            elif R is not None and L == R - 1 and L - exp in (2, 4):    # 缺一两页才会跳 2/4 栏；别的跳法是页眉读错
                c0 = L
                col_gaps.append((vol, pno, exp, L))
            else:
                c0 = exp
                col_misread.append((vol, pno, (L, R), exp))
            cols = [c0, c0 + 1]
            last_col = c0 + 1
            for c in (1, 2):
                cr = [r for r in body if r['col'] == c]
                if not cr:
                    continue
                left = statistics.median(r['x0'] for r in cr)
                for k, r in enumerate(cr):
                    r['indent'] = r['x0'] - left
                    r['vol'], r['page'] = vol, pno
                    r['anchor'] = cols[c - 1] if k == 0 else None
                    stream.append(r)
            for r in notes:
                r['vol'], r['page'] = vol, pno
                notes_by_anchor.append(r)

    # 行末连字符：把下一行的词头挪上来，判读与排版都按整词走（下一行小写起头才接）
    for k in range(len(stream) - 1):
        r, n = stream[k], stream[k + 1]
        if not r['segs'] or not n['segs']:
            continue
        while r['segs'] and not r['segs'][-1][0].strip():          # 行尾空白碎片
            r['segs'].pop()
        while n['segs'] and not n['segs'][0][0].strip():
            n['segs'].pop(0)
        if not r['segs'] or not n['segs']:
            continue
        t, it = r['segs'][-1]
        if re.search(r'[-¬]\s*$', t) and re.match(r'^\s*[a-zà-ÿ]', n['segs'][0][0]):
            nt, nit = n['segs'][0]
            m = re.match(r'^\s*([^\s]+)\s*', nt)
            head = re.sub(r'[-¬]\s*$', '', t)
            if nit == it:                              # 词头并进同一段，判读按整词看
                r['segs'][-1] = (head + m.group(1), it)
            else:
                r['segs'][-1] = (head, it)
                r['segs'].append((m.group(1), nit))
            n['segs'][0] = (nt[m.end():], nit)
            for x in (r, n):
                x['text'] = ''.join(s for s, _ in x['segs']).strip()

    # 看图整串替换（calvin_1sam_image_check → image_whole_fixes.tsv：希腊词、词中夹符号的脏串），在逐词判读之前落到行文字上；
    # 原串两头的标点保留（答案只给词本身）
    wf = RAW / 'image_whole_fixes.tsv'
    if wf.exists() and not NO_REPAIR:
        rows_by = collections.defaultdict(list)
        for r in stream:
            rows_by[(r['vol'], r['page'], r['col'])].append(r)
        miss = 0
        for ln in wf.read_text(encoding='utf-8').splitlines()[1:]:
            v, pg, col, raw, printed = ln.split('\t')
            lead = re.match(r'^[(\[«"\'„]*', raw).group(0)
            trail = re.search(r'[.,;:!?)\]»"\']*$', raw).group(0)
            rep = lead + printed + trail
            done = False
            for r in rows_by.get((v, int(pg), int(col)), []):
                for k, (t, it) in enumerate(r['segs']):
                    if raw in t:
                        r['segs'][k] = (t.replace(raw, rep, 1), it)
                        r['text'] = ''.join(x for x, _ in r['segs']).strip()
                        done = True
                        break
                if done:
                    break
            miss += not done
        if miss:
            print(f'⚠️ 看图整串替换未落 {miss} 条')

    # OCR 判读：主文本对 tesseract 证人逐栏对齐（repair_calvin_1sam）
    if not NO_REPAIR:
        words = [w for r in stream for s, _ in r['segs'] for w in WORD.findall(s)]
        global REP
        rep = REP = Repairer(RAW / 'witness_tess.jsonl', words)
        bykey = collections.OrderedDict()
        for r in stream:
            bykey.setdefault((r['vol'], r['page'], r['col']), []).append(r)
        for key, rs in bykey.items():
            segs_list = [r['segs'] for r in rs]
            rep.repair_column(key, segs_list)
            for r, sg in zip(rs, segs_list):
                r['segs'] = sg
                r['text'] = ''.join(s for s, _ in sg).strip()
        cnt = rep.write_log(RAW / 'repair_log.tsv')
        print('判读：', dict(cnt))
        REPAIR_STATS['fixed'] = sum(1 for r in rep.log if r[3] != r[5])
        REPAIR_STATS['residue'] = sum(1 for r in rep.log if 'residue' in r[6] and '>' not in r[6])
        REPAIR_STATS['confirmed'] = sum(1 for r in rep.log if 'confirmed' in r[6])
        REPAIR_STATS['image'] = sum(1 for r in rep.log if 'image' in r[6])

    print(f'重扫页（已跳过）{len(dup_pages)}：{dup_pages}')
    print(f'栏码真跳号（左右两数一致）：{col_gaps}')
    print(f'页眉栏码读错、按顺序改用预期值：{len(col_misread)} 页')
    # 切讲章：13.9 号字的 HOMILIA 行起新篇；第 29 卷首的 PROLEGOMENA 单列
    units = []
    cur = None
    for r in stream:
        t = r['text']
        if r['size'] > 12 and len(t) >= 6 and re.search(r'[A-Z]{2}', t):      # 篇题 13.9 号（OCR 常读花：H0MIL1A / HOMITJA / ROMILIA）
            cur = dict(title=t, rows=[], vol=r['vol'], page=r['page'], anchor=r['anchor'])
            units.append(cur)
            continue
        if cur is None:
            cur = dict(title='PROLEGOMENA', rows=[], vol=r['vol'], page=r['page'], anchor=r['anchor'])
            units.append(cur)
        cur['rows'].append(r)

    # 页底脚注挂回所在页的讲章
    for n in notes_by_anchor:
        host = None
        for u in units:
            if (u['vol'], u['page']) <= (n['vol'], n['page']):
                host = u
        host.setdefault('notes', []).append(n)

    front, sermons = [], []
    for u in units:
        title = u['title']
        if 'PROLEGOMENA' in title.upper() or (not sermons and 'HOMIL' not in title.upper()):
            md = build_body(u, prolog=True)
            if front:                                   # 导言标题行上方的碎片单独成了一段，并回去
                front[0]['md'] = (front[0]['md'] + '\n\n' + md).strip()
            else:
                front.append(dict(slug='prolegomena', title='Prolegomena (editors, 1885)', md=md))
            continue
        sermons.append(dict(title=title, unit=u))

    out = []
    cur = 1        # 原书只在换章处印「CAP. …」：沿全书记着当前章
    for i, s in enumerate(sermons, 1):
        u = s['unit']
        num_head = parse_num(s['title'])
        caps = [roman(CAP_RE.match(r['text']).group(1)) for r in u['rows'] if CAP_RE.match(r['text'])]
        caps = [c for c in caps if c and 1 <= c <= 31]
        first_is_cap = bool(u['rows']) and CAP_RE.match(u['rows'][0]['text'])
        ch = caps[0] if (first_is_cap and caps) else cur
        last = caps[-1] if caps else ch
        cur = last
        md, text_md = build_body(u)
        out.append(dict(num=i, num_printed=num_head, title=s['title'], chapter=ch,
                        chapter2=(last if last != ch else None),
                        head=f'Homilia {to_roman(i)} · {"Cap. " + to_roman(ch) + (("–" + to_roman(last)) if last != ch else "")}',
                        vol=u['vol'], page=u['page'], col=u['anchor'], md=md))
    # 散落的星号：行末连字符读成「*」（occa* sionem）→ 拼起来是词就并；两边都是整词的去掉星号；判不了的照录
    if not NO_REPAIR:
        def star(m):
            a, b = m.group(1), m.group(2)
            j = a + b
            fixed, act = REP.fix_word(j, None, None)
            if REP.lex.ok(j) or (act in ('rule', 'force') and fixed != j):
                STAR_LOG.append((a, b, fixed, 'join'))
                return fixed
            if REP.lex.ok(a) and REP.lex.ok(b):
                STAR_LOG.append((a, b, a + ' ' + b, 'drop'))
                return a + ' ' + b
            STAR_LOG.append((a, b, m.group(0), 'keep'))
            return m.group(0)
        def hyph(m):                                  # 看图改正后断词才接得上（flagel- Jans → flagel- lans → flagellans）
            j = m.group(1) + m.group(2)
            if REP.lex.ok(j) and not (REP.lex.ok(m.group(1)) and len(m.group(1)) > 3):
                STAR_LOG.append((m.group(1), m.group(2), j, 'hyphen'))
                return j
            return m.group(0)
        for x in front + out:
            x['md'] = re.sub(r'([A-Za-z]+)&#42;\s?([a-z]+)', star, x['md'])
            x['md'] = re.sub(r'\b([A-Za-z]+)- ([a-z]+)\b', hyph, x['md'])
        print('散星号：', collections.Counter(r[3] for r in STAR_LOG))

    # 手工修订表（看图读定的），落在最终 markdown 上；每条须恰好命中一次
    mf = RAW / 'manual_fixes.tsv'
    if mf.exists():
        units_by = {f['slug']: f for f in front}
        units_by.update({str(x['num']): x for x in out})
        for ln in mf.read_text(encoding='utf-8').splitlines()[1:]:
            if not ln.strip():
                continue
            unit, find, repl, _ = ln.split('\t')
            x = units_by[unit]
            n = x['md'].count(find)
            if n != 1:
                print(f'⚠️ manual_fixes 未落（命中 {n} 次）：{unit} {find!r}')
                continue
            x['md'] = x['md'].replace(find, repl)
    res = dict(front=front, sermons=out, gaps={}, merged={}, repair=REPAIR_STATS)
    (RAW / 'units.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    bad = [(s['num'], s['num_printed']) for s in out if s['num_printed'] != s['num']]
    print(f'讲章 {len(out)} 篇；卷首 {len(front)}；印本篇次与顺序不合：{bad}')
    print('各篇章次：', ' '.join(f'{s["num"]}:{s["chapter"]}' + (f'-{s["chapter2"]}' if s['chapter2'] else '') for s in out))


def to_roman(n):
    out = ''
    for v, r in ((100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')):
        while n >= v:
            out += r
            n -= v
    return out


def parse_num(title):
    t = re.sub(r'^\W*HOM\w*\s*', '', title.upper()).strip(' .')
    words = t.split()
    if words and all(w.strip('.') in ORD or w.strip('.') in ('VIGESIMA', 'TRIGESIMA', 'QUADRAGESIMA', 'CENTESIMA') for w in words):
        v = 0
        for w in words:
            w = w.strip('.')
            v += ORD.get(w, {'VIGESIMA': 20, 'TRIGESIMA': 30, 'QUADRAGESIMA': 40, 'CENTESIMA': 100}.get(w, 0))
        if words[-1].strip('.') == 'DECIMA' and len(words) > 1:
            v = ORD[words[0].strip('.')] + 10
        return v
    return roman(t.replace(' ', ''))


def build_body(u, prolog=False):
    rows = u['rows']
    blocks = []                 # (kind, [rows])
    i = 0
    if not prolog:
        # CAP 行与经文（斜体）块
        text_rows = []
        while i < len(rows):
            r = rows[i]
            if CAP_RE.match(r['text']):
                text_rows.append(dict(r, cap=True))
                i += 1
                continue
            if is_italic_row(r) or (text_rows and not (r['indent'] > 6 and not is_italic_row(r)) and i < len(rows) and
                                    text_rows and not text_rows[-1].get('cap') and not r['text'][:1].isupper()):
                text_rows.append(r)
                i += 1
                continue
            break
        caps = [r for r in text_rows if r.get('cap')]
        vrs = [r for r in text_rows if not r.get('cap')]
        if vrs:
            blocks.append(('text', vrs))
    para = []
    for r in rows[i:]:
        if CAP_RE.match(r['text']):                 # 正文中途换章：居中小标题
            if para:
                blocks.append(('p', para))
                para = []
            blocks.append(('cap', [r]))
            continue
        if para and r['indent'] > 6:
            blocks.append(('p', para))
            para = []
        para.append(r)
    if para:
        blocks.append(('p', para))
    md = []
    for kind, rs in blocks:
        body = render(join_rows(rs))
        if kind == 'cap':
            md.append(f'<p class="cs-head">{body}</p>')
        elif kind == 'text':
            body = re.sub(r'(?<![\w*])(\d{1,2})\.\s', r'<b class="cs-vn">\1</b> ', body)
            md.append(f'<div class="cs-text" markdown="1">\n\n{body}\n\n</div>')
        else:
            md.append(body)
    groups = []
    for n in u.get('notes') or []:                  # 一页可有几条编者注：以 *) / •) 起头分条
        if not groups or re.match(r'^\s*[*•]\s*\)', n['text']):
            groups.append([])
        groups[-1].append(n)
    for g in groups:
        nt = render(join_rows(g)).replace('<sup class="cs-edn">*)</sup>', '')
        md.append(f'<p class="cs-ednote">*) {nt.strip()}</p>')
    joined = '\n\n'.join(md)
    return joined if prolog else (joined, None)


if __name__ == '__main__':
    main()
