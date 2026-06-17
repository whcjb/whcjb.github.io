#!/usr/bin/env python3
"""
fix_romans_ocr_artifacts.py — 罗马书 OCR 发布产物 idempotent 后处理。

按 scan skill (`ocr-pipeline:04-publish`) Gate-9/10/11 修复 publish 留下的
OCR artifact。重跑安全（idempotent）：跑两次结果一样。

修复规则（按发现顺序，最稳的先做）：
1. Gate-11: verse 主体段早于对应 anchor → 删除错位副本（保留 anchor 后的正确版本）
2. Gate-10: 同章 anchor 顺序倒置 → 删除位置错的 anchor（保留正确顺序的）
3. Gate-9:  同 (N,V) 主体段双重出现 → 删除靠前的副本

锁定章节：LOCKED_CHAPTERS = {15, 16} —— 用户校准好，永远跳过。

用法（项目根目录）：
    python3 scripts/fix_romans_ocr_artifacts.py             # dry-run
    python3 scripts/fix_romans_ocr_artifacts.py --apply     # 实际写入
"""
import argparse
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROMANS_DIR = ROOT / 'calvin' / 'romans'
LOCKED_CHAPTERS = {15, 16}


def find_main_segments(text: str, ch: int):
    """Find all `**罗马书 N:V。**` main segments. Returns [(verse, start, end)]."""
    return [(int(m.group(1)), m.start(), m.end())
            for m in re.finditer(rf'\*\*罗马书\s+{ch}:(\d+)。\*\*', text)]


def find_anchors(text: str, ch: int):
    """Find all verse-anchor positions. Returns [(verse, start, end_of_line)]."""
    out = []
    for m in re.finditer(rf'<h2 class="verse-anchor"\s+id="romans-{ch}-(\d+)"[^>]*>[^<]*</h2>\n?',
                         text):
        out.append((int(m.group(1)), m.start(), m.end()))
    return out


def fix_main_before_anchor(text: str, ch: int):
    """Gate-11: 删除位置早于对应 anchor 的 verse 主体段（错位副本）。

    要求 anchor 之后还有同 verse 主体段才删（避免误删唯一一份）。
    """
    n_fixed = 0
    while True:
        mains = find_main_segments(text, ch)
        anchors = find_anchors(text, ch)
        anchor_pos = {v: pos for v, pos, _ in anchors}

        # 同一 verse 的主体段位置列表
        by_verse = {}
        for v, ms, me in mains:
            by_verse.setdefault(v, []).append((ms, me))

        fixed_one = False
        for v, occurrences in by_verse.items():
            if v not in anchor_pos: continue
            ap = anchor_pos[v]
            # 找出 anchor 前的副本
            before = [(s, e) for s, e in occurrences if s < ap]
            after = [(s, e) for s, e in occurrences if s > ap]
            if before and after:
                # 删 anchor 之前最靠前的副本（保留 anchor 之后的）
                ms, me = before[0]
                # 段落范围：从 ms 反推到该段开头（\n\n 之后）+ 到段末尾（下一个 \n\n）
                para_start = text.rfind('\n\n', 0, ms) + 2 if '\n\n' in text[:ms] else 0
                para_end_m = re.search(r'\n\n', text[me:])
                para_end = me + para_end_m.start() + 2 if para_end_m else len(text)
                text = text[:para_start] + text[para_end:]
                n_fixed += 1
                fixed_one = True
                break
        if not fixed_one:
            break
    return text, n_fixed


def fix_anchor_disorder(text: str, ch: int):
    """Gate-10: 同章 anchor 顺序倒置 → 删除位置错的较早 anchor.

    保留正确顺序的（在主体段之前的）anchor。
    """
    n_fixed = 0
    while True:
        anchors = find_anchors(text, ch)
        # 找第一个倒序对
        fixed_one = False
        for i in range(len(anchors) - 1):
            v_cur, _, _ = anchors[i]
            v_next, _, _ = anchors[i + 1]
            if v_cur >= v_next:
                # anchor[i] = v_cur 错位（应该在 v_next 之后）→ 删它
                _, start, end = anchors[i]
                text = text[:start] + text[end:]
                n_fixed += 1
                fixed_one = True
                break
        if not fixed_one:
            break
    return text, n_fixed


def fix_main_duplicate(text: str, ch: int):
    """Gate-9: 同一 (N,V) 主体段双重出现 → 删除靠前的副本（保留靠后/anchor 之后的）.

    经过 fix_main_before_anchor 后，多数双重应已消除；此处兜底。
    """
    n_fixed = 0
    while True:
        mains = find_main_segments(text, ch)
        by_verse = {}
        for v, ms, me in mains:
            by_verse.setdefault(v, []).append((ms, me))

        fixed_one = False
        for v, occs in by_verse.items():
            if len(occs) >= 2:
                # 删最靠前的副本
                ms, me = occs[0]
                para_start = text.rfind('\n\n', 0, ms) + 2 if '\n\n' in text[:ms] else 0
                para_end_m = re.search(r'\n\n', text[me:])
                para_end = me + para_end_m.start() + 2 if para_end_m else len(text)
                text = text[:para_start] + text[para_end:]
                n_fixed += 1
                fixed_one = True
                break
        if not fixed_one:
            break
    return text, n_fixed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='Actually write fixes (default: dry-run)')
    args = ap.parse_args()

    total = {'main_before_anchor': 0, 'anchor_disorder': 0, 'duplicate': 0}
    files_changed = 0

    for p in sorted(ROMANS_DIR.glob('*.md')):
        if not p.stem.isdigit():
            continue
        ch = int(p.stem)
        if ch in LOCKED_CHAPTERS:
            print(f'  {p.name}: SKIP (locked)')
            continue

        text = p.read_text(encoding='utf-8')
        orig = text

        text, n11 = fix_main_before_anchor(text, ch)
        text, n10 = fix_anchor_disorder(text, ch)
        text, n9 = fix_main_duplicate(text, ch)

        if n11 + n10 + n9 > 0:
            total['main_before_anchor'] += n11
            total['anchor_disorder'] += n10
            total['duplicate'] += n9
            print(f'  {p.name}: Gate-11={n11} Gate-10={n10} Gate-9={n9}')
            if args.apply and text != orig:
                p.write_text(text, encoding='utf-8')
                files_changed += 1

    print(f'\n汇总: Gate-11={total["main_before_anchor"]} '
          f'Gate-10={total["anchor_disorder"]} Gate-9={total["duplicate"]}')
    print(f'{"已写入" if args.apply else "Dry-run"} {files_changed} 个文件')
    if not args.apply:
        print('\n用 --apply 实际写入。')


if __name__ == '__main__':
    main()
