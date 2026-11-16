#!/usr/bin/env python3
"""foote_raw/luke/zh_chapters/<N>.md → foote/luke/zh/lecture-<N>.md（中文讲次页）+ foote/luke/index.html（中文书首页）。

与英文版共用 foote-chapter / foote-book 两个 layout，靠 `zh: true` 切换（中文页挂经文引用弹层，layout 里已接）。
福特版式的约定：**书首页就是中文目录**，英文目录在 foote/luke/en/（中文讲次页的「←」指书首页、英文页指 en/）；
publish_foote_en 在 zh/ 存在后不再覆盖书首页。中文讲次页不放「English →」（layout 已处理）。
上下讲导航只在已译的讲之间串；date 取 zh_meta.json 里该讲实际译完的时刻。
跑完回调 publish_foote_en.py --apply（英文页挂 zh_url）与 build_commentaries_index.py（历代解经入口指中文）。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sect_names   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'foote_raw' / 'luke'
ZH_RAW = RAW / 'zh_chapters'
EN = ROOT / 'foote' / 'luke'
OUT = EN / 'zh'
META = RAW / 'zh_meta.json'
VOLS = {1: (1, 40), 2: (41, 90), 3: (91, 137)}
CN = '〇一二三四五六七八九'
ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")
BOOK = '福特《路加福音讲义》'


def cn(n):
    if n < 10:
        return CN[n]
    if n < 100:
        t, u = divmod(n, 10)
        return ('' if t == 1 else CN[t]) + '十' + (CN[u] if u else '')
    h, r = divmod(n, 100)
    return CN[h] + '百' + ('' if r == 0 else ('零' + CN[r] if r < 10 else ('一' if r < 20 else '') + cn(r)))


def en_fm(n):
    t = (EN / f'lecture-{n}.md').read_text(encoding='utf-8')
    fm = t.split('\n---\n', 1)[0]
    g = lambda k: (re.search(rf'^{k}: (.*)$', fm, re.M) or [None, ''])[1].strip().strip('"')
    return g('chapter'), g('subtitle').split('· ')[-1]


def ref_zh(ref):
    return ref.replace('Luke ', '路加福音 ')


def curly(seg):
    """标签外的英文直引号按位置换成中文弯引号：段首、空白、开括号、开引号之后为开，其余为收。"""
    out = []
    for i, ch in enumerate(seg):
        if ch == '"':
            prev = seg[i - 1] if i else ' '
            ch = '“' if prev in ' \n（(“‘—*' else '”'
        elif ch == "'" and i and not seg[i - 1].isalpha():
            ch = '‘' if seg[i - 1] in ' \n（(“—*' else '’'
        out.append(ch)
    return ''.join(out)


def quotes(body):
    """全书一种引号（用户 2026-11-16 定 “” ‘’）：「」『』→“”‘’；标签外直引号换弯引号，标签内（属性值）不动。"""
    body = body.replace('「', '“').replace('」', '”').replace('『', '‘').replace('』', '’')
    parts = re.split(r'(<[^<>]+>)', body)
    return ''.join(p if p.startswith('<') else curly(p) for p in parts)


def clean(body):
    # 和合本合节（路 1:1–2、2:34–35、21:29–30）与不收的经文（17:36、23:17）该节为空：节号不显示
    body = re.sub(r'<sup class="ft-vn">[\d:]+</sup>\s*(?=<sup class="ft-vn">|\n)', '', body)
    body = quotes(body)
    body = re.sub(r'(?<!\*)\*\*(?!\*)', '', body)
    body = ORIG_NAME.sub(r'<span class="ft-orig">（\1）</span>', body)
    return body.strip()


def main():
    done = sorted(int(p.stem) for p in ZH_RAW.glob('*.md') if p.stem.isdigit())
    if not done:
        sys.exit('zh_chapters 里没有任何已译的讲')
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)
    for k, n in enumerate(done):
        ch, ref = en_fm(n)
        fm = ['---', 'layout: foote-chapter', 'book_id: luke', f'book_name: "{BOOK}"',
              f'title: "第{cn(n)}讲"', f'subtitle: "詹姆斯·福特 · {ref_zh(ref)}"', f'date: {meta.get(str(n), now)}',
              f'chapter: {ch}', f'lecture: {n}']
        if k > 0:
            fm += [f'prev_url: "/foote/luke/zh/lecture-{done[k - 1]}/"', f'prev_label: "第{cn(done[k - 1])}讲"']
        if k + 1 < len(done):
            fm += [f'next_url: "/foote/luke/zh/lecture-{done[k + 1]}/"', f'next_label: "第{cn(done[k + 1])}讲"']
        fm += [f'en_url: "/foote/luke/lecture-{n}/"', 'zh: true', '---']
        body = clean((ZH_RAW / f'{n}.md').read_text(encoding='utf-8'))
        body = sect_names.annotate(body, (EN / f'lecture-{n}.md').read_text(encoding='utf-8'), 'ft-orig')
        (OUT / f'lecture-{n}.md').write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    idx = ['---', 'layout: foote-book', 'book_id: luke', f'book_name: "{BOOK}"', f'title: "{BOOK}"',
           'author: "詹姆斯·福特（James Foote），阿伯丁自由教会东堂牧师"',
           'edition: "Lectures on the Gospel according to Luke · 第 2 版，三卷，爱丁堡"',
           'en_url: "/foote/luke/en/"', 'zh: true', '---', '']
    for v, (a, b) in VOLS.items():
        idx += [f'<h2 class="ft-group">卷{cn(v)} · 第{cn(a)}讲至第{cn(b)}讲</h2>', '<ul class="ft-toc ft-toc-sm">']
        for n in range(a, b + 1):
            _, ref = en_fm(n)
            if n in done:
                idx.append(f'  <li><a href="{{{{ site.baseurl }}}}/foote/luke/zh/lecture-{n}/">第{cn(n)}讲'
                           f'<small>{ref_zh(ref)}</small></a></li>')
            else:
                idx.append(f'  <li><a class="ft-other" href="{{{{ site.baseurl }}}}/foote/luke/lecture-{n}/">Lecture {n}'
                           f'<small>{ref}（英文）</small></a></li>')
        idx.append('</ul>')
    idx += ['', f'<p class="ft-note-zh">中译已上线 {len(done)} / 137 讲；未译的讲暂只有英文。'
            '底本说明（所据版本、校勘经过、原书印刷错字一览）见'
            '<a href="{{ site.baseurl }}/foote/luke/en/">英文版书首页</a>。</p>', '']
    (EN / 'index.html').write_text('\n'.join(idx), encoding='utf-8')
    for cmd in (['publish_foote_en.py', '--apply'], ['build_commentaries_index.py']):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts' / cmd[0]), *cmd[1:]], cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            print(f'⚠️ {cmd[0]} 失败：' + r.stderr[-300:], file=sys.stderr)
    print(f'发布中文 {len(done)}/137 讲 → {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
