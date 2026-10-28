#!/usr/bin/env python3
"""taylor_raw/titus/src/A13535.xml（EEBO-TCP）→ en_chapters/*.md

    python3 scripts/extract_taylor.py            # 试跑，只报统计
    python3 scripts/extract_taylor.py --apply

托马斯·泰勒《提多书注释》Cambridge: Cantrell Legge for L. Greene 1612（STC 23825），印本页 1–751。
底本是 TCP 人工录入的 TEI，**不是 OCR**。骨架照搬 extract_rollock.py：只做结构映射，缺字原样留记号，
交给 taylor_common.py 按判读表回填。

原书没有分讲，按经文一段一段讲：每段前排出要讲的经文（「Vers. 5. For this cause …」），段内再逐语
（lemma，「Not angrie]」）解说。发布按段一页，页名 `<章>-<首节>`；每章另出一页目录 `<章>.md`。

| TEI | 原书 | 产出 |
|---|---|---|
| ch1 <epigraph><q><p n> / ch2–3 <head>CHAP. II. 经文… | 章首经文 | `## CHAP. I.` + `<div class="ty-text">` |
| <q> 以「Vers. N.」起头 | 段前经文（一节或几节） | `<div class="ty-text">`，**分页点** |
| <q> 以「]」收尾 | 逐语解说的引语 | `<p class="ty-lemma">` |
| <p> 以「vers. N.」起头 | 段前经文已在上一段框里，新一节的解说从这里起 | 分页点 |
| <hi> | 斜体 | `*…*`；嵌套 = 反转 |
| <note place="margin"> | 页边旁注（出处、要点） | `<span class="ty-margin">` |
| <pb n="N"> | 印本页码 | `<span class="ty-pb" id="pN">` |
| <seg rend="decorInit"> | 花饰首字 | `<span class="ty-dropcap">` |
| <gap …> | 读不出的字母／词／一截／外文 | `•`×N / `〈◊〉` / `〈…〉` / `〈Greek〉` |
| <g ref="char:punc"> | 认不清的标点 | `▪` |
| <gap reason="duplicate"> | 缩微胶片重拍页 | 丢 |

长 ſ 归一成 s；u/v、i/j 等拼写照原样。
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'taylor_raw' / 'titus'
SRC = RAW / 'src' / 'A13535.xml'
OUT = RAW / 'en_chapters'
TEI = '{http://www.tei-c.org/ns/1.0}'

GAP_LETTER, GAP_WORD, GAP_SPAN, GAP_FOREIGN, PUNC = '•', '〈◊〉', '〈…〉', '〈Greek〉', '▪'
NV = {1: 16, 2: 15, 3: 15}
RE_LABEL = re.compile(r'^\W*(?:v|vers?|verse)\W*(\d+)\b', re.I)

FRONT = {'title_page': 'title', 'dedication': 'dedication', 'to_the_reader': 'to-the-reader'}
BACK = {'table_of_doctrines': 'doctrines', 'table_of_observations': 'observations',
        'table_of_questions': 'questions', 'errata': 'errata'}


def tag(e):
    return e.tag.replace(TEI, '')


def text_of(e):
    return re.sub(r'\s+', ' ', ''.join(e.itertext())).strip()


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
                out.append(self.hold('<span class="ty-dropcap">' + norm(self, self.inline(c)) + '</span>'))
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
        if not n:      # 无页码的页（扉页、献辞、表）：只留叶号，供证人定位
            return f'<span class="ty-pb" data-facs="{facs}"></span>'
        self.pages.append((n, facs))
        k = self.pb_seen.get(n, 0) + 1
        self.pb_seen[n] = k
        pid = f'p{n}' + ('' if k == 1 else f'-{k}')
        return (f'<span class="ty-pb" id="{pid}" data-p="{n}" data-facs="{facs}" '
                f'title="Page {n} of the 1612 edition begins here (原书第 {n} 页起)"></span>')

    def note(self, c):
        return f'<span class="ty-margin" markdown="1">{norm(self, self.inline(c))}</span>'


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


def is_label_q(e):
    return tag(e) == 'q' and RE_LABEL.match(text_of(e)) is not None


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
        # 段里嵌的 <list>：列表前的引导句、各条各成一段
        if e.find(TEI + 'list') is not None:
            paras.extend(split_list_p(r, e))
            return
        txt = block_text(r, e)
        if txt:
            paras.append(('p', txt))
    elif t == 'q':
        kids = [c for c in e if tag(c) == 'p']
        bib = e.find(TEI + 'bibl')
        if bib is not None:             # 扉页题辞：出处 + 引文
            lab = block_text(r, bib)
            e.remove(bib)
            paras.append(('quote', f'{block_text(r, e)} {lab}'))
            return
        if is_label_q(e) or (kids and all(tag(c) in ('p', 'pb') for c in e) and len(kids) > 1
                             and RE_LABEL.match(text_of(kids[0]))):
            vs = []
            if kids:
                for c in e:
                    if tag(c) == 'p':
                        vs.append(block_text(r, c))
                    elif tag(c) == 'pb':
                        x = r.pb(c)
                        if x:
                            vs.append(x)
                    else:
                        raise ValueError(f'经文 q 下未处理 <{tag(c)}>')
            else:
                vs.append(block_text(r, e))
            paras.append(('verses', vs))
        elif kids:                      # 引语 + 下一节经文（3:1 末「Readie …]」+ 旁注 vers. 2 + 经文）
            for c in e:
                if tag(c) == 'p':
                    txt = block_text(r, c)
                    paras.append(('lemma' if txt.rstrip('*').endswith(']') else 'verses1', txt))
                elif tag(c) == 'pb':
                    x = r.pb(c)
                    if x:
                        paras.append(('pb', x))
                else:
                    raise ValueError(f'q 下未处理 <{tag(c)}>')
        else:
            txt = block_text(r, e)
            if txt:
                paras.append(('lemma', txt))
    elif t in ('closer', 'trailer'):
        paras.append(('closer', block_text(r, e)))
    elif t == 'list':
        for it in e:
            if tag(it) in ('item', 'head'):
                txt = block_text(r, it)
                if txt:
                    paras.append(('item', txt))
            elif tag(it) == 'pb':
                x = r.pb(it)
                if x:
                    paras.append(('pb', x))
            else:
                raise ValueError(f'list 下未处理 <{tag(it)}>')
    elif t == 'figure':
        pass
    elif t == 'epigraph':
        for q in e:
            if tag(q) != 'q':
                raise ValueError(f'epigraph 下未处理 <{tag(q)}>')
            vs = []
            for p in q:
                if tag(p) == 'p':
                    vs.append(block_text(r, p))
                elif tag(p) == 'pb':
                    x = r.pb(p)
                    if x:
                        vs.append(x)
                else:
                    raise ValueError(f'epigraph/q 下未处理 <{tag(p)}>')
            paras.append(('verses', vs))
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
        elif k in ('verses', 'verses1'):
            vs = item[1] if k == 'verses' else [item[1]]
            lines, hold = [], pre
            for v in vs:
                if v.startswith('<span class="ty-pb"') and v.endswith('</span>') and v.count('<span') == 1:
                    hold += v
                    continue
                lines.append(f'<p class="ty-v" markdown="1">{hold}{v}</p>')
                hold = ''
            if hold:
                lines.append(hold)
            out.append('<div class="ty-text" markdown="1">\n\n' + '\n'.join(lines) + '\n\n</div>')
        elif k == 'lemma':
            out.append(f'<p class="ty-lemma" markdown="1">{pre}{item[1]}</p>')
        elif k == 'quote':
            out.append(f'<p class="ty-quote" markdown="1">{pre}{item[1]}</p>')
        elif k == 'item':
            out.append(f'<p class="ty-item" markdown="1">{pre}{item[1]}</p>')
        elif k == 'closer':
            out.append(f'<p class="ty-closer" markdown="1">{pre}{item[1]}</p>')
        else:
            out.append(pre + item[1])
    if pending:
        out.append(''.join(pending))
    return '\n\n'.join(out)


def chapter_head(r, head, paras):
    """ch2/ch3 的 <head>：CHAP. II. + 章首经文（内嵌 <hi>2</hi> 节号）。"""
    txt = block_text(r, head)
    m = re.match(r'^(CHAP\. *[IVX]+\.)\s*(.*)$', txt)
    if not m:
        raise ValueError(f'章标题认不出：{txt[:60]}')
    paras.append(('head', m.group(1)))
    body = m.group(2)
    if body:
        # 以斜体节号 *2* 断行
        vs = re.split(r' (?=\*\d+\*)', body)
        paras.append(('verses', vs))


def label_of(e):
    """分页点：返回节号；不是分页点返回 None。"""
    t = tag(e)
    if t == 'q':
        m = RE_LABEL.match(text_of(e))
        return int(m.group(1)) if m else None
    if t == 'p':
        m = RE_LABEL.match(text_of(e))
        if m and re.match(r'^\W*vers?\W', text_of(e), re.I):
            return int(m.group(1))
    return None


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
    for part in body:
        if tag(part) == 'head':          # 正文总标题（重复书名）：挂到 argument 页首
            put('argument', [('head', block_text(r, part))])
            continue
        for c in part:
            if tag(c) == 'div' and c.get('type') == 'chapter':
                ch = int(c.get('n'))
                cur, paras, carry = None, [], []
                for x in c:
                    if tag(x) == 'head':
                        dst = paras if cur is not None else carry
                        if ch == 1:
                            dst.append(('head', block_text(r, x)))
                        else:
                            chapter_head(r, x, dst)
                        continue
                    v = label_of(x)
                    if cur is None:
                        cur = 1
                        paras = carry
                        carry = []
                    if v is not None and v > cur:
                        put(f'{ch}-{cur}', paras)
                        sections.append([ch, cur])
                        cur, paras = v, []
                    render_block(r, x, paras)
                put(f'{ch}-{cur}', paras)
                sections.append([ch, cur])
            else:
                paras = []
                render_block(r, c, paras)
                put('argument', paras)

    for div in text.find(TEI + 'back'):
        simple(BACK[div.get('type')], div)

    # 每段的节段：首节到下一段首节 − 1
    secs = []
    for i, (ch, v) in enumerate(sections):
        nxt = sections[i + 1] if i + 1 < len(sections) else None
        end = nxt[1] - 1 if nxt and nxt[0] == ch else NV[ch]
        secs.append(dict(slug=f'{ch}-{v}', ch=ch, v1=v, v2=end))

    bad = 0
    for k, md in files.items():
        plain = re.sub(r'<[^>]+>', '', md)
        if plain.count('*') % 2:
            print(f'⚠️ {k}: 星号奇数', file=sys.stderr); bad += 1
        if 'ſ' in md:
            print(f'⚠️ {k}: 残留 ſ', file=sys.stderr); bad += 1
    print('  ' + ' '.join(f'{k}({len(files[k]) // 1000}k)' for k in order), file=sys.stderr)
    print(f'页码 {len(r.pages)}  缺字 {r.gaps}', file=sys.stderr)
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
