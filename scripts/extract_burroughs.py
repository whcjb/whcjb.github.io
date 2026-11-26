#!/usr/bin/env python3
"""burroughs_raw/hosea/src/*.xml（EEBO-TCP 四卷）→ en_chapters/*.md + order.json + gap_sites.json

    python3 scripts/extract_burroughs.py            # 试跑，只报统计
    python3 scripts/extract_burroughs.py --apply

耶利米·巴罗夫《何西阿书讲解》，原是伦敦康希尔圣米迦勒堂（Michael's Cornhill）的周间讲座，分四卷出版：

| TCP | 章 | 出版 | 录入本结构 |
|---|---|---|---|
| A30572 | 1–3 | 1652（合订再版；首版 1643 起分册） | 章下按讲次分 <div type="lecture">，共 29 讲 |
| A77979 | 4–7 | 1650，Peter Cole（Goodwin、Greenhill 等五人刊行） | 章下 <div type="verse">，段首 <epigraph> |
| A30574 | 8–10 | 1650，Peter Cole | 同上；第 8 章 div 无 n |
| A30575 | 11–13 | 1651，Peter Cole | 段首经文录作 <argument>；卷末「校订者致读者」 |

巴罗夫 1646 年去世，讲到 13:11 为止（13:12 起由 Thomas Hall、第 14 章由 Edward Reynolds 续完，另成书，不收）。
底本是 TCP 人工录入的 TEI，**不是 OCR**；CC0。缺字原样留记号，交给 burroughs_common.py 按判读表回填。

分页：
- 第 1–3 章：一讲一页，节段照每讲段首所引经文（见 LECTURES，手工从 <epigraph> 定）；
  一讲常从上一讲讲到的那节中间接着讲，节段可以重叠。页名 `<章>-<首节>`，同一节起头的第二、三讲加 `-2`、`-3`。
- 第 4–13 章：照录入本 verse 分段，相邻段合并到每页至少 MIN_WORDS 词（照 extract_greenhill.py）。

卷首：各卷书名页、致读者书；第四卷卷末「校订者致读者」（说明巴罗夫讲到何处为止）列在卷末。
目录、准印、书商广告、扉页画、索引不收。
"""
import argparse
import collections
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import burroughs_common as gc  # noqa: E402
import tcp_tei as tt  # noqa: E402

RAW = gc.RAW
OUT = RAW / 'en_chapters'
TEI = tt.TEI
P = 'jb'
MIN_WORDS = 3000
VOLS = [('A30572', 1652, range(1, 4)), ('A77979', 1650, range(4, 8)), ('A30574', 1650, range(8, 11)),
        ('A30575', 1651, range(11, 14))]
# 何西阿书各章节数（钦定本），共 197 节；本书只到 13:11
NV = dict(enumerate([11, 23, 5, 19, 15, 11, 16, 14, 17, 15, 12, 14, 16], 1))
LAST = {13: 11}
# 第 1–3 章每讲的节段（据各讲段首 <epigraph>）
LECTURES = {
    1: [(1, 2), (2, 5), (6, 7), (8, 10), (10, 11), (11, 11), (11, 11)],
    2: [(1, 2), (2, 3), (3, 4), (5, 5), (6, 7), (7, 8), (9, 10), (11, 11), (11, 11), (11, 11), (12, 13), (14, 14),
        (15, 15), (15, 15), (15, 16), (16, 18), (19, 20), (19, 19), (20, 23)],
    3: [(1, 3), (4, 5), (5, 5)],
}
ROMAN = ['', 'I', 'II', 'III', 'IV']
FRONT_TYPES = {'title_page': ('title', 'Title Page'),
               'to_the_reader': ('to-the-reader', 'To the Reader')}
FRONT_SKIP = {'imprimatur', 'publishers_advertisement', 'table_of_contents', 'frontispiece', 'by_the_same_author'}
RE_VQ = re.compile(r'^\W*(?:Ver[ſs]?e?\.?\s*)?(\d{1,2})\b')




_LEX = None


