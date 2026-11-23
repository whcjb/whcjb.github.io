#!/usr/bin/env python3
"""布里奇斯《传道书释义》英文版：bridges_raw/ecclesiastes/src/preceptaustin.html → bridges/ecclesiastes/

    python3 scripts/publish_bridges_ecclesiastes_en.py

底本：Precept Austin 所刊录入本（标 Public Domain），据 New York: Robert Carter & Brothers, 1860。
  - Monergism Books 2022 电子版是同一份录入（逐词比对只差 Precept Austin 把「Ib.」「Chap.」展开成了书卷名），
    但它文末声明版权、禁止转载，不用。
  - 两份录入都删掉了原书脚注，正文里只剩孤立的角标数字（「mastered it.2」「name4」），共 73 处，这里一并去掉。
    角标判据：紧贴在字母或收尾标点后的 1–2 位数，后面不接数字、冒号、连字号——经文出处「12:24」「Ps. 51」都不会命中。
  - 原书没有斜体保留下来（录入本里经文段也是平排），照录。
  - 校勘证人：archive.org 上 1860 年版的两份独立扫描（expositionofbook00bridrich、expositionofbook00brid_0）
    的 OCR。录入本与两份 OCR 逐词对齐，**两份 OCR 一致而录入本不同**的地方逐条看过，见 FIXES。
    原书经文出处用罗马数字章号（vi. 23），录入本改成了阿拉伯数字（6:23），「bloud」改成了「blood」，这类照录入本不动。
处理：
  - 段：<p> 与 <br> 都是分段（录入本用 <br> 分隔同一 <p> 里的几段）；
    例外是诗行——同一 <p> 里各段都短于 90 字的是一首诗（或落款），各行以 <br> 相接成一段，
    末行若是出处（「Olney Hymns, iii. 48.」「Task, Book iv.」）另起一段右对齐；
  - 以「N. 」起头的段是经文段，可能连排几节（「4. … 5. … 6. …」），按节号拆出 <span class="bg-vnum">；
  - 一章一页，序言一页；书末索引（INDEX）不收。
版式照原书（用户 2026-11-23：「排版按照原文 pdf 整理，但是首行不要缩进」）：
  - 经文段斜体连排，节号正体带句点（「4. One generation…」），续行悬挂缩进，不加底色框（.ec-verse）；
  - 引诗整首居中、正体；四行一节的短行赞美诗偶数行缩进；出处斜体靠诗的右缘（.ec-poem / .ec-src）；
  - 录入本里的全大写词（段首「THESE」、「Royal PREACHER」）原书是小型大写，转 .ec-sc；罗马数字不转；
    每章第一个解经词原书都是小型大写，录入本第 7、8、10 章没保留，按规则补；
  - 章题用罗马数字（Chapter I.）；
  - 段首不缩进（原书缩进），段间靠段距分隔。
  原书的行内斜体（*words*、*the Preacher*）录入本没有保留，无从恢复。
"""
import html
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'bridges_raw' / 'ecclesiastes' / 'src' / 'preceptaustin.html'
OUT = ROOT / 'bridges' / 'ecclesiastes'
BASE = '/bridges/ecclesiastes'
BOOK = 'Bridges on Ecclesiastes'
# 每条必须原样命中一次。三类：
#   - 节号：原书 6:11 经文段一直排到 6:12 末尾、不印「12.」（对照 1860 年扫描本 p. 168），录入本照原书；
#     这里按 KJV 分节补回节号与锚点，但渲染成「[12.]」标明是编者所补（EDITORIAL_VERSES）；
#   - 录入错（两份扫描 OCR 一致、与录入本不同，原书是对的）；
#   - 原书排印错（两份 OCR 与录入本一致，原书就这么印：instrinsically、ecclesiastial、unchangable、
#     buisness、secrect、widsom、mumutual、excercise、iminent；fourth→forth 是逐页对照时看出的），径改。
#   古拼法（phrenzy、recompence、secresies、merchandize）、拉丁词、estuations（aestuation 本有其词）、
#   「a stern chubbishness」（两份 OCR 同）一概不动。
FIXES = [('what is man the better? For who knoweth', 'what is man the better? 12. For who knoweth'),   # 6:12
         ('The thing that hath, been,', 'The thing that hath been,'),                               # 1:9
         ('Is there anthing whereof', 'Is there anything whereof'),                                 # 1:10
         ('Our buisness is', 'Our business is'),
         ('his dcceptable words', 'his acceptable words'),
         ('All ecclesiastial revolutions', 'All ecclesiastical revolutions'),
         ('the excercise, the more', 'the exercise, the more'),
         ('appeared to be iminent', 'appeared to be imminent'),
         ('Things instrinsically excellent', 'Things intrinsically excellent'),
         ('in mumutual forbearance', 'in mutual forbearance'),
         ('come not thou into his secrect', 'come not thou into his secret'),
         ('an unchangable, covenant-keeping', 'an unchangeable, covenant-keeping'),
         ('‘vcnom must there be', '‘venom must there be'),
         ('Natural widsom', 'Natural wisdom'),
         ('(lb. 8:22)', '(Ib. 8:22)'),
         # —— 以下为录入错，括号里是两份扫描 OCR 的读法 ——
         ('never be broken dawn', 'never be broken down'),
         ('lest if should make', 'lest it should make'),
         ('but be that is slow to anger', 'but he that is slow to anger'),               # Prov. 15:18
         ('ringing in his cars', 'ringing in his ears'),
         ('Hasten thy coining', 'Hasten thy coming'),
         ('Romove sorrow', 'Remove sorrow'),
         ('little power for goof', 'little power for good'),
         ('Wharever God can be found', 'Wherever God can be found'),
         ('God will call thee judgment', 'God will call thee to judgment'),
         ('pleasure vast which of money', 'pleasure vast sums of money'),
         ('devil’s work; make religion', 'devil’s work; makes religion'),
         ('touches our I foundation', 'touches our foundation'),                         # 录入本多出的孤立「I」
         ('the greatest I good', 'the greatest good'),
         ('Who can I forbear', 'Who can forbear'),
         # —— 抽查第 6 章逐页对照扫描本后，按同类全书扫出的（2026-11-23）——
         ('(Job 3:19. Chap. 3:20.)', '(Job 3:19. Ecclesiastes 3:20.)'),     # 全书唯一一处没展开的 Chap.
         ('one flesh pleasing indulgence', 'one flesh-pleasing indulgence'),
         ('his words—’Here by then', 'his words—‘Hereby then'),            # 原书行尾断「Here- by」；开引号打反
         ('the proverb—’A place', 'the proverb—‘A place'),                  # 开引号打反（全书扫「空格/破折号 + ’ + 字母」）
         ('the matter—’After Solomon', 'the matter—‘After Solomon'),
         # 标点：两份 OCR 都有、录入本没有的 ; ? 与开引号（三方按词对齐比较词间标点）
         ('Save me from the foolish exchange’', 'Save me from ‘the foolish exchange’'),
         ('thy choice for me not mine', 'thy choice for me; not mine'),
         ('opened “as a morning', 'opened as “a morning'),
         ('results are grief and sorrow.', 'results are grief and sorrow?'),
         ('as good music, the flowers', 'as good music; the flowers'),
         # —— 抽查第 11 章逐页对照扫描本后，按同类全书扫出的（2026-11-23）——
         ('pours fourth a', 'pours forth a'),                                  # 原书排印错（真词误植，拼写扫描查不出）
         ('self-will’ no indulgence', 'self-will, no indulgence'),            # 逗号错录成 ’（全书扫「’ + 空格 + 小写」对 OCR）
         ('He adds,‘A man', 'He adds, ‘A man'),                               # 标点与引号间缺空格（全书扫）
         ('hedge of thorns”or', 'hedge of thorns” or'),
         ('in the end.’Learn', 'in the end.’ Learn'),
         # 破折号与逗号：三方按词对齐，录入本多出 / 缺少而两份 OCR 一致的
         ('discouragements.—Though', 'discouragements. Though'),
         ('oblivion than remembrance, shows', 'oblivion than remembrance; shows'),
         ('recollection of and gratitude for,', 'recollection of, and gratitude for,'),
         ('Wherefore, I praised', 'Wherefore I praised'),                     # 4:2
         ('“held, his peace”', '“held his peace”'),
         ('What, mischief it', 'What mischief it'),
         ('for constant, remembrance', 'for constant remembrance'),
         # —— 抽查第 9 章逐页对照扫描本后，按同类全书扫出的（2026-11-23）——
         # 经文出处：录入本把原书罗马数字章号转阿拉伯数字时转错（l=50 当成 1 等）。全书 897 条出处
         # 按上文定位到两份 OCR 的对应出处、罗马数字转换后比章节号，不一致的逐条按经文内容核定
         ('resting-place.” (Jer. 1:6.)', 'resting-place.” (Jer. 50:6.)'),      # 原书 l. 6
         ('(Prov. 10:21; Isa. 1:4.)', '(Prov. 10:21; Isa. 50:4.)'),           # 原书 l. 4（the tongue of the learned）
         ('(Comp. 2 Cor. 4:10.)', '(Comp. 2 Cor. 6:10.)'),                   # as having nothing
         ('(Gen. 2:18. Comp. Ps. 48:6.)', '(Gen. 2:18. Comp. Ps. 68:6.)'),   # setteth the solitary in families
         ('“labourer.” (John 6:21.)', '“labourer.” (John 6:27.)'),           # 原书 vi. 27（p. 282 页图）
         # 漏掉的收尾引号：两份 OCR 该处有引号的，裁原书页图逐条看，多数是脚注角标（本站已删），以下 4 处原书确有 ’
         ('to make an experiment. But', 'to make an experiment.’ But'),
         ('school of the breast.', 'school of the breast.’'),
         ('rich mine of satisfaction. But', 'rich mine of satisfaction.’ But'),
         ('present duties. Every moment', 'present duties.’ Every moment')]
