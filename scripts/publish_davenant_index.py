#!/usr/bin/env python3
"""达文南特卷二末尾六种索引 + ERRATA → davenant/colossians/indexes/*.md

输入  davenant_raw/colossians/davenant_colossians_index.txt
输出  davenant/colossians/indexes/{general,questions,contents,biographical,
      notes,scripture,errata}.md

渲染
----
索引条目一律直接出 HTML（`<p class="…">`），不走 markdown：条目里满是
`*` `_` `[` `&` 这些在 kramdown 里有语义的字符，逐个转义再让它解析一遍，
比自己拼标签更容易出岔子，也没有任何 markdown 语法要用。

原书是双栏密排、页码指向 1831 年印本。网页上改单栏悬挂缩进——分栏是纸面
排版的产物，照搬到网页只会在窄屏上碎掉；条目与页码的对应关系才是内容。
每一页页首都写明「页码指 1831 年印本」，免得读者拿去点本站的章节。

用法: python3 scripts/publish_davenant_index.py
"""
import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
OUT = ROOT / 'davenant' / 'colossians' / 'indexes'
BOOK_URL = '/davenant/colossians/'
BOOK_LABEL = 'Davenant on Colossians'

# raw 里的 SEC id → (文件名, 页面标题, 中文题名)
PAGES = {
    'index-general': ('general', 'General Index', '总索引'),
    'index-questions': ('questions', 'Index of Questions', '问题索引'),
    'contents-dissertation': ('contents', 'Contents of the Dissertation',
                              '《论基督之死》目次'),
    'index-biographical': ('biographical', 'Index to the Biographical Sketches',
                           '传略索引'),
    'index-notes': ('notes', 'Index of Subjects and Works in the Notes',
                    '注中人事索引'),
    'index-scripture': ('scripture', 'Index of Passages of Scripture',
                        '经文索引'),
    'errata': ('errata', 'Errata', '勘误'),
}
ORDER = ['index-general', 'index-questions', 'contents-dissertation',
         'index-biographical', 'index-notes', 'index-scripture', 'errata']

# 页首小字。第二栏那句只有传略索引要——它原书是个小表，两栏页码分属两卷。
LEAD = ('原书页码指 <strong>1831 年 Allport 英译本</strong>的印本页码，'
        '不是本站的章节编号。')
LEAD_BIO = LEAD + '右侧一列是卷二的页码，左侧行内的数字是卷一的。'


def esc(t):
    return html.escape(t, quote=False)


def parse():
    secs, cur = [], None
    for ln in (RAW / 'davenant_colossians_index.txt').read_text(
            encoding='utf-8').splitlines():
        m = re.match(r'^\[([A-Z0-9_]+)\] (.*)$', ln)
        if not m:
            continue
        tag, rest = m.group(1), m.group(2)
        if tag == 'SEC':
            sid, title, sub = (rest.split('|') + ['', ''])[:3]
            cur = {'id': sid, 'title': title, 'sub': sub, 'rows': []}
            secs.append(cur)
            continue
        if cur is None:
            continue
        rest = re.sub(r'^<!--[^>]*-->', '', rest)
        cur['rows'].append((tag, rest))
    return secs


def render(sec):
    out = []
    rows = []
    for tag, text in sec['rows']:
        # 连着几行的译者说明是同一段（经文索引那条占四行），拼成一段再出
        if tag == 'NOTE' and rows and rows[-1][0] == 'NOTE':
            rows[-1] = ('NOTE', rows[-1][1] + ' ' + text)
        else:
            rows.append((tag, text))
    for tag, text in rows:
        if tag == 'LETTER':
            out.append(f'<p class="dv-idx-letter">{esc(text)}</p>')
        elif tag == 'SUBHEAD':
            out.append(f'<h2>{esc(text)}</h2>')
        elif tag == 'CAPTION':
            out.append(f'<p class="dv-idx-caption">{esc(text)}</p>')
        elif tag == 'NOTE':
            out.append(f'<p class="dv-idx-note">{esc(text)}</p>')
        else:
            body, _, vol2 = text.partition('¦')
            lv = (len(body) - len(body.lstrip())) // 2
            cls = 'dv-idx' + ('-2' if lv else '')
            line = esc(body.strip())
            if vol2:
                line += f'<span class="dv-idx-b">{esc(vol2)}</span>'
            out.append(f'<p class="{cls}">{line}</p>')
    return out


def main():
    secs = [s for s in parse()]
    by = {s['id']: s for s in secs}
    chain = [k for k in ORDER if k in by]
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True,
                         text=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)

    def url(k):
        return f'{BOOK_URL}indexes/{PAGES[k][0]}/'

    for i, k in enumerate(chain):
        sec = by[k]
        slug, title, cn = PAGES[k]
        fm = ['---', 'layout: davenant-appendix', f'title: "{title}"',
              f'up_url: "{BOOK_URL}"', f'up_label: "{BOOK_LABEL}"',
              'kicker: "Indexes to the Original Edition"', 'dense: true',
              f'date: {now}']
        if sec['sub']:
            fm.append(f'subtitle: "{sec["sub"]}"')
        if i:
            fm += [f'prev_url: "{url(chain[i-1])}"',
                   f'prev_label: "{PAGES[chain[i-1]][1]}"']
        else:
            fm += [f'prev_url: "{BOOK_URL}gallican/"',
                   'prev_label: "The Gallican Controversy"']
        if i + 1 < len(chain):
            fm += [f'next_url: "{url(chain[i+1])}"',
                   f'next_label: "{PAGES[chain[i+1]][1]}"']
        fm.append('---')
        lead = LEAD_BIO if k == 'index-biographical' else LEAD
        body = [f'<p class="dv-idx-lead">{cn} · {lead}</p>'] + render(sec)
        (OUT / f'{slug}.md').write_text(
            '\n'.join(fm) + '\n\n' + '\n'.join(body) + '\n', encoding='utf-8')
        print(f'  → indexes/{slug}.md  {len(sec["rows"])} 行')
    # 书卷目录页用的清单，见 publish_davenant_appx.py 里同一处的说明
    data = ROOT / '_data' / 'davenant_indexes.yml'
    data.parent.mkdir(exist_ok=True)
    y = ['# 由 scripts/publish_davenant_index.py 生成，勿手改',
         'colossians:',
         '  - title: "Indexes to the Original Edition"',
         '    cn: "原书索引"',
         '    note: "1831 年英译本卷末的六种索引与勘误，页码指该印本，'
         '不是本站章节编号。双栏密排的几种已按栏重做 OCR。"',
         '    items:']
    for k in chain:
        slug, title, cn = PAGES[k]
        y += [f'      - url: "{url(k)}"', f'        label: "{title}"',
              f'        cn: "{cn}"']
    data.write_text('\n'.join(y) + '\n', encoding='utf-8')
    print(f'  → _data/{data.name}')
    print(f'[ok] {len(chain)} 页')
    return 0


if __name__ == '__main__':
    sys.exit(main())
