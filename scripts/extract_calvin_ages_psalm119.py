#!/usr/bin/env python3
"""加尔文《诗篇 119 篇讲章》AGES PDF → calvin_sermons_raw/psalm119/units.json（结构与 extract_calvin_sermons.py 相容）

    /usr/bin/python3 scripts/extract_calvin_ages_psalm119.py      # PyMuPDF 只装在系统 python 上

底本 ~/Documents/论文/calvin/CAL_S119.pdf（AGES Digital Library，sabda.org alkitab-7/LIBRARY/CALVIN/CAL_S119.PDF，326 页）：
Old Paths Publications 1996 年据 1580 年 Thomas Stocker 英译本重排、改现代拼法的版本（扉页 © 1996 All Rights Reserved；
用户 2026-11-19 明确选定用此版而非 EEBO-TCP A17724）。p3–6 出版者说明、p7–11 现代序言是 1996 年新写的，不收。

版面规则（逐页实测）：
  · 单列，正文 x≈26，12pt。段内行距 15pt，段间 ≥ 22pt → 新段。每页首行 y≈26，跨页：上页末行右缘 < 330 且以句末标点收尾 → 新段，
    否则接上页末段。
  · 字色：红斜体 #800000 = 经文引语 → *…*；黑斜体 = 1996 版在古词后加的方括号释义 [..] → *…*（与原文斜体同样照录）；
    8pt 红/朱 `<NNNNNN>` 经文锚点一律丢，引文出处（如「Isaiah 53:6)」）留着。
  · 段首小型大写：12pt 首字母 + 9pt 余字（B+ELOVED）→ 首字母作 .cs-dropcap，其余照大写。
  · 篇首：24pt 蓝「THE … SERMON」、绿 16pt「M. JOHN CALVIN」、黑粗体标题、斜体「The … eight Verses upon」、粗体字母名（ALEPH）；
    随后经文框：红粗体节号（x≈26）+ 藏青经文（x≈76），节号行起新节。
"""
import json
import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
PDF = Path.home() / 'Documents' / '论文' / 'calvin' / 'CAL_S119.pdf'
RAW = ROOT / 'calvin_sermons_raw' / 'psalm119'
RED, NAVY, BLUE, GREEN = 0x800000, 0x000080, 0x0000d4, 0x006411
FRONT = [('title', 'Title Page', 2, 2), ('dedication', 'The Epistle Dedicatory', 12, 13),
         ('to-the-reader', 'To All Faithful Readers', 14, 14)]
SERMON_START = [15, 30, 44, 57, 71, 86, 101, 117, 131, 145, 159, 172, 185, 199, 213, 227, 240, 256, 270, 284, 298, 313]
LAST = 326
PARA_GAP = 20


def lines_of(page):
    """页内按 y 合并成行（锚点会把一行劈开），每行是 [(text, size, color, italic, bold, x0, x1)]。"""
    spans = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if not s['text']:
                    continue
                if s['size'] < 8.5 and re.fullmatch(r'\s*<[0-9A-F@]{6,8}>\s*', s['text']):
                    continue                      # 经文锚点
                spans.append((s['bbox'][1], s['bbox'][0], s))
    spans.sort(key=lambda t: (round(t[0]), t[1]))
    rows = []
    for y, x, s in spans:
        if rows and abs(rows[-1][0] - y) < 4:
            rows[-1][1].append(s)
        else:
            rows.append([y, [s]])
    out = []
    for y, ss in rows:
        ss.sort(key=lambda s: s['bbox'][0])
        out.append(dict(y=y, x0=ss[0]['bbox'][0], x1=ss[-1]['bbox'][2], spans=ss))
    return out


def span_md(ss):
    """一行 span → markdown：斜体包 *…*，空白不入斜体。"""
    parts = []
    for s in ss:
        t = s['text'].replace('*', '\\*')
        ital = bool(s['flags'] & 2) and not (s['flags'] & 16) and t.strip()
        parts.append((t, ital))
    out, cur, buf = [], None, ''
    for t, it in parts + [('', None)]:
        if it != cur and buf:
            out.append((buf, cur))
            buf = ''
        cur = it
        buf += t
    md = ''
    for t, it in out:
        if it:
            lead = t[:len(t) - len(t.lstrip())]
            trail = t[len(t.rstrip()):]
            md += f'{lead}*{t.strip()}*{trail}'
        else:
            md += t
    return md.replace('**', '')


def join(a, b):
    if not a:
        return b
    if a.endswith('-') and not a.endswith(' -'):
        return a + b.lstrip()
    return a.rstrip() + ' ' + b.lstrip()


def dropcap(ss):
    """段首 12pt 首字母 + 9pt 小型大写 → .cs-dropcap；返回替换后的 md，若不是此形制返回 None。"""
    if len(ss) > 1 and len(ss[0]['text'].strip()) == 1 and ss[0]['text'].isupper() and round(ss[1]['size']) == 9:
        rest = ''.join(s['text'] for s in ss[1:])
        return f'<span class="cs-dropcap">{ss[0]["text"]}</span>' + rest
    return None


