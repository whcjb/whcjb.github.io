#!/usr/bin/env python3
"""perkins_raw/galatians/zh_chapters/*.md → perkins/galatians/zh/*.md（中文版）。

    python3 scripts/publish_perkins_zh.py

与英文版共用 perkins-chapter / perkins-book 两个 layout，靠 `zh: true` 切换。

- 上下篇导航**只在已译的篇之间串**（逐篇推进，指向未译的篇等于送读者去 404）。
- date 取 zh_meta.json 里该篇**实际译完的时刻**；取不到才沿用已发布文件原值，
  再取不到才用当前时间（CLAUDE.md：已有文件的时间不要修改）。
- 每章一页中文目录 zh/<章>.md（「历代解经」与对照抽屉按章号找页面），只列已译的段。
- 书的首页 /perkins/galatians/ 是中文目录，英文目录在 /en/（同约翰斯通）。
- 章顶 verse-nav 的中文版数据 _data/perkins_galatians_zh.json 只含已译的页。
- 跑完回调 publish_perkins_en.py，让英文页补上「中文版 →」。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'perkins_raw' / 'galatians'
ZH_RAW = RAW / 'zh_chapters'
META = RAW / 'zh_meta.json'
PAGES = RAW / 'pages_en.json'
EN = ROOT / 'perkins' / 'galatians'
OUT = EN / 'zh'
BOOK_NAME_ZH = '珀金斯《加拉太书注释》'
FM_DATE = re.compile(r'^date:\s*(.+)$', re.M)

FRONT_LABEL = {
    'dedication': ('献辞', '卡德沃思致里奇勋爵'),
    'reader': ('致读者', '拉尔夫·卡德沃思'),
    'supplement': ('第六章补编', '扉页与献辞（致加迪爵士）'),
    'conclusion': ('结语', '拉尔夫·卡德沃思'),
}
CN = '一二三四五六'


def label(p):
    if 'ch' in p:
        a, b = p['v1'], p['v2']
        return f'加拉太书 {p["ch"]}:{a}' + (f'-{b}' if b != a else '')
    return FRONT_LABEL[p['slug']][0]


def subtitle(p):
    if 'ch' in p:
        return '威廉·珀金斯' if p['ch'] <= 5 else '拉尔夫·卡德沃思（续写）'
    return FRONT_LABEL[p['slug']][1]


# 原书分条「2. …」各自成段——段首「数字 + 点 + 空格」会被 kramdown 当成有序列表、
# 从 1 重新编号（第 2 条显示成 1.）。转义那个点，原样显示（2026-10-19，同雷登）。
RE_OL = re.compile(r'^(\d+)\. ', re.M)


def clean(body: str) -> str:
    # 原文相邻两段斜体 `* *` 在译文里常被并成 `**`：本书没有粗体，`**` 只会是这个，
    # 不合并就渲染成粗体开标记（2026-10-16 试译 1-2 发现）。
    body = re.sub(r'(?<!\*)\*\*(?!\*)', '', body)
    body = re.sub(r'<<<[^>]*>>>', '', body)
    body = RE_OL.sub(r'\1\\. ', body)
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
        fm = ['---', 'layout: perkins-chapter', 'book_id: galatians',
              f'book_name: "{BOOK_NAME_ZH}"', f'title: "{label(p)}"',
              f'subtitle: "{subtitle(p)}"', f'date: {date}']
        if 'ch' in p:
            fm += [f'chapter: {p["ch"]}', f'verse_from: {p["v1"]}', f'verse_to: {p["v2"]}']
        if k > 0:
            q = names[k - 1]
            fm += [f'prev_url: "/perkins/galatians/zh/{q["slug"]}/"', f'prev_label: "{label(q)}"']
        if k + 1 < len(names):
            q = names[k + 1]
            fm += [f'next_url: "/perkins/galatians/zh/{q["slug"]}/"', f'next_label: "{label(q)}"']
        fm += [f'en_url: "/perkins/galatians/{slug}/"', 'zh: true', '---']
        body = clean((ZH_RAW / f'{slug}.md').read_text(encoding='utf-8'))
        path.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    # 每章中文目录页
    nav = {}
    for ch in range(1, 7):
        secs = [p for p in names if p.get('ch') == ch]
        if not secs:
            continue
        for p in secs:
            body = (ZH_RAW / f'{p["slug"]}.md').read_text(encoding='utf-8')
            for v in re.findall(r'id="galatians-\d+-(\d+)"', body):
                nav.setdefault(str(ch), []).append({'v': int(v), 'slug': p['slug']})
        lst = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/perkins/galatians/zh/{p["slug"]}/">'
                        f'{label(p)}</a></li>' for p in secs)
        fm = ['---', 'layout: perkins-chapter', 'book_id: galatians', f'book_name: "{BOOK_NAME_ZH}"',
              f'title: "加拉太书第{CN[ch - 1]}章"', f'subtitle: "{subtitle(secs[0])}"',
              f'date: {meta.get(secs[-1]["slug"], now)}', f'chapter: {ch}',
              f'en_url: "/perkins/galatians/{ch}/"', 'zh: true', '---']
        (OUT / f'{ch}.md').write_text('\n'.join(fm) + f'\n\n<ul class="pk-chtoc">\n{lst}\n</ul>\n',
                                      encoding='utf-8')
    (ROOT / '_data' / 'perkins_galatians_zh.json').write_text(
        json.dumps(nav, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    (EN / 'index.html').write_text(build_index(names, len(pages)), encoding='utf-8')
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'publish_perkins_en.py'), '--apply'],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 英文页回调失败：' + r.stderr[-300:], file=sys.stderr)
    print(f'发布中文 {len(names)}/{len(pages)} 篇 → {OUT}')


def build_index(names, total):
    out = ['---', 'layout: perkins-book', 'book_id: galatians', f'book_name: "{BOOK_NAME_ZH}"',
           'author: "威廉·珀金斯（William Perkins，1558–1602）著 · 第六章与结语由拉尔夫·卡德沃思（Ralph Cudworth）续写"',
           'edition: "《加拉太书前五章注释》· 剑桥 John Legat，1604"',
           f'title: "{BOOK_NAME_ZH}"', 'en_url: "/perkins/galatians/en/"', 'zh: true', '---', '']
    groups = [('卷首', [p for p in names if p['slug'] in ('dedication', 'reader')])]
    for ch in range(1, 7):
        lst = [p for p in names if p.get('ch') == ch]
        if ch == 6:
            lst = [p for p in names if p['slug'] == 'supplement'] + lst + \
                  [p for p in names if p['slug'] == 'conclusion']
        groups.append((f'第{CN[ch - 1]}章' + ('（卡德沃思续写）' if ch == 6 else ''), lst))
    for g, lst in groups:
        if not lst:
            continue
        out.append(f'<h2 class="pk-group">{g}</h2>')
        out.append('<ul class="pk-toc">')
        for p in lst:
            out.append(f'  <li><a href="{{{{ site.baseurl }}}}/perkins/galatians/zh/{p["slug"]}/">{label(p)}</a></li>')
        out.append('</ul>')
    out.append(f'<p class="pk-note">已译 {len(names)} / {total} 篇，逐篇上线。底本：EEBO-TCP A09383'
               '（1604 年剑桥初版人工录入本），缺字与录入错已对照 1604、1607、1617 三版影像校订；'
               '处理过程见 <code>perkins_raw/galatians/PROVENANCE.md</code>。</p>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
