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
    """
    return t.replace('*', '\\*').replace('|', '\\|')


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
        if it['tag'] == 'H3':
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

            txt = REF_RE.sub(sub, it['text'])
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
    for kind, txt in u['blocks']:
        if kind == 'H3':
            out.append(f'## {txt}')
        elif kind == 'END':
            out.append(f'<p class="dv-end">{txt}</p>')
        else:
            out.append(enum_lead(md_escape(txt)))
    if u['fns']:
        out += ['', '---', '']
        for seq, text, p in u['fns']:
            out.append(f'[^da{seq}]: {md_escape(text)}  '
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
