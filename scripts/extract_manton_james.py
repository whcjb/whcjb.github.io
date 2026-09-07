#!/usr/bin/env python3
"""CCEL EPUB → manton_raw/james/*.md（托马斯·曼顿《雅各书注释》英文 raw）

底本
----
Thomas Manton, *A Practical Commentary, or an Exposition with Notes on the
Epistle of James*（1657 初版），收于 Nichol 版《曼顿全集》第 4 卷（1870–75）。
曼顿卒于 1677，全集为 19 世纪版本，均已进入公有领域。
本站所据电子本 = CCEL 的 ThML 转写，取其 EPUB 导出：

    https://www.ccel.org/ccel/m/manton/manton04/cache/manton04.epub

为什么用 EPUB 而不是 PDF
------------------------
同一份 CCEL ThML 导出了 pdf / txt / epub 三种。PDF 是 XEP 从 ThML 渲染的，
走 PDF 路线等于把已有的结构信息（标题层级、脚注配对、经文引用的 canonical
ref、希腊文 span）压扁成几何坐标再猜回来——正是 principles §0.3 说的
「几何信号做语义判断必翻车」。EPUB 保留原始标签，直接映射即可，
不需要任何几何启发式。

三种格式已逐字比对过同一段落，正文内容一致（见 §引号 的比对记录）。

元素映射（principles §0.0：原文有什么就还原什么，没有的不自创）
--------------------------------------------------------------
| CCEL 元素                        | 输出                                |
|----------------------------------|-------------------------------------|
| h1 / h2 / h4                     | `#` / `##` / `####`                 |
| p.center                         | `<p style="text-align:center" markdown="1">` |
| p.normal / p.first / p.continue  | 普通段落                            |
| `VER. N.` 开头段                 | `<!--VERSE N-->` 标记 + 段落        |
| `<i>`                            | `*…*`                               |
| span.Greek / span.Hebrew         | 原样（已是 Unicode）                |
| span.sc（小型大写）              | 原样文字                            |
| a.scripRef                       | 文字保留；canonical ref 另存 sidecar |
| sup > a.Note（id `fna_*`）       | `[^fN]`                             |
| div.mnote（id `fnf_*`）          | `[^fN]: …`                          |
| span.pb id="…Page_NNN"           | `<!-- PAGE NNN -->`                 |
| hr（脚注区分隔线）               | 丢弃                                |

引号：CCEL 转写的已知缺陷
-------------------------
Nichol 原书的单引号在 CCEL 的 ThML 里被压成了 `` ` ``（开）与 `,`（闭）。
这不是 EPUB 转换丢的——pdf / txt / epub / 线上网页四处一致（线上页
`‘`/`’` 计数为 0，backtick 1528），所以 CCEL 手上就是这样，换格式救不回来。

反引号必须处理：markdown 里裸 `` ` `` 会起 code span，留着等于主动破坏渲染。
闭引号则**只做证据充分的还原，不猜**：

  规则 A  `` ` `` → `‘`
          1:1 字符替换。原文说这里开引号，不涉及任何推断。
  规则 B  `[;:?!],` → `[;:?!]’`
          逗号紧跟在终止标点后不是合法英文标点，只能是被压坏的 `’`。
  规则 C  `.,` → `.’`，但排除缩写后的句点
          （`Vulg.,` `Gal.,` `xi.,` 这类句点+逗号是合法的）。缩写用下面
          ABBREV 白名单 + scripRef 锚点边界判定，不用「看着像缩写」的启发式。
  其余逗号一律不动。

量过的反例（别再试）：「逗号紧邻 scripRef 就算闭引号」——候选数
2004，加上规则 B 后覆盖率 108%，明显过冲：`当他说，Gal. iii. 28，` 这种
引用前的逗号本来就是合法逗号。该规则已废弃。

残余未配对的 `‘` 会在末尾统计里报出来，不静默吞掉。

用法
----
    python3 scripts/extract_manton_james.py
"""
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'manton_raw' / 'james' / 'source' / 'epub_x' / 'OEBPS'
OUT = ROOT / 'manton_raw' / 'james'

