#!/usr/bin/env python3
"""J. A. Alexander《马太福音释义》(1861)：Precept Austin 录入本 + 扫描本 ABBYY → units.json

底本与分工（详见 alexander_raw/matthew/PROVENANCE.md）。骨架照搬 extract_alexander_acts.py：

  字句   Precept Austin 网页录入本（据 1864 重印本；希腊文、希伯来文完整）。分两页：1–7 章、8–28 章。
  斜体   录入本全丢。从三份扫描本（IA 普林斯顿藏 1861 初版 gospelaccordingt00alex / gospelaccordin00alex、
         1864 重印 gospelaccordingt00alex_0）的 ABBYY 逐词对齐、多数票搬过来——只搬格式，不搬字。
  经文头 录入本把每节注释前大字排印的 KJV 经文整段删了。取主扫描本里比本页正文大 2 号以上的段落，
         OCR 读坏的字拿 KJV 同位词修正（header_fix）。
  脚注   录入本留了注号（145 个，只漏 p.99 一个 ‖，MARK_INSERT 补回），注文全丢。注文逐条看原图转录，
         存 footnotes.tsv；录入本注号按出现次序与表逐条配对，注号符号须一致。

两份 ABBYY 版本不同：1861 两份是 FineReader 6（italic="true"，正文 13–14 号、经文头 17–18、注 12），
1864 是 FineReader 10（italic="1"，正文 12）。字号一律按「本页正文众数」相对判，不写死。

用法：python3 scripts/extract_alexander_matthew.py   → alexander_raw/matthew/units.json + work/ 日志
"""
import gzip
import html
import json
import pickle
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'alexander_raw' / 'matthew'
SRC = RAW / 'src'
WORK = RAW / 'work'
PA = [SRC / 'preceptaustin_1.html', SRC / 'preceptaustin_2.html']
VOLS = ['gospelaccordingt00alex']
PAGE_SUBST = {}
KJV = SRC / '70-MATeng-kjv2006.usfm'


# ── Precept Austin ────────────────────────────────────────────────────

def load_pa():
    """→ [{'kind': 'preface'|'group'|'chapter', 'ch': n, 'paras': [str]}]
    group = 「CHAPTERS 5–7」登山宝训总说，挂在第 5 章章首。"""
    secs, cur = [], None
    for f in PA:
        t = f.read_text(encoding='utf-8')
        art = re.search(r'<article.*?</article>', t, re.S).group(0)
        for m in re.finditer(r'<(p|h\d)([^>]*)>(.*?)</\1>', art, re.S):
            tag, attr, inner = m.groups()
            txt = html.unescape(re.sub(r'<[^>]+>', '', inner)).replace('\xa0', ' ')
            txt = re.sub(r'\s+', ' ', txt).strip()
            if not txt:
                continue
            if 'class="author"' in attr:
                mm = re.fullmatch(r'CHAPTERS? (\d+)(?:–(\d+))?', txt)
                if not mm:
                    raise SystemExit(f'认不出的章题 {txt}')
                cur = dict(kind='group' if mm.group(2) else 'chapter', ch=int(mm.group(1)), paras=[],
                           title=txt)
                secs.append(cur)
                continue
            if txt.startswith('PREFACE '):
                cur = dict(kind='preface', paras=[txt[len('PREFACE '):]])
                secs.append(cur)
                continue
            if txt == 'THE END.' or tag != 'p' or cur is None or txt.startswith(('INDEX - ', 'GO TO COMMENTARY')):
                if txt == 'THE END.':
                    cur = None
                continue
            cur['paras'].append(txt)
    chs = [s['ch'] for s in secs if s['kind'] == 'chapter']
    assert chs == list(range(1, 29)), chs
    for line in (RAW / 'body_fixes.tsv').read_text(encoding='utf-8').splitlines() \
            if (RAW / 'body_fixes.tsv').exists() else []:
        if not line.strip() or line.startswith('#'):
            continue
        a, b = line.split('\t')[:2]
        hits = [(s, i) for s in secs for i, p in enumerate(s['paras']) if a in p]
        if len(hits) != 1 or hits[0][0]['paras'][hits[0][1]].count(a) != 1:
            raise SystemExit(f'body_fixes「{a}」命中 {len(hits)} 段')
        s_, i = hits[0]
        s_['paras'][i] = s_['paras'][i].replace(a, b)
    for a, b in MARK_INSERT:
        hits = [(s, i) for s in secs for i, p in enumerate(s['paras']) if a in p]
        if len(hits) != 1:
            raise SystemExit(f'MARK_INSERT「{a}」命中 {len(hits)} 段')
        s_, i = hits[0]
        s_['paras'][i] = s_['paras'][i].replace(a, b)
    return secs


