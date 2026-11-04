#!/usr/bin/env python3
"""dickson_raw/matthew/en_chapters/*.md（+ 判读表、缺页补录）→ dickson/matthew/*.md

    python3 scripts/publish_dickson_en.py            # 试跑
    python3 scripts/publish_dickson_en.py --apply

大卫·迪克森《马太福音简释》1651（第三版）。**一章一页**（`<章>.md`）：每节讲解太短，逐段分页翻起来太碎
（用户 2026-11-04），各段依次排进本章页，段前挂锚点 `#v<首节>`。原先的逐段页 `<章>-<首节>` 改成跳转页，
指到本章页对应锚点，站内外旧链接不死。共用逻辑在 tcp_publish.py（逐段分页的 publish 不用，这里重写）。

录入本第五章 23 节后缺原书 pp. 52–53（`〈MISSING:1〉`）：据 1647 年初版胶片影像补录的文字放 supplied/1.md，
发布时换进去，外包 `.dk-supplied` 并加一行说明；还没补录时照样留一行红字说明缺了哪两页。
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dickson_common as tc  # noqa: E402
import tcp_publish  # noqa: E402
from extract_dickson import NV  # noqa: E402

SUPPLIED = tc.RAW / 'supplied'
RE_MISS = re.compile(r'〈MISSING:(\d+)〉')
MISSING_PAGES = {1: 'pp. 52–53'}


def supplied(m):
    n = int(m.group(1))
    f = SUPPLIED / f'{n}.md'
    pp = MISSING_PAGES[n]
    if not f.exists():
        return (f'\n\n<p class="dk-supplied-note dk-gap">[{pp} of the 1651 edition are missing from the '
                f'transcription here (TCP gap {n}). 录入本此处缺原书 {pp}，待据 1647 年初版胶片影像补录。]</p>\n\n')
    body = f.read_text(encoding='utf-8').strip()
    return (f'\n\n<div class="dk-supplied" markdown="1">\n\n<p class="dk-supplied-note">{pp} of the 1651 edition are '
            'missing from the EEBO-TCP transcription; supplied here from the page images of the first edition '
            f'(Glasgow, 1647). 录入本缺原书 {pp}，据 1647 年格拉斯哥初版胶片影像补录。</p>\n\n' + body + '\n\n</div>\n\n')


class Dickson(tcp_publish.Book):
    def load_page(self, slug):
        md = super().load_page(slug)
        md = RE_MISS.sub(supplied, md)
        return re.sub(r'\n{3,}', '\n\n', md)

    def _anchor(self, slug, page):
        """首页逐条说明的位置链接：逐段页已并进本章页，链到本章页的原书页码锚点（没有就链段首）。"""
        ch, v1 = slug.split('-', 1) if re.fullmatch(r'\d+-\d+', slug) else (None, None)
        if ch is None:
            return super()._anchor(slug, page)
        return f'/{self.slug}/{self.book}/{ch}/' + (f'#p{page}' if page else f'#v{v1}')

    def redirect_stub(self, pg):
        to = f'/{self.slug}/{self.book}/{pg["ch"]}/#v{pg["v1"]}'
        return ('---\nlayout: null\nsitemap: false\n---\n<!doctype html>\n<meta charset="utf-8">\n'
                '<!-- 迪克森马太福音改为一章一页（用户 2026-11-04），逐段页只作跳转，保住旧链接。 -->\n'
                f'<link rel="canonical" href="{{{{ site.baseurl }}}}{to}">\n'
                f'<meta http-equiv="refresh" content="0; url={{{{ site.baseurl }}}}{to}">\n'
                f'<script>location.replace("{{{{ site.baseurl }}}}{to}");</script>\n'
                f'<title>{pg["rng"]} · {self.name}</title>\n'
                f'<p>本段已并入 <a href="{{{{ site.baseurl }}}}{to}">{self.ref} {pg["ch"]}</a>。</p>\n')

    def publish(self, apply):
        meta = json.loads(self.META.read_text(encoding='utf-8')) if self.META.exists() else {}
        m = meta.setdefault(self.book, {})
        stamp = self.now()
        pages = self.build_pages()
        front = [p for p in pages if p['group'] == 'front']
        chs = sorted(self.NV)
        nav = [dict(slug=p['slug'], short=p['title']) for p in front] + \
              [dict(slug=str(c), short=f'{self.ref} {c}') for c in chs]

        def fm_nav(i):
            out = []
            if i:
                out += [f'prev_url: "/{self.slug}/{self.book}/{nav[i - 1]["slug"]}/"', f'prev_label: "{nav[i - 1]["short"]}"']
            if i + 1 < len(nav):
                out += [f'next_url: "/{self.slug}/{self.book}/{nav[i + 1]["slug"]}/"', f'next_label: "{nav[i + 1]["short"]}"']
            return out

        def zh(slug):
            return [f'zh_url: "/{self.slug}/{self.book}/zh/{slug}/"'] if (self.OUT / 'zh' / f'{slug}.md').exists() else []

        files = {}
        for i, pg in enumerate(front):
            fm = ['---', f'layout: {self.layout}', f'book_id: {self.book}', f'book_name: "{self.name}"',
                  f'title: "{pg["title"]}"'] + ([f'subtitle: "{pg["subtitle"]}"'] if pg['subtitle'] else []) + \
                 [f'date: {m.setdefault(pg["slug"], stamp)}'] + fm_nav(i) + zh(pg['slug']) + ['---']
            files[pg['slug']] = '\n'.join(fm) + '\n\n' + self.render_body(pg['body'], pg) + '\n'
        for k, ch in enumerate(chs):
            secs = [p for p in pages if p.get('ch') == ch or p.get('inch') == ch]
            slug = str(ch)
            fm = ['---', f'layout: {self.layout}', f'book_id: {self.book}', f'book_name: "{self.name}"',
                  f'title: "{self.ref} {ch}"', f'subtitle: "{self.author}"', f'date: {m.setdefault(slug, stamp)}',
                  f'chapter: {ch}', 'verse_from: 1', f'verse_to: {self.NV[ch]}'] + fm_nav(len(front) + k) + zh(slug) + ['---']
            body = f'\n\n<hr class="{self.P}-secrule">\n\n'.join(
                (f'<div class="{self.P}-sec" id="v{p["v1"]}"></div>\n\n' if 'v1' in p else '')
                + self.render_body(p['body'], p) for p in secs)
            files[slug] = '\n'.join(fm) + '\n\n' + body + '\n'
            for p in secs:
                if 'v1' in p:
                    files[p['slug']] = self.redirect_stub(p)
        if apply:
            for slug, txt in files.items():
                (self.OUT / f'{slug}.md').write_text(txt, encoding='utf-8')
            idx = self.build_index(pages)
            (self.OUT / 'en').mkdir(exist_ok=True)
            (self.OUT / 'en' / 'index.html').write_text(idx, encoding='utf-8')
            if not (self.OUT / 'zh').exists():
                (self.OUT / 'index.html').write_text(idx, encoding='utf-8')
            self.META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        left = sum(len(self.tc.TOK.findall(p['body'])) for p in pages)
        conj = sum(len(self.RE_CONJ.findall(p['body'])) for p in pages)
        print(f'{self.slug}/{self.book}: {"写入" if apply else "试跑"} {len(front)} 篇卷首 + {len(chs)} 章（一章一页）；'
              f'逐段跳转页 {sum(1 for p in pages if "v1" in p)}；推补 {conj}；剩余缺字记号 {left}', file=sys.stderr)
        return pages


def about_en(f):
    return [
        '<p><b>About this text.</b> EEBO-TCP A35949 (the third edition, London: for Ralph Smith, 1651; Wing D1400), '
        'keyed by hand from the EEBO microfilm; CC0. Original spelling and italics are retained; the long s is printed '
        'as s. Page numbers of the original are kept as in-page anchors. Verse headings misprinted in the source '
        '(10:19 as 29; 12:8–9 as 18 and 8; 12:27 as 17) are left as printed; pages are named by the true verse. '
        'Pages 52–53 (on Matthew 5:24–30) are missing from the transcription.</p>',
        f'<p><b>Illegible places.</b> The keyers marked {f["n"]} places they could not read from the film images. '
        f'{f["w"]} have been read from the page images so far; {f["c"]} are editorial conjectures shown '
        f'<span class="dk-conj">[in brackets]</span>. The rest remain marked <span class="dk-gap">in red</span>.</p>']


def about_zh(f):
    return [
        '<p class="dk-note-zh"><b>文本说明。</b>本书据 EEBO-TCP 人工录入本 A35949（第三版，伦敦 1651 年，Wing D1400，'
        'EEBO 缩微胶片）。保留原书拼写与斜体，长 ſ 作 s；印本页码保留为页内锚点。原书有几处经文头节号印错'
        '（10:19 印作 29；12:8、9 印作 18、8；12:27 印作 17），正文照录，页名按真节号。'
        '录入本缺原书第 52–53 页（马太福音 5:24–30 的讲解），待据 1647 年格拉斯哥初版的胶片影像补录。'
        f'录入本有 {f["n"]} 处读不出的字，目前已看图读出 {f["w"]} 处；{f["c"]} 处为编者推补，以 '
        '<span class="dk-conj">[方括号]</span> 另色标出；其余标红留在明面，待对照 Internet Archive 所藏 1651、1647 '
        '两版胶片灰度扫描逐处判读。判读记录见 <code>dickson_raw/matthew/</code>。</p>']


BOOK = Dickson(
    tc=tc, NV=NV, slug='dickson', book='matthew', P='dk', layout='dickson-chapter',
    author='David Dickson', years='1583?–1663', name='Dickson on Matthew', ref='Matthew',
    edition='A Brief Exposition of the Evangel of Jesus Christ according to Matthew · '
            'the third edition, London: for Ralph Smith, 1651',
    front=[('title', 'Title Page', 'London, 1651'),
           ('dedication', 'Epistle Dedicatory', 'To the Earl of Loudoun, Chancellor of Scotland'),
           ('to-the-reader', 'To the Honest-Hearted Reader', ''),
           ('titles', 'The Titles of the Book', 'The New Testament; the Gospel according to Matthew')],
    back=[],
    back_label='',
    about_en=about_en, about_zh=about_zh,
    witness_zh='1651、1647 两版的胶片灰度扫描')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    BOOK.publish(a.apply)


if __name__ == '__main__':
    main()