# EPUB 文件 → 输出名 / 标题。顺序即全书顺序。
SECTIONS = [
    ('manton04.i_2.html',    'dedicatory',   'The Epistle Dedicatory'),
    ('manton04.iii.ii.html', 'advertisement', 'An Advertisement to the Reader'),
    ('manton04.iii.iii.html', 'preface',     'A Preface to the Whole Epistle'),
    ('manton04.iv.html',     '1',            'Chapter I'),
    ('manton04.v.html',      '2',            'Chapter II'),
    ('manton04.vi.html',     '3',            'Chapter III'),
    ('manton04.vii.html',    '4',            'Chapter IV'),
    ('manton04.viii.html',   '5',            'Chapter V'),
]

# 规则 C 的缩写白名单：这些词后面的 `.,` 是合法的「缩写句点 + 逗号」，
# 不是被压坏的闭引号。取自本卷实际出现的缩写（拉丁文献简称 + 圣经卷名简称
# + 罗马数字），逐条在文本里查过。
ABBREV = {
    # 文献 / 版本简称
    'Vulg', 'Eras', 'Montan', 'Syr', 'Sept', 'Cap', 'cap', 'lib', 'Lib',
    'tom', 'Tom', 'fol', 'p', 'pp', 'vol', 'ver', 'Ver', 'cf', 'ibid',
    'Ibid', 'viz', 'sc', 'q', 'v', 'i.e', 'e.g', 'etc', 'Chrysost',
    'Hieron', 'Aug', 'Ambros', 'Tertul', 'Calv', 'Beza', 'Grot', 'Estius',
    'Cajet', 'Œcum', 'Theophyl', 'Epiphan', 'Euseb', 'Athanas', 'Basil',
    'Greg', 'Nissen', 'Nazianz', 'Cyprian', 'Clem', 'Alexand', 'Origen',
    'Justin', 'Mart', 'Iren', 'Lact', 'Bern', 'Aquin', 'Suarez', 'Bellarm',
    'Dr', 'Mr', 'St', 'Rev', 'Doct', 'Prof',
    # 圣经卷名简称
    'Gen', 'Exod', 'Lev', 'Num', 'Deut', 'Josh', 'Judg', 'Sam', 'Kings',
    'Chron', 'Ezra', 'Neh', 'Esth', 'Job', 'Psa', 'Ps', 'Prov', 'Eccl',
    'Cant', 'Isa', 'Jer', 'Lam', 'Ezek', 'Dan', 'Hos', 'Joel', 'Amos',
    'Obad', 'Jonah', 'Mic', 'Nah', 'Hab', 'Zeph', 'Hag', 'Zech', 'Mal',
    'Matt', 'Mat', 'Mark', 'Luke', 'John', 'Acts', 'Rom', 'Cor', 'Gal',
    'Eph', 'Phil', 'Philem', 'Col', 'Thes', 'Thess', 'Tim', 'Tit', 'Heb',
    'James', 'Jam', 'Pet', 'Jude', 'Rev',
}
# 罗马数字（章节号 `Gal. iii. 28` 里的 `iii.`）
ROMAN_RE = re.compile(r'^[ivxlcdm]+$', re.I)


# ── 引号还原 ──────────────────────────────────────────────────

def restore_quotes(text):
    """CCEL 的 `` ` ``/`,` 引号缺陷还原。见模块 docstring §引号。

    输入是**已去标签的纯文本**（scripRef 边界信息由调用方先行处理）。
    返回 (text, n_open, n_close)。
    """
    n_open = text.count('`')
    text = text.replace('`', '‘')

    # 规则 B：终止标点后的逗号只能是闭引号
    text, nb = re.subn(r'([;:?!]),', r'\1’', text)

    # 规则 C：`.,` —— 排除缩写与罗马数字后的句点
    def _dot(m):
        word = m.group(1)
        if word in ABBREV or ROMAN_RE.match(word) or word.isdigit():
            return m.group(0)
        return word + '.’'

    text, nc = re.subn(r'\b([A-Za-z0-9]+)\.,', _dot, text)
    return text, n_open, nb + nc


# ── 行内元素 → markdown ───────────────────────────────────────

