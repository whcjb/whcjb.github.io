#!/usr/bin/env python3
"""达拉谟《雅歌之钥》提取：EEBO-TCP 人工录入本（TEI P5）→ markdown。

底本
----
`durham_raw/song/A37032.xml` —— EEBO-TCP Phase I，A37032（Wing D2802），
1668 年爱丁堡初版（Swintoun & Glen），**双人键入**，不是 OCR。CC0。
下载：https://raw.githubusercontent.com/textcreationpartnership/A37032/master/A37032.xml

TCP 录入员看不清的地方留了 `<gap>`，共 299 处（240 处单字母、25 处整词、
3 处整段、4 处外文）。补字表在 `durham_raw/song/gap_fills.tsv`，按文中出现
顺序编号，每条注明依据：
    ctx  上下文自明（单字母残缺，如 `per•ection`）
    ia   archive.org 1669 年伦敦本（与初版同页码）OCR 当第二证人，按前后文对齐取读
    img  看过 IA 原图
补字表条数必须与 gap 数一致，否则直接报错——TCP 文件若换了版本，编号会错位。

输出
----
`durham_raw/song/durham_song.md`，结构：
    <div durham-titlepage>        （书名页 + 枢密院许可，TCP front）
    # TO THE CHRISTIAN READER · JOHN OWEN   （1669 伦敦版欧文序，见 owen_preface()）
    # TO THE CHRISTIAN READER     （初版原有的序，他人所作）
    # CLAVIS CANTICI              （作者总论 + 结论）
    # CHAP. N                     （1–8 章）
    ### BRIDE.                    （原书说话人标记，有才出）
    ## Verses 1:5–6               （经节分段；锚点脚本按它铺锚）
    > **Vers. 5, 6.** 经文        （原书段首经文）

用法:
    python3 scripts/extract_durham_song.py
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'durham_raw' / 'song'
NS = '{http://www.tei-c.org/ns/1.0}'
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8}

# 补字后才拼得回来的断词（gap 正好落在行末断字处）
POST_FIX = [
    ('men tioned', 'mentioned'),        # gap 9
    ('Leba non', 'Lebanon'),            # gap 158
    ('from his of heart-purpose', 'from his heart-purpose'),   # gap 148，IA 原图无此词
    ('satisfied, , and', 'satisfied, and'),                      # gap 172，同上
]


def load_fills():
    fills = []
    for line in (RAW / 'gap_fills.tsv').read_text(encoding='utf-8').splitlines():
        if line.startswith('#') or not line.strip():
            continue
        k, fill, _src = line.split('\t', 2)
        assert int(k) == len(fills), f'补字表编号断档：{k}'
        fills.append(fill)
    return fills


def prepare(xml: str) -> str:
    fills = load_fills()
    gaps = list(re.finditer(r'<gap\b[^>]*>\s*<desc>[^<]*</desc>\s*</gap>', xml))
    if len(gaps) != len(fills):
        raise SystemExit(f'gap {len(gaps)} 处，补字表 {len(fills)} 条，对不上')
    out, pos = [], 0
    for m, fill in zip(gaps, fills):
        out += [xml[pos:m.start()], fill.replace('&', '&amp;').replace('<', '&lt;')]
        pos = m.end()
    out.append(xml[pos:])
    xml = ''.join(out)
    # 行末断字：`Instru<g EOLhyphen/>\nments` → Instruments
    xml = re.sub(r'<g ref="char:EOL(?:un)?hyphen"/>\s*', '', xml)
    # ▪ = TCP「看得出是标点、认不出是哪个」。后接大写或数字（`1 Cor▪ 13`）按句号，否则按逗号
    xml = re.sub(r'<g ref="char:punc">▪</g>(?=\s*[A-Z0-9])', '.', xml)
    xml = re.sub(r'<g ref="char:punc">▪</g>', ',', xml)
    return xml


def inline(el) -> str:
    """元素内文 → markdown 行内文本。<hi> 斜体，<pb> 落页码注释。"""
    parts = [el.text or '']
    for c in el:
        tag = c.tag.replace(NS, '')
        if tag == 'hi':
            t = inline(c)
            if c.get('rend') == 'sup':
                parts.append(t)
            elif t.strip():
                lead = t[:len(t) - len(t.lstrip())]
                trail = t[len(t.rstrip()):]
                parts.append(f'{lead}*{t.strip()}*{trail}')
        elif tag == 'pb':
            if c.get('n'):
                parts.append(f' <!-- PAGE {c.get("n")} --> ')
        else:
            parts.append(inline(c))
        parts.append(c.tail or '')
    return ''.join(parts)


def clean(t: str) -> str:
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'\*\s*\*', '', t)                    # 相邻斜体并段留下的空 **
    return t


def verse_label(n: str) -> str:
    return f'Verses {n.replace("-", "–")}' if '-' in n else f'Verse {n}'


def render_block(el, out, ch=None):
    for c in el:
        tag = c.tag.replace(NS, '')
        if tag == 'head':
            pass  # 由上层处理
        elif tag == 'p':
            t = clean(inline(c))
            # 花体首字母（decorInit）后的排字习惯：`BEfore` `THis` → Before / This
            t = re.sub(r'^([A-Z])([A-Z]+)(?=[a-z])', lambda m: m.group(1) + m.group(2).lower(), t)
            if t:
                out.append(t)
        elif tag == 'pb':
            if c.get('n'):
                out.append(f'<!-- PAGE {c.get("n")} -->')
        elif tag == 'epigraph':
            bibl = c.find(f'{NS}bibl')
            q = c.find(f'{NS}q')
            b = clean(inline(bibl)) if bibl is not None else ''
            qt = clean(inline(q)) if q is not None else ''
            out.append(f'> **{b}** {qt}'.strip())
        elif tag == 'trailer':
            out.append(f'<p style="text-align:center">{clean(inline(c))}</p>')
        elif tag == 'div':
            render_div(c, out, ch)
        elif tag in ('closer', 'signed'):
            out.append(f'<p style="text-align:right">{clean(inline(c))}</p>')
        else:
            t = clean(inline(c))
            if t:
                out.append(t)


def render_div(div, out, ch=None):
    typ = div.get('type')
    head = div.find(f'{NS}head')
    htxt = clean(inline(head)) if head is not None else ''
    if typ == 'chapter':
        m = re.match(r'CHAP\.\s*([IVX]+)', htxt)
        ch = ROMAN[m.group(1)]
        out.append(f'# CHAP. {ch}')
        render_block(div, out, ch)
    elif typ == 'verse':
        if htxt:                                     # 说话人标记：BRIDE. / Part 3. BRIDES Words.
            out.append(f'### {htxt}')
        out.append(f'## {verse_label(div.get("n"))} ({ch}:{div.get("n").replace("-", "–")})')
        render_block(div, out, ch)
    elif typ == 'conclusions':
        out.append(f'## {htxt}')
        render_block(div, out, ch)
    else:
        if htxt:
            out.append(f'## {htxt}')
        render_block(div, out, ch)


def title_page_html(body) -> str:
    """书名页 + 枢密院出版许可（TCP front）。

    初版（1668 爱丁堡）的原图拿不到（EEBO 影像要授权），版式只能照录入本的
    分段居中排，**不是照原图排**，页上注明。整块不留空行，免得 kramdown 拆块。
    """
    tp = next(d for d in body.iter(f'{NS}div') if d.get('type') == 'title_page')
    lic = next(d for d in body.iter(f'{NS}div') if d.get('type') == 'license')
    ps = [clean(inline(p)) for p in tp.findall(f'{NS}p')]
    md_em = lambda s: re.sub(r'\*([^*]+)\*', r'<em>\1</em>', s)
    epis = []
    for b, q in zip(tp.findall(f'{NS}bibl'), tp.findall(f'{NS}q')):
        epis.append(f'<p class="dtp-epi"><span>{clean(inline(b))}</span> {clean(inline(q))}</p>')
    lic_date = clean(inline(lic.find(f'{NS}head')))
    lic_p = md_em(clean(inline(lic.find(f'{NS}p'))))
    lic_sig = clean(inline(lic.find(f'.//{NS}signed')))
    title = re.sub(r'^Clavis Cantici:\s*OR, AN\s*', '', ps[0])
    return '\n'.join([
        '<div class="durham-titlepage" style="text-align:center;border:1px solid #d7cfe2;padding:28px 18px;margin:0 0 30px;background:#fff;">',
        '<p style="font-size:30px;letter-spacing:.06em;margin:0;">Clavis Cantici:</p>',
        f'<p style="font-size:15px;letter-spacing:.12em;margin:6px 0 0;">OR, AN<br>{title.replace("OF THE ", "OF THE<br>")}</p>',
        '<hr style="width:40%;margin:16px auto;border-color:#d7cfe2;">',
        f'<p style="margin:0;">{md_em(ps[1])}</p>',
        '<hr style="width:40%;margin:16px auto;border-color:#d7cfe2;">',
        *[e.replace('class="dtp-epi"', 'style="font-style:italic;font-size:13.5px;margin:6px 8%;"') for e in epis],
        '<hr style="width:40%;margin:16px auto;border-color:#d7cfe2;">',
        f'<p style="font-size:13.5px;margin:0;">{md_em(ps[2])}</p>',
        '<div style="font-size:12.5px;color:#666;border-top:1px dashed #d7cfe2;margin:22px auto 0;padding-top:12px;max-width:440px;">',
        f'<p style="margin:0 0 4px;">{lic_date}</p><p style="margin:0;">{lic_p}</p><p style="margin:4px 0 0;text-align:right;">{lic_sig}</p>',
        '</div>',
        '<p style="font-size:11.5px;color:#999;margin:18px 0 0;">书名页与出版许可据 EEBO-TCP 录入本（1668 年爱丁堡初版）；未见初版原图，版式非照原书排。</p>',
        '</div>',
    ])


def owen_preface():
    """欧文序：1669 年伦敦版新加，初版（TCP 底本）没有。

    底稿 owen_preface_base.txt 是 puritansermons.com 的现代拼写录入本，
    措辞逐页对过 IA 1669 伦敦本原图（leaf 2–5），改正见 owen_preface_fixes.tsv。
    """
    text = (RAW / 'owen_preface_base.txt').read_text(encoding='utf-8')
    for line in (RAW / 'owen_preface_fixes.tsv').read_text(encoding='utf-8').splitlines():
        if line.startswith('#') or not line.strip():
            continue
        old, new, _ = line.split('\t', 2)
        old, new = old.replace('\\n', '\n'), new.replace('\\n', '\n')
        if text.count(old) != 1:
            raise SystemExit(f'欧文序改正条目「{old}」在底稿中命中 {text.count(old)} 次（应为 1）')
        text = text.replace(old, new)
    paras = [p.strip() for p in text.split('\n\n') if p.strip()]
    *body_ps, close, sig = paras
    return ['# TO THE CHRISTIAN READER · JOHN OWEN',
            '*Prefixed by John Owen to the London edition of 1669; not in the Edinburgh first edition of 1668. '
            'Text from a modern-spelling transcription, collated for wording against the 1669 printing.*',
            *body_ps,
            f'<p style="text-align:right">{close}<br>{sig}</p>']


def main():
    xml = prepare((RAW / 'A37032.xml').read_text(encoding='utf-8'))
    root = ET.fromstring(xml)
    body = root.find(f'.//{NS}text')
    front = {d.get('type'): d for d in body.iter(f'{NS}div') if d.get('type') in ('to_the_reader', 'text')}

    out = [title_page_html(body)]
    out += owen_preface()
    out.append('# TO THE CHRISTIAN READER')
    render_block(front['to_the_reader'], out)

    # 作者总论：`text` div 里章之前的部分（含 conclusions）
    out.append('# CLAVIS CANTICI: A KEY OF THE SONG')
    out.append('*Useful for opening up thereof.*')
    text_div = front['text']
    chapters = []
    for c in text_div:
        tag = c.tag.replace(NS, '')
        if tag == 'div' and c.get('type') == 'chapter':
            chapters.append(c)
        elif tag != 'head':
            tmp = []
            if tag == 'div':
                render_div(c, tmp)
            else:
                wrapper = ET.Element('x'); wrapper.append(c)
                render_block(wrapper, tmp)
            out += tmp
    for c in chapters:
        render_div(c, out)

    md = '\n\n'.join(out) + '\n'
    for a, b in POST_FIX:
        n = md.count(a)
        if n != 1:
            raise SystemExit(f'POST_FIX「{a}」命中 {n} 次（应为 1）')
        md = md.replace(a, b)
    md = re.sub(r' +', ' ', md)
    md = re.sub(r' ([,;:])', r'\1', md)

    dst = RAW / 'durham_song.md'
    dst.write_text(md, encoding='utf-8')
    n_ch = len(re.findall(r'^# CHAP\.', md, re.M))
    n_v = len(re.findall(r'^## Verses? ', md, re.M))
    print(f'→ {dst.relative_to(ROOT)}  {n_ch} 章 / {n_v} 段经文 / {len(md.split()):,} 词')
    left = re.findall(r'〔|<gap|▪', md)
    if left:
        print(f'  ⚠ 残留 {len(left)} 处未处理标记', file=sys.stderr)


if __name__ == '__main__':
    sys.exit(main())