def prose(doc, p0, p1, skip_head=None):
    """p0–p1 页（1 起）正文 → 段落 md 列表。skip_head(page_idx, row) 为 True 的行跳过（篇首、经文框）。"""
    paras, cur = [], ''
    prev = None
    for pno in range(p0 - 1, p1):
        rows = lines_of(doc[pno])
        first = True
        for r in rows:
            if skip_head and skip_head(pno, r):
                continue
            ss = r['spans']
            dc = dropcap(ss) if not cur or (prev and r['y'] - prev['y'] > PARA_GAP) else None
            md = dc if dc is not None else span_md(ss)
            if prev is None:
                new = True
            elif first:
                t = ''.join(s['text'] for s in prev['spans']).rstrip()
                new = prev['x1'] < 330 and t[-1:] in '.?!:”’)'
            else:
                new = r['y'] - prev['y'] > PARA_GAP or dc is not None
            if new and cur:
                paras.append(cur.strip())
                cur = ''
            cur = join(cur, md)
            prev, first = r, False
    if cur:
        paras.append(cur.strip())
    # 经文引语被黑色标点劈成几段斜体（*a*: *b*.）→ 合成一段
    return [re.sub(r'\*([,:;.?!]?\s*)\*', r'\1', p) for p in paras]


def sermon(doc, n, p0, p1):
    page0 = lines_of(doc[p0 - 1])
    head, verses, body_y = [], [], None
    for r in page0:
        ss = r['spans']
        col = ss[0]['color']
        if col == RED and ss[0]['flags'] & 16 and ss[0]['text'].strip().isdigit():
            verses.append([int(ss[0]['text']), ''.join(s['text'] for s in ss[1:]).strip()])
        elif any(s['color'] == NAVY for s in ss) and verses:
            verses[-1][1] = join(verses[-1][1], ''.join(s['text'] for s in ss).strip())
        elif not verses:
            head.append(''.join(s['text'] for s in ss).strip())
        else:
            body_y = r['y']
            break
    for v in verses:
        v[1] = re.sub(r'\s+([:;,.?!])', r'\1', re.sub(r'\s+', ' ', v[1])).strip()
    paras = prose(doc, p0, p1, skip_head=lambda pno, r: pno == p0 - 1 and r['y'] < body_y)
    if n == 22 and paras[-1].endswith(' FINIS'):        # 末页居中的 FINIS 与末段同页、段距不足，单拆
        paras = paras[:-1] + [paras[-1][:-6], '<p class="cs-center">FINIS</p>']
    letter = {'NVN': 'Nun'}.get(head[-1], head[-1].title())          # 字母名照书上拼法（Vav、Iod、Schyn、Thav…；NVN 即 Nun）
    title = re.sub(r'\s+', ' ', ' '.join(head[:-1]))
    first, last = verses[0][0], verses[-1][0]
    assert last - first == 7 and first == 8 * (n - 1) + 1, (n, first, last)
    vbox = ' '.join(f'<b class="cs-vn">{v}</b> {t}' for v, t in verses)
    md = (f'<p class="cs-head" markdown="1">{title}<br>{head[-1]}</p>\n\n'
          f'<div class="cs-text" markdown="1">\n\n{vbox}\n\n</div>\n\n' + '\n\n'.join(paras))
    words = len(re.findall(r"[A-Za-z']+", ' '.join(paras)))
    ordn = re.sub(r'\s+OF$', '', head[0]).title().replace('-S', '-s')        # THE TWENTY-FIRST SERMON OF → The Twenty-first Sermon
    return dict(num=n, head=f'{ordn} · {letter}',
                letter=letter, chapter=119, chapter2=None, verses=[first, last], lost=0, words=words, md=md,
                same_text=True)


def main():
    doc = fitz.open(PDF)
    assert len(doc) == LAST, len(doc)
    front = []
    for slug, title, p0, p1 in FRONT:
        paras = prose(doc, p0, p1)
        if slug == 'title':
            paras = [f'<p class="cs-center">{" ".join(paras)}</p>']
        front.append(dict(slug=slug, title=title, md='\n\n'.join(paras)))
    sermons = []
    for i, p0 in enumerate(SERMON_START):
        p1 = SERMON_START[i + 1] - 1 if i + 1 < len(SERMON_START) else LAST
        sermons.append(sermon(doc, i + 1, p0, p1))
    RAW.mkdir(parents=True, exist_ok=True)
    u = dict(book='psalm119', source='AGES CAL_S119.PDF', front=front, sermons=sermons, merged={}, gaps={})
    (RAW / 'units.json').write_text(json.dumps(u, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'psalm119: 卷首 {len(front)} 页，讲章 {len(sermons)} 篇，'
          f'{sum(s["words"] for s in sermons)} 词 → {RAW / "units.json"}')


if __name__ == '__main__':
    main()