def en_lexicon():
    """本书正文（不含旁注）里出现 ≥ 20 次的词：判旁注是不是外文用。"""
    global _LEX
    if _LEX is None:
        c = collections.Counter()
        for tcp, _, _ in VOLS:
            root = ET.parse(RAW / 'src' / f'{tcp}.xml').getroot()
            for n in list(root.iter(TEI + 'note')):
                n.clear()
            txt = ' '.join(root.itertext()).replace('ſ', 's')
            c.update(w.lower() for w in re.findall(r'[A-Za-z]+', txt))
        _LEX = {w for w, k in c.items() if k >= 20}
    return _LEX


def latin_note(t):
    """旁注底子（去掉 <hi> 部分）是不是成句的外文：只看三字母以上的小写词（专名、缩写出处不算），
    至少 2 个，其中本书正文常用英文词不到三分之一。
    格林希尔的判据（英文虚词 < 15%）在这本书上把英文短旁注（Use to Ministers.）也判成外文，不用。"""
    base = re.sub('\x01.*?\x02', ' ', t, flags=re.S)
    base = re.sub(r'<[^>]+>|[\x03-\x04]', '', base).replace('ſ', 's')          # \x04 = 行末断词拼合点
    ws = re.findall(r"(?<![A-Za-z•])[a-z]{3,}(?![A-Za-z•])", base)               # 带缺字记号的残词不算
    lex = en_lexicon()
    if not (len(ws) >= 2 and sum(1 for w in ws if w in lex) * 3 < len(ws)):
        return False
    # 还要有拉丁的正面证据：虚词，或多数词带拉丁词尾（挡住 Fair Skins foul Souls oftimes 这类生僻英文）
    toks = re.findall(r"(?<![A-Za-z•])[A-Za-z]+(?![A-Za-z•])", base)
    if any(w.lower() in LATIN_MARK for w in toks):
        return True
    return sum(1 for w in ws if re.search(LATIN_END, w)) * 3 >= len(ws) * 2


# 纲目标签（Obs. 2、Use.、Expos. 1. …）与只有一个人名的旁注（Jareb.、Hierom.——p.392/393 看图）斜体底子页上也排正体，不翻
RE_LABEL = re.compile(r'^[A-Z][a-zſ]+\.?$|^(?:\d+\.?\s*)?(?:Obs|Obser|Observ|Use|Us|Uses|Expos|Exp|Quest|Qu|Answ|Ans|Reas|Object|Obj|Applic|Applicat|Doct|Doctr|Motive|Motives|Means|Note|Simile|simile|Caution|Signes?|Reason)\.?,?\s*\d*\.?\s*$')
LATIN_MARK = set('et est non quod qui quae quam sed cum nec neque vel enim sunt esse sic sicut ut ad nisi hoc id ab ex pro '
                 'per ejus eius sua suam eum eos quia atque quasi tamen ergo autem etiam inquit'.split())
LATIN_END = r'(us|um|am|is|ae|orum|arum|ibus|ur|unt|ent|it|at|em|ere|ari|iri|tio|tas)$'