# 斜体哨兵：Unicode 私用区，正文绝不会出现，故不会误伤真实文本
ITAL_OPEN, ITAL_CLOSE = '', ''

SCRIPREF_RE = re.compile(
    r'<a class="scripRef"[^>]*href="[^"]*?/(?:asv|kjv)\.([^"#]+?)\.html(?:#([^"]*))?"[^>]*>(.*?)</a>',
    re.S)


def collect_scriprefs(chunk, sink):
    """把 a.scripRef 的 canonical ref 收进 sink，正文只留可见文字。

    href 形如 .../asv.Gal.3.html#Gal.3.28 —— fragment 精确到节，没有
    fragment 时只精确到章。这是 verse-index（step 7）的现成输入，
    不需要再从正文正则去猜「Gal. iii. 28」这种罗马数字写法。
    """
    def _sub(m):
        book_ch, frag, label = m.group(1), m.group(2), m.group(3)
        ref = frag or book_ch
        sink.append({'ref': ref, 'label': re.sub(r'<[^>]+>', '', label).strip()})
        return label
    return SCRIPREF_RE.sub(_sub, chunk)


def inline_to_md(chunk, sink, fn_seen):
    """一段 HTML 内容 → markdown 行内文本。"""
    # 脚注引用：<sup ...><a class="Note" id="fna_..." ...>NUM</a></sup>
    def _fnref(m):
        num = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        fn_seen.add(num)
        return f'[^f{num}]'
    chunk = re.sub(r'<sup[^>]*>\s*<a class="Note"[^>]*id="fna_[^"]*"[^>]*>(.*?)</a>\s*</sup>',
                   _fnref, chunk, flags=re.S)

    # 页码锚：<span class="pb" id="xx-Page_179"/>
    chunk = re.sub(r'<span class="pb"[^>]*id="[^"]*Page_(\d+)"[^>]*/?>',
                   r'\n\n<!-- PAGE \1 -->\n\n', chunk)

    chunk = collect_scriprefs(chunk, sink)

    # 斜体。span.Greek / span.Hebrew / span.sc 只脱标签，文字原样保留
    chunk = re.sub(r'<i>(.*?)</i>', lambda m: _ital(m.group(1)), chunk, flags=re.S)
    chunk = re.sub(r'</?span[^>]*>', '', chunk)
    chunk = re.sub(r'<a\b[^>]*/>', '', chunk)          # 空锚点
    chunk = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', chunk, flags=re.S)
    chunk = re.sub(r'<br\s*/?>', '  \n', chunk)
    chunk = re.sub(r'<[^>]+>', '', chunk)

    chunk = html.unescape(chunk)
    # 哨兵还原（必须在 unescape 之后：unescape 不会动这两个私用码位，
    # 但还原出的 < > 若先出现，会被上面的兜底正则误伤）
    chunk = chunk.replace(ITAL_OPEN, '<em>').replace(ITAL_CLOSE, '</em>')
    chunk = re.sub(r'[ \t\r\n]+', ' ', chunk)
    return chunk.strip()


def _ital(inner):
    """<i>…</i> → <em>…</em>，空内容不产生空标签。

    **不用 markdown 的 `*…*`**：kramdown 只在开标记前是空白/行首时才认它是
    emphasis。本书大量斜体紧贴前一个词，如原文 `smoke.<i> Crassa negligentia
    dolus est</i>,` —— 转成 `smoke.*Crassa…*` 后开标记前是句点，kramdown
    不当强调处理，星号原样打到页面上，后面的配对还会连锁错位
    （踩过：ch1 该段 12 个星号全配错，`<em>` 开在了 est 之后）。

    源本身就是 HTML，斜体是显式标签、没有歧义，直接出 `<em>` 最忠实也最稳：
    行内 HTML 被 kramdown 原样透传，不受相邻字符影响。
    §0.4 / §0.5 那两类星号病因此在本书不会出现。
    """
    txt = inner.strip()
    if not txt:
        return ''
    # 用哨兵占位，等 inline_to_md 末尾那道「剥掉所有剩余标签」的兜底
    # 正则跑完之后再还原成 <em>。直接写 <em> 会被那道正则一起剥掉
    # （踩过：斜体全丢，连带 VERSE 头一节都认不出来）。
    return f'{ITAL_OPEN}{txt}{ITAL_CLOSE}'


