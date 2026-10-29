#!/usr/bin/env python3
"""attersoll_raw/philemon/src/A22481.xml（EEBO-TCP）→ en_chapters/*.md

    python3 scripts/extract_attersoll.py            # 试跑，只报统计
    python3 scripts/extract_attersoll.py --apply

威廉·阿特索尔《腓利门书注释》London: William Jaggard 1612（STC 890），印本页 1–495。
底本是 TCP 人工录入的 TEI，**不是 OCR**。骨架照搬 extract_taylor.py：只做结构映射，缺字原样留记号，
交给 attersoll_common.py 按判读表回填。

原书按经文分段讲（TCP 已分好 <div type="verse(s)" n="1-2">）：每段前排出经文（<epigraph>），段内
「The order of the words」→ 释义 → 教义（Doct.）、理由、应用。发布按段一页，页名 `1-<首节>`；
腓利门书只有一章，另出章目录 `1.md`（历代解经扫描器与对照抽屉按章号页找书）。

| TEI | 原书 | 产出 |
|---|---|---|
| <epigraph><q><p><bibl>N</bibl><hi>经文</hi> | 段前经文（一节一行） | `<div class="at-text">`，节号 `.at-vn` |
| <div type="preface"> | 序论（写作时地、本书缘起） | `preface` 页 |
| <hi> | 斜体 | `*…*`；嵌套 = 反转 |
| <note place="margin" type="runSum"> | 页边要点（Doct. 1. …） | `<span class="at-margin at-sum">` |
| <note n="a" place="margin"> | 页边出处，正文以字母 a b c 指引 | `<span class="at-margin" data-n="a">` |
| <q><l> | 诗句 | `<span class="at-l">` 一行一块 |
| <pb n="N"> | 印本页码 | `<span class="at-pb" id="pN">` |
| <seg rend="decorInit"> | 花饰首字 | `<span class="at-dropcap">` |
| <gap …> | 读不出的字母／词／一截／外文 | `•`×N / `〈◊〉` / `〈…〉` / `〈Greek〉` |
| <g ref="char:punc"> | 认不清的标点 | `▪` |
| <gap reason="duplicate"> | 缩微胶片重拍页 | 丢 |

长 ſ 归一成 s，录入本的 Ʋ（char:V，花体大写 V）作 V；u/v、i/j 等拼写照原样。
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'attersoll_raw' / 'philemon'
SRC = RAW / 'src' / 'A22481.xml'
OUT = RAW / 'en_chapters'
TEI = '{http://www.tei-c.org/ns/1.0}'

GAP_LETTER, GAP_WORD, GAP_SPAN, GAP_FOREIGN, PUNC = '•', '〈◊〉', '〈…〉', '〈Greek〉', '▪'
NV = {1: 25}

FRONT = {'title_page': 'title', 'dedication': 'dedication', 'to_the_reader': 'to-the-reader',
         'list_of_doctrines': 'doctrines'}
# 书末索引不叫 index：会和书首页 index.html 撞同一路径（feedback_slug_index_collision）
BACK = {'index': 'contents-table', 'errata': 'errata'}


def tag(e):
    return e.tag.replace(TEI, '')


class R:
    def __init__(self):
        self.pages = []
        self.gaps = {}
        self.held = []
        self.pb_seen = {}

    def gap(self, e):
        reason = e.get('reason', '')
        ext = e.get('extent', '') or ''
        if reason == 'duplicate':
            return ''
        if reason == 'foreign':
            self.gaps['foreign'] = self.gaps.get('foreign', 0) + 1
            return GAP_FOREIGN
        m = re.match(r'(\d+)\+? letters?', ext)
        if m:
            self.gaps['letter'] = self.gaps.get('letter', 0) + int(m.group(1))
            return GAP_LETTER * int(m.group(1))
        m = re.match(r'(\d+) words?', ext)
        if m:
            self.gaps['word'] = self.gaps.get('word', 0) + int(m.group(1))
            return ' ' + ' '.join([GAP_WORD] * int(m.group(1))) + ' '
        if re.match(r'\d+ (span|line|page|paragraph)s?', ext):
            self.gaps['span'] = self.gaps.get('span', 0) + 1
            return ' ' + GAP_SPAN + ' '
        raise ValueError(f'未知 gap: {e.attrib}')

    def inline(self, e, italic=False):
        on, off = ('\x01', '\x02')
        out = [e.text or '']
        for c in e:
            t = tag(c)
            if t == 'hi':
                inner = self.inline(c, not italic)
                out.append((on if not italic else off) + inner + (off if not italic else on))
            elif t == 'g':
                ref = c.get('ref')
                if ref in ('char:EOLhyphen', 'char:EOLunhyphen'):
                    while out and out[-1].strip() == '' and '\n' in out[-1]:
                        out.pop()
                    if out and out[-1].endswith(('\n', ' ', '\t')) and '\n' in out[-1]:
                        out[-1] = out[-1].rstrip()
                    out.append('\x04')       # 拼合点：吃掉后面的排版空白
                elif ref == 'char:punc':
                    out.append(PUNC)
                elif ref == 'char:V':
                    out.append('V')
                else:                        # cmbAbbrStroke 等：照录字形
                    out.append(c.text or '')
            elif t == 'gap':
                out.append(self.gap(c))
            elif t == 'pb':
                out.append(self.hold(self.pb(c)))
            elif t == 'note':
                out.append(' ' + self.hold(self.note(c)) + ' ')
            elif t == 'seg' and c.get('rend') == 'decorInit':
                out.append(self.hold('<span class="at-dropcap">' + norm(self, self.inline(c)) + '</span>'))
            elif t == 'q' and c.find(TEI + 'l') is not None:     # 诗句：一行一块
                for l in c:
                    if tag(l) != 'l':
                        raise ValueError(f'q/l 下未处理 <{tag(l)}>')
                    out.append(self.hold('<span class="at-l" markdown="1">' + norm(self, self.inline(l, italic))
                                         + '</span>'))
            elif t == 'label':
                out.append(self.inline(c, italic) + ' ')
            elif t in ('seg', 'q', 'p', 'signed', 'bibl', 'head', 'trailer', 'expan', 'am', 'ex', 'date',
                       'dateline', 'list', 'item', 'closer'):
                if t == 'item':
                    out.append(' ')
                out.append(self.inline(c, italic))
            elif t == 'lb':
                out.append(' ')
            elif t in ('desc', 'figure', 'milestone'):
                pass
            else:
                raise ValueError(f'行内未处理的元素 <{t}>')
            out.append(c.tail or '')
        return ''.join(out)

    def hold(self, html):
        if not html:
            return ''
        self.held.append(html)
        return f'\x03{len(self.held) - 1}\x03'

    def pb(self, c):
        facs = (c.get('facs') or '').split(':')[-1]
        n = c.get('n')
        if not n:      # 无页码的页（扉页、献辞、表）：只留图号，供证人定位
            return f'<span class="at-pb" data-facs="{facs}"></span>'
        self.pages.append((n, facs))
        k = self.pb_seen.get(n, 0) + 1
        self.pb_seen[n] = k
        pid = f'p{n}' + ('' if k == 1 else f'-{k}')
        return (f'<span class="at-pb" id="{pid}" data-p="{n}" data-facs="{facs}" '
                f'title="Page {n} of the 1612 edition begins here (原书第 {n} 页起)"></span>')

    def note(self, c):
        cls = 'at-margin at-sum' if c.get('type') == 'runSum' else 'at-margin'
        n = c.get('n')
        dn = f' data-n="{n}"' if n else ''
        return f'<span class="{cls}"{dn} markdown="1">{norm(self, self.inline(c))}</span>'


def norm(r, s):
    s = s.replace('ſ', 's')
    s = re.sub(r'\x04\s*', '', s)
    s = re.sub(r'\s+', ' ', s)
    runs, depth, buf = [], 0, []

    def flush():
        if buf:
            runs.append((depth > 0, ''.join(buf)))
            buf.clear()
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '\x01':
            flush(); depth += 1
        elif ch == '\x02':
            flush(); depth -= 1
        elif ch == '\x03':
            j = s.index('\x03', i + 1)
            flush()
            runs.append((None, r.held[int(s[i + 1:j])].replace('ſ', 's')))
            i = j
        else:
            buf.append(ch)
        i += 1
    flush()
    merged = []
    for it, tx in runs:
        if merged and merged[-1][0] == it and it is not None:
            merged[-1] = (it, merged[-1][1] + tx)
        else:
            merged.append((it, tx))
    out = []
    for it, tx in merged:
        if it is None or not it:
            out.append(tx)
            continue
        core = tx.strip()
        if not core:
            out.append(tx)
            continue
        lead = tx[:len(tx) - len(tx.lstrip())]
        trail = tx[len(tx.rstrip()):]
        out.append(f'{lead}*{core}*{trail}')
    return re.sub(r' {2,}', ' ', ''.join(out)).strip()


def block_text(r, e):
    return norm(r, r.inline(e))


def render_block(r, e, paras):
    """块级元素 → 段落元组（追加到 paras）。"""
    t = tag(e)
    if t == 'head':
        txt = block_text(r, e)
        if txt:
            paras.append(('head', txt))
    elif t == 'pb':
        x = r.pb(e)
        if x:
            paras.append(('pb', x))
    elif t == 'p':
        if e.find(TEI + 'list') is not None:
            paras.extend(split_list_p(r, e))
            return
        txt = block_text(r, e)
        if txt:
            paras.append(('p', txt))
    elif t == 'q':
        bib = e.find(TEI + 'bibl')
        if bib is not None:             # 扉页题辞：出处 + 引文
            lab = block_text(r, bib)
            e.remove(bib)
            paras.append(('quote', f'{block_text(r, e)} {lab}'))
            return
        txt = block_text(r, e)
        if txt:
            paras.append(('quote', txt))
    elif t in ('closer', 'trailer'):
        paras.append(('closer', block_text(r, e)))
    elif t == 'list':
        for it in e:
            if tag(it) == 'head':
                txt = block_text(r, it)
                if txt:
                    paras.append(('lhead', txt))
            elif tag(it) == 'item':
                txt = block_text(r, it)
                if txt:
                    paras.append(('item', txt))
            elif tag(it) == 'pb':
                x = r.pb(it)
                if x:
                    paras.append(('pb', x))
            else:
                raise ValueError(f'list 下未处理 <{tag(it)}>')
    elif t == 'epigraph':
        for q in e:
            if tag(q) != 'q':
                raise ValueError(f'epigraph 下未处理 <{tag(q)}>')
            vs = []
            for p in q:
                if tag(p) == 'p':
                    b = p.find(TEI + 'bibl')
                    lab = ''
                    if b is not None:
                        lab = block_text(r, b)
                        tail = b.tail
                        p.remove(b)
                        p.text = (p.text or '') + (tail or '')
                    vs.append((lab, block_text(r, p)))
                elif tag(p) == 'pb':
                    x = r.pb(p)
                    if x:
                        vs.append(('', x))
                else:
                    raise ValueError(f'epigraph/q 下未处理 <{tag(p)}>')
            paras.append(('verses', vs))
    elif t in ('figure', 'gap'):
        if t == 'gap':
            r.gap(e)
    else:
        raise ValueError(f'块级未处理的元素 <{t}>')


def split_list_p(r, e):
    """<p>引导句<list><item>…</item></list>后文</p> → 引导句一段、每条一段、后文一段。"""
    out = []
    pieces, cur = [], ET.Element(TEI + 'p')
    cur.text = e.text
    for c in e:
        if tag(c) == 'list':
            pieces.append(('p', cur))
            pieces.append(('list', c))
            cur = ET.Element(TEI + 'p')
            cur.text = c.tail
        else:
            cur.append(c)
    pieces.append(('p', cur))
    for k, el in pieces:
        if k == 'p':
            txt = block_text(r, el)
            if txt:
                out.append(('p', txt))
        else:
            tail, el.tail = el.tail, None
            render_block(r, el, out)
            el.tail = tail
    return out


def vnum(lab):
    """经文行首的节号：「1」「Verse 10.」「Vers. 3.」→ '10'。"""
    m = re.search(r'(\d+)', lab)
    return m.group(1) if m else lab


def to_md(paras):
    """段落元组 → markdown。页码锚点挂进下一段行内（与块级 div 同行会让 div 失效）。"""
    out, pending = [], []
    for item in paras:
        k = item[0]
        if k == 'pb':
            pending.append(item[1])
            continue
        pre = ''.join(pending)
        pending = []
        if k == 'head':
            out.append(f'## {pre}{item[1]}')
        elif k == 'lhead':
            out.append(f'<p class="at-lhead" markdown="1">{pre}{item[1]}</p>')
        elif k == 'verses':
            lines, hold = [], pre
            for lab, v in item[1]:
                if not lab and v.startswith('<span class="at-pb"') and v.endswith('</span>') \
                        and v.count('<span') == 1:
                    hold += v
                    continue
                vn = f'<span class="at-vn">{vnum(lab)}</span> ' if lab else ''
                lines.append(f'<p class="at-v" markdown="1">{hold}{vn}{v}</p>')
                hold = ''
            if hold:
                lines.append(hold)
            out.append('<div class="at-text" markdown="1">\n\n' + '\n'.join(lines) + '\n\n</div>')
        elif k == 'quote':
            out.append(f'<p class="at-quote" markdown="1">{pre}{item[1]}</p>')
        elif k == 'item':
            out.append(f'<p class="at-item" markdown="1">{pre}{item[1]}</p>')
        elif k == 'closer':
            out.append(f'<p class="at-closer" markdown="1">{pre}{item[1]}</p>')
        else:
            out.append(pre + item[1])
    if pending:
        out.append(''.join(pending))
    return '\n\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    root = ET.parse(SRC).getroot()
    text = root.find(TEI + 'text')
    r = R()
    files, order, sections = {}, [], []

    def put(slug, paras):
        md = to_md(paras)
        if slug in files:
            files[slug] += '\n\n' + md
        else:
            files[slug] = md
            order.append(slug)

    def simple(slug, div):
        paras = []
        for c in div:
            render_block(r, c, paras)
        put(slug, paras)

    for div in text.find(TEI + 'front'):
        simple(FRONT[div.get('type')], div)

    body = text.find(TEI + 'body')
    for part in body:                     # 唯一的 <div type="exposition">
        lead = []                         # 总标题与页码：挂到 preface 页首
        for c in part:
            t = tag(c)
            if t in ('pb', 'head'):
                render_block(r, c, lead)
            elif t == 'div' and c.get('type') == 'preface':
                paras = lead
                lead = []
                for x in c:
                    render_block(r, x, paras)
                put('preface', paras)
            elif t == 'div' and c.get('type') in ('verse', 'verses'):
                v1, _, v2 = c.get('n').partition('-')
                v1, v2 = int(v1), int(v2 or v1)
                slug = f'1-{v1}'
                paras = lead
                lead = []
                for x in c:
                    render_block(r, x, paras)
                put(slug, paras)
                sections.append(dict(slug=slug, ch=1, v1=v1, v2=v2))
            elif t == 'trailer':
                paras = []
                render_block(r, c, paras)
                put(sections[-1]['slug'], paras)
            else:
                raise ValueError(f'正文未处理 <{t}> {c.attrib}')

    for div in text.find(TEI + 'back'):
        simple(BACK[div.get('type')], div)

    # 节段须首尾相接、覆盖 1–25
    want = 1
    for s in sections:
        if s['v1'] != want:
            raise ValueError(f'节段断档：{s}')
        want = s['v2'] + 1
    if want != NV[1] + 1:
        raise ValueError(f'节段未到第 {NV[1]} 节')

    bad = 0
    for k, md in files.items():
        plain = re.sub(r'<[^>]+>', '', md)
        if plain.count('*') % 2:
            print(f'⚠️ {k}: 星号奇数', file=sys.stderr); bad += 1
        if 'ſ' in md or 'Ʋ' in md:
            print(f'⚠️ {k}: 残留 ſ/Ʋ', file=sys.stderr); bad += 1
    print('  ' + ' '.join(f'{k}({len(files[k]) // 1000}k)' for k in order), file=sys.stderr)
    print(f'页码 {len(r.pages)}  缺字 {r.gaps}', file=sys.stderr)
    if a.apply:
        OUT.mkdir(parents=True, exist_ok=True)
        for k, md in files.items():
            (OUT / f'{k}.md').write_text(md.strip() + '\n', encoding='utf-8')
        (RAW / 'pages.json').write_text(json.dumps(r.pages) + '\n', encoding='utf-8')
        (RAW / 'order.json').write_text(json.dumps({'order': order, 'sections': sections}, indent=1) + '\n',
                                        encoding='utf-8')
        print(f'写入 {len(files)} 篇 → {OUT}', file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
