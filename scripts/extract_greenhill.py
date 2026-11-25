#!/usr/bin/env python3
"""greenhill_raw/ezekiel/src/*.xml（EEBO-TCP 五卷）→ en_chapters/*.md + order.json + gap_sites.json

    python3 scripts/extract_greenhill.py            # 试跑，只报统计
    python3 scripts/extract_greenhill.py --apply

威廉·格林希尔《以西结书释义》，原是伦敦「讲解讲座」（Expository Lectures）上逐节所讲，分五卷出版：

| TCP | 章 | 出版 |
|---|---|---|
| A85666 | 1–5 | 1645，Matthew Simmons 印、Benjamin Allen 售（Wing G1851） |
| A85667 | 6–13 | 1649，M.S. 印、Hanna Allen 售 |
| A42015 | 14–19 | 1651，M.S. 印、Livewell Chapman 售（Wing G1855） |
| A85668 | 20–29 | 1658，Livewell Chapman 售 |
| A42016 | 30–48 | 1662，Tho. Parkhurst 售 |

底本是 TCP 人工录入的 TEI，**不是 OCR**；CC0。缺字原样留记号，交给 greenhill_common.py 按判读表回填。

分页：章下再切，一页一段经文，页名 `<章>-<首节>`。
- 一、二、三、五卷：录入本章下有 <div type="verse|verses" n="…">，以它为单元。n 有重叠（`1-3` 后接 `2`、`3`：
  先引一段经文，再逐节细讲）和空值；首节不大于上一单元首节的并进上一单元。
- 第四卷（20–29 章）录入本章下没有 verse 层，正文是 <q>经文</q> 与 <p>讲解</p> 相间：<q> 以节号起头
  （`Verſ. 5 …`／`1 And it came…`）且节号大于本章已讲到的最大节，就开新单元。
- 单元太碎（第四卷几乎逐节讲，每节千把词），相邻单元合并到每页至少 MIN_WORDS 词；章末不足 MIN_WORDS/3 的并进前页。
- 每页节段：首节 = 首单元首节（每章第一页从 1 起），末节 = 下一页首节 − 1，章末页到章末。

卷首：各卷书名页、献辞／致读者书；第一卷另有「致真理的爱慕者」与「全书引言」，
第一章正文前的总论（书名、年代、宗旨、全书分段）单出一页 prolegomena。
勘误表、主题索引、经文索引、书商广告不收。
"""
import argparse
import collections
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import greenhill_common as gc  # noqa: E402
import tcp_tei as tt  # noqa: E402

RAW = gc.RAW
OUT = RAW / 'en_chapters'
TEI = tt.TEI
P = 'gh'
MIN_WORDS = 3000
VOLS = [('A85666', 1645, range(1, 6)), ('A85667', 1649, range(6, 14)), ('A42015', 1651, range(14, 20)),
        ('A85668', 1658, range(20, 30)), ('A42016', 1662, range(30, 49))]
# 以西结书各章节数（钦定本），共 1273 节
NV = dict(enumerate([28, 10, 27, 17, 17, 14, 27, 18, 11, 22, 25, 28, 23, 23, 8, 63, 24, 32, 14, 49, 32, 31, 49, 27,
                     17, 21, 36, 26, 21, 26, 18, 32, 33, 31, 15, 38, 28, 23, 29, 49, 26, 20, 27, 31, 25, 24, 23, 35], 1))
assert sum(NV.values()) == 1273
ROMAN = ['', 'I', 'II', 'III', 'IV', 'V']
# 卷首篇目：(TCP div type, 页名后缀, 标题)
FRONT_TYPES = {'title_page': ('title', 'Title Page'),
               'dedication': ('dedication', 'The Epistle Dedicatory'),
               'author_to_well-willers_of_truth': ('well-willers', 'To All Well-willers of Truth'),
               'introduction': ('introduction', 'The Introduction to the Work'),
               'author_to_the_reader': ('to-the-reader', 'To the Christian Reader')}
FRONT_SKIP = {'errata', 'publishers_advertisement'}
RE_VQ = re.compile(r'^\W*(?:Ver[ſs]?e?\.?\s*)?(\d{1,2})\b')


