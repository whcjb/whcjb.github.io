#!/usr/bin/env python3
"""亚历山大《使徒行传释义》中文版发布：alexander_raw/acts/zh_chapters/<N>.md → alexander/acts/zh/<N>.md

zh_chapters 由 scripts/translate_alexander_acts.py 生成（斜体是 *…*，经文头已是和合本）。本脚本只管：
  - *…* 转回 <em>（页面是 HTML 段落，kramdown 不处理块内 markdown）；
  - 前言：date 取 zh_meta.json（每章真正译完的时刻）；上一章 / 下一章只链已有中文页的；
    中文书首页还没有，返回链接指英文书首页；
  - 回头给英文章节页补 zh_url（重跑 publish_alexander_acts_en.py，它见到中文页就加链接）。

用法：python3 scripts/publish_alexander_acts_zh.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'alexander_raw' / 'acts'
SRC = RAW / 'zh_chapters'
OUT = ROOT / 'alexander' / 'acts' / 'zh'
META = RAW / 'zh_meta.json'


def em(t: str) -> str:
    """标签外的 *…* → <em>…</em>（标签内属性里不会有星号，仍逐段只处理标签之间的文字）。"""
    parts = re.split(r'(<[^<>]+>)', t)
    return ''.join(p if p.startswith('<') else re.sub(r'\*([^*\n]+?)\*', r'<em>\1</em>', p) for p in parts)


def label(slug: str) -> str:
    return {'preface': '著者序', 'introduction': '导论', 'title-1': '书名页（上卷）',
            'title-2': '书名页（下卷）'}.get(slug, f'使徒行传 {slug}')


CMP = ROOT / '_data' / 'compare_sources.yml'
CMP_EN = '    - {key: alexander-en, author: alexander, lang: en, label: "亚历山大注释（英文版）", url_tpl: "/alexander/acts/__CH__/"'


def compare_range(chs):
    """对照抽屉里的中文条目只覆盖已发布的连续章（从第 1 章起），免得链到还没译的章。"""
    n = 0
    while n + 1 in chs:
        n += 1
    t = CMP.read_text(encoding='utf-8')
    zh = ('    - {key: alexander, author: alexander, lang: zh, label: "亚历山大注释", '
          'url_tpl: "/alexander/acts/zh/__CH__/", accent: "#7d2f2f", ch_from: 1, ch_to: %d}' % n)
    lines = t.split('\n')
    lines = [l for l in lines if 'url_tpl: "/alexander/acts/zh/' not in l]
    if n:
        i = next(k for k, l in enumerate(lines) if l.startswith(CMP_EN))
        lines.insert(i + 1, zh)
    new = '\n'.join(lines)
    if new != t:
        CMP.write_text(new, encoding='utf-8')


def main():
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    order = ['title-1', 'preface', 'introduction'] + [str(n) for n in range(1, 13)] + ['title-2'] + [str(n) for n in range(13, 29)]
    have = [s for s in order if (SRC / f'{s}.md').exists()]
    OUT.mkdir(parents=True, exist_ok=True)
    for s in have:
        body = em((SRC / f'{s}.md').read_text(encoding='utf-8')).strip()
        # 注号链接里的 * 是注号本身，剔掉再查落单星号
        bare = re.sub(r'<sup class="aa-fnref">.*?</sup>|<a class="aa-fnback"[^>]*>.*?</a>', '', body)
        if '*' in re.sub(r'<[^<>]+>', '', bare):
            raise SystemExit(f'{s}: 转换后仍有落单的星号')
        i = order.index(s)
        prev = next((x for x in reversed(order[:i]) if x in have), None)
        nxt = next((x for x in order[i + 1:] if x in have), None)
        fm = ['---', 'layout: alexander-acts-chapter', 'book_id: acts',
              'book_name: "亚历山大《使徒行传释义》"', 'book_url: "/alexander/acts/zh/"',
              f'title: "{label(s)}"', 'subtitle: "Joseph Addison Alexander"', f'date: {meta[s]}', 'zh: true',
              f'en_url: "/alexander/acts/{s}/"']
        if s.isdigit():
            fm.append(f'chapter: {s}')
        if prev:
            fm += [f'prev_section: "{prev}"', f'prev_label: "{label(prev)}"']
        if nxt:
            fm += [f'next_section: "{nxt}"', f'next_label: "{label(nxt)}"']
        fm.append('---')
        (OUT / f'{s}.md').write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')
        print(f'写入 {OUT / (s + ".md")}', file=sys.stderr)
    compare_range([int(s) for s in have if s.isdigit()])
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'publish_alexander_acts_en.py'), '--apply'],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr)


if __name__ == '__main__':
    main()
