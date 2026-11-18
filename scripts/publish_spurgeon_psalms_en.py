#!/usr/bin/env python3
"""司布真《大卫的宝库》（The Treasury of David）英文版：Spurgeon Archive 录入本 → spurgeon/psalms/

    python3 scripts/publish_spurgeon_psalms_en.py

底本 spurgeon_raw/psalms/src/archive/<pref|psNNN>.html：The Spurgeon Archive（archive.spurgeon.org/treasury/，
Phil Johnson 建，现由 Midwestern Baptist Theological Seminary 维护）的人工录入本，每篇一页。
第 119 篇该站没有（目录链到 StudyLight），取 Blue Letter Bible 的同一录入本（spurgeon_raw/psalms/src/blb/，
逐字比对过诗 40 篇：两站正文字句相同，只差标点空格与 BLB 给经文引句加的引号）：全篇总论一页 + 每 8 节一页，共 23 页，
页址 /spurgeon/psalms/119/ 与 /spurgeon/psalms/119/1-8/ …

每篇页面的固定分块：TITLE / SUBJECT / DIVISION 等卷首说明（.td-head）→ EXPOSITION → EXPLANATORY NOTES AND
QUAINT SAYINGS → HINTS TO THE VILLAGE PREACHER → WORKS UPON THE … PSALM，各块一个 <h2 class="td-sec">。
已知缺陷：原书希伯来文在录入本里是按字体编码的拉丁字母（如 `(hwq)` = קוה），照录未改。
manual_fixes.tsv：Spurgeon Archive 页面编码丢字（U+FFFD）的补字表，逐条注明依据；原样须在该页恰好出现一次。
"""
import html
import re
from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'spurgeon_raw' / 'psalms' / 'src' / 'archive'
BLB = ROOT / 'spurgeon_raw' / 'psalms' / 'src' / 'blb'
PS119 = ['119'] + [f'119/{a}-{a + 7}' for a in range(1, 177, 8)]
OUT = ROOT / 'spurgeon' / 'psalms'
BASE = '/spurgeon/psalms'
BOOK = 'The Treasury of David'
SECTIONS = {'expo': 'Exposition', 'expl': 'Explanatory Notes and Quaint Sayings',
            'hint': 'Hints to the Village Preacher', 'othe': 'Other Works'}


def clean(x):
    """录入本段内 HTML → 页面 HTML：只留 b / i / br，大写标签转小写，去 FONT/CENTER/锚点。"""
    x = re.sub(r'<img src="images/([a-z])\.gif"[^>]*>', lambda m: m.group(1).upper(), x, flags=re.I)   # 首字下沉图
    x = re.sub(r'<(/?)(b|strong)\b[^>]*>', r'<\1b>', x, flags=re.I)
    x = re.sub(r'<(/?)(i|em)\b[^>]*>', lambda m: '<' + m.group(1) + 'em>', x, flags=re.I)
    x = re.sub(r'<br\s*/?>', '<br>', x, flags=re.I)
    x = re.sub(r'<(?!/?(b|em|br)\b)[^>]+>', '', x)
    x = html.unescape(x).replace('&', '&amp;').replace('<b>', '\x01').replace('</b>', '\x02')
    x = x.replace('<em>', '\x03').replace('</em>', '\x04').replace('<br>', '\x05')
    x = x.replace('<', '&lt;').replace('>', '&gt;')
    x = x.replace('\x01', '<b>').replace('\x02', '</b>').replace('\x03', '<em>').replace('\x04', '</em>').replace('\x05', '<br>')
    x = re.sub(r'<em>(\s*)</em>|<b>(\s*)</b>', r'\1\2', x)
    x = re.sub(r'\s+', ' ', x).strip()
    return re.sub(r'(<br>\s*)+$', '', x).strip()


def paras(chunk):
    out = []
    for p in re.split(r'<p\b[^>]*>|</p>|<hr\b[^>]*>', chunk, flags=re.I):
        c = clean(p)
        if c:
            out.append(c)
    return out


def page_body(t):
    """→ (标题, [(区块 id 或 None, [段落])])"""
    t = re.sub(r'(?is)<(script|style)\b.*?</\1>', '', t)
    h1 = re.search(r'<h1>(.*?)</h1>', t, re.I | re.S)
    title = clean(h1.group(1))
    body = t[h1.end():]
    end = re.search(r'Collection administered by', body)
    body = body[:end.start()] if end else body
    # 去掉目录链接块（Exposition / Explanatory … 的页内跳转）
    body = re.sub(r'<A HREF="[^"]*#(expo|expl|hint|othe)">[^<]*</a>\s*(<BR>|<P>)?', '', body, flags=re.I)
    parts = re.split(r'<A NAME="(expo|expl|hint|othe)">(.*?)</A>', body, flags=re.I | re.S)
    blocks = [(None, paras(parts[0]))]
    for k in range(1, len(parts), 3):
        blocks.append((parts[k].lower(), [clean(parts[k + 1])], paras(parts[k + 2])))
    return title, blocks


