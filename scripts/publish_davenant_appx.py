#!/usr/bin/env python3
"""达文南特卷二附卷 raw → davenant/colossians/{dissertation/*,gallican}.md

输入  davenant_raw/colossians/davenant_colossians_appendix.txt
      （scripts/extract_davenant_appx.py 产出）
输出  davenant/colossians/dissertation/0.md   致读者（1683 年 12mo 版的序）
      davenant/colossians/dissertation/1-7.md 《论基督之死》七章
      davenant/colossians/gallican.md         论法国教会之争

脚注归章
--------
raw 里的 `[FN]` 一律排在各自那一块的末尾（提取时是按页扫完正文再扫注区），
所以**不能按出现顺序分章**——那样七章的注会全堆在第七章。改按页号归属：
先由各章 `[BODY]` 的页码标记算出该章的页区间，再把注按页落回去。

行内引用配对与注释正文那边同法（见 publish_davenant_en.py）：脚注符是
每页重置的 `*` / `†` / `‡`，只配 `*` 与 `+` 两种（`†` 常被 OCR 读成 `+`，
读成 `f`/`t`/`J`/`I` 的会粘在词尾，切不出来）。配不上的注不丢，挂在该页
最后一段的段尾——位置退到「本页」这个粒度，比整条丢掉诚实。

用法: python3 scripts/publish_davenant_appx.py
"""
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
OUT = ROOT / 'davenant' / 'colossians'
BOOK_URL = '/davenant/colossians/'
BOOK_LABEL = 'Davenant on Colossians'
ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII'}
PRINTED = -9        # 扫描页号 → 书上印的页码（vol2 实测：p327→318、p571→562）

DISS_KICKER = 'A Dissertation on the Death of Christ'
CN = {                                   # 目录与导航上的中文题名
    0: '致读者',
    1: '第一章 · 争论的由来',
    2: '第二章 · 基督之死为普世的救恩之因',
    3: '第三章 · 答辩',
    4: '第四章 · 第二命题的申述与证立',
    5: '第五章 · 第三命题的申述与证立',
    6: '第六章 · 末一命题的申述与证立',
    7: '第七章 · 基督之死之于蒙拣选者',
}

FN_MARK_START = re.compile(r'^\s*(\*|\+|†|‡|[ftJI])\s+')
REF_RE = re.compile(r'(?<=[\w.,;:)\'"”’])(\*|\+)|(?<=\s)(\*|\+)(?=\s)')


# ── 斜体 ────────────────────────────────────────────────────────────────────
# 原书的斜体承担三种实义：被注释的词句、圣经引语、拉丁词句（DIAGNOSIS §3）。
# 两个文本源都给不出字体信息，所以另跑一遍量笔画倾角，见
# scripts/ocr_davenant_slant.py。全书 45 万词的倾角直方图是清楚的双峰：
# 正体 -6°~+3°（峰在 -2°），斜体 +11°~+21°（峰在 +15°），中间 4°~10° 是空谷。
#
# ⚠️ 这一步必须放在**发布**这一侧，不能塞进提取器。试过在行文本上打标记
# 再一路带下去：标记落在行首，`SECTION_RE` / `LEMMA_RE` 立刻认不出
# （节组 92→85、lemma 328→203），`dehyph` 的「后一行首字母小写才接」也被
# 标记挡掉，跨行断词全断在那里（`ano</em>- <em>ther`）。结构化产物一个字
# 都不动，斜体只在最后贴上去。
IT0, IT1 = '\ue000', '\ue001'
ITALIC_MIN = 9.0
_slant = {}


def slant_words(vol, page):
    """→ [(词, 倾角), …]，该页按 OCR 顺序的全部词。"""
    if vol not in _slant:
        f = RAW / f'vol{vol}_slant.jsonl'
        _slant[vol] = {}
        if f.exists():
            for ln in f.open(encoding='utf-8'):
                r = json.loads(ln)
                _slant[vol][r['page']] = [w for l in r['lines']
                                          for w in l['words']]
    return _slant[vol].get(page, [])


def _nrm(t):
    return re.sub(r'[^a-z0-9]', '', t.lower())