# 录入本漏的注号（看原图 p.99：第 5 条注 ‖ 挂在 to try thoroughly. 后；tesseract 在此读出 `||`）
MARK_INSERT = [('to try thoroughly.', 'to try thoroughly.‖')]
MARKS = '*†‡§‖¶'


# ── ABBYY ─────────────────────────────────────────────────────────────

def load_abbyy(vol):
    """→ [(page, [par, ...])]；par = {'head', 'small', 'words': [(text, italic)], 'fs'}。缓存到 work/。
    FineReader 6 / 10 两种 schema 都认；head = 段落字号比本页正文众数大 ≥ 2，small = 小 ≥ 1。"""
    WORK.mkdir(parents=True, exist_ok=True)
    pk = WORK / f'{vol}.pkl'
    if pk.exists():
        return pickle.loads(pk.read_bytes())
    out, idx, ns = [], 0, None
    for _, el in ET.iterparse(gzip.open(SRC / f'{vol}_abbyy.gz'), events=('end',)):
        if ns is None:
            ns = el.tag[:el.tag.index('}') + 1] if el.tag.startswith('{') else ''
        if el.tag != ns + 'page':
            continue
        idx += 1
        raw = []
        for blk in el.iter(ns + 'block'):
            if blk.get('blockType') != 'Text':
                continue
            for par in blk.iter(ns + 'par'):
                chars, sizes, xh, top = [], Counter(), [], None
                for ln in par.iter(ns + 'line'):
                    if top is None and ln.get('t'):
                        top = int(ln.get('t'))
                    lc = []
                    for f in ln.iter(ns + 'formatting'):
                        it = f.get('italic') in ('true', '1')
                        fs = float(f.get('fs') or 0)
                        for cp in f.iter(ns + 'charParams'):
                            if (cp.text or '') in XCHARS and cp.get('b') and cp.get('t'):
                                xh.append(int(cp.get('b')) - int(cp.get('t')))
                            for ch in (cp.text or ''):
                                lc.append((ch, it))
                                if not ch.isspace():
                                    sizes[fs] += 1
                    if not lc:
                        continue
                    if chars and chars[-1][0] == '-' and lc[0][0].islower():
                        chars.pop()
                    elif chars:
                        chars.append((' ', False))
                    chars += lc
                if not sizes:
                    continue
                words, buf = [], []
                for ch, it in chars + [(' ', False)]:
                    if ch.isspace():
                        if buf:
                            w = ''.join(c for c, _ in buf)
                            letters = [i for c, i in buf if c.isalnum()]
                            words.append((w, bool(letters) and sum(letters) * 2 > len(letters)))
                            buf = []
                    else:
                        buf.append((ch, it))
                xh.sort()
                raw.append((sizes.most_common(1)[0][0], sum(sizes.values()), words,
                            xh[len(xh) // 2] if xh else None, top or 0))
        page_fs = Counter()
        for fs, n, *_ in raw:
            page_fs[fs] += n
        body_fs = page_fs.most_common(1)[0][0] if page_fs else 0
        # 正文 x 高度：本页正文字号段落的 x 高度中位数。脚注字号标签常与正文相同（p.30、p.40），
        # 但字形实测矮 2–4 像素（正文 27–28、注 24–25、经文头 33–34，1861 主扫描本 500 ppi）
        # 按字数加权取中位数（p.30 正文只有一大段、注有四段，按段数取会取到注的 x 高度）
        bx = sorted((x, n) for fs, n, w, x, t in raw if fs == body_fs and x)
        tot, acc, body_xh = sum(n for _, n in bx), 0, None
        for x, n in bx:
            acc += n
            if acc * 2 >= tot:
                body_xh = x
                break

        def small(x, w):
            if not (x and body_xh):
                return False
            lead = ' '.join(c for c, _ in w[:2])
            return x <= body_xh - 2.5 or (x <= body_xh - 1 and bool(FOOTNOTE.match(lead + ' ')))
        pars = [dict(head=fs >= body_fs + 2 and not (x and body_xh and x <= body_xh + 1),
                     small=small(x, w), fs=fs, xh=x, top=t, words=w)
                for fs, n, w, x, t in raw]
        out.append((idx, pars))
        el.clear()
    pk.write_bytes(pickle.dumps(out))
    return out


XCHARS = set('acemnorsuvwxz')                     # 无升部降部的小写字母，量 x 高度


def key(w):
    return re.sub(r'[^a-z0-9]', '', w.lower())


# 节号段头：`24. ` `21, 22. ` `5-10. `；后接大写才算漏了句点的 `25 By …`
LABEL = re.compile(r'^(?:V[sv]?\.\s*)?(\d{1,2})((?:\s*[.,\-–]\s*\d{1,2})*)(?:\s*\.\s+|\s+(?=[A-Z(]))')


def label_verses(s):
    m = LABEL.match(s)
    if not m:
        return None
    nums = [int(x) for x in re.findall(r'\d+', m.group(0))]
    if re.search(r'[-–]', m.group(0)) and len(nums) == 2:
        return list(range(nums[0], nums[1] + 1))
    return nums


# ── 扫描本：正文词流 + 经文头 + 脚注 ─────────────────────────────────

def ocr_stream():
    """正文词流（不含经文头、页眉、页脚注）与经文头、页脚注列表。经文头、脚注记下它前面已有多少正文词。
    页脚注按 x 高度认（字号标签未必比正文小：p.30 注与正文同为 13 号），见下。"""
    body, heads, notes = [], [], []
    for vol in VOLS:
        for pg, pars in load_abbyy(vol):
            txts = [' '.join(w for w, _ in p['words']) for p in pars]
            # 页脚注：小字段（x 高度矮于正文）以注号开头 → 新注；紧跟在注后面的小字段 → 续注。
            # ABBYY 不一定把注排在页末（p.43 注夹在跨页的经文头与正文之间），所以逐段判，不按位置。
            # 注既不进正文词流，也不打断跨页的经文头。
            in_note = False
            for i, p in enumerate(pars):
                txt = txts[i]
                if RUNHEAD.match(txt) or re.fullmatch(r'[\dIl|\s.,]{1,8}', txt) or JUNKPAR.fullmatch(txt):
                    continue
                if p['small'] and not p['head']:
                    if len(re.findall(r'[A-Za-z]', txt)) < 3:          # 污点 `o`
                        continue
                    if FOOTNOTE.match(txt) or not in_note:
                        notes.append(dict(vol=vol, page=pg, text=txt, at=len(body)))
                    else:
                        notes[-1]['text'] += ' ' + txt
                    in_note = True
                    continue
                in_note = False
                if p['head']:
                    if re.match(r'^CHAPTERS?\b', txt) or len(txt) < 4:
                        continue
                    words = [x for w, _ in p['words'] for x in w.replace('—', '— ').split()]
                    vv = label_verses(txt)
                    if vv is None:
                        m = re.match(r'^(\d{1,2})\s*[-.,:;]?\s+(?=[A-Z(])', txt)
                        if m:
                            vv = [int(m.group(1))]
                    if vv is None:
                        prev_done = not heads or not heads[-1]['open'] or \
                            re.search(r'[.?!:;—]\W{0,3}$', ' '.join(heads[-1]['words']))
                        if prev_done and HEADSTART.match(txt):
                            vv = [0]
                    if vv is None and heads and heads[-1]['open']:
                        heads[-1]['words'] += words
                        heads[-1]['pages'].append(pg)
                        continue
                    if vv is None:
                        continue
                    heads.append(dict(vv=vv, words=words, at=len(body), vol=vol, pages=[pg], open=True))
                    continue
                if heads:
                    heads[-1]['open'] = False
                for w, it in p['words']:
                    body.append((w, it, vol, pg))
    return body, heads, notes


HEADSTART = re.compile(r"^[^\w(]{0,3}(?:\(\)|[\w']{1,3})(?:[.,;:\-]\s*[\w']{1,3})?[.,;:\-\\|]{0,2}\s+(?=[A-Z(])")

# 注号：* † ‡ §（† 常读成 t / f，‡ 读成 X / % / +，* 读成 - " „），后接空格
FOOTNOTE = re.compile(r'^\W{0,2}(?:[*†‡§tfX%"„\-•+]{1,2}\s+(?=\S)|[*†‡§]\s*(?=[A-Z]))')

RUNHEAD = re.compile(r'^\W{0,3}[\dA-Za-z]{0,4}\s*\W?\s*M\s?A\s?T\s?T\s?(?:H|I\s?I|Ii)\s?E\s?(?:W|A\s?V|A\s?Y|V\s?V)'
                     r'|^\W{0,3}[\dIl]{0,4}\s*PREFACE\b\.?\s*[\dIl]*$')
JUNKPAR = re.compile(r'[^A-Za-z]{1,12}')            # 页面上的花饰、污点（`•■»>`）


# ── 斜体三证人 ────────────────────────────────────────────────────────
ITALIC_WITNESSES = ['gospelaccordingt00alex', 'gospelaccordin00alex', 'gospelaccordingt00alex_0']


def witness_italics(ident, mtoks, idxs):
    """一份扫描本 → {录入本词序号: 斜体}"""
    words = []
    for pg, pars in load_abbyy(ident):
        for p in pars:
            t = ' '.join(w for w, _ in p['words'])
            if p['head'] or RUNHEAD.match(t):
                continue
            words += [(w, it) for w, it in p['words'] if key(w)]
    ok = [key(w) for w, _ in words]
    mk = [key(mtoks[i][2]) for i in idxs]
    start = next((j for j in range(len(ok)) if ok[j:j + 8] == mk[:8]), 0)
    pairs, low = align(mk, ok[start:])
    return {idxs[a]: words[start + b][1] for a, b in pairs.items()}


# ── 对齐 ──────────────────────────────────────────────────────────────

def align(mk, ok, chunk=2500, look=6000):
    """分块对齐：mk / ok 为两边的键序列（空键已剔）。返回 {m_index: o_index}。"""
    pairs = {}
    mi = oi = 0
    low = []
    while mi < len(mk):
        a = mk[mi:mi + chunk]
        b = ok[oi:oi + look]
        sm = SequenceMatcher(None, a, b, autojunk=False)
        blocks = [bl for bl in sm.get_matching_blocks() if bl.size]
        matched = sum(bl.size for bl in blocks)
        if matched < len(a) * 0.5:
            low.append((mi, matched, len(a)))
        last_m = last_o = None
        for bl in blocks:
            for k in range(bl.size):
                pairs[mi + bl.a + k] = oi + bl.b + k
            last_m, last_o = bl.a + bl.size, bl.b + bl.size
        # 同长度的 replace 块：按位对上（OCR 读错的词，位置仍可靠）
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'replace' and i2 - i1 == j2 - j1 and i2 - i1 <= 4:
                for k in range(i2 - i1):
                    pairs.setdefault(mi + i1 + k, oi + j1 + k)
        if mi + chunk >= len(mk):
            break
        # 下一块从本块后段的最后一个匹配处起跑（留重叠，免得块尾对不齐）
        cut = int(chunk * 0.8)
        anchor = [bl for bl in blocks if bl.a + bl.size <= cut]
        if not anchor:
            raise SystemExit(f'对齐失步：录入本词 {mi}')
        bl = anchor[-1]
        mi, oi = mi + bl.a + bl.size, oi + bl.b + bl.size
    return pairs, low


# ── 经文头清理 ────────────────────────────────────────────────────────

def load_kjv():
    """→ {(ch, v): [词]}。eBible KJV2006 USFM：\\w / \\+w（耶稣的话外面再包一层 \\wj）带 strong 属性，
    \\add 是 KJV 斜体（补出词）——Alexander 用括号标，但不是每处都标，所以这里只取字。"""
    t = KJV.read_text(encoding='utf-8')
    out, ch = {}, 0
    for line in t.splitlines():
        m = re.match(r'\\c (\d+)', line)
        if m:
            ch = int(m.group(1))
            continue
        m = re.match(r'\\v (\d+) (.*)', line)
        if not m:
            continue
        s = re.sub(r'\|[^\\]*', '', m.group(2))            # strong="..." 等属性
        s = re.sub(r'\\\+?[a-z]+\*?', ' ', s)              # 标记
        s = s.replace('¶', ' ').replace('\u2019', "'")
        s = re.sub(r"\s+'\s*", "'", s)                       # day ’ s → day's
        s = re.sub(r'\s+([,.;:?!])', r'\1', s)
        out[(ch, int(m.group(1)))] = s.split()
    return out


JUNK = re.compile(r'^[\\|■\'`^*~_»«]+$')
SINGLE_OK = {'a', 'i', 'o'}


def _prep(words):
    """经文头 OCR 词预处理：去掉装订口噪点（`\\` `■` `'` 之类），再把被噪点隔开的行末断词接回
    （`com- \\ panied` → `companied`）。孤立字母这里**不删**：`m` 常是 `in` 读错，交给 KJV 比对去改；
    比对后仍对不上 KJV 的孤立字母才当噪点删（header_fix 的 delete 分支）。"""
    ws = [w for w in words if not JUNK.match(w)]
    out = []
    for w in ws:
        if out and out[-1].endswith('-') and len(out[-1]) > 1 and w[:1].islower():
            out[-1] = out[-1][:-1] + w
        else:
            out.append(w)
    return out


def _swap(w, k, start=False):
    """把 OCR 词 w 的字母部分换成 KJV 词 k 的字母部分，保留 w 两端的标点。大小写一律照 KJV，
    只在句首（经文头开头或句末标点之后）大写——OCR 的首字母大小写不可信（`Avhicli` `Wlien` 的
    大写是把 w 读成 Av / W 造成的，照抄就成了句中的 Which / When）。"""
    core = re.sub(r"[^A-Za-z'\-]", '', k).strip("'")
    lead = re.match(r'^[^A-Za-z0-9]*', w).group(0)
    trail = re.search(r'[^A-Za-z0-9]*$', w).group(0) if re.search(r'[A-Za-z0-9]', w) else ''
    if start and core[:1].islower():
        core = core[:1].upper() + core[1:]
    return lead + core + trail


def header_fix(words, kjv_words, vocab, confus):
    """OCR 经文头逐词修正，KJV 同位词当证人。三种情况才换：
      1. OCR 词不是真词（`fortli` `tlie` `Avhicli`）；
      2. 两边都是真词，但这一对在 head_confusions.tsv 里判为 OCR 字形混淆（`clay`/`day`、`lie`/`he`）；
      3. OCR 一个带连字符的非词对 KJV 两个词（`sabbatli-day's`）→ 保留连字符。
    其余真词差异一律照 OCR——亚历山大的经文头本就与 KJV 有出入（show/shew、Judea/Judæa、
    补出词加不加括号）。KJV 多出、OCR 没有的词**不补**，记日志。"""
    words = _prep(words)
    ok = [key(w) for w in words]
    start = [i == 0 or bool(re.search(r'[.?!]["\')]*$', words[i - 1])) for i in range(len(words))]
    kk = [key(w) for w in kjv_words]
    sm = SequenceMatcher(None, ok, kk, autojunk=False)
    out, changes, unresolved = list(words), [], []
    real = lambda k: k in vocab and (len(k) > 1 or k in SINGLE_OK or k.isdigit())
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        if tag == 'replace' and i2 - i1 == j2 - j1:
            for k in range(i2 - i1):
                w, kw, kj = words[i1 + k], ok[i1 + k], kk[j1 + k]
                if not kw or kw == kj:
                    continue
                if not real(kw):
                    out[i1 + k] = _swap(w, kjv_words[j1 + k], start[i1 + k])
                    changes.append(('非词', w, out[i1 + k]))
                elif (kw, kj) in confus:
                    out[i1 + k] = _swap(w, kjv_words[j1 + k], start[i1 + k])
                    changes.append(('混淆', w, out[i1 + k]))
                else:
                    unresolved.append(('真词', w, kjv_words[j1 + k]))
            continue
        if tag == 'replace':
            seg = words[i1:i2]
            kseg = kjv_words[j1:j2]
            if i2 - i1 == 1 and '-' in seg[0] and j2 - j1 == 2 and not real(ok[i1]):
                out[i1] = _swap(seg[0], '-'.join(re.sub(r"[^A-Za-z']", '', x) for x in kseg), start[i1])
                changes.append(('连字', seg[0], out[i1]))
            elif all(not real(key(w)) for w in seg if key(w)) and j2 - j1 <= i2 - i1 + 1:
                lead = re.match(r'^[^A-Za-z0-9]*', seg[0]).group(0)
                trail = re.search(r'[^A-Za-z0-9]*$', seg[-1]).group(0)
                rep = ' '.join(re.sub(r"[^A-Za-z']", '', x) for x in kseg)
                for k in range(i1, i2):
                    out[k] = None
                out[i1] = lead + rep + trail
                changes.append(('拆粘', ' '.join(seg), out[i1]))
            else:
                unresolved.append(('段', ' '.join(seg), ' '.join(kseg)))
        elif tag == 'delete':
            seg = words[i1:i2]
            if all(len(key(w)) == 1 and key(w) not in SINGLE_OK and not key(w).isdigit() for w in seg):
                for k in range(i1, i2):
                    out[k] = None
                changes.append(('噪点', ' '.join(seg), ''))
            else:
                unresolved.append(('OCR多', ' '.join(seg), ''))
        elif tag == 'insert':
            unresolved.append(('KJV多', '', ' '.join(kjv_words[j1:j2])))
    s = ' '.join(w for w in out if w)
    s = re.sub(r'\s+([,.;:?!)])', r'\1', s)
    s = re.sub(r'\(\s+', '(', s)
    s = re.sub(r'\s*—\s*', '—', s)
    s = re.sub(r'[\s•■^*»«\\/\]\[]+$', '', s)            # 行末噪点（`—•` `^` `]`）
    s = re.sub(r'[\^\\\]\[*/¥%{}<>»«•■|]', '', s)         # 词中噪点（`w^ord`）：经文头里不会有这些字符
    s = re.sub(r'\s{2,}', ' ', s)
    s2 = punct_gate(s, kjv_words)
    if s2 != s:
        changes.append(('标点', s, s2))
    return s2.strip(), changes, unresolved


def punct_gate(s, kjv_words):
    """经文头标点清理——只动标点与大小写，字母一个不改（改完按字母序列自检）。
    亚历山大的经文头不带引号，KJV 也不带；括号只用来标补出词，必须成对。"""
    before = re.sub(r'[^a-z]', '', s.lower())
    kj = {re.sub(r'[^A-Za-z]', '', w).lower(): re.sub(r'[^A-Za-z]', '', w) for w in kjv_words}
    s = re.sub(r'^(?:\d{1,2}|[\dA-Za-z]{1,2})\.\s+(?=[A-Z])', '', s) if re.match(r'^\d[\dGlIO]\.\s', s) else s
    s = re.sub(r'(?<![A-Za-z])[\'"“”‘](?=[A-Za-z])|(?<=[A-Za-z,.;:?!])["“”](?!\w)', '', s)   # 零散引号（词中撇号不动）
    s = re.sub(r'(?<=[a-z])\.(?=[a-z])', '', s)                 # mu.ch
    s = re.sub(r'([,;:])[,;:.]+', r'\1', s)                     # crying:,
    s = re.sub(r'(?<=[a-z])\.(?= [a-z])', '', s)                # threatenings. and
    s = re.sub(r'\){2,}', ')', s)
    s = re.sub(r'^(?:[-.,;:]+\s*\d{0,2}[.,]?\s*)+(?=[A-Z(])', '', s)   # 段头残渣 `-10. ` `.Because` `-And`
    s = re.sub(r"(?<=[a-rt-wyz])'(?=\s)", '', s)                 # 词尾游离撇号 your' / favour'（复数所有格 s' 与 x' 不动）
    # 括号配对：从左到右扫，删掉配不上的
    out, stack = list(s), []
    for i, c in enumerate(out):
        if c == '(':
            stack.append(i)
        elif c == ')':
            if stack:
                stack.pop()
            else:
                out[i] = ''
    for i in stack:
        out[i] = ''
    s = ''.join(out)
    s = re.sub(r'\)(?=[A-Za-z])', ') ', s)
    # 词中大写（deLay）：KJV 同词小写则照 KJV
    s = re.sub(r'\b([a-z]+[A-Z][a-z]*)\b', lambda m: m.group(1).lower() if m.group(1).lower() in kj else m.group(1), s)
    s = re.sub(r'\s{2,}', ' ', s).strip()
    assert re.sub(r'[^a-z]', '', s.lower()) == before or not re.match(r'^\d', s), (before, s)
    return s


def load_head_manual():
    """head_manual.tsv：{(章, 节): [(现文, 改为)]}"""
    out = {}
    for line in (RAW / 'head_manual.tsv').read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.startswith('#'):
            ref, a, b = line.split('\t')[:3]
            c, v = map(int, ref.split(':'))
            out.setdefault((c, v), []).append((a, b))
    return out


def load_confusions():
    p = RAW / 'head_confusions.tsv'
    out = set()
    if p.exists():
        for line in p.read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.startswith('#'):
                a, b = line.split('\t')[:2]
                out.add((a.strip(), b.strip()))
    return out


# ── 组装 ──────────────────────────────────────────────────────────────

def render(tokens):
    """[(词, 斜体)] → HTML。每个斜体词只包字母部分（两端标点留在外面），相邻的再并成一个 <em>：
    `some (one)` → `<em>some</em> (<em>one</em>)`，与原书只把字排斜、括号照排正体一致。"""
    out = []
    for w, it in tokens:
        m = re.match(r'^([^A-Za-z0-9\u0370-\u03ff\u1f00-\u1fff]*)(.*?)([^A-Za-z0-9\u0370-\u03ff\u1f00-\u1fff]*)$', w, re.S)
        a, b, c = (html.escape(x, False) for x in m.groups())
        out.append(a + (f'<em>{b}</em>' if it and b else b) + c)
    return re.sub(r'</em> <em>', ' ', ' '.join(out))


def main():
    secs = load_pa()
    vocab = set()
    mtoks = []          # (sec_i, para_i, word)
    for si, s in enumerate(secs):
        for pi, p in enumerate(s['paras']):
            for w in p.split(' '):
                mtoks.append((si, pi, w))
                vocab.add(key(w))
    body, heads, notes = ocr_stream()
    print(f'录入本 {len(mtoks)} 词；扫描本正文 {len(body)} 词、经文头 {len(heads)} 段、页脚注 {len(notes)} 条', file=sys.stderr)

    mi_idx = [i for i, t in enumerate(mtoks) if key(t[2])]
    oi_idx = [i for i, t in enumerate(body) if key(t[0])]
    pairs, low = align([key(mtoks[i][2]) for i in mi_idx], [key(body[i][0]) for i in oi_idx])
    print(f'对齐 {len(pairs)}/{len(mi_idx)} 词；低匹配块 {low}', file=sys.stderr)
    m2o = {mi_idx[a]: oi_idx[b] for a, b in pairs.items()}

    # 斜体：三份扫描本逐词投票（≥2 票为斜体；只有两份对上时须两份都是斜体）。
    # 三份都没对上的词（多为 OCR 读坏的希腊文、专名）夹在两个斜体词之间 → 斜体（只补格式，不补字）
    ital = [False] * len(mtoks)
    votes = [[] for _ in mtoks]
    for ident in ITALIC_WITNESSES:
        for m, it in witness_italics(ident, mtoks, mi_idx).items():
            votes[m].append(it)
    vote_log = Counter()
    for m, vs in enumerate(votes):
        if not vs:
            continue
        n = sum(vs)
        ital[m] = n * 2 > len(vs)
        vote_log[(len(vs), n)] += 1
    print('斜体票型（证人数, 斜体票）:', sorted(vote_log.items()), file=sys.stderr)
    filled = 0
    for i in range(len(mtoks)):
        if votes[i] or not key(mtoks[i][2]):
            continue
        a = next((j for j in range(i - 1, max(i - 4, -1), -1) if votes[j]), None)
        b = next((j for j in range(i + 1, min(i + 4, len(mtoks))) if votes[j]), None)
        if a is not None and b is not None and ital[a] and ital[b] \
                and mtoks[a][:2] == mtoks[i][:2] == mtoks[b][:2]:
            ital[i] = True
            filled += 1

    # 经文头 → 落到附近「节号开头、且该组节的 KJV 与经文头最像」的注释段。
    # 不信 OCR 读出的节号（`48.` 其实是 43、`81.` 是 31），只用它在缺 KJV 时兜底。
    import bisect
    kjv = load_kjv()
    confus = load_confusions()
    manual, used = load_head_manual(), set()
    o2m = {o: m for m, o in m2o.items()}
    head_log, unres_log = [], []
    para_head = {}
    sorted_o = sorted(o2m)

    def sim(words, vv, ch):
        kw = [key(w) for v in vv for w in kjv.get((ch, v), [])]
        hw = [key(w) for w in words]
        return SequenceMatcher(None, hw, kw, autojunk=False).ratio() if kw and hw else 0

    for h in heads:
        k = bisect.bisect_left(sorted_o, h['at'])
        if k >= len(sorted_o):
            continue
        m = o2m[sorted_o[k]]
        si, pi = mtoks[m][:2]
        s = secs[si]
        if s['kind'] != 'chapter':
            head_log.append(f'未落位\t非章节\t{" ".join(h["words"])[:80]}')
            continue
        ch = s['ch']
        lab = LABEL.match(' '.join(h['words'])) or re.match(r'^\d{1,2}\s*[-.,:;]?\s+', ' '.join(h['words'])) \
            or (HEADSTART.match(' '.join(h['words'])) if h['vv'] == [0] else None)
        words = h['words'][len(lab.group(0).split()):] if lab else h['words']
        cand = []
        for j in range(max(pi - 3, 0), min(pi + 4, len(s['paras']))):
            vv = label_verses(s['paras'][j])
            if vv:
                # 录入本常把几节并成一段注释（`45, 46.`），原书却每节各印一个经文头：逐节也比一次，取高者
                best = max([sim(words, vv, ch)] + [sim(words, [v], ch) for v in vv])
                cand.append((best, -abs(j - pi), j, vv))
        if not cand or max(cand)[0] < 0.5:
            head_log.append(f'未落位\t{ch}:{h["vv"]}\t{max(cand)[0] if cand else 0:.2f}\t{" ".join(h["words"])[:90]}')
            continue
        sc, _, j, vv = max(cand)
        # 这个经文头对的是组内哪几节：逐节比，取与它最像的一节起、连续若干节（KJV 拼起来最像为止）
        sub = vv
        if len(vv) > 1:
            best = (sim(words, vv, ch), vv)
            for a_ in range(len(vv)):
                for b_ in range(a_ + 1, len(vv) + 1):
                    sc_ = sim(words, vv[a_:b_], ch)
                    if sc_ > best[0] + 0.02:
                        best = (sc_, vv[a_:b_])
            sub = best[1]
        prev = para_head.get((si, j))
        if prev and set(sub) & set(prev['parts_vv']):
            head_log.append(f'重复\t{ch}:{sub}\t{" ".join(h["words"])[:90]}')
            continue
        kw = [w for v in sub for w in kjv.get((ch, v), [])]
        text, ch_, un = header_fix(words, kw, vocab, confus)
        for kind, a_, b_ in ch_:
            head_log.append(f'改\t{kind}\t{ch}:{vv[0]}\t{a_}\t→\t{b_}')
        for kind, a_, b_ in un:
            unres_log.append(f'{kind}\t{ch}:{vv[0]}\t{a_}\t|KJV|\t{b_}\t{h["vol"]}\t{h["pages"]}')
        for a_, b_ in manual.get((ch, vv[0]), []):
            if text.count(a_) != 1:
                raise SystemExit(f'head_manual {ch}:{vv[0]} 「{a_}」命中 {text.count(a_)} 次：{text}')
            text = text.replace(a_, b_)
            used.add((ch, vv[0], a_))
        if prev:                    # 同一段注释的第二、三个经文头：按节序拼接
            parts = sorted(prev['parts'] + [(sub[0], text, sub)])
            prev.update(parts=parts, parts_vv=prev['parts_vv'] + sub,
                        text=' '.join(f'{v[0]}. {t}' if k else t for k, (_, t, v) in enumerate(parts)),
                        pages=prev['pages'] + h['pages'])
            continue
        para_head[(si, j)] = dict(vv=vv, text=text, pages=h['pages'], vol=h['vol'], sim=round(sc, 3),
                                  parts=[(sub[0], text, sub)], parts_vv=list(sub))

    left = [(c, v, a) for (c, v), xs in manual.items() for a, _ in xs if (c, v, a) not in used]
    if left:
        raise SystemExit(f'head_manual 有条目没用上：{left}')

    # 脚注：录入本注号按出现次序与 footnotes.tsv 逐条配对（表按页、页内序排），注号符号须一致
    fns = [l.split('\t') for l in (RAW / 'footnotes.tsv').read_text(encoding='utf-8').splitlines()
           if l.strip() and not l.startswith('#')]
    fns.sort(key=lambda f: (int(f[0]), int(f[1])))
    seq = [c for _, _, w in mtoks for c in w if c in MARKS]
    if ''.join(seq) != ''.join(f[2] for f in fns):
        raise SystemExit(f'录入本注号 {len(seq)} 个与 footnotes.tsv {len(fns)} 条对不上')
    fn_iter = iter(dict(mark=f[2], page=f[0], k=f[1], text=f[3], remark=f[4] if len(f) > 4 else '')
                   for f in fns)
    print(f'脚注 {len(fns)} 条，与录入本注号逐条对上', file=sys.stderr)

    # 输出
    units = dict(preface=[], chapters=[])
    group = {}
    for si, s in enumerate(secs):
        toks = {}
        for i, (a, b, w) in enumerate(mtoks):
            if a == si:
                toks.setdefault(b, []).append((w, ital[i]))
        notes_here = []

        def para(pi):
            h = render(toks.get(pi, []))

            def sub(m_):
                n = next(fn_iter)
                assert n['mark'] == m_.group(0)
                notes_here.append(n)
                return f'⟦fn:{len(notes_here)}⟧'
            return re.sub(f'[{MARKS}]', sub, h)
        paras = [para(pi) for pi in range(len(s['paras']))]
        if s['kind'] == 'preface':
            units['preface'] = paras
            continue
        if s['kind'] == 'group':
            group = dict(title=s['title'], paras=paras, notes=notes_here)
            continue
        ch = dict(ch=s['ch'], intro=[], units=[], notes=notes_here)
        if group and s['ch'] == 5:
            ch['group'] = group
        for pi, h in enumerate(paras):
            vv = label_verses(s['paras'][pi]) if s['ch'] <= 16 else None
            if vv:
                hd = para_head.get((si, pi))
                ch['units'].append(dict(vv=vv, label=LABEL.match(s['paras'][pi]).group(0).strip(),
                                        head=hd['text'] if hd else None,
                                        head_vv=hd['vv'] if hd else None,
                                        head_src=[hd['vol'], hd['pages']] if hd else None,
                                        paras=[LABEL.sub('', h, count=1)]))
            elif ch['units']:
                ch['units'][-1]['paras'].append(h)
            else:
                ch['intro'].append(h)
        units['chapters'].append(ch)

    nh = sum(1 for c in units['chapters'] for u in c['units'] if u['head'])
    nu = sum(len(c['units']) for c in units['chapters'])
    units['log'] = dict(aligned=len(pairs), words=len(mi_idx), italic_filled=filled,
                        heads_found=len(heads), heads_placed=nh, units=nu)
    (RAW / 'units.json').write_text(json.dumps(units, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (WORK / 'head_fixes.log').write_text('\n'.join(head_log) + '\n', encoding='utf-8')
    (WORK / 'head_unresolved.log').write_text('\n'.join(unres_log) + '\n', encoding='utf-8')
    nit = sum(ital)
    print(f'斜体词 {nit}（其中夹补 {filled}）；经文头落位 {nh}/{nu} 条注释（扫描本 {len(heads)} 段）', file=sys.stderr)
    print(f'经文头修正 {sum(1 for x in head_log if x.startswith("改"))}，未落位 '
          f'{sum(1 for x in head_log if x.startswith("未落位"))}，与 KJV 不一致留原样 {len(unres_log)}', file=sys.stderr)


if __name__ == '__main__':
    main()
