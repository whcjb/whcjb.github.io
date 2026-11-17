#!/usr/bin/env python3
"""bonar_raw/psalms/zh_chapters/<篇>.md → bonar/psalms/zh/<篇>.md（中文版）+ zh/index.html（中文书首页）。

与英文版共用 bonar-chapter / bonar-book 两个 layout，靠 `zh: true` 切换（中文页挂经文引用弹层，layout 里已接）。
上下篇导航只在已译的篇之间串；date 取 zh_meta.json 里该篇实际译完的时刻。
跑完回调 publish_bonar_en.py（英文页挂 zh_url）与 build_commentaries_index.py（历代解经入口有中文就指中文）。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sect_names   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'bonar_raw' / 'psalms'
ZH_RAW = RAW / 'zh_chapters'
EN = ROOT / 'bonar' / 'psalms'
OUT = EN / 'zh'
META = RAW / 'zh_meta.json'
ORDER = ['preface'] + [str(n) for n in range(1, 120)] + ['degrees'] + [str(n) for n in range(120, 151)]
BOOK = '博纳尔《诗篇中的基督与教会》'
ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")


def title(slug):
    return {'preface': '序言', 'degrees': '上行之诗'}.get(slug, f'诗篇第 {slug} 篇')


def short(slug):
    return {'preface': '序言', 'degrees': '上行之诗'}.get(slug, f'第 {slug} 篇')


def fm_value(text, key):
    m = re.search(rf'^{key}: (.*)$', text, re.M)
    return m.group(1).strip() if m else None


def main():
    done = [s for s in ORDER if (ZH_RAW / f'{s}.md').exists()]
    if not done:
        sys.exit('zh_chapters 里没有任何已译的篇')
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)
    for k, s in enumerate(done):
        en = (EN / f'{s}.md').read_text(encoding='utf-8')
        fm = ['---', 'layout: bonar-chapter', 'book_id: psalms', f'book_name: "{BOOK}"',
              f'title: "{title(s)}"', f'date: {meta.get(s, now)}']
        tn = fm_value(en, 'title_note')
        if tn:
            fm.append(f'title_note: {tn}')
        if k > 0:
            fm += [f'prev_url: "/bonar/psalms/zh/{done[k - 1]}/"', f'prev_label: "{short(done[k - 1])}"']
        if k + 1 < len(done):
            fm += [f'next_url: "/bonar/psalms/zh/{done[k + 1]}/"', f'next_label: "{short(done[k + 1])}"']
        fm += [f'en_url: "/bonar/psalms/{s}/"', 'zh: true', '---']
        body = (ZH_RAW / f'{s}.md').read_text(encoding='utf-8').strip()
        body = ORIG_NAME.sub(r'<span class="bn-orig">（\1）</span>', body)
        body = sect_names.annotate(body, en, 'bn-orig')
        (OUT / f'{s}.md').write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    # 中文书首页：目录（已译的指中文，未译的标「英文」指英文页）+ 文本说明（中文段与改动表）
    def cell(s):
        if s in done:
            return f'  <li><a href="{{{{ site.baseurl }}}}/bonar/psalms/zh/{s}/">{short(s)}</a></li>'
        lab = {'preface': 'Preface', 'degrees': 'Songs of Degrees'}.get(s, f'Psalm {s}')
        return f'  <li><a class="bn-other" href="{{{{ site.baseurl }}}}/bonar/psalms/{s}/">{lab}<small>英文</small></a></li>'
    en_idx = (EN / 'index.html').read_text(encoding='utf-8')
    note = re.search(r'<div class="bn-note">(.*?)</div>\s*$', en_idx, re.S).group(1)
    note = re.sub(r'<p><b>About this text\.</b>.*?</p>\n?', '', note, flags=re.S)
    idx = ['---', 'layout: bonar-book', 'book_id: psalms', f'book_name: "{BOOK}"', f'title: "{BOOK}"',
           'author: "安德鲁·博纳尔（Andrew A. Bonar，1810–1892）"',
           'edition: "Christ and His Church in the Book of Psalms · 伦敦 1859"',
           'en_url: "/bonar/psalms/"', 'zh: true', '---', '',
           '<ul class="bn-toc bn-wide">', cell('preface'), '</ul>',
           '<h2 class="bn-group">诗篇 <small>（一百五十篇，上行之诗总论在第 120 篇前）</small></h2>',
           '<ul class="bn-toc">'] + [cell(s) for s in ORDER if s != 'preface'] + ['</ul>',
           f'<div class="bn-note">\n<p>中译已上线 {len(done)} / {len(ORDER)} 篇；未译的篇暂只有英文。</p>\n{note.strip()}\n</div>', '']
    (OUT / 'index.html').write_text('\n'.join(idx), encoding='utf-8')

    for cmd in (['publish_bonar_en.py'], ['build_commentaries_index.py']):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts' / cmd[0])], cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f'{cmd[0]} 失败：{r.stderr[-400:]}')
    print(f'中文 {len(done)} 篇已写出')


if __name__ == '__main__':
    main()