def mark_italics(txt, pages):
    """把 txt 里原书排斜体的词圈上私用码。对不上就原样返回。

    倾角是按页面上的词量的，而 txt 已经过校勘（拆词、换字、接断词），
    所以按归一化词形对齐再贴，不按下标硬配。
    """
    # 附卷这一路的 pages 是**纯页号**（整卷都在卷二），不是 (卷, 页) 对
    stream = [w for pg in pages
              for w in slant_words(*(pg if isinstance(pg, tuple) else (2, pg)))]
    if not stream:
        return txt
    mine = txt.split()
    sm = difflib.SequenceMatcher(None, [_nrm(t) for t in mine],
                                 [_nrm(w[0]) for w in stream], autojunk=False)
    flags = [w[1] is not None and w[1] >= ITALIC_MIN for w in stream]
    mark = [False] * len(mine)
    hit = 0
    for tag, a1, a2, b1, b2 in sm.get_opcodes():
        if tag == 'equal':
            hit += a2 - a1
            for k in range(a2 - a1):
                mark[a1 + k] = flags[b1 + k]
        elif tag == 'replace':
            seg = flags[b1:b2]
            for k in range(a1, a2):
                mark[k] = bool(seg) and all(seg)   # 拆词/并词处要整段都斜才算
    if hit < len(mine) * 0.5:
        return txt                        # 对齐太差，宁可不标
    out, i = [], 0
    while i < len(mine):
        if not mark[i]:
            out.append(mine[i]); i += 1; continue
        j = i
        while j < len(mine) and mark[j]:
            j += 1
        run = mine[i:j]
        run[0] = IT0 + run[0]
        run[-1] = run[-1] + IT1
        out += run
        i = j
    return ' '.join(out)


def italics(t):
    """私用码 → <em>。放在 md_escape 之后：escape 只动 markdown 元字符，
    碰不到私用码；反过来先换成 <em> 就会被 escape 掉。"""
    t = re.sub(IT0 + r'\s*' + IT1, '', t)
    if t.count(IT0) != t.count(IT1):
        return t.replace(IT0, '').replace(IT1, '')   # 落单的丢掉，不留半个标签
    return t.replace(IT0, '<em>').replace(IT1, '</em>')


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


def enum_lead(t):
    """段首编号包成 span，防止 kramdown 变成有序列表。

    论文里大量段落以 `1.` / `2.` 起首（三条命题、各条答辩），原书排的是
    普通段落，不是悬挂列表。不处理的话 kramdown 生成 ol/li，既改了版式，
    还会重排号——单独以 `3.` 起首的段落会被渲染成 `1.`。
    编号后面不限定是拉丁字母：OCR 会把标点留在编号后（`2. , Because…`），
    中译里跟的又是汉字，写死 `[A-Za-z…]` 两种都漏。
    """
    return re.sub(r'^(\d{1,3})\.\s+(?=[^\s\d])',
                  r'<span class="dv-enum">\1.</span> ', t)


def parse():
    items = []
    for ln in (RAW / 'davenant_colossians_appendix.txt').read_text(
            encoding='utf-8').splitlines():
        m = re.match(r'^\[([A-Z0-9_]+)\] (.*)$', ln)
        if not m:
            continue
        tag, rest = m.group(1), m.group(2)
        pm = re.match(r'<!--v(\d+)p(\d+)(?:-(\d+))?-->\s*', rest)
        pages = []
        if pm:
            a, b = int(pm.group(2)), int(pm.group(3) or pm.group(2))
            pages = list(range(a, b + 1))
            rest = rest[pm.end():]
        items.append({'tag': tag, 'text': rest, 'pages': pages})
    return items


def collect_notes(items):
    """→ {page: [note_text, …]}，多段的注合并为一条。

    ⚠️ 一条注**跨页**时也要合。Allport 的传记体长注常连着两三页，续页的注区
    顶上没有脚注符。原来只在同一页内合并，续页一律另起一条，于是读者看到的是
    一条从半句话开始、单独编号的注（`[^da64]: by the minister of that city was
    appointed to teach…`），而正文里那个 `†` 指向的是被砍掉一半的上半条。
    判据：本条不以脚注符起首，且页号正好是上一条的下一页——这正是「注区溢到
    下一页」的物理形态。跨页处用 dehyph 接，`Bergeron` 这种断词不会留下空格。
    """
    notes, cur, cur_p, cur_last = {}, None, None, None
    for it in items:
        if it['tag'] != 'FN':
            continue
        p = it['pages'][0] if it['pages'] else cur_p
        marked = bool(FN_MARK_START.match(it['text']))
        same_note = cur is not None and (
            p == cur_p or (not marked and p == cur_last + 1))
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


