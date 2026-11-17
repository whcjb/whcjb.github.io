#!/usr/bin/env python3
"""布里奇斯《诗篇 119 篇讲解》英文版：bridges_raw/psalm119/work/lines.json → bridges/psalm119/

    python3 scripts/bridges_ps119_lines.py && python3 scripts/publish_bridges_psalm119_en.py

底本：Biblical eLearning 所刊 Gordon College 录入本（Erin Bensing，2007），据 New York: Robert Carter, 1876 重印本逐行录入。
处理：
  - 分页后第一行是页眉，丢掉；页底以 * † ‡ § 起头的行（连同其后到页末的续行）是脚注，
    按符号与同页正文里的注号配对，改成每页（每个「部分」页）连续编号；
  - 段：缩进 3–20 格的行起新段；「N. <em>经文</em>」起头的经文行自成一段（续行全是斜体的并入）；
    缩进 ≥ 30 格的居中行是标题（PART I. 等）或落款；
  - 行尾连字符：接下一行小写起头时，按全书其他地方的写法决定保留与否（都没出现过就拼合）；
  - 一页一个「部分」（原书 22 部分，每部分 8 节），序言（含第十六版序）一页；书末索引不收。
"""
import html
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINES = ROOT / 'bridges_raw' / 'psalm119' / 'work' / 'lines.json'
OUT = ROOT / 'bridges' / 'psalm119'
BASE = '/bridges/psalm119'
BOOK = 'Bridges on Psalm 119'
MARKS = '*†‡§'
ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI',
         'XVII', 'XVIII', 'XIX', 'XX', 'XXI', 'XXII']
HEB = ['Aleph', 'Beth', 'Gimel', 'Daleth', 'He', 'Vau', 'Zain', 'Cheth', 'Teth', 'Jod', 'Caph', 'Lamed', 'Mem', 'Nun',
       'Samech', 'Ain', 'Pe', 'Tzaddi', 'Koph', 'Resh', 'Schin', 'Tau']


def plain(t):
    return re.sub(r'<[^>]+>', '', t)


