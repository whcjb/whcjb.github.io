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
# 三处 OCR 变体要一起认，否则**整节的锚点与编号一起消失**，而页面上看不出异常
# （靠「显示的节号必须连号」这条才查得出来，全书 4 处）：
#   `*5* (4).`   节号自己被斜体裹住（诗 31、69）
#   `*24:* (23).` 斜体裹住 + 收尾是冒号（诗 44）
#   `7^(6).`     括号前多一个 OCR 噪点 `^`（诗 140）
# `close` 记下节号后面那个收尾星号：有它就说明斜体已经闭合，
# 不能再照 `lead` 补一个 ` *`，否则整段被拖进斜体。
PSALMS_VERSE = re.compile(
    r'^(?P<lead>\*?)'
    r'(?P<g1>\d{1,3}(?:\s*[-–—,]\s*\d{1,3})*)'
    r':?(?P<close>\*?)'
    r'(?:[\s^]*\(\s*(?P<g2>\d{1,3}(?:\s*[-–—,]\s*\d{1,3})*)\s*\.?\s*\))?'
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
    anchor = ('' if num is None else
              f'<span class="ax-anchor" id="{book_id}-{chapter}-{num}"></span>')
    reopen = bool(m.group('lead')) and not (
        'close' in m.groupdict() and m.group('close'))
    return f'{anchor}<span class="ax-vnum">{inner}</span>' + (' *' if reopen else '')


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



# 节号标题永远另起一段。抽取阶段偶尔把段落断点吞掉，标题就粘在上一段末尾，
# `transform` 的 `^` 锚匹配不到，**整节的锚点与编号一起消失**（诗 8 的第 3 节、
# 诗 30 的第 4 节、诗 89 的第 30 节就是这么没的），而页面上看不出任何异常。
#
# 判据不能只看「句末 + 数字 + 括号数字 + 斜体」——那正是经文引用的样子
# （`See above, on Ps. vii. 7 (6). *Raise thy hand,*`），一试跑命中 300 多处。
# 加两道闸才准：
#   ① 编号必须**正好接上本篇的下一节**（主号 +1 且括号英文号也 +1）
#   ② 紧挨在前的不能是罗马数字或 `ver.`/`chap.` —— 那是引用的章节号
# 两道闸一起，全书恰好命中 3 处，逐条核过影像。
RUNON_HEAD = re.compile(
    r'(?P<g1>\d{1,3})'
    r'(?:\s*\(\s*(?P<g2>\d{1,3})\s*(?P<pin>\.?)\s*\))?'
    r'\s*(?P<p>[.,:]?)\s*(?=\*)')
RUNON_CITE = re.compile(r'\b(?:[ivxlcdm]+|ver|vers|chap)[.,]\s*[•·.,]?\s*$')
# 句末与节号之间可能夹一粒墨点（诗 112 的 `disposition. • 2.`）
RUNON_END = re.compile(r'[.!?]\s*[•·‘’\'"]?\s*$')
# 前面必须是**正文**，不能只是另一个节号：`15. 16. *Let (such) give thanks*`
# 印面作 `15, 16.`——他把两节合在一个标题下，逗号被读成了句点，
# 那是「标点读错」，不是「段落断点丢了」，断开只会多出一个不存在的节。
RUNON_ONLY_NUM = re.compile(r'^[\s*]*\d{1,3}\s*[.,:]?\s*$')



RAW_FIXES = ROOT / 'alexander_raw/psalms/raw_fixes.tsv'


def raw_fixes(chapter):
    """发布之前先打的补丁：**节号本身**被 OCR 读坏的那几处。

    节号读坏了，`transform` 认不出标题，整节的锚点与编号一起消失，而页面上
    看不出任何异常——只有「显示的节号必须连号」那条判据查得出来。
    坏法各不相同（`G (5).` 把 6 读成字母、`o20 (19).` 多一个噪点、
    `178.` 是 173、`2. 6.` 把 5 读成 6 又粘进上一段），没有共同的形态可写规则，
    只能按处落表。

    补丁打在 **raw 之后、transform 之前**：en_chapters 保持原样（重新 extract
    仍可复现），而锚点编号由 transform 统一分配，不会与后面的 manual_fixes 打架。
    每条都要命中，命中不到就报错——上游一改，这张表会静默失效。
    """
    if not RAW_FIXES.exists():
        return []
    rows = []
    for line in RAW_FIXES.read_text(encoding='utf-8').splitlines()[1:]:
        if not line.strip():
            continue
        f = line.split('\t')
        if len(f) != 4:
            raise SystemExit(f'✗ raw_fixes.tsv 不是 4 列：{line[:80]!r}')
        if f[0] == chapter:
            # 两列都要解码：有的补丁是**把被残渣劈开的段落接回去**，
            # 被匹配的原串里就带换行（诗 119 的 `as in Ps.\\n\\n■»■ t • lxxxi.`）
            rows.append((f[1].replace('\\n', '\n'), f[2].replace('\\n', '\n')))
    return rows


def split_runon_verse(body, verse_re):
    """把粘在上一段末尾的节号标题拆成独立一段。"""
    out, last1, last2 = [], None, None
    for line in body.split('\n'):
        if not line.strip() or line.startswith('<!--'):
            out.append(line)
            continue
        m = verse_re.match(line)
        if m:
            last1 = max(int(x) for x in FIRST_NUM.findall(m.group('g1')))
            last2 = (max(int(x) for x in FIRST_NUM.findall(m.group('g2')))
                     if m.group('g2') else None)
        cut = None
        for h in RUNON_HEAD.finditer(line):
            if h.start() == 0 or last1 is None:
                continue
            if not (h.group('pin') or h.group('p')):
                continue                      # 节号后面总得有个收尾的点或逗号
            a, b = int(h.group('g1')), h.group('g2')
            if a != last1 + 1:
                continue
            # 两套编号要么都有、要么都没有：单套编号的篇（诗 112）不会突然多出括号
            if (b is None) != (last2 is None):
                continue
            if b is not None and int(b) != last2 + 1:
                continue
            pre = line[:h.start()]
            if (not RUNON_END.search(pre) or RUNON_CITE.search(pre)
                    or RUNON_ONLY_NUM.match(pre)):
                continue
            cut = h.start()
            last1, last2 = a, (int(b) if b else None)
            break
        if cut is None:
            out.append(line)
        else:
            out.append(line[:cut].rstrip())
            out.append('')
            out.append(line[cut:])
    return '\n'.join(out)


# `i. e.` / `e. g.` 中间**有一个空格**是这本书的体例：全书 736 处带空格、
# 165 处不带。少数形态是 OCR 把细空格吞了，影像上一律带空格（诗 11 的
# `(i. e. bend)`、诗 76 的 `i. e.` 逐页对读时都核过）。
# 纯排版归一，不涉及字形判读，所以直接在发布时统一，不占规则表。
IE_SPACE = re.compile(r'\b([ie])\.([eg])\.')


def transform(body, book_id, chapter, verse_re):
    body = IE_SPACE.sub(lambda m: f'{m.group(1)}. {m.group(2)}.', body)
    for old, new in raw_fixes(chapter):
        if body.count(old) != 1:
            raise SystemExit(f'✗ raw_fixes 第 {chapter} 章命中 '
                             f'{body.count(old)} 次（应为 1）：{old[:60]!r}')
        body = body.replace(old, new, 1)
    body = split_runon_verse(body, verse_re)
    # 希伯来文的题注在希伯来编号里算第 1 节，英译不算。锚点一律取英文节号，
    # 于是题注（只有 `1.`、没有括号里的英文号）与真正的第 1 节（`2 (1).`）
    # 会拿到同一个 id，全书六十来篇如此：HTML 里出现重复 id，章顶 verse-nav
    # 点「1」落到题注上，真正的第 1 节反而够不着。
    # 判据：这一篇里只要有任何一节带括号英文号，说明两套编号是错开的，
    # 那么开头那个光杆 `1.` 就是题注 —— 它不发锚点，只保留节号的样子。
    dual = any(verse_re.match(l) and verse_re.match(l).group('g2')
               for l in body.split('\n') if l.strip())
    title_done = not dual
    out, n_anchor = [], 0
    for line in body.split('\n'):
        if not line.strip() or line.startswith('<!--'):
            out.append(line)
            continue
        m = verse_re.match(line)
        if m:
            src = m.group('g2') or m.group('g1')
            num = FIRST_NUM.search(src).group(0)
            # 题注可能占两段（诗 52、54、60 的希伯来文题注是两节），
            # 所以「第一个带括号英文号的段」之前的光杆节号全算题注
            if not title_done and not m.group('g2'):
                out.append(render_verse(m, book_id, chapter, None)
                           + escape_stray_lt(line[m.end():]))
                continue
            title_done = True
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
        # 中译是逐篇推进的：这一篇的中文页已经发出来了，英文页就带上 zh_url，
        # 好让右上角出现「中文版 →」。重跑本脚本不会把它冲掉。
        if (out / 'zh' / f'{sec}.md').exists():
            fm.append(f'zh_url: "/alexander/{book}/zh/{sec}/"')
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
