#!/usr/bin/env python3
"""leighton_raw/1peter/src/A47642.xml + A47643.xml（EEBO-TCP）→ en_chapters/*.md

    python3 scripts/extract_leighton.py            # 试跑，只报统计
    python3 scripts/extract_leighton.py --apply

雷登《彼得前书实用注释》原书两卷：
  A47642  卷一，York: J. White, 1693，第 1–2 章（Wing L1028A）
  A47643  卷二，London: B.G. for Sam. Keble, 1694，第 3–5 章

底本是 TCP 人工录入的 TEI，**不是 OCR**（old-book-ocr §2.2）。这里只做结构映射，不做字形修复；
TCP 标出的缺字原样留成可见记号，交给 manual_fixes.tsv 回填。骨架照搬 extract_hutcheson.py。

| TEI | 原书 | 产出 |
|---|---|---|
| <div type="verse"><head>Verse. 3, 4.</head><epigraph><q> | 每段讲解前排出的经文（卷一） | `<div class="lt-text">`：标签行 + 经文 |
| <epigraph><bibl>Verses 3, 4.</bibl><q> | 同上（卷二，标签在 bibl） | 同上 |
| <hi> | 斜体 | `*…*`；嵌套 = 反转 |
| <note place="margin"> | 页边旁注（卷二 163 条：出处、拉丁引语） | `<span class="lt-margin">` |
| <pb n="N"> | 印本页码（**两卷各自从 1 起**） | `<span class="lt-pb" id="p{卷}-{N}">` |
| <seg rend="decorInit"> | 花饰首字 | `<span class="lt-dropcap">` |
| <g ref="char:EOLhyphen"> | 行末断词 | 删（拼合） |
| <gap …> | 读不出的字母／词／一截／外文 | `•`×N / `〈◊〉` / `〈…〉` / `〈Greek〉` |
| <g ref="char:punc"> | 认不清的标点 | `▪` |
| <gap reason="duplicate"> | 缩微胶片重拍页 | 丢（连同紧挨着的 pb） |

长 ſ 归一成 s；u/v、i/j（Iesus、Vnto）等拼写照原样。经文框里印本自带的节号（`8. Whom…`）照排。
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'leighton_raw' / '1peter'
SRCS = [(1, RAW / 'src' / 'A47642.xml', (1, 2)), (2, RAW / 'src' / 'A47643.xml', (3, 4, 5))]
OUT = RAW / 'en_chapters'
TEI = '{http://www.tei-c.org/ns/1.0}'

GAP_LETTER, GAP_WORD, GAP_SPAN, GAP_FOREIGN, PUNC = '•', '〈◊〉', '〈…〉', '〈Greek〉', '▪'
NV = {1: 25, 2: 25, 3: 22, 4: 19, 5: 14}


def tag(e):
    return e.tag.replace(TEI, '')


class R:
    def __init__(self):
        self.vol = None
        self.pages = []
        self.gaps = {}
        self.held = []
        self.slug = None
        self.cur_page = None
        self.cur_facs = None
        self.gap_sites = []
        self.pb_seen = {}

    def site(self, kind, tok):
        self.gap_sites.append({'slug': self.slug, 'kind': kind, 'tok': tok,
                               'vol': self.vol, 'page': self.cur_page, 'facs': self.cur_facs})
        return tok

    def gap(self, e):
        reason = e.get('reason', '')
        ext = e.get('extent', '') or ''
        if reason == 'duplicate':
            return ''
        if reason == 'foreign':
            self.gaps['foreign'] = self.gaps.get('foreign', 0) + 1
            return self.site('foreign', GAP_FOREIGN)
        m = re.match(r'(\d+) letters?', ext)
        if m:
            self.gaps['letter'] = self.gaps.get('letter', 0) + int(m.group(1))
            return self.site('letter', GAP_LETTER * int(m.group(1)))
        if ext == '1 word':
            self.gaps['word'] = self.gaps.get('word', 0) + 1
            return self.site('word', GAP_WORD)
        if ext == '1 span':
            self.gaps['span'] = self.gaps.get('span', 0) + 1
            return self.site('span', GAP_SPAN)
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
                elif ref == 'char:punc':
                    out.append(self.site('punc', PUNC))
                else:
                    raise ValueError(f'未知 g ref={ref}')
            elif t == 'gap':
                out.append(self.gap(c))
            elif t == 'pb':
                out.append(self.hold(self.pb(c)))
            elif t == 'note':
                out.append(' ' + self.hold(self.note(c)) + ' ')
            elif t == 'seg' and c.get('rend') == 'decorInit':
                out.append(self.hold('<span class="lt-dropcap">' + norm(self, self.inline(c)) + '</span>'))
            elif t in ('seg', 'date', 'q', 'l', 'p', 'signed', 'label', 'desc', 'salute', 'bibl',
                       'list', 'item', 'dateline'):
                out.append(self.inline(c, italic))
            elif t == 'lb':
                out.append(' ')
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
        self.pages.append((self.vol, n, facs))
        # 两卷页码各自从 1 起；同卷内页码印重的，第二次起加后缀
        key = (self.vol, n)
        k = self.pb_seen.get(key, 0) + 1
        self.pb_seen[key] = k
        pid = f'p{self.vol}-{n}' + ('' if k == 1 else f'-{k}')
        return (f'<span class="lt-pb" id="{pid}" data-p="{n}" data-vol="{self.vol}" '
                f'data-facs="{facs}"></span>')

    def note(self, c):
        return f'<span class="lt-margin" markdown="1">{norm(self, self.inline(c))}</span>'


def norm(r, s):
    s = s.replace('ſ', 's')
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


def verse_numbers(label, n_attr, ch):
    """节号来源：卷一 div@n（"3,4"），卷二 bibl／head 文字（"Verses 19, 20, 21."）。"""
    src = n_attr or label
    nums = [int(x) for x in re.findall(r'\d+', src)]
    return [v for v in nums if 1 <= v <= NV[ch]]


def render_verse_div(r, d, ch):
    """一个讲解单元 → [('text', 标签, 经文, 节号表)] + 后续段落。"""
    paras = []
    head = d.find(TEI + 'head')
    label = block_text(r, head) if head is not None else ''
    for e in d:
        t = tag(e)
        if t == 'head':
            continue
        if t == 'pb':
            x = r.pb(e)
            if x:
                paras.append(('pb', x))
        elif t == 'epigraph':
            bib = [block_text(r, b) for b in e.iter(TEI + 'bibl')]
            lab = bib[0] if bib else label
            q = e.find(TEI + 'q')
            # 卷二 bibl 与 q 并列；q 自身内容即经文
            verse = block_text(r, q) if q is not None else ''
            nums = verse_numbers(lab, d.get('n'), ch)
            for v0, extra in COVERED_IN.items():
                if v0[0] == ch and v0[1] in nums:
                    nums = nums + extra
            paras.append(('text', lab, verse, nums))
        elif t == 'p':
            txt = block_text(r, e)
            if txt:
                paras.append(('p', txt))
        elif t in ('trailer', 'closer'):
            paras.append(('closer', block_text(r, e)))
        elif t == 'gap':
            r.gap(e)
        else:
            raise ValueError(f'讲解单元里未处理的元素 <{t}>')
    return paras


def render_div(r, div):
    paras = []
    for e in div:
        t = tag(e)
        if t == 'head':
            paras.append(('head', block_text(r, e)))
        elif t == 'pb':
            x = r.pb(e)
            if x:
                paras.append(('pb', x))
        elif t == 'p':
            txt = block_text(r, e)
            if txt:
                paras.append(('p', txt))
        elif t in ('opener',):
            paras.append(('salute', block_text(r, e)))
        elif t in ('closer', 'trailer', 'signed', 'dateline'):
            paras.append(('closer', block_text(r, e)))
        elif t == 'gap':
            r.gap(e)
        elif t == 'list':
            for it in e:
                if tag(it) == 'item':
                    paras.append(('p', block_text(r, it)))
        else:
            raise ValueError(f'块级未处理的元素 <{t}>')
    return paras


SEEN_V = set()

# 原书没有单列、但在相邻单元的讲解里讲了的节：锚点挂到那个单元（经文框不改，照印本）。
#   1:19 → 1:18 单元（讲解直接引 1:19 "As of a Lamb without blemish"）
#   2:8  → 2:7 单元（讲解引 2:8 "a stone of stumbling, and a rock of offence"）
# 2:19–20 原书没有讲，不挂（verse-nav 上就没有这两节）。
COVERED_IN = {(1, 18): [19], (2, 7): [8]}


def to_md(paras, ch=None):
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
        elif k == 'text':
            lab, verse, nums = item[1], item[2], item[3]
            ids = []
            for v in nums:
                if (ch, v) not in SEEN_V:          # 卷二 3:21 印了两次：锚点只给头一次
                    SEEN_V.add((ch, v))
                    ids.append(v)
            data = ' '.join(str(v) for v in ids)
            out.append(f'<div class="lt-text" data-verses="{data}" markdown="1">\n\n'
                       f'<p class="lt-vlabel" markdown="1">{pre}{lab}</p>\n'
                       f'<p class="lt-v" markdown="1">{verse}</p>\n\n</div>')
        elif k == 'salute':
            out.append(f'<p class="lt-salute" markdown="1">{pre}{item[1]}</p>')
        elif k == 'closer':
            out.append(f'<p class="lt-closer" markdown="1">{pre}{item[1]}</p>')
        else:
            out.append(pre + item[1])
    if pending:
        out.append(''.join(pending))
    return '\n\n'.join(out)


def mark_duplicates(root):
    """缩微胶片重拍页：<pb/> 紧跟 <gap reason="duplicate">，页码标记也不出。"""
    for par in root.iter():
        kids = list(par)
        for x, y in zip(kids, kids[1:]):
            if tag(x) == 'pb' and tag(y) == 'gap' and y.get('reason') == 'duplicate' \
                    and not (x.tail or '').strip():
                x.set('dup', '1')


FRONT_SLUG = {  # (卷, div type) → 篇名
    (1, 'title_page'): 'title1', (1, 'to_the_reader'): 'reader1',
    (2, 'imprimatur'): 'title2', (2, 'title_page'): 'title2', (2, 'dedication'): 'reader2',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    r = R()
    files = {}
    for vol, path, chs in SRCS:
        r.vol = vol
        root = ET.parse(path).getroot()
        mark_duplicates(root)
        chq = list(chs)
        for sec in root.find(TEI + 'text'):
            for div in sec.iter(TEI + 'div'):
                typ = div.get('type')
                if typ in ('verse', 'commentary'):
                    continue
                if typ == 'chapter':
                    ch = chq.pop(0)
                    r.slug = str(ch)
                    paras = []
                    for e in div:
                        t = tag(e)
                        if t == 'head':
                            paras.append(('head', block_text(r, e)))
                        elif t == 'pb':
                            x = r.pb(e)
                            if x:
                                paras.append(('pb', x))
                        elif t == 'div':
                            paras += render_verse_div(r, e, ch)
                        elif t in ('trailer', 'closer'):
                            paras.append(('closer', block_text(r, e)))
                        else:
                            raise ValueError(f'章下未处理 <{t}>')
                    files[str(ch)] = to_md(paras, ch)
                elif typ == 'publishers_advertisement':
                    print(f'  跳过卷{vol} 书商广告', file=sys.stderr)
                elif typ == 'errata':
                    r.slug = f'errata{vol}'
                    files[r.slug] = to_md(render_div(r, div))
                elif (vol, typ) in FRONT_SLUG:
                    r.slug = FRONT_SLUG[(vol, typ)]
                    md = to_md(render_div(r, div))
                    files[r.slug] = (files[r.slug] + '\n\n' + md) if r.slug in files else md
                else:
                    raise ValueError(f'卷{vol} 未处理的 div type={typ}')

    bad = 0
    for ch in range(1, 6):
        got = sorted({int(v) for v in re.findall(r'data-verses="([^"]*)"', files[str(ch)])
                      for v in []} | {int(x) for m in re.findall(r'data-verses="([^"]*)"', files[str(ch)])
                                       for x in m.split()})
        miss = [v for v in range(1, NV[ch] + 1) if v not in got]
        print(f'  ch{ch} 经文框 {files[str(ch)].count("lt-text")} 个，未单列的节 {miss}', file=sys.stderr)
    for k, md in files.items():
        plain = re.sub(r'<[^>]+>', '', md)
        if plain.count('*') % 2:
            print(f'⚠️ {k}: 星号奇数', file=sys.stderr); bad += 1
        if '|' in md:
            print(f'⚠️ {k}: 含竖线', file=sys.stderr); bad += 1
        if 'ſ' in md:
            print(f'⚠️ {k}: 残留 ſ', file=sys.stderr); bad += 1
    print(f'页码 {len(r.pages)}  缺字 {r.gaps}  缺字点 {len(r.gap_sites)}', file=sys.stderr)
    for k, md in files.items():
        print(f'  {k:9s} {len(md):8d} 字符', file=sys.stderr)
    if a.apply:
        OUT.mkdir(parents=True, exist_ok=True)
        for k, md in files.items():
            (OUT / f'{k}.md').write_text(md.strip() + '\n', encoding='utf-8')
        (RAW / 'pages.json').write_text(json.dumps(r.pages, indent=0) + '\n', encoding='utf-8')
        (RAW / 'gap_sites.json').write_text(json.dumps(r.gap_sites, ensure_ascii=False, indent=0) + '\n',
                                            encoding='utf-8')
        print(f'写入 {len(files)} 篇 → {OUT}', file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
