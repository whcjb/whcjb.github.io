#!/usr/bin/env python3
"""达文南特《歌罗西书注释》结构化 raw → davenant/colossians/*.md + index.html

输入  davenant_raw/colossians/davenant_colossians_structured.txt
输出  davenant/colossians/{1,2,3,4}.md + index.html

脚注配对
--------
本书脚注符是**每页重置的符号**（`*` / `†` / `‡`），不是全书连号，所以配对
只能按页做：`[FN]` 条目带 `<!--pN-->`，正文段落带 `<!--pA-->` 或
`<!--pA-B-->`（跨页段）。按出现顺序在同页的注队列里取。

⚠️ `†` `‡` 在 OCR 里常被读成 `+` `f` `t` `J` `I`，其中后三个会粘在词尾
（`Thomasf`），无法可靠地从词里切出来。所以**只配 `*` 与 `+` 两种**
（正文里 208 + 19 处，覆盖绝大多数），其余的注仍会输出定义、只是没有
行内引用——宁可少连一个，也不猜错位置。

用法: python3 scripts/publish_davenant_en.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
# 英文放主目录、中译日后进 zh/ 子路径 —— 与贺智/欧文/曼顿一致
# （PRIMARY_LANG['davenant'] = 'en'）。用 colossians-en 会被
# build_commentaries_index 的 SKIP(-en$) 跳过，「历代解经」里出不来。
OUT = ROOT / 'davenant' / 'colossians'
BOOK_ID = 'colossians'
BOOK_NAME = 'Davenant on Colossians'
ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV'}
# 扫描页号 → 书上印的页码（两卷各有固定偏移，抽样 vol1 p120→35 / p200→115 /
# p422→337、vol2 p14→5 / p150→141 / p223→214 全对得上）。脚注标签给读者看的
# 得是书上的页码，扫描序号对读者没意义。
PRINTED = {1: -85, 2: -9}

# 跨页续注是否并回上一条。见 collect_notes 的说明——开之前先看那段。
MERGE_CROSS_PAGE = False

FN_MARK_START = re.compile(r'^\s*(\*|\+|†|‡|[ftJI])\s+')
# 正文里的脚注引用：`Jerome,*` / `laudibus.+` / 孤立的 ` * `
REF_RE = re.compile(r'(?<=[\w.,;:)\'"”’])(\*|\+)|(?<=\s)(\*|\+)(?=\s)')


def parse():
    items = []
    for ln in (RAW / 'davenant_colossians_structured.txt').read_text(
            encoding='utf-8').splitlines():
        m = re.match(r'^\[([A-Z0-9_]+)\] (.*)$', ln)
        if not m:
            continue
        tag, rest = m.group(1), m.group(2)
        # `<!--v1p93-->` / `<!--v1p93-94-->`：卷号 + 扫描页号。页号两卷重叠，
        # 脚注按页配对必须连卷号一起当 key，否则 3/4 章会抢 1/2 章的注。
        pm = re.match(r'<!--v(\d+)p(\d+)(?:-(\d+))?-->', rest)
        pages = []
        if pm:
            v = int(pm.group(1))
            a = int(pm.group(2))
            b = int(pm.group(3)) if pm.group(3) else a
            pages = [(v, n) for n in range(a, b + 1)]
            rest = rest[pm.end():]
        items.append({'tag': tag, 'text': rest, 'pages': pages})
    return items


def collect_notes(items):
    """→ {(vol, page): [note_text, …]}，多段的注合并为一条。

    ⚠️ 一条注**跨页**时也要合。Allport 的传记体长注常连着两三页，续页的注区
    顶上没有脚注符。原来只在同一页内合并，续页一律另起一条：全书 277 条注里
    有 60 条其实是上一条的下半截，读者看到的是一条从半句话开始、单独编号的注
    （`[^dv121]: tle; for Gregory was remarkable for his earnestness…`），
    而正文里那个符号指向的是被砍掉一半的上半条。
    判据：本条不以脚注符起首，且页号正好是上一条的下一页（同卷）——这正是
    「注区溢到下一页」的物理形态。跨页处用连字规则接，断词不留空格。

    ⚠️ **默认关**（MERGE_CROSS_PAGE = False），要和中译一起开。合并会让脚注
    总数从 277 掉到 240，正文里的 `[^dvN]` 全部重排号；而中译的缓存是按
    「送模型的那段英文原文」做 md5 的，段落里带着这些编号，重排一次
    **431 段**直接缓存落空要重译（实测 ch1 261 段 / ch2 77 / ch3 86 / ch4 7），
    已发布的中文页脚注编号也会与英文页对不上。歌罗西书注释的中译正在进行中
    （1–3 章已发布、第 4 章未译），这一刀要等中译重跑那一轮再一起下。
    附卷（publish_davenant_appx.py）没有这个包袱，那边默认就是合并的。
    """
    if not MERGE_CROSS_PAGE:
        notes, cur, cur_p = {}, None, None
        for it in items:
            if it['tag'] != 'FN':
                continue
            p = it['pages'][0] if it['pages'] else cur_p
            if FN_MARK_START.match(it['text']) or cur is None or p != cur_p:
                if cur is not None:
                    notes.setdefault(cur_p, []).append(cur)
                cur, cur_p = it['text'], p
            else:
                cur += ' ' + it['text']
        if cur is not None:
            notes.setdefault(cur_p, []).append(cur)
        return notes

    notes, cur, cur_p, cur_last = {}, None, None, None
    for it in items:
        if it['tag'] != 'FN':
            continue
        p = it['pages'][0] if it['pages'] else cur_p
        marked = bool(FN_MARK_START.match(it['text']))
        nxt_page = (cur_last[0], cur_last[1] + 1) if cur_last else None
        same_note = cur is not None and (p == cur_p
                                         or (not marked and p == nxt_page))
        if marked or not same_note:
            if cur is not None:
                notes.setdefault(cur_p, []).append(cur)
            cur, cur_p, cur_last = it['text'], p, p
        else:
            cur = (cur[:-1] + it['text'] if cur.endswith('-')
                   and it['text'][:1].islower() else cur + ' ' + it['text'])
            cur_last = p
    if cur is not None:
        notes.setdefault(cur_p, []).append(cur)
    return notes


def md_escape(t):
    """OCR 文本里在 kramdown 有语义的字符，凡不是真语法的都转义。

    `*`  —— 会被当强调符。
    `|`  —— 会被当**表格**分隔符。这是扫描件里最阴的一个：`|` 是扫描斑点与
             断笔的常见误读（`should | bring into contempt`），落在段落中间时
             kramdown 把整段拆成表格单元格，`|` 本身消失、前后段落被吸进同一张
             表，连带该段的脚注引用也不再解析（实测歌罗西书注释四章共生成 89 张
             假表，dissertation 另有 45 张；`[^da21]` / `[^da43]` 两条注因此
             以字面量印在正文里）。
             转义而不是删掉：按既定规矩，底本的版面碎片一律保留原样。
    `+` / `-` 起首 —— 会被当**无序列表**。原书的第二个脚注符是 `†`，OCR 一律
             读成 `+`，于是 `[^da21]: + After what has been said…` 整条注被渲染成
             带项目符号的列表项，缩进一大截（全站实测 51 处，中英都有）。
             只转义**块首**那一个：正文中间的 `+` `-` 是真标点，不能动。
    """
    # ⚠️ 允许前面有空白：注释正文那边页码标记后留了个空格
    # （`[^dv10]:  + Council of Nice…`），写死 `^` 会漏掉全部 20 条。
    t = re.sub(r'^(\s*)([+\-])(\s)', r'\1\\\2\3', t)
    return t.replace('*', '\\*').replace('|', '\\|')


# 原书每页脚注符按 `*` → `†` → `‡` 排（vol1 p88 三条注，裁图逐个核过）。
# `†` `‡` 不在 OCR 的常用字表里，一律被读成 `+` / `t` / `f` / `J` / `I`，
# 页面上就印成 `+ The characters referred to…`，读者看着莫名其妙。
# 按「该页第几条**带符号**的注」回填正确的字形——不能按注的序号排：
# 跨页续注不带符号，它排在前面会把序号顶掉（实测 15 页第一条是续注，
# 真正的第一条 `*` 排到了第二位）。
# ⚠️ 读成 `*` 的一律不动：`*` 本来就是合法的第一个符号，改它等于拿位置猜字形。
FN_SYMBOLS = ('*', '†', '‡', '§')
FN_DAGGER = re.compile(r'^(\s*)([+tfJI])(\s)')


def fix_fn_symbol(text, ordinal):
    """→ (文本, 是否带符号)。ordinal = 该页此前已有几条带符号的注。"""
    if re.match(r'^\s*\*\s', text):
        return text, True
    m = FN_DAGGER.match(text)
    if not m:
        return text, False
    sym = FN_SYMBOLS[min(ordinal, len(FN_SYMBOLS) - 1)]
    return m.group(1) + sym + m.group(3) + text[m.end():], True


ROMAN_N = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7,
           'viii': 8, 'ix': 9, 'x': 10, 'xi': 11, 'xii': 12, 'xiii': 13,
           'xiv': 14, 'xv': 15, 'xvi': 16, 'xvii': 17, 'xviii': 18, 'xix': 19,
           'xx': 20, 'xxi': 21, 'xxii': 22, 'xxiii': 23, 'xxiv': 24,
           'xxv': 25, 'xxvi': 26, 'xxvii': 27, 'xxviii': 28, 'xxix': 29}


def enum_lead(t):
    """段首编号包成 span，防止 kramdown 变成有序列表。

    达文南特论证里大量段落以 `1.` / `2.` 起首（`1. The congratulatory
    proposition; …`），原书排的是**普通段落**，不是悬挂列表。不处理的话
    kramdown 生成 ol/li（实测正文里 453 个 ol、989 个 li），既改了版式，
    还会重排号——单独以 `3.` 起首的段落会被渲染成 `1.`。

    ⚠️ 编号后面**不限定是拉丁字母**。原先只认 `[A-Za-z(“"']`，两处漏网：
    OCR 把标点留在编号后（`2. , Because God…`），以及中译里编号后面跟的是
    汉字（`2. 出自提摩太前书 1:5…`）——中文三章各有二十来段因此变成 ol/li，
    编号还被 kramdown 重排。改成「后面只要不是空白、不是数字」即可。
    """
    return re.sub(r'^(\d{1,3})\.\s+(?=[^\s\d])',
                  r'<span class="dv-enum">\1.</span> ', t)


def verse_nums(t):
    """经文块里的节号转成 HTML 粗体。

    不转的话行首 `1. Paul, an Apostle…` 会被 kramdown 当有序列表，
    整段经文渲染成 `<ol><li>`（实测）。段中的 ` 2. To the Saints…` 一并转，
    与行首保持一致。
    """
    t = re.sub(r'^(\d{1,3})\.\s+', r'<strong>\1.</strong> ', t)
    return re.sub(r'(?<=[.;:!?)\s])(\d{1,3})\.\s+(?=[A-Z(])',
                  r'<strong>\1.</strong> ', t)


def main():
    items = parse()
    notes = collect_notes(items)
    used = {p: 0 for p in notes}
    fn_seq = 0
    seen_anchors = {}
    chapters, cur = [], None

    for it in items:
        if it['tag'] == 'TITLE':
            continue
        if it['tag'] == 'FN':
            continue
        if it['tag'] == 'H1':
            m = re.search(r'CHAP\.\s*([IVX]+)', it['text'])
            n = {v: k for k, v in ROMAN.items()}.get(m.group(1)) if m else None
            cur = {'n': n, 'blocks': [], 'fns': [], 'last': {}}
            chapters.append(cur)
            continue
        if cur is None:
            continue

        # ── 行内脚注引用配对 ────────────────────────────────────────
        txt = it['text']
        if it['tag'] in ('BODY', 'LEMMA'):
            def sub(m):
                nonlocal fn_seq
                for p in it['pages']:
                    q = notes.get(p, [])
                    if used.get(p, 0) < len(q):
                        fn_seq += 1
                        cur['fns'].append((fn_seq, q[used[p]], p))
                        used[p] += 1
                        return f'[^dv{fn_seq}]'
                return m.group(0)          # 该页注已用尽 → 原样留符号
            txt = REF_RE.sub(sub, txt)

        if it['tag'] == 'SECTION':
            # ⚠️ 节号要从 `Verses` 之后取。直接 findall(r'\d+|[IVXLivxl]+')
            # 会先吃到 "Verses" 的首字母 V（它也是合法罗马数字），
            # 结果 88 个锚点 id 全变成 colossians-N-V（实测）。
            after = re.sub(r'^\s*Vers?e?s?\.?\s*', '', txt)
            nums = re.findall(r'\d+|[IVXLivxl]+', after)
            if nums and not nums[0].isdigit():
                nums[0] = str(ROMAN_N.get(nums[0].lower(), nums[0]))
            anchor = f'colossians-{cur["n"]}-{nums[0]}' if nums and cur['n'] else ''
            if anchor:
                # 同一节被分两段释经时会重号（实测 88 个锚点里 2 处重复）。
                # id 重复既是非法 HTML，也会让跳转落到第一处。照贺智的做法
                # 缀 -2/-3。
                seen_anchors[anchor] = seen_anchors.get(anchor, 0) + 1
                if seen_anchors[anchor] > 1:
                    anchor = f'{anchor}-{seen_anchors[anchor]}'
                cur['blocks'].append(
                    f'<div class="dv-anchor" id="{anchor}"></div>')
            cur['blocks'].append(f'## {txt}')
        elif it['tag'] == 'SCRIPTURE':
            m = re.match(r'(\d+):([\d,]+)\|([\d.]+)\| (.*)$', txt)
            if m:
                ref, body = f'Colossians {m.group(1)}:{m.group(2)}', m.group(4)
            else:
                ref, body = '', txt
            cur['blocks'].append(
                f'<div class="dv-scripture" markdown="1">\n'
                f'<p class="dv-scripture-ref">{ref}</p>\n\n'
                f'{verse_nums(md_escape(body))}\n</div>')
        elif it['tag'] == 'LEMMA':
            cur['blocks'].append(('LEMMA', md_escape(txt)))
        else:
            prev = cur['blocks'][-1] if cur['blocks'] else None
            if isinstance(prev, tuple) and prev[0] == 'LEMMA':
                cur['blocks'][-1] = (f'<span class="dv-lemma">{prev[1]}.]</span> '
                                     + md_escape(txt))
            else:
                cur['blocks'].append(enum_lead(md_escape(txt)))
        if it['tag'] in ('BODY', 'LEMMA'):
            for pp in it['pages']:
                cur['last'][pp] = len(cur['blocks']) - 1

    # 收尾：孤立的 LEMMA（后面没跟正文）
    for ch in chapters:
        ch['blocks'] = [(f'<span class="dv-lemma">{b[1]}.]</span>'
                         if isinstance(b, tuple) else b) for b in ch['blocks']]

    # 收尾：没配上行内引用的注。原来这些注**整条丢掉**（kramdown 只渲染被
    # 引用到的定义），实测 207 条注只出了 174 条。丢掉的多半是正文里那个符号
    # 被 OCR 吃了或粘进了词里（`Thomasf`）。改成挂在该页最后一段的段尾：
    # 位置退到「本页」这个粒度，比整条丢掉诚实。
    for ch in chapters:
        for (v, pg), q in sorted(notes.items()):
            k = used.get((v, pg), 0)
            if k >= len(q) or (v, pg) not in ch['last']:
                continue
            idx = ch['last'][(v, pg)]
            if not isinstance(ch['blocks'][idx], str):
                continue
            for text in q[k:]:
                fn_seq += 1
                ch['fns'].append((fn_seq, text, (v, pg)))
                ch['blocks'][idx] += f'[^dv{fn_seq}]'
                used[(v, pg)] = used.get((v, pg), 0) + 1

    OUT.mkdir(parents=True, exist_ok=True)
    import subprocess
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True,
                         text=True).stdout.strip()

    def keep(n, key):
        """已有文件里该 front matter 项的原值，没有就 None。

        `date` 按站内规矩「已有文件的时间不要修改」，重跑不该把它刷成当下；
        `zh_url` 是中译发布时另加的，本脚本不知道它，重跑一次就没了。
        """
        f = OUT / f'{n}.md'
        if not f.exists():
            return None
        m = re.search(rf'^{key}: (.*)$', f.read_text(encoding='utf-8'), re.M)
        return m.group(1) if m else None
    n_ch = len(chapters)
    for k, ch in enumerate(chapters):
        n = ch['n'] or (k + 1)
        fm = ['---', 'layout: davenant-chapter', 'book_id: colossians',
              f'book_name: "{BOOK_NAME}"', f'chapter: {n}',
              f'title: "Chapter {ROMAN.get(n, n)}"',
              f'date: {keep(n, "date") or now}']
        if k:
            fm += [f'prev_section: {chapters[k-1]["n"] or k}',
                   f'prev_label: "Chapter {ROMAN.get(chapters[k-1]["n"], k)}"']
        if k + 1 < n_ch:
            fm += [f'next_section: {chapters[k+1]["n"] or k+2}',
                   f'next_label: "Chapter {ROMAN.get(chapters[k+1]["n"], k+2)}"']
        zh = keep(n, 'zh_url')
        if zh:
            fm.append(f'zh_url: {zh}')
        fm.append('---')
        body = [f'# CHAPTER {ROMAN.get(n, n)}', '']
        body += [b for blk in ch['blocks'] for b in (blk, '')]
        if ch['fns']:
            body += ['', '---', '']
            sym_seen = {}                 # (卷,页) → 该页已出现几条带符号的注
            for seq, text, (v, pg) in ch['fns']:
                # ⚠️ 先改符号再转义：md_escape 会把块首的 `+` 转成 `\+`，
                # 之后 FN_DAGGER 就认不出来了（实测 30 条一条没改到）。
                fixed, has_sym = fix_fn_symbol(text, sym_seen.get((v, pg), 0))
                esc = md_escape(fixed)
                if has_sym:
                    sym_seen[(v, pg)] = sym_seen.get((v, pg), 0) + 1
                body.append(f'[^dv{seq}]: {esc}  <span '
                            f'class="dv-fn-page">Vol. {ROMAN[v]}. p. '
                            f'{pg + PRINTED[v]}</span>')
                body.append('')
        (OUT / f'{n}.md').write_text('\n'.join(fm) + '\n\n' + '\n'.join(body) + '\n',
                                     encoding='utf-8')
        print(f'  → {OUT.name}/{n}.md  段落 {len(ch["blocks"])}  脚注 {len(ch["fns"])}')

    (OUT / 'index.html').write_text(
        '---\nlayout: davenant-book\nbook_id: colossians\n'
        f'book_name: "{BOOK_NAME}"\nchapters: {n_ch}\n---\n', encoding='utf-8')
    tot_fn = sum(len(c['fns']) for c in chapters)
    print(f'[ok] {n_ch} 章，行内配对脚注 {tot_fn} / 共 '
          f'{sum(len(v) for v in notes.values())} 条')
    return 0


if __name__ == '__main__':
    sys.exit(main())
