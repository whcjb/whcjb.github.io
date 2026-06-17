#!/usr/bin/env python3
"""
fix_romans_ocr_artifacts.py — 罗马书 OCR 发布产物 idempotent 后处理。

按 scan skill (`ocr-pipeline:04-publish`) Gate-9/10/11 修复 publish 留下的
OCR artifact。重跑安全（idempotent）：跑两次结果一样。

修复规则（按发现顺序，最稳的先做）：
1. Gate-11: verse 主体段早于对应 anchor → 删除错位副本（保留 anchor 后的正确版本）
2. Gate-10: 同章 anchor 顺序倒置 → 删除位置错的 anchor（保留正确顺序的）
3. Gate-9:  同 (N,V) 主体段双重出现 → 删除靠前的副本
4. Gate-12: 嵌入式主体段（`**罗马书 N:V。**` 出现在段中而非段首）→ 报告，
   不自动修（需人工分段 + 补 anchor，分段位置脚本无法判断）
5. Gate-13: 缺失 anchor（有主体段但无对应 anchor）→ 报告，需人工补

Detect-only gates（12/13）只报告不修改，避免误删用户校准的内容。

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


def fix_missing_anchor(text: str, ch: int):
    """Gate-13 自动修：主体段段首正确但缺 anchor → 在主体段前插入 anchor。

    仅当主体段前段是空白（即段首干净）时才修；若是嵌入式（Gate-12），跳过。
    """
    n_fixed = 0
    # 收集所有当前 anchor
    while True:
        main_v = {int(m.group(1)) for m in
                  re.finditer(rf'\*\*罗马书\s+{ch}:(\d+)。\*\*', text)}
        anchor_v = {int(m.group(1)) for m in
                    re.finditer(rf'class="verse-anchor"\s+id="romans-{ch}-(\d+)"', text)}
        single = {int(m.group(1)) for m in
                  re.finditer(rf'^## 罗马书 {ch}:(\d+)\s*$', text, re.MULTILINE)}
        missing = sorted(main_v - anchor_v - single)

        fixed_one = False
        for v in missing:
            m = re.search(rf'\*\*罗马书\s+{ch}:{v}。\*\*', text)
            if not m:
                continue
            ms = m.start()
            before = text[:ms]
            para_start = max(before.rfind('\n\n') + 2,
                             before.rfind('</h2>'),
                             before.rfind('</div>'))
            between = text[para_start:ms].strip()
            # 段首干净（前面是 \n\n / </h2> / </div>）才自动补
            if between and not between.endswith(('>', '\n')):
                continue
            anchor_html = (f'<h2 class="verse-anchor" id="romans-{ch}-{v}" '
                           f'data-ref="罗马书 {ch}:{v}">罗马书 {ch}:{v}</h2>\n\n')
            # 在主体段前插入 anchor (确保前面有 \n\n)
            insert_at = ms
            text = text[:insert_at] + anchor_html + text[insert_at:]
            n_fixed += 1
            fixed_one = True
            break
        if not fixed_one:
            break
    return text, n_fixed


def detect_embedded_main(text: str, ch: int):
    """Gate-12: 嵌入式主体段。`**罗马书 N:V。**` 出现在段中（非段首+非紧跟 anchor）。

    检测：找所有 main marker，看其前是否有非空白非 anchor 字符（即段中嵌入）。
    返回 [(verse, line_num, context)] 不修改文本。
    """
    issues = []
    for m in re.finditer(rf'\*\*罗马书\s+{ch}:(\d+)。\*\*', text):
        v = int(m.group(1))
        ms = m.start()
        # 段首 = 文件首 / `\n\n` 后 / `</h2>\n*` 后
        if ms == 0:
            continue
        before = text[:ms]
        # 反查最近的 `\n\n` 或 `</h2>` 或 `</div>`
        para_start = max(
            before.rfind('\n\n') + 2,
            before.rfind('</h2>'),
            before.rfind('</div>'),
        )
        between = text[para_start:ms].strip()
        # 段首允许空、html 标签、`#` 标题
        if between and not between.endswith(('>', '。', '\n')):
            line = text[:ms].count('\n') + 1
            ctx = text[max(0, ms - 40):ms + 30].replace('\n', ' ')
            issues.append((v, line, ctx))
    return issues


def detect_missing_anchor(text: str, ch: int):
    """Gate-13: 有 `**罗马书 N:V。**` 主体段但缺对应 verse-anchor。

    单 verse section（如 `## 罗马书 12:3` 后接 scripture-anchor `romans-12-3`）
    不需要额外 verse-anchor，从结果排除。
    """
    main_verses = {int(m.group(1)) for m in
                   re.finditer(rf'\*\*罗马书\s+{ch}:(\d+)。\*\*', text)}
    anchor_verses = {int(m.group(1)) for m in
                     re.finditer(rf'class="verse-anchor"\s+id="romans-{ch}-(\d+)"', text)}
    single_verse_sections = {int(m.group(1)) for m in
                             re.finditer(rf'^## 罗马书 {ch}:(\d+)\s*$', text, re.MULTILINE)}
    return sorted(main_verses - anchor_verses - single_verse_sections)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='Actually write fixes (default: dry-run)')
    args = ap.parse_args()

    total = {'main_before_anchor': 0, 'anchor_disorder': 0, 'duplicate': 0,
             'embedded': 0, 'missing_anchor': 0}
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

        # Detect-only gates（不修改文本）
        embedded = detect_embedded_main(text, ch)
        missing = detect_missing_anchor(text, ch)
        total['embedded'] += len(embedded)
        total['missing_anchor'] += len(missing)

        if n11 + n10 + n9 > 0 or embedded or missing:
            total['main_before_anchor'] += n11
            total['anchor_disorder'] += n10
            total['duplicate'] += n9
            msg = f'  {p.name}: Gate-11={n11} Gate-10={n10} Gate-9={n9}'
            if embedded:
                msg += f' Gate-12={len(embedded)}'
            if missing:
                msg += f' Gate-13={len(missing)} (verses {missing})'
            print(msg)
            for v, line, ctx in embedded:
                print(f'    Gate-12 v.{ch}:{v} @L{line}  ...{ctx}...')
            if args.apply and text != orig:
                p.write_text(text, encoding='utf-8')
                files_changed += 1

    print(f'\n汇总: Gate-11={total["main_before_anchor"]} '
          f'Gate-10={total["anchor_disorder"]} Gate-9={total["duplicate"]} '
          f'Gate-12={total["embedded"]} Gate-13={total["missing_anchor"]}')
    print(f'{"已写入" if args.apply else "Dry-run"} {files_changed} 个文件')
    if total['embedded'] or total['missing_anchor']:
        print('\n⚠️  Gate-12/13 是 detect-only，不会自动修。需人工:')
        print('   - Gate-12: 主体段嵌在段中 → 段首加 \\n\\n 拆段')
        print('   - Gate-13: verse 缺 anchor → scripture-box 后插入 <h2 class="verse-anchor">')
    if not args.apply:
        print('\n用 --apply 实际写入。')


if __name__ == '__main__':
    main()
