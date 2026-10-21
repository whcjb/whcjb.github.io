#!/usr/bin/env python3
"""adams_raw/2peter/src/A00665.xml（EEBO-TCP）→ en_chapters/*.md

    python3 scripts/extract_adams.py            # 试跑，只报统计
    python3 scripts/extract_adams.py --apply

托马斯·亚当斯《彼得后书注释》London 1633，两卷合一号（STC 108）：
  卷一 第 1 章 + 第 2 章前半（至 2:9），印本页 1–764
  卷二 第 2 章后半（2:10 起）+ 第 3 章，印本页 801–1634；书末索引、勘误

底本是 TCP 人工录入的 TEI，**不是 OCR**（old-book-ocr §2.2）。骨架照搬 extract_leighton.py：
只做结构映射，缺字原样留记号，交给 adams_common.py 按判读表回填。

| TEI | 原书 | 产出 |
|---|---|---|
| <div type="verse" n="1"><epigraph><q><bibl>VER. I.</bibl><p>经文 | 每段讲解前排出的经文 | `<div class="ad-text">` 标签 + 经文 |
| <div type="part"><head> | 讲解里的小标题 | `### ` |
| <hi> | 斜体 | `*…*`；嵌套 = 反转 |
| <note place="margin"> | 页边旁注（6,552 条：出处、拉丁） | `<span class="ad-margin">` |
| <pb n="N"> | 印本页码 | `<span class="ad-pb" id="pN">` |
| <seg rend="decorInit"> | 花饰首字 | `<span class="ad-dropcap">` |
| <milestone> | 原书段内分条记号 | 丢（只是排版标记） |
| <gap …> | 读不出的字母／词／一截／外文 | `•`×N / `〈◊〉` / `〈…〉` / `〈Greek〉` |
| <g ref="char:punc"> | 认不清的标点 | `▪` |
| <gap reason="duplicate"> | 缩微胶片重拍页 | 丢（连同紧挨着的 pb） |

长 ſ 归一成 s；u/v、i/j 等拼写照原样。
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'adams_raw' / '2peter'
SRC = RAW / 'src' / 'A00665.xml'
OUT = RAW / 'en_chapters'
TEI = '{http://www.tei-c.org/ns/1.0}'

GAP_LETTER, GAP_WORD, GAP_SPAN, GAP_FOREIGN, PUNC = '•', '〈◊〉', '〈…〉', '〈Greek〉', '▪'
NV = {1: 21, 2: 22, 3: 18}


def tag(e):
    return e.tag.replace(TEI, '')


class R:
    def __init__(self):
        self.pages = []
        self.gaps = {}
        self.held = []
        self.slug = None
        self.cur_page = None
        self.cur_facs = None
        self.pb_seen = {}

    def gap(self, e):
        reason = e.get('reason', '')
        ext = e.get('extent', '') or ''
        if reason == 'duplicate':
            return ''
        if reason == 'foreign':
            self.gaps['foreign'] = self.gaps.get('foreign', 0) + 1
            return GAP_FOREIGN
        m = re.match(r'(\d+) letters?', ext)
        if m:
            self.gaps['letter'] = self.gaps.get('letter', 0) + int(m.group(1))
            return GAP_LETTER * int(m.group(1))
        m = re.match(r'(\d+) words?', ext)
        if m:
            self.gaps['word'] = self.gaps.get('word', 0) + int(m.group(1))
            return ' ' + ' '.join([GAP_WORD] * int(m.group(1))) + ' '
        if re.match(r'\d+ (span|line|page)s?', ext):
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
                    out.append('U')
                else:                        # cmbAbbrStroke / abque：照录字形
                    out.append(c.text or '')
            elif t == 'gap':
                out.append(self.gap(c))
            elif t == 'pb':
                out.append(self.hold(self.pb(c)))
            elif t == 'note':
                out.append(' ' + self.hold(self.note(c)) + ' ')
            elif t == 'seg' and c.get('rend') == 'decorInit':
                out.append(self.hold('<span class="ad-dropcap">' + norm(self, self.inline(c)) + '</span>'))
            elif t in ('seg', 'date', 'q', 'l', 'p', 'signed', 'label', 'salute', 'bibl',
                       'list', 'item', 'dateline', 'expan', 'abbr', 'am', 'ex', 'head', 'trailer'):
                out.append(self.inline(c, italic))
            elif t in ('lb',):
                out.append(' ')
            elif t in ('milestone', 'desc', 'figure', 'figDesc'):
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
        self.cur_facs = facs
        self.cur_page = n
        if not n or c.get('dup'):
            return ''
        self.pages.append((n, facs))
        k = self.pb_seen.get(n, 0) + 1
        self.pb_seen[n] = k
        pid = f'p{n}' + ('' if k == 1 else f'-{k}')
        return f'<span class="ad-pb" id="{pid}" data-p="{n}" data-facs="{facs}"></span>'

    def note(self, c):
        return f'<span class="ad-margin" markdown="1">{norm(self, self.inline(c))}</span>'


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
        txt = block_text(r, e)
        if txt:
            paras.append(('p', txt))
    elif t == 'q':
        txt = block_text(r, e)
        if txt:
            paras.append(('quote', txt))
    elif t in ('opener', 'salute'):
        paras.append(('salute', block_text(r, e)))
    elif t in ('closer', 'trailer', 'signed', 'dateline'):
        paras.append(('closer', block_text(r, e)))
    elif t == 'gap':
        r.gap(e)
    elif t == 'list':
        for it in e:
            if tag(it) in ('item', 'head'):
                txt = block_text(r, it)
                if txt:
                    paras.append(('p', txt))
            elif tag(it) == 'pb':
                x = r.pb(it)
                if x:
                    paras.append(('pb', x))
    elif t == 'figure':
        pass
    elif t == 'epigraph':
        for q in e:
            if tag(q) == 'pb':
                x = r.pb(q)
                if x:
                    paras.append(('pb', x))
                continue
            bib = q.find(TEI + 'bibl')
            lab = block_text(r, bib) if bib is not None else ''
            if bib is not None:
                q.remove(bib)
            paras.append(('text', lab, block_text(r, q)))
    elif t == 'div':
        sub = []
        for c in e:
            render_block(r, c, sub)
        if e.get('type') == 'part' and sub and sub[0][0] == 'head':
            sub[0] = ('subhead', sub[0][1])
        paras.extend(sub)
    else:
        raise ValueError(f'块级未处理的元素 <{t}>')


def to_md(paras):
    """段落元组 → markdown。页码锚点挂进下一段行内（Perkins 踩过：与块级 div 同行会让 div 失效）。"""
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
        elif k == 'subhead':
            out.append(f'### {pre}{item[1]}')
        elif k == 'text':
            out.append(f'<div class="ad-text" markdown="1">\n\n'
                       f'<p class="ad-vlabel" markdown="1">{pre}{item[1]}</p>\n'
                       f'<p class="ad-v" markdown="1">{item[2]}</p>\n\n</div>')
        elif k == 'quote':
            out.append(f'<p class="ad-quote" markdown="1">{pre}{item[1]}</p>')
        elif k == 'salute':
            out.append(f'<p class="ad-salute" markdown="1">{pre}{item[1]}</p>')
        elif k == 'closer':
            out.append(f'<p class="ad-closer" markdown="1">{pre}{item[1]}</p>')
        else:
            out.append(pre + item[1])
    if pending:
        out.append(''.join(pending))
    return '\n\n'.join(out)


def mark_duplicates(root):
    for par in root.iter():
        kids = list(par)
        for x, y in zip(kids, kids[1:]):
            if tag(x) == 'pb' and tag(y) == 'gap' and y.get('reason') == 'duplicate' \
                    and not (x.tail or '').strip():
                x.set('dup', '1')


def verse_slug(ch, d):
    """verse div@n：'1' / '20-21'。页名 <章>-<首节>。"""
    n = d.get('n') or ''
    nums = [int(x) for x in re.findall(r'\d+', n)]
    return nums


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    root = ET.parse(SRC).getroot()
    mark_duplicates(root)
    r = R()
    files = {}
    order = []
    vols = root.find(TEI + 'text').find(TEI + 'group').findall(TEI + 'text')

    last_verse = [None]

    def put(slug, paras):
        md = to_md(paras)
        if slug in files:
            files[slug] += '\n\n' + md
        else:
            files[slug] = md
            order.append(slug)

    for vi, vol in enumerate(vols, 1):
        for part in vol:
            for div in part:
                typ = div.get('type')
                if typ == 'title_page':
                    r.slug = f'title{vi}'
                    paras = []
                    for c in div:
                        render_block(r, c, paras)
                    put(r.slug, paras)
                elif typ == 'dedication':
                    r.slug = 'dedication'
                    paras = []
                    for c in div:
                        render_block(r, c, paras)
                    put(r.slug, paras)
                elif typ and typ.startswith('commentary'):
                    for c in div:
                        t = tag(c)
                        if t == 'div' and c.get('type') == 'chapter':
                            ch = int(c.get('n'))
                            head_paras = []
                            for e in c:
                                if tag(e) == 'div' and e.get('type') == 'verse':
                                    vs = verse_slug(ch, e)
                                    r.slug = f'{ch}-{vs[0]}'
                                    last_verse[0] = r.slug
                                    paras = head_paras
                                    head_paras = []
                                    for x in e:
                                        render_block(r, x, paras)
                                    put(r.slug, paras)
                                elif tag(e) == 'div':        # 卷二开头续 2:10 的 conclusion「The Summe of the Verse」
                                    r.slug = last_verse[0]
                                    paras = []
                                    render_block(r, e, paras)
                                    put(r.slug, paras)
                                else:
                                    render_block(r, e, head_paras)
                            if head_paras:
                                put(r.slug, head_paras)
                        elif t in ('pb', 'head', 'trailer'):
                            paras = []
                            render_block(r, c, paras)
                            if paras:
                                put(r.slug or 'front', paras)
                        else:
                            raise ValueError(f'卷{vi} commentary 下未处理 <{t}> {c.get("type")}')
                elif typ == 'index':
                    r.slug = 'index'
                    paras = []
                    for c in div:
                        render_block(r, c, paras)
                    put(r.slug, paras)
                elif typ == 'errata':
                    r.slug = 'errata'
                    paras = []
                    for c in div:
                        render_block(r, c, paras)
                    put(r.slug, paras)
                else:
                    raise ValueError(f'卷{vi} 未处理的 div type={typ}')

    bad = 0
    for k, md in files.items():
        plain = re.sub(r'<[^>]+>', '', md)
        if plain.count('*') % 2:
            print(f'⚠️ {k}: 星号奇数', file=sys.stderr); bad += 1
        if 'ſ' in md:
            print(f'⚠️ {k}: 残留 ſ', file=sys.stderr); bad += 1
    print(f'篇 {len(files)}  页码 {len(r.pages)}  缺字 {r.gaps}', file=sys.stderr)
    print('  ' + ' '.join(order), file=sys.stderr)
    if a.apply:
        OUT.mkdir(parents=True, exist_ok=True)
        for k, md in files.items():
            (OUT / f'{k}.md').write_text(md.strip() + '\n', encoding='utf-8')
        (RAW / 'pages.json').write_text(json.dumps(r.pages, indent=0) + '\n', encoding='utf-8')
        (RAW / 'order.json').write_text(json.dumps(order) + '\n', encoding='utf-8')
        print(f'写入 {len(files)} 篇 → {OUT}', file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
