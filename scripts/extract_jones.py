#!/usr/bin/env python3
"""jones_raw/src/A04619.xml（EEBO-TCP）→ jones_raw/{2john,3john}/en_chapters/*.md

    python3 scripts/extract_jones.py            # 试跑，只报统计
    python3 scripts/extract_jones.py --apply

威廉·琼斯《腓利门书、希伯来书注释，附约翰二书、三书简释》London: R. B. for Robert Allot 1635
（STC 14739.5）。本站只取卷末的约翰二书（印本 pp. 661–688 前后）、约翰三书两篇；腓利门书、希伯来书不取。
底本是 TCP 人工录入的 TEI，**不是 OCR**。骨架照搬 extract_attersoll.py：只做结构映射，缺字原样留记号，
交给 jones_common.py 按判读表回填。

原书按节讲（TCP 已分好 <div type="verse">，题头「VERSE. 1.」）：节下不排经文，直接以方括号引出
所讲字句（「[THE ELDER]」）再逐条讲。发布一节一页，页名 `1-<节>`；约翰三书末段合讲 13、14 节，页名 `1-13`。
每卷另出章目录 `1.md`（历代解经扫描器与对照抽屉按章号页找书）。
卷首书名页、致读者是全书共用的，献给杰尔明爵士的献辞专为约翰二书、三书与腓利门书而写，三篇两卷各收一份；卷末勘误只取「In Epist. Iohan.」一节。

| TEI | 原书 | 产出 |
|---|---|---|
| <head>VERSE. N.</head> | 节题 | 丢（页题已有），只取节号 |
| <p>[<hi>…</hi>]</p> | 所讲字句（lemma） | `<p class="jw-lemma">` |
| <hi> | 斜体 | `*…*`；嵌套 = 反转 |
| <hi rend="sup"> | 上标（S<sup>t</sup>） | `<sup>` |
| <note place="margin"> | 页边出处 | `<span class="jw-margin">` |
| <pb n="N"> | 印本页码 | `<span class="jw-pb" id="pN">` |
| <seg rend="decorInit"> | 花饰首字 | `<span class="jw-dropcap">` |
| <gap reason="foreign"> | 录入者未录的希腊文 | `〈Greek〉` |
| <gap …> | 读不出的字母／词 | `•`×N / `〈◊〉` |
| <g ref="char:punc"> | 认不清的标点 | `▪` |
| <g ref="char:abque"> | que 的缩写符 | que |
| <opener> / <closer> / <trailer> | 献辞称呼／落款／FINIS | `.jw-opener` / `.jw-closer` / `.jw-trailer` |
| <gap reason="duplicate"> | 缩微胶片重拍页 | 丢 |

长 ſ 归一成 s；u/v、i/j 等拼写照原样。
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jones_common as jc  # noqa: E402

TEI = '{http://www.tei-c.org/ns/1.0}'
GAP_LETTER, GAP_WORD, GAP_SPAN, GAP_FOREIGN, PUNC = '•', '〈◊〉', '〈…〉', '〈Greek〉', '▪'
# 卷末两篇的 exegesis 题头 → 卷名；各卷节数（约翰三书末段合讲 13–14）
HEADS = {'second': '2john', 'third': '3john'}
NV = {'2john': 13, '3john': 14}


def tag(e):
    return e.tag.replace(TEI, '')


class R:
    def __init__(self):
        self.pages = []
        self.gaps = {}
        self.held = []

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
            if t == 'hi' and c.get('rend') == 'sup':
                out.append(self.hold('<sup>' + norm(self, self.inline(c)) + '</sup>'))
            elif t == 'hi':
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
                elif ref == 'char:abque':
                    out.append('que')
                else:                        # cmbAbbrStroke 等：照录字形
                    out.append(c.text or '')
            elif t == 'gap':
                out.append(self.gap(c))
            elif t == 'pb':
                out.append(self.hold(self.pb(c)))
            elif t == 'note':
                out.append(' ' + self.hold(self.note(c)) + ' ')
            elif t == 'seg' and c.get('rend') == 'decorInit':
                out.append(self.hold('<span class="jw-dropcap">' + norm(self, self.inline(c)) + '</span>'))
            elif t in ('seg', 'q', 'p', 'bibl', 'expan', 'am', 'ex', 'signed', 'salute', 'dateline', 'date'):
                out.append(self.inline(c, italic))
            elif t == 'lb':
                out.append(' ')
            elif t in ('desc', 'figure'):
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
        if c.get('rendition'):           # TCP 自加的「additions」页标记，与下一个 pb 重复
            return ''
        if not n:
            return f'<span class="jw-pb" data-facs="{facs}"></span>'
        self.pages.append((n, facs))
        return (f'<span class="jw-pb" id="p{n}" data-p="{n}" data-facs="{facs}" '
                f'title="Page {n} of the 1635 edition begins here (原书第 {n} 页起)"></span>')

    def note(self, c):
        return f'<span class="jw-margin" markdown="1">{norm(self, self.inline(c))}</span>'


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


RE_LEMMA = re.compile(r'^((?:<span class="jw-pb"[^>]*></span>)*)\s*\[([^\[\]]+)\]\s*$')


def render_block(r, e, paras):
    t = tag(e)
    if t == 'head':
        txt = norm(r, r.inline(e))
        if txt:
            paras.append(('head', txt))
    elif t == 'pb':
        x = r.pb(e)
        if x:
            paras.append(('pb', x))
    elif t == 'p':
        if e.find(TEI + 'q') is not None and e.find(TEI + 'q').find(TEI + 'bibl') is not None:
            q = e.find(TEI + 'q')            # 扉页题辞：引文 + 出处
            b = q.find(TEI + 'bibl')
            lab = norm(r, r.inline(b))
            q.remove(b)
            paras.append(('quote', f'{norm(r, r.inline(q))} {lab}'))
            return
        txt = norm(r, r.inline(e))
        if not txt:
            return
        m = RE_LEMMA.match(txt)
        paras.append(('lemma', m.group(1) + '[' + m.group(2) + ']') if m else ('p', txt))
    elif t == 'opener':                  # 献辞起首称呼（RIGHT HONOVRABLE,）
        paras.append(('opener', norm(r, r.inline(e))))
    elif t in ('closer', 'trailer'):
        paras.append((t, norm(r, r.inline(e))))
    elif t in ('figure', 'gap'):
        if t == 'gap':
            r.gap(e)
    else:
        raise ValueError(f'块级未处理的元素 <{t}>')


def to_md(paras):
    """段落元组 → markdown。页码锚点挂进下一段行内。"""
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
        elif k == 'lemma':
            out.append(f'<p class="jw-lemma" markdown="1">{pre}{item[1]}</p>')
        elif k == 'quote':
            out.append(f'<p class="jw-quote" markdown="1">{pre}{item[1]}</p>')
        elif k == 'opener':
            out.append(f'<p class="jw-opener" markdown="1">{pre}{item[1]}</p>')
        elif k in ('closer', 'trailer'):
            out.append(f'<p class="jw-{k}" markdown="1">{pre}{item[1]}</p>')
        else:
            out.append(pre + item[1])
    if pending:
        out.append(''.join(pending))
    return '\n\n'.join(out)


def verse_range(head):
    ns = [int(x) for x in re.findall(r'\d+', head)]
    if not ns:
        raise ValueError(f'节题无节号：{head}')
    return ns[0], ns[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    root = ET.parse(jc.SRC_XML).getroot()
    text = root.find(TEI + 'text')
    r = R()

    def simple(div):
        paras = []
        for c in div:
            render_block(r, c, paras)
        return to_md(paras)

    front = {d.get('type'): d for d in text.find(TEI + 'front')}
    # 两篇献辞：给里奇勋爵的是献希伯来书；给杰尔明爵士的献约翰二书、三书与腓利门书，只取这篇
    ded = next(d for d in text.find(TEI + 'front')
               if d.get('type') == 'dedication' and 'IERMYN' in ''.join(d.find(TEI + 'head').itertext()))
    shared = {'title': simple(front['title_page']), 'dedication': simple(ded),
              'to-the-reader': simple(front['to_the_reader'])}
    errata = next(s for s in text.find(TEI + 'back').iter(TEI + 'div')
                  if s.get('type') == 'section' and 'Iohan' in ''.join(s.find(TEI + 'head').itertext()))
    shared['errata'] = simple(errata)

    books = {}
    for part in text.find(TEI + 'body'):
        h = ' '.join(''.join(part.find(TEI + 'head').itertext()).split())
        key = next((v for k, v in HEADS.items() if f'The {k} Epistle' in h), None)
        if not key:
            continue
        files, order, sections, lead = {}, ['title', 'dedication', 'to-the-reader'], [], []
        for c in part:
            t = tag(c)
            if t in ('pb', 'head'):
                render_block(r, c, lead)
            elif t == 'div' and c.get('type') == 'verse':
                v1, v2 = verse_range(''.join(c.find(TEI + 'head').itertext()))
                slug = f'1-{v1}'
                paras = lead
                lead = []
                for x in c:
                    if tag(x) == 'head':
                        continue
                    render_block(r, x, paras)
                files[slug] = to_md(paras)
                order.append(slug)
                sections.append(dict(slug=slug, ch=1, v1=v1, v2=v2))
            elif t == 'trailer':
                paras = []
                render_block(r, c, paras)
                files[sections[-1]['slug']] += '\n\n' + to_md(paras)
            else:
                raise ValueError(f'正文未处理 <{t}> {c.attrib}')
        want = 1
        for s in sections:
            if s['v1'] != want:
                raise ValueError(f'{key} 节段断档：{s}')
            want = s['v2'] + 1
        if want != NV[key] + 1:
            raise ValueError(f'{key} 节段未到第 {NV[key]} 节')
        order.append('errata')
        files.update(shared)
        books[key] = (files, order, sections)

    if set(books) != set(jc.BOOKS):
        raise ValueError(f'卷没找全：{sorted(books)}')
    bad = 0
    for key, (files, order, sections) in books.items():
        for k, md in files.items():
            plain = re.sub(r'<[^>]+>', '', md)
            if plain.count('*') % 2:
                print(f'⚠️ {key}/{k}: 星号奇数', file=sys.stderr); bad += 1
            if 'ſ' in md:
                print(f'⚠️ {key}/{k}: 残留 ſ', file=sys.stderr); bad += 1
        print(f'{key}: ' + ' '.join(f'{k}({len(files[k]) // 1000}k)' for k in order), file=sys.stderr)
    print(f'页码 {len(r.pages)}  缺字 {r.gaps}（含书名页、致读者、勘误各算一次）', file=sys.stderr)
    if a.apply:
        for key, (files, order, sections) in books.items():
            out = jc.raw(key) / 'en_chapters'
            out.mkdir(parents=True, exist_ok=True)
            for k, md in files.items():
                (out / f'{k}.md').write_text(md.strip() + '\n', encoding='utf-8')
            (jc.raw(key) / 'order.json').write_text(
                json.dumps({'order': order, 'sections': sections}, indent=1) + '\n', encoding='utf-8')
            print(f'写入 {len(files)} 篇 → {out}', file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
