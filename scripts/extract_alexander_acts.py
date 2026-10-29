#!/usr/bin/env python3
"""J. A. Alexander《使徒行传注释》(1857)：Monergism 录入本 + 扫描本 ABBYY → units.json

底本与分工（详见 alexander_raw/acts/PROVENANCE.md）：

  字句   Monergism Books 电子本（2022 ePub）。录入干净，1–28 章齐。
  斜体   录入本把斜体全丢了。Alexander 全书靠斜体标出被讲解的经文字词与他自己的译法
         （`*Former treatise* might be more exactly rendered *first book*`），丢了就分不清
         哪是经文哪是解说。斜体从扫描本（IA 普林斯顿藏 1857 初版 actsofapostlesex01alex /
         ex02alex）的 ABBYY XML 逐词对齐后搬过来——只搬「格式」，不搬字。
  经文头 录入本把每节注释前大字排印的英文经文整段删了。经文头取扫描本 ABBYY 里
         字号 11 的段落（正文 9），OCR 读坏的字拿 KJV 同位词修正，见 header_fix()。

对齐：两边按「字母数字小写键」切词，分块跑 SequenceMatcher。经文头、页眉、页码只在
扫描本里有，对齐时自然落成插入，不影响。

用法：python3 scripts/extract_alexander_acts.py   → alexander_raw/acts/units.json + work/ 日志
"""
import gzip
import html
import json
import pickle
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'alexander_raw' / 'acts'
SRC = RAW / 'src'
WORK = RAW / 'work'
EPUB = SRC / 'monergism_acts.epub'
VOLS = ['actsofapostlesex01alex', 'actsofapostlesex02alex']
# 主扫描本 OCR 错词率 > 12% 的页（以录入本词表计），整页换用同版另一册（普林斯顿 actsofapostlese02alex，
# 页序号一律 −2，逐页按词串比对确认，相似度 0.80–0.87）。替补页错词率 3–8.5%。
PAGE_SUBST = {('actsofapostlesex02alex', p): ('actsofapostlese02alex', p - 2)
              for p in (119, 159, 163, 171, 193, 197, 263)}
KJV = SRC / '74-ACTeng-kjv2006.usfm'
NS = '{http://www.abbyy.com/FineReader_xml/FineReader6-schema-v1.xml}'

HEAD_FS = 10.5          # 经文头字号 11，正文 9


# ── Monergism ─────────────────────────────────────────────────────────

def load_monergism():
    """→ [{'kind': 'preface'|'introduction'|'chapter', 'ch': n, 'paras': [str]}]"""
    z = zipfile.ZipFile(EPUB)
    names = sorted(n for n in z.namelist() if re.match(r'acts_split_\d+\.html$', n))
    secs, cur = [], None
    for n in names:
        t = z.read(n).decode('utf-8')
        for m in re.finditer(r'<(h[234]|p)\b[^>]*>(.*?)</\1>', t, re.S):
            tag, inner = m.group(1), m.group(2)
            txt = html.unescape(re.sub(r'<[^>]+>', '', inner)).replace('\xa0', ' ')
            txt = re.sub(r'\s+', ' ', txt).strip()
            if tag != 'p':
                if txt == 'PREFACE':
                    cur = dict(kind='preface', paras=[])
                elif txt == 'INTRODUCTION':
                    cur = dict(kind='introduction', paras=[])
                elif re.fullmatch(r'CHAPTER \d+', txt):
                    cur = dict(kind='chapter', ch=int(txt.split()[1]), paras=[])
                else:
                    cur = None
                if cur is not None:
                    secs.append(cur)
                continue
            if cur is None or not txt:
                continue
            if txt.startswith('-----'):        # 文末 Monergism 版权声明
                cur = None
                continue
            cur['paras'].append(txt)
    chs = [s['ch'] for s in secs if s['kind'] == 'chapter']
    assert chs == list(range(1, 29)), chs
    # 录入本错字（body_fixes.tsv：三份扫描本同位一致 + 逐条看图核过）。每条须全书恰好命中一次
    for line in (RAW / 'body_fixes.tsv').read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        a, b = line.split('\t')[:2]
        hits = [(s, i) for s in secs for i, p in enumerate(s['paras']) if a in p]
        if len(hits) != 1 or hits[0][0]['paras'][hits[0][1]].count(a) != 1:
            raise SystemExit(f'body_fixes「{a}」命中 {len(hits)} 段')
        s_, i = hits[0]
        s_['paras'][i] = s_['paras'][i].replace(a, b)
    return secs


# ── ABBYY ─────────────────────────────────────────────────────────────