class GR(tt.R):
    nest_lists = True                                # 嵌套分条各起一行（old-book-ocr §3.3a）

    def note(self, c):
        if c.get('place') == 'mark':                 # 页边纲目标记（Note 1 / Obs. / Use …）
            t = tt.norm(self, self.inline(c))
            return f'<span class="{self.P}-mark">{t}</span>' if t else ''
        plain = tt.norm(self, self.inline(c))
        lat = latin_note(self.inline(c))
        if lat or (self.italic_base() and not RE_LABEL.match(re.sub(r'<[^>]+>|\*|[▪•]', '', plain))):
            # 拉丁文旁注原书底子是斜体，录入本只给正体部分（英文连接词、出处人名）标 <hi>，整条正斜互换
            # （2026-11-26 抽 10:12 对杜克藏本影像核实：Hierom 注、Arias Mont. 注、Paratus sum 注、Ipsa gratiarum actio 注）
            t = tt.norm(self, chr(1) + self.inline(c, True) + chr(2))
            if not lat:                              # 斜体底子页：条首序号「2.」原书正体
                t = re.sub(r'^\*(\d+\.?) ', r'\1 *', t)
            return f'<span class="{self.P}-margin" markdown="1">{t}</span>'
        return super().note(c)

    def italic_base(self):
        """这一页的英文旁注原书是不是斜体底子（录入本照例只给正体部分标 <hi>，须整条正斜互换）。
        第 3 卷 pp. 1–441 是（逐叶测倾斜 + 看图核 p.68/110/114/203/204/271/420/430/431）；p.442 起回到正体底子
        （第 1 轮实读 442–487），其中 p.467 那条长注例外仍是斜体。第 2、4 卷看图都是正体底子。"""
        if getattr(self, 'tcp', None) != 'A30574' or not self.pages:
            return False
        n = self.pages[-1][0]
        return n.isdigit() and (int(n) <= 441 or n == '467')

    def gap(self, e):
        if e.get('reason') == 'illegible' and (e.get('extent') or '') == '1 chunk':
            self.gaps['span'] = self.gaps.get('span', 0) + 1
            return ' ' + tt.GAP_SPAN + ' '
        return super().gap(e)


def prep(root):
    for g in root.iter(TEI + 'g'):
        if g.get('ref') == 'char:V':                 # Ʋ：原书 U/V 同形的大写 V 字模。后接元音读 V（Vatablus、Vulg.），后接辅音读 U（Unto、Upon）
            tail = (g.tail or '').replace('ſ', 's')
            g.text = 'V' if tail[:1].lower() in tuple('aeiouy') or tail.startswith('ladislaus') else 'U'
    for lab in root.iter(TEI + 'label'):
        if lab.get('type') == 'milestone':
            lab.tag = TEI + 'note'
            lab.attrib.clear()
            lab.set('place', 'mark')
    # 页边只印一个序号（2、3…）的，录入本记作空 <milestone type="tcpmilestone" n="2"/>，原先整类丢掉；
    # 段内的照页边纲目标记排（2026-11-26 抽 7:9、5:15 看图：p.678「2. 3 4」、p.522「2」）。块级的（章节间）不动。
    inline = {c for p in root.iter() if tt.tag(p) in ('p', 'item', 'q', 'l', 'hi') for c in p}
    for ms in root.iter(TEI + 'milestone'):
        if ms.get('type') == 'tcpmilestone' and ms in inline:
            unit = ms.get('unit', 'unspecified')
            txt = ((unit + ' ') if unit != 'unspecified' else '') + (ms.get('n') or '')
            ms.tag = TEI + 'note'
            ms.attrib.clear()
            ms.set('place', 'mark')
            ms.text = txt.strip()
    # 段尾的 <q>（前面是句末标点、后面段落结束）原书是居中的逐句小标题，录入本录进了上一段：
    # 挪出来与其他段外 <q> 一样排 jb-quote（2026-11-26 抽 11:2 看图 p.37「But they knew not that I healed them.」）
    parent = {c: p for p in root.iter() for c in p}
    for p in list(root.iter(TEI + 'p')):
        kids = list(p)
        if not kids or tt.tag(kids[-1]) != 'q' or (kids[-1].tail or '').strip() \
                or any(tt.tag(x) not in ('note', 'hi') for x in kids[-1]):
            continue
        q = kids[-1]
        before = (kids[-2].tail if len(kids) > 1 else p.text) or ''
        qtext = ''.join(t for x in [q] for t in [q.text or ''] + [(y.tail or '') for y in q])
        # 前文以句末标点收尾，或以引出论点的 That / this / thus 收尾（p.404「the Note is this, That ⟨论点⟩」）
        # 或以「Note (is) likewise,」「observe,」这类引语加逗号收尾（p.408「Thence this Note likewise, ⟨论点⟩」）
        if not (re.search(r'(?:[.;:?!)]|\b(?:That|that|this|thus))\s*$', before)
                or re.search(r'\b(?:Note|note|Notes|observe|Observe|observed)\b[^.;:]{0,25},\s*$', before)) or len(qtext) > 200:
            continue
        p.remove(q)
        q.tail = '\n'
        gp = parent[p]
        gp.insert(list(gp).index(p) + 1, q)
    for el in root.iter():                          # 原书字面星号不当斜体
        for a in ('text', 'tail'):
            v = getattr(el, a)
            if v and '*' in v:
                setattr(el, a, v.replace('*', '&#42;'))