def normalize_emphasis(text):
    """principles §0.4 / §0.5：emit 出口的标记归一化。"""
    # §0.4 相邻 `**A**``**B**` 合并（本源虽无 bold，仍按契约走一遍）
    text = text.replace('****', '')
    # §0.5 引号被切成独立 italic span 的两种形态
    QO = r'["“”\'‘’]'
    QD = r'["“”]'
    text = re.sub(rf'\*({QO})\*([^*]+?)\*([,.;:!?]*{QO})\*', r'*\1\2\3*', text)
    text = re.sub(rf'\*({QO})\*([^*]+?{QD})', r'*\1\2*', text)
    # 空斜体 / 紧邻斜体
    text = text.replace('**', '')
    return text


def dehyphenate(text):
    """Gate 7：行末断字。CCEL txt 有换行断字，EPUB 基本没有，仍兜一道。"""
    return re.sub(r'([A-Za-z]{2,})-\s+([a-z]{2,})', r'\1\2', text)


# ── 段落级处理 ────────────────────────────────────────────────

# 释经单元头：`Ver. 2. *经文*`
#   - 前缀 `[,`’ ]*`：v-p221（ch2 v21）整段以一个孤立逗号开头 —— 那是上一段
#     引文被压坏的闭引号漏到了段首（段落不可能合法地以逗号起头）。不容忍
#     它，ch2 第 21 节整个单元就没有锚点。
#   - 节号后 `[.．]\s*[—–-]?`：iv-p513（ch1 v27）写作 `Ver. 27.—<i>`，
#     句点与斜体之间夹了破折号。只写 `\s*` 会漏掉这一节。
# 两处都是逐条查过原文确认的，不是「看着像」就放宽。
#   - 结尾 lookahead 认 `<em>`：斜体已在 inline_to_md 里转成 <em>（见 _ital），
#     这里匹配的是转换**之后**的文本。写成 `<i>` 会一节都认不出来。
VERSE_HEAD_RE = re.compile(
    r'^[,‘’\s]*(?:VER|Ver)\.\s*([0-9][0-9,\s–-]*?)\.\s*[—–-]?\s*(?=<em>)')

BLOCK_RE = re.compile(r'<(h1|h2|h4|p|div)\b([^>]*)>(.*?)</\1>', re.S)


def convert_file(path, sink, fn_defs, fn_seen, is_chapter=False):
    raw = path.read_text(encoding='utf-8')
    # 去掉最外层 <div class="book-content"> 包裹本身。留着它，非贪婪的
    # BLOCK_RE 会把它匹配到第一个 </div>（某条 mnote 的收尾），整章正文
    # 被当成一个 div 块整块跳过 —— 踩过：ch1 只剩 11k 字符。
    body = raw[raw.find('<div class="book-content">'):]
    body = body[body.find('>') + 1:]
    out = []
    seen_verse = False

    for m in BLOCK_RE.finditer(body):
        tag, attrs, inner = m.group(1), m.group(2), m.group(3)
        cm = re.search(r'class="([^"]*)"', attrs)
        cls = cm.group(1) if cm else ''

        if tag == 'div' and 'mnote' in cls:
            # 脚注定义：<div class="mnote"><a class="Note" id="fnf_..."><sup>N</sup></a>TEXT</div>
            nm = re.search(r'<sup class="NoteRef">(\d+)</sup>', inner)
            if not nm:
                continue
            num = nm.group(1)
            text = re.sub(r'<a class="Note".*?</a>', '', inner, flags=re.S)
            text = inline_to_md(text, sink, fn_seen)
            text = re.sub(r'\s*<!-- PAGE \d+ -->\s*', ' ', text).strip()
            fn_defs[num] = text
            continue

        if tag == 'div':
            continue

        text = inline_to_md(inner, sink, fn_seen)
        if not text.strip():
            continue

        if tag == 'h1':
            out.append(('h1', text))
        elif tag == 'h2':
            out.append(('h2', text))
        elif tag == 'h4':
            out.append(('h4', text))
        else:
            vm = VERSE_HEAD_RE.match(text)
            if vm:
                seen_verse = True
                out.append(('verse', vm.group(1).strip(), text))
            elif 'center' in cls and not seen_verse and is_chapter:
                # 第 1 章开篇的书信题辞（雅 1:1）在原书里是居中排的，
                # 没有 `Ver. 1.` 前缀 —— 但它就是第 1 节的释经单元头。
                # 不认它，全书唯独 1:1 没有锚点。居中版式照原书保留。
                #
                # ⚠️ 必须限定 is_chapter：前置三篇里也有居中段，献辞开头
                # 那行受献人「To the Honourable Colonel Alexander Popham…」
                # 同样是首个 p.center，不加限定会被当成经节头，凭空造出
                # 一个 james-0-1 锚点、还把受献人行套上经文头样式（踩过）。
                seen_verse = True
                out.append(('verse-center', '1', text))
            elif 'center' in cls:
                out.append(('center', text))
            else:
                out.append(('p', text))
    return out


