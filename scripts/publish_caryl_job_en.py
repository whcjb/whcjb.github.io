#!/usr/bin/env python3
"""caryl_raw/job/en_chapters/*.md → caryl/job/*.md（英文版）

    python3 scripts/extract_caryl.py --apply && python3 scripts/publish_caryl_job_en.py --apply

约瑟·卡里尔《约伯记释义》。一段（≈一讲或连续几讲）一页 `<章>-<首节>`，每章一页目录 `<章>.md`；
各部卷首（书名页、出版许可、致读者、勘误；第 1 部另有全书引论）`p<部>-<类>`，排在该部各段之前。
共用骨架 tcp_publish.Book，这里改三处：页序按部交错、锚点已在段内的不重挂、书首页按 12 部列章格子。
EEBO-TCP 只录了 8 部；另 4 部（11–14、18–21、27–29、30–31 章）据扫描影像 OCR（caryl_raw/job_ocr/，见 caryl_ocr*.py），
段落取 job_ocr/p<部>/fixed/（两层纠错后），每段页首注明来源；还没出 fixed/ 的部，各章出占位页。
date 沿用 en_meta.json 原值，新页才写当前真实时间。
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcp_publish  # noqa: E402
from extract_caryl import NV as NV_ALL, PARTS  # noqa: E402


OCR_DIR = Path(__file__).resolve().parent.parent / 'caryl_raw' / 'job_ocr'
# OCR 各部：底本、对照本、扉页所见（年份读不清的不写）
OCR_INFO = {
    4: dict(base='J. I. Packer 藏本（IA 扫描，600 ppi）', edition='London: for Thomas Sawbridge, 1670',
            witness='1670 年同一印次的 EEBO 缩微胶片', year='1670'),
    6: dict(base='J. I. Packer 藏本（IA 扫描，600 ppi）', edition='London: M. Simmons, sold by Joseph Cranford',
            witness='1653 年印本的 EEBO 缩微胶片', year=''),
    8: dict(base='1670 年印本的 EEBO 缩微胶片与 J. I. Packer 藏本（300 ppi），逐页取读得好的一份', edition='London, 1670',
            witness='两份互为对照', year='1670'),
    9: dict(base='J. I. Packer 藏本（IA 扫描，300 ppi）', edition='London: M. Simmons for Elisha Wallis',
            witness='1676–77 年对开合订本第二卷的 EEBO 缩微胶片', year=''),
}


# 已上线的 OCR 部（2026-11-25 用户定：先上 4、6、9，第 8 部段首切分与底本质量修好再上）
OCR_READY = (4, 6, 9)


class tc:
    ROOT = Path(__file__).resolve().parent.parent
    RAW = ROOT / 'caryl_raw' / 'job'
    TOK = re.compile(r'•+|〈◊〉|〈…〉|〈Greek〉|▪')
    OCR_SRC = {}

    @classmethod
    def order(cls):
        o = json.loads((cls.RAW / 'order.json').read_text(encoding='utf-8'))
        for part in OCR_READY:
            f = OCR_DIR / f'p{part}' / 'order.json'
            if not f.exists() or not (OCR_DIR / f'p{part}' / 'fixed').is_dir():
                continue
            secs = [dict(x, src='ocr') for x in json.loads(f.read_text(encoding='utf-8'))['sections']]
            # 出处行只引头几节的段延到下一段之前、章末段延到章末（同 extract_caryl.py）
            secs.sort(key=lambda x: (x['ch'], x['v1']))
            for i, x in enumerate(secs):
                nx = secs[i + 1] if i + 1 < len(secs) and secs[i + 1]['ch'] == x['ch'] else None
                x['v2'] = max(x['v2'], (nx['v1'] - 1) if nx else NV_ALL[x['ch']])
                if nx and x['v2'] >= nx['v1']:
                    x['v2'] = nx['v1'] - 1
                cls.OCR_SRC[x['slug']] = OCR_DIR / f'p{part}' / 'fixed' / f'{x["slug"]}.md'
            o['sections'] += secs
        return o

    @classmethod
    def load(cls, slug):
        if slug in cls.OCR_SRC:
            md = cls.OCR_SRC[slug].read_text(encoding='utf-8').strip()
            md = md.replace('|', '')         # OCR 噪点竖线会被 kramdown 当表格（old-book-ocr §4.4：删，不转义）
            return ('<p class="cy-ocrnote">This section is machine-read (OCR) from page images and corrected against a '
                    'second copy; it has not been proofread word by word. Doubtful words are underlined. '
                    '本段据扫描影像机器识别，经另一印本校勘，未逐字人工校对；存疑处加虚下划线。</p>\n\n' + md)
        return (cls.RAW / 'en_chapters' / f'{slug}.md').read_text(encoding='utf-8').strip()


ORD = tc.order()
NV = {s['ch']: NV_ALL[s['ch']] for s in ORD['sections']}
ORD_PART = {s['slug']: s['part'] for s in ORD['sections']}
FRONT_RANK = {'title': 0, 'license': 1, 'reader': 2, 'intro': 3, 'errata': 4}
# 各部扉页所印讲数（XXI lectures / thirty two lectures …）
LECTURES = {1: 21, 2: 35, 3: 32, 5: 23, 7: 37, 10: 49, 11: 35, 12: 52}
CN = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']


def ocr_en(parts):
    if not parts:
        return ''
    names = ', '.join(f'Part {p} (chapters {a}–{b})' for p, _, (a, b), _ in PARTS if p in parts)
    return (f'{names} {"was" if len(parts) == 1 else "were"} never transcribed by EEBO-TCP; their text here is machine-read (OCR, kraken with the CATMuS-Print '
            'model) from page images of the printed parts, then corrected word by word against a second copy wherever the two '
            'could be aligned. It has not been proofread by eye: words neither copy could settle are underlined with dots, and '
            'some misreadings that happen to form real words remain. Italics are not reproduced in these parts. ')


def ocr_zh(parts):
    if not parts:
        return ''
    names = '、'.join(f'第{CN[p]}部（{a}–{b} 章）' for p, _, (a, b), _ in PARTS if p in parts)
    srcs = '；'.join(f'第{CN[p]}部底本为{OCR_INFO[p]["base"]}，对照本为{OCR_INFO[p]["witness"]}' for p in parts)
    return (f'{names}EEBO-TCP 未录入，本站据原书扫描影像机器识别（kraken 引擎、CATMuS-Print 模型），再逐词与另一印本对照校勘'
            f'（{srcs}）。这几部未经逐字人工校对：两份都判不了的词加虚下划线，碰巧读成别的真词的错字仍可能留存；斜体未能还原。')


def chs_label(a, b):
    return f'{a}–{b}'


class Caryl(tcp_publish.Book):
    def build_pages(self):
        fronts = sorted(ORD['front'], key=lambda f: (f['part'], FRONT_RANK[f['slug'].split('-', 1)[1]]))
        pages = []
        for part, tcp, chs, year in PARTS:
            for f in fronts:
                if f['part'] == part:
                    pages.append(dict(slug=f['slug'], title=f'{f["title"]} (Part {part})', short=f'Part {part}: {f["title"]}',
                                      subtitle=f'第{CN[part]}部 · {f["cn"]}', body=self.load_page(f['slug']),
                                      group='front', part=part, label=f['title'], cn=f['cn']))
            for x in ORD['sections']:
                if x['part'] != part:
                    continue
                r = self.rng(x['ch'], x['v1'], x['v2'])
                short = f'{x["ch"]}:{x["v1"]}' + ('' if x['v1'] == x['v2'] else f'–{x["v2"]}')
                pages.append(dict(slug=x['slug'], title=r, short=short, rng=r, subtitle=self.author,
                                  body=self.load_page(x['slug']), group='section', ch=x['ch'], v1=x['v1'], v2=x['v2']))
        return pages

    def add_anchors(self, body, pg):
        """段内小经文框处已挂的节不重挂；其余（段首几节、段内没单列的节）挂在段首经文框后。"""
        if 'ch' not in pg:
            return body
        ch = pg['ch']
        prior = self.__dict__.setdefault('_anchored', set())     # 前面各段已挂过的 (章, 节)
        # 两段都标的节（1:5、1:11、2:5–6 …）只在前一段挂锚点，id 不重复
        seen = set()

        def keep(m):                         # 前面各段已挂过的、本页已出现过的（OCR 段同一节的逐节标题读出两次）都去掉
            v = int(m.group(1))
            if (ch, v) in prior or v in seen:
                return ''
            seen.add(v)
            return m.group(0)
        body = re.sub(rf'<div class="commentary-anchor" id="{self.book}-{ch}-(\d+)"></div>\n*', keep, body)
        # OCR 段的逐节锚点节号是读出来的，可能读错：超出本章节数的去掉
        body = re.sub(rf'<div class="commentary-anchor" id="{self.book}-{ch}-(\d+)"></div>\n*',
                      lambda m: m.group(0) if 1 <= int(m.group(1)) <= NV_ALL[ch] else '', body)
        have = {int(v) for v in re.findall(rf'id="{self.book}-{ch}-(\d+)"', body)}
        vs = [v for v in range(pg['v1'], pg['v2'] + 1) if v not in have and (ch, v) not in prior]
        prior |= {(ch, v) for v in have | set(vs)}
        anc = ''.join(f'\n\n<div class="commentary-anchor" id="{self.book}-{pg["ch"]}-{v}"></div>' for v in vs)
        m = re.search(rf'<div class="{self.P}-text" markdown="1">.*?\n\n</div>', body, re.S)
        if m and m.start() < 3000:
            return body[:m.end()] + anc + body[m.end():]
        return anc.lstrip('\n') + '\n\n' + body

    def stats(self):
        return 0, 0, 0

    def build_index(self, pages):
        P = self.P
        out = ['---', 'layout: caryl-job-book', f'book_id: {self.book}', f'book_name: "{self.name}"',
               f'title: "{self.name}"', f'author: "{self.author} ({self.years})"', f'edition: "{self.edition}"',
               '---', '']
        u = '{{ site.baseurl }}'
        out.append(f'<h2 class="{P}-group">Chapters</h2>')
        cells = []
        for part, tcp, (a, b), year in PARTS:
            for c in range(a, b + 1):
                if tcp:
                    cells.append(f'<li><a href="{u}/{self.slug}/{self.book}/{c}/">Chapter {c}<small>Part {part} · {year}</small></a></li>')
                elif c in self.NV:
                    y = OCR_INFO[part]['year']
                    cells.append(f'<li><a class="{P}-ocrcell" href="{u}/{self.slug}/{self.book}/{c}/" '
                                 f'title="据扫描影像 OCR，未逐字人工校对">Chapter {c}<small>Part {part} · OCR'
                                 + (f' · {y}' if y else '') + '</small></a></li>')
                else:
                    cells.append(f'<li><span class="{P}-none" title="EEBO-TCP 未录此部，待据原书影像补录">Chapter {c}'
                                 f'<small>Part {part} · 待补录</small></span></li>')
        out.append(f'<ul class="{P}-chgrid">' + ''.join(cells) + '</ul>')
        out.append(f'<h2 class="{P}-group">Prefatory Matter of Each Part</h2>')
        for part, tcp, (a, b), year in PARTS:
            if not tcp:
                continue
            fs = [p for p in pages if p['group'] == 'front' and p['part'] == part]
            out.append(f'<p class="{P}-part">Part {part} · Job {chs_label(a, b)}<small>{year} · EEBO-TCP {tcp}</small></p>')
            out.append(f'<ul class="{P}-toc {P}-partlist">' + ''.join(
                f'<li><a href="{u}/{self.slug}/{self.book}/{p["slug"]}/">{p["label"]}<small>{p["cn"]}</small></a></li>'
                for p in fs) + '</ul>')
        g = ORD['gaps']
        nlec = sum(LECTURES[p] for p, t, _, _ in PARTS if t)
        have = [p for p in PARTS if p[1]]
        ocr_parts = sorted({x['part'] for x in ORD['sections'] if x.get('src') == 'ocr'})
        lack = [p for p in PARTS if not p[1] and p[0] not in ocr_parts]
        lack_en = ', '.join(f'Part {p} (chapters {a}–{b})' for p, _, (a, b), _ in lack)
        lack_zh = '、'.join(f'第{CN[p]}部（{a}–{b} 章）' for p, _, (a, b), _ in lack)
        tcps = ', '.join(t for _, t, _, _ in have)
        out.append(f'<div class="{P}-note">')
        out.append(f'''<p><b>About this text.</b> Caryl expounded Job in a long course of lectures at St Magnus the Martyr, near London
Bridge, and published them in twelve quarto parts as the course went on, from 1643 to 1666 (collected in two folio volumes
in 1676–77). The eight parts given here contain {nlec} lectures by the count on their title pages. The text here is the keyed transcription of {len(have)} of those parts made by the Text
Creation Partnership (EEBO-TCP {tcps}; released under CC0), each from the edition named on its title page; part 2 is the
reissue of 1656. Spelling is that of the original; only the long s is printed as s. Each page is one section of the
exposition as Caryl divided it, headed by the verses he quotes; the page numbers of the printed part are shown in the text.
Places the transcribers could not read are shown in red ({g.get("letter", 0):,} letters, {g.get("word", 0)} words,
{g.get("span", 0)} longer passages, and {g.get("foreign", 0):,} Greek or Hebrew words left untranscribed).
{ocr_en(ocr_parts)}{(lack_en + (' was' if len(lack) == 1 else ' were') + ' never transcribed by EEBO-TCP and will be added from page images. ') if lack else ''}The subject and Scripture indexes at the
end of each part are not included.</p>''')
        out.append(f'''<p class="{P}-note-zh"><b>文本说明。</b>卡里尔在伦敦桥边圣马格努斯堂逐节讲约伯记，边讲边分 12 部（四开本）出版，
1643 年出第一部，1666 年出完；1676–77 年合为对开两卷。本站所收 8 部，按各部扉页所记共 {nlec} 讲。本站正文据 EEBO-TCP 人工录入本（{tcps}，CC0 公共领域授权），
共 {len(have)} 部，各据扉页所印之版；第二部是 1656 年再版。拼法照录原书，只把长 s（ſ）印作 s。一页是卡里尔所分的一段，段首是他所引经文，
正文中标出原书页码。录入者读不出的地方以红色标出：缺字母 {g.get("letter", 0):,} 个、缺整词 {g.get("word", 0)} 处、缺一段以上 {g.get("span", 0)} 处，
另有希腊文、希伯来文 {g.get("foreign", 0):,} 处未录。{ocr_zh(ocr_parts)}{(lack_zh + 'EEBO-TCP 未录入，待据原书影像补录。') if lack else ''}各部卷末的主题索引与经文索引未收。</p>''')
        out.append('</div>')
        return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    b = Caryl(tc=tc, NV=NV, slug='caryl', book='job', P='cy', layout='caryl-job-chapter',
              author='Joseph Caryl', years='1602–1673', name='An Exposition upon the Book of Job', ref='Job',
              edition='An Exposition with Practical Observations upon the Book of Job · London, 1643–1666 · '
                      'Parts 1–3, 5, 7, 10–12 (EEBO-TCP); Parts 4, 6, 9 (OCR)',
              front=[], back=[])
    b.publish(a.apply)
    if a.apply:
        placeholders(b)


def placeholders(b):
    """EEBO-TCP 未录的 4 部：每章出一页占位说明。对比抽屉按章号区间 1–42 列本书，没有这页就点进 404。"""
    meta = json.loads(b.META.read_text(encoding='utf-8'))
    m = meta.setdefault(b.book, {})
    stamp = b.now()
    for part, tcp, (lo, hi), _ in PARTS:
        if tcp:
            continue
        for ch in range(lo, hi + 1):
            if ch in b.NV:              # 已有 OCR 内容的章，章目录页由 publish 写好了，不覆盖
                continue
            slug = str(ch)
            m.setdefault(slug, stamp)
            fm = ['---', f'layout: {b.layout}', f'book_id: {b.book}', f'book_name: "{b.name}"', f'title: "Job {ch}"',
                  f'subtitle: "{b.author}"', f'date: {m[slug]}', f'chapter: {ch}', 'verse_from: 1', f'verse_to: {NV_ALL[ch]}',
                  'placeholder: true', '---']
            body = (f'<p class="cy-pending">Caryl\'s exposition of Job {lo}–{hi} is Part {part} of the work. '
                    'It was not transcribed by EEBO-TCP and will be added here from the page images of the original.</p>\n\n'
                    f'<p class="cy-pending">本章属原书第{CN[part]}部（{lo}–{hi} 章）。EEBO-TCP 未录入此部，待据原书影像补录。'
                    f'<a href="{{{{ site.baseurl }}}}/{b.slug}/{b.book}/">返回书首页</a></p>\n')
            (b.OUT / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + body, encoding='utf-8')
    b.META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