def load_abbyy(vol):
    """→ [(page, [par, ...])]；par = {'head': bool, 'words': [(text, italic)]}。缓存到 work/"""
    WORK.mkdir(parents=True, exist_ok=True)
    pk = WORK / f'{vol}.pkl'
    if pk.exists():
        return pickle.loads(pk.read_bytes())
    out, idx = [], 0
    for _, el in ET.iterparse(gzip.open(SRC / f'{vol}_abbyy.gz'), events=('end',)):
        if el.tag != NS + 'page':
            continue
        idx += 1
        pars = []
        for blk in el.iter(NS + 'block'):
            if blk.get('blockType') != 'Text':
                continue
            for par in blk.iter(NS + 'par'):
                # 每个字符带上 (斜体, 字号)，行拼起来再切词
                chars, nbig, ntot, nsmall = [], 0, 0, 0
                for ln in par.iter(NS + 'line'):
                    lc = []
                    for f in ln.iter(NS + 'formatting'):
                        it = f.get('italic') == 'true'
                        fs = float(f.get('fs') or 0)
                        for cp in f.iter(NS + 'charParams'):
                            c = cp.text or ''
                            for ch in c:
                                lc.append((ch, it))
                                if not ch.isspace():
                                    ntot += 1
                                    nbig += fs >= HEAD_FS
                                    nsmall += 0 < fs <= 8.5
                    if not lc:
                        continue
                    # 行尾连字符 + 下行小写开头 → 断词，接上；否则行间补空格
                    if chars and chars[-1][0] == '-' and lc[0][0].islower():
                        chars.pop()
                    elif chars:
                        chars.append((' ', False))
                    chars += lc
                if not ntot:
                    continue
                words, buf = [], []
                for ch, it in chars + [(' ', False)]:
                    if ch.isspace():
                        if buf:
                            w = ''.join(c for c, _ in buf)
                            letters = [i for c, i in buf if c.isalnum()]
                            ital = bool(letters) and sum(letters) * 2 > len(letters)
                            words.append((w, ital))
                            buf = []
                    else:
                        buf.append((ch, it))
                pars.append(dict(head=nbig * 2 > ntot, small=nsmall * 2 > ntot, words=words))
        out.append((idx, pars))
        el.clear()
    pk.write_bytes(pickle.dumps(out))
    return out


def key(w):
    return re.sub(r'[^a-z0-9]', '', w.lower())


# 节号段头：`24. ` `21, 22. ` `5-10. `；录入本另有 `Vv. 31, 32. ` 与漏了句点的 `25 By …`（后接大写才算）
LABEL = re.compile(r'^(?:V[sv]?\.\s*)?(\d{1,2})((?:\s*[.,\-–]\s*\d{1,2})*)(?:\s*\.\s+|\s+(?=[A-Z(]))')


def label_verses(s):
    """`21. 22.` / `21, 22.` / `5-10.` / `46, 47.` → [21, 22] 等；不是节号开头 → None"""
    m = LABEL.match(s)
    if not m:
        return None
    nums = [int(x) for x in re.findall(r'\d+', m.group(0))]
    if re.search(r'[-–]', m.group(0)) and len(nums) == 2:
        return list(range(nums[0], nums[1] + 1))
    return nums


# ── 扫描本：正文词流 + 经文头 ─────────────────────────────────────────