# 经文框原书「经文斜体、专名正体」，站上整框斜体、框内 *…* 转正体。第 2、3 卷录入本经文框里的专名多半没标 <hi>
# （2026-11-26 看图 p.392 Assyria/Jareb、p.402 Samaria），按专名表补标；已在 *…* 里的、出处行、标签内的不动。
EPI_NAMES = ('Israel|Ephraim|Samaria|Judah|Egypt|Assyria|Jacob|Gilead|Bethel|Beth-el|Gibeah|Ramah|Baal|Baalim|Jareb|'
             'Beth-aven|Bethaven|Lebanon|Admah|Zeboim|Gilgal|Jezreel|Mizpah|Tabor|Shittim|Adam|Moses|Aven|Shalman|'
             'Betharbel|Beth-arbel|Edom|Achor|Hosea|Jeroboam|Uzziah|Jotham|Ahaz|Hezekiah|Joash|Gomer|Diblaim|'
             'Lo-ruhamah|Loruhamah|Lo-ammi|Loammi|Ammi|Ruhamah|Ishi|Sodom|Gomorrah|Memphis|Tyrus|Mesopotamia|Syria|Aram|'
             'David|Abraham|Isaac|Gibeon|Zion|Jerusalem|Assur|Ashur|Canaan|Egyptians|Assyrians')
RE_EPI_NAME = re.compile(r'(?<![\w*-])(' + EPI_NAMES + r")(?=[\s.,;:!?)'’]|$)")


def mark_names(line):
    if line.startswith(f'<span class="{P}-ref">'):
        return line
    held = []
    t = re.sub(r'<[^>]+>|\*[^*]+\*', lambda m: held.append(m.group(0)) or f'\x01{len(held) - 1}\x02', line)
    t = RE_EPI_NAME.sub(r'*\1*', t)
    return re.sub(r'\x01(\d+)\x02', lambda m: held[int(m.group(1))], t)


def epigraph_box(r, ep):
    """段首经文：<bibl> 出处一行，<q> 每段一行（<q><p>… 或 <q><bibl>节号</bibl>经文</q>）。"""
    lines = []
    for c in ep:
        k = tt.tag(c)
        if k == 'bibl':
            lines.append(f'<span class="{P}-ref">{r.text(c)}</span>')
        elif k == 'q':
            if any(tt.tag(x) == 'p' for x in c):
                loose = ET.Element(TEI + 'p')        # <p> 之间的散字与行内元素（<gap>、<hi>…）并成一行
                loose.text = c.text

                def flush():
                    nonlocal loose
                    t = r.text(loose)
                    if t:
                        lines.append(t)
                    loose = ET.Element(TEI + 'p')
                for x in c:
                    kx = tt.tag(x)
                    if kx in ('p', 'pb'):
                        flush()
                        lines.append(r.text(x) if kx == 'p' else r.pb(x))
                        loose.text = x.tail
                    elif kx == 'bibl':                   # 出处行录在 <q> 里面（VERS. 19, 20.），照样排成出处行
                        flush()
                        lines.append(f'<span class="{P}-ref">{r.text(x)}</span>')
                        loose.text = x.tail
                    else:
                        loose.append(x)
                flush()
            else:
                lines.append(r.text(c))
        elif k == 'pb':
            lines.append(r.pb(c))
        elif k == 'p':                               # 第四卷段首经文录作 <argument><p>
            lines.append(r.text(c))
        elif k == 'note':
            lines.append(r.note(c))
        else:
            raise ValueError(f'epigraph 下未处理 <{k}>')
    lines = [mark_names(x) for x in lines]
    out = []
    for x in lines:                                  # 页码锚点挂进下一行
        if not x:
            continue
        if out and out[-1].startswith(f'<span class="{P}-pb"') and out[-1].endswith('</span>'):
            out[-1] += x
        else:
            out.append(x)
    return '\n\n'.join(out)


