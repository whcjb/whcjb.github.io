#!/usr/bin/env python3
"""福特《路加福音讲义》英文版：foote_raw/luke/en_chapters/NNN.md → foote/luke/*.md

    python3 scripts/extract_foote.py                 # ABBYY → work/md/
    cp foote_raw/luke/work/md/*.md foote_raw/luke/en_chapters/
    python3 scripts/repair_alexander_ocr.py foote    # 第 ① 层
    python3 scripts/foote_spans.py --apply           # 两条字流按片段换（ABBYY 读废的一截换 tesseract，§3.2d）
    python3 scripts/adjudicate_foote_ocr.py --apply  # 第 ② 层：ed3 证人(Lect.1–66) → tesseract 证人(全书)
    python3 scripts/foote_symbols.py --apply         # 游离符号逐个取证（symbol_fixes.tsv）
    python3 scripts/adjudicate_foote_ocr.py --apply --vlm  # 第 ③ 层：整页转录＋tesseract 同位一致（vlm_fixes.tsv）
    python3 scripts/foote_punct.py --apply           # 第 ③ 层·标点：逐缝两家一致（punct_fixes.tsv）
    python3 scripts/foote_glyphs.py --apply          # 撇号 / æ 连写 / 多余斜体 / 断词（glyph_fixes.tsv）
    python3 scripts/foote_image_check.py --apply     # 单证人残留按页一次看图定夺（image_fixes.tsv）
    python3 scripts/publish_foote_en.py              # 试跑（自检）
    python3 scripts/publish_foote_en.py --apply

页面：
  lecture-1 … lecture-137   一讲一页（不用裸数字：扫描器把 <N>.md 当路加福音第 N 章）
  1 … 24                     章目录页（对照抽屉的 __CH__ 指向它）：本章所涉各讲
底本与各层处理见 foote_raw/luke/PROVENANCE.md。正文目前只过了第 ① 层，残字照留。
date 一律沿用 en_meta.json 里的原值，新页才写当前真实时间。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'foote_raw' / 'luke'
SRC = RAW / 'en_chapters'
OUT = ROOT / 'foote' / 'luke'
META = RAW / 'en_meta.json'

BOOK_ID = 'luke'
BOOK_NAME = 'Foote on Luke'
AUTHOR = 'James Foote'
FN_MARK = ''
VOLS = {1: (1, 40), 2: (41, 90), 3: (91, 137)}

# 各讲所讲经文。印本讲题下的出处 OCR 读花甚多（`V. ML`、`XI. 1-9` 实为 IX、`XXr. 26-88`），
# 按前后讲连续性定；拿不准的四讲（15、42、91、114）以经文段里印出的末节号核过。
# 「续讲」（82、83、88、94、113、117、137）讲题下排小标题、不重印经文，沿用上一讲的范围。
VERSES = {
    1: '1:1-4', 2: '1:5-25', 3: '1:26-38', 4: '1:39-56', 5: '1:57-66', 6: '1:67-80', 7: '2:1-7',
    8: '2:8-20', 9: '2:21-33', 10: '2:34-35', 11: '2:36-52', 12: '3:1-14', 13: '3:15-20', 14: '3:21-38',
    15: '4:1-13', 16: '4:14-22', 17: '4:22-32', 18: '4:33-44', 19: '5:1-11', 20: '5:12-15', 21: '5:16-26',
    22: '5:27-32', 23: '5:33-39', 24: '6:1-11', 25: '6:12-14', 26: '6:14', 27: '6:14-16', 28: '6:17-26',
    29: '6:27-36', 30: '6:37-40', 31: '6:41-45', 32: '6:46-49', 33: '7:1-10', 34: '7:11-17', 35: '7:18-23',
    36: '7:24-35', 37: '7:36-50', 38: '8:1-3', 39: '8:4-15', 40: '8:16-21', 41: '8:22-25', 42: '8:26-39',
    43: '8:40-56', 44: '9:1-9', 45: '9:10-17', 46: '9:18-27', 47: '9:28-36', 48: '9:37-45', 49: '9:46-50',
    50: '9:51-56', 51: '9:57-62', 52: '10:1-20', 53: '10:21-24', 54: '10:25-37', 55: '10:38-42',
    56: '11:1-4', 57: '11:5-13', 58: '11:14-26', 59: '11:27-28', 60: '11:29-36', 61: '11:37-44',
    62: '11:45-54', 63: '12:1-9', 64: '12:10-12', 65: '12:13-21', 66: '12:22-31', 67: '12:32-34',
    68: '12:35-48', 69: '12:49-53', 70: '12:54-59', 71: '13:1-5', 72: '13:6-9', 73: '13:10-17',
    74: '13:18-21', 75: '13:22-30', 76: '13:31-35', 77: '14:1-11', 78: '14:12-24', 79: '14:25-35',
    80: '15:1-10', 81: '15:11-32', 82: '15:11-32', 83: '15:11-32', 84: '16:1-8', 85: '16:9-13',
    86: '16:14-18', 87: '16:19-31', 88: '16:19-31', 89: '17:1-10', 90: '17:11-19', 91: '17:20-37',
    92: '18:1-8', 93: '18:9-14', 94: '18:9-14', 95: '18:15-17', 96: '18:18-27', 97: '18:28-34',
    98: '18:35-43', 99: '19:1-10', 100: '19:11-27', 101: '19:28-40', 102: '19:41-44', 103: '19:45-48',
    104: '20:1-8', 105: '20:9-18', 106: '20:19-26', 107: '20:27-40', 108: '20:41-47', 109: '21:1-4',
    110: '21:5-11', 111: '21:12-19', 112: '21:20-24', 113: '21:20-24', 114: '21:25-38', 115: '22:1-18',
    116: '22:19-20', 117: '22:19-20', 118: '22:21-30', 119: '22:31-38', 120: '22:39-46', 121: '22:47-53',
    122: '22:54-62', 123: '22:63-71', 124: '23:1-12', 125: '23:13-25', 126: '23:26-31', 127: '23:32-34',
    128: '23:35-43', 129: '23:44-45', 130: '23:46-49', 131: '23:50-56', 132: '24:1-12', 133: '24:13-27',
    134: '24:28-35', 135: '24:36-49', 136: '24:50-53', 137: '24:50-53',
}
NV = {1: 80, 2: 52, 3: 38, 4: 44, 5: 39, 6: 49, 7: 50, 8: 56, 9: 62, 10: 42, 11: 54, 12: 59,
      13: 35, 14: 35, 15: 32, 16: 31, 17: 37, 18: 43, 19: 48, 20: 47, 21: 38, 22: 71, 23: 56, 24: 53}


def roman(n):
    vals = [(100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
    out = ''
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


def expand(spec):
    c, _, vv = spec.partition(':')
    c = int(c)
    a, _, b = vv.partition('-')
    return [(c, v) for v in range(int(a), int(b or a) + 1)]


def vlabel(spec):
    return 'Luke ' + spec.replace('-', '–')


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


# ── 读 en_chapters ────────────────────────────────────────────

def parse(path):
    """extract_foote.to_md 的格式 → dict(head, passage, paras[(page, text)], notes[(page, text)])"""
    text = path.read_text(encoding='utf-8')
    body, _, notes_part = text.partition('\n---\n')
    m = re.search(r'^\*\*(.*?)\*\*$', body, re.M)
    head = m.group(1) if m else ''
    m = re.search(r'^> (.*)$', body, re.M)
    passage = m.group(1) if m else ''
    # 只有带 PAGE 标记的块才进正文；不带标记的块会被静默丢掉（2026-11-13 第 122 讲手加分段吞了 3800 字），报错不放行
    loose = [b.strip()[:60] for b in body.split('\n\n')
             if b.strip() and not b.lstrip().startswith(('<!-- PAGE', '**', '>', '#'))]
    if loose:
        raise SystemExit(f'{path.name}: 段落缺页码标记，发布会丢掉：{loose}')
    paras = [(pg, t.strip()) for pg, t in re.findall(r'<!-- PAGE (\S*) -->\n(.*?)(?=\n\n|\Z)', body, re.S)]
    # 各段第一个注号哨兵在本讲正文里的序号（fn_symbols.json 按正文全序记；未发布的段里也可能有哨兵）
    pord = [body[:m.start(2)].count(FN_MARK) for m in re.finditer(r'<!-- PAGE (\S*) -->\n(.*?)(?=\n\n|\Z)', body, re.S)]
    m = re.search(r'^> (.*)$', body, re.M)
    sord = body[:m.start(1)].count(FN_MARK) if m else 0
    notes = [(pg, t.strip()) for pg, t in re.findall(r'<!-- NOTE p\.(\S*) --> (.*?)(?=\n\n|\Z)', notes_part, re.S)]
    return dict(head=head, passage=passage, paras=paras, pord=pord, sord=sord, notes=notes)


RE_OL = re.compile(r'^(\d+)\. ')


def md_escape(t):
    """OCR 正文 → 安全的 markdown 行内文本。

    - 竖线一律删（skill §4.4：kramdown 会把整段连同邻段框成表格；本书正文不存在真竖线）
    - `<` 转义，行首 `# > + -` 与 `1. ` 转义（不许变成标题／引用／列表）
    - 脚注哨兵原样留着，由 link_notes 换成带链接的上标
    """
    t = t.replace('|', '')
    t = t.replace('<', '&lt;')
    t = re.sub(r'(?<!\\)_', r'\\_', t)
    t = RE_OL.sub(r'\1\\. ', t)
    t = re.sub(r'^([#>+-]) ', r'\\\1 ', t)
    t = re.sub(r' {2,}', ' ', t)
    return t


SEQ = ['*', '†', '‡', '§', '‖', '¶']
NSYM = {'♦': '*', '*': '*', '†': '†', '‡': '‡', '§': '§', '‖': '‖', '¶': '¶'}


def pgnum(p):
    m = re.match(r'\d+', p or '')
    return int(m.group()) if m else -1


def link_notes(n, blocks, notes, tags):
    """正文注号哨兵 ↔ 讲末注条，双向链接，上标显示该条的印本符号（* † ‡ § ‖ ¶）；注区 ♦ 显示成 *。

    blocks：[(该块第一个哨兵在本讲正文里的序号, 文本)]；notes：[(页, 文本)]；tags：fn_symbols.json 本讲一行，
    [[页, 符号] | null]（链条按转录同位注号定的）。按阅读顺序保序配对（最长公共子序列），一对成立须号与注
    同页同符号。配不上的号（转录同位无注号或定不了符号、或那条注 OCR 丢了）不链、上标作 *；配不上的注不回链。"""
    marks = []
    for k0, b in blocks:
        marks += [tuple(tags[k0 + k]) if k0 + k < len(tags) and tags[k0 + k] else None
                  for k in range(b.count(FN_MARK))]
    # 一条里并了几条注的（`♦ Isa. xxi. 10. † Jer. xv. 7.`）在干净符号处拆开；符号 OCR 读花的（`•` `t` `*X*`）
    # 按本页次序推：印本每页注号依次为 * † ‡ § ‖ ¶
    split = [(pg, x) for pg, t in notes for x in re.split(r'\s+(?=[†‡§‖¶] )', t)]
    syms, prev = [], {}
    for pg, t in split:
        c = t[:1]
        if c in NSYM:
            sym, body_ = NSYM[c], t[1:].lstrip()
        else:
            k = SEQ.index(prev[pg]) + 1 if pg in prev and prev[pg] in SEQ[:-1] else 0
            sym, body_ = SEQ[k], t
        prev[pg] = sym
        syms.append((pg, sym, body_))
    M, K = len(marks), len(syms)
    ok = lambda i, j: marks[i] is not None and marks[i][0] == syms[j][0] and NSYM.get(marks[i][1]) == syms[j][1]
    L = [[0] * (K + 1) for _ in range(M + 1)]
    for i in range(M - 1, -1, -1):
        for j in range(K - 1, -1, -1):
            L[i][j] = max(L[i + 1][j], L[i][j + 1], L[i + 1][j + 1] + 1 if ok(i, j) else 0)
    pair, i, j = {}, 0, 0
    while i < M and j < K:
        if ok(i, j) and L[i][j] == L[i + 1][j + 1] + 1:
            pair[i] = j
            i, j = i + 1, j + 1
        elif L[i + 1][j] >= L[i][j + 1]:
            i += 1
        else:
            j += 1
    back = {j: i for i, j in pair.items()}
    it = iter(range(M))

    def ref(_):
        i = next(it)
        if i not in pair:
            return '<sup class="ft-fn">&#42;</sup>'
        j = pair[i]
        sym = syms[j][1].replace('*', '&#42;')
        return f'<sup class="ft-fn"><a href="#fn-{n}-{j + 1}" id="fnref-{n}-{j + 1}">{sym}</a></sup>'
    out = [re.sub(FN_MARK, ref, b) for _, b in blocks]
    nl = []
    for j, (_, sym, t) in enumerate(syms):
        s_ = (sym or '*').replace('*', '&#42;')
        if j in back:
            nl.append(f'<a class="ft-nsym" href="#fnref-{n}-{j + 1}" id="fn-{n}-{j + 1}">{s_}</a> {t}')
        else:
            nl.append(f'{s_} {t}' if sym else t)
    return out, nl, len(pair), M, K


def passage_md(p):
    """经文段：剥掉段首 OCR 噪点（`*^*` `"` `•*` 等开引号残形），节号上标。"""
    p = re.sub(r'^[^A-Za-z]{0,8}(?=[A-Z])', '', p.replace('\\*', ''))
    p = md_escape(p)
    return re.sub(r'(?<=[\s;:,.?!])(\d{1,2})\. (?=[A-Z(])', r'<sup class="ft-vn">\1</sup>', p)


# ── 组页 ──────────────────────────────────────────────────────

LINKS = []   # (讲, 配上, 号, 注)
FNSYM_PATH = RAW / 'fn_symbols.json'   # foote_fnmark_check.py --symbols 产出（链条最末）
FNSYM = json.loads(FNSYM_PATH.read_text(encoding='utf-8')) if FNSYM_PATH.exists() else {}


def build():
    pages = []
    seen = set()
    for n in range(1, 138):
        u = parse(SRC / f'{n:03d}.md')
        spec = VERSES[n]
        vv = expand(spec)
        vol = next(v for v, (a, b) in VOLS.items() if a <= n <= b)
        out = [f'<h2 class="ft-head">{vlabel(spec)}</h2>']
        cont = not re.match(r'^\W{0,3}L', u['head'] or '') or n in (82, 83, 88, 94, 113, 117, 137)
        if u['passage'].strip():
            if re.match(r'^[^a-z]{8,}$', re.sub(r'[^A-Za-z .]', '', u['passage'][:40])) and cont:
                # 续讲：讲题下的小标题（全大写），不是经文
                out.append(f'<p class="ft-sub">{md_escape(u["passage"])}</p>')
            else:
                out.append('<div class="ft-text" markdown="1">\n\n' + passage_md(u['passage']) + '\n\n</div>')
        anchors = ''.join(f'\n\n<div class="commentary-anchor" id="{BOOK_ID}-{c}-{v}"></div>'
                          for c, v in vv if (c, v) not in seen)
        seen.update(vv)
        if anchors:
            out.append(anchors.strip())
        blocks = [(u['sord'], b) for b in out] + [(k, md_escape(t)) for (pg, t), k in zip(u['paras'], u['pord'])]
        out, notes, *st = link_notes(n, blocks, [(pg, md_escape(t)) for pg, t in u['notes']], FNSYM.get(str(n), []))
        LINKS.append((n, *st))
        if notes:
            nn = ['<div class="ft-notes" markdown="1">', '']
            for t in notes:
                nn += [t, '']
            nn.append('</div>')
            out.append('\n'.join(nn))
        pages.append(dict(slug=f'lecture-{n}', title=f'Lecture {roman(n)}', label=f'Lecture {roman(n)}',
                          subtitle=f'{AUTHOR} · {vlabel(spec)}', body='\n\n'.join(out), n=n, vol=vol,
                          ch=vv[0][0], vv=vv, spec=spec, start=u['paras'][0][0] if u['paras'] else ''))
    missing = [(c, v) for c in NV for v in range(1, NV[c] + 1) if (c, v) not in seen]
    # 三卷扉页：照原书影像手排（skill §5.6），不走抽取
    front = []
    for v in (1, 2, 3):
        mp = RAW / 'manual_pages' / f'title-{v}.html'
        front.append(dict(slug=f'title-{v}', title=f'Title Page · Vol. {roman(v)}', label=f'Title Page, Vol. {roman(v)}',
                          subtitle='Second edition, Edinburgh: John Johnstone, 1849',
                          body=mp.read_text(encoding='utf-8'), vol=v, front=True))
    return front + pages, missing


def fm_nav(pg, key):
    o = pg.get(key)
    if not o:
        return []
    return [f'{key}_url: "/foote/{BOOK_ID}/{o["slug"]}/"', f'{key}_label: "{o["label"]}"']


def yq(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def chapter_pages(pages, meta, stamp):
    out = []
    for c in range(1, 25):
        lst = [p for p in pages if not p.get('front') and any(cc == c for cc, _ in p['vv'])]
        meta.setdefault(str(c), stamp)
        fm = ['---', 'layout: foote-chapter', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
              f'title: "Luke {c}"', f'subtitle: "{AUTHOR}"', f'date: {meta[str(c)]}', f'chapter: {c}',
              'verse_from: 1', f'verse_to: {NV[c]}']
        if c > 1:
            fm += [f'prev_url: "/foote/{BOOK_ID}/{c - 1}/"', f'prev_label: "Luke {c - 1}"']
        if c < 24:
            fm += [f'next_url: "/foote/{BOOK_ID}/{c + 1}/"', f'next_label: "Luke {c + 1}"']
        fm.append('---')
        items = '\n'.join(
            f'<li><a href="{{{{ site.baseurl }}}}/foote/{BOOK_ID}/{p["slug"]}/">{p["title"]}'
            f'<span class="ft-ref">{vlabel(p["spec"])}</span></a></li>' for p in lst)
        out.append((str(c), '\n'.join(fm) + '\n\n<ul class="ft-chtoc">\n' + items + '\n</ul>\n'))
    return out


def build_index(pages):
    out = ['---', 'layout: foote-book', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
           f'title: "{BOOK_NAME}"', f'author: "{AUTHOR}, A.M., Minister of the Free East Church, Aberdeen"',
           'edition: "Lectures on the Gospel according to Luke · second edition, 3 vols., Edinburgh: '
           'John Johnstone (vol. I preface dated Aberdeen, August 1838)"',
           '---', '']

    def li(p):
        return (f'  <li><a href="{{{{ site.baseurl }}}}/foote/{BOOK_ID}/{p["slug"]}/">{p["title"]}'
                f'<small>{vlabel(p["spec"])}</small></a></li>')
    for v, (a, b) in VOLS.items():
        out.append(f'<h2 class="ft-group">Volume {roman(v)} · Lectures {roman(a)}–{roman(b)}</h2>')
        out.append(f'<p class="ft-part-sub"><a href="{{{{ site.baseurl }}}}/foote/{BOOK_ID}/title-{v}/">'
                   f'Title page of Volume {roman(v)}</a></p>')
        out.append('<ul class="ft-toc ft-toc-sm">')
        out += [li(p) for p in pages if p['vol'] == v and not p.get('front')]
        out.append('</ul>')
    out.append('<h2 class="ft-group">By Chapter</h2>')
    out.append('<ul class="ft-chgrid">')
    out += [f'  <li><a href="{{{{ site.baseurl }}}}/foote/{BOOK_ID}/{c}/">Luke {c}</a></li>' for c in range(1, 25)]
    out.append('</ul>')
    out.append('<div class="ft-note">')
    out.append('<p><b>About this text.</b> James Foote preached these 137 lectures to his congregation in '
               'Aberdeen and afterwards expanded them for the press; they expound the whole of Luke\'s Gospel, '
               'each lecture opening with the passage in the Authorised Version. The text here is taken from '
               'the OCR of the second-edition volumes scanned by Google from the Bodleian copy (Internet Archive '
               '<i>lecturesongospe03footgoog</i>, <i>…02footgoog</i>, <i>…00footgoog</i>). '
               '<b>It is a working text:</b> systematic misreadings (ligatures, broken letters) have been '
               'corrected by rule, but scattered OCR errors remain, especially in Greek, Latin and footnote '
               'references, and are being corrected against the page images.</p>')
    out.append('<p class="ft-note-zh"><b>文本说明。</b>福特在阿伯丁向会众逐段宣讲路加福音，后扩写成书，共 137 讲，'
               '每讲先列钦定本经文。本页正文取自 Google 扫描的牛津大学藏第 2 版三卷 OCR。'
               '<b>目前是校勘中的工作本：</b>成套的连字误读、残字已按规则改正，零星 OCR 错字仍在，'
               '希腊文、拉丁文与脚注出处尤多，正对照页面影像逐步校正。</p>')
    out.append('</div>')
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    pages, missing = build()
    print(f'{len(pages)} 讲；未覆盖经节 {len(missing)} {missing[:12]}', file=sys.stderr)
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    stamp = now()
    for i, pg in enumerate(pages):
        pg['prev'] = pages[i - 1] if i else None
        pg['next'] = pages[i + 1] if i + 1 < len(pages) else None
    if not a.apply:
        print('试跑完毕（--apply 写入）', file=sys.stderr)
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for pg in pages:
        slug = pg['slug']
        meta.setdefault(slug, stamp)
        fm = ['---', 'layout: foote-chapter', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
              f'title: {yq(pg["title"])}', f'subtitle: {yq(pg["subtitle"])}', f'date: {meta[slug]}']
        if not pg.get('front'):
            fm += [f'chapter: {pg["ch"]}', f'lecture: {pg["n"]}']
        fm += fm_nav(pg, 'prev') + fm_nav(pg, 'next')
        if (OUT / 'zh' / f'{slug}.md').exists():
            fm.append(f'zh_url: "/foote/{BOOK_ID}/zh/{slug}/"')
        fm.append('---')
        (OUT / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + pg['body'] + '\n', encoding='utf-8')
    for slug, text in chapter_pages(pages, meta, stamp):
        (OUT / f'{slug}.md').write_text(text, encoding='utf-8')
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / 'en').mkdir(exist_ok=True)
    (OUT / 'en' / 'index.html').write_text(build_index(pages), encoding='utf-8')
    if not (OUT / 'zh').exists():
        (OUT / 'index.html').write_text(build_index(pages), encoding='utf-8')
    print(f'写入 {len(pages)} 讲 + 章目录 24 页 → {OUT}', file=sys.stderr)
    pm, mk, nt = (sum(x[k] for x in LINKS) for k in (1, 2, 3))
    print(f'注号链接：配上 {pm}／正文注号 {mk}／注条 {nt}', file=sys.stderr)


if __name__ == '__main__':
    main()