def build_units(items):
    """→ [{'key','title','blocks','pages'}]，一个 unit = 一个页面。"""
    units, cur = [], None
    for it in items:
        if it['tag'] == 'SEC':
            sec = it['text'].split('|')[0]
            if sec != 'diss':                     # 序与法国之争各自一页
                cur = {'key': sec, 'sub': '', 'blocks': [], 'pages': set(),
                       'fns': [], 'last': {}}
                units.append(cur)
            continue
        if it['tag'] == 'H1':                     # 论文的章
            n = int(it['text'].split('|')[0])
            cur = {'key': f'diss{n}', 'n': n, 'sub': '', 'blocks': [],
                   'pages': set(), 'fns': [], 'last': {}}
            units.append(cur)
            continue
        if cur is None or it['tag'] == 'FN':
            continue
        if it['tag'] == 'H2':
            # 标题末尾那个 `*` 是脚注符，不是文字。front matter 不过 markdown，
            # 留着会在页面副题上直接印出一个星号；该条注仍会照常输出，
            # 只是行内引用退到本页首段（见 attach_notes 的兜底）。
            cur['sub'] = it['text'].rstrip('*+ ')
            continue
        cur['pages'].update(it['pages'])
        if it['tag'] in ('VERSE', 'CITE'):
            cur['blocks'].append((it['tag'], it['text']))
        elif it['tag'] == 'H3':
            cur['blocks'].append(('H3', it['text']))
        elif it['tag'] == 'END':
            cur['blocks'].append(('END', it['text']))
        else:
            cur['blocks'].append(('P', it))
    return units


def attach_notes(units, notes):
    """行内配对 + 兜底挂段尾。按页归章，见模块 docstring。"""
    used = {p: 0 for p in notes}
    seq = 0
    for u in units:
        for i, (kind, payload) in enumerate(u['blocks']):
            if kind != 'P':
                continue
            it = payload

            def sub(m):
                nonlocal seq
                for p in it['pages']:
                    q = notes.get(p, [])
                    if used.get(p, 0) < len(q):
                        seq += 1
                        u['fns'].append((seq, q[used[p]], p))
                        used[p] += 1
                        return f'[^da{seq}]'
                return m.group(0)              # 该页注已用尽 → 原样留符号

            txt = REF_RE.sub(sub, mark_italics(it['text'], it['pages']))
            u['blocks'][i] = ('P', txt)
            for p in it['pages']:
                u['last'][p] = i
        # 该页还剩没配上行内引用的注 → 挂在本页最后一段段尾
        for p in sorted(u['pages']):
            q = notes.get(p, [])
            k = used.get(p, 0)
            if k >= len(q) or p not in u['last']:
                continue
            idx = u['last'][p]
            kind, txt = u['blocks'][idx]
            for text in q[k:]:
                seq += 1
                u['fns'].append((seq, text, p))
                txt += f'[^da{seq}]'
                used[p] += 1
            u['blocks'][idx] = (kind, txt)
    left = sum(len(q) - used.get(p, 0) for p, q in notes.items())
    return seq, left


def render(u):
    out = []
    blocks = u['blocks']
    i = 0
    while i < len(blocks):
        kind, txt = blocks[i]
        if kind == 'VERSE':
            # 连着的引诗行是一块，原书缩进居中另排；出处行（Cap. 10, &c.）
            # 紧随其后、右对齐，一并收进同一块里
            j = i
            lines = []
            while j < len(blocks) and blocks[j][0] == 'VERSE':
                lines.append(italics(md_escape(blocks[j][1]))); j += 1
            cite = ''
            if j < len(blocks) and blocks[j][0] == 'CITE':
                cite = f'\n<p class="dv-cite">{italics(md_escape(blocks[j][1]))}</p>'
                j += 1
            body = '\n'.join(f'<p>{x}</p>' for x in lines)
            out.append(f'<div class="dv-verse">\n{body}\n</div>{cite}')
            i = j
            continue
        i += 1
        if kind == 'CITE':
            out.append(f'<p class="dv-cite">{italics(md_escape(txt))}</p>')
        elif kind == 'H3':
            out.append(f'## {txt}')
        elif kind == 'END':
            out.append(f'<p class="dv-end">{txt}</p>')
        else:
            out.append(enum_lead(italics(md_escape(txt))))
    if u['fns']:
        out += ['', '---', '']
        sym_seen = {}                     # 页 → 该页已出现几条带符号的注
        for seq, text, p in u['fns']:
            # 先改符号再转义，见 publish_davenant_en.py 同处说明
            fixed, has_sym = fix_fn_symbol(text, sym_seen.get(p, 0))
            esc = md_escape(fixed)
            if has_sym:
                sym_seen[p] = sym_seen.get(p, 0) + 1
            out.append(f'[^da{seq}]: {esc}  '
                       f'<span class="dv-fn-page">Vol. II. p. {p + PRINTED}</span>')
    return out