def render(blocks):
    out = []
    plain = len(blocks) == 1            # 序言：没有分块，不套卷首说明样式
    for b in blocks:
        if b[0] is None:
            out += [f'<p>{p}</p>' if plain else f'<p class="td-head">{p}</p>' for p in b[1]]
            continue
        sid, head, ps = b
        out.append(f'<h2 class="td-sec" id="{sid}">{head[0]}</h2>')
        for p in ps:
            p = re.sub(r'^<b>((?:Verses?|Whole Psalm)[^<]*)</b>', r'<b class="td-v">\1</b>', p)
            out.append(f'<p>{p}</p>')
    return '\n\n'.join(out)


class BLBParser(HTMLParser):
    """BLB 第 119 篇页面正文 → [(kind, html)]，kind: sec / sub / p / hint{n} / quote / auth。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.buf, self.kind = [], None, None
        self.depth = 0          # hint-list 嵌套层数
        self.divs = []          # 每个打开的 div 是什么
        self.quote = False

    def flush(self):
        if self.buf is not None:
            x = clean(''.join(self.buf))
            if x:
                self.out.append((self.kind, x))
        self.buf = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'div':
            cls = a.get('class', '')
            self.divs.append(cls)
            if 'hint-list' in cls:
                self.depth += 1
            elif 'tod_authorRepos' in cls:
                self.flush(); self.buf, self.kind = [], 'auth'
        elif tag == 'h3':
            self.flush()
            hid = a.get('id', '')
            self.buf, self.kind = [], 'sec' if hid.startswith(('exposition', 'notes')) else 'sub'
        elif tag == 'blockquote':
            self.quote = True
        elif tag == 'p':
            if self.kind == 'auth' and self.buf is not None:
                return
            self.flush()
            self.buf, self.kind = [], 'quote' if self.quote else (f'hint{self.depth}' if self.depth else 'p')
        elif self.buf is not None:
            if tag in ('b', 'strong', 'i', 'em', 'br', 'small'):
                self.buf.append(f'<{tag}>' if tag != 'small' else '\x06')
            elif tag == 'a' and (a.get('href') or '').startswith('#fn'):
                self.buf.append('\x07')

    def handle_endtag(self, tag):
        if tag == 'div':
            cls = self.divs.pop() if self.divs else ''
            if 'hint-list' in cls:
                self.depth -= 1
            elif 'tod_authorRepos' in cls:
                self.flush()
        elif tag in ('h3', 'p'):
            if not (tag == 'p' and self.kind == 'auth'):
                self.flush()
        elif tag == 'blockquote':
            self.quote = False
        elif self.buf is not None:
            if tag in ('b', 'strong', 'i', 'em'):
                self.buf.append(f'</{tag}>')
            elif tag == 'small':
                self.buf.append('\x08')
            elif tag == 'a' and self.buf and self.buf[-1] == '\x07':
                self.buf.pop()

    def handle_data(self, d):
        if self.buf is not None:
            self.buf.append(html.escape(d, quote=False))


def blb_page(slug):
    f = BLB / ('ps119_00.html' if slug == '119' else 'ps119_{:03d}-{:03d}.html'.format(*map(int, slug[4:].split('-'))))
    t = re.sub(r'(?is)<(script|style)\b.*?</\1>', '', f.read_text(encoding='utf-8', errors='replace'))
    i = t.find('class="spurgeon_charles tod"')
    i = t.find('<hr', t.find('id="tod_nav"', i))
    j = t.find('<div id="bodyCol2"', i)
    ps = BLBParser()
    ps.feed(t[t.find('>', i) + 1:j])
    ps.flush()
    title = 'Psalm 119' if slug == '119' else 'Psalm 119:' + slug[4:].replace('-', '–')
    out, seen_sec = [], False
    for kind, x in ps.out:
        x = x.replace('\x07', '').replace('\x06', '<small>').replace('\x08', '</small>')
        x = re.sub(r'\{\s*(\d+)\s*\}', r'<sup>\1</sup>', x)
        if kind == 'sec':
            seen_sec = True
            out.append(f'<h2 class="td-sec">{x}</h2>')
        elif kind == 'sub':
            out.append(f'<h3 class="td-sub">{x}</h3>')
        elif kind == 'auth':
            out.append(f'<p class="td-auth">{x}</p>')
        elif kind == 'quote':
            out.append(f'<p class="td-quote">{x}</p>')
        elif kind.startswith('hint'):
            out.append(f'<p class="td-hint td-hint-{min(int(kind[4:]), 3)}">{x}</p>')
        else:
            if re.fullmatch(r'Psalm 119:[\d-]+', x):     # BLB 自加的经文链接行，原书没有
                continue
            x = re.sub(r'^<b>((?:Verses?|Whole)[^<]*)</b>', r'<b class="td-v">\1</b>', x)
            out.append(f'<p class="td-head">{x}</p>' if not seen_sec else f'<p>{x}</p>')
    return title, '\n\n'.join(out)


def main():
    order = ['preface']
    for n in range(1, 151):
        if n == 119:
            order += [s for s in PS119 if (BLB / ('ps119_00.html' if s == '119' else
                      'ps119_{:03d}-{:03d}.html'.format(*map(int, s[4:].split('-'))))).exists()]
        elif (SRC / f'ps{n:03d}.html').exists():
            order.append(str(n))
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    OUT.mkdir(parents=True, exist_ok=True)
    pages = []
    for slug in order:
        if slug.startswith('119'):
            title, body = blb_page(slug)
            pages.append(dict(slug=slug, title=title, html=body))
            continue
        f = SRC / ('pref.html' if slug == 'preface' else f'ps{int(slug):03d}.html')
        title, blocks = page_body(f.read_text(encoding='utf-8', errors='replace'))
        pages.append(dict(slug=slug, title=title, html=render(blocks)))
    fixes = [l.split('\t') for l in (ROOT / 'spurgeon_raw' / 'psalms' / 'manual_fixes.tsv').read_text(encoding='utf-8').splitlines()
             if l and not l.startswith('#')]
    for r in fixes:
        pg = next(p for p in pages if p['slug'] == r[0])
        if pg['html'].count(r[1]) != 1:
            raise SystemExit(f'改正表：第 {r[0]} 篇「{r[1]}」命中 {pg["html"].count(r[1])} 次')
        pg['html'] = pg['html'].replace(r[1], r[2])
    for i, p in enumerate(pages):
        dst = OUT / f'{p["slug"]}.md'
        dst.parent.mkdir(parents=True, exist_ok=True)
        m = re.search(r'^date: (.+)$', dst.read_text(encoding='utf-8'), re.M) if dst.exists() else None
        fm = ['---', 'layout: spurgeon-psalms-chapter', 'book_id: psalms', f'book_name: "{BOOK}"',
              f'title: "{p["title"]}"', f'date: {m.group(1) if m else stamp}']
        if i:
            fm += [f'prev_url: "{BASE}/{pages[i-1]["slug"]}/"', f'prev_label: "{pages[i-1]["title"]}"']
        if i + 1 < len(pages):
            fm += [f'next_url: "{BASE}/{pages[i+1]["slug"]}/"', f'next_label: "{pages[i+1]["title"]}"']
        fm.append('---')
        dst.write_text('\n'.join(fm) + '\n\n' + p['html'] + '\n', encoding='utf-8')
    cells = ''.join(f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/{p["slug"]}/">{p["slug"]}</a></li>\n'
                    for p in pages if p['slug'].isdigit())
    c119 = ''.join(f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/{p["slug"]}/">{p["slug"][4:] or "Whole Psalm"}</a></li>\n'
                   for p in pages if p['slug'].startswith('119'))
    have = {p['slug'] for p in pages}
    missing = [n for n in range(1, 151) if str(n) not in have]
    (OUT / 'index.html').write_text(f'''---
layout: spurgeon-psalms-book
book_id: psalms
book_name: "{BOOK}"
author: "Charles Haddon Spurgeon (1834–1892)"
edition: "Seven volumes, London, 1869–1885"
title: "Spurgeon, {BOOK}"
---

<ul class="td-toc td-wide">
  <li><a href="{{{{ site.baseurl }}}}{BASE}/preface/">Preface</a></li>
</ul>
<h2 class="td-group">Psalms</h2>
<ul class="td-toc td-nums">
{cells}</ul>
<h2 class="td-group">Psalm 119 <small>（by sections of eight verses）</small></h2>
<ul class="td-toc td-wide">
{c119}</ul>

<div class="td-note">
<p><b>About this text.</b> The text is the transcription of <i>The Treasury of David</i> made for The Spurgeon Archive
(archive.spurgeon.org, now administered by Midwestern Baptist Theological Seminary).
Each psalm has Spurgeon’s own Exposition, the Explanatory Notes and Quaint Sayings he collected from earlier writers,
and his Hints to the Village Preacher.{" Not yet added: Psalm " + ", ".join(map(str, missing)) + "." if missing else ""}
Hebrew words in that transcription are encoded in a Latin-letter font (e.g. “hwq” for קוה) and are reproduced as found.</p>
<p class="td-note-zh"><b>文本说明。</b>正文据 Spurgeon Archive（司布真文献库，现由中西部浸信会神学院维护）的人工录入本。
每篇含司布真本人的讲解、他汇集的历代注释与古人语录、给乡村传道人的讲章提示。{"尚未收入：第 " + "、".join(map(str, missing)) + " 篇。" if missing else ""}
录入本里的希伯来文是按字体编码的拉丁字母（如 “hwq” 即 קוה），暂照录未改。中文版《大卫宝库》另有麦种传道会正式译本，本站不做中译。</p>
</div>
''', encoding='utf-8')
    print(len(pages), 'pages; missing', missing)


if __name__ == '__main__':
    main()
