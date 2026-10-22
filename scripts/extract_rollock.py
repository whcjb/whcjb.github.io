#!/usr/bin/env python3
"""rollock_raw/thessalonians/src/A11010.xml（EEBO-TCP）→ en_chapters/<书>/*.md

    python3 scripts/extract_rollock.py            # 试跑，只报统计
    python3 scripts/extract_rollock.py --apply

罗洛克《帖撒罗尼迦前后书讲章》Edinburgh: Robert Charteris 1606（STC 21281）：
  帖前 献辞 + 致读者 + 提要 + 27 讲（印本页 1–346，原书页码误作 246）
  帖后 另有扉页与页码：扉页 + 提要 + 14 讲（印本页 1–173）

底本是 TCP 人工录入的 TEI，**不是 OCR**（old-book-ocr §2.2）。骨架照搬 extract_adams.py：
只做结构映射，缺字原样留记号，交给 rollock_common.py 按判读表回填。

| TEI | 原书 | 产出 |
|---|---|---|
| <div type="lecture" n> | 一讲 | 一页，页名 `<章>-<首节>` |
| <epigraph><bibl>…<q><p>… | 讲前排出的经文（逐节一段） | `<div class="rl-text">` 标签 + 逐节 |
| <head> | 讲题 | `## ` |
| <hi> | 斜体 | `*…*`；嵌套 = 反转 |
| <note place="margin"> | 页边旁注（321 条：分段提要、出处） | `<span class="rl-margin">` |
| <pb n="N"> | 印本页码 | `<span class="rl-pb" id="pN">` |
| <seg rend="decorInit"> | 花饰首字 | `<span class="rl-dropcap">` |
| <closer> / <trailer> | 讲末 AMEN. / FINIS. | `<p class="rl-closer">` |
| <gap …> | 读不出的字母／词／一截／外文 | `•`×N / `〈◊〉` / `〈…〉` / `〈Greek〉` |
| <g ref="char:punc"> | 认不清的标点 | `▪` |

长 ſ 归一成 s；u/v、i/j 等拼写照原样。
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'rollock_raw' / 'thessalonians'
SRC = RAW / 'src' / 'A11010.xml'
OUT = RAW / 'en_chapters'
TEI = '{http://www.tei-c.org/ns/1.0}'
BOOKS = ('1thessalonians', '2thessalonians')

GAP_LETTER, GAP_WORD, GAP_SPAN, GAP_FOREIGN, PUNC = '•', '〈◊〉', '〈…〉', '〈Greek〉', '▪'
NV = {'1thessalonians': {1: 10, 2: 20, 3: 13, 4: 18, 5: 28},
      '2thessalonians': {1: 12, 2: 17, 3: 18}}
# 讲前经文标签的节号录入有误、按讲内逐节经文改的：帖后第 5 讲 `verſ. 34.` 实为 3–4 节
BIBL_FIX = {('2thessalonians', 5): [(2, [3, 4])]}


def tag(e):
    return e.tag.replace(TEI, '')


class R:
    def __init__(self):
        self.pages = []
        self.gaps = {}
        self.held = []
        self.book = None
        self.pb_seen = {}

    def gap(self, e):
        reason = e.get('reason', '')
        ext = e.get('extent', '') or ''
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
                else:                        # cmbAbbrStroke：照录字形
                    out.append(c.text or '')
            elif t == 'gap':
                out.append(self.gap(c))
            elif t == 'pb':
                out.append(self.hold(self.pb(c)))
            elif t == 'note':
                out.append(' ' + self.hold(self.note(c)) + ' ')
            elif t == 'seg' and c.get('rend') == 'decorInit':
                out.append(self.hold('<span class="rl-dropcap">' + norm(self, self.inline(c)) + '</span>'))
            elif t in ('seg', 'q', 'p', 'signed', 'bibl', 'head', 'trailer'):
                out.append(self.inline(c, italic))
            elif t in ('lb',):
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
        if not n:      # 无页码的页（扉页、献辞）：只留叶号，供证人定位
            return f'<span class="rl-pb" data-facs="{facs}"></span>'
        self.pages.append((self.book, n, facs))
        key = (self.book, n)
        k = self.pb_seen.get(key, 0) + 1
        self.pb_seen[key] = k
        pid = f'p{n}' + ('' if k == 1 else f'-{k}')
        return (f'<span class="rl-pb" id="{pid}" data-p="{n}" data-facs="{facs}" '
                f'title="Page {n} of the 1606 edition begins here (原书第 {n} 页起)"></span>')

    def note(self, c):
        return f'<span class="rl-margin" markdown="1">{norm(self, self.inline(c))}</span>'


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
    elif t in ('closer', 'trailer'):
        paras.append(('closer', block_text(r, e)))
    elif t == 'figure':
        pass
    elif t == 'epigraph':
        for q in e:
            if tag(q) == 'pb':
                x = r.pb(q)
                if x:
                    paras.append(('pb', x))
            elif tag(q) == 'bibl':
                paras.append(('bibl', block_text(r, q)))
            elif tag(q) == 'q':
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
                raise ValueError(f'epigraph 下未处理 <{tag(q)}>')
    else:
        raise ValueError(f'块级未处理的元素 <{t}>')


def to_md(paras):
    """段落元组 → markdown。页码锚点挂进下一段行内（Perkins 踩过：与块级 div 同行会让 div 失效）。
    一讲开头的 bibl + verses 合成一个经文框。"""
    out, pending = [], []
    i = 0
    while i < len(paras):
        item = paras[i]
        k = item[0]
        if k == 'pb':
            pending.append(item[1])
            i += 1
            continue
        pre = ''.join(pending)
        pending = []
        if k == 'head':
            out.append(f'## {pre}{item[1]}')
        elif k == 'bibl':
            vs = paras[i + 1][1] if i + 1 < len(paras) and paras[i + 1][0] == 'verses' else []
            if vs:
                i += 1
            lines, hold = [], ''
            for v in vs:
                if v.startswith('<span class="rl-pb"'):      # 经文里换页：挂到下一节行首
                    hold += v
                    continue
                lines.append(f'<p class="rl-v" markdown="1">{hold}{v}</p>')
                hold = ''
            if hold:
                lines.append(hold)
            out.append('<div class="rl-text" markdown="1">\n\n'
                       f'<p class="rl-vlabel" markdown="1">{pre}{item[1]}</p>\n' + '\n'.join(lines) + '\n\n</div>')
        elif k == 'verses':
            raise ValueError('经文段前面没有 bibl')
        elif k == 'closer':
            out.append(f'<p class="rl-closer" markdown="1">{pre}{item[1]}</p>')
        else:
            out.append(pre + item[1])
        i += 1
    if pending:
        out.append(''.join(pending))
    return '\n\n'.join(out)


def lecture_range(book, n, div):
    """讲前经文标签 → [(章, [节…])…]。"""
    if (book, n) in BIBL_FIX:
        return BIBL_FIX[(book, n)]
    res = []
    for e in div.findall(TEI + 'epigraph'):
        b = re.sub(r'\s+', ' ', ''.join(e.find(TEI + 'bibl').itertext()))
        m = re.search(r'CHAP\.\s*(\d+)\W+ver[sſ]\W*(.*)$', b, re.I)
        if not m:
            raise ValueError(f'{book} 第 {n} 讲经文标签认不出：{b}')
        vs = [int(x) for x in re.findall(r'\d+', m.group(2))]
        res.append((int(m.group(1)), vs))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    root = ET.parse(SRC).getroot()
    text = root.find(TEI + 'text')
    r = R()
    files = {b: {} for b in BOOKS}
    order = {b: [] for b in BOOKS}
    lectures = []

    def put(slug, paras):
        md = to_md(paras)
        f = files[r.book]
        if slug in f:
            f[slug] += '\n\n' + md
        else:
            f[slug] = md
            order[r.book].append(slug)

    def simple(slug, div):
        paras = []
        for c in div:
            render_block(r, c, paras)
        put(slug, paras)

    r.book = BOOKS[0]
    for div in text.find(TEI + 'front'):
        typ = div.get('type')
        slug = {'title_page': 'title', 'dedication': 'dedication', 'to_the_reader': 'to-the-reader'}[typ]
        simple(slug, div)
    for bi, part in enumerate(text.find(TEI + 'body')):
        r.book = BOOKS[bi]
        for div in part:
            typ = div.get('type')
            if typ == 'title_page':
                simple('title', div)
            elif typ == 'argument':
                simple('argument', div)
            elif typ == 'lecture':
                n = int(div.get('n'))
                rng = lecture_range(r.book, n, div)
                slug = f'{rng[0][0]}-{rng[0][1][0]}'
                lectures.append(dict(book=r.book, n=n, slug=slug,
                                     start=[rng[0][0], rng[0][1][0]], end=[rng[-1][0], rng[-1][1][-1]],
                                     boxes=[[c, v[0], v[-1]] for c, v in rng]))
                simple(slug, div)
            else:
                raise ValueError(f'{r.book} 未处理的 div type={typ}')

    bad = 0
    for b in BOOKS:
        for k, md in files[b].items():
            plain = re.sub(r'<[^>]+>', '', md)
            if plain.count('*') % 2:
                print(f'⚠️ {b}/{k}: 星号奇数', file=sys.stderr); bad += 1
            if 'ſ' in md:
                print(f'⚠️ {b}/{k}: 残留 ſ', file=sys.stderr); bad += 1
        print(f'{b}: 篇 {len(files[b])}  ' + ' '.join(order[b]), file=sys.stderr)
    # 讲与讲的节段要首尾相接（允许同一节跨两讲）
    for x, y in zip(lectures, lectures[1:]):
        if x['book'] != y['book']:
            continue
        nv = NV[x['book']]
        ec, ev = x['end']
        sc, sv = y['start']
        nxt = (ec, ev + 1) if ev < nv[ec] else (ec + 1, 1)
        if (sc, sv) not in ((ec, ev), nxt):
            print(f'⚠️ {x["book"]} 第 {x["n"]}→{y["n"]} 讲节段不接：{x["end"]} → {y["start"]}', file=sys.stderr)
            bad += 1
    print(f'页码 {len(r.pages)}  缺字 {r.gaps}', file=sys.stderr)
    if a.apply:
        for b in BOOKS:
            (OUT / b).mkdir(parents=True, exist_ok=True)
            for k, md in files[b].items():
                (OUT / b / f'{k}.md').write_text(md.strip() + '\n', encoding='utf-8')
        (RAW / 'pages.json').write_text(json.dumps(r.pages, indent=0) + '\n', encoding='utf-8')
        (RAW / 'order.json').write_text(json.dumps(order, indent=1) + '\n', encoding='utf-8')
        (RAW / 'lectures.json').write_text(json.dumps(lectures, indent=1) + '\n', encoding='utf-8')
        print(f'写入 → {OUT}', file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
