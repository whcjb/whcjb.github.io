"""EEBO-TCP TEI → markdown 的共用行内／块级渲染（霍尔、巴洛《提摩太后书》用）。

行内与规范化照搬 extract_taylor.py（已在泰勒、罗洛克上跑通），只把 class 前缀做成参数，
块级换成按 TEI 元素直译（这两本的 div 结构是录入时就分好的，不用像泰勒那样从经文引语猜分段）。

| TEI | 产出（前缀 P，如 hl / bl） |
|---|---|
| <hi> | `*…*`；嵌套 = 反转 |
| <note place="margin"> | `<span class="P-margin">` |
| <pb n facs> | `<span class="P-pb" id="pN">`（无页码的页只留 data-facs，供证人定位） |
| <seg rend="decorInit"> | `<span class="P-dropcap">` |
| <gap …> | `•`×N / `〈◊〉` / `〈…〉` / `〈Greek〉`；reason=missing → `〈MISSING:N〉`；duplicate 丢 |
| <g ref="char:punc"> | `▪` |
| <head> | `### `（深一层 div 用 `#### `） |
| <list> | 每条 `<p class="P-item">`；<label> 并入下一条，作粗体 |
| <q><l> | `<div class="P-poem">` 每行一段 |
| <q><p>/<q>文字 | `<p class="P-quote">` |
| <table> | `<table class="P-table">` |
| closer/opener/signed/trailer… | `<p class="P-closer">` |
"""
import re
import xml.etree.ElementTree as ET

TEI = '{http://www.tei-c.org/ns/1.0}'
GAP_LETTER, GAP_WORD, GAP_SPAN, GAP_FOREIGN, PUNC = '•', '〈◊〉', '〈…〉', '〈Greek〉', '▪'


def tag(e):
    return e.tag.replace(TEI, '')


def text_of(e):
    return re.sub(r'\s+', ' ', ''.join(e.itertext())).strip()


class R:
    def __init__(self, P, edition):
        self.P = P
        self.edition = edition
        self.pages = []
        self.gaps = {}
        self.held = []
        self.pb_seen = {}
        self.missing = 0

    # ── 行内 ──
    def gap(self, e):
        reason = e.get('reason', '')
        ext = e.get('extent', '') or ''
        if reason == 'duplicate':
            return ''
        if reason == 'missing':
            self.missing += 1
            self.gaps['missing'] = self.gaps.get('missing', 0) + 1
            return f' 〈MISSING:{self.missing}〉 '
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
                else:                        # cmbAbbrStroke 等：照录字形
                    out.append(c.text or '')
            elif t == 'gap':
                out.append(self.gap(c))
            elif t == 'pb':
                out.append(self.hold(self.pb(c)))
            elif t == 'note':
                out.append(' ' + self.hold(self.note(c)) + ' ')
            elif t == 'seg' and c.get('rend') == 'decorInit':
                out.append(self.hold(f'<span class="{self.P}-dropcap">' + norm(self, self.inline(c)) + '</span>'))
            elif t in ('seg', 'q', 'p', 'signed', 'bibl', 'head', 'trailer', 'expan', 'am', 'ex', 'date',
                       'dateline', 'item', 'closer', 'label', 'l', 'salute', 'cell'):
                if t in ('item', 'p', 'l', 'label') and out and not out[-1].endswith(' '):
                    out.append(' ')
                out.append(self.inline(c, italic))
            elif t == 'list':
                for it in c:
                    if tag(it) == 'pb':
                        out.append(self.hold(self.pb(it)))
                    elif tag(it) in ('item', 'head', 'label'):
                        out.append(' ' + self.inline(it, italic))
            elif t == 'lb':
                out.append(' ')
            elif t in ('desc', 'figure', 'milestone', 'figDesc'):
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
        if not n:
            return f'<span class="{self.P}-pb" data-facs="{facs}"></span>'
        self.pages.append((n, facs))
        k = self.pb_seen.get(n, 0) + 1
        self.pb_seen[n] = k
        pid = f'p{n}' + ('' if k == 1 else f'-{k}')
        return (f'<span class="{self.P}-pb" id="{pid}" data-p="{n}" data-facs="{facs}" '
                f'title="Page {n} of the {self.edition} edition begins here (原书第 {n} 页起)"></span>')

    def note(self, c):
        return f'<span class="{self.P}-margin" markdown="1">{norm(self, self.inline(c))}</span>'

    def text(self, e):
        return norm(self, self.inline(e))


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


