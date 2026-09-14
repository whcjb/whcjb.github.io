#!/usr/bin/env python3
"""alexander_raw/psalms/zh_chapters/*.md → alexander/psalms/zh/*.md（中文版）。

    python3 scripts/publish_alexander_psalms_zh.py          # 发布全部已翻译的
    python3 scripts/publish_alexander_psalms_zh.py 1 3      # 只发布指定篇

与英文版共用 alexander-chapter / alexander-book 两个 layout，靠 `zh: true`
切换（贺智那边的既定写法）。不另起一套 layout：同一本书的样式本来就该一致，
「每本书独立样式」说的是**不与别家共用**，不是中英文各造一份。

上下篇导航**只在已翻译的篇之间串**：翻译逐篇推进，把导航指到还没译的篇
等于送读者去 404。每次重跑本脚本会按当前已译清单重新串一遍。

页面 date 取 `zh_meta.json` 里**该篇实际译完的时刻**，不是发布这一刻——
一次发布把六篇的时间戳写成同一分钟，等于没有信息（用户 2026-09-14 指出）。
取不到才退回已发布文件的原值，再取不到才用当前时间（CLAUDE.md：已有文件的
时间不要修改）。

顺带回填英文页的 `zh_url`，好让英文页右上角出现「中文版 →」。
publish_alexander_en.py 重跑时也会按 zh 目录的存在与否自己补上，两边幂等。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'alexander_raw/psalms/zh_chapters'
META = ROOT / 'alexander_raw/psalms/zh_meta.json'
OUT = ROOT / 'alexander/psalms/zh'
EN = ROOT / 'alexander/psalms'

BOOK_NAME_ZH = '亚历山大《诗篇注释》'
FM_DATE = re.compile(r'^date:\s*(.+)$', re.M)


def label(sec: str) -> str:
    return '著者序' if sec == 'preface' else f'诗篇 第 {sec} 篇'


def sequence():
    """全书顺序：序 + 1..150。"""
    return ['preface'] + [str(i) for i in range(1, 151)]


def existing_date(path: Path):
    if not path.exists():
        return None
    m = FM_DATE.search(path.read_text(encoding='utf-8')[:400])
    return m.group(1).strip() if m else None


def backfill_zh_url(sec: str):
    """英文页 front matter 里补 `zh_url`（已有则不动）。"""
    p = EN / f'{sec}.md'
    if not p.exists():
        return False
    t = p.read_text(encoding='utf-8')
    if 'zh_url:' in t.split('\n---\n', 1)[0]:
        return False
    head, body = t.split('\n---\n', 1)
    p.write_text(f'{head}\nzh_url: "/alexander/psalms/zh/{sec}/"\n---\n{body}',
                 encoding='utf-8')
    return True


def main(only=None):
    if not RAW.exists():
        sys.exit(f'找不到 {RAW}，先跑 translate_alexander_psalms.py')
    done = {p.stem for p in RAW.glob('*.md')}
    names = [s for s in sequence() if s in done]
    if not names:
        sys.exit('zh_chapters 里没有任何已翻译的篇')

    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True,
                         text=True, check=True).stdout.strip()
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True)

    written = kept = filled = 0
    for k, sec in enumerate(names):
        if only and sec not in only:
            continue
        body = (RAW / f'{sec}.md').read_text(encoding='utf-8').strip()
        path = OUT / f'{sec}.md'
        # 译完时刻优先；没记到才沿用已发布的原值
        date = meta.get(sec) or existing_date(path)
        kept += date is not None
        fm = ['---', 'layout: alexander-chapter', 'book_id: psalms',
              f'book_name: "{BOOK_NAME_ZH}"']
        if sec.isdigit():
            fm.append(f'chapter: {sec}')
        fm += [f'title: "{label(sec)}"', f'date: {date or now}']
        if k > 0:
            fm += [f'prev_section: {names[k - 1]}',
                   f'prev_label: "{label(names[k - 1])}"']
        if k + 1 < len(names):
            fm += [f'next_section: {names[k + 1]}',
                   f'next_label: "{label(names[k + 1])}"']
        fm += [f'en_url: "/alexander/psalms/{sec}/"', 'zh: true', '---']
        path.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')
        written += 1
        filled += backfill_zh_url(sec)

    (OUT / 'index.html').write_text(
        '---\n'
        'layout: alexander-book\n'
        'book_id: psalms\n'
        f'book_name: "{BOOK_NAME_ZH}"\n'
        'chapters: 150\n'
        'zh: true\n'
        '---\n', encoding='utf-8')

    print(f'发布中文 {written} 篇（已译共 {len(names)}），date 取自译完时刻 {kept} 篇，'
          f'回填英文页 zh_url {filled} 处 → {OUT}')


if __name__ == '__main__':
    main(set(sys.argv[1:]) or None)
