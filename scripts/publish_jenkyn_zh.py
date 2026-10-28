#!/usr/bin/env python3
"""jenkyn_raw/jude/zh_chapters/*.md → jenkyn/jude/zh/*.md（中文版）。

    python3 scripts/publish_jenkyn_zh.py

骨架照搬 publish_adams_zh.py。与英文版共用 jenkyn-chapter / jenkyn-book 两个 layout，
靠 `zh: true` 切换（中文页才挂经文引用弹层）。

- 上下篇导航**只在已译的篇之间串**（指向未译的篇等于送读者去 404）。
- date 取 zh_meta.json 里该篇**实际译完的时刻**；取不到才沿用已发布文件原值，再取不到才用当前时间。
- 犹大书只一章：有已译的正文页才出中文章目录 zh/1.md。
- 书的首页 /jenkyn/jude/ 换成中文目录，英文目录在 /en/。
- 跑完回调 publish_jenkyn_en.py --apply，让英文页补上「中文版 →」；再重建「历代解经」数据。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'jenkyn_raw' / 'jude'
ZH_RAW = RAW / 'zh_chapters'
META = RAW / 'zh_meta.json'
PAGES = RAW / 'pages_en.json'
EN = ROOT / 'jenkyn' / 'jude'
OUT = EN / 'zh'
BOOK_NAME_ZH = '詹金《犹大书讲解》'
AUTHOR_ZH = '威廉·詹金'
AUTHOR_EN = 'William Jenkyn'   # 页面副标题一律写英文原名（用户 2026-10-16 定）
FM_DATE = re.compile(r'^date:\s*(.+)$', re.M)

FRONT_LABEL = {
    'title1': ('书名页（第一部分）', '伦敦，1652'),
    'to-the-reader': ('致读者', '致伦敦基督堂（Christ-Church）堂区众信徒'),
    'errata1': ('勘误表（第一部分）', AUTHOR_EN),
    'advertisement': ('书商告读者', AUTHOR_EN),
    'title2': ('书名页（第二部分）', '伦敦，1654'),
    'dedication': ('献辞（第二部分）', '致伦敦黑衣修士区（Black-Friars）的神的教会'),
    'errata2': ('勘误表（第二部分）', AUTHOR_EN),
}
RE_PART = re.compile(r'\(part (\d+) of (\d+)\)')


def label(p):
    if 'ch' in p:
        a, b = p['v1'], p['v2']
        s = f'犹大书 {a}' + (f'-{b}' if b != a else '') + ' 节'
        if p.get('src') == '8-ii':
            s += '（第二部分）'
        m = RE_PART.search(p['title'])
        return s + (f'（第 {m.group(1)}/{m.group(2)} 段）' if m else '')
    return FRONT_LABEL[p['slug']][0]


def subtitle(p):
    return AUTHOR_EN if 'ch' in p else FRONT_LABEL[p['slug']][1]


# 原书分条「2. …」各自成段——段首「数字 + 点 + 空格」会被 kramdown 当成有序列表、
# 从 1 重新编号（第 2 条显示成 1.）。转义那个点，原样显示。
RE_OL = re.compile(r'^(\d+)\. ', re.M)
# 音译专名后的原名括注「（Augustine）」→ 小一号灰字方括号（样式在 layout 的 .jk-orig）。
# 只认括号里全是西文字母的；夹了中文的、拉丁词释义都不动。zh_chapters 里仍存圆括号。
ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")


def clean(body: str) -> str:
    # 相邻两段斜体在译文里常被并成 `**`：本书没有粗体，只合并孤立的 `**`
    body = re.sub(r'(?<!\*)\*\*(?!\*)', '', body)
    body = re.sub(r'<<<[^>]*>>>', '', body)
    body = RE_OL.sub(r'\1\\. ', body)
    # 章题照原书斜体搬来——中文书名里斜体不成样子，标题行去掉星号
    body = re.sub(r'^(#+ .*)$', lambda m: m.group(1).replace('*', ''), body, flags=re.M)
    body = ORIG_NAME.sub(r'<span class="jk-orig">[\1]</span>', body)
    # 首字下沉：模型把英文首字母连同外壳里的字一起丢了，留下空壳——把中文第一个字挪进去
    body = re.sub(r'<span class="jk-dropcap"></span>([^\s<*])', r'<span class="jk-dropcap">\1</span>', body)
    # 扉页英文几行（AN / EXPOSITION / Of the Epistle of）在中文里并成一行，剩下的空行去掉
    body = re.sub(r'<div class="jk-tp-l[^"]*"></div>\n', '', body)
    # 扉页是 HTML 块，kramdown 不解析里面的 *斜体*：换回 <i>
    body = re.sub(r'(<div class="jk-tp-l[^"]*">)(.*?)(</div>)',
                  lambda m: m.group(1) + re.sub(r'\*([^*]+)\*', r'<i>\1</i>', m.group(2)) + m.group(3), body)
    body = re.sub(r'(<p>)(.*?)(</p>)',
                  lambda m: m.group(1) + re.sub(r'\*([^*]+)\*', r'<i>\1</i>', m.group(2)) + m.group(3), body)
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
        fm = ['---', 'layout: jenkyn-chapter', 'book_id: jude',
              f'book_name: "{BOOK_NAME_ZH}"', f'title: "{label(p)}"',
              f'subtitle: "{subtitle(p)}"', f'date: {date}']
        if 'ch' in p:
            fm += [f'chapter: {p["ch"]}', f'verse_from: {p["v1"]}', f'verse_to: {p["v2"]}']
        if k > 0:
            q = names[k - 1]
            fm += [f'prev_url: "/jenkyn/jude/zh/{q["slug"]}/"', f'prev_label: "{label(q)}"']
        if k + 1 < len(names):
            q = names[k + 1]
            fm += [f'next_url: "/jenkyn/jude/zh/{q["slug"]}/"', f'next_label: "{label(q)}"']
        fm += [f'en_url: "/jenkyn/jude/{slug}/"', 'zh: true', '---']
        body = clean((ZH_RAW / f'{slug}.md').read_text(encoding='utf-8'))
        path.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    # 章目录页 + 章内导航数据（只列已译的正文页）
    nav = {}
    secs = [p for p in names if 'ch' in p]
    if secs:
        for p in secs:
            if p.get('cont') or p.get('src') == '8-ii':
                continue
            for v in range(p['v1'], p['v2'] + 1):
                nav.setdefault('1', []).append({'v': v, 'slug': p['slug']})
        lst = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/jenkyn/jude/zh/{p["slug"]}/">'
                        f'{label(p)}</a></li>' for p in secs)
        fm = ['---', 'layout: jenkyn-chapter', 'book_id: jude', f'book_name: "{BOOK_NAME_ZH}"',
              'title: "犹大书"', f'subtitle: "{AUTHOR_EN}"',
              f'date: {meta.get(secs[-1]["slug"], now)}', 'chapter: 1',
              'en_url: "/jenkyn/jude/1/"', 'zh: true', '---']
        (OUT / '1.md').write_text('\n'.join(fm) + f'\n\n<ul class="jk-chtoc">\n{lst}\n</ul>\n',
                                  encoding='utf-8')
    (ROOT / '_data' / 'jenkyn_jude_zh.json').write_text(
        json.dumps(nav, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    (EN / 'index.html').write_text(build_index(names, pages), encoding='utf-8')
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'publish_jenkyn_en.py'), '--apply'],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 英文页回调失败：' + r.stderr[-300:], file=sys.stderr)
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_commentaries_index.py')],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 历代解经数据重建失败：' + r.stderr[-300:], file=sys.stderr)
    print(f'发布中文 {len(names)}/{len(pages)} 篇 → {OUT}')


def build_index(names, pages):
    out = ['---', 'layout: jenkyn-book', 'book_id: jude', f'book_name: "{BOOK_NAME_ZH}"',
           f'author: "{AUTHOR_ZH}（William Jenkyn，1613–1685）"',
           'edition: "An Exposition of the Epistle of Jude · 伦敦，第一部分 1652，第二部分 1654"',
           f'title: "{BOOK_NAME_ZH}"', 'en_url: "/jenkyn/jude/en/"', 'zh: true', '---', '']

    def group(name, pred):
        lst = [p for p in names if pred(p)]
        if lst:
            out.append(f'<h2 class="jk-group">{name}</h2>')
            out.append('<ul class="jk-toc">')
            out.extend(f'  <li><a href="{{{{ site.baseurl }}}}/jenkyn/jude/zh/{p["slug"]}/">{label(p)}</a></li>'
                       for p in lst)
            out.append('</ul>')

    group('第一部分（1652）卷首', lambda p: p['group'] == 'front1')
    group('第一部分：第 1–8 节', lambda p: p.get('part') == 1 and not p.get('cont'))
    group('第二部分（1654）卷首', lambda p: p['group'] == 'front2')
    group('第二部分：第 8–25 节', lambda p: p.get('part') == 2 and not p.get('cont'))
    group('勘误', lambda p: p['group'] == 'tail')
    out.append(f'<p class="jk-note-zh">中译已上线 {len(names)} / {len(pages)} 篇，逐篇推进；未译的篇见'
               '<a href="{{ site.baseurl }}/jenkyn/jude/en/">英文版</a>。</p>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