# ── 块级 ──
def blocks(r, e, out, depth=3):
    """e 的子元素逐个渲染成段落元组，追加到 out。"""
    for c in e:
        block(r, c, out, depth)


def block(r, e, out, depth=3):
    P = r.P
    t = tag(e)
    if t == 'head':
        txt = r.text(e)
        if txt:
            out.append(('head', '#' * depth + ' ' + txt))
    elif t == 'pb':
        x = r.pb(e)
        if x:
            out.append(('pb', x))
    elif t == 'p':
        if any(tag(c) in ('list', 'table', 'q') and _blockish(c) for c in e):
            out.extend(split_mixed(r, e, depth))
            return
        txt = r.text(e)
        if txt:
            out.append(('p', txt))
    elif t == 'list':
        lab = ''
        for it in e:
            k = tag(it)
            if k == 'pb':
                x = r.pb(it)
                if x:
                    out.append(('pb', x))
            elif k == 'label':
                lab = r.text(it)
            elif k == 'head':
                txt = r.text(it)
                if txt:
                    out.append(('cls', f'{P}-listhead', txt))
            elif k == 'item':
                txt = r.text(it)
                if lab:
                    txt = f'**{lab}** {txt}'.strip()
                    lab = ''
                if txt:
                    out.append(('cls', f'{P}-item', txt))
            else:
                raise ValueError(f'list 下未处理 <{k}>')
        if lab:
            out.append(('cls', f'{P}-item', f'**{lab}**'))
    elif t == 'q':
        if any(tag(c) == 'l' for c in e):
            lines = []
            for c in e:
                k = tag(c)
                if k == 'l':
                    lines.append(r.text(c))
                elif k == 'bibl':
                    lines.append(r.text(c))
                elif k == 'pb':
                    x = r.pb(c)
                    if x:
                        lines.append(x)
                elif k == 'note':
                    lines.append(r.note(c))
                else:
                    raise ValueError(f'q/l 下未处理 <{k}>')
            out.append(('poem', lines))
            if (e.text or '').strip():
                raise ValueError('q 带散字')
            return
        if any(tag(c) == 'floatingText' for c in e):
            for c in e:
                if tag(c) == 'floatingText':
                    inner = []
                    for b in c:
                        blocks(r, b, inner, depth + 1)
                    out.append(('float', inner))
                else:
                    block(r, c, out, depth)
            return
        if any(tag(c) == 'p' for c in e):
            for c in e:
                if tag(c) == 'p':
                    out.append(('cls', f'{P}-quote', r.text(c)))
                else:
                    block(r, c, out, depth)
            return
        txt = r.text(e)
        if txt:
            out.append(('cls', f'{P}-quote', txt))
    elif t == 'bibl':
        out.append(('cls', f'{P}-quote', r.text(e)))
    elif t in ('closer', 'trailer', 'opener', 'signed', 'dateline', 'salute', 'byline'):
        txt = r.text(e)
        if txt:
            out.append(('cls', f'{P}-closer', txt))
    elif t == 'table':
        out.append(('table', table_html(r, e)))
    elif t == 'note':
        out.append(('p', r.note(e)))
    elif t == 'figure':
        h = e.find(TEI + 'head')
        if h is not None:
            out.append(('cls', f'{P}-closer', r.text(h)))
    elif t == 'div':
        blocks(r, e, out, min(depth + 1, 5))
    elif t == 'gap':
        g = r.gap(e)
        if g.strip():
            out.append(('p', g.strip()))
    elif t == 'label':
        out.append(('p', f'**{r.text(e)}**'))
    else:
        raise ValueError(f'块级未处理的元素 <{t}>')


