#!/usr/bin/env python3
"""亚历山大《使徒行传注释》(1857) 英文版发布：alexander_raw/acts/units.json → alexander/acts/

units.json 由 scripts/extract_alexander_acts.py 生成（录入本字句 + 扫描本斜体三证人投票 + 经文头 + 脚注）。
本脚本只管排版：

  alexander/acts/preface/ · introduction/     前置件
  alexander/acts/<N>/                         逐章注释（1–28）
  alexander/acts/index.html                   书首页（含文本说明与编者改动逐条表）

date 沿用 en_meta.json 里的原值，新页才写当前真实时间。

用法：python3 scripts/publish_alexander_acts_en.py            # 试跑
      python3 scripts/publish_alexander_acts_en.py --apply    # 写盘
"""
import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'alexander_raw' / 'acts'
OUT = ROOT / 'alexander' / 'acts'
META = RAW / 'en_meta.json'
BOOK_NAME = 'Alexander on Acts'
AUTHOR = 'Joseph Addison Alexander'

# 和合本 / KJV 使徒行传各章节数
NV = [26, 47, 26, 37, 42, 15, 60, 40, 43, 48, 30, 25, 52, 28, 41, 40, 34, 28, 41, 38, 40, 30, 35, 27, 27, 32,
      44, 31]


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def yq(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def vlabel(vv):
    if len(vv) == 1:
        return f'{vv[0]}.'
    if len(vv) == 2:
        return f'{vv[0]}, {vv[1]}.'
    return f'{vv[0]}–{vv[-1]}.'


def fn_html(ch, paras_html, notes):
    """⟦fn:N⟧ → 上标注号（照原书 * / †）；注文列在章末。"""
    def rep(m):
        n = int(m.group(1))
        mk = html.escape(notes[n - 1]['mark'])
        return f'<sup class="aa-fnref"><a href="#acts-{ch}-fn{n}" id="acts-{ch}-fnref{n}">{mk}</a></sup>'
    return [re.sub(r'⟦fn:(\d+)⟧', rep, h) for h in paras_html]


def notes_block(ch, notes):
    if not notes:
        return ''
    out = ['<div class="aa-notes">']
    for n, x in enumerate(notes, 1):
        mk = html.escape(x['mark'])
        txt = x['text']
        if txt == '⟦missing⟧':
            txt = ('<span class="aa-lost">No note is printed for this mark in the original edition '
                   '(checked against the page images).</span>')
        out.append(f'<p id="acts-{ch}-fn{n}"><a class="aa-fnback" href="#acts-{ch}-fnref{n}">{mk}</a> {txt}</p>')
    out.append('</div>')
    return '\n'.join(out)


def chapter_body(c):
    ch = c['ch']
    notes = c.get('notes', [])
    out = []
    for h in fn_html(ch, c['intro'], notes):
        out.append(f'<p class="aa-analysis">{h}</p>')
    seen = set()
    for u in c['units']:
        vv = [v for v in u['vv'] if v not in seen and 1 <= v <= NV[ch - 1]]
        seen.update(vv)
        out += [f'<span class="ax-anchor" id="acts-{ch}-{v}"></span>' for v in vv]
        head = html.escape(u['head'], False) if u['head'] else ''
        out.append(f'<p class="aa-head"><span class="aa-vn">{vlabel(u["vv"])}</span> {head}</p>')
        for h in fn_html(ch, u['paras'], notes):
            out.append(f'<p>{h}</p>')
    miss = sorted(set(range(1, NV[ch - 1] + 1)) - seen)
    if miss:
        raise SystemExit(f'第 {ch} 章缺锚点：{miss}')
    nb = notes_block(ch, notes)
    if nb:
        out.append(nb)
    return '\n\n'.join(out)


def front_body(paras):
    return '\n\n'.join(f'<p>{h}</p>' for h in paras)


def pages(units):
    pg = [dict(slug='preface', title='Preface', label='Preface', body=front_body(units['preface'])),
          dict(slug='introduction', title='Introduction', label='Introduction',
               body=front_body(units['introduction']))]
    for c in units['chapters']:
        pg.append(dict(slug=str(c['ch']), title=f'Acts {c["ch"]}', label=f'Acts {c["ch"]}', chapter=c['ch'],
                       body=chapter_body(c)))
    for i, x in enumerate(pg):
        x['prev'] = pg[i - 1] if i else None
        x['next'] = pg[i + 1] if i + 1 < len(pg) else None
    return pg


def page_md(x, date):
    fm = ['---', 'layout: alexander-acts-chapter', 'book_id: acts', f'book_name: "{BOOK_NAME}"',
          f'title: {yq(x["title"])}', f'subtitle: {yq(AUTHOR)}', f'date: {date}']
    if x.get('chapter'):
        fm.append(f'chapter: {x["chapter"]}')
    for k in ('prev', 'next'):
        if x[k]:
            fm += [f'{k}_section: "{x[k]["slug"]}"', f'{k}_label: {yq(x[k]["label"])}']
    fm.append('---')
    return '\n'.join(fm) + '\n\n' + x['body'] + '\n'


def tsv_rows(name):
    rows = []
    for line in (RAW / name).read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.startswith('#'):
            rows.append(line.split('\t'))
    return rows


def esc(s):
    return html.escape(s, False)


def index_html(units):
    L = units['log']
    body_fixes = tsv_rows('body_fixes.tsv')
    head_manual = tsv_rows('head_manual.tsv')
    confus = tsv_rows('head_confusions.tsv')
    fns = tsv_rows('footnotes.tsv')
    t_body = '\n'.join(f'<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td></tr>' for a, b, c in body_fixes)
    t_head = '\n'.join(f'<tr><td>{esc(r)}</td><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(e)}</td></tr>'
                       for r, a, b, e in head_manual)
    t_conf = '\n'.join(f'<tr><td>{esc(a)} → {esc(b)}</td><td>{esc(e)}</td></tr>' for a, b, e in confus)
    t_fn = '\n'.join(f'<tr><td>{esc(m)}</td><td>{esc(p)}</td><td>{esc(r) if r else "照原图转录"}</td></tr>'
                     for m, p, _, r in [(f + [''])[:4] for f in fns])
    return f'''---
layout: alexander-acts-book
book_id: acts
book_name: "{BOOK_NAME}"
title: "The Acts of the Apostles Explained"
chapters: 28
---

<div class="aa-note">
<p><b>About this text.</b> The wording follows the Monergism Books e-text (2022) of Alexander's
<i>The Acts of the Apostles Explained</i>. That e-text drops all italics, the verse of the English Bible
printed in large type before each comment, and the text of the author's footnotes. These have been
restored from three scans of the first edition (New York: Charles Scribner, 1857; Internet Archive:
Princeton Theological Seminary copies <i>actsofapostlesex01alex/02alex</i> and <i>actsofapostlese01alex/02alex</i>,
University of California copy <i>actsofapostlesex01alexiala/02alexiala</i>): italics by a word-for-word
majority of the three scans; the verse headings from the scans, with misread letters corrected against
the King James text and doubtful places checked on the page images; the footnotes transcribed from the
page images. Scripture references in the comments are in the modern form of the e-text
(<i>3:2</i>, where the original prints <i>3, 2</i>).</p>
<p class="aa-note-zh"><b>文本说明。</b>正文字句据 Monergism Books 电子本（2022）。该本丢了三样东西：
全书斜体（亚历山大以斜体标出所讲解的经文字词与他自己的译法）、每条注释前大字排印的英文经文、
作者页脚注的注文。这三样都从 1857 年纽约初版的三份扫描本补回：斜体按三份扫描本逐词多数票；
经文头取自扫描本，OCR 读坏的字以 KJV 同位词为证人修正，拿不准的逐处看原图；脚注逐条看原图转录。
注释中的经文出处照电子本的现代写法（原书作 3, 2，电子本作 3:2），未回改。
对齐录入本 {L["words"]:,} 词中的 {L["aligned"]:,} 词；经文头 {L["heads_placed"]} 条全部落位。
以下逐条列出所有编者改动。</p>

<details class="aa-ed"><summary>录入本错字 {len(body_fixes)} 处（三份扫描本同位一致，逐条看原图核过）</summary>
<table><tr><th>录入本</th><th>改为</th><th>扫描本出处</th></tr>
{t_body}
</table></details>

<details class="aa-ed"><summary>经文头：OCR 字形混淆按 KJV 改回 {len(confus)} 类（逐类看图）</summary>
<table><tr><th>OCR → 改为</th><th>依据</th></tr>
{t_conf}
</table></details>

<details class="aa-ed"><summary>经文头逐条手改 {len(head_manual)} 处</summary>
<table><tr><th>章:节</th><th>OCR</th><th>改为</th><th>依据</th></tr>
{t_head}
</table></details>

<details class="aa-ed"><summary>脚注 {len(fns)} 条（含推断 2 处、原书缺注文 1 处）</summary>
<table><tr><th>注号所在词</th><th>扫描页</th><th>说明</th></tr>
{t_fn}
</table></details>
</div>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    units = json.loads((RAW / 'units.json').read_text(encoding='utf-8'))
    pg = pages(units)
    bad = [x['slug'] for x in pg if '{{' in x['body'] or '{%' in x['body'] or '⟦' in x['body']]
    if bad:
        raise SystemExit(f'正文里有 Liquid 记号或未替换的占位：{bad}')
    nanc = sum(x['body'].count('class="ax-anchor"') for x in pg)
    print(f'{len(pg)} 页；经节锚点 {nanc}/{sum(NV)}', file=sys.stderr)
    if nanc != sum(NV):
        raise SystemExit('经节锚点数不对')
    if not a.apply:
        return
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    stamp = now()
    OUT.mkdir(parents=True, exist_ok=True)
    for x in pg:
        meta.setdefault(x['slug'], stamp)
        (OUT / f'{x["slug"]}.md').write_text(page_md(x, meta[x['slug']]), encoding='utf-8')
    (OUT / 'index.html').write_text(index_html(units), encoding='utf-8')
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'写入 {len(pg)} 页 + 书首页 → {OUT}', file=sys.stderr)


if __name__ == '__main__':
    main()
