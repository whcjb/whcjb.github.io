#!/usr/bin/env python3
"""亚历山大《马太福音释义》(1861) 英文版发布：alexander_raw/matthew/units.json → alexander/matthew/

units.json 由 scripts/extract_alexander_matthew.py 生成（录入本字句 + 扫描本斜体三证人投票 + 经文头 + 脚注）。
本脚本只管排版：

  alexander/matthew/preface/                  序（S. D. A.，1860）
  alexander/matthew/<N>/                      逐章注释（1–16 详注，17–28 纲要）
  alexander/matthew/index.html                书首页（含文本说明与编者改动逐条表）

date 沿用 en_meta.json 里的原值，新页才写当前真实时间。

用法：python3 scripts/publish_alexander_matthew_en.py            # 试跑
      python3 scripts/publish_alexander_matthew_en.py --apply    # 写盘
"""
import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'alexander_raw' / 'matthew'
OUT = ROOT / 'alexander' / 'matthew'
META = RAW / 'en_meta.json'
BOOK_NAME = 'Alexander on Matthew'
AUTHOR = 'Joseph Addison Alexander'

# KJV 马太福音各章节数
NV = [25, 23, 17, 25, 48, 34, 29, 34, 38, 42, 30, 50, 58, 36, 39, 28, 27, 35, 30, 34, 46, 46, 39, 51, 46, 75,
      66, 20]
DETAIL_TO = 16                  # 逐节详注到第 16 章；17–28 章原书只有纲要


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
        return f'<sup class="am-fnref"><a href="#matthew-{ch}-fn{n}" id="matthew-{ch}-fnref{n}">{mk}</a></sup>'
    return [re.sub(r'⟦fn:(\d+)⟧', rep, h) for h in paras_html]


def notes_block(ch, notes):
    if not notes:
        return ''
    out = ['<div class="am-notes">']
    for n, x in enumerate(notes, 1):
        mk = html.escape(x['mark'])
        txt = x['text']
        if txt is None:
            raise SystemExit(f'第 {ch} 章脚注 {n}（p.{x["page"]}）还没转录：footnotes.tsv 缺这一条')
        if txt == '⟦missing⟧':
            txt = ('<span class="am-lost">No note is printed for this mark in the original edition '
                   '(checked against the page images).</span>')
        out.append(f'<p id="matthew-{ch}-fn{n}"><a class="am-fnback" href="#matthew-{ch}-fnref{n}">{mk}</a> {txt}</p>')
    out.append('</div>')
    return '\n'.join(out)


def chapter_body(c):
    ch = c['ch']
    notes = c.get('notes', [])
    out = []
    g = c.get('group')
    if g:                          # 登山宝训（5–7 章）总说，排在第 5 章章首
        if g.get('notes'):
            raise SystemExit('登山宝训总说里有脚注，发布脚本未处理')
        out.append(f'<h3 class="am-group">Chapters 5–7</h3>')
        out += [f'<p class="am-analysis">{h}</p>' for h in g['paras']]
    for h in fn_html(ch, c['intro'], notes):
        out.append(f'<p class="am-analysis">{h}</p>')
    if ch > DETAIL_TO:             # 纲要章：全章各节锚点都挂在纲要段之前
        out = [f'<span class="ax-anchor" id="matthew-{ch}-{v}"></span>' for v in range(1, NV[ch - 1] + 1)] + out
        if c['units']:
            raise SystemExit(f'第 {ch} 章应只有纲要，却有逐节注释')
        nb = notes_block(ch, notes)
        return '\n\n'.join(out + ([nb] if nb else []))
    seen = set()
    for u in c['units']:
        vv = [v for v in u['vv'] if v not in seen and 1 <= v <= NV[ch - 1]]
        seen.update(vv)
        out += [f'<span class="ax-anchor" id="matthew-{ch}-{v}"></span>' for v in vv]
        head = html.escape(u['head'], False) if u['head'] else ''
        out.append(f'<p class="am-head"><span class="am-vn">{vlabel(u["vv"])}</span> {head}</p>')
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
    pg = [dict(slug='preface', title='Preface', label='Preface', body=front_body(units['preface']))]
    for c in units['chapters']:
        pg.append(dict(slug=str(c['ch']), title=f'Matthew {c["ch"]}', label=f'Matthew {c["ch"]}', chapter=c['ch'],
                       body=chapter_body(c)))
    for i, x in enumerate(pg):
        x['prev'] = pg[i - 1] if i else None
        x['next'] = pg[i + 1] if i + 1 < len(pg) else None
    return pg


