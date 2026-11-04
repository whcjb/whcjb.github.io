#!/usr/bin/env python3
"""petter_raw/mark/src/A54583.xml（EEBO-TCP）→ en_chapters/*.md

    python3 scripts/extract_petter.py            # 试跑，只报统计
    python3 scripts/extract_petter.py --apply

乔治·佩特《马可福音注释》London: J. Streater for George Sawbridge 1661（Wing P1888，作者身后由其弟约翰·佩特出版）。
底本是 TCP 人工录入的 TEI，**不是 OCR**。缺字原样留记号，交给 petter_common.py 按判读表回填。

录入本残缺：所据大英图书馆藏本只到原书 p.884（第十一章末），**第 12–16 章整个没有**（TCP 题注
「Imperfect; lacks all after p.884」）。

录入本结构：<div type="chapter"> = 章，章下每个 <div type="verse|verses" n="…"> 是一讲（原是逐主日讲道，
1618 年 6 月起），先 <epigraph>（<bibl>Mark 1. 4.</bibl> + <q>本讲经文</q>，经文里夹一条页边旁注＝讲道日期），
其后讲解。同一节常连讲几讲，n 相同。发布一讲一页，页名 `<章>-<首节>`，同一首节的第二、三讲加 b、c……
节段取 n：`7-8` → 7–8；`36, &c.` → 36 到下一讲首节 − 1。
讲解里页边的纲目标记（Obser. 1 / Use 2 / Quest. / Answ. …，录入本 <label type="milestone">）→ `<span class="pt-mark">`。
卷首：书名页、约翰·佩特序（1661）、按字母排的主题索引（索引里的页码是原书页码，过 884 的部分录入本没有）。
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcp_tei as tt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'petter_raw' / 'mark'
SRC = RAW / 'src' / 'A54583.xml'
OUT = RAW / 'en_chapters'
TEI = tt.TEI
P = 'pt'
# 马可福音各章节数（钦定本）；录入本只有 1–11 章
NV_ALL = dict(enumerate([45, 28, 35, 41, 43, 56, 37, 38, 50, 52, 33, 44, 37, 72, 47, 20], 1))
NV = {c: NV_ALL[c] for c in range(1, 12)}
FRONT = ['title', 'preface', 'alphabetical-table']
# 讲题节号印错／录错（经文对钦定本可证）：只改页名与节段，正文照录。
# (章, n 原值) → (首节, 末节)
N_FIX = {
    (7, '33-24'): (33, 34),          # 题作「Mark 7. 33, 24.」，经文是 33–34 节
    (9, '43-44'): (43, 49),          # 题作「Mark 9. 43, 44, unto ver. 49.」
}


class PR(tt.R):
    """页边纲目标记：抽取前把 <label type="milestone"> 改成 <note place="mark">，这里渲染成 pt-mark。"""
    def note(self, c):
        if c.get('place') == 'mark':
            t = tt.norm(self, self.inline(c))
            return f'<span class="{self.P}-mark">{t}</span>' if t else ''
        return super().note(c)

    def gap(self, e):
        """录入本另有「1+ letters」「1+ pages」两种不定量的缺：前者记作 〈…〉（几个字母读不出，紧贴原词），
        后者照 span 记。"""
        ext = e.get('extent', '') or ''
        if e.get('reason') == 'illegible' and ext == '1+ letters':
            self.gaps['span'] = self.gaps.get('span', 0) + 1
            return tt.GAP_SPAN
        if e.get('reason') == 'illegible' and ext == '1+ pages':
            self.gaps['span'] = self.gaps.get('span', 0) + 1
            return ' ' + tt.GAP_SPAN + ' '
        return super().gap(e)


def marks_to_notes(root):
    for lab in root.iter(TEI + 'label'):
        if lab.get('type') == 'milestone':
            lab.tag = TEI + 'note'
            lab.attrib.clear()
            lab.set('place', 'mark')


def epigraph_box(r, ep):
    """本讲经文：`*Mark 1. 4.*` 一行在前，经文一行在后；经文里夹的讲道日期旁注照留（发布时浮在框右）。"""
    head, lines = '', []
    for c in ep:
        k = tt.tag(c)
        if k == 'bibl':
            head = r.text(c)
        elif k == 'q':
            lines.append(r.text(c))
        elif k == 'pb':
            lines.append(r.pb(c))
        elif k == 'hi':                      # 「bibl, hi, q」：题下多出的一行斜体（「Verse 7.」之类）
            lines.append(f'*{r.text(c)}*')
        else:
            raise ValueError(f'epigraph 下未处理 <{k}>')
    if (ep.text or '').strip():
        raise ValueError('epigraph 带散字')
    out = [f'<span class="{P}-ref">{head}</span>'] if head else []
    for x in lines:                          # 页码锚点挂进下一行
        if out and out[-1].startswith(f'<span class="{P}-pb"') and out[-1].endswith('</span>'):
            out[-1] += x
        else:
            out.append(x)
    return '\n\n'.join(out)


def table_paras(r, div):
    """卷首字母索引：<list><head>A.</head><item><label>词条</label><list><item>子条, 页码</item>…</list></item>…"""
    paras = []
    for c in div:
        k = tt.tag(c)
        if k == 'head':
            paras.append(('head', '### ' + r.text(c)))
        elif k == 'pb':
            x = r.pb(c)
            if x:
                paras.append(('pb', x))
        elif k == 'list':
            for it in c:
                kk = tt.tag(it)
                if kk == 'head':
                    paras.append(('head', '#### ' + r.text(it)))
                elif kk == 'pb':
                    x = r.pb(it)
                    if x:
                        paras.append(('pb', x))
                elif kk == 'item':
                    lab = it.find(TEI + 'label')
                    sub = it.find(TEI + 'list')
                    if lab is None and sub is None:
                        paras.append(('cls', f'{P}-ixsub', r.text(it)))
                        continue
                    # 录入本索引格式不齐：词条有的写在 label 里、有的是 item 开头的散字；
                    # 无子条的词条，页码跟在 label 后。散字一律接到上一条后面，不丢字。

                    def loose(s):
                        s = tt.norm(r, (s or '').replace('ſ', 's'))
                        if not s:
                            return
                        if paras and paras[-1][0] == 'cls' and paras[-1][1].startswith(f'{P}-ix'):
                            paras[-1] = (paras[-1][0], paras[-1][1], paras[-1][2] + ' ' + s)
                        else:
                            paras.append(('cls', f'{P}-ixterm', s))
                    if (it.text or '').strip():
                        paras.append(('cls', f'{P}-ixterm', tt.norm(r, it.text.replace('ſ', 's'))))
                    for y in it:
                        ky = tt.tag(y)
                        if ky == 'label':
                            paras.append(('cls', f'{P}-ixterm', r.text(y)))
                        elif ky == 'pb':
                            x = r.pb(y)
                            if x:
                                paras.append(('pb', x))
                        elif ky == 'list':
                            for z in y:
                                ks = tt.tag(z)
                                if ks == 'item':
                                    paras.append(('cls', f'{P}-ixsub', r.text(z)))
                                elif ks == 'pb':
                                    x = r.pb(z)
                                    if x:
                                        paras.append(('pb', x))
                                else:
                                    raise ValueError(f'索引子条下 <{ks}>')
                                loose(z.tail)
                        elif ky == 'p':
                            paras.append(('cls', f'{P}-ixterm', r.text(y)))
                        elif ky in ('hi', 'g', 'gap'):   # 行内元素夹在词条散字里：包一层按行内渲染
                            w = ET.Element(TEI + 'p')
                            tail, y.tail = y.tail, None
                            w.append(y)
                            loose_raw = tt.norm(r, r.inline(w))
                            y.tail = tail
                            loose(loose_raw)
                        else:
                            raise ValueError(f'索引条下 <{ky}>')
                        loose(y.tail)
                else:
                    raise ValueError(f'索引 list 下 <{kk}>')
        else:
            tt.block(r, c, paras)
    return paras


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    root = ET.parse(SRC).getroot()
    marks_to_notes(root)
    text = root.find(TEI + 'text')
    r = PR(P, '1661')
    files, order, sections = {}, [], []

    def put(slug, paras):
        md = tt.to_md(P, paras)
        if slug in files:
            files[slug] += '\n\n' + md
        else:
            files[slug] = md
            order.append(slug)

    front = {}
    for div in text.find(TEI + 'front'):
        ty = div.get('type')
        paras = []
        if ty == 'index':
            paras = table_paras(r, div)
        else:
            tt.blocks(r, div, paras)
        front[{'title_page': 'title', 'preface': 'preface', 'index': 'alphabetical-table'}[ty]] = paras
    for slug in FRONT:
        put(slug, front[slug])

    body = text.find(TEI + 'body')
    top = [d for d in body if tt.tag(d) == 'div']
    if len(top) != 1:
        raise ValueError(f'body 下 div 数 {len(top)}')
    lead = []                                 # 书题（A COMMENTARY VPON …）与页码，并进第一讲
    chapters = []
    for c in top[0]:
        if tt.tag(c) == 'div':
            chapters.append(c)
        elif not chapters or tt.tag(c) == 'pb':
            tt.block(r, c, lead, 2)
        else:
            raise ValueError(f'章与章之间多出 <{tt.tag(c)}>')
    if len(chapters) != 11:
        raise ValueError(f'章数 {len(chapters)}')

    bad = 0
    for ch, cdiv in enumerate(chapters, 1):
        if cdiv.get('n') != str(ch):
            print(f'⚠️ 第 {ch} 个 chapter div 的 n={cdiv.get("n")}', file=sys.stderr)
            bad += 1
        seen = {}
        last_v1 = 0
        for x in cdiv:
            k = tt.tag(x)
            if k != 'div':
                if k == 'trailer':                    # 「Finis Primi Capitis.」挂到本章最后一讲末尾
                    files[order[-1]] += '\n\n' + tt.to_md(P, [('cls', f'{P}-closer', r.text(x))])
                else:                                  # 章题 CHAP. II. 与页码：并进本章第一讲
                    tt.block(r, x, lead, 2)
                continue
            n = x.get('n') or ''
            if (ch, n) in N_FIX:
                v1, v2 = N_FIX[(ch, n)]
            else:
                nums = [int(z) for z in re.findall(r'\d+', n)]
                if not nums:
                    raise ValueError(f'{ch}: 讲题 n 认不出 {n!r}')
                v1 = nums[0]
                v2 = nums[-1] if len(nums) > 1 else (None if '&c' in n else v1)
                if v2 is not None and v2 < v1:
                    raise ValueError(f'{ch}: n={n!r} 末节小于首节，需进 N_FIX')
            if v1 > NV[ch] or (v2 or v1) > NV[ch]:
                print(f'⚠️ {ch}:{n} 越界', file=sys.stderr)
                bad += 1
            if v1 < last_v1:
                print(f'  · {ch}: n={n!r} 首节比上一讲小（{last_v1}）', file=sys.stderr)
            last_v1 = v1
            seen[v1] = seen.get(v1, 0) + 1
            slug = f'{ch}-{v1}' + ('' if seen[v1] == 1 else 'abcdefghijklmnop'[seen[v1] - 1])
            paras = lead
            lead = []
            for y in x:
                ky = tt.tag(y)
                if ky == 'epigraph':
                    paras.append(('text', epigraph_box(r, y)))
                else:
                    tt.block(r, y, paras)
            put(slug, paras)
            sections.append(dict(slug=slug, ch=ch, v1=v1, v2=v2, n=n))
        if lead:
            raise ValueError(f'{ch}: 章末剩下未挂的块')

    # 「&c.」的末节：到同章下一讲中首节比它大的那一讲 − 1；本章没有就到章末
    for i, s in enumerate(sections):
        if s['v2'] is None:
            nxt = next((t['v1'] for t in sections[i + 1:] if t['ch'] == s['ch'] and t['v1'] > s['v1']), None)
            s['v2'] = nxt - 1 if nxt else NV[s['ch']]
    secs = [dict(slug=s['slug'], ch=s['ch'], v1=s['v1'], v2=s['v2'], n=s['n']) for s in sections]

    bad += tt.check(files)
    print(f'篇 {len(files)}（讲 {len(secs)}）  页码 {len(r.pages)}  缺字 {r.gaps}', file=sys.stderr)
    if a.apply:
        OUT.mkdir(parents=True, exist_ok=True)
        for k, md in files.items():
            (OUT / f'{k}.md').write_text(md.strip() + '\n', encoding='utf-8')
        (RAW / 'pages.json').write_text(json.dumps(r.pages) + '\n', encoding='utf-8')
        (RAW / 'order.json').write_text(json.dumps({'order': order, 'sections': secs}, indent=1) + '\n',
                                        encoding='utf-8')
        print(f'写入 {len(files)} 篇 → {OUT}', file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
