#!/usr/bin/env python3
"""jenkyn_raw/jude/src/A87554.xml + A87557.xml（EEBO-TCP）→ en_chapters/*.md

    python3 scripts/extract_jenkyn.py            # 试跑，只报统计
    python3 scripts/extract_jenkyn.py --apply

William Jenkyn《犹大书讲解》两部分：
  第一部分 A87554：London 1652（Thomason 本扉页 1653），Jude 1–8 前半，印本页 1–640
  第二部分 A87557：London 1654，Jude 8 后半–25，印本页 1–686（另起页码）

底本是 TCP 人工录入的 TEI，**不是 OCR**。骨架照搬 extract_adams.py，只做结构映射；
缺字原样留记号，交给 jenkyn_common.py 按判读表回填。

与 adams 的不同：每个 <gap> / 认不清的标点在记号前嵌一个编号 `\\ue000N\\ue001`（N = 两部分按文档顺序
统一编号，jenkyn_witness.py 用同一个函数编），落判读时按编号精确定位，不再靠串比对对齐。

| TEI | 原书 | 产出 |
|---|---|---|
| <div type="verse(s)"><epigraph><bibl>VER. 1.</bibl><q>经文 | 每节讲解前的经文 | `<div class="jk-text">` |
| <div type="part/commentary/observations"><head> | EXPLICATION / OBSERVATIONS 等小标题 | `### ` |
| <hi> | 斜体 | `*…*`；嵌套 = 反转 |
| <note place="margin"> | 页边旁注 | `<span class="jk-margin">` |
| <pb n="N"> | 印本页码 | `<span class="jk-pb" id="pN">`（第二部分 id 前缀 `q`） |
| <add> | Thomason 藏本的手写批注（日期等） | 丢（非印刷文字） |
| <gap reason="duplicate"> | 缩微胶片重拍页 | 丢（连同紧挨着的 pb） |
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'jenkyn_raw' / 'jude'
SRCS = [RAW / 'src' / 'A87554.xml', RAW / 'src' / 'A87557.xml']
OUT = RAW / 'en_chapters'
TEI = '{http://www.tei-c.org/ns/1.0}'

GAP_LETTER, GAP_WORD, GAP_SPAN, GAP_FOREIGN, PUNC = '•', '〈◊〉', '〈…〉', '〈Greek〉', '▪'
ID_L, ID_R = '', ''
NV = 25


def tag(e):
    return e.tag.replace(TEI, '')


def load_roots():
    """两部分的 TEI 根；丢 <add>（手写批注），标出 duplicate 页，给缺字元素统一编号（属性 gn）。"""
    roots = [ET.parse(f).getroot() for f in SRCS]
    n = 0
    for root in roots:
        for par in root.iter():
            for c in list(par):
                if tag(c) == 'add':
                    # 保住 tail
                    kids = list(par)
                    i = kids.index(c)
                    tail = c.tail or ''
                    if i:
                        kids[i - 1].tail = (kids[i - 1].tail or '') + tail
                    else:
                        par.text = (par.text or '') + tail
                    par.remove(c)
        mark_duplicates(root)
        for e in root.find(TEI + 'text').iter():
            if (tag(e) == 'gap' and e.get('reason') != 'duplicate') or \
                    (tag(e) == 'g' and e.get('ref') == 'char:punc'):
                e.set('gn', str(n))
                n += 1
    return roots


def mark_duplicates(root):
    for par in root.iter():
        kids = list(par)
        for x, y in zip(kids, kids[1:]):
            if tag(x) == 'pb' and tag(y) == 'gap' and y.get('reason') == 'duplicate' \
                    and not (x.tail or '').strip():
                x.set('dup', '1')


def gap_text(e):
    """缺字元素 → (记号串, 类别)。"""
    reason = e.get('reason', '')
    ext = e.get('extent', '') or ''
    if reason == 'foreign':
        return GAP_FOREIGN, 'foreign'
    m = re.match(r'(\d+) letters?', ext)
    if m:
        return GAP_LETTER * int(m.group(1)), 'letter'
    m = re.match(r'(\d+) words?', ext)
    if m:
        return ' ' + ' '.join([GAP_WORD] * int(m.group(1))) + ' ', 'word'
    if re.match(r'\d+ (span|line|page|chunk)s?', ext):
        return ' ' + GAP_SPAN + ' ', 'span'
    raise ValueError(f'未知 gap: {e.attrib}')


def gid_mark(e):
    return f'{ID_L}{e.get("gn")}{ID_R}'


class R:
    def __init__(self):
        self.pages = []
        self.gaps = {}
        self.held = []
        self.part = 1
        self.pb_seen = {}

    def gap(self, e):
        if e.get('reason') == 'duplicate':
            return ''
        s, k = gap_text(e)
        self.gaps[k] = self.gaps.get(k, 0) + 1
        # 编号贴在记号前；多词缺口（' 〈◊〉 〈◊〉 '）贴在第一个记号上
        lead = s[:len(s) - len(s.lstrip())]
        return lead + gid_mark(e) + s.lstrip()

    def inline(self, e, italic=False):
        on, off = ('\x01', '\x02')
        out = [e.text or '']
        for c in e:
            t = tag(c)
            if t == 'hi':
                if c.get('rend') == 'sup':
                    out.append(self.inline(c, italic))
                else:
                    inner = self.inline(c, not italic)
                    out.append((on if not italic else off) + inner + (off if not italic else on))
            elif t == 'g':
                ref = c.get('ref')
                if ref in ('char:EOLhyphen', 'char:EOLunhyphen'):
                    while out and out[-1].strip() == '' and '\n' in out[-1]:
                        out.pop()
                    if out and out[-1].endswith(('\n', ' ', '\t')) and '\n' in out[-1]:
                        out[-1] = out[-1].rstrip()
                    out.append('\x04')
                elif ref == 'char:punc':
                    self.gaps['punc'] = self.gaps.get('punc', 0) + 1
                    out.append(gid_mark(c) + PUNC)
                elif ref == 'char:V':
                    out.append('U')
                else:
                    out.append(c.text or '')
            elif t == 'gap':
                out.append(self.gap(c))
            elif t == 'pb':
                out.append(self.hold(self.pb(c)))
            elif t == 'note':
                out.append(' ' + self.hold(self.note(c)) + ' ')
            elif t == 'seg' and c.get('rend') == 'decorInit':
                out.append(self.hold('<span class="jk-dropcap">' + norm(self, self.inline(c)) + '</span>'))
            elif t in ('seg', 'date', 'q', 'l', 'p', 'signed', 'label', 'salute', 'bibl',
                       'list', 'item', 'dateline', 'expan', 'abbr', 'am', 'ex', 'head', 'trailer'):
                out.append(self.inline(c, italic))
            elif t == 'lb':
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
        if not n or c.get('dup'):
            return ''
        pre = 'p' if self.part == 1 else 'q'
        self.pages.append((self.part, n, facs))
        k = self.pb_seen.get((pre, n), 0) + 1
        self.pb_seen[(pre, n)] = k
        pid = f'{pre}{n}' + ('' if k == 1 else f'-{k}')
        yr = '1652' if self.part == 1 else '1654'
        return (f'<span class="jk-pb" id="{pid}" data-p="{n}" data-part="{self.part}" data-facs="{facs}" '
                f'title="Part {self.part}, page {n} of the {yr} edition begins here (第{"一二"[self.part - 1]}部分原书第 {n} 页起)"></span>')

    def note(self, c):
        return f'<span class="jk-margin" markdown="1">{norm(self, self.inline(c))}</span>'


def norm(r, s):
    s = s.replace('ſ', 's').replace('*', '&#42;')     # 原书的星号参见记号：写实体，不与斜体星号混
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


def render_list(r, e, paras):
    """<list> → ('list', [条目…])：一条一行、条间不留段距。夹在条目之间的页码挂进下一条行首。"""
    items, pend = [], ''
    for it in e:
        if tag(it) in ('item', 'head'):
            txt = block_text(r, it)
            if txt:
                items.append(pend + txt)
                pend = ''
        elif tag(it) == 'pb':
            pend += r.pb(it)
        else:
            raise ValueError(f'list 下未处理 <{tag(it)}>')
    if pend:
        if items:
            items[-1] += pend
        else:
            paras.append(('pb', pend))
    if items:
        paras.append(('list', items))


def render_block(r, e, paras):
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
        # 段内直属的 <list>：原书是引导句下逐条分行的紧凑列表，切出来单独排（2026-10-30）。
        # 条目里再套的 <list>（Cain/Balaam/Core 一类花括号并列）和旁注里的仍按行内拍平。
        cur = ET.Element(e.tag)
        cur.text = e.text
        for c in e:
            if tag(c) == 'list':
                txt = block_text(r, cur)
                if txt:
                    paras.append(('p', txt))
                render_list(r, c, paras)
                cur = ET.Element(e.tag)
                cur.text = c.tail
            else:
                cur.append(c)
        txt = block_text(r, cur)
        if txt:
            paras.append(('p', txt))
    elif t == 'q':
        bib = e.find(TEI + 'bibl')
        if bib is not None:
            lab = block_text(r, bib)
            e.remove(bib)
            paras.append(('quote', f'{lab} {block_text(r, e)}'))
        else:
            txt = block_text(r, e)
            if txt:
                paras.append(('quote', txt))
    elif t in ('opener', 'salute'):
        paras.append(('salute', block_text(r, e)))
    elif t in ('closer', 'trailer', 'signed', 'dateline'):
        paras.append(('closer', block_text(r, e)))
    elif t == 'gap':
        if e.get('reason') != 'duplicate':
            paras.append(('p', r.gap(e).strip()))
    elif t == 'list':
        render_list(r, e, paras)
    elif t in ('figure', 'milestone'):
        pass
    elif t == 'note':                  # 块级旁注（夹在两段之间）：单独成段
        paras.append(('p', r.note(e)))
    elif t == 'epigraph':
        # 经文：<bibl> 与 <q> 可能是兄弟（VER. 1 的 epigraph 连排两节），也可能 <bibl> 在 <q> 里
        lab = ''
        for q in e:
            if tag(q) == 'pb':
                x = r.pb(q)
                if x:
                    paras.append(('pb', x))
            elif tag(q) == 'bibl':
                lab = block_text(r, q)
            elif tag(q) == 'q':
                bib = q.find(TEI + 'bibl')
                if bib is not None:
                    lab = block_text(r, bib)
                    q.remove(bib)
                paras.append(('text', lab, block_text(r, q)))
                lab = ''
            else:
                raise ValueError(f'epigraph 下未处理 <{tag(q)}>')
        if lab:
            raise ValueError(f'epigraph 落单的 bibl: {lab}')
    elif t == 'div':
        sub = []
        for c in e:
            render_block(r, c, sub)
        if sub and sub[0][0] == 'head':
            sub[0] = ('subhead', sub[0][1])
        paras.extend(sub)
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
        elif k == 'subhead':
            out.append(f'### {pre}{item[1]}')
        elif k == 'text':
            out.append(f'<div class="jk-text" markdown="1">\n\n'
                       f'<p class="jk-vlabel" markdown="1">{pre}{item[1]}</p>\n'
                       f'<p class="jk-v" markdown="1">{item[2]}</p>\n\n</div>')
        elif k == 'quote':
            out.append(f'<p class="jk-quote" markdown="1">{pre}{item[1]}</p>')
        elif k == 'salute':
            out.append(f'<p class="jk-salute" markdown="1">{pre}{item[1]}</p>')
        elif k == 'list':
            out.append('<div class="jk-list" markdown="1">\n'
                       + '\n'.join(f'<p markdown="1">{pre if i == 0 else ""}{x}</p>'
                                   for i, x in enumerate(item[1]))
                       + '\n</div>')
        elif k == 'closer':
            out.append(f'<p class="jk-closer" markdown="1">{pre}{item[1]}</p>')
        else:
            out.append(pre + item[1])
    if pending:
        out.append(''.join(pending))
    return '\n\n'.join(out)


def verse_range(d):
    """verse div → (首节, 末节)。n 缺（20、21 两节）时取经文标签 VER. N。"""
    n = d.get('n') or ''
    nums = [int(x) for x in re.findall(r'\d+', n)]
    if not nums:
        bib = d.find(f'{TEI}epigraph/{TEI}bibl')
        if bib is None:
            bib = d.find(f'{TEI}epigraph/{TEI}q/{TEI}bibl')
        nums = [int(x) for x in re.findall(r'\d+', ''.join(bib.itertext()))]
    lab = d.find(f'{TEI}epigraph/{TEI}bibl')
    if lab is not None:            # 24 的 n 只写首节，标签是「Ver. 24, 25.」
        more = [int(x) for x in re.findall(r'\d+', ''.join(lab.itertext()))]
        if more and more[0] == nums[0]:
            nums = more
    return nums[0], nums[-1]


FRONT_SLUG = {(1, 'title_page'): 'title1', (1, 'to_the_reader'): 'to-the-reader',
              (1, 'errata'): 'errata1', (1, 'publishers_advertisement'): 'advertisement',
              (2, 'title_page'): 'title2', (2, 'dedication'): 'dedication', (2, 'errata'): 'errata2'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    roots = load_roots()
    r = R()
    files, order, ranges = {}, [], {}

    def put(slug, paras):
        md = to_md(paras)
        if slug in files:
            files[slug] += '\n\n' + md
        else:
            files[slug] = md
            order.append(slug)

    for part, root in enumerate(roots, 1):
        r.part = part
        text = root.find(TEI + 'text')
        for sect in text:
            for div in sect:
                typ = div.get('type')
                if (part, typ) in FRONT_SLUG:
                    paras = []
                    for c in div:
                        render_block(r, c, paras)
                    put(FRONT_SLUG[(part, typ)], paras)
                elif typ in ('exegesis_of_Jude', 'biblical_exegesis'):
                    carry, slug = [], None
                    for c in div:
                        if tag(c) == 'div' and c.get('type') in ('verse', 'verses'):
                            v1, v2 = verse_range(c)
                            slug = str(v1) if not (part == 2 and v1 == 8) else '8-ii'
                            ranges[slug] = (v1, v2, part)
                            paras = carry
                            carry = []
                            for x in c:
                                render_block(r, x, paras)
                            put(slug, paras)
                        elif slug is None or tag(c) == 'pb':
                            render_block(r, c, carry)       # 正文总标题、首页页码、节间页码挂到下一节前
                        else:                               # 节与节之间的段落（结语、FINIS）接在上一节后
                            paras = []
                            render_block(r, c, paras)
                            put(slug, paras)
                    if carry:
                        put(slug, carry)
                else:
                    raise ValueError(f'第{part}部分未处理的 div type={typ}')

    bad = 0
    for k, md in files.items():
        plain = re.sub(r'<[^>]+>', '', md)
        if plain.count('*') % 2:
            print(f'⚠️ {k}: 星号奇数', file=sys.stderr); bad += 1
        if 'ſ' in md:
            print(f'⚠️ {k}: 残留 ſ', file=sys.stderr); bad += 1
    nid = sum(md.count(ID_L) for md in files.values())
    print(f'篇 {len(files)}  页码 {len(r.pages)}  缺字 {r.gaps}  编号 {nid}', file=sys.stderr)
    print('  ' + ' '.join(f'{k}({len(files[k]) // 1000}k)' for k in order), file=sys.stderr)
    if a.apply:
        OUT.mkdir(parents=True, exist_ok=True)
        for k, md in files.items():
            (OUT / f'{k}.md').write_text(md.strip() + '\n', encoding='utf-8')
        (RAW / 'pages.json').write_text(json.dumps(r.pages) + '\n', encoding='utf-8')
        (RAW / 'order.json').write_text(json.dumps({'order': order, 'ranges': ranges}) + '\n', encoding='utf-8')
        print(f'写入 {len(files)} 篇 → {OUT}', file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
