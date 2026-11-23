#!/usr/bin/env python3
"""达拉谟《雅歌之钥》中文版发布：durham_raw/song/zh_chapters/<页>.md → durham/songofsolomon/zh/<页>.md。

- 中文页 front matter：layout durham-chapter、zh: true、en_url；date 取 zh_meta.json（该页译完的时刻，
  不是发布时刻）；上一页／下一页只连已译的页，免得点进 404。
- 中文目录 zh/index.html：照英文目录的卷首入口（front_extra）配置，标 zh: true。
- 英文页回填 zh_url（durham-chapter 据此显示「中文版 →」）。
  注意 publish_durham_en.py --no-zh 重出英文页会冲掉它，重出后再跑一次本脚本。
- 收尾：锚点、经文索引、「历代解经」总目。

用法：python3 scripts/publish_durham_song_zh.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize_zh_quotes import normalize_text   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BOOK = 'songofsolomon'
EN = ROOT / 'durham' / BOOK
ZH = EN / 'zh'
RAW = ROOT / 'durham_raw' / 'song'
ORDER = ['preface', 'key', 'conclusions'] + [str(n) for n in range(1, 9)]
LABEL = {'preface': '书名页与序', 'key': '雅歌之钥（总论）', 'conclusions': '结论',
         **{str(n): f'雅歌第 {n} 章' for n in range(1, 9)}}


def main():
    meta = json.loads((RAW / 'zh_meta.json').read_text(encoding='utf-8'))
    done = [s for s in ORDER if (RAW / 'zh_chapters' / f'{s}.md').exists()]
    if not done:
        print('还没有译好的页'); return 0
    ZH.mkdir(parents=True, exist_ok=True)
    for k, s in enumerate(done):
        body = (RAW / 'zh_chapters' / f'{s}.md').read_text(encoding='utf-8')
        # 段首「2. …」是原书分条序号：kramdown 会排成 <ol> 并从 1 重新编号，转义成 `2\.`
        body = re.sub(r'^((?:<!-- PAGE \d+ --> )?\d+)\. ', r'\1\\. ', body, flags=re.M)
        fm = ['---', 'layout: durham-chapter', f'book_id: {BOOK}', 'book_name: "达拉谟《雅歌之钥》"',
              f'title: "{LABEL[s]}"', f'date: {meta[s]}']
        i = ORDER.index(s)
        if i > 0 and ORDER[i - 1] in done:
            fm += [f'prev_section: {ORDER[i - 1]}', f'prev_label: "{LABEL[ORDER[i - 1]]}"']
        if i + 1 < len(ORDER) and ORDER[i + 1] in done:
            fm += [f'next_section: {ORDER[i + 1]}', f'next_label: "{LABEL[ORDER[i + 1]]}"']
        fm += [f'en_url: "/durham/{BOOK}/{s}/"', 'zh: true', '---']
        page, n_q, n_h, warn = normalize_text('\n'.join(fm) + '\n\n' + body)
        if warn:
            print(f'  ⚠ {s} 标点归一跳过：{warn}')
        (ZH / f'{s}.md').write_text(page, encoding='utf-8')

        # 英文页回填 zh_url
        ep = EN / f'{s}.md'
        t = ep.read_text(encoding='utf-8')
        if 'zh_url:' not in t.split('\n---', 1)[0]:
            t = re.sub(r'^(title: .*)$', rf'\1\nzh_url: "/durham/{BOOK}/zh/{s}/"', t, count=1, flags=re.M)
            ep.write_text(t, encoding='utf-8')

    # 中文目录：卷首配置照英文目录
    en_idx = (EN / 'index.html').read_text(encoding='utf-8')
    extra = en_idx.split('---', 2)[1]
    keep = '\n'.join(l for l in extra.strip().split('\n')
                     if not l.startswith(('layout:', 'book_name:')))
    (ZH / 'index.html').write_text(
        '---\nlayout: durham-book\nbook_name: "雅歌之钥"\n' + keep + '\nzh: true\n---\n', encoding='utf-8')
    print(f'✓ 中文 {len(done)} 页：{", ".join(done)}')

    for cmd in (['scripts/add_durham_verse_anchors.py', '--book', BOOK],
                ['scripts/build_hodge_verse_index.py', '--book', BOOK],
                ['scripts/build_commentaries_index.py']):
        r = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            print(f'⛔ {cmd[0]} 失败：{r.stderr[-400:]}', file=sys.stderr)
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