RE_HVLIST = re.compile(r'^\W*VER[SſE]*\.?[\s\d.,&and-]*$', re.I)
RE_HVERS = re.compile(r'^\W*Ver[ſs]?[ei]?[.,]?\s*\d')


def head_md(r, e, depth, before_text=False):
    """标题版式照原书（old-book-ocr §3.3a）。录入本 <hi> 只标「与本行不同的字体」，本行底子是正是斜要推：
    无 <hi>，或 <hi> 之外还有两个以上词 → 底子斜体（所引经文），<hi> 部分转正体；否则底子正体（Observ. 1.）。
    段首经文前那一行（VERS. 60, 61.）居中大字；Vers. N 起头的引语行齐左悬挂；其余居中。"""
    txt = r.text(e)
    if not txt:
        return None
    his = [x for x in e.iter() if tt.tag(x) == 'hi']
    rest = tt.text_of(e)
    for h in his:
        rest = rest.replace(tt.text_of(h), ' ', 1)
    base_it = not his or len(re.findall(r'[A-Za-zſ]{2,}', rest)) >= 2
    plain = tt.text_of(e).replace('ſ', 's').strip()
    if before_text or RE_HVLIST.match(plain):          # 只有节号的一行（VERS. 60, 61, 62.）
        cls, base_it = 'jb-h-vers', False
    elif re.match(r'CHAP(?:TER)?\.? +[IVXLC\d]+\.?$', plain, re.I):   # 章标题原书正体大字（CHAP. XXXII.）
        cls, base_it = 'jb-h-c', False
    elif RE_HVERS.match(plain):
        cls = 'jb-h-lv'
    else:
        cls = 'jb-h-c'
    if base_it:
        parts = re.split(r'(<span class="jb-margin".*?</span>)', txt, flags=re.S)   # 旁注里的斜体不动
        txt = ''.join(x if x.startswith('<span class="jb-margin"') else
                      re.sub(r'(?<![\\*])\*([^*\n]+?)\*(?!\*)', r'<span class="jb-up">\1</span>', x) for x in parts)
        cls += ' jb-h-it'
    return '#' * depth + ' ' + txt + '\n{: .' + cls.replace(' ', ' .') + '}'


def render(r, e, paras, depth=3):
    """块级：在 tt.block 之上加 epigraph；div 递归（深一层标题多一个 #）。"""
    k = tt.tag(e)
    if k == 'milestone':                             # 块级的空 milestone（第二卷章节间）
        return
    if k in ('epigraph', 'argument'):
        paras.append(('text', epigraph_box(r, e)))
    elif k == 'div':
        kids = list(e)
        for i, c in enumerate(kids):
            if tt.tag(c) == 'head':
                nxt = next((x for x in kids[i + 1:] if tt.tag(x) != 'pb'), None)
                h = head_md(r, c, depth, nxt is not None and tt.tag(nxt) == 'epigraph')
                if h:
                    paras.append(('head', h))
                continue
            render(r, c, paras, min(depth + 1, 5))
    elif k == 'head':
        h = head_md(r, e, depth)
        if h:
            paras.append(('head', h))
    else:
        tt.block(r, e, paras, depth)


def words(paras):
    n = 0
    for p in paras:
        v = p[-1]
        if isinstance(v, list):
            v = ' '.join(x if isinstance(x, str) else '' for x in v)
        v = re.sub(r'<span class="jb-mark">[0-9]+</span>', ' ', v)        # 页边纯序号不计词（2026-11-26 补出后不改动分页）
        n += len(re.sub(r'<[^>]+>|\n\{: [^}]*\}', ' ', v).split())       # 标题版式行不计词
    return n