# 经文段里的边注异读（marg.、M. R.、Heb.）原书排正体，夹在斜体经文中；KJV 本身的括号（saith the Preacher）仍斜体
MARGINAL = re.compile(r'\([^()]*(?:marg\.|M\. R\.|Heb\.)[^()]*\)')
EDITORIAL_VERSES = {(6, 12)}
POEM_SRC = re.compile(r'Hymns|Task, Book|Lyra Germanica')
# 逗号后只认「字母/引号 + 逗号 + 数字」（「love,3」）；冒号不认——「22:30」的 30 会被误删
FN = re.compile(r"(?:(?<=[A-Za-z.;!?’”'\"\)—])|(?<=[A-Za-z’”],))\d{1,2}(?![\d:–\-])(?=[\s,.;—)’”]|$)")


def paras(src):
    a = src.find('PREFACE</')
    a = src.rfind('<p', 0, a)
    z = src.find('INDEX', a)
    out = []
    for p in re.findall(r'(?s)<(?:p|h2)[^>]*>(.*?)</(?:p|h2)>', src[a:z]):
        segs = [html.unescape(re.sub(r'<[^>]+>', '', s)).replace('\xa0', ' ') for s in re.split(r'<br\s*/?>', p)]
        segs = [re.sub(r'\s+', ' ', s).strip() for s in segs]
        segs = [s for s in segs if s]
        if not segs:
            continue
        if re.match(r'^Hinton Martell Rectory', segs[0]):       # 序言落款三行
            out.append(('sign', segs))
            continue
        if len(segs) >= 2 and all(len(s) < 90 for s in segs):  # 诗行
            src_line = segs.pop() if POEM_SRC.search(segs[-1]) else None
            out.append(('poem', (segs, src_line)))
            continue
        out += [('p', s) for s in segs]
    return out


