#!/usr/bin/env python3
"""perkins_raw/galatians/src/A09383.xml（EEBO-TCP）→ en_chapters/*.md

    python3 scripts/extract_perkins.py            # 试跑，只报统计
    python3 scripts/extract_perkins.py --apply

底本是 TCP 人工双录入的 TEI，**不是 OCR**（old-book-ocr §2.2：有可信文本层就
不要重 OCR）。所以这里只做结构映射，不做任何字形修复；TCP 自己标出的缺字
（<gap>）原样留成可见记号，交给 manual_fixes.tsv 按影像回填。

TEI → markdown 的对照（每一条都对应原书版面上看得见的东西，§0.0）：

| TEI | 原书 | 产出 |
|---|---|---|
| <hi> | 斜体（正文为罗马体） | `*…*`；嵌套 <hi> = 斜体里的正体，反转 |
| <note place="margin"> | 页边旁注 | `<span class="pk-margin">…</span>` |
| <pb n="N"> | 印刷页码 | `<span class="pk-pb" id="pN" data-facs="F"></span>` |
| <q> / 段首斜体节号段 | 被讲解的经文 | `<div class="pk-text">` |
| <seg rend="decorInit"> | 花饰首字 | `<span class="pk-dropcap">` |
| <g ref="char:EOLhyphen"> | 行末断词连字符 | 删（拼合） |
| <g ref="char:cmbAbbrStroke"> | 缩写横线（cōmand） | 保留组合横线 U+0304 |
| <gap reason="illegible" extent="N letter(s)"> | 影像上读不出的字母 | `•`×N |
| <gap … extent="1 word"> / "1 span" | 读不出的词 / 一截 | `〈◊〉` / `〈…〉` |
| <gap reason="foreign"> | 希腊／希伯来活字（TCP 不录） | `〈Greek〉` |
| <g ref="char:punc"> | 认不清的标点 | `▪` |
| <milestone> | TCP 行号（每 5 行） | 丢 |

缺字记号在发布时包成 `.pk-gap`，页面上看得见，不静默。
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'perkins_raw' / 'galatians'
SRC = RAW / 'src' / 'A09383.xml'
OUT = RAW / 'en_chapters'
TEI = '{http://www.tei-c.org/ns/1.0}'

GAP_LETTER = '•'
GAP_WORD = '〈◊〉'
GAP_SPAN = '〈…〉'
GAP_FOREIGN = '〈Greek〉'
PUNC = '▪'

# 印本的节号印错了两处（ch3 第二个 `17` 实为 3:18，第二个 `23` 实为 3:25），
# 经文内容对过和合本／日内瓦本。**显示照印本**，只有锚点 id 用实际节号，
# 否则 verse-nav 与经文索引会跳到重复 id。键 = (章, 印本节号, 本章第几次出现)
VERSE_ID_FIX = {
    (3, 17, 2): 18,
    (3, 23, 2): 25,
}

# 节号写法：`1.` `9 ` `v. 11.` `V. 11.` `ver. 6.` `Vers. 15.` `Verse 7.`
# 另有一处 TCP 把 6:11 的 `11` 录成了罗马字 `II`（`II Ye see how large a letter…`），
# 只认这一个形态，不开放罗马数字——`I am crucified…` 这类经文就是 I 起头。
RE_VNUM = re.compile(r'^\s*(?:The Text\.\s*)?(?:v(?:er(?:se?)?)?\.?\s*)?(\d{1,2}|II(?= Ye see))\b\.?', re.I)


def tag(e):
    return e.tag.replace(TEI, '')


class R:
    """把一棵 TEI 子树渲成 markdown 行内文本。"""

    def __init__(self):
        self.pages = []          # [(n, facs)]
        self.last_facs = None
        self.gaps = {}
        self.held = []
        # 缺字定位：每处 <gap>／认不清的标点记下所在印本页、TCP 图号、页内行号
        # （<milestone n="5|10|…"> 就是原书版心右侧印的行号，见 leaf 0035 影像）
        self.slug = None
        self.cur_page = None
        self.cur_facs = None
        self.cur_line = 0
        self.gap_sites = []

    def site(self, kind, tok):
        self.gap_sites.append({'slug': self.slug, 'kind': kind, 'tok': tok,
                               'page': self.cur_page, 'facs': self.cur_facs,
                               'line': self.cur_line})
        return tok

    def gap(self, e):
        reason = e.get('reason', '')
        ext = e.get('extent', '')
        if reason == 'duplicate':
            return ''
        return self.site(*self._gap(e, reason, ext))

    def _gap(self, e, reason, ext):
        if reason == 'foreign':
            self.gaps['foreign'] = self.gaps.get('foreign', 0) + 1
            return 'foreign', GAP_FOREIGN
        m = re.match(r'(\d+) letters?', ext)
        if m:
            self.gaps['letter'] = self.gaps.get('letter', 0) + int(m.group(1))
            return 'letter', GAP_LETTER * int(m.group(1))
        if ext == '1 word':
            self.gaps['word'] = self.gaps.get('word', 0) + 1
            return 'word', GAP_WORD
        if ext == '1 span':
            self.gaps['span'] = self.gaps.get('span', 0) + 1
            return 'span', GAP_SPAN
        raise ValueError(f'未知 gap: {e.attrib}')

    def inline(self, e, italic=False):
        """斜体用控制符记状态切换：\x01 开、\x02 关；HTML 片段存成 \x03n\x03 占位。
        最后由 norm() 统一出星号——嵌套 <hi>（斜体里的正体）、旁注落在斜体中间，
        这些情形在字符串层面直接拼星号必然配错（§0.4 / old-book-ocr §4.4）。"""
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
                    # 行末断词：断点前若是 XML 排版换行（缩写横线 <g> 恰在行尾时出现，
                    # 全书 46 处），那是排版空白不是词间空格，拼合时一并去掉
                    # （通读第 1 章发现 `dispē sation`）。
                    while out and out[-1].strip() == '' and '\n' in out[-1]:
                        out.pop()
                    if out and out[-1].endswith(('\n', ' ', '\t')) and '\n' in out[-1]:
                        out[-1] = out[-1].rstrip()
                elif ref == 'char:punc':
                    out.append(self.site('punc', PUNC))
                else:
                    out.append(c.text or '')
            elif t == 'gap':
                out.append(self.gap(c))
            elif t == 'milestone':
                if (c.get('n') or '').isdigit():
                    self.cur_line = int(c.get('n'))
            elif t == 'pb':
                out.append(self.hold(self.pb(c)))
            elif t == 'note':
                out.append(' ' + self.hold(self.note(c)) + ' ')
            elif t == 'seg' and c.get('rend') == 'decorInit':
                out.append(self.hold('<span class="pk-dropcap">'
                                     + norm(self, self.inline(c)) + '</span>'))
            elif t in ('seg', 'expan', 'abbr', 'am', 'ex', 'date', 'q', 'lg', 'l', 'p',
                       'signed', 'label', 'desc'):
                out.append(self.inline(c, italic))
            elif t == 'lb':
                out.append(' ')
            elif t == 'figure':
                out.append(' '.join(self.inline(p, italic) for p in c))
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
        if facs != self.cur_facs or n:
            self.cur_line = 0
        self.cur_facs = facs
        self.cur_page = n
        if not n:
            self.last_facs = facs
            return ''
        self.pages.append((n, facs))
        return f'<span class="pk-pb" id="p{n}" data-p="{n}" data-facs="{facs}"></span>'

    def note(self, c):
        body = norm(self, self.inline(c))
        n = c.get('n')
        lab = f'<b>{n}</b> ' if n else ''
        return f'<span class="pk-margin" markdown="1">{lab}{body}</span>'


def norm(r, s):
    """控制符流 → markdown。按字符算出每段是否斜体，相邻同体合并，
    空白一律落在星号外侧，空强调丢掉；HTML 占位视为正体分隔。"""
    s = re.sub(r'\s+', ' ', s)
    runs = []          # [(italic, text)]
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
            runs.append((None, r.held[int(s[i + 1:j])]))
            i = j
        else:
            buf.append(ch)
        i += 1
    flush()
    # 合并相邻同体
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


def is_verse_para(p):
    """段首就是斜体经文：`<hi>N. 经文…</hi>`，且斜体占了段落的大半。"""
    kids = list(p)
    lead = (p.text or '').strip()
    if lead or not kids:
        return None
    first = kids[0]
    if tag(first) == 'seg':      # 花饰首字开头的是注释正文，不是经文
        return None
    if tag(first) != 'hi':
        return None
    full = ''.join(p.itertext())
    hitxt = ''.join(first.itertext())
    m = RE_VNUM.match(re.sub(r'\s+', ' ', hitxt))
    if not m:
        return None
    if len(hitxt.strip()) < 0.6 * len(full.strip()):
        return None
    return 11 if m.group(1) == 'II' else int(m.group(1))


def render_div(r, div, ch=None, seen=None):
    """一个 div → markdown 段落串。"""
    paras = []
    for e in div:
        t = tag(e)
        if t == 'head':
            paras.append(('head', block_text(r, e)))
        elif t == 'pb':
            x = r.pb(e)
            if x:
                paras.append(('pb', x))
        elif t == 'argument':
            sub = render_div(r, e, ch, seen)
            paras.append(('argument', sub))
        elif t == 'q':
            for p in e:
                if tag(p) == 'pb':
                    x = r.pb(p)
                    if x:
                        paras.append(('pb', x))
                    continue
                v = is_verse_para(p)
                paras.append(('verse', block_text(r, p), v))
        elif t == 'p':
            v = is_verse_para(e) if ch else None
            if v is not None:
                paras.append(('verse', block_text(r, e), v))
            elif e.find(TEI + 'table') is not None:
                paras.append(('table', render_table(r, e.find(TEI + 'table'))))
                rest = e.find(TEI + 'table').tail or ''
                if rest.strip():
                    paras.append(('p', norm(r, rest)))
            else:
                txt = block_text(r, e)
                if txt:
                    paras.append(('p', txt))
        elif t in ('closer', 'trailer', 'signed', 'opener', 'salute', 'dateline'):
            paras.append(('closer', block_text(r, e)))
        elif t == 'figure':
            paras.append(('center', ' · '.join(block_text(r, p) for p in e)))
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
        elif t == 'div':
            paras += render_div(r, e, ch, seen)
        else:
            raise ValueError(f'块级未处理的元素 <{t}>')
    return paras


def render_table(r, tb):
    rows = []
    for row in tb:
        if tag(row) != 'row':
            continue
        # HTML 块里 kramdown 不解析 markdown：单元格斜体直接出 <em>
        cells = [re.sub(r'\*([^*]+)\*', r'<em>\1</em>', block_text(r, c)) for c in row if tag(c) == 'cell']
        th = row[0].get('role') == 'label' if len(row) else False
        tg = 'th' if th else 'td'
        rows.append('<tr>' + ''.join(f'<{tg}>{c}</{tg}>' for c in cells) + '</tr>')
    return '<table class="pk-errata">\n' + '\n'.join(rows) + '\n</table>'


def to_md(paras, ch=None, pending=None):
    """段落元组 → markdown。经文段 → .pk-text 块并带锚点。

    两段之间的页码锚点挂进**下一段的行内**：与块级 `<div>` 写在同一行会让
    kramdown 把整行当成段落、div 不再是块（页面上经文框消失）。"""
    out = []
    count = {}
    pending_pb = list(pending or [])
    for item in paras:
        k = item[0]
        if k == 'pb':
            # 两段之间的页码：挂到下一段开头，不独占一段
            pending_pb.append(item[1])
            continue
        pre = ''.join(pending_pb)
        pending_pb = []
        if k == 'head':
            out.append(f'## {pre}{item[1]}')
        elif k == 'argument':
            inner = to_md(item[1], ch, [pre] if pre else None)
            out.append(f'<div class="pk-argument" markdown="1">\n\n{inner}\n\n</div>')
        elif k == 'verse':
            txt, v = item[1], item[2]
            vid = ''
            if ch and v:
                count[v] = count.get(v, 0) + 1
                real = VERSE_ID_FIX.get((ch, v, count[v]), v)
                if count[v] == 1 or (ch, v, count[v]) in VERSE_ID_FIX:
                    vid = f' id="v{real}"'
            out.append(f'<div class="pk-text"{vid} markdown="1">\n\n{pre}{txt}\n\n</div>')
        elif k == 'table':
            out.append((pre + '\n\n' if pre else '') + item[1])
        elif k == 'closer':
            out.append(f'<p class="pk-closer" markdown="1">{pre}{item[1]}</p>')
        elif k == 'center':
            out.append(f'<p class="pk-center" markdown="1">{pre}{item[1]}</p>')
        else:
            out.append(pre + item[1])
    if pending_pb:
        out.append(''.join(pending_pb))
    return '\n\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    tree = ET.parse(SRC)
    texts = tree.getroot().find(TEI + 'text')
    group = texts.find(TEI + 'group')
    parts = list(group) if group is not None else [texts]

    r = R()
    files = {}
    front_parts = []
    supp_parts = []
    for ti, tx in enumerate(parts):
        for sec in tx:            # front / body / back
            for div in sec:
                if tag(div) != 'div':
                    continue
                typ = div.get('type')
                r.slug = {'chapter': div.get('n'), 'conclusion': 'conclusion',
                          'title_page': 'dedication', 'dedication': 'dedication',
                          'to_the_reader': 'reader', 'errata': 'reader'}.get(typ)
                if ti > 0 and typ in ('title_page', 'dedication'):
                    r.slug = 'supplement'
                if typ == 'chapter':
                    n = int(div.get('n'))
                    paras = render_div(r, div, n)
                    files[str(n)] = to_md(paras, n)
                elif typ in ('title_page', 'dedication', 'to_the_reader', 'errata'):
                    md = to_md(render_div(r, div))
                    (front_parts if ti == 0 else supp_parts).append((typ, md))
                elif typ == 'conclusion':
                    files['conclusion'] = to_md(render_div(r, div))
                else:
                    # 书末：论题一览、经文索引、字母索引 —— 全按印本页码检索，
                    # 网页按章分页后页码失去意义。PROVENANCE.md 记录了不收的理由。
                    print(f'  跳过书末 <div type="{typ}">', file=sys.stderr)

    def join(parts_):
        return '\n\n'.join(f'<div class="pk-{t.replace("_", "-")}" markdown="1">\n\n{md}\n\n</div>'
                           for t, md in parts_)
    # 卷首拆两篇：书名页 + 献辞 / 致读者 + 勘误表
    files['dedication'] = join([x for x in front_parts if x[0] in ('title_page', 'dedication')])
    files['reader'] = join([x for x in front_parts if x[0] in ('to_the_reader', 'errata')])
    files['supplement'] = join(supp_parts)

    # 自检：星号奇偶、残留 TEI、`|`
    bad = 0
    for k, md in files.items():
        plain = re.sub(r'<[^>]+>', '', md)
        if plain.count('*') % 2:
            print(f'⚠️ {k}: 星号奇数 {plain.count("*")}', file=sys.stderr)
            bad += 1
        if '|' in md:
            print(f'⚠️ {k}: 含竖线', file=sys.stderr)
            bad += 1

    print(f'页码 {len(r.pages)}  缺字 {r.gaps}', file=sys.stderr)
    for k, md in files.items():
        nv = len(re.findall(r'class="pk-text"', md))
        print(f'  {k:11s} {len(md):8d} 字符  经文块 {nv}', file=sys.stderr)
    if a.apply:
        OUT.mkdir(parents=True, exist_ok=True)
        for k, md in files.items():
            (OUT / f'{k}.md').write_text(md.strip() + '\n', encoding='utf-8')
        (RAW / 'pages.json').write_text(json.dumps(r.pages, indent=0) + '\n', encoding='utf-8')
        # 每篇里缺字记号的出现次序 = 这里的次序（ordinal），回填按它对位
        keep = [g for g in r.gap_sites if g['slug'] in files]
        (RAW / 'gap_sites.json').write_text(
            json.dumps(keep, ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
        print(f'写入 {len(files)} 篇 → {OUT}', file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