def units_from_divs(r, cdiv, ch, lead):
    """一、二、三、五卷：每个 verse div 一个单元。返回 [(首节, 末节, paras)]。"""
    units = []
    for x in cdiv:
        if tt.tag(x) != 'div':
            if units:
                render(r, x, units[-1][2])
            else:
                render(r, x, lead, 2)
            continue
        n = x.get('n') or ''
        nums = [int(z) for z in re.findall(r'\d+', n)]
        paras = []
        for c in x:
            render(r, c, paras, 3)
        if not nums or (units and nums[0] <= units[-1][0]):
            if not units:
                raise ValueError(f'{ch}: 首单元 n 认不出 {n!r}')
            units[-1][2].extend(paras)
            units[-1][1] = max(units[-1][1], max(nums) if nums else 0)
            continue
        units.append([nums[0], max(nums), paras])
    return units


def units_from_quotes(r, cdiv, ch, lead):
    """第四卷：在以新节号起头的 <q> 处切。原书一段经文常连引数节（Vers. 25 … 26 … 27 …），
    中间无正文的连续节号引语同属一段，只在第一节处切，后面几节并进同一单元。"""
    units, maxv, run = [], 0, False
    for x in cdiv:
        k = tt.tag(x)
        if k == 'pb':
            pass
        elif k == 'q':
            m = RE_VQ.match(tt.text_of(x).replace('ſ', 's'))
            if m and maxv < int(m.group(1)) <= NV[ch]:
                v = int(m.group(1))
                if run and units:
                    units[-1][1] = v
                else:
                    units.append([v, v, []])
                maxv, run = v, True
            else:
                run = False
        else:
            run = False
        if not units:
            render(r, x, lead, 2 if k == 'head' else 3)
        else:
            render(r, x, units[-1][2])
    return units


def merge(units, ch):
    pages = []
    for u in units:
        if pages and words(pages[-1][2]) < MIN_WORDS:
            pages[-1][1] = max(pages[-1][1], u[1])
            pages[-1][2].extend(u[2])
        else:
            pages.append([u[0], u[1], list(u[2])])
    if len(pages) > 1 and words(pages[-1][2]) < MIN_WORDS // 3:
        last = pages.pop()
        pages[-1][2].extend(last[2])
    return pages


def lecture_pages(r, cdiv, ch, lead):
    """第 1–3 章：每讲一页。章标题（HOSEA, CHAP. 2.）与页码并进第一讲。"""
    lecs = [x for x in cdiv if tt.tag(x) == 'div']
    if len(lecs) != len(LECTURES[ch]):
        raise ValueError(f'{ch}: 讲数 {len(lecs)} ≠ LECTURES {len(LECTURES[ch])}')
    for x in cdiv:
        if tt.tag(x) == 'div':
            break
        render(r, x, lead, 2)
    pages = []
    for (v1, v2), lec in zip(LECTURES[ch], lecs):
        paras = []
        for c in lec:
            render(r, c, paras, 3)
        pages.append([v1, v2, paras, int(lec.get('n'))])
    pages[0][2][:0] = lead
    return pages