def main():
    L = json.loads(LINES.read_text(encoding='utf-8'))
    # 1) 切页、丢页眉、分出脚注
    pages, cur = [], []
    for l in L:
        if l['pb']:
            if 'INDEX' in l['t']:                     # 书末索引起，不收
                break
            pages.append(cur); cur = []
            continue                                  # 分页后第一行是页眉
        cur.append(l)
    pages.append(cur)
    body_lines = []                                   # (line, page_idx)
    notes = {}                                        # page_idx → [(mark, text)]
    for pi, pg in enumerate(pages):
        k = len(pg)
        for j, l in enumerate(pg):
            if re.match(rf'^[{MARKS}]', plain(l['t'])) and j >= len(pg) * 0.3 and j > 0:
                k = j
                break
        for l in pg[:k]:
            body_lines.append((l, pi))
        fn = []
        for l in pg[k:]:
            m = re.match(rf'^(?:<em>)?([{MARKS}])\s*(.*)$', l['t'])
            if m:
                # 一行里两条（「†Locke. ‡. Bishop Horne in loco.」）
                for k2, seg in enumerate(re.split(rf'(?<=\.)\s+(?=[{MARKS}])', m.group(1) + ' ' + m.group(2))):
                    mm = re.match(rf'^([{MARKS}])\.?\s*(.*)$', seg)
                    fn.append([mm.group(1), mm.group(2)])
            elif fn:
                fn[-1][1] += '\x03' + l['t']
        if fn:
            notes[pi] = fn
    # 2) 行尾连字符的取舍依据：全书行内出现过的带连字符词与不带连字符词
    mid = ' '.join(plain(l['t']) for l, _ in body_lines)
    hy = Counter(re.findall(r"\b([A-Za-z]+-[a-z]+)\b", mid))
    words = Counter(w.lower() for w in re.findall(r"[A-Za-z]+", mid))

    DICT = {w.strip().lower() for w in open('/usr/share/dict/words')}

    def real(w):
        w = w.lower()
        return len(w) >= 3 and any(x in DICT for x in (w, w[:-1], w[:-2], w[:-3], w[:-3] + 'e', w[:-2] + 'e'))

    def join(a, b):
        mk = re.match(r'^(\x02\d+\x02)', b)
        if mk:
            b = b[mk.end():]
        b = re.sub(r'^(<em>)\s+', r'\1', b.lstrip())
        a = re.sub(r'\s+(</em>)$', r'\1', a.rstrip())
        m1, m2 = re.search(r'([A-Za-z]+)-$', plain(a)), re.match(r'^(?:<em>)?([a-z]+)', b)
        if mk and m1 and m2:      # 页标记挪到拼合词后面，免得把词拆开
            r = join(a, b)
            w = re.search(r'\S+', r[len(a) - len(m1.group(1)) - 1:])
            cut = len(a) - len(m1.group(1)) - 1 + w.end()
            return r[:cut] + mk.group(1) + r[cut:]
        if mk:
            return a + ' ' + mk.group(1) + b
        if not (m1 and m2):
            return a + ' ' + b
        w1, w2 = m1.group(1), m2.group(1)
        if hy[f'{w1}-{w2}'] > words[(w1 + w2).lower()] or (
                hy[f'{w1}-{w2}'] == words[(w1 + w2).lower()] == 0 and real(w1) and real(w2) and not real(w1 + w2)):
            return a + b
        if a.endswith('-'):
            return a[:-1] + b
        # 「…com-</em>」+「<em>fort…」：去连字符，斜体照接
        return re.sub(r'-(</em>)$', r'\1', a) + b

    for lst in notes.values():
        for it in lst:
            parts_ = it[1].split('\x03')
            acc = parts_[0]
            for nx in parts_[1:]:
                acc = join(acc, nx)
            it[1] = acc
    # 3) 拼段
    blocks = []   # dict(kind, text, page)
    for l, pi in body_lines:
        t = l['t'].replace('―', '—')
        ind = l['ind']
        # 经文行的几种录法：「11 . <em>」「32<em>. I will…」→ 统一成「N. <em>…」
        mv = re.match(r'^(\d{1,3})\s*(<em>)?\s*\.\s*(<em>)?\s*', t)
        if mv and (mv.group(2) or mv.group(3)):
            t = f'{mv.group(1)}. <em>' + t[mv.end():]
        t = re.sub(r'(?<=\s)(\d{1,3})<em>\.\s*', r'\1. <em>', t)     # 行中：「…heaven</em>. 90<em>. Thy」
        is_verse = re.match(r'^\d+\. <em>', t)
        if ind >= 30 or (ind > 20 and len(plain(t)) < 50) or re.match(rf'^PART [IVXL]+\.?[{MARKS}]?$', plain(t)):
            blocks.append(dict(kind='head', text=t, page=pi))
            continue
        prev = blocks[-1] if blocks else None
        if is_verse:
            blocks.append(dict(kind='verse', text=t, page=pi))
            continue
        if prev and prev['kind'] == 'verse' and re.fullmatch(r'(?:\s*(?:<em>.*?</em>|[.,;:?!]|\d{1,3}\.))+\s*', t):
            prev['text'] = join(prev['text'], t)
            continue
        if prev is None or prev['kind'] in ('head', 'verse') or 3 <= ind <= 20:
            blocks.append(dict(kind='p', text=t, page=pi, pages=[pi]))
            continue
        prev.setdefault('pages', [prev['page']])
        if pi not in prev['pages']:
            prev['pages'].append(pi)
            t = f'\x02{pi}\x02' + t
        prev['text'] = join(prev['text'], t)
    # 两节连排的经文（「…me.</em> 99. <em>have more…」）拆开
    split = []
    for bk in blocks:
        if bk['kind'] != 'verse':
            split.append(bk)
            continue
        for sg in re.split(r'(?<=</em>)\.?\s*(?=\d{1,3}\.\s*<em>)|(?<=</em>\.)\s*(?=\d{1,3}\.\s*<em>)', bk['text']):
            if sg.strip():
                split.append(dict(bk, text=sg.strip()))
    blocks = split
    # 4) 分篇
    parts, cur = [], None
    for b in blocks:
        h = plain(b['text']).strip()
        if b['kind'] == 'head' and h.upper().startswith('PREFACE'):
            if cur is None or cur['slug'] != 'preface':
                cur = dict(slug='preface', title='Preface', blocks=[]); parts.append(cur)
            if 'SIXTEENTH' in h.upper():
                cur['blocks'].append(dict(kind='h2', text='Preface to the Sixteenth Edition', page=b['page']))
            continue
        m = re.match(rf'^PART ([IVXL]+)\.?[{MARKS}]?$', h)
        if m:
            n = ROMAN.index(m.group(1)) + 1
            cur = dict(slug=str(n), title=f'Part {m.group(1)}', blocks=[], n=n); parts.append(cur)
            sym = re.search(rf'[{MARKS}]$', h)
            if sym:
                cur['head_mark'] = (sym.group(0), b['page'])
            continue
        if b['kind'] == 'head' and h.upper().startswith(('INDEX', 'EXPOSITION OF PSALM')):
            if h.upper().startswith('INDEX'):
                cur = None
            continue
        if cur is not None:
            cur['blocks'].append(b)
    # 5) 脚注配对与渲染
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    OUT.mkdir(parents=True, exist_ok=True)
    warn = []
    for i, p in enumerate(parts):
        out, foot, k, orphan = [], [], 0, []
        used = {}
        if p.get('head_mark'):
            sym, pi = p['head_mark']
            lst = notes.get(pi, [])
            if lst and lst[0][0] == sym:
                used[pi] = 1; k = 1
                foot.append(re.sub(r'\s+', ' ', lst[0][1]).strip())
                p['title_note'] = 1
        for b in p['blocks']:
            t = re.sub(r'</em><em>', '', b['text'])
            t = re.sub(r'</em>\s+<em>', ' ', t)
            t = re.sub(r'\s+', ' ', t).strip()

            pos2page = []
            curp = b['page']
            for mm in re.finditer(r'\x02(\d+)\x02', t):
                pos2page.append((mm.start(), int(mm.group(1))))

            def page_at(pos):
                pg = b['page']
                for st, pgi in pos2page:
                    if st <= pos:
                        pg = pgi
                return pg

            def mark(sym, pos, b=b, t=t):
                nonlocal k
                for pi in [page_at(pos)]:
                    lst = notes.get(pi, [])
                    u = used.setdefault(pi, 0)
                    if u < len(lst) and lst[u][0] == sym:
                        used[pi] = u + 1
                        k += 1
                        foot.append(re.sub(r'\s+', ' ', lst[u][1].replace('\u2015', '—')).strip())
                        return f'\x00{k}\x00'
                warn.append(f'{p["slug"]}: 注号 {sym} 配不上（{plain(t)[max(0, pos - 30):pos]}）')
                return sym
            # 注号紧贴前一字（vain."*）或隔一个空格（.' * It is）；后面不能紧跟字母
            t = re.sub(rf'(?:(?<=\S)|(?<=\S ))([{MARKS}])(?![A-Za-z])(?!\s*\d)', lambda m: mark(m.group(1), m.start()), t)
            t = re.sub(r'\s*\x02\d+\x02\s*', lambda m: ' ' if m.group(0).strip() != m.group(0) else '', t)
            t = re.sub(r' (\x00\d+\x00)', r'\1', t)
            t = re.sub(r'\x00(\d+)\x00', r'<sup class="bg-fn"><a href="#fn-\1" id="fnref-\1">\1</a></sup>', t)
            if b['kind'] == 'verse':
                m = re.match(r'^(\d+)\. (.*)$', t)
                out.append(f'<p class="bg-verse" id="v{m.group(1)}"><span class="bg-vnum">{m.group(1)}</span>{m.group(2)}</p>')
            elif b['kind'] == 'h2':
                out.append(f'<h2 class="bg-h2">{t}</h2>')
            elif b['kind'] == 'head':
                out.append(f'<p class="bg-center">{t}</p>')
            else:
                out.append(f'<p>{t}</p>')
        for pi, lst in notes.items():
            if any(pi in b.get('pages', [b['page']]) for b in p['blocks']) and used.get(pi, 0) < len(lst):
                for sym, txt in lst[used.get(pi, 0):]:
                    orphan.append(re.sub(r'\s+', ' ', txt).strip())
                warn.append(f'{p["slug"]}: 第 {pi} 页有 {len(lst) - used.get(pi, 0)} 条脚注录入本正文里找不到注号，列在注末')
        body = '\n\n'.join(out)
        if foot:
            body += '\n\n<div class="bg-notes">\n' + '\n'.join(
                f'<p id="fn-{j}"><a class="bg-back" href="#fnref-{j}">{j}</a>{t}</p>' for j, t in enumerate(foot, 1)) \
            + ''.join(f'\n<p class="bg-orphan"><span class="bg-back">*</span>{t} <span class="bg-orphan-tag">[reference mark wanting in the transcription]</span></p>' for t in orphan) + '\n</div>'
        elif orphan:
            body += '\n\n<div class="bg-notes">' + ''.join(f'\n<p class="bg-orphan"><span class="bg-back">*</span>{t} <span class="bg-orphan-tag">[reference mark wanting in the transcription]</span></p>' for t in orphan) + '\n</div>'
        if 'n' in p:
            p['label'] = f'Part {ROMAN[p["n"] - 1]} · {HEB[p["n"] - 1]}'
            p['sub'] = f'Verses {p["n"] * 8 - 7}–{p["n"] * 8}'
        else:
            p['label'], p['sub'] = p['title'], ''
        p['body'] = body
    for i, p in enumerate(parts):
        old = OUT / f'{p["slug"]}.md'
        m = re.search(r'^date: (.+)$', old.read_text(encoding='utf-8'), re.M) if old.exists() else None
        fm = ['---', 'layout: bridges-psalm119-chapter', 'book_id: psalm119', f'book_name: "{BOOK}"',
              f'title: "{p["label"]}"'] + ([f'subtitle: "{p["sub"]}"'] if p['sub'] else []) + ([f'title_note: {p["title_note"]}'] if p.get('title_note') else []) + [f'date: {m.group(1) if m else stamp}']
        if i:
            fm += [f'prev_url: "{BASE}/{parts[i-1]["slug"]}/"', f'prev_label: "{parts[i-1]["label"]}"']
        if i + 1 < len(parts):
            fm += [f'next_url: "{BASE}/{parts[i+1]["slug"]}/"', f'next_label: "{parts[i+1]["label"]}"']
        fm.append('---')
        old.write_text('\n'.join(fm) + '\n\n' + p['body'] + '\n', encoding='utf-8')
    toc = '\n'.join(f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/{p["slug"]}/">'
                    + (f'<span class="bg-no">{p["label"]}</span>{p["sub"]}' if p['sub'] else p['label']) + '</a></li>'
                    for p in parts)
    (OUT / 'index.html').write_text(f'''---
layout: bridges-psalm119-book
book_id: psalm119
book_name: "An Exposition of Psalm CXIX"
author: "Charles Bridges (1794–1869)"
edition: "First published 1827; text of the New York edition, Robert Carter, 1876"
title: "{BOOK}"
---

<ul class="bg-toc">
{toc}
</ul>

<div class="bg-note">
<p><b>About this text.</b> The text follows the transcription of the 1876 New York edition (Robert Carter) made by Erin Bensing
at Gordon College (2007) and published by Biblical eLearning. Line-end hyphens and running heads of the printed page have been removed,
and the author’s footnotes are numbered afresh on each page of this edition. The index at the end of the book is not reproduced.</p>
<p class="bg-note-zh"><b>文本说明。</b>正文据 Gordon College 录入本（Erin Bensing，2007，Biblical eLearning 刊布），所据为 1876 年纽约 Robert Carter 版。
已去掉印本的行尾连字符与页眉；作者脚注在本站每页重新编号。书末索引未收。</p>
</div>
''', encoding='utf-8')
    print(len(parts), 'pages;', sum(len(v) for v in notes.values()), 'footnotes on', len(notes), 'printed pages')
    if warn:
        print(len(warn), 'warnings'); print('\n'.join(warn[:40]))


if __name__ == '__main__':
    main()