def main():
    items = parse()
    notes = collect_notes(items)
    units = build_units(items)
    n_fn, left = attach_notes(units, notes)

    # 页面顺序：序 → 论文 I–VII → 法国之争。上一篇/下一篇按这条链串。
    order = ['preface'] + [f'diss{n}' for n in range(1, 8)] + ['gallican']
    by_key = {u['key']: u for u in units}
    chain = [k for k in order if k in by_key]

    def path_of(k):
        return ('dissertation/0.md' if k == 'preface'
                else 'gallican.md' if k == 'gallican'
                else f'dissertation/{k[4:]}.md')

    def url_of(k):
        return (f'{BOOK_URL}dissertation/0/' if k == 'preface'
                else f'{BOOK_URL}gallican/' if k == 'gallican'
                else f'{BOOK_URL}dissertation/{k[4:]}/')

    def label_of(k):
        if k == 'preface':
            return 'To the Kind Reader'
        if k == 'gallican':
            return 'The Gallican Controversy'
        return f'Chapter {ROMAN[int(k[4:])]}'

    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True,
                         text=True).stdout.strip()
    (OUT / 'dissertation').mkdir(parents=True, exist_ok=True)

    for i, k in enumerate(chain):
        u = by_key[k]
        title = label_of(k)
        fm = ['---', 'layout: davenant-appendix', f'title: "{title}"',
              f'up_url: "{BOOK_URL}"', f'up_label: "{BOOK_LABEL}"',
              f'date: {now}']
        if k.startswith('diss') or k == 'preface':
            fm.append(f'kicker: "{DISS_KICKER}"')
        # 序那一页的原书标题就是 TO THE KIND READER，与页面标题重复，不再印一遍
        def _key(x):
            return re.sub(r'[^a-z]', '', x.lower())
        if u['sub'] and _key(u['sub']) != _key(title):
            fm.append(f'subtitle: "{u["sub"]}"')
        if i:
            fm += [f'prev_url: "{url_of(chain[i-1])}"',
                   f'prev_label: "{label_of(chain[i-1])}"']
        if i + 1 < len(chain):
            fm += [f'next_url: "{url_of(chain[i+1])}"',
                   f'next_label: "{label_of(chain[i+1])}"']
        else:
            # 法国之争之后接原书的六种索引（publish_davenant_index.py 出）
            fm += [f'next_url: "{BOOK_URL}indexes/general/"',
                   'next_label: "General Index"']
        fm.append('---')
        body = render(u)
        dst = OUT / path_of(k)
        dst.write_text('\n'.join(fm) + '\n\n' + '\n\n'.join(body) + '\n',
                       encoding='utf-8')
        pr = (f'{min(u["pages"]) + PRINTED}-{max(u["pages"]) + PRINTED}'
              if u['pages'] else '-')
        print(f'  → {dst.relative_to(OUT)}  段 {len(u["blocks"])}  '
              f'注 {len(u["fns"])}  书页 {pr}')

    # 书卷目录页（_layouts/davenant-book.html）要列出这些附卷。
    # 不去改 index.html：那个文件由 publish_davenant_en.py 写，两个脚本
    # 抢同一份 front matter，谁后跑谁把对方的抹掉。改走 Jekyll 的 _data，
    # 各写各的一份，layout 有就渲染、没有就跳过。
    data = ROOT / '_data' / 'davenant_appendix.yml'
    data.parent.mkdir(exist_ok=True)
    y = ['# 由 scripts/publish_davenant_appx.py 生成，勿手改',
         'colossians:',
         f'  - title: "{DISS_KICKER}"',
         '    cn: "论基督之死"',
         '    note: "达文南特在多特会议前后所撰，附于 1831 年英译本卷二之末；'
         '论基督之死的范围与特殊功效，改革宗「假设普救论」的经典文献。"',
         '    items:']
    for k in chain:
        if k == 'gallican':
            continue
        n = 0 if k == 'preface' else int(k[4:])
        y += [f'      - url: "{url_of(k)}"',
              f'        label: "{label_of(k)}"',
              f'        cn: "{CN[n]}"']
    g = by_key.get('gallican')
    y += ['  - title: "On the Gallican Controversy"',
          '    cn: "论法国教会之争"',
          '    note: "法国改革宗内部就『神对罪人施恩得救的旨意』起争，英国神学家'
          '受询而作；达文南特此篇由其侄呈交阿马大主教，原书附于全书之末。"',
          '    items:',
          f'      - url: "{BOOK_URL}gallican/"',
          '        label: "On the Gallican Controversy"',
          '        cn: "论法国教会之争"']
    data.write_text('\n'.join(y) + '\n', encoding='utf-8')
    print(f'  → _data/{data.name}')

    print(f'[ok] {len(chain)} 页，脚注 {n_fn} / 共 '
          f'{sum(len(v) for v in notes.values())} 条'
          + (f'（{left} 条未落位）' if left else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