def chapter_no(cdiv, expect):
    n = cdiv.get('n')
    if n:
        return int(n)
    h = cdiv.find(TEI + 'head')
    m = re.search(r'CHAP\.?\s*([IVXL]+)', tt.text_of(h) if h is not None else '')
    roman = {'I': 1, 'V': 5, 'X': 10, 'L': 50}
    if not m:
        raise ValueError(f'认不出章号（预期 {expect}）')
    s, v = m.group(1), 0
    for i, c in enumerate(s):
        v += -roman[c] if i + 1 < len(s) and roman[s[i + 1]] > roman[c] else roman[c]
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    files, order, sections, front_meta, back_meta = {}, [], [], [], []
    gaps = collections.Counter()
    bad = 0

    def put(slug, paras):
        if slug in files:
            raise ValueError(f'重复页名 {slug}')
        files[slug] = tt.to_md(P, paras)
        order.append(slug)

    for vi, (tcp, year, chs) in enumerate(VOLS, 1):
        root = ET.parse(RAW / 'src' / f'{tcp}.xml').getroot()
        prep(root)
        text = root.find(f'.//{TEI}text')
        r = GR(P, str(year))
        r.tcp = tcp
        for div in text.find(TEI + 'front'):
            if tt.tag(div) != 'div' or div.get('type') in FRONT_SKIP:
                continue
            suf, title = FRONT_TYPES[div.get('type')]
            paras = []
            for c in div:
                render(r, c, paras, 3)
            slug = f'vol{vi}-{suf}'
            put(slug, paras)
            front_meta.append(dict(slug=slug, title=f'Vol. {ROMAN[vi]} · {title}', vol=vi, year=year, tcp=tcp))

        body = text.find(TEI + 'body')
        lead, cdivs, tail, pre = [], [], [], {}

        def collect(e):
            for c in e:
                k = tt.tag(c)
                if k == 'div' and c.get('type') == 'chapter':
                    cdivs.append(c)
                elif k == 'div' and c.get('type') in ('biblical_commentary', 'exposition'):
                    collect(c)
                elif k == 'div' and c.get('type') == 'table_of_contents':
                    continue
                elif k in ('trailer', 'closer'):
                    tail.append(c)
                elif k in ('head', 'pb'):         # 总题（第二卷第 6 章前又有一个）：并进其后一章的第一页
                    if k == 'head' or not cdivs:
                        render(r, c, pre.setdefault(len(cdivs), []), 2)
                else:
                    raise ValueError(f'{tcp}: 章外多出 <{k}> {c.get("type")}')
        collect(body)
        nums = [chapter_no(c, ch) for c, ch in zip(cdivs, chs)]
        if nums != list(chs):
            raise ValueError(f'{tcp}: 章号 {nums}')
        for k, (cdiv, ch) in enumerate(zip(cdivs, chs)):
            lead = pre.get(k, [])
            if vi == 1:
                pages = lecture_pages(r, cdiv, ch, lead)
                lead = []
            else:
                units = units_from_divs(r, cdiv, ch, lead)
                if not units:
                    raise ValueError(f'{ch}: 没有单元')
                units[0][2][:0] = lead
                lead = []
                pages = [p + [None] for p in merge(units, ch)]
                pages[0][0] = 1
            seen = collections.Counter()
            last = LAST.get(ch, NV[ch])
            for i, (v1, v2, paras, lec) in enumerate(pages):
                if lec is None:
                    end = pages[i + 1][0] - 1 if i + 1 < len(pages) else last
                else:
                    end = v2
                if end < v1 or v2 > NV[ch]:
                    print(f'⚠️ {ch}:{v1}–{end}（单元末节 {v2}）越界', file=sys.stderr)
                    bad += 1
                seen[v1] += 1
                slug = f'{ch}-{v1}' + ('' if seen[v1] == 1 else f'-{seen[v1]}')
                put(slug, paras)
                sections.append(dict(slug=slug, ch=ch, v1=v1, v2=end, words=words(paras), vol=vi,
                                     **({'lecture': lec} if lec else {})))
        for c in tail:
            files[order[-1]] += '\n\n' + tt.to_md(P, [('cls', f'{P}-closer', r.text(c))])
        back = text.find(TEI + 'back')
        for div in (back if back is not None else []):
            if tt.tag(div) == 'div' and div.get('type') == 'to_the_reader':
                paras = []
                for c in div:
                    render(r, c, paras, 3)
                slug = f'vol{vi}-supervisor'
                put(slug, paras)
                back_meta.append(dict(slug=slug, title=f'Vol. {ROMAN[vi]} · The Supervisor to the Reader', vol=vi,
                                      year=year, tcp=tcp))
        gaps.update(r.gaps)

    bad += tt.check(files)
    ws = [s['words'] for s in sections]
    print(f'页 {len(files)}（经文段 {len(sections)}，卷首 {len(front_meta)}，卷末 {len(back_meta)}）  缺字 {dict(gaps)}',
          file=sys.stderr)
    print(f'每段词数：最少 {min(ws)}  中位 {sorted(ws)[len(ws) // 2]}  最多 {max(ws)}', file=sys.stderr)
    big = sorted(sections, key=lambda s: -s['words'])[:5]
    print('最长：' + '，'.join(f'{s["slug"]} {s["words"]}' for s in big), file=sys.stderr)
    per = collections.Counter(s['ch'] for s in sections)
    print('每章页数：' + ' '.join(f'{c}:{per[c]}' for c in sorted(per)), file=sys.stderr)
    if a.apply:
        OUT.mkdir(parents=True, exist_ok=True)
        for f in OUT.glob('*.md'):
            f.unlink()
        for k, md in files.items():
            (OUT / f'{k}.md').write_text(md.strip() + '\n', encoding='utf-8')
        (RAW / 'order.json').write_text(json.dumps({'order': order, 'sections': sections, 'front': front_meta,
                                                    'back': back_meta}, indent=1, ensure_ascii=False) + '\n',
                                        encoding='utf-8')
        write_gap_sites(order)
        print(f'写入 {len(files)} 篇 → {OUT}', file=sys.stderr)
    return 1 if bad else 0