def ocr_stream():
    """正文词流（不含经文头）与经文头列表。经文头记下它前面已有多少正文词，用来定位。"""
    body, heads, notes = [], [], []
    alt = {}
    for (v, p), (av, ap) in PAGE_SUBST.items():
        alt.setdefault(av, dict(load_abbyy(av)))
    for vol in VOLS:
        for pg, pars in load_abbyy(vol):
            if (vol, pg) in PAGE_SUBST:
                av, ap = PAGE_SUBST[(vol, pg)]
                pars = alt[av][ap]
            for p in pars:
                txt = ' '.join(w for w, _ in p['words'])
                # 页眉（`ACTS 1, 12. 17`）与孤立页码：既不进经文头，也不打断跨页的经文头
                if RUNHEAD.match(txt) or re.fullmatch(r'[\dIl|\s.,]{1,8}', txt):
                    continue
                if p['head']:
                    if re.match(r'^CHAPTER\b', txt) or len(txt) < 4:
                        continue
                    words = [x for w, _ in p['words'] for x in w.replace('—', '— ').split()]
                    vv = label_verses(txt)
                    if vv is None:
                        # OCR 把节号后的句点读成 `-` `,`（`5- And`、`27, Because`）。落位靠 KJV 相似度，节号只作记录
                        m = re.match(r'^(\d{1,2})\s*[-.,:;]?\s+(?=[A-Z(])', txt)
                        if m:
                            vv = [int(m.group(1))]
                    if vv is None:
                        # 节号读坏（`G.` `i.` `'lA.` `^ 28.`）：上一段经文头已以句末标点收住、本段又是
                        # 「短记号 + 大写」开头 → 当新经文头，节号记 0（落位只看 KJV 相似度）
                        prev_done = not heads or not heads[-1]['open'] or \
                            re.search(r'[.?!:;—]\W{0,3}$', ' '.join(heads[-1]['words']))
                        if prev_done and HEADSTART.match(txt):
                            vv = [0]
                    if vv is None and heads and heads[-1]['open']:
                        heads[-1]['words'] += words                                # 跨页续行
                        heads[-1]['pages'].append(pg)
                        continue
                    if vv is None:
                        continue                                                # 书名页等大字
                    heads.append(dict(vv=vv, words=words, at=len(body),
                                      vol=vol, pages=[pg], open=True))
                    continue
                # 页脚注（`* " Truth is …`、`† " Tell me …`）：录入本没有，另收；也不打断跨页的经文头
                cont = notes and notes[-1]['page'] in (pg, pg - 1) and not FOOTNOTE.match(txt)
                if p.get('small') and (FOOTNOTE.match(txt) or cont):
                    if FOOTNOTE.match(txt):
                        notes.append(dict(vol=vol, page=pg, text=txt, at=len(body), open=True))
                    else:
                        notes[-1]['text'] += ' ' + txt                                # 跨页续注
                    continue
                if heads:
                    heads[-1]['open'] = False
                for w, it in p['words']:
                    body.append((w, it, vol, pg))
    return body, heads, notes


# 读坏的节号段头：`G. ` `i. ` `'lA. ` `^ 28. ` `3G. 87. ` `(). ` `• 25.26. `，后接大写
HEADSTART = re.compile(r"^[^\w(]{0,3}(?:\(\)|[\w']{1,3})(?:[.,;:\-]\s*[\w']{1,3})?[.,;:\-\\|]{0,2}\s+(?=[A-Z(])")

FOOTNOTE = re.compile(r'^\W{0,2}[*†‡f]\s')        # 小字号段 + 注号开头（† 常被读成 f）

RUNHEAD = re.compile(r'^\W{0,3}[\dA-Za-z]{0,4}\s*A\s?C\s?T\s?S\s+[\dIlO]|^\W{0,3}(?:INTRODUCTION|PREFACE)\b\.?\s*[\dIl]*$'
                     r'|^V\s?O\s?L\s?\.?\s*[IVl1]+\b')          # 页脚折标 `VOL. I.—18`


# ── 斜体三证人 ────────────────────────────────────────────────────────
# 同一版（1857 纽约 Scribner 初版）在 IA 上的三份扫描：普林斯顿两册 + 加州大学一册。
# ABBYY 的斜体判断有随机误报漏报（两份普林斯顿卷二逐词比，不一致 292 / 约 1.4 万斜体词），
# 逐词取多数票。
ITALIC_WITNESSES = {
    'v1': ['actsofapostlesex01alex', 'actsofapostlese01alex', 'actsofapostlesex01alexiala'],
    'v2': ['actsofapostlesex02alex', 'actsofapostlese02alex', 'actsofapostlesex02alexiala'],
}