class GR(tt.R):
    nest_lists = True                                # 嵌套分条各起一行（old-book-ocr §3.3a）

    def note(self, c):
        if c.get('place') == 'mark':                 # 页边纲目标记（Note 1 / Obs. / Use …）
            t = tt.norm(self, self.inline(c))
            return f'<span class="{self.P}-mark">{t}</span>' if t else ''
        return super().note(c)

    def gap(self, e):
        if e.get('reason') == 'illegible' and (e.get('extent') or '') == '1 chunk':
            self.gaps['span'] = self.gaps.get('span', 0) + 1
            return ' ' + tt.GAP_SPAN + ' '
        return super().gap(e)


def prep(root):
    for g in root.iter(TEI + 'g'):
        if g.get('ref') == 'char:V':                 # Ʋ：大写 U 的旧字形
            g.text = 'U'
    for lab in root.iter(TEI + 'label'):
        if lab.get('type') == 'milestone':
            lab.tag = TEI + 'note'
            lab.attrib.clear()
            lab.set('place', 'mark')
    for el in root.iter():                          # 原书字面星号不当斜体
        for a in ('text', 'tail'):
            v = getattr(el, a)
            if v and '*' in v:
                setattr(el, a, v.replace('*', '&#42;'))


def epigraph_box(r, ep):
    """段首经文：<bibl> 出处一行，<q> 每段一行（<q><p>… 或 <q><bibl>节号</bibl>经文</q>）。"""
    lines = []
    for c in ep:
        k = tt.tag(c)
        if k == 'bibl':
            lines.append(f'<span class="{P}-ref">{r.text(c)}</span>')
        elif k == 'q':
            if any(tt.tag(x) == 'p' for x in c):
                loose = ET.Element(TEI + 'p')        # <p> 之间的散字与行内元素（<gap>、<hi>…）并成一行
                loose.text = c.text

                def flush():
                    nonlocal loose
                    t = r.text(loose)
                    if t:
                        lines.append(t)
                    loose = ET.Element(TEI + 'p')
                for x in c:
                    kx = tt.tag(x)
                    if kx in ('p', 'pb'):
                        flush()
                        lines.append(r.text(x) if kx == 'p' else r.pb(x))
                        loose.text = x.tail
                    elif kx == 'bibl':                   # 出处行录在 <q> 里面（VERS. 19, 20.），照样排成出处行
                        flush()
                        lines.append(f'<span class="{P}-ref">{r.text(x)}</span>')
                        loose.text = x.tail
                    else:
                        loose.append(x)
                flush()
            else:
                lines.append(r.text(c))
        elif k == 'pb':
            lines.append(r.pb(c))
        else:
            raise ValueError(f'epigraph 下未处理 <{k}>')
    out = []
    for x in lines:                                  # 页码锚点挂进下一行
        if not x:
            continue
        if out and out[-1].startswith(f'<span class="{P}-pb"') and out[-1].endswith('</span>'):
            out[-1] += x
        else:
            out.append(x)
    return '\n\n'.join(out)


RE_HVLIST = re.compile(r'^\W*VER[SſE]*\.?[\s\d.,&and-]*$', re.I)
RE_HVERS = re.compile(r'^\W*Ver[ſs]?[ei]?[.,]?\s*\d')


