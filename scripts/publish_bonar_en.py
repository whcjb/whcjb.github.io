#!/usr/bin/env python3
"""博纳尔《诗篇中的基督与教会》英文版发布：bonar_raw/psalms → bonar/psalms/

    python3 scripts/publish_bonar_en.py

输入：
  units.json            Monergism 录入本正文（extract_bonar.py），希伯来文是 ⟪id⟫ 占位
  hebrew_fixes.tsv      希伯来文看 1859 初版定稿（没列的 id 用 work/hebrew_runs.json 的重建结果）
  notes_1859.tsv        1859 初版脚注（bonar_notes_build.py 生成）
  work/note_sites.json  录入本里每个注号的位置（单元、段号、前后文）
  manual_fixes.tsv      编者改正：单元 psalm-N 的套正文，note-N 的已在 notes_1859 里套过；
                        首页的编者改动表列全部 editor 条目
  index_note.md         首页文本说明（中英两段 + 中文条目列表）
输出：
  bonar/psalms/index.html、preface.md、1.md … 150.md、degrees.md
"""
import html
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'bonar_raw' / 'psalms'
OUT = ROOT / 'bonar' / 'psalms'
BOOK_NAME = 'Bonar on the Psalms'
BASE = '/bonar/psalms'


def tsv(name):
    return [l.rstrip('\n').split('\t') for l in open(RAW / name, encoding='utf-8')
            if l.strip() and not l.startswith('#')]


def hebrew_map():
    runs = {r['id']: r['text'] for r in json.load(open(RAW / 'work' / 'hebrew_runs.json'))}
    for r in tsv('hebrew_fixes.tsv'):
        runs[int(r[0])] = r[1]
    return runs


def he(s):
    return f'<span class="bn-he" lang="he" dir="rtl">{s}</span>'


HEB = re.compile(r'[֐-׿יִ-ﭏ]+(?:[\s־]+[֐-׿יִ-ﭏ]+)*')


def inline_note(t):
    """脚注正文：*斜体* → <em>，「 / 」→ 换行，希伯来文包 rtl。"""
    t = html.escape(t, quote=False)
    t = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', t)
    t = t.replace(' / ', '<br>')
    return HEB.sub(lambda m: he(m.group(0)), t)


def norm_para(p):
    p = p.replace('⁣', '')
    p = re.sub(r'-\n', '-', p)
    return re.sub(r'\s*\n\s*', ' ', p).strip()


def unit_key(u):
    return 'preface' if u['type'] == 'preface' else 'songs-of-degrees' if u['type'] == 'section' else f"psalm-{u['num']}"


