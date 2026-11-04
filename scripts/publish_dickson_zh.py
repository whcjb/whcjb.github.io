#!/usr/bin/env python3
"""dickson_raw/matthew/zh_chapters/*.md → dickson/matthew/zh/*.md（中文版）。

    python3 scripts/publish_dickson_zh.py

骨架照搬 publish_taylor_zh.py。英文版一章一页（用户 2026-11-04），中文版同样：zh/<章>.md、卷首 zh/<篇名>.md。
与英文版共用 dickson-chapter / dickson-book 两个 layout，靠 `zh: true` 切换（中文页才挂经文引用弹层）。

- 上下篇导航**只在已译的篇之间串**（指向未译的篇等于送读者去 404）。
- date 取 zh_meta.json 里该篇**实际译完的时刻**；取不到才沿用已发布文件原值，再取不到才用当前时间。
- 书首页 /dickson/matthew/ 换成中文目录：28 章格子照排，已译的章链中文，未译的链英文并标「英文」；
  英文目录在 /en/（publish_dickson_en 见到 zh/ 就不再覆盖首页）。
- 跑完回调 publish_dickson_en.py --apply，让英文页补上「中文版 →」；再重建「历代解经」数据。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import sect_names  # noqa: E402  教派名补原名
import publish_dickson_en as P  # noqa: E402

RAW = ROOT / 'dickson_raw' / 'matthew'
ZH_RAW = RAW / 'zh_chapters'
META = RAW / 'zh_meta.json'
EN = ROOT / 'dickson' / 'matthew'
OUT = EN / 'zh'
BOOK_NAME_ZH = '迪克森《马太福音简释》'
AUTHOR_ZH = '大卫·迪克森'
AUTHOR_EN = 'David Dickson'   # 页面副标题一律写英文原名（用户 2026-10-16 定）
FM_DATE = re.compile(r'^date:\s*(.+)$', re.M)
CN = '零一二三四五六七八九'

LABEL = {
    'title': ('书名页', '伦敦，1651'),
    'dedication': ('献辞', '致苏格兰大法官劳登伯爵（Earl of Loudoun）'),
    'to-the-reader': ('致诚实的读者', AUTHOR_EN),
    'titles': ('本书的标题', '新约；马太所记的福音'),
}


def cn(n):
    if n < 10:
        return CN[n]
    t, u = divmod(n, 10)
    return ('' if t == 1 else CN[t]) + '十' + (CN[u] if u else '')


def label(slug):
    return f'马太福音 第{cn(int(slug))}章' if slug.isdigit() else LABEL[slug][0]


def subtitle(slug):
    return AUTHOR_EN if slug.isdigit() else LABEL[slug][1]


# 原书分条「2. …」各自成段——段首「数字 + 点 + 空格」会被 kramdown 当成有序列表。转义那个点。
RE_OL = re.compile(r'^(\d+)\. ', re.M)
# 音译专名后的原名括注「（Augustine）」→ 小一号灰字方括号（样式在 layout 的 .dk-orig）
ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")


def _ref_books_re():
    """经文弹层认的中文书卷名，直接从 _includes/scripture-popup.html 的 BOOKS 表读。"""
    src = (ROOT / '_includes' / 'scripture-popup.html').read_text(encoding='utf-8')
    a = src.index('var BOOKS = ['); b = src.index('];', a)
    names = sorted(re.findall(r"\['([^']+)',\d+\]", src[a:b]), key=len, reverse=True)
    return re.compile(r'\*([^*\n]*?)(' + '|'.join(map(re.escape, names)) + r')\*(?=\s*\d{1,3}\s*[:：]\s*\d)')


# 书卷名排斜体「*马太福音* 10:4」——书名与章节号落在两个文本节点，经文弹层认不出：书名挪到斜体外
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
    body = ORIG_NAME.sub(r'<span class="dk-orig">[\1]</span>', body)
    body = re.sub(r'<span class="dk-dropcap"></span>([^\s<*])', r'<span class="dk-dropcap">\1</span>', body)
    # HTML 块里 kramdown 不解析 *斜体*：换回 <i>
    body = re.sub(r'(<p>)(.*?)(</p>)',
                  lambda m: m.group(1) + re.sub(r'\*([^*]+)\*', r'<i>\1</i>', m.group(2)) + m.group(3), body)
    return body.strip()


def existing_date(path: Path):
    if not path.exists():
        return None
    m = FM_DATE.search(path.read_text(encoding='utf-8')[:800])
    return m.group(1).strip() if m else None


def main():
    order = [x[0] for x in P.BOOK.front] + [str(c) for c in sorted(P.NV)]
    done = {p.stem for p in ZH_RAW.glob('*.md')}
    names = [s for s in order if s in done]
    if not names:
        sys.exit('zh_chapters 里没有任何已译的篇')
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True,
                         check=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)

    for k, slug in enumerate(names):
        path = OUT / f'{slug}.md'
        date = meta.get(slug) or existing_date(path) or now
        fm = ['---', 'layout: dickson-chapter', 'book_id: matthew',
              f'book_name: "{BOOK_NAME_ZH}"', f'title: "{label(slug)}"',
              f'subtitle: "{subtitle(slug)}"', f'date: {date}']
        if slug.isdigit():
            fm += [f'chapter: {slug}', 'verse_from: 1', f'verse_to: {P.NV[int(slug)]}']
        if k > 0:
            q = names[k - 1]
            fm += [f'prev_url: "/dickson/matthew/zh/{q}/"', f'prev_label: "{label(q)}"']
        if k + 1 < len(names):
            q = names[k + 1]
            fm += [f'next_url: "/dickson/matthew/zh/{q}/"', f'next_label: "{label(q)}"']
        fm += [f'en_url: "/dickson/matthew/{slug}/"', 'zh: true', '---']
        body = clean((ZH_RAW / f'{slug}.md').read_text(encoding='utf-8'))
        body = sect_names.annotate(body, (EN / f'{slug}.md').read_text(encoding='utf-8'), 'dk-orig')
        path.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    (EN / 'index.html').write_text(build_index(names), encoding='utf-8')
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'publish_dickson_en.py'), '--apply'],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 英文页回调失败：' + r.stderr[-300:], file=sys.stderr)
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_commentaries_index.py')],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 历代解经数据重建失败：' + r.stderr[-300:], file=sys.stderr)
    print(f'发布中文 {len(names)}/{len(order)} 篇 → {OUT}')


def build_index(names):
    out = ['---', 'layout: dickson-book', 'book_id: matthew', f'book_name: "{BOOK_NAME_ZH}"',
           f'title: "{BOOK_NAME_ZH}"', f'author: "{AUTHOR_ZH}（David Dickson，1583?–1663）"',
           'edition: "A Brief Exposition of the Evangel of Jesus Christ according to Matthew · 伦敦，1651（第三版）"',
           'en_url: "/dickson/matthew/en/"', 'zh: true', '---', '']
    front = [s for s in names if not s.isdigit()]
    if front:
        out.append('<h2 class="dk-group">卷首</h2>')
        out.append('<ul class="dk-toc">')
        out.extend(f'  <li><a href="{{{{ site.baseurl }}}}/dickson/matthew/zh/{s}/">{label(s)}'
                   f'<small>{subtitle(s)}</small></a></li>' for s in front)
        out.append('</ul>')
    out.append('<h2 class="dk-group">各章</h2>')
    cells = []
    for c in sorted(P.NV):
        if str(c) in names:
            cells.append(f'<li><a href="{{{{ site.baseurl }}}}/dickson/matthew/zh/{c}/">第{cn(c)}章</a></li>')
        else:
            cells.append(f'<li><a class="dk-other" href="{{{{ site.baseurl }}}}/dickson/matthew/{c}/">'
                         f'第{cn(c)}章<small>英文</small></a></li>')
    out.append('<ul class="dk-chgrid">' + ''.join(cells) + '</ul>')
    n_ch = sum(1 for s in names if s.isdigit())
    out.append(f'<p class="dk-note-zh">中译已上线 {n_ch} / {len(P.NV)} 章；虚线框的章暂只有英文。'
               '原书录入本里读不出的字，中文里同样标红留在明面；底本与缺字说明见'
               '<a href="{{ site.baseurl }}/dickson/matthew/en/">英文版首页</a>。</p>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
