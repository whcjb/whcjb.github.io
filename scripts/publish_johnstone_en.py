#!/usr/bin/env python3
"""johnstone_raw/philippians/en_chapters/*.md → johnstone/philippians/*.md + index.html

    python3 scripts/publish_johnstone_en.py            # 试跑，只报不写
    python3 scripts/publish_johnstone_en.py --apply

做四件事：
  1. 补 front matter（layout / 上下篇导航 / 时间戳）
  2. 讲章开头那段被讲解的经文 → `.jh-epigraph` 题记块
  3. 书末希腊文注的节号 `Ver. 1.` → `.jh-vref`
  4. 生成书卷首页 index.html

**已发布文件的 date 一律沿用原值**，只有新建的才写当前真实时间
（CLAUDE.md：已有文件的时间不要修改）。时刻落在 en_meta.json，
重跑不会把 38 篇的发布时间集体改成今天。

经文出处**不写死在脚本里**，从每篇自己的题记末尾取（`—PHIL. i. 1, 2.`）。
手抄目录是另一处可能抄错的地方，底本自己给得出来就不要手抄。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'johnstone_raw' / 'philippians'
SRC = RAW / 'en_chapters'
OUT = ROOT / 'johnstone' / 'philippians'
META = RAW / 'en_meta.json'

BOOK_ID = 'philippians'
BOOK_NAME = 'Johnstone on Philippians'
AUTHOR = 'Robert Johnstone, LL.B. (1875)'
EDITION = 'Lectures Exegetical and Practical · Edinburgh: William Oliphant, 1875'

ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
         'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX',
         'XXI', 'XXII', 'XXIII', 'XXIV', 'XXV', 'XXVI', 'XXVII', 'XXVIII',
         'XXIX', 'XXX']

TAIL_TITLES = {
    'preface': 'Preface',
    'introduction': 'Introduction',
    'translation': 'Revised Translation of the Epistle',
    'notes-1': 'Notes on the Greek Text · Chapter I',
    'notes-2': 'Notes on the Greek Text · Chapter II',
    'notes-3': 'Notes on the Greek Text · Chapter III',
    'notes-4': 'Notes on the Greek Text · Chapter IV',
    'polycarp': 'Appendix · Epistle of Polycarp to the Philippians',
}

# 题记（被讲解的那段经文）末尾的出处：`—PHIL. i. 1, 2.`
# 三十篇全找得到，但写法很花：章号有 `i.` `ii,` `1].` `2`，节号里 1 常印成
# 罗马数字 `I`，还夹着斜体星号和 OCR 噪点（`PHIL. ii. 5-11. Τ᾿"`）。
RE_REF = re.compile(r'PHIL[.,]?\s*(.{0,36})$', re.I | re.S)
RE_CH = re.compile(r'^\W*([ivx]{1,4})\b', re.I)
CH_NUM = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4}
# 希腊文注的节号。只有第一条写全了 `Ver. 1.`，后面一律只印数字
# （`3.` `16,17.`），所以**裸数字那一支只在 notes-* 里开**——
# 别处段落以数字起头的多得是（引文编号、年份），一开全书就乱标。
RE_VER = re.compile(r'^(Vers?\.\s*\d{1,3}(?:\s*[,-]\s*\d{1,3})*\.)')
RE_VER_BARE = re.compile(r'^(\d{1,3}(?:\s*[,-]\s*\d{1,3})*\.)(?=\s)')
# 罗马数字单独成段 = 讲章序号；全大写单独成段 = 讲题。两者都已经写进
# front matter 的 title，正文里不再重复。
RE_ROMAN_ONLY = re.compile(r'^\W{0,3}[IVXLivxl]{1,6}[.,]?\W{0,3}$')
RE_CAPS_ONLY = re.compile(r'^[^a-z]{5,}$')


def parse_ref(tail, fallback_ch):
    """`i. I, 2.` → ('i', '1, 2')。章号读不出就沿用上一篇的（章号单调不减）。

    OCR 把章号读成 `2`（第 4 讲）和 `1].`（第 13 讲）两处 —— 与其为这两处
    写专门的字形规则，不如用「章号只能是 i–iv 且不倒退」这条结构约束兜，
    它同时也拦得住以后别的读法。
    """
    t = tail.replace('*', ' ')
    m = RE_CH.match(t)
    ch = m.group(1).lower() if m and m.group(1).lower() in CH_NUM else None
    if ch is None or (fallback_ch and CH_NUM[ch] < CH_NUM[fallback_ch]):
        ch = fallback_ch
    if ch is None:
        return None, None
    rest = t[m.end():] if m else t
    rest = re.sub(r'\bIst\b', '1st', rest)
    rest = re.sub(r'\b2d\b', '2nd', rest)
    rest = re.sub(r'\b3d\b', '3rd', rest)
    # 节号里的 1 常印成罗马数字 I：`i. I, 2.` `ii. I-4.` `iv. I.`
    rest = re.sub(r'(?<![A-Za-z])I(?![A-Za-z])', '1', rest)
    # 章号读花时它的残骸还留在串里（`2 12-18.`、`1]. 12, 13.`），
    # 只取第一个数字就会把残骸当成节号。改成**全扫一遍取最长的那一段**。
    # `21, 1st clause` 这一支必须排在 `, 2` 那一支**前面**：
    # 否则 `(?:,\s*\d{1,3})*` 会先把 `, 1` 吃掉，剩下 `st clause` 配不上，
    # 出来就是 `i. 21, 1`（三篇讲章中招）。
    VERSE = re.compile(
        r'\d{1,3}(?:\s*[-–—]\s*\d{1,3})?'
        r'(?:\s*,\s*\d(?:st|nd|rd)\s+clause|(?:\s*,\s*\d{1,3})*)')
    best = max((m3.group(0) for m3 in VERSE.finditer(rest)), key=len, default='')
    verses = re.sub(r'\s*([-–—])\s*', '–', best.strip())
    verses = re.sub(r'\s*,\s*', ', ', verses)
    return ch, verses


def order():
    """发布顺序 = 原书顺序。"""
    return (['preface', 'introduction'] + [str(i) for i in range(1, 31)]
            + ['translation', 'notes-1', 'notes-2', 'notes-3', 'notes-4',
               'polycarp'])


def nice_ref(roman, verses):
    v = re.sub(r'\s+', '', verses).strip(' .,')
    v = v.replace('—', '–').replace('-', '–')
    return f'Philippians {roman.lower()}. {v}' if v else f'Philippians {roman.lower()}.'


def split_paras(text):
    body = text.split('\n', 1)[1] if text.startswith('# ') else text
    return [p.strip() for p in body.split('\n\n') if p.strip()]


def render(paras, fallback_ch, slug=''):
    """段落 → 正文，并顺带取出经文出处与题记。

    题记不一定只占一段：第 9 讲的经文与出处被排版拆成了两段
    （`…gospel of Christ.’—` / `PHIL. i. 27, 1st clause.`）。
    所以按「出处落在哪一段」往回圈，把序号行、讲题行之后到出处那一段
    整个收进题记，而不是只收一段。
    """
    ref = ch = None
    ref_at = None
    for i, p in enumerate(paras[:6]):
        m = RE_REF.search(p.replace('\n', ' '))
        if m:
            ch, verses = parse_ref(m.group(1), fallback_ch)
            if ch:
                ref = f'Philippians {ch}. {verses}' if verses else f'Philippians {ch}.'
                ref_at = i
            break

    out, start = [], 0
    for i, p in enumerate(paras[:3]):
        if RE_ROMAN_ONLY.match(p) or RE_CAPS_ONLY.match(p.strip('* ')):
            start = i + 1                 # 序号行、讲题行：已在 title 里
    if ref_at is not None and ref_at >= start:
        head = '\n\n'.join(paras[start:ref_at + 1])
        head = RE_REF.sub('', head.replace('\n', ' ')).rstrip(' —–-.,')
        out.append('<div class="jh-epigraph" markdown="1">\n\n' + head
                   + f'\n\n<span class="jh-ref">{ref}</span>\n\n</div>')
        start = ref_at + 1

    notes = slug.startswith('notes-')
    for p in paras[start:]:
        m = RE_VER.match(p) or (RE_VER_BARE.match(p) if notes else None)
        if m:
            p = f'<span class="jh-vref">{m.group(1)}</span>' + p[m.end():]
        out.append(p)
    return '\n\n'.join(out), ref, ch


def load_meta():
    if META.exists():
        return json.loads(META.read_text(encoding='utf-8'))
    return {}


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True,
                          text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    meta = load_meta()
    stamp = now()
    seq = [s for s in order() if (SRC / f'{s}.md').exists()]
    missing = [s for s in order() if not (SRC / f'{s}.md').exists()]
    if missing:
        print('⚠️ 缺章：' + ' '.join(missing), file=sys.stderr)

    pages, ch = [], None
    for s in seq:
        paras = split_paras((SRC / f'{s}.md').read_text(encoding='utf-8'))
        body, ref, got = render(paras, ch if s.isdigit() else None, s)
        if got:
            ch = got
        if s.isdigit():
            n = int(s)
            title = f'Lecture {ROMAN[n - 1]}'
            subtitle = (SRC / f'{s}.md').read_text(encoding='utf-8') \
                .split('\n', 1)[0].lstrip('# ').strip()
        else:
            title = TAIL_TITLES.get(s, s)
            subtitle = None
        pages.append(dict(slug=s, title=title, subtitle=subtitle, ref=ref,
                          body=body, chars=len(body)))

    for i, pg in enumerate(pages):
        pg['prev'] = pages[i - 1] if i else None
        pg['next'] = pages[i + 1] if i + 1 < len(pages) else None

    OUT.mkdir(parents=True, exist_ok=True)
    wrote = 0
    for pg in pages:
        slug = pg['slug']
        if slug not in meta:
            meta[slug] = stamp
        label = lambda p: (f"{p['title']} · {p['subtitle']}" if p['subtitle']
                           else p['title'])
        fm = ['---', 'layout: johnstone-chapter', f'book_id: {BOOK_ID}',
              f'book_name: "{BOOK_NAME}"',
              f'title: "{pg["title"]}{" · " + pg["subtitle"] if pg["subtitle"] else ""}"']
        if pg['ref']:
            fm.append(f'subtitle: "{pg["ref"]}"')
        fm.append(f'date: {meta[slug]}')
        if pg['prev']:
            fm += [f'prev_url: "/johnstone/{BOOK_ID}/{pg["prev"]["slug"]}/"',
                   f'prev_label: "{label(pg["prev"])}"']
        if pg['next']:
            fm += [f'next_url: "/johnstone/{BOOK_ID}/{pg["next"]["slug"]}/"',
                   f'next_label: "{label(pg["next"])}"']
        fm.append('---')
        text = '\n'.join(fm) + '\n\n' + pg['body'] + '\n'
        path = OUT / f'{slug}.md'
        if a.apply:
            path.write_text(text, encoding='utf-8')
        wrote += 1

    if a.apply:
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n',
                        encoding='utf-8')
        (OUT / 'index.html').write_text(build_index(pages), encoding='utf-8')

    print(f'{"写入" if a.apply else "试跑"} {wrote} 篇 → {OUT}', file=sys.stderr)
    for pg in pages:
        print(f'  {pg["slug"]:13s} {pg["chars"]:7d}  {pg["title"]}'
              f'{" · " + pg["subtitle"] if pg["subtitle"] else ""}'
              f'{"   [" + pg["ref"] + "]" if pg["ref"] else ""}', file=sys.stderr)


GROUPS = [
    ('卷首', ['preface', 'introduction']),
    ('讲章 · 三十篇', [str(i) for i in range(1, 31)]),
    ('修订译文与希腊文注', ['translation', 'notes-1', 'notes-2', 'notes-3',
                            'notes-4']),
    ('附录', ['polycarp']),
]


def build_index(pages):
    by = {p['slug']: p for p in pages}
    out = ['---', 'layout: johnstone-book', f'book_id: {BOOK_ID}',
           f'book_name: "{BOOK_NAME}"', f'author: "{AUTHOR}"',
           f'edition: "{EDITION}"',
           'title: "Johnstone on Philippians"', '---', '']
    for group, slugs in GROUPS:
        slugs = [s for s in slugs if s in by]
        if not slugs:
            continue
        out.append(f'<h2 class="jh-group">{group} <small>'
                   f'（{len(slugs)} 篇）</small></h2>')
        out.append('<ul class="jh-toc">')
        for s in slugs:
            p = by[s]
            no = p['title'] if s.isdigit() else ''
            name = p['subtitle'] or p['title']
            ref = f'<span class="jh-ref">{p["ref"]}</span>' if p['ref'] else ''
            out.append(
                f'  <li><a href="{{{{ site.baseurl }}}}/johnstone/{BOOK_ID}/{s}/">'
                + (f'<span class="jh-no">{no}</span>' if no else '')
                + f'{name}{"<br>" + ref if ref else ""}</a></li>')
        out.append('</ul>')
    out.append(
        '<p class="jh-note">底本：Internet Archive <code>lecturesexegeti00john</code>'
        '（1875 年爱丁堡 William Oliphant 初版，多伦多大学 Robarts 图书馆藏本）。'
        '正文由页图重新 OCR 并与 ABBYY 版面流合并而成，'
        '处理过程见 <code>johnstone_raw/philippians/PROVENANCE.md</code>。</p>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