def main():
    units = json.load(open(RAW / 'units.json', encoding='utf-8'))
    heb = hebrew_map()
    notes = {int(r[0]): r[1] for r in tsv('notes_1859.tsv')}
    dup = {int(r[0]) for r in tsv('notes_map.tsv') if r[1].startswith('DUP')}
    sites = json.load(open(RAW / 'work' / 'note_sites.json'))
    fixes = [r for r in tsv('manual_fixes.tsv')]
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    # 录入本第 18 篇第 2 段是页间误断（「1 Sam. / 23:28)」），并回上一段
    for u in units:
        if u['type'] == 'psalm' and u['num'] == 18 and u['paras'][2].startswith('23:28)'):
            u['paras'][1] = u['paras'][1].rstrip() + ' ' + u['paras'].pop(2)
            for s in sites:
                if s['unit'] == 'psalm-18' and isinstance(s['para'], int) and s['para'] >= 2:
                    s['para'] = s['para'] - 1 if s['para'] > 2 else 1

    by_unit = {}
    for s in sites:
        by_unit.setdefault(s['unit'], []).append(s)

    OUT.mkdir(parents=True, exist_ok=True)
    pages, bad = [], []
    for u in units:
        key = unit_key(u)
        paras = [norm_para(p) for p in u['paras']]
        for r in fixes:
            if r[0] == key and r[4] == 'editor':
                hits = [i for i, p in enumerate(paras) if r[1] in p]
                if len(hits) != 1 or paras[hits[0]].count(r[1]) != 1:
                    bad.append(f'{key}: 编者改正「{r[1]}」命中 {len(hits)} 段')
                    continue
                paras[hits[0]] = paras[hits[0]].replace(r[1], r[2])
        # 注号落位：按出现先后编号（每页从 1 起）
        local, title_note = [], None
        for s in sorted(by_unit.get(key, []), key=lambda s: s['n']):
            local.append(s)
        k = 0
        marks = {}   # 段号 → [(在段中的位置, 记号长度, 本页号, 全书号)]
        for s in local:
            n = s['n']
            if n in dup:
                k_here = None
            else:
                k += 1
                k_here = k
            if s['para'] == 'head':
                title_note = (k_here, n)
                continue
            pi = s['para']
            p = paras[pi]
            raw_before = re.sub(r'\s*\n\s*', ' ', re.sub(r'-\n', '-', s['before'].replace('\u2063', '')))
            ctx = raw_before + s['mark']
            pos = p.find(ctx)
            if pos < 0 or p.find(ctx, pos + 1) >= 0:
                # 前文里有行尾连字符等写法差异时，只取末尾 25 字再试（仍须唯一命中）
                ctx = raw_before[-25:] + s['mark']
                pos = p.find(ctx)
                if pos < 0 or p.find(ctx, pos + 1) >= 0:
                    bad.append(f'{key}: 注 {n} 落位失败')
                    continue
            at = pos + len(ctx) - len(s['mark'])
            marks.setdefault(pi, []).append((at, len(s['mark']), k_here, n))
        body = []
        for i, p in enumerate(paras):
            segs, last = [], 0
            for at, ln, kk, n in sorted(marks.get(i, [])):
                seg = p[last:at]
                segs.append(html.escape(seg.rstrip() if kk is not None else seg, quote=False))
                if kk is not None:
                    segs.append(f'\x00{kk}\x00')
                last = at + ln
            segs.append(html.escape(p[last:], quote=False))
            t = ''.join(segs)
            t = re.sub(r'⟪(\d+)⟫', lambda m: he(heb[int(m.group(1))]), t)
            t = re.sub(r'\x00(\d+)\x00',
                       lambda m: f'<sup class="bn-fn"><a href="#fn-{m.group(1)}" id="fnref-{m.group(1)}">{m.group(1)}</a></sup>', t)
            m = re.match(r'^(\d+(?:–\d+)?)\s+(?=[A-Z(“"\'(])', t)
            if m and (i == 0 or key == 'psalm-119'):
                t = f'<span class="bn-vr">{m.group(1)}</span>' + t[m.end():]
            # 篇旨：初版每篇末另起一行斜体印出（「…we may inscribe as the title of this Psalm,」之后），
            # 录入本丢了斜体、成了普通段落 → 末段且上一段以字母或逗号收尾的，标作 bn-sum
            is_sum = (i == len(paras) - 1 and i > 0 and re.search(r'[A-Za-z,]$', paras[i - 1].strip()))
            body.append(f'<p class="bn-sum">{t}</p>' if is_sum else f'<p>{t}</p>')
        foot = []
        for s in local:
            n = s['n']
            if n in dup:
                continue
            kk = sum(1 for x in local if x['n'] <= n and x['n'] not in dup)
            foot.append(f'<p id="fn-{kk}"><a class="bn-back" href="#fnref-{kk}">{kk}</a>{inline_note(notes[n])}</p>')
        if foot:
            body.append('<div class="bn-notes">\n' + '\n'.join(foot) + '\n</div>')
        if key == 'preface':
            slug, title = 'preface', 'Preface'
        elif key == 'songs-of-degrees':
            slug, title = 'degrees', 'The Songs of Degrees'
        else:
            slug, title = str(u['num']), f"Psalm {u['num']}"
        pages.append(dict(slug=slug, title=title, body='\n\n'.join(body),
                          title_note=title_note[0] if title_note else None))
    if bad:
        print('\n'.join(bad))
        raise SystemExit(1)

    zh_done = {p.stem for p in (RAW / 'zh_chapters').glob('*.md')}
    for i, pg in enumerate(pages):
        old = OUT / f'{pg["slug"]}.md'
        m = re.search(r'^date: (.+)$', old.read_text(encoding='utf-8'), re.M) if old.exists() else None
        fm = ['---', 'layout: bonar-chapter', 'book_id: psalms', f'book_name: "{BOOK_NAME}"',
              f'title: "{pg["title"]}"', f'date: {m.group(1) if m else stamp}']   # 重跑不改已发布页的日期
        if pg['slug'] in zh_done:
            fm.append(f'zh_url: "{BASE}/zh/{pg["slug"]}/"')
        if pg['title_note']:
            fm.append(f'title_note: {pg["title_note"]}')
        if i > 0:
            fm += [f'prev_url: "{BASE}/{pages[i-1]["slug"]}/"', f'prev_label: "{pages[i-1]["title"]}"']
        if i + 1 < len(pages):
            fm += [f'next_url: "{BASE}/{pages[i+1]["slug"]}/"', f'next_label: "{pages[i+1]["title"]}"']
        fm.append('---')
        (OUT / f'{pg["slug"]}.md').write_text('\n'.join(fm) + '\n\n' + pg['body'] + '\n', encoding='utf-8')

    write_index(pages, fixes)
    print(len(pages), 'pages;', sum(p['body'].count('class="bn-fn"') for p in pages)
          + sum(1 for p in pages if p['title_note']), 'note refs')


