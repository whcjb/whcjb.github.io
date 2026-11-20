#!/usr/bin/env python3
"""皮尔森《苦难中的大鼓励》诗篇 84、85、87 篇三篇讲解 → pierson/psalm84|85|87/（英文版），底本 1868 年 Nichol 重印本 OCR。

    python3 scripts/publish_pierson_ocr.py

1647 年原版（EEBO-TCP A54870）只录了第一篇（诗篇 27 篇，见 publish_tcp_psalm.py 的 pierson-psalm27），其余三篇
（原书各自单独编页）TCP 没有，故用 1868 年 Nichol 合订本（IA davidsblessedman00smit）OCR；清理链与古治同
（publish_gouge_psalm116.py 的 assemble/clean/render），只是没有 TCP 第三证人。

切页：段首「Ver. N.」的 N 大于本页已讲到的最大节号才起新页；新标题紧接上一个标题、中间没有正文（如诗 84 第 83 页 5、6、7 节连引）
就并成一页；不大于最大节号的重引（诗 85「Ver. 1.」两次、「Ver. 6.」）只当经文小标题。页名取「起始节号—下一页起始节号减一」。
诗 84 的讲解只到第 10 节（出版者附言说明是讲稿只完整到这里），附言作为该篇末页；诗 85 前有哈维（Christopher Harvey）的献辞。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nichol1868_ocr as n            # noqa: E402
import publish_tcp_psalm as tp        # noqa: E402
import publish_gouge_psalm116 as g    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'pierson_raw' / 'psalms'
C0, C1 = '#1f3a7a', '#354aa0'
PSALMS = {
    84: dict(P='p84', pages=(189, 220), stop='POSTSCRIPT', last=12, title_en="David's Heart's Desire: An Exposition of Psalm LXXXIV",
             back=('postscript', 'A Postscript by the Publisher to the Readers', '出版者附言', 220, 221, 'POSTSCRIPT')),
    85: dict(P='p85', pages=(223, 268), last=13, title_en="The Church's Exercise under Affliction: An Exposition of Psalm LXXXV",
             front=('dedication', 'The Epistle Dedicatory (Christopher Harvey)', '献辞', 222, 222, None)),
    87: dict(P='p87', pages=(269, 296), last=7, title_en='The Great Charter of the Church: An Exposition of Psalm LXXXVII'),
}


def vnum(plain):
    """「Ver. 5, 6.」→ (5, 6)；不是节标题 → None。"""
    m = re.match(r'Ver[.,s]*\s*([\dILl]+(?:\s*,\s*\d+)*)', plain)
    if not m:
        return None
    ns = [int(x.replace('I', '1').replace('L', '1').replace('l', '1')) for x in re.findall(r'[\dILl]+', m.group(1))]
    return ns[0], ns[-1]


def split(stream, last):
    units, cur, label0, mx, body_since = [], [], 'title', 0, 0
    for x in stream:
        plain = re.sub(r'<[^>]+>', '', x['text']).replace(n.IT_ON, '').replace(n.IT_OFF, '').strip()
        vv = vnum(plain) if x['kind'] == 'body' else None
        v = vv[0] if vv else None
        if v and v > mx:
            if cur and body_since < 500 and label0 != 'title':      # 连引：并进当前页
                mx = vv[1]
                cur.append(x)
                continue
            if cur:
                units.append([label0, cur])
            cur, label0, mx, body_since = [], v, vv[1], 0
            cur.append(x)
            continue
        if x['kind'] == 'body' and not v:
            body_since += len(plain)
        cur.append(x)
    units.append([label0, cur])
    # 标题页（第一个 Ver. 之前的诗题）并进第一节
    if units[0][0] == 'title' and len(units) > 1:
        units[1][1] = units[0][1] + units[1][1]
        units.pop(0)
    out = []
    for i, (a, xs) in enumerate(units):
        b = (units[i + 1][0] - 1) if i + 1 < len(units) else None
        out.append((a, b, xs))
    return out


def main():
    tcp = ([], {})
    for ps, c in PSALMS.items():
        g.P = c['P']                       # render/md/heb 用模块级 P
        log = []
        stream = g.assemble(c['pages'][0], c['pages'][1], tcp, log)
        if c.get('stop'):                  # 诗 84 末页：附言大字标题处截断
            k = next(i for i, x in enumerate(stream) if x['kind'] == 'big' and c['stop'] in x['text'].upper())
            stream = stream[:k]
        units = split(stream, c['last'])
        U = []
        for a, b, xs in units:
            label = str(a) if not b or b == a else f'{a}–{b}'
            pg = [x['page'] for x in xs if x['page']]
            U.append(dict(verse=label, part=None, pages=(min(pg), max(pg)) if pg else None, contents=[],
                          md=g.apply_fixes(g.render(xs), RAW / f'psalm{ps}' / 'fixes.tsv'), slug=f'v{label.replace("–", "-")}',
                          name=None))
        fronts, backs = [], []
        for key, acc in (('front', fronts), ('back', backs)):
            if c.get(key):
                slug, en, zh, a, b, start = c[key]
                st = g.assemble(a, b, tcp, log)
                if start:
                    k = next(i for i, x in enumerate(st) if x['kind'] == 'big' and start in x['text'].upper())
                    st = st[k:]
                acc.append(dict(slug=slug, title=en, zh=zh, md=g.apply_fixes(g.render(st), RAW / f'psalm{ps}' / 'fixes.tsv')))
        g.fix_report()
        g.FIXHITS.clear()
        tot = bad = 0
        for u in U:
            bb, cc = n.nonwords(re.sub(r'<[^>]+>', ' ', u['md']))
            tot += cc
            bad += len(bb)
        print(f'诗 {ps}：', [u['verse'] for u in U], f'{tot} 词，残余非词 {bad / max(tot, 1):.2%}，未决真词互换 {len(log)}')
        cfg = dict(tcp='—', author='pierson', book=f'psalm{ps}', P=c['P'], c0=C0, c1=C1, psalm=ps, year='1868',
                   short=f'Pierson on Psalm {ps}', hero=f'Psalm {ps}', title_en=c['title_en'],
                   tagline=f'Thomas Pierson · {c["title_en"].split(":")[0]}',
                   edition='First published in Excellent Encouragements against Afflictions, London 1647 · '
                           'text of the Edinburgh reprint, James Nichol, 1868',
                   about_full=True, omitted_en='', omitted_zh='',
                   about_en=ABOUT_EN + (NOTE84_EN if ps == 84 else ''), about_zh=ABOUT_ZH + (NOTE84_ZH if ps == 84 else ''))
        tp.write_layouts(f'pierson-psalm{ps}', cfg, force='--layouts' in sys.argv)
        tp.publish(f'pierson-psalm{ps}', cfg, fronts, U, backs, {}, ROOT / 'pierson' / f'psalm{ps}',
                   f'/pierson/psalm{ps}/', RAW / f'psalm{ps}')


ABOUT_EN = ("Pierson's expositions of Psalms 27, 84, 85 and 87 were published after his death by Christopher Harvey as "
            "Excellent Encouragements against Afflictions (London, 1647), each with its own title page and pagination. "
            "Only the first, on Psalm 27, survives in a keyed transcription (EEBO-TCP); this one is given from the Edinburgh "
            "reprint of 1868 (Nichol's Series of Commentaries), read by OCR from the Princeton copy (Internet Archive "
            "davidsblessedman00smit) and checked against a second, independent OCR. Each verse, or group of verses as "
            "Pierson handles them, is one page; the notes at the foot of the 1868 pages are collected at the end of each "
            "page, and its page numbers are marked in the text. Hebrew and Greek words, which OCR cannot read, are marked "
            "in red. OCR errors still remain, chiefly in italic passages; they are being corrected against the page images.")
ABOUT_ZH = ("皮尔森讲诗篇 27、84、85、87 篇的四篇讲解，在他身后由哈维（Christopher Harvey）编成《苦难中的大鼓励》（伦敦 1647）出版，"
            "四篇各有扉页、各自编页。只有第一篇（诗篇 27 篇）有 EEBO-TCP 录入本；本篇据 1868 年爱丁堡 Nichol《清教徒注释丛书》重印本，"
            "用普林斯顿藏本扫描件（IA davidsblessedman00smit）OCR 识读，并与另一份独立 OCR 对照校过。按皮尔森的讲法，每节（或几节合讲）一页；"
            "1868 年版页脚的注收在各页之末，文中标出该版页码。希伯来文、希腊文 OCR 读不出，以红字标出。目前仍有 OCR 错误，主要在斜体段落，正在对照页面影像逐页校正。")
NOTE84_EN = (" The exposition of Psalm 84 breaks off after verse 10: the publisher's postscript explains that the author's "
             "copy was perfect only so far.")
NOTE84_ZH = "诗篇 84 篇的讲解到第 10 节为止：出版者在附言里说明，作者的讲稿只完整到这里。"

if __name__ == '__main__':
    main()
