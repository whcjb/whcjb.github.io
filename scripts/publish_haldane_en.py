#!/usr/bin/env python3
"""霍尔丹《罗马书释义》英文版发布：haldane_raw/romans/units.json → haldane/romans/{1..16}.md + index.html

链条：fetch_haldane.sh → extract_haldane.py → 本脚本 → build_commentaries_index.py。重跑产物逐字节不变
（发布时刻记在 en_meta.json，首次写入后不改）。

- 一章一页；章首概述（Introduction）包在 .hd-intro 里；每条注释前放 commentary-anchor（id romans-章-节），
  录入本没单独讲的经节，锚点挂到讲它的那一条（向前找最近的一条）——保证 433 节节节有锚点。
- 正文写成 markdown 段落（内含 <em> 行内 HTML），脚注 [^fN] 才会被 kramdown 渲染；定义放该章末尾。
- 录入本只有注号、没有脚注正文的 7 条（22 23 34 38 56 57 58）给一条说明性的定义，免得页面上露出字面 [^f22]。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'haldane_raw' / 'romans'
OUT = ROOT / 'haldane' / 'romans'
META = RAW / 'en_meta.json'
NV = [32, 29, 31, 25, 21, 23, 25, 39, 33, 21, 36, 21, 14, 23, 33, 27]   # 罗马书各章节数
MISSING_NOTE = ('<span class="hd-fnmiss">The text of this note is wanting in the transcription on which this edition '
                'is based (the original edition prints it).</span>')


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def md_para(t: str) -> str:
    t = re.sub(r'^(\d+)\. ', r'\1\\. ', t)          # 段首「1. 」别被 kramdown 当有序列表
    t = re.sub(r'^([#>+\-]) ', r'\\\1 ', t)
    return t


def vlabel(e):
    if e['v1'] == e['v2']:
        return f'Ver. {e["v1"]}.'
    return f'Vers. {e["v1"]}–{e["v2"]}.'


def chapter_md(c, defs_all):
    ch = c['ch']
    out, covered, notes_here = [], set(), []
    verse_entries = [e for e in c['entries'] if 'v1' in e]
    # 每节锚点归到哪一条：该节有条目就是它，否则挂到它前面最近的一条（并讲）
    owner = {}
    for v in range(1, NV[ch - 1] + 1):
        cand = [e for e in verse_entries if e['v1'] <= v <= e['v2']] or \
               [e for e in verse_entries if e['v1'] <= v][-1:] or verse_entries[:1]
        owner.setdefault(id(cand[0]), []).append(v)
    for e in c['entries']:
        refs = re.findall(r'\[\^f(\d+)\]', ' '.join(e['paras'] + [e['lemma']]))
        notes_here += [r for r in refs if r not in notes_here]
        if e['key'] == 'introduction':
            out.append('<div class="hd-intro" markdown="1">')
            out.append('')
            out.append('Introduction')
            out.append('{: .hd-intro-h}')
            out.append('')
            for p in e['paras']:
                out += [md_para(p), '']
            out += ['</div>', '']
            continue
        for v in owner.get(id(e), []):
            out.append(f'<div class="commentary-anchor" id="romans-{ch}-{v}"></div>')
            covered.add(v)
        out.append('')
        lemma = f' <em>{e["lemma"]}</em>' if e['lemma'] else ''
        out += [f'<b class="hd-ver">{vlabel(e)}</b>{lemma}', '{: .hd-lemma}', '']
        for p in e['paras']:
            out += [md_para(p), '']
    for r in notes_here:
        txt = defs_all.get(r)
        out.append(f'[^f{r}]: {txt if txt else MISSING_NOTE}')
    missing = set(range(1, NV[ch - 1] + 1)) - covered
    return '\n'.join(out).rstrip() + '\n', missing


def main():
    u = json.loads((RAW / 'units.json').read_text(encoding='utf-8'))
    defs = {k: v for c in u['chapters'] for e in c['entries'] for k, v in e['notes'].items()}
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    stamp = now()
    OUT.mkdir(parents=True, exist_ok=True)
    bad = []
    for c in u['chapters']:
        ch = c['ch']
        body, miss = chapter_md(c, defs)
        if miss:
            bad.append((ch, sorted(miss)))
        meta.setdefault(str(ch), stamp)
        fm = ['---', 'layout: haldane-chapter', 'book_id: romans', 'book_name: "Haldane on Romans"',
              f'title: "Romans {ch}"', 'subtitle: "Robert Haldane"', f'date: {meta[str(ch)]}', f'chapter: {ch}']
        if ch > 1:
            fm += [f'prev_url: "/haldane/romans/{ch - 1}/"', f'prev_label: "Romans {ch - 1}"']
        if ch < 16:
            fm += [f'next_url: "/haldane/romans/{ch + 1}/"', f'next_label: "Romans {ch + 1}"']
        if (OUT / 'zh' / f'{ch}.md').exists():
            fm.append(f'zh_url: "/haldane/romans/zh/{ch}/"')
        fm.append('---')
        (OUT / f'{ch}.md').write_text('\n'.join(fm) + '\n\n' + body, encoding='utf-8')
    if bad:
        sys.exit(f'有经节没有锚点：{bad}')
    (OUT / 'index.html').write_text(index_html(u), encoding='utf-8')
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    refs = sum(len(re.findall(r'\[\^f\d+\]', (OUT / f'{c["ch"]}.md').read_text())) for c in u['chapters'])
    print(f'写入 16 章 + 书首页 → {OUT.relative_to(ROOT)}；经节锚点 433/433；脚注 {len(defs)} 条定义')


def index_html(u):
    out = ['---', 'layout: haldane-book', 'book_id: romans', 'book_name: "Haldane on Romans"',
           'title: "Robert Haldane · Exposition of the Epistle to the Romans"', 'author: "Robert Haldane (1764–1842)"',
           'edition: "Exposition of the Epistle to the Romans, with Remarks on the Commentaries of Dr. Macknight, '
           'Professor Moses Stuart, and Professor Tholuck · first published 1835–1839"',
           *(['zh_url: "/haldane/romans/zh/"'] if (OUT / 'zh' / 'index.html').exists() else []), '---', '',
           '<h2 class="hd-group">Exposition</h2>', '<ul class="hd-chgrid">']
    out += [f'  <li><a href="{{{{ site.baseurl }}}}/haldane/romans/{c}/">Romans {c}</a></li>' for c in range(1, 17)]
    out += ['</ul>', '',
            '<div class="hd-note">',
            '<p><b>About this edition.</b> The text is the transcription distributed by BibleSupport.com (public domain), '
            'taken from StudyLight.org through the Internet Archive. It was checked passage by passage against a scan of the '
            'ninth edition (Edinburgh: William Oliphant, 1874; Internet Archive <code>expositionofthee00halduoft</code>): '
            'for chapters 1–16 no passage of the commentary is missing.</p>',
            '<p>The transcription contains the exposition of chapters 1–16 only. The following parts of the original edition '
            'are not in it and are not yet given here: the Preface and Introduction (pp. 3–18 of the 1874 edition); the two '
            'dissertations at the end, “The State of the Heathen World Destitute of the Gospel” (with “The Case of Cornelius”) '
            'and “The Sanctification of the Sabbath” (pp. 653–702); the Conclusion (pp. 703–712); and the Appendix, with the '
            'letter to the Rev. Edward Bickersteth and the remarks on Mr. Stuart, Dr. Macknight and Mr. Tholuck (pp. 713–730).</p>',
            '<p>Seven footnotes (nos. 22, 23, 34, 38, 56, 57, 58) are referred to in the text but their wording is wanting in '
            'the transcription; they are marked as such where they occur.</p>',
            '</div>', '']
    return '\n'.join(out)


if __name__ == '__main__':
    main()
