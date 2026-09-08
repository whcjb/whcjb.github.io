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
        pm = re.match(r'<!--p(\d+)(?:-(\d+))?-->', rest)
        pages = []
        if pm:
            a = int(pm.group(1))
            b = int(pm.group(2)) if pm.group(2) else a
            pages = list(range(a, b + 1))
            rest = rest[pm.end():]
        items.append({'tag': tag, 'text': rest, 'pages': pages})
    return items


def collect_notes(items):
    """→ {page: [note_text, …]}，多段的注合并为一条。"""
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


def md_escape(t):
    """OCR 文本里的 `*` 会被 kramdown 当强调符——凡不是脚注引用的都转义。"""
    return t.replace('*', '\\*')


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
    chapters, cur = [], None

    for it in items:
        if it['tag'] == 'TITLE':
            continue
        if it['tag'] == 'FN':
            continue
        if it['tag'] == 'H1':
            m = re.search(r'CHAP\.\s*([IVX]+)', it['text'])
            n = {v: k for k, v in ROMAN.items()}.get(m.group(1)) if m else None
            cur = {'n': n, 'blocks': [], 'fns': []}
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
            nums = re.findall(r'\d+|[IVXLivxl]+', txt)
            anchor = f'colossians-{cur["n"]}-{nums[0]}' if nums and cur['n'] else ''
            if anchor:
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
                cur['blocks'].append(md_escape(txt))

    # 收尾：孤立的 LEMMA（后面没跟正文）
    for ch in chapters:
        ch['blocks'] = [(f'<span class="dv-lemma">{b[1]}.]</span>'
                         if isinstance(b, tuple) else b) for b in ch['blocks']]

    OUT.mkdir(parents=True, exist_ok=True)
    import subprocess
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True,
                         text=True).stdout.strip()
    n_ch = len(chapters)
    for k, ch in enumerate(chapters):
        n = ch['n'] or (k + 1)
        fm = ['---', 'layout: davenant-chapter', 'book_id: colossians',
              f'book_name: "{BOOK_NAME}"', f'chapter: {n}',
              f'title: "Chapter {ROMAN.get(n, n)}"', f'date: {now}']
        if k:
            fm += [f'prev_section: {chapters[k-1]["n"] or k}',
                   f'prev_label: "Chapter {ROMAN.get(chapters[k-1]["n"], k)}"']
        if k + 1 < n_ch:
            fm += [f'next_section: {chapters[k+1]["n"] or k+2}',
                   f'next_label: "Chapter {ROMAN.get(chapters[k+1]["n"], k+2)}"']
        fm.append('---')
        body = [f'# CHAPTER {ROMAN.get(n, n)}', '']
        body += [b for blk in ch['blocks'] for b in (blk, '')]
        if ch['fns']:
            body += ['', '---', '']
            for seq, text, p in ch['fns']:
                body.append(f'[^dv{seq}]: {md_escape(text)}  <span '
                            f'class="dv-fn-page">p.{p}</span>')
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