def head_md(r, e, depth, before_text=False):
    """标题版式照原书（old-book-ocr §3.3a）。录入本 <hi> 只标「与本行不同的字体」，本行底子是正是斜要推：
    无 <hi>，或 <hi> 之外还有两个以上词 → 底子斜体（所引经文），<hi> 部分转正体；否则底子正体（Observ. 1.）。
    段首经文前那一行（VERS. 60, 61.）居中大字；Vers. N 起头的引语行齐左悬挂；其余居中。"""
    txt = r.text(e)
    if not txt:
        return None
    his = [x for x in e.iter() if tt.tag(x) == 'hi']
    rest = tt.text_of(e)
    for h in his:
        rest = rest.replace(tt.text_of(h), ' ', 1)
    base_it = not his or len(re.findall(r'[A-Za-zſ]{2,}', rest)) >= 2
    plain = tt.text_of(e).replace('ſ', 's').strip()
    if before_text or RE_HVLIST.match(plain):          # 只有节号的一行（VERS. 60, 61, 62.）
        cls, base_it = 'gh-h-vers', False
    elif re.match(r'CHAP(?:TER)?\.? +[IVXLC\d]+\.?$', plain, re.I):   # 章标题原书正体大字（CHAP. XXXII.）
        cls, base_it = 'gh-h-c', False
    elif RE_HVERS.match(plain):
        cls = 'gh-h-lv'
    else:
        cls = 'gh-h-c'
    if base_it:
        parts = re.split(r'(<span class="gh-margin".*?</span>)', txt, flags=re.S)   # 旁注里的斜体不动
        txt = ''.join(x if x.startswith('<span class="gh-margin"') else
                      re.sub(r'(?<![\\*])\*([^*\n]+?)\*(?!\*)', r'<span class="gh-up">\1</span>', x) for x in parts)
        cls += ' gh-h-it'
    return '#' * depth + ' ' + txt + '\n{: .' + cls.replace(' ', ' .') + '}'


def render(r, e, paras, depth=3):
    """块级：在 tt.block 之上加 epigraph；div 递归（深一层标题多一个 #）。"""
    k = tt.tag(e)
    if k == 'epigraph':
        paras.append(('text', epigraph_box(r, e)))
    elif k == 'div':
        kids = list(e)
        for i, c in enumerate(kids):
            if tt.tag(c) == 'head':
                nxt = next((x for x in kids[i + 1:] if tt.tag(x) != 'pb'), None)
                h = head_md(r, c, depth, nxt is not None and tt.tag(nxt) == 'epigraph')
                if h:
                    paras.append(('head', h))
                continue
            render(r, c, paras, min(depth + 1, 5))
    elif k == 'head':
        h = head_md(r, e, depth)
        if h:
            paras.append(('head', h))
    else:
        tt.block(r, e, paras, depth)


def words(paras):
    n = 0
    for p in paras:
        v = p[-1]
        if isinstance(v, list):
            v = ' '.join(x if isinstance(x, str) else '' for x in v)
        n += len(re.sub(r'<[^>]+>|\n\{: [^}]*\}', ' ', v).split())       # 标题版式行不计词
    return n


def units_from_divs(r, cdiv, ch, lead):
    """一、二、三、五卷：每个 verse div 一个单元。返回 [(首节, 末节, paras)]。"""
    units = []
    for x in cdiv:
        if tt.tag(x) != 'div':
            if units:
                render(r, x, units[-1][2])
            else:
                render(r, x, lead, 2)
            continue
        n = x.get('n') or ''
        nums = [int(z) for z in re.findall(r'\d+', n)]
        paras = []
        for c in x:
            render(r, c, paras, 3)
        if not nums or (units and nums[0] <= units[-1][0]):
            if not units:
                raise ValueError(f'{ch}: 首单元 n 认不出 {n!r}')
            units[-1][2].extend(paras)
            units[-1][1] = max(units[-1][1], max(nums) if nums else 0)
            continue
        units.append([nums[0], max(nums), paras])
    return units


def units_from_quotes(r, cdiv, ch, lead):
    """第四卷：在以新节号起头的 <q> 处切。原书一段经文常连引数节（Vers. 25 … 26 … 27 …），
    中间无正文的连续节号引语同属一段，只在第一节处切，后面几节并进同一单元。"""
    units, maxv, run = [], 0, False
    for x in cdiv:
        k = tt.tag(x)
        if k == 'pb':
            pass
        elif k == 'q':
            m = RE_VQ.match(tt.text_of(x).replace('ſ', 's'))
            if m and maxv < int(m.group(1)) <= NV[ch]:
                v = int(m.group(1))
                if run and units:
                    units[-1][1] = v
                else:
                    units.append([v, v, []])
                maxv, run = v, True
            else:
                run = False
        else:
            run = False
        if not units:
            render(r, x, lead, 2 if k == 'head' else 3)
        else:
            render(r, x, units[-1][2])
    return units


