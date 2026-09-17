#!/usr/bin/env python3
"""bridges_raw/proverbs/raw/*.md → bridges/proverbs/*.md（+ index.html）

毕列志（Charles Bridges）《箴言书注释》，改革宗翻译社简体中文版。
raw 由 extract_bridges_proverbs.py 从 PDF 提取，本脚本只加 front matter、
导航链和索引页——不改正文一个字。

导航链：前言 → 第 1 章 → … → 第 31 章 → 总结

用法:
    python3 scripts/publish_bridges_proverbs.py
    python3 scripts/publish_bridges_proverbs.py --chapter 1
"""
import argparse, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'bridges_raw/proverbs/raw'
OUT = ROOT / 'bridges/proverbs'
BOOK_ID = 'proverbs'
BOOK_NAME = '箴言书注释'
AUTHOR = '查理·毕列志（Charles Bridges）'
TRANSLATOR = '乔兰山以妲'
TOTAL = 31
# 每页一张独立风景图（img/bridges-bg-NN.jpg，由 scripts/fetch_bridges_headers.py
# 从 Unsplash 下载，本书专用、不与 nt-bg-*/calvin 图池共用）。
# 分配：index=01，前言=02，第 1–31 章=03–33，总结=34。
HEADER_POOL = 'bridges-bg-{:02d}.jpg'


def header_img(key):
    """已发布过的章节沿用原配图——同 date，手工换过的图不能被重跑刷回默认分配
    （第 8、20 章就是手工换过的）。"""
    p = OUT / f'{key}.md'
    if p.exists():
        for line in p.read_text(encoding='utf-8').split('\n', 30):
            if line.startswith('header-img:'):
                return line.split(':', 1)[1].strip()
    order = seq()                      # ['preface', '1'..'31', 'summary']
    idx = order.index(key) + 2 if key in order else 1
    return HEADER_POOL.format(idx)


def now():
    # CLAUDE.md：date 必须精确到分钟，且用真实当前时间
    return subprocess.check_output(['date', '+%Y-%m-%d %H:%M']).decode().strip()


def existing_date(key):
    """已发布过的章节沿用原 date——CLAUDE.md：已有文件的时间不要修改。"""
    p = OUT / f'{key}.md'
    if not p.exists():
        return None
    m = re.search(r'^date:\s*(.+)$', p.read_text(encoding='utf-8'), re.M)
    return m.group(1).strip() if m else None


def seq():
    """发布顺序：preface, 1..31, summary"""
    return ['preface'] + [str(i) for i in range(1, TOTAL + 1)] + ['summary']


def label(key):
    return {'preface': '前言', 'summary': '总结'}.get(key, f'第 {key} 章')


def url(key):
    return f'/bridges/{BOOK_ID}/{key}/'


def front_matter(key, stamp):
    order = seq()
    i = order.index(key)
    fm = [
        '---',
        'layout: bridges-chapter',
        f'book_id: {BOOK_ID}',
        f'book_name: {BOOK_NAME}',
        f'author: "{AUTHOR}"',
        f'header-img: {header_img(key)}',
        f'title: "{BOOK_NAME} · {label(key)}"',
        f'date: {stamp}',
    ]
    if key.isdigit():
        fm += [f'chapter: {key}', f'total_chapters: {TOTAL}']
    else:
        fm += [f'section: {key}']
    if i > 0:
        fm += [f'prev_url: {url(order[i-1])}', f'prev_label: "{label(order[i-1])}"']
    if i < len(order) - 1:
        fm += [f'next_url: {url(order[i+1])}', f'next_label: "{label(order[i+1])}"']
    fm += ['---', '']
    return '\n'.join(fm)


INDEX_INTRO = f"""---
layout: bridges-book
book_id: {BOOK_ID}
book_name: {BOOK_NAME}
author: "{AUTHOR}"
chapters: {TOTAL}
header-img: bridges-bg-01.jpg
title: "{BOOK_NAME}"
source_note: |
  英文原著 <em>An Exposition of the Book of Proverbs</em>, by Charles Bridges,
  Robert Carter &amp; Brothers, New York, 1850。<br>
  简体中文版 © 2023 改革宗翻译社（Reformation Translation Fellowship, RTF-USA），
  {TRANSLATOR} 译。原书标注「FOR FREE DISTRIBUTION ONLY – NOT FOR SALE」，
  本站仅作免费分享之用。<br>
  正文一律照中译本录入，只修正 PDF 字体映射造成的错字。另有极少数句子，
  因英文原文用了承前省略的对句、中译照搬后读来像缺字，本站对照英文原书作了
  改动——补足谓语、调整对句、必要时加一处释义括注——每一处都逐字记在下方
  「本站校订」里，未记录的即与中译本一字不差。
---

<p>本书逐段解经，共 31 章、571 个解经单元，每单元先列箴言经文，再逐层解说，
注重把箴言的智慧应用到信徒的日常生活与内心光景。书末另有作者的总结。</p>

<p>作者的前言署「1846 年 10 月 7 日，落笔于老牛顿教区」；本站所据英文版为
1850 年纽约 Robert Carter &amp; Brothers 版，中译为改革宗翻译社简体中文版。</p>

<p><strong>本站校订</strong>（对照英文原书 1865 年 Robert Carter &amp; Brothers 版）：
第 16 章 16:1 注释「我们的是媒介，他却苏醒生命」→
「我们<u>所出</u>的是媒介<u>（即工具性的作为）</u>，他<u>所赐的是</u>苏醒的生命」。
英文原文作 <em>Ours is the duty; his is the strength. Ours the agency; his the
quickening life.</em>，后半句承前省略了系动词，中译照搬这个省略，读来像是缺字；
本站补足谓语，并把主语调成「我们所出的……他所赐的……」的对句。括注中的
「工具性的作为」是本站为 <em>agency</em> 所加的释义，非译者原文。</p>

<p>逐章可读：</p>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chapter')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = now()

    todo = [args.chapter] if args.chapter else seq()
    for key in todo:
        raw_p = RAW / f'{key}.md'
        if not raw_p.exists():
            print(f'  !! 缺 raw: {raw_p}')
            continue
        body = raw_p.read_text(encoding='utf-8')
        # publish 只加壳，不动正文。这三条是 pdf-pipeline §0.4/§0.5 的通用净化
        body = body.replace('****', '')
        body = re.sub(r'<<<[^>]*?>>>', '', body)
        out_p = OUT / f'{key}.md'
        out_p.write_text(front_matter(key, existing_date(key) or stamp) + body,
                         encoding='utf-8')
        print(f'✓ {out_p.relative_to(ROOT)} ({out_p.stat().st_size} bytes)')

    if not args.chapter:
        idx = OUT / 'index.html'
        idx.write_text(INDEX_INTRO, encoding='utf-8')
        print(f'✓ {idx.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
