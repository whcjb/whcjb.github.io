#!/usr/bin/env python3
"""candlish_raw/1john/zh_chapters/*.md → candlish/1john/zh/*.md（中文版）。

    python3 scripts/publish_candlish_zh.py

骨架照搬 publish_attersoll_zh.py。与英文版共用 candlish-chapter / candlish-book 两个 layout，
靠 `zh: true` 切换（中文页才挂经文引用弹层，layout 里已接）。
篇目、讲次、经节、章归属一律读**英文页的 front matter 与英文章目录页**（publish_candlish_en 是唯一来源）。

- 上下篇导航只在已译的篇之间串；date 取 zh_meta.json 里该篇实际译完的时刻。
- 有已译讲章的章才出中文章目录 zh/<章>.md；书首页 /candlish/1john/ 换成中文目录，英文目录在 /en/。
- 跑完回调 publish_candlish_en.py --apply（英文页挂 zh_url），再重建「历代解经」数据。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import sect_names  # noqa: E402  教派名补原名

RAW = ROOT / 'candlish_raw' / '1john'
ZH_RAW = RAW / 'zh_chapters'
META = RAW / 'zh_meta.json'
EN = ROOT / 'candlish' / '1john'
OUT = EN / 'zh'
BOOK_NAME_ZH = '坎德利什《约翰一书讲解》'
AUTHOR_ZH = '罗伯特·坎德利什'
AUTHOR_EN = 'Robert S. Candlish'
FM_DATE = re.compile(r'^date:\s*(.+)$', re.M)
CN_NUM = '〇一二三四五六七八九'

FRONT = {'preface-2': ('第二版序', '1869'), 'preface-1': ('初版序', '1866'), 'contents': ('全书纲目', '作者原拟的分析目录')}


def cn(n: int) -> str:
    """1–99 → 一 … 九十九"""
    if n < 10:
        return CN_NUM[n]
    t, u = divmod(n, 10)
    return ('' if t == 1 else CN_NUM[t]) + '十' + (CN_NUM[u] if u else '')


def en_fm(slug):
    t = (EN / f'{slug}.md').read_text(encoding='utf-8')
    fm = t.split('\n---\n', 1)[0]
    d = {}
    for ln in fm.splitlines()[1:]:
        k, _, v = ln.partition(':')
        d[k.strip()] = v.strip().strip('"')
    return d


def pages():
    lect = sorted((p.stem for p in EN.glob('lecture-*.md')), key=lambda x: int(x.split('-')[1]))
    out = []
    for s in ['preface-2', 'preface-1', 'contents'] + lect:
        d = en_fm(s)
        p = dict(slug=s, en=d)
        if s.startswith('lecture-'):
            p['k'] = int(d['lecture'])
            p['ch'] = int(d['chapter'])
            m = re.search(r'1 John ([\d:–,\-\s]+)$', d.get('subtitle', ''))
            p['ref'] = '约翰一书 ' + m.group(1).strip() if m else ''
        out.append(p)
    return out


def label(p):
    return f'第{cn(p["k"])}讲' if 'k' in p else FRONT[p['slug']][0]


def subtitle(p):
    return f'{AUTHOR_EN} · {p["ref"]}' if 'k' in p else FRONT[p['slug']][1]


RE_OL = re.compile(r'^(\d+)\. ', re.M)
ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")


def _ref_books_re():
    src = (ROOT / '_includes' / 'scripture-popup.html').read_text(encoding='utf-8')
    a = src.index('var BOOKS = ['); b = src.index('];', a)
    names = sorted(re.findall(r"\['([^']+)',\d+\]", src[a:b]), key=len, reverse=True)
    return re.compile(r'\*([^*\n]*?)(' + '|'.join(map(re.escape, names)) + r')\*(?=\s*\d{1,3}\s*[:：]\s*\d)')


REF_BOOK_ITALIC = _ref_books_re()


def _unitalic_ref(m):
    pre = m.group(1)
    if not pre.strip():
        return m.group(2)
    core = pre.rstrip()
    return f'*{core}*{pre[len(core):]}{m.group(2)}'


def clean(body: str) -> str:
    body = re.sub(r'(?<!\*)\*\*(?!\*)', '', body)
    body = re.sub(r'<<<[^>]*>>>', '', body)
    body = REF_BOOK_ITALIC.sub(_unitalic_ref, body)
    body = RE_OL.sub(r'\1\\. ', body)
    body = re.sub(r'^(#+ .*)$', lambda m: m.group(1).replace('*', ''), body, flags=re.M)
    body = ORIG_NAME.sub(r'<span class="cd-orig">[\1]</span>', body)
    body = re.sub(r'(<p>)(.*?)(</p>)',
                  lambda m: m.group(1) + re.sub(r'\*([^*]+)\*', r'<i>\1</i>', m.group(2)) + m.group(3), body)
    return body.strip()


# 全书纲目是结构化目录，不能听凭模型排版（2026-11-03：编号有「一、」「第三讲」「XV.」「[四、…]」多种、
# 经节写法各异、链接全指英文页）。逐条按固定格式重排：第N讲　[标题（约翰一书 X）](中文页或英文页)。
RE_TOC = re.compile(r'^(.*?)\[(.*?)\]\(\{\{ site\.baseurl \}\}/candlish/1john/((?:lecture-\d+)|preface-[12])/\)\s*$', re.M)
RE_NUMPFX = re.compile(r'^\s*(?:第[一二三四五六七八九十〇]+讲|[一二三四五六七八九十〇]+、|[IVXLC]+\.)\s*')
RE_REFTAIL = re.compile(r'[\s：:—\-（(，,]*约翰一书\s*[\d:：–\-,，、；;\s]+[）)]?[。.]?\s*$')


def fix_contents(body, done, allp):
    def rep(m):
        slug = m.group(3)
        url = f'{{{{ site.baseurl }}}}/candlish/1john/{"zh/" if slug in done else ""}{slug}/'
        if slug.startswith('preface'):
            return f'[{FRONT[slug][0]}]({url})'
        p = allp[slug]
        title = RE_NUMPFX.sub('', RE_NUMPFX.sub('', m.group(1).strip()) + m.group(2)).strip()
        title = RE_REFTAIL.sub('', title).rstrip('：:——-，, 。.')
        return f'{label(p)}　[{title}（{TOC_REF.get(slug) or p["ref"]}）]({url})'
    return RE_TOC.sub(rep, body)


def _toc_refs():
    """英文纲目每条末尾的讲题经文（:—1 JOHN 1:3）→ 约翰一书 1:3。纲目经节照原书，不取讲章覆盖范围。"""
    t = (EN / 'contents.md').read_text(encoding='utf-8')
    out = {}
    for m in re.finditer(r'\[[^\]]*?[:：]?—\s*1 JOHN\s*([^\]]+?)\.?\]\(\{\{ site\.baseurl \}\}/candlish/1john/(lecture-\d+)/\)', t):
        ref = re.sub(r'\s*:\s*', ':', m.group(1).strip()).replace(' ;', ';')
        ref = re.sub(r'\s+and\s+', '、', ref)
        out[m.group(2)] = '约翰一书 ' + ref
    return out


TOC_REF = _toc_refs()


def existing_date(path: Path):
    if not path.exists():
        return None
    m = FM_DATE.search(path.read_text(encoding='utf-8')[:800])
    return m.group(1).strip() if m else None


def main():
    allp = pages()
    done = {p.stem for p in ZH_RAW.glob('*.md')}
    names = [p for p in allp if p['slug'] in done]
    if not names:
        sys.exit('zh_chapters 里没有任何已译的篇')
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True, check=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)

    for k, p in enumerate(names):
        slug = p['slug']
        path = OUT / f'{slug}.md'
        date = meta.get(slug) or existing_date(path) or now
        fm = ['---', 'layout: candlish-chapter', 'book_id: 1john', f'book_name: "{BOOK_NAME_ZH}"',
              f'title: "{label(p)}"', f'subtitle: "{subtitle(p)}"', f'date: {date}']
        if 'k' in p:
            fm += [f'chapter: {p["ch"]}', f'lecture: {p["k"]}']
        if k > 0:
            q = names[k - 1]
            fm += [f'prev_url: "/candlish/1john/zh/{q["slug"]}/"', f'prev_label: "{label(q)}"']
        if k + 1 < len(names):
            q = names[k + 1]
            fm += [f'next_url: "/candlish/1john/zh/{q["slug"]}/"', f'next_label: "{label(q)}"']
        fm += [f'en_url: "/candlish/1john/{slug}/"', 'zh: true', '---']
        body = clean((ZH_RAW / f'{slug}.md').read_text(encoding='utf-8'))
        if slug == 'contents':
            body = fix_contents(body, {q['slug'] for q in names}, {q['slug']: q for q in allp})
        body = sect_names.annotate(body, (EN / f'{slug}.md').read_text(encoding='utf-8'), 'cd-orig')
        path.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    # 章目录：按英文章目录页列出的讲章，只列已译的
    for c in range(1, 6):
        en_ch = (EN / f'{c}.md').read_text(encoding='utf-8')
        slugs = re.findall(r'/candlish/1john/(lecture-\d+)/', en_ch)
        lst = [p for p in names if p['slug'] in slugs]
        if not lst:
            continue
        items = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/candlish/1john/zh/{p["slug"]}/">{label(p)}'
                          f'<span class="cd-ref">{p["ref"]}</span></a></li>' for p in lst)
        fm = ['---', 'layout: candlish-chapter', 'book_id: 1john', f'book_name: "{BOOK_NAME_ZH}"',
              f'title: "约翰一书 第 {c} 章"', f'subtitle: "{AUTHOR_EN}"',
              f'date: {meta.get(lst[-1]["slug"], now)}', f'chapter: {c}',
              f'en_url: "/candlish/1john/{c}/"', 'zh: true', '---']
        (OUT / f'{c}.md').write_text('\n'.join(fm) + f'\n\n<ul class="cd-chtoc">\n{items}\n</ul>\n',
                                     encoding='utf-8')

    (EN / 'index.html').write_text(build_index(names, allp), encoding='utf-8')
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'publish_candlish_en.py'), '--apply'],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 英文页回调失败：' + r.stderr[-300:], file=sys.stderr)
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_commentaries_index.py')],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 历代解经数据重建失败：' + r.stderr[-300:], file=sys.stderr)
    print(f'发布中文 {len(names)}/{len(allp)} 篇 → {OUT}')


def build_index(names, allp):
    out = ['---', 'layout: candlish-book', 'book_id: 1john', f'book_name: "{BOOK_NAME_ZH}"',
           f'title: "{BOOK_NAME_ZH}"', f'author: "{AUTHOR_ZH}（Robert S. Candlish，1806–1873）"',
           'edition: "The First Epistle of John Expounded in a Series of Lectures · 爱丁堡，1866；1869 再版"',
           'en_url: "/candlish/1john/en/"', 'zh: true', '---', '']
    front = [p for p in names if 'k' not in p]
    if front:
        out.append('<h2 class="cd-group">卷首</h2>')
        out.append('<ul class="cd-toc cd-toc-sm">')
        out.extend(f'  <li><a href="{{{{ site.baseurl }}}}/candlish/1john/zh/{p["slug"]}/">{label(p)}'
                   f'<small>{subtitle(p)}</small></a></li>' for p in front)
        out.append('</ul>')
    lect = [p for p in names if 'k' in p]
    if lect:
        out.append('<h2 class="cd-group">讲章</h2>')
        # 小按钮网格（用户 2026-11-04：整行长条太占地方）；经文都是约翰一书，按钮里只写章节
        out.append('<ul class="cd-toc cd-toc-sm">')
        out.extend(f'  <li><a href="{{{{ site.baseurl }}}}/candlish/1john/zh/{p["slug"]}/">{label(p)}'
                   f'<small>{p["ref"].replace("约翰一书 ", "")}</small></a></li>' for p in lect)
        out.append('</ul>')
    if len(names) < len(allp):
        out.append(f'<p class="cd-note-zh">中译已上线 {len(names)} / {len(allp)} 篇，逐篇推进；未译的篇见'
                   '<a href="{{ site.baseurl }}/candlish/1john/en/">英文版</a>。底本说明与编者改动逐条说明见英文版首页。</p>')
    else:
        out.append('<p class="cd-note-zh">底本说明与编者改动逐条说明见'
                   '<a href="{{ site.baseurl }}/candlish/1john/en/">英文版首页</a>。</p>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
