"""TCP 录入本注释书的英文版发布（霍尔、巴洛《提摩太后书》共用）。骨架照搬 publish_taylor_en.py，
书名、前缀、卷首卷末篇目、文本说明做成参数（见 publish_hall_en.py / publish_barlow_en.py）。

一段经文一页，页名 `<章>-<首节>`；每章另出一页目录 `<章>.md`（历代解经扫描器与对照抽屉按章号页找书）。
date 一律沿用 en_meta.json 里的原值，新页才写当前真实时间。
"""
import html
import json
import re
import subprocess
import sys


class Book:
    """cfg 键：tc（*_common 模块）NV slug book P layout author years name ref edition
    front back extra（[(插在哪页之后, slug, 标题, 副标题)]）about_en about_zh witness_zh"""

    def __init__(self, **cfg):
        self.__dict__.update(cfg)
        self.ROOT = self.tc.ROOT
        self.RAW = self.tc.RAW
        self.META = self.RAW / 'en_meta.json'
        self.OUT = self.ROOT / self.slug / self.book
        self.RE_CONJ = re.compile(r'⟦([^⟧]*)⟧')

    def rng(self, ch, a, b):
        return f'{self.ref} {ch}:{a}' + ('' if a == b else f'–{b}')

    def load_page(self, slug):
        f = self.RAW / 'manual_pages' / f'{slug}.html'
        if f.exists():
            return f.read_text(encoding='utf-8').strip()
        md = self.tc.load(slug)
        # 献辞题头等原书逐行居中、字号递减的块：抽取压成一行粗体标题，照原图手排后换掉页首那行 ###
        # （页码锚点保留在前）。手排文件放 manual_heads/<slug>.html。
        h = self.RAW / 'manual_heads' / f'{slug}.html'
        if h.exists():
            m = re.match(r'(#+ )((?:<span class="[a-z]+-pb"[^>]*></span>)*)[^\n]*\n', md)
            if not m:
                raise ValueError(f'{slug}: 页首不是标题行，manual_heads 无处替换')
            md = m.group(2) + '\n\n' + h.read_text(encoding='utf-8').strip() + md[m.end():]
        return md

    def build_pages(self):
        od = self.tc.order()
        extra = {after: (s, t, sub) for after, s, t, sub in getattr(self, 'extra', [])}
        pages = []
        for slug, title, sub in self.front:
            pages.append(dict(slug=slug, title=title, subtitle=sub, body=self.load_page(slug), group='front'))
        for x in od['sections']:
            r = self.rng(x['ch'], x['v1'], x['v2'])
            short = f'{x["ch"]}:{x["v1"]}' + ('' if x['v1'] == x['v2'] else f'–{x["v2"]}')
            pages.append(dict(slug=x['slug'], title=r, short=short, rng=r, subtitle=self.author,
                              body=self.load_page(x['slug']), group='section', ch=x['ch'], v1=x['v1'], v2=x['v2']))
            if x['slug'] in extra:
                s, t, sub = extra[x['slug']]
                pages.append(dict(slug=s, title=t, short=t, rng=sub, subtitle=sub, body=self.load_page(s),
                                  group='section-extra', inch=x['ch']))
        for slug, title, sub in self.back:
            pages.append(dict(slug=slug, title=title, subtitle=sub, body=self.load_page(slug), group='back'))
        return pages

    def add_anchors(self, body, pg):
        """本段每节一个 commentary-anchor（07-verse-index §1），挂在段首经文框后；没有经文框的挂在页首。"""
        if 'ch' not in pg:
            return body
        anc = ''.join(f'\n\n<div class="commentary-anchor" id="{self.book}-{pg["ch"]}-{v}"></div>'
                      for v in range(pg['v1'], pg['v2'] + 1))
        m = re.search(rf'<div class="{self.P}-text" markdown="1">.*?\n\n</div>', body, re.S)
        if m and m.start() < 3000:
            return body[:m.end()] + anc + body[m.end():]
        return anc.lstrip('\n') + '\n\n' + body

    def render_body(self, body, pg):
        P = self.P
        body = re.sub(r'^(\d+)\. ', r'\1\\. ', body, flags=re.M)
        body = re.sub(r'^([IVXL]+)\. ', r'\1\\. ', body, flags=re.M)
        body = self.add_anchors(body, pg)
        title = ('Editorial conjecture: illegible in the source; supplied from the stated evidence '
                 '(编者推补；非原书原文)')
        body = self.RE_CONJ.sub(lambda m: f'<span class="{P}-conj" title="{title}">[{m.group(1)}]</span>'
                                if m.group(1) else '', body)
        body = self.tc.TOK.sub(lambda m: f'<span class="{P}-gap" title="TCP: illegible in source">{m.group(0)}</span>',
                               body)
        return body

    @staticmethod
    def now():
        return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()

    def fm_nav(self, pg, key):
        o = pg[key]
        if not o:
            return []
        return [f'{key}_url: "/{self.slug}/{self.book}/{o["slug"]}/"', f'{key}_label: "{o.get("short", o["title"])}"']

    def publish(self, apply):
        meta = json.loads(self.META.read_text(encoding='utf-8')) if self.META.exists() else {}
        stamp = self.now()
        pages = self.build_pages()
        for i, pg in enumerate(pages):
            pg['prev'] = pages[i - 1] if i else None
            pg['next'] = pages[i + 1] if i + 1 < len(pages) else None
        if apply:
            self.OUT.mkdir(parents=True, exist_ok=True)
        m = meta.setdefault(self.book, {})
        for pg in pages:
            slug = pg['slug']
            m.setdefault(slug, stamp)
            fm = ['---', f'layout: {self.layout}', f'book_id: {self.book}', f'book_name: "{self.name}"',
                  f'title: "{pg["title"]}"']
            if pg['subtitle']:
                fm.append(f'subtitle: "{pg["subtitle"]}"')
            fm.append(f'date: {m[slug]}')
            if 'ch' in pg:
                fm += [f'chapter: {pg["ch"]}', f'verse_from: {pg["v1"]}', f'verse_to: {pg["v2"]}']
            fm += self.fm_nav(pg, 'prev') + self.fm_nav(pg, 'next')
            if (self.OUT / 'zh' / f'{slug}.md').exists():
                fm.append(f'zh_url: "/{self.slug}/{self.book}/zh/{slug}/"')
            fm.append('---')
            if apply:
                (self.OUT / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + self.render_body(pg['body'], pg) + '\n',
                                                     encoding='utf-8')
        chs = sorted(self.NV)
        if apply:
            for k, ch in enumerate(chs):
                secs = [p for p in pages if p.get('ch') == ch or p.get('inch') == ch]
                slug = str(ch)
                m.setdefault(slug, stamp)
                fm = ['---', f'layout: {self.layout}', f'book_id: {self.book}', f'book_name: "{self.name}"',
                      f'title: "{self.ref} {ch}"', f'subtitle: "{self.author}"', f'date: {m[slug]}', f'chapter: {ch}',
                      'verse_from: 1', f'verse_to: {self.NV[ch]}']
                if k > 0:
                    fm += [f'prev_url: "/{self.slug}/{self.book}/{chs[k - 1]}/"', f'prev_label: "{self.ref} {chs[k - 1]}"']
                if k + 1 < len(chs):
                    fm += [f'next_url: "/{self.slug}/{self.book}/{chs[k + 1]}/"', f'next_label: "{self.ref} {chs[k + 1]}"']
                fm.append('---')
                lst = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/{self.slug}/{self.book}/{p["slug"]}/">{p["short"]}'
                                f'<small>{p["rng"]}</small></a></li>' for p in secs)
                (self.OUT / f'{slug}.md').write_text('\n'.join(fm) + f'\n\n<ul class="{self.P}-chtoc">\n{lst}\n</ul>\n',
                                                     encoding='utf-8')
            idx = self.build_index(pages)
            (self.OUT / 'en').mkdir(exist_ok=True)
            (self.OUT / 'en' / 'index.html').write_text(idx, encoding='utf-8')
            if not (self.OUT / 'zh').exists():
                (self.OUT / 'index.html').write_text(idx, encoding='utf-8')
            self.META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        left = sum(len(self.tc.TOK.findall(p['body'])) for p in pages)
        conj = sum(len(self.RE_CONJ.findall(p['body'])) for p in pages)
        print(f'{self.slug}/{self.book}: {"写入" if apply else "试跑"} {len(pages)} 页；推补 {conj}；剩余缺字记号 {left}',
              file=sys.stderr)
        return pages

    # ── 首页 ──
    def stats(self):
        sites = json.loads((self.RAW / 'gap_sites.json').read_text(encoding='utf-8'))
        dec = self.tc.decisions()
        w = sum(1 for g, v in dec.items() if v[1] == 'w')
        c = sum(1 for g, v in dec.items() if v[1] == 'c')
        return len(sites), w, c

    def _anchor(self, slug, page):
        return f'/{self.slug}/{self.book}/{slug}/' + (f'#p{page}' if page else '')

    @staticmethod
    def _ctx(s):
        return html.escape(' '.join(s['left'][-5:]) + ' ⟨' + s['tcp'] + '⟩ ' + ' '.join(s['right'][:5]))

    def notes_tables(self):
        """首页逐条说明（从判读表生成，表改首页跟着变）：① 编者推补（用户同意的推断）② 仍读不出的。"""
        P = self.P
        sites = {s['gid']: s for s in json.loads((self.RAW / 'gap_sites.json').read_text(encoding='utf-8'))}
        review = {int(r[0]): r for r in self.tc._tsv('gap_review.tsv')}
        appr = [(int(r[0]), r[1]) for r in self.tc._tsv('gap_approved.tsv')]
        out = []

        def loc(s):
            return (f'<a href="{{{{ site.baseurl }}}}{self._anchor(s["slug"], s.get("page"))}">{s["slug"]}'
                    + (f' · p.{s["page"]}' if s.get('page') else '') + '</a>')
        if appr:
            out.append(f'<h3 class="{P}-conjhead">编者推补逐条说明（{len(appr)} 处）</h3>')
            out.append(f'<p class="{P}-note-zh">以下各处录入本标为读不出，对照{self.witness_zh}也只能认出一部分字形。'
                       '编者按看得见的字形，参照本句上下文补出，经本站同意后发布。正文中以 '
                       f'<span class="{P}-conj">[方括号]</span> 另色标出，<b>不是原书确定的文字</b>；每条看图所见写在「依据」一栏。</p>')
            out.append(f'<table class="{P}-conjtab"><tr><th>位置</th><th>录入本原样（前后文）</th><th>现作</th><th>依据</th></tr>')
            for g, v in appr:
                s = sites[g]
                note = review.get(g, ['', '', '', ''])[3] if len(review.get(g, [])) > 3 else ''
                out.append(f'<tr><td>{loc(s)}</td><td>{self._ctx(s)}</td>'
                           f'<td>[{html.escape(v.replace("*", ""))}]</td><td>{html.escape(note)}</td></tr>')
            out.append('</table>')
        left = [g for g, r in review.items() if r[1] == '?']
        if left:
            out.append(f'<h3 class="{P}-conjhead">仍读不出的（{len(left)} 处）</h3>')
            out.append(f'<p class="{P}-note-zh">这些位置在{self.witness_zh}上都读不出，正文中标红留在明面，不推补。</p>')
            out.append(f'<table class="{P}-conjtab"><tr><th>位置</th><th>录入本原样（前后文）</th><th>原因</th></tr>')
            for g in sorted(left):
                s = sites[g]
                note = review[g][3] if len(review[g]) > 3 else ''
                out.append(f'<tr><td>{loc(s)}</td><td>{self._ctx(s)}</td><td>{html.escape(note)}</td></tr>')
            out.append('</table>')
        return out

    def build_index(self, pages):
        P = self.P
        out = ['---', f'layout: {self.layout.replace("-chapter", "-book")}', f'book_id: {self.book}',
               f'book_name: "{self.name}"', f'title: "{self.name}"', f'author: "{self.author} ({self.years})' + (f' · {self.author_note}' if getattr(self, 'author_note', '') else '') + '"',
               f'edition: "{self.edition}"']
        co = getattr(self, 'coauthor', None)       # 同卷另一本（提后：巴洛第 1 章 + 霍尔第 3–4 章），书首页并列两位作者
        if co:
            out += [f'author2: "{co[0]}"', f'author2_url: "{co[1]}"', f'edition2: "{co[2]}"']
        out += ['---', '']
        if (self.OUT / 'zh').exists():
            out.insert(-2, f'zh_url: "/{self.slug}/{self.book}/"')

        def link(p, sub=True):
            return (f'  <li><a href="{{{{ site.baseurl }}}}/{self.slug}/{self.book}/{p["slug"]}/">'
                    f'{p.get("short", p["title"]) if p["group"].startswith("section") else p["title"]}'
                    + (f'<small>{p["rng"] if p["group"].startswith("section") else p["subtitle"]}</small>'
                       if sub and (p.get('rng') or p.get('subtitle')) else '') + '</a></li>')
        out.append(f'<h2 class="{P}-group">Prefatory Matter</h2>')
        out += [f'<ul class="{P}-toc">'] + [link(p) for p in pages if p['group'] == 'front'] + ['</ul>']
        out.append(f'<h2 class="{P}-group">Chapters</h2>')
        # 这一卷由几本拼成（提后：巴洛第 1 章、霍尔第 3–4 章）：书首页按全卷章数排，本书没有的章接到别本，
        # 谁都没有的标灰。历代解经卡片只显示一位注释家，不在这里互相接上，另一本就没有入口。
        allch = getattr(self, 'all_chapters', None) or sorted(self.NV)
        other = getattr(self, 'others', {})
        cells = []
        for c in allch:
            if c in self.NV:
                cells.append(f'<li><a href="{{{{ site.baseurl }}}}/{self.slug}/{self.book}/{c}/">Chapter {c}</a></li>')
            elif c in other:
                who, url = other[c]
                cells.append(f'<li><a class="{P}-other" href="{{{{ site.baseurl }}}}{url}">Chapter {c}<small>{who}</small></a></li>')
            else:
                cells.append(f'<li><span class="{P}-none">Chapter {c}<small>not on this site</small></span></li>')
        out.append(f'<ul class="{P}-chgrid">' + ''.join(cells) + '</ul>')
        if other:
            out.append(f'<p class="{P}-note-zh {P}-companion">{self.companion_zh}</p>')
        # 逐段目录不放书首页（用户 2026-10-28：只留章格子，各段在每章目录页里列）
        if self.back:
            out.append(f'<h2 class="{P}-group">{self.back_label}</h2>')
            out += [f'<ul class="{P}-toc">'] + [link(p) for p in pages if p['group'] == 'back'] + ['</ul>']
        n, w, c = self.stats()
        left = sum(1 for r in self.tc._tsv('gap_review.tsv') if r[1] == '?')
        fill = dict(n=f'{n:,}', w=f'{w:,}', c=f'{c:,}', left=f'{left:,}')
        out.append(f'<div class="{P}-note">')
        for para in self.about_en(fill) + self.about_zh(fill):
            out.append(para)
        out.extend(self.notes_tables())
        out.append('</div>')
        return '\n'.join(out) + '\n'