def _blockish(c):
    return tag(c) in ('table',) or (tag(c) == 'list' and len(c) > 1) or \
        (tag(c) == 'q' and any(tag(x) in ('l', 'p', 'floatingText') for x in c))


def split_mixed(r, e, depth):
    """<p>前文<list|table|q>…</…>后文</p> → 前文一段、块、后文一段。"""
    out, cur = [], ET.Element(TEI + 'p')
    cur.text = e.text
    pieces = []
    for c in e:
        if tag(c) in ('list', 'table', 'q') and _blockish(c):
            pieces.append(('p', cur))
            pieces.append(('blk', c))
            cur = ET.Element(TEI + 'p')
            cur.text = c.tail
        else:
            cur.append(c)
    pieces.append(('p', cur))
    for k, el in pieces:
        if k == 'p':
            txt = r.text(el)
            if txt:
                out.append(('p', txt))
        else:
            tail, el.tail = el.tail, None
            block(r, el, out, depth)
            el.tail = tail
    return out


def em(s):
    """*斜体* → <em>（只用于不交给 kramdown 的 HTML 块，如表格单元格）。"""
    return re.sub(r'\*([^*]+)\*', r'<em>\1</em>', s)


def table_html(r, e):
    P = r.P
    rows = []
    for c in e:
        k = tag(c)
        if k == 'head':
            rows.append(f'<caption>{em(r.text(c))}</caption>')
        elif k == 'pb':
            x = r.pb(c)
            if x:
                rows.append(f'<tr class="{P}-pbrow"><td colspan="9">{x}</td></tr>')
        elif k == 'row':
            cells = []
            for cell in c:
                txt = em(r.text(cell))
                th = cell.get('role') == 'label' or c.get('role') == 'label'
                # 单元格不带 markdown="1"：几百格各自递归交给 kramdown，jekyll serve 的子线程栈会溢出
                # （巴洛卷首要目 18 张表、四百行实测 SystemStackError）；斜体在这里直接写成 <em>
                cells.append(f'<{"th" if th else "td"}>{txt}</{"th" if th else "td"}>')
            rows.append('<tr>' + ''.join(cells) + '</tr>')
        else:
            raise ValueError(f'table 下未处理 <{k}>')
    return f'<table class="{P}-table">\n' + '\n'.join(rows) + '\n</table>'


def to_md(P, paras):
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
            hashes, txt = item[1].split(' ', 1)
            out.append(f'{hashes} {pre}{txt}')
        elif k == 'text':                       # 节首经文框
            out.append(f'<div class="{P}-text" markdown="1">\n\n{pre}{item[1]}\n\n</div>')
        elif k == 'cls':
            out.append(f'<p class="{item[1]}" markdown="1">{pre}{item[2]}</p>')
        elif k == 'poem':
            lines = [f'<p class="{P}-l" markdown="1">{x}</p>' for x in item[1]]
            out.append(f'<div class="{P}-poem" markdown="1">\n\n{pre}' + '\n'.join(lines) + '\n\n</div>')
        elif k == 'float':
            out.append(f'<div class="{P}-float" markdown="1">\n\n{pre}' + to_md(P, item[1]) + '\n\n</div>')
        elif k == 'table':
            out.append((pre + '\n\n' if pre else '') + item[1])
        else:
            out.append(pre + item[1])
    if pending:
        out.append(''.join(pending))
    return '\n\n'.join(out)


def check(files):
    bad = 0
    for k, md in files.items():
        plain = re.sub(r'<[^>]+>', '', md)
        if plain.count('*') % 2:
            print(f'⚠️ {k}: 星号奇数')
            bad += 1
        if 'ſ' in md:
            print(f'⚠️ {k}: 残留 ſ')
            bad += 1
    return bad