def merge(units, ch):
    pages = []
    for u in units:
        if pages and words(pages[-1][2]) < MIN_WORDS:
            pages[-1][1] = max(pages[-1][1], u[1])
            pages[-1][2].extend(u[2])
        else:
            pages.append([u[0], u[1], list(u[2])])
    if len(pages) > 1 and words(pages[-1][2]) < MIN_WORDS // 3:
        last = pages.pop()
        pages[-1][2].extend(last[2])
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    files, order, sections, front_meta = {}, [], [], []
    gaps = collections.Counter()
    bad = 0

    def put(slug, paras):
        if slug in files:
            raise ValueError(f'重复页名 {slug}')
        files[slug] = tt.to_md(P, paras)
        order.append(slug)

    vol_rs = []
    for vi, (tcp, year, chs) in enumerate(VOLS, 1):
        root = ET.parse(RAW / 'src' / f'{tcp}.xml').getroot()
        prep(root)
        text = root.find(f'.//{TEI}text')
        r = GR(P, str(year))
        vol_rs.append(r)
        for div in text.find(TEI + 'front'):
            if tt.tag(div) != 'div':
                continue
            ty = div.get('type')
            if ty in FRONT_SKIP:
                continue
            suf, title = FRONT_TYPES[ty]
            paras = []
            for c in div:
                render(r, c, paras, 3)
            slug = f'vol{vi}-{suf}'
            put(slug, paras)
            front_meta.append(dict(slug=slug, title=f'Vol. {ROMAN[vi]} · {title}', vol=vi, year=year, tcp=tcp))

        body = text.find(TEI + 'body')
        top = [d for d in body if tt.tag(d) == 'div']
        if len(top) != 1:
            raise ValueError(f'{tcp}: body 下 div 数 {len(top)}')
        lead = []                                    # 卷首总题（An Exposition upon more Chapters…）与页码，并进本卷第一段
        cdivs, tail = [], []
        for c in top[0]:
            if tt.tag(c) == 'div':
                cdivs.append(c)
            elif not cdivs and tt.tag(c) in ('head', 'pb'):
                render(r, c, lead, 2)
            elif tt.tag(c) in ('trailer', 'closer'):   # 卷末 FINIS／颂词：等各章出完，挂到本卷正文最后一页
                tail.append(c)
            else:
                raise ValueError(f'{tcp}: 章与章之间多出 <{tt.tag(c)}>')
        if [int(c.get('n')) for c in cdivs] != list(chs):
            raise ValueError(f'{tcp}: 章号 {[c.get("n") for c in cdivs]}')
        for cdiv in cdivs:
            ch = int(cdiv.get('n'))
            if ch == 1:                              # 总论：第一章正文前、第一个 verse div 之前的全部
                pro = lead
                lead = []
                kids = list(cdiv)
                k0 = next(i for i, x in enumerate(kids) if tt.tag(x) == 'div')
                for x in kids[:k0]:
                    render(r, x, pro, 2 if tt.tag(x) == 'head' else 3)
                for x in kids[:k0]:
                    cdiv.remove(x)
                put('prolegomena', pro)
                front_meta.append(dict(slug='prolegomena', title='The Antiquity, Scope and Parts of this Prophecy',
                                       vol=1, year=year, tcp=tcp))
            units = (units_from_quotes if tcp == 'A85668' else units_from_divs)(r, cdiv, ch, lead)
            if not units:
                raise ValueError(f'{ch}: 没有单元')
            units[0][2][:0] = lead
            lead = []
            pages = merge(units, ch)
            pages[0][0] = 1
            for i, (v1, v2, paras) in enumerate(pages):
                end = pages[i + 1][0] - 1 if i + 1 < len(pages) else NV[ch]
                if end < v1 or v2 > NV[ch]:
                    print(f'⚠️ {ch}:{v1}–{end}（单元末节 {v2}）越界', file=sys.stderr)
                    bad += 1
                slug = f'{ch}-{v1}'
                put(slug, paras)
                sections.append(dict(slug=slug, ch=ch, v1=v1, v2=end, words=words(paras), vol=vi))
        tail += [c for c in body if tt.tag(c) in ('trailer', 'closer')]      # body 层（总 div 之外）的 FINIS
        for c in tail:
            files[order[-1]] += '\n\n' + tt.to_md(P, [('cls', f'{P}-closer', r.text(c))])
        gaps.update(r.gaps)

    bad += tt.check(files)
    ws = [s['words'] for s in sections]
    print(f'页 {len(files)}（经文段 {len(sections)}，卷首 {len(front_meta)}）  缺字 {dict(gaps)}', file=sys.stderr)
    print(f'每段词数：最少 {min(ws)}  中位 {sorted(ws)[len(ws) // 2]}  最多 {max(ws)}', file=sys.stderr)
    big = sorted(sections, key=lambda s: -s['words'])[:5]
    print('最长：' + '，'.join(f'{s["slug"]} {s["words"]}' for s in big), file=sys.stderr)
    per = collections.Counter(s['ch'] for s in sections)
    print('每章页数：' + ' '.join(f'{c}:{per[c]}' for c in sorted(per)), file=sys.stderr)
    if a.apply:
        OUT.mkdir(parents=True, exist_ok=True)
        for f in OUT.glob('*.md'):
            f.unlink()
        for k, md in files.items():
            (OUT / f'{k}.md').write_text(md.strip() + '\n', encoding='utf-8')
        (RAW / 'order.json').write_text(json.dumps({'order': order, 'sections': sections, 'front': front_meta},
                                                   indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
        write_gap_sites(order)
        print(f'写入 {len(files)} 篇 → {OUT}', file=sys.stderr)
    return 1 if bad else 0


def write_gap_sites(order, nctx=8):
    """缺字组清单（照 petter_witness.py gaps）：gid / slug / 原串 / 前后文 / 原书页码。"""
    od = {x['slug']: x['vol'] for x in json.loads((RAW / 'order.json').read_text())['sections']}
    od |= {x['slug']: x['vol'] for x in json.loads((RAW / 'order.json').read_text())['front']}
    sites, prev_tail, pnum, facs, main_total, po_base = [], [], None, None, 0, 0
    for slug in order:
        md = gc.read_src(slug)
        margins = [(m.start(), m.end()) for m in re.finditer(r'<span class="gh-margin"[^>]*>.*?</span>', md, re.S)]
        blank = md
        for a, b in margins:
            blank = blank[:a] + ' ' * (b - a) + blank[b:]
        pns = [(m.start(), m.group(1)) for m in re.finditer(r'<span class="gh-pb"[^>]*data-p="([^"]+)"', md)]
        fcs = [(m.start(), int(m.group(1))) for m in re.finditer(r'<span class="gh-pb"[^>]*data-facs="(\d+)"', md)]
        if slug.endswith('-title') or slug == f'vol{od[slug]}-title':
            pnum, facs, po_base = None, None, 0      # 新一卷：页码、帧号、页序从头算
        for a, b, s, isnote in gc.gap_groups(md):
            pn = next((x for p, x in reversed(pns) if p < a), pnum)
            fc = next((x for p, x in reversed(fcs) if p < a), facs)
            po = po_base + sum(1 for p, _ in pns if p < a)   # 本卷第几个带页码的页：原书有两次分页、页码重号时也单调
            if isnote:
                na, nb = next((x, y) for x, y in margins if x <= a < y)
                left, right = gc.flat_words(md[na:a]), gc.flat_words(md[b:nb])
            else:
                left, right = prev_tail + gc.flat_words(blank[:a]), gc.flat_words(blank[b:])
            sites.append({'gid': len(sites), 'slug': slug, 'stream': 'note' if isnote else 'main', 'tcp': s,
                          'left': left[-nctx:], 'right': right[:nctx], 'page': pn, 'po': po, 'facs': fc, 'vol': od[slug],
                          'i': main_total + len(gc.flat_words(blank[:a])),
                          **({'mleft': (prev_tail + gc.flat_words(blank[:na]))[-nctx:],
                              'mright': gc.flat_words(blank[nb:])[:nctx]} if isnote else {})})
        if pns:
            pnum = pns[-1][1]
        po_base += len(pns)
        if fcs:
            facs = fcs[-1][1]
        prev_tail = gc.flat_words(blank)[-nctx:]
        main_total += len(gc.flat_words(blank))
    (RAW / 'gap_sites.json').write_text(json.dumps(sites, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'缺字组 {len(sites)}', file=sys.stderr)


if __name__ == '__main__':
    sys.exit(main())