def render(blocks, title):
    """块序列 → markdown 正文。"""
    lines = []
    for b in blocks:
        kind = b[0]
        if kind == 'h1':
            lines.append(f'# {b[1]}')
        elif kind == 'h2':
            lines.append(f'## {b[1]}')
        elif kind == 'h4':
            lines.append(f'#### {b[1]}')
        elif kind == 'center':
            lines.append(f'<p style="text-align:center" markdown="1">{b[1]}</p>')
        elif kind == 'verse':
            lines.append(f'<!--VERSE {b[1]}-->')
            lines.append(b[2])
        elif kind == 'verse-center':
            lines.append(f'<!--VERSE {b[1]} center-->')
            lines.append(b[2])
        else:
            lines.append(b[1])
    return '\n\n'.join(lines)


def main():
    if not SRC.exists():
        sys.exit(f'找不到 EPUB 解包目录：{SRC}\n'
                 f'先跑：cd {SRC.parent} && unzip -oq ../manton04.epub')

    OUT.mkdir(parents=True, exist_ok=True)
    stats = Counter()
    all_refs = {}

    for fname, out_name, title in SECTIONS:
        sink, fn_defs, fn_seen = [], {}, set()
        blocks = convert_file(SRC / fname, sink, fn_defs, fn_seen,
                              is_chapter=out_name.isdigit())
        text = render(blocks, title)

        # 出口归一化：顺序固定 —— 先还原引号（要看得到 `,` 原样），
        # 再断字合并，最后 emphasis 归一化。
        text, n_open, n_close = restore_quotes(text)
        text = dehyphenate(text)
        text = normalize_emphasis(text)

        # 脚注定义追加在正文末（kramdown 需要 def 与 ref 同文件）
        if fn_defs:
            defs = []
            for num in sorted(fn_defs, key=int):
                d, _, _ = restore_quotes(fn_defs[num])
                d = normalize_emphasis(dehyphenate(d))
                defs.append(f'[^f{num}]: {d}')
            text = text.rstrip() + '\n\n---\n\n' + '\n\n'.join(defs) + '\n'

        (OUT / f'{out_name}.md').write_text(text, encoding='utf-8')
        all_refs[out_name] = sink

        missing = sorted(fn_seen - set(fn_defs), key=int)
        stats['open'] += n_open
        stats['close'] += n_close
        print(f'{out_name:14s} {len(text):8,d} chars  '
              f'refs={len(sink):5d}  fn={len(fn_defs):3d}/{len(fn_seen):3d}  '
              f'quotes {n_open}→{n_close}'
              + (f'  ⚠ 缺 def: {missing}' if missing else ''))

    (OUT / 'scriprefs.json').write_text(
        json.dumps(all_refs, ensure_ascii=False, indent=1), encoding='utf-8')

    print(f'\n引号：开 {stats["open"]}  闭 {stats["close"]}  '
          f'残余未配对 {stats["open"] - stats["close"]} '
          f'({(stats["open"]-stats["close"])/max(1,stats["open"]):.1%})')
    print(f'scripRef sidecar → {OUT / "scriprefs.json"}')


if __name__ == '__main__':
    main()