def md_inline(t):
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', t)
    return HEB.sub(lambda m: he(m.group(0)), t)


def fix_where(unit):
    if unit.startswith('note-'):
        return '脚注 ' + unit[5:]
    return {'preface': '序言', 'songs-of-degrees': '上行之诗'}.get(unit) or unit.replace('psalm-', '第 ') + ' 篇'


def write_index(pages, fixes):
    src = (RAW / 'index_note.md').read_text(encoding='utf-8')
    src = re.sub(r'<!--.*?-->', '', src, flags=re.S).strip()
    note, items = [], []
    for block in src.split('\n\n'):
        lines = block.strip().split('\n')
        if all(l.startswith('- ') for l in lines):
            note.append('<ul>' + ''.join(f'<li>{md_inline(l[2:])}</li>' for l in lines) + '</ul>')
        else:
            note.append(f'<p>{md_inline(" ".join(lines))}</p>')
    rows = [r for r in fixes if len(r) > 4 and r[4] == 'editor']
    tbl = ''.join(
        f'<tr><td>{fix_where(r[0])}</td>'
        f'<td>{md_inline(html.escape(r[1], quote=False))}</td><td>{md_inline(html.escape(r[2], quote=False))}</td>'
        f'<td>{html.escape(r[3], quote=False)}</td></tr>' for r in rows)
    lead = [p for p in pages if not p['slug'].isdigit()]
    toc_ps = []
    for p in pages:
        if p['slug'] == 'degrees':
            toc_ps.append(f'<li><a href="{{{{ site.baseurl }}}}{BASE}/degrees/">Songs of Degrees</a></li>')
        elif p['slug'].isdigit():
            toc_ps.append(f'<li><a href="{{{{ site.baseurl }}}}{BASE}/{p["slug"]}/">Psalm {p["slug"]}</a></li>')
    out = f'''---
layout: bonar-book
book_id: psalms
book_name: "Christ and His Church in the Book of Psalms"
author: "Andrew A. Bonar (1810–1892)"
edition: "London: James Nisbet, 1859"
title: "Bonar on the Psalms"
{'zh_url: "' + BASE + '/zh/"' + chr(10) if (OUT / 'zh' / 'index.html').exists() else ''}---

<ul class="bn-toc bn-wide">
  <li><a href="{{{{ site.baseurl }}}}{BASE}/preface/">Preface</a></li>
</ul>
<h2 class="bn-group">The Psalms <small>(150, with the Songs of Degrees)</small></h2>
<ul class="bn-toc">
  {chr(10).join("  " + x for x in toc_ps).strip()}
</ul>
<div class="bn-note">
{chr(10).join(note)}
<details class="bn-ed"><summary>编者改动 {len(rows)} 处</summary>
<table><tr><th>位置</th><th>原样</th><th>改作</th><th>依据</th></tr>{tbl}</table></details>
</div>
'''
    (OUT / 'index.html').write_text(out, encoding='utf-8')


if __name__ == '__main__':
    main()