def page_md(x, date):
    fm = ['---', 'layout: alexander-matthew-chapter', 'book_id: matthew', f'book_name: "{BOOK_NAME}"',
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
    t_fn = '\n'.join(f'<tr><td>p.{esc(p)}</td><td>{esc(k)}</td><td>{esc(r) if r else "照原图转录"}</td></tr>'
                     for p, k, _, _, r in [(f + [''])[:5] for f in fns])
    nfn = sum(len(c.get('notes', [])) for c in units['chapters'])
    return f'''---
layout: alexander-matthew-book
book_id: matthew
book_name: "{BOOK_NAME}"
title: "The Gospel according to Matthew Explained"
chapters: 28
---

<div class="am-note">
<p><b>About this text.</b> The wording follows the Precept Austin e-text of Alexander's
<i>The Gospel according to Matthew Explained</i> (from the 1864 printing; Greek and Hebrew intact).
That e-text drops all italics, the verse of the English Bible printed in large type before each comment,
and the text of the author's footnotes (the reference marks survive). These have been restored from three scans
(Internet Archive, Princeton Theological Seminary copies: <i>gospelaccordingt00alex</i> and
<i>gospelaccordin00alex</i>, New York: Charles Scribner, 1861; <i>gospelaccordingt00alex_0</i>, 1864):
italics by a word-for-word majority of the three scans; the verse headings from the 1861 scan, with misread
letters corrected against the King James text and doubtful places checked on the page images; the footnotes
transcribed from the page images and matched to the marks in order. As the preface explains,
the notes are complete only to the end of chapter 16; for chapters 17–28 the author left an analysis of each
chapter.</p>
<p class="am-note-zh"><b>文本说明。</b>正文字句据 Precept Austin 网页录入本（据 1864 年重印本，希腊文、希伯来文完整）。
该本丢了三样东西：全书斜体（亚历山大以斜体标出所讲解的经文字词与他自己的译法）、每条注释前大字排印的英文经文、
作者页脚注的注文（注号还在）。这三样都从三份扫描本补回（IA 普林斯顿神学院藏 1861 年纽约初版两份、1864 年重印一份）：
斜体按三份扫描本逐词多数票；经文头取自 1861 年扫描本，OCR 读坏的字以 KJV 同位词为证人修正，拿不准的逐处看原图；
脚注 {nfn} 条逐条看原图转录，与录入本注号按次序逐条配对。对齐录入本 {L["words"]:,} 词中的 {L["aligned"]:,} 词；
经文头 {L["heads_placed"]} 条落位。原书逐节详注只到第 16 章，第 17–28 章作者只留下每章一段纲要（见序）。
以下逐条列出所有编者改动。</p>

<details class="am-ed"><summary>录入本错字 {len(body_fixes)} 处（扫描本同位一致，逐条看原图核过）</summary>
<table><tr><th>录入本</th><th>改为</th><th>扫描本出处</th></tr>
{t_body}
</table></details>

<details class="am-ed"><summary>经文头：OCR 字形混淆按 KJV 改回 {len(confus)} 类（逐类看图）</summary>
<table><tr><th>OCR → 改为</th><th>依据</th></tr>
{t_conf}
</table></details>

<details class="am-ed"><summary>经文头逐条手改 {len(head_manual)} 处</summary>
<table><tr><th>章:节</th><th>OCR</th><th>改为</th><th>依据</th></tr>
{t_head}
</table></details>

<details class="am-ed"><summary>脚注 {nfn} 条（逐条看原图转录）</summary>
<table><tr><th>扫描页</th><th>页内第几条</th><th>说明</th></tr>
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
