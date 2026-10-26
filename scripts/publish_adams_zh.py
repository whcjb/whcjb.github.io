#!/usr/bin/env python3
"""adams_raw/2peter/zh_chapters/*.md → adams/2peter/zh/*.md（中文版）。

    python3 scripts/publish_adams_zh.py

骨架照搬 publish_leighton_zh.py。与英文版共用 adams-chapter / adams-book 两个 layout，
靠 `zh: true` 切换（中文页才挂经文引用弹层）。

- 上下篇导航**只在已译的篇之间串**（指向未译的篇等于送读者去 404）。
- date 取 zh_meta.json 里该篇**实际译完的时刻**；取不到才沿用已发布文件原值，再取不到才用当前时间。
- 每章一页中文目录 zh/<章>.md，只列已译的段。
- 书的首页 /adams/2peter/ 换成中文目录，英文目录在 /en/。
- 跑完回调 publish_adams_en.py，让英文页补上「中文版 →」；再重建「历代解经」数据。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'adams_raw' / '2peter'
ZH_RAW = RAW / 'zh_chapters'
META = RAW / 'zh_meta.json'
PAGES = RAW / 'pages_en.json'
EN = ROOT / 'adams' / '2peter'
OUT = EN / 'zh'
BOOK_NAME_ZH = '亚当斯《彼得后书注释》'
AUTHOR_ZH = '托马斯·亚当斯'
AUTHOR_EN = 'Thomas Adams'   # 页面副标题一律写英文原名（用户 2026-10-16 定）
FM_DATE = re.compile(r'^date:\s*(.+)$', re.M)

FRONT_LABEL = {
    'title1': ('书名页（卷一）', '伦敦，1633'),
    'dedication': ('献辞', '致亨利·马滕爵士（Sir Henry Marten）'),
    'title2': ('书名页（卷二）', '伦敦，1633'),
    'alphabetical-index': ('要目索引', '按字母排列的要点索引'),
    'errata': ('勘误表', AUTHOR_EN),
}
RE_PART = re.compile(r'\(part (\d+) of (\d+)\)')


def label(p):
    if 'ch' in p:
        a, b = p['v1'], p['v2']
        s = f'彼得后书 {p["ch"]}:{a}' + (f'-{b}' if b != a else '')
        m = RE_PART.search(p['title'])
        return s + (f'（第 {m.group(1)}/{m.group(2)} 部分）' if m else '')
    return FRONT_LABEL[p['slug']][0]


def subtitle(p):
    return AUTHOR_EN if 'ch' in p else FRONT_LABEL[p['slug']][1]


# 原书分条「2. …」各自成段——段首「数字 + 点 + 空格」会被 kramdown 当成有序列表、
# 从 1 重新编号（第 2 条显示成 1.）。转义那个点，原样显示。
RE_OL = re.compile(r'^(\d+)\. ', re.M)
# 音译专名后的原名括注「（Augustine）」→ 小一号灰字方括号（样式在 layout 的 .ad-orig）。
# 只认括号里全是西文字母的；夹了中文的、拉丁词释义都不动。zh_chapters 里仍存圆括号。
ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")


def clean(body: str) -> str:
    # 相邻两段斜体在译文里常被并成 `**`：本书没有粗体，只合并孤立的 `**`
    body = re.sub(r'(?<!\*)\*\*(?!\*)', '', body)
    body = re.sub(r'<<<[^>]*>>>', '', body)
    body = RE_OL.sub(r'\1\\. ', body)
    # 章题照原书斜体搬来——中文书名里斜体不成样子，标题行去掉星号
    body = re.sub(r'^(#+ .*)$', lambda m: m.group(1).replace('*', ''), body, flags=re.M)
    body = ORIG_NAME.sub(r'<span class="ad-orig">[\1]</span>', body)
    return body.strip()


def existing_date(path: Path):
    if not path.exists():
        return None
    m = FM_DATE.search(path.read_text(encoding='utf-8')[:800])
    return m.group(1).strip() if m else None


def main():
    pages = json.loads(PAGES.read_text(encoding='utf-8'))
    done = {p.stem for p in ZH_RAW.glob('*.md')}
    names = [p for p in pages if p['slug'] in done]
    if not names:
        sys.exit('zh_chapters 里没有任何已译的篇')
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True,
                         check=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)

    for k, p in enumerate(names):
        slug = p['slug']
        path = OUT / f'{slug}.md'
        date = meta.get(slug) or existing_date(path) or now
        fm = ['---', 'layout: adams-chapter', 'book_id: 2peter',
              f'book_name: "{BOOK_NAME_ZH}"', f'title: "{label(p)}"',
              f'subtitle: "{subtitle(p)}"', f'date: {date}']
        if 'ch' in p:
            fm += [f'chapter: {p["ch"]}', f'verse_from: {p["v1"]}', f'verse_to: {p["v2"]}']
        if k > 0:
            q = names[k - 1]
            fm += [f'prev_url: "/adams/2peter/zh/{q["slug"]}/"', f'prev_label: "{label(q)}"']
        if k + 1 < len(names):
            q = names[k + 1]
            fm += [f'next_url: "/adams/2peter/zh/{q["slug"]}/"', f'next_label: "{label(q)}"']
        fm += [f'en_url: "/adams/2peter/{slug}/"', 'zh: true', '---']
        body = clean((ZH_RAW / f'{slug}.md').read_text(encoding='utf-8'))
        path.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    # 每章中文目录页 + 章内导航数据
    nav = {}
    for ch in range(1, 4):
        secs = [p for p in names if p.get('ch') == ch]
        if not secs:
            continue
        for p in secs:
            body = (ZH_RAW / f'{p["slug"]}.md').read_text(encoding='utf-8')
            for v in re.findall(r'id="2peter-\d+-(\d+)"', body):
                nav.setdefault(str(ch), []).append({'v': int(v), 'slug': p['slug']})
        lst = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/adams/2peter/zh/{p["slug"]}/">'
                        f'{label(p)}</a></li>' for p in secs)
        fm = ['---', 'layout: adams-chapter', 'book_id: 2peter', f'book_name: "{BOOK_NAME_ZH}"',
              f'title: "彼得后书第 {ch} 章"', f'subtitle: "{AUTHOR_EN}"',
              f'date: {meta.get(secs[-1]["slug"], now)}', f'chapter: {ch}',
              f'en_url: "/adams/2peter/{ch}/"', 'zh: true', '---']
        (OUT / f'{ch}.md').write_text('\n'.join(fm) + f'\n\n<ul class="ad-chtoc">\n{lst}\n</ul>\n',
                                      encoding='utf-8')
    (ROOT / '_data' / 'adams_2peter_zh.json').write_text(
        json.dumps(nav, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    (EN / 'index.html').write_text(build_index(names, pages), encoding='utf-8')
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'publish_adams_en.py'), '--apply'],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 英文页回调失败：' + r.stderr[-300:], file=sys.stderr)
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_commentaries_index.py')],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 历代解经数据重建失败：' + r.stderr[-300:], file=sys.stderr)
    print(f'发布中文 {len(names)}/{len(pages)} 篇 → {OUT}')


def build_index(names, pages):
    out = ['---', 'layout: adams-book', 'book_id: 2peter', f'book_name: "{BOOK_NAME_ZH}"',
           f'author: "{AUTHOR_ZH}（Thomas Adams，约 1583–1652）"',
           'edition: "A Commentary or, Exposition vpon the Diuine Second Epistle Generall · 伦敦 1633，两卷对开本"',
           f'title: "{BOOK_NAME_ZH}"', 'en_url: "/adams/2peter/en/"', 'zh: true', '---', '']

    def group(name, pred):
        lst = [p for p in names if pred(p)]
        if lst:
            out.append(f'<h2 class="ad-group">{name}</h2>')
            out.append('<ul class="ad-toc">')
            out.extend(f'  <li><a href="{{{{ site.baseurl }}}}/adams/2peter/zh/{p["slug"]}/">{label(p)}</a></li>'
                       for p in lst)
            out.append('</ul>')

    group('卷首', lambda p: p['group'] == 'front')
    chs = sorted({p['ch'] for p in names if 'ch' in p})
    if chs:
        out.append('<h2 class="ad-group">各章</h2>')
        out.append('<ul class="ad-chgrid">' + ''.join(
            f'<li><a href="{{{{ site.baseurl }}}}/adams/2peter/zh/{ch}/">第 {ch} 章</a></li>' for ch in chs)
            + '</ul>')
    group('卷二', lambda p: p['group'] == 'vol2')
    group('索引与勘误', lambda p: p['group'] == 'tail')
    out.append(f'<p class="ad-note-zh">中译已上线 {len(names)} / {len(pages)} 篇，逐篇推进；未译的篇见'
               '<a href="{{ site.baseurl }}/adams/2peter/en/">英文版</a>。</p>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