def witness_italics(ident, mtoks, idxs):
    """一份扫描本 → {录入本词序号: 斜体}。只对齐 idxs 这一段（该卷覆盖的部分）。"""
    words = []
    for pg, pars in load_abbyy(ident):
        for p in pars:
            t = ' '.join(w for w, _ in p['words'])
            if p['head'] or p.get('small') or RUNHEAD.match(t):
                continue
            words += [(w, it) for w, it in p['words'] if key(w)]
    ok = [key(w) for w, _ in words]
    mk = [key(mtoks[i][2]) for i in idxs]
    # 卷二从第 13 章起，先按 8 词串定起点；卷一序言首词是小型大写对不上，就从头对（分块对齐的 6000 词
    # 搜索窗跨得过扉页）
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
            raise SystemExit(f'对齐失步：monergism 词 {mi}')
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
    secs = load_monergism()
    vocab = set()
    mtoks = []          # (sec_i, para_i, word)
    for si, s in enumerate(secs):
        for pi, p in enumerate(s['paras']):
            for w in p.split(' '):
                mtoks.append((si, pi, w))
                vocab.add(key(w))
    body, heads, notes = ocr_stream()
    print(f'monergism {len(mtoks)} 词；扫描本正文 {len(body)} 词、经文头 {len(heads)} 段', file=sys.stderr)

    mi_idx = [i for i, t in enumerate(mtoks) if key(t[2])]
    oi_idx = [i for i, t in enumerate(body) if key(t[0])]
    pairs, low = align([key(mtoks[i][2]) for i in mi_idx], [key(body[i][0]) for i in oi_idx])
    print(f'对齐 {len(pairs)}/{len(mi_idx)} 词；低匹配块 {low}', file=sys.stderr)
    m2o = {mi_idx[a]: oi_idx[b] for a, b in pairs.items()}

    # 斜体：三份扫描本逐词投票（≥2 票为斜体；只有两份对上时须两份都是斜体）。
    # 三份都没对上的词（多为 OCR 读坏的希腊文、专名）夹在两个斜体词之间 → 斜体（只补格式，不补字）
    ital = [False] * len(mtoks)
    v2_start = next(i for i, t in enumerate(mtoks) if secs[t[0]].get('ch') == 13)
    span = {'v1': [i for i in mi_idx if i < v2_start], 'v2': [i for i in mi_idx if i >= v2_start]}
    votes = [[] for _ in mtoks]
    for vk, ids in ITALIC_WITNESSES.items():
        for ident in ids:
            for m, it in witness_italics(ident, mtoks, span[vk]).items():
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
                cand.append((sim(words, vv, ch), -abs(j - pi), j, vv))
        if not cand or max(cand)[0] < 0.5:
            head_log.append(f'未落位\t{ch}:{h["vv"]}\t{max(cand)[0] if cand else 0:.2f}\t{" ".join(h["words"])[:90]}')
            continue
        sc, _, j, vv = max(cand)
        if (si, j) in para_head:
            head_log.append(f'重复\t{ch}:{vv}\t{" ".join(h["words"])[:90]}')
            continue
        kw = [w for v in vv for w in kjv.get((ch, v), [])]
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
        para_head[(si, j)] = dict(vv=vv, text=text, pages=h['pages'], vol=h['vol'], sim=round(sc, 3))

    # 脚注号 → 扫描本页：取注号前最近一个已对齐词所在页
    marks = []
    for i, (si, pi, w) in enumerate(mtoks):
        if re.search(r'[*†]', w):
            j = next((j for j in range(i, max(i - 40, -1), -1) if j in m2o), None)
            o = body[m2o[j]] if j is not None else None
            marks.append(dict(sec=si, para=pi, word=w, vol=o[2] if o else None, page=o[3] if o else None))
    (WORK / 'footnote_marks.json').write_text(json.dumps(marks, ensure_ascii=False, indent=1), encoding='utf-8')

    left = [(c, v, a) for (c, v), xs in manual.items() for a, _ in xs if (c, v, a) not in used]
    if left:
        raise SystemExit(f'head_manual 有条目没用上：{left}')

    # 脚注：录入本注号 ↔ footnotes.tsv 逐条配对（按出现顺序，注号所在词须一致）
    fns = [l.split('\t') for l in (RAW / 'footnotes.tsv').read_text(encoding='utf-8').splitlines()
           if l.strip() and not l.startswith('#')]
    mark_words = [m['word'] for m in marks]
    if [f[0] for f in fns] != mark_words:
        raise SystemExit(f'footnotes.tsv 与录入本注号不符：{mark_words}')
    fn_of = {}                                   # (sec, para, k-th mark in para) → note
    seen = Counter()
    for m, f in zip(marks, fns):
        k = seen[(m['sec'], m['para'])]
        seen[(m['sec'], m['para'])] += 1
        fn_of[(m['sec'], m['para'], k)] = dict(text=f[2], page=f[1], remark=f[3] if len(f) > 3 else '')

    def attach(si, pi, h, bucket):
        k = 0

        def rep(mm):
            nonlocal k
            note = dict(fn_of[(si, pi, k)], mark=mm.group(0))
            k += 1
            bucket.append(note)
            return f'⟦fn:{len(bucket)}⟧'
        return re.sub(r'[*†]', rep, h)

    # 输出
    units = dict(preface=[], introduction=[], chapters=[])
    cur = {}
    for si, s in enumerate(secs):
        toks = {}
        for i, (a, b, w) in enumerate(mtoks):
            if a == si:
                toks.setdefault(b, []).append((w, ital[i]))
        notes_here = []
        paras = [attach(si, pi, render(toks.get(pi, [])), notes_here) for pi in range(len(s['paras']))]
        if s['kind'] != 'chapter':
            units[s['kind']] = paras
            continue
        ch = dict(ch=s['ch'], intro=[], units=[], notes=notes_here)
        for pi, h in enumerate(paras):
            vv = label_verses(s['paras'][pi])
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
