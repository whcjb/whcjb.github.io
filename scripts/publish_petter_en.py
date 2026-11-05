#!/usr/bin/env python3
"""petter_raw/mark/en_chapters/*.md（+ 判读表）→ petter/mark/*.md

    python3 scripts/publish_petter_en.py            # 试跑
    python3 scripts/publish_petter_en.py --apply

乔治·佩特《马可福音注释》1661。共用 tcp_publish.Book：**一讲一页**（页名 `<章>-<首节>[b|c…]`，同一首节连讲几讲
依次加字母），每章一页目录 `<章>.md`。每讲原是一次主日讲道，经文框里有讲道日期（页边旁注），章目录逐讲注出。

录入本只到原书 p.884（第十一章末）：书首页第 12–16 章标灰并注明；第十一章末讲 `〈MISSING:1〉` 换成一行说明。
卷首字母索引的页码是原书页码：≤ 884 的链到那一讲页里的页码锚点，其余照录。
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import petter_common as tc  # noqa: E402
import tcp_publish  # noqa: E402
from extract_petter import NV, NV_ALL  # noqa: E402

RE_MISS = re.compile(r'\n*〈MISSING:1〉\n*')
END_NOTE = ('<p class="pt-endnote">The transcription ends here. The copy filmed for EEBO (British Library) lacks everything '
            'after p. 884, so the commentary on chapters 12–16 is not available on this site. '
            '录入本所据大英图书馆藏本缺原书第 884 页以后的全部内容，第 12–16 章的注释本站暂缺。</p>')
ORD = ['', '', '2nd', '3rd'] + [f'{k}th' for k in range(4, 20)]


def date_of(body):
    """经文框里的讲道日期旁注（「June 28. 1618.」）。框里没有就空。"""
    m = re.search(r'<div class="pt-text" markdown="1">(.*?)\n\n</div>', body, re.S)
    if not m:
        return ''
    d = re.search(r'<span class="pt-margin" markdown="1">(.*?)</span>', m.group(1))
    return re.sub(r'<[^>]+>|\*', '', d.group(1)).strip() if d else ''


class Petter(tcp_publish.Book):
    def load_page(self, slug):
        md = super().load_page(slug)
        if '〈MISSING:1〉' in md:
            md = RE_MISS.sub('\n\n', md).rstrip() + '\n\n' + END_NOTE
        if slug == 'alphabetical-table':
            md = self.link_table(md)
        return md

    def page_map(self):
        """原书页码 → 所在发布页 slug。"""
        if not hasattr(self, '_pm'):
            pm = {}
            for slug in self.tc.order()['order']:
                for n in re.findall(r'<span class="pt-pb" id="p(\d+)"', self.tc.read_src(slug)):
                    pm.setdefault(int(n), slug)
            self._pm = pm
        return self._pm

    def link_table(self, md):
        pm = self.page_map()

        def one(m):
            n = int(m.group(0))
            if n in pm:
                return f'<a href="{{{{ site.baseurl }}}}/{self.slug}/{self.book}/{pm[n]}/#p{n}">{n}</a>'
            return m.group(0)

        def para(m):                           # 只动每条末尾那串页码（「…, 1434, 1615 1616」）
            txt = m.group(2)
            k = re.search(r'(?:[ ,.;]*\b\d{1,4}\b)+[ .,;]*$', txt)
            if not k:
                return m.group(0)
            return m.group(1) + txt[:k.start()] + re.sub(r'\b\d{1,4}\b', one, txt[k.start():]) + m.group(3)
        return re.sub(r'(<p class="pt-ix(?:term|sub)" markdown="1">)(.*?)(</p>)', para, md)

    def build_pages(self):
        pages = super().build_pages()
        for p in pages:
            if p['group'] != 'section':
                continue
            k = re.search(r'([a-z])$', p['slug'])
            nth = ORD[ord(k.group(1)) - ord('a') + 1] if k else ''
            d = date_of(p['body'])
            if nth:
                p['title'] = f'{p["rng"]} ({nth} lecture)'
                p['short'] = f'{p["short"]} ({nth})'
            p['rng'] = p['rng'] + (f' · preached {d}' if d else '')
        return pages

    def build_index(self, pages):
        idx = super().build_index(pages)
        return idx.replace('<small>not on this site</small>', '<small>lacking in the source</small>')


def about_en(f):
    return [
        '<p><b>About this text.</b> EEBO-TCP A54583 (London: J. Streater for George Sawbridge, 1661; Wing P1888), '
        'keyed by hand from the EEBO microfilm of the British Library copy; CC0. That copy is imperfect: it lacks '
        'everything after p. 884, so the transcription ends with chapter 11 and the commentary on chapters 12–16 '
        'is wanting. Original spelling and italics are retained; the long s is printed as s. Page numbers of the '
        'original are kept as in-page anchors. Each page is one lecture, as preached at Brede from June 1618 '
        'onward; the date in the margin of each text is the author’s own. The marginal heads of the original '
        '(<i>Observ.</i>, <i>Use</i>, <i>Quest.</i>, <i>Answ.</i> …) are shown as small tags in the text. '
        'Two lecture headings disagree with the text they introduce (7:33–34 headed “33, 24”; 8:31 headed “Mark 7. 31.”); '
        'the 1661 page images show these are misprints in the original. They are left as printed, and the pages are named by the true verse.</p>',
        f'<p><b>Illegible places.</b> The keyers marked {f["n"]} places they could not read from the film images. '
        f'{f["w"]} have been read from the page images so far; {f["c"]} are editorial conjectures shown '
        f'<span class="pt-conj">[in brackets]</span>. The rest remain marked <span class="pt-gap">in red</span>.</p>']


def about_zh(f):
    return [
        '<p class="pt-note-zh"><b>文本说明。</b>本书据 EEBO-TCP 人工录入本 A54583（伦敦 1661 年，J. Streater 印、'
        'George Sawbridge 发售，Wing P1888；作者身后由其弟约翰·佩特出版并作序），录入所据为大英图书馆藏本的 EEBO 缩微胶片。'
        '该藏本残缺，缺原书第 884 页以后的全部内容，<b>录入本止于第十一章，第 12–16 章的注释暂缺</b>。'
        '保留原书拼写与斜体，长 ſ 作 s；印本页码保留为页内锚点。每页是一讲，原是作者 1618 年 6 月起在布雷德（Brede）逐主日所讲，'
        '经文旁的日期是原书页边所记的讲道日期；原书页边的纲目标记（Observ. 观察、Use 应用、Quest. 问、Answ. 答等）在正文中以小标签显示。'
        '有两处讲题与经文对不上（7:33–34 题作「33, 24」；8:31 题作「Mark 7. 31.」），对照 1661 年原版影像，是原书印错，录入无误；正文照原书，页名按真节号。'
        f'录入本有 {f["n"]} 处读不出的字，对照 1661 年原版胶片影像（Internet Archive，希腊文与缺整词处取原生分辨率）'
        f'已看图读出 {f["w"]} 处；{f["c"]} 处墨淡褪色、只认得出部分字形，由编者推补，以 '
        '<span class="pt-conj">[方括号]</span> 另色标出，逐条列在下面；其余标红留在明面。'
        '判读记录见 <code>petter_raw/mark/</code>。</p>']


BOOK = Petter(
    tc=tc, NV=NV, slug='petter', book='mark', P='pt', layout='petter-chapter',
    author='George Petter', years='?–1654', name='Petter on Mark', ref='Mark',
    edition='A Learned, Pious, and Practical Commentary upon the Gospel according to St. Mark · '
            'London: J. Streater for George Sawbridge, 1661',
    front=[('title', 'Title Page', 'London, 1661'),
           ('preface', 'The Preface to the Pious Reader', 'by John Petter, the author’s brother, 1661'),
           ('alphabetical-table', 'An Alphabetical Table', 'The principal matters of the Commentary')],
    back=[],
    back_label='',
    all_chapters=list(NV_ALL),
    about_en=about_en, about_zh=about_zh,
    witness_zh='1661 年原版胶片影像（原生分辨率）')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    BOOK.publish(a.apply)


if __name__ == '__main__':
    main()
