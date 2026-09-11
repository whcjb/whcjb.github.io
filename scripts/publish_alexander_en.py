#!/usr/bin/env python3
"""alexander_raw/<书>/en_chapters/*.md → 站内 alexander/<书>/*.md（英文版）。

    python3 scripts/publish_alexander_en.py            # 诗篇
    python3 scripts/publish_alexander_en.py isaiah     # 以赛亚书

做三件事：
  1. 补 front matter（layout / 上下篇导航 / 时间戳）
  2. 节号段落 → 锚点 + `.ax-vnum`，供章顶 verse-nav 与经文索引取用
  3. 生成书卷首页 index.html

**已发布文件的 date 一律沿用原值**，只有新建的才写当前时间
（CLAUDE.md：已有文件的时间不要修改）。重跑本脚本不该把 150 篇的发布时间
集体改成今天——那会让「最新内容」和 sitemap 的 lastmod 全部失真。

节号的两套编号：诗篇写作 `7 (6).`，前者是希伯来文本的节号、括号里是英文
圣经的节号（诗篇题注在希伯来文里算第 1 节，英译不算，于是差一节）；
以赛亚书写作 `V. 7.`，只有一套。**锚点一律取英文节号**——站内其他注释、
经文索引、和合本都按英文编号，取希伯来节号会让同一节在不同注释之间对不上。
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 节号段落。分三段捕获，好把两套编号分别着色：
#   g1  主编号，可能是范围或列表：'7'  '21, 22'  '31-33'
#   g2  括号内的英文编号（可缺）：'6'  '30—32'
#   g3  收尾标点
PSALMS_VERSE = re.compile(
    r'^(?P<lead>\*?)'
    r'(?P<g1>\d{1,3}(?:\s*[-–—,]\s*\d{1,3})*)'
    r'(?:\s*\(\s*(?P<g2>\d{1,3}(?:\s*[-–—,]\s*\d{1,3})*)\s*\.?\s*\))?'
    r'(?P<g3>[.,:])?(?=\s)')
# 以赛亚书统一是 `V. 7.`；`V. 9, 10.` 这类连节也认。
# 边角上要放宽三处，否则整节拿不到锚点（全书 4 处）：
#   `. V. 5.`   节号前多出一个 OCR 噪点句号
#   `V. 20;`    收尾标点是分号
#   `V. 3..For` `V. 4'.`  收尾多一个句点或撇号，后面直接接正文
ISAIAH_VERSE = re.compile(
    r'^(?P<lead>\*?)[.,;]?\s*V+\s*\.\s*'
    r'(?P<g1>\d{1,3}(?:\s*[-–—,]\s*\d{1,3})*)'
    r"'?"
    r'(?:\s*\(\s*(?P<g2>\d{1,3}(?:\s*[-–—,]\s*\d{1,3})*)\s*\.?\s*\))?'
    r'(?P<g3>[.,:;])?(?=[\s*.,;)]|$)')

BOOKS = {
    'psalms': dict(
        book_name='Alexander on the Psalms', layout='alexander-chapter',
        index_layout='alexander-book', chapters=(1, 150), verse=PSALMS_VERSE,
        # 「著者序」在正文之前；诗篇没有导论
        sequence=lambda: ([('preface', 'Preface')]
                          + [(str(i), f'Psalm {i}') for i in range(1, 151)]),
        label=lambda n: f'Psalm {n}'),
    'isaiah': dict(
        book_name='Alexander on Isaiah', layout='alexander-chapter',
        index_layout='alexander-isaiah-book', chapters=(1, 66),
        verse=ISAIAH_VERSE,
        # 两卷各有自己的序与导论。**卷二那两篇要排在第 39 与 40 章之间**，
        # 不能一股脑堆到最前面——原书就是两本，上下篇导航照原书走才对，
        # 否则第 1 章的「上一篇」会指到卷二导论去。
        sequence=lambda: (
            [('preface', 'Preface (Vol. I)'),
             ('introduction', 'Introduction (Vol. I)')]
            + [(str(i), f'Isaiah {i}') for i in range(1, 40)]
            + [('later-preface', 'Preface (Vol. II)'),
               ('later-introduction', 'Introduction (Vol. II)')]
            + [(str(i), f'Isaiah {i}') for i in range(40, 67)]),
        label=lambda n: f'Isaiah {n}'),
}

FIRST_NUM = re.compile(r'\d{1,3}')
FM_DATE = re.compile(r'^date:\s*(.+)$', re.M)


def render_verse(m, book_id, chapter, num):
    """把节号本身包起来。lead 的 `*` 要移到节号之后，否则斜体跨过节号，
    读者会以为编号也是经文的一部分（原书的斜体只包译文）。"""
    g1, g2, g3 = m.group('g1'), m.group('g2'), m.group('g3') or '.'
    inner = g1
    if g2:
        inner += f' <span class="ax-veng">({g2}){g3}</span>'
    else:
        inner += g3
    anchor = f'<span class="ax-anchor" id="{book_id}-{chapter}-{num}"></span>'
    return f'{anchor}<span class="ax-vnum">{inner}</span>' + (' *' if m.group('lead') else '')


# 本流水线只产 `<span …>` 与 `<!-- … -->` 两种标记，别的都不是我们写的
OURS = re.compile(r'</?span\b[^<>]*>|<!--')


def escape_stray_lt(line):
    """把不是我们写的 `<` 转义掉。

    OCR 把希伯来/希腊活字读崩的残渣里常带尖括号（`<B`、`<TT(>`、`<X^>`），
    kramdown 会把它们当 HTML 标签解析，**整段正文被当成标签属性吞掉**：
    第 14 章有一处 `<B, supposing the verb…(p7t>`，页面上那 180 个字符
    直接不见了。全书 19 处，`span` 之外的标签一个都不是我们写的。
    """
    out, i = [], 0
    while True:
        j = line.find('<', i)
        if j < 0:
            return ''.join(out) + line[i:]
        out.append(line[i:j])
        m = OURS.match(line, j)
        if m:
            out.append(m.group())
            i = m.end()
        else:
            out.append('&lt;')
            i = j + 1


def transform(body, book_id, chapter, verse_re):
    out, n_anchor = [], 0
    for line in body.split('\n'):
        if not line.strip() or line.startswith('<!--'):
            out.append(line)
            continue
        m = verse_re.match(line)
        if m:
            src = m.group('g2') or m.group('g1')
            num = FIRST_NUM.search(src).group(0)
            out.append(render_verse(m, book_id, chapter, num)
                       + escape_stray_lt(line[m.end():]))
            n_anchor += 1
        else:
            # kramdown 会把 `* ` 开头的行当无序列表。正文不该有，防一手。
            line = escape_stray_lt(line)
            out.append('\\' + line if line.startswith('* ') else line)
    return '\n'.join(out), n_anchor


def existing_date(path):
    """已发布文件的 date 原样取回；没有就返回 None。"""
    if not path.exists():
        return None
    m = FM_DATE.search(path.read_text(encoding='utf-8')[:400])
    return m.group(1).strip() if m else None


def main(book='psalms'):
    cfg = BOOKS[book]
    src = ROOT / f'alexander_raw/{book}/en_chapters'
    out = ROOT / f'alexander/{book}'
    lo, hi = cfg['chapters']
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True,
                         text=True, check=True).stdout.strip()
    out.mkdir(parents=True, exist_ok=True)

    seq = cfg['sequence']()
    names = [n for n, _ in seq]
    labels = dict(seq)

    total_anchors = kept = 0
    for k, sec in enumerate(names):
        raw = (src / f'{sec}.md').read_text(encoding='utf-8')
        body, n = transform(raw.strip(), book, sec, cfg['verse'])
        total_anchors += n
        path = out / f'{sec}.md'
        date = existing_date(path)
        kept += date is not None
        fm = [
            '---',
            f'layout: {cfg["layout"]}',
            f'book_id: {book}',
            f'book_name: "{cfg["book_name"]}"',
        ]
        if sec.isdigit():
            fm.append(f'chapter: {sec}')
        fm += [f'title: "{labels[sec]}"', f'date: {date or now}']
        if k > 0:
            fm += [f'prev_section: {names[k - 1]}',
                   f'prev_label: "{labels[names[k - 1]]}"']
        if k + 1 < len(names):
            fm += [f'next_section: {names[k + 1]}',
                   f'next_label: "{labels[names[k + 1]]}"']
        fm.append('---')
        # 正文里不再重复一个 h1：layout 顶部已经用 page.title 打了标题，
        # 两处都写「Psalm 1」是同一串字连着出现两遍。
        path.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    (out / 'index.html').write_text(
        '---\n'
        f'layout: {cfg["index_layout"]}\n'
        f'book_id: {book}\n'
        f'book_name: "{cfg["book_name"]}"\n'
        f'chapters: {hi}\n'
        '---\n', encoding='utf-8')

    print(f'发布 {len(names)} 篇（含序与导论），节号锚点 {total_anchors} 个，'
          f'沿用原 date {kept} 篇 → {out}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'psalms')
