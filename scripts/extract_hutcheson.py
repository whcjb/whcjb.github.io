#!/usr/bin/env python3
"""hutcheson_raw/john/src/A45241.xml（EEBO-TCP）→ en_chapters/*.md

    python3 scripts/extract_hutcheson.py            # 试跑，只报统计
    python3 scripts/extract_hutcheson.py --apply

底本是 TCP 人工录入的 TEI（Phase 2，CC0），**不是 OCR**（old-book-ocr §2.2：
有可信文本层就不要重 OCR）。这里只做结构映射，不做字形修复；TCP 标出的缺字
（<gap>）原样留成可见记号，交给 manual_fixes.tsv 按影像回填。

骨架照搬 extract_perkins.py，差别只在本书的 TEI 形态：

| TEI | 原书 | 产出 |
|---|---|---|
| <div type="verse"><epigraph><q><bibl>Ver. N.</bibl> 经文 | 每段讲解前排出的经文（可连列几节） | `<div class="hc-text">`，每节一段，节号加粗 |
| <hi> | 斜体 | `*…*`；嵌套 = 反转 |
| <note place="margin"> | 页边旁注（只在卷首 Calamy 序里） | `<span class="hc-margin">` |
| <pb n="N"> | 印本页码 | `<span class="hc-pb" id="pN">` |
| <seg rend="decorInit"> | 花饰首字 | `<span class="hc-dropcap">` |
| <g ref="char:EOLhyphen"> | 行末断词 | 删（拼合） |
| <g ref="char:V">Ʋ</g> | 小型大写式的 U 字模（`HƲTCHESON`、`ƲPON`） | `U` |
| <gap reason="illegible" extent="N letter(s)"> | 读不出的字母 | `•`×N |
| <gap … "1 word"> / "1 span" | 读不出的词／一截 | `〈◊〉` / `〈…〉` |
| <gap reason="foreign"> | 希腊活字（TCP 不录） | `〈Greek〉` |
| <g ref="char:punc"> | 认不清的标点 | `▪` |
| <gap reason="duplicate"> | 缩微胶片重拍页 | 丢 |

**长 ſ 归一成 s**：ſ 是字形不是拼写（同一个字母的词中形），归一不改动原书
拼写；u/v、i/j、`doth`、`then`(=than) 等拼写一概照原样。Perkins 那份 TCP
本来就没有 ſ，所以本书是第一次碰到这个决定，记在 PROVENANCE.md。
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'hutcheson_raw' / 'john'
SRC = RAW / 'src' / 'A45241.xml'
OUT = RAW / 'en_chapters'
TEI = '{http://www.tei-c.org/ns/1.0}'

GAP_LETTER = '•'
GAP_WORD = '〈◊〉'
GAP_SPAN = '〈…〉'
GAP_FOREIGN = '〈Greek〉'
PUNC = '▪'

# 和合本／KJV 每章节数，抽取后逐章核对 bibl 节号是否连续覆盖（Step 1 实测全齐）
NV = {1: 51, 2: 25, 3: 36, 4: 54, 5: 47, 6: 71, 7: 53, 8: 59, 9: 41, 10: 42, 11: 57,
      12: 50, 13: 38, 14: 31, 15: 27, 16: 33, 17: 26, 18: 40, 19: 42, 20: 31, 21: 25}

# 节号写法：`Verse 1.` `Ver. 2.` `Ver 1.` `Ver, 4.` `Verse. 1.` `33.`
RE_BIBL = re.compile(r'^\s*(?:Ver(?:se)?[.,]?\s*)?(\d{1,2})\s*[.,]?\s*$', re.I)


def tag(e):
    return e.tag.replace(TEI, '')


class R:
    """把一棵 TEI 子树渲成 markdown 行内文本。"""

    def __init__(self):
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
                               'page': self.cur_page, 'facs': self.cur_facs})
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
        """斜体用控制符记状态切换：\x01 开、\x02 关；HTML 片段存成 \x03n\x03 占位，
        最后由 norm() 统一出星号（§0.4 / old-book-ocr §4.4）。"""
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
                    # 断点前的 XML 排版换行是排版空白不是词间空格，拼合时一并去掉
                    while out and out[-1].strip() == '' and '\n' in out[-1]:
                        out.pop()
                    if out and out[-1].endswith(('\n', ' ', '\t')) and '\n' in out[-1]:
                        out[-1] = out[-1].rstrip()
                elif ref == 'char:punc':
                    out.append(self.site('punc', PUNC))
                elif ref == 'char:V':
                    out.append('U')
                else:
                    raise ValueError(f'未知 g ref={ref}')
            elif t == 'gap':
                out.append(self.gap(c))
            elif t == 'pb':
                out.append(self.hold(self.pb(c)))
            elif t == 'note':
                out.append(' ' + self.hold(self.note(c)) + ' ')
            elif t == 'seg' and c.get('rend') == 'decorInit':
                out.append(self.hold('<span class="hc-dropcap">'
                                     + norm(self, self.inline(c)) + '</span>'))
            elif t in ('seg', 'date', 'q', 'l', 'p', 'signed', 'label', 'desc', 'salute'):
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
        self.pages.append((n, facs))
        # 原书页码印错（150 之后印了两个 152、没有 151；全书缺 89/151/161/322/327）：
        # 显示照印本，锚点 id 第二次起加后缀，否则页内跳转跳错
        k = self.pb_seen.get(n, 0) + 1
        self.pb_seen[n] = k
        pid = f'p{n}' if k == 1 else f'p{n}-{k}'
        return f'<span class="hc-pb" id="{pid}" data-p="{n}" data-facs="{facs}"></span>'

    def note(self, c):
        body = norm(self, self.inline(c))
        return f'<span class="hc-margin" markdown="1">{body}</span>'


def norm(r, s):
    """控制符流 → markdown。相邻同体合并，空白落在星号外侧，空强调丢掉；
    HTML 占位视为正体分隔。ſ → s 也在这里做（唯一出口）。"""
    s = s.replace('ſ', 's')
    s = re.sub(r'\s+', ' ', s)
    runs = []
    depth = 0
    buf = []

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
    s = ''.join(out)
    s = re.sub(r' {2,}', ' ', s).strip()
    return s


def block_text(r, e):
    return norm(r, r.inline(e))


def render_epigraph(r, ep, ch):
    """一个 epigraph → [(节号, 经文)]。<q> 里每个 <bibl> 起一节。"""
    verses = []
    for q in ep:
        if tag(q) == 'pb':
            x = r.pb(q)
            if x:
                verses.append((None, x))
            continue
        if tag(q) != 'q':
            raise ValueError(f'epigraph 下未处理的元素 <{tag(q)}>')
        # 把 q 按 bibl 切开：每个 bibl 起一个新的伪元素，后续兄弟节点归它。
        # 连列几节时一节一个 <p>（q > p > bibl），递归进去照样切。
        segs = []           # [(节号, Element)]

        def split(box):
            if (box.text or '').strip():
                # 续列上一单元讲过的半节（13:4 后半 `— and laid aside his garments…`）：
                # 原书就这样排，照排；节号 0 = 不带号、不出锚点
                if segs:
                    raise ValueError(f'ch{ch} 经文中段有无号文字：{box.text.strip()[:60]!r}')
                x = ET.Element('x')
                x.text = box.text
                segs.append((0, x))
            for c in box:
                if tag(c) == 'p':
                    split(c)
                    if (c.tail or '').strip():
                        raise ValueError(f'ch{ch} 经文段之间有文字：{c.tail.strip()[:60]!r}')
                elif tag(c) == 'bibl':
                    lab = ' '.join(''.join(c.itertext()).split()).replace('ſ', 's')
                    m = RE_BIBL.match(lab)
                    if not m:
                        raise ValueError(f'ch{ch} 认不出的节号 {lab!r}')
                    x = ET.Element('x')
                    x.text = c.tail or ''
                    segs.append((int(m.group(1)), x))
                else:
                    if not segs:
                        raise ValueError(f'ch{ch} 经文在节号前有元素 <{tag(c)}>')
                    segs[-1][1].append(c)
        split(q)
        for v, x in segs:
            verses.append((v, block_text(r, x)))
    return verses


def render_div(r, div, ch=None):
    paras = []
    for e in div:
        t = tag(e)
        if t == 'head':
            paras.append(('head', block_text(r, e)))
        elif t == 'pb':
            x = r.pb(e)
            if x:
                paras.append(('pb', x))
        elif t == 'epigraph':
            paras.append(('verses', render_epigraph(r, e, ch)))
        elif t == 'p':
            txt = block_text(r, e)
            if txt:
                paras.append(('p', txt))
        elif t in ('opener',):
            paras.append(('salute', block_text(r, e)))
        elif t in ('closer', 'trailer', 'signed'):
            paras.append(('closer', block_text(r, e)))
        elif t == 'gap':
            r.gap(e)      # 只有 duplicate 会落在块级
        elif t == 'div':
            sub = render_div(r, e, ch)
            typ = e.get('type')
            paras.append(('div', typ, sub))
        elif t == 'list':
            for it in e:
                if tag(it) == 'item':
                    paras.append(('p', block_text(r, it)))
                elif tag(it) == 'pb':
                    x = r.pb(it)
                    if x:
                        paras.append(('pb', x))
                elif tag(it) == 'head':
                    paras.append(('head', block_text(r, it)))
        else:
            raise ValueError(f'块级未处理的元素 <{t}>')
    return paras


SEEN_V = set()

# 经文框里没排出来、但讲解里讲了的节（`From verse 5. Learn`）。是**原书漏排**：
# 书末勘误表自己说 `mistakes in printing the verses of the Text Ex. gr. ch. 7.
# v 2, 3, 4. with which the fifth verse should also be printed`。照印本不补（§0.0），
# 勘误表原样在卷末。
MISSING_V = {(7, 5)}


def to_md(paras, ch=None, pending=None):
    """段落元组 → markdown。

    两段之间的页码锚点挂进**下一段的行内**：与块级 <div> 写在同一行会让
    kramdown 把整行当段落、div 不再是块（Perkins 踩过）。"""
    out = []
    pending_pb = list(pending or [])
    for item in paras:
        k = item[0]
        if k == 'pb':
            pending_pb.append(item[1])
            continue
        pre = ''.join(pending_pb)
        pending_pb = []
        if k == 'head':
            out.append(f'## {pre}{item[1]}')
        elif k == 'div':
            typ, sub = item[1], item[2]
            inner = to_md(sub, ch, [pre] if pre else None)
            if typ == 'argument':
                out.append(f'<div class="hc-argument" markdown="1">\n\n{inner}\n\n</div>')
            else:
                out.append(inner)
        elif k == 'verses':
            lines = []
            for v, txt in item[1]:
                if v is None:          # 经文框里的页码：挂到下一节
                    pre += txt
                    continue
                if v == 0:             # 续列的半节：不带号、不出锚点
                    lines.append(f'<p class="hc-v hc-v-cont" markdown="1">{pre}{txt}</p>')
                    pre = ''
                    continue
                # 原书把一节拆成两半分段讲时，两半都印节号（8:6、8:41、19:16、21:7）：
                # 照印本显示，锚点只给头一次，否则 verse-nav 跳到重复 id
                key = (ch, v)
                vid = '' if key in SEEN_V else f' id="v{v}"'
                SEEN_V.add(key)
                cls = 'hc-v' if vid else 'hc-v hc-v-cont'
                lines.append(f'<p class="{cls}"{vid} markdown="1">{pre}**{v}** {txt}</p>')
                pre = ''
            body = '\n'.join(lines)
            out.append(f'<div class="hc-text" markdown="1">\n\n{body}\n\n</div>')
        elif k == 'salute':
            out.append(f'<p class="hc-salute" markdown="1">{pre}{item[1]}</p>')
        elif k == 'closer':
            out.append(f'<p class="hc-closer" markdown="1">{pre}{item[1]}</p>')
        else:
            out.append(pre + item[1])
    if pending_pb:
        out.append(''.join(pending_pb))
    return '\n\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    root = ET.parse(SRC).getroot()
    # 缩微胶片重拍页：<pb/> 紧跟 <gap reason="duplicate">，那一页的字 TCP 没录
    # （正本已在前面），页码标记也不出——否则同一页码出两次（142/143 等 14 处）
    for par in root.iter():
        kids = list(par)
        for x, y in zip(kids, kids[1:]):
            if tag(x) == 'pb' and tag(y) == 'gap' and y.get('reason') == 'duplicate' \
                    and not (x.tail or '').strip():
                x.set('dup', '1')
    text = root.find(TEI + 'text')
    r = R()
    files = {}
    front = []
    for sec in text:
        st = tag(sec)
        for div in sec:
            if tag(div) == 'pb':
                r.pb(div)
                continue
            if tag(div) != 'div':
                raise ValueError(f'{st} 下未处理的元素 <{tag(div)}>')
            typ = div.get('type')
            if st == 'front':
                # 书名页 / Calamy 序 / 献辞 / 作者致读者
                slug = {'title_page': 'title', 'dedication': 'dedication'}.get(typ)
                if typ == 'to_the_reader':
                    slug = 'calamy' if not any(f[0] == 'calamy' for f in front) else 'reader'
                r.slug = slug
                front.append((slug, to_md(render_div(r, div))))
            elif st == 'body':
                # <div type="text">：书名 head + argument + 21 章
                for e in div:
                    t = tag(e)
                    if t == 'pb':
                        r.pb(e)
                    elif t == 'head':
                        files['_booktitle'] = block_text(r, e)
                    elif t == 'div' and e.get('type') == 'argument':
                        r.slug = 'argument'
                        files['argument'] = to_md(render_div(r, e))
                    elif t == 'div' and e.get('type') == 'chapter':
                        n = int(e.get('n'))
                        r.slug = str(n)
                        files[str(n)] = to_md(render_div(r, e, n), n)
                    elif t == 'trailer':
                        files[str(21)] += '\n\n<p class="hc-closer" markdown="1">' + block_text(r, e) + '</p>'
                    else:
                        raise ValueError(f'正文未处理 <{t}> type={e.get("type")}')
            elif st == 'back':
                if typ == 'errata':
                    r.slug = 'errata'
                    files['errata'] = to_md(render_div(r, div))
                else:
                    # 书商 Ralph Smith 的售书广告：不是本书内容，PROVENANCE 记录不收
                    print(f'  跳过书末 <div type="{typ}">', file=sys.stderr)
    for slug, md in front:
        files[slug] = md
    booktitle = files.pop('_booktitle', '')

    # 自检：节号连续覆盖、星号奇偶、竖线
    bad = 0
    for ch in range(1, 22):
        vs = [int(x) for x in re.findall(r'class="hc-v" id="v(\d+)"', files[str(ch)])]
        want = [v for v in range(1, NV[ch] + 1) if (ch, v) not in MISSING_V]
        if vs != want:
            print(f'⚠️ ch{ch}: 节号不连续 {vs}', file=sys.stderr)
            bad += 1
    for k, md in files.items():
        plain = re.sub(r'<[^>]+>', '', md)
        if plain.count('*') % 2:
            print(f'⚠️ {k}: 星号奇数 {plain.count("*")}', file=sys.stderr)
            bad += 1
        if '|' in md:
            print(f'⚠️ {k}: 含竖线', file=sys.stderr)
            bad += 1
        if 'ſ' in md:
            print(f'⚠️ {k}: 残留 ſ', file=sys.stderr)
            bad += 1

    print(f'书名 {booktitle!r}', file=sys.stderr)
    print(f'页码 {len(r.pages)}  缺字 {r.gaps}  缺字点 {len(r.gap_sites)}', file=sys.stderr)
    for k, md in files.items():
        nv = len(re.findall(r'class="hc-v"', md))
        print(f'  {k:11s} {len(md):8d} 字符  经文节 {nv}', file=sys.stderr)
    if a.apply:
        OUT.mkdir(parents=True, exist_ok=True)
        for k, md in files.items():
            (OUT / f'{k}.md').write_text(md.strip() + '\n', encoding='utf-8')
        (RAW / 'pages.json').write_text(json.dumps(r.pages, indent=0) + '\n', encoding='utf-8')
        keep = [g for g in r.gap_sites if g['slug'] in files]
        (RAW / 'gap_sites.json').write_text(
            json.dumps(keep, ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
        print(f'写入 {len(files)} 篇 → {OUT}', file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
