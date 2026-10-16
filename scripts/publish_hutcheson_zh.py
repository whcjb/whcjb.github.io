#!/usr/bin/env python3
"""hutcheson_raw/john/zh_chapters/*.md → hutcheson/john/zh/*.md（中文版）。

    python3 scripts/publish_hutcheson_zh.py

骨架照搬 publish_perkins_zh.py。与英文版共用 hutcheson-chapter / hutcheson-book 两个 layout，
靠 `zh: true` 切换（中文页才挂经文引用弹层）。

- 上下篇导航**只在已译的篇之间串**（指向未译的篇等于送读者去 404）。
- date 取 zh_meta.json 里该篇**实际译完的时刻**；取不到才沿用已发布文件原值，再取不到才用当前时间。
- 每章一页中文目录 zh/<章>.md（「历代解经」与对照抽屉按章号找页面），只列已译的段。
- 书的首页 /hutcheson/john/ 换成中文目录，英文目录在 /en/。**首页必须带上文本说明与
  「最后 29 个缺字记号逐条说明」表**——表由 publish_hutcheson_en.conj_table 从判读表生成，
  中英两个首页共用同一个函数，说法不会不一致。
- 章顶 verse-nav 的中文版数据 _data/hutcheson_john_zh.json 只含已译的页。
- 跑完回调 publish_hutcheson_en.py，让英文页补上「中文版 →」。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_hutcheson_en as pe  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'hutcheson_raw' / 'john'
ZH_RAW = RAW / 'zh_chapters'
META = RAW / 'zh_meta.json'
PAGES = RAW / 'pages_en.json'
EN = ROOT / 'hutcheson' / 'john'
OUT = EN / 'zh'
BOOK_NAME_ZH = '赫奇森《约翰福音注释》'
AUTHOR_ZH = '乔治·赫奇森'
AUTHOR_EN = 'George Hutcheson'   # 页面副标题一律写英文原名（用户 2026-10-16 定）
FM_DATE = re.compile(r'^date:\s*(.+)$', re.M)

FRONT_LABEL = {
    'title': ('书名页', '伦敦，1657'),
    'calamy': ('致基督徒读者', 'Edmund Calamy'),
    'dedication': ('献辞', '致韦姆斯与巴克卢两位伯爵夫人'),
    'reader': ('致读者', AUTHOR_EN),
    'argument': ('论旨', AUTHOR_EN),
    'errata': ('勘误表', AUTHOR_EN),
}


def label(p):
    if 'ch' in p:
        a, b = p['v1'], p['v2']
        return f'约翰福音 {p["ch"]}:{a}' + (f'-{b}' if b != a else '')
    return FRONT_LABEL[p['slug']][0]


def subtitle(p):
    return AUTHOR_EN if 'ch' in p else FRONT_LABEL[p['slug']][1]


def clean(body: str) -> str:
    # 相邻两段斜体在译文里常被并成 `**`；本书的 `**N**` 是节号粗体，只合并「孤立的」`**`
    body = re.sub(r'(?<![*\d])\*\*(?![*\d])', '', body)
    body = re.sub(r'<<<[^>]*>>>', '', body)
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
        fm = ['---', 'layout: hutcheson-chapter', 'book_id: john',
              f'book_name: "{BOOK_NAME_ZH}"', f'title: "{label(p)}"',
              f'subtitle: "{subtitle(p)}"', f'date: {date}']
        if 'ch' in p:
            fm += [f'chapter: {p["ch"]}', f'verse_from: {p["v1"]}', f'verse_to: {p["v2"]}']
        if k > 0:
            q = names[k - 1]
            fm += [f'prev_url: "/hutcheson/john/zh/{q["slug"]}/"', f'prev_label: "{label(q)}"']
        if k + 1 < len(names):
            q = names[k + 1]
            fm += [f'next_url: "/hutcheson/john/zh/{q["slug"]}/"', f'next_label: "{label(q)}"']
        fm += [f'en_url: "/hutcheson/john/{slug}/"', 'zh: true', '---']
        body = clean((ZH_RAW / f'{slug}.md').read_text(encoding='utf-8'))
        path.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    # 每章中文目录页 + 章顶 verse-nav 数据
    nav = {}
    for ch in range(1, 22):
        secs = [p for p in names if p.get('ch') == ch]
        if not secs:
            continue
        for p in secs:
            body = (ZH_RAW / f'{p["slug"]}.md').read_text(encoding='utf-8')
            for v in re.findall(r'id="john-\d+-(\d+)"', body):
                nav.setdefault(str(ch), []).append({'v': int(v), 'slug': p['slug']})
        lst = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/hutcheson/john/zh/{p["slug"]}/">'
                        f'{label(p)}</a></li>' for p in secs)
        fm = ['---', 'layout: hutcheson-chapter', 'book_id: john', f'book_name: "{BOOK_NAME_ZH}"',
              f'title: "约翰福音第 {ch} 章"', f'subtitle: "{AUTHOR_EN}"',
              f'date: {meta.get(secs[-1]["slug"], now)}', f'chapter: {ch}',
              f'en_url: "/hutcheson/john/{ch}/"', 'zh: true', '---']
        (OUT / f'{ch}.md').write_text('\n'.join(fm) + f'\n\n<ul class="hc-chtoc">\n{lst}\n</ul>\n',
                                      encoding='utf-8')
    (ROOT / '_data' / 'hutcheson_john_zh.json').write_text(
        json.dumps(nav, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    (EN / 'index.html').write_text(build_index(names, pages), encoding='utf-8')
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'publish_hutcheson_en.py'), '--apply'],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 英文页回调失败：' + r.stderr[-300:], file=sys.stderr)
    # 对照抽屉里中文版的章范围（ch_to）随已译章数增长：每次发布都重建「历代解经」数据
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_commentaries_index.py')],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 历代解经数据重建失败：' + r.stderr[-300:], file=sys.stderr)
    print(f'发布中文 {len(names)}/{len(pages)} 篇 → {OUT}')


def build_index(names, pages):
    out = ['---', 'layout: hutcheson-book', 'book_id: john', f'book_name: "{BOOK_NAME_ZH}"',
           f'author: "{AUTHOR_ZH}（George Hutcheson，1615–1674）· 爱丁堡福音牧师"',
           'edition: "An Exposition of the Gospel of Jesus Christ according to John · 伦敦 Ralph Smith，1657"',
           f'title: "{BOOK_NAME_ZH}"', 'en_url: "/hutcheson/john/en/"', 'zh: true', '---', '']
    front = [p for p in names if p['slug'] in ('title', 'calamy', 'dedication', 'reader', 'argument')]
    if front:
        out.append('<h2 class="hc-group">卷首</h2>')
        out.append('<ul class="hc-toc">')
        out += [f'  <li><a href="{{{{ site.baseurl }}}}/hutcheson/john/zh/{p["slug"]}/">{label(p)}</a></li>'
                for p in front]
        out.append('</ul>')
    chs = sorted({p['ch'] for p in names if 'ch' in p})
    if chs:
        out.append('<h2 class="hc-group">逐章释义</h2>')
        out.append('<ul class="hc-chgrid">')
        out += [f'  <li><a href="{{{{ site.baseurl }}}}/hutcheson/john/zh/{ch}/">第 {ch} 章</a></li>' for ch in chs]
        out.append('</ul>')
    tail = [p for p in names if p['slug'] == 'errata']
    if tail:
        out.append('<h2 class="hc-group">书末</h2>')
        out.append('<ul class="hc-toc">')
        out += [f'  <li><a href="{{{{ site.baseurl }}}}/hutcheson/john/zh/{p["slug"]}/">{label(p)}</a></li>'
                for p in tail]
        out.append('</ul>')
    out.append(f'<p class="hc-note-zh">中译已上线 {len(names)} / {len(pages)} 篇，逐篇推进；未译的篇见'
               '<a href="{{ site.baseurl }}/hutcheson/john/en/">英文版</a>。</p>')
    # 文本说明 + 逐条说明表：与英文首页同一来源
    en_index = pe.build_index(pages)
    i = en_index.index('<div class="hc-note">')
    out.append(en_index[i:].rstrip())
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