def verse_html(t, ch=0):
    """「4. text 5. text」→ 每节一个节号。节号只在句末标点或段首之后认，免得把正文数字当节号。"""
    parts = re.split(r'(?:^|(?<=[.;:?!’”)—]) )(\d{1,2})\. ', t)
    out, first = [], None
    for k in range(1, len(parts), 2):
        n, body = parts[k], parts[k + 1].strip()
        first = first or n
        num = f'[{n}.]' if (ch, int(n)) in EDITORIAL_VERSES else f'{n}.'
        body = MARGINAL.sub(lambda m: f'<span class="ec-rom">{m.group(0)}</span>', body)
        out.append(f'<span class="ec-vn" id="v{n}">{num}</span> {body}')
    return first, ' '.join(out), int(parts[-2])


ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII']
CAPS = re.compile(r"\b(?![IVXLC]+\b)([A-Z])([A-Z][A-Z’']*)\b(?![a-z’])")


def sc(t):
    """全大写词 → 小型大写（首字母保持大写，其余小写交给 font-variant）。"""
    return CAPS.sub(lambda m: f'<span class="ec-sc">{m.group(1)}{m.group(2).lower()}</span>', t)


def poem_html(lines, src_line):
    esc = [sc(html.escape(FN.sub('', x), quote=False)) for x in lines]
    alt = len(esc) % 4 == 0 and all(len(x) < 45 for x in lines)    # 四行一节的赞美诗：偶数行缩进
    refrain = len(esc) == 5 and lines[4].startswith('Make haste, O man')   # Bonar「Make haste」：四行 + 叠句（p. 274）
    rows = [f'<span class="ec-in">{x}</span>' if (alt or refrain) and i % 2 else x for i, x in enumerate(esc)]
    if refrain:
        rows[4] = f'<span class="ec-in2">{esc[4]}</span>'
    if src_line:
        rows.append(f'<span class="ec-src">{html.escape(src_line, quote=False)}</span>')
    return '<p class="ec-poem">' + '<br>'.join(rows) + '</p>'