def write_gap_sites(order, nctx=8):
    """缺字组清单（照 petter_witness.py gaps）：gid / slug / 原串 / 前后文 / 原书页码。"""
    od = {x['slug']: x['vol'] for x in json.loads((RAW / 'order.json').read_text())['sections']}
    od |= {x['slug']: x['vol'] for k in ('front', 'back') for x in json.loads((RAW / 'order.json').read_text())[k]}
    sites, prev_tail, pnum, facs, main_total, po_base = [], [], None, None, 0, 0
    for slug in order:
        md = gc.read_src(slug)
        margins = [(m.start(), m.end()) for m in re.finditer(r'<span class="jb-margin"[^>]*>.*?</span>', md, re.S)]
        blank = md
        for a, b in margins:
            blank = blank[:a] + ' ' * (b - a) + blank[b:]
        pns = [(m.start(), m.group(1)) for m in re.finditer(r'<span class="jb-pb"[^>]*data-p="([^"]+)"', md)]
        fcs = [(m.start(), int(m.group(1))) for m in re.finditer(r'<span class="jb-pb"[^>]*data-facs="(\d+)"', md)]
        if slug.endswith('-title') or slug == f'vol{od[slug]}-title':
            pnum, facs, po_base = None, None, 0      # 新一卷：页码、帧号、页序从头算
        for a, b, s, isnote in gc.gap_groups(md):
            pn = next((x for p, x in reversed(pns) if p < a), pnum)
            fc = next((x for p, x in reversed(fcs) if p < a), facs)
            po = po_base + sum(1 for p, _ in pns if p < a)   # 本卷第几个带页码的页：原书有两次分页、页码重号时也单调
            if isnote:
                na, nb = next((x, y) for x, y in margins if x <= a < y)
                left, right = gc.flat_words(md[na:a]), gc.flat_words(md[b:nb])
            else:
                left, right = prev_tail + gc.flat_words(blank[:a]), gc.flat_words(blank[b:])
            sites.append({'gid': len(sites), 'slug': slug, 'stream': 'note' if isnote else 'main', 'tcp': s,
                          'left': left[-nctx:], 'right': right[:nctx], 'page': pn, 'po': po, 'facs': fc, 'vol': od[slug],
                          'i': main_total + len(gc.flat_words(blank[:a])),
                          **({'mleft': (prev_tail + gc.flat_words(blank[:na]))[-nctx:],
                              'mright': gc.flat_words(blank[nb:])[:nctx]} if isnote else {})})
        if pns:
            pnum = pns[-1][1]
        po_base += len(pns)
        if fcs:
            facs = fcs[-1][1]
        prev_tail = gc.flat_words(blank)[-nctx:]
        main_total += len(gc.flat_words(blank))
    (RAW / 'gap_sites.json').write_text(json.dumps(sites, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'缺字组 {len(sites)}', file=sys.stderr)


if __name__ == '__main__':
    sys.exit(main())
