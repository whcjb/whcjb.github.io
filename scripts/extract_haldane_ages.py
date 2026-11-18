#!/usr/bin/env python3
"""霍尔丹《罗马书释义》AGES PDF → units.json（版式照 AGES；结构与 extract_haldane.py 的 units.json 相容）

    /usr/bin/python3 scripts/extract_haldane_ages.py [out.json]      # PyMuPDF 只装在系统 python 上

底本 ~/Documents/论文/haldane/haldane_romans_ages.pdf（AGES Digital Library，sabda.org HAL_ROMA.PDF，908 页）。
诊断见 haldane_raw/romans/DIAGNOSIS.md。通用 calvin_extract.py `ages_phil` 在本书上会把以经文锚点 `<NNNNNN>`
起首的续行误判成 [FOOTNOTE]（1,296 处），不宜为一本书改通用提取器，故单写；规则照 AGES skill。

版面规则（逐条实测）：
  · 单列，正文 x≈26、左对齐。**分段靠段间空白**：段内行距 14–16pt，段间 22–24pt，> 19pt 即新段。
    每页首行都在 y≈55，跨页无从判断 → 上页末行以句末标点收尾、且本页首行开头 6 词是 1874 扫描本某段的段首 → 新段；
    `Ver.` / `ftN.` 起首也是新段；否则接上页末段。
    （2026-11-18 改）录入本自己多分了段（1:1「…Church. / From the period…」、15:1「…weak brethren. / Some persons…」，
    1874 版都是同一段），不可作证；跨页改以 1874 第九版扫描 OCR 的段首（空行之后）为证，页内只认 AGES 段距。
  · 页码（页顶 10pt）丢；经文锚点 `<NNNNNN>`（6pt 红，诗 100 篇以上章号是十六进制如 <19E719>；第 7–16 章章题里
    有正文字号的）一律丢；同一高度被锚点劈成两截的合回一行。
  · 字色照录：红斜体 #800000 = 经文 → <em>；黑斜体 → <i>；藏青粗体 #000080（分点 1st / 2nd / 1.）
    → <b class="hd-nv">；其余粗体 → <b>；希腊文（Koine 体，蓝 #0000d4）→ <span class="hd-gk">，AGES 转写码
    按 convert_ages_greek 转 Unicode，再以录入本里字母相同的词定送气 / 重音。
  · 小型大写：段首大字母 16pt + 余字 9pt（`T`+`HIS`）、正文 12pt 中 9pt 的大写（S+AUL）→ <span class="hd-sc">。
  · 脚注号：9pt 红色升高的 `fN` → [^fN]；文末 FOOTNOTES 区 `ftN.` 条目 → notes。
  · 对齐：整段左缘 ≥ 40 且（多行，或单行以藏青分点起首）→ indent；行中心与版心中心差 < 25 → center。
  · 标题：CHAPTER N（蓝 24pt）/ PART N.（绿 16pt）/ ROMANS a:b-c（黑粗 12pt）均居中，记入下一条目的 heads。
  · p3–4 是 AGES 版加的现代 FOREWORD，不收；p906–907 AGES 出版说明丢。
结构：front（PREFACE、INTRODUCTION）→ chapters（同章分 PART 的合并；首个 `Ver.` 前是章首概述 introduction；
每个 `Ver. N.` 起 verse-N，`Ver. N-M` / `Vers. N, M.` 起 verses-N-M；节头那一段其余部分是 lemma，带 HTML 字色）→ back（CONCLUSION）。
每条目 paras 与 align 等长（'' / 'center' / 'indent'）。
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calvin_extract import convert_ages_greek   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'haldane_raw' / 'romans'
PDF = Path.home() / 'Documents' / '论文' / 'haldane' / 'haldane_romans_ages.pdf'
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else RAW / 'units.json'
FIRST, STOP = 5, 906
RED, NAVY, BLUE, GREEN = 0x800000, 0x000080, 0x0000d4, 0x006411
ANCHOR = re.compile(r'^<[0-9A-F]{6,8}>$')       # 诗篇 100 篇以上章号是十六进制：<19E719> = 诗 147:19
ANCHOR_ANY = re.compile(r'<[0-9A-F]{6,8}>')
PAGE_CENTER = 205          # 版心 26–385 的中点
PARA_GAP = 19


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def norm_words(html, n=8):
    s = re.sub(r'<[^>]+>|\[\^f\d+\]', ' ', html)
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    return ' '.join(re.findall(r"[a-z]+", s.lower())[:n])


# ── 证人：录入本的段首、希腊词 ──────────────────────────────────────
OLD = json.load(open(RAW / 'units_studylight.json', encoding='utf-8'))
OLD_STARTS = {norm_words(p) for c in OLD['chapters'] for e in c['entries'] for p in e['paras']}
OLD_STARTS |= {norm_words(e['lemma']) for c in OLD['chapters'] for e in c['entries'] if e['lemma']}
# 1874 第九版扫描 OCR（IA expositionofthee00halduoft）：段与段之间有空行。取「空行之后、且空行前一段以句末标点收尾、
# 不是页眉页码」的行作段首——跨页时判新段用（录入本自己多分了段，如 1:1「…Church. / From the period…」，不可作证）
SCAN = (RAW / 'src' / 'scan' / 'expositionofthee00halduoft_djvu.txt').read_text(encoding='utf-8')
SCAN_STARTS = set()
_blocks = [b.strip() for b in re.split(r'\n\s*\n', SCAN) if b.strip()]
for _prev, _b in zip(_blocks, _blocks[1:]):
    _last = _prev.split('\n')[-1].strip()
    if re.fullmatch(r'[\dIVXLC .,]+|[A-Z0-9 .,;:]{1,30}', _last):       # 页码 / 页眉
        continue
    if re.search(r'[.?!:’”\'"]\s*$', _last):
        SCAN_STARTS.add(norm_words(_b, 6))
OLD_GREEK = {}
for c in OLD['chapters']:
    for e in c['entries']:
        for p in e['paras'] + list(e['notes'].values()):
            for w in re.findall(r'[Ͱ-Ͽἀ-῿]+', p):
                bare = ''.join(ch for ch in unicodedata.normalize('NFD', w) if not unicodedata.combining(ch)).lower()
                OLD_GREEK.setdefault(bare, w)


def greek(t):
    out = []
    for tok in re.split(r'(\s+)', t):
        if not tok.strip():
            out.append(tok); continue
        u = convert_ages_greek(tok)
        core = re.sub(r'[^Ͱ-Ͽἀ-῿]', '', u)
        bare = ''.join(ch for ch in unicodedata.normalize('NFD', core) if not unicodedata.combining(ch)).lower()
        if core and bare in OLD_GREEK:
            w = OLD_GREEK[bare]
            u = u.replace(core, w[0].upper() + w[1:] if core[0].isupper() else w)
        out.append(u)
    return ''.join(out)


# ── 行 → 带样式的片段 ────────────────────────────────────────────────
def line_runs(line, body_size=12):
    """→ [(kind, text)]：t 正文 / em 红斜体 / i 黑斜体 / b 粗体 / nv 藏青粗体 / gk 希腊 / sc 小型大写 / f 脚注号"""
    out = []
    spans = [s for s in line['spans'] if s['text']]
    for k, s in enumerate(spans):
        t, st, size, col, font = s['text'], s['text'].strip(), s['size'], s['color'], s['font']
        if ANCHOR.match(st) or size < 7:                         # 全书 6pt 只用于锚点（常拆成 `451301` + `>` 两片）
            continue
        if ANCHOR_ANY.search(t):                                   # 第 7–16 章章题里锚点是正文字号、与题字同一 span
            t = ANCHOR_ANY.sub('', t); st = t.strip()
            if not st:
                continue
        if size < 10 and col == RED and re.fullmatch(r'f\d+', st):
            out.append(('f', st[1:])); continue
        if 'Koine' in font or ('Symbol' in font and col == BLUE):
            out.append(('gk', greek(t))); continue
        if 8 <= size < 10.5 and st and st.upper() == st and re.search(r'[A-Z]', st):
            out.append(('sc', t)); continue                         # 小型大写的小号部分
        if size >= 15 and k + 1 < len(spans) and len(st) == 1 and spans[k + 1]['size'] < 10.5:
            out.append(('t', t)); continue                          # 段首大字母，后接小型大写
        if 'Bold' in font:
            kind = 'nv' if col == NAVY else 'b'
        elif 'Italic' in font:
            kind = 'em' if col == RED else 'i'
        else:
            kind = 't'
        out.append((kind, t))
    return out


OPEN = {'em': '<em>', 'i': '<i>', 'b': '<b>', 'nv': '<b class="hd-nv">', 'gk': '<span class="hd-gk">',
        'sc': '<span class="hd-sc">'}
CLOSE = {'em': '</em>', 'i': '</i>', 'b': '</b>', 'nv': '</b>', 'gk': '</span>', 'sc': '</span>'}


def runs_html(runs):
    html, cur = [], None
    for kind, t in runs:
        if kind == 'f':
            if cur:
                html.append(CLOSE[cur]); cur = None
            html.append(f'[^f{t}]'); continue
        want = kind if kind in OPEN else None
        if want != cur and not (t.strip() == '' and cur):          # 空白不打断当前样式
            if cur:
                html.append(CLOSE[cur])
            if want:
                html.append(OPEN[want])
            cur = want
        html.append(esc(t))
    if cur:
        html.append(CLOSE[cur])
    s = ''.join(html)
    for k in OPEN:
        o, c = re.escape(OPEN[k]), re.escape(CLOSE[k])
        s = re.sub(o + r'(\s*)' + c, r'\1', s)
        s = re.sub(c + r'(\s*)' + o, r'\1', s)                    # 跨行同样式合并
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'(<(?:em|i|b)[^>]*>)\s+', r' \1', s)              # 空白移到标签外
    s = re.sub(r'\s+(</(?:em|i|b)>)', r'\1 ', s)
    return unicodedata.normalize('NFC', re.sub(r'\s+', ' ', s).strip())


def read_lines():
    """→ dict(p, x0, x1, y, size, color, runs, txt)，去页码，同高两截合一。"""
    doc = fitz.open(PDF)
    rows = []
    for p in range(FIRST, STOP):
        for b in doc[p].get_text('dict')['blocks']:
            for l in b.get('lines', []):
                sp = [s for s in l['spans'] if s['text'].strip()]
                if not sp:
                    continue
                txt = ANCHOR_ANY.sub('', ''.join(s['text'] for s in l['spans'] if s['size'] >= 7)).strip()
                if txt == str(p + 1) and round(max(s['size'] for s in sp)) == 10:
                    continue                                      # 页码（必须 = 本页印刷页码且 10pt；p330 首行「<470514>2」
                                                                  # 去锚点后只剩「2」，旧条件把它当页码删了）
                runs = line_runs(l)
                if not runs:
                    continue
                big = max(sp, key=lambda s: s['size'])
                x0, y0, x1, y1 = l['bbox']
                if rows and rows[-1]['p'] == p and abs(rows[-1]['y'] - y1) < 3 and x0 >= rows[-1]['x1'] - 4:
                    r = rows[-1]
                    r['runs'] += [('t', ' ')] + runs; r['txt'] += ' ' + txt; r['x1'] = x1
                    r['size'] = max(r['size'], big['size'])
                    continue
                rows.append(dict(p=p, x0=x0, x1=x1, y=y1, size=big['size'], color=big['color'], runs=runs, txt=txt))
    return rows


def is_heading(r):
    return (r['size'] >= 15 and r['color'] in (BLUE, GREEN) and r['x0'] > 60) or \
           (r['x0'] > 120 and re.fullmatch(r'ROMANS \d+:[\d-]+\.?', r['txt']))


def blocks(rows):
    """→ [('h', text) | ('p', runs, lines, page)]，lines 是该段各行 (x0, x1) 供判对齐，page 是起始页的印刷页码。"""
    out, cur, prev = [], None, None
    for r in rows:
        if is_heading(r):
            if cur:
                out.append(cur); cur = None
            out.append(('h', re.sub(r'\s+', ' ', r['txt']))); prev = None
            continue
        if cur is None or prev is None:
            new = True
        elif r['p'] != prev['p']:
            new = (bool(re.match(r'ft\d+\.', r['txt'])) or bool(re.match(r'Vers?\.\s*\d', r['txt']))
                   or (re.search(r'[.?!:’”)]\s*$', prev['txt']) is not None
                       and norm_words(runs_html(r['runs']), 6) in SCAN_STARTS))
        else:
            new = r['y'] - prev['y'] > PARA_GAP or bool(re.match(r'ft\d+\.(\s|$)', r['txt']))
        if new:
            if cur:
                out.append(cur)
            cur = ('p', list(r['runs']), [(r['x0'], r['x1'])], r['p'] + 1)     # 第 4 项：起始页（印刷页码 = 0 起页号 + 1）
        else:
            last = cur[1][-1] if cur[1] else None
            # AGES 是 Word 排版，行末没有自动断字：行尾的「-」都是真连字符 / 破折号，保留、与下行直接相接
            # （曾当断字删掉，把「anything- towards」接成「anythingtowards」，Gate X 查出）
            if not (last and last[0] != 'f' and last[1].endswith('-') and not last[1].endswith(' -')):
                cur[1].append(('t', ' '))
            cur[1].extend(r['runs'])
            cur[2].append((r['x0'], r['x1']))
        prev = r
    if cur:
        out.append(cur)
    return out


def align_of(lines, runs):
    """AGES 段落对齐：居中 / 缩进（整段左缘 ≥ 40）/ 左齐。前半本普通段落首行也缩到 x≈44，故单行段落只在
    以藏青分点（1. / 1st）起首时才算缩进列表项（如 2:17「1. Their bearing the name of Jew.」等六条，x=44）。"""
    lefts = [x0 for x0, _ in lines]
    if all(abs((x0 + x1) / 2 - PAGE_CENTER) < 25 and x0 > 45 for x0, x1 in lines):
        return 'center'
    if min(lefts) >= 40 and (len(lines) > 1 or (runs and runs[0][0] == 'nv')):
        return 'indent'
    return ''


# 节头变体（逐条实测）：`Ver. 1.` / `Ver. 27 —`（只有 `Ver. 2` 是粗体，`7` 是正文字）/ `Ver. 31:` / `Vers. 1, 2.` /
# `Ver. 14-15`；破折号有时排成黑斜体 <i>—</i>
def printed_num(s):
    m = re.search(r'\d+', s)
    return m.group(0) if m else ''


VER = re.compile(r'^<b>\s*(Vers?)\.?\s*(\d+)\s*(?:[-–,]\s*(\d+))?\s*[.:]?\s*,?\s*</b>(\d*)\s*[.:]?\s*'
                 r'(?:<i>\s*[—–-]+\s*</i>|[—–-]+)?\s*')
# AGES 自身的节号错印（录入本已改）：(章, lemma 开头, 应作的节)
VER_FIX = [(8, 'For they that are after the', 5)]   # 8:5 AGES 印作 Ver. 6.，紧接真 Ver. 6.


def build(items):
    u = {'front': [], 'chapters': [], 'back': [], 'notes': {}}
    sec, ch, entry, fn_cur, heads = None, None, None, None, []

    def new_entry(key, label, lemma=''):
        e = {'key': key, 'label': label, 'lemma': lemma, 'heads': list(heads), 'paras': [], 'align': [], 'pages': [],
             'notes': {}}
        heads.clear()
        return e

    for it in items:
        if it[0] == 'h':
            h = it[1].rstrip('.').upper()
            if h == 'FOOTNOTES':
                sec = 'fn'; continue
            m = re.fullmatch(r'CHAPTER (\d+)', h)
            if m:
                n = int(m.group(1))
                if not ch or ch['ch'] != n:
                    ch = {'ch': n, 'entries': []}
                    u['chapters'].append(ch)
                    heads.clear(); heads.append(it[1].strip())
                    entry = None
                else:
                    heads.append(it[1].strip())           # PART 2 前 AGES 重印的章题（1:16、3:21），照印
                sec = 'ch'; continue
            if h in ('PREFACE', 'INTRODUCTION', 'CONCLUSION'):
                sec = h.lower(); ch = None
                (u['back'] if sec == 'conclusion' else u['front']).append(
                    {'key': sec, 'label': h.title(), 'paras': [], 'align': [], 'pages': []})
                continue
            if h in ('EXPOSITION', 'THE END'):
                if h == 'THE END' and u['back']:
                    u['back'][-1]['paras'].append('THE END.'); u['back'][-1]['align'].append('center-end')
                    u['back'][-1]['pages'].append(u['back'][-1]['pages'][-1])
                continue
            heads.append(it[1].strip())                              # PART N. / ROMANS a:b-c
            continue
        html, al, pg = runs_html(it[1]), align_of(it[2], [r for r in it[1] if r[1].strip()]), it[3]
        if not html:
            continue
        if sec == 'fn':
            m = re.match(r'^(?:<[^>]+>)?ft(\d+)\.(?:</[^>]+>)?\s*(.*)$', html)
            if m:
                fn_cur = m.group(1); u['notes'][fn_cur] = m.group(2).strip()
            elif fn_cur:
                u['notes'][fn_cur] = (u['notes'][fn_cur] + ' ' + html).strip()
            continue
        if sec in ('preface', 'introduction', 'conclusion'):
            tgt = (u['back'] if sec == 'conclusion' else u['front'])[-1]
            tgt['paras'].append(html); tgt['align'].append(al); tgt['pages'].append(pg); continue
        if sec != 'ch':
            continue
        m = VER.match(html)
        if m:
            a, b2 = m.group(2) + m.group(4), m.group(3)
            rest = html[m.end():]
            lem_txt = re.sub(r'<[^>]+>', '', rest)
            for fc, start, real in VER_FIX:
                if ch['ch'] == fc and lem_txt.startswith(start):
                    u.setdefault('ver_fixes', []).append(f'{fc}:{real} (printed “Ver. {a}.” in the AGES edition)')
                    a = str(real)
            # AGES 里 `Ver. N. —` 那一段通常只印本节经文（注释另起段），整段即 lemma，保留红 / 黑字色。
            # 少数几处（3:27、6:6、11:30、13:12）经文与注释排成一段，注释照例以经文首句重提起头、有时与经文
            # 挤在同一个红斜体里：在红斜体内找经文开头 3 词的重提处断开；无重提则在首个红斜体收尾处断开。
            lemma, tail = rest.strip(), ''
            if len(re.sub(r'<[^>]+>', '', lemma)) > 600:
                em = re.match(r'^(.*?<em>)(.*?)(</em>)(.*)$', lemma, re.S)
                if em:
                    body = em.group(2)
                    words = re.sub(r'<[^>]+>', '', body).split()
                    k = body.find(' '.join(words[:3]), 10)
                    if k < 0:                                   # 重提只两词（6:6「Knowing this.」）：在后半段找
                        k = body.find(' '.join(words[:2]), len(body) // 2)
                    if k > 0:
                        lemma, tail = em.group(1) + body[:k].rstrip() + '</em>', '<em>' + body[k:] + '</em>' + em.group(4)
                    else:
                        lemma, tail = em.group(1) + body + '</em>', em.group(4).strip()
            entry = new_entry(f'verses-{a}-{b2}' if b2 else f'verse-{a}', f'Verses {a}–{b2}' if b2 else f'Verse {a}',
                              lemma)
            # 节号照 AGES 原印（Ver. 31 / Ver. 1: / Ver. 14, / Ver. 14, 15. / Ver. 19-22. / Vers. …）；8:5 编者改号
            printed = re.sub(r'<[^>]+>', '', m.group(0)).strip().rstrip('—–- ').strip()
            entry['ver'] = re.sub(r'\d+', a, printed, count=1) if printed_num(printed) != a else printed
            entry['lemma_page'] = pg
            ch['entries'].append(entry)
            if tail.strip():
                entry['paras'].append(tail.strip()); entry['align'].append(''); entry['pages'].append(pg)
            continue
        if entry is None:
            entry = new_entry('introduction', 'Introduction')
            ch['entries'].append(entry)
        if heads:                                                    # 条目中间冒出的 PART / ROMANS 标题
            entry.setdefault('mid_heads', []).append([len(entry['paras']), list(heads)]); heads.clear()
        entry['paras'].append(html); entry['align'].append(al); entry['pages'].append(pg)
    for c in u['chapters']:
        for e in c['entries']:
            for p in e['paras']:
                for k in re.findall(r'\[\^f(\d+)\]', p):
                    if k in u['notes']:
                        e['notes'][k] = u['notes'][k]
    return u


# AGES 转写码 convert_ages_greek 转不对的几处（J 粗气、w|= 带 iota 下标、混入拉丁字母的），按录入本已核对的
# 拼写定；罗 5:18 δικαιώματος AGES 也漏 μ（录入本同漏，2026-11 经用户同意补）。(原样, 改作, 应命中次数)
GREEK_FIX = [
    ('<span class="hd-gk">eF</span>’ <span class="hd-gk">ῳ=</span>', '<span class="hd-gk">ἐφ’ ᾧ</span>', 4),   # 脚注 29，notes 与条目下各存一份
    ('<span class="hd-gk">di</span>’ <span class="hd-gk">εJνός δικαιώατος</span>',
     '<span class="hd-gk">δι’ ἑνός δικαιώματος</span>', 1),
    ('υJπακοή', 'ὑπακοή', 2),
    ('διkαιοσυ&gt;νh ', 'δικαιοσύνη ', 1),
    ('ποι&gt;ηµα', 'ποίημα', 1),
    ('cρο&gt;νοi αιω&gt;νioi ', 'χρόνοι αἰώνιοι ', 1),
    ('Δικαιοσύνη de... Ἰησοῦ', 'Δικαιοσύνη δὲ… Ἰησοῦ', 1),
    ('<span class="hd-gk">καγώ</span>', '<span class="hd-gk">κἀγώ</span>', 1),
    ('<span class="hd-gk">δικαιοσύν</span>,', '<span class="hd-gk">δικαιοσύνη</span>,', 1),   # AGES 漏末字母 h
]


# AGES 段尾标点错（1874 第九版扫描本为证），Gate 5g 据此把下一段误报为跨页断句：(章, 段尾原样, 改作, 说明)
TAIL_FIX = [
    (8, 'the glory of the kingdom of heaven,', 'the glory of the kingdom of heaven.', '8:24 “heaven.” (AGES: comma)'),
    (15, 'whom we acknowledge that Christ has received', 'whom we acknowledge that Christ has received.',
     '15:5 “received.” (AGES omits the full stop)'),
]


def fix_tails(u):
    for ch, a, b, note in TAIL_FIX:
        hits = [(e, i) for e in u['chapters'][ch - 1]['entries'] for i, x in enumerate(e['paras']) if x.endswith(a)]
        if len(hits) != 1:
            raise SystemExit(f'TAIL_FIX 第 {ch} 章「{a}」命中 {len(hits)} 段，应为 1')
        e, i = hits[0]
        e['paras'][i] = e['paras'][i][:-len(a)] + b
        u.setdefault('ed_fixes', []).append(note)
    return u


def fix_greek(u):
    s = json.dumps(u, ensure_ascii=False)
    for a, b, n in GREEK_FIX:
        k = s.count(json.dumps(a, ensure_ascii=False)[1:-1])
        if k != n:
            raise SystemExit(f'GREEK_FIX「{a}」命中 {k} 次，应为 {n}')
        s = s.replace(json.dumps(a, ensure_ascii=False)[1:-1], json.dumps(b, ensure_ascii=False)[1:-1])
    return json.loads(s)


# ── 出口：中间 HTML → skill 规定的 markdown + 行内色（pdf-pipeline 01 §9 / hodge 产物同款）────────────
# 红斜体 `<span style="color:#800000">*X*</span>`、黑斜体 `*X*`、粗体 `**X**`、藏青粗体 `<span style="color:#000080">**X**</span>`、
# 希腊文 `<span style="color:#0000d4">X</span>`、小型大写 `<span style="font-size:.76em">X</span>`。Gate T 按这套口径数字形。
MD = [(r'<em>(.*?)</em>', r'<span style="color:#800000">*\1*</span>'),
      (r'<i>(.*?)</i>', r'*\1*'),
      (r'<b class="hd-nv">(.*?)</b>', r'<span style="color:#000080">**\1**</span>'),
      (r'<b>(.*?)</b>', r'**\1**'),
      (r'<span class="hd-gk">(.*?)</span>', r'<span style="color:#0000d4">\1</span>'),
      (r'<span class="hd-sc">(.*?)</span>', r'<span style="font-size:.76em">\1</span>')]


def to_md(s):
    # 只含标点的斜体片段（单独一个引号 `“`、斜体破折号 `—`）去掉斜体：视觉无别，且 `*“*` 正是 Gate 1 的 split italic
    s = re.sub(r'<(em|i)>([^\w<>]*)</\1>', r'\2', s)
    for a, b in MD:
        s = re.sub(a, b, s)
    s = s.replace('****', '')                                     # principles §0.4：紧邻粗体合并
    return s


def md_all(u):
    for c in u['chapters']:
        for e in c['entries']:
            e['lemma'] = to_md(e['lemma'])
            e['paras'] = [to_md(x) for x in e['paras']]
            e['notes'] = {k: to_md(v) for k, v in e['notes'].items()}
    for f in u['front'] + u['back']:
        f['paras'] = [to_md(x) for x in f['paras']]
    u['notes'] = {k: to_md(v) for k, v in u['notes'].items()}
    return u


def main():
    u = md_all(fix_tails(fix_greek(build(blocks(read_lines())))))
    OUT.write_text(json.dumps(u, ensure_ascii=False, indent=1), encoding='utf-8')
    n_e = sum(len(c['entries']) for c in u['chapters'])
    n_p = sum(len(e['paras']) for c in u['chapters'] for e in c['entries'])
    print(f'front {[f["key"] for f in u["front"]]} chapters {len(u["chapters"])} entries {n_e} paras {n_p} '
          f'back {[b["key"] for b in u["back"]]} notes {len(u["notes"])} → {OUT}')


if __name__ == '__main__':
    main()