def main():
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    pages, cur, removed = [], None, 0
    src = SRC.read_text(encoding='utf-8')
    for a, b in FIXES:
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    for kind, t in paras(src):
        if kind == 'poem':
            cur['out'].append(poem_html(*t)); continue
        if kind == 'sign':
            cur['out'].append('<p class="bg-center">' + '<br>'.join(html.escape(x, quote=False) for x in t) + '</p>'); continue
        if t == 'PREFACE':
            cur = dict(slug='preface', label='Preface', sub='', out=[]); pages.append(cur); continue
        if t == 'EXPOSITION OF ECCLESIASTES':
            continue
        m = re.fullmatch(r'CHAPTER (\d+)', t)
        if m:
            n = int(m.group(1))
            cur = dict(slug=str(n), label=f'Chapter {ROMAN[n]}', n=n, out=[], last=0); pages.append(cur); continue
        t, k = FN.subn('', t)
        removed += k
        t = sc(html.escape(t, quote=False))
        if cur.get('n') and re.match(r'^\d{1,2}\. ', t):
            _, body, last = verse_html(t, cur['n'])
            cur['last'] = max(cur['last'], last)
            cur['out'].append(f'<p class="ec-verse">{body}</p>')
        else:
            # 原书每章（含序言）第一个解经词是小型大写；录入本只在部分章保留了全大写，这里统一补
            if not cur.get('sc_done'):
                cur['sc_done'] = True
                if 'ec-sc' not in t[:60]:
                    t = re.sub(r'^([‘“]?)([A-Za-z]+)', r'\1<span class="ec-sc">\2</span>', t, count=1)
            cur['out'].append(f'<p>{t}</p>')
    for p in pages:
        if 'n' in p:
            p['sub'] = f'Ecclesiastes {p["n"]}:1–{p["last"]}'
    OUT.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(pages):
        f = OUT / f'{p["slug"]}.md'
        m = re.search(r'^date: (.+)$', f.read_text(encoding='utf-8'), re.M) if f.exists() else None
        fm = ['---', 'layout: bridges-psalm119-chapter', 'book_id: ecclesiastes', f'book_name: "{BOOK}"',
              f'title: "{p["label"]}"'] + ([f'subtitle: "{p["sub"]}"'] if p['sub'] else []) + \
             [f'date: {m.group(1) if m else stamp}']
        if 'n' in p:
            fm.append(f'chapter: {p["n"]}')
        if (OUT / 'zh' / f'{p["slug"]}.md').exists():          # 已有中译：英文页放「中文版 →」
            fm.append(f'zh_url: "{BASE}/zh/{p["slug"]}/"')
        if i:
            fm += [f'prev_url: "{BASE}/{pages[i-1]["slug"]}/"', f'prev_label: "{pages[i-1]["label"]}"']
        if i + 1 < len(pages):
            fm += [f'next_url: "{BASE}/{pages[i+1]["slug"]}/"', f'next_label: "{pages[i+1]["label"]}"']
        fm.append('---')
        f.write_text('\n'.join(fm) + '\n\n' + '\n\n'.join(p['out']) + '\n', encoding='utf-8')
    toc = '\n'.join(f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/{p["slug"]}/">'
                    + (f'<span class="bg-no">{p["label"]}</span>Verses 1–{p["last"]}' if 'n' in p else p['label'])
                    + '</a></li>' for p in pages)
    (OUT / 'index.html').write_text(f'''---
layout: bridges-psalm119-book
book_id: ecclesiastes
book_name: "An Exposition of the Book of Ecclesiastes"
author: "Charles Bridges (1794–1869)"
edition: "New York: Robert Carter & Brothers, 1860"
title: "{BOOK}"
{'zh_url: "' + BASE + '/zh/"' + chr(10) if (OUT / 'zh' / 'index.html').exists() else ''}---
<ul class="bg-toc">
{toc}
</ul>
<div class="bg-note">
<p><b>About this text.</b> The text follows the public-domain transcription of the 1860 New York edition (Robert Carter &amp; Brothers)
published by Precept Austin. The transcription does not preserve the author’s footnotes; the stray reference figures it left in the text
have been removed. Where the printed book has “Ib.” or “Chap.” in Scripture references, the transcription gives the name of the book.
The index at the end of the volume is not reproduced.</p>
<p class="bg-note-zh"><b>文本说明。</b>正文据 Precept Austin 刊布的公有领域录入本，所据为 1860 年纽约 Robert Carter &amp; Brothers 版。
录入本未收作者脚注，正文残留的注号已删去；原书经文出处中的「Ib.」「Chap.」，录入本已改写为书卷名。书末索引未收。</p>
</div>
''', encoding='utf-8')
    print(len(pages), 'pages;', removed, 'stray footnote figures removed')


if __name__ == '__main__':
    main()
