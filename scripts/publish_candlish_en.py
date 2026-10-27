#!/usr/bin/env python3
"""坎德利什《约翰一书讲解》英文版：candlish_raw/1john/units.json（+ 修正表、脚注表）→ candlish/1john/*.md

    python3 scripts/extract_candlish.py           # PDF → units.json
    python3 scripts/candlish_build_notes.py       # e-Sword 本脚注 → notes.json（定稿已入库，一般不用重跑）
    python3 scripts/publish_candlish_en.py        # 试跑（自检）
    python3 scripts/publish_candlish_en.py --apply

页面：
  lecture-1 … lecture-46   一讲一页（不用裸数字：扫描器把 <N>.md 当约翰一书第 N 章）
  1 … 5                     章目录页（对照抽屉的 __CH__ 指向它）：本章所涉各讲
  contents / preface-2 / preface-1
底本处理（均见 candlish_raw/1john/PROVENANCE.md）：
  - 跨页接缝（extract 留的 JOIN 记号）：接缝后的文字是 e-Sword 本某段的开头 → 分段，否则接上；
  - manual_fixes.tsv 逐条落，每条须恰好命中 1 次；
  - 脚注号 `*`/`†` → kramdown 脚注，正文取 notes.json；两份录入本都缺的标 .cd-lost。
date 一律沿用 en_meta.json 里的原值，新页才写当前真实时间。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import align_candlish as A  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'candlish_raw' / '1john'
OUT = ROOT / 'candlish' / '1john'
META = RAW / 'en_meta.json'

BOOK_ID = '1john'
BOOK_NAME = 'Candlish on 1 John'
AUTHOR = 'Robert S. Candlish'
JOIN = '\n⁣'

ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI',
         'XVII', 'XVIII', 'XIX', 'XX', 'XXI', 'XXII', 'XXIII', 'XXIV', 'XXV', 'XXVI', 'XXVII', 'XXVIII', 'XXIX',
         'XXX', 'XXXI', 'XXXII', 'XXXIII', 'XXXIV', 'XXXV', 'XXXVI', 'XXXVII', 'XXXVIII', 'XXXIX', 'XL', 'XLI',
         'XLII', 'XLIII', 'XLIV', 'XLV', 'XLVI']

# 各讲所讲经文（据题记末尾的出处；「3:6 and 9」只取所举两节（中间两节作者明言留待下一讲）；「5:6 and 8」取 6–8（第 7 节作者认为非原文，脚注里讨论的就是它））
VERSES = {
    'I': '1:1-3', 'II': '1:4', 'III': '1:5-7', 'IV': '1:8-10', 'V': '2:1', 'VI': '2:1-2', 'VII': '2:3-5',
    'VIII': '2:6', 'IX': '2:7-8', 'X': '2:9-11', 'XI': '2:12-14', 'XII': '2:15-16', 'XIII': '2:17',
    'XIV': '2:18-20', 'XV': '2:21-23', 'XVI': '2:24-25', 'XVII': '2:26-28', 'XVIII': '2:29-3:1',
    'XIX': '2:29-3:2', 'XX': '3:2-4', 'XXI': '3:4-6', 'XXII': '3:6,3:9', 'XXIII': '3:7-8', 'XXIV': '3:10-12',
    'XXV': '3:13-16', 'XXVI': '3:17-21', 'XXVII': '3:22-23', 'XXVIII': '3:24-4:1', 'XXIX': '3:24-4:4',
    'XXX': '4:4-6', 'XXXI': '4:7-10', 'XXXII': '4:10-12', 'XXXIII': '4:13-16', 'XXXIV': '4:17-19',
    'XXXV': '4:20-5:3', 'XXXVI': '5:2-3', 'XXXVII': '5:4-5', 'XXXVIII': '5:6-8', 'XXXIX': '5:9-10',
    'XL': '5:11-12', 'XLI': '5:13-15', 'XLII': '5:16-17', 'XLIII': '5:17-18', 'XLIV': '5:18-19',
    'XLV': '5:20', 'XLVI': '5:20-21',
}
NV = {1: 10, 2: 29, 3: 24, 4: 21, 5: 21}

# 部分（原书目录的称呼）与各部分第一讲
PARTS = [('I', 'Preliminary Chapters', 'General Aim of the Book'),
         ('III', 'Part First', 'Primary Condition of the Divine Fellowship — Light'),
         ('XVIII', 'Part Second', 'Intermediate Condition of the Divine Fellowship — Righteousness'),
         ('XXXI', 'Part Third', 'Ultimate Condition of the Divine Fellowship — Love'),
         ('XXXVI', 'Part Fourth', 'The Divine Fellowship of Light, Righteousness, and Love, '
                                  'Overcoming the World and Its Prince')]


def expand(spec):
    out = []
    for part in spec.split(','):
        a, _, b = part.partition('-')
        c1, v1 = map(int, a.split(':'))
        if not b:
            out.append((c1, v1))
            continue
        c2, v2 = (map(int, b.split(':')) if ':' in b else (c1, int(b)))
        c, v = c1, v1
        while (c, v) <= (c2, v2):
            out.append((c, v))
            v += 1
            if v > NV[c]:
                c, v = c + 1, 1
    return out


def vlabel(spec):
    return '1 John ' + spec.replace('-', '–').replace(',', ', ')


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


# ── 底本文字处理 ──────────────────────────────────────────────

def norm7(s):
    return ' '.join(re.findall(r'[a-z0-9]+', s.lower())[:7])


def resolve_joins(units, cc_starts, log):
    """JOIN 记号：接缝后是 e-Sword 本的段首（或目录的下一条「XXX.」）→ 分段，否则接上。"""
    def fix(lst):
        out = []
        for p in lst:
            pieces = p.split(JOIN)
            cur = pieces[0]
            for nxt in pieces[1:]:
                if norm7(nxt) in cc_starts or re.match(r'[IVXL]+\. ', nxt):
                    out.append(cur)
                    cur = nxt
                    log['split'] += 1
                else:
                    cur += '\n' + nxt
                    log['joined'] += 1
            out.append(cur)
        return out
    for u in units:
        if 'paras' in u:
            u['epi'] = fix(u['epi'])
            u['paras'] = fix(u['paras'])


def apply_fixes(units, log):
    key = {u.get('num') or u['title']: u for u in units if 'paras' in u}
    for ln in (RAW / 'manual_fixes.tsv').read_text(encoding='utf-8').splitlines():
        if not ln.strip() or ln.startswith('#'):
            continue
        unit, old, new, _why = ln.split('\t')
        u = key[unit]
        hits = 0
        for f in ('epi', 'paras'):
            for i, p in enumerate(u[f]):
                flat = flatten(p)
                if old in flat:
                    hits += flat.count(old)
                    u[f][i] = flat.replace(old, new)
        if hits != 1:
            raise SystemExit(f'manual_fixes: {unit} 「{old}」命中 {hits} 次（应为 1）')
        log['fixes'] += 1


def flatten(p):
    """行与行之间：行尾是连字符或破折号的直接相接，否则补一个空格。"""
    lines = p.split('\n')
    out = lines[0]
    for ln in lines[1:]:
        out += ln if out.endswith(('-', '—')) else ' ' + ln
    return re.sub(r' {2,}', ' ', out).strip()


RE_OL = re.compile(r'^(\d+)\. ')


def md_escape(t):
    t = t.replace('\\', '\\\\').replace('_', '\\_').replace('<', '&lt;')
    t = re.sub(r'\[(?=[^\]]*\]\()', '\\[', t)        # [x](…) 形不许成链接
    t = RE_OL.sub(r'\1\\. ', t)
    # 破折号后紧贴字母的直引号只能是开引号；kramdown 的智能引号把它判成收引号（`;—"But` → —”But），这里先写死
    t = re.sub(r'([—–])"(?=[A-Za-z0-9(\[])', '\\1“', t)
    t = re.sub(r"([—–])'(?=[A-Za-z])", '\\1‘', t)
    t = re.sub(r'^([#>+-]) ', r'\\\1 ', t)
    return t


LOST = ('<span class="cd-lost" title="Wanting in both transcriptions used for this edition '
        '(两份录入本此处均缺)">…</span>')


def place_notes(units, notes, log):
    """`*`/`†` → [^n]；脚注正文挂到该讲（或序言）的 notes 列表。"""
    key = {u.get('num') or u['title']: u for u in units if 'paras' in u}
    for nt in notes:
        u = key[nt['unit']]
        u.setdefault('notes', [])
        anchor = flatten(nt['anchor'])
        done = False
        for f in ('epi', 'paras'):
            for i, p in enumerate(u[f]):
                flat = flatten(p)
                m = re.search(re.escape(anchor) + r'\s?([*†])', flat)
                if m and not done:
                    tag = f'@@FN{nt["n"]}@@'
                    u[f][i] = flat[:m.start(1)].rstrip() + tag + flat[m.end(1):]
                    done = True
        if not done:
            raise SystemExit(f'脚注 #{nt["n"]} 定位失败：{nt["unit"]} 「{anchor}」')
        u['notes'].append(nt)
        log['notes'] += 1


def note_md(nt, k):
    if nt['text'] is None:
        body = ('<span class="cd-edit">[The text of this note is wanting in both transcriptions used for this '
                'edition. 此条脚注正文两份录入本均缺。]</span>')
    else:
        body = md_escape(nt['text']).replace('⟦lost⟧', LOST)
        if nt.get('head'):
            body = f'<span class="cd-notehead">{nt["head"]}.</span> ' + body
    return f'[^{k}]: {body}'


def render(u, extra_top=''):
    """一讲（或序言）→ markdown 正文。脚注按页内出现次序编号。"""
    order = {}
    blocks = []

    def sub_fn(t):
        def rep(m):
            n = int(m.group(1))
            order.setdefault(n, len(order) + 1)
            return f'[^{order[n]}]'
        return re.sub(r'@@FN(\d+)@@', rep, t)

    for p in u.get('epi', []):
        blocks.append(('epi', sub_fn(md_escape(flatten(p)))))
    for p in u['paras']:
        blocks.append(('p', sub_fn(md_escape(flatten(p)))))
    out = [extra_top] if extra_top else []
    epi = [b for k, b in blocks if k == 'epi']
    if epi:
        out.append('<div class="cd-text" markdown="1">\n\n' + '\n\n'.join(epi) + '\n\n</div>')
        out.append('@@ANCHORS@@')
    out += [b for k, b in blocks if k == 'p']
    nmap = {nt['n']: nt for nt in u.get('notes', [])}
    defs = [note_md(nmap[n], k) for n, k in sorted(order.items(), key=lambda x: x[1])]
    body = '\n\n'.join(out)
    if defs:
        body += '\n\n' + '\n\n'.join(defs)
    return body


# ── 组页 ──────────────────────────────────────────────────────

def toc_entries(units):
    """作者目录 → [(kind, text)]：kind = part / lecture(num) / preface。"""
    toc = next(u for u in units if u.get('title') == 'Table of Contents')
    out = []
    for p in toc['paras']:
        t = flatten(p)
        t = re.sub(r'\s+', ' ', t)
        m = re.match(r'([IVXL]+)\. (.*)$', t)
        if m:
            out.append(('lecture', m.group(1), m.group(2)))
        elif t.startswith('Preface'):
            out.append(('preface', None, t))
        else:
            out.append(('part', None, t))
    return out


def toc_title(text):
    """目录条目去掉末尾的经文出处（「:—1 JOHN 2:3–5」等）。"""
    t = re.split(r'\s*[:;.]?\s*[:"]?—+\s*1\s*JOHN', text)[0]
    return t.rstrip(' :;.—"')


def build(units, notes_ok=True):
    lects = [u for u in units if u['type'] == 'lecture']
    assert [u['num'] for u in lects] == ROMAN, [u['num'] for u in lects]
    toc = toc_entries(units)
    titles = {num: toc_title(t) for k, num, t in toc if k == 'lecture'}
    part_of = {}
    pi = -1
    for u in lects:
        if any(u['num'] == p[0] for p in PARTS):
            pi += 1
        part_of[u['num']] = pi
    seen = set()
    pages = []
    pre2 = next(u for u in units if u.get('title', '').startswith('PREFACE TO SECOND'))
    pre1 = next(u for u in units if u.get('title', '').startswith('PREFACE TO FIRST'))
    pages.append(dict(slug='preface-2', title='Preface to the Second Edition', subtitle='1869',
                      body=render(pre2), group='front'))
    pages.append(dict(slug='preface-1', title='Preface to the First Edition', subtitle='1866',
                      body=render(pre1), group='front'))
    pages.append(dict(slug='contents', title='Contents', subtitle="The author's analytical table",
                      body=contents_body(toc), group='front'))
    for k, u in enumerate(lects, 1):
        num = u['num']
        vv = expand(VERSES[num])
        top = ''
        for p in PARTS:
            if p[0] == num:
                top = f'<div class="cd-part">{p[1].upper()}<small>{p[2]}</small></div>'
        head = re.sub(r'\s+', ' ', u['title']).replace('— ', '—')
        top += ('\n\n' if top else '') + f'<h2 class="cd-head">{head}</h2>'
        body = render(u, top)
        anchors = ''.join(f'\n\n<div class="commentary-anchor" id="{BOOK_ID}-{c}-{v}"></div>'
                          for c, v in vv if (c, v) not in seen)
        seen.update(vv)
        body = body.replace('\n\n@@ANCHORS@@', anchors)
        pages.append(dict(slug=f'lecture-{k}', title=f'Lecture {num}', label=f'Lecture {num}',
                          subtitle=f'{AUTHOR} · {vlabel(VERSES[num])}', body=body, group='lecture',
                          num=num, k=k, ch=vv[0][0], vv=vv, part=part_of[num], toc_title=titles[num]))
    missing = [(c, v) for c in NV for v in range(1, NV[c] + 1) if (c, v) not in seen]
    return pages, missing


def contents_body(toc):
    out = ['<div class="cd-contents" markdown="1">']
    k = 0
    for kind, num, t in toc:
        if kind == 'part':
            out.append(f'\n<h2 class="cd-group">{md_escape(t)}</h2>\n')
        elif kind == 'preface':
            slug = 'preface-2' if 'Second' in t else 'preface-1'
            out.append(f'[{t}]({{{{ site.baseurl }}}}/candlish/{BOOK_ID}/{slug}/)\n')
        else:
            k += 1
            out.append(f'{num}. [{md_escape(t)}]({{{{ site.baseurl }}}}/candlish/{BOOK_ID}/lecture-{k}/)\n')
    out.append('</div>')
    return '\n'.join(out)


def fm_nav(pg, key):
    o = pg.get(key)
    if not o:
        return []
    return [f'{key}_url: "/candlish/{BOOK_ID}/{o["slug"]}/"', f'{key}_label: "{o.get("label", o["title"])}"']


def yq(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def chapter_pages(pages, meta, stamp):
    lect = [p for p in pages if p['group'] == 'lecture']
    out = []
    for c in range(1, 6):
        lst = [p for p in lect if any(cc == c for cc, _ in p['vv'])]
        meta.setdefault(str(c), stamp)
        fm = ['---', 'layout: candlish-chapter', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
              f'title: "1 John {c}"', f'subtitle: "{AUTHOR}"', f'date: {meta[str(c)]}', f'chapter: {c}',
              'verse_from: 1', f'verse_to: {NV[c]}']
        if c > 1:
            fm += [f'prev_url: "/candlish/{BOOK_ID}/{c - 1}/"', f'prev_label: "1 John {c - 1}"']
        if c < 5:
            fm += [f'next_url: "/candlish/{BOOK_ID}/{c + 1}/"', f'next_label: "1 John {c + 1}"']
        fm.append('---')
        items = '\n'.join(
            f'<li><a href="{{{{ site.baseurl }}}}/candlish/{BOOK_ID}/{p["slug"]}/">{p["title"]}. {p["toc_title"]}'
            f'<span class="cd-ref">{vlabel(VERSES[p["num"]])}</span></a></li>' for p in lst)
        out.append((str(c), '\n'.join(fm) + '\n\n<ul class="cd-chtoc">\n' + items + '\n</ul>\n'))
    return out


def build_index(pages):
    out = ['---', 'layout: candlish-book', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
           f'title: "{BOOK_NAME}"', f'author: "{AUTHOR} (1806–1873)"',
           'edition: "The First Epistle of John, Expounded in a Series of Lectures · '
           'first published 1866; second edition revised by the author (preface 1869), Edinburgh: A. and C. Black"',
           '---', '']
    if (OUT / 'zh').exists():
        out.insert(-2, f'zh_url: "/candlish/{BOOK_ID}/"')

    def li(p, ref=True):
        r = f'<span class="cd-ref">{vlabel(VERSES[p["num"]])}</span>' if ref and 'num' in p else ''
        t = f'{p["title"]}. {p["toc_title"]}' if 'num' in p else p['title']
        return f'  <li><a href="{{{{ site.baseurl }}}}/candlish/{BOOK_ID}/{p["slug"]}/">{t}{r}</a></li>'
    out.append('<h2 class="cd-group">Prefaces and Contents</h2>')
    out.append('<ul class="cd-toc">')
    out += [li(p) for p in pages if p['group'] == 'front']
    out.append('</ul>')
    for i, (first, name, sub) in enumerate(PARTS):
        out.append(f'<h2 class="cd-group">{name}</h2>')
        out.append(f'<p class="cd-part-sub">{sub}</p>')
        out.append('<ul class="cd-toc">')
        out += [li(p) for p in pages if p['group'] == 'lecture' and p['part'] == i]
        out.append('</ul>')
    out.append('<h2 class="cd-group">By Chapter</h2>')
    out.append('<ul class="cd-chgrid">')
    out += [f'  <li><a href="{{{{ site.baseurl }}}}/candlish/{BOOK_ID}/{c}/">1 John {c}</a></li>' for c in range(1, 6)]
    out.append('</ul>')
    nfix = sum(1 for ln in (RAW / 'manual_fixes.tsv').read_text(encoding='utf-8').splitlines()
               if ln.strip() and not ln.startswith('#'))
    out.append('<div class="cd-note">')
    out.append('<p><b>About this text.</b> The text follows the Monergism Books e-text (2020), a modern keyed '
               'transcription in which Scripture references are given in modern form (1 John 2:3) and the '
               'original italics are not marked. That e-text omits the author\'s footnotes, leaving only the '
               'asterisks; their wording has been supplied from a second, independent transcription (the '
               'e-Sword / BibleSupport module, from William A. Anderson\'s 2008 Libronix edition), cleared of '
               'that module\'s conversion damage. Where the second transcription supplies a word or a passage '
               f'the first has dropped or misspelled, the reading has been adopted ({nfix} places). Places '
               'wanting in both are marked <span class="cd-lost">…</span>.</p>')
    out.append(f'<p class="cd-note-zh"><b>文本说明。</b>本书正文据 Monergism Books 电子本（2020）。该本是现代人工录入本，'
               f'经文出处已改作现代格式（1 John 2:3），原书斜体未标。它把作者的脚注正文全部丢了，只剩星号；'
               f'脚注据另一份独立录入本（e-Sword / BibleSupport 模块，出自 William A. Anderson 2008 年的 Libronix 本）补回，'
               f'并清理了该模块转换时造成的损坏。第一份漏掉或拼错、第二份同位读出的字句，取第二份（{nfix} 处）。'
               f'两份都缺的标 <span class="cd-lost">…</span>。逐条依据见 <code>candlish_raw/1john/PROVENANCE.md</code>。</p>')
    out.append('</div>')
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    units = json.loads((RAW / 'units.json').read_text(encoding='utf-8'))
    cc_starts = {norm7(p) for p in A.cc_text() if len(p.split()) >= 7}
    log = dict(split=0, joined=0, fixes=0, notes=0)
    resolve_joins(units, cc_starts, log)
    apply_fixes(units, log)
    notes = json.loads((RAW / 'notes.json').read_text(encoding='utf-8'))
    place_notes(units, notes, log)
    pages, missing = build(units)
    left = [(p['slug'], m.group(0)) for p in pages for m in re.finditer(r'[*†]|@@FN', p['body'])]
    print(f"接缝 分段 {log['split']} / 接上 {log['joined']}；修正 {log['fixes']}；脚注 {log['notes']}；"
          f"残留记号 {left[:5]}；未覆盖经节 {missing}", file=sys.stderr)
    if left:
        raise SystemExit('有未处理的 * / † 记号')

    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    stamp = now()
    seq = pages
    for i, pg in enumerate(seq):
        pg['prev'] = seq[i - 1] if i else None
        pg['next'] = seq[i + 1] if i + 1 < len(seq) else None
    if not a.apply:
        print(f'试跑 {len(pages)} 页', file=sys.stderr)
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for pg in pages:
        slug = pg['slug']
        meta.setdefault(slug, stamp)
        fm = ['---', 'layout: candlish-chapter', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
              f'title: {yq(pg["title"])}', f'subtitle: {yq(pg["subtitle"])}', f'date: {meta[slug]}']
        if pg['group'] == 'lecture':
            fm += [f'chapter: {pg["ch"]}', f'lecture: {pg["k"]}']
        fm += fm_nav(pg, 'prev') + fm_nav(pg, 'next')
        if (OUT / 'zh' / f'{slug}.md').exists():
            fm.append(f'zh_url: "/candlish/{BOOK_ID}/zh/{slug}/"')
        fm.append('---')
        (OUT / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + pg['body'] + '\n', encoding='utf-8')
    for slug, text in chapter_pages(pages, meta, stamp):
        (OUT / f'{slug}.md').write_text(text, encoding='utf-8')
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / 'en').mkdir(exist_ok=True)
    (OUT / 'en' / 'index.html').write_text(build_index(pages), encoding='utf-8')
    if not (OUT / 'zh').exists():
        (OUT / 'index.html').write_text(build_index(pages), encoding='utf-8')
    print(f'写入 {len(pages)} 页 + 章目录 5 页 → {OUT}', file=sys.stderr)


if __name__ == '__main__':
    main()
