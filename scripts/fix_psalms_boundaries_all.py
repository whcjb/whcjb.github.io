#!/usr/bin/env python3
"""把诗篇各章错挂在前一章末尾的「章标题 + 题解 + 题词」块搬回本章开头。

缺陷来源：分章时边界取在第一个带节号的 anchor（`id="psalm-N-1-5"`），而不是
章标题行（`id="psalm-N" data-ref="PSALM N"`），于是每篇的题解落到了前一章文件末尾。

英文版 calvin/psalms-1-en/ 与中文 raw calvin_raw/psalms-1/zh_chapters/ 结构一一对应
（翻译保留了全部 HTML 锚点），所以两边做同一个搬移即可，中文不需要重翻。

用法:
    python3 scripts/fix_psalms_boundaries_all.py --dry-run
    python3 scripts/fix_psalms_boundaries_all.py
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    ROOT / 'calvin/psalms-1-en',
    ROOT / 'calvin_raw/psalms-1/zh_chapters',
]
# 章标题行：英文正文写 "PSALM 65"，中文写 "诗篇 65"，故标题文字不参与匹配
HEAD_RE = r'<h2 class="scripture-anchor" id="psalm-{n}" data-ref="PSALM {n}"[^>]*>[^<]*</h2>'
VERSE_ANCHOR_RE = re.compile(r'id="psalm-\d+-\d')
FM_RE = re.compile(r'(---\n.*?\n---\n)(.*)$', re.S)


def split_fm(text, path):
    m = FM_RE.match(text)
    if not m:
        sys.exit(f'{path}: front matter 解析失败')
    return m.group(1), m.group(2)


def fix_dir(d: Path, dry: bool, skip=()):
    moved = []
    for n in range(2, 200):
        if n in skip:
            continue
        prev_p, cur_p = d / f'{n-1}.md', d / f'{n}.md'
        if not prev_p.exists() or not cur_p.exists():
            continue
        prev_t = prev_p.read_text(encoding='utf-8')
        m = re.search(HEAD_RE.format(n=n), prev_t)
        if not m:
            continue

        fm_prev, body_prev = split_fm(prev_t, prev_p)
        idx = m.start() - len(fm_prev)
        if idx < 0:
            continue
        block = body_prev[idx:].strip()

        # 安全校验：搬走的块只能是标题+题解+题词，不得含任何经文段
        if VERSE_ANCHOR_RE.search(block):
            sys.exit(f'{prev_p}: 待搬移块含经文段 anchor，中止（可能不是纯章首块）')
        # 安全校验：本章不能已经有这个标题
        if re.search(HEAD_RE.format(n=n), cur_p.read_text(encoding='utf-8')):
            continue

        new_prev = fm_prev + body_prev[:idx].rstrip() + '\n'
        fm_cur, body_cur = split_fm(cur_p.read_text(encoding='utf-8'), cur_p)
        new_cur = fm_cur + '\n' + block + '\n\n' + body_cur.strip() + '\n'

        moved.append((n, len(block)))
        if not dry:
            for p in (prev_p, cur_p):
                p.chmod(0o644)
            prev_p.write_text(new_prev, encoding='utf-8')
            cur_p.write_text(new_cur, encoding='utf-8')
    return moved


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--skip', default='', help='跳过的诗篇号，逗号分隔（正在翻译的章节要跳过，'
                                              '否则会和 translate_serial.sh 抢同一个文件）')
    args = ap.parse_args()
    skip = {int(x) for x in args.skip.split(',') if x.strip()}

    for d in TARGETS:
        if not d.exists():
            print(f'跳过（不存在）: {d}')
            continue
        if not args.dry_run:
            bak = d.parent / (d.name + '.bak-boundaries')
            if not bak.exists():
                shutil.copytree(d, bak)
                print(f'备份 → {bak}')
        moved = fix_dir(d, args.dry_run, skip)
        print(f'\n{d.relative_to(ROOT)}: {"将搬移" if args.dry_run else "已搬移"} {len(moved)} 章')
        print('  ' + ', '.join(f'ch{n}({b}B)' for n, b in moved))
